"""Stock analysis tables. Portable SQLite/Postgres through `app.dbcompat`."""
from __future__ import annotations

from app.dbcompat import table_names

DDL = """
CREATE TABLE IF NOT EXISTS stock_analysis (
  id INTEGER PRIMARY KEY,
  ticker TEXT NOT NULL,
  horizon TEXT NOT NULL,
  status TEXT NOT NULL,
  result_json TEXT,
  error TEXT,
  model TEXT,
  tokens INTEGER,
  started_at TEXT NOT NULL,
  finished_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_stock_analysis_t ON stock_analysis (ticker, horizon, started_at);
CREATE TABLE IF NOT EXISTS stock_analysis_messages (
  id INTEGER PRIMARY KEY,
  analysis_id INTEGER NOT NULL REFERENCES stock_analysis(id),
  role TEXT NOT NULL,
  output_json TEXT,
  error TEXT,
  tokens_in INTEGER NOT NULL DEFAULT 0,
  tokens_out INTEGER NOT NULL DEFAULT 0,
  latency_ms INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
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
    """Create the tables once per database (a cheap table lookup when they already exist)."""
    if {"stock_analysis", "stock_analysis_messages", "source_cache"} <= table_names(conn):
        return
    conn.executescript(DDL)
    conn.commit()
