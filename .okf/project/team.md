---
type: Team Assignments
title: Team split and PR status
description: Who owns which part, what has been merged into main, and the limits that remain
tags: [team]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-01T06:40:00Z }
---

All merged into `main` on 2026-11-01 (each passed API checks + `tsc`/`lint`, but nobody has clicked through every page yet).

| Person | Area | PR | Delivered |
|---|---|---|---|
| Han | login/security | #1 | forgot/reset password, login failure limit, auth log · [Auth and security](/architecture/auth-security.md) |
| Adrian | search + watchlist in DB | #2 | `/watchlist`, `/api/search`, `/api/watchlist`, `watchlist` table |
| Vincent | questionnaire + save answers to DB | #3 | real Google News, status bar, `/api/news-sentiment`, `/api/data-status`, `sentiment_responses` table · **per-stock questionnaire UI was removed** · the 5-question onboarding questionnaire already existed |
| Steven | charts | #4 | ticker links to TradingView · [TradingView chart link](/decisions/tradingview-chart-link.md) |

- PR #1 was closed once without merging, then reopened when its author confirmed it could be merged
- All conflicts were in `Backend/app/main.py` (schema/imports) and `IdeasView.tsx` · resolved by keeping both sides
- Per-person guides: `VINCENT.md`, `AUTH_SECURITY_GUIDE.md`
- A 60–80% win rate is a target that needs a backtest, not a promise
- The S&P 500 list is already in the DB (Wikipedia, prices from yfinance)
