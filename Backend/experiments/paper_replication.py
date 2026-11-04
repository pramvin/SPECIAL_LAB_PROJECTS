# Replication of Joshi et al. 2016 "Stock Trend Prediction Using News Sentiment Analysis" (arXiv 1607.01958).
# RUN ON KAGGLE, one cell per `# P` block, in one session. Inputs to add to the notebook:
#   "Apple Stock (AAPL): Historical Financial News Data" (frankossai/apple-stock-aapl-historical-financial-news-data)
# Internet must be ON (pip + nltk data are fetched on the Kaggle machine, not locally).
# Typed into the Kaggle editor by hand: no indented blocks except `def run`.
# Differences from the paper (not hidden): sklearn instead of Weka · their 92 articles and exact word lists are unknown ·
# our stop-word list is our own approximation · dictionary = Hu&Liu (NLTK) + McDonald (pysentiment2), de-duplicated.

# P1. Dictionaries (paper: general words + McDonald finance words)
import subprocess, sys, glob, os
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pysentiment2"], check=False)
import pysentiment2 as ps
print(glob.glob(os.path.dirname(ps.__file__) + "/**/*.csv", recursive=True))
import nltk
nltk.download("opinion_lexicon", quiet=True)
from nltk.corpus import opinion_lexicon as ol
print("Hu&Liu words:", len(ol.positive()), "positive,", len(ol.negative()), "negative")

# P2. Look at the McDonald file and the Apple news file
import pandas as pd, re
lm = pd.read_csv(os.path.dirname(ps.__file__) + "/static/LM.csv")
print(lm.columns.tolist(), len(lm))
ap = glob.glob("/kaggle/input/**/apple_news_data.csv", recursive=True)[0]
news = pd.read_csv(ap)
print(ap, news.shape)

# P3. Paper step 1: label every article by dictionary (Score = #positive - #negative; Score >= 0 -> positive)
lmc = {c.lower(): c for c in lm.columns}
lm_pos = set(lm.loc[lm[lmc["positive"]] > 0, lmc["word"]].str.lower())
lm_neg = set(lm.loc[lm[lmc["negative"]] > 0, lmc["word"]].str.lower())
pos_words, neg_words = set(ol.positive()) | lm_pos, set(ol.negative()) | lm_neg
print("McDonald:", len(lm_pos), "pos,", len(lm_neg), "neg | combined:", len(pos_words), "pos,", len(neg_words), "neg | paper: 2360 pos, 7383 neg")
news = news.dropna(subset=["title", "content"]).copy()
news["date"] = pd.to_datetime(news["date"], utc=True, format="mixed")
news["text"] = news["title"].astype(str) + " " + news["content"].astype(str)
tok = lambda s: re.findall(r"[a-z]+", s.lower())
news["tokens"] = news["text"].map(tok)
news["score"] = news["tokens"].map(lambda t: sum(w in pos_words for w in t) - sum(w in neg_words for w in t))
news["label"] = (news["score"] >= 0).astype(int)
news = news.sort_values("date").reset_index(drop=True)
print(len(news), "articles | share positive", round(news["label"].mean(), 3), "| score exactly 0:", round((news["score"] == 0).mean(), 3))

# P4. Paper pre-processing: tokenize, stop-words (general + finance), stemming; tf-idf with min document frequency 3 is in P5
from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
fin_stop = set("january february march april may june july august september october november december monday tuesday wednesday thursday friday saturday sunday dollar dollars usd eur euro euros yen cents million billion trillion percent year week day quarter fiscal china chinese india europe european asia america american united states york california japan korea taiwan london canada germany".split())
stops = ENGLISH_STOP_WORDS | fin_stop
st, cache = PorterStemmer(), {}
stem = lambda w: cache[w] if w in cache else cache.setdefault(w, st.stem(w))
news["clean"] = news["tokens"].map(lambda t: " ".join(stem(w) for w in t if len(w) > 2 and w not in stops))

