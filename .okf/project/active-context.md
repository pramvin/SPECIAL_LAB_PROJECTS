---
type: Active Context
title: Current focus
description: Open problems, pending user decisions, and next steps (the most frequently updated file)
tags: [active]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-22T09:00:00Z }
---

**Focus:** direction (up/down) prediction is **retired** (user, 2026-11-06): no test beat "always up" or the shuffled control, see [Direction prediction](/experiments/direction-prediction.md). The app may claim only the **big-move chance** badge (chart-only, AUC 0.674 on 2023–2026) and stock matching, not "predicts up/down". Next: build the **AI agent review** (user, 2026-11-17): a TradingAgents-style team of LLM agents reviews each home-page idea; built by two OpenCode agents, live-tested on Grok 4.3 and, since 2026-11-21, on the `gateway.9arm.co` model chosen by the user, and committed in PR #13 (91 backend tests pass, tsc clean); on 2026-11-19 a cheap one-call **quick review** (triage, then funnel to the full 12-agent review) was added so many more stocks can get an AI opinion · see [AI agent review](/architecture/agent-review.md). Also pending: the 2-hour news refresh on GitHub (see Waiting on the user).

**Hourly news routine** (2026-11-21, user): a macOS LaunchAgent runs `pipeline.collect_hourly` every hour against Neon (headlines, local sentiment, price reaction after each headline, earnings calendar, intraday volume of the curated stocks, AI filter that sends flagged stocks to a quick review) · not committed or pushed (user said no) · runs only while the Mac is awake · see [Hourly news routine](/architecture/news-routine.md).

**Direction of the product** (user, 2026-11-21): the app moves from "investment" toward short-term **trading**. The ideas list is now a **Top 5 per horizon** (`TOP_N_SERVED = 5` in `app/main.py`, was 20; user, 2026-11-21), narrowed by personal fit only (the existing sector + ATR volatility match; swapping ATR for `bigmove_p` is still undecided); no model that predicts up/down is planned, since every such test failed. Three data collectors were added first (earnings calendar, intraday volume, S&P 500 membership log) · see [Market context data](/architecture/market-context-data.md) · then a **shadow Top 5 tracker** that logs eight pick recipes daily (two are random controls) and scores them against SPY, so the choice is made by measurement · see [Shadow Top 5 portfolios](/architecture/shadow-portfolios.md). A literature search the user pasted (weekly/monthly ML papers) was checked: it does not contradict the failed tests here.

The idea card no longer shows Stop, Target or Position (removed for every stock, 2026-11-21, because the ATR multipliers are unbacktested guesses); the paper-trade panel has no suggested amount and no "if stop/target hit" rows.

No Kaggle session is running (stopped 2026-11-06); a draft notebook `faislol/notebook9b0675f2f8` remains on the user's Kaggle (not saved as a version).

# Git status

- `main` = `e645e50` · PR #1–#7 merged, including the frontend redesign and local ML news sentiment · see [Team](/project/team.md)
- Current branch: `fais-agent-review`, pushed, **PR #13** open against `main` (agent review + the Yahoo news commit `130aeba` + `.github/workflows/refresh-news.yml`; mergeable) · Neon Postgres is live for data, Render still lacks `DATABASE_URL`
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

1. Check in the browser that real ROP/TYL reviews render `[n]` chips with no raw `metric:` ids (not yet seen)
2. News sentiment labels are word-list copies: 64% Neutral, price words (down, slips, up) missed, no human labels yet · see [News sentiment](/architecture/news-sentiment.md)
3. LLM leans bullish (up 36 / down 2 / none 6)
4. The LLM does not use the sentiment labels (it reads every headline with `rule_noise=0`)
5. Per-stock questionnaire: backend only (`sentiment_responses`), no UI, no answers are saved
6. The quick AI badge covers every served idea (hourly `review-served`); the curated 1w top 5 also has full reviews. Ratings are unvalidated: the old short prompts gave Overweight almost everywhere, the new detailed prompts gave Underweight for 4 of the 5 curated stocks, and neither has been backtested · reviews of other profiles still have the old short text · the AI sometimes writes its own stop prices in the how-to-act line although the rules' stop/target are no longer given to it · see [AI agent review](/architecture/agent-review.md)
7. Session tokens are stored unhashed in the DB · see [Auth and security](/architecture/auth-security.md)

# Runtime status

