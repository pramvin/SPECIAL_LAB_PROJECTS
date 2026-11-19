"""AI agent reviews: latest opinion per idea plus the full review detail.

Reads the tables Agent A writes (agent_runs / agent_decisions). Every evidence id
shown to the user is resolved from data we already had; ids that cannot be
resolved are dropped, never invented.
"""
import json
import re
import sqlite3
from typing import Literal

from fastapi import APIRouter, Cookie, HTTPException

from .dbcompat import table_names

router = APIRouter(prefix="/api")

TICKER_RE = re.compile(r"[A-Z.\-]{1,10}")
RATINGS = {"Buy", "Overweight", "Hold", "Underweight", "Sell", "REVIEW"}
SIGNALS = {"bullish", "neutral", "bearish", "no_data"}
AGREE_BY_RATING = {
    "Buy": "agree",
    "Overweight": "agree",
    "Hold": "caution",
    "Underweight": "disagree",
    "Sell": "disagree",
    "REVIEW": "review",
}
SOURCE_KEYS = ("prices", "news", "fmp", "sec", "social", "macro")
SOURCE_STATUSES = {"ok", "unavailable", "skipped"}
ANALYST_KEYS = ("market", "news", "fundamentals", "social")
RISK_KEYS = ("aggressive", "conservative", "neutral")
EVIDENCE_KINDS = {"news", "metric", "fund", "sec", "social", "macro", "rule", "agent", "memory"}
AGENT_LABELS = {
    "market": "Market analyst",
    "news": "News analyst",
    "fundamentals": "Fundamentals analyst",
    "social": "Social analyst",
    "bull": "Bull researcher",
    "bear": "Bear researcher",
    "research_manager": "Research manager",
    "trader": "Trader",
    "aggressive": "Aggressive risk analyst",
    "conservative": "Conservative risk analyst",
    "neutral": "Neutral risk analyst",
    "portfolio_manager": "Portfolio manager",
}
MAX_TRACK_RECORD = 5
NO_RUN_STATUSES = ("ok", "partial")
# Quick one-call reviews carry this prompt_version (agents/config.py TRIAGE_PROMPT_VERSION).
TRIAGE_VERSION = "ta-triage-v1"
CONFIDENCES = {"low", "medium", "high"}


def rating_agrees(rating: str | None) -> str:
    return AGREE_BY_RATING.get(rating or "", "review")


