"""Explore FNSPID on Kaggle: how much news per stock, how much is junk, and the "always up" baseline.

RUN ON KAGGLE, NOT LOCALLY. In a new notebook: Add Input -> FNSPID, then paste this file (cells split by `# %%`).
It only reads and counts. No model is trained or run. Nothing is written except /kaggle/working/fnspid_summary.json.

Column names of the Kaggle copy are NOT verified. Cell 2 prints what it found; if it guesses wrong,
set the COL_* overrides below and rerun.
"""
# %% 0. Settings
import glob
import json
import os
import re

import pandas as pd

INPUT_DIR = "/kaggle/input"
MAX_ROWS = 2_000_000          # news rows to scan (the full file is huge); None = everything
CHUNK = 250_000
HORIZON_DAYS = 5              # about 1 week of trading days
N_TICKERS = 20                # top tickers by news count used for the baseline
TRAIN_END = "2018-12-31"      # time-based split, never random (this Kaggle copy ends mid-2020)

COL_DATE = None               # override if the guess is wrong, e.g. "Date"
COL_TICKER = None             # e.g. "Stock_symbol"
COL_TITLE = None              # e.g. "Article_title"
NEWS_FILE = None              # full path; None = pick the biggest csv with a title-like column
PRICE_DIR = None              # folder with one csv per ticker; None = guess

# Same idea as Backend/pipeline/news.py NOISE, plus generic explainer headlines
NOISE = re.compile(
    r"stock price,? news|quote and history|how to buy|how much you would have made|"
    r"\b(?:stock|shares) (?:sold|bought|acquired|purchased) by\b|\bposition (?:in|trimmed|raised|lifted|cut)\b|"
    r"^what is\b|how to invest|step-by-step guide|\bnasdaq:|zacks rank|\bbuy, sell, or hold\b",
    re.I,
)

# %% 1. What files are there
files = sorted(glob.glob(f"{INPUT_DIR}/**/*", recursive=True))
files = [f for f in files if os.path.isfile(f)]
print(len(files), "files")
for f in files[:40]:
    print(f"{os.path.getsize(f)/1e6:10.1f} MB  {f}")


def guess(cols, names):
    low = {c.lower(): c for c in cols}
    for n in names:
        for lc, c in low.items():
            if n in lc:
                return c
    return None


# %% 2. Find the news file and its columns
csvs = [f for f in files if f.lower().endswith((".csv", ".csv.gz"))]
news_path, best = NEWS_FILE, None
if not news_path:
    for f in csvs:
        head = pd.read_csv(f, nrows=3)
        if guess(head.columns, ["title", "headline"]) and guess(head.columns, ["date"]):
            size = os.path.getsize(f)
            if best is None or size > best:
                news_path, best = f, size
assert news_path, "no csv with title + date columns found; set NEWS_FILE"
head = pd.read_csv(news_path, nrows=5)
print(news_path)
print(head.columns.tolist())
print(head.head(3).to_string()[:1500])

c_date = COL_DATE or guess(head.columns, ["date"])
c_tick = COL_TICKER or guess(head.columns, ["stock_symbol", "ticker", "symbol", "stock"])
c_title = COL_TITLE or guess(head.columns, ["article_title", "title", "headline"])
print("\nusing:", dict(date=c_date, ticker=c_tick, title=c_title))
assert c_date and c_tick and c_title, "set COL_DATE / COL_TICKER / COL_TITLE at the top"

# %% 3. One pass over the news: per year, per ticker, junk rate
per_year, per_ticker, junk_year = {}, {}, {}
total = bad_date = 0
dup_check = set()
dups = 0
for chunk in pd.read_csv(news_path, usecols=[c_date, c_tick, c_title], chunksize=CHUNK):
    d = pd.to_datetime(chunk[c_date], errors="coerce", utc=True, format="mixed")  # formats differ per row
    bad_date += int(d.isna().sum())
    chunk = chunk.assign(_d=d).dropna(subset=["_d", c_title, c_tick])
    chunk["_y"] = chunk["_d"].dt.year
    junk = chunk[c_title].astype(str).str.contains(NOISE)
    for y, n in chunk["_y"].value_counts().items():
        per_year[int(y)] = per_year.get(int(y), 0) + int(n)
    for y, n in chunk.loc[junk, "_y"].value_counts().items():
        junk_year[int(y)] = junk_year.get(int(y), 0) + int(n)
    for t, n in chunk[c_tick].value_counts().items():
        per_ticker[t] = per_ticker.get(t, 0) + int(n)
    key = (chunk[c_tick] + "|" + chunk[c_title].astype(str).str.lower()).tolist()
    for k in key:
        if k in dup_check:
            dups += 1
        else:
            dup_check.add(k)
    total += len(chunk)
    if MAX_ROWS and total >= MAX_ROWS:
        break
del dup_check

