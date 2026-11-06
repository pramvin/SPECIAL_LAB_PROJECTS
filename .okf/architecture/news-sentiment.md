---
type: Architecture
title: News sentiment (local ML)
description: How headlines get a Positive / Neutral / Negative label, what it was trained on, and its limits
tags: [architecture, news, ml]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-06T11:00:00Z }
---

**Replaces Laya (retired 2026-11-06).** Display-only: the label never changes a stock's score.

# Flow

1. `pipeline.news` stores Google News headlines in `news_items` ([Data sources](/architecture/data-sources.md))
2. `pipeline.sentiment` scores headlines that have no row yet with `Backend/models/news_sentiment_model.joblib` and writes `news_scores` (`kind = "n/a"`, `p_filler` NULL; probabilities are a softmax of the SVM margins, not calibrated), then refreshes the 3 headlines on each card
3. `/api/news-sentiment` (labels `bullish` / `neutral` / `bearish`) feeds the card's News column and the "News mood" bar; the panel is hidden when a ticker has no scored headline

The model runs on the user's machine with scikit-learn only (about 1.8 MB, milliseconds per headline); no GPU, no gateway, no Kaggle at serving time. Run: `.venv/bin/python -m pipeline.sentiment [--all] [--limit N]`.

# Model

- tf-idf (unigrams, English stop words, no stemmer) + LinearSVC, 3 classes · code `Backend/experiments/news_sentiment_train.py` (Kaggle CPU, cells P50–P53) · tests `Backend/tests/test_sentiment.py`
- Trained 2026-11-06 on 793,916 unique Benzinga headlines (2010–2020) up to 2018-12-17 · **labels are the sign of the Hu & Liu + McDonald word score** (neutral = no listed word matched), never checked by humans
- 2018 check: 94.5% agreement with those labels (majority baseline 57.7%); this measures copying the word list, not whether a label is right

# Limits (seen on 530 real Google News headlines)

- 64% Neutral, 23% Positive, 13% Negative
- Misses price words: "Stock Price Down 1.2%", "Slips 1.62%", "Is Up Nearly 57%" came out Neutral
- Trained on 2011–2020 analyst-style headlines, applied to 2026 Google News
- Retraining needs a Kaggle run and a download of the joblib (ask the user first)
