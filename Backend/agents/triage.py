"""Quick review (triage): one LLM call per stock on a one-page brief.

The full review (agents/graph.py) makes 12 calls per stock. Triage reads only the
rule idea, a few price metrics and up to TRIAGE_NEWS recent headlines, so it is
cheap enough to run on a long list. It uses the same evidence-id and number
checks, never changes the rule's entry/stop/target/score, and is stored as an
`agent_runs` row whose `prompt_version` is `config.TRIAGE_PROMPT_VERSION`.

A triage run does not write `agent_decisions`: the track record and the memory
lessons belong to full reviews only.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from . import config, context, graph, llm_client, schema, validate


def _skipped(*args, **kwargs) -> dict:
    return {"status": "skipped", "reason": "not used in the quick review", "items": []}


# SEC filings and social posts are left to the full review (fundamentals and macro are in the brief).
SKIPPED_FETCHERS = {"sec": _skipped, "social": _skipped}

ESCALATE_AGAINST = ("Underweight", "Sell")
ESCALATE_FOR = ("Buy", "Overweight")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def brief_text(ctx: context.Context) -> str:
    intro = (f"Ticker: {ctx.ticker} ({ctx.name or 'unknown name'}). Horizon: {ctx.horizon}. "
             f"Price data as of: {ctx.as_of}.")
    return "\n\n".join([
        intro,
        context.section("Rule-based idea (read-only; never change these numbers)",
                        context.rule_lines(ctx)),
        context.section("Price metrics and indicators", context.metric_lines(ctx)
                        + _extra_metric_lines(ctx)),
        context.section("Company fundamentals (Yahoo Finance ratios, last four quarters, insider activity)",
                        context.fund_lines(ctx), empty="(No fundamentals available.)"),
        context.section("Macro", context.macro_lines(ctx), empty="(No macro data available.)"),
        context.section(f"Recent headlines (up to {config.TRIAGE_NEWS})", context.news_lines(ctx),
                        empty="(No recent headlines.)"),
    ])


def _extra_metric_lines(ctx: context.Context) -> list[str]:
    return [f"- {entry['label']}: {entry['value']} ({key})"
            for key, entry in ctx.evidence.items()
            if key in ("metric:bigmove_p", "metric:atr_pct")]


def _add_rule_metrics(ctx: context.Context) -> None:
    rules = ctx.rules or {}
    bigmove = rules.get("bigmove_p")
    if isinstance(bigmove, (int, float)) and not isinstance(bigmove, bool):
        ctx.evidence["metric:bigmove_p"] = {
            "kind": "metric", "label": "Chance of a big 5-day move (model)",
            "value": f"{float(bigmove) * 100:.0f}%"}
    atr = rules.get("atr_pct")
    if isinstance(atr, (int, float)) and not isinstance(atr, bool):
        ctx.evidence["metric:atr_pct"] = {
            "kind": "metric", "label": "Average daily range (ATR %)", "value": f"{float(atr):.2f}%"}


def triage_ticker(conn, llm, ticker: str, horizon: str = "1w", fetchers: dict | None = None,
                  on_event=None) -> int:
    """Quick-review one ticker and return the `agent_runs.id`. Never raises for one ticker."""
    ticker = ticker.strip().upper()
    settings = config.llm_settings()
    model = getattr(llm, "model", "") or settings.get("triage_model") or "unknown"
    schema.ensure(conn)
    today = datetime.now(timezone.utc).date().isoformat()
    with conn:
        row = conn.execute(
            "INSERT INTO agent_runs (ticker, horizon, as_of, model, deep_model, prompt_version, status, "
            "sources_json, started_at) VALUES (?, ?, ?, ?, ?, ?, 'error', '{}', ?) RETURNING id",
            (ticker, horizon, today, model, model, config.TRIAGE_PROMPT_VERSION, _now()),
        ).fetchone()
    run_id = row[0]

    try:
        ctx = context.collect(conn, ticker, horizon, fetchers={**SKIPPED_FETCHERS, **(fetchers or {})})
        ctx.news = ctx.news[:config.TRIAGE_NEWS]
        shown = {f"news:{item['id']}" for item in ctx.news}
        ctx.evidence = {key: value for key, value in ctx.evidence.items()
                        if not key.startswith("news:") or key in shown}
        _add_rule_metrics(ctx)
        with conn:
            conn.execute("UPDATE agent_runs SET as_of = ? WHERE id = ?", (ctx.as_of, run_id))

        runner = graph.Runner(conn, llm, run_id, ctx, on_event=on_event, secret=settings.get("api_key"))
        brief = brief_text(ctx)
        # Only numbers the model can actually see in the brief may be repeated.
        runner.numbers = validate.numbers_in(brief + "\n" + json.dumps(runner._evidence_values()))
        output = runner.call("triage", brief, set(ctx.evidence))

        if output and not ctx.news and output["confidence"] != "low":
            output["confidence"] = "low"  # no headlines: the call rests on numbers alone
        rating = output["rating"] if output else config.REVIEW
        confidence = output["confidence"] if output else "low"
        summary = output["summary"] if output else "The quick review did not return a valid answer."
        points = output["points"] if output else []

        rules = ctx.rules or {}
        final = {
            "mode": "triage", "rating": rating, "confidence": confidence, "summary": summary,
            "agrees": config.agrees(rating), "points": points,
            "verdict": output["verdict"] if output else {},
            "rules": {key: rules.get(key) or 0 for key in ("entry", "stop", "target", "score")},
            "evidence_index": {
                key: {field: value[field] for field in
                      ("label", "value", "url", "published_at", "sentiment") if value.get(field)}
                for key, value in ctx.evidence.items() if not key.startswith(("news:", "rule:"))
            },
        }
        status = "ok" if output else "partial"
        with conn:
            conn.execute(
                "UPDATE agent_runs SET as_of = ?, status = ?, rating = ?, summary = ?, final_json = ?, "
                "sources_json = ?, tokens_in = ?, tokens_out = ?, finished_at = ? WHERE id = ?",
                (ctx.as_of, status, rating, summary, json.dumps(final), json.dumps(ctx.sources),
                 runner.tokens_in, runner.tokens_out, _now(), run_id),
            )
        return run_id
    except Exception as exc:  # noqa: BLE001 - one ticker failure is stored, not raised
        message = llm_client.scrub(f"{type(exc).__name__}: {exc}", settings.get("api_key"))[:300]
        with conn:
            conn.execute(
                "UPDATE agent_runs SET status = 'error', error = ?, finished_at = ? WHERE id = ?",
                (message, _now(), run_id),
            )
        if on_event:
            on_event("run", "fail", 0, 0, message)
        return run_id


def select_for_full(results: list[dict], limit: int) -> list[dict]:
    """Which triaged stocks deserve the 12-agent review.

    `results`: dicts with ticker, rating, confidence, score. A stock goes through
    when the quick review argues against the rule idea (Underweight/Sell) or backs
    it with high confidence (Buy/Overweight). Highest rule score first, at most `limit`.
    """
    picked = []
    for item in results:
        rating, confidence = item.get("rating"), item.get("confidence")
        if rating in ESCALATE_AGAINST:
            reason = "disagrees with the rules"
        elif rating in ESCALATE_FOR and confidence == "high":
            reason = "strong agreement"
        else:
            continue
        picked.append({**item, "reason": reason})
    picked.sort(key=lambda item: (-(item.get("score") or 0), item["ticker"]))
    return picked[:max(0, limit)]
