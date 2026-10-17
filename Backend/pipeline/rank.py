"""Pipeline steps 5-7 (price-only version): indicators -> score per horizon -> ATR risk levels.

Reads `prices` + `universe`, writes `recommendations` (is_example = 0).
No news or fundamentals yet: reasons only quote numbers computed here.
The score weights and ATR multiples are untested heuristics until backtested.

Run from Backend/:  .venv/bin/python -m pipeline.rank
"""
import json
import os
import sqlite3
import time

import numpy as np
import pandas as pd

DB_PATH = os.environ.get("PLANWISE_DB", os.path.join(os.path.dirname(__file__), "..", "planwise.db"))
TOP_N = 20  # per horizon
MAX_PER_GICS_SECTOR = 4
MIN_BARS = 200
MIN_DOLLAR_VOLUME = 50e6  # 20-day average traded value, USD
MAX_ABOVE_SMA50 = 0.25  # skip names already stretched far above trend

# horizon -> (weights over percentile ranks, stop ATRs, target ATRs)
HORIZONS = {
    "1w": ({"ret_20d": 0.35, "ret_5d": 0.25, "vol_ratio": 0.25, "low_atr": 0.15}, 2.0, 3.0),
    "1m": ({"ret_60d": 0.40, "ret_20d": 0.30, "vol_ratio": 0.15, "low_atr": 0.15}, 3.0, 5.0),
    "3m": ({"ret_126d": 0.50, "ret_60d": 0.25, "low_atr": 0.25}, 4.5, 8.0),
}

LABELS = {
    "ret_5d": "5-day return", "ret_20d": "20-day return", "ret_60d": "60-day return",
    "ret_126d": "6-month return",
}


def indicators(g: pd.DataFrame) -> dict | None:
    if len(g) < MIN_BARS:
        return None
    c, h, l, v = g["close"].to_numpy(), g["high"].to_numpy(), g["low"].to_numpy(), g["volume"].to_numpy(float)
    prev = np.roll(c, 1)
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev), np.abs(l - prev)))[1:]
    atr = tr[-14:].mean()
    last = c[-1]
    sma50, sma200 = c[-50:].mean(), c[-200:].mean()
    return {
        "close": last, "atr": atr, "atr_pct": atr / last * 100,
        "sma50": sma50, "sma200": sma200,
        "above_sma50": last / sma50 - 1, "above_sma200": last / sma200 - 1,
        "ret_5d": last / c[-6] - 1, "ret_20d": last / c[-21] - 1,
        "ret_60d": last / c[-61] - 1, "ret_126d": last / c[-127] - 1,
        "vol_ratio": v[-5:].mean() / max(v[-30:].mean(), 1),
        "dollar_vol": (c[-20:] * v[-20:]).mean(),
        "as_of": g["date"].iloc[-1],
    }


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    px = pd.read_sql("SELECT ticker, date, high, low, close, volume FROM prices ORDER BY ticker, date", conn)
    uni = pd.read_sql("SELECT ticker, name, gics_sector, sector FROM universe", conn).set_index("ticker")
    if px.empty:
        raise SystemExit("prices is empty: run `python -m pipeline.ingest` first")

    rows = {}
    for t, g in px.groupby("ticker"):
        ind = indicators(g)
        if ind and t in uni.index:
            rows[t] = ind
    df = pd.DataFrame(rows).T.infer_objects()
    as_of = df["as_of"].max()
    df = df[df["dollar_vol"] >= MIN_DOLLAR_VOLUME]
    df = df.join(uni)
    pct = lambda s: s.rank(pct=True) * 100  # noqa: E731
    for col in ("ret_5d", "ret_20d", "ret_60d", "ret_126d", "vol_ratio"):
        df[f"r_{col}"] = pct(df[col])
    df["r_low_atr"] = 100 - pct(df["atr_pct"])
    print(f"{len(rows)} tickers with enough history, {len(df)} liquid enough, prices as of {as_of}")

    now = int(time.time())
    out = []
    for horizon, (weights, stop_k, target_k) in HORIZONS.items():
        d = df.copy()
        # Long-only trend filter: 1w needs price above 50-day, longer horizons also above 200-day.
        d = d[(d["above_sma50"] > 0) & (d["above_sma50"] < MAX_ABOVE_SMA50)]
        if horizon != "1w":
            d = d[d["above_sma200"] > 0]
        d["score"] = sum(d[f"r_{k}"] * w for k, w in weights.items())
        d = d.sort_values("score", ascending=False)
        d["n"] = d.groupby("gics_sector").cumcount()
        d = d[d["n"] < MAX_PER_GICS_SECTOR].head(TOP_N)
        for t, r in d.iterrows():
            entry = float(r["close"])
            stop = round(entry - stop_k * r["atr"], 2)
            target = round(entry + target_k * r["atr"], 2)
            reasons = []
            for k in weights:
                if k in LABELS:
                    reasons.append(f"{LABELS[k]} {r[k]:+.1%}, ahead of {r[f'r_{k}']:.0f}% of S&P 500 stocks")
                elif k == "vol_ratio":
                    reasons.append(f"Recent volume is {r['vol_ratio']:.1f}x its 30-day average")
            reasons.append(f"Trading {r['above_sma50']:.1%} above its 50-day average")
            if horizon != "1w":
                reasons.append(f"Trading {r['above_sma200']:.1%} above its 200-day average")
            reasons.append(f"Typical daily range (ATR) is {r['atr_pct']:.1f}% of price; stop {stop_k:g}x ATR, target {target_k:g}x ATR")
            out.append((t, r["name"], r["sector"], horizon, round(entry, 2), stop, target, int(round(r["score"])),
                        json.dumps(reasons), json.dumps([]), 0, now, as_of))

    cols = {r[1] for r in conn.execute("PRAGMA table_info(recommendations)")}
    with conn:
        if "as_of" not in cols:
            conn.execute("ALTER TABLE recommendations ADD COLUMN as_of TEXT")
        conn.execute("DELETE FROM recommendations")
        conn.executemany(
            "INSERT INTO recommendations (ticker, name, sector, horizon, entry, stop, target, score, reasons, news, "
            "is_example, generated_at, as_of) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", out)
    for h in HORIZONS:
        top = [o[0] for o in out if o[3] == h][:5]
        print(f"{h}: {sum(1 for o in out if o[3] == h)} ideas, top: {', '.join(top)}")


if __name__ == "__main__":
    main()
