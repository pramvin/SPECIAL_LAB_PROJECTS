"""Click analysis: the market, news and social analysts run in parallel and one result is stored.

`run_analysis` is the whole job for one ticker. It never raises: any failure ends in a stored
`error` row with a short message (no key, no URL with a secret).
"""
from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from . import config, context, llm_client, prompts, schema, validate

# The gateway allows 3 concurrent requests per key, so this caps LLM calls across every run.
LLM_SLOTS = threading.BoundedSemaphore(3)

NEWS_ITEMS_SHOWN = 10
SOCIAL_TEXT_CHARS = 280
SENTIMENTS = {"positive": "positive", "bullish": "positive", "negative": "negative",
              "bearish": "negative", "neutral": "neutral"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def make_llm(fake: bool = False):
    if fake:
        return llm_client.FakeLLM(auto=True)
    config.load_env()
    settings = config.llm_settings()
    if not settings["api_key"] or not settings["base_url"] or not settings["model"]:
        raise llm_client.LLMError("the model is not configured (AGENT_LLM_BASE_URL, _API_KEY, _MODEL)")
    return llm_client.OpenAICompatLLM(settings["base_url"], settings["api_key"], settings["model"])


def start_run(conn, ticker: str, horizon: str) -> int:
    """Insert a `running` row and return its id."""
    schema.ensure(conn)
    with conn:
        row = conn.execute(
            "INSERT INTO stock_analysis (ticker, horizon, status, started_at) "
            "VALUES (?, ?, 'running', ?) RETURNING id", (ticker, horizon, now_iso()),
        ).fetchone()
    return row[0]


def finish(conn, analysis_id: int, status: str, result: dict | None, error: str | None,
            model: str | None, tokens: int) -> None:
    with conn:
        conn.execute(
            "UPDATE stock_analysis SET status = ?, result_json = ?, error = ?, model = ?, tokens = ?, "
            "finished_at = ? WHERE id = ?",
            (status, json.dumps(result) if result is not None else None, error, model, tokens,
             now_iso(), analysis_id),
        )


def _log(conn, analysis_id: int, role: str, entry: dict) -> None:
    with conn:
        conn.execute(
            "INSERT INTO stock_analysis_messages (analysis_id, role, output_json, error, tokens_in, "
            "tokens_out, latency_ms, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (analysis_id, role, json.dumps(entry["data"]) if entry["data"] is not None else None,
             entry["error"], entry["tokens_in"], entry["tokens_out"], entry["latency_ms"], now_iso()),
        )


# ---------------------------------------------------------------------------
# One analyst call: retry once on an invalid answer, never touches the database
# ---------------------------------------------------------------------------

def call_role(llm, role: str, user: str, allowed: set[str], numbers: set[float],
              levels: dict | None = None, secret: str | None = None) -> dict:
    """Returns {"output": cleaned dict or None, "error": str or None, "logs": [...], "model": str}."""
    system = prompts.system(role)
    prompt = f"{user}\n\n{prompts.allowed_line(sorted(allowed))}"
    logs: list[dict] = []

    def entry(data, error, reply=None):
        reply = reply or {}
        return {"data": data, "error": error, "tokens_in": int(reply.get("tokens_in") or 0),
                "tokens_out": int(reply.get("tokens_out") or 0),
                "latency_ms": int(reply.get("latency_ms") or 0)}

    def failed(message: str, model: str = "") -> dict:
        return {"output": None, "error": llm_client.scrub(message, secret)[:300], "logs": logs, "model": model}

    for attempt in range(2):
        try:
            with LLM_SLOTS:
                reply = llm.chat_json(role, system, prompt)
        except llm_client.AuthError:
            logs.append(entry(None, "the model gateway rejected the API key"))
            return failed("the model gateway rejected the API key")
        except Exception as exc:  # noqa: BLE001 - a failed analyst never stops the others
            message = f"{type(exc).__name__}: {exc}"
            logs.append(entry(None, llm_client.scrub(message, secret)[:300]))
            return failed(message)
        data = reply.get("data") or {}
        model = reply.get("model") or ""
        try:
            cleaned = validate.validate(role, data, reply.get("raw", ""), allowed, numbers, levels)
        except validate.ValidationError as exc:
            logs.append(entry(data, str(exc)[:300], reply))
            if attempt == 0:
                prompt = (f"{user}\n\nYour previous output was invalid: {exc}\n"
                          f"Correct it and output only one JSON object.\n\n"
                          f"{prompts.allowed_line(sorted(allowed))}")
                continue
            return failed(str(exc), model)
        logs.append(entry(data, None, reply))
        return {"output": cleaned, "error": None, "logs": logs, "model": model}
    return failed("no valid answer")


