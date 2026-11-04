---
type: Scoring Rules
title: Scoring and ATR stop/target
description: The scoring formula, filters, and ATR multipliers in pipeline/rank.py (guessed values, not backtested)
tags: [architecture, scoring]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-01T11:00:00Z }
---

⚠ All weights and multipliers are **guesses, not backtested** (task T8 in [Progress](/project/progress.md))

- **Score:** percentile of momentum, volume ratio, and low volatility, weighted per horizon (`pipeline/rank.py`)
- **Filters:** liquidity ≥ $50M/day · price > SMA50 (+SMA200 for 1m/3m) · at most 25% above SMA50
- **Personal fit (served by `/api/recommendations`):** `final = 0.7*score + 0.3*100*cosine(stock, user)` · constants in `app/matching.py` are guesses
- **Storage:** every stock that passes is saved in `recommendations` (~144–171 per horizon) with `atr_pct`; `in_top=1` marks the curated list (≤ 4 per sector, top 20) that `/api/recommendations` serves for now

| Horizon | stop | target |
|---|---|---|
| 1w | 2x ATR | 3x ATR |
| 1m | 3x ATR | 5x ATR |
| 3m | 4.5x ATR | 8x ATR |

Pipeline structure: [System patterns](/architecture/system-patterns.md)
