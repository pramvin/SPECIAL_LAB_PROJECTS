"""Run from Backend/:  .venv/bin/python -m unittest tests.test_trading -v"""
import os
import sqlite3
import tempfile
import unittest

from app import trading, wallet


class TradingTest(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL)")
        self.conn.execute("INSERT INTO users (id, email) VALUES (1, 'one@example.test')")
        self.conn.execute("INSERT INTO users (id, email) VALUES (2, 'two@example.test')")
        self.conn.execute(
            "CREATE TABLE prices (ticker TEXT NOT NULL, date TEXT NOT NULL, close REAL NOT NULL)"
        )
        self.set_price("AAPL", 100.0, "2026-01-01")
        self.conn.commit()
        wallet.init_schema(self.conn)
        trading.init_schema(self.conn)
        wallet.ensure_wallet(self.conn, 1)
        wallet.ensure_wallet(self.conn, 2)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.path)

    def set_price(self, ticker, price, date="2026-01-02"):
        self.conn.execute(
            "INSERT INTO prices (ticker, date, close) VALUES (?, ?, ?)",
            (ticker, date, price),
        )

    def commit(self):
        self.conn.commit()
        return self.conn

    def test_schema_is_idempotent(self):
        trading.init_schema(self.conn)
        trading.init_schema(self.conn)
        tables = {
            row["name"]
            for row in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        self.assertTrue({"positions", "trades"} <= tables)

    def test_open_long_deducts_margin_and_uses_leverage(self):
        position, wallet_row = trading.open_position(
            self.conn, 1, "aapl", "long", 500, 2
        )
        self.commit()
        self.assertEqual(position["ticker"], "AAPL")
        self.assertEqual(trading.money(position["notional"]), 1000.0)
        self.assertEqual(round(position["quantity"], 6), 10.0)
        self.assertEqual(trading.money(position["amount_deducted"]), 500.0)
        self.assertEqual(wallet.money(wallet_row["balance"]), 500.0)

    def test_open_short_is_supported(self):
        position, _ = trading.open_position(self.conn, 1, "AAPL", "short", 100, 1)
        self.commit()
        self.assertEqual(position["side"], "short")
        self.assertEqual(round(position["quantity"], 6), 1.0)

    def test_close_long_profit_credits_wallet_and_logs_trade(self):
        position, _ = trading.open_position(self.conn, 1, "AAPL", "long", 500, 2)
        self.commit()
        self.set_price("AAPL", 110.0)
        self.commit()
        trade, wallet_row = trading.close_position(self.conn, 1, position["id"])
        self.commit()
        self.assertEqual(trading.money(trade["pnl"]), 100.0)
        self.assertEqual(trade["pnl_pct"], 20.0)
        self.assertEqual(wallet.money(wallet_row["balance"]), 1100.0)
        self.assertEqual(trading.list_positions(self.conn, 1), [])
        trades = trading.list_trades(self.conn, 1, 10)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["ticker"], "AAPL")
        self.assertEqual(trades[0]["exit_price"], 110.0)

    def test_close_short_profit(self):
        position, _ = trading.open_position(self.conn, 1, "AAPL", "short", 500, 2)
        self.commit()
        self.set_price("AAPL", 90.0)
        self.commit()
        trade, wallet_row = trading.close_position(self.conn, 1, position["id"])
        self.commit()
        self.assertEqual(trading.money(trade["pnl"]), 100.0)
        self.assertEqual(trade["pnl_pct"], 20.0)
        self.assertEqual(wallet.money(wallet_row["balance"]), 1100.0)

    def test_loss_can_make_balance_negative(self):
        position, _ = trading.open_position(self.conn, 1, "AAPL", "long", 900, 10)
        self.commit()
        self.set_price("AAPL", 1.0)
        self.commit()
        trade, wallet_row = trading.close_position(self.conn, 1, position["id"])
        self.commit()
        self.assertEqual(trading.money(trade["pnl"]), -8910.0)
        self.assertEqual(trade["pnl_pct"], -990.0)
        self.assertEqual(wallet.money(wallet_row["balance"]), -7910.0)

    def test_open_rejects_insufficient_balance(self):
        with self.assertRaises(trading.InsufficientFunds):
            trading.open_position(self.conn, 1, "AAPL", "long", 1000.01, 1)

    def test_open_rejects_unknown_ticker(self):
        with self.assertRaises(trading.UnknownTicker):
            trading.open_position(self.conn, 1, "NOPE", "long", 100, 1)

    def test_open_rejects_invalid_side_and_leverage(self):
        with self.assertRaises(trading.TradingError):
            trading.open_position(self.conn, 1, "AAPL", "sideways", 100, 1)
        with self.assertRaises(trading.TradingError):
            trading.open_position(self.conn, 1, "AAPL", "long", 100, 10.1)
        with self.assertRaises(trading.TradingError):
            trading.open_position(self.conn, 1, "AAPL", "long", 0, 1)

    def test_positions_include_unrealized_pnl(self):
        trading.open_position(self.conn, 1, "AAPL", "long", 500, 2)
        self.commit()
        self.set_price("AAPL", 105.0)
        self.commit()
        items = trading.list_positions(self.conn, 1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["current_price"], 105.0)
        self.assertEqual(items[0]["unrealized_pnl"], 50.0)
        self.assertEqual(items[0]["unrealized_pnl_pct"], 10.0)

    def test_users_are_isolated(self):
        position, _ = trading.open_position(self.conn, 1, "AAPL", "long", 100, 1)
        self.commit()
        with self.assertRaises(trading.PositionNotFound):
            trading.close_position(self.conn, 2, position["id"])
        self.assertEqual(len(trading.list_positions(self.conn, 2)), 0)
        self.assertEqual(len(trading.list_trades(self.conn, 2, 10)), 0)


if __name__ == "__main__":
    unittest.main()
