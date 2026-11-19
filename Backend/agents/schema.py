"""Agent tables (SPEC DDL). Portable SQLite/Postgres through `app.dbcompat`."""
from __future__ import annotations

DDL = """
CREATE TABLE IF NOT EXISTS agent_runs (
  id INTEGER PRIMARY KEY,
  ticker TEXT NOT NULL,
  horizon TEXT NOT NULL,
  as_of TEXT NOT NULL,
  model TEXT NOT NULL,
  deep_model TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  status TEXT NOT NULL,
  rating TEXT,
  summary TEXT,
  final_json TEXT,
  sources_json TEXT NOT NULL,
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
  role TEXT NOT NULL,
  turn INTEGER NOT NULL DEFAULT 0,
  model TEXT NOT NULL,
  input_ids TEXT NOT NULL,
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
  entry_close REAL,
  settle_after_days INTEGER NOT NULL DEFAULT 5,
  settled_on TEXT,
  return_pct REAL,
  benchmark_return_pct REAL,
  alpha_pct REAL,
  reflection TEXT,
  settled_at TEXT
);
CREATE TABLE IF NOT EXISTS source_cache (
  source TEXT NOT NULL,
  key TEXT NOT NULL,
  fetched_on TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  PRIMARY KEY (source, key, fetched_on)
);
"""


def ensure(conn) -> None:
    conn.executescript(DDL)
