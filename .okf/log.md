# Update Log

## 2026-11-24
* **Replaced**: the 12-agent review, the quick review, the hourly review job and the AI news filter are superseded by the click analysis (three analysts, run when a stock is opened, stored in `stock_analysis`); the home page no longer shows any AI output — [AI agent review](/architecture/agent-review.md).
* **Retired**: the SEC, fundamentals and macro data in the AI step, the bull/bear, trader, risk and portfolio-manager roles, and the Buy/Overweight/Hold/Underweight/Sell ratings.

## 2026-11-22
* **Replaced**: the agent review prompts and data. The short prompts and the FMP fundamentals source are superseded by the full TradingAgents instructions and Yahoo Finance fundamentals, indicators and macro; the old tab layout of the AI panel is superseded by the verdict card with a More info area — [AI agent review](/architecture/agent-review.md).
* **Retired**: unused frontend dashboard, sidebar and mobile top bar components with their mock data, the FMP fetchers, and `triage.is_triage`; all repository files are now in English.

## 2026-11-21
* **Replaced**: the agent review's LLM is back on `gateway.9arm.co` (qwen3.8-27b-fp8) by user choice, superseding xAI `grok-4.3`; the gateway answered without a visible 503 but a full review takes ~16 min — [AI agent review](/architecture/agent-review.md).

## 2026-11-18
* **Replaced**: the agent review's LLM `gateway.9arm.co` (qwen3.8-27b-fp8) is superseded by xAI `grok-4.3`; the gateway was too slow and could not disable thinking — [AI agent review](/architecture/agent-review.md).

## 2026-11-06
* **Retired**: Laya (the Kaggle event/filler/sentiment model) and its filler step are removed from code and UI; the local ML headline label replaces it — [News sentiment](/architecture/news-sentiment.md). The Kaggle runbook now covers the LLM only — [Kaggle gateways](/runbooks/kaggle-gateways.md).
* **Retired**: up/down prediction as a product claim, after every test failed — [Direction prediction](/experiments/direction-prediction.md).

## 2026-11-01
* **Creation**: Created this knowledge bundle in OKF v0.2 format in place of the old `memory-bank/` (older history lives in git) — [Index](/index.md).
* **Deprecation**: `memory-bank/` and the old read/write rules in `CLAUDE.md` are replaced by `.okf/` and the `okf` skill in `.claude/skills/` — [Project brief](/project/brief.md).
