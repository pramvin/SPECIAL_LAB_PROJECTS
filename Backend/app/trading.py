"""Simulated long/short positions and closed-trade history."""
import math
import sqlite3
import time
from typing import Callable, Literal, TypedDict

import yfinance as yf
from fastapi import APIRouter, Cookie, HTTPException, Query
from pydantic import BaseModel, Field

from .wallet import change_balance, ensure_wallet, money, wallet_payload
from .watchlist import TICKER_RE, normalize_ticker

LEVERAGE_OPTIONS = (1, 2, 3, 4, 5, 10, 50, 100)        # what the UI offers
ALLOWED_LEVERAGE = (1, *LEVERAGE_OPTIONS)  # what the API accepts (x1 kept for old data/tests)
MIN_LEVERAGE = 1.0
MAX_LEVERAGE = 100.0
# True  -> a position is liquidated when price moves 1/leverage against it, so the
#          most you can lose is the margin you put in (P/L is floored at -margin).
# False -> old behaviour: losses are unlimited and the wallet can go negative.
LIQUIDATE_AT_MARGIN = True
LIVE_PRICE_TTL = 15.0                      # seconds a fetched price is reused
PREVIEW_MOVES_PCT = (-10, -5, -1, 1, 5, 10)
MAX_AMOUNT = 1_000_000.0
DEFAULT_TRADE_LIMIT = 100
MAX_TRADE_LIMIT = 500

PRICES_SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
  ticker TEXT NOT NULL, date TEXT NOT NULL,
  open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL, close REAL NOT NULL,
  volume INTEGER NOT NULL,
  PRIMARY KEY (ticker, date)
);
"""

POSITIONS_DDL = """
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  ticker TEXT NOT NULL,
  side TEXT NOT NULL CHECK (side IN ('long', 'short')),
  entry_price REAL NOT NULL CHECK (entry_price > 0),
  quantity REAL NOT NULL CHECK (quantity > 0),
  leverage REAL NOT NULL CHECK (leverage >= 1 AND leverage <= 100),
  amount_deducted REAL NOT NULL CHECK (amount_deducted > 0),
  notional REAL NOT NULL,
  opened_at INTEGER NOT NULL
"""

POSITIONS_COLUMNS = (
    "id, user_id, ticker, side, entry_price, quantity, leverage, "
    "amount_deducted, notional, opened_at"
)

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS positions ({POSITIONS_DDL});
CREATE INDEX IF NOT EXISTS idx_positions_user_time
  ON positions(user_id, opened_at DESC);
CREATE TABLE IF NOT EXISTS trades (
  id INTEGER PRIMARY KEY,
  position_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL REFERENCES users(id),
  ticker TEXT NOT NULL,
  side TEXT NOT NULL CHECK (side IN ('long', 'short')),
  entry_price REAL NOT NULL,
  exit_price REAL NOT NULL,
  quantity REAL NOT NULL,
  leverage REAL NOT NULL,
  amount_deducted REAL NOT NULL,
  pnl REAL NOT NULL,
  pnl_pct REAL NOT NULL,
  opened_at INTEGER NOT NULL,
  closed_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_trades_user_time
  ON trades(user_id, closed_at DESC);
"""


class TradingError(Exception):
    pass


class UnknownTicker(TradingError):
    pass


class InsufficientFunds(TradingError):
    pass


class PositionNotFound(TradingError):
    pass


class MarketDataUnavailable(TradingError):
    pass


class PriceBar(TypedDict):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


def migrate_leverage_limit(conn: sqlite3.Connection) -> None:
    """Old databases have CHECK (leverage <= 10). SQLite can't alter a CHECK,
    so rebuild `positions` once, keeping every row."""
    if not isinstance(conn, sqlite3.Connection):
        return
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'positions'"
    ).fetchone()
    if row is None or "leverage <= 10)" not in row[0]:
        return
    conn.executescript(
        f"""
        DROP TABLE IF EXISTS positions_new;
        CREATE TABLE positions_new ({POSITIONS_DDL});
        INSERT INTO positions_new ({POSITIONS_COLUMNS})
          SELECT {POSITIONS_COLUMNS} FROM positions;
        DROP TABLE positions;
        ALTER TABLE positions_new RENAME TO positions;
        CREATE INDEX IF NOT EXISTS idx_positions_user_time
          ON positions(user_id, opened_at DESC);
        """
    )


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(PRICES_SCHEMA)
    conn.executescript(SCHEMA)
    migrate_leverage_limit(conn)


