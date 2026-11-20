---
type: Architecture
title: Financial audit and reliability
description: Linked SQLite balance history and allowlisted financial failure diagnostics
tags: [backend, database, security]
generated: { by: codex/gpt-6, at: 2026-11-20T18:15:11Z }
sources:
  - id: wallet
    resource: Backend/app/wallet.py
    title: Balance history and schema upgrade
  - id: logging
    resource: Backend/app/financial_logging.py
    title: Safe financial diagnostics
  - id: tests
    resource: Backend/tests/test_financial_audit.py
    title: Default-journal and WAL audit tests
---

# Balance history

SQLite startup adds nullable `operation_type`, `delta`, `wallet_transaction_id`, `position_id`, and `trade_id` to the existing `balance_history` table. The column check and ALTER statements run under writer protection in one schema transaction, safely repeatable on existing databases. Existing rows keep NULL metadata; timestamps are never used to infer links.

Each new history row records the rounded actual balance difference: positive credit, negative debit, or zero unchanged balance. Operation types are `initialization`, `deposit`, `withdrawal`, `trade_open`, and `trade_close`. Trusted generic `change_balance` calls without a named cause use `adjustment`.

- Initialization records the starting credit once.
- Deposits/withdrawals link their existing `wallet_transactions.id`.
- Openings link the allocated position ID; closings link both the historical position ID and the new trade ID. Position references deliberately do not require a live position row.

No additional financial rows or audit tables are created. Audit inserts share the outer financial transaction and must succeed before commit; audit failure rolls back wallet, history, trade/position, price, and idempotency changes. Existing API payloads stay unchanged; successful idempotent replays create no history rows.

# Diagnostics

The four financial POST operations emit selected failures through standard logger `planwise.financial`, after request connection/transaction contexts unwind. JSON contains only `operation`, authenticated `user_id` when available, `status`, a fixed `reason_code`, and a server-generated correlation ID.

Reasons cover invalid keys, key conflicts, unavailable positions, SQLite contention, unavailable market data, and unexpected failures. Normal insufficient funds and successful replays emit no warning. Bodies, notes, raw keys, credentials, stored responses, exception text, and tracebacks are excluded. Handler failures are ignored without replacing the original outcome.

These diagnostics are best effort, not a second ledger; retention depends on server logging configuration. Legacy history and prior position ID ambiguity are not repaired. See [Wallet](/architecture/wallet.md), [Trading](/architecture/trading.md), and [Idempotency](/architecture/idempotency.md).
