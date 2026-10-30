"""PlanWise AI backend: auth + 5-question investor profile on SQLite."""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import Cookie, FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from .seed import NEWS_SOURCE, SEED

DB_PATH = os.environ.get("PLANWISE_DB", os.path.join(os.path.dirname(__file__), "..", "planwise.db"))
SESSION_TTL = 7 * 24 * 3600

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS risk_profiles (
  user_id INTEGER PRIMARY KEY REFERENCES users(id),
  horizon TEXT NOT NULL,
  max_loss_pct INTEGER NOT NULL,
  experience TEXT NOT NULL,
  capital TEXT NOT NULL,
  sectors TEXT NOT NULL,
  risk_level TEXT NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sentiment_responses (
  user_id INTEGER NOT NULL REFERENCES users(id),
  ticker TEXT NOT NULL,
  view TEXT NOT NULL,
  confidence TEXT NOT NULL,
  useful TEXT NOT NULL,
  comment TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  PRIMARY KEY (user_id, ticker)
);
CREATE TABLE IF NOT EXISTS recommendations (
  id INTEGER PRIMARY KEY,
  ticker TEXT NOT NULL,
  name TEXT NOT NULL,
  sector TEXT NOT NULL,
  horizon TEXT NOT NULL,
  action TEXT NOT NULL DEFAULT 'BUY',
  entry REAL NOT NULL,
  stop REAL NOT NULL,
  target REAL NOT NULL,
  score INTEGER NOT NULL,
  reasons TEXT NOT NULL,
  news TEXT NOT NULL,
  is_example INTEGER NOT NULL DEFAULT 1,
  generated_at INTEGER NOT NULL,
  as_of TEXT
);
"""


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


with db() as _c:
    _c.executescript(SCHEMA)
    if "as_of" not in {r[1] for r in _c.execute("PRAGMA table_info(recommendations)")}:
        _c.execute("ALTER TABLE recommendations ADD COLUMN as_of TEXT")
    if _c.execute("SELECT COUNT(*) FROM recommendations").fetchone()[0] == 0:
        _c.executemany(
            "INSERT INTO recommendations (ticker, name, sector, horizon, entry, stop, target, score, reasons, news, generated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (t, n, sec, h, e, st, tg, sc, json.dumps(r),
                 json.dumps([{"title": x, "source": NEWS_SOURCE} for x in nw]), int(time.time()))
                for t, n, sec, h, e, st, tg, sc, r, nw in SEED
            ],
        )

app = FastAPI(title="PlanWise AI")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt_hex, digest_hex = stored.split(":")
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
    return hmac.compare_digest(digest.hex(), digest_hex)


class Credentials(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)


class Profile(BaseModel):
    horizon: Literal["1w", "1m", "3m"]
    max_loss_pct: Literal[2, 5, 10]
    experience: Literal["beginner", "some", "experienced"]
    capital: Literal["under_1k", "1k_10k", "over_10k"]
    sectors: list[Literal["tech", "healthcare", "finance", "energy", "consumer", "any"]] = Field(min_length=1)


class SentimentResponse(BaseModel):
    """Per-stock questionnaire answers. User input, not example data."""

    ticker: str = Field(min_length=1, max_length=10)
    view: Literal["positive", "neutral", "negative"]
    confidence: Literal["low", "medium", "high"]
    useful: Literal["yes", "no", "unsure"]
    comment: str = Field(default="", max_length=500)


def risk_level(p: Profile) -> str:
    score = {2: 0, 5: 1, 10: 2}[p.max_loss_pct] + {"beginner": 0, "some": 1, "experienced": 2}[p.experience]
    return "conservative" if score <= 1 else "moderate" if score <= 3 else "aggressive"


def start_session(conn: sqlite3.Connection, response: Response, user_id: int) -> None:
    token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, int(time.time()) + SESSION_TTL),
    )
    response.set_cookie("session", token, max_age=SESSION_TTL, httponly=True, samesite="lax", path="/")


def current_user(conn: sqlite3.Connection, token: str | None) -> sqlite3.Row:
    row = None
    if token:
        row = conn.execute(
            "SELECT u.id, u.email FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token = ? AND s.expires_at > ?",
            (token, int(time.time())),
        ).fetchone()
    if row is None:
        raise HTTPException(401, "Not signed in")
    return row


def profile_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {
        "horizon": row["horizon"],
        "max_loss_pct": row["max_loss_pct"],
        "experience": row["experience"],
        "capital": row["capital"],
        "sectors": row["sectors"].split(","),
        "risk_level": row["risk_level"],
    }


@app.post("/api/auth/register")
def register(body: Credentials, response: Response):
    email = body.email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(422, "Invalid email")
    with db() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                (email, hash_password(body.password), int(time.time())),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Email already registered")
        start_session(conn, response, cur.lastrowid)
    return {"email": email}


@app.post("/api/auth/login")
def login(body: Credentials, response: Response):
    email = body.email.strip().lower()
    with db() as conn:
        row = conn.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,)).fetchone()
        if row is None or not verify_password(body.password, row["password_hash"]):
            raise HTTPException(401, "Wrong email or password")
        start_session(conn, response, row["id"])
    return {"email": email}


@app.post("/api/auth/logout")
def logout(response: Response, session: str | None = Cookie(default=None)):
    if session:
        with db() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (session,))
    response.delete_cookie("session", path="/")
    return {"ok": True}


@app.get("/api/me")
def me(session: str | None = Cookie(default=None)):
    with db() as conn:
        user = current_user(conn, session)
        row = conn.execute("SELECT * FROM risk_profiles WHERE user_id = ?", (user["id"],)).fetchone()
    return {"email": user["email"], "profile": profile_dict(row)}


@app.put("/api/profile")
def save_profile(body: Profile, session: str | None = Cookie(default=None)):
    level = risk_level(body)
    with db() as conn:
        user = current_user(conn, session)
        conn.execute(
            "INSERT INTO risk_profiles (user_id, horizon, max_loss_pct, experience, capital, sectors, risk_level, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET "
            "horizon=excluded.horizon, max_loss_pct=excluded.max_loss_pct, experience=excluded.experience, "
            "capital=excluded.capital, sectors=excluded.sectors, risk_level=excluded.risk_level, updated_at=excluded.updated_at",
            (user["id"], body.horizon, body.max_loss_pct, body.experience, body.capital,
             ",".join(body.sectors), level, int(time.time())),
        )
    return {"risk_level": level}


def sentiment_response_dict(row: sqlite3.Row) -> dict:
    return {
        "ticker": row["ticker"],
        "view": row["view"],
        "confidence": row["confidence"],
        "useful": row["useful"],
        "comment": row["comment"],
        "updated_at": row["updated_at"],
    }


@app.get("/api/sentiment-responses")
def list_sentiment_responses(session: str | None = Cookie(default=None)):
    """All saved per-stock questionnaire answers for the signed-in user."""
    with db() as conn:
        user = current_user(conn, session)
        rows = conn.execute(
            "SELECT ticker, view, confidence, useful, comment, updated_at "
            "FROM sentiment_responses WHERE user_id = ?",
            (user["id"],),
        ).fetchall()
    return {"responses": {r["ticker"]: sentiment_response_dict(r) for r in rows}}


@app.put("/api/sentiment-response")
def save_sentiment_response(
    body: SentimentResponse,
    session: str | None = Cookie(default=None),
):
    """Upsert one user's questionnaire answers for a ticker."""
    ticker = body.ticker.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z.\-]{0,9}", ticker):
        raise HTTPException(422, "Invalid ticker")
    now = int(time.time())
    with db() as conn:
        user = current_user(conn, session)
        conn.execute(
            "INSERT INTO sentiment_responses "
            "(user_id, ticker, view, confidence, useful, comment, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, ticker) DO UPDATE SET "
            "view=excluded.view, confidence=excluded.confidence, useful=excluded.useful, "
            "comment=excluded.comment, updated_at=excluded.updated_at",
            (
                user["id"],
                ticker,
                body.view,
                body.confidence,
                body.useful,
                body.comment.strip(),
                now,
                now,
            ),
        )
        row = conn.execute(
            "SELECT ticker, view, confidence, useful, comment, updated_at "
            "FROM sentiment_responses WHERE user_id = ? AND ticker = ?",
            (user["id"], ticker),
        ).fetchone()
    return sentiment_response_dict(row)


