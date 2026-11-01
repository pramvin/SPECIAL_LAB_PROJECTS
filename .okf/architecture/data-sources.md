---
type: Data Sources
title: Data sources
description: Prices, news, and FMP currently in use, plus sources that are deferred or not used
tags: [architecture, data]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-01T06:40:00Z }
---

| Source | Status | Notes |
|---|---|---|
| yfinance prices | in use | 2 years · the S&P 500 list comes from Wikipedia and is stored in the DB |
| Google News RSS | in use | unofficial, no key · ~7 days · may be rate-limited · run `pipeline.news` manually |
| FMP | partly used | key in `Backend/.env` (`FMP_API_KEY`) works for `quote`, `profile`, `search-symbol`, EOD prices · **402** on `sp500-constituent`, `etf/holdings`, `stock-list`, screener · FMP news not tested yet · `ingest.py` tries FMP first, then falls back to Wikipedia |
| SEC EDGAR | deferred | the user brings it back — **do not start on your own** |
| X/influencer | not used | locked · [Project brief](/project/brief.md) |

- The FMP key was once pasted in chat → the user should create a new one
- News shown in the web app comes from the `news_items` table · the filtering rules are described in `VINCENT.md`
- Pulling historical news from FMP requires asking the user first (a download)
