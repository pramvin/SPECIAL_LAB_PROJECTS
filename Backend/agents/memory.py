"""Decision memory: record a decision, settle it vs SPY, and write one reflection.

Adapted from TauricResearch/TradingAgents (Apache-2.0), memory/settlement.py,
memory/reflection.py and memory/log.py.
"""
from __future__ import annotations

import json
from bisect import bisect_right
from datetime import datetime, timezone

from . import config, prompts, sources


def record_decision(conn, run_id: int, ticker: str, rating: str, as_of: str) -> None:
    if rating not in config.RATINGS:
        return
    with conn:
        conn.execute(
            "INSERT INTO agent_decisions (run_id, ticker, rating, as_of, settle_after_days) "
            "VALUES (?, ?, ?, ?, ?)",
            (run_id, ticker, rating, as_of, config.SETTLE_DAYS),
        )


def _series(rows) -> tuple[list[str], list[float]]:
    dates = [row["date"] if "date" in row.keys() else row[0] for row in rows]
    closes = [float(row["close"] if "close" in row.keys() else row[1]) for row in rows]
    return dates, closes


def _at_or_before(dates: list[str], closes: list[float], day: str) -> tuple[str, float] | None:
    index = bisect_right(dates, day) - 1
    if index < 0:
        return None
    return dates[index], closes[index]


def _settle_one(conn, llm, decision, on_event=None) -> bool:
    ticker = decision["ticker"]
    rows = conn.execute(
        "SELECT date, close FROM prices WHERE ticker = ? AND date > ? ORDER BY date",
        (ticker, decision["as_of"]),
    ).fetchall()
    if len(rows) <= config.SETTLE_DAYS:
        return False
    dates, closes = _series(rows)
    entry_date, entry_close = dates[0], closes[0]
    exit_date, exit_close = dates[config.SETTLE_DAYS], closes[config.SETTLE_DAYS]

    spy = sources.spy_closes(conn)
    if not spy:
        return False
    spy_dates = [row["date"] for row in spy]
    spy_closes = [float(row["close"]) for row in spy]
    bench_entry = _at_or_before(spy_dates, spy_closes, entry_date)
    bench_exit = _at_or_before(spy_dates, spy_closes, exit_date)
    if not bench_entry or not bench_exit or spy_dates[-1] < exit_date:
        return False

    return_pct = exit_close / entry_close - 1
    bench_return = bench_exit[1] / bench_entry[1] - 1
    alpha = return_pct - bench_return

    user = (
        f"Raw return over {config.SETTLE_DAYS} trading days: {return_pct:+.1%}\n"
        f"Alpha vs SPY: {alpha:+.1%}\n\n"
        f"Final Decision:\n{decision['summary'] or decision['rating']}"
    )
    try:
        result = llm.chat_json("reflection", prompts.system("reflection"), user)
    except Exception as exc:  # noqa: BLE001 - leave the decision pending
        if on_event:
            on_event("reflection", "fail", 0, 0, f"{type(exc).__name__}: {exc}"[:200])
        return False
    if on_event:
        on_event("reflection", "ok", result.get("latency_ms", 0),
                 result.get("tokens_in", 0) + result.get("tokens_out", 0), None)
    reflection = (result.get("data") or {}).get("reflection")
    if not isinstance(reflection, str) or not reflection.strip():
        return False

    with conn:
        conn.execute(
            "UPDATE agent_decisions SET entry_close = ?, settled_on = ?, return_pct = ?, "
            "benchmark_return_pct = ?, alpha_pct = ?, reflection = ?, settled_at = ? WHERE id = ?",
            (entry_close, exit_date, return_pct, bench_return, alpha, reflection.strip(),
             datetime.now(timezone.utc).isoformat(), decision["id"]),
        )
    return True


def settle(conn, llm, on_event=None) -> int:
    """Settle every decision whose full 5-trading-day window has traded. Returns a count."""
    rows = conn.execute(
        "SELECT d.id, d.ticker, d.rating, d.as_of, r.summary FROM agent_decisions d "
        "JOIN agent_runs r ON r.id = d.run_id "
        "WHERE d.settled_at IS NULL ORDER BY d.id"
    ).fetchall()
    settled = 0
    for row in rows:
        decision = {key: row[key] for key in row.keys()}
        decision["summary"] = decision.get("summary") or decision.get("rating") or ""
        try:
            settled += bool(_settle_one(conn, llm, decision, on_event=on_event))
        except Exception as exc:  # noqa: BLE001 - one bad decision never stops the batch
            if on_event:
                on_event("reflection", "fail", 0, 0, f"{type(exc).__name__}: {exc}"[:200])
    return settled


def memory_items(conn, ticker: str, same: int = 3, cross: int = 3) -> list[dict]:
    """Last settled decisions for this ticker, then lessons from other tickers."""
    columns = ("id, ticker, rating, as_of, return_pct, benchmark_return_pct, alpha_pct, "
               "reflection, settled_on")
    rows = conn.execute(
        f"SELECT {columns} FROM agent_decisions WHERE settled_at IS NOT NULL AND ticker = ? "
        "ORDER BY id DESC LIMIT ?", (ticker, same),
    ).fetchall()
    rows += conn.execute(
        f"SELECT {columns} FROM agent_decisions WHERE settled_at IS NOT NULL AND ticker <> ? "
        "ORDER BY id DESC LIMIT ?", (ticker, cross),
    ).fetchall()
    items = []
    for row in rows:
        item = {key: row[key] for key in row.keys()}
        for key in ("return_pct", "benchmark_return_pct", "alpha_pct"):
            if item.get(key) is not None:
                item[key] = round(float(item[key]) * 100, 2)
        items.append(item)
    return items


def memory_evidence(items: list[dict]) -> dict:
    """`memory:<id>` entries for the evidence index."""
    out = {}
    for item in items:
        value = f"{item['ticker']} {item['rating']} on {item['as_of']}"
        if item.get("alpha_pct") is not None:
            value += f", alpha {item['alpha_pct']:.2f}%"
        out[f"memory:{item['id']}"] = {
            "kind": "memory", "label": "Past decision", "value": value,
            "published_at": item.get("settled_on"),
        }
    return out
