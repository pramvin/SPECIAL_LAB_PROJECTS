"""Simulated wallet: balance, deposit/withdraw log, and balance history."""
import sqlite3
import time
from typing import Callable

from fastapi import APIRouter, Cookie, HTTPException, Query
from pydantic import BaseModel, Field

STARTING_BALANCE = 1000.0
DEFAULT_TRANSACTION_LIMIT = 50
MAX_TRANSACTION_LIMIT = 200
MAX_HISTORY_LIMIT = 500
MAX_AMOUNT = 1_000_000.0

SCHEMA = """
CREATE TABLE IF NOT EXISTS wallets (
  user_id INTEGER PRIMARY KEY REFERENCES users(id),
  balance REAL NOT NULL DEFAULT 1000,
  starting_balance REAL NOT NULL DEFAULT 1000,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS wallet_transactions (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  kind TEXT NOT NULL CHECK (kind IN ('deposit', 'withdraw')),
  amount REAL NOT NULL CHECK (amount > 0),
  balance_after REAL NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_wallet_transactions_user_time
  ON wallet_transactions(user_id, created_at DESC);
CREATE TABLE IF NOT EXISTS balance_history (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  balance REAL NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_balance_history_user_time
  ON balance_history(user_id, created_at DESC);
"""


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def money(value: float) -> float:
    return round(float(value), 2)


