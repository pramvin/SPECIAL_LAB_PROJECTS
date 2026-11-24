# Agent C: new home page and stock detail page (frontend)

Read first: `specs/click-analysis/SPEC.md` (contract, rules), `frontend/AGENTS.md` (**this Next.js has breaking changes: read the relevant guide in `frontend/node_modules/next/dist/docs/` before writing routes or fetching code**), `.okf/decisions/apple-inspired-ui.md`. Then read the current code: `src/app/(app)/page.tsx`, `src/components/ideas/IdeasView.tsx`, `CardActions.tsx`, `TopNews.tsx`, `SentimentBadge.tsx`, `src/lib/recommendations.ts`, `src/lib/session.ts`, `src/components/ui/LineChart.tsx`, `ProvenanceBadge.tsx`, `src/app/globals.css`.

Branch: `feat/click-analysis-frontend`. You own everything under `frontend/`. Do not touch `Backend/`.

The backend endpoints do not exist in your branch yet (other agents build them at the same time). Code against the contract in SPEC.md. Do not add mock data to the app: if an endpoint fails, show a plain error state. For your own typecheck use the types only.

## Home page (`/`)

- Replace the "Top news" box with **Latest news** (`GET /api/latest-news`): rows with headline, source and time ago, a sentiment pill (Positive / Negative / Neutral; no pill when `null`), current price and % change (green/red, `tabular-nums`), a **ticker button** (links to `/stock/{ticker}?h=1w`) and a **source button** (opens `url` in a new tab with `rel="noopener noreferrer"`). Refetch every 60 s on the client without a full reload.
- "Ideas for 1 week" cards (the existing Top 5 per horizon; keep the horizon switch): rank number, ticker (link to the detail page, `?h=<horizon>`), name, big-move badge (exists), Buy / Sell buttons (reuse the existing `CardActions` paper-trade actions), and the 3 newest headlines each with a sentiment pill. **Remove** every AI element from the card: `AgentPanel`, `AiVerdict`, `AiRatingBadge`, "AI pending", More info, stop/target/position text.
- Keep: header, balance pill, watchlist star, the "Not investment advice / not backtested" banner, data status.

## Stock detail page (`/stock/[ticker]`, `?h=1w`)

Order: header (ticker, name, price, % change; tabs 1 week / 1 month / 3 month, where 1 month and 3 month are visibly "Coming soon" and not clickable; back link to home) → price chart (hand-built SVG from `GET /api/prices/{ticker}?days=60`) → **Latest news** (3 to 5 newest headlines from the analysis `news.items`, source button, sentiment pill) → **This week's news** (half-circle gauge: red left, green right, needle at `news.positive_share`; the counts and `news.summary` under it; gauge shows "No headlines" when `positive_share` is null) → **Social media** (direction, summary, source status chips, items) → **Chart read** (support, resistance, momentum, volume, summary).

Behaviour: on mount, `POST /api/analysis/{ticker}?horizon=1w`, then poll `GET` every 3 s until `status` is not `running` (stop after 5 minutes with a clear message; stop on unmount). While running, show a skeleton and the line "Analyzing this week's news, chart and social posts. This takes a minute or two." Each block handles `status: unavailable | skipped` with its `reason` in plain words. A `partial` run shows what exists. An `error` run shows the message and a "Try again" button (POST again). `1m` or `3m` in the URL shows the Coming soon state with no request.
Under the news and social blocks add one line: "Labels come from a model and can be wrong." Use `ProvenanceBadge` (kind `ai`) on the analysis blocks.

## Delete

`components/ideas/AgentPanel.tsx`, `AiVerdict.tsx`, `AiRatingBadge.tsx`, `TopNews.tsx` (replaced), `lib/agent-example.json`, and in `lib/recommendations.ts` every type and function only they used (`AgentReview`, `AiSummary`, `Rating`, `getTopNews`, ...). Remove `ai` from `Recommendation`; add `sentiment` to the headline type.

## Finish

`npx tsc --noEmit`, `npm run lint`, and `npm run build` must pass (in your worktree `frontend/node_modules` is a symlink to the main checkout's; do not run `npm install`). Fix what you break. Keep files under ~300 lines: split the detail page into small components under `src/components/stock/` (`StockHeader`, `PriceChart`, `NewsGauge`, `NewsList`, `SocialBox`, `ChartRead`, ...).
