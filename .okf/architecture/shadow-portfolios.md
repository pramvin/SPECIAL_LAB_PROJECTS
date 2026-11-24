---
type: Architecture
title: Shadow Top 5 portfolios
description: "Eight recipes for narrowing the ranked list to five stocks, logged daily and scored against SPY, with two random controls (nothing is bought or shown)"
tags: [architecture, evaluation, trading]
status: draft
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-22T00:00:00Z }
---

Built 2026-11-21 (user: "build it"). Answers "which way of picking a Top 5 works" by measurement, since no direction model passed any test ([Direction prediction](/experiments/direction-prediction.md)). **Nothing is bought and nothing is shown to users.** Code `Backend/pipeline/shadow.py`, tests `Backend/tests/test_shadow.py` (15), table `shadow_picks`, run by the hourly job ([Hourly news routine](/architecture/news-routine.md)) and idempotent.

# Recipes (horizon 1w, all start from the rule score in `recommendations`)

| Recipe | Picks 5 stocks by |
|---|---|
| `rules` | top rule score, at most 2 per sector (the current method) |
| `calm` | from the top 30, the smallest daily range (ATR %) |
| `bigmove` | from the top 30, the highest big-move chance (skipped if fewer than 5 have one) |
| `no_earnings` | like `rules`, skipping stocks that report within 5 days ([Market context data](/architecture/market-context-data.md)) |
| `volume` | from the top 30, last daily volume vs previous 30-day average |
| `ai_veto` | like `rules`, skipping stocks whose latest stored AI review is Underweight or Sell (no new reviews are written since 2026-11-24, so it equals `rules` from now on) |
| `random_top30`, `random_pool` | random from the top 30 / from everything that passed the filters (controls, seeded by date) |

# Measurement

- Entry = the ranking date's daily close (not a price anyone could trade); return after 1 and 5 trading days from `prices`, minus SPY over the same dates · `--report` prints mean excess return, share beating SPY, and the difference to `rules` per recipe
- Logs only if the ranking is ≤ 4 days old, so it needs `pipeline.ingest` + `pipeline.rank` first · they are not in the hourly job because `rank` replaces all recommendations
- **Decision rule, fixed in advance:** a recipe is a candidate for the real Top 5 only after 40 logged days, and only if its mean 5-day excess return beats `rules` and both random controls; before that the table is counts, not a result

# State

- Plumbing checked on a scratch copy with real Yahoo prices and SPY: logging, idempotence, scoring, report · the one scoring run used picks chosen with hindsight, so its numbers mean nothing
- Neon: ingest and rank were run by hand on 2026-11-21 (user OK) and day 1, the ranking of 2026-11-20, is logged there with earnings data (an earlier log without it was deleted and redone) · no scores yet, the first 1-day returns come after the next trading day
- On 2026-11-21 `rules`, `no_earnings` and `ai_veto` picked the same five (COST DUK TSN ED VLTO) · `ai_veto` now has no fresh flags to use
- Logging stops when the ranking is more than 4 days old, and ingest + rank are not in the hourly job: daily scheduling is the user's decision ([Active context](/project/active-context.md))
- Picks are not independent (same days, same market), so even 40 days is a weak test; a recipe's edge over `rules` is the number to watch, not its raw return
