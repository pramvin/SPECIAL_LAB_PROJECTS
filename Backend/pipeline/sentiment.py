"""Pipeline step 5 (light): score archived headlines with the local ML sentiment model.

The model is a scikit-learn Pipeline (tf-idf + LinearSVC) trained on Kaggle with
experiments/news_sentiment_train.py. It is NOT run on Kaggle at serving time and
needs no gateway. Scores go to the existing `news_scores` table (one row per
headline per model); the LLM (`pipeline.llm`) is separate and unchanged.

`kind` is written as "n/a" and `p_filler` as NULL, because the Laya event/filler
question no longer exists. Scores are display-only.

Run from Backend/ after news:  .venv/bin/python -m pipeline.sentiment [--all] [--limit N]
"""
import argparse
import json
import os
import sqlite3
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(__file__)
DB_PATH = os.environ.get("PLANWISE_DB", os.path.join(HERE, "..", "planwise.db"))
MODEL_PATH = os.path.join(os.path.dirname(HERE), "models", "news_sentiment_model.joblib")
BATCH = 50
PER_STOCK = 3
DEFAULT_NAME = "news_sentiment"

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


def load_bundle(path: str | None = None):
    """Load the model bundle, or stop with a clear message (never score blind)."""
    try:
        import joblib
        import sklearn  # noqa: F401  (the saved pipeline was trained with sklearn)
    except Exception as e:
        raise SystemExit(
            f"scikit-learn/joblib is not installed in this venv ({type(e).__name__}: {e}). "
            "Install Backend/requirements.txt before running pipeline.sentiment."
        )
    p = path or MODEL_PATH
    if not os.path.isfile(p):
        raise SystemExit(
            f"Sentiment model not found: {p}\n"
            "Train it on Kaggle with experiments/news_sentiment_train.py and copy "
            "news_sentiment_model.joblib into Backend/models/."
        )
    try:
        bundle = joblib.load(p)
    except Exception as e:
        raise SystemExit(f"Could not load sentiment model {p}: {type(e).__name__}: {e}")
    if not isinstance(bundle, dict) or "model" not in bundle:
        raise SystemExit(f"{p} is not a sentiment bundle (expected a dict with a 'model' key).")
    return bundle


def softmax(scores) -> np.ndarray:
    """Row-wise softmax of LinearSVC decision values (stable; rows sum to 1)."""
    s = np.asarray(scores, dtype=float)
    s = s - s.max(axis=-1, keepdims=True)
    e = np.exp(s)
    return e / e.sum(axis=-1, keepdims=True)


def score_texts(bundle, texts: list[str]) -> list[dict]:
    """Return one {sentiment, p_bearish, p_bullish, p_neutral} per headline."""
    model = bundle["model"]
    decision = np.asarray(model.decision_function(texts), dtype=float)
    if decision.ndim == 1:  # two-class fallback; the served model has three
        decision = np.column_stack([-decision, decision])
    probs = softmax(decision)
    classes = [str(c) for c in model.classes_]
    out = []
    for row in probs:
        p = dict(zip(classes, row))
        out.append({
            "sentiment": classes[int(np.argmax(row))],
            "p_bearish": float(p.get("bearish", 0.0)),
            "p_bullish": float(p.get("bullish", 0.0)),
            "p_neutral": float(p.get("neutral", 0.0)),
        })
    return out


def pending(conn: sqlite3.Connection, model: str, all_: bool) -> list[tuple]:
    """Headlines with no row yet for this model (newest first)."""
    scope = "" if all_ else "AND n.ticker IN (SELECT DISTINCT ticker FROM recommendations)"
    return conn.execute(
        "SELECT n.id, n.title FROM news_items n "
        "WHERE NOT EXISTS (SELECT 1 FROM news_scores s WHERE s.news_id = n.id AND s.model = ?) "
        f"{scope} ORDER BY n.published_at DESC",
        (model,),
    ).fetchall()


def score_pending(conn: sqlite3.Connection, bundle, all_: bool = False, limit: int | None = None) -> int:
    """Score only headlines that do not have a row for this model yet."""
    model = bundle.get("name") or DEFAULT_NAME
    rows = pending(conn, model, all_)
    if limit:
        rows = rows[:limit]
    print(f"{len(rows)} headlines to score with {model}")
    done = 0
    for i in range(0, len(rows), BATCH):
        chunk = rows[i : i + BATCH]
        scored = score_texts(bundle, [t for _, t in chunk])
        now = datetime.now(timezone.utc).isoformat()
        with conn:
            conn.executemany(
                "INSERT OR REPLACE INTO news_scores VALUES (?,?,?,?,?,?,?,?,?)",
                [(nid, model, r["sentiment"], r["p_bearish"], r["p_bullish"], r["p_neutral"], "n/a", None, now)
                 for (nid, _), r in zip(chunk, scored)],
            )
        done += len(chunk)
        print(f"  scored {done}/{len(rows)}")
    return done


def refresh_cards(conn: sqlite3.Connection, model: str) -> int:
    """Put the newest 3 non-noise headlines on each idea, with sentiment when scored."""
    tickers = [r[0] for r in conn.execute("SELECT DISTINCT ticker FROM recommendations")]
    for t in tickers:
        rows = conn.execute(
            "SELECT n.title, n.source, n.url, n.published_at, s.sentiment, s.p_bearish, s.p_bullish, s.p_neutral "
            "FROM news_items n LEFT JOIN news_scores s ON s.news_id = n.id AND s.model = ? "
            "WHERE n.ticker = ? AND n.rule_noise = 0 ORDER BY n.published_at DESC LIMIT 60",
            (model, t),
        ).fetchall()
        items = []
        for title, source, url, pub, sent, pb, pu, pn in rows:
            item = {"title": title, "source": source, "url": url, "published": pub[:10], "published_at": pub}
            if sent:
                item["sentiment"] = sent
                item["sentiment_conf"] = round({"bearish": pb, "bullish": pu, "neutral": pn}[sent], 3)
            items.append(item)
        with conn:
            conn.execute(
                "UPDATE recommendations SET news = ? WHERE ticker = ?",
                (json.dumps(items[:PER_STOCK]), t),
            )
    return len(tickers)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="score the whole archive, not just current ideas")
    ap.add_argument("--limit", type=int, help="score at most N new headlines (smoke test)")
    args = ap.parse_args()

    bundle = load_bundle()
    model = bundle.get("name") or DEFAULT_NAME
    print(f"model {model} | trained through {bundle.get('trained_through', 'unknown')} | "
          f"sklearn {bundle.get('sklearn_version', 'unknown')}")

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    score_pending(conn, bundle, args.all, args.limit)
    n = refresh_cards(conn, model)
    print(f"cards refreshed for {n} tickers")


if __name__ == "__main__":
    main()
