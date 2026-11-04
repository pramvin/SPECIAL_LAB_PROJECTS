# Long-short test of headline sentiment across many stocks (style of Tetlock 2007 / Ke-Kelly-Xiu 2019 / Heston-Sinha).
# RUN ON KAGGLE, one cell per `# P` block, self-contained. Input to add: "Financial News and Stock Price Integration Dataset"
# (elsabetyemane, file raw_analyst_ratings.csv: headline/date/stock, 1.4M rows, 2009 to mid-2020). Internet ON (pip, nltk, yfinance).
# Typed into the Kaggle editor by hand, so no indented blocks except `def`.
# Known limits: prices only for 331 of the 500 most-covered tickers (the rest are delisted/renamed on Yahoo) -> survivorship bias;
# headline-only text; entry = close of the first trading day AFTER the news day (conservative, loses the day-0 reaction); no trading costs.

# P12. Dictionary score per headline (Hu&Liu + McDonald, as in paper_replication.py), prices for the 500 most-covered tickers
import subprocess, sys, glob, os, re
import numpy as np, pandas as pd
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pysentiment2"], check=False)
import pysentiment2 as ps, nltk
nltk.download("opinion_lexicon", quiet=True)
from nltk.corpus import opinion_lexicon as ol
lm = pd.read_csv(os.path.dirname(ps.__file__) + "/static/LM.csv")
lmc = {c.lower(): c for c in lm.columns}
pos_words = set(ol.positive()) | set(lm.loc[lm[lmc["positive"]] > 0, lmc["word"]].str.lower())
neg_words = set(ol.negative()) | set(lm.loc[lm[lmc["negative"]] > 0, lmc["word"]].str.lower())
tok = lambda s: re.findall(r"[a-z]+", s.lower())
bzp = glob.glob("/kaggle/input/**/raw_analyst_ratings.csv", recursive=True)[0]
bz = pd.read_csv(bzp, usecols=["headline", "date", "stock"])
bz["date"] = pd.to_datetime(bz["date"], utc=True, format="mixed")
bz = bz[(bz["date"] >= "2011-01-01") & bz["headline"].notna()].copy()
bz["score"] = bz["headline"].map(lambda s: sum(w in pos_words for w in tok(s)) - sum(w in neg_words for w in tok(s)))
bz["day"] = bz["date"].dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
top = bz["stock"].value_counts().index[:500].tolist()
import yfinance as yf
pxm = yf.download(top, start="2010-12-01", end="2020-09-01", progress=False, auto_adjust=True)["Close"].dropna(axis=1, thresh=1500)
print(len(bz), "headlines |", pxm.shape, "price table (days x tickers kept)")

# P13. Each day rank stocks by that day's mean headline score; long top 20% (score>0), short bottom 20% (score<0)
g = bz[bz["stock"].isin(pxm.columns)].groupby(["day", "stock"], as_index=False)["score"].mean()
ix, cx = pxm.index.searchsorted(g["day"], side="right"), pxm.columns.get_indexer(g["stock"])
def daily_spread(g, col):
    hi = g.groupby("day")[col].transform(lambda s: s.quantile(0.8))
    lo = g.groupby("day")[col].transform(lambda s: s.quantile(0.2))
    t = g.assign(grp=np.select([(g[col] >= hi) & (g[col] > 0), (g[col] <= lo) & (g[col] < 0)], [1, -1], 0)).dropna(subset=["ret"]).groupby(["day", "grp"])["ret"].mean().unstack()
    return (t[1] - t[-1]).dropna()

