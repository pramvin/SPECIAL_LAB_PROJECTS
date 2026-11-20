"""SQLite financial request replay; the route's outer transaction owns commit."""
from contextlib import ExitStack, contextmanager
import hashlib
import json
import re
import sqlite3
import time

from fastapi import HTTPException, Response

from .dbcompat import begin_financial_write, is_pg

SCHEMA = """
CREATE TABLE IF NOT EXISTS financial_requests (
  user_id INTEGER NOT NULL REFERENCES users(id),
  key TEXT NOT NULL,
  fingerprint TEXT NOT NULL,
  status_code INTEGER NOT NULL CHECK (status_code = 200),
  response_json TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  PRIMARY KEY (user_id, key)
);
"""
KEY_RE = re.compile(r"[!-~]{1,128}", re.ASCII)


def init_schema(conn) -> None:
    if not is_pg(conn):
        conn.executescript(SCHEMA)


@contextmanager
def connection(db):
    """Close raw connections too: sqlite3's own context manager only completes transactions."""
    with ExitStack() as stack:
        resource = db()
        if hasattr(resource, "close"):
            stack.callback(resource.close)
        yield stack.enter_context(resource)


def fingerprint(operation: str, inputs: dict) -> str:
    canonical = json.dumps({"version": 1, "operation": operation, "inputs": inputs},
                           sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return "v1:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def lookup(conn, user_id: int, key: str, digest: str):
    cur = conn.execute(
        "SELECT fingerprint, status_code, response_json FROM financial_requests "
        "WHERE user_id = ? AND key = ?", (user_id, key))
    try:
        row = cur.fetchone()
    finally:
        cur.close()
    if row is None:
        return None
    if row["fingerprint"] != digest:
        raise HTTPException(409, "Idempotency-Key was already used with different request inputs")
    return Response(content=row["response_json"], status_code=row["status_code"],
                    media_type="application/json")


def record(conn, user_id: int, key: str, digest: str, payload: dict) -> Response:
    encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    conn.execute(
        "INSERT INTO financial_requests "
        "(user_id, key, fingerprint, status_code, response_json, created_at) VALUES (?, ?, ?, 200, ?, ?)",
        (user_id, key, digest, encoded, int(time.time())),
    ).close()
    return Response(content=encoded, status_code=200, media_type="application/json")


def run(db, current_user, session, key, operation, inputs, execute, prepare=None):
    """Cache successful keyed effects only; all exceptions escape for outer rollback."""
    try:
        if key is None:
            with connection(db) as conn:
                user = current_user(conn, session)
                result = execute(conn, user["id"], None)
            return result

        digest = fingerprint(operation, inputs)
        # No financial transaction, wallet creation, or retained read snapshot.
        with connection(db) as conn:
            user_id = current_user(conn, session)["id"]
            if not KEY_RE.fullmatch(key):
                raise HTTPException(422, "Idempotency-Key must be 1-128 visible ASCII characters")
            if is_pg(conn):
                raise HTTPException(501, "Financial idempotency is supported only on SQLite")
            result = lookup(conn, user_id, key, digest)
        if result is not None:
            return result

        prepared = None
        preparation_error = None
        if prepare is not None:
            try:
                prepared = prepare(user_id)
            except Exception as exc:
                preparation_error = exc

        with connection(db) as conn:
            if current_user(conn, session)["id"] != user_id:
                raise HTTPException(401, "Not signed in")
            begin_financial_write(conn)
            result = lookup(conn, user_id, key, digest)
            if result is None:
                # A winner's completed response always precedes preparation errors.
                if preparation_error is not None:
                    raise preparation_error
                payload = execute(conn, user_id, prepared)
                result = record(conn, user_id, key, digest, payload)
        # The connection context committed successfully before exposing success.
        return result
    except sqlite3.OperationalError as exc:
        code = getattr(exc, "sqlite_errorcode", 0)
        if code & 0xFF in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
            raise HTTPException(503, "Financial database is busy. Try again.",
                                headers={"Retry-After": "1"}) from exc
        raise
