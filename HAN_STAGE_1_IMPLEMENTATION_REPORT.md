# Han Security — Stage 1 Implementation Report

Date: 2026-11-21 (Asia/Taipei). Branch: `feature/Security`.
Baseline HEAD: `9cf6482ef41417a1c6e2a95111cb49b66919a2b3`.

## Outcome

Stage 1 is implemented for review. Wallet initialization is conflict-safe; shared balance mutations are protected by database locks; withdrawals and trade openings conditionally debit the current available funds. All existing P/L formulas and the leveraged-loss behavior remain intact. No commit or push was made.

Before editing, the branch matched `feature/Security`, tracked files were clean, and the only untracked files were the supplied analysis and implementation plan. Source and tests matched the planning baseline exactly. Those two documents were preserved. No unrelated working-tree changes were found or discarded.

## Files changed

| File | Change |
|---|---|
| `Backend/app/dbcompat.py` | Added narrowly scoped `begin_financial_write` and `lock_wallet`; retained existing connection selection, SQL translation, row mapping, and context behavior |
| `Backend/app/wallet.py` | Conflict-safe creation; shared locked mutation; keyword-only `require_funds=False`; conditional funds predicate; numeric/request validation; protected withdrawal |
| `Backend/app/trading.py` | Final opening debit requests funds protection; maps the wallet exception to the existing trading exception; validates raw amount/leverage inputs |
| `Backend/tests/test_dbcompat.py` | Added SQLite/PostgreSQL adapter transaction tests; reads main's schema constant via AST instead of importing a module that initializes a DB; closes the existing SQLite test connection |
| `Backend/tests/test_transaction_security.py` (new) | Independent-connection SQLite concurrency, stale-precheck, WAL, initialization, numeric, isolation, and rollback tests |
| `Backend/tests/test_security_api.py` (new) | Existing API contracts, HTTP 409/422/401, real registration and registration rollback in an isolated child process |
| `.okf/architecture/wallet.md`, `.okf/architecture/trading.md` | Current protection/limitations |
| `.okf/project/active-context.md`, `.okf/project/progress.md` | Current security status and remaining work |
| `HAN_STAGE_1_IMPLEMENTATION_REPORT.md` (new) | This report |

`main.py`, existing `test_wallet.py` and `test_trading.py`, frontend code, dependency manifests, schemas, and migrations were unchanged. Application databases and `.env` secrets were not opened. Test databases were created only in temporary directories. An ignored local `.venv` was created and dependencies installed after user approval.

## What changed, in beginner-friendly terms

Previously, two requests could both read the same balance, make a decision using that old value, and then overwrite each other's updates. A withdrawal could also pass its check, wait while another request spent funds, and still deduct the original amount.

Now every wallet change first obtains database protection, rereads the balance under that protection, calculates the new value with the existing `money()`, and updates the row. Voluntary spending also has a funds condition on the actual UPDATE. Protection lasts until the surrounding operation commits or rolls back. The wallet and its history are written together.

For example, two $700 withdrawals from $1,000 result in one success and one insufficient-funds rejection, leaving $300. Two $500 withdrawals both succeed, leaving zero. A withdrawal and a trade opening compete for the same protected balance.

### Shared mutation and initialization

`change_balance()` remains the only balance mutation implementation. Its added argument is keyword-only, so existing positional calls and the `(wallet, optional_transaction)` return format remain compatible. All credits and settlements use the same locking path; only withdrawals and openings request `require_funds=True`.

After obtaining the protected balance, it calculates `money(balance + delta)`. For a guarded debit, it executes an UPDATE with `AND balance >= requested_debit` and reads the saved wallet through RETURNING. A missing returned row raises `wallet.InsufficientFunds` before adding mutation history. There is no epsilon-based authorization. An absolute target is safe here because it is calculated while holding the database lock, unlike the previous unprotected calculation.

`ensure_wallet()` retains its existing-wallet read path. For an absent wallet it obtains write protection, inserts with `ON CONFLICT (user_id) DO NOTHING RETURNING user_id`, and adds the $1,000 initial snapshot only when that INSERT created a row. It never resets an existing balance.

### SQLite protection

On a connection without an open transaction, `begin_financial_write()` executes `BEGIN IMMEDIATE` before the authoritative wallet read. SQLite permits only one writer, so competing financial operations wait before reading the balance they will mutate.

