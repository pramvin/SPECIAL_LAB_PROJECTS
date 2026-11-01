---
type: Experiment Results
title: Laya / FinBERT / LLM experiments
description: Numbers from Kaggle T4 runs on 2026-10-16 to 10-19 (single runs, no CI, no human labels on our own headlines)
tags: [evaluation]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-01T06:40:00Z }
---

# A: Public dataset

`zeroshot/twitter-financial-news-sentiment`, 2,388 rows

| Model | Acc | Macro F1 |
|---|---|---|
| FinBERT | 0.725 | 0.668 |
| Laya English | 0.796 | 0.736 |
| Laya typed-decisions | 0.767 | 0.731 |

Speeds are not comparable (batch vs loop) · Laya leans neutral, FinBERT errs the opposite way

# B: Our headlines

1,000 of 12,801: FinBERT↔Laya **agree** 74.1% = agreement, **not accuracy** · Laya calls 138 of 924 unflagged headlines filler; agrees with the rule on 17 of 76 flagged ones (we don't know who is right)

# C: LLM `qwen3:8b`, temp 0, 42 tickers

All JSON valid · 8.8 s per ticker · up 36 / down 2 / none 6 · high confidence (0.7–0.75) · accuracy not checked

# D: A/B drop filler (10-18)

Code `pipeline/llm_ab.py`, raw output `Backend/experiments/ab_result.json` · A = same news as before, B = drop headlines Laya tags `filler` before picking 15 · A: up 34 / down 2 / none 6 · B: up 33 / down 3 / none 6 · direction changed for 2 stocks · **dropping filler barely changes the result; the bullish bias remains**

# E: A/B anon (company name hidden, 10-18)

A up 34 / down 2 / none 6 · anon up 33 / down 2 / none 7 · direction changed for 5 stocks · the company name is not the cause of the bullish bias · raw output `Backend/experiments/ab_anon.json`

# F: think mode (qwen3 reasoning) failed

The Cloudflare quick tunnel cuts at ~100 s (HTTP 524); ACN took 251 s and failed · **decision: keep `think=False` (the user agreed)** · to retry, send fewer headlines or build a streaming gateway

# Proposed criterion (not approved by the user)

On the 200 labeled rows, Laya should be no worse than FinBERT and reach ~75%+, otherwise fine-tune (`github.com/NandhaKishorM/laya`, `notebooks/laya_finetune_typed_decisions_2xT4_kaggle.ipynb`) · Laya probabilities are **not calibrated**

Follow-up: [Verification layer](/project/verification-layer.md)
