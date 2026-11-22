---
type: Architecture
title: Financial request idempotency
description: SQLite financial request keys, atomic result storage, and replay behavior
tags: [backend, database, security]
generated: { by: codex/gpt-6, at: 2026-11-20T18:15:11Z }
sources:
  - id: code
    resource: Backend/app/idempotency.py
    title: Financial request replay
  - id: tests
    resource: Backend/tests/test_idempotency.py
    title: Default-journal and WAL API tests
---

# Contract

The deposit, withdrawal, open-position, and close-position POST endpoints accept optional `Idempotency-Key`: 1–128 visible ASCII characters, case-sensitive, without spaces. Authentication is required for every replay. Unkeyed requests retain legacy behavior and have no general replay protection.

Keys are unique per authenticated user across all four operations. The versioned fingerprint includes the operation and effective validated inputs: rounded amount, trimmed note, normalized ticker, side, leverage including its default, or target position ID. Changed effective inputs return HTTP 409. Equivalent normalized inputs replay successfully.

# Transaction flow

1. Authenticate and look up the key on a short-lived read connection; close it before quote preparation. A matching completed record returns its stored response without fetching quotes or changing state.
2. Prepare trading quotes and receipt timestamps without write protection. Close-position preparation also closes its owner-filtered lookup connection before fetching.
3. In the outer write transaction, authenticate again, acquire financial write protection, and recheck the key. A concurrent winner's response takes precedence over any preparation error. Otherwise execute the financial operation and insert its serialized successful response together.
4. Expose success only after the outer transaction commits. Exceptions roll back both financial effects and the request record. Helpers never commit independently.

`financial_requests` stores `user_id`, `key`, version-prefixed `fingerprint`, `status_code` (200), `response_json`, and `created_at`, with primary key `(user_id, key)`. SQLite startup creates the table for existing databases. Only successful operations consume keys; failed attempts may be retried. No expiration or cleanup is automatic.

Replays return the original JSON and status, including historical wallet/position snapshots. They do not reprice a trade or recreate a closed position. SQLite BUSY/LOCKED failures return HTTP 503 with `Retry-After: 1`; clients should retry with the same key. No persistent pending reservations are used. Selected failure diagnostics run only after connection contexts unwind; [logging failures](/architecture/financial-audit.md) cannot replace the original outcome.

See [Wallet](/architecture/wallet.md) and [Simulated trading](/architecture/trading.md). Their funds guards, close-once claims, ID allocation, settlement quotes, and shared cache ordering remain in force.