# ---------------------------------------------------------------------------
# Result blocks (SPEC "Rules for result"): numbers and labels come from code
# ---------------------------------------------------------------------------

def normalize_sentiment(label) -> str | None:
    return SENTIMENTS.get(str(label or "").strip().lower())


def chart_block(ctx: context.Context, output: dict | None, error: str | None) -> dict:
    if output is None:
        return {"summary": "", "support": [], "resistance": [],
                "momentum": {"label": None, "why": ""}, "volume": {"label": None, "why": ""},
                "status": "unavailable", "reason": error}
    notes = {side: {item["price"]: item["label"] for item in ctx.levels[side]}
             for side in ("support", "resistance")}

    def levels(side: str) -> list[dict]:
        picked = output[side] or [{"price": item["price"], "why": ""} for item in ctx.levels[side][:2]]
        return [{"price": item["price"], "why": item["why"] or notes[side].get(item["price"], "")}
                for item in picked]

    return {"summary": output["summary"], "support": levels("support"), "resistance": levels("resistance"),
            "momentum": output["momentum"], "volume": output["volume"], "status": "ok", "reason": None}


def news_block(ctx: context.Context, output: dict | None, error: str | None) -> dict:
    labels = [normalize_sentiment(item.get("sentiment")) for item in ctx.news]
    counts = {name: labels.count(name) for name in ("positive", "neutral", "negative")}
    total = sum(counts.values())
    items = [{"title": item.get("title") or "", "source": item.get("source") or "",
              "url": item.get("url") or "", "published_at": item.get("published_at") or "",
              "sentiment": label}
             for item, label in list(zip(ctx.news, labels))[:NEWS_ITEMS_SHOWN]]
    block = {"direction": None, "positive_share": round(counts["positive"] / total, 2) if total else None,
             "counts": counts, "summary": "", "items": items, "status": "ok", "reason": None}
    if not ctx.news:
        return {**block, "direction": "neutral", "summary": "There are no headlines from the last 7 days."}
    if output is None:
        return {**block, "status": "unavailable", "reason": error}
    return {**block, "direction": output["direction"], "summary": output["summary"]}


def _social_sources(ctx: context.Context) -> dict:
    """Each source's state, read back from the posts and the reason `fetch_social` gave."""
    reason = ctx.sources["social"]["reason"] or ""
    sources = {}
    for name in ("stocktwits", "reddit"):
        count = sum(1 for post in ctx.social if post.get("source") == name)
        if count:
            status = "ok"
        elif name == "reddit" and "credentials are not set" in reason:
            status = "skipped"
        else:
            status = "unavailable"
        sources[name] = {"status": status, "count": count}
    return sources


def social_block(ctx: context.Context, output: dict | None, error: str | None) -> dict:
    labels = {item["id"]: item["sentiment"] for item in (output or {}).get("items", [])}
    items = []
    for post in ctx.social:
        text = " ".join(part for part in (post.get("title"), post.get("body")) if part)
        items.append({"text": text[:SOCIAL_TEXT_CHARS], "source": post.get("source") or "",
                      "sentiment": normalize_sentiment(post.get("sentiment")) or labels.get(post["id"]),
                      "url": post.get("url")})
    block = {"direction": "no_data", "summary": "", "sources": _social_sources(ctx), "items": items,
             "status": "ok", "reason": None}
    if not ctx.social:
        status = ctx.sources["social"]["status"]
        return {**block, "status": "skipped" if status == "skipped" else "unavailable",
                "reason": ctx.sources["social"]["reason"] or "no social posts were found"}
    if output is None:
        return {**block, "status": "unavailable", "reason": error}
    return {**block, "direction": output["direction"], "summary": output["summary"]}


def run_status(result: dict) -> str:
    states = [block["status"] for block in result.values()]
    if "ok" not in states:
        return "error"
    return "partial" if "unavailable" in states else "ok"


# ---------------------------------------------------------------------------
# The job
# ---------------------------------------------------------------------------

