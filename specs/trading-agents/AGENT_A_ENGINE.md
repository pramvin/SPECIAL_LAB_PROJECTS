# Agent A — agent engine (backend)

Read first: [SPEC.md](SPEC.md) (rules, env, DDL, contract), `Backend/pipeline/llm.py` (current single-LLM step: env loading, validation, retry and logging pattern to copy), `Backend/app/dbcompat.py` (use `connect()`; write portable SQL with `?`), `Backend/pipeline/bigmove_features.py` (indicator formulas to reuse).
Only edit: `Backend/agents/**`, `Backend/tests/test_agents*.py`, `Backend/.env.example` (names only, no values). Use only packages already in `Backend/requirements.txt` (`requests`, `pandas`, `yfinance`, …).

## 0. Port from the reference repo

Root: `/Users/fais/Downloads/TradingAgents-main/tradingagents/` (read-only, see SPEC "Reference code"). Keep the role wording and intent, but change every prompt's output section to our JSON shape + evidence ids (§3) and drop tool-calling (we pass data in the prompt).

| Our file / role | Read in the reference |
|---|---|
| `prompts.py` market / news / fundamentals / social | `agents/analysts/market_analyst.py`, `news_analyst.py`, `fundamentals_analyst.py`, `sentiment_analyst.py` (+ `agents/schemas.py` `SentimentReport`, `SentimentBand`) |
| bull / bear | `agents/researchers/bull_researcher.py`, `bear_researcher.py`, `agents/context.py` (`opponent_argument_or_opening`, `report_or_absent`) |
| research_manager | `agents/managers/research_manager.py`, `agents/schemas.py` `ResearchPlan` |
| trader | `agents/trader/trader.py`, `agents/schemas.py` `TraderProposal`, `TraderAction` |
| aggressive / conservative / neutral | `agents/risk_mgmt/*_debator.py` |
| portfolio_manager | `agents/managers/portfolio_manager.py` (rating scale text, "conflict alone is not a reason to Hold"), `agents/schemas.py` `PortfolioDecision` |
| `validate.py` rating fallback | `agents/rating.py` (`extract_rating` / `parse_rating` → `REVIEW`; port it as the fallback when JSON has no valid rating) |
| `llm_client.py` structured-output fallback | `agents/structured.py` |
| `graph.py` turn order + stop counts | `graph/conditional_logic.py`, `graph/setup.py`, `agents/state.py` |
| `memory.py` | `memory/settlement.py` (`fetch_returns`: entry = first close after the analysis date, full window must have traded), `memory/reflection.py` (prompt: 2–4 sentences, cite the alpha, say if the window is too short), `memory/log.py` (what the PM gets back) |
| `sources.py` | `dataflows/vendors/sec_edgar.py`, `reddit.py`, `stocktwits.py`, `fred.py` (endpoints, headers, rate limits); prices/news come from our DB instead of `vendors/yahoo/` |

Reference differences we keep on purpose: reflection uses the quick model (as the reference does); no checkpointing; no `post_screen.py`/TypeSafe screening; no Polymarket.

## Files

| File | Job |
|---|---|
| `agents/__init__.py` | empty |
| `agents/config.py` | load `Backend/.env` (same as `pipeline/llm.py:load_env`), constants: `PROMPT_VERSION="ta-v1"`, `MAX_DEBATE_ROUNDS=1`, `MAX_RISK_ROUNDS=1`, `SETTLE_DAYS=5`, `MAX_NEWS=15`, `MAX_SOCIAL=20`, `TEMPERATURE=0.2` |
| `agents/schema.py` | the exact DDL from SPEC + `ensure(conn)` |
| `agents/llm_client.py` | `LLM` protocol + `OpenAICompatLLM` + `FakeLLM` |
| `agents/sources.py` | one function per source, each returns `{"status","reason","items"}` |
| `agents/context.py` | builds per-role context text + the set of allowed evidence ids |
| `agents/prompts.py` | system prompt + JSON shape per role |
| `agents/validate.py` | parse + validate each role's output |
| `agents/graph.py` | runs the roles in order for one ticker → `AgentReview.review` dict |
| `agents/memory.py` | write decision, settle old decisions vs SPY, reflection |
| `agents/run.py` | CLI |

## 1. `llm_client.py`

