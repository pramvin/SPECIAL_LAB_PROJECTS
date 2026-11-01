"""stock search and watchlist s&p500, schd and QQQ"""
import re
import sqlite3
import time
from typing import Callable, Literal

from fastapi import APIRouter, Cookie, HTTPException, Query
from pydantic import BaseModel, Field

# ETFs are kept out of `universe` on purpose: rank.py / news.py read that table
# and trade ideas are S&P 500 only.
ETFS: dict[str, str] = {
    "SCHD": "Schwab U.S. Dividend Equity ETF",
    "QQQ": "Invesco QQQ Trust",
}
MAX_WATCHLIST = 100
MAX_RESULTS = 25
TICKER_RE = re.compile(r"[A-Z0-9][A-Z0-9\-]{0,9}")
EMPTY_QUOTE = {"price": None, "change": None, "change_pct": None, "price_date": None}

SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist (
  user_id INTEGER NOT NULL REFERENCES users(id),
  ticker TEXT NOT NULL,
  name TEXT NOT NULL,
  added_at INTEGER NOT NULL,
  PRIMARY KEY (user_id, ticker)
);
"""


def normalize_ticker(raw: str) -> str:
    return raw.strip().upper().replace(".", "-")  # brk.b -> BRK-B


def has_table(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)).fetchone() is not None


def like_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def match_rank(ticker: str, name: str, t: str, n: str) -> int:
    if ticker == t:
        return 0
    if ticker.startswith(t):
        return 1
    if name.upper().startswith(n):
        return 2
    if t in ticker:
        return 3
    return 4


def find_instruments(conn: sqlite3.Connection, q: str, group: str, limit: int) -> list[dict]:
    n = q.strip().upper()
    t = normalize_ticker(q)
    found: list[tuple[int, int, str, dict]] = []

    if group in ("all", "etf"):
        for ticker, name in ETFS.items():
            if t in ticker or n in name.upper():
                item = {"ticker": ticker, "name": name, "kind": "etf", "sector": None, "gics_sector": None}
                found.append((match_rank(ticker, name, t, n), 0, ticker, item))

    if group in ("all", "sp500") and has_table(conn, "universe"):
        t_any, n_any = f"%{like_escape(t)}%", f"%{like_escape(n)}%"
        rows = conn.execute(
            "SELECT ticker, name, gics_sector, sector FROM universe "
            "WHERE ticker LIKE ? ESCAPE '\\' OR UPPER(name) LIKE ? ESCAPE '\\'",
            (t_any, n_any),
        ).fetchall()
        for r in rows:
            item = {"ticker": r["ticker"], "name": r["name"], "kind": "stock",
                    "sector": r["sector"], "gics_sector": r["gics_sector"]}
            found.append((match_rank(r["ticker"], r["name"], t, n), 1, r["ticker"], item))

    found.sort(key=lambda x: x[:3])
    return [x[3] for x in found[:limit]]


def describe(conn: sqlite3.Connection, tickers: list[str]) -> dict[str, dict]:
    info: dict[str, dict] = {}
    if tickers and has_table(conn, "universe"):
        marks = ",".join("?" * len(tickers))
        for r in conn.execute(
            f"SELECT ticker, name, gics_sector, sector FROM universe WHERE ticker IN ({marks})", tickers
        ):
            info[r["ticker"]] = {"ticker": r["ticker"], "name": r["name"], "kind": "stock",
                                 "sector": r["sector"], "gics_sector": r["gics_sector"]}
    for t in tickers:
        if t in ETFS:
            info[t] = {"ticker": t, "name": ETFS[t], "kind": "etf", "sector": None, "gics_sector": None}
    return info


def last_quotes(conn: sqlite3.Connection, tickers: list[str]) -> dict[str, dict]:
    if not tickers or not has_table(conn, "prices"):
        return {}
    out: dict[str, dict] = {}
    for t in tickers:
        bars = conn.execute(
            "SELECT date, close FROM prices WHERE ticker = ? ORDER BY date DESC LIMIT 2", (t,)
        ).fetchall()
        if not bars:
            continue
        price = bars[0]["close"]
        change = price - bars[1]["close"] if len(bars) == 2 else None
        out[t] = {
            "price": round(price, 2),
            "change": None if change is None else round(change, 2),
            "change_pct": None if change is None else round(change / bars[1]["close"] * 100, 2),
            "price_date": bars[0]["date"],
        }
    return out


def with_quotes_and_flags(conn: sqlite3.Connection, items: list[dict], user_id: int) -> list[dict]:
    tickers = [i["ticker"] for i in items]
    quotes = last_quotes(conn, tickers)
    saved: set[str] = set()
    if tickers:
        marks = ",".join("?" * len(tickers))
        saved = {
            r["ticker"] for r in conn.execute(
                f"SELECT ticker FROM watchlist WHERE user_id = ? AND ticker IN ({marks})", [user_id, *tickers]
            )
        }
    return [{**i, **quotes.get(i["ticker"], EMPTY_QUOTE), "in_watchlist": i["ticker"] in saved} for i in items]


class WatchlistAdd(BaseModel):
    ticker: str = Field(min_length=1, max_length=12)


def build_router(db: Callable[[], sqlite3.Connection], current_user: Callable) -> APIRouter:
    with db() as conn:
        conn.executescript(SCHEMA)

    router = APIRouter(prefix="/api")

    @router.get("/search")
    def search(
        q: str = Query("", max_length=60),
        group: Literal["all", "sp500", "etf"] = "all",
        limit: int = Query(20, ge=1, le=MAX_RESULTS),
        session: str | None = Cookie(default=None),
    ):
        with db() as conn:
            user = current_user(conn, session)
            items = with_quotes_and_flags(conn, find_instruments(conn, q, group, limit), user["id"])
        return {"query": q, "group": group, "items": items}

    @router.get("/watchlist")
    def get_watchlist(session: str | None = Cookie(default=None)):
        with db() as conn:
            user = current_user(conn, session)
            rows = conn.execute(
                "SELECT ticker, name, added_at FROM watchlist WHERE user_id = ? ORDER BY added_at DESC, ticker",
                (user["id"],),
            ).fetchall()
            tickers = [r["ticker"] for r in rows]
            known = describe(conn, tickers)
            quotes = last_quotes(conn, tickers)
        items = []
        for r in rows:
            t = r["ticker"]
            # Fall back to the saved name if the ticker later left the S&P 500.
            base = known.get(t) or {"ticker": t, "name": r["name"], "kind": "stock", "sector": None, "gics_sector": None}
            items.append({**base, **quotes.get(t, EMPTY_QUOTE), "in_watchlist": True, "added_at": r["added_at"]})
        return {"items": items}

    @router.post("/watchlist")
    def add_to_watchlist(body: WatchlistAdd, session: str | None = Cookie(default=None)):
        ticker = normalize_ticker(body.ticker)
        if not TICKER_RE.fullmatch(ticker):
            raise HTTPException(422, "Invalid ticker")
        with db() as conn:
            user = current_user(conn, session)
            info = describe(conn, [ticker])
            if ticker not in info:
                raise HTTPException(404, "Ticker not found in the S&P 500, SCHD or QQQ")
            exists = conn.execute(
                "SELECT added_at FROM watchlist WHERE user_id = ? AND ticker = ?", (user["id"], ticker)
            ).fetchone()
            if exists is None:
                count = conn.execute("SELECT COUNT(*) FROM watchlist WHERE user_id = ?", (user["id"],)).fetchone()[0]
                if count >= MAX_WATCHLIST:
                    raise HTTPException(409, f"Watchlist is full ({MAX_WATCHLIST} tickers)")
                added_at = int(time.time())
                conn.execute(
                    "INSERT INTO watchlist (user_id, ticker, name, added_at) VALUES (?, ?, ?, ?)",
                    (user["id"], ticker, info[ticker]["name"], added_at),
                )
            else:
                added_at = exists["added_at"]
            quote = last_quotes(conn, [ticker]).get(ticker, EMPTY_QUOTE)
        return {**info[ticker], **quote, "in_watchlist": True, "added_at": added_at}

    @router.delete("/watchlist/{ticker}")
    def remove_from_watchlist(ticker: str, session: str | None = Cookie(default=None)):
        t = normalize_ticker(ticker)
        with db() as conn:
            user = current_user(conn, session)
            conn.execute("DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user["id"], t))
        return {"ok": True}

    return router