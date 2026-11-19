---
type: Architecture
title: AI agent review
description: TradingAgents-style LLM agent team that reviews each home-page idea, plus a cheap one-call quick review (both built and live-tested on Grok)
tags: [architecture, llm, agents]
status: draft
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-19T10:00:00Z }
sources:
  - id: spec
    resource: specs/trading-agents/SPEC.md
    title: Shared spec, DB tables and API contract
  - id: ta
    resource: https://github.com/TauricResearch/TradingAgents
    title: TauricResearch/TradingAgents (pattern source, code not copied)
---

Decided by the user 2026-11-17: use an LLM again, mixed with the existing rules/ML, and bring in **all** TradingAgents roles.[^ta] Built 2026-11-17 by two OpenCode agents (committed in PR #13, branch `fais-agent-review`): engine `Backend/agents/`, API `Backend/app/agents_api.py`, UI `frontend/src/components/ideas/AgentPanel.tsx` · agent + API tests pass (91 in the backend suite), frontend tsc/lint pass · live full runs on `grok-4.3` 2026-11-18: TYL, COST, TSN, ROP, AAPL, MSI finished (ROP and TYL re-run 2026-11-19: both Hold with caution) (12 roles, ~2–5 min each; the validator rejected invented evidence ids and forced retries) · spec in `specs/trading-agents/`.[^spec]

Run: `cd Backend && .venv/bin/python -m agents.run --tickers TYL --horizon 1w` · `--fake` refuses to run without `PLANWISE_DB` (a fake run once wrote into Neon via `DATABASE_URL`; cleaned up).

# Flow per stock (12 LLM calls + 1 reflection per settled decision)

4 analysts (market + macro, news, fundamentals, social) → bull/bear debate (1 round) → research manager → trader → risk debate (aggressive, conservative, neutral) → portfolio manager → rating Buy/Overweight/Hold/Underweight/Sell or `REVIEW` → memory settles each call after 5 trading days vs SPY with a short reflection.

# Quick review (triage, built 2026-11-19)

One LLM call per stock on a one-page brief: rule idea + price metrics (+ big-move %, ATR %) + at most 5 headlines; fundamentals, SEC, social and macro are skipped. Same evidence-id and number checks; answer = rating + confidence + 2 points. Stored in `agent_runs` with `prompt_version = ta-triage-v1`, no `agent_decisions` row (no track record or memory). Code `Backend/agents/triage.py`.

- CLI: `--mode triage` (every ranked idea, best score first, default top 100) · `--mode funnel` (triage, then the 12-agent review for flagged stocks: Underweight/Sell, or Buy/Overweight with high confidence; highest rule score first, at most `--full` = 15)
- No headlines → confidence is forced to `low`. Model: `AGENT_LLM_TRIAGE_MODEL` (= `grok-4.20-0309-non-reasoning`)
- API: `ai.mode` is `full` or `quick` (a full review wins over a newer quick one; quick adds `confidence` and `points`; `/api/agents/{ticker}` ignores quick runs) · UI: badge `AI quick · <rating>` and a short block in the card panel
- Measured 2026-11-19 on xAI: ~1.5k tokens and ~2 s per stock once warm (first call 40–90 s) vs 34.4k tokens and 1 min 44 s for one full review (MSI), about 24x fewer · provider counts leave reasoning tokens out
- 20 curated 1w ideas: Hold 16, Underweight 4, Buy/Overweight 0, confidence mostly low → the "strong agreement" path never fired · compared with a full review on one stock only (MSI, both Underweight) · quality not validated

# Rules

- The AI never changes entry/stop/target/score/position; trader and risk numbers are shown separately as "AI suggestion"
- Every claim cites evidence ids from its input; numbers not in the input are rejected in code; failed sources show as unavailable
- AI says Hold/Sell → the card stays with a warning (not hidden)
- LLM: xAI `https://api.x.ai/v1`, `grok-4.3` (~10 s per call, reasons ~500 tokens), keys in `Backend/.env` only · the old `gateway.9arm.co` qwen3.8 was dropped (~100 s per call, Cloudflare 524, frequent 503)
- Client streams the reply, fails on `finish_reason=length`, retries 5xx/524 · number guard ignores signs (418-430 is a range), allows textbook thresholds, drops a point with an invented number
- Plain Python loop (no LangGraph) in `Backend/agents/`; tables `agent_runs`, `agent_messages`, `agent_decisions`, `source_cache`; API `/api/agents/{ticker}` + `ai` field on `/api/recommendations`

# Data status (checked 2026-11-18)

SEC EDGAR 200 OK but skipped (no `SEC_EDGAR_USER_AGENT`) · StockTwits worked (was 403 the day before) · anonymous Reddit RSS 403 · FMP free key returns 402 → fundamentals `no_data` · UI renders evidence ids as `[n]` chips (browser check pending) · see [Data sources](/architecture/data-sources.md)

[^spec]: specs/trading-agents/SPEC.md
[^ta]: TauricResearch/TradingAgents
