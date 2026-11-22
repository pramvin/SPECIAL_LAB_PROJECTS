"""Run from Backend/:  .venv/bin/python -m unittest tests.test_card_news -v"""
import sqlite3
import unittest

from app import main


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


if __name__ == "__main__":
    unittest.main()
