---
type: Runbook
title: Run app and refresh data
description: Start the backend/frontend and run the pipeline steps in order
tags: [ops]
generated: { by: opencode/deepseek-flash, at: 2026-11-13T05:22:32Z }
---

```bash
Backend/.venv/bin/uvicorn app.main:app --port 8000 --app-dir Backend   # restart after code changes
cd frontend && npm run dev                                         # port 3000 · webpack mode
```

Run from `Backend/` in this order:

```bash
.venv/bin/python -m pipeline.ingest   # prices ~90 s
.venv/bin/python -m pipeline.rank     # replaces ALL recommendations
.venv/bin/python -m pipeline.news     # --all = 503 tickers ~9 min
.venv/bin/python -m pipeline.analyze  # Laya: needs LAYA_URL/LAYA_TOKEN
.venv/bin/python -m pipeline.llm      # ~9 s per ticker: needs LLM_URL/LLM_TOKEN
```

- Run news/analyze/llm **after every rank** (`llm_analysis` keeps old rows; the API uses the latest successful row per ticker)
- News only accumulates if `news` runs regularly (Google News keeps ~7 days) · installing a cron job requires **asking the user first**
- The Refresh button in the web app only re-reads the DB; it does not run the pipeline
- Cautions: [Tech context](/architecture/tech-context.md)