For an existing transaction, the helper executes `UPDATE wallets SET balance = balance WHERE 0`. It changes no rows but obtains write protection without a nested BEGIN. This supports registration's existing user INSERT and trading's existing writes, as well as upgrading a read-only transaction. If a WAL read snapshot is stale, SQLite rejects its upgrade; that failure propagates rather than overwriting a newer balance. A dedicated test verifies this.

No helper commits, rolls back, closes a caller-owned connection, changes global connection defaults, or initializes schemas. The existing SQLite timeout remains in effect; lock exhaustion is an error, not insufficient funds.

### PostgreSQL protection

The adapter joins psycopg's existing non-autocommit transaction; authentication SELECTs may already have started it. `lock_wallet()` reads the wallet using parameterized `SELECT ... FOR UPDATE` before Python calculates the target. The row stays locked until the outer commit/rollback. The guarded UPDATE is an additional funds check. Autocommit PostgreSQL connections are rejected for financial writes.

Adapter tests verify the translated placeholder, FOR UPDATE, cursor cleanup, autocommit rejection, absence of internal commit/rollback/connection close, and unchanged context-manager delegation. **These are mocked adapter tests, not live PostgreSQL integration tests.** No approved disposable PostgreSQL environment was supplied, so none was created or used. Deployment isolation and live locking behavior still need verification; stronger isolation can return serialization failures.

### Trade opening and settlements

Opening retains its earlier balance precheck as a quick rejection, but the final deduction explicitly calls `change_balance(..., require_funds=True)`. If the balance changed meanwhile, the final UPDATE rejects the debit. `WalletInsufficientFunds` is converted into the existing `trading.InsufficientFunds`, which the existing endpoint maps to HTTP 409 with its existing message.

The exception propagates through the outer connection context. Any inserted position and refreshed price, as well as wallet/history writes in that transaction, roll back. Tests force a withdrawal to commit after the opening precheck but before its final debit and verify no rejected position, trade, extra history, or quote survives.

Closing still calls `change_balance()` without the voluntary-spending guard. Long/short move, P/L, P/L percentage, leverage, notional, quantity, and settlement formulas were not changed. Existing regressions still expect P/L -8,910 and wallet -7,910 for the original extreme-loss fixture.

### Numeric behavior and compatibility

External amounts must be finite int/float numbers, excluding booleans, positive, and at most $1,000,000 before rounding. The existing Python `money()` function is unchanged. Amounts are normalized with it before use, so the amount deducted/credited and the logged amount agree. Fractional cents remain accepted when they round to a positive cent amount; rounded-zero inputs are rejected before writes. Examples tested include 1.005, 2.675, 0.005, and 10.125.

This intentionally removes the old ambiguity where the raw fractional amount was added to the balance but the transaction amount was rounded separately. No Decimal, fixed-point, integer-cents, storage conversion, SQL ROUND replacement, or P/L rewrite was introduced. Numeric strings and bools previously coercible by Pydantic are now invalid inputs. HTTP non-finite JSON tokens are explicitly rejected with 422 before Pydantic can retain a NaN/Infinity input in an error response that cannot itself be serialized.

Signed internal settlement deltas must be finite but have no external deposit/withdraw cap. They may be positive, zero, or negative. The stored balance and calculated target are also checked for finiteness. Existing success response fields, wallet/history/transaction formats, endpoint paths, and insufficient-funds HTTP 409 remain intact.

## Executed tests and actual results

The approved environment was created with `py -3.14 -m venv .venv`. Installation used `.\.venv\Scripts\python.exe -m pip install -r Backend/requirements.txt httpx PyYAML`. The sandboxed attempt failed on network permissions; the approved network-enabled retry completed successfully. No manifests were changed.

