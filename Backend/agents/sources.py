"""Evidence sources for the click analysis (prices, indicators, news, social).

Every function returns `{"status": "ok"|"unavailable"|"skipped", "reason": str|None,
"items": ...}` and never raises into the analysis. A failed source is reported as
unavailable, never filled in by the model.
"""
from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

from app.dbcompat import table_names

from . import config
from .llm_client import scrub

USER_AGENT = "PlanWise-AI/1.0"

METRIC_LABELS = {
    "close": "Last close",
    "r5": "5-day return",
    "r20": "20-day return",
    "r60": "60-day return",
    "rsi14": "RSI 14",
    "macd": "MACD vs price",
    "ma50_gap": "Price vs 50-day average",
    "ma200_gap": "Price vs 200-day average",
    "vol20": "20-day volatility",
    "atr14_pct": "ATR 14 as % of price",
    "volx": "Volume vs 20-day average",
    "high_52w_gap": "Price vs 52-week high",
    # Full indicator set of the TradingAgents market analyst (price units, not percent)
    "ema10": "10-day EMA (price)",
    "sma50": "50-day SMA (price)",
    "sma200": "200-day SMA (price)",
    "macd_line": "MACD line (price units)",
    "macd_signal": "MACD signal line (price units)",
    "macd_hist": "MACD histogram (price units)",
    "boll": "Bollinger middle, 20-day SMA (price)",
    "boll_ub": "Bollinger upper band (price)",
    "boll_lb": "Bollinger lower band (price)",
    "vwma20": "20-day volume-weighted average (price)",
    "atr14": "ATR 14 (price units)",
}
PERCENT_METRICS = {"r5", "r20", "r60", "macd", "ma50_gap", "ma200_gap", "vol20",
                   "atr14_pct", "high_52w_gap"}


def _rowdict(row) -> dict:
    return {key: row[key] for key in row.keys()}


def _today(as_of: str | None = None) -> str:
    return as_of or datetime.now(timezone.utc).date().isoformat()


def cache_get(conn, source: str, key: str, day: str):
    row = conn.execute(
        "SELECT payload_json FROM source_cache WHERE source = ? AND key = ? AND fetched_on = ?",
        (source, key, day),
    ).fetchone()
    if not row:
        return None
    try:
        return json.loads(row[0])
    except ValueError:
        return None


def cache_put(conn, source: str, key: str, day: str, payload) -> None:
    with conn:
        conn.execute(
            "INSERT INTO source_cache (source, key, fetched_on, payload_json) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(source, key, fetched_on) DO UPDATE SET payload_json = excluded.payload_json",
            (source, key, day, json.dumps(payload, default=str)),
        )


# ---------------------------------------------------------------------------
# Prices and metrics
# ---------------------------------------------------------------------------

def fetch_prices(conn, ticker: str, as_of: str | None = None) -> dict:
    try:
        rows = conn.execute(
            "SELECT date, open, high, low, close, volume FROM prices WHERE ticker = ? "
            "ORDER BY date DESC LIMIT 260", (ticker,),
        ).fetchall()
        if not rows:
            return {"status": "unavailable", "reason": "no price rows for this ticker", "items": []}
        return {"status": "ok", "reason": None, "items": [_rowdict(r) for r in reversed(rows)]}
    except Exception as exc:  # noqa: BLE001 - source failures never reach the graph
        return {"status": "unavailable", "reason": f"prices read failed: {type(exc).__name__}", "items": []}


