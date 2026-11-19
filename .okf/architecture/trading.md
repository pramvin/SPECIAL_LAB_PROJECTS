---
type: Architecture
title: Simulated trading
description: Long and short positions, leverage, wallet deductions, and closed-trade P/L history.
tags: [backend, database]
generated: { by: copilot-sdk/ai-assistant, at: 2026-11-17T00:49:47+08:00 }
sources:
  - id: code
    resource: Backend/app/trading.py
    title: Trading module
---

# Overview

Simulated positions fetch the latest daily bar from Yahoo Finance for entry and close, then upsert it into `prices`. Prices are not real-time. Trade ideas remain long-only; this ledger supports **long and short** positions because it is a separate simulation layer.

# Schema

- `positions`: open trades with `ticker`, `side`, `entry_price`, `quantity`, `leverage`, `amount_deducted`, `notional`, `opened_at`
- `trades`: closed trades with `exit_price`, `pnl`, `pnl_pct`, `opened_at`, `closed_at`

The router creates `prices`, `positions`, and `trades` with `CREATE TABLE IF NOT EXISTS` at startup. The pipeline and trading module use the same `prices` schema.

# Rules

- `amount` is the cash margin deducted from the wallet.
- `notional = amount × leverage`
- `quantity = notional ÷ entry_price`
- Leverage is **1–10**, default `1`.
- Long P/L: `(exit − entry) × quantity`
- Short P/L: `(entry − exit) × quantity`
- `pnl_pct = pnl ÷ amount_deducted × 100`
- On close, `amount_deducted + pnl` is returned to the wallet.
- Win rate = winning closed trades ÷ all closed trades; break-even trades remain in the denominator.
- Win rate and average/best/worst trade metrics are `null` until a closed trade exists.
- A leveraged loss may make the wallet balance negative; the UI must warn rather than hide it.
- Multiple positions per ticker are allowed.
- Summary metrics aggregate all of the signed-in user's trades. Unrealized P/L is unknown (`null`) if any open position lacks a saved daily price.

# Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/positions` | Open positions with current price and unrealized P/L |
| POST | `/api/positions` | Open a position |
| POST | `/api/positions/{id}/close` | Close a position and write a trade |
| GET | `/api/trades` | Paginated history; optional ticker `search`, `side`, and `outcome` filters |
| GET | `/api/trading/summary` | All-time realized/unrealized P/L, trade outcome counts, win rate, and open margin |

# Frontend

`/wallet` includes the open-position form, sortable open positions, a confirmation step before closing, all-time performance metrics, and searchable/filterable closed-trade history with pagination. If the DB has no `prices` row for a ticker, the form shows the backend error instead of creating a position. Close confirmation identifies the saved daily close as an estimate; the actual close fetches a fresh daily bar.

# Cautions

- Entry/exit prices use Yahoo Finance daily bars, not the frontend or a real-time feed. If the provider is unavailable, open/close fails explicitly rather than reusing a stale price.
- Test against a copy of the DB; never commit `Backend/planwise.db`.
- All routes require the existing `session` cookie.
