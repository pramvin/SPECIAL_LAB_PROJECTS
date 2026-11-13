---
type: Experiment Results
title: Laya / FinBERT / LLM experiments
description: Numbers from Kaggle T4 runs on 2026-10-16 to 10-19 (single runs, no CI, no human labels on our own headlines)
tags: [evaluation]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-06T11:00:00Z }
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

# G: Do the scorers predict price? (2026-11-02, Kaggle T4, zero-shot)

Code `Backend/experiments/zeroshot_scorers.py` · Benzinga headlines of 330 stocks, 66,356 headlines / 39,420 unique, trading days 2019-01 to 2020-08 (31,159 stock-days) · each scorer's mean score per stock-day; top 20% minus bottom 20% of the same day, entry = next day's close, no costs · Laya asked ONE question (sentiment), score = P(bullish) − P(bearish) · Laya 38.6 ms per headline (about 25 min for all), FinBERT 145 s

| Scorer | 1-day AUC | 1-day spread | 5-day spread |
|---|---|---|---|
| Dictionary (Hu&Liu + McDonald) | 0.504 | +22 bps (t 3.0) | +19 bps (t 0.5) |
| FinBERT | 0.513 | +38 bps (t 4.5) | +42 bps (t 0.7) |
| Laya | 0.517 | +38 bps (t 3.2) | +76 bps (t 0.9) |
| Shuffled control | 0.501 | +1 bps (t 0.0) | +21 bps (t 0.8) |

Spearman between scores: dictionary–FinBERT 0.47 · dictionary–Laya 0.43 · FinBERT–Laya 0.78 · **Laya ≈ FinBERT at 1 day (equal spread, AUC 0.517 vs 0.513, no test of the difference); both above the dictionary; nothing significant at 5 days** · one window that includes the Mar-2020 crash (the same dictionary gave only +3 bps over 2016–2020 in `longshort_benzinga.py`, so the window may be special) · both models may have seen 2019–20 news in training (look-ahead risk) · gross of costs, daily turnover

# H: Probability model, chart + news (2026-11-02, Kaggle, `Backend/experiments/prob_model.py`)

331 stocks (Benzinga tickers with Yahoo prices, survivors only), 780,360 stock-days, 386,130 headlines scored by FinBERT (2.7 min) · features: 10 chart indicators (1/5/20/60-day return, 5/20-day volatility, distance from 50-day average, RSI, MACD, volume vs 20-day average) + 7 news features (headline count today and 5 days, mean FinBERT score today and 5 days, dictionary score, share negative/positive), all relative to the day's median stock · targets: beat1/beat5 = return above that day's median over 1/5 days from the next close · big5 = |5-day return − day median| in the day's top 20% (base 20%) · logistic / gradient boosting / small NN (32,16; 15 epochs, not fully converged), train 2011–16, calibrate on 2017 (isotonic), test 2018–mid 2020 (219,775 rows)

| Target | Features | Test AUC 2018 / 2019 / 2020 | Brier skill |
|---|---|---|---|
| beat1 (direction vs market, 1 day) | chart | 0.50 / 0.50 / 0.52 | ≈ 0 |
| beat1 | news | 0.50 / 0.50 / 0.50–0.51 | ≈ 0 |
| beat5 | chart+news | 0.50–0.51 / 0.50–0.51 / 0.51 | ≈ 0 |
| big5 (big move) | chart | 0.67–0.69 / 0.72–0.73 / 0.73–0.75 | +0.08 to +0.10 |
| big5 | news only | 0.51 / 0.51–0.52 / 0.51–0.53 | ≈ 0 |
| big5 | chart+news | 0.67–0.69 / 0.72–0.73 / 0.73–0.75 | +0.09 to +0.10 |

**Direction: no usable probability (AUC 0.50–0.52); the NN is no better than logistic; news adds nothing. Big move: a real, stable, well-calibrated signal, but it comes from chart (volatility history), news adds about +0.001 AUC.** Calibration of P(big move), gradient boosting chart+news, ten equal groups (predicted → actual): 0.045→0.054 · 0.082→0.084 · 0.101→0.104 · 0.122→0.124 · 0.149→0.148 · 0.182→0.176 · 0.236→0.214 · 0.292→0.265 · 0.390→0.334 · **0.557→0.494** (top group actual by year 0.503 / 0.537 / 0.462 vs base 0.20; slightly over-confident at the top) · social sentiment not used (no history, see [Data sources](/architecture/data-sources.md)) · the 1-day top-minus-bottom hint of section G does not show up here as AUC (different measurement: all stock-days vs only days with news)

Laya was retired on 2026-11-06 (see [News sentiment](/architecture/news-sentiment.md)); sections A to G are history.

Follow-up: [Verification layer](/project/verification-layer.md)

# I: Big-move model retrained on current S&P 500 (2026-11-03, Kaggle CPU, `Backend/experiments/bigmove_train.py`)

497 current S&P 500 stocks (survivors only), yfinance adjusted prices 2016-06 to 2026-11-02, 1.2M stock-days · target big5 as in section H (base 20%) · 10 chart features relative to the day's median · gradient boosting, train 2017–2021, isotonic calibration on 2022, 14-day gaps, test 2023 to 2026-10 (473,732 rows) · sklearn 1.9.1

| Check | Result |
|---|---|
| Test AUC (2023 / 2024 / 2025 / 2026) | **0.674** (0.646 / 0.672 / 0.668 / 0.714) |
| Baseline: rank by 20-day volatility only | 0.663 |
| Control: trained on shuffled labels | 0.532 |
| Brier skill | +0.071 |
| Top decile predicted → actual | 0.458 → 0.456 (base 0.201) |

The model beats the volatility rule by only ~0.01 AUC: the signal is "volatile stocks stay volatile". Calibration is good across all ten groups (lowest groups slightly over-predict: 0.113 → 0.096). A first run with sklearn 1.6.1 gave the same numbers (AUC 0.6737) and was replaced to match the backend's sklearn. No news features, no direction.
