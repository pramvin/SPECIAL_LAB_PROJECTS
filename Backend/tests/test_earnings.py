"""Run from Backend/:  .venv/bin/python -m unittest tests.test_earnings -v"""
import os
import sqlite3
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from pipeline import earnings

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)


def frame(rows):
    """rows: (timestamp text in New York time, estimate, actual, surprise)."""
    idx = pd.DatetimeIndex([pd.Timestamp(r[0], tz="America/New_York") for r in rows], name="Earnings Date")
    return pd.DataFrame({"EPS Estimate": [r[1] for r in rows], "Reported EPS": [r[2] for r in rows],
                         "Surprise(%)": [r[3] for r in rows]}, index=idx)


class RowsFromFrameTest(unittest.TestCase):
    def test_new_york_day_numbers_and_missing_values(self):
        rows = earnings.rows_from_frame(frame([
            ("2027-01-28 16:00", 2.91, float("nan"), float("nan")),
            ("2026-11-02 16:00", 1.98, 2.10, 5.8),
        ]))
        self.assertEqual([r["event_date"] for r in rows], ["2027-01-28", "2026-11-02"])
        self.assertIsNone(rows[0]["eps_actual"])
        self.assertEqual(rows[1]["surprise_pct"], 5.8)

    def test_empty_or_missing(self):
        self.assertEqual(earnings.rows_from_frame(None), [])
        self.assertEqual(earnings.rows_from_frame(pd.DataFrame()), [])


class Base(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(earnings.SCHEMA)

    def tearDown(self):
        self.conn.close()
        os.unlink(self.path)


class RunTest(Base):
    def fake(self, ticker):
        return [{"event_date": "2026-11-25", "eps_estimate": 1.0, "eps_actual": None, "surprise_pct": None}]

    def test_fetches_saves_and_skips_fresh_tickers(self):
        calls = []

        def get(t):
            calls.append(t)
            return self.fake(t)

        s = earnings.run(self.conn, ["AAA", "BBB"], get, NOW, delay=0)
        self.assertEqual((s["fetched"], s["events"]), (2, 2))
        earnings.run(self.conn, ["AAA", "BBB"], get, NOW + timedelta(hours=1), delay=0)
        self.assertEqual(len(calls), 2)  # nothing is stale an hour later
        earnings.run(self.conn, ["AAA"], get, NOW + timedelta(hours=21), delay=0)
        self.assertEqual(len(calls), 3)  # stale after MAX_AGE_H

    def test_failed_ticker_does_not_stop_the_run_and_is_retried(self):
        def flaky(t):
            if t == "AAA":
                raise RuntimeError("boom")
            return self.fake(t)

        s = earnings.run(self.conn, ["AAA", "BBB"], flaky, NOW, delay=0)
        self.assertEqual((s["failed"], s["fetched"]), (1, 1))
        self.assertEqual(earnings.stale(self.conn, ["AAA", "BBB"], NOW), ["AAA"])

    def test_empty_answer_is_remembered_so_it_is_not_asked_every_hour(self):
        earnings.run(self.conn, ["AAA"], lambda t: [], NOW, delay=0)
        self.assertEqual(earnings.stale(self.conn, ["AAA"], NOW + timedelta(hours=1)), [])

    def test_limit_caps_calls_per_run(self):
        s = earnings.run(self.conn, ["AAA", "BBB", "CCC"], self.fake, NOW, delay=0, limit=2)
        self.assertEqual(s["fetched"], 2)

    def test_rerun_updates_instead_of_duplicating(self):
        earnings.run(self.conn, ["AAA"], self.fake, NOW, delay=0)
        done = lambda t: [{"event_date": "2026-11-25", "eps_estimate": 1.0, "eps_actual": 1.2, "surprise_pct": 20.0}]  # noqa: E731
        earnings.run(self.conn, ["AAA"], done, NOW + timedelta(hours=21), delay=0)
        rows = self.conn.execute("SELECT eps_actual FROM earnings_events").fetchall()
        self.assertEqual(rows, [(1.2,)])


class UpcomingTest(Base):
    def test_only_wanted_tickers_inside_the_window(self):
        for t, d in (("AAA", "2026-11-23"), ("BBB", "2026-12-30"), ("CCC", "2026-11-22"), ("AAA", "2026-12-01")):
            self.conn.execute("INSERT INTO earnings_events (ticker, event_date, fetched_at) VALUES (?,?,?)",
                              (t, d, "x"))
        got = earnings.upcoming(self.conn, ["AAA", "BBB"], date(2026, 11, 20), 7)
        self.assertEqual(got, {"AAA": "2026-11-23"})  # BBB too far, CCC not wanted, AAA's nearest date wins


if __name__ == "__main__":
    unittest.main()