# t-stat uses every h-th day so 5-day returns do not overlap
summ = lambda s, h: {"days": len(s), "mean_bps": 1e4 * s.iloc[::h].mean(), "t_stat": s.iloc[::h].mean() / s.iloc[::h].std() * len(s.iloc[::h]) ** 0.5, "share_days_positive": (s > 0).mean()}
def run_ls(h):
    rt = (pxm.shift(-h) / pxm - 1).values
    g0 = g.assign(ret=np.where(ix < len(pxm), rt[np.minimum(ix, len(pxm) - 1), cx], np.nan))
    g0["rs"] = g0.groupby("day")["score"].transform(lambda s: s.sample(frac=1, random_state=0).values)
    sp = {c: daily_spread(g0, c) for c in ("score", "rs")}
    return [dict(horizon=h, period=nm, signal="headline score" if c == "score" else "shuffled control", **summ(sp[c][(sp[c].index >= a) & (sp[c].index < b)], h)) for nm, a, b in (("2011-2015", "2011-01-01", "2016-01-01"), ("2016-2020", "2016-01-01", "2021-01-01")) for c in sp]

lsres = pd.DataFrame([r for h in (1, 5) for r in run_ls(h)])
print(lsres.round(3).to_string())

# P15. News BUNDLE per stock (needs `bz`, `pxm` from P12). Decision day t every 5 trading days (so windows never overlap);
# text = all headlines of the last 5 trading days up to t; answer = beats the SAME day's median return across stocks,
# measured from the close of t+1 over 1 or 5 trading days (removes the market's drift). Price features use closes up to t only.
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
dg = {t: s.groupby("day")["headline"].agg(" ".join) for t, s in bz.groupby("stock") if t in pxm.columns}
P = pxm.values
V, M = pxm.pct_change(fill_method=None).rolling(20).std().values, (pxm / pxm.rolling(50).mean() - 1).values
ix = np.arange(50, len(pxm) - 7, 5)
feats = ["f_r1", "f_r5", "f_r20", "f_vol", "f_ma"]
def rows_of(t):
    s, j = dg[t], pxm.columns.get_loc(t)
    a, b = s.index.searchsorted(pxm.index[ix - 5], side="right"), s.index.searchsorted(pxm.index[ix], side="right")
    return pd.DataFrame({"tick": t, "date": pxm.index[ix], "n": b - a, "text": [" ".join(s.values[x:y]) for x, y in zip(a, b)], "r1": P[ix + 2, j] / P[ix + 1, j] - 1, "r5": P[ix + 6, j] / P[ix + 1, j] - 1, "f_r1": P[ix, j] / P[ix - 1, j] - 1, "f_r5": P[ix, j] / P[ix - 5, j] - 1, "f_r20": P[ix, j] / P[ix - 20, j] - 1, "f_vol": V[ix, j], "f_ma": M[ix, j]})

rows = pd.concat([rows_of(t) for t in dg], ignore_index=True)
rows = rows[rows["n"] > 0].dropna(subset=["r1", "r5"] + feats).reset_index(drop=True)
rows["beat1"] = (rows["r1"] > rows.groupby("date")["r1"].transform("median")).astype(int)
rows["beat5"] = (rows["r5"] > rows.groupby("date")["r5"].transform("median")).astype(int)
rows[feats] = rows[feats] - rows.groupby("date")[feats].transform("median")
print(len(rows), "stock-bundles |", rows["tick"].nunique(), "stocks |", rows["date"].nunique(), "decision days | median news-days per bundle", int(rows["n"].median()), "| share beat5", round(rows["beat5"].mean(), 3))

# P16. Text only / price only / text+price (logistic regression, C picked on 2018 by AUC), train 2011-17 (+2018 for the refit), TEST 2019-mid 2020.
# spread = mean return of the top-20% predicted minus bottom-20% predicted stocks per decision day (bps), t over those (non-overlapping) days.
def spr(s, r, dd):
    f = pd.DataFrame({"s": s, "r": r, "d": dd})
    f["q"] = f.groupby("d")["s"].rank(pct=True)
    w = (f[f["q"] >= 0.8].groupby("d")["r"].mean() - f[f["q"] <= 0.2].groupby("d")["r"].mean()).dropna()
    return {"spread_bps": 1e4 * w.mean(), "t": w.mean() / w.std() * len(w) ** 0.5, "days": len(w)}