def ensure_wallet(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row:
    row = conn.execute(
        "SELECT user_id, balance, starting_balance, created_at, updated_at "
        "FROM wallets WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if row is not None:
        return row

    now = int(time.time())
    conn.execute(
        "INSERT INTO wallets (user_id, balance, starting_balance, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, STARTING_BALANCE, STARTING_BALANCE, now, now),
    )
    conn.execute(
        "INSERT INTO balance_history (user_id, balance, created_at) VALUES (?, ?, ?)",
        (user_id, STARTING_BALANCE, now),
    )
    return conn.execute(
        "SELECT user_id, balance, starting_balance, created_at, updated_at "
        "FROM wallets WHERE user_id = ?",
        (user_id,),
    ).fetchone()


def change_balance(
    conn: sqlite3.Connection,
    user_id: int,
    delta: float,
    kind: str | None = None,
    note: str = "",
) -> tuple[sqlite3.Row, sqlite3.Row | None]:
    """Apply a balance delta, write history, and optionally log the transaction."""
    wallet = ensure_wallet(conn, user_id)
    balance_after = money(wallet["balance"] + delta)
    now = int(time.time())
    conn.execute(
        "UPDATE wallets SET balance = ?, updated_at = ? WHERE user_id = ?",
        (balance_after, now, user_id),
    )
    conn.execute(
        "INSERT INTO balance_history (user_id, balance, created_at) VALUES (?, ?, ?)",
        (user_id, balance_after, now),
    )

    transaction = None
    if kind is not None:
        cur = conn.execute(
            "INSERT INTO wallet_transactions "
            "(user_id, kind, amount, balance_after, note, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, kind, money(abs(delta)), balance_after, note, now),
        )
        transaction = conn.execute(
            "SELECT id, kind, amount, balance_after, note, created_at "
            "FROM wallet_transactions WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()

    wallet = conn.execute(
        "SELECT user_id, balance, starting_balance, created_at, updated_at "
        "FROM wallets WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    return wallet, transaction


class InsufficientFunds(Exception):
    pass


def deposit(
    conn: sqlite3.Connection, user_id: int, amount: float, note: str = ""
) -> tuple[sqlite3.Row, sqlite3.Row | None]:
    if amount <= 0:
        raise ValueError("Amount must be positive")
    return change_balance(conn, user_id, amount, kind="deposit", note=note)


def withdraw(
    conn: sqlite3.Connection, user_id: int, amount: float, note: str = ""
) -> tuple[sqlite3.Row, sqlite3.Row | None]:
    if amount <= 0:
        raise ValueError("Amount must be positive")
    wallet = ensure_wallet(conn, user_id)
    if amount > wallet["balance"] + 1e-9:
        raise InsufficientFunds("Insufficient wallet balance")
    return change_balance(conn, user_id, -amount, kind="withdraw", note=note)


def wallet_payload(row: sqlite3.Row) -> dict:
    balance = money(row["balance"])
    starting = money(row["starting_balance"])
    change = money(balance - starting)
    change_pct = round(change / starting * 100, 2) if starting else 0.0
    return {
        "balance": balance,
        "starting_balance": starting,
        "change": change,
        "change_pct": change_pct,
        "currency": "USD",
        "updated_at": row["updated_at"],
    }


def transaction_payload(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "kind": row["kind"],
        "amount": money(row["amount"]),
        "balance_after": money(row["balance_after"]),
        "note": row["note"],
        "created_at": row["created_at"],
    }


def history_payload(conn: sqlite3.Connection, user_id: int, limit: int) -> dict:
    wallet = ensure_wallet(conn, user_id)
    starting = money(wallet["starting_balance"])
    rows = conn.execute(
        "SELECT balance, created_at FROM balance_history "
        "WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    items = []
    for row in reversed(rows):
        balance = money(row["balance"])
        change_pct = round((balance - starting) / starting * 100, 2) if starting else 0.0
        items.append(
            {
                "balance": balance,
                "change_pct": change_pct,
                "created_at": row["created_at"],
            }
        )
    return {"starting_balance": starting, "items": items}


class AmountBody(BaseModel):
    amount: float = Field(gt=0, le=MAX_AMOUNT)
    note: str = Field(default="", max_length=200)


def build_router(db: Callable[[], sqlite3.Connection], current_user: Callable) -> APIRouter:
    with db() as conn:
        init_schema(conn)

    router = APIRouter(prefix="/api")

    @router.get("/wallet")
    def get_wallet(session: str | None = Cookie(default=None)):
        with db() as conn:
            user = current_user(conn, session)
            return wallet_payload(ensure_wallet(conn, user["id"]))

    @router.post("/wallet/deposit")
    def deposit_funds(body: AmountBody, session: str | None = Cookie(default=None)):
        with db() as conn:
            user = current_user(conn, session)
            wallet, transaction = deposit(
                conn, user["id"], body.amount, note=body.note.strip()
            )
        return {
            "wallet": wallet_payload(wallet),
            "transaction": transaction_payload(transaction),
        }

    @router.post("/wallet/withdraw")
    def withdraw_funds(body: AmountBody, session: str | None = Cookie(default=None)):
        with db() as conn:
            user = current_user(conn, session)
            try:
                wallet, transaction = withdraw(
                    conn, user["id"], body.amount, note=body.note.strip()
                )
            except InsufficientFunds as exc:
                raise HTTPException(409, str(exc))
        return {
            "wallet": wallet_payload(wallet),
            "transaction": transaction_payload(transaction),
        }

    @router.get("/wallet/transactions")
    def get_transactions(
        limit: int = Query(DEFAULT_TRANSACTION_LIMIT, ge=1, le=MAX_TRANSACTION_LIMIT),
        session: str | None = Cookie(default=None),
    ):
        with db() as conn:
            user = current_user(conn, session)
            ensure_wallet(conn, user["id"])
            rows = conn.execute(
                "SELECT id, kind, amount, balance_after, note, created_at "
                "FROM wallet_transactions WHERE user_id = ? "
                "ORDER BY created_at DESC, id DESC LIMIT ?",
                (user["id"], limit),
            ).fetchall()
        return {"items": [transaction_payload(r) for r in rows]}

    @router.get("/wallet/history")
    def get_history(
        limit: int = Query(MAX_HISTORY_LIMIT, ge=2, le=MAX_HISTORY_LIMIT),
        session: str | None = Cookie(default=None),
    ):
        with db() as conn:
            user = current_user(conn, session)
            return history_payload(conn, user["id"], limit)

    return router
