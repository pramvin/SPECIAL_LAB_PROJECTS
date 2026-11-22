"""Evidence sources for the agent review.

Every function returns `{"status": "ok"|"unavailable"|"skipped", "reason": str|None,
"items": ...}` and never raises into the graph. A failed source is reported as
unavailable, never filled in by the model.
"""
from __future__ import annotations

import html
import json
import os
import re
import time
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
import requests

from app.dbcompat import table_names

from . import config
from .llm_client import scrub

SEC_TICKERS = "https://www.sec.gov/files/company_tickers.json"
SEC_FACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
FRED_BASE = "https://api.stlouisfed.org/fred"
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


def spy_closes(conn, as_of: str | None = None) -> list[dict]:
    """SPY daily closes, cached per day (SPY is not in our `prices` table)."""
    day = _today(as_of)
    cached = cache_get(conn, "spy", "SPY", day)
    if cached is not None:
        return cached
    import yfinance as yf  # imported only when needed; tests seed the cache instead

    raw = yf.download("SPY", period="2y", interval="1d", progress=False, auto_adjust=True)
    closes = []
    if raw is not None and not raw.empty:
        series = raw["Close"]
        if hasattr(series, "columns"):
            series = series.iloc[:, 0]
        for stamp, value in series.dropna().items():
            closes.append({"date": stamp.date().isoformat(), "close": round(float(value), 4)})
    cache_put(conn, "spy", "SPY", day, closes)
    return closes


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
# Recommendations (the rule/ML idea) and news
# ---------------------------------------------------------------------------

def fetch_rules(conn, ticker: str, horizon: str, as_of: str | None = None) -> dict:
    try:
        row = conn.execute(
            "SELECT * FROM recommendations WHERE ticker = ? AND horizon = ? ORDER BY id DESC LIMIT 1",
            (ticker, horizon),
        ).fetchone()
    except Exception as exc:  # noqa: BLE001
        return {"status": "unavailable", "reason": f"recommendations read failed: {type(exc).__name__}", "items": None}
    if not row:
        return {"status": "unavailable", "reason": "no recommendation row for this horizon", "items": None}
    try:
        reasons = json.loads(row["reasons"]) if row["reasons"] else []
    except ValueError:
        reasons = []
    return {
        "status": "ok",
        "reason": None,
        "items": {
            "entry": row["entry"], "stop": row["stop"], "target": row["target"],
            "score": row["score"], "reasons": reasons,
            "bigmove_p": row["bigmove_p"] if "bigmove_p" in row.keys() else None,
            "atr_pct": row["atr_pct"] if "atr_pct" in row.keys() else None,
        },
    }


def fetch_news(conn, ticker: str, as_of: str | None = None, name: str | None = None) -> dict:
    try:
        cutoff = (date.fromisoformat(_today(as_of)) - timedelta(days=14)).isoformat()
        tables = table_names(conn)
        if "news_scores" in tables:
            rows = conn.execute(
                "SELECT n.id, n.title, n.source, n.url, n.published_at, "
                "(SELECT s.sentiment FROM news_scores s WHERE s.news_id = n.id "
                " ORDER BY s.scored_at DESC LIMIT 1) AS sentiment "
                "FROM news_items n WHERE n.ticker = ? AND n.rule_noise = 0 AND n.published_at >= ? "
                "ORDER BY n.published_at DESC LIMIT ?",
                (ticker, cutoff, config.MAX_NEWS),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, title, source, url, published_at, NULL AS sentiment "
                "FROM news_items WHERE ticker = ? AND rule_noise = 0 AND published_at >= ? "
                "ORDER BY published_at DESC LIMIT ?",
                (ticker, cutoff, config.MAX_NEWS),
            ).fetchall()
        return {"status": "ok", "reason": None, "items": [_rowdict(r) for r in rows]}
    except Exception as exc:  # noqa: BLE001
        return {"status": "unavailable", "reason": f"news read failed: {type(exc).__name__}", "items": []}


# ---------------------------------------------------------------------------
# Yahoo Finance fundamentals (free, no key): what the TradingAgents fundamentals analyst gets from its
# get_fundamentals / get_balance_sheet / get_cashflow / get_income_statement / get_insider_transactions tools
# ---------------------------------------------------------------------------

