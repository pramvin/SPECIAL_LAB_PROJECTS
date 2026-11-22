---
type: Project Brief
title: PlanWise AI brief
description: What the project does, the locked decisions, and the hard rules (source of truth)
tags: [core]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-18T05:00:00Z }
---

**PlanWise AI** is a capstone project: a web app that recommends **short-term S&P 500 stocks, personalized per user**, with reasons and news. Short term first, long term later.

# Locked (do not reopen)

- S&P 500 only · trade ideas are **long-only**; simulated positions support **long and short** · holding periods `1w` `1m` `3m`
- **No AI runs on the user's machine** → remote API, or Kaggle + Cloudflare tunnel ([runbook](/runbooks/kaggle-gateways.md))
- LLM = remote OpenAI-compatible API xAI `https://api.x.ai/v1`, model `grok-4.3` (user, 2026-11-18; replaces `gateway.9arm.co` qwen3.8, too slow, and Ollama `qwen3:8b` on Kaggle) · used by the multi-agent review in [AI agent review](/architecture/agent-review.md)
- Social data (Reddit, StockTwits) and SEC EDGAR are **allowed** for the agent review (user, 2026-11-17) · X is still not used
- Earnings trigger: deferred, the user brings it back — **do not start on your own**
- The user prefers **English** replies · the web UI is in English

# Hard rules

- Never invent numbers, formulas, data sources, or reasons: they must be real or labeled as examples
- *Proposal/TBD* = not approved
- No payments, real trading, or bank connections · no secrets in the frontend
- Show the banner "Not investment advice / not backtested" · never promise returns
- Ask first: downloads, uploads, installs, scheduled jobs, commits
