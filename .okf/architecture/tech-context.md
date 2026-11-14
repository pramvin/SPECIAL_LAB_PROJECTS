---
type: Tech Context
title: Tech stack and cautions
description: Stack, ports, and tooling cautions (commands live in runbooks)
tags: [tech]
generated: { by: opencode/deepseek-flash, at: 2026-11-13T17:23:20Z }
---

- **Frontend:** Next.js **v16** (breaking changes: read `frontend/node_modules/next/dist/docs/` before writing code) + React + TS · port 3000 (use `-p 3001` if it clashes with another project)
- **Backend:** Python 3.14, FastAPI, uvicorn, yfinance, pandas, lxml, requests · port 8000 · SQLite `Backend/planwise.db` (git-ignored)
- **AI:** Ollama `qwen3:8b` on Kaggle T4 x2 (LLM) · news sentiment and the big-move model are scikit-learn files that run locally ([News sentiment](/architecture/news-sentiment.md))
- Data: [Data sources](/architecture/data-sources.md) · commands: [Daily refresh](/runbooks/daily-refresh.md), [Kaggle gateways](/runbooks/kaggle-gateways.md)

# Cautions

- **Never install torch/transformers or run LLM/deep models on the user's machine** (scikit-learn joblib models are fine)
- `Backend/.env` is secret: never print its contents · **never guess a token character by character** (blocked as credential guessing)
- `npm run dev` uses `next dev --webpack` (Next 16.3.8 rejects `--turbopack=false`)
- Test against a copy of the DB (`PLANWISE_DB=/path/copy.db`) on a temporary port · the backend has no `--reload` · macOS has no `timeout`
- Do not touch the Kaggle notebook `colony-models-eval` or processes you did not start
- Run `tsc --noEmit` / `npm run lint` / `npm run build` before saying frontend work is done