# P5a. Paper's evaluation at PAPER SCALE: 92 articles, 5/10/15-fold CV, 70%/80% split, plus 20 unseen later articles; 30 random draws
import numpy as np
from sklearn.model_selection import cross_val_score, StratifiedKFold, train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier
mk = {"RandomForest": lambda: RandomForestClassifier(n_estimators=100, random_state=0, n_jobs=-1), "NaiveBayes": lambda: MultinomialNB(), "SVM": lambda: LinearSVC()}
cv = lambda k: (lambda m, X, y: cross_val_score(m, X, y, cv=StratifiedKFold(k, shuffle=True, random_state=0)).mean())
sp = lambda f: (lambda m, X, y: (lambda a: m.fit(X[a[0]], y[a[0]]).score(X[a[1]], y[a[1]]))(train_test_split(np.arange(len(y)), train_size=f, stratify=y, random_state=0)))
opts = {"5-fold": cv(5), "10-fold": cv(10), "15-fold": cv(15), "70% split": sp(0.7), "80% split": sp(0.8)}
known = news[(news["date"] >= "2021-01-01") & (news["date"] < "2024-01-01")]
later = news[news["date"] >= "2024-01-01"]
def run(seed):
    tr, un = known.iloc[np.random.default_rng(seed).choice(len(known), 92, replace=False)], later.sample(20, random_state=seed)
    vec = TfidfVectorizer(min_df=3)
    X, y = vec.fit_transform(tr["clean"]), tr["label"].values
    Xu, yu = vec.transform(un["clean"]), un["label"].values
    return {(n, o): f(mk[n](), X, y) for n in mk for o, f in opts.items()} | {(n, "unseen 20"): mk[n]().fit(X, y).score(Xu, yu) for n in mk}

res = pd.DataFrame([run(s) for s in range(30)])
res.columns = pd.MultiIndex.from_tuples(res.columns)
print("PAPER SCALE (92 articles, 30 random draws) mean accuracy vs dictionary label:")
print(res.mean().unstack().round(3).to_string())
print("std across draws:")
print(res.std().unstack().round(3).to_string())
print("share labelled positive in the sample pool:", round(known["label"].mean(), 3))

# P5b. FULL SCALE: train on ALL 2021-2023 articles, test on ALL 2024 articles (label = paper's dictionary label)
from sklearn.metrics import f1_score
vec = TfidfVectorizer(min_df=3)
Xk, yk = vec.fit_transform(known["clean"]), known["label"].values
Xl, yl = vec.transform(later["clean"]), later["label"].values
fit = {n: mk[n]().fit(Xk, yk) for n in mk}
rows = [f"{n:13s} accuracy {m.score(Xl, yl):.3f} | macro-F1 {f1_score(yl, m.predict(Xl), average='macro'):.3f}" for n, m in fit.items()]
print(f"FULL SCALE: train {len(known):,} (2021-23) -> test {len(later):,} (2024) | features {Xk.shape[1]:,} | always-positive baseline {max(yl.mean(), 1 - yl.mean()):.3f}", *rows, sep=chr(10))

# P6. Paper step 3 with numbers: does daily news sentiment (dictionary score) go with AAPL's next-week move?
# Entry = close of the first trading day AFTER the news day (time of day unknown); exit = 5 trading days later.
import yfinance as yf
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
px = yf.download("AAPL", start="2020-12-01", end="2024-12-31", progress=False, auto_adjust=True)["Close"].squeeze()
px.index = pd.to_datetime(px.index).tz_localize(None)
news["day"] = news["date"].dt.tz_localize(None).dt.normalize()
daily = news[news["date"] >= "2021-01-01"].groupby("day")["score"].agg(["mean", "count"])
pos = px.index.searchsorted(daily.index, side="right")
ok = pos + 5 < len(px)
daily = daily[ok].assign(ret5=[px.iloc[i + 5] / px.iloc[i] - 1 for i in pos[ok]])
up, sent_pos = daily["ret5"] > 0, daily["mean"] >= 0
r, p = spearmanr(daily["mean"], daily["ret5"])
print(f"{len(daily)} days | Spearman correlation(daily mean score, next-week return) = {r:.3f} (p={p:.3f})")
print(f"sentiment sign matches next-week direction on {(sent_pos == up).mean():.3f} of days | always-up baseline {max(up.mean(), 1 - up.mean()):.3f}")
print(daily.groupby(pd.qcut(daily["mean"], 3, duplicates="drop"), observed=True)["ret5"].agg(["count", "mean", lambda s: (s > 0).mean()]).round(4).to_string())
fig, ax = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
ax[0].scatter(daily.index, daily["mean"], s=4)
ax[0].set_ylabel("daily mean news score")
ax[1].plot(px.index, px.values)
ax[1].set_ylabel("AAPL close")
plt.show()

