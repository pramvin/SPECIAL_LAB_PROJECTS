"""Configuration for the AI trading-agent review.

Keys are read from `Backend/.env` (same loader as `pipeline/llm.py`) or the
environment. Nothing here prints or stores a secret.
"""
from __future__ import annotations

import os

HERE = os.path.dirname(__file__)
BACKEND = os.path.dirname(HERE)

PROMPT_VERSION = "ta-v1"
TRIAGE_PROMPT_VERSION = "ta-triage-v1"  # marks a quick one-call review (see agents/triage.py)
TRIAGE_NEWS = 5
CONFIDENCES = ("low", "medium", "high")
MAX_DEBATE_ROUNDS = 1
MAX_RISK_ROUNDS = 1
SETTLE_DAYS = 5
MAX_NEWS = 15
MAX_SOCIAL = 20
TEMPERATURE = 0.2
MAX_TOKENS = 6000
REQUEST_TIMEOUT = 300

RATINGS = ("Buy", "Overweight", "Hold", "Underweight", "Sell")
REVIEW = "REVIEW"
SIGNALS = ("bullish", "neutral", "bearish", "no_data")

ROLE_LABELS = {
    "market": "Market analyst",
    "news": "News analyst",
    "fundamentals": "Fundamentals analyst",
    "social": "Social media analyst",
    "bull": "Bull researcher",
    "bear": "Bear researcher",
    "research_manager": "Research manager",
    "trader": "Trader",
    "aggressive": "Aggressive risk analyst",
    "conservative": "Conservative risk analyst",
    "neutral": "Neutral risk analyst",
    "portfolio_manager": "Portfolio manager",
    "reflection": "Reflection",
}


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
    deep_model = os.environ.get("AGENT_LLM_DEEP_MODEL", "").strip() or model
    triage_model = os.environ.get("AGENT_LLM_TRIAGE_MODEL", "").strip() or model
    return {"base_url": base_url, "api_key": api_key, "model": model, "deep_model": deep_model,
            "triage_model": triage_model}


def agrees(rating: str | None) -> str:
    """Mapping from SPEC: the card's short agreement label."""
    if rating in ("Buy", "Overweight"):
        return "agree"
    if rating == "Hold":
        return "caution"
    if rating in ("Underweight", "Sell"):
        return "disagree"
    return "review"
