"""Run from Backend/:  .venv/bin/python -m unittest tests.test_index_changes -v"""
import os
import sqlite3
import tempfile
import unittest
from datetime import date

import pandas as pd

from pipeline import index_changes as ic


def table(rows):
    cols = pd.MultiIndex.from_tuples([
        ("Effective Date", "Effective Date"), ("Added", "Ticker"), ("Added", "Security"),
        ("Removed", "Ticker"), ("Removed", "Security"), ("Reason", "Reason"), ("Refs", "Refs")])
    return pd.DataFrame(rows, columns=cols)


def series(first: str, last: str) -> pd.Series:
    idx = pd.bdate_range(first, last)
    return pd.Series(1.0, index=idx)


class ParseTest(unittest.TestCase):
    def test_dates_blank_tickers_and_dots(self):
        rows = ic.rows_from_table(table([
            ["October 30, 2026", "OKTA", "Okta", "KVUE", "Kenvue", "Acquired", "[2]"],
            ["October 6, 2026", None, None, "CTVA", "Corteva", "Market cap", "[3]"],
            ["June 1, 2025", "BRK.B", "Berkshire", None, None, "Joined", "[4]"],
            ["not a date", "XXX", "x", "YYY", "y", "bad", "[5]"],
            ["May 1, 2024", None, None, None, None, "nothing", "[6]"],
        ]))
        self.assertEqual(rows, [
            ("2026-10-30", "OKTA", "KVUE", "Acquired"),
            ("2026-10-06", "", "CTVA", "Market cap"),
            ("2025-06-01", "BRK-B", "", "Joined"),
        ])


class SaveCheckTest(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(ic.SCHEMA)

    def tearDown(self):
        self.conn.close()
        os.unlink(self.path)

    def test_save_twice_keeps_one_row(self):
        rows = [("2026-10-30", "OKTA", "KVUE", "a")]
        ic.save(self.conn, rows)
        ic.save(self.conn, [("2026-10-30", "OKTA", "KVUE", "b")])
        self.assertEqual(self.conn.execute("SELECT reason FROM index_changes").fetchall(), [("b",)])

    def test_check_marks_good_missing_and_reused_symbols(self):
        ic.save(self.conn, [
            ("2020-06-01", "", "GOOD", "x"),   # long history right up to removal
            ("2020-06-01", "", "GONE", "x"),   # Yahoo has nothing
            ("2020-06-01", "", "REUSED", "x"), # symbol reused: history starts after the removal
            ("2020-06-01", "", "OLDER", "x"),  # history ends a year before removal
            ("2015-01-01", "", "ANCIENT", "x"),  # before --since, not checked
        ])
        frame = pd.DataFrame({
            "GOOD": series("2018-01-01", "2020-05-29"),
            "REUSED": series("2021-01-01", "2022-01-01"),
            "OLDER": series("2017-01-01", "2019-06-01"),
        })
        res = ic.check_removed(self.conn, "2016-01-01", get_close=lambda tickers, start: frame)
        self.assertEqual((res["removals"], res["price_ok"]), (4, 1))
        got = dict(self.conn.execute("SELECT removed_ticker, price_ok FROM index_changes").fetchall())
        self.assertEqual(got["GOOD"], 1)
        self.assertEqual((got["GONE"], got["REUSED"], got["OLDER"]), (0, 0, 0))
        self.assertIsNone(got["ANCIENT"])

    def test_usable_edges(self):
        eff = date(2020, 6, 1)
        self.assertFalse(ic.usable(None, eff))
        self.assertFalse(ic.usable(pd.Series(dtype=float), eff))
        self.assertTrue(ic.usable(series("2019-05-30", "2020-05-05"), eff))
        self.assertFalse(ic.usable(series("2019-07-01", "2020-05-05"), eff))  # starts less than a year before


if __name__ == "__main__":
    unittest.main()
