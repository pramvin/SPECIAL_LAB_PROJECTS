---
type: Data Sources
title: Data sources
description: Prices, news, and FMP currently in use, plus sources that are deferred or not used
tags: [architecture, data]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-02T15:00:00Z }
---

| Source | Status | Notes |
|---|---|---|
| yfinance prices | in use (decided 2026-11-01: free, no paid feed) | daily closes only, **not real-time and not a 15-min feed** · UI says so · 2 years · the S&P 500 list comes from Wikipedia and is stored in the DB |
| Yahoo quotes (`/api/quotes`) | in use, unofficial | latest 1-min bar via yfinance, cached 60 s · UI labels it "delayed, usually about 15 minutes" and shows the real quote time · the 15-min figure is Yahoo's usual delay, **not verified by us** |
| TradingView | link only | the ticker opens tradingview.com (their own live data) · see [TradingView chart link](/decisions/tradingview-chart-link.md) |
| Google News RSS | in use | unofficial, no key · ~7 days · may be rate-limited · run `pipeline.news` manually |
| FMP | partly used | key in `Backend/.env` (`FMP_API_KEY`) works for `quote`, `profile`, `search-symbol`, EOD prices · **402** on `sp500-constituent`, `etf/holdings`, `stock-list`, screener · **news is not available on this plan** (tested 2026-11-01: `stable/news/stock` 402, legacy `v3/stock_news` 403, so no historical news from FMP) · `ingest.py` tries FMP first, then falls back to Wikipedia |
| SEC EDGAR | deferred | the user brings it back — **do not start on your own** |
| X/influencer | not used | locked · [Project brief](/project/brief.md) |
| Reddit (social sentiment) | idea, not used yet | the user made a Reddit "script" app (2026-11-02; keys only in the user's hands, never in the repo) · the API lists only ~1,000 recent items per query and the Pushshift archive is restricted to moderators, so it gives **no 2011–2020 history to train on** (community sources, not checked against Reddit's docs) · possible only for live display, or via an archive dump such as a Kaggle r/wallstreetbets dataset (unverified: date range, ticker tagging not included) |

- Paid/realtime feeds (Finnhub, Polygon, exchanges) and OpenStock (AGPL) were considered and not adopted
- The FMP key was once pasted in chat → the user should create a new one
- News shown in the web app comes from the `news_items` table · the filtering rules are described in `VINCENT.md`
- News history for ML: Google News RSS gives ~7 days and `news_items` keeps what we collect (the experiment CSV spans only 2026-10-09 to 10-16) · for history the user picked the Kaggle dataset "Financial News and Stock Price Integration Dataset" (Elsabet Yemane Girma, 81 MB) · checked on Kaggle 2026-11-01: **headlines only, no prices**, columns `date, ticker=stock, title=headline`, 1,407,328 rows, 2009 to mid-2020, 6,204 tickers, junk ≤0.4%, 67,280 duplicate ticker+title, mixed date formats (parse with `format="mixed"`, which fixed the lost rows) · source file `raw_analyst_ratings.csv` with Benzinga URLs · it is **not** the full FNSPID paper dataset (1999–2023) · used only on Kaggle via `Backend/experiments/fnspid_explore.py` · prices come from yfinance (Internet ON) · Apple news for the paper replication: Kaggle `frankossai/apple-stock-aapl-historical-financial-news-data` (`apple_news_data.csv`, 29,752 articles with body, dense only from 2020-12; 2019 has 41) · paid FMP plan still needs the user's approval
