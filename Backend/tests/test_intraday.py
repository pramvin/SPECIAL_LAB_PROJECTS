"""Run from Backend/:  .venv/bin/python -m unittest tests.test_intraday -v"""
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

import pandas as pd

from pipeline import intraday

NY = "America/New_York"


def session(day: str, bars: int, volume: float, price: float = 100.0, start="09:30") -> pd.DataFrame:
    """`bars` five-minute bars from `start`; index = bar start time in New York time."""
    idx = pd.date_range(f"{day} {start}", periods=bars, freq="5min", tz=NY)
    return pd.DataFrame({"Open": price, "Close": price, "Volume": float(volume)}, index=idx)


def history(prior_days: int, today_bars: int, today_volume: float, prior_volume=100.0) -> pd.DataFrame:
    days = pd.bdate_range("2026-10-01", periods=prior_days)
    parts = [session(d.strftime("%Y-%m-%d"), 78, prior_volume) for d in days]
    parts.append(session("2026-11-20", today_bars, today_volume))
    return pd.concat(parts)


class SnapshotTest(unittest.TestCase):
    def test_rvol_compares_same_clock_time(self):
        # 12 earlier full sessions at 100 per bar; today has 40 bars at 200 per bar -> twice as busy
        s = intraday.snapshot(history(12, 40, 200.0))
        self.assertAlmostEqual(s["rvol"], 2.0)
        self.assertEqual(s["prior_sessions"], 12)
        self.assertEqual(s["session_date"], "2026-11-20")

    def test_too_few_reference_sessions_gives_no_rvol(self):
        self.assertIsNone(intraday.snapshot(history(5, 40, 200.0))["rvol"])

    def test_half_day_sessions_are_not_references(self):
        parts = [history(12, 40, 200.0)]
        half = session("2026-09-25", 30, 1.0)  # ends well before today's reference time
        s = intraday.snapshot(pd.concat([half] + parts))
        self.assertEqual(s["prior_sessions"], 12)

    def test_gap_and_move_since_open(self):
        df = history(12, 3, 100.0)
        today = df.index.date == df.index.date[-1]
        df.loc[today, "Open"] = 102.0
        df.loc[today, "Close"] = 104.04
        s = intraday.snapshot(df)
        self.assertAlmostEqual(s["gap_pct"], 0.02)
        self.assertAlmostEqual(s["ret_since_open"], 0.02)

    def test_asof_is_the_end_of_the_last_bar_in_utc(self):
        s = intraday.snapshot(history(12, 2, 100.0))  # bars 09:30 and 09:35 -> last ends 09:40 NY = 14:40 UTC
        self.assertEqual(s["asof"], datetime(2026, 11, 20, 14, 40, tzinfo=timezone.utc))

    def test_empty(self):
        self.assertIsNone(intraday.snapshot(None))
        self.assertIsNone(intraday.snapshot(pd.DataFrame()))


class RunTest(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(intraday.SCHEMA)
        self.df = history(12, 40, 200.0)
        self.asof = intraday.snapshot(self.df)["asof"]
        self.calls = 0

    def tearDown(self):
        self.conn.close()
        os.unlink(self.path)

    def get(self, ticker):
        self.calls += 1
        return self.df

    def test_saves_while_the_market_is_open_and_is_idempotent(self):
        now = self.asof + timedelta(minutes=10)
        s = intraday.run(self.conn, ["AAA", "BBB"], self.get, now, delay=0)
        self.assertEqual(s["saved"], 2)
        intraday.run(self.conn, ["AAA", "BBB"], self.get, now, delay=0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM intraday_snapshot").fetchone()[0], 2)

    def test_closed_market_stops_after_one_probe_and_writes_nothing(self):
        now = self.asof + timedelta(hours=10)
        s = intraday.run(self.conn, ["AAA", "BBB", "CCC"], self.get, now, delay=0)
        self.assertEqual((s["saved"], s["closed"], self.calls), (0, 3, 1))

    def test_failed_ticker_does_not_stop_the_run(self):
        def flaky(t):
            if t == "AAA":
                raise RuntimeError("boom")
            return self.df

        s = intraday.run(self.conn, ["AAA", "BBB"], flaky, self.asof + timedelta(minutes=5), delay=0)
        self.assertEqual((s["failed"], s["saved"]), (1, 1))


if __name__ == "__main__":
    unittest.main()
