---
type: Data Sources
title: Data sources
description: Prices and news currently in use, plus sources that are deferred or not used
tags: [architecture, data]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-18T05:00:00Z }
---

| Source | Status | Notes |
|---|---|---|
| yfinance prices | in use (decided 2026-11-01: free, no paid feed) | daily closes only, **not real-time and not a 15-min feed** · UI says so · 2 years · the S&P 500 list comes from Wikipedia (no API key) and is stored in the DB |
| Yahoo quotes (`/api/quotes`) | in use, unofficial | latest 1-min bar via yfinance, cached 60 s · UI labels it "delayed, usually about 15 minutes" and shows the real quote time · the 15-min figure is Yahoo's usual delay, **not verified by us** |
| TradingView | link only | the ticker opens tradingview.com (their own live data) · see [TradingView chart link](/decisions/tradingview-chart-link.md) |
| Yahoo Finance news (`yf.Search`, replaced Google News RSS 2026-11-17) | in use | unofficial, no key · recent headlines only (we keep the last 7 days) · tagged with `relatedTickers` · an `&` in the query returns nothing, so it is stripped · `Ticker.get_news()` raised "Yahoo is down" in a test while `Search` worked · run `pipeline.news` manually |
| SEC EDGAR | planned for the agent review (2026-11-17) | company facts API, needs `SEC_EDGAR_USER_AGENT` with a contact email (not given yet) · 200 OK from this machine 2026-11-17 · [AI agent review](/architecture/agent-review.md) |
| StockTwits | used by the agent review's social analyst | returned 403 on 2026-11-17 but worked on 2026-11-18 (posts cited as `social:stocktwits:<id>`) → intermittent, shown as unavailable when blocked |
| X/influencer | not used | |
| Reddit (social sentiment) | planned for the agent review (live display only) · anonymous RSS returned 403 on 2026-11-17, so it needs OAuth app keys `REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET` | the user made a Reddit "script" app (2026-11-02; keys only in the user's hands, never in the repo) · the API lists only ~1,000 recent items per query and the Pushshift archive is restricted to moderators, so it gives **no 2011–2020 history to train on** (community sources, not checked against Reddit's docs) · possible only for live display, or via an archive dump such as a Kaggle r/wallstreetbets dataset (unverified: date range, ticker tagging not included) |

- Paid/realtime feeds (Finnhub, Polygon, exchanges) and OpenStock (AGPL) were considered and not adopted
- FMP: removed 2026-11-22 (its free key returned HTTP 402); the agent review reads fundamentals, quarterly statements and insider activity from Yahoo Finance instead
- News shown in the web app comes from the `news_items` table · the filtering rules are described in `VINCENT.md`
- News history for ML: Yahoo news gives only recent headlines and `news_items` keeps what we collect (the experiment CSV spans only 2026-10-09 to 10-16) · for history the user picked the Kaggle dataset "Financial News and Stock Price Integration Dataset" (Elsabet Yemane Girma, 81 MB) · checked on Kaggle 2026-11-01: **headlines only, no prices**, columns `date, ticker=stock, title=headline`, 1,407,328 rows, 2009 to mid-2020, 6,204 tickers, junk ≤0.4%, 67,280 duplicate ticker+title, mixed date formats (parse with `format="mixed"`, which fixed the lost rows) · source file `raw_analyst_ratings.csv` with Benzinga URLs · it is **not** the full FNSPID paper dataset (1999–2023) · used only on Kaggle via `Backend/experiments/fnspid_explore.py` · prices come from yfinance (Internet ON) · Apple news for the paper replication: Kaggle `frankossai/apple-stock-aapl-historical-financial-news-data` (`apple_news_data.csv`, 29,752 articles with body, dense only from 2020-12; 2019 has 41)
