# Agent B — API + home-page UI

Read first: [SPEC.md](SPEC.md) (rules, DDL, contract), [example_review.json](example_review.json), `Backend/app/main.py` (see `latest_llm` and `/api/recommendations` around line 520–590), `frontend/AGENTS.md` (Next.js version has breaking changes: read the docs it points to before writing code), `frontend/src/lib/recommendations.ts`, `frontend/src/components/ideas/IdeasView.tsx`, `frontend/src/components/ui/*`.
Only edit: `Backend/app/agents_api.py` (new), `Backend/app/main.py` (2 edits below), `Backend/tests/test_agents_api.py` (new), `frontend/**`. Agent A builds the engine in parallel; do not import from `Backend/agents/` — copy the DDL from SPEC into your test fixture only.

## Backend

1. `app/agents_api.py`: `router = APIRouter()` (same pattern as `app/watchlist.py`).
   - `latest_ai(conn, tickers, horizon) -> dict[ticker, ai]` for the recommendations list (SPEC shape). Return `{}` if `agent_runs` does not exist (use the existing `table_names` helper). Statuses `ok`/`partial` only.
   - `GET /api/agents/{ticker}?horizon=1w`: session required (reuse `current_user` the way other routers do), ticker upper-cased and checked against `^[A-Z.\-]{1,10}$`, 404 when no run. Build `AgentReview` from `agent_runs.final_json` + `sources_json`; collect every evidence id cited anywhere in `review`, resolve into `evidence[]`:
     - `news:<id>` → `news_items` title/source/url/published_at + latest `news_scores.sentiment`
     - `rule:<i>` → `recommendations.reasons[i]` for (ticker, horizon)
     - `metric:`/`fund:`/`sec:`/`social:`/`macro:` → look up `final_json.evidence_index[id]` (`{label, value?, url?, published_at?}`, written by Agent A).
     - Ids found nowhere are dropped, never invented. Do not return `evidence_index` itself in the response.
     - `agent:<role>` → label = role name; `memory:<id>` → that decision's date + rating.
   - `track_record`: up to 5 newest `agent_decisions` for the ticker.
2. `main.py`: (a) `app.include_router(agents_api.router)` next to the other routers; (b) in `/api/recommendations` add `"ai": ai.get(r["ticker"])` with `ai = agents_api.latest_ai(conn, tickers, horizon)` beside the `latest_llm` call. Nothing else in `main.py`.
3. `tests/test_agents_api.py`: temp SQLite (`PLANWISE_DB`), create the SPEC tables, insert one run whose `final_json` is the `review` from `example_review.json`; test: list has `ai` with correct `agrees`; detail endpoint shape matches the contract keys; 404 without run; 401 without session; unknown evidence ids are dropped; table missing → `ai: null`, no crash. Follow the login/session setup used in existing tests (e.g. `tests/test_wallet.py`).

## Frontend

1. `lib/recommendations.ts`: add `Rating`, `AiSummary`, `AgentReview` types exactly as SPEC; `ai: AiSummary | null` on `Recommendation`.
2. Card header (`IdeasView.tsx`, currently `<ProvenanceBadge provenance="ai" label="Rule-based" />`): if `r.ai` → badge `AI · {rating}` (Buy/Overweight green, Hold amber, Underweight/Sell red, REVIEW gray), tooltip "AI opinion · not backtested". Else keep "Rule-based".
3. Expanded "Why this stock and the news" → new client component `components/ideas/AgentPanel.tsx`, fetches `/api/agents/{ticker}?horizon=…` **only when first opened** (same-origin; Next rewrites proxy it), loading skeleton, error state. If 404 or `r.ai` is null: show today's Reasons + News exactly as now, plus a line "AI review pending".
   - **Verdict box** on top: rating, summary with evidence chips, `agrees` → green "Agrees with the rules" / amber "Caution" / red "Disagrees with the rules — the idea is still shown" / gray "Needs review"; small "AI opinion · not backtested · not investment advice".
   - **Tabs** (accessible: `role="tablist"`, arrow keys, horizontal scroll on mobile):
     1. *Summary* — "From the rules" = current reasons list (unchanged); "AI key points" = `key_risks` + manager rationale.
     2. *Analysts* — 4 small cards (market/news/fundamentals/social): signal pill, summary, points, data gaps; `null` analyst → "Not available"; source status from `sources` (e.g. "Social: unavailable — StockTwits blocked").
     3. *Bull vs Bear* — two columns (stack on mobile), then the research manager lean + rationale.
     4. *Trade plan & risk* — table: rows Entry/Stop/Target, columns "Rules (used)" vs "AI suggestion"; `null` → "—". Trader stance + rationale; 3 risk views with suggested position %; a note that the card's numbers come from the rules.
     5. *News & social* — evidence of kind news/social with sentiment badge (`SentimentBadge`), date, link (new tab, `rel="noopener noreferrer"`).
     6. *Track record* — past ratings, return vs SPY, alpha, reflection; empty → "No settled reviews yet (settles after 5 trading days)".
   - **Footer**: model · prompt version · reviewed at (local time) · "Not investment advice".
4. **Evidence chips**: render `[1] [2]` numbered per panel in first-seen order; each chip links/tooltips to the resolved `evidence` item; ids missing from `evidence` render nothing (this also fixes the open bug where `ReasonText` shows bare `[1]` numbers — apply the same rule there: only ids in `cited` get a chip, numbering by position in `cited`).
5. Style: existing tokens in `globals.css`, `tabular-nums` on numbers, `ProvenanceBadge` "ai" on AI figures; no new dependencies; no secrets; works at 375 px width.
6. While Agent A is not done, you may develop against `example_review.json`, but the shipped code must only show it when `process.env.NODE_ENV === "development"` AND the URL has `?demoAgents=1`, always with an "Example data" badge.

Finish with: `npm run build`, `npm run lint`, `npx tsc --noEmit` pass; backend `python -m unittest tests.test_agents_api -v` passes. Report anything you could not verify.
