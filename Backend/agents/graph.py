"""Runs the agent roles in order for one ticker and stores an AgentReview.

Adapted from TauricResearch/TradingAgents (Apache-2.0), graph/conditional_logic.py
and graph/setup.py (turn order), agents/context.py (`report_or_absent` intent).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from . import config, context, llm_client, memory, prompts, schema, sources, validate


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rowdict(row) -> dict:
    return {key: row[key] for key in row.keys()}


class Runner:
    def __init__(self, conn, llm, run_id: int, ctx: context.Context, on_event=None,
                 secret: str | None = None):
        self.conn = conn
        self.llm = llm
        self.run_id = run_id
        self.ctx = ctx
        self.on_event = on_event
        self.secret = secret
        self.tokens_in = 0
        self.tokens_out = 0
        self.failures: set[str] = set()
        text = context.all_data_text(ctx) + "\n" + context.memory_block(ctx)
        text += "\n" + json.dumps(self._evidence_values(), ensure_ascii=False)
        self.numbers = validate.numbers_in(text)
        self.agent_ids: set[str] = set()
        self._record_calls = 0

    def _evidence_values(self) -> dict:
        return {key: value.get("value") for key, value in self.ctx.evidence.items() if value.get("value")}

    def _log(self, role: str, turn: int, model: str, allowed: set[str], data, error,
             tokens_in: int, tokens_out: int, latency_ms: int) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO agent_messages (run_id, role, turn, model, input_ids, output_json, error, "
                "tokens_in, tokens_out, latency_ms, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (self.run_id, role, turn, model or "", json.dumps(sorted(allowed)),
                 json.dumps(data) if data is not None else None, error,
                 tokens_in, tokens_out, latency_ms, _now()),
            )
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out

    def _emit(self, role: str, status: str, latency: int, tokens: int, detail: str | None = None) -> None:
        if self.on_event:
            self.on_event(role, status, latency, tokens, detail)

    def call(self, role: str, user: str, allowed: set[str], turn: int = 0,
             deep: bool = False) -> dict | None:
        system = prompts.system(role)
        full_user = f"{user}\n\n{prompts.allowed_line(sorted(allowed))}"
        atr = self.ctx.metrics.get("_atr")
        for attempt in range(2):
            try:
                result = self.llm.chat_json(role, system, full_user, deep=deep)
            except llm_client.AuthError:
                raise  # a rejected key fails the whole run at once instead of 12 more calls
            except Exception as exc:  # noqa: BLE001 - a failed role never stops the review
                message = llm_client.scrub(f"{type(exc).__name__}: {exc}", self.secret)[:300]
                self._log(role, turn, "", allowed, None, message, 0, 0, 0)
                self.failures.add(role)
                self._emit(role, "fail", 0, 0, message)
                return None
            data = result.get("data") or {}
            model = result.get("model") or ""
            tin = int(result.get("tokens_in") or 0)
            tout = int(result.get("tokens_out") or 0)
            latency = int(result.get("latency_ms") or 0)
            try:
                cleaned = validate.validate(role, data, result.get("raw", ""), allowed,
                                            self.numbers, rules=self.ctx.rules, atr=atr)
            except validate.ValidationError as exc:
                self._log(role, turn, model, allowed, data, str(exc)[:300], tin, tout, latency)
                if attempt == 0:
                    self._emit(role, "retry", latency, tin + tout, str(exc))
                    full_user = (f"{user}\n\nYour previous output was invalid: {exc}\n"
                                 f"Correct it and output only one JSON object.\n\n"
                                 f"{prompts.allowed_line(sorted(allowed))}")
                    continue
                self.failures.add(role)
                self._emit(role, "fail", latency, tin + tout, str(exc))
                return None
            self._log(role, turn, model, allowed, data, None, tin, tout, latency)
            self.numbers |= validate.numbers_in(json.dumps(cleaned, ensure_ascii=False))
            self._emit(role, "ok", latency, tin + tout)
            return cleaned
        return None

    def register(self, role: str, cleaned: dict, field: str) -> None:
        value = cleaned.get(field) or ""
        self.ctx.evidence[f"agent:{role}"] = {
            "kind": "agent", "label": config.ROLE_LABELS.get(role, role), "value": str(value)[:500],
        }
        self.agent_ids.add(f"agent:{role}")


def _source_ids(ctx: context.Context, prefix: str) -> set[str]:
    return {key for key in ctx.evidence if key.startswith(prefix)}


def _rating_of(output: dict | None, key: str = "rating") -> str | None:
    return output.get(key) if output else None


def review_ticker(conn, llm, ticker: str, horizon: str = "1w", fetchers: dict | None = None,
                  on_event=None) -> int:
    """Review one ticker and return the `agent_runs.id`. Never raises for one ticker."""
    ticker = ticker.strip().upper()
    settings = config.llm_settings()
    model = getattr(llm, "model", "") or settings.get("model") or "unknown"
    deep_model = getattr(llm, "deep_model", "") or settings.get("deep_model") or model
    schema.ensure(conn)
    today = datetime.now(timezone.utc).date().isoformat()
    with conn:
        row = conn.execute(
            "INSERT INTO agent_runs (ticker, horizon, as_of, model, deep_model, prompt_version, status, "
            "sources_json, started_at) VALUES (?, ?, ?, ?, ?, ?, 'error', '{}', ?) RETURNING id",
            (ticker, horizon, today, model, deep_model, config.PROMPT_VERSION, _now()),
        ).fetchone()
    run_id = row[0]

    runner = None
    try:
        ctx = context.collect(conn, ticker, horizon, fetchers=fetchers)
        with conn:
            conn.execute("UPDATE agent_runs SET as_of = ? WHERE id = ?", (ctx.as_of, run_id))
        runner = Runner(conn, llm, run_id, ctx, on_event=on_event,
                        secret=settings.get("api_key"))

        analyst_ids = {
            "market": _source_ids(ctx, "metric:") | _source_ids(ctx, "rule:") | _source_ids(ctx, "macro:"),
            "news": _source_ids(ctx, "news:"),
            "fundamentals": _source_ids(ctx, "fund:") | _source_ids(ctx, "sec:"),
            "social": _source_ids(ctx, "social:"),
        }
        sections = {
            "market": context.market_text(ctx),
            "news": context.news_text(ctx),
            "fundamentals": context.fundamentals_text(ctx),
            "social": context.social_text(ctx),
        }
        intro = (f"Ticker: {ticker} ({ctx.name or 'unknown name'}). Horizon: {ctx.horizon}. "
                 f"Price data as of: {ctx.as_of}.")
        analyst_outputs: dict[str, dict | None] = {}
        for role in ("market", "news", "fundamentals", "social"):
            analyst_outputs[role] = runner.call(
                role, f"{intro}\n\n{sections[role]}", analyst_ids[role], deep=False)
            if analyst_outputs[role]:
                runner.register(role, analyst_outputs[role], "summary")

        all_no_data = all((not out) or out.get("signal") == "no_data"
                          for out in analyst_outputs.values())

        bull_points: list[dict] = []
        bear_points: list[dict] = []
        manager = None
        trader = None
        risk_outputs: dict[str, dict | None] = {"aggressive": None, "conservative": None, "neutral": None}

        if not all_no_data:
            analyst_agent_ids = runner.agent_ids & {
                "agent:market", "agent:news", "agent:fundamentals", "agent:social"}
            source_ids = set(ctx.evidence)

            bull_user = (f"{intro}\n\n{context.analysts_block(analyst_outputs)}\n\n"
                         f"{context.all_data_text(ctx)}\n\n{context.debate_block([], [])}")
            bull = runner.call("bull", bull_user, source_ids | analyst_agent_ids, turn=1)
            if bull:
                bull_points = bull["points"]
                runner.register("bull", {"summary": bull_points[0]["text"] if bull_points else ""}, "summary")

            bear_user = (f"{intro}\n\n{context.analysts_block(analyst_outputs)}\n\n"
                         f"{context.all_data_text(ctx)}\n\n"
                         f"{context.debate_block(bull_points, [])}\n\n"
                         "The bear has not spoken yet in this round; answer the bull's points above.")
            bear = runner.call("bear", bear_user, source_ids | analyst_agent_ids | {"agent:bull"}, turn=2)
            if bear:
                bear_points = bear["points"]
                runner.register("bear", {"summary": bear_points[0]["text"] if bear_points else ""}, "summary")

            manager_allowed = (runner.agent_ids & analyst_agent_ids) | {
                "agent:bull", "agent:bear"} & runner.agent_ids
            manager_user = (f"{intro}\n\n{context.analysts_block(analyst_outputs)}\n\n"
                            f"{context.debate_block(bull_points, bear_points)}")
            manager = runner.call("research_manager", manager_user, manager_allowed, deep=True)
            if manager:
                runner.register("research_manager", manager, "rationale")

            trader_allowed = ({f"agent:research_manager"} & runner.agent_ids) | _source_ids(ctx, "metric:") | _source_ids(ctx, "rule:")
            manager_text = (f"agent:research_manager — {manager['lean']}: {manager['rationale']}"
                            if manager else "(No research manager output in this run.)")
            trader_user = (f"{intro}\n\nResearch manager plan: {manager_text}\n\n"
                           f"{context.market_text(ctx)}")
            trader = runner.call("trader", trader_user, trader_allowed, deep=False)
            if trader:
                runner.register("trader", trader, "rationale")

            risk_base = (({f"agent:research_manager"} & runner.agent_ids)
                         | ({f"agent:trader"} & runner.agent_ids)
                         | _source_ids(ctx, "metric:") | _source_ids(ctx, "rule:"))
            risk_turns = []
            for index, role in enumerate(("aggressive", "conservative", "neutral"), start=1):
                allowed = risk_base | (runner.agent_ids & {"agent:aggressive", "agent:conservative",
                                                           "agent:neutral"})
                user = (f"{intro}\n\nResearch manager: "
                        f"{manager['lean'] + ': ' + manager['rationale'] if manager else '(none)'}\n\n"
                        f"Trader: {trader['stance'] + ': ' + trader['rationale'] if trader else '(none)'}\n\n"
                        f"{context.market_text(ctx)}\n\n"
                        f"{context.prior_risk_block({r: risk_outputs.get(r) for r in ('aggressive', 'conservative', 'neutral')})}")
                output = runner.call(role, user, allowed, turn=index, deep=False)
                risk_outputs[role] = output
                if output:
                    runner.register(role, output, "view")
                risk_turns.append(role)

            pm_memory = memory.memory_items(conn, ticker)
            ctx.memory = pm_memory
            runner.numbers |= validate.numbers_in(context.memory_block(ctx))
            memory_ids = {f"memory:{item['id']}" for item in pm_memory}
            if pm_memory:
                memory_fresh = memory.memory_evidence(pm_memory)
                for key, value in memory_fresh.items():
                    ctx.evidence.setdefault(key, value)
            pm_allowed = set(ctx.evidence) | runner.agent_ids | memory_ids
            risk_text = context.prior_risk_block(risk_outputs)
            pm_user = (f"{intro}\n\n{context.all_data_text(ctx)}\n\n"
                       f"{context.analysts_block(analyst_outputs)}\n\n"
                       f"{context.debate_block(bull_points, bear_points)}\n\n"
                       f"Research manager: {manager or '(none)'}\n\n"
                       f"Trader: {trader or '(none)'}\n\n{risk_text}\n\n{context.memory_block(ctx)}")
            pm = runner.call("portfolio_manager", pm_user, pm_allowed, deep=True)
            if pm:
                runner.register("portfolio_manager", pm, "summary")
        else:
            pm = None

        if all_no_data:
            rating = config.REVIEW
            summary = ("Some analysts failed and the rest found no usable data, so no debate was run."
                       if runner.failures else
                       "All four analysts found no usable data, so no debate was run.")
            key_risks = []
        else:
            rating = _rating_of(pm) if pm else config.REVIEW
            summary = (pm or {}).get("summary") or (
                "The portfolio manager did not return a valid decision.")
            key_risks = (pm or {}).get("key_risks") or []

        review = {
            "rating": rating,
            "summary": summary,
            "agrees": config.agrees(rating),
            "key_risks": key_risks,
            "analysts": {role: analyst_outputs.get(role) for role in ("market", "news", "fundamentals", "social")},
            "debate": {"bull": bull_points, "bear": bear_points, "manager": manager},
            "trader": trader,
            "risk": risk_outputs,
            "rules": {
                "entry": (ctx.rules or {}).get("entry") or 0,
                "stop": (ctx.rules or {}).get("stop") or 0,
                "target": (ctx.rules or {}).get("target") or 0,
                "score": (ctx.rules or {}).get("score") or 0,
            },
        }

        evidence_index = {
            key: {field: value[field] for field in
                  ("label", "value", "url", "published_at", "sentiment") if value.get(field)}
            for key, value in ctx.evidence.items()
            if not key.startswith(("news:", "rule:"))
        }
        final_json = {**review, "evidence_index": evidence_index}

        failed = bool(runner.failures)
        if all_no_data or failed or rating == config.REVIEW:
            status = "partial"
        else:
            status = "ok"

        with conn:
            conn.execute(
                "UPDATE agent_runs SET as_of = ?, status = ?, rating = ?, summary = ?, final_json = ?, "
                "sources_json = ?, tokens_in = ?, tokens_out = ?, finished_at = ? WHERE id = ?",
                (ctx.as_of, status, rating, summary, json.dumps(final_json), json.dumps(ctx.sources),
                 runner.tokens_in, runner.tokens_out, _now(), run_id),
            )
        memory.record_decision(conn, run_id, ticker, rating, ctx.as_of)
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
