"""SQLite cache observation ordering, legacy upgrade, and ingest integration."""
import contextlib
import io
import sqlite3
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

from app import trading
from app.price_cache import init_price_observations
from pipeline import ingest


class PriceCacheTest(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.addCleanup(self.conn.close)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(trading.PRICES_SCHEMA)
        self.conn.execute("INSERT INTO prices VALUES ('AAPL', '2026-01-02', 100, 100, 100, 100, 1)")
        self.conn.commit()
        init_price_observations(self.conn)

    @staticmethod
    def bar(price, date="2026-01-02"):
        return dict(date=date, open=price, high=price, low=price, close=price, volume=2)

    def test_legacy_upgrade_preserves_rows_and_is_repeatable(self):
        init_price_observations(self.conn)
        row = self.conn.execute("SELECT close, observed_at_ns FROM prices").fetchone()
        self.assertEqual(tuple(row), (100, 0))
        trading.save_price_bar(self.conn, "AAPL", self.bar(110), 10)
        self.assertEqual(trading.latest_close(self.conn, "AAPL"), 110)

    def test_newer_lower_price_wins_older_and_equal_observations_do_not(self):
        for price, observed in ((120, 20), (110, 10), (130, 20), (90, 30)):
            with self.conn:
                self.assertEqual(trading.save_price_bar(self.conn, "AAPL", self.bar(price), observed), price)
            expected = 90 if observed == 30 else 120
            self.assertEqual(trading.latest_close(self.conn, "AAPL"), expected)
        with self.conn:
            trading.save_price_bar(self.conn, "MSFT", self.bar(80), 1)
            trading.save_price_bar(self.conn, "AAPL", self.bar(70, "2026-01-03"), 1)
        self.assertEqual(trading.latest_close(self.conn, "MSFT"), 80)
        self.assertEqual(trading.latest_close(self.conn, "AAPL"), 70)

    def test_ingest_respects_observation_order_against_trading_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "prices.db")
            conn = sqlite3.connect(path)
            try:
                conn.executescript(ingest.SCHEMA)
                init_price_observations(conn)
                with conn:
                    trading.save_price_bar(conn, "AAPL", self.bar(120), 20)
                frame = pd.DataFrame({
                    "Open": [110.0], "High": [110.0], "Low": [110.0],
                    "Close": [110.0], "Volume": [2],
                }, index=pd.to_datetime(["2026-01-02"]))
                universe = pd.DataFrame([dict(ticker="AAPL", name="Apple", gics_sector="tech", sector="tech")])
                for observation, expected in ((10, 120), (30, 110)):
                    frame.attrs["observed_at_ns"] = observation
                    with patch.object(ingest, "DB_PATH", path), \
                            patch.object(ingest, "connect", return_value=conn), \
                            patch("sys.argv", ["ingest"]), \
                            patch.object(ingest, "fetch_universe", return_value=universe), \
                            patch.object(ingest, "fetch_prices", return_value={"AAPL": frame}), \
                            patch.object(ingest, "validate", return_value=(frame, [])), \
                            contextlib.redirect_stdout(io.StringIO()):
                        ingest.main()
                    self.assertEqual(conn.execute("SELECT close FROM prices").fetchone()[0], expected)
            finally:
                conn.close()
