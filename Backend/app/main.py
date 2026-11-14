"""PlanWise AI backend: auth + 5-question investor profile on SQLite."""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
import json
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Literal
from urllib.parse import quote

from fastapi import Request

from fastapi import Cookie, FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from . import matching
from .seed import NEWS_SOURCE, SEED
from .watchlist import build_router as build_watchlist_router
from .wallet import build_router as build_wallet_router
from .trading import build_router as build_trading_router

DB_PATH = os.environ.get("PLANWISE_DB", os.path.join(os.path.dirname(__file__), "..", "planwise.db"))
SESSION_TTL = 7 * 24 * 3600
RESET_TTL = 30 * 60
LOGIN_WINDOW = 15 * 60
MAX_LOGIN_FAILURES = 5

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
CREATE TABLE IF NOT EXISTS password_reset_tokens (
  token_hash TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  expires_at INTEGER NOT NULL,
  used_at INTEGER
);
CREATE TABLE IF NOT EXISTS auth_events (
  id INTEGER PRIMARY KEY,
  user_id INTEGER,
  email TEXT NOT NULL,
  event_type TEXT NOT NULL,
  ip_address TEXT,
  created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS login_failures (
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL,
  ip_address TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_login_failures_lookup ON login_failures(email, ip_address, created_at);
CREATE INDEX IF NOT EXISTS idx_auth_events_created_at ON auth_events(created_at);
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
CREATE TABLE IF NOT EXISTS watchlist (
    user_id INTEGER NOT NULL REFERENCES users(id),
    ticker TEXT NOT NULL,
    name TEXT NOT NULL,
    added_at INTEGER NOT NULL,
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
  as_of TEXT,
  atr_pct REAL,
  in_top INTEGER NOT NULL DEFAULT 1,
  bigmove_p REAL
);
"""


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


with db() as _c:
    _c.executescript(SCHEMA)
    _rec_cols = {r[1] for r in _c.execute("PRAGMA table_info(recommendations)")}
    if "as_of" not in _rec_cols:
        _c.execute("ALTER TABLE recommendations ADD COLUMN as_of TEXT")
    if "atr_pct" not in _rec_cols:
        _c.execute("ALTER TABLE recommendations ADD COLUMN atr_pct REAL")
    if "in_top" not in _rec_cols:
        _c.execute("ALTER TABLE recommendations ADD COLUMN in_top INTEGER NOT NULL DEFAULT 1")
    if "bigmove_p" not in _rec_cols:
        _c.execute("ALTER TABLE recommendations ADD COLUMN bigmove_p REAL")
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
    sectors: list[Literal[
        "tech", "communication", "healthcare", "finance", "energy", "consumer_discretionary",
        "consumer_staples", "industrials", "materials", "real_estate", "utilities", "any",
    ]] = Field(min_length=1)


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


def record_auth_event(conn: sqlite3.Connection, email: str, event_type: str,
                      ip_address: str | None = None, user_id: int | None = None) -> None:
    """Save a small audit record; never store passwords or reset tokens here."""
    conn.execute(
        "INSERT INTO auth_events (user_id, email, event_type, ip_address, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, email[:254], event_type, ip_address, int(time.time())),
    )


def login_is_limited(conn: sqlite3.Connection, email: str, ip_address: str) -> bool:
    cutoff = int(time.time()) - LOGIN_WINDOW
    count = conn.execute(
        "SELECT COUNT(*) FROM login_failures WHERE email = ? AND ip_address = ? AND created_at > ?",
        (email, ip_address, cutoff),
    ).fetchone()[0]
    return count >= MAX_LOGIN_FAILURES


def record_login_failure(conn: sqlite3.Connection, email: str, ip_address: str) -> None:
    now = int(time.time())
    conn.execute("DELETE FROM login_failures WHERE created_at < ?", (now - LOGIN_WINDOW,))
    conn.execute(
        "INSERT INTO login_failures (email, ip_address, created_at) VALUES (?, ?, ?)",
        (email[:254], ip_address, now),
    )


def start_session(conn: sqlite3.Connection, response: Response, user_id: int) -> None:
    token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, int(time.time()) + SESSION_TTL),
    )
    secure_default = "1" if os.environ.get("APP_ENV", "development").lower() == "production" else "0"
    secure_cookie = os.environ.get("COOKIE_SECURE", secure_default).strip().lower() in {"1", "true", "yes"}
    response.set_cookie(
        "session", token, max_age=SESSION_TTL, httponly=True,
        secure=secure_cookie, samesite="lax", path="/",
    )


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
def register(body: Credentials, request: Request, response: Response):
    email = body.email.strip().lower()
    ip_address = request.client.host if request.client else "unknown"
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(422, "Invalid email")
    with db() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                (email, hash_password(body.password), int(time.time())),
            )
        except sqlite3.IntegrityError:
            record_auth_event(conn, email, "registration_duplicate", ip_address)
            conn.commit()  # Preserve the security event even though registration failed.
            raise HTTPException(409, "Email already registered")
        record_auth_event(conn, email, "registration_success", ip_address, cur.lastrowid)
        start_session(conn, response, cur.lastrowid)
    return {"email": email}


@app.post("/api/auth/login")
def login(body: Credentials, request: Request, response: Response):
    email = body.email.strip().lower()
    ip_address = request.client.host if request.client else "unknown"
    with db() as conn:
        if login_is_limited(conn, email, ip_address):
            record_auth_event(conn, email, "login_rate_limited", ip_address)
            conn.commit()
            raise HTTPException(429, "Too many sign-in attempts. Please wait 15 minutes and try again.")
        row = conn.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,)).fetchone()
        # Keep the same message for unknown emails and incorrect passwords.
        if row is None or not verify_password(body.password, row["password_hash"]):
            record_login_failure(conn, email, ip_address)
            record_auth_event(conn, email, "login_failed", ip_address, row["id"] if row else None)
            conn.commit()  # Failed attempts must still be saved before returning the error.
            raise HTTPException(401, "Wrong email or password")
        conn.execute("DELETE FROM login_failures WHERE email = ? AND ip_address = ?", (email, ip_address))
        record_auth_event(conn, email, "login_success", ip_address, row["id"])
        start_session(conn, response, row["id"])
    return {"email": email}


class ForgotPasswordRequest(BaseModel):
    email: str = Field(max_length=254)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=32, max_length=200)
    new_password: str = Field(min_length=8, max_length=128)


def send_reset_email(email: str, reset_url: str) -> None:
    """Send via SMTP when configured; otherwise print the link for local development only."""
    host = os.environ.get("SMTP_HOST")
    if not host:
        if os.environ.get("APP_ENV", "development").lower() == "production":
            raise RuntimeError("SMTP_HOST must be configured in production")
        print(f"[PlanWise development password reset] {email}: {reset_url}")
        return

    message = EmailMessage()
    message["Subject"] = "Reset your PlanWise AI password"
    message["From"] = os.environ.get("SMTP_FROM", os.environ.get("SMTP_USER", "no-reply@localhost"))
    message["To"] = email
    message.set_content(
        "We received a request to reset your PlanWise AI password.\n\n"
        f"Open this one-time link within 30 minutes: {reset_url}\n\n"
        "If you did not request this, you can ignore this email."
    )
    port = int(os.environ.get("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=10) as server:
        server.starttls()
        username = os.environ.get("SMTP_USER")
        password = os.environ.get("SMTP_PASSWORD")
        if username and password:
            server.login(username, password)
        server.send_message(message)


@app.post("/api/auth/forgot-password")
def forgot_password(body: ForgotPasswordRequest, request: Request):
    email = body.email.strip().lower()
    ip_address = request.client.host if request.client else "unknown"
    # Return the same response whether the account exists or not, to reduce account enumeration.
    generic_response = {"message": "If an account exists for that email, password reset instructions will be sent."}
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return generic_response

    with db() as conn:
        cutoff = int(time.time()) - LOGIN_WINDOW
        reset_request_count = conn.execute(
            "SELECT COUNT(*) FROM auth_events WHERE ip_address = ? AND event_type = 'password_reset_requested' AND created_at > ?",
            (ip_address, cutoff),
        ).fetchone()[0]
        if reset_request_count >= MAX_LOGIN_FAILURES:
            record_auth_event(conn, email, "password_reset_rate_limited", ip_address)
            return generic_response
        row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        record_auth_event(conn, email, "password_reset_requested", ip_address, row["id"] if row else None)
        if row is None:
            return generic_response
        now = int(time.time())
        conn.execute("UPDATE password_reset_tokens SET used_at = ? WHERE user_id = ? AND used_at IS NULL", (now, row["id"]))
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        conn.execute(
            "INSERT INTO password_reset_tokens (token_hash, user_id, expires_at, used_at) VALUES (?, ?, ?, NULL)",
            (token_hash, row["id"], now + RESET_TTL),
        )

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
    reset_url = f"{frontend_url}/reset-password?token={quote(raw_token)}"
    try:
        send_reset_email(email, reset_url)
    except Exception:
        # Do not expose email-service errors or reset tokens to the requester.
        with db() as conn:
            conn.execute("UPDATE password_reset_tokens SET used_at = ? WHERE token_hash = ?", (int(time.time()), token_hash))
            record_auth_event(conn, email, "password_reset_delivery_failed", ip_address, row["id"])
        raise HTTPException(503, "Password reset email is temporarily unavailable. Please try again later.")
    return generic_response


@app.post("/api/auth/reset-password")
def reset_password(body: ResetPasswordRequest, request: Request, response: Response):
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    now = int(time.time())
    ip_address = request.client.host if request.client else "unknown"
    with db() as conn:
        row = conn.execute(
            "SELECT t.user_id, u.email FROM password_reset_tokens t JOIN users u ON u.id = t.user_id "
            "WHERE t.token_hash = ? AND t.expires_at > ? AND t.used_at IS NULL",
            (token_hash, now),
        ).fetchone()
        if row is None:
            raise HTTPException(400, "This password reset link is invalid or has expired. Request a new one.")
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(body.new_password), row["user_id"]))
        conn.execute("UPDATE password_reset_tokens SET used_at = ? WHERE token_hash = ?", (now, token_hash))
        # Revoke every existing session after a password change.
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (row["user_id"],))
        conn.execute("DELETE FROM login_failures WHERE email = ?", (row["email"],))
        record_auth_event(conn, row["email"], "password_reset_success", ip_address, row["user_id"])
    response.delete_cookie("session", path="/")
    return {"message": "Password updated. Please sign in with your new password."}


@app.get("/api/auth/security-events")
def security_events(session: str | None = Cookie(default=None)):
    """Return only the signed-in user's recent authentication events."""
    with db() as conn:
        user = current_user(conn, session)
        rows = conn.execute(
            "SELECT event_type, created_at FROM auth_events WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
            (user["id"],),
        ).fetchall()
    return {"events": [{"type": r["event_type"], "created_at": r["created_at"]} for r in rows]}


@app.post("/api/auth/logout")
def logout(response: Response, session: str | None = Cookie(default=None)):
    if session:
        with db() as conn:
            row = conn.execute("SELECT u.id, u.email FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ?", (session,)).fetchone()
            conn.execute("DELETE FROM sessions WHERE token = ?", (session,))
            if row:
                record_auth_event(conn, row["email"], "logout", user_id=row["id"])
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
TOP_N_SERVED = 20  # ideas shown per horizon


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
    interests = prof["sectors"].split(",") if prof else ["any"]
    # Personalized: rank every stock that passed the filters by score + fit to the user's answers.
    # No profile yet: serve the curated list (in_top) by plain score.
    cands = [dict(r) for r in rows]
    if prof:
        ranked = matching.rank_for_user(cands, interests, prof["risk_level"], TOP_N_SERVED)
    else:
        ranked = [{**c, "fit": None, "match_reasons": []} for c in cands if c["in_top"]][:TOP_N_SERVED]
    with db() as conn:
        llm = latest_llm(conn, [c["ticker"] for c in ranked])
    out = []
    for r in ranked:  # each item is a recommendations row (dict) plus fit / match_reasons
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
            "matches_interest": matching.matches_interest(r["sector"], interests),
            "fit": r["fit"], "match_reasons": r["match_reasons"],
            "is_example": bool(r["is_example"]),
            "as_of": r["as_of"],
            "bigmove_p": (round(float(r["bigmove_p"]), 4)
                          if horizon == "1w" and r["bigmove_p"] is not None else None),
            "llm": llm.get(r["ticker"]),
        })
    return {"horizon": horizon, "items": out}


