"""Run from Backend/:  .venv/bin/python -m unittest tests.test_sentiment -v

Builds a tiny in-test Pipeline and a temporary SQLite DB, so the real model file
is never needed and the production database is never touched.
"""
import json
import os
import sqlite3
import tempfile
import unittest

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from pipeline import sentiment

TEXTS = ["profit gain up", "loss drop down", "the company said", "record revenue beat",
         "weak sales miss", "no clear change today"]


def tiny_pipeline():
    return Pipeline([("tfidf", TfidfVectorizer()), ("svc", LinearSVC())]).fit(
        TEXTS, ["bullish", "bearish", "neutral", "bullish", "bearish", "neutral"]
    )


def tiny_bundle(name="test_model"):
    return {"model": tiny_pipeline(), "trained_through": "2018-12-17", "sklearn_version": "1.9.1", "name": name}


class FakeModel:
    classes_ = np.array(["bearish", "neutral", "bullish"])

    def decision_function(self, texts):
        return np.array([[2.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 2.0]])


class SoftmaxTest(unittest.TestCase):
    def test_rows_sum_to_one_and_keep_order(self):
        p = sentiment.softmax([[2.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0, 0.0]])
        self.assertTrue(np.allclose(p.sum(axis=1), 1.0))
        self.assertGreater(p[0, 0], p[0, 1])
        self.assertGreater(p[1, 2], p[1, 0])
        self.assertTrue(np.allclose(p[2], [1 / 3, 1 / 3, 1 / 3]))

    def test_class_mapping_and_probabilities(self):
        out = sentiment.score_texts({"model": FakeModel()}, ["a", "b", "c"])
        self.assertEqual([r["sentiment"] for r in out], ["bearish", "neutral", "bullish"])
        for r in out:
            self.assertAlmostEqual(r["p_bearish"] + r["p_bullish"] + r["p_neutral"], 1.0)
            self.assertGreater(max(r["p_bearish"], r["p_bullish"], r["p_neutral"]), 0.5)

    def test_real_pipeline_classes_are_mapped(self):
        bundle = tiny_bundle()
        out = sentiment.score_texts(bundle, ["profit gain up", "loss drop down", "the company said"])
        self.assertEqual(len(out), 3)
        self.assertEqual(len(bundle["model"].classes_), 3)
        for r in out:
            self.assertAlmostEqual(r["p_bearish"] + r["p_bullish"] + r["p_neutral"], 1.0)
            self.assertIn(r["sentiment"], set(bundle["model"].classes_))


class DatabaseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "test.db")
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript("""
            CREATE TABLE news_items (
              id INTEGER PRIMARY KEY, ticker TEXT, title TEXT, source TEXT, url TEXT,
              published_at TEXT, first_seen_at TEXT, last_seen_at TEXT, rule_noise INTEGER);
            CREATE TABLE recommendations (ticker TEXT PRIMARY KEY, news TEXT);
        """)
        self.conn.executescript(sentiment.SCHEMA)
        rows = [
            (1, "AAA", "profit gain up", "Wire", "u1", "2024-01-05T10:00:00+00:00", 0),
            (2, "AAA", "loss drop down", "Wire", "u2", "2024-01-04T10:00:00+00:00", 0),
            (3, "AAA", "the company said", "Wire", "u3", "2024-01-03T10:00:00+00:00", 0),
            (4, "AAA", "record revenue beat", "Wire", "u4", "2024-01-02T10:00:00+00:00", 0),
            (5, "AAA", "weak sales miss", "Wire", "u5", "2024-01-01T10:00:00+00:00", 0),
            (6, "AAA", "stock price quote page", "Noise", "u6", "2024-01-06T10:00:00+00:00", 1),
            (7, "BBB", "no clear change today", "Wire", "u7", "2024-01-06T10:00:00+00:00", 0),
        ]
        self.conn.executemany(
            "INSERT INTO news_items VALUES (?,?,?,?,?,?,NULL,NULL,?)",
            [(i, t, title, src, url, pub, noise) for i, t, title, src, url, pub, noise in rows],
        )
        self.conn.execute("INSERT INTO recommendations (ticker, news) VALUES ('AAA', '[]'), ('BBB', '[]')")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def test_scores_are_written_once_and_not_repeated(self):
        bundle = tiny_bundle()
        self.assertEqual(sentiment.score_pending(self.conn, bundle, all_=True), 7)
        rows = self.conn.execute(
            "SELECT model, sentiment, kind, p_filler, p_bearish, p_bullish, p_neutral FROM news_scores"
        ).fetchall()
        self.assertEqual(len(rows), 7)
        for model, label, kind, pf, pb, pu, pn in rows:
            self.assertEqual(model, "test_model")
            self.assertIn(label, ("bearish", "neutral", "bullish"))
            self.assertEqual(kind, "n/a")
            self.assertIsNone(pf)
            self.assertAlmostEqual(pb + pu + pn, 1.0)

        self.assertEqual(sentiment.score_pending(self.conn, bundle, all_=True), 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM news_scores").fetchone()[0], 7)

    def test_limit_only_scores_new_rows(self):
        self.assertEqual(sentiment.score_pending(self.conn, tiny_bundle(), all_=True, limit=2), 2)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM news_scores").fetchone()[0], 2)

    def test_default_scope_uses_current_ideas(self):
        self.assertEqual(sentiment.score_pending(self.conn, tiny_bundle(), all_=False), 7)

    def test_refresh_cards_newest_first_three_and_no_filler_fields(self):
        bundle = tiny_bundle()
        sentiment.score_pending(self.conn, bundle, all_=True)
        n = sentiment.refresh_cards(self.conn, "test_model")
        self.assertEqual(n, 2)

        news = json.loads(self.conn.execute("SELECT news FROM recommendations WHERE ticker = 'AAA'").fetchone()[0])
        self.assertEqual(len(news), 3)
        self.assertEqual([x["title"] for x in news],
                         ["profit gain up", "loss drop down", "the company said"])
        for item in news:
            self.assertIn("sentiment", item)
            self.assertIn("sentiment_conf", item)
            self.assertNotIn("kind", item)
            self.assertNotIn("_demoted", item)
        self.assertNotIn("stock price quote page", [x["title"] for x in news])

        other = json.loads(self.conn.execute("SELECT news FROM recommendations WHERE ticker = 'BBB'").fetchone()[0])
        self.assertEqual(len(other), 1)


class LoadBundleTest(unittest.TestCase):
    def test_missing_model_file_stops_with_a_clear_message(self):
        missing = os.path.join(tempfile.gettempdir(), "definitely-not-here-news-sentiment.joblib")
        self.assertFalse(os.path.exists(missing))
        with self.assertRaises(SystemExit) as ctx:
            sentiment.load_bundle(missing)
        self.assertIn("not found", str(ctx.exception))
        self.assertIn(missing, str(ctx.exception))

    def test_corrupt_model_file_reports_the_real_error(self):
        with tempfile.NamedTemporaryFile("w", suffix=".joblib", delete=False) as f:
            f.write("not a joblib file")
            bad = f.name
        try:
            with self.assertRaises(SystemExit) as ctx:
                sentiment.load_bundle(bad)
            self.assertIn("Could not load", str(ctx.exception))
        finally:
            os.unlink(bad)


if __name__ == "__main__":
    unittest.main()
