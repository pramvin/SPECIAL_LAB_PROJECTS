---
type: Runbook
title: Run app and refresh data
description: Start the backend/frontend and run the pipeline steps in order
tags: [ops]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-22T02:00:00Z }
---

```bash
Backend/.venv/bin/uvicorn app.main:app --port 8000 --app-dir Backend   # restart after code changes
cd frontend && npm run dev                                         # port 3000 · webpack mode
```

That backend command reads the local `planwise.db`. To serve what the hourly job and the pipeline write to Neon, use the `backend-neon` config in `.claude/launch.json`, or run from `Backend/`: `.venv/bin/python -c "from agents import config; config.load_env(); import uvicorn; uvicorn.run('app.main:app', port=8000)"` · it also writes accounts, wallet, trades and watchlist to Neon.

Run from `Backend/` in this order:

```bash
.venv/bin/python -m pipeline.ingest   # prices ~90 s
.venv/bin/python -m pipeline.rank     # replaces ALL recommendations
.venv/bin/python -m pipeline.news     # --all = 503 tickers ~9 min
.venv/bin/python -m pipeline.sentiment # local ML labels, no Kaggle ([News sentiment](/architecture/news-sentiment.md))
.venv/bin/python -m pipeline.llm      # ~9 s per ticker: needs LLM_URL/LLM_TOKEN
```

- Run news/sentiment/llm **after every rank** (`llm_analysis` keeps old rows; the API uses the latest successful row per ticker)
- News only accumulates if `news` runs regularly (Yahoo returns only recent headlines) · installing a cron job requires **asking the user first**
- Automatic: `.github/workflows/refresh-news.yml` runs `news` + `sentiment` every 2 hours against Neon (needs secret `DATABASE_URL`; only runs from `main`; GitHub disables it after 60 days without repo activity) · written, not yet run on GitHub
- Local alternative (2026-11-21, user approved): LaunchAgent `com.planwise.collect` runs `pipeline.collect_hourly` hourly (news, sentiment, price reaction, earnings calendar, intraday volume, shadow Top 5 portfolios, AI filter) against Neon while the Mac is awake · stop it with `launchctl bootout gui/$(id -u)/com.planwise.collect` · see [Hourly news routine](/architecture/news-routine.md)
- Manual, a few times a month: `.venv/bin/python -m pipeline.index_changes --check` refreshes the S&P 500 join/leave log and tests which removed stocks still have Yahoo prices ([Market context data](/architecture/market-context-data.md))
- The Refresh button in the web app only re-reads the DB; it does not run the pipeline
- Cautions: [Tech context](/architecture/tech-context.md)