_quote_cache: dict[str, tuple[float, dict]] = {}


@app.get("/api/quotes")
def quotes(tickers: str, session: str | None = Cookie(default=None)):
    """Latest 1-minute bar per ticker from Yahoo Finance (unofficial feed, usually ~15 min delayed).

    `quote_time` is the real timestamp of that bar, so the UI can show how old the price is.
    Cached 60 s per ticker set.
    """
    with db() as conn:
        current_user(conn, session)
    wanted: list[str] = []
    for raw in tickers.split(","):
        t = raw.strip().upper()
        if re.fullmatch(r"[A-Z][A-Z.\-]{0,9}", t) and t not in wanted:
            wanted.append(t)
    wanted = wanted[:30]
    if not wanted:
        return {"quotes": {}}
    key = ",".join(sorted(wanted))
    hit = _quote_cache.get(key)
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    import yfinance as yf
    try:
        raw = yf.download([t.replace(".", "-") for t in wanted], period="1d", interval="1m",
                          group_by="ticker", progress=False, auto_adjust=True, threads=True)
    except Exception:
        raise HTTPException(502, "Quote provider unavailable")
    out: dict[str, dict] = {}
    for t in wanted:
        sym = t.replace(".", "-")
        try:
            df = (raw[sym] if len(wanted) > 1 else raw).dropna(how="all")
        except KeyError:
            continue
        if not df.empty:
            out[t] = {"price": round(float(df["Close"].iloc[-1]), 2), "quote_time": df.index[-1].isoformat()}
    result = {"quotes": out, "source": "Yahoo Finance"}
    _quote_cache.clear()
    _quote_cache[key] = (time.time(), result)
    return result


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

app.include_router(build_watchlist_router(db, current_user))
app.include_router(build_wallet_router(db, current_user))
app.include_router(build_trading_router(db, current_user))

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
