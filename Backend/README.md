# PlanWise backend

FastAPI + SQLite (`planwise.db`, git-ignored). Auth via httpOnly `session` cookie.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --port 8000
```

Endpoints: `POST /api/auth/{register,login,logout}`, `GET /api/me`, `PUT /api/profile`.
The frontend proxies `/api/*` to `BACKEND_URL` (default `http://127.0.0.1:8000`).

## Data pipeline (steps 1–3)

```bash
.venv/bin/python -m pipeline.ingest            # full S&P 500, 2y daily bars (~90s)
.venv/bin/python -m pipeline.ingest --limit 10 # quick test
```

Writes `universe`, `prices` (validated rows only) and `data_issues` (every rejected/suspect row).
Re-running is safe: prices upsert on `(ticker, date)`.

## News archive

```bash
.venv/bin/python -m pipeline.news         # headlines for current ideas (~20s)
.venv/bin/python -m pipeline.news --all   # whole S&P 500 (~9 min)
```

Appends to `news_items` (unique per ticker+url, `first_seen_at` = when we first fetched it).
Google News RSS keeps only ~7 days, so the archive only grows if this runs regularly, e.g. cron:
`0 * * * * cd /path/to/Backend && .venv/bin/python -m pipeline.news >> news.log 2>&1`

## Kaggle gateways (Laya + LLM, one notebook)

1. Import `experiments/kaggle_gateways.ipynb` into Kaggle (GPU T4 x2, Internet On). Run cell 1, cell 2, then cell 3 and leave cell 3 running.
2. Cell 3 prints four lines (`LLM_URL`, `LLM_TOKEN`, `LAYA_URL`, `LAYA_TOKEN`; one token, two URLs). Replace the old ones in `Backend/.env`.
3. `.venv/bin/python -m pipeline.llm [--limit N]` (LLM analysis, display-only, logged in `llm_analysis`) and `.venv/bin/python -m pipeline.analyze` (Laya).
4. Stop the Kaggle session when finished. Re-running cell 3 after an interrupt stops the old servers first.
