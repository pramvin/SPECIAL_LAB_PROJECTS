"""Layer 1b: pick which fresh headlines deserve an AI review (the cheap filter before the LLM).

Every new, non-noise, scored headline on a stock that is in the curated list (`in_top = 1`) is judged once:
- material  = the local sentiment model is confident it is bullish/bearish (>= MIN_CONF), or the
              headline mentions an event word (earnings, downgrade, lawsuit, FDA, merger, ...)
- a stock with a material headline goes to the AI unless it was already reviewed in the last
  COOLDOWN_H hours; at most MAX_PAIRS (stock, horizon) pairs go per run, the rest wait for the next run
- everything else is logged as `skip`, so no headline is judged twice

The AI step is `python -m agents.run --mode funnel` (one quick call per stock, then the 12-agent review
only for the few the quick call flags, at most FULL_PER_RUN per horizon). The AI never changes a score.
The filter is a guess, not validated: the point of `news_triggers` is to measure later whether flagged
headlines were followed by bigger moves (join with `news_reaction`).

Run from Backend/ after sentiment:
  .venv/bin/python -m pipeline.news_trigger --dry-run   # show decisions, write nothing, call no LLM
  .venv/bin/python -m pipeline.news_trigger             # decide, log, run the AI step
"""
import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from app.dbcompat import connect, table_names

DB_PATH = os.environ.get("PLANWISE_DB", os.path.join(os.path.dirname(__file__), "..", "planwise.db"))
MIN_CONF = 0.6
COOLDOWN_H = 5
LOOKBACK_H = 6
MAX_PAIRS = 8
FULL_PER_RUN = 2

MATERIAL = re.compile(
    r"\b(earnings|guidance|outlook|downgrad\w*|upgrad\w*|price target|lawsuit|sues?|sued|probe|investigation|"
    r"recall|fda|approv\w*|merger|acquir\w*|acquisition|buyout|takeover|bankrupt\w*|layoffs?|"
    r"resigns?|steps? down|dividend|buyback|short seller|halts?|plunge\w*|soar\w*|surge\w*|tumble\w*)\b",
    re.I,
)

# Market-wide wrap-ups that Yahoo tags to many stocks: they say nothing about one company.
GENERIC = re.compile(r"^stock market today|^stocks? (making|moving)|^dow,? s&p|\bwall street\b.*\b(today|week)\b", re.I)

SCHEMA = """
CREATE TABLE IF NOT EXISTS news_triggers (
  news_id INTEGER PRIMARY KEY REFERENCES news_items(id),
  ticker TEXT NOT NULL,
  decided_at TEXT NOT NULL,
  material INTEGER NOT NULL,
  reason TEXT,
  decision TEXT NOT NULL
);
"""


def material_reason(title: str, sentiment: str | None, p: float | None) -> str | None:
    """Why this headline counts as material, or None."""
    if GENERIC.search(title):
        return None
    if sentiment in ("bullish", "bearish") and p is not None and p >= MIN_CONF:
        return f"model says {sentiment} ({p:.2f})"
    m = MATERIAL.search(title)
    return f"event word '{m.group(1).lower()}'" if m else None


def candidates(conn, now: datetime) -> list[dict]:
    """New scored headlines on curated stocks, one dict per headline."""
    since = (now - timedelta(hours=LOOKBACK_H)).isoformat()
    rows = conn.execute(
        "SELECT n.id, n.ticker, n.title, s.sentiment, s.p_bearish, s.p_bullish, s.p_neutral "
        "FROM news_items n JOIN news_scores s ON s.news_id = n.id "
        "LEFT JOIN news_triggers t ON t.news_id = n.id "
        "WHERE t.news_id IS NULL AND n.rule_noise = 0 AND n.first_seen_at >= ? "
        "AND n.ticker IN (SELECT ticker FROM recommendations WHERE in_top = 1) "
        "ORDER BY n.id",
        (since,),
    ).fetchall()
    seen: dict[int, dict] = {}
    for nid, ticker, title, sent, pb, pu, pn in rows:
        p = {"bearish": pb, "bullish": pu, "neutral": pn}.get(sent)
        seen[nid] = {"id": nid, "ticker": ticker, "title": title, "reason": material_reason(title, sent, p)}
    return list(seen.values())


