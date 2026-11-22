"""Intraday volume snapshots for the curated stocks: is today's trading unusually heavy?

For each stock in the curated list (`in_top = 1`) we read the last ~30 days of 5-minute bars from
Yahoo Finance and compute, as of the latest bar:
- rvol           = volume traded so far today / average volume traded by the same clock time on each of
                   the previous (up to 20) sessions. 2.0 means twice as busy as usual at this hour.
- gap_pct        = today's open vs the previous session's last close
- ret_since_open = latest close vs today's open
Nothing here changes a score or a card; it is data for later filters and for the shadow-portfolio test.

Rules (kept simple on purpose)
- Sessions that ended before the reference time (half days) or that start after 09:35 New York time
  (a cut-off window edge) are not used as references. Fewer than MIN_PRIOR references -> rvol is empty.
- A snapshot is stored only if its last bar ended within MAX_STALE of the run, so a run at night or on a
  weekend writes nothing (it stops after the first stock). The last bar of a live session may be incomplete.
- Regular hours only (no pre/after-market volume); Yahoo's feed is delayed about 15 minutes.

Run from Backend/ (the hourly wrapper `pipeline.collect_hourly` does this too):
  .venv/bin/python -m pipeline.intraday            # take a snapshot now (only writes while the market is open)
  .venv/bin/python -m pipeline.intraday --report   # latest snapshot per curated stock, busiest first
"""
import argparse
import os
import time
from datetime import datetime, time as dtime, timedelta, timezone

import pandas as pd

from app.dbcompat import connect

DB_PATH = os.environ.get("PLANWISE_DB", os.path.join(os.path.dirname(__file__), "..", "planwise.db"))
BAR = timedelta(minutes=5)
MAX_STALE = timedelta(minutes=30)
PRIOR_N = 20
MIN_PRIOR = 10
SESSION_START = dtime(9, 35)
DELAY_S = 0.3

SCHEMA = """
CREATE TABLE IF NOT EXISTS intraday_snapshot (
  ticker TEXT NOT NULL,
  asof TEXT NOT NULL,
  session_date TEXT NOT NULL,
  rvol REAL,
  gap_pct REAL,
  ret_since_open REAL,
  prior_sessions INTEGER NOT NULL,
  PRIMARY KEY (ticker, asof)
);
"""


def fetch_bars(ticker: str) -> pd.DataFrame | None:
    """5-minute bars for the last ~30 days; index = bar START time in New York time."""
    import yfinance as yf

    df = yf.Ticker(ticker).history(period="30d", interval="5m", auto_adjust=False)
    return None if df is None or df.empty else df[["Open", "Close", "Volume"]]


def snapshot(df: pd.DataFrame | None) -> dict | None:
    """Latest-session numbers from 5-minute bars, or None if there is nothing usable."""
    if df is None or df.empty:
        return None
    df = df.dropna(subset=["Open", "Close", "Volume"])
    if df.empty:
        return None
    days = pd.Series(df.index.date, index=df.index)
    last_day = days.iloc[-1]
    today = df[days == last_day]
    ref = today.index[-1].time()
    prior_days = sorted(set(days[days != last_day]))

    cums = []
    for d in prior_days:
        g = df[days == d]
        if g.index[-1].time() < ref or g.index[0].time() > SESSION_START:
            continue  # shorter session, or its start is cut off by the data window
        cums.append(float(sum(v for t, v in zip(g.index.time, g["Volume"]) if t <= ref)))
    cums = cums[-PRIOR_N:]

    rvol = None
    if len(cums) >= MIN_PRIOR and sum(cums) > 0:
        rvol = float(today["Volume"].sum()) / (sum(cums) / len(cums))
    open_ = float(today["Open"].iloc[0])
    gap = None
    if prior_days:
        prev_close = float(df[days == prior_days[-1]]["Close"].iloc[-1])
        gap = open_ / prev_close - 1 if prev_close else None
    return {
        "asof": (today.index[-1].tz_convert("UTC") + BAR).to_pydatetime(),
        "session_date": str(last_day),
        "rvol": rvol,
        "gap_pct": gap,
        "ret_since_open": float(today["Close"].iloc[-1]) / open_ - 1 if open_ else None,
        "prior_sessions": len(cums),
    }