def _refresh_news(conn, ticker: str, fetchers: dict) -> None:
    """Pull the newest Yahoo headlines now; on any failure the analysis uses what is in the DB."""
    try:
        hook = fetchers.get("refresh_news")
        if hook:
            hook(conn, ticker, context.lookup_name(conn, ticker))
            return
        from pipeline import news_live  # written by another branch; absent means no refresh

        news_live.refresh_ticker(conn, ticker, context.lookup_name(conn, ticker))
    except Exception:  # noqa: BLE001 - stale headlines are better than no analysis
        return


def _jobs(ctx: context.Context) -> dict[str, tuple]:
    """Role -> (user text, allowed evidence ids, levels); a role with nothing to read is left out."""
    intro = f"Ticker: {ctx.ticker} ({ctx.name or 'unknown name'}). Price data as of: {ctx.as_of}."
    jobs: dict[str, tuple] = {}
    if ctx.metrics:
        jobs["market"] = (f"{intro}\n\n{context.market_text(ctx)}", context.evidence_ids(ctx, "metric:"),
                          ctx.levels)
    if context.shown_news(ctx):
        jobs["news"] = (f"{intro}\n\n{context.news_text(ctx)}", context.evidence_ids(ctx, "news:"), None)
    if ctx.social:
        jobs["social"] = (f"{intro}\n\n{context.social_text(ctx)}", context.evidence_ids(ctx, "social:"), None)
    return jobs


def _analyze(conn, llm, ticker: str, horizon: str, fetchers: dict, analysis_id: int) -> tuple[dict, int, str]:
    _refresh_news(conn, ticker, fetchers)
    ctx = context.collect(conn, ticker, horizon, fetchers)
    secret = config.llm_settings().get("api_key")
    jobs = _jobs(ctx)
    reasons = {"market": "not enough price history for the chart read",
               "news": None, "social": None}
    outcomes: dict[str, dict] = {}
    if jobs:
        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            futures = {
                role: pool.submit(call_role, llm, role, user, allowed, validate.numbers_in(user), levels, secret)
                for role, (user, allowed, levels) in jobs.items()
            }
            outcomes = {role: future.result() for role, future in futures.items()}
    tokens = 0
    for role, outcome in outcomes.items():
        for entry in outcome["logs"]:
            _log(conn, analysis_id, role, entry)
            tokens += entry["tokens_in"] + entry["tokens_out"]

    def output(role: str):
        return (outcomes[role]["output"] if role in outcomes else None,
                outcomes[role]["error"] if role in outcomes else reasons[role])

    result = {"chart": chart_block(ctx, *output("market")),
              "news": news_block(ctx, *output("news")),
              "social": social_block(ctx, *output("social"))}
    model = next((o["model"] for o in outcomes.values() if o["model"]), getattr(llm, "model", ""))
    return result, tokens, model


def run_analysis(conn_factory, llm, ticker: str, horizon: str = "1w", fetchers: dict | None = None,
                 analysis_id: int | None = None) -> int:
    """Analyse one ticker and store the result; returns the `stock_analysis.id` (0 if the DB is down).

    `fetchers` may replace `prices`, `news`, `social` and `refresh_news` (tests inject them).
    `analysis_id` continues a row the caller already inserted with `start_run`.
    """
    ticker = ticker.strip().upper()
    secret = None
    conn = None
    try:
        secret = config.llm_settings().get("api_key")
        conn = conn_factory()
        analysis_id = analysis_id or start_run(conn, ticker, horizon)
        try:
            result, tokens, model = _analyze(conn, llm, ticker, horizon, fetchers or {}, analysis_id)
            status = run_status(result)
            error = None
            if status == "error":
                error = "; ".join(f"{name}: {block['reason']}" for name, block in result.items()
                                  if block["status"] != "ok")[:300]
            finish(conn, analysis_id, status, result, error, model, tokens)
        except Exception as exc:  # noqa: BLE001 - one ticker failure is stored, not raised
            message = llm_client.scrub(f"{type(exc).__name__}: {exc}", secret)[:300]
            finish(conn, analysis_id, "error", None, message, getattr(llm, "model", None), 0)
        return analysis_id
    except Exception:  # noqa: BLE001 - even a dead database must not crash the caller's thread
        return analysis_id or 0
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass
