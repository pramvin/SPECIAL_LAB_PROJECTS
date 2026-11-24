"""Click analysis API: start or reuse a three-analyst run, and read the stored result.

`POST /api/analysis/{ticker}` never waits for the model: the run goes to a background thread and
the client polls `GET` until `status` is no longer `running`. The module-level
`agents.analyze.LLM_SLOTS` semaphore (3) caps model calls across every user.
"""
import json
import os
import re
import threading
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Cookie, HTTPException

from agents import analyze
from .dbcompat import table_names

router = APIRouter(prefix="/api")

TICKER_RE = re.compile(r"[A-Z][A-Z.\-]{0,9}")
REUSE_MINUTES = 30
STALE_RUNNING_MINUTES = 15  # a `running` row older than this belongs to a dead process
FETCHERS: dict | None = None  # tests inject source fetchers here; None means the real sources

_start_lock = threading.Lock()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(stamp: str | None) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(stamp or "")
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _body(row, cached: bool) -> dict:
    try:
        result = json.loads(row["result_json"]) if row["result_json"] else None
    except ValueError:
        result = None
    return {"ticker": row["ticker"], "horizon": row["horizon"], "status": row["status"], "cached": cached,
            "started_at": row["started_at"], "finished_at": row["finished_at"], "error": row["error"],
            "result": result}


def _latest(conn, ticker: str, horizon: str):
    if "stock_analysis" not in table_names(conn):
        return None
    return conn.execute(
        "SELECT * FROM stock_analysis WHERE ticker = ? AND horizon = ? ORDER BY id DESC LIMIT 1",
        (ticker, horizon),
    ).fetchone()


def _expire_stale(conn) -> None:
    if "stock_analysis" not in table_names(conn):
        return
    cutoff = (_utc_now() - timedelta(minutes=STALE_RUNNING_MINUTES)).isoformat(timespec="seconds")
    with conn:
        conn.execute(
            "UPDATE stock_analysis SET status = 'error', error = 'the analysis did not finish', "
            "finished_at = ? WHERE status = 'running' AND started_at < ?",
            (_utc_now().isoformat(timespec="seconds"), cutoff),
        )


def _fresh(conn, row) -> bool:
    """A finished run is reused for 30 minutes unless a newer non-noise headline arrived since."""
    if row["status"] not in ("ok", "partial"):
        return False
    finished = _parse(row["finished_at"] or row["started_at"])
    if finished is None or _utc_now() - finished > timedelta(minutes=REUSE_MINUTES):
        return False
    if "news_items" not in table_names(conn):
        return True
    newer = conn.execute(
        "SELECT 1 FROM news_items WHERE ticker = ? AND rule_noise = 0 AND published_at > ? LIMIT 1",
        (row["ticker"], row["started_at"]),
    ).fetchone()
    return newer is None


def _known_ticker(conn, ticker: str) -> bool:
    if not TICKER_RE.fullmatch(ticker):
        return False
    tables = table_names(conn)
    for table in ("recommendations", "universe"):
        if table in tables and conn.execute(
                f"SELECT 1 FROM {table} WHERE ticker = ? LIMIT 1", (ticker,)).fetchone():
            return True
    return False


def _worker(analysis_id: int, ticker: str, horizon: str) -> None:
    from .main import db  # local import: main wires this router in

    try:
        llm = analyze.make_llm(fake=os.environ.get("AGENT_FAKE_LLM") == "1")
    except Exception as exc:  # noqa: BLE001 - e.g. the model is not configured
        conn = db()
        try:
            analyze.finish(conn, analysis_id, "error", None, f"{exc}"[:300], None, 0)
        finally:
            conn.close()
        return
    analyze.run_analysis(db, llm, ticker, horizon, FETCHERS, analysis_id=analysis_id)


def _checked(conn, ticker: str, horizon: str, session) -> str:
    from .main import current_user  # local import: main wires this router in

    current_user(conn, session)
    if horizon != "1w":
        raise HTTPException(422, "horizon not supported yet")
    t = ticker.strip().upper()
    if not _known_ticker(conn, t):
        raise HTTPException(404, "unknown ticker")
    return t


@router.post("/analysis/{ticker}")
def start_analysis(ticker: str, horizon: Literal["1w", "1m", "3m"] = "1w",
                   session: str | None = Cookie(default=None)):
    from .main import db

    conn = db()
    try:
        t = _checked(conn, ticker, horizon, session)
        with _start_lock:
            _expire_stale(conn)
            row = _latest(conn, t, horizon)
            if row is not None and row["status"] == "running":
                return _body(row, False)
            if row is not None and _fresh(conn, row):
                return _body(row, True)
            analysis_id = analyze.start_run(conn, t, horizon)
            threading.Thread(target=_worker, args=(analysis_id, t, horizon), daemon=True).start()
            return _body(_latest(conn, t, horizon), False)
    finally:
        conn.close()


@router.get("/analysis/{ticker}")
def read_analysis(ticker: str, horizon: Literal["1w", "1m", "3m"] = "1w",
                  session: str | None = Cookie(default=None)):
    from .main import db

    conn = db()
    try:
        t = _checked(conn, ticker, horizon, session)
        _expire_stale(conn)
        row = _latest(conn, t, horizon)
        if row is None:
            raise HTTPException(404, "no analysis")
        return _body(row, False)
    finally:
        conn.close()
