"""Click-analysis engine and API. Run from Backend/:  python -m unittest tests.test_analysis -v

Temp SQLite only (`PLANWISE_DB` points at the test file), `FakeLLM`, and injected fetchers:
no test calls the network or a real model. `app.main` is replaced by a tiny stand-in module so
the API tests do not depend on the rest of the web app.
"""
import json
import os
import sys
import tempfile
import threading
import time
import types
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from agents import analyze, config, context, llm_client, schema
from app import analysis_api, dbcompat

TICKER = "DIS"
SECRET = "sk-test-SECRET-must-never-be-stored"
ZIGZAG = [100, 102, 104, 106, 108, 106, 104, 102, 100, 98]  # the last close (98) sits at a trough


def now():
    return datetime.now(timezone.utc)


def ago(**kwargs) -> str:
    return (now() - timedelta(**kwargs)).isoformat()


def static(result):
    def fetch(*args, **kwargs):
        return result
    return fetch


SOCIAL_OK = {"status": "ok", "reason": None, "items": [
    {"id": "social:stocktwits:1", "source": "stocktwits", "title": "$DIS looks strong", "body": "",
     "score": 5, "sentiment": "Bullish", "published_at": ago(hours=2), "url": "https://example.test/s/1"},
    {"id": "social:stocktwits:2", "source": "stocktwits", "title": "Watching $DIS today", "body": "",
     "score": 1, "sentiment": None, "published_at": ago(hours=3), "url": "https://example.test/s/2"},
]}
NO_SOCIAL = {"status": "skipped", "reason": "Reddit credentials are not set; StockTwits returned 403", "items": []}


class BaseCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = os.path.join(directory.name, "analysis.db")
        env = mock.patch.dict(os.environ, {"PLANWISE_DB": self.path})
        env.start()
        self.addCleanup(env.stop)
        self.conn = dbcompat.connect(self.path)
        self.addCleanup(self.conn.close)
        self.conn.executescript("""
            CREATE TABLE prices (ticker TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume INTEGER);
            CREATE TABLE recommendations (id INTEGER PRIMARY KEY, ticker TEXT, name TEXT, horizon TEXT);
            CREATE TABLE news_items (id INTEGER PRIMARY KEY, ticker TEXT, title TEXT, source TEXT, url TEXT,
                                     published_at TEXT, rule_noise INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE news_scores (news_id INTEGER, model TEXT, sentiment TEXT, scored_at TEXT);
        """)
        today = now().date()
        for i in range(120):
            close = float(ZIGZAG[i % 10])
            day = (today - timedelta(days=119 - i)).isoformat()
            self.conn.execute("INSERT INTO prices VALUES (?, ?, ?, ?, ?, ?, ?)",
                              (TICKER, day, close, close + 1, close - 1, close, 1_000_000))
        self.conn.execute("INSERT INTO recommendations (ticker, name, horizon) VALUES (?, ?, '1w')",
                          (TICKER, "Walt Disney"))
        self.conn.commit()
        schema.ensure(self.conn)
        self.fetchers = {"social": static(SOCIAL_OK), "refresh_news": lambda *args: None}

    def add_news(self, title, sentiment=None, published_at=None, noise=0):
        cursor = self.conn.execute(
            "INSERT INTO news_items (ticker, title, source, url, published_at, rule_noise) "
            "VALUES (?, ?, 'testwire', ?, ?, ?)",
            (TICKER, title, f"https://example.test/{title.replace(' ', '-')}", published_at or ago(days=1), noise))
        if sentiment:
            self.conn.execute("INSERT INTO news_scores VALUES (?, 'ml', ?, ?)",
                              (cursor.lastrowid, sentiment, ago(hours=1)))
        self.conn.commit()
        return cursor.lastrowid

    def seed_week_of_news(self):
        for title, sentiment in (("DIS beats estimates", "bullish"), ("DIS raises outlook", "bullish"),
                                 ("DIS parks busy", "positive"), ("DIS faces a lawsuit", "bearish"),
                                 ("DIS names a new chair", "neutral")):
            self.add_news(title, sentiment)
        self.add_news("DIS sponsored listicle", "bullish", noise=1)              # noise: ignored
        self.add_news("DIS old story", "bullish", published_at=ago(days=10))     # older than 7 days

    def factory(self):
        return dbcompat.connect(self.path)

    def run_job(self, llm, **overrides):
        run_id = analyze.run_analysis(self.factory, llm, TICKER, "1w", {**self.fetchers, **overrides})
        row = self.conn.execute("SELECT * FROM stock_analysis WHERE id = ?", (run_id,)).fetchone()
        return row, (json.loads(row["result_json"]) if row["result_json"] else None)