# P7. Price as the answer: label each Apple article by AAPL's next-week move; train 2021-23, test 2024 (needs `px` from P6)
art = news[news["date"] >= "2021-01-01"].copy()
art["day"] = art["date"].dt.tz_localize(None).dt.normalize()
pos = px.index.searchsorted(art["day"], side="right")
ok = pos + 5 < len(px)
art = art[ok].assign(ret5=[px.iloc[i + 5] / px.iloc[i] - 1 for i in pos[ok]])
art["up"] = (art["ret5"] > 0).astype(int)
trn, tst = art[art["date"] < "2024-01-01"], art[art["date"] >= "2024-01-01"]
vec = TfidfVectorizer(min_df=3)
Xa, ya = vec.fit_transform(trn["clean"]), trn["up"].values
Xb, yb = vec.transform(tst["clean"]), tst["up"].values
fit = {n: mk[n]().fit(Xa, ya) for n in mk}
shuf = LinearSVC().fit(Xa, np.random.default_rng(0).permutation(ya)).predict(Xb)
rows = [f"{n:13s} accuracy {m.score(Xb, yb):.3f} | macro-F1 {f1_score(yb, m.predict(Xb), average='macro'):.3f} | predicts up {m.predict(Xb).mean():.2f}" for n, m in fit.items()]
rows.append(f"shuffled-label accuracy {(shuf == yb).mean():.3f}  (control)")
print(f"PRICE LABEL: train {len(trn):,} (2021-23, share up {ya.mean():.3f}) -> test {len(tst):,} (2024, share up {yb.mean():.3f}) | always-up {max(yb.mean(), 1 - yb.mean()):.3f}", *rows, sep=chr(10))

# P9. Step 2: horizon 1 day vs 5 days, train only on the biggest moves, TEST ON ALL 2024 articles (needs `px` from P6)
# (the notebook also has a cell P8 with ev(), added by the user, that filters the TEST set by move size too; not copied here)
base = news[news["date"] >= "2021-01-01"].copy()
base["day"] = base["date"].dt.tz_localize(None).dt.normalize()
p0 = px.index.searchsorted(base["day"], side="right")
def ev2(h, q):
    ok = p0 + h < len(px)
    a = base[ok].assign(ret=[px.iloc[i + h] / px.iloc[i] - 1 for i in p0[ok]])
    trn, tst = a[a["date"] < "2024-01-01"], a[a["date"] >= "2024-01-01"]
    trn = trn[trn["ret"].abs() >= trn["ret"].abs().quantile(q)]
    vec = TfidfVectorizer(min_df=3)
    Xa, ya = vec.fit_transform(trn["clean"]), (trn["ret"] > 0).astype(int).values
    Xb, yb = vec.transform(tst["clean"]), (tst["ret"] > 0).astype(int).values
    return {"horizon": f"{h} day", "train_on": f"top {round((1 - q) * 100)}% moves ({len(trn):,})", "n_test": len(tst), "always_up": max(yb.mean(), 1 - yb.mean()), **{n: mk[n]().fit(Xa, ya).score(Xb, yb) for n in mk}}

print(pd.DataFrame([ev2(h, q) for h in (1, 5) for q in (0, 0.5, 2 / 3)]).round(3).to_string())

