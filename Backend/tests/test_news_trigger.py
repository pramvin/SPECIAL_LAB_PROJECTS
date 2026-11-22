"""Run from Backend/:  .venv/bin/python -m unittest tests.test_news_trigger -v"""
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from pipeline import news_trigger as nt

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)


class Base(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(
            "CREATE TABLE news_items (id INTEGER PRIMARY KEY, ticker TEXT, title TEXT, source TEXT, url TEXT, "
            "published_at TEXT, first_seen_at TEXT, last_seen_at TEXT, rule_noise INTEGER);"
            "CREATE TABLE news_scores (news_id INTEGER, model TEXT, sentiment TEXT, p_bearish REAL, p_bullish REAL, "
            "p_neutral REAL, kind TEXT, p_filler REAL, scored_at TEXT, PRIMARY KEY (news_id, model));"
            "CREATE TABLE recommendations (id INTEGER PRIMARY KEY, ticker TEXT, horizon TEXT, in_top INTEGER);"
            "CREATE TABLE agent_runs (id INTEGER PRIMARY KEY, ticker TEXT, status TEXT, finished_at TEXT);"
        )
        self.conn.executescript(nt.SCHEMA)
        self.n = 0

    def tearDown(self):
        self.conn.close()
        os.unlink(self.path)

    def rec(self, ticker, horizon="1w", in_top=1):
        self.conn.execute("INSERT INTO recommendations (ticker, horizon, in_top) VALUES (?,?,?)", (ticker, horizon, in_top))

    def news(self, ticker, title, sentiment="neutral", p=0.9, age_h=1, noise=0):
        self.n += 1
        seen = (NOW - timedelta(hours=age_h)).isoformat()
        self.conn.execute("INSERT INTO news_items VALUES (?,?,?,?,?,?,?,?,?)",
                          (self.n, ticker, title, "x", f"u{self.n}", seen, seen, seen, noise))
        probs = {"bearish": 0.05, "bullish": 0.05, "neutral": 0.05}
        probs[sentiment] = p
        self.conn.execute("INSERT INTO news_scores VALUES (?,?,?,?,?,?,?,?,?)",
                          (self.n, "m", sentiment, probs["bearish"], probs["bullish"], probs["neutral"], "n/a", None, seen))
        return self.n

    def review(self, ticker, hours_ago, status="ok"):
        self.conn.execute("INSERT INTO agent_runs (ticker, status, finished_at) VALUES (?,?,?)",
                          (ticker, status, (NOW - timedelta(hours=hours_ago)).isoformat()))


class MaterialReasonTest(unittest.TestCase):
    def test_confident_label_or_event_word(self):
        self.assertIn("bullish", nt.material_reason("Stock rises", "bullish", 0.8))
        self.assertIn("downgrade", nt.material_reason("Analyst downgrades ACME", "neutral", 0.9))
        self.assertIsNone(nt.material_reason("ACME holds annual meeting", "neutral", 0.9))
        self.assertIsNone(nt.material_reason("Stock rises", "bullish", 0.4))
        self.assertIsNone(nt.material_reason("Stock market today: Dow sinks as earnings worry", "bearish", 0.9))


class DecideTest(Base):
    def test_material_headline_on_curated_stock_goes_to_ai(self):
        self.rec("AAA")
        self.news("AAA", "AAA gets FDA approval for drug")
        d = nt.decide(self.conn, NOW)
        self.assertEqual(d["pairs"], [("AAA", "1w")])
        self.assertEqual(d["log"][0][4], "review")

    def test_boring_headline_is_skipped_and_not_judged_twice(self):
        self.rec("AAA")
        self.news("AAA", "AAA holds annual meeting")
        d = nt.decide(self.conn, NOW)
        self.assertEqual(d["pairs"], [])
        nt.save_log(self.conn, d["log"], NOW)
        self.assertEqual(nt.decide(self.conn, NOW)["stats"]["new"], 0)

    def test_stock_outside_curated_list_and_noise_are_ignored(self):
        self.rec("AAA", in_top=0)
        self.rec("BBB")
        self.news("AAA", "AAA gets FDA approval")
        self.news("BBB", "BBB stock price, news, quote and history", noise=1)
        self.assertEqual(nt.decide(self.conn, NOW)["stats"]["new"], 0)

    def test_cooldown_blocks_a_recently_reviewed_stock(self):
        self.rec("AAA")
        self.news("AAA", "AAA to be acquired")
        self.review("AAA", hours_ago=2)
        d = nt.decide(self.conn, NOW)
        self.assertEqual(d["pairs"], [])
        self.assertEqual(d["log"][0][4], "cooldown")

    def test_old_review_or_failed_review_does_not_block(self):
        self.rec("AAA")
        self.rec("BBB")
        self.news("AAA", "AAA to be acquired")
        self.news("BBB", "BBB faces lawsuit")
        self.review("AAA", hours_ago=9)
        self.review("BBB", hours_ago=1, status="error")
        self.assertEqual(len(nt.decide(self.conn, NOW)["pairs"]), 2)

    def test_cap_leaves_extra_stocks_unlogged_for_next_run(self):
        for t in ("AAA", "BBB", "CCC"):
            self.rec(t)
            self.news(t, f"{t} faces lawsuit")
        d = nt.decide(self.conn, NOW, max_pairs=2)
        self.assertEqual(len(d["pairs"]), 2)
        self.assertEqual(d["stats"]["waiting"], 1)
        self.assertEqual(len(d["log"]), 2)  # the waiting stock's headline is not logged

    def test_old_headlines_are_outside_the_lookback(self):
        self.rec("AAA")
        self.news("AAA", "AAA to be acquired", age_h=30)
        self.assertEqual(nt.decide(self.conn, NOW)["stats"]["new"], 0)


if __name__ == "__main__":
    unittest.main()
