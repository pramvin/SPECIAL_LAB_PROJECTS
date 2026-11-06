---
type: Active Context
title: Current focus
description: Open problems, pending user decisions, and next steps (the most frequently updated file)
tags: [active]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-06T10:00:00Z }
---

**Focus:** direction (up/down) prediction is **retired** (user, 2026-11-06): no test beat "always up" or the shuffled control, see [Direction prediction](/experiments/direction-prediction.md). The app may claim only the **big-move chance** badge (chart-only, AUC 0.674 on 2023–2026) and stock matching, not "predicts up/down". Next: get real data into the DB (`ingest` then `rank`), then make Stage 5 (LLM) trustworthy and fix the UI bugs below.

No Kaggle session is running (stopped 2026-11-06); a draft notebook `faislol/notebook9b0675f2f8` remains on the user's Kaggle (not saved as a version).

# Git status

- `main` = `143ebaa` · PR #1–#4 (Han, Adrian, Vincent, Steven) merged 2026-11-01; PR #5 (matching, big-move badge, Log out button, experiment scripts) merged from `fais-questionire` · see [Team](/project/team.md)
- Ask before committing or pushing (rule in `AGENTS.md`)

# Personalized matching (in main via PR #5)

Done: `rank.py` stores every stock that passes the filters with `atr_pct` and `in_top` · `app/matching.py` ranks them per user (cosine on sector one-hot + calm/wild from ATR%; constants are guesses; tests: `python -m unittest tests.test_matching`) · `/api/recommendations` uses it for users with a profile, others get the curated `in_top` list · onboarding has 11 GICS sectors (old saved `consumer` still works) · cards show match reasons. A personalized top 20 can be all one sector (no per-sector cap). Still to do: run `ingest` then `rank` for real data (see Runtime status) · see [Progress](/project/progress.md) T13

# Big-move badge (in main via PR #5)

Model = chance a stock's next-5-day move is in the day's top 20% vs the market, up **or down** (not direction). Features: 10 chart indicators only (news added ≈0) · code `Backend/pipeline/bigmove_features.py` (shared train/serve), `bigmove_train.py` (+ `.ipynb` for Kaggle import), `pipeline/bigmove.py` (serve) · model `Backend/models/bigmove_model.joblib` (sklearn **1.9.1**, same as `requirements.txt`; trained through 2021-12, calibrated 2022) · test 2023–2026-10: AUC 0.674 vs 0.663 for the trivial "high 20-day volatility" rule, shuffled control 0.53, top group predicted 45.8% / actual 45.6% (base 20.1%) → real and calibrated, but almost all of it is volatility · details in [Results](/experiments/results.md) section I.
Wired: `rank.py` writes `recommendations.bigmove_p` · `/api/recommendations` returns it only for `1w` · `IdeasView.tsx` shows "Big-move chance N% · typical 20%" with a not-a-direction note, hidden when null · `tests/test_bigmove.py` passes (17 tests with matching).
Still to do: run `ingest` then `rank` on real data (DB has no prices; asked, not approved) · user to look at the UI · OpenCode left a silent `except` in `load_bundle` (a corrupt model file looks like "no model").

# Open problems

1. `ReasonText` (`IdeasView.tsx`) puts `[1]` on every link; ids not in `cited_news_ids` render as bare numbers
2. Laya labels look wrong on clear cases (good M&A news labeled Bearish) · no ground truth yet
3. LLM leans bullish (up 36 / down 2 / none 6)
4. Laya and the LLM are not connected yet (the LLM reads every headline with `rule_noise=0`)
6. `npm run dev` is broken: the script is `next dev --turbopack=false`, which Next 16.3.8 rejects → use `npx next dev --webpack` (waiting for the user to approve fixing `package.json`)
7. Per-stock questionnaire: backend only (`sentiment_responses`), no UI, no answers are saved
8. Session tokens are stored unhashed in the DB · see [Auth and security](/architecture/auth-security.md)

# Runtime status

- `planwise.db` = 12 seed rows (`is_example`) + 744 real Google News headlines for those 12 tickers (`pipeline.news` run 2026-11-01); no prices, no real ranking yet → run `ingest` then `rank` (asked, not yet approved)
- Cards show a delayed Yahoo quote (`/api/quotes`) only for real (non-example) ideas
- The backend started from a tool session dies after 10 min → run it in the user's own terminal ([runbook](/runbooks/daily-refresh.md))
- The Kaggle link from the last run is dead and the values in `Backend/.env` are stale → **stop any lingering session** to save GPU · news has no scores yet (`news_scores` empty → UI shows "not scored yet")

# Waiting on the user

1. Approve source tiers + corroboration rule (Proposal)
2. Approve the Laya criterion: no worse than FinBERT and ~75%+
3. Install a daily scheduled job for `pipeline.news`?
4. Hide the Laya sentiment chip until it is evaluated?
5. Want the per-stock questionnaire back in the UI? (the UI was removed)
6. Fix the `dev` script (`npm run dev` is broken, see Open problems)?
7. Email for the SEC User-Agent (when SEC comes back)
8. Numeric confirmation layer: [Verification layer](/project/verification-layer.md)

# Next

T0 (user labels) ∥ T2, T3, fix `ReasonText` → T1 → rerun T5 on filtered news + T6 → T4/T7 when the user asks → T8 · task table: [Progress](/project/progress.md)

Experiments with code already written: `python -m pipeline.llm_ab --arm anon` (done) · `--arm think` (failed, keep think off) · `python -m pipeline.disagree` flags 13/42 stocks where the LLM and Laya disagree · results in [Results](/experiments/results.md)
