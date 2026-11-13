---
type: Runbook
title: Start the LLM on Kaggle
description: "Start the LLM gateway on Kaggle: steps, verification, and gotchas (the Laya half of the notebook is retired)"
tags: [ops, kaggle, ai]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-06T11:00:00Z }
---

1. Kaggle (account `faislol`) → Import `Backend/experiments/kaggle_gateways.ipynb` · GPU **T4 x2**, Internet On
2. Run cell 1 (setup) → 2 (write the server files) → 3 (launch, **leave it running**; safe to rerun, it kills the old one and issues a new token)
3. Cell 3 prints `LLM_URL LLM_TOKEN` (plus `LAYA_URL LAYA_TOKEN`, **unused now**: the notebook still has its Laya cells and `laya_server/` was deleted, so clean the notebook before relying on it) → put the LLM values in `Backend/.env`
4. Verify: `curl <url>/health`; a wrong token must return 401; `pipeline.llm --limit 2` = end-to-end
5. When done, **stop the session** (the link lives ≤ ~11 hours)

# Gotchas

- Output sits in an iframe and cannot be read as text; safe ways to move the values: the user copies the 4 lines, or downloads the `.ipynb` and reads it as text · screenshots risk confusing `I`/`l` · **never guess a token**
- Ollama needs `zstd` + `pciutils` (the notebook installs them) · Ollama on GPU 0
- Adding a dataset mid-run resets the session · "Run All" sometimes stops midway, run the remaining cells by hand
- After editing `llm_server/server.py`, regenerate the notebook
- `think=true` uses several times more tokens · the quick tunnel cuts off at ~100 s, see [Results](/experiments/results.md)
