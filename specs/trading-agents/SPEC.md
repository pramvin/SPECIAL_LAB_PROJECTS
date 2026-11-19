# AI trading-agent review — shared spec

Status: approved by the user 2026-11-17. Two coding agents build it in parallel:

| Agent | Brief | Owns (only edit these) |
|---|---|---|
| A — engine | [AGENT_A_ENGINE.md](AGENT_A_ENGINE.md) | `Backend/agents/**`, `Backend/tests/test_agents*.py`, `Backend/.env.example` |
| B — API + UI | [AGENT_B_API_UI.md](AGENT_B_API_UI.md) | `Backend/app/agents_api.py`, `Backend/app/main.py` (2 small edits only), `Backend/tests/test_agents_api.py`, `frontend/**` |

Do not edit files owned by the other agent. Do not edit `.okf/`, `PIPELINE_SPEC.md`, `rank.py`, `news.py`, `sentiment.py`, `ingest.py`, `llm.py`. Do not commit, push, or install new packages; tell the user if you need one.

## Reference code (read-only)

The original repo is downloaded at `/Users/fais/Downloads/TradingAgents-main` (Apache-2.0). Read it to port prompts and logic. **Do not** import it, `pip install` it, run its code, or copy LangGraph/LangChain. Any file that adapts its prompts or logic starts with:
`# Adapted from TauricResearch/TradingAgents (Apache-2.0), <original path>`
Per-file mapping is in [AGENT_A_ENGINE.md](AGENT_A_ENGINE.md) § 0.

## Goal

For each stock on the home page, a team of LLM agents (modelled on TauricResearch/TradingAgents, rewritten as plain Python, no LangGraph) reviews the rule/ML idea and writes an opinion. The card shows the opinion and the full reasoning.

```
context (DB + APIs)
 → 4 analysts: market · news · fundamentals · social      (macro data goes to the market analyst)
 → bull ↔ bear debate (MAX_DEBATE_ROUNDS=1 → 2 turns) → research manager
 → trader (plan)
 → risk debate: aggressive → conservative → neutral (MAX_RISK_ROUNDS=1 → 3 turns)
 → portfolio manager → final rating
 → memory: after 5 trading days, settle vs SPY + 1 reflection call
```

About 13 LLM calls per stock (+1 per settled past decision, + retries).

## Hard rules (from the project brief — break none)

1. **The AI never changes** `entry`, `stop`, `target`, `score`, `position_pct` in `recommendations`. Trader/risk numbers are stored and shown separately as "AI suggestion".
2. **No invented data.** Every claim cites evidence ids that exist in the context the agent was given (validated in code). A source that fails is `unavailable` and shown as "no data" — never filled in by the model.
3. Rating is the AI's opinion, labelled "AI opinion · not backtested · not investment advice".
4. No secrets in the frontend, logs, DB, or error messages. Only read keys from env.
5. Recommendations stay long-only. If the AI says Hold/Underweight/Sell the card stays and shows a yellow warning; it is not hidden.
6. No AI on the user's machine: the model is a remote OpenAI-compatible API.

## Environment (`Backend/.env`, never committed)

| Var | Required | Value / note |
|---|---|---|
| `AGENT_LLM_BASE_URL` | yes | `https://gateway.9arm.co/v1` |
| `AGENT_LLM_API_KEY` | yes | user puts it in; never print it |
| `AGENT_LLM_MODEL` | yes | `qwen3.8-27b-fp8` (quick roles) |
| `AGENT_LLM_DEEP_MODEL` | no | defaults to `AGENT_LLM_MODEL` (research manager, portfolio manager) |
| `FMP_API_KEY` | no | already set; free plan = 250 requests/day → cache per day |
| `SEC_EDGAR_USER_AGENT` | no | `"PlanWise <email>"`; if unset, SEC is `skipped` (do not send a fake contact) |
| `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` | no | Reddit OAuth (app-only). Anonymous Reddit RSS and StockTwits returned **403** from this machine on 2026-11-17 |
| `FRED_API_KEY` | no | macro; skipped if unset |

## Evidence ids (used in every agent output)