class EngineTest(BaseCase):
    def test_happy_path_stores_one_ok_result_with_counts_from_labels(self):
        self.seed_week_of_news()
        llm = llm_client.FakeLLM(auto=True)
        row, result = self.run_job(llm)
        self.assertEqual(row["status"], "ok")
        self.assertIsNone(row["error"])
        self.assertGreater(row["tokens"], 0)
        self.assertEqual(row["model"], "fake-model")
        self.assertTrue(row["finished_at"])
        self.assertEqual({call["role"] for call in llm.calls}, {"market", "news", "social"})
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM stock_analysis_messages").fetchone()[0], 3)
        self.assertEqual(set(result), {"chart", "news", "social"})
        self.assertTrue(all(block["status"] == "ok" for block in result.values()))
        news = result["news"]
        self.assertEqual(news["counts"], {"positive": 3, "neutral": 1, "negative": 1})
        self.assertEqual(news["positive_share"], 0.6)
        self.assertEqual(len(news["items"]), 5)
        self.assertEqual({item["sentiment"] for item in news["items"]}, {"positive", "neutral", "negative"})
        self.assertNotIn("DIS old story", {item["title"] for item in news["items"]})
        self.assertNotIn("DIS sponsored listicle", {item["title"] for item in news["items"]})
        self.assertEqual(news["direction"], "neutral")

    def test_social_uses_the_user_tag_first_then_the_model_label(self):
        self.seed_week_of_news()
        llm = llm_client.FakeLLM(auto=True, responses={"social": [{
            "direction": "positive", "summary": "Most posts are upbeat.", "evidence": ["social:stocktwits:1"],
            "items": [{"id": "social:stocktwits:1", "sentiment": "negative"},
                      {"id": "social:stocktwits:2", "sentiment": "neutral"}]}]})
        _, result = self.run_job(llm)
        social = result["social"]
        self.assertEqual([item["sentiment"] for item in social["items"]], ["positive", "neutral"])
        self.assertEqual(social["direction"], "positive")
        self.assertEqual(social["sources"]["stocktwits"], {"status": "ok", "count": 2})
        self.assertEqual(social["sources"]["reddit"], {"status": "unavailable", "count": 0})

    def test_support_and_resistance_come_only_from_computed_levels(self):
        ctx = context.collect(self.conn, TICKER, "1w", {"social": static(SOCIAL_OK)})
        self.assertTrue(ctx.levels["support"] and ctx.levels["resistance"])
        support = ctx.levels["support"][0]["price"]
        market = {"summary": "The price sits near the bottom of its recent range.",
                  "evidence": ["metric:close"],
                  "support": [{"price": support, "why": "Buyers stepped in here before."},
                              {"price": 999.99, "why": "Invented level."}],
                  "resistance": [],
                  "momentum": {"label": "weakening", "why": "Closes are slipping."},
                  "volume": {"label": "normal", "why": ""}}
        _, result = self.run_job(llm_client.FakeLLM(auto=True, responses={"market": [market]}))
        chart = result["chart"]
        self.assertEqual(chart["support"], [{"price": support, "why": "Buyers stepped in here before."}])
        computed_resistance = {item["price"] for item in ctx.levels["resistance"]}
        self.assertTrue(chart["resistance"])
        self.assertTrue({item["price"] for item in chart["resistance"]} <= computed_resistance)
        self.assertEqual(chart["momentum"], {"label": "weakening", "why": "Closes are slipping."})

    def test_invented_number_fails_the_role_after_one_retry(self):
        bad = {"summary": "The stock will reach 987.65 next week.", "evidence": ["metric:close"]}
        llm = llm_client.FakeLLM(auto=True, responses={"market": [bad, bad]})
        row, result = self.run_job(llm)
        self.assertEqual(sum(1 for call in llm.calls if call["role"] == "market"), 2)
        self.assertEqual(result["chart"]["status"], "unavailable")
        self.assertIn("not in the context", result["chart"]["reason"])
        self.assertEqual(row["status"], "partial")

    def test_one_role_failing_gives_partial(self):
        self.seed_week_of_news()

        class MarketDown(llm_client.FakeLLM):
            def chat_json(self, role, system, user):
                if role == "market":
                    raise llm_client.LLMError("HTTP 500: boom")
                return super().chat_json(role, system, user)

        row, result = self.run_job(MarketDown(auto=True))
        self.assertEqual(row["status"], "partial")
        self.assertEqual(result["chart"]["status"], "unavailable")
        self.assertIn("boom", result["chart"]["reason"])
        self.assertEqual(result["news"]["status"], "ok")
        self.assertEqual(result["social"]["status"], "ok")

    def test_all_roles_failing_gives_error_and_keeps_the_real_headline_data(self):
        self.seed_week_of_news()

        class Down(llm_client.FakeLLM):
            def chat_json(self, role, system, user):
                raise llm_client.LLMError("gateway down")

        row, result = self.run_job(Down(auto=True))
        self.assertEqual(row["status"], "error")
        self.assertIn("gateway down", row["error"])
        self.assertTrue(all(block["status"] == "unavailable" for block in result.values()))
        self.assertEqual(result["news"]["counts"]["positive"], 3)  # counts come from code, not the model

    def test_a_rejected_key_fails_each_role_without_retrying(self):
        class Rejected(llm_client.FakeLLM):
            def chat_json(self, role, system, user):
                raise llm_client.AuthError("HTTP 401: gateway rejected the API key")

        self.seed_week_of_news()
        llm = Rejected(auto=True)
        row, _ = self.run_job(llm)
        self.assertEqual(row["status"], "error")

    def test_api_key_never_reaches_the_database(self):
        self.seed_week_of_news()

        class Leaky(llm_client.FakeLLM):
            def chat_json(self, role, system, user):
                raise RuntimeError(f"auth failed for key {SECRET}")

        with mock.patch.dict(os.environ, {"AGENT_LLM_API_KEY": SECRET}):
            self.run_job(Leaky(auto=True))
        dump = json.dumps([list(map(str, row)) for table in ("stock_analysis", "stock_analysis_messages")
                           for row in self.conn.execute(f"SELECT * FROM {table}").fetchall()])
        self.assertNotIn(SECRET, dump)
        self.assertIn("***", dump)

    def test_no_headlines_and_no_posts_skip_those_model_calls(self):
        llm = llm_client.FakeLLM(auto=True)
        row, result = self.run_job(llm, social=static(NO_SOCIAL))
        self.assertEqual([call["role"] for call in llm.calls], ["market"])
        news = result["news"]
        self.assertEqual((news["status"], news["direction"], news["positive_share"]), ("ok", "neutral", None))
        self.assertEqual(news["counts"], {"positive": 0, "neutral": 0, "negative": 0})
        social = result["social"]
        self.assertEqual((social["status"], social["direction"], social["items"]), ("skipped", "no_data", []))
        self.assertEqual(social["sources"]["reddit"]["status"], "skipped")
        self.assertEqual(row["status"], "ok")

    def test_no_price_history_leaves_the_chart_unavailable(self):
        self.conn.execute("DELETE FROM prices")
        self.conn.commit()
        self.seed_week_of_news()
        row, result = self.run_job(llm_client.FakeLLM(auto=True))
        self.assertEqual(result["chart"]["status"], "unavailable")
        self.assertIn("price history", result["chart"]["reason"])
        self.assertEqual(row["status"], "partial")

    def test_refresh_hook_runs_first_and_its_headlines_are_analysed(self):
        calls = []

        def refresh(conn, ticker, name):
            calls.append((ticker, name))
            self.add_news("DIS fresh headline", "bullish")

        _, result = self.run_job(llm_client.FakeLLM(auto=True), refresh_news=refresh)
        self.assertEqual(calls, [(TICKER, "Walt Disney")])
        self.assertEqual(result["news"]["counts"]["positive"], 1)

    def test_a_failing_refresh_does_not_stop_the_analysis(self):
        def refresh(conn, ticker, name):
            raise RuntimeError("yahoo is down")

        self.seed_week_of_news()
        row, _ = self.run_job(llm_client.FakeLLM(auto=True), refresh_news=refresh)
        self.assertEqual(row["status"], "ok")

    def test_the_three_analysts_run_at_the_same_time(self):
        self.seed_week_of_news()
        barrier = threading.Barrier(3, timeout=5)

        class Meeting(llm_client.FakeLLM):
            def chat_json(self, role, system, user):
                barrier.wait()  # raises BrokenBarrierError unless all three calls are in flight together
                return super().chat_json(role, system, user)

        row, _ = self.run_job(Meeting(auto=True))
        self.assertEqual(row["status"], "ok")
        self.assertEqual(analyze.LLM_SLOTS._value, 3)  # every slot was given back

    def test_a_crash_is_stored_as_an_error_row_not_raised(self):
        with mock.patch.object(analyze.context, "collect", side_effect=RuntimeError("disk gone")):
            row, result = self.run_job(llm_client.FakeLLM(auto=True))
        self.assertEqual((row["status"], row["error"], result), ("error", "RuntimeError: disk gone", None))

    def test_a_dead_database_does_not_raise(self):
        def broken():
            raise RuntimeError("no database")

        self.assertEqual(analyze.run_analysis(broken, llm_client.FakeLLM(auto=True), TICKER), 0)


