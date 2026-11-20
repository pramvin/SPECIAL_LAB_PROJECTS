"""Financial invariants on disposable files and independent connections."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from app import dbcompat, trading, wallet


class FinancialTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = str(Path(self.directory.name) / "financial.db")
        self.environment = patch.dict(os.environ, {"PLANWISE_DB": self.path})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        conn = self.connect()
        try:
            conn.executescript(
                "CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT);"
                "INSERT INTO users VALUES (1, 'one@example.test');"
                "INSERT INTO users VALUES (2, 'two@example.test');"
            )
            wallet.init_schema(conn)
            trading.init_schema(conn)
        finally:
            conn.close()

    def connect(self):
        return dbcompat.connect(self.path)

    def observe(self, sql, params=()):
        conn = self.connect()
        try:
            return [dict(row) for row in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

    def race(self, *operations, rollback_first=False):
        """Require a real conflicting write while the first transaction is open.

        Only the blocked SQL statement is retried, with its original parameters.
        Restarting the whole operation here could hide a stale balance calculation.
        """
        self.assertEqual(len(operations), 2)
        first_written = threading.Event()
        contended = threading.Event()
        first_finished = threading.Event()
        busy_errors = []
        case = self

        class RollbackFirst(Exception):
            pass

        class ContendingConnection:
            def __init__(self, raw):
                self.raw = raw

            def __getattr__(self, name):
                return getattr(self.raw, name)

            def __enter__(self):
                self.raw.__enter__()
                return self

            def __exit__(self, *args):
                return self.raw.__exit__(*args)

            def execute(self, sql, params=()):
                try:
                    return self.raw.execute(sql, params)
                except sqlite3.OperationalError as exc:
                    if exc.sqlite_errorcode != sqlite3.SQLITE_BUSY:
                        raise
                    busy_errors.append(exc.sqlite_errorcode)
                    contended.set()
                    case.assertTrue(first_finished.wait(5), "first transaction did not finish")
                    return self.raw.execute(sql, params)

        def worker(index):
            raw = self.connect()  # Each worker creates and owns its connection.
            try:
                if index == 1:
                    self.assertTrue(first_written.wait(5), "first operation did not write")
                    raw.execute("PRAGMA busy_timeout=0")
                    conn = ContendingConnection(raw)
                else:
                    conn = raw
                with conn:
                    operations[index](conn)
                    if index == 0:
                        self.assertTrue(raw.in_transaction)
                        first_written.set()
                        self.assertTrue(contended.wait(5), "second writer never encountered a lock")
                        if rollback_first:
                            raise RollbackFirst()
                return "ok"
            except RollbackFirst:
                return "rolled_back"
            except (wallet.InsufficientFunds, trading.InsufficientFunds):
                return "insufficient"
            except trading.PositionNotFound:
                return "not_found"
            finally:
                raw.close()
                if index == 0:
                    first_finished.set()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker, index) for index in range(2)]
            results = [future.result(timeout=15) for future in futures]
        self.assertEqual(busy_errors, [sqlite3.SQLITE_BUSY])
        return results

    def seed_wallet(self, user_id=1):
        conn = self.connect()
        try:
            with conn:
                wallet.ensure_wallet(conn, user_id)
        finally:
            conn.close()

    def test_concurrent_initialization(self):
        self.assertEqual(self.race(*(lambda c: wallet.ensure_wallet(c, 1) for _ in range(2))),
                         ["ok", "ok"])
        self.assertEqual(len(self.observe("SELECT * FROM wallets")), 1)
        self.assertEqual(self.observe("SELECT balance FROM balance_history"), [{"balance": 1000}])
        self.assertEqual(self.observe("SELECT * FROM wallet_transactions"), [])

    def test_initialization_never_resets_existing_balance(self):
        conn = self.connect()
        try:
            with conn:
                wallet.ensure_wallet(conn, 1)
                conn.execute("UPDATE wallets SET balance = 123 WHERE user_id = 1")
                self.assertEqual(wallet.ensure_wallet(conn, 1)["balance"], 123)
            self.assertEqual(len(self.observe("SELECT * FROM balance_history")), 1)
        finally:
            conn.close()

    def assert_wallet(self, balance, transactions, history):
        self.assertEqual(self.observe("SELECT balance FROM wallets WHERE user_id=1"),
                         [{"balance": balance}])
        self.assertEqual(len(self.observe("SELECT * FROM wallet_transactions WHERE user_id=1")),
                         transactions)
        self.assertEqual([r["balance"] for r in self.observe(
            "SELECT balance FROM balance_history WHERE user_id=1 ORDER BY id")], history)
        txs = self.observe("SELECT kind, amount, balance_after FROM wallet_transactions "
                           "WHERE user_id=1 ORDER BY id")
        for tx in txs:
            self.assertIn(tx["balance_after"], history[1:])
        if len(history) == len(txs) + 1:
            running = history[0]
            for tx, after in zip(txs, history[1:]):
                running = wallet.money(running + (tx["amount"] if tx["kind"] == "deposit"
                                                  else -tx["amount"]))
                self.assertEqual(tx["balance_after"], after)
                self.assertEqual(running, after)

    def test_competing_700_withdrawals(self):
        self.seed_wallet()
        results = self.race(*(lambda c: wallet.withdraw(c, 1, 700) for _ in range(2)))
        self.assertCountEqual(results, ["ok", "insufficient"])
        self.assert_wallet(300, 1, [1000, 300])

    def test_two_500_withdrawals(self):
        self.seed_wallet()
        self.assertEqual(self.race(*(lambda c: wallet.withdraw(c, 1, 500) for _ in range(2))),
                         ["ok", "ok"])
        self.assert_wallet(0, 2, [1000, 500, 0])

    def test_concurrent_deposits(self):
        self.seed_wallet()
        self.assertEqual(self.race(lambda c: wallet.deposit(c, 1, 100),
                                   lambda c: wallet.deposit(c, 1, 200)), ["ok", "ok"])
        history = self.observe("SELECT balance FROM balance_history ORDER BY id")
        self.assertIn(history[1]["balance"], (1100, 1200))
        self.assert_wallet(1300, 2, [1000, history[1]["balance"], 1300])

    def test_invalid_numbers_and_rounding(self):
        self.seed_wallet()
        conn = self.connect()
        try:
            for value in (float("nan"), float("inf"), -float("inf"), True, False,
                          None, "10", [], {}, 0, -1, 1_000_000.01, 0.001, 10**1000):
                for operation in (wallet.deposit, wallet.withdraw):
                    with self.subTest(value=repr(value), operation=operation.__name__):
                        with self.assertRaises(ValueError), conn:
                            operation(conn, 1, value)
            self.assert_wallet(1000, 0, [1000])
            for value in (1.005, 2.675, 0.005, 10.125):
                before = wallet.ensure_wallet(conn, 1)["balance"]
                with conn:
                    row, tx = wallet.deposit(conn, 1, value)
                self.assertEqual(tx["amount"], round(value, 2))
                self.assertEqual(row["balance"], wallet.money(before + wallet.money(value)))
        finally:
            conn.close()

    def test_internal_settlement_has_no_external_cap_or_nonnegative_rule(self):
        self.seed_wallet()
        conn = self.connect()
        try:
            with conn:
                row, tx = wallet.change_balance(conn, 1, -2_000_000)
                self.assertEqual(row["balance"], -1_999_000)
                self.assertIsNone(tx)
                row, _ = wallet.change_balance(conn, 1, 0)
                self.assertEqual(row["balance"], -1_999_000)
                row, _ = wallet.change_balance(conn, 1, 2_000_000)
                self.assertEqual(row["balance"], 1000)
        finally:
            conn.close()

    @staticmethod
    def bar(_ticker):
        return {"date": "2026-01-01", "open": 100, "high": 100,
                "low": 100, "close": 100, "volume": 1}

    def test_withdraw_and_open_compete_for_same_funds(self):
        self.seed_wallet()
        with patch.object(trading, "fetch_latest_bar", side_effect=self.bar):
            results = self.race(lambda c: wallet.withdraw(c, 1, 700),
                                lambda c: trading.open_position(c, 1, "AAPL", "long", 700, 1))
        self.assertCountEqual(results, ["ok", "insufficient"])
        self.assertEqual(self.observe("SELECT balance FROM wallets")[0]["balance"], 300)
        positions = self.observe("SELECT * FROM positions")
        txs = self.observe("SELECT * FROM wallet_transactions")
        self.assertEqual(len(positions) + len(txs), 1)
        self.assertEqual(len(self.observe("SELECT * FROM balance_history")), 2)
        self.assertEqual(self.observe("SELECT * FROM trades"), [])

    def test_open_precheck_becomes_stale_and_leaves_no_position(self):
        self.seed_wallet()
        quote_started = threading.Event()
        withdrawn = threading.Event()

        def delayed_quote(ticker):
            quote_started.set()  # Opening has already passed its unlocked precheck.
            if not withdrawn.wait(5):
                raise AssertionError("withdrawal did not complete")
            return self.bar(ticker)

        def withdraw(conn):
            self.assertTrue(quote_started.wait(5))
            wallet.withdraw(conn, 1, 700)
            # Signal only after the worker's outer transaction has committed.

        def opening():
            conn = self.connect()
            try:
                with self.assertRaises(trading.InsufficientFunds), conn:
                    trading.open_position(conn, 1, "AAPL", "long", 700, 1)
            finally:
                conn.close()

        with patch.object(trading, "fetch_latest_bar", side_effect=delayed_quote):
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(opening)
                conn = self.connect()
                try:
                    with conn:
                        withdraw(conn)
                finally:
                    conn.close()
                    withdrawn.set()
                future.result(timeout=10)
        self.assert_wallet(300, 1, [1000, 300])
        for table in ("positions", "trades", "prices"):
            self.assertEqual(self.observe(f"SELECT * FROM {table}"), [])

    def test_open_holds_funds_against_overlapping_withdrawal(self):
        self.seed_wallet()
        with patch.object(trading, "fetch_latest_bar", side_effect=self.bar):
            results = self.race(lambda c: trading.open_position(c, 1, "AAPL", "long", 700, 1),
                                lambda c: wallet.withdraw(c, 1, 700))
        self.assertEqual(results, ["ok", "insufficient"])
        self.assert_wallet(300, 0, [1000, 300])
        self.assertEqual(len(self.observe("SELECT * FROM positions")), 1)
        self.assertEqual(self.observe("SELECT * FROM trades"), [])

    def test_late_write_failures_roll_back_all_business_effects(self):
        self.seed_wallet()
        for table, event in (("wallets", "UPDATE"), ("balance_history", "INSERT"),
                             ("wallet_transactions", "INSERT")):
            with self.subTest(table=table):
                conn = self.connect()
                try:
                    conn.execute(f"CREATE TRIGGER fail_write AFTER {event} ON {table} "
                                 "BEGIN SELECT RAISE(ABORT, 'injected failure'); END")
                    conn.commit()
                    before = self.observe("SELECT * FROM wallets")
                    with self.assertRaises(sqlite3.IntegrityError), conn:
                        conn.execute("INSERT INTO users VALUES (3, 'outer@example.test')")
                        wallet.deposit(conn, 1, 100)
                    self.assertEqual(self.observe("SELECT * FROM wallets"), before)
                    self.assert_wallet(1000, 0, [1000])
                    self.assertEqual(self.observe("SELECT * FROM users WHERE id=3"), [])
                    conn.execute("DROP TRIGGER fail_write")
                    conn.commit()
                finally:
                    conn.close()

    def test_registration_style_outer_rollback_removes_user_and_initial_wallet(self):
        conn = self.connect()
        try:
            with self.assertRaises(RuntimeError), conn:
                conn.execute("INSERT INTO users VALUES (3, 'new@example.test')")
                wallet.ensure_wallet(conn, 3)
                wallet.deposit(conn, 3, 100)
                raise RuntimeError("later registration failure")
            for table in ("wallets", "balance_history", "wallet_transactions"):
                self.assertEqual(self.observe(f"SELECT * FROM {table}"), [])
            self.assertEqual(self.observe("SELECT * FROM users WHERE id=3"), [])
        finally:
            conn.close()

    def test_initialization_rolls_back_and_waiter_can_create(self):
        self.assertEqual(self.race(*(lambda c: wallet.ensure_wallet(c, 1) for _ in range(2)),
                                   rollback_first=True), ["rolled_back", "ok"])
        self.assert_wallet(1000, 0, [1000])

    def test_concurrent_users_are_isolated(self):
        self.seed_wallet(1)
        self.seed_wallet(2)
        self.assertEqual(self.race(lambda c: wallet.withdraw(c, 1, 700),
                                   lambda c: wallet.deposit(c, 2, 200)), ["ok", "ok"])
        self.assert_wallet(300, 1, [1000, 300])
        self.assertEqual(self.observe("SELECT balance FROM wallets WHERE user_id=2"),
                         [{"balance": 1200}])

    def test_open_invalid_amount_and_leverage_write_nothing(self):
        self.seed_wallet()
        conn = self.connect()
        try:
            for value in (True, "2", None, float("nan"), float("inf"), -float("inf")):
                for field in ("amount", "leverage"):
                    args = {"amount": 100, "leverage": 1, field: value}
                    with self.subTest(value=value, field=field):
                        with self.assertRaises(trading.TradingError), conn:
                            trading.open_position(conn, 1, "AAPL", "long", **args)
            self.assert_wallet(1000, 0, [1000])
            self.assertEqual(self.observe("SELECT * FROM positions"), [])
        finally:
            conn.close()

    def test_waiting_writer_proceeds_after_rollback(self):
        self.seed_wallet()
        self.assertEqual(self.race(*(lambda c: wallet.withdraw(c, 1, 700) for _ in range(2)),
                                   rollback_first=True), ["rolled_back", "ok"])
        self.assert_wallet(300, 1, [1000, 300])

    def test_commit_failure_rolls_back_wallet_and_surrounding_writes(self):
        self.seed_wallet()
        conn = self.connect()
        try:
            conn.execute("CREATE TABLE deferred_check (user_id INTEGER REFERENCES users(id) "
                         "DEFERRABLE INITIALLY DEFERRED)")
            conn.commit()
            before = self.observe("SELECT * FROM wallets")
            reached_commit = False
            with self.assertRaises(sqlite3.IntegrityError) as error:
                with conn:
                    wallet.deposit(conn, 1, 100)
                    conn.execute("INSERT INTO users VALUES (3, 'outer@example.test')")
                    conn.execute("INSERT INTO deferred_check VALUES (999)")
                    # Deferred constraint permits all statements; __exit__ fails at COMMIT.
                    self.assertTrue(conn.in_transaction)
                    self.assertEqual(conn.execute("SELECT balance FROM wallets").fetchone()[0], 1100)
                    reached_commit = True
            self.assertTrue(reached_commit)
            self.assertEqual(error.exception.sqlite_errorcode, sqlite3.SQLITE_CONSTRAINT_FOREIGNKEY)
            self.assertFalse(conn.in_transaction)
            self.assertEqual(self.observe("SELECT * FROM wallets"), before)
            self.assert_wallet(1000, 0, [1000])
            self.assertEqual(self.observe("SELECT * FROM users WHERE id=3"), [])
            self.assertEqual(self.observe("SELECT * FROM deferred_check"), [])
        finally:
            conn.close()

    def test_trade_history_failure_rolls_back_position_and_quote(self):
        self.seed_wallet()
        conn = self.connect()
        try:
            conn.execute("CREATE TRIGGER fail_history BEFORE INSERT ON balance_history "
                         "BEGIN SELECT RAISE(ABORT, 'history unavailable'); END")
            conn.commit()
            with patch.object(trading, "fetch_latest_bar", side_effect=self.bar):
                with self.assertRaises(sqlite3.IntegrityError), conn:
                    trading.open_position(conn, 1, "AAPL", "long", 100, 2)
            self.assert_wallet(1000, 0, [1000])
            for table in ("positions", "trades", "prices"):
                self.assertEqual(self.observe(f"SELECT * FROM {table}"), [])
        finally:
            conn.close()

    def test_invalid_internal_deltas_write_nothing(self):
        conn = self.connect()
        try:
            for value in (True, False, None, "1", [], float("nan"), float("inf"), -float("inf")):
                with self.subTest(value=value), self.assertRaises(ValueError), conn:
                    wallet.change_balance(conn, 1, value)
            self.assertEqual(self.observe("SELECT * FROM wallets"), [])
            self.assertEqual(self.observe("SELECT * FROM balance_history"), [])
        finally:
            conn.close()

    def test_exact_funds_and_one_cent_above(self):
        self.seed_wallet()
        conn = self.connect()
        try:
            with self.assertRaises(wallet.InsufficientFunds), conn:
                wallet.withdraw(conn, 1, 1000.01)
            with conn:
                wallet.withdraw(conn, 1, 1000)
            self.assert_wallet(0, 1, [1000, 0])
        finally:
            conn.close()

    def seed_position(self):
        self.seed_wallet()
        conn = self.connect()
        try:
            with patch.object(trading, "fetch_latest_bar", side_effect=self.bar), conn:
                position, _ = trading.open_position(conn, 1, "AAPL", "long", 500, 2)
            return position["id"]
        finally:
            conn.close()

    @staticmethod
    def exit_bar(_ticker):
        return {"date": "2026-01-02", "open": 110, "high": 110,
                "low": 110, "close": 110, "volume": 2}

    def financial_state(self):
        return {table: self.observe(f"SELECT * FROM {table} ORDER BY {order}")
                for table, order in (("wallets", "user_id"), ("positions", "id"),
                                     ("trades", "id"), ("balance_history", "id"),
                                     ("wallet_transactions", "id"), ("prices", "ticker, date"))}

    def assert_settled_once(self, position_id):
        self.assert_wallet(1100, 0, [1000, 500, 1100])
        self.assertEqual(self.observe("SELECT * FROM positions"), [])
        self.assertEqual(self.observe("SELECT position_id, pnl FROM trades"),
                         [{"position_id": position_id, "pnl": 100}])
        self.assertEqual(self.observe("SELECT close FROM prices ORDER BY date"),
                         [{"close": 100}, {"close": 110}])

    def test_concurrent_close_settles_only_once(self):
        position_id = self.seed_position()
        with patch.object(trading, "fetch_latest_bar", side_effect=self.exit_bar) as quote:
            self.assertEqual(self.race(*(lambda c: trading.close_position(c, 1, position_id)
                                        for _ in range(2))), ["ok", "not_found"])
            self.assertEqual(quote.call_count, 2)
        self.assert_settled_once(position_id)

    def test_rolled_back_claimant_allows_waiting_close(self):
        position_id = self.seed_position()
        with patch.object(trading, "fetch_latest_bar", side_effect=self.exit_bar):
            self.assertEqual(self.race(*(lambda c: trading.close_position(c, 1, position_id)
                                        for _ in range(2)), rollback_first=True),
                             ["rolled_back", "ok"])
        self.assert_settled_once(position_id)

    def test_failure_immediately_after_claim_restores_position(self):
        position_id = self.seed_position()
        before = self.financial_state()
        conn = self.connect()

        def fail_after_claim(_conn, _ticker, _bar, _observed_at_ns):
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0], 0)
            raise trading.MarketDataUnavailable("injected quote failure after claim")

        try:
            with patch.object(trading, "fetch_latest_bar", side_effect=self.exit_bar), \
                    patch.object(trading, "save_price_bar", side_effect=fail_after_claim):
                with self.assertRaises(trading.MarketDataUnavailable), conn:
                    trading.close_position(conn, 1, position_id)
            self.assertEqual(self.financial_state(), before)
        finally:
            conn.close()

    def test_quote_failures_leave_all_state_unchanged(self):
        position_id = self.seed_position()
        before = self.financial_state()
        conn = self.connect()
        try:
            for error in (trading.MarketDataUnavailable("offline"), trading.UnknownTicker("no data")):
                with self.subTest(error=type(error).__name__):
                    def fail_quote(_ticker):
                        self.assertFalse(conn.in_transaction)
                        raise error

                    with patch.object(trading, "fetch_latest_bar", side_effect=fail_quote):
                        with self.assertRaises(type(error)), conn:
                            trading.close_position(conn, 1, position_id)
                    self.assertEqual(self.financial_state(), before)
        finally:
            conn.close()

    def test_simultaneous_quotes_still_settle_once(self):
        position_id = self.seed_position()
        fetching = threading.Barrier(2)

        def quote(ticker):
            fetching.wait(timeout=5)
            return self.exit_bar(ticker)

        def close():
            conn = self.connect()
            try:
                with conn:
                    trading.close_position(conn, 1, position_id)
                return "ok"
            except trading.PositionNotFound:
                return "not_found"
            finally:
                conn.close()

        with patch.object(trading, "fetch_latest_bar", side_effect=quote), \
                ThreadPoolExecutor(max_workers=2) as pool:
            results = [pool.submit(close) for _ in range(2)]
            self.assertCountEqual([result.result(timeout=10) for result in results],
                                  ["ok", "not_found"])
        self.assert_settled_once(position_id)

    def test_delayed_close_keeps_own_quote_without_overwriting_newer_cache(self):
        first_id = self.seed_position()
        conn = self.connect()
        try:
            with patch.object(trading, "fetch_latest_bar", side_effect=self.bar), conn:
                second, _ = trading.open_position(conn, 1, "AAPL", "long", 100, 1)
        finally:
            conn.close()
        observed = threading.Event()
        release = threading.Event()
        delayed_thread = []
        original_begin = trading.begin_financial_write

        def pause_before_lock(conn):
            if threading.get_ident() == delayed_thread[0]:
                self.assertFalse(conn.in_transaction)
                observed.set()
                self.assertTrue(release.wait(10), "delayed close was not released")
            original_begin(conn)

        def close_first():
            delayed_thread.append(threading.get_ident())
            conn = self.connect()
            try:
                with conn:
                    trade, _ = trading.close_position(conn, 1, first_id)
                return dict(trade)
            finally:
                conn.close()

        old_bar = self.exit_bar("AAPL")
        new_bar = dict(old_bar, open=120, high=120, low=120, close=120, volume=3)
        with patch.object(trading, "fetch_latest_bar", side_effect=[old_bar, new_bar]), \
                patch.object(trading, "begin_financial_write", side_effect=pause_before_lock), \
                ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(close_first)
            try:
                self.assertTrue(observed.wait(5), "first close did not fetch its quote")
                conn = self.connect()
                try:
                    with conn:
                        second_trade, _ = trading.close_position(conn, 1, second["id"])
                finally:
                    conn.close()
                cached = self.observe("SELECT * FROM prices WHERE date = '2026-01-02'")
                self.assertEqual(cached[0]["close"], 120)
                self.assertFalse(first.done())
            finally:
                release.set()
            first_trade = first.result(timeout=5)
        self.assertEqual(first_trade["exit_price"], 110)
        self.assertEqual(first_trade["pnl"], 100)
        self.assertEqual(second_trade["exit_price"], 120)
        self.assertEqual(second_trade["pnl"], 20)
        self.assertEqual(self.observe("SELECT * FROM prices WHERE date = '2026-01-02'"), cached)
        self.assertEqual(self.observe("SELECT * FROM positions"), [])
        self.assertEqual(len(self.observe("SELECT * FROM trades")), 2)
        self.assert_wallet(1120, 0, [1000, 500, 400, 520, 1120])

    def test_close_write_failures_restore_all_state(self):
        position_id = self.seed_position()
        for table, event in (("trades", "INSERT"), ("wallets", "UPDATE"),
                             ("balance_history", "INSERT")):
            with self.subTest(table=table):
                conn = self.connect()
                try:
                    conn.execute(f"CREATE TRIGGER fail_close AFTER {event} ON {table} "
                                 "BEGIN SELECT RAISE(ABORT, 'injected close failure'); END")
                    conn.commit()
                    before = self.financial_state()
                    with patch.object(trading, "fetch_latest_bar", side_effect=self.exit_bar):
                        with self.assertRaises(sqlite3.IntegrityError), conn:
                            trading.close_position(conn, 1, position_id)
                    self.assertEqual(self.financial_state(), before)
                    conn.execute("DROP TRIGGER fail_close")
                    conn.commit()
                finally:
                    conn.close()
        conn = self.connect()
        try:
            with patch.object(trading, "fetch_latest_bar", side_effect=self.exit_bar), conn:
                trading.close_position(conn, 1, position_id)
        finally:
            conn.close()
        self.assert_settled_once(position_id)

    def test_close_commit_failure_restores_all_state(self):
        position_id = self.seed_position()
        before = self.financial_state()
        conn = self.connect()
        try:
            conn.execute("CREATE TABLE deferred_close (user_id INTEGER REFERENCES users(id) "
                         "DEFERRABLE INITIALLY DEFERRED)")
            conn.commit()
            reached_commit = False
            with patch.object(trading, "fetch_latest_bar", side_effect=self.exit_bar):
                with self.assertRaises(sqlite3.IntegrityError) as error:
                    with conn:
                        trading.close_position(conn, 1, position_id)
                        self.assertEqual(conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0], 0)
                        self.assertEqual(conn.execute("SELECT balance FROM wallets").fetchone()[0], 1100)
                        conn.execute("INSERT INTO deferred_close VALUES (999)")
                        reached_commit = True
                self.assertTrue(reached_commit)
                self.assertEqual(error.exception.sqlite_errorcode, sqlite3.SQLITE_CONSTRAINT_FOREIGNKEY)
                self.assertFalse(conn.in_transaction)
                self.assertEqual(self.financial_state(), before)
                self.assertEqual(self.observe("SELECT * FROM deferred_close"), [])
                with conn:
                    trading.close_position(conn, 1, position_id)
            self.assert_settled_once(position_id)
        finally:
            conn.close()

    def test_close_reopen_does_not_reuse_position_id(self):
        old_id = self.seed_position()
        conn = self.connect()
        try:
            with patch.object(trading, "fetch_latest_bar", side_effect=self.exit_bar):
                with conn:
                    trading.close_position(conn, 1, old_id)
                with conn:
                    new_position, _ = trading.open_position(conn, 1, "AAPL", "short", 100, 1)
                self.assertGreater(new_position["id"], old_id)
                before = self.financial_state()
                with self.assertRaises(trading.PositionNotFound), conn:
                    trading.close_position(conn, 1, old_id)
                self.assertEqual(self.financial_state(), before)
        finally:
            conn.close()

    def test_allocator_uses_other_users_closed_ids_above_live_ids(self):
        first_id = self.seed_position()
        self.seed_wallet(2)
        conn = self.connect()
        try:
            with patch.object(trading, "fetch_latest_bar", side_effect=self.bar):
                with conn:
                    other, _ = trading.open_position(conn, 2, "AAPL", "long", 100, 1)
                with conn:
                    trading.close_position(conn, 2, other["id"])
                with conn:
                    new_position, _ = trading.open_position(conn, 1, "AAPL", "long", 100, 1)
            self.assertEqual(other["id"], first_id + 1)
            self.assertEqual(new_position["id"], other["id"] + 1)
            self.assertEqual(len(self.observe("SELECT * FROM positions")), 2)
        finally:
            conn.close()

    def test_concurrent_openings_allocate_different_ids(self):
        self.seed_wallet()
        with patch.object(trading, "fetch_latest_bar", side_effect=self.bar):
            self.assertEqual(self.race(*(lambda c: trading.open_position(c, 1, "AAPL", "long", 100, 1)
                                        for _ in range(2))), ["ok", "ok"])
        self.assertEqual(self.observe("SELECT id FROM positions ORDER BY id"), [{"id": 1}, {"id": 2}])
        self.assert_wallet(800, 0, [1000, 900, 800])


class FinancialWalTest(FinancialTest):
    """The same financial invariants with SQLite WAL snapshot semantics."""

    def setUp(self):
        super().setUp()
        conn = self.connect()
        try:
            self.assertEqual(conn.execute("PRAGMA journal_mode=WAL").fetchone()[0], "wal")
        finally:
            conn.close()

    def test_stale_read_transaction_fails_without_overwriting_new_balance(self):
        self.seed_wallet()
        stale = self.connect()
        writer = self.connect()
        try:
            stale.execute("BEGIN")
            self.assertEqual(wallet.ensure_wallet(stale, 1)["balance"], 1000)
            with writer:
                wallet.withdraw(writer, 1, 700)
            with self.assertRaises(sqlite3.OperationalError) as error, stale:
                wallet.withdraw(stale, 1, 700)
            self.assertEqual(error.exception.sqlite_errorcode, sqlite3.SQLITE_BUSY_SNAPSHOT)
            self.assert_wallet(300, 1, [1000, 300])
        finally:
            stale.close()
            writer.close()


if __name__ == "__main__":
    unittest.main()
