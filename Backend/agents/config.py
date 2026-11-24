"""Configuration for the click-analysis engine.

Keys are read from `Backend/.env` (same loader as `pipeline/llm.py`) or the
environment. Nothing here prints or stores a secret.
"""
from __future__ import annotations

import os

HERE = os.path.dirname(__file__)
BACKEND = os.path.dirname(HERE)

MAX_NEWS = 15
MAX_SOCIAL = 20
NEWS_DAYS = 7
TEMPERATURE = 0.2
MAX_TOKENS = 14000  # a reasoning model spends most of this thinking; the JSON itself is small
REQUEST_TIMEOUT = 300
PRIMARY_TIMEOUT = 50  # seconds the main model may stay silent before the backup model takes over
CONNECT_TIMEOUT = 10


def load_env() -> None:
    """Load `Backend/.env` without overriding variables already set."""
    path = os.path.join(BACKEND, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def db_path() -> str:
    return os.environ.get("PLANWISE_DB", os.path.join(BACKEND, "planwise.db"))


def llm_settings() -> dict:
    base_url = os.environ.get("AGENT_LLM_BASE_URL", "").strip().rstrip("/")
    api_key = os.environ.get("AGENT_LLM_API_KEY", "").strip()
    model = os.environ.get("AGENT_LLM_MODEL", "").strip()
    return {"base_url": base_url, "api_key": api_key, "model": model}


def llm_fallback_settings() -> dict | None:
    """The backup model (AGENT_LLM_FALLBACK_*), or None when it is not fully configured."""
    base_url = os.environ.get("AGENT_LLM_FALLBACK_BASE_URL", "").strip().rstrip("/")
    api_key = os.environ.get("AGENT_LLM_FALLBACK_API_KEY", "").strip()
    model = os.environ.get("AGENT_LLM_FALLBACK_MODEL", "").strip()
    if not (base_url and api_key and model):
        return None
    return {"base_url": base_url, "api_key": api_key, "model": model}