def compute_metrics(rows: list[dict]) -> dict:
    """Indicators from the ticker's own price history (raw values, not market-relative)."""
    if len(rows) < 20:
        return {}
    close = pd.Series([float(r["close"]) for r in rows], dtype="float64")
    high = pd.Series([float(r["high"]) for r in rows], dtype="float64")
    low = pd.Series([float(r["low"]) for r in rows], dtype="float64")
    volume = pd.Series([float(r["volume"]) for r in rows], dtype="float64")
    ret = close.pct_change(fill_method=None)
    out: dict[str, float] = {"close": float(close.iloc[-1])}
    for name, window in (("r5", 5), ("r20", 20), ("r60", 60)):
        if len(close) > window:
            out[name] = float(close.iloc[-1] / close.iloc[-1 - window] - 1)
    up = ret.clip(lower=0).rolling(14).mean()
    down = (-ret.clip(upper=0)).rolling(14).mean()
    rsi = 100 - 100 / (1 + up / down)
    if pd.notna(rsi.iloc[-1]):
        out["rsi14"] = float(rsi.iloc[-1])
    out["macd"] = float((close.ewm(span=12).mean() - close.ewm(span=26).mean()).iloc[-1] / close.iloc[-1])
    if len(close) >= 50:
        out["ma50_gap"] = float(close.iloc[-1] / close.iloc[-50:].mean() - 1)
    if len(close) >= 200:
        out["ma200_gap"] = float(close.iloc[-1] / close.iloc[-200:].mean() - 1)
    if ret.notna().sum() >= 20:
        out["vol20"] = float(ret.iloc[-20:].std())
    prev = close.shift(1)
    tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    atr = float(tr.iloc[-14:].mean())
    if atr > 0:
        out["atr14_pct"] = atr / float(close.iloc[-1])  # a fraction like the other percent metrics (display multiplies by 100)
        out["_atr"] = atr
    window = min(252, len(volume))
    if window >= 20 and volume.iloc[-window:].mean() > 0:
        out["volx"] = float(volume.iloc[-1] / volume.iloc[-20:].mean())
    high_window = min(252, len(high))
    if high_window >= 20:
        out["high_52w_gap"] = float(close.iloc[-1] / high.iloc[-high_window:].max() - 1)
    # Indicators of the TradingAgents market analyst's menu (stockstats definitions).
    ema10 = close.ewm(span=10, adjust=False).mean()
    macd_line = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    extra = {"ema10": ema10.iloc[-1], "macd_line": macd_line.iloc[-1], "macd_signal": macd_signal.iloc[-1],
             "macd_hist": macd_line.iloc[-1] - macd_signal.iloc[-1], "atr14": atr}
    if len(close) >= 50:
        extra["sma50"] = close.iloc[-50:].mean()
    if len(close) >= 200:
        extra["sma200"] = close.iloc[-200:].mean()
    mid, spread = close.iloc[-20:].mean(), close.iloc[-20:].std()
    extra.update({"boll": mid, "boll_ub": mid + 2 * spread, "boll_lb": mid - 2 * spread})
    traded = volume.iloc[-20:].sum()
    if traded > 0:
        extra["vwma20"] = (close.iloc[-20:] * volume.iloc[-20:]).sum() / traded
    for key, value in extra.items():
        if pd.notna(value) and (key != "atr14" or value > 0):
            out[key] = float(value)
    return {key: round(value, 4) for key, value in out.items()}


def metric_display(name: str, value: float) -> str:
    if name == "close":
        return f"{value:.2f}"
    if name in PERCENT_METRICS:
        return f"{value * 100:.2f}%"
    if name == "rsi14":
        return f"{value:.2f}"
    return f"{value:.2f}"


# ---------------------------------------------------------------------------
# News and social (Reddit OAuth + StockTwits)
# ---------------------------------------------------------------------------

def fetch_news(conn, ticker: str, limit: int = 100) -> dict:
    """Non-noise headlines of the last `config.NEWS_DAYS` days, newest first, with the local label."""
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=config.NEWS_DAYS)).isoformat()
        if "news_scores" in table_names(conn):
            rows = conn.execute(
                "SELECT n.id, n.title, n.source, n.url, n.published_at, "
                "(SELECT s.sentiment FROM news_scores s WHERE s.news_id = n.id "
                " ORDER BY s.scored_at DESC LIMIT 1) AS sentiment "
                "FROM news_items n WHERE n.ticker = ? AND n.rule_noise = 0 AND n.published_at >= ? "
                "ORDER BY n.published_at DESC LIMIT ?",
                (ticker, cutoff, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, title, source, url, published_at, NULL AS sentiment "
                "FROM news_items WHERE ticker = ? AND rule_noise = 0 AND published_at >= ? "
                "ORDER BY published_at DESC LIMIT ?",
                (ticker, cutoff, limit),
            ).fetchall()
        return {"status": "ok", "reason": None, "items": [_rowdict(r) for r in rows]}
    except Exception as exc:  # noqa: BLE001
        return {"status": "unavailable", "reason": f"news read failed: {type(exc).__name__}", "items": []}


def _reddit_token(client_id: str, client_secret: str) -> str | None:
    try:
        response = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            headers={"User-Agent": USER_AGENT},
            timeout=20,
        )
        if response.status_code != 200:
            return None
        return response.json().get("access_token")
    except (requests.RequestException, ValueError):
        return None


