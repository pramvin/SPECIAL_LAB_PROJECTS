---
type: Decision
title: Long and short simulated positions
description: The trading ledger supports long and short positions while stock recommendations stay long-only.
tags: [backend, trading]
status: stable
generated: { by: opencode/deepseek-flash, at: 2026-11-13T17:37:52Z }
---

# Decision

Stock recommendations remain **long-only**. The simulated trading ledger now supports **long and short** positions because Vincent's database assignment requires both.

# Rules

- Leverage range: **1–10**, default `1`.
- `amount` is cash margin deducted from the wallet.
- Notional position size = `amount × leverage`.
- Entry and exit prices come from the latest `prices` close.
- Negative wallet balances are allowed when a leveraged loss exceeds the margin.
- This is simulated trading only; no real orders, payments, or broker connection.

# Rationale

The original long-only lock covered trade ideas. The team asked for a separate position ledger that can demonstrate both directions without changing the recommendation rules.

# Related

- [Wallet](/architecture/wallet.md)
- [Simulated trading](/architecture/trading.md)
