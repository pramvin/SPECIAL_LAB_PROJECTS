"""Pipeline steps 1-3: S&P 500 universe -> yfinance daily prices -> validate -> SQLite.

Run from Backend/:  .venv/bin/python -m pipeline.ingest [--limit N] [--period 2y]
Only rows that pass validation are written to `prices`; everything rejected is
recorded in `data_issues` so nothing is silently dropped.
"""
import argparse
import os
import sqlite3
import time
from io import StringIO

import pandas as pd
import requests
import yfinance as yf

DB_PATH = os.environ.get("PLANWISE_DB", os.path.join(os.path.dirname(__file__), "..", "planwise.db"))
WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
BATCH = 100
MAX_DAILY_MOVE = 0.5  # |close/prev_close - 1| above this is flagged as suspect
MIN_ROWS = 60  # fewer valid daily bars than this -> ticker is rejected

# GICS sector -> the sector keys used by the onboarding form.
SECTOR_MAP = {
    "Information Technology": "tech",
    "Communication Services": "tech",
    "Health Care": "healthcare",
    "Financials": "finance",
    "Energy": "energy",
    "Consumer Discretionary": "consumer",
    "Consumer Staples": "consumer",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS universe (
  ticker TEXT PRIMARY KEY, name TEXT NOT NULL, gics_sector TEXT NOT NULL,
  sector TEXT NOT NULL, updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS prices (
  ticker TEXT NOT NULL, date TEXT NOT NULL,
  open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL, close REAL NOT NULL,
  volume INTEGER NOT NULL,
  PRIMARY KEY (ticker, date)
);
CREATE TABLE IF NOT EXISTS data_issues (
  id INTEGER PRIMARY KEY, run_at INTEGER NOT NULL, ticker TEXT NOT NULL,
  date TEXT, kind TEXT NOT NULL, detail TEXT NOT NULL
);
"""


def fetch_universe() -> pd.DataFrame:
    html = requests.get(WIKI_URL, headers={"User-Agent": "PlanWiseAI-student-project/0.1"}, timeout=30)
    html.raise_for_status()
    t = pd.read_html(StringIO(html.text))[0]
    df = pd.DataFrame({
        "ticker": t["Symbol"].str.replace(".", "-", regex=False).str.strip(),  # BRK.B -> BRK-B
        "name": t["Security"],
        "gics_sector": t["GICS Sector"],
    })
    df["sector"] = df["gics_sector"].map(SECTOR_MAP).fillna("other")
    return df.drop_duplicates("ticker").reset_index(drop=True)


def fetch_prices(tickers: list[str], period: str) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for i in range(0, len(tickers), BATCH):
        chunk = tickers[i : i + BATCH]
        raw = yf.download(chunk, period=period, interval="1d", auto_adjust=True,
                          group_by="ticker", threads=True, progress=False)
        for t in chunk:
            try:
                df = raw[t] if len(chunk) > 1 else raw
            except KeyError:
                continue
            out[t] = df.dropna(how="all")
    return out


def validate(ticker: str, df: pd.DataFrame) -> tuple[pd.DataFrame, list[tuple[str | None, str, str]]]:
    """Return (clean rows, issues). Issues are (date, kind, detail)."""
    issues: list[tuple[str | None, str, str]] = []
    if df is None or df.empty:
        return pd.DataFrame(), [(None, "no_data", "provider returned no rows")]
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()

    def reject(mask: pd.Series, kind: str, detail: str) -> None:
        nonlocal df
        for d in df.index[mask]:
            issues.append((d.strftime("%Y-%m-%d"), kind, detail))
        df = df[~mask]

    dup = df.index.duplicated(keep="last")
    reject(pd.Series(dup, index=df.index), "duplicate_date", "duplicate timestamp, kept last")
    reject(df.isna().any(axis=1), "missing_value", "NaN in OHLCV")
    reject((df[["Open", "High", "Low", "Close"]] <= 0).any(axis=1), "non_positive_price", "price <= 0")
    reject((df["High"] < df["Low"]), "high_below_low", "High < Low")
    inside = (df["Close"] <= df["High"] * 1.0001) & (df["Close"] >= df["Low"] * 0.9999)
    reject(~inside, "close_outside_range", "Close outside [Low, High]")
    reject(df["Volume"] < 0, "negative_volume", "Volume < 0")
    df = df.sort_index()
    # Large day-over-day moves are kept but reported: could be real news or a bad split adjustment.
    move = df["Close"].pct_change().abs()
    for d in df.index[move > MAX_DAILY_MOVE]:
        issues.append((d.strftime("%Y-%m-%d"), "suspect_jump", f"close moved {move[d]:.0%} in one day"))
    zero_vol = (df["Volume"] == 0).sum()
    if zero_vol:
        issues.append((None, "zero_volume_days", f"{zero_vol} days with zero volume (kept)"))
    if len(df) < MIN_ROWS:
        issues.append((None, "too_few_rows", f"only {len(df)} valid bars, need {MIN_ROWS}; ticker rejected"))
        return pd.DataFrame(), issues
    return df, issues


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="only the first N tickers (for quick tests)")
    ap.add_argument("--period", default="2y")
    args = ap.parse_args()

    now = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    uni = fetch_universe()
    if args.limit:
        uni = uni.head(args.limit)
    print(f"universe: {len(uni)} tickers")
    with conn:
        conn.executemany(
            "INSERT INTO universe (ticker, name, gics_sector, sector, updated_at) VALUES (?,?,?,?,?) "
            "ON CONFLICT(ticker) DO UPDATE SET name=excluded.name, gics_sector=excluded.gics_sector, "
            "sector=excluded.sector, updated_at=excluded.updated_at",
            [(r.ticker, r.name, r.gics_sector, r.sector, now) for r in uni.itertuples()],
        )

    frames = fetch_prices(list(uni["ticker"]), args.period)
    ok = rejected = rows = n_issues = 0
    for ticker in uni["ticker"]:
        clean, issues = validate(ticker, frames.get(ticker))
        with conn:
            conn.executemany(
                "INSERT INTO data_issues (run_at, ticker, date, kind, detail) VALUES (?,?,?,?,?)",
                [(now, ticker, d, k, det) for d, k, det in issues],
            )
            if not clean.empty:
                conn.executemany(
                    "INSERT OR REPLACE INTO prices (ticker, date, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
                    [(ticker, d.strftime("%Y-%m-%d"), float(r.Open), float(r.High), float(r.Low),
                      float(r.Close), int(r.Volume)) for d, r in clean.iterrows()],
                )
        n_issues += len(issues)
        if clean.empty:
            rejected += 1
        else:
            ok += 1
            rows += len(clean)
    print(f"prices: {ok} tickers ok, {rejected} rejected, {rows} rows written, {n_issues} issues logged")


if __name__ == "__main__":
    main()
