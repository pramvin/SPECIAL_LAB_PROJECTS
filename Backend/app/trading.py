"""Simulated long/short positions and closed-trade history."""
import sqlite3
import time
from typing import Callable, Literal

from fastapi import APIRouter, Cookie, HTTPException, Query
from pydantic import BaseModel, Field

from .wallet import change_balance, ensure_wallet, money, wallet_payload
from .watchlist import TICKER_RE, normalize_ticker

MIN_LEVERAGE = 1.0
MAX_LEVERAGE = 10.0
MAX_AMOUNT = 1_000_000.0
DEFAULT_TRADE_LIMIT = 100
MAX_TRADE_LIMIT = 500

SCHEMA = """
CREATE TABLE IF NOT EXISTS positions (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  ticker TEXT NOT NULL,
  side TEXT NOT NULL CHECK (side IN ('long', 'short')),
  entry_price REAL NOT NULL CHECK (entry_price > 0),
  quantity REAL NOT NULL CHECK (quantity > 0),
  leverage REAL NOT NULL CHECK (leverage >= 1 AND leverage <= 10),
  amount_deducted REAL NOT NULL CHECK (amount_deducted > 0),
  notional REAL NOT NULL,
  opened_at INTEGER NOT NULL
);
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


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def latest_close(conn: sqlite3.Connection, ticker: str) -> float | None:
    try:
        row = conn.execute(
            "SELECT close FROM prices WHERE ticker = ? ORDER BY date DESC LIMIT 1",
            (ticker,),
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    return None if row is None else float(row["close"])


def position_payload(row: sqlite3.Row, current_price: float | None = None) -> dict:
    entry = float(row["entry_price"])
    quantity = float(row["quantity"])
    amount = float(row["amount_deducted"])
    side = row["side"]

    unrealized_pnl = None
    unrealized_pct = None
    if current_price is not None:
        move = current_price - entry if side == "long" else entry - current_price
        unrealized_pnl = money(move * quantity)
        unrealized_pct = round(unrealized_pnl / amount * 100, 2) if amount else 0.0

    return {
        "id": row["id"],
        "ticker": row["ticker"],
        "side": side,
        "entry_price": money(entry),
        "current_price": None if current_price is None else money(current_price),
        "quantity": round(quantity, 6),
        "leverage": round(float(row["leverage"]), 2),
        "amount_deducted": money(amount),
        "notional": money(row["notional"]),
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pnl_pct": unrealized_pct,
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
    amount = money(amount)
    leverage = float(leverage)
    if amount <= 0:
        raise TradingError("Amount must be positive")
    if not MIN_LEVERAGE <= leverage <= MAX_LEVERAGE:
        raise TradingError(f"Leverage must be between {MIN_LEVERAGE:g} and {MAX_LEVERAGE:g}")

    entry = latest_close(conn, ticker)
    if entry is None or entry <= 0:
        raise UnknownTicker("No price data for this ticker")

    wallet = ensure_wallet(conn, user_id)
    if amount > wallet["balance"] + 1e-9:
        raise InsufficientFunds("Insufficient wallet balance")

    notional = money(amount * leverage)
    quantity = round(notional / entry, 8)
    now = int(time.time())
    cur = conn.execute(
        "INSERT INTO positions "
        "(user_id, ticker, side, entry_price, quantity, leverage, amount_deducted, notional, opened_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, ticker, side, entry, quantity, leverage, amount, notional, now),
    )
    wallet, _ = change_balance(conn, user_id, -amount)
    position = conn.execute(
        "SELECT id, user_id, ticker, side, entry_price, quantity, leverage, "
        "amount_deducted, notional, opened_at FROM positions WHERE id = ?",
        (cur.lastrowid,),
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

    exit_price = latest_close(conn, position["ticker"])
    if exit_price is None or exit_price <= 0:
        raise UnknownTicker("No price data for this ticker")

    entry = float(position["entry_price"])
    quantity = float(position["quantity"])
    amount = float(position["amount_deducted"])
    move = exit_price - entry if position["side"] == "long" else entry - exit_price
    pnl = money(move * quantity)
    pnl_pct = round(pnl / amount * 100, 2) if amount else 0.0
    now = int(time.time())

    cur = conn.execute(
        "INSERT INTO trades "
        "(position_id, user_id, ticker, side, entry_price, exit_price, quantity, leverage, "
        "amount_deducted, pnl, pnl_pct, opened_at, closed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
    )
    conn.execute("DELETE FROM positions WHERE id = ? AND user_id = ?", (position_id, user_id))
    wallet, _ = change_balance(conn, user_id, amount + pnl)
    trade = conn.execute(
        "SELECT id, position_id, user_id, ticker, side, entry_price, exit_price, quantity, "
        "leverage, amount_deducted, pnl, pnl_pct, opened_at, closed_at "
        "FROM trades WHERE id = ?",
        (cur.lastrowid,),
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


def list_trades(conn: sqlite3.Connection, user_id: int, limit: int) -> list[dict]:
    rows = conn.execute(
        "SELECT id, position_id, user_id, ticker, side, entry_price, exit_price, "
        "quantity, leverage, amount_deducted, pnl, pnl_pct, opened_at, closed_at "
        "FROM trades WHERE user_id = ? ORDER BY closed_at DESC, id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return [trade_payload(row) for row in rows]


class OpenPositionBody(BaseModel):
    ticker: str = Field(min_length=1, max_length=12)
    side: Literal["long", "short"]
    amount: float = Field(gt=0, le=MAX_AMOUNT)
    leverage: float = Field(default=1, ge=MIN_LEVERAGE, le=MAX_LEVERAGE)


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
        return {
            "trade": trade_payload(trade),
            "wallet": wallet_payload(wallet),
        }

    @router.get("/trades")
    def get_trades(
        limit: int = Query(DEFAULT_TRADE_LIMIT, ge=1, le=MAX_TRADE_LIMIT),
        session: str | None = Cookie(default=None),
    ):
        with db() as conn:
            user = current_user(conn, session)
            items = list_trades(conn, user["id"], limit)
        return {"items": items}

    return router