def fetch_latest_bar(ticker: str) -> PriceBar:
    try:
        history = yf.Ticker(ticker).history(
            period="1mo", interval="1d", auto_adjust=True
        )
    except Exception as exc:
        raise MarketDataUnavailable("Yahoo Finance request failed") from exc

    if history is None or history.empty:
        raise UnknownTicker("Yahoo Finance returned no price data for this ticker")

    try:
        history = history.dropna(subset=["Close"])
        if history.empty:
            raise ValueError("No daily close")
        latest = history.iloc[-1]
        bar: PriceBar = {
            "date": history.index[-1].strftime("%Y-%m-%d"),
            "open": float(latest["Open"]),
            "high": float(latest["High"]),
            "low": float(latest["Low"]),
            "close": float(latest["Close"]),
            "volume": int(latest["Volume"]),
        }
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError) as exc:
        raise MarketDataUnavailable("Yahoo Finance returned an invalid daily price bar") from exc

    prices = (bar["open"], bar["high"], bar["low"], bar["close"])
    volume = float(bar["volume"])
    if (
        not all(math.isfinite(price) and price > 0 for price in prices)
        or bar["high"] < bar["low"]
        or not math.isfinite(volume)
        or volume < 0
    ):
        raise MarketDataUnavailable("Yahoo Finance returned an invalid daily price bar")

    return bar


def refresh_latest_close(conn: sqlite3.Connection, ticker: str) -> float:
    bar = fetch_latest_bar(ticker)
    conn.execute(
        "INSERT INTO prices (ticker, date, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(ticker, date) DO UPDATE SET "
        "open=excluded.open, high=excluded.high, low=excluded.low, "
        "close=excluded.close, volume=excluded.volume",
        (
            ticker,
            bar["date"],
            bar["open"],
            bar["high"],
            bar["low"],
            bar["close"],
            bar["volume"],
        ),
    )
    return float(bar["close"])