The requested checks were executed after installation:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip list
.\.venv\Scripts\python.exe -m pip check
```

Actual results: **Python 3.14.5**; package listing succeeded; `No broken requirements found.` SQLite runtime: **3.50.4**. Installed packages include FastAPI 0.165.0, Pydantic 2.14.4, pandas 3.1.1, yfinance 1.8.0, psycopg/psycopg-binary 3.3.9, scikit-learn 1.9.1, httpx 0.28.1, and PyYAML 6.0.3.

Incremental checks were run from `Backend/`, using `..\.venv\Scripts\python.exe`:

| Step | Arguments after Python executable | Actual result |
|---|---|---|
| Adapter | `-m unittest tests.test_dbcompat -v` | 13 passed |
| Safe creation | `-m unittest tests.test_wallet tests.test_transaction_security -v` | 11 passed at that step |
| Shared mutation/withdrawal | Same command after added mutation cases | 16 passed |
| Trade integration | `-m unittest tests.test_trading tests.test_transaction_security -v` | 23 passed |
| Expanded concurrency/rollback | `-m unittest tests.test_transaction_security tests.test_trading tests.test_wallet tests.test_dbcompat -v` | 53 passed |
| API after fixes | `-m unittest tests.test_security_api -v` | 4 passed |

The initial pre-install adapter test failed because pandas was absent. The first API run failed due to cross-thread cleanup in the test fixture and non-finite validation-error serialization. Both were corrected, then the API suite passed. An existing adapter test's unclosed SQLite connection was also fixed. These failed intermediate runs are not counted as passing verification.

Final combined command, from `Backend/`:

```powershell
..\.venv\Scripts\python.exe -m unittest tests.test_dbcompat tests.test_wallet tests.test_trading tests.test_transaction_security tests.test_security_api -v
```

**84 tests passed:** 13 adapter, 9 existing wallet, 16 existing trading, 20 financial default-journal, 21 financial WAL, and 5 API tests. The registration cases run the actual app in a child process with `PLANWISE_DB` pointing to a disposable file **before import**, including failure after session creation. Quote providers are mocked; no Yahoo download occurs. The test client emits a Starlette deprecation warning about httpx; tests succeed and no additional package upgrade was performed.

Concurrency workers each open their own connection. The strengthened harness requires a real `SQLITE_BUSY` while the first writer remains uncommitted, then retries only the blocked SQL statement with its original parameters so a stale calculation cannot be hidden by restarting the operation. Observers use fresh connections to verify committed balances and records. Coverage includes concurrent initialization, 700/500 withdrawals, credits, user isolation, both withdrawal/opening orders, stale prechecks, write-failure rollback, and rollback at COMMIT from a deferred foreign-key constraint. WAL tests assert `SQLITE_BUSY_SNAPSHOT` specifically. No production code changed during this test-strengthening pass.

Documentation check, from repository root (direct validator fallback because `uv` is unavailable):

```powershell
.\.venv\Scripts\python.exe .claude/skills/validate/scripts/okf_validate.py .okf --strict
git diff --check
```

Strict OKF validation and diff whitespace checks passed. No broader unrelated model/pipeline/frontend suite was run.

## Remaining limitations and Stage 2

1. **Close-once and position identity:** deferred. Two concurrent close requests can still record/settle the same position. Serialized wallet writes prevent lost updates but do not decide whether a close is legitimate exactly once. Stage 2 must claim the position and coordinate durable identity and lock order.
2. **Idempotency/replay:** approved for a later stage. Repeating an intentional-looking valid POST still executes again. Do not automatically retry an unknown commit outcome.
3. **Financial audits:** no new table or failure-audit mechanism was added. Existing transaction/trade/history records remain the business records.
4. **Live PostgreSQL:** needs an approved disposable target and engine/isolation-specific contention tests before claiming deployment verification.
5. **Contention/retries:** no new automatic retries or new transient HTTP error contract. Existing SQLite lock timeouts and PostgreSQL deadlock/serialization failures propagate and roll back through the outer owner. Agree retry budgets and client error handling separately.
6. **Quote/connection lifecycle:** existing trading quote/upsert placement can prolong SQLite write locks. The production connection-context contract still leaves caller-owned connections open. This stage did not change ownership globally; test-owned connections are closed. Coordinate a narrow lifecycle/quote-lock review later.
7. **Portability and precision:** pre-existing PostgreSQL `instr()` filtered-history portability remains outside this change. Float storage and Python rounding remain; legacy malformed/non-finite values are rejected rather than repaired. No database data migration was attempted.

No new policy decision blocks review of this implementation. The team must provide/approve a disposable PostgreSQL target for live verification and agree the later contention, close-once, replay, and connection-lifecycle contracts. Exceptions must continue escaping the outer transaction owner: callers must not catch a failed multi-write operation inside the context and then commit earlier writes. No global nonnegative restriction was added.
