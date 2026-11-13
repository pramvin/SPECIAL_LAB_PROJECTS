---
okf_version: "0.2"
---

# Project

* [Project brief](/project/brief.md) - Scope, locked decisions, hard rules (**read every time**)
* [Active context](/project/active-context.md) - Open problems, pending decisions, next steps (**read every time**)
* [Progress](/project/progress.md) - Status of the 8 pipeline stages and remaining tasks
* [Product context](/project/product-context.md) - Problem, solution, main flow, trust principles
* [Team](/project/team.md) - Who owns what, and PR status
* [Verification layer](/project/verification-layer.md) - Numeric confirmation proposal (not approved)

# Architecture

* [System patterns](/architecture/system-patterns.md) - Pipeline structure and patterns in use
* [Scoring](/architecture/scoring.md) - Scoring formula and ATR stop/target (guessed values, not backtested)
* [Tech context](/architecture/tech-context.md) - Stack, ports, tooling cautions
* [Auth and security](/architecture/auth-security.md) - Login, hashing, rate limit, known limits
* [Data sources](/architecture/data-sources.md) - Prices, news, FMP, and sources not used

# Decisions

* [TradingView chart link](/decisions/tradingview-chart-link.md) - Ticker opens the chart in a new tab, no embedded widget
* [Apple-inspired light UI](/decisions/apple-inspired-ui.md) - Neutral surfaces, top navigation, system font, and one blue accent

# Runbooks

* [Daily refresh](/runbooks/daily-refresh.md) - Start backend/frontend and run the pipeline in order
* [Kaggle gateways](/runbooks/kaggle-gateways.md) - Start/stop Laya + LLM on Kaggle

# Experiments

* [Results](/experiments/results.md) - Laya / FinBERT / LLM experiment results
* [Direction prediction](/experiments/direction-prediction.md) - Every up/down test (news, chart, RSI/MACD); retired 2026-11-06
