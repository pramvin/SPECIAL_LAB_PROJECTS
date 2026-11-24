"""Builds the evidence context for the three analysts: prices and levels, headlines, social posts."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from . import config, sources

SWING_BARS = 60   # how far back swing highs and lows are searched
SWING_SIDE = 2    # a swing low/high beats this many bars on each side
LEVELS_PER_SIDE = 4


@dataclass
class Context:
    ticker: str
    horizon: str
    as_of: str
    name: str = ""
    sources: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    levels: dict = field(default_factory=lambda: {"support": [], "resistance": []})
    news: list = field(default_factory=list)       # every non-noise headline of the last week
    social: list = field(default_factory=list)
    prices: list = field(default_factory=list)
    evidence: dict = field(default_factory=dict)


def _status(result: dict) -> dict:
    return {"status": result.get("status", "unavailable"),
            "reason": sources.redact_reason(result.get("reason"))}


def _call(fn, *args, **kwargs) -> dict:
    try:
        result = fn(*args, **kwargs)
        if not isinstance(result, dict) or "status" not in result:
            raise ValueError("bad source result")
        return result
    except Exception as exc:  # noqa: BLE001 - one source never stops the analysis
        return {"status": "unavailable", "reason": f"{type(exc).__name__}", "items": []}


def price_levels(prices: list[dict], metrics: dict) -> dict:
    """Support and resistance prices the code can stand behind, nearest to the last close first.

    Sources: the lowest low / highest high of 20 days, swing lows and highs of the last 60 bars,
    the 50/200-day averages and the Bollinger bands. The model may only pick among these.
    """
    if not prices or "close" not in metrics:
        return {"support": [], "resistance": []}
    close = round(float(metrics["close"]), 2)
    recent = prices[-SWING_BARS:]
    lows = [float(r["low"]) for r in recent]
    highs = [float(r["high"]) for r in recent]
    candidates = [
        (min(lows[-20:]), "20-day low"), (max(highs[-20:]), "20-day high"),
        (metrics.get("sma50"), "50-day average"), (metrics.get("sma200"), "200-day average"),
        (metrics.get("boll_lb"), "lower Bollinger band"), (metrics.get("boll_ub"), "upper Bollinger band"),
    ]
    for i in range(SWING_SIDE, len(recent) - SWING_SIDE):
        if lows[i] == min(lows[i - SWING_SIDE:i + SWING_SIDE + 1]):
            candidates.append((lows[i], "recent swing low"))
        if highs[i] == max(highs[i - SWING_SIDE:i + SWING_SIDE + 1]):
            candidates.append((highs[i], "recent swing high"))
    support: dict[float, str] = {}
    resistance: dict[float, str] = {}
    for value, label in candidates:
        if value is None:
            continue
        price = round(float(value), 2)
        if price < close:
            support.setdefault(price, label)
        elif price > close:
            resistance.setdefault(price, label)

    def nearest(found: dict[float, str]) -> list[dict]:
        keep = sorted(found, key=lambda p: abs(p - close))[:LEVELS_PER_SIDE]
        return [{"price": p, "label": found[p]} for p in keep]

    return {"support": nearest(support), "resistance": nearest(resistance)}


def lookup_name(conn, ticker: str) -> str:
    for table in ("recommendations", "universe"):
        try:
            row = conn.execute(f"SELECT name FROM {table} WHERE ticker = ? LIMIT 1", (ticker,)).fetchone()
        except Exception:  # noqa: BLE001 - a missing table just means no name
            continue
        if row:
            return row[0]
    return ""


def collect(conn, ticker: str, horizon: str, fetchers: dict | None = None) -> Context:
    """Read prices, headlines and social posts. `fetchers` may replace `prices`, `news`, `social`."""
    fetchers = fetchers or {}
    prices_result = _call(fetchers.get("prices") or sources.fetch_prices, conn, ticker)
    price_items = prices_result.get("items") or []
    as_of = price_items[-1]["date"] if price_items else datetime.now(timezone.utc).date().isoformat()
    news_result = _call(fetchers.get("news") or sources.fetch_news, conn, ticker)
    social_result = _call(fetchers.get("social") or sources.fetch_social, conn, ticker, as_of=as_of)

    metrics = sources.compute_metrics(price_items) if price_items else {}
    ctx = Context(
        ticker=ticker, horizon=horizon, as_of=as_of, name=lookup_name(conn, ticker), metrics=metrics,
        levels=price_levels(price_items, metrics),
        news=news_result.get("items") or [], social=social_result.get("items") or [],
        prices=price_items,
        sources={
            "prices": _status(prices_result),
            "metrics": {"status": "ok" if metrics else "unavailable",
                        "reason": None if metrics else "not enough price history"},
            "news": _status(news_result),
            "social": _status(social_result),
        },
    )
    _index_evidence(ctx)
    return ctx


def shown_news(ctx: Context) -> list[dict]:
    """The newest headlines the news analyst reads (all of them still count in the gauge)."""
    return ctx.news[:config.MAX_NEWS]


def _index_evidence(ctx: Context) -> None:
    for name, value in ctx.metrics.items():
        if not name.startswith("_"):
            ctx.evidence[f"metric:{name}"] = {"label": sources.METRIC_LABELS.get(name, name),
                                              "value": sources.metric_display(name, value)}
    for item in shown_news(ctx):
        ctx.evidence[f"news:{item['id']}"] = {"label": item.get("title") or "Headline"}
    for item in ctx.social:
        ctx.evidence[item["id"]] = {"label": item.get("title") or "Post"}


def evidence_ids(ctx: Context, prefix: str) -> set[str]:
    return {key for key in ctx.evidence if key.startswith(prefix)}


# ---------------------------------------------------------------------------
# Text blocks (what each analyst reads)
# ---------------------------------------------------------------------------

def _section(title: str, lines: list[str], empty: str = "(No data available for this section.)") -> str:
    return f"{title}:\n" + ("\n".join(lines) if lines else empty)


def _level_lines(levels: list[dict]) -> list[str]:
    return [f"- {item['price']:.2f} ({item['label']})" for item in levels]


def market_text(ctx: Context) -> str:
    metrics = [f"- {sources.METRIC_LABELS.get(k, k)}: {sources.metric_display(k, v)} (metric:{k})"
               for k, v in ctx.metrics.items() if not k.startswith("_")]
    closes = [f"{row['date']}: {float(row['close']):.2f}" for row in ctx.prices[-30:]]
    return "\n\n".join([
        _section("Metrics", metrics),
        _section("Recent closes", closes),
        _section("Support candidates (the only prices you may pick as support)",
                 _level_lines(ctx.levels["support"]), "(none computed)"),
        _section("Resistance candidates (the only prices you may pick as resistance)",
                 _level_lines(ctx.levels["resistance"]), "(none computed)"),
    ])


def news_text(ctx: Context) -> str:
    lines = [f"[news:{n['id']}] {str(n.get('published_at') or '')[:10]} | {n.get('source')} | {n.get('title')}"
             for n in shown_news(ctx)]
    return _section("News headlines of the last 7 days", lines)


def social_text(ctx: Context) -> str:
    lines = [f"[{item['id']}] {item.get('source')} | {item.get('title')}"
             + (f" - {item['body']}" if item.get("body") else "")
             + (f" (user tag: {item['sentiment']})" if item.get("sentiment") else "")
             for item in ctx.social]
    return _section("Social posts", lines)
