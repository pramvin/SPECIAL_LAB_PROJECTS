"""OpenAI-compatible chat client for the analyst roles.

The model runs remotely (never on the user's machine). Every call asks for one
JSON object, strips a thinking block and markdown fences, retries transient
failures, and never puts the API key in an exception or log message.
"""
from __future__ import annotations

import json
import re
import threading
import time
from typing import Any

import requests

from . import config


class LLMError(Exception):
    """A finished call that failed; the message never contains the API key."""


class AuthError(LLMError):
    """401/403 from the gateway: the key is wrong or revoked, so no later call can work either."""


def scrub(text: str, secret: str | None) -> str:
    if secret:
        text = text.replace(secret, "***")
    return text


def extract_json(text: str) -> dict:
    """Take the first JSON object in a model reply, tolerating think blocks/fences."""
    if not isinstance(text, str):
        raise LLMError("model returned no text")
    text = re.sub(r"<think\b[^>]*>.*?</think\s*>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "").strip()
    decoder = json.JSONDecoder()
    for i, char in enumerate(text):
        if char != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[i:])
        except ValueError:
            continue
        if isinstance(obj, dict):
            return obj
    raise LLMError("no JSON object in model reply")


class OpenAICompatLLM:
    RETRY_STATUSES = {429, 500, 502, 503, 504, 522, 524}
    BACKOFF = (3, 5, 10, 20, 30, 30, 30, 30)

    def __init__(self, base_url: str, api_key: str, model: str, timeout: int = config.REQUEST_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._no_response_format = False

    def _post(self, payload: dict) -> requests.Response:
        # stream=True: the gateway sits behind Cloudflare, which answers 524 when no byte
        # arrives for ~100 s. A reasoning model can think longer than that, so read it as a
        # stream (reasoning chunks keep the connection alive) and join the pieces ourselves.
        return requests.post(
            f"{self.base_url}/chat/completions",
            json={**payload, "stream": True, "stream_options": {"include_usage": True}},
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            timeout=self.timeout,
            stream=True,
        )

    @staticmethod
    def _read_stream(response: requests.Response) -> tuple[str, dict, str, str]:
        """Join the content deltas of an SSE reply: (content, usage, model, finish_reason)."""
        parts: list[str] = []
        usage: dict = {}
        model = ""
        finish = ""
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            chunk = line[5:].strip()
            if chunk == "[DONE]":
                break
            try:
                data = json.loads(chunk)
            except ValueError:
                continue
            model = data.get("model") or model
            usage = data.get("usage") or usage
            for choice in data.get("choices") or []:
                finish = choice.get("finish_reason") or finish
                delta = choice.get("delta") or choice.get("message") or {}
                if delta.get("content"):
                    parts.append(delta["content"])
        return "".join(parts), usage, model, finish

    def chat_json(self, role: str, system: str, user: str) -> dict:
        model = self.model
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": config.TEMPERATURE,
            "max_tokens": config.MAX_TOKENS,
        }
        if not self._no_response_format:
            body["response_format"] = {"type": "json_object"}

        t0 = time.time()
        last_error = ""
        for attempt in range(len(self.BACKOFF) + 1):
            try:
                response = self._post(body)
                if (response.status_code == 400 and not self._no_response_format
                        and "response_format" in (response.text or "").lower()):
                    self._no_response_format = True
                    body.pop("response_format", None)
                    response = self._post(body)
                if response.status_code in self.RETRY_STATUSES:
                    last_error = f"HTTP {response.status_code}: {scrub((response.text or '')[:200], self.api_key)}"
                    raise _Retryable(last_error)
                if response.status_code in (401, 403):
                    raise AuthError(f"HTTP {response.status_code}: gateway rejected the API key")
                if response.status_code >= 400:
                    raise LLMError(f"HTTP {response.status_code}: {scrub((response.text or '')[:200], self.api_key)}")
                content, usage, reply_model, finish = self._read_stream(response)
                if finish == "length":
                    # cut off at max_tokens: the JSON is incomplete, and extract_json would
                    # otherwise pick an inner object out of it, so fail loudly instead
                    raise LLMError("reply cut off at the max_tokens limit (the model thought too long)")
                if not content.strip():
                    last_error = "empty model reply (reasoning used the whole token budget?)"
                    raise _Retryable(last_error)
                parsed = extract_json(content)
                return {
                    "data": parsed,
                    "raw": content,
                    "model": reply_model or model,
                    "tokens_in": int(usage.get("prompt_tokens") or 0),
                    "tokens_out": int(usage.get("completion_tokens") or 0),
                    "latency_ms": int((time.time() - t0) * 1000),
                }
            except _Retryable as exc:
                last_error = str(exc)
            except (requests.Timeout, requests.ConnectionError, requests.exceptions.ChunkedEncodingError) as exc:
                last_error = f"{type(exc).__name__}: {scrub(str(exc), self.api_key)}"[:300]
            if attempt < len(self.BACKOFF):
                time.sleep(self.BACKOFF[attempt])
        raise LLMError(last_error or "request failed")


class _Retryable(Exception):
    pass


class FakeLLM:
    """Canned or auto-generated valid replies, for tests and `--fake`.

    `responses` maps a role to a list consumed in order; each item is a dict or
    a JSON string. With `auto=True`, a role without a scripted reply gets a
    shape-valid object that cites the first allowed evidence id in the prompt.
    """

    def __init__(self, responses: dict[str, list] | None = None, auto: bool = False,
                 model: str = "fake-model"):
        self.responses = {role: list(items) for role, items in (responses or {}).items()}
        self.auto = auto
        self.model = model
        self.calls: list[dict] = []
        self._lock = threading.Lock()

    def chat_json(self, role: str, system: str, user: str) -> dict:
        with self._lock:
            queued = self.responses.get(role)
            item = queued.pop(0) if queued else None
            if item is None and self.auto:
                item = _auto_output(role, user)
            if item is None:
                item = {}
            raw = item if isinstance(item, str) else json.dumps(item)
            try:
                data = json.loads(raw) if isinstance(raw, str) else item
            except ValueError:
                data = {}
            self.calls.append({"role": role, "system": system, "user": user,
                               "data": data, "raw": raw})
        return {"data": data, "raw": raw, "model": self.model,
                "tokens_in": max(1, len(system + user) // 4), "tokens_out": max(1, len(raw) // 4),
                "latency_ms": 1}


def _allowed_ids(user: str) -> list[str]:
    match = re.search(r"Allowed evidence ids:\s*(.+)", user)
    if not match:
        return []
    ids = [part.strip() for part in match.group(1).split(",")]
    return [i for i in ids if i and not i.startswith("(")]


def _auto_output(role: str, user: str) -> dict:
    ids = _allowed_ids(user)
    if role == "market":
        return {"summary": "The price data is limited.", "evidence": ids[:1],
                "support": [], "resistance": [],
                "momentum": {"label": "flat", "why": ""}, "volume": {"label": "normal", "why": ""}}
    if role == "news":
        return {"direction": "neutral", "summary": "The headlines do not point one way.",
                "evidence": ids[:1]}
    if role == "social":
        return {"direction": "neutral", "summary": "The posts do not point one way.",
                "evidence": ids[:1], "items": []}
    return {}
