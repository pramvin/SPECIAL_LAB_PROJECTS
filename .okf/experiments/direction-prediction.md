---
type: Experiment Results
title: Direction prediction (retired)
description: Every up/down test on news, chart and indicators; none beat "always up" or the shuffled control, so the user retired it on 2026-11-06
tags: [evaluation, decision]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-06T09:00:00Z }
---

# Decision

Predicting whether a stock goes up or down is **retired** (user, 2026-11-06). The app may claim only the big-move chance badge ([Results](/experiments/results.md) section I, AUC 0.674 on 2023–2026) and stock matching. "Always up" scores 54–57% on these windows, so accuracy near 50% is a failure, not a near miss. Not tried: small stocks, intraday timestamps (4.3% of Benzinga rows), earnings surprise, delisted stocks, RL.

# What was tested

| Test | Result |
|---|---|
| Headline text → 1-week direction, NB/SVM/RF (FNSPID, 20 stocks, test 2019–20) | 50.7–51.7% vs always-up 55.7%, shuffled 51.3% |
| Apple articles → AAPL 5-day direction (train 2021–23, test 2024), tuned, + past prices | accuracy 50.8–56.3% vs 54.5–57.5%; test AUC 0.36–0.53 (price pattern flipped in 2024) |
| Paper replication (tf-idf + SVM/RF/NB) | 91.7% / 86.3% / 84.3% = agreement with the word-count dictionary, not price; vs price Spearman −0.032 |
| Dictionary long-short, 331 Benzinga stocks, 2011–20 | spreads −15 to +3 bps, same as shuffled |
| Chart + news logistic / SVR / ExtraTrees / learned word weights / 7–28 day horizons | direction AUC 0.49–0.52; at most a weak 1-day hint |
| Probability model (chart + news) | direction AUC 0.50–0.52 |
| Zero-shot scorers, 1-day spread 2019-01 to 2020-08 | dictionary +22 bps (t 3.0), FinBERT +38 (t 4.5), Laya +38 (t 3.2); gross, crash window |

# News score x big-move group (2026-11-06, Kaggle CPU, `Backend/experiments/newsxbigmove.py`)

Idea: inside stocks the big-move model ranks in the day's top 20%, does the news score pick the direction? Big-move model retrained before 2019 (pre-test AUC 0.687), SVM (tf-idf, paper style) trained on the dictionary sign, 331 stocks, test 2019-01 to 2020-08, cost 40 bps per pair, pass rule fixed before the run. **Passed 0 of 4.**

| Scorer, horizon | Gross | Net | Net t | Shuffle p |
|---|---|---|---|---|
| SVM, 1 day (primary) | +53.6 bps | +13.6 | 0.66 | 0.010 |
| Dictionary, 1 day | +64.1 | +24.1 | 0.93 | 0.005 |
| SVM / dictionary, 5 days | +18.0 / +38.0 | −22.0 / −2.0 | −0.10 / 0.20 | 0.41 / 0.31 |

A real-looking gross 1-day hint beats shuffling, but daily spreads are noisy (277 days, about 3 names per side), so net t stays far below 2. Crash window, survivors only.

# RSI and MACD fixed rules (2026-11-06, Kaggle CPU, `Backend/experiments/indicator_experts.py`)

RSI(14) below 30 / above 70 and MACD(12,26,9) crosses, no training, decision window 2023-01 to 2026-10, cost 40 bps per pair, 4 cells at p < 0.0125. **Passed 0 of 4**: gross +3.0 / +2.1 bps (RSI 1 / 5 day) and −2.4 / −5.1 (MACD), net −37 to −45. Descriptive 2017–22: RSI gross +9.7 / +24 bps, still negative after cost. Price audit: 503 current S&P 500 tickers, 34 dropped (over 5% missing), 8 stock-days with a move over 50% removed, 1,999 flat-price stock-days removed (almost all AMCR); survivors only.