def save(conn, ticker: str, s: dict) -> None:
    with conn:
        conn.execute(
            "INSERT INTO intraday_snapshot (ticker, asof, session_date, rvol, gap_pct, ret_since_open, prior_sessions) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT (ticker, asof) DO NOTHING",
            (ticker, s["asof"].isoformat(), s["session_date"], s["rvol"], s["gap_pct"], s["ret_since_open"],
             s["prior_sessions"]),
        )


def run(conn, tickers: list[str], get_bars=fetch_bars, now: datetime | None = None, delay: float = DELAY_S) -> dict:
    now = now or datetime.now(timezone.utc)
    conn.executescript(SCHEMA)
    stats = {"tickers": len(tickers), "saved": 0, "closed": 0, "failed": 0}
    for i, ticker in enumerate(tickers):
        try:
            snap = snapshot(get_bars(ticker))
        except Exception as e:  # one bad ticker must not stop the run
            print(f"  {ticker}: failed ({e.__class__.__name__})")
            stats["failed"] += 1
            continue
        if snap is None:
            stats["failed"] += 1
            continue
        if now - snap["asof"] > MAX_STALE:
            if stats["saved"] == 0:  # the market is closed for every stock: stop after the first probe
                stats["closed"] = len(tickers) - i
                break
            stats["closed"] += 1
            continue
        save(conn, ticker, snap)
        stats["saved"] += 1
        time.sleep(delay)
    return stats


def curated_tickers(conn) -> list[str]:
    return [r[0] for r in conn.execute(
        "SELECT DISTINCT ticker FROM recommendations WHERE in_top = 1 ORDER BY ticker").fetchall()]


def report(conn, limit: int = 15) -> None:
    rows = conn.execute(
        "SELECT s.ticker, s.asof, s.rvol, s.gap_pct, s.ret_since_open FROM intraday_snapshot s "
        "JOIN (SELECT ticker, MAX(asof) AS m FROM intraday_snapshot GROUP BY ticker) x "
        "ON x.ticker = s.ticker AND x.m = s.asof "
        "WHERE s.ticker IN (SELECT ticker FROM recommendations WHERE in_top = 1) AND s.rvol IS NOT NULL "
        "ORDER BY s.rvol DESC"
    ).fetchall()
    print(f"{len(rows)} curated stocks have a snapshot; busiest first")
    print("ticker  as of (UTC)          rvol   gap     since open")
    for t, asof, rvol, gap, ret in rows[:limit]:
        g = "-" if gap is None else f"{gap * 100:+.1f}%"
        r = "-" if ret is None else f"{ret * 100:+.1f}%"
        print(f"{t:<6}  {asof[:16]:<19} {rvol:5.2f}  {g:>6}  {r:>7}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="show the latest snapshot per curated stock")
    args = ap.parse_args()
    from agents import config

    config.load_env()  # DATABASE_URL (Neon) unless PLANWISE_DB points at a SQLite file
    conn = connect(DB_PATH)
    conn.executescript(SCHEMA)
    if args.report:
        report(conn)
        return
    stats = run(conn, curated_tickers(conn))
    total = conn.execute("SELECT COUNT(*) FROM intraday_snapshot").fetchone()[0]
    note = " (market closed: nothing written)" if stats["closed"] and not stats["saved"] else ""
    print(f"intraday: {stats['tickers']} curated tickers, {stats['saved']} snapshots saved, "
          f"{stats['closed']} closed, {stats['failed']} failed, {total} snapshots in total{note}")


if __name__ == "__main__":
    main()
