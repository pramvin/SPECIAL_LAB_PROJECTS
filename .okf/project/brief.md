---
type: Project Brief
title: PlanWise AI brief
description: What the project does, the locked decisions, and the hard rules (source of truth)
tags: [core]
generated: { by: opencode/deepseek-flash, at: 2026-11-13T17:37:52Z }
---

**PlanWise AI** is a capstone project: a web app that recommends **short-term S&P 500 stocks, personalized per user**, with reasons and news. Short term first, long term later.

# Locked (do not reopen)

- S&P 500 only · trade ideas are **long-only**; simulated positions support **long and short** · holding periods `1w` `1m` `3m`
- **No AI runs on the user's machine** → Kaggle + Cloudflare tunnel ([runbook](/runbooks/kaggle-gateways.md))
- LLM = Ollama `qwen3:8b` on Kaggle
- **No X/influencer data**
- SEC EDGAR + earnings trigger: deferred, the user will bring them back themselves — **do not start on your own**
- The user prefers **English** replies · the web UI is in English

# Hard rules

- Never invent numbers, formulas, data sources, or reasons: they must be real or labeled as examples
- *Proposal/TBD* = not approved
- No payments, real trading, or bank connections · no secrets in the frontend
- Show the banner "Not investment advice / not backtested" · never promise returns
- Ask first: downloads, uploads, installs, scheduled jobs, commits
