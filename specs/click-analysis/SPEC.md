# Click analysis: shared spec (read this first)

Product change (user, 2026-11-24). The home page has **no AI agents**: it shows only ML (rule score + big-move chance) and news.
When a user **clicks a stock** (1 week tab only for now), the backend runs **three analysts in one pass**, stores the result in the DB, and the stock detail page shows it after a short loading state. The old 12-agent review, the quick review, and the hourly review job are **deleted**.

Three agents work in parallel on three git branches. Each owns a disjoint set of files (see its AGENT_*.md). Nobody edits another agent's files. The contract below is what makes the pieces fit.

## Rules for every agent

- Work only inside your own git worktree (your current directory). Commit to your branch with small commits. **Never push, never touch `main`, never run `git checkout` to another branch.**
- Never read or write `Backend/.env`, never use Neon or any `DATABASE_URL`. Tests use `PLANWISE_DB=<temp sqlite file>` and `FakeLLM` / injected fetchers. **No test may call the network or a real LLM.**
- Backend Python: use `/Users/fais/Desktop/SPECIAL_LAB_PROJECTS/Backend/.venv/bin/python` run from your worktree's `Backend/` folder. Tests: `python -m unittest <module>`. Use `app.dbcompat.connect()` and portable SQL with `?` placeholders (the same code runs on SQLite and Postgres).
- Do not invent numbers or data. Every figure shown to a user comes from the DB or a real source. Labels written by a model are guesses and may be wrong: say so in the UI.
- Do not `DROP` any table (Neon has data). Just stop creating or using old tables.
- Delete the old code you replace (user's instruction). Do not leave dead files, dead imports, or commented-out code.
- When done, write a short `HANDOFF.md` at your worktree root (what changed, what was deleted, what you did not finish, how you tested). Do not commit `HANDOFF.md`.
- Replies and code comments in English. Keep files short and readable.

## Data flow

1. Home page: `GET /api/recommendations?horizon=1w` (ML only, each card carries its 3 newest headlines with a sentiment label) and `GET /api/latest-news` (newest headlines with price and % change).
2. News must be fresh: Yahoo headlines are pulled **on demand** by `pipeline/news_live.py` (see Agent B), not only by the hourly job.
3. Click on a stock → frontend opens `/stock/{ticker}?h=1w` and calls `POST /api/analysis/{ticker}?horizon=1w`.
4. Backend: refresh that ticker's Yahoo news → run market, news, social analysts **in parallel** (3 LLM calls) → store in table `stock_analysis` → `GET /api/analysis/{ticker}?horizon=1w` returns it. The frontend polls GET every 3 s until `status` is not `running`.

## Table `stock_analysis` (Agent A creates it, in `agents/schema.py`)

```sql
CREATE TABLE IF NOT EXISTS stock_analysis (
  id INTEGER PRIMARY KEY,            -- use the same autoincrement style as agent_runs in the old schema
  ticker TEXT NOT NULL,
  horizon TEXT NOT NULL,
  status TEXT NOT NULL,              -- running | ok | partial | error
  result_json TEXT,                  -- the `result` object below, JSON
  error TEXT,
  model TEXT,
  tokens INTEGER,
  started_at TEXT NOT NULL,          -- UTC ISO
  finished_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_stock_analysis_t ON stock_analysis (ticker, horizon, started_at);
```

Reuse rule: a finished run (ok or partial) is reused for 30 minutes **and only if no non-noise headline for that ticker has `published_at` later than the run's `started_at`**. Otherwise a click starts a new run. At most one `running` row per (ticker, horizon); a second click while running returns that row.

## API contract (Agent A builds `app/analysis_api.py`; Agent C consumes it)

Both endpoints need a logged-in user (use `current_user`, same as the other routers) and a valid ticker (`^[A-Z][A-Z.\-]{0,9}$`, must exist in `recommendations` or `universe`, else 404). Only `horizon=1w` is supported now; `1m` and `3m` return HTTP 422 with `detail: "horizon not supported yet"`.

`POST /api/analysis/{ticker}?horizon=1w` → starts (or reuses) a run, returns the same body as GET. Never blocks on the LLM: the run goes to a background thread.
`GET /api/analysis/{ticker}?horizon=1w` → latest row for (ticker, horizon), or 404 `{"detail": "no analysis"}`.

```json
{
  "ticker": "DIS",
  "horizon": "1w",
  "status": "running | ok | partial | error",
  "cached": false,
  "started_at": "2026-11-24T10:00:00+00:00",
  "finished_at": "2026-11-24T10:01:20+00:00",
  "error": null,
  "result": {
    "chart": {
      "summary": "2 to 3 plain sentences",
      "support": [{"price": 146.2, "why": "short"}],
      "resistance": [{"price": 155.0, "why": "short"}],
      "momentum": {"label": "improving | flat | weakening", "why": "short"},
      "volume": {"label": "above_average | normal | below_average", "why": "short"},
      "status": "ok | unavailable", "reason": null
    },
    "news": {
      "direction": "positive | neutral | negative | mixed",
      "positive_share": 0.62,
      "counts": {"positive": 11, "neutral": 5, "negative": 2},
      "summary": "2 to 3 plain sentences about this week's news",
      "items": [{"title": "", "source": "", "url": "", "published_at": "", "sentiment": "positive | neutral | negative | null"}],
      "status": "ok | unavailable", "reason": null
    },
    "social": {
      "direction": "positive | neutral | negative | mixed | no_data",
      "summary": "2 to 3 plain sentences",
      "sources": {"stocktwits": {"status": "ok", "count": 20}, "reddit": {"status": "skipped", "count": 0}},
      "items": [{"text": "", "source": "stocktwits | reddit", "sentiment": "positive | neutral | negative | null", "url": null}],
      "status": "ok | unavailable | skipped", "reason": null
    }
  }
}
```

Rules for `result`:
- `news.counts`, `news.positive_share`, `news.items` and each item's `sentiment` come **from code** (the local labels in `news_scores`, headlines of the last 7 days, non-noise), not from the LLM. The LLM writes only `direction` and `summary`. `positive_share = positive / (positive + negative + neutral)`, rounded to 2 decimals, `null` when there are no headlines.
- `chart.support`, `chart.resistance` prices must be real price levels derived from the stored prices; the LLM may only choose among levels the code computed (recent swing lows/highs, SMA50/200, Bollinger bands from `agents/sources.compute_metrics`). The existing number guard (`agents/validate.py`) must still reject invented numbers.
- A role that fails leaves its block with `status: "unavailable"` and a `reason`; run `status` is `partial` when some roles failed, `error` when all failed.
- Social: Reddit anonymous access is blocked (HTTP 403), StockTwits works. Keep the existing `fetch_social` as is. `social.sources` reports each source's status.
- The 3 analyst LLM calls run in parallel threads (the gateway allows 3 concurrent requests per key). A module-level `threading.BoundedSemaphore(3)` limits the total across all users; extra runs wait.

## News contract (Agent B builds `pipeline/news_live.py`; Agent A calls it)

```python
# Backend/pipeline/news_live.py
def refresh_ticker(conn, ticker: str, name: str | None = None) -> dict:
    """Pull Yahoo headlines for one ticker NOW, insert new ones into news_items, label the new ones with the
    local sentiment model (news_scores), refresh recommendations.news for that ticker.
    Returns {"new": int, "scored": int, "status": "ok" | "unavailable", "reason": str | None}.
    Never raises (a network failure returns status "unavailable")."""
def refresh_many(conn, tickers: list[str]) -> dict:   # same, for a list (sleeps a short delay between tickers)
```

Agent A imports it lazily inside the job (`from pipeline import news_live`) and wraps it in try/except; if the import fails, the analysis continues with the news already in the DB.

`GET /api/latest-news?limit=10` (Agent B, in `app/main.py`; login required):

```json
{"items": [{"ticker": "DIS", "name": "Walt Disney", "title": "", "source": "", "url": "", "published_at": "",
            "sentiment": "positive | neutral | negative | null",
            "price": 150.9, "change": 1.5, "change_pct": 1.0, "price_date": "2026-11-20"}],
 "refreshed_at": "2026-11-24T10:00:00+00:00"}
```

Newest first, non-noise, one headline per row (several rows may share a ticker but never the same url), only for tickers the app serves (rows in `recommendations` with `in_top = 1`, horizon 1w). Opening this endpoint starts a **background** refresh (`refresh_many`) of those tickers when the last one is older than 5 minutes (module-level timestamp + lock, never blocks the response). The old `/api/top-news` is removed.

`GET /api/recommendations` (Agent B edits): remove the `ai` field and every use of `agents_api`. Add `sentiment` (`positive|neutral|negative|null`) to each headline in `news` (the 3 newest). Keep everything else.

## Frontend contract (Agent C)

Routes: `/` (home, existing `(app)/page.tsx`) and new `/stock/[ticker]` (query `?h=1w`). Types in `src/lib/` mirror the JSON above. The detail page shows, in this order: header (ticker, name, price, % change, horizon tabs 1 week / 1 month / 3 month where the last two show "Coming soon"), price chart (hand-built SVG, last ~60 daily closes; get them from `GET /api/prices/{ticker}?days=60`, which Agent B builds, see below), latest news (3 to 5 headlines, ticker button is not needed here, source link button, sentiment pill), weekly news gauge (half-circle: red left, green right, needle from `positive_share`), social media sentiment box, chart read box (support, resistance, momentum, volume). Loading state while `status = running`. A banner under news and social says labels are model guesses and can be wrong. Banner "Not investment advice / not backtested" stays.

`GET /api/prices/{ticker}?days=60` (Agent B): `{"ticker": "DIS", "name": "...", "bars": [{"date": "2026-11-20", "close": 150.9, "volume": 123}], "price": 150.9, "change": 1.5, "change_pct": 1.0}` from the `prices` table, oldest first; 404 for an unknown ticker; `days` clamped to 5..250.

## Branches

| Agent | Branch | Owns |
|---|---|---|
| A engine | `feat/click-analysis-engine` | `Backend/agents/**`, `Backend/app/analysis_api.py`, `Backend/app/agents_api.py` (delete), `Backend/pipeline/review_served.py` (delete), tests for those |
| B news | `feat/live-news-api` | `Backend/pipeline/news_live.py`, `Backend/pipeline/collect_hourly.py`, `Backend/pipeline/news_trigger.py` (delete), `Backend/app/main.py`, `Backend/tests/test_news_live.py`, `Backend/tests/test_card_news.py`, `Backend/tests/test_news_trigger.py` (delete) |
| C frontend | `feat/click-analysis-frontend` | `frontend/**` |

`Backend/app/main.py` is edited by **B only**. The orchestrator wires `analysis_api.router` into `main.py` at merge time, so A must not touch `main.py` (A's router is `router` in `app/analysis_api.py`, and uses a local import `from .main import current_user, db` like the old `agents_api.py` did).
