---
type: Proposal
title: Verification layer (numeric confirmation)
description: Proposal to compare news-sentiment/LLM labels with actual price moves after the news (discussed 2026-10-26, not approved by the user)
tags: [proposal, tbd]
status: draft
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-06T11:00:00Z }
---

**Not a decision** until the user approves it.

**Problem:** the sentiment model and the LLM output labels and text, so we can't tell whether they are right or guessing → we need numbers that explain why a stock goes up or down.

# Proposed approach

- Compare news-sentiment/LLM labels with the **actual price outcome after the news** (1w/1m/3m vs the market) and show "this kind of news happened N times, beat the market Y%" + an uncertainty range
- Optional: estimate volatility (more predictable than direction)
- No third text-reading model · deep learning waits for enough data (~200 news items now is too few)
- The result may be a "weak signal", which must be stated plainly to the user

# Ask first

- Pulling historical news from FMP (a download)
- Using 5/10/15 days instead of 1w/1m/3m (the locked frame is 1w/1m/3m)

# Prohibition

Advisor (Wen Huang, USTC, pure mathematics): the work is off-topic for him; never claim it as a basis of the project.

Related: [Results](/experiments/results.md) · task T11 in [Progress](/project/progress.md)
