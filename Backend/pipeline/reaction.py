"""Layer 1 of the routine: record how the price moved after each headline.

For every archived, non-noise headline we store the stock's price (and SPY's) at the time the
article came out and again 1 hour, 1 day and 5 days later. This builds the "news -> what the price
did next" table that nothing else can rebuild later: Yahoo keeps only about 60 days of 5-minute
bars and Google/Yahoo news only about 7 days. Nothing here changes a score or a card.

Definitions (kept simple on purpose)
- price at time T = close of the last 5-minute bar that ended at or before T. If the market was
  closed at T this is the last close, so a headline that comes out overnight shows no move until
  the next open. `market_open` marks whether a bar ended within 10 minutes before publication.
- a slot (1h / 1d / 5d after publication) is filled only once T is at least 30 minutes in the past,
  so a delayed Yahoo feed is never read as "no move".
- 1d and 5d are calendar offsets (24 h and 120 h), not trading days.
- excess return = stock return minus SPY return over the same window (`--report`).

Run from Backend/ after news and sentiment (the hourly wrapper `pipeline.collect_hourly` does all three):
  .venv/bin/python -m pipeline.reaction            # fill whatever can be filled now
  .venv/bin/python -m pipeline.reaction --report   # mean excess return per sentiment label
"""
import argparse
import os
import time
from datetime import datetime, timedelta, timezone

import pandas as pd

from app.dbcompat import connect

DB_PATH = os.environ.get("PLANWISE_DB", os.path.join(os.path.dirname(__file__), "..", "planwise.db"))
HORIZONS = {"1h": timedelta(hours=1), "1d": timedelta(days=1), "5d": timedelta(days=5)}
BAR = timedelta(minutes=5)
SAFETY = timedelta(minutes=30)  # wait this long past a slot before trusting the feed
OPEN_GAP = timedelta(minutes=10)
MAX_AGE = timedelta(days=55)  # Yahoo's 5-minute history is about 60 days
DELAY_S = 0.4

SCHEMA = """
CREATE TABLE IF NOT EXISTS news_reaction (
  news_id INTEGER PRIMARY KEY REFERENCES news_items(id),
  ticker TEXT NOT NULL,
  published_at TEXT NOT NULL,
  market_open INTEGER,
  p0 REAL, spy0 REAL,
  p_1h REAL, spy_1h REAL,
  p_1d REAL, spy_1d REAL,
  p_5d REAL, spy_5d REAL,
  updated_at TEXT NOT NULL
);
"""
COLUMNS = ["market_open", "p0", "spy0", "p_1h", "spy_1h", "p_1d", "spy_1d", "p_5d", "spy_5d"]


def parse_ts(text: str) -> datetime:
    t = datetime.fromisoformat(text)
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def price_at(bars: pd.Series, ts: datetime) -> float | None:
    """Close of the last bar that ended at or before ts. `bars` is indexed by bar END time (UTC)."""
    if bars is None or bars.empty:
        return None
    i = bars.index.searchsorted(pd.Timestamp(ts), side="right") - 1
    return float(bars.iloc[i]) if i >= 0 else None


def bar_gap(bars: pd.Series, ts: datetime) -> timedelta | None:
    """How long before ts the last bar ended (None if there is no earlier bar)."""
    if bars is None or bars.empty:
        return None
    i = bars.index.searchsorted(pd.Timestamp(ts), side="right") - 1
    return ts - bars.index[i].to_pydatetime() if i >= 0 else None


def fetch_bars(ticker: str) -> pd.Series | None:
    """5-minute closes for the last ~60 days, indexed by bar end time in UTC."""
    import yfinance as yf

    df = yf.Ticker(ticker).history(period="60d", interval="5m", auto_adjust=False)
    if df is None or df.empty:
        return None
    s = df["Close"].dropna()
    s.index = s.index.tz_convert("UTC") + BAR
    return s


def fill_row(existing: dict, published: datetime, bars: pd.Series, spy: pd.Series, now: datetime) -> dict:
    """Return `existing` with every slot that is due and still empty filled in."""
    row = dict(existing)
    if row.get("p0") is None:
        row["p0"], row["spy0"] = price_at(bars, published), price_at(spy, published)
        gap = bar_gap(bars, published)
        row["market_open"] = None if gap is None else int(gap <= OPEN_GAP)
    for name, delta in HORIZONS.items():
        due = published + delta
        if row.get(f"p_{name}") is None and due <= now - SAFETY:
            row[f"p_{name}"], row[f"spy_{name}"] = price_at(bars, due), price_at(spy, due)
    return row


def needs_bars(existing: dict, published: datetime, now: datetime) -> bool:
    """True if at least one slot of this headline is empty and already due (so fetching bars can help)."""
    if existing.get("p0") is None:
        return True
    return any(existing.get(f"p_{n}") is None and published + d <= now - SAFETY for n, d in HORIZONS.items())


