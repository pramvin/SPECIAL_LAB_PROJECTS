---
type: Active Context
title: Current focus
description: Open problems, pending user decisions, and next steps (the most frequently updated file)
tags: [active]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-01T06:40:00Z }
---

**Focus:** Stage 5 (LLM) has run once on 42/42 stocks → make it trustworthy: fix UI bugs, have the user label data to measure accuracy.

# Git status

- `main` = `716ca86` · PR #1–#4 (Han, Adrian, Vincent, Steven) all merged 2026-11-01 · see [Team](/project/team.md)
- **Log out button** (`LogoutButton.tsx` + edits to Header/MobileTopBar/OnboardingForm) exists only on the user's machine, **not committed**; the user said not to put it in main yet
- Do not commit unless told to

# Open problems

1. `ReasonText` (`IdeasView.tsx`) puts `[1]` on every link; ids not in `cited_news_ids` render as bare numbers
2. Laya labels look wrong on clear cases (good M&A news labeled Bearish) · no ground truth yet
3. LLM leans bullish (up 36 / down 2 / none 6)
4. Laya and the LLM are not connected yet (the LLM reads every headline with `rule_noise=0`)
5. Test account `llmcheck@planwise.test` in the DB must be deleted
6. `npm run dev` is broken: the script is `next dev --turbopack=false`, which Next 16.3.8 rejects → use `npx next dev --webpack` (waiting for the user to approve fixing `package.json`)
7. Per-stock questionnaire: backend only (`sentiment_responses`), no UI, no answers are saved
8. Session tokens are stored unhashed in the DB · see [Auth and security](/architecture/auth-security.md)

# Runtime status

- The Kaggle link from the last run is dead and the values in `Backend/.env` are stale → **stop any lingering session** to save GPU · news has no scores yet (`news_scores` empty → UI shows "not scored yet")

# Waiting on the user

1. Approve source tiers + corroboration rule (Proposal)
2. Approve the Laya criterion: no worse than FinBERT and ~75%+
3. Install a daily scheduled job for `pipeline.news`?
4. Hide the Laya sentiment chip until it is evaluated?
5. Want the per-stock questionnaire back in the UI? (the UI was removed)
6. Commit the Log out button and fix the `dev` script?
7. Email for the SEC User-Agent (when SEC comes back)
8. Numeric confirmation layer: [Verification layer](/project/verification-layer.md)

# Next

T0 (user labels) ∥ T2, T3, fix `ReasonText` → T1 → rerun T5 on filtered news + T6 → T4/T7 when the user asks → T8 · task table: [Progress](/project/progress.md)

Experiments with code already written: `python -m pipeline.llm_ab --arm anon` (done) · `--arm think` (failed, keep think off) · `python -m pipeline.disagree` flags 13/42 stocks where the LLM and Laya disagree · results in [Results](/experiments/results.md)
