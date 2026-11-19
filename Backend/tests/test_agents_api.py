"""Run from Backend/:  .venv/bin/python -m unittest tests.test_agents_api -v

No network, no LLM. Builds the SPEC tables in a temp SQLite DB and serves the
`final_json` from specs/trading-agents/example_review.json (fake values).
"""
import json
import os
import sqlite3
import tempfile
import time
import unittest
from unittest import mock

from fastapi import HTTPException

from app import agents_api, main

EXAMPLE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "specs", "trading-agents", "example_review.json"
)

SPEC_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_runs (
  id INTEGER PRIMARY KEY,
  ticker TEXT NOT NULL,
  horizon TEXT NOT NULL,
  as_of TEXT NOT NULL,
  model TEXT NOT NULL,
  deep_model TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  status TEXT NOT NULL,
  rating TEXT,
  summary TEXT,
  final_json TEXT,
  sources_json TEXT NOT NULL,
  tokens_in INTEGER NOT NULL DEFAULT 0,
  tokens_out INTEGER NOT NULL DEFAULT 0,
  error TEXT,
  started_at TEXT NOT NULL,
  finished_at TEXT
);
CREATE TABLE IF NOT EXISTS agent_decisions (
  id INTEGER PRIMARY KEY,
  run_id INTEGER NOT NULL,
  ticker TEXT NOT NULL,
  rating TEXT NOT NULL,
  as_of TEXT NOT NULL,
  entry_close REAL,
  settle_after_days INTEGER NOT NULL DEFAULT 5,
  settled_on TEXT,
  return_pct REAL,
  benchmark_return_pct REAL,
  alpha_pct REAL,
  reflection TEXT,
  settled_at TEXT
);
CREATE TABLE IF NOT EXISTS news_items (
  id INTEGER PRIMARY KEY,
  ticker TEXT NOT NULL,
  title TEXT NOT NULL,
  source TEXT NOT NULL,
  url TEXT NOT NULL,
  published_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS news_scores (
  news_id INTEGER NOT NULL,
  model TEXT NOT NULL,
  sentiment TEXT NOT NULL,
  scored_at TEXT NOT NULL,
  PRIMARY KEY (news_id, model)
);
CREATE TABLE IF NOT EXISTS recommendations (
  id INTEGER PRIMARY KEY,
  ticker TEXT NOT NULL,
  horizon TEXT NOT NULL,
  entry REAL NOT NULL,
  stop REAL NOT NULL,
  target REAL NOT NULL,
  score INTEGER NOT NULL,
  reasons TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
"""

DETAIL_KEYS = {
    "run_id", "ticker", "horizon", "as_of", "model", "deep_model", "prompt_version",
    "created_at", "status", "sources", "review", "evidence", "track_record",
}
REVIEW_KEYS = {
    "rating", "summary", "agrees", "key_risks", "analysts", "debate", "trader",
    "risk", "rules",
}


def example() -> dict:
    with open(EXAMPLE_PATH, encoding="utf-8") as f:
        return json.load(f)


def example_review_with_index() -> dict:
    """The example review, plus an evidence_index for the ids the API resolves itself."""
    data = example()
    review = json.loads(json.dumps(data["review"]))
    # Cite a rule reason, a second (unknown) rule, an unknown metric and a memory id
    # so the resolution/dropping behaviour is covered.
    review["key_risks"].append(
        {"text": "Momentum is the main rule supporting this idea.", "evidence": ["rule:0", "rule:99", "metric:missing"]}
    )
    review["trader"]["evidence"].append("memory:7")
    index = {
        e["id"]: {k: e[k] for k in ("label", "value", "url", "published_at") if k in e}
        for e in data["evidence"]
        if e["kind"] in ("metric", "fund", "sec", "social", "macro")
    }
    return {**review, "evidence_index": index}


class AgentsApiTest(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SPEC_SCHEMA)
        self.conn.execute("INSERT INTO users (id, email) VALUES (1, 'one@example.test')")
        self.conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES ('tok', 1, ?)",
            (int(time.time()) + 3600,),
        )
        self.conn.execute(
            "INSERT INTO recommendations (ticker, horizon, entry, stop, target, score, reasons) "
            "VALUES ('TYL', '1w', 403.94, 372.62, 450.92, 80, ?)",
            (json.dumps(["Momentum is strong", "Volume is above normal"]),),
        )
        self.conn.execute(
            "INSERT INTO news_items (id, ticker, title, source, url, published_at) "
            "VALUES (101, 'TYL', 'Example Co wins state software contract', 'Example Wire', "
            "'https://example.com/news/101', '2026-11-13T14:00:00Z')"
        )
        self.conn.execute(
            "INSERT INTO news_scores (news_id, model, sentiment, scored_at) "
            "VALUES (101, 'ml', 'bullish', '2026-11-14T01:00:00Z')"
        )
        self.conn.execute(
            "INSERT INTO agent_decisions (id, run_id, ticker, rating, as_of, return_pct, "
            "benchmark_return_pct, alpha_pct, reflection) "
            "VALUES (7, 0, 'TYL', 'Buy', '2026-11-05', 2.1, 0.8, 1.3, 'Momentum call worked.')"
        )
        data = example()
        self.conn.execute(
            "INSERT INTO agent_runs (ticker, horizon, as_of, model, deep_model, prompt_version, "
            "status, rating, summary, final_json, sources_json, started_at) "
            "VALUES ('TYL', '1w', '2026-11-14', ?, ?, 'ta-v1', 'partial', 'Overweight', ?, ?, ?, ?)",
            (
                data["model"], data["deep_model"], data["review"]["summary"],
                json.dumps(example_review_with_index()), json.dumps(data["sources"]),
                data["created_at"],
            ),
        )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.path)

    def call_endpoint(self, ticker="TYL", horizon="1w", session="tok"):
        with mock.patch.object(main, "DB_PATH", self.path):
            return agents_api.agent_review(ticker, horizon, session)

    def test_latest_ai_agree_mapping_and_status_filter(self):
        ai = agents_api.latest_ai(self.conn, ["TYL", "NOPE"], "1w")
        self.assertEqual(set(ai), {"TYL"})
        self.assertEqual(ai["TYL"]["rating"], "Overweight")
        self.assertEqual(ai["TYL"]["agrees"], "agree")
        self.assertEqual(ai["TYL"]["run_id"], 1)

        # A newer run that failed must not replace the last usable opinion.
        self.conn.execute(
            "INSERT INTO agent_runs (ticker, horizon, as_of, model, deep_model, prompt_version, "
            "status, started_at, sources_json) VALUES ('TYL', '1w', '2026-11-15', 'm', 'd', "
            "'ta-v1', 'error', '2026-11-16T00:00:00Z', '{}')"
        )
        self.conn.commit()
        self.assertEqual(agents_api.latest_ai(self.conn, ["TYL"], "1w")["TYL"]["run_id"], 1)

    def test_latest_ai_hold_and_sell_map_to_caution_and_disagree(self):
        for rating, agrees in (("Hold", "caution"), ("Underweight", "disagree"), ("Sell", "disagree"),
                               ("REVIEW", "review"), ("Buy", "agree")):
            self.conn.execute(
                "INSERT INTO agent_runs (ticker, horizon, as_of, model, deep_model, prompt_version, "
                "status, rating, summary, started_at, sources_json) VALUES ('HOLD', '1w', "
                "'2026-11-14', 'm', 'd', 'ta-v1', 'ok', ?, '', '2026-11-17T00:00:00Z', '{}')",
                (rating,),
            )
            self.conn.commit()
            self.assertEqual(agents_api.latest_ai(self.conn, ["HOLD"], "1w")["HOLD"]["agrees"], agrees)

    def _insert_quick_run(self, ticker, run_date="2026-11-17"):
        final = {"mode": "triage", "rating": "Buy", "confidence": "high", "summary": "Signals agree.",
                 "agrees": "agree", "points": [{"text": "Momentum is strong.", "evidence": ["rule:0"]}]}
        self.conn.execute(
            "INSERT INTO agent_runs (ticker, horizon, as_of, model, deep_model, prompt_version, "
            "status, rating, summary, final_json, sources_json, started_at) VALUES (?, '1w', ?, 'q', 'q', "
            "'ta-triage-v1', 'ok', 'Buy', 'Signals agree.', ?, '{}', '2026-11-17T00:00:00Z')",
            (ticker, run_date, json.dumps(final)),
        )
        self.conn.commit()

    def test_latest_ai_quick_only_ticker_is_marked_quick(self):
        self._insert_quick_run("QCK")
        ai = agents_api.latest_ai(self.conn, ["QCK"], "1w")["QCK"]
        self.assertEqual(ai["mode"], "quick")
        self.assertEqual(ai["rating"], "Buy")
        self.assertEqual(ai["confidence"], "high")
        self.assertEqual(ai["points"], [{"text": "Momentum is strong.", "evidence": ["rule:0"]}])

    def test_full_review_wins_over_a_newer_quick_review(self):
        self._insert_quick_run("TYL")
        ai = agents_api.latest_ai(self.conn, ["TYL"], "1w")["TYL"]
        self.assertEqual(ai["mode"], "full")
        self.assertEqual(ai["run_id"], 1)
        self.assertNotIn("points", ai)

    def test_detail_endpoint_ignores_quick_reviews(self):
        self._insert_quick_run("QCK")
        with self.assertRaises(HTTPException) as caught:
            self.call_endpoint("QCK")
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(self.call_endpoint("TYL")["run_id"], 1)

    def test_detail_shape_matches_contract(self):
        detail = self.call_endpoint()
        self.assertEqual(set(detail), DETAIL_KEYS)
        self.assertEqual(set(detail["review"]), REVIEW_KEYS)
        self.assertNotIn("evidence_index", detail)
        self.assertEqual(detail["ticker"], "TYL")
        self.assertEqual(detail["status"], "partial")
        self.assertEqual(set(detail["sources"]), set(agents_api.SOURCE_KEYS))
        self.assertEqual(detail["sources"]["social"]["status"], "unavailable")
        self.assertEqual(detail["review"]["rating"], "Overweight")
        self.assertEqual(detail["review"]["agrees"], "agree")
        self.assertEqual(set(detail["review"]["analysts"]), set(agents_api.ANALYST_KEYS))
        self.assertIsNone(detail["review"]["analysts"]["social"])
        self.assertEqual(detail["review"]["rules"], {"entry": 403.94, "stop": 372.62,
                                                     "target": 450.92, "score": 80})
        self.assertEqual(detail["track_record"][0]["as_of"], "2026-11-05")
        self.assertEqual(detail["track_record"][0]["alpha_pct"], 1.3)

    def test_evidence_is_resolved_and_unknown_ids_are_dropped(self):
        detail = self.call_endpoint()
        ids = [e["id"] for e in detail["evidence"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertNotIn("rule:99", ids)
        self.assertNotIn("metric:missing", ids)
        by_id = {e["id"]: e for e in detail["evidence"]}
        self.assertEqual(by_id["rule:0"]["label"], "Momentum is strong")
        self.assertEqual(by_id["news:101"]["sentiment"], "bullish")
        self.assertEqual(by_id["news:101"]["url"], "https://example.com/news/101")
        self.assertEqual(by_id["metric:rsi14"]["value"], "71.3")
        self.assertEqual(by_id["fund:pe"]["label"], "P/E (TTM)")
        self.assertEqual(by_id["agent:bull"]["label"], "Bull researcher")
        self.assertEqual(by_id["memory:7"]["label"], "2026-11-05 · Buy")
        # The example cites ids in contract order; that order is the chip order.
        self.assertEqual(ids[0], "metric:ma50_gap")

    def test_404_without_a_run(self):
        self.conn.execute("DELETE FROM agent_runs")
        self.conn.commit()
        with self.assertRaises(HTTPException) as ctx:
            self.call_endpoint()
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "no review")

    def test_401_without_session(self):
        with self.assertRaises(HTTPException) as ctx:
            self.call_endpoint(session=None)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_invalid_ticker_is_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            self.call_endpoint(ticker="bad ticker")
        self.assertEqual(ctx.exception.status_code, 422)

    def test_missing_tables_are_safe(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            conn = sqlite3.connect(path)
            conn.row_factory = sqlite3.Row
            self.assertEqual(agents_api.latest_ai(conn, ["TYL"], "1w"), {})
            self.assertIsNone(agents_api.build_review(conn, "TYL", "1w"))
            conn.close()
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
