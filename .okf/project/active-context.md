---
type: Active Context
title: Current focus
description: Open problems, pending user decisions, and next steps (the most frequently updated file)
tags: [active]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-19T10:00:00Z }
---

**Focus:** direction (up/down) prediction is **retired** (user, 2026-11-06): no test beat "always up" or the shuffled control, see [Direction prediction](/experiments/direction-prediction.md). The app may claim only the **big-move chance** badge (chart-only, AUC 0.674 on 2023–2026) and stock matching, not "predicts up/down". Next: build the **AI agent review** (user, 2026-11-17): a TradingAgents-style team of LLM agents reviews each home-page idea; built by two OpenCode agents (uncommitted, all tests pass) and live-tested on Grok 4.3; on 2026-11-19 a cheap one-call **quick review** (triage, then funnel to the full 12-agent review) was added so many more stocks can get an AI opinion · see [AI agent review](/architecture/agent-review.md). Also pending: the 2-hour news refresh on GitHub (see Waiting on the user).

No Kaggle session is running (stopped 2026-11-06); a draft notebook `faislol/notebook9b0675f2f8` remains on the user's Kaggle (not saved as a version).

# Git status

- `main` = `e645e50` · PR #1–#7 merged, including the frontend redesign and local ML news sentiment · see [Team](/project/team.md)
- Current branch: `fais-yahoo-news` (Yahoo Finance news + `.github/workflows/refresh-news.yml`; committed, **not pushed**, no PR) · Neon Postgres is live for data, Render still lacks `DATABASE_URL`
- Ask before committing or pushing (rule in `AGENTS.md`)

# Wallet and trading database (Vincent, due Friday)

`Backend/app/wallet.py` and `Backend/app/trading.py` follow the watchlist pattern: own `SCHEMA`, own `APIRouter`, included from `main.py` so tables are created at startup. Wallet starts at $1,000; deposits/withdrawals and balance snapshots are logged. Positions support long and short, leverage 1–10, latest `prices` close for entry/exit, and closed trades store P/L and P/L%. See [Wallet](/architecture/wallet.md) and [Simulated trading](/architecture/trading.md). Tests: `python -m unittest tests.test_wallet tests.test_trading`. The `/wallet` page now shows the balance, deposit/withdraw forms, history chart, open positions, closed trades, and transaction log.

# Personalized matching (in main via PR #5)

Done: `rank.py` stores every stock that passes the filters with `atr_pct` and `in_top` · `app/matching.py` ranks them per user (cosine on sector one-hot + calm/wild from ATR%; constants are guesses; tests: `python -m unittest tests.test_matching`) · `/api/recommendations` uses it for users with a profile, others get the curated `in_top` list · onboarding has 11 GICS sectors (old saved `consumer` still works) · cards show match reasons. A personalized top 20 can be all one sector (no per-sector cap). Still to do: the personalized top 20 can be all one sector · see [Progress](/project/progress.md) T13

# Big-move badge (in main via PR #5)

Model = chance a stock's next-5-day move is in the day's top 20% vs the market, up **or down** (not direction). Features: 10 chart indicators only (news added ≈0) · code `Backend/pipeline/bigmove_features.py` (shared train/serve), `bigmove_train.py` (+ `.ipynb` for Kaggle import), `pipeline/bigmove.py` (serve) · model `Backend/models/bigmove_model.joblib` (sklearn **1.9.1**, same as `requirements.txt`; trained through 2021-12, calibrated 2022) · test 2023–2026-10: AUC 0.674 vs 0.663 for the trivial "high 20-day volatility" rule, shuffled control 0.53, top group predicted 45.8% / actual 45.6% (base 20.1%) → real and calibrated, but almost all of it is volatility · details in [Results](/experiments/results.md) section I.
Wired: `rank.py` writes `recommendations.bigmove_p` · `/api/recommendations` returns it only for `1w` · `IdeasView.tsx` shows "Big-move chance N% · typical 20%" with a not-a-direction note, hidden when null · `tests/test_bigmove.py` passes (17 tests with matching).
Still to do: OpenCode left a silent `except` in `load_bundle` in `pipeline/bigmove.py` (a corrupt model file looks like "no model").

# Open problems

1. `ReasonText` (`IdeasView.tsx`) puts `[1]` on every link; ids not in `cited_news_ids` render as bare numbers
2. News sentiment labels are word-list copies: 64% Neutral, price words (down, slips, up) missed, no human labels yet · see [News sentiment](/architecture/news-sentiment.md)
3. LLM leans bullish (up 36 / down 2 / none 6)
4. The LLM does not use the sentiment labels (it reads every headline with `rule_noise=0`)
5. Per-stock questionnaire: backend only (`sentiment_responses`), no UI, no answers are saved
6. Session tokens are stored unhashed in the DB · see [Auth and security](/architecture/auth-security.md)

# Runtime status

- `planwise.db` has prices (last close 2026-11-02) and 879 ranked recommendations (333 with a big-move %), no example rows · 744 older Google News headlines for only 12 tickers (`pipeline.news` ran 2026-11-01; since 2026-11-17 the source is Yahoo Finance and has only been run on a scratch copy), so most cards show no news · 530 headlines scored by the local sentiment model on 2026-11-06 · no `llm_analysis` table
- Cards show a delayed Yahoo quote (`/api/quotes`) only for real (non-example) ideas
- The backend started from a tool session dies after 10 min → run it in the user's own terminal ([runbook](/runbooks/daily-refresh.md))
- The Kaggle link from the last run is dead and the values in `Backend/.env` are stale (`LAYA_URL`/`LAYA_TOKEN` there are unused now) → **stop any lingering session** to save GPU

# Waiting on the user

1. Approve source tiers + corroboration rule (Proposal)
2. Push `fais-yahoo-news`, merge to `main`, add the repo secret `DATABASE_URL` (Neon), then run the workflow once by hand (Actions → Run workflow) · it runs `pipeline.news` + `pipeline.sentiment` every 2 hours (cron, may lag 5–15 min, never run on GitHub yet) · prices are not refreshed by it (`pipeline.ingest` last ran for 2026-11-02) · also add `DATABASE_URL` on Render and reset the exposed Neon password
3. Want the per-stock questionnaire back in the UI? (the UI was removed)
4. For the agent review, `Backend/.env` already has the xAI key (`AGENT_LLM_*`, Grok 4.3, `AGENT_LLM_TRIAGE_MODEL` for the quick review); decide whether to run `--mode funnel` on the top 100 (about 100 quick calls plus up to 15 full reviews, uses xAI credits); still optional: `SEC_EDGAR_USER_AGENT` (contact email, gives fundamentals because FMP free key returns 402), `REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET`, `FRED_API_KEY` · refresh with `pipeline.ingest` + `pipeline.rank` + `pipeline.news` before real runs · real runs without `PLANWISE_DB` write to Neon and show on the live site (confirm first)
5. Numeric confirmation layer: [Verification layer](/project/verification-layer.md)

# Next

T14 agent review (includes T4 SEC and the `ReasonText` fix) → user tests → T0 (user labels) ∥ T2 → T1 → T7 when the user asks → T8 · task table: [Progress](/project/progress.md)

Experiments with code already written: `python -m pipeline.llm_ab --arm anon` (done) · `--arm think` (failed, keep think off) · results in [Results](/experiments/results.md)
