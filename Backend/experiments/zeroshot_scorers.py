# Zero-shot headline scorers on the Benzinga test window: dictionary (P12) vs FinBERT vs Laya (the model the app uses now).
# RUN ON KAGGLE with a GPU accelerator (Settings -> Accelerator), Internet ON, after P12 in longshort_benzinga.py (needs `bz`, `pxm`).
# No training: each scorer ranks the stocks that had news on a day; we check whether the top 20% beat the bottom 20% the next day.
# Test window 2019-01 to 2020-08 (same as P16). Trading days only, entry = close of the next trading day (as in P13). No costs.
# Typed into the Kaggle editor by hand, so no indented blocks except `def`.
# Known limits: FinBERT/Laya may have seen 2019-20 news in training (look-ahead risk, cf. Glasserman & Lin); Laya is asked ONE question
# (sentiment), not the two the server asks; Laya score = P(bullish) - P(bearish) from its probabilities (check the raw print).

# P17. Pick the headlines to score and load FinBERT
import os, time, subprocess, sys
os.environ["USE_TF"] = "0"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "laya"], check=False)
import torch
from transformers import pipeline
from sklearn.metrics import roc_auc_score
tdays = pxm.index[(pxm.index >= "2019-01-01") & (pxm.index < "2020-08-20")]
sub = bz[bz["stock"].isin(pxm.columns) & bz["day"].isin(tdays)].copy()
sub["txt"] = sub["headline"].str.slice(0, 500)
texts = sub["txt"].unique().tolist()
print(len(sub), "headlines on", len(tdays), "trading days |", len(texts), "unique texts | GPU:", torch.cuda.is_available())

# P18. FinBERT score = P(positive) - P(negative)
fbp = pipeline("text-classification", model="ProsusAI/finbert", device=0, truncation=True, batch_size=64, top_k=None)
t0 = time.time()
fbd = [{x["label"].lower(): x["score"] for x in o} for o in fbp(texts)]
fbs = dict(zip(texts, [d["positive"] - d["negative"] for d in fbd]))
print("FinBERT done in", round(time.time() - t0), "s")

# P19. Laya: load, look at one raw answer, time 100 headlines (decide from the speed whether to score all or a sample)
import laya
Q = {"sentiment": {"type": "choice", "instructions": "What is the likely effect of this financial news on the stock price?", "criteria": {"bearish": "negative for the stock price", "bullish": "positive for the stock price", "neutral": "no clear effect, or purely informational"}}}
agent = laya.load("convaiinnovations/laya")
print(agent.predict(texts[0], Q))
t0 = time.time()
tmp = [agent.predict(s, Q) for s in texts[:100]]
print("Laya ms per headline:", round(10 * (time.time() - t0), 1))

# P20. Laya on every unique text (if too slow, set `texts = texts[:N]` and rerun P21 with `sub = sub[sub["txt"].isin(texts)]`)
def lscore(r):
    p = r["answers"]["sentiment"]["probabilities"]
    return p["bullish"] - p["bearish"]

lay = dict(zip(texts, [lscore(agent.predict(s, Q)) for s in texts]))
print("Laya done:", len(lay))

# P21. Per stock-day mean score -> does the top 20% beat the bottom 20% the next day (1 day) / next 5 days (every 5th day)? Shuffled control included.
sub["fin"], sub["lay"] = sub["txt"].map(fbs), sub["txt"].map(lay)
sc = sub.groupby(["day", "stock"], as_index=False)[["score", "fin", "lay"]].mean()
ix1, cx1 = pxm.index.searchsorted(sc["day"], side="right"), pxm.columns.get_indexer(sc["stock"])
sc["r1"] = (pxm.shift(-1) / pxm - 1).values[ix1, cx1]
sc["r5"] = (pxm.shift(-5) / pxm - 1).values[ix1, cx1]
sc["rand"] = sc.groupby("day")["score"].transform(lambda s: s.sample(frac=1, random_state=0).values)
def ev(col, rcol, h):
    f = sc.dropna(subset=[col, rcol]).copy()
    f = f[f.groupby("day")[col].transform("size") >= 10]
    f["q"] = f.groupby("day")[col].rank(pct=True)
    w = (f[f["q"] >= 0.8].groupby("day")[rcol].mean() - f[f["q"] <= 0.2].groupby("day")[rcol].mean()).dropna().iloc[::h]
    y = (f[rcol] > f.groupby("day")[rcol].transform("median")).astype(int)
    return {"scorer": col, "horizon": h, "days": len(w), "rows": len(f), "auc": roc_auc_score(y, f["q"]), "spread_bps": 1e4 * w.mean(), "t": w.mean() / w.std() * len(w) ** 0.5}

res6 = pd.DataFrame([ev(c, r, h) for c in ("score", "fin", "lay", "rand") for r, h in (("r1", 1), ("r5", 5))])
print(res6.round(3).to_string())
print(sc[["score", "fin", "lay"]].corr(method="spearman").round(2).to_string())
print("share of stock-days labelled bullish / bearish by each scorer:", {c: (round((sc[c] > 0.2).mean(), 3), round((sc[c] < -0.2).mean(), 3)) for c in ("fin", "lay")})