def pending(conn, now: datetime) -> dict[str, list[tuple]]:
    """Non-noise headlines whose 5-day slot is still empty, grouped by ticker."""
    oldest = (now - MAX_AGE).isoformat()
    rows = conn.execute(
        "SELECT n.id, n.ticker, n.published_at, "
        + ", ".join(f"r.{c}" for c in COLUMNS)
        + " FROM news_items n LEFT JOIN news_reaction r ON r.news_id = n.id "
        "WHERE n.rule_noise = 0 AND n.published_at >= ? AND (r.news_id IS NULL OR r.p_5d IS NULL) "
        "ORDER BY n.ticker, n.published_at",
        (oldest,),
    ).fetchall()
    out: dict[str, list[tuple]] = {}
    for r in rows:
        out.setdefault(r[1], []).append(tuple(r))
    return out


def save_many(conn, rows: list[tuple[int, str, str, dict]], now: datetime) -> None:
    """Write many rows in one transaction (one round trip per row is far too slow on Neon)."""
    sets = ", ".join(f"{c} = excluded.{c}" for c in COLUMNS)
    sql = (f"INSERT INTO news_reaction (news_id, ticker, published_at, {', '.join(COLUMNS)}, updated_at) "
           f"VALUES (?, ?, ?, {', '.join('?' for _ in COLUMNS)}, ?) "
           f"ON CONFLICT (news_id) DO UPDATE SET {sets}, updated_at = excluded.updated_at")
    with conn:
        for news_id, ticker, published_at, row in rows:
            conn.execute(sql, (news_id, ticker, published_at, *[row.get(c) for c in COLUMNS], now.isoformat()))


def run(conn, get_bars=fetch_bars, now: datetime | None = None, delay: float = DELAY_S) -> dict:
    now = now or datetime.now(timezone.utc)
    conn.executescript(SCHEMA)
    todo = pending(conn, now)
    stats = {"tickers": len(todo), "rows": 0, "failed": 0}  # tickers = with a not-yet-complete headline
    if not todo:
        return stats
    spy = get_bars("SPY")
    if spy is None:
        raise SystemExit("could not fetch SPY bars; nothing written")
    for ticker, items in todo.items():
        items = [it for it in items
                 if needs_bars(dict(zip(COLUMNS, it[3:])), parse_ts(it[2]), now)]
        if not items:
            continue  # nothing due yet: skip the Yahoo call
        try:
            bars = get_bars(ticker)
        except Exception as e:  # one bad ticker must not stop the run
            print(f"  {ticker}: failed ({e.__class__.__name__})")
            stats["failed"] += 1
            continue
        if bars is None:
            stats["failed"] += 1
            continue
        changed = []
        for news_id, _, published_at, *old in items:
            existing = dict(zip(COLUMNS, old))
            row = fill_row(existing, parse_ts(published_at), bars, spy, now)
            if row != existing:
                changed.append((news_id, ticker, published_at, row))
        if changed:
            save_many(conn, changed, now)
            stats["rows"] += len(changed)
        time.sleep(delay)
    return stats


def report(conn) -> None:
    """Mean excess return (stock minus SPY) per sentiment label. n is small at first: read it as a count, not a result."""
    rows = conn.execute(
        "SELECT s.sentiment, r.p0, r.spy0, r.p_1h, r.spy_1h, r.p_1d, r.spy_1d, r.p_5d, r.spy_5d "
        "FROM news_reaction r JOIN news_scores s ON s.news_id = r.news_id "
        "WHERE r.p0 IS NOT NULL AND r.spy0 IS NOT NULL"
    ).fetchall()
    print("label      window     n   mean excess return")
    for label in ("bullish", "neutral", "bearish"):
        for h in HORIZONS:
            vals = []
            for r in rows:
                p0, s0 = r[1], r[2]
                ph, sh = r[{"1h": 3, "1d": 5, "5d": 7}[h]], r[{"1h": 4, "1d": 6, "5d": 8}[h]]
                if r[0] == label and None not in (ph, sh) and p0 and s0:
                    vals.append((ph / p0 - 1) - (sh / s0 - 1))
            if vals:
                print(f"{label:<9}  {h:<5}  {len(vals):>5}   {sum(vals) / len(vals) * 100:+.3f}%")
            else:
                print(f"{label:<9}  {h:<5}  {0:>5}   -")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="print mean excess return per sentiment label")
    args = ap.parse_args()
    conn = connect(DB_PATH)
    conn.executescript(SCHEMA)
    if args.report:
        report(conn)
        return
    stats = run(conn)
    total = conn.execute("SELECT COUNT(*) FROM news_reaction").fetchone()[0]
    print(f"reaction: {stats['tickers']} tickers with open slots, {stats['rows']} rows updated, "
          f"{stats['failed']} failed, {total} rows in total")


if __name__ == "__main__":
    main()