def _json(value, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _points(raw) -> list[dict]:
    out = []
    for p in raw if isinstance(raw, list) else []:
        if not isinstance(p, dict) or not isinstance(p.get("text"), str):
            continue
        evidence = [e for e in p.get("evidence") or [] if isinstance(e, str) and e]
        out.append({"text": p["text"], "evidence": evidence})
    return out


def _evidence_ids(raw) -> list[str]:
    return [e for e in raw or [] if isinstance(e, str) and e]


def latest_ai(conn: sqlite3.Connection, tickers: list[str], horizon: str) -> dict:
    """Newest ok/partial review per ticker, in the shape the ideas list needs.

    A full 12-agent review wins; a ticker with only a quick (triage) review gets that,
    marked `mode: "quick"` with its confidence and points.
    """
    if not tickers or "agent_runs" not in table_names(conn):
        return {}
    out: dict[str, dict] = {}
    for ticker in tickers:
        mode = "full"
        row = conn.execute(
            "SELECT id, rating, summary, as_of, started_at, model, final_json FROM agent_runs "
            "WHERE ticker = ? AND horizon = ? AND status IN ('ok', 'partial') "
            "AND prompt_version <> ? ORDER BY id DESC LIMIT 1",
            (ticker, horizon, TRIAGE_VERSION),
        ).fetchone()
        if row is None:
            mode = "quick"
            row = conn.execute(
                "SELECT id, rating, summary, as_of, started_at, model, final_json FROM agent_runs "
                "WHERE ticker = ? AND horizon = ? AND status IN ('ok', 'partial') "
                "AND prompt_version = ? ORDER BY id DESC LIMIT 1",
                (ticker, horizon, TRIAGE_VERSION),
            ).fetchone()
        if row is None:
            continue
        rating = row["rating"] if row["rating"] in RATINGS else "REVIEW"
        item = {
            "run_id": row["id"],
            "mode": mode,
            "rating": rating,
            "summary": row["summary"] or "",
            "agrees": rating_agrees(rating),
            "as_of": row["as_of"],
            "created_at": row["started_at"],
            "model": row["model"],
        }
        if mode == "quick":
            final = _json(row["final_json"], {})
            final = final if isinstance(final, dict) else {}
            item["confidence"] = final.get("confidence") if final.get("confidence") in CONFIDENCES else "low"
            item["points"] = _points(final.get("points"))
        out[ticker] = item
    return out


def _sources(raw) -> dict:
    out = {}
    for key in SOURCE_KEYS:
        value = raw.get(key) if isinstance(raw, dict) else None
        if isinstance(value, dict) and value.get("status") in SOURCE_STATUSES:
            item = {"status": value["status"]}
            if value.get("reason"):
                item["reason"] = str(value["reason"])
            out[key] = item
        else:
            out[key] = {"status": "unavailable", "reason": "not reported"}
    return out


def _analyst(raw):
    if not isinstance(raw, dict):
        return None
    signal = raw.get("signal")
    return {
        "signal": signal if signal in SIGNALS else "no_data",
        "summary": raw["summary"] if isinstance(raw.get("summary"), str) else "",
        "points": _points(raw.get("points")),
        "data_gaps": [g for g in raw.get("data_gaps") or [] if isinstance(g, str) and g],
    }


def _manager(raw):
    if not isinstance(raw, dict):
        return None
    lean = raw.get("lean")
    return {
        "lean": lean if lean in RATINGS else "REVIEW",
        "rationale": raw["rationale"] if isinstance(raw.get("rationale"), str) else "",
        "evidence": _evidence_ids(raw.get("evidence")),
    }


def _trader(raw):
    if not isinstance(raw, dict) or raw.get("stance") not in ("enter", "wait", "avoid"):
        return None

    def number(key):
        value = raw.get(key)
        return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None

    return {
        "stance": raw["stance"],
        "rationale": raw["rationale"] if isinstance(raw.get("rationale"), str) else "",
        "evidence": _evidence_ids(raw.get("evidence")),
        "suggested_stop": number("suggested_stop"),
        "suggested_target": number("suggested_target"),
    }


def _risk(raw):
    out = {}
    for key in RISK_KEYS:
        value = raw.get(key) if isinstance(raw, dict) else None
        if not isinstance(value, dict):
            out[key] = None
            continue
        pct = value.get("suggested_position_pct")
        out[key] = {
            "view": value["view"] if isinstance(value.get("view"), str) else "",
            "suggested_position_pct": pct if isinstance(pct, (int, float)) and not isinstance(pct, bool) else None,
            "evidence": _evidence_ids(value.get("evidence")),
        }
    return out


def _rules(conn: sqlite3.Connection, ticker: str, horizon: str, review: dict) -> dict:
    raw = review.get("rules")
    if isinstance(raw, dict) and all(
        isinstance(raw.get(k), (int, float)) and not isinstance(raw.get(k), bool)
        for k in ("entry", "stop", "target", "score")
    ):
        return {k: raw[k] for k in ("entry", "stop", "target", "score")}
    if "recommendations" in table_names(conn):
        row = conn.execute(
            "SELECT entry, stop, target, score FROM recommendations "
            "WHERE ticker = ? AND horizon = ? ORDER BY id DESC LIMIT 1",
            (ticker, horizon),
        ).fetchone()
        if row is not None:
            return {k: row[k] for k in ("entry", "stop", "target", "score")}
    return {"entry": 0, "stop": 0, "target": 0, "score": 0}


def _cited_ids(review: dict) -> list[str]:
    """Every evidence id cited in the review, in first-seen order (contract order)."""
    seen: set[str] = set()
    order: list[str] = []

    def add(ids):
        for evidence_id in ids:
            if evidence_id not in seen:
                seen.add(evidence_id)
                order.append(evidence_id)

    for point in review["key_risks"]:
        add(point["evidence"])
    for key in ANALYST_KEYS:
        analyst = review["analysts"][key]
        if analyst:
            for point in analyst["points"]:
                add(point["evidence"])
    add(review["debate"]["manager"]["evidence"] if review["debate"]["manager"] else [])
    for side in ("bull", "bear"):
        for point in review["debate"][side]:
            add(point["evidence"])
    if review["trader"]:
        add(review["trader"]["evidence"])
    for key in RISK_KEYS:
        if review["risk"][key]:
            add(review["risk"][key]["evidence"])
    return order


def _resolve(conn: sqlite3.Connection, ticker: str, horizon: str, evidence_id: str,
             index: dict, has_news: bool, has_scores: bool, has_decisions: bool):
    kind, _, rest = evidence_id.partition(":")
    if kind not in EVIDENCE_KINDS or not rest:
        return None

    if kind == "news":
        try:
            news_id = int(rest)
        except ValueError:
            return None
        if not has_news:
            return None
        row = conn.execute(
            "SELECT id, title, source, url, published_at FROM news_items WHERE id = ?",
            (news_id,),
        ).fetchone()
        if row is None:
            return None
        item = {
            "id": evidence_id,
            "kind": "news",
            "label": row["title"],
            "url": row["url"],
            "published_at": row["published_at"],
        }
        if has_scores:
            score = conn.execute(
                "SELECT sentiment FROM news_scores WHERE news_id = ? "
                "ORDER BY scored_at DESC, model DESC LIMIT 1",
                (news_id,),
            ).fetchone()
            if score is not None:
                item["sentiment"] = score["sentiment"]
        return item

    if kind == "rule":
        try:
            position = int(rest)
        except ValueError:
            return None
        if "recommendations" not in table_names(conn):
            return None
        row = conn.execute(
            "SELECT reasons FROM recommendations WHERE ticker = ? AND horizon = ? "
            "ORDER BY id DESC LIMIT 1",
            (ticker, horizon),
        ).fetchone()
        reasons = _json(row["reasons"], []) if row is not None else []
        if not isinstance(reasons, list) or not 0 <= position < len(reasons):
            return None
        return {"id": evidence_id, "kind": "rule", "label": str(reasons[position])}

    if kind == "agent":
        return {
            "id": evidence_id,
            "kind": "agent",
            "label": AGENT_LABELS.get(rest, rest.replace("_", " ")),
        }

    if kind == "memory":
        try:
            decision_id = int(rest)
        except ValueError:
            return None
        if not has_decisions:
            return None
        row = conn.execute(
            "SELECT as_of, rating FROM agent_decisions WHERE id = ?", (decision_id,)
        ).fetchone()
        if row is None:
            return None
        return {"id": evidence_id, "kind": "memory", "label": f"{row['as_of']} · {row['rating']}"}

    entry = index.get(evidence_id)
    if not isinstance(entry, dict) or not isinstance(entry.get("label"), str):
        return None
    item = {"id": evidence_id, "kind": kind, "label": entry["label"]}
    for key in ("value", "url", "published_at", "sentiment"):
        if isinstance(entry.get(key), str) and entry[key]:
            item[key] = entry[key]
    return item


def _track_record(conn: sqlite3.Connection, ticker: str) -> list[dict]:
    if "agent_decisions" not in table_names(conn):
        return []
    rows = conn.execute(
        "SELECT as_of, rating, return_pct, benchmark_return_pct, alpha_pct, reflection "
        "FROM agent_decisions WHERE ticker = ? ORDER BY as_of DESC, id DESC LIMIT ?",
        (ticker, MAX_TRACK_RECORD),
    ).fetchall()
    return [
        {
            "as_of": r["as_of"],
            "rating": r["rating"],
            "return_pct": r["return_pct"],
            "benchmark_return_pct": r["benchmark_return_pct"],
            "alpha_pct": r["alpha_pct"],
            "reflection": r["reflection"],
        }
        for r in rows
    ]


def build_review(conn: sqlite3.Connection, ticker: str, horizon: str) -> dict | None:
    """The AgentReview payload for the newest usable run, or None (-> 404)."""
    if "agent_runs" not in table_names(conn):
        return None
    row = conn.execute(
        "SELECT * FROM agent_runs WHERE ticker = ? AND horizon = ? "
        "AND status IN ('ok', 'partial') AND prompt_version <> ? ORDER BY id DESC LIMIT 1",
        (ticker, horizon, TRIAGE_VERSION),
    ).fetchone()
    if row is None:
        return None

    final = _json(row["final_json"], {})
    if not isinstance(final, dict):
        final = {}
    nested = final.get("review")
    raw_review = nested if isinstance(nested, dict) else final
    evidence_index = final.get("evidence_index")
    if not isinstance(evidence_index, dict):
        evidence_index = raw_review.get("evidence_index")
    if not isinstance(evidence_index, dict):
        evidence_index = {}

    rating = raw_review.get("rating")
    if rating not in RATINGS:
        rating = row["rating"] if row["rating"] in RATINGS else "REVIEW"
    summary = raw_review.get("summary")
    if not isinstance(summary, str):
        summary = row["summary"] or ""

    debate_raw = raw_review.get("debate") if isinstance(raw_review.get("debate"), dict) else {}
    analysts_raw = raw_review.get("analysts") if isinstance(raw_review.get("analysts"), dict) else {}
    review = {
        "rating": rating,
        "summary": summary,
        "agrees": rating_agrees(rating),
        "key_risks": _points(raw_review.get("key_risks")),
        "analysts": {key: _analyst(analysts_raw.get(key)) for key in ANALYST_KEYS},
        "debate": {
            "bull": _points(debate_raw.get("bull")),
            "bear": _points(debate_raw.get("bear")),
            "manager": _manager(debate_raw.get("manager")),
        },
        "trader": _trader(raw_review.get("trader")),
        "risk": _risk(raw_review.get("risk")),
        "rules": _rules(conn, ticker, horizon, raw_review),
    }

    tables = table_names(conn)
    has_news = "news_items" in tables
    evidence = []
    for evidence_id in _cited_ids(review):
        item = _resolve(
            conn, ticker, horizon, evidence_id, evidence_index,
            has_news, "news_scores" in tables, "agent_decisions" in tables,
        )
        if item is not None:
            evidence.append(item)

    return {
        "run_id": row["id"],
        "ticker": row["ticker"],
        "horizon": row["horizon"],
        "as_of": row["as_of"],
        "model": row["model"],
        "deep_model": row["deep_model"],
        "prompt_version": row["prompt_version"],
        "created_at": row["started_at"],
        "status": row["status"],
        "sources": _sources(_json(row["sources_json"], {})),
        "review": review,
        "evidence": evidence,
        "track_record": _track_record(conn, ticker),
    }


@router.get("/agents/{ticker}")
def agent_review(
    ticker: str,
    horizon: Literal["1w", "1m", "3m"] = "1w",
    session: str | None = Cookie(default=None),
):
    from .main import current_user, db  # local import: main imports this module

    t = ticker.strip().upper()
    if not TICKER_RE.fullmatch(t):
        raise HTTPException(422, "Invalid ticker")
    with db() as conn:
        current_user(conn, session)
        review = build_review(conn, t, horizon)
    if review is None:
        raise HTTPException(404, "no review")
    return review
