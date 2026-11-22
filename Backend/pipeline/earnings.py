"""Earnings calendar: when each stock reports next, and how the last reports went.

Source: Yahoo Finance via yfinance (`get_earnings_dates`, free, one call per ticker). Per ticker we keep
the last ~12 report days plus the next announced one, with the analyst EPS estimate, the reported EPS and
the surprise in percent. Nothing here changes a score or a card; it is data for later filters
(for example: skip a stock that reports within 5 days) and for the shadow-portfolio comparison.

Caveats (kept simple on purpose)
- `event_date` is the calendar day in New York time. Yahoo's time of day is a placeholder for many
  stocks, so we do not say whether the report is before the open or after the close.
- A future date can still move; it is refreshed whenever the ticker is older than MAX_AGE_H hours.
- Yahoo returns nothing for a few tickers; those are retried at the next run, one call each.

Run from Backend/ (the hourly wrapper `pipeline.collect_hourly` does this too):
  .venv/bin/python -m pipeline.earnings            # refresh stale tickers (all ~330 take about 3 minutes)
  .venv/bin/python -m pipeline.earnings --report   # curated stocks that report in the next 7 days
"""
import argparse
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from app.dbcompat import connect

DB_PATH = os.environ.get("PLANWISE_DB", os.path.join(os.path.dirname(__file__), "..", "planwise.db"))
NY = "America/New_York"
MAX_AGE_H = 20
DELAY_S = 0.3
MAX_PER_RUN = 400  # measured: 150 tickers took 77 s with 4 threads, so a full refresh is about 3 minutes
WORKERS = 4

SCHEMA = """
CREATE TABLE IF NOT EXISTS earnings_events (
  ticker TEXT NOT NULL,
  event_date TEXT NOT NULL,
  eps_estimate REAL,
  eps_actual REAL,
  surprise_pct REAL,
  fetched_at TEXT NOT NULL,
  PRIMARY KEY (ticker, event_date)
);
CREATE TABLE IF NOT EXISTS earnings_fetch (
  ticker TEXT PRIMARY KEY,
  fetched_at TEXT NOT NULL,
  n_events INTEGER NOT NULL
);
"""


def _num(v) -> float | None:
    return None if v is None or pd.isna(v) else float(v)


def rows_from_frame(df) -> list[dict]:
    """yfinance earnings frame (index = report timestamp) -> one dict per New York calendar day."""
    if df is None or df.empty:
        return []
    out: dict[str, dict] = {}
    for ts, r in df.iterrows():
        t = pd.Timestamp(ts)
        day = (t.tz_convert(NY) if t.tzinfo else t).date().isoformat()
        out.setdefault(day, {
            "event_date": day,
            "eps_estimate": _num(r.get("EPS Estimate")),
            "eps_actual": _num(r.get("Reported EPS")),
            "surprise_pct": _num(r.get("Surprise(%)")),
        })
    return list(out.values())


def fetch_events(ticker: str) -> list[dict]:
    import yfinance as yf

    return rows_from_frame(yf.Ticker(ticker).get_earnings_dates(limit=12))


def stale(conn, tickers: list[str], now: datetime, max_age_h: int = MAX_AGE_H) -> list[str]:
    """Tickers not fetched within the last `max_age_h` hours (including ones never fetched)."""
    cutoff = (now - timedelta(hours=max_age_h)).isoformat()
    fresh = {r[0] for r in conn.execute("SELECT ticker FROM earnings_fetch WHERE fetched_at >= ?", (cutoff,)).fetchall()}
    return [t for t in tickers if t not in fresh]


def save(conn, ticker: str, rows: list[dict], now: datetime) -> None:
    stamp = now.isoformat()
    with conn:
        conn.executemany(
            "INSERT INTO earnings_events (ticker, event_date, eps_estimate, eps_actual, surprise_pct, fetched_at) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (ticker, event_date) DO UPDATE SET "
            "eps_estimate = excluded.eps_estimate, eps_actual = excluded.eps_actual, "
            "surprise_pct = excluded.surprise_pct, fetched_at = excluded.fetched_at",
            [(ticker, r["event_date"], r["eps_estimate"], r["eps_actual"], r["surprise_pct"], stamp) for r in rows],
        )
        conn.execute(
            "INSERT INTO earnings_fetch (ticker, fetched_at, n_events) VALUES (?, ?, ?) "
            "ON CONFLICT (ticker) DO UPDATE SET fetched_at = excluded.fetched_at, n_events = excluded.n_events",
            (ticker, stamp, len(rows)),
        )


def _fetch(get, ticker: str, delay: float):
    """Runs in a worker thread: (ticker, rows, error). One bad ticker must not stop the run."""
    try:
        rows = get(ticker)
    except Exception as e:
        return ticker, None, e
    time.sleep(delay)
    return ticker, rows, None


def run(conn, tickers: list[str], get=fetch_events, now: datetime | None = None,
        delay: float = DELAY_S, limit: int = MAX_PER_RUN, workers: int = WORKERS) -> dict:
    """Fetch up to `limit` stale tickers with `workers` threads (a Yahoo call takes ~7 s), save in this thread."""
    now = now or datetime.now(timezone.utc)
    conn.executescript(SCHEMA)
    due = stale(conn, tickers, now)
    todo = due[:limit]
    stats = {"wanted": len(tickers), "stale": len(due), "fetched": 0, "failed": 0, "events": 0}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for ticker, rows, err in pool.map(lambda t: _fetch(get, t, delay), todo):
            if err is not None:
                print(f"  {ticker}: failed ({err.__class__.__name__})")
                stats["failed"] += 1
                continue
            save(conn, ticker, rows, now)
            stats["fetched"] += 1
            stats["events"] += len(rows)
    return stats


def upcoming(conn, tickers: list[str], today: date, days: int) -> dict[str, str]:
    """{ticker: next event_date} for tickers that report from `today` up to `days` days ahead."""
    end = (today + timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT ticker, MIN(event_date) FROM earnings_events WHERE event_date >= ? AND event_date <= ? GROUP BY ticker",
        (today.isoformat(), end),
    ).fetchall()
    wanted = set(tickers)
    return {r[0]: r[1] for r in rows if r[0] in wanted}


def recommended_tickers(conn, only_top: bool = False) -> list[str]:
    where = " WHERE in_top = 1" if only_top else ""
    return [r[0] for r in conn.execute(f"SELECT DISTINCT ticker FROM recommendations{where} ORDER BY ticker").fetchall()]


def report(conn, days: int = 7) -> None:
    today = datetime.now(timezone.utc).date()
    top = recommended_tickers(conn, only_top=True)
    soon = upcoming(conn, top, today, days)
    print(f"curated stocks: {len(top)}, reporting within {days} days: {len(soon)}")
    for t, d in sorted(soon.items(), key=lambda x: x[1]):
        print(f"  {t:<6} {d}  (in {(date.fromisoformat(d) - today).days} days)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="list curated stocks that report soon")
    args = ap.parse_args()
    from agents import config

    config.load_env()  # DATABASE_URL (Neon) unless PLANWISE_DB points at a SQLite file
    conn = connect(DB_PATH)
    conn.executescript(SCHEMA)
    if args.report:
        report(conn)
        return
    stats = run(conn, recommended_tickers(conn))
    total = conn.execute("SELECT COUNT(*) FROM earnings_events").fetchone()[0]
    print(f"earnings: {stats['wanted']} tickers wanted, {stats['stale']} stale, {stats['fetched']} fetched, "
          f"{stats['failed']} failed, {stats['events']} events written, {total} events in total")


if __name__ == "__main__":
    main()
