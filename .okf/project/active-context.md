---
type: Active Context
title: Current focus
description: Open problems, pending user decisions, and next steps (the most frequently updated file)
tags: [active]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-24T09:00:00Z }
---

**Focus:** direction (up/down) prediction is **retired** (user, 2026-11-06): no test beat "always up" or the shuffled control, see [Direction prediction](/experiments/direction-prediction.md). The app may claim only the **big-move chance** badge (chart-only, AUC 0.674 on 2023–2026) and stock matching, not "predicts up/down". **New front end (user, 2026-11-24), built on local branch `feat/click-analysis`, not merged or pushed:** the home page is ML only (Top 5 per horizon, 3 newest headlines with sentiment pills, Buy/Sell, plus a Latest news box that refreshes Yahoo headlines on demand); opening a stock (1 week) starts three LLM analysts (chart, news, social) in parallel, stored in `stock_analysis` · the 12-agent review, quick review and hourly review job are deleted · see [AI agent review](/architecture/agent-review.md). Also pending: the 2-hour news refresh on GitHub (see Waiting on the user).

**Hourly news routine** (2026-11-21, user): a macOS LaunchAgent runs `pipeline.collect_hourly` every hour against Neon (headlines, local sentiment, price reaction after each headline, earnings calendar, intraday volume of the curated stocks, shadow Top 5) · no AI step since 2026-11-24 · not committed or pushed (user said no) · runs only while the Mac is awake · see [Hourly news routine](/architecture/news-routine.md).

**Direction of the product** (user, 2026-11-21): the app moves from "investment" toward short-term **trading**. The ideas list is now a **Top 5 per horizon** (`TOP_N_SERVED = 5` in `app/main.py`, was 20; user, 2026-11-21), narrowed by personal fit only (the existing sector + ATR volatility match; swapping ATR for `bigmove_p` is still undecided); no model that predicts up/down is planned, since every such test failed. Three data collectors were added first (earnings calendar, intraday volume, S&P 500 membership log) · see [Market context data](/architecture/market-context-data.md) · then a **shadow Top 5 tracker** that logs eight pick recipes daily (two are random controls) and scores them against SPY, so the choice is made by measurement · see [Shadow Top 5 portfolios](/architecture/shadow-portfolios.md). A literature search the user pasted (weekly/monthly ML papers) was checked: it does not contradict the failed tests here.

The idea card no longer shows Stop, Target or Position (removed for every stock, 2026-11-21, because the ATR multipliers are unbacktested guesses); the paper-trade panel has no suggested amount and no "if stop/target hit" rows.

No Kaggle session is running (stopped 2026-11-06); a draft notebook `faislol/notebook9b0675f2f8` remains on the user's Kaggle (not saved as a version).

# Git status