- `chat_json(role, system, user, deep=False) -> {"data": dict, "raw": str, "model", "tokens_in", "tokens_out", "latency_ms"}`.
- POST `{AGENT_LLM_BASE_URL}/chat/completions`, header `Authorization: Bearer …`, body `{model, messages, temperature, max_tokens: 1500, response_format: {"type":"json_object"}}`. If the gateway answers 400 mentioning `response_format`, retry once without it and remember that for the session.
- Parse: strip `<think>…</think>` and ```` ```json ```` fences, take the first `{…}` block, `json.loads`.
- HTTP 429/5xx/timeouts: 3 tries, backoff 2s/6s/15s. Timeout 120s. Other 4xx: raise.
- Never put the key in exceptions, logs or DB (`error` strings: status code + first 200 chars of body only).
- `FakeLLM(responses: dict[role, list[dict|str]])` returns canned outputs and records every call (tests count calls per role).

## 2. `sources.py` (each wrapped in try/except → `unavailable` with a short reason; never raise to the graph)

| Source | What | How |
|---|---|---|
| `prices` | last 120 closes of the ticker + SPY | DB `prices`; SPY is not in `prices` → yfinance `SPY` daily, cached in `source_cache(source='spy')` per day |
| `metrics` | `close`, `r5`, `r20`, `r60`, `rsi14`, `macd`, `ma50_gap`, `ma200_gap`, `vol20`, `atr14_pct`, `volx`, `high_52w_gap` | computed in pandas from `prices` (formulas like `bigmove_features.py`, raw values not market-relative); id `metric:<name>`, round to 2 dp |
| `news` | up to 15 newest `news_items` (last 14 days, `rule_noise=0`) + `news_scores.sentiment` if present | id `news:<id>`; include date, source, title |
| `rules` | the `recommendations` row for (ticker, horizon): entry, stop, target, score, reasons, bigmove_p | id `rule:<i>` per reason; `metric:entry` etc. |
| `fmp` | profile, key-metrics-ttm, ratios-ttm, last 4 quarterly income statements | `https://financialmodelingprep.com/stable/...` with `apikey`; ≤4 requests per ticker, cache per day in `source_cache`; on 401/402/403/429 → `unavailable`. ids `fund:<field>` (pick ≤15 fields: pe, ps, pb, ev_ebitda, gross_margin, op_margin, net_margin, roe, debt_equity, revenue_growth_yoy, eps_growth_yoy, fcf_yield, market_cap, dividend_yield, next_earnings_date if available) |
| `sec` | latest 10-K/10-Q facts: Revenues, NetIncomeLoss, EPS diluted, Assets, Liabilities (last 4 values) | `company_tickers.json` → CIK → `data.sec.gov/api/xbrl/companyfacts/CIK##########.json`; only if `SEC_EDGAR_USER_AGENT` set, else `skipped`; ≤10 req/s; cache per day; ids `sec:<concept>:<period end>` |
| `social` | Reddit (r/stocks, r/investing, r/wallstreetbets, last 7 days, search `$TICKER OR "company name"`) + StockTwits symbol stream | Reddit via OAuth app-only token (`https://www.reddit.com/api/v1/access_token`, `grant_type=client_credentials`) then `https://oauth.reddit.com/r/{sub}/search` — only if client id/secret set, else `skipped`. StockTwits `https://api.stocktwits.com/api/2/streams/symbol/{T}.json`, on 403 → `unavailable` (expected today). ids `social:reddit:<id>`, `social:stocktwits:<id>`; keep title/body ≤280 chars, score, date. Max 20 posts |
| `macro` | FEDFUNDS, DGS10, CPIAUCSL YoY, UNRATE latest | FRED, only if `FRED_API_KEY`, else `skipped`; ids `macro:<series>` |

## 3. Roles, inputs and output JSON

Every system prompt says: use ONLY the context; every point lists evidence ids from the context; no prices/numbers that are not in the context; if data is missing say so in `data_gaps`/`no_data`; plain English; ≤ 3 sentences per text field; output one JSON object only.

