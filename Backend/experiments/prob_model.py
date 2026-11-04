# Probability model: news scores + chart indicators -> P(stock beats the market median) and P(big move), per stock-day. No social data (see below).
# RUN ON KAGGLE (GPU, Internet ON), after P12 in longshort_benzinga.py (needs `bz`, `pxm`). Typed by hand: no indented blocks except `def`.
# Universe = 330 Benzinga tickers with Yahoo prices (survivors only). Decision day t = every trading day; news up to t (weekend news goes to the next
# trading day), entry = close of t+1, outcome = return from t+1 to t+2 (1 day) or t+6 (5 days). Targets are RELATIVE to the same day's cross-section:
#   beat1/beat5 = return above that day's median over all stocks · big5 = |5-day return - day median| in that day's top 20% (base rate 20%).
# Split by time: train 2011-2016, validation 2017 (isotonic calibration), test 2018 to mid-2020 reported per year.
# Social sentiment is NOT used: the Reddit API only lists ~1000 recent items, so there is no 2011-2020 history to train on.

# P22. FinBERT score (P(positive) - P(negative)) for every unique headline of the 330 stocks; fp16, sorted by length; saved to /kaggle/working/fbs.pkl
import os, time, pickle
os.environ["USE_TF"] = "0"
import torch
from transformers import pipeline
allb = bz[bz["stock"].isin(pxm.columns)].copy()
allb["txt"] = allb["headline"].str.slice(0, 300)
texts = sorted(allb["txt"].unique().tolist(), key=len)
print(len(allb), "headlines |", len(texts), "unique texts")
fbp = pipeline("text-classification", model="ProsusAI/finbert", device=0, truncation=True, max_length=96, batch_size=128, top_k=None, torch_dtype=torch.float16)
t0 = time.time()
fbd = [{x["label"].lower(): x["score"] for x in o} for o in fbp(texts)]
fbs = dict(zip(texts, [d["positive"] - d["negative"] for d in fbd]))
pickle.dump(fbs, open("/kaggle/working/fbs.pkl", "wb"))
print("FinBERT done in", round((time.time() - t0) / 60, 1), "min")

# P23. Chart indicators + news features per (trading day, stock), targets, relative-to-the-day features
import yfinance as yf
pv = yf.download(pxm.columns.tolist(), start="2010-12-01", end="2020-09-01", progress=False, auto_adjust=True)["Volume"].reindex(index=pxm.index, columns=pxm.columns)
r1 = pxm.pct_change(fill_method=None)
dl, ds = r1.clip(lower=0).rolling(14).mean(), (-r1.clip(upper=0)).rolling(14).mean()
F = {"r1": r1, "r5": pxm.pct_change(5, fill_method=None), "r20": pxm.pct_change(20, fill_method=None), "r60": pxm.pct_change(60, fill_method=None), "vol20": r1.rolling(20).std(), "vol5": r1.rolling(5).std(), "ma50": pxm / pxm.rolling(50).mean() - 1, "rsi": 100 - 100 / (1 + dl / ds), "macd": (pxm.ewm(span=12).mean() - pxm.ewm(span=26).mean()) / pxm, "volx": pv / pv.rolling(20).mean()}
allb["p"] = pxm.index.searchsorted(allb["day"], side="left")
allb = allb[allb["p"] < len(pxm)].copy()
allb["j"] = pxm.columns.get_indexer(allb["stock"])
allb["fin"] = allb["txt"].map(fbs)
allb["one"] = 1.0
allb["neg"], allb["pos_"] = (allb["fin"] < -0.3).astype(float), (allb["fin"] > 0.3).astype(float)
def acc(col):
    A = np.zeros(pxm.shape)
    np.add.at(A, (allb["p"].values, allb["j"].values), allb[col].values)
    return pd.DataFrame(A, index=pxm.index, columns=pxm.columns)

