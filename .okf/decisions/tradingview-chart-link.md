---
type: Decision
title: TradingView chart link on trade ideas
description: The ticker on a Trade Ideas card opens its TradingView chart in a new tab, with no embedded widget and no API key
tags: [decision, ui]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-01T06:40:00Z }
---

Decided 2026-10-31 (Steven, PR #4 merged 2026-11-01)

- The ticker opens a TradingView chart in a new tab via a direct link
- Interval: `1w` → 4H · `1m` → 1D · `3m` → 1D
- **No embedded widget and no API key** (rule: no external data flows the team has not chosen)
- Code: `frontend/src/components/ideas/IdeasView.tsx` (`CHART_INTERVAL`)
- Result: **no chart is rendered inside the card**, only a link · embedding a chart needs fresh user approval

Related: [Team](/project/team.md)
