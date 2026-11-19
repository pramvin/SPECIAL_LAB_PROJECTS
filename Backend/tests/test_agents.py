"""Tests for the AI agent review engine.

Run from Backend/:  .venv/bin/python -m unittest tests.test_agents -v

Temp SQLite only (`PLANWISE_DB` is pointed at the test file) and no network: every
external source is either read from the seeded DB or replaced by a canned fetcher.
"""
import json
import os
import sqlite3
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone

from agents import config, graph, llm_client, memory, schema, sources, triage, validate

TICKER = "TYL"
SETTLE_TICKER = "ZZZ"
SECRET = "sk-test-SECRET-must-never-be-stored"
PRICE_DAYS = 300
START = date(2025, 9, 1)

EXPECTED_ROLES = (
    "market", "news", "fundamentals", "social", "bull", "bear",
    "research_manager", "trader", "aggressive", "conservative", "neutral",
    "portfolio_manager",
)
FINAL_KEYS = {"rating", "summary", "agrees", "key_risks", "analysts", "debate",
              "trader", "risk", "rules", "evidence_index"}

MARKET_OK = {"signal": "neutral", "summary": "Momentum is steady.",
             "points": [{"text": "The trend is up.", "evidence": ["metric:close"]}],
             "data_gaps": []}


def _static(result):
    def fetch(*args, **kwargs):
        return result
    return fetch


def _boom(*args, **kwargs):
    raise RuntimeError("source exploded")


def _price_row(ticker, day, close):
    return (ticker, day.isoformat(), round(close - 0.2, 4), round(close + 1.0, 4),
            round(close - 1.0, 4), round(close, 4), 1_000_000)


class _LeakOnceLLM(llm_client.FakeLLM):
    """Fails the first role with an exception that contains the API key."""

    def __init__(self, secret):
        super().__init__(auto=True)
        self.secret = secret

    def chat_json(self, role, system, user, deep=False):
        if role == "market":
            raise RuntimeError(f"auth failed for key {self.secret}")
        return super().chat_json(role, system, user, deep=deep)


