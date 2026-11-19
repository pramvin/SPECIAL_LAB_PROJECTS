---
type: Progress
title: Stage and task status
description: Status of the 8 pipeline stages and the tasks still open
tags: [status]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-18T05:00:00Z }
---

Status: ✅ Done · 🟡 Built, unvalidated · ⬜ Todo · ⏸ Deferred (user brings it back) · ❌ Dropped

| # | Stage | Status | Files |
|---|---|---|---|
| 0 | Prices | ✅ | `pipeline/ingest.py` |
| 1 | Earnings trigger | ⏸ | |
| 2 | Yahoo Finance news (was Google News) | ✅ | `pipeline/news.py` |
| 2 | SEC EDGAR, Reddit, StockTwits, FMP fundamentals | ⬜ spec'd, part of the agent review | [AI agent review](/architecture/agent-review.md) |
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
| T7 | Earnings trigger + scheduler | ⏸ |
| T8 | Backtest, event study, latency (state survivorship bias) | ⬜ |
| T11 | Numeric confirmation layer | ⬜ waiting on user approval · [Verification layer](/project/verification-layer.md) |
| T12 | Per-stock sentiment questionnaire | 🟡 backend ready, no UI |
| T14 | AI agent review: engine + API + UI built (uncommitted) · 6 stocks reviewed live on Grok 4.3 (2–5 min each) · quick one-call review (`--mode triage`/`funnel`) built 2026-11-19: ~24x fewer tokens per stock, tested on 20 ideas · next: user tests, then funnel on the top 100 | 🟡 · [AI agent review](/architecture/agent-review.md) |
| T13 | Personalized matching (branch `fais-questionire`): step 1 store all filtered stocks + `atr_pct` ✅ · step 2 matcher `app/matching.py` + `tests/test_matching.py` ✅ · step 3 API `/api/recommendations` ranks all stocks per user + UI shows match reasons ✅ · onboarding now 11 GICS sectors ✅ · real data needs `ingest` + `rank` ⬜ | 🟡 |
| T14 | Big-move badge (chart-only model, 1w): train on Kaggle ✅ · serve in `rank.py` + API + UI badge ✅ · needs real `ingest` + `rank` to show numbers ⬜ | 🟡 |
| T15 | Direction (up/down) prediction from news, chart, RSI/MACD, ML | ❌ dropped 2026-11-06 · [Direction prediction](/experiments/direction-prediction.md) |
| T16 | News sentiment: Laya removed, local ML model trained on Kaggle (2026-11-06), `pipeline.sentiment` run on 530 headlines, card UI shows labels + News mood bar ✅ · headlines exist for only 12 tickers, so run `pipeline.news` for the current ideas ⬜ · labels unvalidated vs humans ⬜ | 🟡 |
| T17 | Wallet + trading DB: `wallet.py` / `trading.py`, startup schema, endpoints, tests, docs | 🟡 due Friday |

Experiment results: [Results](/experiments/results.md)
