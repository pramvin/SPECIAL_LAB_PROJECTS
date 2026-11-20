"""Linked history and safe diagnostics on disposable default/WAL databases."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import sqlite3
import threading
import unittest
from unittest.mock import patch

from app import dbcompat, financial_logging, wallet
from tests import test_idempotency


class FinancialAuditTest(unittest.TestCase):
    journal_mode = "delete"
    metadata_columns = ("operation_type", "delta", "wallet_transaction_id", "position_id", "trade_id")

    def setUp(self):
        self.case = test_idempotency.IdempotencyApiTest()
        self.case.journal_mode = self.journal_mode
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        logging_patch = patch.object(financial_logging.logger, "warning")
        self.warning = logging_patch.start()
        self.addCleanup(logging_patch.stop)

    def history(self):
        return self.case.state()["balance_history"]

    def assert_reconciled(self):
        state = self.case.state()
        for account in state["wallets"]:
            previous = 0
            rows = [row for row in state["balance_history"] if row["user_id"] == account["user_id"]]
            self.assertTrue(rows)
            for row in rows:
                self.assertEqual(wallet.money(previous + row["delta"]), row["balance"])
                previous = row["balance"]
            self.assertEqual(previous, account["balance"])

    def test_initialization_deposit_withdrawal_metadata_and_reconciliation(self):
        self.case.arrange("deposit")
        initial = self.history()[0]
        self.assertEqual(initial["operation_type"], "initialization")
        self.assertEqual(initial["delta"], 1000)
        self.assertEqual(initial["balance"], 1000)
        for column in self.metadata_columns[2:]:
            self.assertIsNone(initial[column])
        for operation, amount, expected in (("deposit", 10.125, 10.12), ("withdraw", 0.005, -0.01)):
            response = self.case.post(f"/api/wallet/{operation}", {"amount": amount}, key=operation)
            self.assertEqual(response.status_code, 200)
            row = self.history()[-1]
            self.assertEqual(row["user_id"], 1)
            self.assertGreater(row["created_at"], 0)
            self.assertEqual(row["operation_type"], "withdrawal" if operation == "withdraw" else operation)
            self.assertEqual(row["delta"], expected)
            transaction = response.json()["transaction"]
            self.assertEqual(row["wallet_transaction_id"], transaction["id"])
            self.assertEqual(row["balance"], transaction["balance_after"])
            self.assertIsNone(row["position_id"])
            self.assertIsNone(row["trade_id"])
            before = self.case.state()
            replay = self.case.post(f"/api/wallet/{operation}", {"amount": amount}, key=operation)
            self.assertEqual(replay.content, response.content)
            self.assertEqual(self.case.state(), before)
        self.assertEqual(len(self.history()), 3)
        self.assertEqual(len(self.case.state()["wallet_transactions"]), 2)
        self.assert_reconciled()

    def test_trade_references_and_positive_negative_zero_settlements(self):
        for exit_price, expected_delta in ((110, 200), (80, -100), (90, 0)):
            with self.subTest(exit_price=exit_price):
                body = dict(ticker="AAPL", side="long", amount=100, leverage=10)
                opened = self.case.post("/api/positions", body, key=f"open-{exit_price}")
                self.assertEqual(opened.status_code, 200)
                position_id = opened.json()["position"]["id"]
                opening_history = dict(self.history()[-1])
                self.assertEqual(opening_history["operation_type"], "trade_open")
                self.assertEqual(opening_history["delta"], -100)
                self.assertEqual(opening_history["position_id"], position_id)
                self.assertIsNone(opening_history["trade_id"])
                self.assertIsNone(opening_history["wallet_transaction_id"])
                url = f"/api/positions/{position_id}/close"
                quote = dict(self.case.bar("AAPL"), open=exit_price, high=exit_price,
                             low=exit_price, close=exit_price)
                with patch.object(test_idempotency.trading, "fetch_latest_bar", return_value=quote):
                    closed = self.case.post(url, key=f"close-{exit_price}")
                self.assertEqual(closed.status_code, 200)
                trade = closed.json()["trade"]
                row = self.history()[-1]
                self.assertEqual(row["operation_type"], "trade_close")
                self.assertEqual(row["delta"], expected_delta)
                self.assertEqual(row["position_id"], position_id)
                self.assertEqual(row["trade_id"], trade["id"])
                self.assertIsNone(row["wallet_transaction_id"])
                self.assertEqual(self.case.state()["positions"], [])
                self.assertIn(opening_history, self.history())
                before = self.case.state()
                self.assertEqual(self.case.post(url, key=f"close-{exit_price}").content, closed.content)
                self.assertEqual(self.case.post("/api/positions", body, key=f"open-{exit_price}").content,
                                 opened.content)
                self.assertEqual(self.case.state(), before)
                self.assert_reconciled()
        self.assertEqual(len(self.history()), 7)
        self.assertEqual(self.case.state()["wallet_transactions"], [])

    def test_audit_write_failure_rolls_back_keyed_and_unkeyed_operations(self):
        for operation in self.case.operations:
            for keyed in (False, True):
                with self.subTest(operation=operation, keyed=keyed):
                    url, body = self.case.arrange(operation)
                    event = {"deposit": "deposit", "withdraw": "withdrawal",
                             "open": "trade_open", "close": "trade_close"}[operation]
                    with self.case.db() as conn:
                        conn.execute("CREATE TRIGGER fail_audit AFTER INSERT ON balance_history "
                                     f"WHEN NEW.operation_type = '{event}' "
                                     "BEGIN SELECT RAISE(ABORT, 'audit metadata failure'); END")
                    before = self.case.state()
                    key = operation if keyed else None
                    with self.assertRaises(sqlite3.IntegrityError):
                        self.case.post(url, body, key=key)
                    self.assertEqual(self.case.state(), before)
                    with self.case.db() as conn:
                        conn.execute("DROP TRIGGER fail_audit")
                    self.assertEqual(self.case.post(url, body, key=key).status_code, 200)
                    self.assert_reconciled()

    def test_initial_history_failure_rolls_back_wallet_creation(self):
        with self.case.db() as conn:
            conn.execute("CREATE TRIGGER fail_initial_audit AFTER INSERT ON balance_history "
                         "WHEN NEW.operation_type = 'initialization' "
                         "BEGIN SELECT RAISE(ABORT, 'initial audit failure'); END")
        before = self.case.state()
        with self.assertRaises(sqlite3.IntegrityError):
            self.case.client.get("/api/wallet", headers={"Cookie": "session=one"})
        self.assertEqual(self.case.state(), before)

    def legacy_database(self):
        path = str(Path(self.case.path).with_name("legacy.db"))
        conn = sqlite3.connect(path)
        conn.execute(f"PRAGMA journal_mode={self.journal_mode}")
        conn.executescript("CREATE TABLE users (id INTEGER PRIMARY KEY); INSERT INTO users VALUES (1);")
        conn.executescript(wallet.SCHEMA)
        conn.execute("INSERT INTO wallets VALUES (1, 750, 1000, 1, 1)")
        conn.executemany("INSERT INTO balance_history (user_id, balance, created_at) VALUES (1, ?, 1)",
                         [(1000,), (750,)])
        conn.commit()
        conn.close()
        return path

    def test_legacy_migration_leaves_metadata_null_and_preserves_new_rows(self):
        conn = dbcompat.connect(self.legacy_database())
        try:
            wallet.init_schema(conn)
            columns = {row[1]: row for row in conn.execute("PRAGMA table_info(balance_history)")}
            for name in self.metadata_columns:
                self.assertIn(name, columns)
                self.assertEqual(columns[name][3], 0)
                self.assertIsNone(columns[name][4])
            legacy = [dict(row) for row in conn.execute("SELECT * FROM balance_history ORDER BY id")]
            self.assertEqual([row["balance"] for row in legacy], [1000, 750])
            for row in legacy:
                for name in self.metadata_columns:
                    self.assertIsNone(row[name])
            with conn:
                wallet.deposit(conn, 1, 20)
            before = [dict(row) for row in conn.execute("SELECT * FROM balance_history ORDER BY id")]
            wallet.init_schema(conn)
            wallet.init_schema(conn)
            after = [dict(row) for row in conn.execute("SELECT * FROM balance_history ORDER BY id")]
            self.assertEqual(after, before)
            self.assertEqual(after[:2], legacy)
            self.assertEqual(after[-1]["operation_type"], "deposit")
            self.assertEqual(after[-1]["delta"], 20)
        finally:
            conn.close()

    def test_concurrent_schema_initialization_is_repeatable(self):
        path = self.legacy_database()
        barrier = threading.Barrier(2)

        def initialize():
            conn = dbcompat.connect(path)
            try:
                barrier.wait(timeout=5)
                wallet.init_schema(conn)
            finally:
                conn.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(initialize) for _ in range(2)]
            for result in futures:
                result.result(timeout=10)
        conn = dbcompat.connect(path)
        try:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(balance_history)")]
            self.assertEqual(len(columns), 9)
            for row in conn.execute("SELECT * FROM balance_history"):
                for name in self.metadata_columns:
                    self.assertIsNone(row[name])
        finally:
            conn.close()

    def test_diagnostics_have_only_allowlisted_fields_and_no_sensitive_values(self):
        secret_key = "private-idempotency-key"
        secret_note = "private-note-password-token"
        self.case.post("/api/wallet/deposit", {"amount": 1, "note": secret_note}, key=secret_key)
        self.assertEqual(self.case.post("/api/wallet/deposit", {"amount": 2, "note": secret_note},
                                        key=secret_key).status_code, 409)
        self.assertEqual(self.case.post("/api/wallet/deposit", {"amount": 1, "note": secret_note},
                                        key="invalid " + secret_key).status_code, 422)
        self.assertEqual(self.case.post("/api/positions/999/close", key="private-close-key").status_code, 404)
        events = [json.loads(call.args[0]) for call in self.warning.call_args_list]
        self.assertEqual([event["reason_code"] for event in events],
                         ["idempotency_conflict", "invalid_idempotency_key", "position_unavailable"])
        self.assertEqual([event["status"] for event in events], [409, 422, 404])
        for event in events:
            self.assertEqual(set(event), {"operation", "user_id", "status", "reason_code", "correlation_id"})
            self.assertEqual(event["user_id"], 1)
            self.assertRegex(event["correlation_id"], r"^[0-9a-f]{32}$")
        self.assertEqual(len({event["correlation_id"] for event in events}), 3)
        rendered = repr(self.warning.call_args_list)
        for secret in (secret_key, secret_note, "private-close-key", "session=one", "response_json"):
            self.assertNotIn(secret, rendered)
        for call in self.warning.call_args_list:
            self.assertEqual(len(call.args), 1)
            self.assertEqual(call.kwargs, {"exc_info": False, "stack_info": False})

    def test_replays_and_insufficient_funds_do_not_emit_events(self):
        url, body = self.case.arrange("deposit")
        first = self.case.post(url, body, key="good")
        self.assertEqual(self.case.post(url, body, key="good").content, first.content)
        self.assertEqual(self.case.post("/api/wallet/withdraw", {"amount": 100000}, key="funds").status_code, 409)
        self.assertEqual(self.case.post("/api/positions", dict(ticker="AAPL", side="long", amount=100000),
                                        key="open-funds").status_code, 409)
        self.warning.assert_not_called()

    def test_unexpected_failure_logs_only_after_full_rollback_and_connection_close(self):
        self.case.arrange("deposit")
        before = self.case.state()
        observations = []
        original = wallet.deposit

        def fail_after_write(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError("secret-cookie-and-token-in-exception")

        def capture(message, **kwargs):
            active = len(self.case.active_connections)
            observations.append((json.loads(message), active, self.case.state()))

        self.warning.side_effect = capture
        with patch.object(wallet, "deposit", side_effect=fail_after_write):
            with self.assertRaisesRegex(RuntimeError, "secret-cookie-and-token-in-exception"):
                self.case.post("/api/wallet/deposit", {"amount": 1, "note": "private-note"}, key="private-key")
        self.assertEqual(len(observations), 1)
        event, active, state = observations[0]
        self.assertEqual(active, 0)
        self.assertEqual(state, before)
        self.assertEqual(event["reason_code"], "unexpected_failure")
        self.assertEqual(event["status"], 500)
        self.assertNotIn("secret-cookie", repr(self.warning.call_args_list))
        self.assertNotIn("private-note", repr(self.warning.call_args_list))
        self.assertNotIn("private-key", repr(self.warning.call_args_list))

    def test_logging_failures_preserve_success_replay_rejection_and_failure(self):
        self.warning.side_effect = RuntimeError("broken logging handler")
        url, body = self.case.arrange("deposit")
        first = self.case.post(url, body, key="good")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(self.case.post(url, body, key="good").content, first.content)
        self.assertEqual(self.case.post(url, dict(body, amount=21), key="good").status_code, 409)
        self.assertEqual(self.case.post(url, body, key="bad key").status_code, 422)
        self.assertEqual(self.case.post("/api/positions/999/close").status_code, 404)
        before = self.case.state()
        with patch.object(wallet, "deposit", side_effect=RuntimeError("original operation failure")):
            with self.assertRaisesRegex(RuntimeError, "original operation failure"):
                self.case.post(url, body, key="failed")
        self.assertEqual(self.case.state(), before)
        self.assertEqual(self.warning.call_count, 4)
        self.assert_reconciled()

    def test_contention_logs_after_request_cleanup_without_changing_503(self):
        url, body = self.case.arrange("deposit")
        before = self.case.state()
        events = []
        holder = dbcompat.connect(self.case.path)
        self.case.busy_timeout = 20

        def capture(message, **kwargs):
            events.append((json.loads(message), len(self.case.active_connections)))

        self.warning.side_effect = capture
        try:
            holder.execute("BEGIN IMMEDIATE")
            response = self.case.post(url, body, key="busy")
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.headers["Retry-After"], "1")
        finally:
            holder.rollback()
            holder.close()
            self.case.busy_timeout = 5000
        self.assertEqual(self.case.state(), before)
        self.assertEqual(len(events), 1)
        event, active = events[0]
        self.assertEqual(active, 0)
        self.assertEqual(event["status"], 503)
        self.assertEqual(event["reason_code"], "database_contention")


class FinancialAuditWalTest(FinancialAuditTest):
    journal_mode = "wal"
