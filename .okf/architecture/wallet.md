---
type: Architecture
title: Wallet
description: Simulated USD wallet with deposits, withdrawals, and balance-history snapshots.
tags: [backend, database]
generated: { by: opencode/deepseek-flash, at: 2026-11-13T17:37:52Z }
sources:
  - id: code
    resource: Backend/app/wallet.py
    title: Wallet module
---

# Overview

Each user gets one simulated wallet. It starts at **$1,000** and is created lazily on first access. No real money or bank connection is involved.

# Schema

- `wallets`: `user_id` primary key, `balance`, `starting_balance`, `created_at`, `updated_at`
- `wallet_transactions`: deposit/withdraw log with `amount`, `balance_after`, `note`, `created_at`
- `balance_history`: one snapshot after every wallet change, used for the percentage up/down chart

All tables use `CREATE TABLE IF NOT EXISTS` and are created when the router is included in `main.py`.

# Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/wallet` | Current balance and % change from $1,000 |
| POST | `/api/wallet/deposit` | Add simulated funds |
| POST | `/api/wallet/withdraw` | Remove simulated funds |
| GET | `/api/wallet/transactions` | Deposit/withdraw log |
| GET | `/api/wallet/history` | Chronological balance snapshots |

Withdrawals fail with `409` when the balance is insufficient. Trades also update the wallet through internal helpers, but only deposit and withdraw appear in `wallet_transactions`.

# Cautions

- Test against a copy of the DB (`PLANWISE_DB=/path/copy.db`).
- Never commit `Backend/planwise.db`.
- All routes require the existing `session` cookie.
