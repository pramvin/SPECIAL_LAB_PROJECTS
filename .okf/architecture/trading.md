---
type: Architecture
title: Simulated trading
description: Long and short positions, leverage, wallet deductions, and closed-trade P/L history.
tags: [backend, database]
generated: { by: codex/gpt-6, at: 2026-11-20T17:59:32Z }
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

The router creates `prices`, `positions`, and `trades` at startup. Trading and ingest upgrade existing SQLite `prices` with internal `observed_at_ns` metadata (legacy rows default to zero).

# Rules

- `amount` is the cash margin deducted from the wallet.
- Opening's final debit uses the shared funds guard; rejection retains HTTP 409 and outer rollback removes the position. SQLite opening allocates an integer ID above both live IDs and retained `trades.position_id`, under writer protection. Closed-trade IDs must not be purged; existing reused IDs are not repaired.
- SQLite closing fetches the external quote after an owner-filtered lookup and before acquiring writer protection. The protected `DELETE ... RETURNING` rereads and claims the owned position; only its winner saves the price, trade, and signed settlement. Losers retain HTTP 404. The outer transaction rolls back all database changes on failure, including failed commit. Default/WAL tests verify deposits finish during paused quote fetching, concurrent closes settle once, and quote failures leave financial state unchanged; other engines remain unverified.
- Shared SQLite price-cache upserts atomically accept only a strictly newer local receipt timestamp for the same ticker/date; equal or older observations leave all OHLCV fields unchanged. Trading and ingest use the same rule. Each trade settles from its own fetched quote even when that quote loses the cache comparison. Receipt time is local observation ordering, not a provider freshness guarantee.
- Open/close endpoints support optional SQLite [financial idempotency](/architecture/idempotency.md). Keyed requests prepare quotes before the protected second key lookup and atomically store the successful response with settlement.
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
