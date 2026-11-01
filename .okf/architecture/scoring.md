---
type: Scoring Rules
title: Scoring and ATR stop/target
description: The scoring formula, filters, and ATR multipliers in pipeline/rank.py (guessed values, not backtested)
tags: [architecture, scoring]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-01T06:40:00Z }
---

⚠ All weights and multipliers are **guesses, not backtested** (task T8 in [Progress](/project/progress.md))

- **Score:** percentile of momentum, volume ratio, and low volatility, weighted per horizon (`pipeline/rank.py`)
- **Filters:** liquidity ≥ $50M/day · price > SMA50 (+SMA200 for 1m/3m) · at most 25% above SMA50 · ≤ 4 per sector

| Horizon | stop | target |
|---|---|---|
| 1w | 2x ATR | 3x ATR |
| 1m | 3x ATR | 5x ATR |
| 3m | 4.5x ATR | 8x ATR |

Pipeline structure: [System patterns](/architecture/system-patterns.md)