def _strip_html(text: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", text or "")).split())


def _fetch_reddit(ticker: str, name: str, token: str) -> list[dict]:
    items = []
    query = f'${ticker} OR "{name}"'
    for sub in ("stocks", "investing", "wallstreetbets"):
        response = requests.get(
            f"https://oauth.reddit.com/r/{sub}/search",
            params={"q": query, "restrict_sr": "on", "sort": "new", "t": "week", "limit": 10},
            headers={"Authorization": f"bearer {token}", "User-Agent": USER_AGENT},
            timeout=20,
        )
        if response.status_code != 200:
            continue
        for child in (response.json().get("data") or {}).get("children", []):
            data = child.get("data") or {}
            items.append({
                "id": f"social:reddit:{data.get('id')}",
                "source": "reddit",
                "subreddit": sub,
                "title": (data.get("title") or "")[:280],
                "body": _strip_html(data.get("selftext") or "")[:280],
                "score": data.get("score"),
                "published_at": datetime.fromtimestamp(
                    float(data.get("created_utc") or 0), tz=timezone.utc).isoformat(),
                "url": "https://www.reddit.com" + (data.get("permalink") or ""),
            })
    return items


def _fetch_stocktwits(ticker: str) -> tuple[list[dict], str | None]:
    try:
        response = requests.get(
            f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json",
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=20,
        )
        if response.status_code == 403:
            return [], "StockTwits returned 403"
        if response.status_code != 200:
            return [], f"StockTwits returned {response.status_code}"
        messages = (response.json() or {}).get("messages") or []
    except (requests.RequestException, ValueError) as exc:
        return [], f"StockTwits failed ({type(exc).__name__})"
    items = []
    for message in messages:
        sentiment = ((message.get("entities") or {}).get("sentiment") or {}).get("basic")
        items.append({
            "id": f"social:stocktwits:{message.get('id')}",
            "source": "stocktwits",
            "title": (message.get("body") or "")[:280],
            "body": "",
            "score": message.get("likes", {}).get("total") if isinstance(message.get("likes"), dict) else None,
            "sentiment": sentiment,
            "published_at": message.get("created_at"),
            "url": f"https://stocktwits.com/symbol/{ticker}",
        })
    return items, None


def fetch_social(conn, ticker: str, name: str | None = None, as_of: str | None = None) -> dict:
    day = _today(as_of)
    cached = cache_get(conn, "social", ticker, day)
    if cached is not None:
        return cached
    client_id = os.environ.get("REDDIT_CLIENT_ID", "").strip()
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET", "").strip()
    items: list[dict] = []
    reasons: list[str] = []
    reddit_status = "skipped"
    if client_id and client_secret:
        token = _reddit_token(client_id, client_secret)
        if token:
            try:
                items.extend(_fetch_reddit(ticker, name or ticker, token))
                reddit_status = "ok"
            except (requests.RequestException, ValueError) as exc:
                reasons.append(f"Reddit failed ({type(exc).__name__})")
                reddit_status = "unavailable"
        else:
            reasons.append("Reddit OAuth failed")
            reddit_status = "unavailable"
    else:
        reasons.append("Reddit credentials are not set")
    twits, twits_error = _fetch_stocktwits(ticker)
    items.extend(twits)
    if twits_error:
        reasons.append(twits_error)
    items = items[: config.MAX_SOCIAL]
    if items:
        result = {"status": "ok", "reason": None, "items": items}
    elif reddit_status == "skipped":
        result = {"status": "skipped", "reason": "; ".join(reasons), "items": []}
    else:
        result = {"status": "unavailable", "reason": "; ".join(reasons), "items": []}
    cache_put(conn, "social", ticker, day, result)
    return result


def redact_reason(reason: str | None) -> str | None:
    """Defence in depth: reasons are built from status codes/type names, never headers."""
    return scrub(reason or "", os.environ.get("AGENT_LLM_API_KEY")) or None
