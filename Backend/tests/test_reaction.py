"""Run from Backend/:  .venv/bin/python -m unittest tests.test_reaction -v"""
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

import pandas as pd

from pipeline import reaction

UTC = timezone.utc
T0 = datetime(2026, 11, 16, 15, 0, tzinfo=UTC)  # a Monday, market open


def make_bars(start: datetime, end: datetime, base: float, step: float = 0.0) -> pd.Series:
    """5-minute closes, indexed by bar END time, price drifts by `step` per bar."""
    idx = pd.date_range(start, end, freq="5min", tz="UTC")
    return pd.Series([base + step * i for i in range(len(idx))], index=idx)


class PriceAtTest(unittest.TestCase):
    def test_last_bar_at_or_before(self):
        bars = make_bars(T0, T0 + timedelta(hours=1), 100.0, 1.0)
        self.assertEqual(reaction.price_at(bars, T0 + timedelta(minutes=7)), 101.0)
        self.assertEqual(reaction.price_at(bars, T0), 100.0)

    def test_before_first_bar_is_none(self):
        bars = make_bars(T0, T0 + timedelta(hours=1), 100.0)
        self.assertIsNone(reaction.price_at(bars, T0 - timedelta(minutes=1)))

    def test_empty_or_missing(self):
        self.assertIsNone(reaction.price_at(None, T0))
        self.assertIsNone(reaction.price_at(pd.Series(dtype=float), T0))


class FillRowTest(unittest.TestCase):
    def setUp(self):
        self.bars = make_bars(T0 - timedelta(days=1), T0 + timedelta(days=6), 100.0, 0.01)
        self.spy = make_bars(T0 - timedelta(days=1), T0 + timedelta(days=6), 500.0, 0.0)

    def test_only_due_slots_are_filled(self):
        now = T0 + timedelta(hours=2)  # 1h slot is due, 1d and 5d are not
        row = reaction.fill_row({}, T0, self.bars, self.spy, now)
        self.assertIsNotNone(row["p0"])
        self.assertIsNotNone(row["p_1h"])
        self.assertIsNone(row.get("p_1d"))
        self.assertIsNone(row.get("p_5d"))
        self.assertEqual(row["market_open"], 1)

    def test_safety_margin_blocks_a_slot_that_just_passed(self):
        now = T0 + timedelta(hours=1, minutes=10)  # 1h mark passed 10 min ago, margin is 30 min
        row = reaction.fill_row({}, T0, self.bars, self.spy, now)
        self.assertIsNone(row.get("p_1h"))

    def test_filled_values_are_never_overwritten(self):
        now = T0 + timedelta(days=6)
        first = reaction.fill_row({}, T0, self.bars, self.spy, now)
        again = reaction.fill_row({**first, "p_1h": 1.23}, T0, self.bars, self.spy, now)
        self.assertEqual(again["p_1h"], 1.23)
        self.assertIsNotNone(again["p_5d"])

    def test_closed_market_is_flagged(self):
        night = T0.replace(hour=2)  # no bar within 10 minutes before this time
        bars = make_bars(T0 - timedelta(days=1), T0 - timedelta(days=1) + timedelta(hours=6), 100.0)
        row = reaction.fill_row({}, night, bars, self.spy, T0 + timedelta(days=6))
        self.assertEqual(row["market_open"], 0)


class RunTest(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            "CREATE TABLE news_items (id INTEGER PRIMARY KEY, ticker TEXT, title TEXT, source TEXT, url TEXT, "
            "published_at TEXT, first_seen_at TEXT, last_seen_at TEXT, rule_noise INTEGER);"
        )
        pub = T0.isoformat()
        self.conn.executemany(
            "INSERT INTO news_items (ticker, title, source, url, published_at, first_seen_at, last_seen_at, rule_noise) "
            "VALUES (?,?,?,?,?,?,?,?)",
            [("AAA", "good news", "x", "u1", pub, pub, pub, 0), ("AAA", "noise", "x", "u2", pub, pub, pub, 1)],
        )
        self.conn.commit()
        self.bars = make_bars(T0 - timedelta(days=1), T0 + timedelta(days=6), 100.0, 0.01)

    def tearDown(self):
        self.conn.close()
        os.unlink(self.path)

    def fake(self, ticker):
        return self.bars

    def test_first_run_fills_1h_only_and_skips_noise(self):
        now = T0 + timedelta(hours=3)
        stats = reaction.run(self.conn, self.fake, now, delay=0)
        self.assertEqual(stats["rows"], 1)
        r = self.conn.execute("SELECT * FROM news_reaction").fetchall()
        self.assertEqual(len(r), 1)
        self.assertIsNotNone(r[0]["p_1h"])
        self.assertIsNone(r[0]["p_5d"])

    def test_later_run_completes_the_row_and_stops_retrying(self):
        reaction.run(self.conn, self.fake, T0 + timedelta(hours=3), delay=0)
        reaction.run(self.conn, self.fake, T0 + timedelta(days=6), delay=0)
        r = self.conn.execute("SELECT * FROM news_reaction").fetchone()
        self.assertIsNotNone(r["p_1d"])
        self.assertIsNotNone(r["p_5d"])
        stats = reaction.run(self.conn, self.fake, T0 + timedelta(days=7), delay=0)
        self.assertEqual(stats["tickers"], 0)

    def test_failed_ticker_does_not_stop_the_run(self):
        def flaky(ticker):
            if ticker == "AAA":
                raise RuntimeError("boom")
            return self.bars

        stats = reaction.run(self.conn, flaky, T0 + timedelta(hours=3), delay=0)
        self.assertEqual(stats["failed"], 1)
        self.assertEqual(stats["rows"], 0)


if __name__ == "__main__":
    unittest.main()
