---
type: Architecture
title: AI agent review
description: TradingAgents-style LLM agent team that reviews each home-page idea, plus a cheap one-call quick review (built; full review live-tested on Grok and on the 9arm gateway)
tags: [architecture, llm, agents]
status: draft
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-24T03:00:00Z }
sources:
  - id: spec
    resource: specs/trading-agents/SPEC.md
    title: Shared spec, DB tables and API contract
  - id: ta
    resource: https://github.com/TauricResearch/TradingAgents
    title: TauricResearch/TradingAgents (pattern source, code not copied)
---

Decided by the user 2026-11-17: use an LLM again, mixed with the existing rules/ML, and bring in **all** TradingAgents roles.[^ta] Built 2026-11-17 by two OpenCode agents (merged in PR #13): engine `Backend/agents/`, API `Backend/app/agents_api.py`, UI `frontend/src/components/ideas/AgentPanel.tsx` · backend tests, frontend tsc, eslint and build pass · live full runs on `grok-4.3` 2026-11-18: TYL, COST, TSN, ROP, AAPL, MSI finished (ROP and TYL re-run 2026-11-19: both Hold with caution) (12 roles, ~2–5 min each; the validator rejected invented evidence ids and forced retries) · spec in `specs/trading-agents/`.[^spec]

Run: `cd Backend && .venv/bin/python -m agents.run --tickers TYL --horizon 1w` · `--fake` refuses to run without `PLANWISE_DB` (a fake run once wrote into Neon via `DATABASE_URL`; cleaned up).

# Flow per stock (12 LLM calls + 1 reflection per settled decision)

4 analysts (market + macro, news, fundamentals, social) → bull/bear debate (1 round) → research manager → trader → risk debate (aggressive, conservative, neutral) → portfolio manager → rating Buy/Overweight/Hold/Underweight/Sell or `REVIEW` → memory settles each call after 5 trading days vs SPY with a short reflection.

# Quick review (triage, built 2026-11-19)

One LLM call per stock on one brief: rule idea (entry and score only) + price metrics and indicators (+ big-move %, ATR %) + a Yahoo fundamentals snapshot + macro lines + at most 5 headlines; SEC filings and social posts are skipped. Same evidence-id and number checks; answer = rating + confidence + a 4 to 6 sentence summary + 4 points (trend and momentum, risk, fundamentals and valuation, news and macro) · about 7.4k tokens and 70 to 80 s per stock (was 2.6k, 2 short points). Stored in `agent_runs` with `prompt_version = ta-triage-v1`, no `agent_decisions` row (no track record or memory). Code `Backend/agents/triage.py`.

- CLI: `--mode triage` (every ranked idea, best score first, default top 100) · `--mode funnel` (triage, then the 12-agent review for flagged stocks: Underweight/Sell, or Buy/Overweight with high confidence; highest rule score first, at most `--full` = 15)
- **Coverage of what the web serves** (2026-11-21, user complaint that cards stayed "AI pending"): `pipeline/review_served.py`, run by the hourly job, quick-reviews every (stock, horizon) the API serves, i.e. the curated top 5 per horizon plus the top 5 of every saved profile on all three horizons, skipping pairs already reviewed for the current ranking date, at most 12 pairs per run, curated first · before it only 19 reviews existed on Neon and one Top 5 stock had an AI badge · a new user's list gets its badges within a few hourly runs, not at once · tests `tests/test_review_served.py` (8)
- On 2026-11-21 the 47 then-stored reviews were almost all Overweight (Hold on a few, no Underweight/Sell among the served stocks), so the known bullish lean remains and the badge says little about which of five is better · the quick brief and the full review still contain the ATR stop/target, so AI text can say "target" or "4% stop" although the card hides them
- **ATR bug found and fixed 2026-11-21:** `agents/sources.py` stored `atr14_pct` already times 100 and the display multiplied by 100 again, so the AI saw "ATR 204.49%" next to the rule's 2.04% (ED) and "17.78%" vs 0.18% (TECH), and cited the conflict as a reason for low confidence / Hold · now a fraction like the other percent metrics, test `tests/test_agent_metrics.py` (3) · reviews stored before the fix saw the wrong number and a pair counts as reviewed for its ranking date, so they are redone by hand: `python -m pipeline.review_served --redo-before <fix time>` (redoes served pairs whose review started earlier) · the user's 15 served cards (Healthcare profile) were redone 2026-11-21 (15 quick calls, 37,026 tokens, no "data error" ATR text left) · **still on the wrong number:** quick reviews of other stocks and profiles (about 37 pairs, about 100k tokens) and the 5 full reviews of the curated 1w top 5 (COST DUK TSN ED WMT, about 370k tokens)
- The card shows one verdict block (`AI says: <rating>`) for both modes; the footnote says whether it is a full 12-agent review or a quick check, and **More info** has 6 rows for a full review and 2 for a quick one
- **Full 12-agent run of the curated 1w top 5, 2026-11-22 (new prompts, 3 in parallel):** COST, DUK, TSN, ED rated Underweight and WMT Overweight, 146k to 216k tokens each, about 75 min for the first four · WMT was rerun alone after its Neon connection dropped while saving (now reconnects) · the earlier run with the short prompts (Overweight for COST, DUK, WMT, TSN, Hold for ED) is superseded · these ratings are not backtested
- No headlines → confidence is forced to `low`. Model: `AGENT_LLM_TRIAGE_MODEL`, or the main model when unset (the gateway offers only one model)
- API: `ai.mode` is `full` or `quick` (a full review wins over a newer quick one; quick adds `confidence` and `points`; `/api/agents/{ticker}` ignores quick runs) · UI: the badge on the card header (`AI quick · <rating>` or `AI · <rating>`) and the verdict block in the panel
- Measured 2026-11-21 on `gateway.9arm.co`: a quick call is ~2.7k tokens and ~50 s, one full review (VLTO) 68.7k tokens and 15 min 42 s · on xAI 2026-11-19 it was ~1.5k tokens and ~2 s vs 34.4k tokens and 1 min 44 s · provider counts may leave reasoning tokens out
- 20 curated 1w ideas: Hold 16, Underweight 4, Buy/Overweight 0, confidence mostly low → the "strong agreement" path never fired · compared with a full review on one stock only (MSI, both Underweight) · quality not validated

# Prompts and tools (2026-11-22)

User complaint: reviews were not detailed and the tools of the original were not used. `agents/prompts.py` now copies the detailed instructions of TradingAgents (Apache-2.0): the market analyst's indicator menu with usage and tips (all computed in `sources.compute_metrics`: SMA50/200, EMA10, MACD line/signal/histogram, RSI, Bollinger, ATR, VWMA), the news, fundamentals and sentiment analyst briefs, bull and bear key points, rating scale and commit-to-a-side rule, risk analysts, portfolio manager. Tool calls are replaced by data already in the message. Text limits were raised (points 6 to 10 for analysts, 3 to 7 for bull and bear, 5 for quick) and the trader and the risk analysts now also see the analyst reports. The AI no longer sees the rule's stop and target. Long answers need room (`MAX_TOKENS` 14000, was 6000: bull was cut off), a sentence with an unseen number is dropped instead of failing the whole call (`validate.clean_text`), a sentence pasted into an evidence list keeps only its valid ids, and the trader and risk roles may cite any evidence id. **Test on CAH 1m (scratch DB, 2026-11-22):** 12 calls, 0 errors, 163,440 tokens (old reviews about 74k), about 19 min, Overweight; bull and bear answer each other point by point with quarterly figures, the portfolio manager states what would change the call. Neon reviews stored before this change still have the short text. Deleted as unused on 2026-11-22: the FMP fetchers, `triage.is_triage`, and in the frontend the old dashboard/sidebar components with their mock data.

# Card design (2026-11-22)

The card shows a short plain-language top and hides the rest. The portfolio manager and the quick review also answer `headline` (one sentence), `checks` (trend, business, news_market, risk: green/amber/red + at most 8 words), `how_to_act` and `change_if`; `validate.verdict_fields` keeps them optional and never fatal (a line with an unseen number is blanked), stored as `final_json.verdict`, served as `ai.verdict` by `/api/recommendations` (`agents_api._verdict`; absent on older reviews, the card then shows the long summary). UI: `AiVerdict.tsx` (verdict, four lights, how to act, change-if) then Reasons and News, then **More info** rows (`MoreRow`): key points, analysts, bull vs bear, trade plan and risk views, numbers and sources, track record; a quick review gets two rows (full reasoning, about this check). Both modes use the same top. Checked on the real page 2026-11-22 (test accounts): the 15 quick reviews of a Healthcare profile (redone after the change, about 7.5k tokens each) show the new top; the 5 full reviews of COST DUK TSN ED WMT predate it and show the long summary until they are rerun (about 820k tokens). The text never shows internal names: `strip_internal` (backend) and `prose()` (UI) drop "(r60)" and "(metric:rsi14)" style brackets. `npm run build` was not run (the user's dev server shares the folder); `tsc` and `eslint` are clean.

# Rules

- The AI never changes entry/stop/target/score/position; the card no longer shows stop/target/position at all, and the AI trader's suggested stop/target and the risk analysts' suggested position are stored but not displayed
- Every claim cites evidence ids from its input; numbers not in the input are rejected in code; failed sources show as unavailable
- AI says Hold/Sell → the card stays with a warning (not hidden)
- LLM (user choice 2026-11-21, "Token Me"): `https://gateway.9arm.co/v1`, `qwen3.8-27b-fp8` (the only model it offers), keys in `Backend/.env` only · 2 direct calls and one full review ran with no visible 503 (the client retries 5xx silently, so hidden retries are not ruled out) · slow: full review ~16 min per stock · xAI `grok-4.3` lines are commented out in `.env`
- **Rate limit (tested 2026-11-22):** `gateway.9arm.co` allows 3 simultaneous requests per key; the 4th gets HTTP 429 with `retry-after: 60` · keep `--workers` at 3 or less and do not overlap a manual run with the hourly job (the client retries 429, so it only slows down)
- Client streams the reply, fails on `finish_reason=length`, retries 5xx/524 · number guard ignores signs (418-430 is a range), allows textbook thresholds, drops a point with an invented number
- Plain Python loop (no LangGraph) in `Backend/agents/`; tables `agent_runs`, `agent_messages`, `agent_decisions`, `source_cache`; API `/api/agents/{ticker}` + `ai` field on `/api/recommendations`

# Data status (checked 2026-11-18)

SEC EDGAR 200 OK but skipped (no `SEC_EDGAR_USER_AGENT`) · StockTwits worked (was 403 the day before) · anonymous Reddit RSS 403 · the FMP code was deleted (its key returned 402), so fundamentals come from Yahoo Finance (`yfinance`, no key: 25 ratios, 4 quarters of revenue/profit/cash flow, balance sheet, insider buys and sales over 6 months, analyst targets), and macro without a FRED key is VIX, 10-year yield, 3-month bill and the dollar index from Yahoo · UI renders evidence ids as `[n]` chips (browser check pending) · see [Data sources](/architecture/data-sources.md)

[^spec]: specs/trading-agents/SPEC.md
[^ta]: TauricResearch/TradingAgents