def run5(col, rcol):
    y, d = rows[col].values, rows["date"]
    m_tr, m_va, m_te = (d < "2018-01-01").values, ((d >= "2018-01-01") & (d < "2019-01-01")).values, (d >= "2019-01-01").values
    T = TfidfVectorizer(stop_words="english", min_df=5, max_features=50000).fit(rows["text"][m_tr | m_va]).transform(rows["text"])
    Pf = csr_matrix(StandardScaler().fit(rows.loc[m_tr | m_va, feats]).transform(rows[feats]))
    X = {"text": T, "price": Pf, "text+price": hstack([T, Pf]).tocsr()}
    best = {k: max([0.1, 1.0], key=lambda C: roc_auc_score(y[m_va], LogisticRegression(C=C, max_iter=300).fit(X[k][m_tr], y[m_tr]).predict_proba(X[k][m_va])[:, 1])) for k in X}
    fin = {k: LogisticRegression(C=best[k], max_iter=300).fit(X[k][m_tr | m_va], y[m_tr | m_va]) for k in X} | {"text (shuffled labels)": LogisticRegression(C=0.1, max_iter=300).fit(T[m_tr | m_va], np.random.default_rng(0).permutation(y[m_tr | m_va]))}
    p = {k: fin[k].predict_proba((X[k] if k in X else T)[m_te])[:, 1] for k in fin}
    return [{"label": col, "features": k, "C": best.get(k, 0.1), "n_test": int(m_te.sum()), "test_auc": roc_auc_score(y[m_te], p[k]), "test_acc": ((p[k] > 0.5) == y[m_te]).mean(), "base": max(y[m_te].mean(), 1 - y[m_te].mean())} | spr(p[k], rows[rcol].values[m_te], d[m_te].values) for k in fin]

res5 = pd.DataFrame([r for c, rc in (("beat1", "r1"), ("beat5", "r5")) for r in run5(c, rc)])
print(res5.round(3).to_string())

# P17. Word weights learned by counting (needs `rows`, `spr` from P15/P16). w_j = log((times word j is in "beat" bundles + 1) / (times in "lag" bundles + 1)),
# learned on 2011-17 only. Bundle score = mean w over its distinct words (divided by word count so long bundles do not win). Then a logistic curve
# P(beat) = 1/(1+exp(-(a+b*score))) is fitted on 2018 only (a, b by gradient descent inside LogisticRegression) and tested ONCE on 2019-mid 2020.
from sklearn.feature_extraction.text import CountVectorizer
def run17(col, rcol, shuffle):
    y, d = rows[col].values, rows["date"]
    m_tr, m_va, m_te = (d < "2018-01-01").values, ((d >= "2018-01-01") & (d < "2019-01-01")).values, (d >= "2019-01-01").values
    X = CountVectorizer(binary=True, stop_words="english", min_df=5, max_features=50000).fit(rows["text"][m_tr]).transform(rows["text"])
    yt = np.random.default_rng(0).permutation(y[m_tr]) if shuffle else y[m_tr]
    w = np.log((np.asarray(X[m_tr][yt == 1].sum(0)).ravel() + 1) / (np.asarray(X[m_tr][yt == 0].sum(0)).ravel() + 1))
    s = (X @ w) / np.maximum(np.asarray(X.sum(1)).ravel(), 1)
    cal = LogisticRegression().fit(s[m_va].reshape(-1, 1), y[m_va])
    p = cal.predict_proba(s[m_te].reshape(-1, 1))[:, 1]
    return {"label": col, "weights": "shuffled labels" if shuffle else "learned", "b": cal.coef_[0][0], "n_test": int(m_te.sum()), "test_auc": roc_auc_score(y[m_te], p), "mean_p": p.mean(), "actual": y[m_te].mean()} | spr(p, rows[rcol].values[m_te], d[m_te].values)