- `main` = `7c87543` (PR #19 merged) · local branch `feat/click-analysis` = main + three branches (`feat/click-analysis-engine`, `feat/live-news-api`, `feat/click-analysis-frontend`) + router wiring · nothing pushed · worktrees for the three branches are in `~/Desktop/planwise-wt/` (a, b, c) · Render deploys `main` automatically · Neon Postgres is live for data, Render still lacks `DATABASE_URL`
- Render deploys `main` automatically. The first deploy after merging #13 and #15 failed (2026-11-22): the merge dropped `idempotency` from the imports in `app/main.py`, so the app crashed at startup with a `NameError`; #18 fixed it and the live service was not checked (the Render dashboard needs the user's login) · Neon Postgres is live for data, Render still lacks `DATABASE_URL`
- Ask before committing or pushing (rule in `AGENTS.md`)

# Paper trading

`Backend/app/wallet.py` and `Backend/app/trading.py` follow the watchlist pattern: own `SCHEMA`, own `APIRouter`, included from `main.py` so tables are created at startup. Wallet starts at $1,000; deposits/withdrawals and balance snapshots are logged. Positions support long and short, leverage 1–10, latest `prices` close for entry/exit, and closed trades store P/L and P/L%. See [Wallet](/architecture/wallet.md) and [Simulated trading](/architecture/trading.md). Tests: `python -m unittest tests.test_wallet tests.test_trading`. Idea cards now have ★ Watch, Open/Close position (long only, 1–10x, fills at the latest daily close in the DB, not the live quote) and a header balance pill (P/L on total equity), all in `CardActions.tsx` / `BalancePill.tsx`; tried on a scratch DB only. The `/wallet` page now shows the balance, deposit/withdraw forms, history chart, open positions, closed trades, and transaction log.

# Personalized matching (in main via PR #5)

Done: `rank.py` stores every stock that passes the filters with `atr_pct` and `in_top` · `app/matching.py` ranks them per user (cosine on sector one-hot + calm/wild from ATR%; constants are guesses; tests: `python -m unittest tests.test_matching`) · `/api/recommendations` uses it for users with a profile, others get the curated `in_top` list · onboarding has 11 GICS sectors (old saved `consumer` still works) · cards show match reasons. A personalized Top 5 can be all one sector (a healthcare-only user gets five healthcare stocks; no per-sector cap). Still to do: decide on a sector cap for the Top 5 · see [Progress](/project/progress.md) T13

# Big-move badge (in main via PR #5)

Model = chance a stock's next-5-day move is in the day's top 20% vs the market, up **or down** (not direction). Features: 10 chart indicators only (news added ≈0) · code `Backend/pipeline/bigmove_features.py` (shared train/serve), `bigmove_train.py` (+ `.ipynb` for Kaggle import), `pipeline/bigmove.py` (serve) · model `Backend/models/bigmove_model.joblib` (sklearn **1.9.1**, same as `requirements.txt`; trained through 2021-12, calibrated 2022) · test 2023–2026-10: AUC 0.674 vs 0.663 for the trivial "high 20-day volatility" rule, shuffled control 0.53, top group predicted 45.8% / actual 45.6% (base 20.1%) → real and calibrated, but almost all of it is volatility · details in [Results](/experiments/results.md) section I.
Wired: `rank.py` writes `recommendations.bigmove_p` · `/api/recommendations` returns it only for `1w` · `IdeasView.tsx` shows "Big-move chance N% · typical 20%" with a not-a-direction note, hidden when null · `tests/test_bigmove.py` passes (17 tests with matching).
Still to do: OpenCode left a silent `except` in `load_bundle` in `pipeline/bigmove.py` (a corrupt model file looks like "no model").

# Open problems

1. Click analysis was run for real only on a scratch DB with synthetic prices (qwen, 160 s, 9,183 tokens); it has not run on Neon or with real prices, and the quality of the text is not validated · see [AI agent review](/architecture/agent-review.md)
2. News sentiment labels are word-list copies: 64% Neutral, price words (down, slips, up) missed, no human labels yet; the page tells users labels can be wrong · see [News sentiment](/architecture/news-sentiment.md)
3. Per-stock questionnaire: backend only (`sentiment_responses`), no UI, no answers are saved
4. Session tokens are stored unhashed in the DB · see [Auth and security](/architecture/auth-security.md)
5. Reddit has no keys, so the social box uses StockTwits only; `shadow.py` recipe `ai_veto` reads old `agent_runs` rows and now equals `rules`
6. `Backend/.venv` was created 2026-11-24 with `uv` from `requirements.txt` plus `httpx2` (tests need it; add it to `requirements.txt`?)

# Runtime status

- `planwise.db` has prices (last close 2026-11-02) and 879 ranked recommendations (333 with a big-move %), no example rows · 744 older Google News headlines for only 12 tickers (`pipeline.news` ran 2026-11-01; since 2026-11-17 the source is Yahoo Finance and has only been run on a scratch copy), so most cards show no news · 530 headlines scored by the local sentiment model on 2026-11-06 · no `llm_analysis` table
- A bare `uvicorn` backend reads the local `planwise.db` (it does not load `Backend/.env`, checked 2026-11-21) · the 2026-11-24 browser check used a scratch DB and the `backend-click-test` style launch (not kept in the repo)
- The web app reads Neon since 2026-11-21 (user: "read from Neon"): the backend on port 8000 runs from the launch config `backend-neon` in `.claude/launch.json` (loads `Backend/.env`; it reads and **writes** Neon: accounts, wallet, trades, watchlist, and local logins do not exist there) · `/api/data-status` shows the hourly job's data (2,139 headlines) · **only one backend may hold port 8000**: starting a plain `uvicorn` (local file) next to it puts the web back on the local data · viewed on a Neon test account 2026-11-21: Top 5 per horizon, ratings badges and the full review panel render
- Neon (what the hourly job and `backend-neon` use) was refreshed on 2026-11-21: prices to 2026-11-20 and ranked recommendations 1w 215 / 1m 167 / 3m 167 (20 curated each, `bigmove_p` on all 1w) · re-ranked once more the same day to drop the stop/target sentence from the Reasons (no other change) · every served card on the three horizons of the user's account showed no stop/target text (checked in the user's Chrome) · the card's News column now shows live headlines (it was empty on every card) · two UI test accounts (`@example.test`) created on Neon on 2026-11-22 are still there · the local `planwise.db` file above was not changed
- Cards show a delayed Yahoo quote (`/api/quotes`) only for real (non-example) ideas
- The backend started from a tool session dies after 10 min → run it in the user's own terminal ([runbook](/runbooks/daily-refresh.md))
- The Kaggle link from the last run is dead and the values in `Backend/.env` are stale (`LAYA_URL`/`LAYA_TOKEN` there are unused now) → **stop any lingering session** to save GPU