# P10. TUNE on a time-ordered validation split (fit 2021-22, validate 2023), then refit on 2021-23 and TEST ONCE on 2024
# (needs `base`, `p0`, `px`, `mk` from P6/P9). AUC on test is threshold-free: 0.5 = no signal.
from sklearn.model_selection import ParameterGrid
from sklearn.metrics import roc_auc_score
vecs = [dict(min_df=3, ngram_range=(1, 1)), dict(min_df=5, ngram_range=(1, 2), max_features=30000)]
grids = {"NaiveBayes": (lambda **k: MultinomialNB(**k), {"alpha": [0.1, 0.3, 1.0, 3.0]}), "SVM": (lambda **k: LinearSVC(**k), {"C": [0.01, 0.03, 0.1, 0.3, 1.0]}), "RandomForest": (lambda **k: RandomForestClassifier(n_estimators=100, random_state=0, n_jobs=-1, **k), {"min_samples_leaf": [5, 20], "max_depth": [None, 20]})}
sc_of = lambda m, X: m.predict_proba(X)[:, 1] if hasattr(m, "predict_proba") else m.decision_function(X)
def tune(h, q):
    ok = p0 + h < len(px)
    a = base[ok].assign(ret=[px.iloc[i + h] / px.iloc[i] - 1 for i in p0[ok]])
    a["up"] = (a["ret"] > 0).astype(int)
    filt = lambda d: d[d["ret"].abs() >= d["ret"].abs().quantile(q)]
    pre, va, te = a[a["date"] < "2023-01-01"], a[(a["date"] >= "2023-01-01") & (a["date"] < "2024-01-01")], a[a["date"] >= "2024-01-01"]
    tr, tv = filt(pre), filt(a[a["date"] < "2024-01-01"])
    V = [TfidfVectorizer(**v).fit(tr["clean"]) for v in vecs]
    Xtr, Xva = [v.transform(tr["clean"]) for v in V], [v.transform(va["clean"]) for v in V]
    sc = [(grids[n][0](**p).fit(Xtr[i], tr["up"]).score(Xva[i], va["up"]), i, n, p) for i in range(len(vecs)) for n in grids for p in ParameterGrid(grids[n][1])]
    best = {n: max((s for s in sc if s[2] == n), key=lambda s: s[0]) for n in grids}
    V2 = [TfidfVectorizer(**v).fit(tv["clean"]) for v in vecs]
    fin = {n: grids[n][0](**b[3]).fit(V2[b[1]].transform(tv["clean"]), tv["up"]) for n, b in best.items()}
    Xte = [v.transform(te["clean"]) for v in V2]
    return [{"horizon": h, "train_on": f"top {round((1 - q) * 100)}%", "model": n, "best_params": str(b[3]) + f" vec{b[1]}", "val_acc": b[0], "val_always_up": max(va["up"].mean(), 1 - va["up"].mean()), "test_acc": fin[n].score(Xte[b[1]], te["up"]), "test_always_up": max(te["up"].mean(), 1 - te["up"].mean()), "test_auc": roc_auc_score(te["up"], sc_of(fin[n], Xte[b[1]]))} for n, b in best.items()]

tuned = pd.DataFrame([r for h in (1, 5) for q in (0, 0.5) for r in tune(h, q)])
print(tuned[["horizon", "train_on", "model", "val_acc", "val_always_up", "test_acc", "test_always_up", "test_auc"]].round(3).to_string())

# P11. Step 3: add past-price features. TEXT only / PRICE only / TEXT+PRICE (logistic regression, C picked on 2023 validation by AUC, tested once on 2024)
# Price features use closes up to the last trading day on/before the news day (entry is the NEXT day's close), so no look-ahead.
# Early 2021 rows have incomplete 20/50-day windows (filled with 0).
from scipy.sparse import hstack, csr_matrix
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
r1 = px.pct_change()
F = pd.DataFrame({"r1": r1, "r5": px.pct_change(5), "r20": px.pct_change(20), "vol20": r1.rolling(20).std(), "ma50": px / px.rolling(50).mean() - 1}).fillna(0)
build = lambda txt, Fa, fm: (lambda T, P: {"text": T, "price": csr_matrix(P), "text+price": hstack([T, csr_matrix(P)]).tocsr()})(TfidfVectorizer(min_df=3).fit(txt[fm]).transform(txt), StandardScaler().fit(Fa[fm]).transform(Fa))
fitp = lambda X, y, fm, em, C: LogisticRegression(C=C, max_iter=1000).fit(X[fm], y[fm]).predict_proba(X[em])[:, 1]
def run3(h):
    ok = p0 + h < len(px)
    a = base[ok].assign(ret=[px.iloc[i + h] / px.iloc[i] - 1 for i in p0[ok]])
    Fa, y, txt, d = F.iloc[p0[ok] - 1].values, (a["ret"] > 0).astype(int).values, a["clean"].values, a["date"]
    m_tr, m_va, m_te = (d < "2023-01-01").values, ((d >= "2023-01-01") & (d < "2024-01-01")).values, (d >= "2024-01-01").values
    Xv, Xf = build(txt, Fa, m_tr), build(txt, Fa, m_tr | m_va)
    bestC = {k: max([0.1, 1, 10], key=lambda C: roc_auc_score(y[m_va], fitp(Xv[k], y, m_tr, m_va, C))) for k in Xv}
    return [{"horizon": h, "features": k, "C": bestC[k], "val_auc": roc_auc_score(y[m_va], fitp(Xv[k], y, m_tr, m_va, bestC[k])), "test_acc": ((fitp(Xf[k], y, m_tr | m_va, m_te, bestC[k]) > 0.5) == y[m_te]).mean(), "test_always_up": max(y[m_te].mean(), 1 - y[m_te].mean()), "test_auc": roc_auc_score(y[m_te], fitp(Xf[k], y, m_tr | m_va, m_te, bestC[k]))} for k in Xv]

