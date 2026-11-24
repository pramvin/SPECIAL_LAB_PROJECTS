"""Layer 1 wrapper: one command for the scheduled job.

Order: collect headlines -> score new ones with the local model -> record price reactions ->
refresh the earnings calendar -> take an intraday volume snapshot of the curated stocks ->
log and score the shadow Top 5 portfolios (`pipeline.shadow`).
A failing step is printed and the next one still runs, because for example a Yahoo news outage
must not stop the reaction slots from filling. Exit code is 1 if any step failed.

Scope of the news step (`--scope`):
  ideas  only stocks currently in `recommendations` (about 170, about 2 minutes)
  all    the whole S&P 500 (about 5 to 10 minutes), keeps the training archive complete
  auto   `all` in even UTC hours, `ideas` in odd hours (default; made for an hourly schedule)

Settings come from Backend/.env (DATABASE_URL = Neon). Set PLANWISE_DB to a SQLite file to test
without touching Neon. Only one run at a time: a run that finds another one still going exits at once.

Run from Backend/:  .venv/bin/python -m pipeline.collect_hourly [--scope auto]
"""
import argparse
import fcntl
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

from agents import config

LOCK = os.path.join(tempfile.gettempdir(), "planwise_collect.lock")


def steps(scope: str) -> list[tuple[str, list[str]]]:
    all_ = scope == "all"
    return [
        ("news", ["-m", "pipeline.news"] + (["--all"] if all_ else [])),
        ("sentiment", ["-m", "pipeline.sentiment"] + (["--all"] if all_ else [])),
        ("reaction", ["-m", "pipeline.reaction"]),
        ("earnings", ["-m", "pipeline.earnings"]),  # skips tickers fetched in the last 20 h
        ("intraday", ["-m", "pipeline.intraday"]),  # writes only while the US market is open
        ("shadow", ["-m", "pipeline.shadow"]),  # logs Top 5 picks once per ranking date, scores matured ones
    ]


def resolve_scope(scope: str, now: datetime) -> str:
    if scope != "auto":
        return scope
    return "all" if now.hour % 2 == 0 else "ideas"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=["ideas", "all", "auto"], default="auto")
    args = ap.parse_args()

    config.load_env()  # DATABASE_URL etc.; PLANWISE_DB (if set) still wins
    lock = open(LOCK, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("another collect run is still going; exiting")
        return 0

    scope = resolve_scope(args.scope, datetime.now(timezone.utc))
    target = "SQLite " + os.environ["PLANWISE_DB"] if os.environ.get("PLANWISE_DB") else (
        "Postgres (DATABASE_URL)" if os.environ.get("DATABASE_URL") else "local SQLite")
    print(f"collect: scope={scope}, database={target}", flush=True)

    failed = []
    for name, cmd in steps(scope):
        t0 = time.time()
        print(f"== {name} ==", flush=True)
        code = subprocess.run([sys.executable, *cmd]).returncode
        print(f"== {name}: {'ok' if code == 0 else f'FAILED (exit {code})'} in {time.time() - t0:.0f}s ==", flush=True)
        if code:
            failed.append(name)
    if failed:
        print("failed steps: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
