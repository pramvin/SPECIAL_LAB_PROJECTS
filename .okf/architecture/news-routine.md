---
type: Architecture
title: Hourly news routine
description: "Scheduled job that archives headlines, scores them, records the price move after each one, and filters which stocks go to an AI review"
tags: [architecture, news, scheduler, ai]
status: draft
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-22T04:00:00Z }
---

Built 2026-11-21 (user: "layer 1", with an AI filter on top). Display-only: nothing here changes a score or a card number. Code in `Backend/pipeline/`: `collect_hourly.py` (wrapper), `reaction.py`, `news_trigger.py` · tests `tests/test_reaction.py`, `tests/test_news_trigger.py` (18).

# Steps (`python -m pipeline.collect_hourly`, in order, a failed step does not stop the next)

1. `news`: Yahoo headlines into `news_items` · scope `auto` = whole S&P 500 in even UTC hours, only current ideas (~170) in odd hours
2. `sentiment`: local ML label ([News sentiment](/architecture/news-sentiment.md))
3. `reaction`: table `news_reaction` = price of the stock and SPY at publication and 1 h / 1 d / 5 d later (5-minute bars, last bar before the time, a slot fills 30 min after it is due; Yahoo keeps only ~60 days of 5-minute bars, so this cannot be rebuilt later) · `--report` prints mean excess return per sentiment label
4. `earnings`, `intraday`, `shadow` (added 2026-11-21): refresh the earnings calendar, snapshot volume of the curated stocks ([Market context data](/architecture/market-context-data.md)), and log/score the shadow Top 5 portfolios ([Shadow Top 5 portfolios](/architecture/shadow-portfolios.md)) · data only
5. `review-served` (added 2026-11-21, only with AI on): quick AI review of every idea the web serves, at most 12 pairs per run, see [AI agent review](/architecture/agent-review.md)
6. `ai-filter`: `news_trigger` judges each new headline once (table `news_triggers`): material = model confident (≥ 0.6) or an event word (earnings, downgrade, lawsuit, FDA, merger...), market-wide wrap-ups ignored · a stock goes to the AI unless reviewed in the last 5 h · at most 8 (stock, horizon) pairs per run · runs `agents.run --mode funnel` (quick call each, full 12-agent review only for flagged ones, at most 2 per horizon)

# Scheduler

- macOS LaunchAgent `~/Library/LaunchAgents/com.planwise.collect.plist`, every 3600 s, log `~/Library/Logs/planwise-collect.log` · runs only while the Mac is awake (started `caffeinate` for 9 h on 2026-11-21) · one run at a time (lock file)
- Writes to Neon (`DATABASE_URL` from `Backend/.env`) and spends LLM credits on the gateway in `AGENT_LLM_*` · set `PLANWISE_DB` to test on SQLite
- Durable alternative: a GitHub Actions workflow, but scheduled workflows run only from `main` and the user declined commit/push on 2026-11-21

# Measured 2026-11-21 on Neon

- First scheduled run (LaunchAgent, scope `all`, Neon): news 823 s, sentiment 143 s, reaction 144 s, AI filter 465 s (3 stocks, 8 quick calls of ~2.7k tokens, 35–240 s each, none escalated) = about 26 min, exit code 0 · an ideas-scope run before the reaction write was batched took 22 min (reaction alone 589 s)

# Limits

- The filter is a guess: ask later whether flagged headlines were followed by bigger moves (`news_triggers` joined with `news_reaction`)
- A headline published while the market is closed shows no move until the next open (`market_open = 0`); 1 d and 5 d are calendar offsets
- The first report (6 stocks, one week) showed positive excess returns for every label: sample too small and clustered, not a result
- Untested: Neon behaviour under a long unattended run
