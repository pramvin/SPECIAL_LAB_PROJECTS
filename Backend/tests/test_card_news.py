"""Card headlines, latest-news feed and price series (no network).
Run from Backend/:  .venv/bin/python -m unittest tests.test_card_news -v"""
import os
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import main
from pipeline import news


def conn_with_news(rows):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE news_items (id INTEGER PRIMARY KEY, ticker TEXT, title TEXT, source TEXT, "
                 "url TEXT, published_at TEXT, rule_noise INTEGER)")
    conn.executemany("INSERT INTO news_items (ticker,title,source,url,published_at,rule_noise) VALUES (?,?,?,?,?,?)", rows)
    return conn


class CardNewsTest(unittest.TestCase):
    def test_newest_first_skips_noise_and_limits(self):
        rows = [("CAH", f"h{i}", "Yahoo", f"u{i}", f"2026-11-0{i}", 0) for i in range(1, 6)]
        rows.append(("CAH", "noise", "Yahoo", "un", "2026-11-09", 1))
        got = main.latest_headlines(conn_with_news(rows), ["CAH", "MTD"])
        self.assertEqual([h["title"] for h in got["CAH"]], ["h5", "h4", "h3"])
        self.assertEqual(got["MTD"], [])

    def test_no_news_table_gives_empty(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        self.assertEqual(main.latest_headlines(conn, ["CAH"]), {})

    def test_headlines_carry_the_latest_label(self):
        conn = conn_with_news([("CAH", "h1", "Yahoo", "u1", "2026-11-01", 0),
                               ("CAH", "h2", "Yahoo", "u2", "2026-11-02", 0)])
        conn.execute("CREATE TABLE news_scores (news_id INTEGER, model TEXT, sentiment TEXT, scored_at TEXT)")
        conn.executemany("INSERT INTO news_scores VALUES (?,?,?,?)",
                         [(1, "old", "bearish", "2026-11-01"), (1, "new", "bullish", "2026-11-03"),
                          (2, "old", "neutral", "2026-11-01")])
        got = main.latest_headlines(conn, ["CAH"])
        self.assertEqual([h["sentiment"] for h in got["CAH"]], ["neutral", "positive"])


class RecommendationsApiTest(unittest.TestCase):
    """/api/recommendations: ML only (no `ai`), three newest headlines each with a sentiment word."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = os.path.join(directory.name, "rec.db")
        conn = sqlite3.connect(self.path)
        try:
            conn.executescript(main.SCHEMA)
            conn.executescript(news.SCHEMA)
            conn.executescript(
                "CREATE TABLE news_scores (news_id INTEGER, model TEXT, sentiment TEXT, scored_at TEXT);"
                "INSERT INTO users VALUES (1, 'one@example.test', 'x', 0);"
                f"INSERT INTO sessions VALUES ('tok', 1, {int(time.time()) + 3600});"
            )
            conn.execute(
                "INSERT INTO recommendations (ticker, name, sector, horizon, entry, stop, target, score, reasons, "
                "news, generated_at, in_top) VALUES ('AAA', 'Acme', 'Technology', '1w', 100, 95, 110, 70, '[]', "
                "'[]', 0, 1)")
            conn.execute(
                "INSERT INTO recommendations (ticker, name, sector, horizon, entry, stop, target, score, reasons, "
                "news, generated_at, in_top) VALUES ('BBB', 'Beta', 'Energy', '1w', 50, 45, 60, 60, '[]', "
                "?, 0, 1)", ('[{"title": "stored", "sentiment": "bearish", "sentiment_conf": 0.9}]',))
            for i, (title, label) in enumerate([("a", "bullish"), ("b", "bearish"), ("c", None), ("d", "neutral")]):
                conn.execute(
                    "INSERT INTO news_items (ticker, title, source, url, published_at, first_seen_at, last_seen_at, "
                    "rule_noise) VALUES ('AAA', ?, 'Yahoo', ?, ?, 'x', 'x', 0)",
                    (title, f"u{i}", f"2026-11-2{i}T10:00:00+00:00"))
                if label:
                    conn.execute("INSERT INTO news_scores VALUES (?, 'm', ?, '2026-11-24')", (i + 1, label))
            conn.commit()
        finally:
            conn.close()
        patcher = patch.object(main, "DB_PATH", self.path)
        patcher.start()
        self.addCleanup(patcher.stop)
        client = TestClient(main.app)
        self.addCleanup(client.close)
        client.cookies.set("session", "tok")
        self.client = client

    def test_cards_have_no_ai_and_headlines_carry_sentiment(self):
        body = self.client.get("/api/recommendations?horizon=1w").json()
        cards = {c["ticker"]: c for c in body["items"]}
        self.assertTrue(all("ai" not in c for c in cards.values()))
        headlines = cards["AAA"]["news"]
        self.assertEqual([h["title"] for h in headlines], ["d", "c", "b"])
        self.assertEqual([h["sentiment"] for h in headlines], ["neutral", None, "negative"])
        self.assertNotIn("id", headlines[0])

    def test_stored_card_headlines_use_the_same_words(self):
        card = {c["ticker"]: c for c in self.client.get("/api/recommendations?horizon=1w").json()["items"]}["BBB"]
        self.assertEqual(card["news"], [{"title": "stored", "sentiment": "negative"}])


class NewsApiTest(unittest.TestCase):
    """Endpoints share main.app; only DB_PATH points at a disposable SQLite file."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = os.path.join(directory.name, "api.db")
        conn = sqlite3.connect(self.path)
        try:
            conn.executescript(
                "CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT);"
                "CREATE TABLE sessions (token TEXT PRIMARY KEY, user_id INTEGER, expires_at INTEGER);"
                "CREATE TABLE recommendations (id INTEGER PRIMARY KEY, ticker TEXT, name TEXT, "
                "  horizon TEXT, in_top INTEGER, news TEXT);"
                "CREATE TABLE prices (ticker TEXT, date TEXT, open REAL, high REAL, low REAL, "
                "  close REAL, volume INTEGER);"
                "CREATE TABLE news_scores (news_id INTEGER, model TEXT, sentiment TEXT, scored_at TEXT);"
                "INSERT INTO users VALUES (1, 'one@example.test');"
                f"INSERT INTO sessions VALUES ('tok', 1, {int(time.time()) + 3600});"
                "INSERT INTO recommendations (ticker, name, horizon, in_top, news) "
                "  VALUES ('AAA', 'Acme', '1w', 1, '[]');"
                "INSERT INTO recommendations (ticker, name, horizon, in_top, news) "
                "  VALUES ('BBB', 'Beta', '1w', 1, '[]');"
                "INSERT INTO recommendations (ticker, name, horizon, in_top, news) "
                "  VALUES ('DDD', 'Delta', '1w', 0, '[]');"
                "INSERT INTO recommendations (ticker, name, horizon, in_top, news) "
                "  VALUES ('CCC', 'Gamma', '1m', 1, '[]');"
            )
            conn.executescript(news.SCHEMA)
            conn.executemany(
                "INSERT INTO news_items (ticker, title, source, url, published_at, first_seen_at, "
                "  last_seen_at, rule_noise) VALUES (?,?,?,?,?,?,?,?)",
                [("AAA", "fresh", "Yahoo", "u1", "2026-11-22T10:00:00+00:00", "x", "x", 0),
                 ("BBB", "same url, other ticker", "Yahoo", "u1", "2026-11-21T10:00:00+00:00", "x", "x", 0),
                 ("AAA", "second", "Yahoo", "u2", "2026-11-20T10:00:00+00:00", "x", "x", 0),
                 ("AAA", "noise", "Yahoo", "u4", "2026-11-23T10:00:00+00:00", "x", "x", 1),
                 ("DDD", "not served", "Yahoo", "u3", "2026-11-23T10:00:00+00:00", "x", "x", 0)],
            )
            fresh_id = conn.execute("SELECT id FROM news_items WHERE title = 'fresh'").fetchone()[0]
            conn.execute("INSERT INTO news_scores VALUES (?, 'm', 'bullish', '2026-11-22')", (fresh_id,))
            for i, close in enumerate((97, 98, 99, 100, 101, 102)):
                conn.execute("INSERT INTO prices VALUES ('AAA', ?, ?, ?, ?, ?, 1000)",
                             (f"2026-11-{15 + i}", close, close, close, close))
            conn.execute("INSERT INTO prices VALUES ('BBB', '2026-11-20', 50, 50, 50, 50, 1)")
            conn.commit()
        finally:
            conn.close()
        self.db_path = patch.object(main, "DB_PATH", self.path)
        self.db_path.start()
        self.addCleanup(self.db_path.stop)
        main._last_news_refresh = time.time()  # no background thread unless a test asks for it
        self.addCleanup(setattr, main, "_last_news_refresh", None)
        client = TestClient(main.app)
        self.addCleanup(client.close)
        client.cookies.set("session", "tok")
        self.client = client

    def test_latest_news_only_served_stocks_newest_first_and_one_row_per_url(self):
        response = self.client.get("/api/latest-news?limit=10")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("refreshed_at", body)
        self.assertEqual([i["title"] for i in body["items"]], ["fresh", "second"])
        self.assertEqual({i["ticker"] for i in body["items"]}, {"AAA"})
        newest = body["items"][0]
        self.assertEqual(newest["sentiment"], "positive")
        self.assertEqual((newest["price"], newest["change"], newest["change_pct"]), (102.0, 1.0, 0.99))
        self.assertEqual(newest["price_date"], "2026-11-20")
        self.assertIsNone(body["items"][1]["sentiment"])

    def test_latest_news_requires_login(self):
        self.client.cookies.clear()
        self.assertEqual(self.client.get("/api/latest-news").status_code, 401)

    def test_background_refresh_is_started_once_and_returns_at_once(self):
        calls = []

        def fake(conn, tickers):
            calls.append(tuple(tickers))
            threading.Event().wait(0.05)

        main._last_news_refresh = None
        with patch("pipeline.news_live.refresh_many", side_effect=fake):
            started = time.time()
            self.assertEqual(self.client.get("/api/latest-news").status_code, 200)
            self.assertLess(time.time() - started, 2)
            for _ in range(50):
                if calls:
                    break
                time.sleep(0.02)
            self.client.get("/api/latest-news")
            time.sleep(0.1)
        self.assertEqual(calls, [("AAA", "BBB")])

    def test_prices_clamps_days_and_returns_oldest_first(self):
        response = self.client.get("/api/prices/AAA?days=1")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["bars"]), 5)
        self.assertEqual(body["bars"][0]["date"], "2026-11-16")
        self.assertEqual(body["bars"][-1]["date"], "2026-11-20")
        self.assertEqual((body["name"], body["price"], body["change"]), ("Acme", 102.0, 1.0))
        self.assertEqual(len(self.client.get("/api/prices/AAA?days=999").json()["bars"]), 6)

    def test_prices_unknown_ticker_is_404(self):
        self.assertEqual(self.client.get("/api/prices/ZZZ").status_code, 404)
        self.assertEqual(self.client.get("/api/prices/lower").status_code, 404)


if __name__ == "__main__":
    unittest.main()