# Waiting on the user

1. Approve source tiers + corroboration rule (Proposal)
2. PR #13 is merged; add the repo secret `DATABASE_URL` (Neon), then run the workflow once by hand (Actions → Run workflow) · it runs `pipeline.news` + `pipeline.sentiment` every 2 hours (cron, may lag 5–15 min, never run on GitHub yet) · prices are not refreshed by it (`pipeline.ingest` last ran for 2026-11-02) · also add `DATABASE_URL` on Render and reset the exposed Neon password
3. Want the per-stock questionnaire back in the UI? (the UI was removed)
4. Real LLM runs: `Backend/.env` has `AGENT_LLM_*` for `gateway.9arm.co` (qwen first; xAI `grok-4.3` only if it fails, user 2026-11-24) · the click analysis spends about 9k tokens per opened stock · real runs without `PLANWISE_DB` write to Neon and show on the live site (confirm first) · optional: `REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET`
5. Numeric confirmation layer: [Verification layer](/project/verification-layer.md)
6. Matching: replace the guessed ATR volatility in `app/matching.py` with `bigmove_p` (the only validated signal, 1-week only)? The user was asked and has not answered "do it" or "not yet"
7. Schedule `pipeline.ingest` + `pipeline.rank` against Neon daily? Done once by hand on 2026-11-21 (user OK): Neon prices to 2026-11-20, ranking as of 2026-11-20 replaced all recommendations (old rows backed up in the session scratchpad only). They are not in the hourly job and `rank` replaces every recommendation on each run, so the shadow tracker stops logging after 4 days unless they are run daily

# Next

Review and test `feat/click-analysis` with real prices → merge to `main` when the user says → refresh `pipeline.ingest` + `pipeline.rank` on Neon · T0 (user labels) ∥ T2 → T1 → T7 when the user asks → T8 · task table: [Progress](/project/progress.md)

Experiments with code already written: `python -m pipeline.llm_ab --arm anon` (done) · `--arm think` (failed, keep think off) · results in [Results](/experiments/results.md)