print(f"scanned {total:,} rows (bad dates dropped: {bad_date:,}), duplicate ticker+title: {dups:,}")
yr = pd.DataFrame({"news": per_year, "junk": junk_year}).fillna(0).astype(int).sort_index()
yr["junk_%"] = (100 * yr["junk"] / yr["news"]).round(1)
print(yr.to_string())
top = sorted(per_ticker.items(), key=lambda kv: -kv[1])[:N_TICKERS]
print("\nstocks:", len(per_ticker), "| top:", top[:10])

# %% 4. Prices: dataset files first, yfinance as fallback (needs Internet ON in the notebook)
price_dir = PRICE_DIR
if not price_dir:
    for f in csvs:
        if f != news_path and re.search(r"price|history", f, re.I):
            price_dir = os.path.dirname(f)
            break


def load_prices(t):
    cand = [f for f in csvs if os.path.splitext(os.path.basename(f).lower())[0] == t.lower()
            and (not price_dir or f.startswith(price_dir))]
    if cand:
        p = pd.read_csv(cand[0])
        c_d, c_c = guess(p.columns, ["date"]), guess(p.columns, ["adj close", "adj_close", "close"])
        if c_d and c_c:
            s = pd.Series(p[c_c].values, index=pd.to_datetime(p[c_d], errors="coerce", utc=True).dt.tz_localize(None))
            return s.dropna().sort_index()
    try:
        import yfinance as yf
        h = yf.download(t, start="1999-01-01", progress=False, auto_adjust=True)["Close"].squeeze()
        return h.dropna().sort_index()
    except Exception as e:  # no internet, delisted, ...
        print(t, "no prices:", type(e).__name__)
        return None


def label_news(news_dates, px, horizon=HORIZON_DAYS):
    """Entry = close of the first trading day AFTER the news date (time of day is unknown, so no look-ahead).
    Exit = close `horizon` trading days later. Returns (return series aligned to news_dates)."""
    idx = px.index
    pos = idx.searchsorted(news_dates.dt.tz_localize(None).dt.normalize(), side="right")
    ok = pos + horizon < len(idx)
    ret = pd.Series(float("nan"), index=news_dates.index)
    p = px.values
    ret[ok] = [p[i + horizon] / p[i] - 1 for i in pos[ok]]
    return ret


# %% 5. Baseline "always up" per year and for the time split
tickers = [t for t, _ in top]
rows = []
for chunk in pd.read_csv(news_path, usecols=[c_date, c_tick, c_title], chunksize=CHUNK):
    chunk = chunk[chunk[c_tick].isin(tickers)].copy()
    chunk["_d"] = pd.to_datetime(chunk[c_date], errors="coerce", utc=True, format="mixed")
    chunk = chunk.dropna(subset=["_d", c_title])
    chunk = chunk[~chunk[c_title].astype(str).str.contains(NOISE)]
    rows.append(chunk[[c_tick, "_d", c_title]])
    if sum(len(r) for r in rows) > 500_000:
        break
news = pd.concat(rows, ignore_index=True)

parts = []
for t in tickers:
    px = load_prices(t)
    sub = news[news[c_tick] == t]
    if px is None or sub.empty:
        continue
    sub = sub.assign(ret=label_news(sub["_d"], px)).dropna(subset=["ret"])
    parts.append(sub)
lab = pd.concat(parts, ignore_index=True)
lab["up"] = lab["ret"] > 0
lab["year"] = lab["_d"].dt.year
print(f"labelled headlines: {len(lab):,} over {lab[c_tick].nunique()} stocks")
by_year = lab.groupby("year")["up"].agg(["count", "mean"]).rename(columns={"mean": "share_up"}).round(3)
print(by_year.to_string())
tr = lab[lab["_d"] <= pd.Timestamp(TRAIN_END, tz="UTC")]
te = lab[lab["_d"] > pd.Timestamp(TRAIN_END, tz="UTC")]
print(f"\ntrain (<= {TRAIN_END}): {len(tr):,} share up {tr['up'].mean():.3f}")
print(f"test  (>  {TRAIN_END}): {len(te):,} share up {te['up'].mean():.3f}")
print("A model must beat 'always up' =", f"{max(te['up'].mean(), 1 - te['up'].mean()):.3f}", "on the test part to mean anything.")

# %% 6. Save a small summary
summary = {
    "news_file": news_path, "columns": dict(date=c_date, ticker=c_tick, title=c_title),
    "rows_scanned": total, "per_year": per_year, "junk_per_year": junk_year,
    "stocks": len(per_ticker), "labelled": int(len(lab)),
    "baseline_test_share_up": float(te["up"].mean()) if len(te) else None,
}
os.makedirs("/kaggle/working", exist_ok=True)
json.dump(summary, open("/kaggle/working/fnspid_summary.json", "w"), indent=2, default=str)
print("saved /kaggle/working/fnspid_summary.json")
