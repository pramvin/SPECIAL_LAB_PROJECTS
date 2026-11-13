# PlanWise backend

FastAPI + SQLite (`planwise.db`, git-ignored). Auth via httpOnly `session` cookie.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --port 8000
```

Endpoints: `POST /api/auth/{register,login,logout}`, `GET /api/me`, `PUT /api/profile`.
The frontend proxies `/api/*` to `BACKEND_URL` (default `http://127.0.0.1:8000`).

## Wallet and simulated trading

Each user starts with a simulated **$1,000** wallet. Tables are created at
startup by `app/wallet.py` and `app/trading.py`; both follow the same
`SCHEMA` + `APIRouter` pattern as `app/watchlist.py`.

Wallet:

| Method | Path | Notes |
|---|---|---|
| GET | `/api/wallet` | balance + change from $1,000 |
| POST | `/api/wallet/deposit` | `{ "amount": 100, "note": "optional" }` |
| POST | `/api/wallet/withdraw` | fails with 409 if balance is insufficient |
| GET | `/api/wallet/transactions` | deposit/withdraw log |
| GET | `/api/wallet/history` | balance snapshots for the chart |

Trading:

| Method | Path | Notes |
|---|---|---|
| GET | `/api/positions` | open positions + unrealized P/L |
| POST | `/api/positions` | `{ "ticker": "AAPL", "side": "long", "amount": 500, "leverage": 2 }` |
| POST | `/api/positions/{id}/close` | close at the latest `prices` close |
| GET | `/api/trades` | closed-trade history |

Rules:

- `amount` is cash margin deducted from the wallet.
- `notional = amount × leverage`; `quantity = notional ÷ entry_price`.
- Leverage is 1–10, default 1.
- Long P/L = `(exit − entry) × quantity`; short P/L = `(entry − exit) × quantity`.
- `pnl_pct = pnl ÷ amount_deducted × 100`.
- A leveraged loss may make the wallet balance negative.

Tests (no real DB touched):

```bash
.venv/bin/python -m unittest tests.test_wallet tests.test_trading -v
```

For HTTP testing, copy the DB first:
```bash
cp planwise.db /tmp/planwise-wallet-test.db
PLANWISE_DB=/tmp/planwise-wallet-test.db .venv/bin/uvicorn app.main:app --port 8010
```

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

## News sentiment (local ML model)

`models/news_sentiment_model.joblib` is trained on Kaggle
(`experiments/news_sentiment_train.py`) and copied here. It scores headlines with
tf-idf + LinearSVC and writes to the same `news_scores` table.

```bash
.venv/bin/python -m pipeline.sentiment            # new headlines for current ideas
.venv/bin/python -m pipeline.sentiment --all      # whole archive
.venv/bin/python -m pipeline.sentiment --limit 20 # smoke test
```

If the model file or scikit-learn is missing, the command says so and exits;
it never guesses labels.

## Kaggle gateway (LLM)

1. Import `experiments/kaggle_gateways.ipynb` into Kaggle (GPU T4 x2, Internet On). Run cell 1, cell 2, then cell 3 and leave cell 3 running.
2. Cell 3 prints `LLM_URL` and `LLM_TOKEN` (it may also print unused extra lines). Replace the old values in `Backend/.env`.
3. `.venv/bin/python -m pipeline.llm [--limit N]` (LLM analysis, display-only, logged in `llm_analysis`).
4. Stop the Kaggle session when finished. Re-running cell 3 after an interrupt stops the old servers first.
