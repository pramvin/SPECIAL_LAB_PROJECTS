# Fixed-rule technical experts (RSI, MACD) x 1-day / 5-day excess returns, on the current S&P 500.
# RUN ON KAGGLE ONLY (CPU is enough, Internet ON). Never run this on the user's machine; do not install anything locally.
# Style follows newsxbigmove.py: one "# P4x" block per Kaggle cell, no top-level indented blocks except `def`.
#
# QUESTION: do two fixed, non-trained chart rules (RSI(14) and MACD(12,26,9) crosses) pick stocks that beat the
# cross-section over the next 1 or 5 days, after costs, better than shuffled signals?
#
# PRE-REGISTERED RULES (set before any result is seen; do not edit after looking at the output):
#   Decision window: 2023-01-01 to 2026-10-31. ONLY these 4 cells decide: RSI and MACD x 1 day and 5 days.
#   The 2017-2022 window is DESCRIPTIVE ONLY and is never used for pass/fail.
#   Pass = net spread > 0 AND net t > 2 AND p_shuffle < 0.0125 (Bonferroni 0.05/4). There is NO primary cell.
#   Costs = 4 x 10 bps = 40 bps per top-minus-bottom pair, charged once per holding period.
#   net t = (mean - 40bps/1e4) / std * sqrt(n) over NON-OVERLAPPING days; for 5 days every phase is used and the
#   mean and range over the 5 phases are reported.
#   Spread per day = mean excess return of signal +1 minus mean excess of signal -1, with >= 5 names per side.
#   Excess return = return from close t+1 to close t+1+h minus the median of ALL stocks over the same window.
#   Shuffled null = 200 permutations of the non-zero signals within each day (group sizes are fixed).
#   SURVIVORS ONLY: the universe is the CURRENT S&P 500 list, so delisted stocks are absent (survivorship bias).
#
# DATA CLEANING (fixed constants, applied in this order):
#   1. drop a ticker if its missing fraction > MAX_MISSING (5%);
#   2. set close to missing on every stock-day with |1-day return| > EXTREME_RET (50%);
#   3. set close to missing on every day inside a run of >= FLAT_RUN (5) unchanged closes.
#   P40 audits the raw data and prints the before/after counts for each rule.
#
# NOTE: the decision window ends 2026-10-31 but the download ends 2026-11-02, so the last few signal days lose their
# forward return (t+1+h) and are dropped. That is expected and reported as dropped days.

# P40. Constants, prices, raw audit, fixed cleaning
import io, json, time
import numpy as np, pandas as pd
import requests
import yfinance as yf

START, END = "2016-06-01", "2026-11-03"  # yfinance end is exclusive -> last day 2026-11-02
DEC_START, DEC_END = pd.Timestamp("2023-01-01"), pd.Timestamp("2026-10-31")
DESC_START, DESC_END = pd.Timestamp("2017-01-01"), pd.Timestamp("2022-12-31")
MAX_MISSING, EXTREME_RET, FLAT_RUN = 0.05, 0.50, 5
MIN_PER_SIDE, COST_BPS, N_SHUFFLE = 5, 10.0, 200
COST_PAIR = 4 * COST_BPS
RSI_N, RSI_LOW, RSI_HIGH = 14, 30, 70
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9
HORIZONS = (1, 5)
ALPHA_CELL, N_CONFIRMATORY = 0.05 / 4, 4

html = requests.get("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
                    headers={"User-Agent": "PlanWiseAI-student-project/0.1"}, timeout=30).text
