"""The backup model takes over when the main model fails or stays silent (no network, no real LLM)."""
import os
import unittest
from unittest import mock

import requests

from agents import analyze, config, llm_client


class _Stub:
    def __init__(self, reply=None, error=None, model="stub"):
        self.reply, self.error, self.model, self.calls = reply, error, model, 0

    def chat_json(self, role, system, user):
        self.calls += 1
        if self.error:
            raise self.error
        return self.reply


class FallbackLLMTest(unittest.TestCase):
    def test_uses_primary_when_it_works(self):
        primary, backup = _Stub({"data": {"a": 1}}), _Stub({"data": {"b": 2}})
        out = llm_client.FallbackLLM(primary, backup).chat_json("market", "s", "u")
        self.assertEqual(out, {"data": {"a": 1}})
        self.assertEqual(backup.calls, 0)

    def test_falls_back_when_primary_fails(self):
        primary = _Stub(error=llm_client.LLMError("ReadTimeout"))
        backup = _Stub({"data": {"b": 2}, "model": "backup"})
        llm = llm_client.FallbackLLM(primary, backup)
        self.assertEqual(llm.chat_json("news", "s", "u")["model"], "backup")
        self.assertEqual(llm.fallback_calls, 1)

    def test_a_rejected_key_on_primary_also_falls_back(self):
        primary = _Stub(error=llm_client.AuthError("HTTP 401"))
        backup = _Stub({"data": {}})
        llm_client.FallbackLLM(primary, backup).chat_json("social", "s", "u")
        self.assertEqual(backup.calls, 1)

    def test_both_failing_reports_both_errors(self):
        llm = llm_client.FallbackLLM(_Stub(error=llm_client.LLMError("first")),
                                     _Stub(error=llm_client.LLMError("second")))
        with self.assertRaises(llm_client.LLMError) as ctx:
            llm.chat_json("market", "s", "u")
        self.assertIn("first", str(ctx.exception))
        self.assertIn("second", str(ctx.exception))


class ShortPrimaryTest(unittest.TestCase):
    def test_one_attempt_and_no_backoff_sleep_on_timeout(self):
        llm = llm_client.OpenAICompatLLM("https://x.test/v1", "k-secret", "m", timeout=(10, 50), attempts=1)
        with mock.patch.object(llm, "_post", side_effect=requests.Timeout("read timed out")) as post, \
                mock.patch("agents.llm_client.time.sleep") as sleep:
            with self.assertRaises(llm_client.LLMError) as ctx:
                llm.chat_json("market", "s", "u")
        self.assertEqual(post.call_count, 1)
        sleep.assert_not_called()
        self.assertNotIn("k-secret", str(ctx.exception))

    def test_default_client_still_retries(self):
        llm = llm_client.OpenAICompatLLM("https://x.test/v1", "k", "m")
        with mock.patch.object(llm, "_post", side_effect=requests.ConnectionError("down")) as post, \
                mock.patch("agents.llm_client.time.sleep"):
            with self.assertRaises(llm_client.LLMError):
                llm.chat_json("market", "s", "u")
        self.assertEqual(post.call_count, len(llm.BACKOFF) + 1)

    def test_timeout_pair_reaches_requests(self):
        llm = llm_client.OpenAICompatLLM("https://x.test/v1", "k", "m", timeout=(10, 50), attempts=1)
        with mock.patch("agents.llm_client.requests.post", side_effect=requests.Timeout("t")) as post:
            with self.assertRaises(llm_client.LLMError):
                llm.chat_json("market", "s", "u")
        self.assertEqual(post.call_args.kwargs["timeout"], (10, 50))


class MakeLLMTest(unittest.TestCase):
    BASE = {"AGENT_LLM_BASE_URL": "https://main.test/v1", "AGENT_LLM_API_KEY": "k1", "AGENT_LLM_MODEL": "main"}
    BACKUP = {"AGENT_LLM_FALLBACK_BASE_URL": "https://backup.test/v1", "AGENT_LLM_FALLBACK_API_KEY": "k2",
              "AGENT_LLM_FALLBACK_MODEL": "backup"}

    def _make(self, env):
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(config, "load_env"):
            return analyze.make_llm()

    def test_without_backup_it_is_a_plain_client(self):
        llm = self._make(self.BASE)
        self.assertIsInstance(llm, llm_client.OpenAICompatLLM)
        self.assertIsNone(llm.attempts)

    def test_with_backup_the_main_model_gets_one_short_try(self):
        llm = self._make({**self.BASE, **self.BACKUP})
        self.assertIsInstance(llm, llm_client.FallbackLLM)
        self.assertEqual(llm.primary.attempts, 1)
        self.assertEqual(llm.primary.timeout, (config.CONNECT_TIMEOUT, config.PRIMARY_TIMEOUT))
        self.assertEqual(llm.fallback.model, "backup")

    def test_an_incomplete_backup_is_ignored(self):
        env = {**self.BASE, "AGENT_LLM_FALLBACK_BASE_URL": "https://backup.test/v1"}
        self.assertIsInstance(self._make(env), llm_client.OpenAICompatLLM)


if __name__ == "__main__":
    unittest.main()
