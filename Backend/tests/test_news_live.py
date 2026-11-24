"""On-demand Yahoo news refresh (no network, no real model). Run from Backend/:
.venv/bin/python -m unittest tests.test_news_live -v"""
import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from pipeline import news, news_live, sentiment

REAL_GET_BUNDLE = news_live._get_bundle
LABEL = {"sentiment": "bullish", "p_bearish": 0.1, "p_bullish": 0.8, "p_neutral": 0.1}


def item(title, url, noise=False, published_at="2026-11-20T10:00:00+00:00"):
    return {"title": title, "source": "Yahoo", "url": url, "published": published_at[:10],
            "published_at": published_at, "noise": noise}


class NewsLiveTest(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.addCleanup(os.unlink, self.path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.addCleanup(self.conn.close)
        self.conn.executescript(news.SCHEMA)
        self.conn.executescript(sentiment.SCHEMA)
        self.conn.executescript(
            "CREATE TABLE recommendations (id INTEGER PRIMARY KEY, ticker TEXT, name TEXT, "
            "horizon TEXT, news TEXT, in_top INTEGER);"
            "INSERT INTO recommendations (ticker, name, horizon, news, in_top) "
            "VALUES ('AAA', 'Acme', '1w', '[]', 1);"
        )
        news_live._last_fetch.clear()
        bundle = patch.object(news_live, "_get_bundle", return_value={"name": "fake-model"})
        score = patch.object(news_live.sentiment, "score_texts",
                             side_effect=lambda _bundle, texts: [dict(LABEL) for _ in texts])
        self.addCleanup(bundle.stop)
        self.addCleanup(score.stop)
        bundle.start()
        score.start()

    def rows(self, sql, *params):
        return self.conn.execute(sql, params).fetchall()

    def test_new_headlines_are_stored_and_labelled(self):
        items = [item("Acme beats estimates", "u1"), item("Acme noise", "u2", noise=True), item("Acme sued", "u3")]
        with patch.object(news_live.news, "fetch", return_value=items):
            result = news_live.refresh_ticker(self.conn, "AAA", "Acme")
        self.assertEqual(result, {"new": 3, "scored": 3, "status": "ok", "reason": None})
        self.assertEqual(len(self.rows("SELECT id FROM news_items")), 3)
        self.assertEqual([r[0] for r in self.rows("SELECT sentiment FROM news_scores")], ["bullish"] * 3)
        card = json.loads(self.rows("SELECT news FROM recommendations WHERE ticker = 'AAA'")[0][0])
        self.assertEqual([n["title"] for n in card], ["Acme beats estimates", "Acme sued"])

    def test_duplicates_are_ignored(self):
        items = [item("Acme beats estimates", "u1")]
        with patch.object(news_live.news, "fetch", return_value=items):
            self.assertEqual(news_live.refresh_ticker(self.conn, "AAA")["new"], 1)
            news_live._last_fetch.clear()
            again = news_live.refresh_ticker(self.conn, "AAA")
        self.assertEqual((again["new"], again["scored"]), (0, 0))
        self.assertEqual(len(self.rows("SELECT id FROM news_items")), 1)

    def test_yahoo_failure_is_reported_not_raised(self):
        with patch.object(news_live.news, "fetch", side_effect=RuntimeError("blocked")):
            result = news_live.refresh_ticker(self.conn, "AAA")
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("blocked", result["reason"])
        self.assertEqual(result["new"], 0)

    def test_memo_skips_a_second_fetch_within_a_minute(self):
        with patch.object(news_live.news, "fetch", return_value=[item("Acme beats", "u1")]) as fetch:
            news_live.refresh_ticker(self.conn, "AAA")
            second = news_live.refresh_ticker(self.conn, "AAA")
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(second["new"], 0)
        self.assertIn("60", second["reason"])

    def test_missing_model_keeps_headlines_and_skips_labels(self):
        with patch.object(news_live, "_get_bundle", return_value=None), \
                patch.object(news_live.news, "fetch", return_value=[item("Acme beats", "u1")]):
            result = news_live.refresh_ticker(self.conn, "AAA")
        self.assertEqual(result, {"new": 1, "scored": 0, "status": "ok", "reason": None})
        self.assertEqual(len(self.rows("SELECT news_id FROM news_scores")), 0)

    def test_bundle_loader_returns_none_when_the_model_file_is_missing(self):
        self.addCleanup(setattr, news_live, "_bundle_loaded", False)
        news_live._bundle, news_live._bundle_loaded = None, False
        with patch.object(news_live.sentiment, "load_bundle", side_effect=SystemExit("no model")) as load:
            self.assertIsNone(REAL_GET_BUNDLE())
            self.assertIsNone(REAL_GET_BUNDLE())
        self.assertEqual(load.call_count, 1)  # the failure is remembered, the file is not re-read per call

    def test_refresh_many_totals_and_partial_status(self):
        def fetch(ticker, _name):
            if ticker == "BBB":
                raise RuntimeError("down")
            return [item(f"{ticker} beats", "u1")]

        with patch.object(news_live.news, "fetch", side_effect=fetch), \
                patch.object(news_live.time, "sleep", return_value=None):
            result = news_live.refresh_many(self.conn, ["AAA", "BBB"])
        self.assertEqual(result["new"], 1)
        self.assertEqual(result["status"], "partial")
        self.assertIn("1 of 2", result["reason"])


if __name__ == "__main__":
    unittest.main()
