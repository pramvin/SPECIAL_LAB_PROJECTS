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
* [AI agent review](/architecture/agent-review.md) - Click analysis: three LLM analysts (chart, news, social) run when a user opens a stock; the home page has no AI (built, not merged)
* [Hourly news routine](/architecture/news-routine.md) - Scheduled job: archive headlines, score them, record price moves, refresh context data (draft)
* [Market context data](/architecture/market-context-data.md) - Earnings calendar, intraday volume, S&P 500 membership changes: data only, not in any score (draft)
* [Shadow Top 5 portfolios](/architecture/shadow-portfolios.md) - Eight recipes for picking a Top 5, logged daily and scored vs SPY with random controls (draft)
* [News sentiment](/architecture/news-sentiment.md) - Local ML label for headlines (replaces Laya), training data, limits
* [Wallet](/architecture/wallet.md) - Simulated $1,000 wallet, deposits, withdrawals, balance history
* [Simulated trading](/architecture/trading.md) - Long/short positions, leverage, P/L, closed trades
* [Financial idempotency](/architecture/idempotency.md) - SQLite request keys, atomic response storage, retries, and conflicts
* [Financial audit](/architecture/financial-audit.md) - Linked balance history, legacy migration, and safe failure diagnostics
* [Auth and security](/architecture/auth-security.md) - Login, hashing, rate limit, known limits
* [Data sources](/architecture/data-sources.md) - Prices, news, and sources not used

# Decisions

* [TradingView chart link](/decisions/tradingview-chart-link.md) - Ticker opens the chart in a new tab, no embedded widget
* [Apple-inspired light UI](/decisions/apple-inspired-ui.md) - Neutral surfaces, top navigation, system font, and one blue accent
* [Long and short simulated positions](/decisions/long-short-trading.md) - Recommendations stay long-only; the trading ledger supports both

# Runbooks

* [Daily refresh](/runbooks/daily-refresh.md) - Start backend/frontend and run the pipeline in order
* [Kaggle gateways](/runbooks/kaggle-gateways.md) - Start/stop the LLM gateway on Kaggle (Laya retired)

# Experiments

* [Results](/experiments/results.md) - Laya / FinBERT / LLM experiment results
* [Direction prediction](/experiments/direction-prediction.md) - Every up/down test (news, chart, RSI/MACD); retired 2026-11-06