tickers = pd.read_html(io.StringIO(html))[0]["Symbol"].str.replace(".", "-", regex=False).str.strip().unique().tolist()
print(len(tickers), "tickers in the current S&P 500 list")
closes, vols = [], []
for i in range(0, len(tickers), 100):
    raw = yf.download(tickers[i:i + 100], start=START, end=END, interval="1d", auto_adjust=True, progress=False, threads=True)
    closes.append(raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]])
    vols.append(raw["Volume"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Volume"]])
    time.sleep(1)
close = pd.concat(closes, axis=1).sort_index()
volume = pd.concat(vols, axis=1).sort_index()
close = close.loc[:, ~close.columns.duplicated()]
volume = volume.reindex(columns=close.columns)
spy = yf.download("SPY", start=START, end=END, interval="1d", auto_adjust=True, progress=False)["Close"].squeeze()
print("price table", close.shape, close.index.min().date(), "to", close.index.max().date())
print("WARNING: survivors only — the universe is the CURRENT S&P 500 list; delisted stocks are missing (survivorship bias).")

def flat_mask(s, min_len):
    m = pd.Series(False, index=s.index)
    ss = s.dropna()
    if ss.empty:
        return m
    same = ss.eq(ss.shift())
    sizes = ss.groupby((~same).cumsum()).transform("size")
    m.loc[ss.index[sizes >= min_len]] = True
    return m

def flat_runs(s, min_len):
    ss = s.dropna()
    if ss.empty:
        return []
    same = ss.eq(ss.shift())
    return [(g.index[0], g.index[-1], len(g)) for _, g in ss.groupby((~same).cumsum()) if len(g) >= min_len]

def audit(close, volume, spy):
    print("\n--- P40 raw data audit ---")
    miss = close.isna().mean().sort_values(ascending=False)
    print("tickers", close.shape[1], "| days", close.shape[0])
    print("missing fraction per ticker (top 25; counts below cover all):")
    print(miss.head(25).round(3).to_string())
    print("missing fraction: min", round(float(miss.min()), 4), "median", round(float(miss.median()), 4),
          "max", round(float(miss.max()), 4), "| tickers >", MAX_MISSING, "=", int((miss > MAX_MISSING).sum()))
    print("duplicate index rows:", int(close.index.duplicated().sum()))
    extra = close.index.difference(spy.index)
    missing = spy.index.difference(close.index)
    print("dates in prices but not in SPY calendar:", len(extra), list(extra[:5]))
    print("SPY trading days missing from prices:", len(missing), list(missing[:10]))
    bad = close.where(close <= 0).stack()
    print("prices <= 0:", len(bad), "|", bad.head(20).to_dict())
    print("volume == 0:", int((volume == 0).sum().sum()), "| volume missing:", int(volume.isna().sum().sum()))
    ext = close.pct_change(fill_method=None).stack()
    ext = ext[ext.abs() > EXTREME_RET]
    ext = ext.reindex(ext.abs().sort_values(ascending=False).index)
    print("|1-day return| >", EXTREME_RET, ":", len(ext))
    print(ext.head(30).round(4).to_string(), "(largest 30 shown)" if len(ext) > 30 else "")
    runs = [(t, a, b, n) for t in close.columns for a, b, n in flat_runs(close[t], FLAT_RUN)]
    print("flat runs >=", FLAT_RUN, "days:", len(runs), "| stock-days:", int(sum(n for _, _, _, n in runs)),
          "| tickers affected:", len({r[0] for r in runs}))
    for t, a, b, n in runs[:30]:
        print("  flat", t, a.date(), "->", b.date(), n, "days")
    return miss

miss = audit(close, volume, spy)

def clean(close, volume):
    print("\n--- P40 fixed cleaning ---")
    n0t, n0d = close.shape[1], int(close.notna().sum().sum())
    keep = close.columns[close.isna().mean() <= MAX_MISSING]
    close1, volume1 = close[keep], volume[keep]
    print("rule 1 (missing >", MAX_MISSING, "): tickers", n0t, "->", len(keep), "(dropped", n0t - len(keep), ")")
    r1 = close1.pct_change(fill_method=None)
    ext_mask = r1.abs() > EXTREME_RET
    close2 = close1.mask(ext_mask)
    print("rule 2 (|r1| >", EXTREME_RET, "): stock-days set missing", int(ext_mask.sum().sum()),
          "| tickers still", close2.shape[1])
    flat = close2.apply(flat_mask, min_len=FLAT_RUN)
    close3 = close2.mask(flat)
    print("rule 3 (flat >=", FLAT_RUN, "days): stock-days set missing", int(flat.sum().sum()),
          "| tickers still", close3.shape[1])
    print("valid stock-days:", n0d, "->", int(close3.notna().sum().sum()))
    return close3, volume1.mask(close3.isna()), {
        "tickers_before": n0t, "tickers_after": int(close3.shape[1]), "tickers_dropped_rule1": int(n0t - len(keep)),
        "stock_days_before": n0d, "stock_days_after": int(close3.notna().sum().sum()),
        "rule2_missing": int(ext_mask.sum().sum()), "rule3_missing": int(flat.sum().sum())}

close, volume, CLEAN = clean(close, volume)

# P41. Fixed-rule experts (NO training): RSI(14) and MACD(12,26,9) crosses; signals use closes up to t only.
def wilder_rsi(close, n=RSI_N):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rsi = 100 - 100 / (1 + up / dn)
    sig = pd.DataFrame(0, index=close.index, columns=close.columns)
    sig[rsi < RSI_LOW] = 1
    sig[rsi > RSI_HIGH] = -1
    return sig, rsi

def macd_cross(close, fast=MACD_FAST, slow=MACD_SLOW, sig_n=MACD_SIGNAL):
    macd = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
    line = macd.ewm(span=sig_n, adjust=False).mean()
    up = (macd > line) & (macd.shift(1) <= line.shift(1))
    dn = (macd < line) & (macd.shift(1) >= line.shift(1))
    sig = pd.DataFrame(0, index=close.index, columns=close.columns)
    sig[up] = 1
    sig[dn] = -1
    return sig, macd, line

SIG_RSI, RSI = wilder_rsi(close)
SIG_MACD, MACD, MACD_LINE = macd_cross(close)

def forward_excess(close, h):
    fwd = (close.shift(-(1 + h)) / close.shift(-1) - 1).replace([np.inf, -np.inf], np.nan)
    return fwd.sub(fwd.median(axis=1), axis=0)

def to_long(sig, exc, start, end):
    s = sig.mask(sig == 0).stack().rename("signal")
    e = exc.stack().rename("excess")
    df = pd.concat([s, e], axis=1).dropna().reset_index()
    df.columns = ["day", "stock", "signal", "excess"]
    return df[(df["day"] >= start) & (df["day"] <= end)]

for nm, sg in (("RSI", SIG_RSI), ("MACD", SIG_MACD)):
    print(nm, "signals: +1", int((sg == 1).sum().sum()), "| -1", int((sg == -1).sum().sum()),
          "| days with any signal", int((sg != 0).any(axis=1).sum()))

# P42. Evaluation: per-day spread (+1 minus -1), costs, net t, all 5-day phases, shuffled null.
def daily_spread(df, stats=None):
    df = df.dropna(subset=["signal", "excess"])
    df = df[df["signal"] != 0]
    all_days = df["day"].nunique()
    pos = df[df["signal"] == 1].groupby("day")["excess"].agg(["mean", "size"])
    neg = df[df["signal"] == -1].groupby("day")["excess"].agg(["mean", "size"])
    both = pos.join(neg, lsuffix="_p", rsuffix="_n", how="inner")
    keep = both[(both["size_p"] >= MIN_PER_SIDE) & (both["size_n"] >= MIN_PER_SIDE)]
    if stats is not None:
        stats["used_days"] = int(len(keep))
        stats["dropped_days"] = int(all_days - len(keep))
    return (keep["mean_p"] - keep["mean_n"]).dropna()

def phase_stats(w, h):
    out = []
    for p in range(h):
        wp = w.iloc[p::h]
        n = len(wp)
        if n < 2 or wp.std() == 0:
            continue
        out.append({"phase": p, "days": n, "gross_bps": 1e4 * wp.mean(),
                    "net_bps": 1e4 * wp.mean() - COST_PAIR,
                    "t": (wp.mean() - COST_PAIR / 1e4) / wp.std() * np.sqrt(n)})
    return out

def net_summary(w, h):
    ph = phase_stats(w, h)
    if not ph:
        return {"days": 0, "phases": 0, "gross_bps": np.nan, "net_bps": np.nan, "net_bps_min": np.nan,
                "net_bps_max": np.nan, "t": np.nan, "t_min": np.nan, "t_max": np.nan}
    net = np.array([x["net_bps"] for x in ph])
    tt = np.array([x["t"] for x in ph])
    gr = np.array([x["gross_bps"] for x in ph])
    return {"days": int(np.mean([x["days"] for x in ph])), "phases": len(ph), "gross_bps": float(gr.mean()),
            "net_bps": float(net.mean()), "net_bps_min": float(net.min()), "net_bps_max": float(net.max()),
            "t": float(tt.mean()), "t_min": float(tt.min()), "t_max": float(tt.max())}

def shuffled_net(df, h, rng):
    g = df.copy()
    g["signal"] = g.groupby("day")["signal"].transform(lambda s: rng.permutation(s.values))
    return net_summary(daily_spread(g), h)["net_bps"]

def evaluate(name, sig, close, h, start, end, confirmatory, seed):
    df = to_long(sig, forward_excess(close, h), start, end)
    stats = {}
    w = daily_spread(df, stats)
    s = net_summary(w, h)
    rng = np.random.default_rng(seed)
    null = np.array([shuffled_net(df, h, rng) for _ in range(N_SHUFFLE)])
    null = null[np.isfinite(null)]
    row = {"expert": name, "horizon": h, "window": "decision" if confirmatory else "descriptive",
           "used_days": stats.get("used_days", 0), "dropped_days": stats.get("dropped_days", 0), **s,
           "null_mean_bps": float(np.mean(null)) if len(null) else np.nan,
           "null_p95_bps": float(np.percentile(null, 95)) if len(null) else np.nan,
           "p_shuffle": float((1 + np.sum(null >= s["net_bps"])) / (1 + len(null))) if len(null) else np.nan}
    row["passes"] = bool(confirmatory and s["net_bps"] > 0 and s["t"] > 2 and row["p_shuffle"] < ALPHA_CELL)
    return row

rows = []
for name, sig in (("RSI(14)", SIG_RSI), ("MACD(12,26,9)", SIG_MACD)):
    for h in HORIZONS:
        rows.append(evaluate(name, sig, close, h, DEC_START, DEC_END, True, seed=100 + h))
        rows.append(evaluate(name, sig, close, h, DESC_START, DESC_END, False, seed=200 + h))
res = pd.DataFrame(rows)
res["verdict"] = np.where(res["window"] == "decision", np.where(res["passes"], "PASS", "fail"), "descriptive")

print("\n--- P42 results ---")
print("PASS RULE: net > 0 and net t > 2 and p_shuffle <", ALPHA_CELL, "(Bonferroni 0.05/4); NO primary cell.")
print("DESCRIPTIVE 2017-01-01 to 2022-12-31 (NOT used for pass/fail):")
print(res[res["window"] == "descriptive"].drop(columns=["passes"]).round(3).to_string(index=False))
print("\nDECISION 2023-01-01 to 2026-10-31 (confirmatory, 4 cells):")
print(res[res["window"] == "decision"].drop(columns=["passes"]).round(3).to_string(index=False))
print("\nDROPPED DAYS (no / thin side; used_days + dropped_days = days with any signal):")
print(res[["expert", "horizon", "window", "used_days", "dropped_days"]].to_string(index=False))
n_pass = int(res[(res["window"] == "decision") & res["passes"]].shape[0])
print("\nPASSED:", n_pass, "of", N_CONFIRMATORY, "confirmatory cells")
print("Chance of >= 1 false pass with the per-cell threshold:", round(1 - (1 - ALPHA_CELL) ** N_CONFIRMATORY, 4),
      "| without correction (0.05):", round(1 - 0.95 ** N_CONFIRMATORY, 4))
print("WARNING: survivors only — the universe is the CURRENT S&P 500 list; delisted stocks are missing (survivorship bias).")

out = {"constants": {"start": START, "end": END, "decision_window": [str(DEC_START.date()), str(DEC_END.date())],
                     "descriptive_window": [str(DESC_START.date()), str(DESC_END.date())], "max_missing": MAX_MISSING,
                     "extreme_return": EXTREME_RET, "flat_run": FLAT_RUN, "min_per_side": MIN_PER_SIDE,
                     "cost_bps_per_fill": COST_BPS, "cost_bps_per_pair": COST_PAIR, "n_shuffle": N_SHUFFLE,
                     "rsi": [RSI_N, RSI_LOW, RSI_HIGH], "macd": [MACD_FAST, MACD_SLOW, MACD_SIGNAL],
                     "alpha_cell": ALPHA_CELL, "n_confirmatory": N_CONFIRMATORY, "primary": None},
       "cleaning": CLEAN, "warning": "survivors only: current S&P 500 list (delisted stocks absent)",
       "results": json.loads(res.to_json(orient="records"))}
json.dump(out, open("/kaggle/working/indicator_experts_results.json", "w"), indent=1)
res.to_csv("/kaggle/working/indicator_experts_results.csv", index=False)
print("saved /kaggle/working/indicator_experts_results.json and .csv")
