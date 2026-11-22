"""Observation ordering for SQLite's shared daily price cache."""
from .dbcompat import is_pg


PRICE_UPSERT = (
    "INSERT INTO prices (ticker, date, open, high, low, close, volume) "
    "VALUES (?, ?, ?, ?, ?, ?, ?) "
    "ON CONFLICT(ticker, date) DO UPDATE SET "
    "open=excluded.open, high=excluded.high, low=excluded.low, "
    "close=excluded.close, volume=excluded.volume"
)
SQLITE_PRICE_UPSERT = (
    "INSERT INTO prices (ticker, date, open, high, low, close, volume, observed_at_ns) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
    "ON CONFLICT(ticker, date) DO UPDATE SET "
    "open=excluded.open, high=excluded.high, low=excluded.low, "
    "close=excluded.close, volume=excluded.volume, observed_at_ns=excluded.observed_at_ns "
    "WHERE excluded.observed_at_ns > prices.observed_at_ns"
)


def init_price_observations(conn) -> None:
    if is_pg(conn):
        return
    # Schema initialization already owns transaction boundaries. Serialize the
    # check and ALTER so simultaneous app/pipeline startup can upgrade safely.
    with conn:
        conn.execute("BEGIN IMMEDIATE").close()
        columns = {row[1] for row in conn.execute("PRAGMA table_info(prices)").fetchall()}
        if "observed_at_ns" not in columns:
            conn.execute("ALTER TABLE prices ADD COLUMN observed_at_ns INTEGER NOT NULL DEFAULT 0").close()


def price_upsert_sql(conn) -> str:
    return PRICE_UPSERT if is_pg(conn) else SQLITE_PRICE_UPSERT


def price_values(conn, values: tuple, observed_at_ns: int) -> tuple:
    return values if is_pg(conn) else (*values, observed_at_ns)
