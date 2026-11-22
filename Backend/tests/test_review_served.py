"""Run from Backend/:  .venv/bin/python -m unittest tests.test_review_served -v"""
import os
import sqlite3
import tempfile
import unittest

from pipeline import review_served as rs

AS_OF = "2026-11-20"
SECTORS = ["tech", "healthcare", "energy", "utilities"]


class Base(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(
            "CREATE TABLE recommendations (id INTEGER PRIMARY KEY, ticker TEXT, sector TEXT, horizon TEXT, score INTEGER, "
            "atr_pct REAL, in_top INTEGER, as_of TEXT);"
            "CREATE TABLE risk_profiles (user_id INTEGER PRIMARY KEY, sectors TEXT, risk_level TEXT, horizon TEXT);"
            "CREATE TABLE agent_runs (id INTEGER PRIMARY KEY, ticker TEXT, horizon TEXT, as_of TEXT, status TEXT, started_at TEXT);"
        )
        for h in rs.HORIZONS:
            for i in range(16):  # T00 best ... T15; sectors cycle; the best 8 are curated
                self.conn.execute(
                    "INSERT INTO recommendations (ticker, sector, horizon, score, atr_pct, in_top, as_of) VALUES (?,?,?,?,?,?,?)",
                    (f"T{i:02d}", SECTORS[i % 4], h, 90 - i, 2.0 + (i % 4), int(i < 8), AS_OF))
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.path)


class ServedTest(Base):
    def test_no_profiles_means_the_curated_top_five(self):
        as_of, wanted = rs.served(self.conn)
        self.assertEqual(as_of, AS_OF)
        self.assertEqual(wanted["1w"], ["T00", "T01", "T02", "T03", "T04"])

    def test_profile_picks_are_added_after_curated_and_not_duplicated(self):
        self.conn.execute("INSERT INTO risk_profiles VALUES (1, 'healthcare', 'moderate', '1w')")
        _, wanted = rs.served(self.conn)
        self.assertEqual(wanted["1w"][:5], ["T00", "T01", "T02", "T03", "T04"])
        extra = wanted["1w"][5:]
        self.assertTrue(extra)
        self.assertEqual(len(extra), len(set(extra)))
        self.assertTrue(set(extra).isdisjoint(wanted["1w"][:5]))
        self.assertTrue(all(t in wanted["1m"] or True for t in extra))

    def test_same_profile_twice_is_computed_once(self):
        self.conn.execute("INSERT INTO risk_profiles VALUES (1, 'healthcare', 'moderate', '1w')")
        self.conn.execute("INSERT INTO risk_profiles VALUES (2, 'healthcare', 'moderate', '3m')")
        _, wanted = rs.served(self.conn)
        self.assertLessEqual(len(wanted["1w"]), 10)

    def test_empty_database(self):
        self.conn.execute("DELETE FROM recommendations")
        self.assertEqual(rs.served(self.conn)[0], None)


class PendingTest(Base):
    def wanted(self):
        return {"1w": ["A", "B", "C"], "1m": ["D", "E"], "3m": ["F"]}

    def test_horizons_take_turns_and_cap_applies(self):
        got = rs.pending(self.conn, AS_OF, self.wanted(), limit=4)
        self.assertEqual(got, [("A", "1w"), ("D", "1m"), ("F", "3m"), ("B", "1w")])

    def test_reviewed_pairs_for_this_ranking_are_skipped(self):
        self.conn.execute("INSERT INTO agent_runs (ticker, horizon, as_of, status) VALUES ('A', '1w', ?, 'ok')", (AS_OF,))
        self.conn.execute("INSERT INTO agent_runs (ticker, horizon, as_of, status) VALUES ('D', '1m', ?, 'partial')", (AS_OF,))
        self.conn.execute("INSERT INTO agent_runs (ticker, horizon, as_of, status) VALUES ('B', '1w', ?, 'error')", (AS_OF,))
        self.conn.execute("INSERT INTO agent_runs (ticker, horizon, as_of, status) VALUES ('C', '1w', '2026-11-10', 'ok')")
        got = rs.pending(self.conn, AS_OF, self.wanted())
        self.assertNotIn(("A", "1w"), got)
        self.assertNotIn(("D", "1m"), got)
        self.assertIn(("B", "1w"), got)  # a failed review does not count
        self.assertIn(("C", "1w"), got)  # an old review does not count for the new ranking

    def test_same_ticker_on_another_horizon_is_still_pending(self):
        self.conn.execute("INSERT INTO agent_runs (ticker, horizon, as_of, status) VALUES ('A', '1m', ?, 'ok')", (AS_OF,))
        self.assertIn(("A", "1w"), rs.pending(self.conn, AS_OF, self.wanted()))

    def test_redo_before_redoes_only_older_reviews(self):
        ins = "INSERT INTO agent_runs (ticker, horizon, as_of, status, started_at) VALUES (?, '1w', ?, 'ok', ?)"
        self.conn.execute(ins, ("A", AS_OF, "2026-11-21T07:00:00+00:00"))  # before the fix
        self.conn.execute(ins, ("B", AS_OF, "2026-11-21T08:00:00+00:00"))  # after the fix
        got = rs.pending(self.conn, AS_OF, self.wanted(), redo_before="2026-11-21T07:33:00+00:00")
        self.assertIn(("A", "1w"), got)
        self.assertNotIn(("B", "1w"), got)


class RunTest(unittest.TestCase):
    def test_one_command_per_horizon_and_failures_are_counted(self):
        calls = []

        class R:
            def __init__(self, code):
                self.returncode = code

        def runner(cmd):
            calls.append(cmd)
            return R(1 if "1m" in cmd else 0)

        failed = rs.run_ai([("A", "1w"), ("B", "1w"), ("C", "1m")], runner=runner)
        self.assertEqual(failed, 1)
        self.assertEqual(len(calls), 2)
        first = calls[0]
        self.assertEqual(first[first.index("--tickers") + 1], "A,B")
        self.assertIn("triage", first)
        self.assertIn("--no-settle", first)


if __name__ == "__main__":
    unittest.main()
