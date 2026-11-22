---
type: Architecture
title: Market context data
description: "Three collectors for later filters: earnings calendar, intraday volume snapshots, and S&P 500 membership changes (data only, not used in any score yet)"
tags: [architecture, data, trading]
status: draft
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-22T00:00:00Z }
---

Built 2026-11-21 (user chose these three first, for the move toward short-term trading). **Data only: nothing here changes a score, a rank or a card.** Code in `Backend/pipeline/`, tests in `Backend/tests/` (21 across the three), all Yahoo or Wikipedia, no new keys. Earnings data feeds the `no_earnings` recipe of [Shadow Top 5 portfolios](/architecture/shadow-portfolios.md).

| Collector | Table | What it stores | Runs |
|---|---|---|---|
| `earnings.py` | `earnings_events`, `earnings_fetch` | per stock: next and last ~12 report days, EPS estimate, reported EPS, surprise % | hourly job, only tickers older than 20 h |
| `intraday.py` | `intraday_snapshot` | per curated stock (`in_top = 1`): `rvol`, gap vs previous close, move since open | hourly job, writes only while the US market is open |
| `index_changes.py` | `index_changes` | S&P 500 joins and leaves since 1976 with reason, and `price_ok` | manual, `--check` tests Yahoo prices |

# Rules

- `rvol` = volume so far today ÷ average volume at the same clock time over up to 20 earlier sessions (needs ≥ 10; half-day and cut-off sessions are skipped); regular hours only, Yahoo delayed ~15 min, last bar may be incomplete
- `event_date` is the New York calendar day; Yahoo's time of day is a placeholder, so before/after the open is not known
- `price_ok` = Yahoo has bars from ≥ 1 year before the removal and within 30 days of it (rejects symbols reused by a newer company)

# Measured 2026-11-21 (scratch copy of the DB, real Yahoo and Wikipedia)

- Earnings: 333 tickers in about 3 min with 4 threads, 8,277 events · only 1 of 44 curated stocks reports within 7 days (SJM, 2026-11-24)
- Intraday: market closed (Saturday), so nothing written, by design · `rvol` was checked on Friday's bars (AAPL 1.7, NVDA 2.5 with −11.6% since open, KDP 0.6), **not yet seen on a live session**
- Index changes: 414 rows · **230 removals since 2016, only 93 (40%) have usable Yahoo prices** (bought-out or bankrupt names are mostly gone), so a survivor-free test can recover under half of the missing stocks · see [Results](/experiments/results.md) for the survivor caveat

# Limits

- Nothing validated: whether earnings proximity, `rvol` or membership churn helps picking is untested
- The shadow `volume` recipe uses daily volume from `prices`, not the intraday snapshots: a snapshot taken after the ranking date's close would leak that day's move into the return · using `rvol` needs an intraday entry price (not built)
- On Neon the earnings tables exist and hold 215 tickers (filled by hand 2026-11-21, 5,314 events); the intraday and index tables are created later by the hourly job and by hand · scheduling details in [Hourly news routine](/architecture/news-routine.md)