`news:<news_items.id>` · `metric:<name>` (e.g. `metric:rsi14`) · `fund:<name>` (e.g. `fund:pe_ttm`) · `sec:<concept>` · `social:<source>:<post id>` · `macro:<series>` · `rule:<index into recommendations.reasons>` · `agent:<role>` (an earlier agent's output) · `memory:<decision id>`.
The validator rejects an output that cites an id not present in that agent's input.

## Database (exact DDL — portable SQLite/Postgres via `app.dbcompat`; A creates it in `Backend/agents/schema.py`, B reads it)

```sql
CREATE TABLE IF NOT EXISTS agent_runs (
  id INTEGER PRIMARY KEY,
  ticker TEXT NOT NULL,
  horizon TEXT NOT NULL,             -- '1w' | '1m' | '3m'
  as_of TEXT NOT NULL,               -- price date the context used (YYYY-MM-DD)
  model TEXT NOT NULL,
  deep_model TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  status TEXT NOT NULL,              -- 'ok' | 'partial' | 'error'
  rating TEXT,                       -- Buy|Overweight|Hold|Underweight|Sell|REVIEW
  summary TEXT,
  final_json TEXT,                   -- AgentReview.review (contract below) + evidence_index {id: {label, value?, url?, published_at?}}
  sources_json TEXT NOT NULL,        -- {source: {status, reason}}
  tokens_in INTEGER NOT NULL DEFAULT 0,
  tokens_out INTEGER NOT NULL DEFAULT 0,
  error TEXT,
  started_at TEXT NOT NULL,
  finished_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_agent_runs_ticker ON agent_runs (ticker, horizon, id);
CREATE TABLE IF NOT EXISTS agent_messages (
  id INTEGER PRIMARY KEY,
  run_id INTEGER NOT NULL REFERENCES agent_runs(id),
  role TEXT NOT NULL,                -- market|news|fundamentals|social|bull|bear|research_manager|trader|aggressive|conservative|neutral|portfolio_manager|reflection
  turn INTEGER NOT NULL DEFAULT 0,
  model TEXT NOT NULL,
  input_ids TEXT NOT NULL,           -- JSON list of evidence ids given
  output_json TEXT,
  error TEXT,
  tokens_in INTEGER NOT NULL DEFAULT 0,
  tokens_out INTEGER NOT NULL DEFAULT 0,
  latency_ms INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_decisions (
  id INTEGER PRIMARY KEY,
  run_id INTEGER NOT NULL REFERENCES agent_runs(id),
  ticker TEXT NOT NULL,
  rating TEXT NOT NULL,
  as_of TEXT NOT NULL,
  entry_close REAL,                  -- first close after as_of, filled when settled
  settle_after_days INTEGER NOT NULL DEFAULT 5,
  settled_on TEXT,
  return_pct REAL,
  benchmark_return_pct REAL,
  alpha_pct REAL,
  reflection TEXT,
  settled_at TEXT
);
CREATE TABLE IF NOT EXISTS source_cache (
  source TEXT NOT NULL,              -- fmp|sec|reddit|stocktwits|fred|spy
  key TEXT NOT NULL,                 -- ticker or series
  fetched_on TEXT NOT NULL,          -- YYYY-MM-DD
  payload_json TEXT NOT NULL,
  PRIMARY KEY (source, key, fetched_on)
);
```

`rank.py` deletes and rebuilds `recommendations`; these tables are independent and keyed by ticker, so they survive.

## API contract (B implements, A's `final_json` must match `review`)

### `GET /api/recommendations?horizon=…` — one new field per item

```ts
ai: {
  run_id: number; rating: Rating; summary: string;
  agrees: "agree" | "caution" | "disagree" | "review";   // Buy/Overweight=agree, Hold=caution, Underweight/Sell=disagree, REVIEW=review
  as_of: string; created_at: string; model: string;
} | null        // newest agent_runs row with status ok|partial for (ticker, horizon); else null
```
The old `llm` field stays unchanged.

### `GET /api/agents/{ticker}?horizon=1w` (session required, like the other routes)

`404 {"detail":"no review"}` when there is no run. Otherwise `AgentReview`:

```ts
type Rating = "Buy" | "Overweight" | "Hold" | "Underweight" | "Sell" | "REVIEW";
type Signal = "bullish" | "neutral" | "bearish" | "no_data";
type Point = { text: string; evidence: string[] };
type Evidence = { id: string; kind: "news"|"metric"|"fund"|"sec"|"social"|"macro"|"rule"|"agent"|"memory";
                  label: string; value?: string; url?: string; published_at?: string; sentiment?: string | null };

interface AgentReview {
  run_id: number; ticker: string; horizon: "1w"|"1m"|"3m"; as_of: string;
  model: string; deep_model: string; prompt_version: string; created_at: string;
  status: "ok" | "partial";
  sources: Record<"prices"|"news"|"fmp"|"sec"|"social"|"macro", { status: "ok"|"unavailable"|"skipped"; reason?: string }>;
  review: {
    rating: Rating; summary: string; agrees: "agree"|"caution"|"disagree"|"review";
    key_risks: Point[];
    analysts: Record<"market"|"news"|"fundamentals"|"social",
      { signal: Signal; summary: string; points: Point[]; data_gaps: string[] } | null>;
    debate: { bull: Point[]; bear: Point[]; manager: { lean: Rating; rationale: string; evidence: string[] } | null };
    trader: { stance: "enter"|"wait"|"avoid"; rationale: string; evidence: string[];
              suggested_stop: number | null; suggested_target: number | null } | null;
    risk: Record<"aggressive"|"conservative"|"neutral",
      { view: string; suggested_position_pct: number | null; evidence: string[] } | null>;
    rules: { entry: number; stop: number; target: number; score: number };   // copied from recommendations, read-only
  };
  evidence: Evidence[];            // every id cited anywhere above, resolved for display
  track_record: { as_of: string; rating: Rating; return_pct: number | null;
                  benchmark_return_pct: number | null; alpha_pct: number | null; reflection: string | null }[];  // newest first, max 5, this ticker
}
```

A full example is in [example_review.json](example_review.json) (fake values, `"_example": true`).

## Done = the user can test

1. `cd Backend && .venv/bin/python -m unittest tests.test_agents tests.test_agents_api -v` passes (no network, fake LLM).
2. `cd Backend && .venv/bin/python -m agents.run --tickers TYL --horizon 1w` prints each role, the rating, tokens, and writes one `agent_runs` row.
3. `.venv/bin/python -m agents.run --horizon 1w --top 20` reviews the 20 curated 1w ideas.
4. `cd frontend && npm run build && npm run lint && npx tsc --noEmit` pass.
5. Home page: badge shows `AI · Buy` (etc.); expanding a card shows the verdict box and 6 tabs; a card without a run shows "Rule-based" and "AI review pending".
