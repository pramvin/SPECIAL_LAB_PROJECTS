---
type: Progress
title: Stage and task status
description: Status of the 8 pipeline stages and the tasks still open
tags: [status]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-22T09:00:00Z }
---

Status: ✅ Done · 🟡 Built, unvalidated · ⬜ Todo · ⏸ Deferred (user brings it back) · ❌ Dropped

| # | Stage | Status | Files |
|---|---|---|---|
| 0 | Prices | ✅ | `pipeline/ingest.py` |
| 1 | Earnings trigger | ⏸ | |
| 2 | Yahoo Finance news (was Google News) | ✅ | `pipeline/news.py` |
| 2 | SEC EDGAR, Reddit, StockTwits, Yahoo fundamentals | ⬜ spec'd, part of the agent review | [AI agent review](/architecture/agent-review.md) |
| 2 | X/influencer | ❌ | |
| 3 | Source check | ⬜ | |
| 4 | News sentiment (local ML; replaces the Laya filter) | 🟡 trained, labels unvalidated | `pipeline/sentiment.py`, `models/news_sentiment_model.joblib` · [News sentiment](/architecture/news-sentiment.md) |
| 5 | LLM analysis | 🟡 old single call · ⬜ multi-agent review spec'd | `pipeline/llm.py` · new: `Backend/agents/` ([AI agent review](/architecture/agent-review.md)) |
| 6 | Risk/size (ATR) | ✅ | `pipeline/rank.py`, `app/main.py` |
| 7 | Idea cards UI | ✅ (`ReasonText` link bug) | `frontend/src/components/ideas/` |
| 8 | Backtest/event study | ⬜ | |

# Open tasks

| ID | Task | Status |
|---|---|---|
| T0 | User labels `Backend/experiments/to_label.csv` (200 rows) | ⬜ waiting on user |
| T1 | Evaluate the sentiment labels (and the LLM) against the user's labels | ⬜ after T0 |
| T2 | Stage 3 source tier + corroboration | ⬜ |
| T3 | Retire Laya: code removed, UI redesigned, Kaggle notebook still has Laya cells | 🟡 clean the notebook |
| T4 | SEC EDGAR (inside the agent review) | ⬜ |
| T5 | LLM: rerun after `rank`, feed filtered news, check against labels | 🟡 |
| T6 | UI: credibility badge, fix `ReasonText` (Laya chip replaced by ML labels + News mood bar) | 🟡 |
| T7 | Earnings trigger: the calendar and surprise data are now collected (T19), no trigger or filter uses them yet | 🟡 |
| T8 | Backtest, event study, latency (state survivorship bias) · the S&P 500 join/leave log exists but only 40% of stocks removed since 2016 still have Yahoo prices (T19) | ⬜ |
| T11 | Numeric confirmation layer | ⬜ waiting on user approval · [Verification layer](/project/verification-layer.md) |
| T12 | Per-stock sentiment questionnaire | 🟡 backend ready, no UI |
| T14 | AI agent review: engine + API + UI built (PR #13) · prompts rewritten from TradingAgents with Yahoo fundamentals, indicators, macro (2026-11-22; full review about 150-220k tokens and 15-25 min per stock, quick about 7.5k) · card redesigned: one-sentence verdict, four lights, how to act, change-if, details under More info · the 5 curated 1w stocks and the 15 cards of one Healthcare profile were rerun on Neon; other profiles' quick reviews (about 37 pairs) still have the old short text · AI ratings are unvalidated · next: user tests, merge | 🟡 · [AI agent review](/architecture/agent-review.md) |
| T13 | Personalized matching (branch `fais-questionire`): step 1 store all filtered stocks + `atr_pct` ✅ · step 2 matcher `app/matching.py` + `tests/test_matching.py` ✅ · step 3 API `/api/recommendations` ranks all stocks per user + UI shows match reasons ✅ · onboarding now 11 GICS sectors ✅ · real data needs `ingest` + `rank` ⬜ | 🟡 |
| T14 | Big-move badge (chart-only model, 1w): train on Kaggle ✅ · serve in `rank.py` + API + UI badge ✅ · needs real `ingest` + `rank` to show numbers ⬜ | 🟡 |
| T15 | Direction (up/down) prediction from news, chart, RSI/MACD, ML | ❌ dropped 2026-11-06 · [Direction prediction](/experiments/direction-prediction.md) |
| T16 | News sentiment: Laya removed, local ML model trained on Kaggle (2026-11-06), `pipeline.sentiment` run on 530 headlines, card UI shows labels + News mood bar ✅ · headlines exist for only 12 tickers, so run `pipeline.news` for the current ideas ⬜ · labels unvalidated vs humans ⬜ | 🟡 |
| T18 | Hourly news routine: archive, score, price reaction after each headline, quick AI review of the ideas the web serves, AI news filter, local LaunchAgent (built 2026-11-21, ran on Neon) | 🟡 · [Hourly news routine](/architecture/news-routine.md) |
| T19 | Market context data (earnings calendar, intraday volume, S&P 500 membership log) and shadow Top 5 portfolios (8 recipes incl. 2 random controls, scored vs SPY): built 2026-11-21 with 36 tests, tried on a scratch DB only, intraday not yet seen on a live session, no results yet · Neon refreshed by hand on 2026-11-21 (ingest + rank) and shadow day 1 logged; a daily ingest + rank is not scheduled ⬜ | 🟡 · [Market context data](/architecture/market-context-data.md) · [Shadow Top 5 portfolios](/architecture/shadow-portfolios.md) |
| T17 | Wallet + trading DB: `wallet.py` / `trading.py`, startup schema, endpoints, tests, docs | 🟡 due Friday |

Experiment results: [Results](/experiments/results.md)