C, S, Dd, NG, PS = [acc(c) for c in ("one", "fin", "score", "neg", "pos_")]
R = lambda A: A.rolling(5, min_periods=1).sum()
C5 = R(C).where(R(C) > 0)
news = {"n0": np.log1p(C), "n5": np.log1p(R(C)), "s0": S / C.where(C > 0), "s5": R(S) / C5, "d5": R(Dd) / C5, "neg5": R(NG) / C5, "pos5": R(PS) / C5}
allf = {**F, **news, "y1": pxm.shift(-2) / pxm.shift(-1) - 1, "y5": pxm.shift(-6) / pxm.shift(-1) - 1}
D = pd.concat({k: v.stack(dropna=False) for k, v in allf.items()}, axis=1).replace([np.inf, -np.inf], np.nan)
price_f, news_f = list(F), list(news)
D = D.dropna(subset=price_f + ["y1", "y5"]).copy()
D[news_f] = D[news_f].fillna(0)
D = D[D.index.get_level_values(0) >= "2011-03-01"].copy()
rel = [c for c in price_f + news_f if c not in ("n0", "n5")]
D[rel] = D[rel] - D.groupby(level=0)[rel].transform("median")
D["beat1"] = (D["y1"] > D.groupby(level=0)["y1"].transform("median")).astype(int)
D["beat5"] = (D["y5"] > D.groupby(level=0)["y5"].transform("median")).astype(int)
dev = (D["y5"] - D.groupby(level=0)["y5"].transform("median")).abs()
D["big5"] = (dev > dev.groupby(level=0).transform(lambda s: s.quantile(0.8))).astype(int)
print(D.shape, "stock-days | stocks", D.index.get_level_values(1).nunique(), "| base rates beat1/beat5/big5:", D[["beat1", "beat5", "big5"]].mean().round(3).tolist(), "| share with news in last 5 days:", round((D["n5"] > 0).mean(), 3))

# P24. chart only / news only / chart+news x logistic / gradient boosting / small neural net, trained 2011-16, calibrated on 2017, tested 2018-mid 2020
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
mods = {"logit": lambda: LogisticRegression(C=0.1, max_iter=300), "gbm": lambda: HistGradientBoostingClassifier(max_depth=4, learning_rate=0.05, max_iter=200, l2_regularization=1.0, random_state=0), "nn": lambda: MLPClassifier((32, 16), alpha=1e-2, batch_size=2048, max_iter=15, random_state=0)}
FS = {"chart": price_f, "news": news_f, "chart+news": price_f + news_f}
dts = D.index.get_level_values(0)
m_tr, m_va, m_te = (dts < "2017-01-01"), ((dts >= "2017-01-01") & (dts < "2018-01-01")), (dts >= "2018-01-01")
yrs = dts[m_te].year
def fit_eval(tgt, fs, mn):
    X, y = D[FS[fs]].values, D[tgt].values
    m = make_pipeline(StandardScaler(), mods[mn]()).fit(X[m_tr], y[m_tr])
    pva, pte = m.predict_proba(X[m_va])[:, 1], m.predict_proba(X[m_te])[:, 1]
    pcal = IsotonicRegression(out_of_bounds="clip").fit(pva, y[m_va]).predict(pte)
    bs = lambda p: 1 - brier_score_loss(y[m_te], p) / brier_score_loss(y[m_te], np.full(m_te.sum(), y[m_tr].mean()))
    out = {"target": tgt, "features": fs, "model": mn, "val_auc": roc_auc_score(y[m_va], pva), **{f"auc{k}": roc_auc_score(y[m_te][yrs == k], pte[yrs == k]) for k in (2018, 2019, 2020)}, "brier_skill_raw": bs(pte), "brier_skill_cal": bs(pcal)}
    return out

res7 = pd.DataFrame([fit_eval(t, fs, mn) for t in ("beat1", "beat5", "big5") for fs in FS for mn in mods])
print(res7.round(3).to_string())

# P25. Calibration of P(big move in the next 5 days), chart+news gradient boosting, test 2018-mid 2020: 10 equal groups, lowest to highest predicted probability
X, y = D[FS["chart+news"]].values, D["big5"].values
m = make_pipeline(StandardScaler(), mods["gbm"]()).fit(X[m_tr], y[m_tr])
pva, pte = m.predict_proba(X[m_va])[:, 1], m.predict_proba(X[m_te])[:, 1]
pcal = IsotonicRegression(out_of_bounds="clip").fit(pva, y[m_va]).predict(pte)
tb = pd.DataFrame({"p": pcal, "y": y[m_te], "yr": yrs})
tb["group"] = pd.qcut(tb["p"].rank(method="first"), 10, labels=False) + 1
print(tb.groupby("group").agg(predicted=("p", "mean"), actual=("y", "mean"), rows=("y", "size")).round(3).to_string())
print("actual rate in the top group by year:", tb[tb["group"] == 10].groupby("yr")["y"].mean().round(3).to_dict(), "| base rate", round(tb["y"].mean(), 3))