def latest_close(conn: sqlite3.Connection, ticker: str) -> float | None:
    try:
        row = conn.execute(
            "SELECT close FROM prices WHERE ticker = ? ORDER BY date DESC LIMIT 1",
            (ticker,),
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    return None if row is None else float(row["close"])


def liquidation_price(side: str, entry: float, leverage: float) -> float:
    """Price at which the margin is fully lost (ignores fees/maintenance margin)."""
    return entry * (1 - 1 / leverage) if side == "long" else entry * (1 + 1 / leverage)


def pnl_at(side: str, entry: float, price: float, quantity: float, amount: float) -> float:
    """Profit/loss in USD. Floored at -margin when LIQUIDATE_AT_MARGIN is on."""
    move = price - entry if side == "long" else entry - price
    pnl = move * quantity
    if LIQUIDATE_AT_MARGIN:
        pnl = max(pnl, -amount)
    return money(pnl)


_live_cache: dict[str, tuple[float, float]] = {}  # ticker -> (fetched_at, price)


def live_price(conn: sqlite3.Connection, ticker: str) -> tuple[float | None, bool]:
    """Latest price for a ticker -> (price, stale). Refreshes from Yahoo at most
    every LIVE_PRICE_TTL seconds; on failure falls back to the saved close."""
    now = time.time()
    hit = _live_cache.get(ticker)
    if hit is not None and now - hit[0] < LIVE_PRICE_TTL:
        return hit[1], False
    try:
        price = refresh_latest_close(conn, ticker)
    except TradingError:
        return latest_close(conn, ticker), True
    _live_cache[ticker] = (now, price)
    return price, False


def leverage_preview(side: str, amount: float, entry: float) -> list[dict]:
    """How the same margin behaves under every leverage option."""
    rows = []
    for lev in LEVERAGE_OPTIONS:
        notional = money(amount * lev)
        quantity = notional / entry
        scenarios = []
        for move in PREVIEW_MOVES_PCT:
            price = entry * (1 + move / 100)
            pnl = pnl_at(side, entry, price, quantity, amount)
            scenarios.append(
                {
                    "price_move_pct": move,
                    "pnl": pnl,
                    "pnl_pct": round(pnl / amount * 100, 2),
                }
            )
        rows.append(
            {
                "leverage": lev,
                "margin": money(amount),
                "notional": notional,
                "quantity": round(quantity, 6),
                "liquidation_price": money(liquidation_price(side, entry, lev)),
                "liquidation_move_pct": round(100 / lev, 2),
                "scenarios": scenarios,
            }
        )
    return rows


def position_payload(
    row: sqlite3.Row, current_price: float | None = None, stale: bool = False
) -> dict:
    entry = float(row["entry_price"])
    quantity = float(row["quantity"])
    amount = float(row["amount_deducted"])
    leverage = float(row["leverage"])
    side = row["side"]

    unrealized_pnl = None
    unrealized_pct = None
    if current_price is not None:
        unrealized_pnl = pnl_at(side, entry, current_price, quantity, amount)
        unrealized_pct = round(unrealized_pnl / amount * 100, 2) if amount else 0.0

    liq = liquidation_price(side, entry, leverage)
    liquidated = (
        current_price is not None
        and (current_price <= liq if side == "long" else current_price >= liq)
    )
    return {
        "id": row["id"],
        "ticker": row["ticker"],
        "side": side,
        "entry_price": money(entry),
        "current_price": None if current_price is None else money(current_price),
        "quantity": round(quantity, 6),
        "leverage": round(leverage, 2),
        "amount_deducted": money(amount),
        "notional": money(row["notional"]),
        "liquidation_price": money(liq),
        "liquidated": bool(liquidated and LIQUIDATE_AT_MARGIN),
        "equity": None if unrealized_pnl is None else money(amount + unrealized_pnl),
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pnl_pct": unrealized_pct,
        "price_is_stale": stale,
        "opened_at": row["opened_at"],
    }


def trade_payload(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "position_id": row["position_id"],
        "ticker": row["ticker"],
        "side": row["side"],
        "entry_price": money(row["entry_price"]),
        "exit_price": money(row["exit_price"]),
        "quantity": round(float(row["quantity"]), 6),
        "leverage": round(float(row["leverage"]), 2),
        "amount_deducted": money(row["amount_deducted"]),
        "pnl": money(row["pnl"]),
        "pnl_pct": round(float(row["pnl_pct"]), 2),
        "opened_at": row["opened_at"],
        "closed_at": row["closed_at"],
    }


def open_position(
    conn: sqlite3.Connection,
    user_id: int,
    ticker: str,
    side: Literal["long", "short"],
    amount: float,
    leverage: float,
) -> tuple[sqlite3.Row, sqlite3.Row]:
    ticker = normalize_ticker(ticker)
    if not TICKER_RE.fullmatch(ticker):
        raise UnknownTicker("Invalid ticker")
    if side not in ("long", "short"):
        raise TradingError("Side must be long or short")
    raw_amount = float(amount)
    if not math.isfinite(raw_amount) or raw_amount <= 0:
        raise TradingError("Amount must be positive")
    amount = money(raw_amount)
    if abs(amount - raw_amount) > 1e-9:  # never silently round the user's money
        raise TradingError("Amount can have at most 2 decimal places")
    if amount <= 0:
        raise TradingError("Amount must be positive")
    leverage = float(leverage)
    if leverage not in ALLOWED_LEVERAGE:
        raise TradingError(
            "Leverage must be one of " + ", ".join(f"x{lev}" for lev in LEVERAGE_OPTIONS)
        )

    wallet = ensure_wallet(conn, user_id)
    balance_before = money(wallet["balance"])
    if amount > wallet["balance"] + 1e-9:
        raise InsufficientFunds("Insufficient wallet balance")

    entry = refresh_latest_close(conn, ticker)
    notional = money(amount * leverage)
    quantity = round(notional / entry, 8)
    now = int(time.time())
    new_id = conn.execute(
        "INSERT INTO positions "
        "(user_id, ticker, side, entry_price, quantity, leverage, amount_deducted, notional, opened_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id",
        (user_id, ticker, side, entry, quantity, leverage, amount, notional, now),
    ).fetchone()[0]
    wallet, _ = change_balance(conn, user_id, -amount)
    if abs((balance_before - money(wallet["balance"])) - amount) > 0.005:
        raise TradingError("Wallet deduction did not match the requested amount")
    position = conn.execute(
        "SELECT id, user_id, ticker, side, entry_price, quantity, leverage, "
        "amount_deducted, notional, opened_at FROM positions WHERE id = ?",
        (new_id,),
    ).fetchone()
    return position, wallet


def close_position(
    conn: sqlite3.Connection, user_id: int, position_id: int
) -> tuple[sqlite3.Row, sqlite3.Row]:
    position = conn.execute(
        "SELECT id, user_id, ticker, side, entry_price, quantity, leverage, "
        "amount_deducted, notional, opened_at "
        "FROM positions WHERE id = ? AND user_id = ?",
        (position_id, user_id),
    ).fetchone()
    if position is None:
        raise PositionNotFound("Open position not found")

    exit_price = refresh_latest_close(conn, position["ticker"])

    entry = float(position["entry_price"])
    quantity = float(position["quantity"])
    amount = float(position["amount_deducted"])
    pnl = pnl_at(position["side"], entry, exit_price, quantity, amount)
    pnl_pct = round(pnl / amount * 100, 2) if amount else 0.0
    now = int(time.time())

    new_id = conn.execute(
        "INSERT INTO trades "
        "(position_id, user_id, ticker, side, entry_price, exit_price, quantity, leverage, "
        "amount_deducted, pnl, pnl_pct, opened_at, closed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id",
        (
            position["id"],
            user_id,
            position["ticker"],
            position["side"],
            entry,
            exit_price,
            quantity,
            position["leverage"],
            amount,
            pnl,
            pnl_pct,
            position["opened_at"],
            now,
        ),
    ).fetchone()[0]
    conn.execute("DELETE FROM positions WHERE id = ? AND user_id = ?", (position_id, user_id))
    wallet, _ = change_balance(conn, user_id, amount + pnl)
    trade = conn.execute(
        "SELECT id, position_id, user_id, ticker, side, entry_price, exit_price, quantity, "
        "leverage, amount_deducted, pnl, pnl_pct, opened_at, closed_at "
        "FROM trades WHERE id = ?",
        (new_id,),
    ).fetchone()
    return trade, wallet


def list_positions(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT id, user_id, ticker, side, entry_price, quantity, leverage, "
        "amount_deducted, notional, opened_at "
        "FROM positions WHERE user_id = ? ORDER BY opened_at DESC, id DESC",
        (user_id,),
    ).fetchall()
    return [position_payload(row, latest_close(conn, row["ticker"])) for row in rows]


def list_positions_live(conn: sqlite3.Connection, user_id: int) -> dict:
    """Open positions priced with a fresh (cached 15s) quote, plus portfolio totals."""
    rows = conn.execute(
        "SELECT id, user_id, ticker, side, entry_price, quantity, leverage, "
        "amount_deducted, notional, opened_at "
        "FROM positions WHERE user_id = ? ORDER BY opened_at DESC, id DESC",
        (user_id,),
    ).fetchall()
    prices: dict[str, tuple[float | None, bool]] = {}
    for ticker in {row["ticker"] for row in rows}:
        prices[ticker] = live_price(conn, ticker)
    items = [position_payload(row, *prices[row["ticker"]]) for row in rows]
    margin = money(sum(item["amount_deducted"] for item in items))
    unpriced = sum(item["unrealized_pnl"] is None for item in items)
    total_pnl = None if unpriced else money(sum(item["unrealized_pnl"] for item in items))
    return {
        "items": items,
        "totals": {
            "open_margin": margin,
            "unrealized_pnl": total_pnl,
            "unrealized_pnl_pct": (
                round(total_pnl / margin * 100, 2)
                if total_pnl is not None and margin
                else None
            ),
            "unpriced_position_count": unpriced,
        },
        "as_of": int(time.time()),
    }


def trade_history(
    conn: sqlite3.Connection,
    user_id: int,
    limit: int,
    offset: int = 0,
    search: str = "",
    side: Literal["long", "short"] | None = None,
    outcome: Literal["win", "loss", "breakeven"] | None = None,
) -> dict:
    clauses = ["user_id = ?"]
    params: list[object] = [user_id]
    search = search.strip()
    if search:
        clauses.append("instr(lower(ticker), lower(?)) > 0")
        params.append(search)
    if side is not None:
        clauses.append("side = ?")
        params.append(side)
    if outcome == "win":
        clauses.append("pnl > 0")
    elif outcome == "loss":
        clauses.append("pnl < 0")
    elif outcome == "breakeven":
        clauses.append("pnl = 0")
    where = " AND ".join(clauses)

    total = conn.execute(
        f"SELECT COUNT(*) FROM trades WHERE {where}", params
    ).fetchone()[0]
    rows = conn.execute(
        "SELECT id, position_id, user_id, ticker, side, entry_price, exit_price, "
        "quantity, leverage, amount_deducted, pnl, pnl_pct, opened_at, closed_at "
        f"FROM trades WHERE {where} ORDER BY closed_at DESC, id DESC LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()
    return {
        "items": [trade_payload(row) for row in rows],
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(rows) < total,
    }


def list_trades(conn: sqlite3.Connection, user_id: int, limit: int) -> list[dict]:
    return trade_history(conn, user_id, limit)["items"]


def trading_summary(conn: sqlite3.Connection, user_id: int) -> dict:
    row = conn.execute(
        "SELECT COUNT(*) AS trade_count, "
        "SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) AS win_count, "
        "SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) AS loss_count, "
        "SUM(CASE WHEN pnl = 0 THEN 1 ELSE 0 END) AS breakeven_count, "
        "SUM(pnl) AS realized_pnl, AVG(pnl) AS average_pnl, "
        "MAX(pnl) AS best_trade_pnl, MIN(pnl) AS worst_trade_pnl "
        "FROM trades WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    trade_count = int(row["trade_count"])
    wins = int(row["win_count"] or 0)
    positions = list_positions(conn, user_id)
    unpriced_positions = sum(
        position["unrealized_pnl"] is None for position in positions
    )
    unrealized_pnl = (
        None
        if unpriced_positions
        else money(sum(position["unrealized_pnl"] or 0 for position in positions))
    )
    return {
        "closed_trade_count": trade_count,
        "win_count": wins,
        "loss_count": int(row["loss_count"] or 0),
        "breakeven_count": int(row["breakeven_count"] or 0),
        "win_rate_pct": round(wins / trade_count * 100, 2) if trade_count else None,
        "realized_pnl": money(row["realized_pnl"] or 0),
        "average_pnl": (
            money(row["average_pnl"]) if row["average_pnl"] is not None else None
        ),
        "best_trade_pnl": (
            money(row["best_trade_pnl"]) if row["best_trade_pnl"] is not None else None
        ),
        "worst_trade_pnl": (
            money(row["worst_trade_pnl"]) if row["worst_trade_pnl"] is not None else None
        ),
        "open_position_count": len(positions),
        "open_margin": money(sum(position["amount_deducted"] for position in positions)),
        "unrealized_pnl": unrealized_pnl,
        "unpriced_position_count": unpriced_positions,
    }


class OpenPositionBody(BaseModel):
    ticker: str = Field(min_length=1, max_length=12)
    side: Literal["long", "short"]
    amount: float = Field(gt=0, le=MAX_AMOUNT)
    leverage: float = Field(default=1, ge=MIN_LEVERAGE, le=MAX_LEVERAGE)  # must be x1/5/10/50/100


def build_router(db: Callable[[], sqlite3.Connection], current_user: Callable) -> APIRouter:
    with db() as conn:
        init_schema(conn)

    router = APIRouter(prefix="/api")

    @router.get("/positions")
    def get_positions(session: str | None = Cookie(default=None)):
        with db() as conn:
            user = current_user(conn, session)
            items = list_positions(conn, user["id"])
        return {"items": items}

    @router.get("/positions/live")
    def get_positions_live(session: str | None = Cookie(default=None)):
        with db() as conn:
            user = current_user(conn, session)
            return list_positions_live(conn, user["id"])

    @router.get("/positions/preview")
    def get_position_preview(
        ticker: str = Query(min_length=1, max_length=12),
        side: Literal["long", "short"] = "long",
        amount: float = Query(gt=0, le=MAX_AMOUNT),
        session: str | None = Cookie(default=None),
    ):
        with db() as conn:
            user = current_user(conn, session)
            symbol = normalize_ticker(ticker)
            if not TICKER_RE.fullmatch(symbol):
                raise HTTPException(404, "Invalid ticker")
            entry, stale = live_price(conn, symbol)
            if entry is None:
                raise HTTPException(404, "No price data for this ticker")
            amount = money(amount)
            balance = money(ensure_wallet(conn, user["id"])["balance"])
        return {
            "ticker": symbol,
            "side": side,
            "amount": amount,
            "entry_price": money(entry),
            "price_is_stale": stale,
            "wallet_balance": balance,
            "balance_after_open": money(balance - amount),
            "affordable": amount <= balance + 1e-9,
            "liquidate_at_margin": LIQUIDATE_AT_MARGIN,
            "options": leverage_preview(side, amount, entry),
        }

    @router.post("/positions")
    def post_position(
        body: OpenPositionBody, session: str | None = Cookie(default=None)
    ):
        with db() as conn:
            user = current_user(conn, session)
            try:
                position, wallet = open_position(
                    conn,
                    user["id"],
                    body.ticker,
                    body.side,
                    body.amount,
                    body.leverage,
                )
            except UnknownTicker as exc:
                raise HTTPException(404, str(exc))
            except MarketDataUnavailable:
                raise HTTPException(502, "Yahoo Finance market data is unavailable. Try again.")
            except InsufficientFunds as exc:
                raise HTTPException(409, str(exc))
            except TradingError as exc:
                raise HTTPException(422, str(exc))
            current = latest_close(conn, position["ticker"])
        return {
            "position": position_payload(position, current),
            "wallet": wallet_payload(wallet),
        }

    @router.post("/positions/{position_id}/close")
    def post_close(
        position_id: int, session: str | None = Cookie(default=None)
    ):
        with db() as conn:
            user = current_user(conn, session)
            try:
                trade, wallet = close_position(conn, user["id"], position_id)
            except PositionNotFound as exc:
                raise HTTPException(404, str(exc))
            except UnknownTicker as exc:
                raise HTTPException(404, str(exc))
            except MarketDataUnavailable:
                raise HTTPException(502, "Yahoo Finance market data is unavailable. Try again.")
        return {
            "trade": trade_payload(trade),
            "wallet": wallet_payload(wallet),
        }

    @router.get("/trades")
    def get_trades(
        limit: int = Query(DEFAULT_TRADE_LIMIT, ge=1, le=MAX_TRADE_LIMIT),
        offset: int = Query(0, ge=0, le=1_000_000),
        search: str = Query("", max_length=12),
        side: Literal["long", "short"] | None = None,
        outcome: Literal["win", "loss", "breakeven"] | None = None,
        session: str | None = Cookie(default=None),
    ):
        with db() as conn:
            user = current_user(conn, session)
            result = trade_history(
                conn, user["id"], limit, offset, search, side, outcome
            )
        return result

    @router.get("/trading/summary")
    def get_trading_summary(session: str | None = Cookie(default=None)):
        with db() as conn:
            user = current_user(conn, session)
            summary = trading_summary(conn, user["id"])
        return summary

    return router