- `planwise.db` has prices (last close 2026-11-02) and 879 ranked recommendations (333 with a big-move %), no example rows · 744 older Google News headlines for only 12 tickers (`pipeline.news` ran 2026-11-01; since 2026-11-17 the source is Yahoo Finance and has only been run on a scratch copy), so most cards show no news · 530 headlines scored by the local sentiment model on 2026-11-06 · no `llm_analysis` table
- A bare `uvicorn` backend reads the local `planwise.db` (it does not load `Backend/.env`, checked 2026-11-21), so the web app then showed the 2026-11-02 entries and "AI pending" on every card · the card UI (Current price and Entry only, no Stop/Target/Position, no console errors) was viewed in the browser on that local data
- The web app reads Neon since 2026-11-21 (user: "read from Neon"): the backend on port 8000 runs from the launch config `backend-neon` in `.claude/launch.json` (loads `Backend/.env`; it reads and **writes** Neon: accounts, wallet, trades, watchlist, and local logins do not exist there) · `/api/data-status` shows the hourly job's data (2,139 headlines) · **only one backend may hold port 8000**: starting a plain `uvicorn` (local file) next to it puts the web back on the local data · viewed on a Neon test account 2026-11-21: Top 5 per horizon, ratings badges and the full review panel render
- Neon (what the hourly job and `backend-neon` use) was refreshed on 2026-11-21: prices to 2026-11-20 and ranked recommendations 1w 215 / 1m 167 / 3m 167 (20 curated each, `bigmove_p` on all 1w) · re-ranked once more the same day to drop the stop/target sentence from the Reasons (no other change) · every served card on the three horizons of the user's account showed an AI badge and no stop/target text (checked in the user's Chrome) · the card's News column now shows live headlines (it was empty on every card) · the 15 quick reviews on the user's cards were redone after the ATR fix · two UI test accounts (`@example.test`) created on Neon on 2026-11-22 are still there · the local `planwise.db` file above was not changed
- Cards show a delayed Yahoo quote (`/api/quotes`) only for real (non-example) ideas
- The backend started from a tool session dies after 10 min → run it in the user's own terminal ([runbook](/runbooks/daily-refresh.md))
- The Kaggle link from the last run is dead and the values in `Backend/.env` are stale (`LAYA_URL`/`LAYA_TOKEN` there are unused now) → **stop any lingering session** to save GPU

# Waiting on the user

1. Approve source tiers + corroboration rule (Proposal)
2. Review and merge PR #13 to `main`, add the repo secret `DATABASE_URL` (Neon), then run the workflow once by hand (Actions → Run workflow) · it runs `pipeline.news` + `pipeline.sentiment` every 2 hours (cron, may lag 5–15 min, never run on GitHub yet) · prices are not refreshed by it (`pipeline.ingest` last ran for 2026-11-02) · also add `DATABASE_URL` on Render and reset the exposed Neon password
3. Want the per-stock questionnaire back in the UI? (the UI was removed)
4. For the agent review, `Backend/.env` uses the `gateway.9arm.co` key (`AGENT_LLM_*`, qwen3.8-27b-fp8; the xAI lines are commented out); decide whether to run `--mode funnel` on the top 100 (about 100 quick calls plus up to 15 full reviews, ~16 min each on this gateway, uses credits); still optional: `SEC_EDGAR_USER_AGENT` (contact email, adds SEC filing facts; fundamentals already come from Yahoo), `REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET`, `FRED_API_KEY` · refresh with `pipeline.ingest` + `pipeline.rank` + `pipeline.news` before real runs · real runs without `PLANWISE_DB` write to Neon and show on the live site (confirm first)
5. Numeric confirmation layer: [Verification layer](/project/verification-layer.md)
6. Matching: replace the guessed ATR volatility in `app/matching.py` with `bigmove_p` (the only validated signal, 1-week only)? The user was asked and has not answered "do it" or "not yet"
7. Schedule `pipeline.ingest` + `pipeline.rank` against Neon daily? Done once by hand on 2026-11-21 (user OK): Neon prices to 2026-11-20, ranking as of 2026-11-20 replaced all recommendations (old rows backed up in the session scratchpad only). They are not in the hourly job and `rank` replaces every recommendation on each run, so the shadow tracker stops logging after 4 days unless they are run daily
8. Redo the quick reviews of the other profiles' served cards with the detailed prompts? About 37 pairs, about 7.5k tokens each (about 280k); the 5 curated 1w full reviews and one Healthcare profile's 15 cards were rerun on 2026-11-22 · full reviews for other horizons or profile lists cost about 150-220k tokens each

# Next

T14 agent review (includes T4 SEC and the `ReasonText` fix) → user tests → T0 (user labels) ∥ T2 → T1 → T7 when the user asks → T8 · task table: [Progress](/project/progress.md)

Experiments with code already written: `python -m pipeline.llm_ab --arm anon` (done) · `--arm think` (failed, keep think off) · results in [Results](/experiments/results.md)
