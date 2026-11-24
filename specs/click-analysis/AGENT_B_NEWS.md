# Agent B: live news, home feed, API cleanup (backend)

Read first: `specs/click-analysis/SPEC.md` (contract, rules). Then read: `Backend/pipeline/news.py` (`fetch`, the insert loop in `main`), `Backend/pipeline/sentiment.py` (`load_bundle`, `score_texts`, `score_pending`, `refresh_cards`), `Backend/pipeline/collect_hourly.py`, `Backend/pipeline/news_trigger.py`, `Backend/app/main.py` (`recommendations`, `latest_headlines`, `top_news`, `news_sentiment`, quotes), `Backend/tests/test_card_news.py`, `Backend/tests/test_news_trigger.py`.

Branch: `feat/live-news-api`. You own `Backend/pipeline/news_live.py`, `Backend/pipeline/collect_hourly.py`, `Backend/pipeline/news_trigger.py` (delete), `Backend/app/main.py`, and tests listed below. Do **not** touch `Backend/agents/**`, `Backend/app/analysis_api.py`, or `frontend/**`.

## Build

1. `pipeline/news_live.py`: `refresh_ticker` and `refresh_many` exactly as in SPEC. Reuse `news.fetch` and the same insert/`ON CONFLICT DO NOTHING` logic as `news.main` (extract a shared helper in `news.py` rather than copying: both the CLI and `news_live` call it). Label only the **new** rows with the local sentiment model (`sentiment.load_bundle` is loaded once per process and cached; if the model file is missing, skip labeling and report `scored: 0`). Then update `recommendations.news` for that ticker like `news.main` does. A Yahoo failure returns `status: "unavailable"`, never raises. Keep a small per-ticker memo so the same ticker is not fetched twice within 60 seconds.
2. `GET /api/latest-news` in `main.py` per SPEC (price and change from the `prices` table: last close vs previous close; sentiment from `news_scores` latest label per news id). Background refresh: module-level `_last_news_refresh` timestamp and a lock; start a daemon thread running `refresh_many` over the served tickers when older than 300 s. Remove `GET /api/top-news` and its frontend-only helpers.
3. `GET /api/prices/{ticker}?days=60` per SPEC.
4. `GET /api/recommendations`: remove `ai` and the `agents_api` import and `include_router`; add `sentiment` to each of the 3 headlines in `news` (batch the lookup, no query per headline). Do not remove the stop/target fields yet (the frontend ignores them).
5. Hourly job: `collect_hourly.py` drops the `review-served` and `ai-filter` steps (and any code only they used). The news, sentiment, reaction, earnings, intraday, and shadow steps stay.

## Delete

`pipeline/news_trigger.py`, `tests/test_news_trigger.py`, `/api/top-news`, and any now-unused import or helper in `main.py`. The `news_triggers` table stays in the DB (no `DROP`), just stop creating or reading it.

## Tests (no network)

`tests/test_news_live.py`: new headlines inserted and labeled, duplicates ignored, Yahoo failure → `unavailable`, per-ticker memo. Extend `tests/test_card_news.py` for the sentiment on card headlines. Tests for `/api/latest-news` (order, one row per url, only served tickers, price change, background refresh not blocking: inject a fake `refresh_many`) and `/api/prices/{ticker}` (clamping, 404). Run `python -m unittest discover -s tests` at the end; failures caused only by Agent A's files (`test_analysis*`, `agents/*`) go in HANDOFF.md, everything else you fix.
