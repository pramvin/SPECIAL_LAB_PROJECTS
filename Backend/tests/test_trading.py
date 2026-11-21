"""Run from Backend/:  .venv/bin/python -m unittest tests.test_trading -v"""
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

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
        wallet.init_schema(self.conn)
        trading.init_schema(self.conn)
        self.set_price("AAPL", 100.0, "2026-01-01")
        wallet.ensure_wallet(self.conn, 1)
        wallet.ensure_wallet(self.conn, 2)
        self.conn.commit()
        self.market_data_patch = patch.object(
            trading, "fetch_latest_bar", side_effect=self.latest_bar_from_db
        )
        self.market_data_patch.start()

    def tearDown(self):
        self.market_data_patch.stop()
        self.conn.close()
        os.unlink(self.path)

    def set_price(self, ticker, price, date="2026-01-02"):
        self.conn.execute(
            "INSERT INTO prices (ticker, date, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(ticker, date) DO UPDATE SET "
            "open=excluded.open, high=excluded.high, low=excluded.low, "
            "close=excluded.close, volume=excluded.volume",
            (ticker, date, price, price, price, price, 0),
        )

    def latest_bar_from_db(self, ticker):
        row = self.conn.execute(
            "SELECT date, open, high, low, close, volume FROM prices "
            "WHERE ticker = ? ORDER BY date DESC LIMIT 1",
            (ticker,),
        ).fetchone()
        if row is None:
            raise trading.UnknownTicker("No price data for this ticker")
        return dict(row)

    def commit(self):
        self.conn.commit()
        return self.conn

    def insert_trade_fixture(
        self, user_id, ticker, side, pnl, closed_at, trade_id
    ):
        self.conn.execute(
            "INSERT INTO trades "
            "(position_id, user_id, ticker, side, entry_price, exit_price, "
            "quantity, leverage, amount_deducted, pnl, pnl_pct, opened_at, closed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                trade_id,
                user_id,
                ticker,
                side,
                100.0,
                100.0 + pnl,
                1.0,
                1.0,
                100.0,
                pnl,
                pnl,
                closed_at - 60,
                closed_at,
            ),
        )

    def test_schema_is_idempotent(self):
        trading.init_schema(self.conn)
        trading.init_schema(self.conn)
        tables = {
            row["name"]
            for row in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        self.assertTrue({"positions", "trades", "prices"} <= tables)

    def test_yfinance_daily_bar_is_persisted_for_a_position(self):
        self.market_data_patch.stop()
        try:
            with patch.object(trading.yf, "Ticker") as ticker:
                ticker.return_value.history.return_value = pd.DataFrame(
                    {
                        "Open": [120.0],
                        "High": [125.0],
                        "Low": [118.0],
                        "Close": [123.0],
                        "Volume": [456],
                    },
                    index=pd.to_datetime(["2026-01-03"]),
                )

                position, _ = trading.open_position(
                    self.conn, 1, "AAPL", "long", 100, 1
                )
                ticker.assert_called_once_with("AAPL")
                ticker.return_value.history.assert_called_once_with(
                    period="1mo", interval="1d", auto_adjust=True
                )
                saved = self.conn.execute(
                    "SELECT date, close, volume FROM prices "
                    "WHERE ticker = ? AND date = ?",
                    ("AAPL", "2026-01-03"),
                ).fetchone()

            self.assertEqual(position["entry_price"], 123.0)
            self.assertEqual(saved["close"], 123.0)
            self.assertEqual(saved["volume"], 456)
        finally:
            self.market_data_patch.start()

    def test_yfinance_failure_does_not_open_or_debit_position(self):
        self.market_data_patch.stop()
        try:
            with patch.object(trading.yf, "Ticker") as ticker:
                ticker.return_value.history.side_effect = RuntimeError("offline")
                with self.assertRaises(trading.MarketDataUnavailable):
                    trading.open_position(self.conn, 1, "AAPL", "long", 100, 1)

            self.assertEqual(
                wallet.money(trading.ensure_wallet(self.conn, 1)["balance"]),
                1000.0,
            )
            self.assertEqual(trading.list_positions(self.conn, 1), [])
        finally:
            self.market_data_patch.start()

    def test_open_long_deducts_margin_and_uses_leverage(self):
        position, wallet_row = trading.open_position(
            self.conn, 1, "aapl", "long", 500, 5
        )
        self.commit()
        self.assertEqual(position["ticker"], "AAPL")
        self.assertEqual(trading.money(position["notional"]), 2500.0)
        self.assertEqual(round(position["quantity"], 6), 25.0)
        self.assertEqual(trading.money(position["amount_deducted"]), 500.0)
        self.assertEqual(wallet.money(wallet_row["balance"]), 500.0)

    def test_open_short_is_supported(self):
        position, _ = trading.open_position(self.conn, 1, "AAPL", "short", 100, 1)
        self.commit()
        self.assertEqual(position["side"], "short")
        self.assertEqual(round(position["quantity"], 6), 1.0)

    def test_close_long_profit_credits_wallet_and_logs_trade(self):
        position, _ = trading.open_position(self.conn, 1, "AAPL", "long", 500, 5)
        self.commit()
        self.set_price("AAPL", 110.0)
        self.commit()
        trade, wallet_row = trading.close_position(self.conn, 1, position["id"])
        self.commit()
        self.assertEqual(trading.money(trade["pnl"]), 250.0)
        self.assertEqual(trade["pnl_pct"], 50.0)
        self.assertEqual(wallet.money(wallet_row["balance"]), 1250.0)
        self.assertEqual(trading.list_positions(self.conn, 1), [])
        trades = trading.list_trades(self.conn, 1, 10)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["ticker"], "AAPL")
        self.assertEqual(trades[0]["exit_price"], 110.0)

    def test_close_short_profit(self):
        position, _ = trading.open_position(self.conn, 1, "AAPL", "short", 500, 5)
        self.commit()
        self.set_price("AAPL", 90.0)
        self.commit()
        trade, wallet_row = trading.close_position(self.conn, 1, position["id"])
        self.commit()
        self.assertEqual(trading.money(trade["pnl"]), 250.0)
        self.assertEqual(trade["pnl_pct"], 50.0)
        self.assertEqual(wallet.money(wallet_row["balance"]), 1250.0)

    @patch.object(trading, "LIQUIDATE_AT_MARGIN", False)
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
            trading.open_position(self.conn, 1, "AAPL", "long", 100, 2)
        with self.assertRaises(trading.TradingError):
            trading.open_position(self.conn, 1, "AAPL", "long", 0, 1)

    def test_positions_include_unrealized_pnl(self):
        trading.open_position(self.conn, 1, "AAPL", "long", 500, 5)
        self.commit()
        self.set_price("AAPL", 105.0)
        self.commit()
        items = trading.list_positions(self.conn, 1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["current_price"], 105.0)
        self.assertEqual(items[0]["unrealized_pnl"], 125.0)
        self.assertEqual(items[0]["unrealized_pnl_pct"], 25.0)

    def test_trade_history_filters_search_and_paginates(self):
        self.insert_trade_fixture(1, "AAPL", "long", 25, 100, 1)
        self.insert_trade_fixture(1, "MSFT", "short", -10, 200, 2)
        self.insert_trade_fixture(1, "AAPL", "short", 0, 300, 3)

        filtered = trading.trade_history(
            self.conn,
            1,
            10,
            search="aapl",
            side="long",
            outcome="win",
        )
        self.assertEqual(filtered["total"], 1)
        self.assertEqual(filtered["items"][0]["ticker"], "AAPL")
        self.assertEqual(filtered["items"][0]["pnl"], 25.0)

        first_page = trading.trade_history(self.conn, 1, 1)
        self.assertEqual(first_page["total"], 3)
        self.assertTrue(first_page["has_more"])
        self.assertEqual(first_page["items"][0]["id"], 3)
        breakeven = trading.trade_history(self.conn, 1, 10, outcome="breakeven")
        self.assertEqual(breakeven["total"], 1)

    def test_trading_summary_aggregates_all_user_activity(self):
        self.insert_trade_fixture(1, "AAPL", "long", 20, 100, 1)
        self.insert_trade_fixture(1, "MSFT", "short", -5, 200, 2)
        self.insert_trade_fixture(1, "AAPL", "long", 0, 300, 3)
        trading.open_position(self.conn, 1, "AAPL", "long", 100, 5)
        self.set_price("AAPL", 105.0)

        summary = trading.trading_summary(self.conn, 1)
        self.assertEqual(summary["closed_trade_count"], 3)
        self.assertEqual(summary["win_count"], 1)
        self.assertEqual(summary["loss_count"], 1)
        self.assertEqual(summary["breakeven_count"], 1)
        self.assertEqual(summary["win_rate_pct"], 33.33)
        self.assertEqual(summary["realized_pnl"], 15.0)
        self.assertEqual(summary["average_pnl"], 5.0)
        self.assertEqual(summary["best_trade_pnl"], 20.0)
        self.assertEqual(summary["worst_trade_pnl"], -5.0)
        self.assertEqual(summary["open_position_count"], 1)
        self.assertEqual(summary["open_margin"], 100.0)
        self.assertEqual(summary["unrealized_pnl"], 25.0)
        self.assertEqual(summary["unpriced_position_count"], 0)
        other_user = trading.trading_summary(self.conn, 2)
        self.assertEqual(other_user["closed_trade_count"], 0)
        self.assertEqual(other_user["realized_pnl"], 0.0)
        self.assertIsNone(other_user["win_rate_pct"])
        self.assertIsNone(other_user["average_pnl"])
        self.assertEqual(other_user["open_position_count"], 0)

    def test_trading_summary_marks_unpriced_positions(self):
        self.conn.execute(
            "INSERT INTO positions "
            "(user_id, ticker, side, entry_price, quantity, leverage, "
            "amount_deducted, notional, opened_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (1, "MISSING", "long", 100.0, 1.0, 1.0, 100.0, 100.0, 100),
        )
        summary = trading.trading_summary(self.conn, 1)
        self.assertIsNone(summary["unrealized_pnl"])
        self.assertEqual(summary["unpriced_position_count"], 1)

    # ---- leverage x5 / x10 / x50 / x100, exact deduction, live P/L ----------
    def test_exact_amount_is_deducted_for_every_leverage(self):
        for lev in trading.LEVERAGE_OPTIONS:
            before = wallet.ensure_wallet(self.conn, 1)["balance"]
            position, wallet_row = trading.open_position(
                self.conn, 1, "AAPL", "long", 12.34, lev
            )
            self.assertEqual(round(before - wallet_row["balance"], 2), 12.34)
            self.assertEqual(position["amount_deducted"], 12.34)
            self.assertEqual(position["notional"], round(12.34 * lev, 2))
            self.assertEqual(position["leverage"], lev)

    def test_amount_with_more_than_two_decimals_is_rejected_not_rounded(self):
        with self.assertRaises(trading.TradingError):
            trading.open_position(self.conn, 1, "AAPL", "long", 10.005, 5)
        self.assertEqual(wallet.ensure_wallet(self.conn, 1)["balance"], 1000.0)
        self.assertEqual(trading.list_positions(self.conn, 1), [])

    def test_only_listed_leverage_options_are_accepted(self):
        for bad in (0, 2, 7.5, 101, 1000):
            with self.assertRaises(trading.TradingError):
                trading.open_position(self.conn, 1, "AAPL", "long", 10, bad)

    def test_liquidation_price_long_and_short(self):
        self.assertEqual(trading.liquidation_price("long", 100, 100), 99.0)
        self.assertEqual(trading.liquidation_price("long", 100, 5), 80.0)
        self.assertEqual(trading.liquidation_price("short", 100, 50), 102.0)

    def test_leveraged_loss_is_capped_at_margin(self):
        position, _ = trading.open_position(self.conn, 1, "AAPL", "long", 100, 100)
        self.commit()
        self.set_price("AAPL", 90.0)  # -10% on x100 would be -1000% of margin
        self.commit()
        row = trading.list_positions(self.conn, 1)[0]
        self.assertTrue(row["liquidated"])
        self.assertEqual(row["unrealized_pnl"], -100.0)
        self.assertEqual(row["unrealized_pnl_pct"], -100.0)
        trade, wallet_row = trading.close_position(self.conn, 1, position["id"])
        self.assertEqual(trade["pnl"], -100.0)
        self.assertEqual(wallet.money(wallet_row["balance"]), 900.0)

    def test_preview_shows_every_leverage_for_the_same_margin(self):
        rows = trading.leverage_preview("long", 100.0, 100.0)
        self.assertEqual([r["leverage"] for r in rows], [5, 10, 50, 100])
        self.assertEqual([r["notional"] for r in rows], [500.0, 1000.0, 5000.0, 10000.0])
        self.assertEqual([r["quantity"] for r in rows], [5.0, 10.0, 50.0, 100.0])
        self.assertEqual(
            [r["liquidation_price"] for r in rows], [80.0, 90.0, 98.0, 99.0]
        )
        plus_five = {s["price_move_pct"]: s for s in rows[3]["scenarios"]}[5]
        self.assertEqual(plus_five["pnl"], 500.0)  # x100: +5% price = +500% margin
        short = trading.leverage_preview("short", 100.0, 100.0)
        minus_one = {s["price_move_pct"]: s for s in short[2]["scenarios"]}[-1]
        self.assertEqual(minus_one["pnl"], 50.0)   # short x50, price -1% = +50%
        minus_ten = {s["price_move_pct"]: s for s in short[0]["scenarios"]}[10]
        self.assertEqual(minus_ten["pnl"], -50.0)  # short x5, price +10% = -50%

    def test_live_positions_refresh_price_and_report_totals(self):
        trading._live_cache.clear()
        trading.open_position(self.conn, 1, "AAPL", "long", 100, 10)
        trading.open_position(self.conn, 1, "AAPL", "short", 100, 5)
        self.set_price("AAPL", 101.0, "2026-01-05")
        live = trading.list_positions_live(self.conn, 1)
        by_side = {p["side"]: p for p in live["items"]}
        self.assertEqual(by_side["long"]["current_price"], 101.0)
        self.assertEqual(by_side["long"]["unrealized_pnl"], 10.0)
        self.assertEqual(by_side["long"]["unrealized_pnl_pct"], 10.0)
        self.assertEqual(by_side["short"]["unrealized_pnl"], -5.0)
        self.assertEqual(live["totals"]["open_margin"], 200.0)
        self.assertEqual(live["totals"]["unrealized_pnl"], 5.0)
        self.assertEqual(live["totals"]["unrealized_pnl_pct"], 2.5)

    def test_live_price_falls_back_to_saved_close_when_provider_fails(self):
        trading._live_cache.clear()
        with patch.object(
            trading, "refresh_latest_close",
            side_effect=trading.MarketDataUnavailable("down"),
        ):
            price, stale = trading.live_price(self.conn, "AAPL")
        self.assertEqual(price, 100.0)
        self.assertTrue(stale)

    def test_old_leverage_check_is_migrated_without_losing_rows(self):
        self.conn.executescript(
            "DROP TABLE positions;"
            "CREATE TABLE positions (id INTEGER PRIMARY KEY,"
            " user_id INTEGER NOT NULL REFERENCES users(id), ticker TEXT NOT NULL,"
            " side TEXT NOT NULL CHECK (side IN ('long', 'short')),"
            " entry_price REAL NOT NULL CHECK (entry_price > 0),"
            " quantity REAL NOT NULL CHECK (quantity > 0),"
            " leverage REAL NOT NULL CHECK (leverage >= 1 AND leverage <= 10),"
            " amount_deducted REAL NOT NULL CHECK (amount_deducted > 0),"
            " notional REAL NOT NULL, opened_at INTEGER NOT NULL);"
            "INSERT INTO positions VALUES (7, 1, 'AAPL', 'long', 100, 5, 5, 100, 500, 1);"
        )
        trading.init_schema(self.conn)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0], 1)
        position, _ = trading.open_position(self.conn, 1, "AAPL", "long", 10, 100)
        self.assertEqual(position["leverage"], 100)
        trading.init_schema(self.conn)  # idempotent
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0], 2)

    def test_users_are_isolated(self):
        position, _ = trading.open_position(self.conn, 1, "AAPL", "long", 100, 1)
        self.commit()
        with self.assertRaises(trading.PositionNotFound):
            trading.close_position(self.conn, 2, position["id"])
        self.assertEqual(len(trading.list_positions(self.conn, 2)), 0)
        self.assertEqual(len(trading.list_trades(self.conn, 2, 10)), 0)


if __name__ == "__main__":
    unittest.main()

