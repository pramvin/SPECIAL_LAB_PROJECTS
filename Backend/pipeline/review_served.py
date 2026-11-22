"""Keep every idea the web actually serves reviewed by the AI (one quick call each).

The news filter (`pipeline.news_trigger`) only calls the AI when a fresh headline looks important, so most
cards stayed on "AI pending". This step looks at what users are really served and reviews exactly those pairs:
- the curated top 5 of each horizon (what a user without a profile sees), and
- the top 5 of every saved profile on each horizon (`app.matching.rank_for_user`, the same call the API makes).
A (stock, horizon) pair is skipped when it already has an ok/partial review for the current ranking date.
At most MAX_PER_RUN pairs go per run, curated first, one horizon after another in turn, so a run costs a bounded
number of quick calls (about 2.7k tokens, 35 to 240 s each) and the rest waits for the next hourly run.
The review never changes a score or a rank.

Run from Backend/:
  .venv/bin/python -m pipeline.review_served --dry-run   # show what would be reviewed, call no LLM
  .venv/bin/python -m pipeline.review_served             # review up to MAX_PER_RUN pairs now
"""
import argparse
import os
import subprocess
import sys

from app import matching
from app.dbcompat import connect, table_names

DB_PATH = os.environ.get("PLANWISE_DB", os.path.join(os.path.dirname(__file__), "..", "planwise.db"))
HORIZONS = ("1w", "1m", "3m")
N_SERVED = 5  # keep equal to TOP_N_SERVED in app/main.py
MAX_PER_RUN = 12


def served(conn, n: int = N_SERVED) -> tuple[str | None, dict[str, list[str]]]:
    """(ranking date, {horizon: tickers served}); curated stocks first, then each distinct profile's picks."""
    row = conn.execute("SELECT MAX(as_of) FROM recommendations WHERE horizon = '1w'").fetchone()
    as_of = row[0] if row else None
    out: dict[str, list[str]] = {h: [] for h in HORIZONS}
    if not as_of:
        return None, out
    rows_by_h = {}
    for h in HORIZONS:
        rows = conn.execute(
            "SELECT ticker, sector, score, atr_pct, in_top FROM recommendations WHERE as_of = ? AND horizon = ? "
            "ORDER BY score DESC, ticker", (as_of, h)).fetchall()
        rows_by_h[h] = [dict(zip(("ticker", "sector", "score", "atr_pct", "in_top"), tuple(r))) for r in rows]
        out[h] = [r["ticker"] for r in rows_by_h[h] if r["in_top"]][:n]
    profiles = conn.execute("SELECT sectors, risk_level FROM risk_profiles ORDER BY user_id DESC").fetchall() \
        if "risk_profiles" in table_names(conn) else []
    for sectors, level in dict.fromkeys((r[0], r[1]) for r in profiles):  # distinct profiles, newest user first
        for h in HORIZONS:
            for r in matching.rank_for_user(rows_by_h[h], sectors.split(","), level, n):
                if r["ticker"] not in out[h]:
                    out[h].append(r["ticker"])
    return as_of, out


def pending(conn, as_of: str | None, wanted: dict[str, list[str]], limit: int = MAX_PER_RUN,
            redo_before: str | None = None) -> list[tuple[str, str]]:
    """(ticker, horizon) pairs without a review for `as_of`, horizons taking turns, capped at `limit`.
    With `redo_before` (UTC ISO time) a review that started earlier does not count, so it is redone."""
    done: set[tuple[str, str]] = set()
    if as_of and "agent_runs" in table_names(conn):
        sql = "SELECT ticker, horizon FROM agent_runs WHERE as_of = ? AND status IN ('ok', 'partial')"
        params: list = [as_of]
        if redo_before:
            sql += " AND started_at >= ?"
            params.append(redo_before)
        done = {(r[0], r[1]) for r in conn.execute(sql, params).fetchall()}
    order = []
    for i in range(max((len(v) for v in wanted.values()), default=0)):
        for h in HORIZONS:
            if i < len(wanted[h]) and (wanted[h][i], h) not in done:
                order.append((wanted[h][i], h))
    return order[:limit]


def run_ai(pairs: list[tuple[str, str]], workers: int = 3, runner=subprocess.run) -> int:
    """One quick-review run per horizon. A failed run is reported and does not stop the others."""
    by_h: dict[str, list[str]] = {}
    for ticker, h in pairs:
        by_h.setdefault(h, []).append(ticker)
    failed = 0
    for h, tickers in by_h.items():
        cmd = [sys.executable, "-m", "agents.run", "--mode", "triage", "--horizon", h, "--tickers", ",".join(tickers),
               "--workers", str(workers), "--no-settle"]
        print(f"review served ({h}): {' '.join(tickers)}", flush=True)
        if runner(cmd).returncode:
            failed += 1
    return failed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="show the plan; call no LLM")
    ap.add_argument("--max", type=int, default=MAX_PER_RUN, help="most pairs to review in this run")
    ap.add_argument("--redo-before", help="UTC ISO time: redo reviews that started before it (e.g. after a bug fix)")
    args = ap.parse_args()
    from agents import config

    config.load_env()  # DATABASE_URL (Neon) unless PLANWISE_DB points at a SQLite file
    conn = connect(DB_PATH)
    as_of, wanted = served(conn)
    pairs = pending(conn, as_of, wanted, args.max, args.redo_before)
    total = sum(len(v) for v in wanted.values())
    print(f"review served: ranking {as_of}, {total} served pairs, {len(pairs)} to review now")
    conn.close()
    if args.dry_run or not pairs:
        return 0
    return 1 if run_ai(pairs) else 0


if __name__ == "__main__":
    raise SystemExit(main())
