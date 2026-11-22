"""Which stocks joined or left the S&P 500, and when, so tests can include stocks that no longer exist.

All our price experiments use today's 500 stocks only ("survivors"), which flatters every result: a stock
that was dropped after a fall is simply missing. This step stores the public change log (Wikipedia page
"Historical components of the S&P 500", about 400 rows back to 1976) and, with `--check`, asks Yahoo whether
the price history of each removed stock still exists. It downloads no prices into the database; the output is
the size of the gap, so we know how far a survivor-free test could go.

A removed stock counts as "price_ok" only if Yahoo has bars from at least a year before its removal date and
within 30 days of it. That rejects the common failure where Yahoo hands back a different, newer company that
reuses the symbol. Stocks bought out or gone bankrupt are often missing from Yahoo entirely.

Run from Backend/ (manual, the page changes only a few times a month; not part of the hourly job):
  .venv/bin/python -m pipeline.index_changes            # fetch the change log and store it
  .venv/bin/python -m pipeline.index_changes --check    # also test which removed stocks have usable prices
"""
import argparse
import os
from datetime import date, timedelta
from io import StringIO

import pandas as pd
import requests

from app.dbcompat import connect

DB_PATH = os.environ.get("PLANWISE_DB", os.path.join(os.path.dirname(__file__), "..", "planwise.db"))
URL = "https://en.wikipedia.org/wiki/Historical_components_of_the_S%26P_500"
UA = {"User-Agent": "PlanWiseAI-student-project/0.1"}
BATCH = 40

SCHEMA = """
CREATE TABLE IF NOT EXISTS index_changes (
  effective_date TEXT NOT NULL,
  added_ticker TEXT NOT NULL,
  removed_ticker TEXT NOT NULL,
  reason TEXT,
  price_ok INTEGER,
  PRIMARY KEY (effective_date, added_ticker, removed_ticker)
);
"""


def _ticker(v) -> str:
    return "" if v is None or pd.isna(v) else str(v).replace(".", "-").strip()


def rows_from_table(t: pd.DataFrame) -> list[tuple]:
    """Wikipedia table (7 columns: date, added ticker/name, removed ticker/name, reason, refs) -> rows."""
    t = t.copy()
    t.columns = ["date", "added", "added_name", "removed", "removed_name", "reason", "refs"]
    t["date"] = pd.to_datetime(t["date"], format="%B %d, %Y", errors="coerce")
    out = []
    for r in t.itertuples():
        if pd.isna(r.date):
            continue
        added, removed = _ticker(r.added), _ticker(r.removed)
        if added or removed:
            out.append((r.date.date().isoformat(), added, removed, None if pd.isna(r.reason) else str(r.reason)))
    return out


def save(conn, rows: list[tuple]) -> None:
    with conn:
        conn.executemany(
            "INSERT INTO index_changes (effective_date, added_ticker, removed_ticker, reason) VALUES (?, ?, ?, ?) "
            "ON CONFLICT (effective_date, added_ticker, removed_ticker) DO UPDATE SET reason = excluded.reason",
            rows,
        )


def usable(close: pd.Series | None, effective: date) -> bool:
    """True if the series has history from a year before `effective` and bars within 30 days of it."""
    if close is None:
        return False
    s = close.dropna()
    if s.empty:
        return False
    return s.index[0].date() <= effective - timedelta(days=365) and s.index[-1].date() >= effective - timedelta(days=30)


def fetch_close(tickers: list[str], start: str) -> pd.DataFrame:
    import yfinance as yf

    df = yf.download(tickers, start=start, progress=False, auto_adjust=True, group_by="column", threads=True)
    close = df["Close"] if len(df) and "Close" in df else pd.DataFrame()
    return close.to_frame(tickers[0]) if isinstance(close, pd.Series) else close


def check_removed(conn, since: str, get_close=fetch_close) -> dict:
    """Mark `price_ok` for every removal on or after `since`. Returns counts."""
    rows = conn.execute(
        "SELECT effective_date, removed_ticker FROM index_changes WHERE removed_ticker <> '' AND effective_date >= ? "
        "ORDER BY effective_date",
        (since,),
    ).fetchall()
    start = (date.fromisoformat(since) - timedelta(days=420)).isoformat()
    tickers = sorted({r[1] for r in rows})
    closes: dict[str, pd.Series] = {}
    for i in range(0, len(tickers), BATCH):
        batch = tickers[i:i + BATCH]
        frame = get_close(batch, start)
        for t in batch:
            closes[t] = frame[t] if t in frame.columns else None
    ok = 0
    with conn:
        for eff, t in rows:
            good = usable(closes.get(t), date.fromisoformat(eff))
            ok += good
            conn.execute("UPDATE index_changes SET price_ok = ? WHERE removed_ticker = ? AND effective_date = ?",
                         (int(good), t, eff))
    return {"removals": len(rows), "tickers": len(tickers), "price_ok": ok}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="test which removed stocks still have usable prices")
    ap.add_argument("--since", default="2016-01-01", help="only check removals from this date (default 2016-01-01)")
    args = ap.parse_args()
    from agents import config

    config.load_env()  # DATABASE_URL (Neon) unless PLANWISE_DB points at a SQLite file
    conn = connect(DB_PATH)
    conn.executescript(SCHEMA)
    r = requests.get(URL, headers=UA, timeout=30)
    r.raise_for_status()
    rows = rows_from_table(pd.read_html(StringIO(r.text))[0])
    save(conn, rows)
    total = conn.execute("SELECT COUNT(*) FROM index_changes").fetchone()[0]
    print(f"index_changes: {len(rows)} rows read, {total} in the table")
    if args.check:
        c = check_removed(conn, args.since)
        print(f"removed since {args.since}: {c['removals']} removals of {c['tickers']} tickers, "
              f"{c['price_ok']} with usable Yahoo prices ({c['price_ok'] / max(c['removals'], 1):.0%})")


if __name__ == "__main__":
    main()
