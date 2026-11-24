"""On-demand Yahoo news: pull one ticker NOW, archive and label the new headlines.

The click-analysis job (`app.analysis_api`) and the home feed (`GET /api/latest-news`)
call this instead of waiting for the hourly job. Yahoo is an unofficial free feed, so a
failure is normal: the result says `status: "unavailable"` and nothing raises.

New rows are labelled with the local sentiment model (`pipeline.sentiment`), loaded once
per process. `recommendations.news` for the same ticker is refreshed by `news.save_items`.
"""
import threading
import time
from datetime import datetime, timezone

from app.dbcompat import table_names

from . import news, sentiment

MEMO_S = 60.0  # do not fetch the same ticker twice within a minute
DELAY_S = 0.5  # pause between tickers in refresh_many

_last_fetch: dict[str, float] = {}
_memo_lock = threading.Lock()
_bundle = None
_bundle_loaded = False
_bundle_lock = threading.Lock()


def _memo_allows(ticker: str) -> bool:
    """True when this ticker may be fetched now; remembers the attempt either way."""
    with _memo_lock:
        last = _last_fetch.get(ticker)
        if last is not None and time.time() - last < MEMO_S:
            return False
        _last_fetch[ticker] = time.time()
        return True


def _get_bundle():
    """The sentiment bundle, or None when the model file is missing (labeling is skipped)."""
    global _bundle, _bundle_loaded
    with _bundle_lock:
        if not _bundle_loaded:
            _bundle_loaded = True
            try:
                _bundle = sentiment.load_bundle()
            except (SystemExit, Exception):  # missing model/sklearn: keep the news, skip labels
                _bundle = None
    return _bundle


def _ticker_name(conn, ticker: str) -> str:
    for table in ("recommendations", "universe"):
        if table in table_names(conn):
            row = conn.execute(f"SELECT name FROM {table} WHERE ticker = ? LIMIT 1", (ticker,)).fetchone()
            if row and row[0]:
                return row[0]
    return ticker


def _label_new(conn, ids: list[int]) -> int:
    """Write a `news_scores` row for each new headline; returns how many were labeled."""
    bundle = _get_bundle()
    if not bundle or not ids:
        return 0
    marks = ",".join("?" * len(ids))
    rows = conn.execute(f"SELECT id, title FROM news_items WHERE id IN ({marks})", ids).fetchall()
    if not rows:
        return 0
    labels = sentiment.score_texts(bundle, [r["title"] for r in rows])
    model = bundle.get("name") or sentiment.DEFAULT_NAME
    now = datetime.now(timezone.utc).isoformat()
    with conn:
        conn.executemany(
            "INSERT INTO news_scores (news_id, model, sentiment, p_bearish, p_bullish, p_neutral, kind, p_filler, scored_at) "
            "VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(news_id, model) DO UPDATE SET sentiment=excluded.sentiment, "
            "p_bearish=excluded.p_bearish, p_bullish=excluded.p_bullish, p_neutral=excluded.p_neutral, "
            "kind=excluded.kind, p_filler=excluded.p_filler, scored_at=excluded.scored_at",
            [(r["id"], model, s["sentiment"], s["p_bearish"], s["p_bullish"], s["p_neutral"], "n/a", None, now)
             for r, s in zip(rows, labels)],
        )
    return len(rows)


def refresh_ticker(conn, ticker: str, name: str | None = None) -> dict:
    """Pull Yahoo headlines for one ticker now and store/label the new ones. Never raises."""
    out = {"new": 0, "scored": 0, "status": "ok", "reason": None}
    ticker = ticker.strip().upper()
    if not _memo_allows(ticker):
        out["reason"] = "fetched in the last 60 seconds"
        return out
    try:
        conn.executescript(news.SCHEMA)
        items = news.fetch(ticker, name or _ticker_name(conn, ticker))
    except Exception as e:  # Yahoo down, blocked, or a changed response shape
        out.update(status="unavailable", reason=f"{e.__class__.__name__}: {e}")
        return out
    try:
        new_ids = news.save_items(conn, ticker, items)
    except Exception as e:
        out.update(status="unavailable", reason=f"store failed: {e.__class__.__name__}: {e}")
        return out
    out["new"] = len(new_ids)
    if new_ids:
        try:
            conn.executescript(sentiment.SCHEMA)
            out["scored"] = _label_new(conn, new_ids)
        except Exception as e:  # headlines are stored; only the labels are missing
            out["reason"] = f"label failed: {e.__class__.__name__}: {e}"
    return out


def refresh_many(conn, tickers: list[str]) -> dict:
    """Refresh a list of tickers (short pause between them) and return the totals."""
    results: list[dict] = []
    for i, ticker in enumerate(dict.fromkeys(t.strip().upper() for t in tickers if t.strip())):
        if i:
            time.sleep(DELAY_S)
        results.append(refresh_ticker(conn, ticker))
    failed = [r for r in results if r["status"] != "ok"]
    if not failed:
        status = "ok"
    elif len(failed) == len(results):
        status = "unavailable"
    else:
        status = "partial"
    return {
        "new": sum(r["new"] for r in results),
        "scored": sum(r["scored"] for r in results),
        "status": status,
        "reason": None if not failed else f"{len(failed)} of {len(results)} tickers unavailable",
    }