# Max share of capital in one position, by risk level.
POSITION_CAP_PCT = {"conservative": 10, "moderate": 20, "aggressive": 30}


def latest_llm(conn: sqlite3.Connection, tickers: list[str]) -> dict:
    """Newest successful LLM analysis per ticker, with the cited headlines resolved (display-only, unvalidated)."""
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'llm_analysis'").fetchone():
        return {}
    out = {}
    for t in tickers:
        row = conn.execute(
            "SELECT output_json, model, as_of FROM llm_analysis WHERE ticker = ? AND output_json IS NOT NULL "
            "ORDER BY id DESC LIMIT 1", (t,)).fetchone()
        if not row:
            continue
        o = json.loads(row["output_json"])
        ids = o.get("cited_news_ids", [])
        cited = conn.execute(
            f"SELECT id, title, source, url FROM news_items WHERE id IN ({','.join('?' * len(ids))})", ids
        ).fetchall() if ids else []
        out[t] = {
            "direction": o["direction"], "magnitude": o["magnitude"], "confidence": o["confidence"],
            "reasons": o["reasons"], "caveats": o["caveats"], "model": row["model"], "as_of": row["as_of"],
            "cited": [{"id": c["id"], "title": c["title"], "source": c["source"], "url": c["url"]} for c in cited],
        }
    return out