res3 = pd.DataFrame([r for h in (1, 5) for r in run3(h)])
print(res3.round(3).to_string())

# P14. News BUNDLE (self-contained: needs only the Apple input + Internet ON, so it can run first in a fresh session).
# One row per trading day t = all Apple articles of the last 5 trading days (up to and incl. t) glued into one text.
# Answer = AAPL return from the close of t+1 (first trading day after the news) to 1 or 5 trading days later. Never uses news after t.
# Train = 2021-23, test = 2024. Same cleaning as P4 (stop words, Porter stemming), tf-idf min_df 3, same three models as the paper.
import glob, re
import numpy as np, pandas as pd, yfinance as yf
from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
fin_stop = set("january february march april may june july august september october november december monday tuesday wednesday thursday friday saturday sunday dollar dollars usd eur euro euros yen cents million billion trillion percent year week day quarter fiscal china chinese india europe european asia america american united states york california japan korea taiwan london canada germany".split())
stops = ENGLISH_STOP_WORDS | fin_stop
st, cache = PorterStemmer(), {}
stem = lambda w: cache[w] if w in cache else cache.setdefault(w, st.stem(w))
news = pd.read_csv(glob.glob("/kaggle/input/**/apple_news_data.csv", recursive=True)[0]).dropna(subset=["title", "content"]).copy()
news["date"] = pd.to_datetime(news["date"], utc=True, format="mixed")
news["day"] = news["date"].dt.tz_localize(None).dt.normalize()
news["clean"] = (news["title"].astype(str) + " " + news["content"].astype(str)).map(lambda s: " ".join(stem(w) for w in re.findall(r"[a-z]+", s.lower()) if len(w) > 2 and w not in stops))
px = yf.download("AAPL", start="2020-12-01", end="2024-12-31", progress=False, auto_adjust=True)["Close"].squeeze()
px.index = pd.to_datetime(px.index).tz_localize(None)
mk = {"RandomForest": lambda: RandomForestClassifier(n_estimators=100, random_state=0, n_jobs=-1), "NaiveBayes": lambda: MultinomialNB(), "SVM": lambda: LinearSVC()}
sc_of = lambda m, X: m.predict_proba(X)[:, 1] if hasattr(m, "predict_proba") else m.decision_function(X)
g = news[news["date"] >= "2021-01-01"].groupby("day")["clean"].agg(" ".join)
ix = np.arange(5, len(px) - 6)
a, b = g.index.searchsorted(px.index[ix - 5], side="right"), g.index.searchsorted(px.index[ix], side="right")
bund = pd.DataFrame({"date": px.index[ix], "n": b - a, "text": [" ".join(g.values[x:y]) for x, y in zip(a, b)], "r1": px.values[ix + 2] / px.values[ix + 1] - 1, "r5": px.values[ix + 6] / px.values[ix + 1] - 1})
bund = bund[(bund["n"] > 0) & (bund["date"] >= "2021-01-08")].reset_index(drop=True)
print(len(bund), "bundles | median articles per bundle", int(bund["n"].median()), "| train", (bund["date"] < "2024-01-01").sum(), "| test", (bund["date"] >= "2024-01-01").sum())
def ev3(col):
    tr, te = bund[bund["date"] < "2024-01-01"], bund[bund["date"] >= "2024-01-01"]
    vec = TfidfVectorizer(min_df=3)
    Xa, ya, Xb, yb = vec.fit_transform(tr["text"]), (tr[col] > 0).astype(int).values, vec.transform(te["text"]), (te[col] > 0).astype(int).values
    sh = LinearSVC().fit(Xa, np.random.default_rng(0).permutation(ya))
    fit = {n: mk[n]().fit(Xa, ya) for n in mk} | {"shuffled SVM": sh}
    return [{"label": col, "model": n, "n_test": len(yb), "acc": m.score(Xb, yb), "always_up": max(yb.mean(), 1 - yb.mean()), "auc": roc_auc_score(yb, sc_of(m, Xb))} for n, m in fit.items()]

res4 = pd.DataFrame([r for c in ("r1", "r5") for r in ev3(c)])
print(res4.round(3).to_string())
nte = (bund["date"] >= "2024-01-01").sum()
print("5-day rows overlap, so independent test rows ~", nte // 5, "-> accuracy noise about +/-", round(1.96 * (0.25 / (nte / 5)) ** 0.5, 3))