class AgentsTest(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self._old_db = os.environ.get("PLANWISE_DB")
        os.environ["PLANWISE_DB"] = self.path
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute(
            "CREATE TABLE prices (ticker TEXT, date TEXT, open REAL, high REAL, low REAL, "
            "close REAL, volume REAL)")
        self.conn.execute(
            "CREATE TABLE recommendations (id INTEGER PRIMARY KEY, ticker TEXT, name TEXT, "
            "sector TEXT, horizon TEXT, entry REAL, stop REAL, target REAL, score REAL, reasons TEXT)")
        self.conn.execute(
            "CREATE TABLE news_items (id INTEGER PRIMARY KEY, ticker TEXT, title TEXT, source TEXT, "
            "url TEXT, published_at TEXT, rule_noise INTEGER NOT NULL DEFAULT 0)")
        self.conn.commit()
        schema.ensure(self.conn)
        self._seed()
        self.entry = float(self.conn.execute(
            "SELECT entry FROM recommendations WHERE ticker = ?", (TICKER,)).fetchone()[0])

    def tearDown(self):
        self.conn.close()
        os.unlink(self.path)
        if self._old_db is None:
            os.environ.pop("PLANWISE_DB", None)
        else:
            os.environ["PLANWISE_DB"] = self._old_db

    # -- fixtures -----------------------------------------------------------
    def _seed(self):
        rows = [_price_row(TICKER, START + timedelta(days=i), 200 + i * 0.5)
                for i in range(PRICE_DAYS)]
        self.conn.executemany(
            "INSERT INTO prices (ticker,date,open,high,low,close,volume) VALUES (?,?,?,?,?,?,?)", rows)
        last = date(START.year, START.month, START.day) + timedelta(days=PRICE_DAYS - 1)
        entry = 200 + (PRICE_DAYS - 1) * 0.5
        self.conn.execute(
            "INSERT INTO recommendations (ticker,name,sector,horizon,entry,stop,target,score,reasons) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (TICKER, "Tyler Technologies", "Technology", "1w", entry,
             round(entry * 0.95, 2), round(entry * 1.08, 2), 0.81,
             json.dumps(["Price is above its 50-day average", "Volume is expanding"])))
        self.conn.execute(
            "INSERT INTO news_items (id,ticker,title,source,url,published_at,rule_noise) "
            "VALUES (?,?,?,?,?,?,?)",
            (1, TICKER, "Tyler Technologies wins a new contract", "testwire",
             "https://example.test/news/1", (last - timedelta(days=3)).isoformat(), 0))
        spy = [{"date": (last - timedelta(days=9 - i)).isoformat(), "close": 400.0 + i}
               for i in range(10)]
        sources.cache_put(self.conn, "spy", "SPY",
                          datetime.now(timezone.utc).date().isoformat(), spy)
        self.conn.commit()

    def fetchers(self, **overrides):
        base = {
            "fmp": _static({"status": "ok", "reason": None, "items": {
                "pe_ttm": {"label": "P/E (TTM)", "value": 30.5},
                "net_margin": {"label": "Net margin", "value": 0.21}}}),
            "sec": _static({"status": "ok", "reason": None, "items": [{
                "concept": "Revenues", "label": "Revenue", "value": 500000000,
                "period_end": "2026-03-31", "form": "10-Q"}]}),
            "social": _static({"status": "ok", "reason": None, "items": [{
                "id": "social:stocktwits:1", "source": "stocktwits", "title": "$TYL looks strong",
                "body": "", "score": 5, "sentiment": "Bullish",
                "published_at": "2026-06-24T12:00:00+00:00",
                "url": "https://example.test/social/1"}]}),
            "macro": _static({"status": "ok", "reason": None, "items": [{
                "series": "DGS10", "label": "10-year Treasury yield", "value": 4.21,
                "date": "2026-06-26"}]}),
        }
        base.update(overrides)
        return base

    # -- helpers ------------------------------------------------------------
    def review(self, llm, **overrides):
        return graph.review_ticker(self.conn, llm, TICKER, "1w", fetchers=self.fetchers(**overrides))

    def test_rejected_key_fails_the_run_after_one_call(self):
        class RejectingLLM(llm_client.FakeLLM):
            def chat_json(self, role, system, user, deep=False):
                self.calls.append({"role": role})
                raise llm_client.AuthError("HTTP 401: gateway rejected the API key")

        llm = RejectingLLM()
        run_id = self.review(llm)
        row = self.run_row(run_id)
        self.assertEqual(row["status"], "error")
        self.assertIn("401", row["error"])
        self.assertEqual(len(llm.calls), 1)

    def run_row(self, run_id):
        return self.conn.execute("SELECT * FROM agent_runs WHERE id = ?", (run_id,)).fetchone()

    def messages(self, run_id):
        return self.conn.execute(
            "SELECT role, error FROM agent_messages WHERE run_id = ? ORDER BY id", (run_id,)).fetchall()

    def final(self, run_id):
        return json.loads(self.run_row(run_id)["final_json"])

    def _insert_run(self, ticker, summary):
        cursor = self.conn.execute(
            "INSERT INTO agent_runs (ticker,horizon,as_of,model,deep_model,prompt_version,status,"
            "sources_json,summary,started_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (ticker, "1w", "2026-01-01", "fake-quick", "fake-deep", config.PROMPT_VERSION,
             "ok", "{}", summary, "2026-01-01T00:00:00+00:00"))
        self.conn.commit()
        return cursor.lastrowid

    def _seed_prices(self, ticker, start, closes):
        rows = [_price_row(ticker, start + timedelta(days=i), close)
                for i, close in enumerate(closes)]
        self.conn.executemany(
            "INSERT INTO prices (ticker,date,open,high,low,close,volume) VALUES (?,?,?,?,?,?,?)", rows)
        self.conn.commit()

    # -- full graph ---------------------------------------------------------
    def test_full_graph_runs_roles_in_order(self):
        # Section 8's "13 calls" counts 12 review roles + 1 settlement reflection;
        # review_ticker itself makes the 12 roles below (see memory tests for settle).
        llm = llm_client.FakeLLM(auto=True)
        run_id = self.review(llm)
        self.assertEqual(tuple(call["role"] for call in llm.calls), EXPECTED_ROLES)
        self.assertEqual(len(EXPECTED_ROLES), 12)
        row = self.run_row(run_id)
        self.assertEqual(row["status"], "ok")
        self.assertEqual(row["rating"], "Hold")
        self.assertGreater(row["tokens_in"], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM agent_runs").fetchone()[0], 1)
        final = self.final(run_id)
        self.assertEqual(set(final), FINAL_KEYS)
        self.assertEqual(final["agrees"], "caution")
        self.assertEqual(final["rules"]["entry"], self.entry)
        self.assertTrue(final["evidence_index"])
        self.assertFalse(any(key.startswith(("news:", "rule:")) for key in final["evidence_index"]))

    def test_unknown_evidence_id_is_retried(self):
        bad = {"signal": "neutral", "summary": "Momentum is steady.",
               "points": [{"text": "The trend is up.", "evidence": ["news:999999"]}],
               "data_gaps": []}
        llm = llm_client.FakeLLM(responses={"market": [bad, MARKET_OK]}, auto=True)
        run_id = self.review(llm)
        messages = self.messages(run_id)
        self.assertEqual([m["role"] for m in messages[:2]], ["market", "market"])
        self.assertIn("news:999999", messages[0]["error"])
        self.assertIsNone(messages[1]["error"])
        self.assertEqual(self.run_row(run_id)["status"], "ok")

    def test_invented_number_is_rejected(self):
        bad = {"signal": "neutral", "summary": "Momentum is steady.",
               "points": [{"text": "The stock jumped 999.99% today.", "evidence": ["metric:close"]}],
               "data_gaps": []}
        llm = llm_client.FakeLLM(responses={"market": [bad, MARKET_OK]}, auto=True)
        run_id = self.review(llm)
        messages = self.messages(run_id)
        self.assertEqual([m["role"] for m in messages[:2]], ["market", "market"])
        self.assertIn("needs at least 1 points", messages[0]["error"])  # the invented point was dropped
        self.assertIsNone(messages[1]["error"])
        self.assertEqual(self.run_row(run_id)["rating"], "Hold")

    def test_point_with_invented_number_is_dropped_but_others_stay(self):
        mixed = {"signal": "neutral", "summary": "Momentum is steady.",
                 "points": [{"text": "The stock jumped 999.99% today.", "evidence": ["metric:close"]},
                            {"text": "The trend is up.", "evidence": ["metric:close"]}],
                 "data_gaps": []}
        llm = llm_client.FakeLLM(responses={"market": [mixed]}, auto=True)
        run_id = self.review(llm)
        messages = self.messages(run_id)
        self.assertIsNone(messages[0]["error"])
        texts = [p["text"] for p in json.loads(self.run_row(run_id)["final_json"])["analysts"]["market"]["points"]]
        self.assertEqual(texts, ["The trend is up."])

    def test_stream_reply_cut_off_is_an_error_not_an_inner_object(self):
        class Resp:
            status_code = 200
            text = ""

            def iter_lines(self, decode_unicode=True):
                yield 'data: {"choices":[{"delta":{"content":"{\\"points\\": [{\\"text\\": \\"a\\", \\"evidence\\": [\\"x\\"]}"},"finish_reason":null}]}'
                yield 'data: {"choices":[{"delta":{},"finish_reason":"length"}],"usage":{"prompt_tokens":3,"completion_tokens":9}}'
                yield "data: [DONE]"

        llm = llm_client.OpenAICompatLLM("http://x", "k", "m")
        llm._post = lambda body: Resp()
        with self.assertRaises(llm_client.LLMError) as ctx:
            llm.chat_json("bull", "s", "u")
        self.assertIn("cut off", str(ctx.exception))

    def test_bad_rating_twice_becomes_review(self):
        bad = {"rating": "Strong Buy", "summary": "Momentum is strong.", "key_risks": [],
               "evidence": ["metric:close"]}
        llm = llm_client.FakeLLM(responses={"portfolio_manager": [bad, bad]}, auto=True)
        run_id = self.review(llm)
        messages = [m for m in self.messages(run_id) if m["role"] == "portfolio_manager"]
        self.assertEqual(len(messages), 2)
        self.assertTrue(all(m["error"] for m in messages))
        row = self.run_row(run_id)
        self.assertEqual(row["rating"], "REVIEW")
        self.assertEqual(row["status"], "partial")
        self.assertEqual(self.final(run_id)["agrees"], "review")

    def test_trader_stop_above_entry_is_nulled(self):
        levels = {"stance": "enter", "rationale": "Trend is up.", "evidence": ["metric:close"],
                  "suggested_stop": self.entry * 2, "suggested_target": self.entry * 0.5}
        llm = llm_client.FakeLLM(responses={"trader": [levels]}, auto=True)
        trader = self.final(self.review(llm))["trader"]
        self.assertIsNone(trader["suggested_stop"])
        self.assertIsNone(trader["suggested_target"])

    def test_trader_levels_inside_the_atr_range_are_kept(self):
        levels = {"stance": "enter", "rationale": "Trend is up.", "evidence": ["metric:close"],
                  "suggested_stop": round(self.entry * 0.99, 2),
                  "suggested_target": round(self.entry * 1.02, 2)}
        llm = llm_client.FakeLLM(responses={"trader": [levels]}, auto=True)
        trader = self.final(self.review(llm))["trader"]
        self.assertAlmostEqual(trader["suggested_stop"], round(self.entry * 0.99, 2))
        self.assertAlmostEqual(trader["suggested_target"], round(self.entry * 1.02, 2))

    def test_all_analysts_no_data_skips_the_debate(self):
        no_data = {"signal": "no_data", "summary": "No usable data.",
                   "points": [], "data_gaps": ["No usable data."]}
        llm = llm_client.FakeLLM(
            responses={role: [no_data] for role in
                       ("market", "news", "fundamentals", "social")}, auto=True)
        run_id = self.review(llm)
        self.assertEqual(tuple(c["role"] for c in llm.calls),
                         ("market", "news", "fundamentals", "social"))
        row = self.run_row(run_id)
        self.assertEqual(row["rating"], "REVIEW")
        self.assertEqual(row["status"], "partial")
        final = self.final(run_id)
        self.assertEqual(final["debate"], {"bull": [], "bear": [], "manager": None})

    def test_raising_source_is_unavailable_not_a_crash(self):
        run_id = self.review(llm_client.FakeLLM(auto=True), fmp=_boom)
        row = self.run_row(run_id)
        self.assertIn(row["status"], ("ok", "partial"))
        self.assertIsNone(row["error"])
        stored = json.loads(row["sources_json"])
        self.assertEqual(stored["fmp"]["status"], "unavailable")
        self.assertEqual(stored["fmp"]["reason"], "RuntimeError")
        self.assertEqual(stored["news"]["status"], "ok")

    def test_api_key_never_appears_in_stored_errors(self):
        old = os.environ.get("AGENT_LLM_API_KEY")
        os.environ["AGENT_LLM_API_KEY"] = SECRET
        try:
            run_id = self.review(_LeakOnceLLM(SECRET))
        finally:
            if old is None:
                os.environ.pop("AGENT_LLM_API_KEY", None)
            else:
                os.environ["AGENT_LLM_API_KEY"] = old
        messages = self.messages(run_id)
        self.assertEqual([m["role"] for m in messages].count("market"), 1)
        self.assertIn("auth failed", messages[0]["error"])
        self.assertIn("***", messages[0]["error"])
        self.assertNotIn(SECRET, messages[0]["error"])
        stored = "\n".join(str(value) for row in self.conn.execute("SELECT * FROM agent_messages")
                           for value in tuple(row))
        self.assertNotIn(SECRET, stored)
        self.assertNotIn(SECRET, self.run_row(run_id)["error"] or "")
        self.assertEqual(self.run_row(run_id)["status"], "partial")

    # -- memory -------------------------------------------------------------
    # -- triage (quick review) ---------------------------------------------
    def triage_run(self, llm):
        return triage.triage_ticker(self.conn, llm, TICKER, "1w")

    def test_triage_is_one_call_and_stored_as_a_quick_run(self):
        llm = llm_client.FakeLLM(auto=True)
        run_id = self.triage_run(llm)
        self.assertEqual([call["role"] for call in llm.calls], ["triage"])
        row = self.run_row(run_id)
        self.assertEqual(row["prompt_version"], config.TRIAGE_PROMPT_VERSION)
        self.assertEqual(row["status"], "ok")
        self.assertEqual(row["rating"], "Hold")
        final = self.final(run_id)
        self.assertEqual(final["mode"], "triage")
        self.assertEqual(final["agrees"], "caution")
        self.assertEqual(final["rules"]["entry"], self.entry)
        sources_json = json.loads(row["sources_json"])
        for skipped in ("fmp", "sec", "social", "macro"):
            self.assertEqual(sources_json[skipped]["status"], "skipped")
        # Quick reviews never feed the track record or the memory.
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM agent_decisions").fetchone()[0], 0)

    def test_triage_prompt_holds_only_the_one_page_brief(self):
        llm = llm_client.FakeLLM(auto=True)
        self.triage_run(llm)
        user = llm.calls[0]["user"]
        self.assertIn("Rule-based idea", user)
        self.assertIn("Price metrics", user)
        self.assertIn("news:1", user)
        self.assertNotIn("Recent closes", user)
        self.assertNotIn("FMP fundamentals", user)

    def test_triage_keeps_only_a_few_headlines(self):
        last = date(START.year, START.month, START.day) + timedelta(days=PRICE_DAYS - 1)
        for i in range(2, 10):
            self.conn.execute(
                "INSERT INTO news_items (id,ticker,title,source,url,published_at,rule_noise) "
                "VALUES (?,?,?,?,?,?,0)",
                (i, TICKER, f"Headline number {i}", "testwire", f"https://example.test/news/{i}",
                 (last - timedelta(days=1)).isoformat()))
        self.conn.commit()
        llm = llm_client.FakeLLM(auto=True)
        self.triage_run(llm)
        shown = [part for part in llm.calls[0]["user"].split("\n") if part.startswith("[news:")]
        self.assertEqual(len(shown), config.TRIAGE_NEWS)

    def test_triage_unknown_evidence_twice_becomes_review(self):
        bad = {"rating": "Buy", "confidence": "high", "summary": "The trend is up.",
               "points": [{"text": "The trend is up.", "evidence": ["news:999"]}]}
        llm = llm_client.FakeLLM(responses={"triage": [bad, bad]})
        run_id = self.triage_run(llm)
        self.assertEqual(len(llm.calls), 2)
        row = self.run_row(run_id)
        self.assertEqual(row["status"], "partial")
        self.assertEqual(row["rating"], config.REVIEW)

    def test_triage_needs_a_valid_confidence(self):
        bad = {"rating": "Buy", "confidence": "certain", "summary": "The trend is up.",
               "points": [{"text": "The trend is up.", "evidence": ["metric:close"]}]}
        llm = llm_client.FakeLLM(responses={"triage": [bad, bad]})
        self.assertEqual(self.run_row(self.triage_run(llm))["rating"], config.REVIEW)

    def test_triage_without_headlines_cannot_claim_high_confidence(self):
        self.conn.execute("DELETE FROM news_items")
        self.conn.commit()
        reply = {"rating": "Buy", "confidence": "high", "summary": "The trend is up.",
                 "points": [{"text": "The trend is up.", "evidence": ["metric:close"]}]}
        run_id = self.triage_run(llm_client.FakeLLM(responses={"triage": [reply]}))
        final = self.final(run_id)
        self.assertEqual(final["rating"], "Buy")
        self.assertEqual(final["confidence"], "low")

    def test_triage_rejects_an_invented_number(self):
        reply = {"rating": "Buy", "confidence": "medium", "summary": "Revenue grew 47.3 percent.",
                 "points": [{"text": "The trend is up.", "evidence": ["metric:close"]}]}
        llm = llm_client.FakeLLM(responses={"triage": [reply, reply]})
        self.assertEqual(self.run_row(self.triage_run(llm))["rating"], config.REVIEW)

    def test_select_for_full_takes_disagreements_and_strong_agreement(self):
        rows = [
            {"ticker": "AAA", "rating": "Buy", "confidence": "high", "score": 90},
            {"ticker": "BBB", "rating": "Buy", "confidence": "medium", "score": 99},
            {"ticker": "CCC", "rating": "Sell", "confidence": "low", "score": 70},
            {"ticker": "DDD", "rating": "Hold", "confidence": "high", "score": 95},
            {"ticker": "EEE", "rating": "Underweight", "confidence": "medium", "score": 80},
            {"ticker": "FFF", "rating": "REVIEW", "confidence": "low", "score": 85},
        ]
        picked = triage.select_for_full(rows, 10)
        self.assertEqual([p["ticker"] for p in picked], ["AAA", "EEE", "CCC"])
        self.assertEqual([p["reason"] for p in picked],
                         ["strong agreement", "disagrees with the rules", "disagrees with the rules"])
        self.assertEqual([p["ticker"] for p in triage.select_for_full(rows, 2)], ["AAA", "EEE"])
        self.assertEqual(triage.select_for_full(rows, 0), [])

    def test_settle_computes_return_benchmark_and_alpha(self):
        run_id = self._insert_run(SETTLE_TICKER, "Buy the trend.")
        memory.record_decision(self.conn, run_id, SETTLE_TICKER, "Buy", "2026-01-01")
        self._seed_prices(SETTLE_TICKER, date(2026, 1, 2), [100, 101, 102, 103, 104, 105])
        sources.cache_put(self.conn, "spy", "SPY", datetime.now(timezone.utc).date().isoformat(),
                          [{"date": "2026-01-02", "close": 400.0},
                           {"date": "2026-01-07", "close": 404.0}])
        self.conn.commit()

        settled = memory.settle(self.conn, llm_client.FakeLLM(auto=True))
        self.assertEqual(settled, 1)
        decision = self.conn.execute(
            "SELECT * FROM agent_decisions WHERE run_id = ?", (run_id,)).fetchone()
        self.assertEqual(decision["entry_close"], 100.0)
        self.assertAlmostEqual(decision["return_pct"], 0.05, places=6)
        self.assertAlmostEqual(decision["benchmark_return_pct"], 0.01, places=6)
        self.assertAlmostEqual(decision["alpha_pct"], 0.04, places=6)
        self.assertTrue(decision["reflection"])

        items = memory.memory_items(self.conn, SETTLE_TICKER)
        self.assertEqual(items[0]["alpha_pct"], 4.0)
        self.assertIn(f"memory:{decision['id']}", memory.memory_evidence(items))

    def test_settle_waits_for_the_full_window(self):
        run_id = self._insert_run(SETTLE_TICKER, "Wait for confirmation.")
        memory.record_decision(self.conn, run_id, SETTLE_TICKER, "Hold", "2026-01-01")
        self._seed_prices(SETTLE_TICKER, date(2026, 1, 2), [100, 101, 102, 103, 104])
        settle_llm = llm_client.FakeLLM(auto=True)
        self.assertEqual(memory.settle(self.conn, settle_llm), 0)
        self.assertEqual(settle_llm.calls, [])
        decision = self.conn.execute(
            "SELECT * FROM agent_decisions WHERE run_id = ?", (run_id,)).fetchone()
        self.assertIsNone(decision["settled_at"])


class ParsingTest(unittest.TestCase):
    def test_extract_json_handles_think_and_fences(self):
        text = '```json\n<think>let me think</think>\n{"rating": "Buy", "n": 1}\n```'
        self.assertEqual(llm_client.extract_json(text), {"rating": "Buy", "n": 1})

    def test_extract_json_skips_leading_prose(self):
        self.assertEqual(llm_client.extract_json('Sure! Here it is: {"a": [1, 2]}'),
                         {"a": [1, 2]})

    def test_extract_json_raises_without_an_object(self):
        with self.assertRaises(llm_client.LLMError):
            llm_client.extract_json("there is no json here")

    def test_extract_rating_variants(self):
        self.assertEqual(validate.extract_rating("Rating: Buy"), "Buy")
        self.assertEqual(validate.extract_rating("rating - Overweight"), "Overweight")
        self.assertIsNone(validate.extract_rating("the rating is unclear"))

    def test_agrees_mapping(self):
        self.assertEqual(config.agrees("Buy"), "agree")
        self.assertEqual(config.agrees("Overweight"), "agree")
        self.assertEqual(config.agrees("Hold"), "caution")
        self.assertEqual(config.agrees("Underweight"), "disagree")
        self.assertEqual(config.agrees("Sell"), "disagree")
        self.assertEqual(config.agrees("REVIEW"), "review")


if __name__ == "__main__":
    unittest.main()
