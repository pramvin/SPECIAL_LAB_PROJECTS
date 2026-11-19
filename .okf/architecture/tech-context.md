---
type: Tech Context
title: Tech stack and cautions
description: Stack, ports, and tooling cautions (commands live in runbooks)
tags: [tech]
generated: { by: claude-code/claude-opus-5-5, at: 2026-11-17T21:00:00Z }
---

- **Frontend:** Next.js **v16** (breaking changes: read `frontend/node_modules/next/dist/docs/` before writing code) + React + TS · port 3000 (use `-p 3001` if it clashes with another project)
- **Backend:** Python 3.14, FastAPI, uvicorn, yfinance, pandas, lxml, requests · port 8000 · SQLite `Backend/planwise.db` (git-ignored) locally, Postgres (Neon) when `DATABASE_URL` is set · `Backend/app/dbcompat.py` picks the engine (`PLANWISE_DB` always forces SQLite) · write SQL in the portable subset (`?`, `ON CONFLICT`, `RETURNING id`)
- **AI:** agent review LLM = remote OpenAI-compatible API (`AGENT_LLM_*` in `.env`, [AI agent review](/architecture/agent-review.md)) · the older stage-5 `pipeline/llm.py` still expects Ollama on Kaggle · news sentiment and the big-move model are scikit-learn files that run locally ([News sentiment](/architecture/news-sentiment.md))
- Data: [Data sources](/architecture/data-sources.md) · commands: [Daily refresh](/runbooks/daily-refresh.md), [Kaggle gateways](/runbooks/kaggle-gateways.md)

# Cautions

- **Never install torch/transformers or run LLM/deep models on the user's machine** (scikit-learn joblib models are fine)
- `Backend/.env` is secret: never print its contents · **never guess a token character by character** (blocked as credential guessing)
- `npm run dev` uses `next dev --webpack` (Next 16.3.8 rejects `--turbopack=false`)
- Render free disk is wiped on sleep/redeploy, so the deployed backend needs `DATABASE_URL` (Neon) · Postgres path verified on 2026-11-17 against `postgres:17` in Docker and against Neon (register, login, reset password, logout) · not yet checked on Render itself · fill Neon with `DATABASE_URL=… python -m pipeline.migrate_to_postgres` (copies market tables from the local `planwise.db`, leaves users alone, safe to re-run) · `.env` has an unquoted `&` in `DATABASE_URL`, so do not `source` it: use `export DATABASE_URL="$(grep '^DATABASE_URL=' .env | cut -d= -f2-)"`
- Test against a copy of the DB (`PLANWISE_DB=/path/copy.db`) on a temporary port · the backend has no `--reload` · macOS has no `timeout`
- Do not touch the Kaggle notebook `colony-models-eval` or processes you did not start
- Run `tsc --noEmit` / `npm run lint` / `npm run build` before saying frontend work is done
