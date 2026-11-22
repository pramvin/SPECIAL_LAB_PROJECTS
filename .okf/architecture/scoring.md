---
type: Scoring Rules
title: Scoring and ATR stop/target
description: The scoring formula, filters, and ATR multipliers in pipeline/rank.py (guessed values, not backtested)
tags: [architecture, scoring]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-22T09:00:00Z }
---

⚠ All weights and multipliers are **guesses, not backtested** (task T8 in [Progress](/project/progress.md))

- **Score:** percentile of momentum, volume ratio, and low volatility, weighted per horizon (`pipeline/rank.py`)
- **Filters:** liquidity ≥ $50M/day · price > SMA50 (+SMA200 for 1m/3m) · at most 25% above SMA50
- **Personal fit (served by `/api/recommendations`):** `final = 0.7*score + 0.3*100*cosine(stock, user)` · constants in `app/matching.py` are guesses
- **Storage:** every stock that passes is saved in `recommendations` (~144–171 per horizon) with `atr_pct`; `in_top=1` marks the curated list (≤ 4 per sector, top 20) · `/api/recommendations` serves **5 per horizon** (`TOP_N_SERVED`): the first 5 of the curated list for users without a profile, the 5 best by personal fit over all passing stocks for users with one

- **Card fields:** Entry = last daily close in `prices` (not live) · `BUY` is the column default (long-only, no sell logic) · Score is a real calculation from real prices but unvalidated · Stop, Target, Position and "you lose about X%" are still computed by the backend (`/api/recommendations`: position capped by risk level 10/20/30% and the user's max loss) but **the web card does not show them** (user decision 2026-11-21: multipliers are guesses, unvalidated); the card shows only Current price, Entry and Score · the Reasons list no longer has the "stop Nx ATR, target Nx ATR" sentence (`rank.py` fixed 2026-11-21 and Neon re-ranked the same day, 0 of 549 rows still have it, checked card by card on all three horizons; the local `planwise.db` keeps it until `rank` runs on it) · the card's **News column** is filled by the API from `news_items` (newest 3 non-noise headlines per ticker, `latest_headlines` in `app/main.py`); `recommendations.news` is written empty by `rank.py`, which is why every card used to say "No recent headlines found" while the AI and the News mood box showed headlines (fixed 2026-11-22) · a stock with no stored headlines (BDX, TECH, MTD) still shows the empty message, because the news collector found none

| Horizon | stop | target |
|---|---|---|
| 1w | 2x ATR | 3x ATR |
| 1m | 3x ATR | 5x ATR |
| 3m | 4.5x ATR | 8x ATR |

Pipeline structure: [System patterns](/architecture/system-patterns.md)
