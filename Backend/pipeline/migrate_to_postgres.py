"""Copy the market-data tables from the local SQLite file to Postgres (Neon).

    DATABASE_URL='postgresql://...' python -m pipeline.migrate_to_postgres [path/to/planwise.db]

Copies market data only (prices, universe, news, scores, recommendations). User tables are left
alone so everyone starts fresh and the demo account is created by the app. Safe to re-run:
the tables are emptied on the target before they are filled.
"""
import os
import sqlite3
import sys

from app import main  # noqa: F401  (importing it creates the app tables on the target)
from app.dbcompat import column_names, connect, database_url, is_pg
from pipeline import ingest, news, sentiment

HERE = os.path.dirname(__file__)
DEFAULT_SOURCE = os.path.join(HERE, "..", "planwise.db")
TABLES = ["universe", "prices", "data_issues", "news_items", "news_scores", "recommendations"]


def copy_table(src: sqlite3.Connection, dst, table: str) -> int:
    cols = [c for c in (r[1] for r in src.execute(f"PRAGMA table_info({table})")) if c in column_names(dst, table)]
    col_list = ", ".join(cols)
    rows = src.execute(f"SELECT {col_list} FROM {table}")
    n = 0
    with dst._raw.cursor().copy(f"COPY {table} ({col_list}) FROM STDIN") as copy:
        for row in rows:
            copy.write_row(row)
            n += 1
    if "id" in cols:
        dst.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 1)) FROM {table}")
    dst.commit()
    return n


def main_cli() -> None:
    if not database_url():
        sys.exit("Set DATABASE_URL to the Postgres connection string first (and leave PLANWISE_DB unset).")
    source = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SOURCE
    src = sqlite3.connect(source)
    dst = connect("")
    assert is_pg(dst)
    for schema in (ingest.SCHEMA, news.SCHEMA, sentiment.SCHEMA):
        dst.executescript(schema)
    for table in reversed(TABLES):  # children first: news_scores points at news_items
        dst.execute(f"DELETE FROM {table}")
    dst.commit()
    for table in TABLES:
        print(f"{table}: {copy_table(src, dst, table)} rows", flush=True)
    dst.close()


if __name__ == "__main__":
    main_cli()