@app.get("/api/recommendations")
def recommendations(horizon: Literal["1w", "1m", "3m"], session: str | None = Cookie(default=None)):
    with db() as conn:
        user = current_user(conn, session)
        prof = conn.execute("SELECT * FROM risk_profiles WHERE user_id = ?", (user["id"],)).fetchone()
        rows = conn.execute(
            "SELECT * FROM recommendations WHERE horizon = ? ORDER BY score DESC", (horizon,)
        ).fetchall()
        llm = latest_llm(conn, [r["ticker"] for r in rows])
    interests = set(prof["sectors"].split(",")) if prof else {"any"}
    out = []
    for r in rows:
        stop_pct = (r["entry"] - r["stop"]) / r["entry"] * 100
        # Position size: capped by risk level, and by the user's per-trade loss budget.
        size = POSITION_CAP_PCT[prof["risk_level"]] if prof else 10
        if prof:
            size = min(size, prof["max_loss_pct"] / stop_pct * 100)
        out.append({
            "ticker": r["ticker"], "name": r["name"], "sector": r["sector"], "horizon": r["horizon"],
            "action": r["action"], "entry": r["entry"], "stop": r["stop"], "target": r["target"],
            "score": r["score"], "reasons": json.loads(r["reasons"]), "news": json.loads(r["news"]),
            "stop_distance_pct": round(stop_pct, 1),
            "upside_pct": round((r["target"] - r["entry"]) / r["entry"] * 100, 1),
            "position_pct": round(size, 1),
            "loss_at_stop_pct": round(size * stop_pct / 100, 2),
            "matches_interest": "any" in interests or r["sector"] in interests,
            "is_example": bool(r["is_example"]),
            "as_of": r["as_of"],
            "llm": llm.get(r["ticker"]),
        })
    out.sort(key=lambda x: (not x["matches_interest"], -x["score"]))
    return {"horizon": horizon, "items": out}


@app.get("/api/top-news")
def top_news(limit: int = 5, session: str | None = Cookie(default=None)):
    """Newest headline per recommended stock, with the stock's last close and 1-day change."""
    with db() as conn:
        current_user(conn, session)
        rows = conn.execute("SELECT ticker, name, news FROM recommendations GROUP BY ticker").fetchall()
        items = []
        for r in rows:
            news = [n for n in json.loads(r["news"]) if n.get("published_at")]
            if not news:
                continue
            n = max(news, key=lambda x: x["published_at"])
            bars = conn.execute(
                "SELECT date, close FROM prices WHERE ticker = ? ORDER BY date DESC LIMIT 2", (r["ticker"],)
            ).fetchall()
            price = change = pct = price_date = None
            if len(bars) == 2:
                price, price_date = bars[0]["close"], bars[0]["date"]
                change = price - bars[1]["close"]
                pct = change / bars[1]["close"] * 100
            items.append({
                "ticker": r["ticker"], "name": r["name"], "title": n["title"], "source": n["source"],
                "url": n.get("url"), "published_at": n["published_at"], "sentiment": n.get("sentiment"),
                "price": price and round(price, 2), "change": change and round(change, 2),
                "change_pct": pct and round(pct, 2), "price_date": price_date,
            })
    items.sort(key=lambda x: x["published_at"], reverse=True)
    return {"items": items[: max(1, min(limit, 20))]}


