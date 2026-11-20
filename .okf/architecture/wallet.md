---
type: Architecture
title: Wallet
description: Simulated USD wallet with deposits, withdrawals, and balance-history snapshots.
tags: [backend, database]
generated: { by: codex/gpt-6, at: 2026-11-20T17:24:46Z }
sources:
  - id: code
    resource: Backend/app/wallet.py
    title: Wallet module
---

# Overview

Each user gets one simulated wallet. It starts at **$1,000** and is created at registration; existing accounts get one on first access. No real money or bank connection is involved.

# Schema

- `wallets`: `user_id` primary key, `balance`, `starting_balance`, `created_at`, `updated_at`
- `wallet_transactions`: deposit/withdraw log with `amount`, `balance_after`, `note`, `created_at`
- `balance_history`: one snapshot after every wallet change, used for the percentage change chart from the initial balance

All tables use `CREATE TABLE IF NOT EXISTS` and are created when the router is included in `main.py`.

# Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/wallet` | Current balance and % change from $1,000 |
| POST | `/api/wallet/deposit` | Add simulated funds |
| POST | `/api/wallet/withdraw` | Remove simulated funds |
| GET | `/api/wallet/transactions` | Deposit/withdraw log; supports `limit`, `offset`, `search` (note/type), and `kind` |
| GET | `/api/wallet/history` | Chronological balance snapshots |

Withdrawals fail with `409` when the balance is insufficient. Trades also update the wallet through internal helpers, but only deposit and withdraw appear in `wallet_transactions`.

# Mutation protection

`change_balance` is the shared mutation path. SQLite acquires writer protection before the authoritative balance read; PostgreSQL locks the wallet row. Withdrawals and position openings use a conditional funds guard. Helpers never commit; exceptions must escape to the outer transaction for rollback. Initialization uses conflict-safe insertion and creates its initial snapshot only for the insert winner.

External amounts are finite JSON numbers, positive, at most $1,000,000, rounded with existing Python `money()` before use; rounded zero is rejected. Internal settlements remain signed and uncapped. SQLite concurrency/rollback/API tests passed; live PostgreSQL locking remains unverified. SQLite close-once claiming now lives in [Trading](/architecture/trading.md); wallet helpers and transaction ownership are unchanged. General replay protection remains deferred.

# Frontend

`/wallet` shows the balance, deposit/withdraw forms, percentage-change chart, and transaction log. Successful deposits and withdrawals show an accessible confirmation based on the saved transaction. The page is a server component that loads the five wallet endpoints with the session cookie; client actions refresh the server render after each POST.

Transaction history returns `items`, `total`, `offset`, `limit`, and `has_more`, so the UI can filter and page through the full log.

# Cautions

- Test against a copy of the DB (`PLANWISE_DB=/path/copy.db`).
- Never commit `Backend/planwise.db`.
- All routes require the existing `session` cookie.