YF_INFO = {  # field: (label, yfinance info key, scale)
    "pe_ttm": ("P/E (TTM)", "trailingPE", 1),
    "pe_forward": ("P/E (forward)", "forwardPE", 1),
    "peg": ("PEG ratio", "trailingPegRatio", 1),
    "ps_ttm": ("P/S (TTM)", "priceToSalesTrailing12Months", 1),
    "pb": ("P/B", "priceToBook", 1),
    "ev_ebitda": ("EV/EBITDA", "enterpriseToEbitda", 1),
    "gross_margin": ("Gross margin (%)", "grossMargins", 100),
    "op_margin": ("Operating margin (%)", "operatingMargins", 100),
    "net_margin": ("Net margin (%)", "profitMargins", 100),
    "roe": ("Return on equity (%)", "returnOnEquity", 100),
    "roa": ("Return on assets (%)", "returnOnAssets", 100),
    "debt_equity": ("Debt/equity (%)", "debtToEquity", 1),
    "current_ratio": ("Current ratio", "currentRatio", 1),
    "revenue_growth_yoy": ("Revenue growth YoY (%)", "revenueGrowth", 100),
    "eps_growth_yoy": ("Earnings growth YoY (%)", "earningsGrowth", 100),
    "eps_ttm": ("EPS (TTM, $)", "trailingEps", 1),
    "eps_forward": ("EPS (forward, $)", "forwardEps", 1),
    "market_cap": ("Market cap ($B)", "marketCap", 1e-9),
    "fcf": ("Free cash flow ($B)", "freeCashflow", 1e-9),
    "dividend_yield": ("Dividend yield (%)", "dividendYield", 1),
    "beta": ("Beta", "beta", 1),
    "short_float": ("Short interest, % of float", "shortPercentOfFloat", 100),
    "analyst_target": ("Analyst mean price target ($)", "targetMeanPrice", 1),
    "analyst_rating": ("Analyst mean rating (1 strong buy to 5 sell)", "recommendationMean", 1),
    "analyst_count": ("Number of analysts", "numberOfAnalystOpinions", 1),
}
YF_STATEMENT_LINES = {  # field: (label, frame, row name)
    "revenue": ("Revenue", "income", "Total Revenue"),
    "gross_profit": ("Gross profit", "income", "Gross Profit"),
    "op_income": ("Operating income", "income", "Operating Income"),
    "net_income": ("Net income", "income", "Net Income"),
    "op_cash_flow": ("Operating cash flow", "cash", "Operating Cash Flow"),
    "free_cash_flow": ("Free cash flow", "cash", "Free Cash Flow"),
}
YF_BALANCE_LINES = {
    "total_debt": ("Total debt", "Total Debt"),
    "cash": ("Cash and equivalents", "Cash And Cash Equivalents"),
    "equity": ("Stockholders' equity", "Stockholders Equity"),
}