class SmallPartsTest(unittest.TestCase):
    def test_extract_json_handles_think_blocks_and_fences(self):
        text = '```json\n<think>let me think</think>\n{"direction": "neutral", "n": 1}\n```'
        self.assertEqual(llm_client.extract_json(text), {"direction": "neutral", "n": 1})
        with self.assertRaises(llm_client.LLMError):
            llm_client.extract_json("there is no json here")

    def test_scrub_hides_the_secret(self):
        self.assertEqual(llm_client.scrub(f"key {SECRET} bad", SECRET), "key *** bad")

    def test_sentiment_labels_are_mapped_to_the_api_words(self):
        self.assertEqual([analyze.normalize_sentiment(x) for x in ("bullish", "Bearish", "neutral", "positive", None, "x")],
                         ["positive", "negative", "neutral", "positive", None, None])

    def test_the_cli_refuses_fake_runs_without_a_scratch_database(self):
        from agents import run

        with mock.patch.dict(os.environ):
            os.environ.pop("PLANWISE_DB", None)
            self.assertEqual(run.main(["--tickers", "DIS", "--fake"]), 2)

    def test_old_tables_are_not_created(self):
        self.assertNotIn("agent_runs", schema.DDL)


class ApiTest(BaseCase):
    def setUp(self):
        super().setUp()
        self.gate = threading.Event()
        self.gate.set()
        analysis_api.FETCHERS = {"social": static(SOCIAL_OK),
                                 "refresh_news": lambda *args: self.gate.wait(10)}
        self.addCleanup(setattr, analysis_api, "FETCHERS", None)

        def current_user(conn, token):
            if token != "tok":
                raise HTTPException(401, "Not signed in")
            return {"id": 1}

        fake_main = types.ModuleType("app.main")
        fake_main.current_user = current_user
        fake_main.db = self.factory
        patch = mock.patch.dict(sys.modules, {"app.main": fake_main})
        patch.start()
        self.addCleanup(patch.stop)
        env = mock.patch.dict(os.environ, {"AGENT_FAKE_LLM": "1"})
        env.start()
        self.addCleanup(env.stop)

        app = FastAPI()
        app.include_router(analysis_api.router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.client.cookies.set("session", "tok")
        self.seed_week_of_news()

    def rows(self):
        return self.conn.execute("SELECT * FROM stock_analysis ORDER BY id").fetchall()

    def wait_done(self, ticker=TICKER):
        deadline = time.time() + 15
        while time.time() < deadline:
            body = self.client.get(f"/api/analysis/{ticker}?horizon=1w").json()
            if body["status"] != "running":
                return body
            time.sleep(0.05)
        self.fail("the analysis never finished")

    def test_login_is_required(self):
        self.client.cookies.clear()
        self.assertEqual(self.client.post(f"/api/analysis/{TICKER}").status_code, 401)
        self.assertEqual(self.client.get(f"/api/analysis/{TICKER}").status_code, 401)

    def test_only_one_week_is_supported(self):
        for horizon in ("1m", "3m"):
            for call in (self.client.post, self.client.get):
                response = call(f"/api/analysis/{TICKER}?horizon={horizon}")
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json()["detail"], "horizon not supported yet")

    def test_unknown_or_malformed_tickers_are_404(self):
        for ticker in ("NOPE", "1ABC", "A" * 12):
            self.assertEqual(self.client.post(f"/api/analysis/{ticker}").status_code, 404, ticker)
        self.assertEqual(self.rows(), [])

    def test_a_ticker_in_the_universe_is_accepted(self):
        self.conn.execute("CREATE TABLE universe (ticker TEXT, name TEXT)")
        self.conn.execute("INSERT INTO universe VALUES ('BRK.B', 'Berkshire')")
        self.conn.commit()
        self.assertEqual(self.client.post("/api/analysis/BRK.B").status_code, 200)
        self.wait_done("BRK.B")

    def test_get_without_an_analysis_is_404(self):
        response = self.client.get(f"/api/analysis/{TICKER}")
        self.assertEqual((response.status_code, response.json()), (404, {"detail": "no analysis"}))

    def test_post_starts_one_background_run_and_get_polls_it_to_the_end(self):
        self.gate.clear()
        first = self.client.post(f"/api/analysis/{TICKER}?horizon=1w").json()
        self.assertEqual((first["status"], first["cached"], first["result"]), ("running", False, None))
        second = self.client.post(f"/api/analysis/{TICKER}?horizon=1w").json()  # a second click joins it
        self.assertEqual(second["started_at"], first["started_at"])
        self.assertEqual(self.client.get(f"/api/analysis/{TICKER}").json()["status"], "running")
        self.assertEqual(len(self.rows()), 1)
        self.gate.set()
        done = self.wait_done()
        self.assertEqual(done["status"], "ok")
        self.assertEqual(done["ticker"], TICKER)
        self.assertEqual(done["horizon"], "1w")
        self.assertEqual(set(done["result"]), {"chart", "news", "social"})
        self.assertEqual(done["result"]["news"]["counts"]["positive"], 3)
        self.assertEqual(len(self.rows()), 1)

    def test_a_fresh_run_is_reused_until_a_newer_headline_arrives(self):
        self.client.post(f"/api/analysis/{TICKER}")
        self.wait_done()
        reused = self.client.post(f"/api/analysis/{TICKER}").json()
        self.assertTrue(reused["cached"])
        self.assertEqual(len(self.rows()), 1)

        self.add_news("DIS breaking story", "bearish", published_at=ago(seconds=-60))  # after the run began
        again = self.client.post(f"/api/analysis/{TICKER}").json()
        self.assertFalse(again["cached"])
        self.wait_done()
        self.assertEqual(len(self.rows()), 2)

    def test_a_noise_headline_does_not_force_a_rerun(self):
        self.client.post(f"/api/analysis/{TICKER}")
        self.wait_done()
        self.add_news("DIS sponsored again", "bullish", published_at=ago(seconds=-60), noise=1)
        self.assertTrue(self.client.post(f"/api/analysis/{TICKER}").json()["cached"])

    def test_an_old_run_is_not_reused(self):
        self.client.post(f"/api/analysis/{TICKER}")
        self.wait_done()
        old = (now() - timedelta(minutes=analysis_api.REUSE_MINUTES + 5)).isoformat(timespec="seconds")
        self.conn.execute("UPDATE stock_analysis SET finished_at = ?", (old,))
        self.conn.commit()
        self.assertFalse(self.client.post(f"/api/analysis/{TICKER}").json()["cached"])
        self.wait_done()
        self.assertEqual(len(self.rows()), 2)

    def test_a_run_that_died_with_the_server_is_expired_and_replaced(self):
        stale = (now() - timedelta(minutes=analysis_api.STALE_RUNNING_MINUTES + 5)).isoformat(timespec="seconds")
        self.conn.execute("INSERT INTO stock_analysis (ticker, horizon, status, started_at) VALUES (?, '1w', 'running', ?)",
                          (TICKER, stale))
        self.conn.commit()
        self.gate.clear()
        body = self.client.post(f"/api/analysis/{TICKER}").json()
        self.assertEqual(body["status"], "running")
        self.assertNotEqual(body["started_at"], stale)
        self.gate.set()
        self.wait_done()
        self.assertEqual([row["status"] for row in self.rows()], ["error", "ok"])

    def test_a_missing_model_setting_ends_in_an_error_row(self):
        with mock.patch.dict(os.environ, {"AGENT_FAKE_LLM": "0", "AGENT_LLM_API_KEY": "", "AGENT_LLM_BASE_URL": "",
                                          "AGENT_LLM_MODEL": ""}), \
                mock.patch.object(config, "load_env"):
            self.client.post(f"/api/analysis/{TICKER}")
            body = self.wait_done()
        self.assertEqual(body["status"], "error")
        self.assertIn("not configured", body["error"])


if __name__ == "__main__":
    unittest.main()
