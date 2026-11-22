"""Builds the per-role evidence context and the allowed evidence-id set."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from . import sources


@dataclass
class Context:
    ticker: str
    horizon: str
    as_of: str
    name: str = ""
    sources: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    rules: dict | None = None
    news: list = field(default_factory=list)
    fund: dict = field(default_factory=dict)
    sec: list = field(default_factory=list)
    social: list = field(default_factory=list)
    macro: list = field(default_factory=list)
    prices: list = field(default_factory=list)
    evidence: dict = field(default_factory=dict)
    memory: list = field(default_factory=list)


def _status(result: dict) -> dict:
    return {"status": result.get("status", "unavailable"),
            "reason": sources.redact_reason(result.get("reason"))}


def _call(fn, *args, **kwargs) -> dict:
    try:
        result = fn(*args, **kwargs)
        if not isinstance(result, dict) or "status" not in result:
            raise ValueError("bad source result")
        return result
    except Exception as exc:  # noqa: BLE001 - one source never stops the review
        return {"status": "unavailable", "reason": f"{type(exc).__name__}", "items": []}


def _fmt_number(value) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{float(value):.2f}"
    return str(value)


def collect(conn, ticker: str, horizon: str, fetchers: dict | None = None) -> Context:
    fetchers = fetchers or {}
    prices_result = _call(fetchers.get("prices") or sources.fetch_prices, conn, ticker)
    price_items = prices_result.get("items") or []
    as_of = price_items[-1]["date"] if price_items else None
    if not as_of:
        from datetime import datetime, timezone
        as_of = datetime.now(timezone.utc).date().isoformat()

    rules_result = _call(fetchers.get("rules") or sources.fetch_rules, conn, ticker, horizon)
    news_result = _call(fetchers.get("news") or sources.fetch_news, conn, ticker, as_of=as_of)
    fmp_result = _call(fetchers.get("fmp") or sources.fetch_fundamentals, conn, ticker, as_of=as_of)
    sec_result = _call(fetchers.get("sec") or sources.fetch_sec, conn, ticker, as_of=as_of)
    social_result = _call(fetchers.get("social") or sources.fetch_social, conn, ticker, as_of=as_of)
    macro_result = _call(fetchers.get("macro") or sources.fetch_macro, conn, as_of=as_of)

    name = ""
    try:
        row = conn.execute(
            "SELECT name FROM recommendations WHERE ticker = ? ORDER BY id DESC LIMIT 1", (ticker,)
        ).fetchone()
        if row:
            name = row[0]
    except Exception:  # noqa: BLE001
        name = ""

    metrics = sources.compute_metrics(price_items) if price_items else {}
    rules = rules_result.get("items") if rules_result.get("status") == "ok" else None
    news = news_result.get("items") or []
    fund = fmp_result.get("items") or {}
    sec = sec_result.get("items") or []
    social = social_result.get("items") or []
    macro = macro_result.get("items") or []

    ctx = Context(
        ticker=ticker, horizon=horizon, as_of=as_of, name=name,
        metrics=metrics, rules=rules, news=news, fund=fund, sec=sec,
        social=social, macro=macro, prices=price_items,
        sources={
            "prices": _status(prices_result),
            "news": _status(news_result),
            "fmp": _status(fmp_result),
            "sec": _status(sec_result),
            "social": _status(social_result),
            "macro": _status(macro_result),
        },
    )
    if rules:
        ctx.sources["metrics"] = {"status": "ok" if metrics else "unavailable",
                                  "reason": None if metrics else "not enough price history"}
        ctx.sources["rules"] = {"status": "ok", "reason": None}
    else:
        ctx.sources["metrics"] = {"status": "ok" if metrics else "unavailable",
                                  "reason": None if metrics else "not enough price history"}
        ctx.sources["rules"] = _status(rules_result)

    _index_evidence(ctx)
    return ctx


def _add(ctx: Context, evidence_id: str, kind: str, label: str, value: str | None = None,
         url: str | None = None, published_at: str | None = None,
         sentiment: str | None = None) -> None:
    entry = {"kind": kind, "label": label}
    if value is not None:
        entry["value"] = value
    if url:
        entry["url"] = url
    if published_at:
        entry["published_at"] = published_at
    if sentiment:
        entry["sentiment"] = sentiment
    ctx.evidence[evidence_id] = entry


def _index_evidence(ctx: Context) -> None:
    for name, value in ctx.metrics.items():
        if name.startswith("_"):
            continue
        _add(ctx, f"metric:{name}", "metric", sources.METRIC_LABELS.get(name, name),
             sources.metric_display(name, value))
    if ctx.rules:
        for key in ("entry", "score"):  # stop/target are unvalidated guesses: the AI never sees them
            value = ctx.rules.get(key)
            if value is not None:
                _add(ctx, f"metric:{key}", "metric", f"Rule {key}", _fmt_number(value))
        for index, reason in enumerate(ctx.rules.get("reasons") or []):
            _add(ctx, f"rule:{index}", "rule", str(reason))
    for item in ctx.news:
        _add(ctx, f"news:{item['id']}", "news", item.get("title") or "Headline",
             item.get("source"), item.get("url"), item.get("published_at"), item.get("sentiment"))
    for field, item in ctx.fund.items():
        _add(ctx, f"fund:{field}", "fund", item.get("label", field), _fmt_number(item.get("value")))
    for item in ctx.sec:
        _add(ctx, f"sec:{item['concept']}:{item['period_end']}", "sec",
             f"{item.get('label')} ({item.get('period_end')})", _fmt_number(item.get("value")))
    for item in ctx.social:
        _add(ctx, item["id"], "social", item.get("title") or "Post",
             item.get("body") or None, item.get("url"), item.get("published_at"), item.get("sentiment"))
    for item in ctx.macro:
        _add(ctx, f"macro:{item['series']}", "macro", item.get("label", item["series"]),
             _fmt_number(item.get("value")) + (f" ({item['date']})" if item.get("date") else ""))


# ---------------------------------------------------------------------------
# Text blocks
# ---------------------------------------------------------------------------

def metric_lines(ctx: Context) -> list[str]:
    return [f"- {sources.METRIC_LABELS.get(k, k)}: {sources.metric_display(k, v)} (metric:{k})"
            for k, v in ctx.metrics.items() if not k.startswith("_")]


def rule_lines(ctx: Context) -> list[str]:
    if not ctx.rules:
        return ["(No rule-based recommendation was available.)"]
    r = ctx.rules
    lines = [f"- Rule entry: {_fmt_number(r.get('entry'))} (metric:entry)",
             f"- Rule score: {_fmt_number(r.get('score'))} (metric:score)"]
    for index, reason in enumerate(r.get("reasons") or []):
        lines.append(f"- Reason {index}: {reason} (rule:{index})")
    return lines


def price_lines(ctx: Context, limit: int = 120) -> list[str]:
    return [f"{row['date']}: {float(row['close']):.2f}" for row in ctx.prices[-limit:]]


def news_lines(ctx: Context) -> list[str]:
    return [f"[news:{n['id']}] {str(n.get('published_at') or '')[:10]} | {n.get('source')} | "
            f"{n.get('title')}" + (f" (sentiment: {n['sentiment']})" if n.get("sentiment") else "")
            for n in ctx.news]


def fund_lines(ctx: Context) -> list[str]:
    return [f"[fund:{field}] {item.get('label', field)}: {_fmt_number(item.get('value'))}"
            for field, item in ctx.fund.items()]


def sec_lines(ctx: Context) -> list[str]:
    return [f"[sec:{item['concept']}:{item['period_end']}] {item.get('label')} "
            f"({item.get('form')}, {item['period_end']}): {_fmt_number(item.get('value'))}"
            for item in ctx.sec]


def social_lines(ctx: Context) -> list[str]:
    return [f"[{item['id']}] {str(item.get('published_at') or '')[:10]} | {item.get('source')} | "
            f"{item.get('title')}" + (f" — {item['body']}" if item.get("body") else "")
            + (f" (score {item['score']})" if item.get("score") is not None else "")
            for item in ctx.social]


def macro_lines(ctx: Context) -> list[str]:
    return [f"[macro:{item['series']}] {item.get('label', item['series'])}: "
            f"{_fmt_number(item.get('value'))}" + (f" ({item['date']})" if item.get("date") else "")
            for item in ctx.macro]


def section(title: str, lines: list[str], empty: str = "(No data available for this section.)") -> str:
    return f"{title}:\n" + ("\n".join(lines) if lines else empty)


def market_text(ctx: Context) -> str:
    return "\n\n".join([
        section("Metrics", metric_lines(ctx)),
        section("Rule-based idea (read-only; never change these numbers)", rule_lines(ctx)),
        section("Recent closes", price_lines(ctx)),
        section("Macro", macro_lines(ctx)),
    ])


def news_text(ctx: Context) -> str:
    return section("News headlines", news_lines(ctx))


def fundamentals_text(ctx: Context) -> str:
    return "\n\n".join([section("Company fundamentals (Yahoo Finance ratios, last four quarters, insider activity)", fund_lines(ctx)),
                        section("SEC filings", sec_lines(ctx))])


def social_text(ctx: Context) -> str:
    return section("Social posts", social_lines(ctx))


def all_data_text(ctx: Context) -> str:
    return "\n\n".join([market_text(ctx), news_text(ctx), fundamentals_text(ctx), social_text(ctx)])


def analyst_report(role: str, output: dict | None) -> str:
    if not output:
        return f"agent:{role} — (No {role} report in this run; it is not available.)"
    if role in ("market", "news", "fundamentals", "social"):
        points = "; ".join(
            f"{p.get('text')} [{' '.join(p.get('evidence') or [])}]" for p in output.get("points") or [])
        gaps = "; ".join(output.get("data_gaps") or [])
        return (f"agent:{role} — signal={output.get('signal')}; {output.get('summary')} "
                f"Points: {points or '(none)'}. Data gaps: {gaps or '(none)'}.")
    return f"agent:{role} — {json.dumps(output, ensure_ascii=False)}"


def analysts_block(outputs: dict) -> str:
    sections = [analyst_report(role, outputs.get(role)) for role in ("market", "news", "fundamentals", "social")]
    return section("Analyst reports (earlier agents)", sections)


def debate_block(bull_points: list, bear_points: list) -> str:
    lines = []
    for role, points in (("bull", bull_points), ("bear", bear_points)):
        for point in points:
            lines.append(f"agent:{role} — {point['text']} [{' '.join(point.get('evidence') or [])}]")
    return section("Debate so far", lines)


def prior_risk_block(outputs: dict) -> str:
    lines = []
    for role in ("aggressive", "conservative", "neutral"):
        output = outputs.get(role)
        if output:
            lines.append(f"agent:{role} — {output.get('view')} "
                         f"(position {output.get('suggested_position_pct')}%) "
                         f"[{' '.join(output.get('evidence') or [])}]")
    return section("Earlier risk views", lines)


def memory_block(ctx: Context) -> str:
    if not ctx.memory:
        return "Memory:\n(No settled past decision for this ticker or cross-ticker lessons.)"
    lines = []
    for item in ctx.memory:
        line = (f"[memory:{item['id']}] {item['as_of']} {item['ticker']} {item['rating']} "
                f"return={item.get('return_pct')} benchmark={item.get('benchmark_return_pct')} "
                f"alpha={item.get('alpha_pct')}")
        if item.get("reflection"):
            line += f" | lesson: {item['reflection']}"
        lines.append(line)
    return section("Memory (settled past decisions)", lines)