@app.get("/api/news-sentiment")
def news_sentiment(tickers: str, limit: int = 3):
    """Real Google News headlines per ticker, plus sentiment when scored.

    Sentiment is display-only and never changes the trade score. If the
    `news_scores` table is missing/empty (model not run yet), headlines are
    still returned and `has_sentiment` is false — no synthetic labels.
    """
    limit = max(1, min(limit, 10))
    wanted: list[str] = []
    for raw in tickers.split(","):
        t = raw.strip().upper()
        if re.fullmatch(r"[A-Z][A-Z.\-]{0,9}", t) and t not in wanted:
            wanted.append(t)
    wanted = wanted[:60]
    result: dict[str, dict] = {}
    with db() as conn:
        tables = {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "news_items" not in tables:
            return {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "tickers": {},
            }
        has_scores = "news_scores" in tables
        for t in wanted:
            if has_scores:
                rows = conn.execute(
                    "SELECT n.title, n.source, n.url, n.published_at, "
                    "(SELECT s.sentiment FROM news_scores s WHERE s.news_id = n.id "
                    " ORDER BY s.scored_at DESC LIMIT 1) AS sentiment "
                    "FROM news_items n WHERE n.ticker = ? AND n.rule_noise = 0 "
                    "ORDER BY n.published_at DESC LIMIT ?",
                    (t, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT title, source, url, published_at, NULL AS sentiment "
                    "FROM news_items WHERE ticker = ? AND rule_noise = 0 "
                    "ORDER BY published_at DESC LIMIT ?",
                    (t, limit),
                ).fetchall()
            distribution = None
            if has_scores:
                counts = conn.execute(
                    "SELECT sentiment, COUNT(*) AS n FROM ("
                    "  SELECT (SELECT s.sentiment FROM news_scores s WHERE s.news_id = n.id "
                    "          ORDER BY s.scored_at DESC LIMIT 1) AS sentiment "
                    "  FROM news_items n WHERE n.ticker = ? AND n.rule_noise = 0"
                    ") WHERE sentiment IS NOT NULL GROUP BY sentiment",
                    (t,),
                ).fetchall()
                by = {r["sentiment"]: r["n"] for r in counts}
                scored = sum(by.values())
                if scored:
                    distribution = {
                        "positive": by.get("bullish", 0),
                        "neutral": by.get("neutral", 0),
                        "negative": by.get("bearish", 0),
                        "scored": scored,
                    }
            result[t] = {
                "items": [dict(r) for r in rows],
                "distribution": distribution,
                "has_sentiment": distribution is not None,
            }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tickers": result,
    }


@app.get("/api/data-status")
def data_status():
    """When the trade-idea data was last refreshed.

    `news_updated_at` is the latest time the news pipeline touched a headline;
    `sentiment_updated_at` is the latest scoring run (null until it runs).
    """
    with db() as conn:
        tables = {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        news_count = 0
        news_updated_at = None
        sentiment_updated_at = None
        recommendations_generated_at = None
        if "news_items" in tables:
            row = conn.execute(
                "SELECT COUNT(*) AS n, MAX(last_seen_at) AS updated FROM news_items"
            ).fetchone()
            news_count = row["n"]
            news_updated_at = row["updated"]
        if "news_scores" in tables:
            sentiment_updated_at = conn.execute(
                "SELECT MAX(scored_at) FROM news_scores"
            ).fetchone()[0]
        if "recommendations" in tables:
            generated = conn.execute(
                "SELECT MAX(generated_at) FROM recommendations"
            ).fetchone()[0]
            if generated:
                recommendations_generated_at = datetime.fromtimestamp(
                    generated, timezone.utc
                ).isoformat()
    return {
        "server_time": datetime.now(timezone.utc).isoformat(),
        "news_updated_at": news_updated_at,
        "news_count": news_count,
        "sentiment_updated_at": sentiment_updated_at,
        "recommendations_generated_at": recommendations_generated_at,
    }


# ---------------------------------------------------------------------------
# Demo account (prototype only)
# ---------------------------------------------------------------------------
# Seeded idempotently so the credential documented in the README works on a
# fresh database. All portfolio/goal data remains synthetic example data.
DEMO_EMAIL = "demo@planwise.ai"
DEMO_PASSWORD = "planwise123"


def ensure_demo_user() -> None:
    with db() as conn:
        exists = conn.execute(
            "SELECT 1 FROM users WHERE email = ?", (DEMO_EMAIL,)
        ).fetchone()
        if exists is None:
            conn.execute(
                "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                (DEMO_EMAIL, hash_password(DEMO_PASSWORD), int(time.time())),
            )


ensure_demo_user()
