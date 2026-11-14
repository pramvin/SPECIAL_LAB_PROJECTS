---
type: Architecture
title: Simulated trading
description: Long and short positions, leverage, wallet deductions, and closed-trade P/L history.
tags: [backend, database]
generated: { by: opencode/deepseek-flash, at: 2026-11-13T17:37:52Z }
sources:
  - id: code
    resource: Backend/app/trading.py
    title: Trading module
---

# Overview

Simulated positions use the latest close in `prices` for entry and exit. Trade ideas remain long-only; this ledger supports **long and short** positions because it is a separate simulation layer.

# Schema

- `positions`: open trades with `ticker`, `side`, `entry_price`, `quantity`, `leverage`, `amount_deducted`, `notional`, `opened_at`
- `trades`: closed trades with `exit_price`, `pnl`, `pnl_pct`, `opened_at`, `closed_at`

All tables use `CREATE TABLE IF NOT EXISTS` and are created when the router is included in `main.py`.

# Rules

- `amount` is the cash margin deducted from the wallet.
- `notional = amount × leverage`
- `quantity = notional ÷ entry_price`
- Leverage is **1–10**, default `1`.
- Long P/L: `(exit − entry) × quantity`
- Short P/L: `(entry − exit) × quantity`
- `pnl_pct = pnl ÷ amount_deducted × 100`
- On close, `amount_deducted + pnl` is returned to the wallet.
- A leveraged loss may make the wallet balance negative; the UI must warn rather than hide it.
- Multiple positions per ticker are allowed.

# Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/positions` | Open positions with current price and unrealized P/L |
| POST | `/api/positions` | Open a position |
| POST | `/api/positions/{id}/close` | Close a position and write a trade |
| GET | `/api/trades` | Closed-trade history |

# Cautions

- Entry/exit prices come from the latest `prices` close, not the frontend.
- Test against a copy of the DB; never commit `Backend/planwise.db`.
- All routes require the existing `session` cookie.
