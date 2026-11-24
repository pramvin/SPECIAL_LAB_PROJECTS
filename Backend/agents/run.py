"""CLI: run the click analysis for some tickers.

  python -m agents.run --tickers DIS,AAPL [--horizon 1w] [--fake]

`--fake` uses canned model replies, so no key is needed, but it writes into the database and
therefore refuses to run unless `PLANWISE_DB` points at a scratch SQLite file.
"""
from __future__ import annotations

import argparse
import os
import sys

from app.dbcompat import connect

from . import analyze, config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Click analysis (market, news, social)")
    parser.add_argument("--tickers", required=True, help="comma-separated tickers")
    parser.add_argument("--horizon", default="1w", choices=["1w"])
    parser.add_argument("--fake", action="store_true", help="canned model replies, no key needed")
    args = parser.parse_args(argv)

    if args.fake and not os.environ.get("PLANWISE_DB"):
        print("--fake writes canned analyses into a database; set PLANWISE_DB to a scratch SQLite "
              "file first, so a dry run never touches the real DATABASE_URL.", file=sys.stderr)
        return 2
    try:
        llm = analyze.make_llm(args.fake)
    except Exception as exc:  # noqa: BLE001 - the message names the missing setting, never a value
        print(exc, file=sys.stderr)
        return 2

    path = config.db_path()
    worst = 0
    for ticker in (t.strip().upper() for t in args.tickers.split(",") if t.strip()):
        run_id = analyze.run_analysis(lambda: connect(path), llm, ticker, args.horizon)
        conn = connect(path)
        row = conn.execute("SELECT status, tokens, error FROM stock_analysis WHERE id = ?",
                           (run_id,)).fetchone() if run_id else None
        conn.close()
        status = row[0] if row else "error"
        print(f"{ticker}: {status} (run {run_id}), tokens {row[1] if row else 0}"
              + (f", {row[2]}" if row and row[2] else ""))
        worst = max(worst, 0 if status in ("ok", "partial") else 1)
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
