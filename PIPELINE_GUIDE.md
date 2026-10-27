# PlanWise AI

A personalized short-term stock idea web app for the **S&P 500**. It pulls daily prices and recent news, ranks stocks
with a transparent scoring rule, and uses two AI models to read the news and explain each idea in plain language.

> **Not investment advice.** Scores and weights are unvalidated guesses and have not been backtested.
> No payments, no real trading, no bank connections.

## Scope (locked decisions)

- S&P 500 only, **long only**, holding periods `1w`, `1m`, `3m`
- AI models do **not** run on your computer: they run on **Kaggle** and are reached through a Cloudflare tunnel
- No X/Twitter or influencer data. News comes from Google News RSS
- The AI only **explains**. It never changes the score, entry, stop or target
- Web UI is in English

## How it works

```
S&P 500 list + prices (yfinance)  ->  rank (score, entry, stop, target)  -> recommendations
Google News RSS                   ->  news_items
news_items  -> Laya (Kaggle)      ->  news_scores   (good/bad/neutral, event vs filler)
news_items  -> qwen3:8b (Kaggle)  ->  llm_analysis  (up/down/unclear, reasons, cited headlines)
FastAPI  <-  SQLite (planwise.db)  ->  Next.js idea cards
```

| Step | Command (run from `Backend/`) | What it does |
|---|---|---|
| Prices | `python -m pipeline.ingest` | S&P 500 universe and daily prices, validated rows only |
| Rank | `python -m pipeline.rank` | Scores stocks, sets ATR stop and target. **Replaces all recommendations** |
| News | `python -m pipeline.news` | Google News headlines (about 7 days kept, so run regularly) |
| Laya | `python -m pipeline.analyze` | Tags each headline: sentiment and event vs filler |
| LLM | `python -m pipeline.llm` | Per stock: direction, confidence, reasons, cited headlines |

The AI models:

- **Laya** (`convaiinnovations/laya`): small model that tags headlines. Used to reorder news on the cards
- **qwen3:8b** via Ollama: reads up to 15 headlines per stock and answers in a fixed JSON schema (validated in code)

## Repo layout

```
Backend/    FastAPI app, SQLite DB, pipeline steps, Kaggle server code and notebook
frontend/   Next.js web app
memory-bank/  project notes and decisions (start at memory-bank/index.md)
OVERVIEW.md, PIPELINE_SPEC.md   original project docs
```

## Run the backend

Requires Python 3. From the repo root:

```bash
cd Backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --port 8000
```

- API docs: http://127.0.0.1:8000/docs
- Restart the server after editing backend code
- The SQLite file `Backend/planwise.db` is git-ignored. If `recommendations` is empty, `app/seed.py` inserts 12 sample ideas

## Run the frontend

Requires Node.js and npm. In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 (Next.js uses 3001 if 3000 is busy). The frontend proxies `/api/*` to the backend at
`http://127.0.0.1:8000`. To point it elsewhere, set `BACKEND_URL` **before** `npm run dev` or `npm run build`
(the value is baked in at build time).

## Refresh the data

Run from `Backend/`, in this order:

```bash
.venv/bin/python -m pipeline.ingest     # prices, about 90 s
.venv/bin/python -m pipeline.rank       # rebuilds recommendations
.venv/bin/python -m pipeline.news       # add --all for all 503 stocks, about 9 min
.venv/bin/python -m pipeline.analyze    # Laya, needs the Kaggle gateways (below)
.venv/bin/python -m pipeline.llm        # LLM, needs the Kaggle gateways (below)
```

Always run `news`, `analyze` and `llm` **after** `rank`, because `rank` rebuilds the recommendations.
Google News keeps only about 7 days, so the news archive only grows if `news` is run regularly.

## Use Kaggle for the AI models

Laya and the LLM run in one Kaggle notebook. You need a Kaggle account (phone-verified for GPU and internet).

1. On Kaggle, create a notebook and import `Backend/experiments/kaggle_gateways.ipynb`
2. Settings: **Accelerator = GPU T4 x2**, **Internet = On**
3. Run cell 1 (setup), then cell 2 (writes the server files), then cell 3 and **leave cell 3 running**
   (stopping it closes the links). Cell 3 downloads `qwen3:8b` (about 5 GB) and starts both servers
4. Cell 3 prints four lines. Copy them into `Backend/.env`, replacing the old ones:

   ```
   LLM_URL=https://....trycloudflare.com
   LLM_TOKEN=...
   LAYA_URL=https://....trycloudflare.com
   LAYA_TOKEN=...
   ```

   One random token is shared by both URLs. The URLs change every restart. **Never commit `.env`** or share the notebook output
5. Check that it works:

   ```bash
   curl <LLM_URL>/health      # {"ok":true,"model":"qwen3:8b"}
   curl <LAYA_URL>/health     # {"ok":true,"model":"convaiinnovations/laya"}
   cd Backend && .venv/bin/python -m pipeline.llm --limit 2     # end-to-end test
   ```

6. When you are done, **stop the Kaggle session** to save GPU time. The links live for about 11 hours at most

Tips:

- Re-running cell 3 is safe: it stops the old servers first and prints a new token
- Adding a Kaggle dataset while running resets the session
- If "Run All" stops halfway, run the remaining cells one by one
- After editing `Backend/laya_server/server.py` or `Backend/llm_server/server.py`, the notebook must be regenerated and re-imported
- Never run the models locally. Do not install torch, transformers or laya on your machine

## Experiments

`Backend/pipeline/llm_ab.py` compares how the LLM's answers change when one thing changes (same prompt, temperature 0).
Run from `Backend/` with the gateways up:

```bash
.venv/bin/python -m pipeline.llm_ab --arm filter   # drop headlines Laya tags as filler
.venv/bin/python -m pipeline.llm_ab --arm anon     # hide company name and ticker
.venv/bin/python -m pipeline.disagree              # stocks where Laya and the LLM disagree (no Kaggle needed)
```

First results on 42 stocks: dropping filler or hiding names barely changes the output, and the LLM still says "up"
for about 80% of stocks. There are no human-labeled answers yet, so these results cannot say which version is right.
Details: `memory-bank/experiments/results.md`.

## Status

Done: prices, news, ranking with ATR stop and target, idea cards UI, first LLM and Laya runs.
Not done: source credibility check, event/rumor/filler tagging, hand-labeled evaluation, backtest.
See `memory-bank/progress.md` for the full list.
