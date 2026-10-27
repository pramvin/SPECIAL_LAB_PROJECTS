"""A/B tests for step 5. A = what pipeline.llm sends today (rule_noise = 0, newest 15 headlines, thinking off).
Each arm changes ONE thing against A; same prompt and model, temperature 0.

  filter  drop headlines Laya labels `filler` before taking the newest 15
  anon    replace the company name / ticker with [COMPANY] (big gap vs A = the model leans on what it knows about the firm)
  think   turn qwen3 reasoning mode on (slower; needs a gateway built from the current notebook)

Results go to experiments/ab_<arm>.json, NOT to `llm_analysis`, so the cards are untouched. The A result is reused from
experiments/ab_result.json (the first filter run) when it exists, so a new arm costs one pass, not two.
Needs LLM_URL / LLM_TOKEN (Kaggle) unless --dry-run. Without gold labels this shows how much an arm differs from A,
not which one is right.

Run from Backend/:  .venv/bin/python -m pipeline.llm_ab --arm filter|anon|think [--limit N] [--dry-run]
"""
import argparse
import json
import os
import re
import sqlite3
from collections import Counter

import requests

from pipeline.llm import DB_PATH, HERE, MAX_HEADLINES, analyse, load_env

EXP = os.path.join(HERE, "..", "experiments")
BASE = os.path.join(EXP, "ab_result.json")
Q = ("SELECT n.id, n.title, n.source, n.published_at FROM news_items n "
     "LEFT JOIN news_scores s ON s.news_id = n.id WHERE n.ticker = ? AND n.rule_noise = 0 {extra} "
     "ORDER BY n.published_at DESC LIMIT ?")
SUFFIX = re.compile(r"\([^)]*\)|[,.]?\s+(inc|corp|corporation|co|company|companies|plc|ltd|holdings|group)\b\.?", re.I)
GENERIC = {"the", "american", "general", "united", "first", "new", "north", "southern", "international", "national"}


def anonymise(ticker: str, name: str, rows: list[tuple]) -> list[tuple]:
    """Best effort (leaks are possible): swap the ticker, the name, the name without its legal suffix and its first word
    for [COMPANY]. Spaces and hyphens in a name match each other (Brown-Forman / Brown Forman)."""
    short = SUFFIX.sub("", name).strip()
    first = short.split()[0] if len(short.split()) > 1 else ""
    names = sorted({w for w in (name, short, first) if len(w) > 3 and w.lower() not in GENERIC}, key=len, reverse=True)
    parts = [r"[\s\-–]+".join(re.escape(x) for x in re.split(r"[\s\-–]+", w)) + r"(?:['’]s)?" for w in names]
    pat = re.compile(r"(?<![\w])(\$?" + re.escape(ticker) + r"|" + "|".join(parts) + r")(?![\w])", re.I)
    return [(i, pat.sub("[COMPANY]", t), s, p) for i, t, s, p in rows]


def summarise(results: dict) -> str:
    ok = [r for r in results.values() if r["output"]]
    d = Counter(r["output"]["direction"] for r in ok)
    conf = sum(r["output"]["confidence"] for r in ok) / max(len(ok), 1)
    ms = sum(r.get("ms", 0) for r in results.values()) / max(len(results), 1)
    return f"ok {len(ok)}/{len(results)} | up {d['up']} down {d['down']} none {d['none']} | conf {conf:.2f} | {ms / 1000:.1f}s/ticker"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["filter", "anon", "think"], default="filter")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--dry-run", action="store_true", help="show the input difference only; no model call")
    args = ap.parse_args()

    conn = sqlite3.connect(DB_PATH)
    tickers = conn.execute("SELECT DISTINCT ticker, name FROM recommendations ORDER BY ticker").fetchall()
    if args.limit:
        tickers = tickers[: args.limit]

    inputs = {}
    for t, name in tickers:
        a = conn.execute(Q.format(extra=""), (t, MAX_HEADLINES)).fetchall()
        if not a:
            continue
        b = {"filter": lambda: conn.execute(Q.format(extra="AND COALESCE(s.kind, '') != 'filler'"), (t, MAX_HEADLINES)).fetchall(),
             "anon": lambda: anonymise(t, name, a), "think": lambda: a}[args.arm]()
        inputs[t] = (name, a, b)
    same = [t for t, (_, a, b) in inputs.items() if a == b]
    print(f"arm {args.arm}: {len(inputs)} tickers; input identical to A for {len(same)}")
    if args.dry_run:
        if args.arm == "anon":
            t, (_, a, b) = next(iter(inputs.items()))
            print("example:", a[0][1], "->", b[0][1])
        return

    load_env()
    url, token = os.environ.get("LLM_URL"), os.environ.get("LLM_TOKEN")
    if not url or not token:
        raise SystemExit("Set LLM_URL and LLM_TOKEN in Backend/.env")
    requests.get(f"{url.rstrip('/')}/health", timeout=30).raise_for_status()

    cached = json.load(open(BASE))["results"]["A"] if os.path.exists(BASE) else {}
    res = {"A": {}, "B": {}}
    for t, (name, a, b) in inputs.items():
        res["A"][t] = cached.get(t) or analyse(url, token, t, name, a)
        if a == b and args.arm != "think":
            res["B"][t] = res["A"][t]  # identical input at temperature 0: no need to call again
        elif b:
            res["B"][t] = analyse(url, token, t, name, b, think=args.arm == "think")
        else:
            res["B"][t] = {"output": {"direction": "none", "confidence": 0, "cited_news_ids": []}, "note": "no headlines left"}
        o = lambda k: res[k][t]["output"] and res[k][t]["output"]["direction"]
        print(f"{t}: A {o('A')} | {args.arm} {o('B')}")
    json.dump({"arm": args.arm, "inputs": {t: {"A": [r[0] for r in v[1]], "B": [r[0] for r in v[2]]} for t, v in inputs.items()},
               "results": res}, open(os.path.join(EXP, f"ab_{args.arm}.json"), "w"), indent=1)
    print("A:", summarise(res["A"]))
    print(f"{args.arm}:", summarise(res["B"]))
    flips = [t for t in inputs if res["A"][t]["output"] and res["B"][t]["output"]
             and res["A"][t]["output"]["direction"] != res["B"][t]["output"]["direction"]]
    print(f"direction changed for {len(flips)} tickers: {', '.join(flips)}")


if __name__ == "__main__":
    main()