res17 = pd.DataFrame([run17(c, rc, sh) for c, rc in (("beat1", "r1"), ("beat5", "r5")) for sh in (False, True)])
print(res17.round(3).to_string())

# P18. Timing check. 96% of the Benzinga dates have NO time of day (00:00:00; only 4.3% carry a time), so the P12 conversion to New York time moved
# them one calendar day back and the "next-day close" entry of P13 was in fact the SAME-DAY close of the news date. Redone with day = the date as written
# (needs `bz`, `pxm`, dictionary `pos_words`/`neg_words` from P12; same `daily_spread` as P13): entry "left" = close of the news date, "right" = close of the next trading day.
# Same-day entry for a date-only headline can look slightly ahead (the news may have come after the close). The typed Kaggle cell has: bz["day"] = bz["date"].dt.tz_localize(None).dt.normalize(),
# ei = pxm.index.searchsorted(g["day"], side=side), return = pxm.shift(-h)/pxm - 1 at ei, spread top 20% (score>0) minus bottom 20% (score<0), shuffled-score control.
# Result (bps per day-pair, t over non-overlapping days), headline score: same-day 1d -1.2 (t -0.4) / +4.0 (0.9); 5d -15.5 (-0.8) / -54.6 (-1.4);
# next-day 1d -2.6 (-0.9) / -2.3 (-0.6); 5d -17.7 (-1.0) / -59.0 (-1.5) for 2011-15 / 2016-20; shuffled control -4 to +24 bps (|t| <= 1.0).

# P19. Support vector regression on price + indicators + news (needs `rows`, `feats` from P15, `spr` from P16, `pos_words`/`neg_words`/`tok` from P12; the typed cell
# also adds 3 indicators per stock-day from closes only: RSI14 `i_rsi`, MACD histogram / price `i_macd`, Bollinger z-score `i_bb`, and 2 news numbers per bundle:
# `dsc` = (positive - negative dictionary words) / words, `ln` = log(1 + headlines). All features and the targets y1/y5 = return minus that day's median over stocks.)
# SVR(RBF, epsilon 0.1, C in {0.1, 1} chosen on 2018 by Spearman), trained on a random 10,000 bundles of 2011-17, tested once on 2019-mid 2020 (16,923 bundles, 74 days).
from sklearn.svm import SVR
from sklearn.preprocessing import StandardScaler
from scipy.stats import spearmanr
def runsvr(ycol, rcol, fs, nm, shuf):
    d = rows["date"]
    m_tr, m_va, m_te = (d < "2018-01-01").values, ((d >= "2018-01-01") & (d < "2019-01-01")).values, (d >= "2019-01-01").values
    X = StandardScaler().fit(rows.loc[m_tr, fs]).transform(rows[fs])
    y = np.clip(rows[ycol].values / rows.loc[m_tr, ycol].std(), -3, 3)
    sub = np.random.default_rng(0).choice(np.where(m_tr)[0], 10000, replace=False)
    ys = np.random.default_rng(1).permutation(y[sub]) if shuf else y[sub]
    fit = lambda C: SVR(C=C, epsilon=0.1).fit(X[sub], ys)
    best = max([0.1, 1.0], key=lambda C: spearmanr(fit(C).predict(X[m_va]), y[m_va])[0])
    p = fit(best).predict(X[m_te])
    return {"target": ycol, "features": nm + (" (shuffled labels)" if shuf else ""), "C": best, "n_test": int(m_te.sum()), "spearman": spearmanr(p, y[m_te])[0]} | spr(p, rows[rcol].values[m_te], d[m_te].values)
# sets = price (feats) / price+indicators / news (dsc, ln) / all three; y1 and y5; plus the all-features model on shuffled labels as control.
# Result: Spearman -0.026 to +0.007 (shuffled control -0.024 / +0.001); top-minus-bottom 20% spread -30 to +4 bps, |t| <= 1.8 -> no signal in any feature set.

