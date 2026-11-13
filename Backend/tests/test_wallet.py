"""Run from Backend/:  .venv/bin/python -m unittest tests.test_wallet -v"""
import os
import sqlite3
import tempfile
import unittest

from app import wallet


class WalletTest(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL)")
        self.conn.execute("INSERT INTO users (id, email) VALUES (1, 'one@example.test')")
        self.conn.execute("INSERT INTO users (id, email) VALUES (2, 'two@example.test')")
        self.conn.commit()
        wallet.init_schema(self.conn)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.path)

    def commit(self):
        self.conn.commit()
        return self.conn

    def test_schema_is_idempotent(self):
        wallet.init_schema(self.conn)
        wallet.init_schema(self.conn)
        tables = {
            row["name"]
            for row in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        self.assertTrue({"wallets", "wallet_transactions", "balance_history"} <= tables)

    def test_wallet_starts_at_1000_with_initial_history(self):
        row = wallet.ensure_wallet(self.conn, 1)
        self.commit()
        self.assertEqual(wallet.money(row["balance"]), 1000.0)
        self.assertEqual(wallet.money(row["starting_balance"]), 1000.0)
        history = wallet.history_payload(self.conn, 1, 10)
        self.assertEqual(len(history["items"]), 1)
        self.assertEqual(history["items"][0]["balance"], 1000.0)
        self.assertEqual(history["items"][0]["change_pct"], 0.0)

    def test_deposit_updates_balance_and_logs_transaction(self):
        wallet.ensure_wallet(self.conn, 1)
        row, tx = wallet.deposit(self.conn, 1, 250.25, "test deposit")
        self.commit()
        self.assertEqual(wallet.money(row["balance"]), 1250.25)
        self.assertEqual(tx["kind"], "deposit")
        self.assertEqual(tx["amount"], 250.25)
        self.assertEqual(tx["balance_after"], 1250.25)
        self.assertEqual(tx["note"], "test deposit")
        history = wallet.history_payload(self.conn, 1, 10)
        self.assertEqual([item["balance"] for item in history["items"]], [1000.0, 1250.25])

    def test_withdraw_rejects_insufficient_balance(self):
        wallet.ensure_wallet(self.conn, 1)
        with self.assertRaises(wallet.InsufficientFunds):
            wallet.withdraw(self.conn, 1, 1000.01)
        self.assertEqual(wallet.money(wallet.ensure_wallet(self.conn, 1)["balance"]), 1000.0)

    def test_withdraw_updates_balance_and_logs_transaction(self):
        wallet.ensure_wallet(self.conn, 1)
        row, tx = wallet.withdraw(self.conn, 1, 100)
        self.commit()
        self.assertEqual(wallet.money(row["balance"]), 900.0)
        self.assertEqual(tx["kind"], "withdraw")
        self.assertEqual(tx["amount"], 100.0)
        self.assertEqual(tx["balance_after"], 900.0)

    def test_rejects_non_positive_amounts(self):
        wallet.ensure_wallet(self.conn, 1)
        with self.assertRaises(ValueError):
            wallet.deposit(self.conn, 1, 0)
        with self.assertRaises(ValueError):
            wallet.withdraw(self.conn, 1, -1)

    def test_history_is_chronological_and_tracks_change_pct(self):
        wallet.ensure_wallet(self.conn, 1)
        wallet.deposit(self.conn, 1, 100)
        wallet.withdraw(self.conn, 1, 50)
        self.commit()
        history = wallet.history_payload(self.conn, 1, 10)
        self.assertEqual([item["balance"] for item in history["items"]], [1000.0, 1100.0, 1050.0])
        self.assertEqual(history["items"][-1]["change_pct"], 5.0)

    def test_users_are_isolated(self):
        wallet.ensure_wallet(self.conn, 1)
        wallet.ensure_wallet(self.conn, 2)
        wallet.deposit(self.conn, 1, 500)
        self.commit()
        self.assertEqual(wallet.money(wallet.ensure_wallet(self.conn, 1)["balance"]), 1500.0)
        self.assertEqual(wallet.money(wallet.ensure_wallet(self.conn, 2)["balance"]), 1000.0)
        self.assertEqual(len(wallet.history_payload(self.conn, 2, 10)["items"]), 1)


if __name__ == "__main__":
    unittest.main()