| Role | Input context | Output JSON |
|---|---|---|
| `market` | metrics + rules + macro | `{signal, summary, points:[{text,evidence}], data_gaps:[]}` |
| `news` | news | same |
| `fundamentals` | fmp + sec | same |
| `social` | social | same |
| `bull` / `bear` (turns alternate, bull first; each sees the 4 analyst outputs and the debate so far) | analysts (`agent:<role>`) + all evidence above | `{points:[{text,evidence}]}` (2–4 points) |
| `research_manager` (deep) | analysts + debate | `{lean: Rating, rationale, evidence}` |
| `trader` | manager + rules + metrics | `{stance:"enter"|"wait"|"avoid", rationale, evidence, suggested_stop, suggested_target}` |
| `aggressive` → `conservative` → `neutral` (each sees the earlier risk turns) | trader + manager + metrics + rules | `{view, suggested_position_pct, evidence}` |
| `portfolio_manager` (deep) | everything + memory (last 3 decisions for this ticker, last 3 lessons from other tickers, ids `memory:<id>`) | `{rating, summary, key_risks:[{text,evidence}], evidence}` |

If all four analysts have `no_data`, skip the debate and set rating `REVIEW`.

## 4. `validate.py`

- Schema check per role (required keys, enums, types). `signal` ∈ Signal, `rating`/`lean` ∈ the 5 ratings.
- Every evidence id ∈ the allowed ids for that call; drop points with no evidence (points must keep ≥1 evidence id).
- Number guard: every number in `text`/`summary`/`rationale`/`view` (regex, ignore years 1990–2035 and list counters) must match a number in the input context after rounding to 0, 1 or 2 dp, or ±0.5% relative; otherwise the output is invalid.
- Trader sanity: `suggested_stop < rules.entry < suggested_target`, both within `entry ± 4×atr14`; else set to `null` (keep the rest).
- Risk: `suggested_position_pct` in 0..30 else `null`.
- Invalid → one retry with the validation error appended to the user message. Still invalid: analyst → `null` (status `partial`); manager/PM → rating `REVIEW`; others → `null`.
- `agrees` is computed in code from the rating (SPEC mapping), not asked of the model.

## 5. `graph.py`

`review_ticker(conn, llm, ticker, horizon) -> run_id`: insert `agent_runs` (status running→ok/partial/error), log every call to `agent_messages` (also failed ones), build `final_json` = `AgentReview.review` exactly (incl. `rules` copied from `recommendations`) **plus** `evidence_index: {id: {label, value?, url?, published_at?}}` for every non-news, non-rule id given to any agent (e.g. `"metric:rsi14": {"label": "RSI 14", "value": "71.3"}`, `"social:reddit:abc": {"label": "<post title>", "url": …}`). The API resolves `evidence[]` from it. `sources_json` = status per source. Sum tokens. One ticker failing never stops the batch.

## 6. `memory.py`

- After a run with rating ≠ REVIEW: insert `agent_decisions` (`entry_close` filled at settle time = first close **after** `as_of`, like the reference).
- `settle(conn, llm)`: for unsettled decisions whose full window (entry + 5 trading days) has traded in `prices`: `return_pct`, SPY `benchmark_return_pct`, `alpha_pct`; one quick-model call `reflection` (2–4 sentences, cites the alpha, says if 5 days is too short to judge) → store. Called at the start of every `run`.

## 7. `run.py`

```
python -m agents.run [--horizon 1w] [--top 20] [--tickers TYL,GDDY] [--workers 2] [--fake] [--no-settle]
```
Default tickers = `recommendations` rows with `in_top=1` for the horizon, by score, top N. `--workers` = thread pool (each worker its own DB connection), default 2. `--fake` uses `FakeLLM` with valid canned outputs (for a dry run with no key). Prints per role: ok/retry/fail, ms, tokens; per ticker: rating; at the end: totals and source statuses. Exit non-zero only if every ticker failed. Refuse to run (clear message) if `AGENT_LLM_API_KEY` is missing and `--fake` is not set.

## 8. Tests — `Backend/tests/test_agents.py` (unittest, temp SQLite via `PLANWISE_DB`, no network)

Seed `prices` (≥ 250 days, ticker + SPY in `source_cache`), `news_items`, `recommendations`. Cover: full graph with `FakeLLM` → 13 calls in role order, one `agent_runs` row, `final_json` keys == contract; unknown evidence id → retry → second output accepted; invented number rejected; bad rating twice → `REVIEW`; trader stop above entry → `null`; all analysts `no_data` → REVIEW without debate calls; source raising → `unavailable` and the run is `partial`/`ok`, not crash; settle math (return/alpha) on seeded prices; JSON parsing with `<think>` and fences; the API key never appears in any stored `error`.

Also add the env var names from SPEC to `Backend/.env.example`.

Finish with: tests pass, `python -m agents.run --tickers TYL --fake` works. Report what you could not verify (e.g. live gateway).
