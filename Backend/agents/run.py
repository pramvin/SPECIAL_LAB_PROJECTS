"""CLI: review tickers with the AI agent team.

  python -m agents.run [--mode full|triage|funnel] [--horizon 1w] [--top N] [--full 15]
                       [--tickers TYL,GDDY] [--workers 2] [--fake] [--no-settle]

Modes:
  full    12-agent review of the curated top list (default, top 20)
  triage  one quick LLM call per stock on every ranked idea, best score first (default top 100)
  funnel  triage first, then the 12-agent review for the stocks it flags (at most --full)

Each worker gets its own DB connection. `--fake` uses canned valid replies, so
no key or network is needed for a dry run.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.dbcompat import connect

from . import config, graph, llm_client, memory, schema, triage

DEFAULT_TOP = {"full": 20, "triage": 100, "funnel": 100}


def _tickers(conn, horizon: str, top: int) -> list[str]:
    rows = conn.execute(
        "SELECT ticker FROM recommendations WHERE horizon = ? AND in_top = 1 "
        "ORDER BY score DESC, ticker LIMIT ?", (horizon, top),
    ).fetchall()
    return [row[0] for row in rows]


def _ranked(conn, horizon: str, top: int) -> list[str]:
    """Every idea that passed the rules (not only the curated list), best score first."""
    rows = conn.execute(
        "SELECT ticker FROM recommendations WHERE horizon = ? "
        "ORDER BY score DESC, ticker LIMIT ?", (horizon, top),
    ).fetchall()
    return [row[0] for row in rows]


def _make_llm(fake: bool, model: str | None = None):
    settings = config.llm_settings()
    if fake:
        return llm_client.FakeLLM(auto=True)
    return llm_client.OpenAICompatLLM(
        settings["base_url"], settings["api_key"], model or settings["model"], settings["deep_model"])


def _run_batch(path: str, tickers: list[str], horizon: str, workers: int, llm, review_fn, label: str):
    """Run `review_fn` over tickers in a thread pool; returns {ticker: (run_id, status, rating)}."""
    print(f"{label}: {len(tickers)} ticker(s), horizon {horizon}, workers {workers}")
    results: dict[str, tuple[int | None, str, str | None]] = {}

    def work(ticker: str):
        worker_conn = connect(path)
        def on_event(role, status, latency, tokens, detail=None):
            line = f"  {ticker} {role}: {status} {latency}ms {tokens}tok"
            if detail:
                line += f" ({detail})"
            print(line)
        run_id = review_fn(worker_conn, llm, ticker, horizon, fetchers=None, on_event=on_event)
        row = worker_conn.execute(
            "SELECT status, rating FROM agent_runs WHERE id = ?", (run_id,)).fetchone()
        worker_conn.close()
        return ticker, run_id, (row[0] if row else "error"), (row[1] if row else None)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(work, ticker) for ticker in tickers]
        for future in as_completed(futures):
            ticker, run_id, status, rating = future.result()
            results[ticker] = (run_id, status, rating)
            print(f"{ticker}: {rating or '-'} ({status}) run {run_id}")

    ok = sum(1 for _, status, _ in results.values() if status in ("ok", "partial"))
    print(f"{label} done: {ok}/{len(results)} ticker(s)")
    _print_tokens(path, results)
    return results


def _print_tokens(path: str, results: dict) -> None:
    run_ids = [run_id for run_id, _, _ in results.values() if run_id]
    if not run_ids:
        return
    conn = connect(path)
    marks = ",".join("?" for _ in run_ids)
    row = conn.execute(
        f"SELECT COALESCE(SUM(tokens_in), 0), COALESCE(SUM(tokens_out), 0) "
        f"FROM agent_runs WHERE id IN ({marks})", run_ids).fetchone()
    conn.close()
    tin, tout = int(row[0]), int(row[1])
    per = (tin + tout) // len(run_ids)
    print(f"tokens: in {tin}, out {tout}, about {per} per ticker "
          f"(as reported by the provider; some providers leave reasoning tokens out)")


def _print_source_status(path: str, results: dict) -> None:
    source_status: dict[str, dict[str, int]] = {}
    check_conn = connect(path)
    for run_id, _, _ in results.values():
        if not run_id:
            continue
        row = check_conn.execute("SELECT sources_json FROM agent_runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            continue
        try:
            sources = json.loads(row[0])
        except ValueError:
            continue
        for source, info in sources.items():
            bucket = source_status.setdefault(source, {})
            status = (info or {}).get("status", "unavailable")
            bucket[status] = bucket.get(status, 0) + 1
    check_conn.close()
    for source in sorted(source_status):
        counts = ", ".join(f"{status}={count}" for status, count in sorted(source_status[source].items()))
        print(f"source {source}: {counts}")


def _triage_rows(path: str, horizon: str, results: dict) -> list[dict]:
    """Rating, confidence and rule score of each triaged ticker, read back from the DB."""
    conn = connect(path)
    rows = []
    for ticker, (run_id, status, rating) in results.items():
        if not run_id or status not in ("ok", "partial"):
            continue
        row = conn.execute("SELECT final_json FROM agent_runs WHERE id = ?", (run_id,)).fetchone()
        try:
            final = json.loads(row[0]) if row and row[0] else {}
        except ValueError:
            final = {}
        rows.append({"ticker": ticker, "rating": rating, "confidence": final.get("confidence"),
                     "score": (final.get("rules") or {}).get("score") or 0})
    conn.close()
    return rows


def _print_triage_summary(rows: list[dict]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["rating"] or "-"] = counts.get(row["rating"] or "-", 0) + 1
    print("triage ratings: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AI trading-agent review")
    parser.add_argument("--mode", default="full", choices=["full", "triage", "funnel"])
    parser.add_argument("--horizon", default="1w", choices=["1w", "1m", "3m"])
    parser.add_argument("--top", type=int, default=None,
                        help="how many ideas (default: 20 for full, 100 for triage/funnel)")
    parser.add_argument("--full", type=int, default=15,
                        help="funnel: most stocks that go on to the 12-agent review")
    parser.add_argument("--tickers", help="comma-separated tickers (overrides --top)")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--fake", action="store_true", help="canned model replies, no network")
    parser.add_argument("--no-settle", action="store_true", help="skip settling past decisions")
    args = parser.parse_args(argv)

    config.load_env()
    settings = config.llm_settings()
    if not args.fake and not settings["api_key"]:
        print("AGENT_LLM_API_KEY is not set in Backend/.env (or use --fake for a dry run).",
              file=sys.stderr)
        return 2
    if not args.fake and not settings["base_url"]:
        print("AGENT_LLM_BASE_URL is not set in Backend/.env.", file=sys.stderr)
        return 2
    if args.fake and not os.environ.get("PLANWISE_DB"):
        print("--fake writes canned reviews into a database; set PLANWISE_DB to a scratch "
              "SQLite file first (e.g. PLANWISE_DB=/tmp/planwise-fake.db), so a dry run "
              "never touches the real DATABASE_URL.", file=sys.stderr)
        return 2

    top = max(1, args.top if args.top is not None else DEFAULT_TOP[args.mode])
    path = config.db_path()
    conn = connect(path)
    schema.ensure(conn)
    llm = _make_llm(args.fake)

    if args.mode != "triage" and not args.no_settle:
        def settle_event(role, status, latency, tokens, detail):
            print(f"settle {role}: {status} {latency}ms {tokens}tok" + (f" ({detail})" if detail else ""))
        settled = memory.settle(conn, llm, on_event=settle_event)
        if settled:
            print(f"settled {settled} past decision(s)")

    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    elif args.mode == "full":
        tickers = _tickers(conn, args.horizon, top)
    else:
        tickers = _ranked(conn, args.horizon, top)
    conn.close()
    if not tickers:
        print("No tickers to review (run the ranking pipeline first or pass --tickers).")
        return 0

    if args.mode == "full":
        results = _run_batch(path, tickers, args.horizon, args.workers, llm,
                             graph.review_ticker, "Full review")
        _print_source_status(path, results)
        ok = sum(1 for _, status, _ in results.values() if status in ("ok", "partial"))
        return 0 if ok else 1

    triage_llm = _make_llm(args.fake, settings["triage_model"])
    results = _run_batch(path, tickers, args.horizon, args.workers, triage_llm,
                         triage.triage_ticker, "Quick review (triage)")
    rows = _triage_rows(path, args.horizon, results)
    _print_triage_summary(rows)
    ok = sum(1 for _, status, _ in results.values() if status in ("ok", "partial"))
    if args.mode == "triage":
        return 0 if ok else 1

    picked = triage.select_for_full(rows, args.full)
    if not picked:
        print("Funnel: the quick review flagged nothing for the full review.")
        return 0 if ok else 1
    print("Funnel: going on to the full review: " + ", ".join(
        f"{p['ticker']} ({p['reason']})" for p in picked))
    full_results = _run_batch(path, [p["ticker"] for p in picked], args.horizon, args.workers, llm,
                              graph.review_ticker, "Full review")
    _print_source_status(path, full_results)
    full_ok = sum(1 for _, status, _ in full_results.values() if status in ("ok", "partial"))
    return 0 if (ok and full_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
