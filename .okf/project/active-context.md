---
type: Active Context
title: Current focus
description: Open problems, pending user decisions, and next steps (the most frequently updated file)
tags: [active]
generated: { by: opencode/deepseek-flash, at: 2026-11-13T17:37:52Z }
---

**Focus:** direction (up/down) prediction is **retired** (user, 2026-11-06): no test beat "always up" or the shuffled control, see [Direction prediction](/experiments/direction-prediction.md). The app may claim only the **big-move chance** badge (chart-only, AUC 0.674 on 2023–2026) and stock matching, not "predicts up/down". Next: fetch headlines for the current ideas (`pipeline.news`, then `pipeline.sentiment`), then make Stage 5 (LLM) trustworthy and fix the UI bugs below.

No Kaggle session is running (stopped 2026-11-06); a draft notebook `faislol/notebook9b0675f2f8` remains on the user's Kaggle (not saved as a version).

# Git status

- `main` = `e645e50` · PR #1–#7 merged, including the frontend redesign and local ML news sentiment · see [Team](/project/team.md)
- Current branch: `vincent-wallet-trading` (wallet + trading database, due Friday) · frontend work remains on `questionare-branch`
- Ask before committing or pushing (rule in `AGENTS.md`)

# Wallet and trading database (Vincent, due Friday)

`Backend/app/wallet.py` and `Backend/app/trading.py` follow the watchlist pattern: own `SCHEMA`, own `APIRouter`, included from `main.py` so tables are created at startup. Wallet starts at $1,000; deposits/withdrawals and balance snapshots are logged. Positions support long and short, leverage 1–10, latest `prices` close for entry/exit, and closed trades store P/L and P/L%. See [Wallet](/architecture/wallet.md) and [Simulated trading](/architecture/trading.md). Tests: `python -m unittest tests.test_wallet tests.test_trading`.

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

- `planwise.db` has prices (last close 2026-11-02) and 879 ranked recommendations (333 with a big-move %), no example rows · 744 Google News headlines for only 12 tickers (`pipeline.news` ran 2026-11-01), so most cards show no news · 530 headlines scored by the local sentiment model on 2026-11-06 · no `llm_analysis` table
- Cards show a delayed Yahoo quote (`/api/quotes`) only for real (non-example) ideas
- The backend started from a tool session dies after 10 min → run it in the user's own terminal ([runbook](/runbooks/daily-refresh.md))
- The Kaggle link from the last run is dead and the values in `Backend/.env` are stale (`LAYA_URL`/`LAYA_TOKEN` there are unused now) → **stop any lingering session** to save GPU

# Waiting on the user

1. Approve source tiers + corroboration rule (Proposal)
2. Run `pipeline.news` for the current ideas (about 9 minutes, Google News)? Install a daily scheduled job for it?
3. Want the per-stock questionnaire back in the UI? (the UI was removed)
4. Email for the SEC User-Agent (when SEC comes back)
5. Numeric confirmation layer: [Verification layer](/project/verification-layer.md)

# Next

T0 (user labels) ∥ T2, fix `ReasonText` → T1 → rerun T5 (LLM) + T6 → T4/T7 when the user asks → T8 · task table: [Progress](/project/progress.md)

Experiments with code already written: `python -m pipeline.llm_ab --arm anon` (done) · `--arm think` (failed, keep think off) · results in [Results](/experiments/results.md)
