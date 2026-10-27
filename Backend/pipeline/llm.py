"""Pipeline step 5 (AI): structured impact analysis of recent headlines per ticker, by an LLM on Kaggle.

The model is NOT run locally. LLM_URL and LLM_TOKEN (Backend/.env or environment) point at the Kaggle
notebook `experiments/kaggle_gateways.ipynb` (Ollama behind a Cloudflare tunnel); the URL changes every restart.
Output is display-only. It never changes the score, entry, stop or target.
Input today is every non-noise headline of the last 7 days; stages 3 and 4 (source tier, event/rumor/filler)
are not built yet, so credibility is NOT filtered here. Every call is logged in `llm_analysis`.

Run from Backend/ after news:  .venv/bin/python -m pipeline.llm [--limit N]
"""
import argparse
import json
import os
import re
import sqlite3
import time
from datetime import datetime, timezone

import requests

HERE = os.path.dirname(__file__)
DB_PATH = os.environ.get("PLANWISE_DB", os.path.join(HERE, "..", "planwise.db"))
PROMPT_VERSION = "v3"
MAX_HEADLINES = 15

SCHEMA = """
CREATE TABLE IF NOT EXISTS llm_analysis (
  id INTEGER PRIMARY KEY,
  ticker TEXT NOT NULL,
  as_of TEXT NOT NULL,
  model TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  input_news_ids TEXT NOT NULL,
  output_json TEXT,
  tokens_in INTEGER, tokens_out INTEGER, latency_ms INTEGER,
  error TEXT,
  created_at TEXT NOT NULL
);
"""

OUT_SCHEMA = {
    "type": "object",
    "properties": {
        "direction": {"type": "string", "enum": ["up", "down", "none"]},
        "magnitude": {"type": "string", "enum": ["low", "medium", "high"]},
        "horizon": {"type": "string", "enum": ["1w", "1m", "3m", "unclear"]},
        "confidence": {"type": "number"},
        "reasons": {"type": "array", "items": {"type": "string"}},
        "cited_news_ids": {"type": "array", "items": {"type": "integer"}},
        "caveats": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["direction", "magnitude", "horizon", "confidence", "reasons", "cited_news_ids", "caveats"],
}

SYSTEM = (
    "You analyse recent news headlines about one US stock. Use ONLY the headlines given. "
    "Decide whether they support a price move up or down over the next days to weeks. "
    "If the headlines do not clearly support a view (filler, quote pages, promotions, unrelated, conflicting), "
    'answer direction "none" with low confidence. Never give prices, targets or advice. '
    "reasons: at most 3 plain sentences in your own words, each resting on a headline whose id you list in "
    "cited_news_ids. Do NOT write ids, brackets or quotes inside reasons. "
    "caveats: only real gaps specific to THESE headlines "
    "(name what is missing or uncertain in the text you were given). Use an empty list if there is none. Do not write generic caveats. "
    "confidence is between 0 and 1; use below 0.5 when the headlines are mixed or thin."
)


def load_env() -> None:
    path = os.path.join(HERE, "..", ".env")
    if not os.path.exists(path):
        return
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def build_prompt(ticker: str, name: str, rows: list[tuple]) -> str:
    lines = [f'[{nid}] {pub[:10]} | {source} | {title}' for nid, title, source, pub in rows]
    return f"Stock: {ticker} ({name})\nHeadlines:\n" + "\n".join(lines)


def validate(out: dict, allowed_ids: set[int]) -> dict:
    """Schema enforcement is done by Ollama; this checks the parts a schema cannot (ids, ranges)."""
    if not isinstance(out.get("confidence"), (int, float)) or not 0 <= out["confidence"] <= 1:
        raise ValueError("confidence outside 0..1")
    bad = [i for i in out["cited_news_ids"] if i not in allowed_ids]
    if bad:
        raise ValueError(f"cited ids not in input: {bad}")
    if out["direction"] != "none" and not out["cited_news_ids"]:
        raise ValueError("a view without any cited headline")
    out["reasons"] = [re.sub(r"^\s*\[?\d+\]?\s*[:\-]?\s*", "", r) for r in out["reasons"]]  # model sometimes copies the id
    return out


def call(url: str, token: str, prompt: str, think: bool = False) -> dict:
    r = requests.post(
        f"{url.rstrip('/')}/chat",
        json={"messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
              "format": OUT_SCHEMA, "options": {"temperature": 0, "num_ctx": 4096}, "think": think},
        headers={"Authorization": f"Bearer {token}"}, timeout=300)
    r.raise_for_status()
    return r.json()


def analyse(url: str, token: str, ticker: str, name: str, rows: list[tuple], think: bool = False) -> dict:
    """One ticker. Retries once on invalid output; always returns a dict ready to log."""
    ids = {r[0] for r in rows}
    prompt = build_prompt(ticker, name, rows)
    res = {"output": None, "tokens_in": 0, "tokens_out": 0, "ms": 0, "error": None, "model": ""}
    for _ in range(2):
        t0 = time.time()
        try:
            j = call(url, token, prompt, think)
            res["model"] = j["model"]
            res["tokens_in"] += j.get("tokens_in") or 0
            res["tokens_out"] += j.get("tokens_out") or 0
            res["output"] = validate(json.loads(j["content"]), ids)
            res["error"] = None
        except (ValueError, KeyError, requests.RequestException) as e:
            res["output"], res["error"] = None, f"{type(e).__name__}: {e}"[:300]
        res["ms"] += int((time.time() - t0) * 1000)
        if res["output"]:
            break
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="analyse at most N tickers (smoke test)")
    args = ap.parse_args()

    load_env()
    url, token = os.environ.get("LLM_URL"), os.environ.get("LLM_TOKEN")
    if not url or not token:
        raise SystemExit("Set LLM_URL and LLM_TOKEN in Backend/.env (printed by the Kaggle notebook)")
    requests.get(f"{url.rstrip('/')}/health", timeout=30).raise_for_status()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    tickers = conn.execute("SELECT DISTINCT ticker, name FROM recommendations ORDER BY ticker").fetchall()
    if args.limit:
        tickers = tickers[: args.limit]
    as_of = datetime.now(timezone.utc).date().isoformat()
    ok = 0
    for ticker, name in tickers:
        rows = conn.execute(
            "SELECT id, title, source, published_at FROM news_items WHERE ticker = ? AND rule_noise = 0 "
            "ORDER BY published_at DESC LIMIT ?", (ticker, MAX_HEADLINES)).fetchall()
        if not rows:
            print(f"{ticker}: no headlines, skipped")
            continue
        res = analyse(url, token, ticker, name, rows)
        with conn:
            conn.execute(
                "INSERT INTO llm_analysis (ticker, as_of, model, prompt_version, input_news_ids, output_json, "
                "tokens_in, tokens_out, latency_ms, error, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (ticker, as_of, res["model"], PROMPT_VERSION, json.dumps([r[0] for r in rows]),
                 json.dumps(res["output"]) if res["output"] else None, res["tokens_in"], res["tokens_out"],
                 res["ms"], res["error"], datetime.now(timezone.utc).isoformat()))
        ok += bool(res["output"])
        print(f"{ticker}: {res['output']['direction'] if res['output'] else 'ERROR ' + res['error']} ({res['ms']} ms)")
    print(f"{ok}/{len(tickers)} tickers analysed")


if __name__ == "__main__":
    main()
