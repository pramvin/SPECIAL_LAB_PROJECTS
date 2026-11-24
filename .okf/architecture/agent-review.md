---
type: Architecture
title: Click analysis (AI agent review)
description: On click, three LLM analysts (chart, news, social) read one stock for 1 week and the result is stored in the DB; the home page has no AI (built 2026-11-24, local only, not pushed)
tags: [architecture, llm, agents]
status: draft
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-24T09:40:00Z }
sources:
  - id: spec
    resource: specs/click-analysis/SPEC.md
    title: Shared contract, table and API
---

User decision 2026-11-24: the home page uses **ML only** (rule score + big-move chance) and news; **AI runs only when a user opens a stock** (1 week only: on the home page and the stock page the 1 month and 3 months tabs show "Coming soon" and cannot be picked; the home page always lists the 1 week ideas).[^spec] This replaced the 12-agent review, the quick review and the hourly review job (all deleted; local only, not pushed).

# Flow

1. `/stock/{ticker}` calls `POST /api/analysis/{ticker}?horizon=1w`, then polls `GET` every 3 s (`Backend/app/analysis_api.py`, frontend `components/stock/`)
2. `agents/analyze.py` refreshes that ticker's Yahoo headlines now (`pipeline/news_live.py`), then runs the **market, news and social analysts in 3 parallel threads** (`BoundedSemaphore(3)`: the gateway allows 3 requests per key) and stores the result in table `stock_analysis`
3. Reuse: a finished run is reused for 30 min unless a newer non-noise headline exists · one running row per ticker · a running row older than 15 min is treated as dead

# What the page shows

- **Chart read** (LLM): support and resistance picked only from levels the code computed (swing lows/highs, SMA, Bollinger), momentum, volume, summary
- **This week's news**: counts and per-headline labels come from the local sentiment model (code, not the LLM); the LLM writes only direction and summary · the gauge needle is (positive − negative) / all headlines, so neutral headlines stay in the middle (the API still sends `positive_share`, now unused by the page) · labels can be wrong
- **Social**: StockTwits works; Reddit anonymous access is blocked (403), so it shows as unavailable
- Number guard kept: sentences with unseen numbers are dropped (`agents/validate.py`) · no Buy/Sell rating, no fundamentals, SEC or macro any more

# Checks (2026-11-24)

- Backend suite 318 tests OK (needs `httpx2` in the venv for `TestClient`; not in `requirements.txt`) · frontend `tsc`, `eslint`, `build` clean
- Real run on a scratch DB with `gateway.9arm.co` qwen3.8-27b-fp8 and synthetic prices: status `ok`, 3 calls, 9,183 tokens, 160 s · fake-LLM run also fine · not run on Neon or with real prices, and the quality of the text is not validated
- LLM: main model `AGENT_LLM_*`, backup model `AGENT_LLM_FALLBACK_*` (both in `Backend/.env`; user order 2026-11-24: qwen gateway first, xAI `grok-4.3` as backup) · with a backup set, the main model gets one try with a 50 s read timeout (`config.PRIMARY_TIMEOUT`) and any failure or silence hands that call to the backup (`llm_client.FallbackLLM`) · tested live 2026-11-24: qwen answered `503 no approved route` and JNJ finished on grok in 29 s, 5,218 tokens; the 50 s silent case is covered by unit tests only · qwen alone took 160 s to 6.6 min per stock, xAI 18 to 29 s

[^spec]: specs/click-analysis/SPEC.md
