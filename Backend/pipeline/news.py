"""Pipeline step 4/5 (light): collect headlines, archive them, attach the best to each idea.

Source: Google News RSS (free, no key, unofficial; only ~7 days of history).
Every relevant headline is APPENDED to `news_items` with the time we first saw
it, so history accumulates for later experiments (labeling, latency, price
reaction). Headlines shown on cards are the top few non-noise ones; they do NOT
affect the score yet and are not fact-checked.

Run from Backend/ after rank:
  .venv/bin/python -m pipeline.news          # tickers currently in recommendations
  .venv/bin/python -m pipeline.news --all    # whole S&P 500 universe (~4 min)
"""
import argparse
import json
import os
import re
import sqlite3
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

DB_PATH = os.environ.get("PLANWISE_DB", os.path.join(os.path.dirname(__file__), "..", "planwise.db"))
RSS = "https://news.google.com/rss/search"
PER_STOCK = 3
MAX_AGE_DAYS = 7
DELAY_S = 0.4
SUFFIX = re.compile(r"\b(inc|corp|corporation|co|company|ltd|plc|holdings|group|the|class [a-c])\b\.?,?", re.I)


# Low-value headlines: quote pages, how-to-buy explainers, fund-holding boilerplate.
NOISE = re.compile(
    r"stock price,? news|quote and history|how to buy|how much you would have made|"
    r"\b(stock|shares) (sold|bought|acquired|purchased) by\b|\bposition (in|trimmed|raised|lifted|cut)\b",
    re.I,
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS news_items (
  id INTEGER PRIMARY KEY,
  ticker TEXT NOT NULL,
  title TEXT NOT NULL,
  source TEXT NOT NULL,
  url TEXT NOT NULL,
  published_at TEXT NOT NULL,   -- UTC ISO, when the article came out
  first_seen_at TEXT NOT NULL,  -- UTC ISO, when we first fetched it
  last_seen_at TEXT NOT NULL,
  rule_noise INTEGER NOT NULL,  -- 1 if the keyword filter flags it as low-value
  UNIQUE (ticker, url)
);
CREATE INDEX IF NOT EXISTS idx_news_ticker_pub ON news_items (ticker, published_at);
"""


def keyword(name: str) -> str:
    """Distinctive part of the company name, e.g. 'Palantir Technologies' -> 'palantir'."""
    words = SUFFIX.sub("", name).replace("&", " ").split()
    return (words[0] if words else name).lower().strip(".,")


def fetch(ticker: str, name: str) -> list[dict]:
    q = f'"{SUFFIX.sub("", name).strip()}" {ticker} stock when:{MAX_AGE_DAYS}d'
    r = requests.get(RSS, params={"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"},
                     headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    r.raise_for_status()
    key, seen, out = keyword(name), set(), []
    for it in ET.fromstring(r.text).findall("./channel/item"):
        source = it.findtext("source") or ""
        title = (it.findtext("title") or "").strip()
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3]
        # Relevance filter: headline must mention the company or its ticker as a word.
        if key not in title.lower() and not re.search(rf"\b{re.escape(ticker)}\b", title):
            continue
        if title.lower() in seen:
            continue
        seen.add(title.lower())
        when = parsedate_to_datetime(it.findtext("pubDate")).astimezone(timezone.utc)
        out.append({"title": title, "source": source or "Unknown", "url": it.findtext("link"),
                    "published": when.strftime("%Y-%m-%d"), "published_at": when.isoformat(),
                    "noise": bool(NOISE.search(title))})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="whole universe instead of current ideas")
    args = ap.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    if args.all:
        pairs = conn.execute("SELECT ticker, name FROM universe").fetchall()
    else:
        pairs = conn.execute("SELECT DISTINCT ticker, name FROM recommendations").fetchall()
    if not pairs:
        raise SystemExit("nothing to fetch: run `python -m pipeline.rank` (or ingest for --all) first")
    rec_tickers = {r[0] for r in conn.execute("SELECT DISTINCT ticker FROM recommendations")}

    found = failed = new_rows = 0
    for ticker, name in pairs:
        try:
            items = fetch(ticker, name)
        except Exception as e:  # network/parse problems must not abort the run
            print(f"  {ticker}: failed ({e.__class__.__name__})")
            failed += 1
            continue
        now = datetime.now(timezone.utc).isoformat()
        with conn:
            for n in items:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO news_items (ticker, title, source, url, published_at, first_seen_at, "
                    "last_seen_at, rule_noise) VALUES (?,?,?,?,?,?,?,?)",
                    (ticker, n["title"], n["source"], n["url"], n["published_at"], now, now, int(n["noise"])),
                )
                if cur.rowcount:
                    new_rows += 1
                else:
                    conn.execute("UPDATE news_items SET last_seen_at = ? WHERE ticker = ? AND url = ?",
                                 (now, ticker, n["url"]))
            if ticker in rec_tickers:
                shown = [{k: v for k, v in n.items() if k != "noise"} for n in items if not n["noise"]][:PER_STOCK]
                conn.execute("UPDATE recommendations SET news = ? WHERE ticker = ?", (json.dumps(shown), ticker))
        found += bool(items)
        time.sleep(DELAY_S)
    total = conn.execute("SELECT COUNT(*) FROM news_items").fetchone()[0]
    print(f"news: {found}/{len(pairs)} tickers had headlines, {failed} failed, {new_rows} new rows, {total} archived in total")


if __name__ == "__main__":
    main()
