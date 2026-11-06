---
type: Architecture
title: System patterns
description: The 8-step pipeline structure and the patterns used in the code
tags: [architecture, pipeline]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-06T11:00:00Z }
sources:
  - id: spec
    resource: PIPELINE_SPEC.md
    title: PIPELINE_SPEC.md (full spec, do not load the whole file unless necessary)
---

**Structure:** FastAPI + SQLite (single module) · Next.js · AI runs separately on Kaggle and is called over HTTPS[^spec]

**Flow:** trigger(1) → scrape(2) → source check(3) → news sentiment(4, local ML, display-only) → LLM(5) → risk/size(6) → trade idea UI(7) → backtest(8) · status of each step: [Progress](/project/progress.md)

# Patterns

- Run as steps: `python -m pipeline.<step>` · `rank` **deletes and rebuilds `recommendations`** → always run news/sentiment/llm after it ([runbook](/runbooks/daily-refresh.md))
- Every decision is reproducible from SQL: `llm_analysis`, `news_scores`, `data_issues`
- Kaggle gateways use a Bearer token, bind to 127.0.0.1, and are exposed through a Cloudflare quick tunnel
- LLM: enforced JSON schema (Ollama `format`) + checks in code (confidence 0..1, cited ids must be in the input, must cite a headline) + one retry · **display-only** (any score adjustment later is ≤ ±10 and only after stage 8 proves it)
- The frontend proxies `/api/*` with Next `rewrites()` (`BACKEND_URL` baked in at build) · if the rewrites are missing, login returns 404
- `app/seed.py` inserts 12 sample rows only when `recommendations` is empty
- Auth: [Auth and security](/architecture/auth-security.md) · scoring: [Scoring](/architecture/scoring.md)

[^spec]: PIPELINE_SPEC.md