def last_review(conn, ticker: str) -> str | None:
    if "agent_runs" not in table_names(conn):
        return None
    row = conn.execute(
        "SELECT MAX(finished_at) FROM agent_runs WHERE ticker = ? AND status IN ('ok', 'partial')", (ticker,)
    ).fetchone()
    return row[0] if row else None


def horizons(conn, ticker: str) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT horizon FROM recommendations WHERE ticker = ? AND in_top = 1 ORDER BY horizon", (ticker,)
    ).fetchall()
    return [r[0] for r in rows]


def decide(conn, now: datetime, max_pairs: int = MAX_PAIRS) -> dict:
    """Judge every new headline. Returns {'pairs': [(ticker, horizon)], 'log': [...], 'stats': {...}}."""
    cands = candidates(conn, now)
    by_ticker: dict[str, list[dict]] = {}
    log: list[tuple] = []  # (news_id, ticker, material, reason, decision)
    for c in cands:
        if c["reason"] is None:
            log.append((c["id"], c["ticker"], 0, None, "skip"))
        else:
            by_ticker.setdefault(c["ticker"], []).append(c)

    cutoff = (now - timedelta(hours=COOLDOWN_H)).isoformat()
    ready: list[tuple[str, list[dict]]] = []
    for ticker, items in by_ticker.items():
        last = last_review(conn, ticker)
        if last and last >= cutoff:
            log += [(c["id"], ticker, 1, c["reason"], "cooldown") for c in items]
        else:
            ready.append((ticker, items))
    ready.sort(key=lambda t: (-len(t[1]), t[0]))

    pairs: list[tuple[str, str]] = []
    taken = 0
    for ticker, items in ready:
        hs = horizons(conn, ticker)
        if pairs and len(pairs) + len(hs) > max_pairs:
            continue  # not logged: waits for the next run
        pairs += [(ticker, h) for h in hs]
        log += [(c["id"], ticker, 1, c["reason"], "review") for c in items]
        taken += 1
    stats = {"new": len(cands), "material": sum(len(i) for _, i in ready) + sum(1 for x in log if x[4] == "cooldown"),
             "tickers_to_review": taken, "waiting": len(ready) - taken}
    return {"pairs": pairs, "log": log, "stats": stats, "examples": {t: i[0]["title"] for t, i in ready[:taken]}}


def save_log(conn, log: list[tuple], now: datetime) -> None:
    with conn:
        conn.executemany(
            "INSERT INTO news_triggers (news_id, ticker, decided_at, material, reason, decision) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (news_id) DO NOTHING",
            [(nid, t, now.isoformat(), m, r, d) for nid, t, m, r, d in log],
        )


def run_ai(pairs: list[tuple[str, str]], workers: int = 3) -> int:
    """One funnel run per horizon. A failed run is reported and does not stop the others."""
    by_h: dict[str, list[str]] = {}
    for ticker, h in pairs:
        by_h.setdefault(h, []).append(ticker)
    failed = 0
    for h, tickers in by_h.items():
        cmd = [sys.executable, "-m", "agents.run", "--mode", "funnel", "--horizon", h, "--tickers", ",".join(tickers),
               "--full", str(FULL_PER_RUN), "--workers", str(workers), "--no-settle"]
        print(f"AI step ({h}): {' '.join(tickers)}", flush=True)
        if subprocess.run(cmd).returncode:
            failed += 1
    return failed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="show decisions; write nothing and call no LLM")
    ap.add_argument("--max-pairs", type=int, default=MAX_PAIRS)
    args = ap.parse_args()
    from agents import config
    config.load_env()  # DATABASE_URL (Neon) unless PLANWISE_DB points at a SQLite file
    now = datetime.now(timezone.utc)
    conn = connect(DB_PATH)
    conn.executescript(SCHEMA)
    d = decide(conn, now, args.max_pairs)
    s = d["stats"]
    print(f"trigger: {s['new']} new headlines, {s['material']} material, "
          f"{s['tickers_to_review']} stocks go to the AI, {s['waiting']} wait for the next run")
    for t, title in d["examples"].items():
        print(f"  {t}: {title[:90]}")
    if args.dry_run:
        print("dry run: nothing written, no LLM called")
        return 0
    save_log(conn, d["log"], now)
    conn.close()
    return 1 if d["pairs"] and run_ai(d["pairs"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