# P20. Data audit, clean long-short, ExtraTrees (Kaggle, same session as P12/P18; typed as cells with no `def` to avoid Kaggle's auto-indent).
# Audit on the 1,314,520 Benzinga rows (2011+): only 29.4% have prices (331 tickers); 18.2% analyst-rating style (regex on upgrade|downgrade|price target|initiates|reiterates|
# maintains|coverage|outperform|underperform|overweight|underweight|rating|analyst|raises/lowers .* target); exact duplicates (stock, day, headline) 0.6%;
# the same headline text listed under >1 stock 46.6% (market round-ups such as "Will the ECB Drag the Market Lower"); ticker written in the headline 8.5%;
# daily price moves beyond 40%: 126 of 812,274. Cleaning = drop duplicates, keep headlines listed under exactly one stock (`nstock == 1`).
# Long-short (dictionary score, next-day close, top/bottom 20%, bps (t)), 2011-15 / 2016-20:
#   all, no duplicates          1d -2.7 (-0.94) / -2.3 (-0.58)   5d -17.6 (-0.97) / -59.2 (-1.55)
#   single-stock headlines      1d -8.1 (-2.57) / -5.7 (-1.34)   5d -10.3 (-0.69) / -2.5 (-0.11)
#   single-stock, not analyst   1d -11.7 (-3.12) / -6.1 (-1.08)  5d  +5.8 (0.32) / -43.1 (-1.48)
#   single-stock, analyst only  1d  +1.1 (0.20) / +1.1 (0.19)    5d +18.2 (0.81) / +43.2 (1.39)
# Null check: 12 runs with shuffled scores (single-stock, 1d) give mean +1.7 / -1.2 bps, std 4.2 / 3.8, min -10 / -9.8 -> the -8.1 is about 2 sd, not clear of chance.
# ExtraTrees (150 trees, min_samples_leaf in {20, 100} chosen on 2018 AUC, class_weight balanced_subsample), 66,476 clean 5-day bundles, train 2011-17, test 2019-mid 2020;
# features: 5 price + RSI/MACD/Bollinger + (log headline count, mean dictionary score, analyst share); big5 = |5d return - day median| in the day's top 20% (base 0.202):
#   big5   test AUC price+indicators 0.713 | news only 0.507 | all 0.712 | shuffled labels 0.523;  top-10% group big5 rate 0.498 (price) / 0.500 (all) vs base 0.202
#   beat1  AUC 0.504 / 0.491 / 0.503 (shuffled 0.490);  beat5 AUC 0.498 / 0.502 / 0.505 (shuffled 0.504);  long-short spreads +/-30 bps, |t| <= 0.9

# P21. Longer horizons (7, 14, 28 trading days) on the same clean 5-day bundles as P20 (single-stock, no duplicates; 66,476 bundles, 331 stocks). Outcome = return from the close
# of the day after the decision day, minus that day's median over stocks; beat{h} = above median, big{h} = |excess return| in the day's top 20% (base 0.202).
# ExtraTrees (100 trees, min_samples_leaf 50), train 2011-18, test 2019-mid 2020; features and sets as in P20. Test AUC (0.5 = guessing):
#   beat7  price+ind 0.498 | news 0.498 | all 0.512   beat14 0.499 | 0.505 | 0.499   beat28 0.489 | 0.511 | 0.509   (shuffled-label control 0.496-0.511)
#   big7   price+ind 0.704 | news 0.499 | all 0.705   big14  0.704 | 0.507 | 0.715   big28  0.705 | 0.496 | 0.715   (shuffled control 0.479-0.525)
# Rank correlation of the news score (mean dictionary score of the 5-day bundle) with the later excess return, test period: 7d +0.015, 14d +0.023, 28d +0.005
# (tiny; the rows are heavily clustered by day, so the apparent significance of 0.023 is overstated).