def _number(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def _yf_statement_items(ticker_obj) -> dict:
    """Last 4 quarters of revenue, profit and cash flow (USD millions) plus the latest balance sheet."""
    items: dict[str, dict] = {}
    frames = {"income": ticker_obj.quarterly_income_stmt, "cash": ticker_obj.quarterly_cashflow}
    for field, (label, frame_name, row) in YF_STATEMENT_LINES.items():
        frame = frames[frame_name]
        if frame is None or frame.empty or row not in frame.index:
            continue
        series = frame.loc[row].dropna()
        for lag, (column, value) in enumerate(list(series.items())[:4]):
            number = _number(value)
            if number is not None:
                items[f"{field}_q{lag}"] = {"label": f"{label}, quarter ending {str(column)[:10]} ($M)",
                                            "value": round(number / 1e6, 1)}
    balance = ticker_obj.quarterly_balance_sheet
    if balance is not None and not balance.empty:
        for field, (label, row) in YF_BALANCE_LINES.items():
            if row in balance.index:
                series = balance.loc[row].dropna()
                number = _number(series.iloc[0]) if len(series) else None
                if number is not None:
                    items[field] = {"label": f"{label}, latest quarter ($M)", "value": round(number / 1e6, 1)}
    return items


def _yf_insider_items(ticker_obj, as_of: str) -> dict:
    """Open-market insider buys and sales over the last 6 months (counts and dollar value)."""
    frame = ticker_obj.insider_transactions
    if frame is None or frame.empty or "Start Date" not in frame.columns:
        return {}
    cutoff = pd.Timestamp(as_of) - pd.Timedelta(days=183)
    dates = pd.to_datetime(frame["Start Date"], errors="coerce")
    recent = frame[dates >= cutoff]
    text = recent["Text"].fillna("").str.lower() if "Text" in recent.columns else pd.Series("", index=recent.index)
    buys, sells = recent[text.str.contains("purchase")], recent[text.str.contains("sale")]
    items = {
        "insider_buys_6m": {"label": "Insider purchases, last 6 months (count)", "value": int(len(buys))},
        "insider_sells_6m": {"label": "Insider sales, last 6 months (count)", "value": int(len(sells))},
    }
    for field, label, rows in (("insider_buy_value_6m", "Insider purchases, last 6 months ($M)", buys),
                               ("insider_sell_value_6m", "Insider sales, last 6 months ($M)", sells)):
        total = pd.to_numeric(rows.get("Value"), errors="coerce").sum() if "Value" in rows.columns else 0
        if _number(total):
            items[field] = {"label": label, "value": round(float(total) / 1e6, 2)}
    return items


def fetch_yf_fundamentals(conn, ticker: str, as_of: str | None = None) -> dict:
    day = _today(as_of)
    cached = cache_get(conn, "yf_fund", ticker, day)
    if cached is not None:
        return {"status": "ok", "reason": None, "items": cached}
    try:
        import yfinance as yf

        handle = yf.Ticker(ticker)
        info = handle.info or {}
        items: dict[str, dict] = {}
        for field, (label, key, scale) in YF_INFO.items():
            number = _number(info.get(key))
            if number is not None:
                items[field] = {"label": label, "value": round(number * scale, 2)}
        for part in (lambda: _yf_statement_items(handle), lambda: _yf_insider_items(handle, day)):
            try:
                items.update(part())
            except Exception:  # noqa: BLE001 - one missing statement never drops the ratios
                continue
    except Exception as exc:  # noqa: BLE001 - network/library failure is reported, never filled in
        return {"status": "unavailable", "reason": f"Yahoo fundamentals failed ({type(exc).__name__})", "items": {}}
    if not items:
        return {"status": "unavailable", "reason": "Yahoo returned no fundamentals", "items": {}}
    cache_put(conn, "yf_fund", ticker, day, items)
    return {"status": "ok", "reason": None, "items": items}


def fetch_fundamentals(conn, ticker: str, name: str | None = None, as_of: str | None = None) -> dict:
    """Yahoo ratios, quarterly statements and insider activity (the source key stays "fmp" in stored reviews)."""
    return fetch_yf_fundamentals(conn, ticker, as_of)


# ---------------------------------------------------------------------------
# SEC EDGAR
# ---------------------------------------------------------------------------

SEC_CONCEPTS = {
    "Revenues": ("Revenue", ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet")),
    "NetIncomeLoss": ("Net income", ("NetIncomeLoss",)),
    "EarningsPerShareDiluted": ("Diluted EPS", ("EarningsPerShareDiluted",)),
    "Assets": ("Total assets", ("Assets",)),
    "Liabilities": ("Total liabilities", ("Liabilities",)),
}


def _sec_headers() -> dict:
    return {"User-Agent": os.environ.get("SEC_EDGAR_USER_AGENT", "").strip(), "Accept-Encoding": "gzip, deflate"}


def _sec_json(url: str) -> dict:
    response = requests.get(url, headers=_sec_headers(), timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_sec(conn, ticker: str, as_of: str | None = None) -> dict:
    user_agent = os.environ.get("SEC_EDGAR_USER_AGENT", "").strip()
    if not user_agent:
        return {"status": "skipped", "reason": "SEC_EDGAR_USER_AGENT is not set", "items": []}
    day = _today(as_of)
    cached = cache_get(conn, "sec", ticker, day)
    if cached is not None:
        return {"status": "ok", "reason": None, "items": cached}
    try:
        table = cache_get(conn, "sec", "company_tickers", day)
        if table is None:
            table = _sec_json(SEC_TICKERS)
            cache_put(conn, "sec", "company_tickers", day, table)
        cik = None
        for entry in (table or {}).values():
            if str(entry.get("ticker", "")).upper() == ticker.upper():
                cik = f"{int(entry['cik_str']):010d}"
                break
        if not cik:
            return {"status": "unavailable", "reason": "not in SEC's US filer list", "items": []}
        time.sleep(0.12)  # SEC asks for <=10 requests/second
        facts = cache_get(conn, "sec", f"CIK{cik}", day)
        if facts is None:
            facts = _sec_json(SEC_FACTS.format(cik=cik))
            cache_put(conn, "sec", f"CIK{cik}", day, facts)
    except (requests.RequestException, ValueError, KeyError) as exc:
        return {"status": "unavailable", "reason": f"SEC EDGAR failed ({type(exc).__name__})", "items": []}
    us_gaap = (facts.get("facts") or {}).get("us-gaap") or {}
    today = _today(as_of)
    items = []
    for concept, (label, tags) in SEC_CONCEPTS.items():
        chosen = None
        for tag in tags:
            values = (us_gaap.get(tag) or {}).get("units", {})
            flat = [fact for unit_values in values.values() for fact in unit_values]
            flat = [f for f in flat if f.get("filed", "9999") <= today
                    and str(f.get("form", "")).startswith(("10-K", "10-Q"))]
            if flat:
                chosen = flat
                break
        if not chosen:
            continue
        latest = {}
        for fact in chosen:
            end = fact.get("end")
            if not end:
                continue
            if end not in latest or fact.get("filed", "") >= latest[end].get("filed", ""):
                latest[end] = fact
        for end in sorted(latest, reverse=True)[:4]:
            fact = latest[end]
            items.append({"concept": concept, "label": label, "value": fact.get("val"),
                          "period_end": end, "form": fact.get("form")})
    cache_put(conn, "sec", ticker, day, items)
    return {"status": "ok", "reason": None, "items": items}


# ---------------------------------------------------------------------------
# Social (Reddit OAuth + StockTwits)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Macro (FRED)
# ---------------------------------------------------------------------------

FRED_SERIES = {
    "FEDFUNDS": "Fed funds rate",
    "DGS10": "10-year Treasury yield",
    "CPIAUCSL": "CPI (YoY)",
    "UNRATE": "Unemployment rate",
}


def _fred_get(series: str, key: str, limit: int) -> list[dict]:
    response = requests.get(
        f"{FRED_BASE}/series/observations",
        params={"series_id": series, "api_key": key, "file_type": "json",
                "sort_order": "desc", "limit": limit},
        timeout=25,
    )
    response.raise_for_status()
    return (response.json() or {}).get("observations") or []


YF_MACRO = {  # market-based stand-ins used when there is no FRED key
    "VIX": ("^VIX", "VIX volatility index"),
    "US10Y": ("^TNX", "10-year Treasury yield (%)"),
    "US3M": ("^IRX", "3-month Treasury bill yield (%)"),
    "USD": ("DX-Y.NYB", "US dollar index"),
}


def fetch_yf_macro(conn, as_of: str | None = None) -> dict:
    day = _today(as_of)
    cached = cache_get(conn, "yf_macro", "macro", day)
    if cached is not None:
        return {"status": "ok", "reason": None, "items": cached}
    items = []
    try:
        import yfinance as yf

        for series, (symbol, label) in YF_MACRO.items():
            try:
                closes = yf.Ticker(symbol).history(period="1mo")["Close"].dropna()
            except Exception:  # noqa: BLE001
                continue
            if len(closes):
                items.append({"series": series, "label": label, "value": round(float(closes.iloc[-1]), 2),
                              "date": str(closes.index[-1])[:10]})
    except Exception as exc:  # noqa: BLE001
        return {"status": "unavailable", "reason": f"Yahoo macro failed ({type(exc).__name__})", "items": []}
    if not items:
        return {"status": "unavailable", "reason": "Yahoo returned no macro series", "items": []}
    cache_put(conn, "yf_macro", "macro", day, items)
    return {"status": "ok", "reason": None, "items": items}


def fetch_macro(conn, as_of: str | None = None) -> dict:
    key = os.environ.get("FRED_API_KEY", "").strip()
    if not key:
        return fetch_yf_macro(conn, as_of)
    day = _today(as_of)
    cached = cache_get(conn, "fred", "macro", day)
    if cached is not None:
        return {"status": "ok", "reason": None, "items": cached}
    items, errors = [], []
    for series, label in FRED_SERIES.items():
        try:
            observations = [o for o in _fred_get(series, key, 13) if o.get("value") not in (".", "", None)]
            if not observations:
                continue
            latest = observations[0]
            value = float(latest["value"])
            if series == "CPIAUCSL" and len(observations) >= 13:
                value = round((value / float(observations[12]["value"]) - 1) * 100, 2)
            items.append({"series": series, "label": label, "value": round(value, 2),
                          "date": latest.get("date")})
        except (requests.RequestException, ValueError, KeyError) as exc:
            errors.append(f"{series} ({type(exc).__name__})")
    if not items:
        return {"status": "unavailable", "reason": "FRED failed: " + ", ".join(errors), "items": []}
    cache_put(conn, "fred", "macro", day, items)
    return {"status": "ok", "reason": None, "items": items}


def redact_reason(reason: str | None) -> str | None:
    """Defence in depth: reasons are built from status codes/type names, never headers."""
    return scrub(reason or "", os.environ.get("AGENT_LLM_API_KEY")) or None
