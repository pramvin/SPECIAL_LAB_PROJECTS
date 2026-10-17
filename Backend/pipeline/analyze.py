"""Pipeline step 5 (AI): score archived headlines with Laya running on Kaggle, then refresh the card news.

The model is NOT run locally. LAYA_URL and LAYA_TOKEN (Backend/.env or environment) point at the
Kaggle notebook's Cloudflare tunnel; the URL changes every time the notebook is restarted.
Scores are stored in `news_scores` (one row per headline per model). Labels are unvalidated on
our own headlines until the hand-labeled set is evaluated, so the card only DEMOTES likely filler,
never hides it, and sentiment is display-only.

Run from Backend/ after news:  .venv/bin/python -m pipeline.analyze [--all] [--limit N]
"""
import argparse
import json
import os
import sqlite3
from datetime import datetime, timezone

import requests

HERE = os.path.dirname(__file__)
DB_PATH = os.environ.get("PLANWISE_DB", os.path.join(HERE, "..", "planwise.db"))
BATCH = 50
FILLER_DEMOTE = 0.8   # p(filler) at or above this pushes a headline below the others on the card
PER_STOCK = 3

SCHEMA = """
CREATE TABLE IF NOT EXISTS news_scores (
  news_id INTEGER NOT NULL REFERENCES news_items(id),
  model TEXT NOT NULL,
  sentiment TEXT NOT NULL,
  p_bearish REAL, p_bullish REAL, p_neutral REAL,
  kind TEXT NOT NULL,
  p_filler REAL,
  scored_at TEXT NOT NULL,
  PRIMARY KEY (news_id, model)
);
"""


def load_env() -> None:
    path = os.path.join(HERE, "..", ".env")
    if not os.path.exists(path):
        return
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def call(url: str, token: str, headlines: list[str]) -> list[dict]:
    r = requests.post(f"{url.rstrip('/')}/analyze", json={"headlines": headlines},
                      headers={"Authorization": f"Bearer {token}"}, timeout=300)
    r.raise_for_status()
    return r.json()["results"]


def refresh_cards(conn: sqlite3.Connection, model: str) -> int:
    tickers = [r[0] for r in conn.execute("SELECT DISTINCT ticker FROM recommendations")]
    for t in tickers:
        rows = conn.execute(
            "SELECT n.title, n.source, n.url, n.published_at, s.sentiment, s.p_bearish, s.p_bullish, s.p_neutral, "
            "s.kind, s.p_filler FROM news_items n LEFT JOIN news_scores s ON s.news_id = n.id AND s.model = ? "
            "WHERE n.ticker = ? AND n.rule_noise = 0 ORDER BY n.published_at DESC LIMIT 60", (model, t)).fetchall()
        items = []
        for title, source, url, pub, sent, pb, pu, pn, kind, pf in rows:
            item = {"title": title, "source": source, "url": url, "published": pub[:10], "published_at": pub}
            if sent:
                item["sentiment"] = sent
                item["sentiment_conf"] = round({"bearish": pb, "bullish": pu, "neutral": pn}[sent], 3)
                item["kind"] = kind
            item["_demoted"] = bool(pf is not None and pf >= FILLER_DEMOTE)
            items.append(item)
        items.sort(key=lambda x: x["_demoted"])  # stable: newest first within each group
        shown = [{k: v for k, v in i.items() if k != "_demoted"} for i in items[:PER_STOCK]]
        with conn:
            conn.execute("UPDATE recommendations SET news = ? WHERE ticker = ?", (json.dumps(shown), t))
    return len(tickers)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="score the whole archive, not just current ideas")
    ap.add_argument("--limit", type=int, help="score at most N new headlines (smoke test)")
    args = ap.parse_args()

    load_env()
    url, token = os.environ.get("LAYA_URL"), os.environ.get("LAYA_TOKEN")
    if not url or not token:
        raise SystemExit("Set LAYA_URL and LAYA_TOKEN in Backend/.env (printed by the Kaggle notebook)")
    health = requests.get(f"{url.rstrip('/')}/health", timeout=30)
    health.raise_for_status()
    model = health.json()["model"]

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    scope = "" if args.all else "AND n.ticker IN (SELECT DISTINCT ticker FROM recommendations)"
    pending = conn.execute(
        f"SELECT n.id, n.title FROM news_items n WHERE NOT EXISTS (SELECT 1 FROM news_scores s WHERE s.news_id = n.id "
        f"AND s.model = ?) {scope} ORDER BY n.published_at DESC", (model,)).fetchall()
    if args.limit:
        pending = pending[: args.limit]
    print(f"{len(pending)} headlines to score with {model}")

    done = 0
    for i in range(0, len(pending), BATCH):
        chunk = pending[i : i + BATCH]
        results = call(url, token, [t for _, t in chunk])
        now = datetime.now(timezone.utc).isoformat()
        with conn:
            conn.executemany(
                "INSERT OR REPLACE INTO news_scores VALUES (?,?,?,?,?,?,?,?,?)",
                [(nid, model, r["sentiment"], r["sentiment_probs"].get("bearish"), r["sentiment_probs"].get("bullish"),
                  r["sentiment_probs"].get("neutral"), r["kind"], r["kind_probs"].get("filler"), now)
                 for (nid, _), r in zip(chunk, results)])
        done += len(chunk)
        print(f"  scored {done}/{len(pending)}")
    n = refresh_cards(conn, model)
    print(f"cards refreshed for {n} tickers")


if __name__ == "__main__":
    main()
