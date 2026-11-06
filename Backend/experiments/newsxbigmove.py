# News score x big-move group: inside stocks the big-move model ranks high, does the news score also get direction right?
# RUN ON KAGGLE ONLY (CPU is enough, Internet ON). Never run this on the user's machine.
# Input: Kaggle dataset "Financial News and Stock Price Integration Dataset" (elsabetyemane, raw_analyst_ratings.csv, 2011 to mid-2020).
# Style follows longshort_benzinga.py and zeroshot_scorers.py: one "# P" block per Kaggle cell, no top-level indented blocks except `def`.
#
# Question (2026-11-05 discussion): the big-move model tells WHEN a stock is likely to move, the news score may tell WHICH WAY,
# maybe only inside high-move names. This script tests that small idea once on a held-out window.
#
# NEWS SCORERS (two, both CPU-only):
#   - `svm`: paper-style tf-idf (unigram+bigram, min_df 3, finance stop words + Porter stemming) trained on pre-test
#     Benzinga headlines to reproduce the sign of the dictionary score; score = LinearSVC decision_function.
#   - `score`: the raw Hu&Liu + McDonald dictionary score (the paper's label source), as a baseline.
#
# PRE-REGISTERED PASS RULE (set BEFORE any result is seen; do not edit after looking at output):
#   A cell passes only if ALL THREE hold in the held-out test window:
#     1. net spread > 0 after costs (top-20% news score minus bottom-20%, inside the group)
#     2. net t > 2, where net t = (mean return - 4*COST_BPS/1e4) / std * sqrt(n) over NON-OVERLAPPING days
#        (for a 5-day horizon every phase is computed and the mean over the 5 phases is used)
#     3. observed net spread > the 95th percentile of a 200-shuffle null (news scores shuffled within day)
#   COSTS: COST_BPS = 10 bps one-way per FILL. Entering and exiting BOTH legs takes 4 fills, so a top-minus-bottom
#   pair pays 4 * COST_BPS = 40 bps once per holding period.
#   The confirmation set is 4 cells (2 scorers x 2 horizons) in the HIGH group; ONLY the primary cell (SVM, 1 day)
#   decides pass/fail. The other 3 are descriptive; 1 - 0.95^4 = 18.5% is the chance of a false pass somewhere in 4 tests.
#   The 4 rest-group cells are descriptive and are NOT part of the pass decision. Total cells printed = 8.
#
# NO-LEAKAGE RULE for the big-move model: the shipped model (Backend/models/bigmove_model.joblib) was trained through
#   2021-12, which OVERLAPS the only window where Benzinga news scores exist (2019 to mid-2020).
#   Using it here would leak the test period. The script therefore retrains an identical HistGradientBoosting model
#   on prices STRICTLY BEFORE TEST_START minus a 14-day gap, on the same price universe (top 500 by news count,
#   kept only when it has >= 1,500 priced days), and uses that.
#   The shipped file is only used if its `trained_through` is earlier than TEST_START (it is not, so it is skipped).
#   ALLOW_OVERLAP=True forces the shipped model and prints a LEAKED-RESULT warning; leave it False.
#
# KNOWN LIMITS (same as P12/P13/G): survivors only (top 500 by news count, kept only if >= 1,500 priced days; about 330
#   in past runs), headline-only text, 96% of Benzinga
#   dates carry no time of day so entry is the next trading day's close, the SVM only learns the dictionary label so it
#   inherits the dictionary's errors rather than adding a new signal, one window that includes the Mar-2020 crash, and the high group is thin (20% of roughly 80 news-days per
#   day, so top/bottom 20% is about 3 names per side) -> low power, especially at 5 days. Headlines are NOT filtered to
#   single-stock text (46.6% of Benzinga rows are market round-ups); P20 found that cleaning them did not create a
#   direction signal, and filtering would shrink the already-thin groups.

# P30. Setup, prices, dictionary score (dedupe as in P20; keep only tickers with a tradeable Yahoo price history)
import os, re, glob, subprocess, sys, json
import numpy as np, pandas as pd
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pysentiment2"], check=False)
import pysentiment2 as ps, nltk
nltk.download("opinion_lexicon", quiet=True)
from nltk.corpus import opinion_lexicon as ol

TEST_START, TEST_END = pd.Timestamp("2019-01-01"), pd.Timestamp("2020-08-20")
TOP_Q, MIN_PER_GROUP, COST_BPS, N_SHUFFLE = 0.20, 10, 10.0, 200
PRIMARY, N_CONFIRMATORY = ("svm", 1), 4
ALLOW_OVERLAP = False
COST_PAIR = 4 * COST_BPS  # bps per top-minus-bottom pair: 2 legs x (entry + exit)

lm = pd.read_csv(os.path.dirname(ps.__file__) + "/static/LM.csv")
lmc = {c.lower(): c for c in lm.columns}
pos_words = set(ol.positive()) | set(lm.loc[lm[lmc["positive"]] > 0, lmc["word"]].str.lower())
neg_words = set(ol.negative()) | set(lm.loc[lm[lmc["negative"]] > 0, lmc["word"]].str.lower())
tok = lambda s: re.findall(r"[a-z]+", s.lower())

bzp = glob.glob("/kaggle/input/**/raw_analyst_ratings.csv", recursive=True)[0]
bz = pd.read_csv(bzp, usecols=["headline", "date", "stock"])
bz["date"] = pd.to_datetime(bz["date"], utc=True, format="mixed")
bz = bz[(bz["date"] >= "2011-01-01") & bz["headline"].notna()].drop_duplicates(["stock", "date", "headline"]).copy()
bz["score"] = bz["headline"].map(lambda s: sum(w in pos_words for w in tok(s)) - sum(w in neg_words for w in tok(s)))
bz["day"] = bz["date"].dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
top = bz["stock"].value_counts().index[:500].tolist()
import yfinance as yf
raw = yf.download(top, start="2010-12-01", end="2020-09-01", progress=False, auto_adjust=True)
pxm = raw["Close"].dropna(axis=1, thresh=1500)
volm = raw["Volume"].reindex(index=pxm.index, columns=pxm.columns)
test_days = pxm.index[(pxm.index >= TEST_START) & (pxm.index < TEST_END)]
print(len(bz), "clean headlines |", pxm.shape, "price table |", len(test_days), "test days")

# P31. Big-move ranker trained WITHOUT the test window (chart features mirror Backend/pipeline/bigmove_features.py)
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

FEATURES = ["r1", "r5", "r20", "r60", "vol5", "vol20", "ma50", "rsi", "macd", "volx"]
HORIZON = 5

def build_features(close, volume):
    r1 = close.pct_change(fill_method=None)
    up = r1.clip(lower=0).rolling(14).mean()
    dn = (-r1.clip(upper=0)).rolling(14).mean()
    raw_f = {"r1": r1, "r5": close.pct_change(5, fill_method=None), "r20": close.pct_change(20, fill_method=None),
             "r60": close.pct_change(60, fill_method=None), "vol5": r1.rolling(5).std(), "vol20": r1.rolling(20).std(),
             "ma50": close / close.rolling(50).mean() - 1, "rsi": 100 - 100 / (1 + up / dn),
             "macd": (close.ewm(span=12).mean() - close.ewm(span=26).mean()) / close,
             "volx": volume / volume.rolling(20).mean()}
    rel = {k: v.replace([np.inf, -np.inf], np.nan).sub(v.replace([np.inf, -np.inf], np.nan).median(axis=1), axis=0)
           for k, v in raw_f.items()}
    return pd.concat({k: v.stack() for k, v in rel.items()}, axis=1).dropna()[FEATURES]

def big_move_label(close):
    y = close.shift(-(HORIZON + 1)) / close.shift(-1) - 1
    dev = y.sub(y.median(axis=1), axis=0).abs()
    big = dev.gt(dev.quantile(0.8, axis=1), axis=0).astype(float).where(dev.notna())
    return big.stack().dropna().astype(int)

def bm_make():
    return HistGradientBoostingClassifier(max_depth=4, learning_rate=0.05, max_iter=200, l2_regularization=1.0, random_state=0)

Xb = build_features(pxm.loc[:TEST_END], volm.loc[:TEST_END])
yb = big_move_label(pxm.loc[:TEST_END])
Db = Xb.join(yb.rename("big5"), how="inner")
Db = Db[Db.index.get_level_values(0) >= "2017-01-01"]
dts = Db.index.get_level_values(0)
train_end = TEST_START - pd.Timedelta(days=14)
m_tr = dts < train_end
m_fit, m_val = dts < pd.Timestamp("2018-07-01"), (dts >= pd.Timestamp("2018-07-01")) & m_tr
auc_val = roc_auc_score(Db["big5"].values[m_val], bm_make().fit(Db[FEATURES].values[m_fit], Db["big5"].values[m_fit]).predict_proba(Db[FEATURES].values[m_val])[:, 1])
model = bm_make().fit(Db[FEATURES].values[m_tr], Db["big5"].values[m_tr])
print("big-move retrain:", int(m_tr.sum()), "rows through", dts[m_tr].max().date(), "| pre-test holdout AUC", round(auc_val, 3))

used_model = "retrained_pre_test"
cands = glob.glob("/kaggle/input/**/bigmove_model.joblib", recursive=True) + glob.glob("**/models/bigmove_model.joblib", recursive=True)
if cands:
    try:
        import joblib
        sb = joblib.load(cands[0])
        tt = str(sb.get("trained_through"))
        print("shipped bundle", cands[0], "trained_through", tt, "| overlaps test:", tt >= str(TEST_START.date()))
        if ALLOW_OVERLAP and tt >= str(TEST_START.date()):
            model, used_model = sb["model"], "shipped_LEAKED"
            print("using shipped model  *** LEAKED RESULT: it saw the test window ***")
        elif tt < str(TEST_START.date()):
            model, used_model = sb["model"], "shipped_no_overlap"
            print("using shipped model (no overlap)")
        else:
            print("shipped model overlaps the test window -> keeping the retrained model")
    except Exception as e:
        print("shipped bundle unusable, keeping the retrained model:", e)
else:
    print("no shipped bundle found on Kaggle; using the retrained model")

Xfull = build_features(pxm, volm)
Xte = Xfull[Xfull.index.get_level_values(0).isin(test_days)]
bmove = pd.DataFrame({"day": Xte.index.get_level_values(0), "stock": Xte.index.get_level_values(1),
                      "bmove_p": model.predict_proba(Xte[FEATURES].values)[:, 1]})
print("big-move scores for", len(bmove), "stock-days; base-rate sanity (median p):", round(float(np.median(bmove["bmove_p"])), 3))

# P32. Paper-style news score: tf-idf (unigram+bigram, min_df 3) + LinearSVC trained to reproduce the dictionary label.
# CPU only. Pre-processing mirrors paper_replication.py: tokens = [a-z]+, finance + English stop words, Porter stemming.
from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.svm import LinearSVC
fin_stop = set("january february march april may june july august september october november december monday tuesday wednesday thursday friday saturday sunday dollar dollars usd eur euro euros yen cents million billion trillion percent year week day quarter fiscal china chinese india europe european asia america american united states york california japan korea taiwan london canada germany".split())
stops = ENGLISH_STOP_WORDS | fin_stop
st, cache = PorterStemmer(), {}
stem = lambda w: cache[w] if w in cache else cache.setdefault(w, st.stem(w))
clean = lambda s: " ".join(stem(w) for w in tok(s) if len(w) > 2 and w not in stops)
bz["clean"] = bz["headline"].map(clean)
bz["dlab"] = np.sign(bz["score"]).astype(int)
TRAIN_END = TEST_START - pd.Timedelta(days=14)

m_fit = (bz["day"] < "2018-01-01") & (bz["dlab"] != 0)
m_val = (bz["day"] >= "2018-01-01") & (bz["day"] < TRAIN_END) & (bz["dlab"] != 0)
m_tr = (bz["day"] < TRAIN_END) & (bz["dlab"] != 0)

vec0 = TfidfVectorizer(min_df=3, ngram_range=(1, 2))
clf0 = LinearSVC().fit(vec0.fit_transform(bz.loc[m_fit, "clean"]), bz.loc[m_fit, "dlab"].values)
y_val = bz.loc[m_val, "dlab"].values
val_pred = clf0.predict(vec0.transform(bz.loc[m_val, "clean"]))
print("SVM sanity (2018 validation, label = dictionary sign): accuracy", round((val_pred == y_val).mean(), 3),
      "| base rate", round(max(y_val.mean(), 1 - y_val.mean()), 3), "| val rows", int(m_val.sum()))

vec = TfidfVectorizer(min_df=3, ngram_range=(1, 2))
Xtr = vec.fit_transform(bz.loc[m_tr, "clean"])
clf = LinearSVC().fit(Xtr, bz.loc[m_tr, "dlab"].values)
print("SVM train rows", int(m_tr.sum()), "| features", Xtr.shape[1], "| train accuracy", round(clf.score(Xtr, bz.loc[m_tr, "dlab"].values), 3))

sub = bz[bz["stock"].isin(pxm.columns) & bz["day"].isin(test_days)].copy()
sub["svm"] = clf.decision_function(vec.transform(sub["clean"]))
print(len(sub), "test headlines |", sub["headline"].nunique(), "unique | SVM score mean", round(float(sub["svm"].mean()), 3))

# P34. Per stock-day scores + returns, split by big-move probability, pre-registered evaluation with a shuffle null
cols = ["score", "svm"]
n_confirm = 2 * len(cols)
if n_confirm != N_CONFIRMATORY:
    print("WARNING:", n_confirm, "confirmatory tests, but the pre-registration assumed", N_CONFIRMATORY)
bmove["q_bm"] = bmove.groupby("day")["bmove_p"].rank(pct=True)
bmove["grp"] = np.where(bmove["q_bm"] >= 1 - TOP_Q, "high", "rest")
sc = sub.groupby(["day", "stock"], as_index=False)[cols].mean().merge(bmove, on=["day", "stock"], how="inner")
sc = sc.dropna(subset=["bmove_p"])
ix, cx = pxm.index.searchsorted(sc["day"], side="right"), pxm.columns.get_indexer(sc["stock"])
sc["r1"] = (pxm.shift(-1) / pxm - 1).values[ix, cx]
sc["r5"] = (pxm.shift(-5) / pxm - 1).values[ix, cx]
print(len(sc), "scored stock-days |", sc["day"].nunique(), "days |", round((sc["grp"] == "high").mean(), 3), "share in the high group")

def daily_spread(f, col, rcol, stats=None):
    f = f.dropna(subset=[col, rcol])
    f = f[f.groupby("day")[col].transform("size") >= MIN_PER_GROUP]
    if f.empty:
        return pd.Series(dtype=float)
    q = f.groupby("day")[col].rank(pct=True)
    hi = f[q >= 1 - TOP_Q].groupby("day")[rcol].mean()
    lo = f[q <= TOP_Q].groupby("day")[rcol].mean()
    both = pd.concat({"hi": hi, "lo": lo}, axis=1)
    w = (both["hi"] - both["lo"]).dropna()
    if stats is not None:
        stats["empty_side_days"] = int(f["day"].nunique() - len(w))
    return w

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

def shuffled_net(f, col, rcol, h, rng):
    g = f.copy()
    g[col] = g.groupby("day")[col].transform(lambda s: rng.permutation(s.values))
    return net_summary(daily_spread(g[g["grp"] == "high"], col, rcol), h)["net_bps"]

rows = []
for col in cols:
    for rc, h in (("r1", 1), ("r5", 5)):
        for grp in ("high", "rest"):
            stats = {}
            w = daily_spread(sc[sc["grp"] == grp], col, rc, stats)
            s = net_summary(w, h)
            row = {"scorer": col, "horizon": h, "group": grp, "empty_side_days": stats.get("empty_side_days", 0), **s}
            if grp == "high":
                rng = np.random.default_rng(0)
                null = np.array([shuffled_net(sc, col, rc, h, rng) for _ in range(N_SHUFFLE)])
                row["null_mean_bps"] = np.nanmean(null)
                row["null_p95_bps"] = np.nanpercentile(null, 95)
                row["p_shuffle"] = (1 + np.sum(null >= s["net_bps"])) / (1 + N_SHUFFLE)
                row["passes"] = bool(s["net_bps"] > 0 and s["t"] > 2 and row["p_shuffle"] < 0.05)
                row["primary"] = (col, h) == PRIMARY
            else:
                row["null_mean_bps"] = row["null_p95_bps"] = row["p_shuffle"] = np.nan
                row["passes"] = row["primary"] = False
            rows.append(row)

res = pd.DataFrame(rows)
prim = res[(res["scorer"] == PRIMARY[0]) & (res["horizon"] == PRIMARY[1])].iloc[0]
names = {"score": "dictionary", "svm": "SVM(tf-idf)"}
disp = res.copy()
disp["scorer"] = disp["scorer"].map(names)
print("\nPRE-REGISTERED CONSTANTS: top/bottom", TOP_Q, "| min names/group/day", MIN_PER_GROUP,
      "| cost", COST_PAIR, "bps/pair (", COST_BPS, "bps/fill x 4 fills) | shuffles", N_SHUFFLE)
print("TESTS:", n_confirm, "confirmatory (2 scorers x 2 horizons, HIGH group) +",
      int((res["group"] == "rest").sum()), "descriptive rest-group cells =", len(res), "cells total")
print("PRIMARY (decides pass/fail):", names[PRIMARY[0]], PRIMARY[1], "day | chance of >= 1 false pass in",
      n_confirm, "tests at p < 0.05 =", round(1 - 0.95 ** n_confirm, 4))
print(disp.round(3).to_string(index=False))
print("\nDAYS DROPPED for an empty top/bottom group (ties):",
      int(res[res["group"] == "high"]["empty_side_days"].sum()), "high-group cell-days; see empty_side_days per row")

print("\nPRIMARY RESULT (" + names[PRIMARY[0]] + ", " + str(PRIMARY[1]) + "d, high group): net", round(prim["net_bps"], 1),
      "bps [range", round(prim["net_bps_min"], 1), "to", round(prim["net_bps_max"], 1), "] | net t", round(prim["t"], 2),
      "[range", round(prim["t_min"], 2), "to", round(prim["t_max"], 2), "] | shuffle p", round(prim["p_shuffle"], 3),
      "| PASS:", prim["passes"])
print("OVERALL PASS (PRIMARY ONLY):", bool(prim["passes"]))
print("Other confirmatory cells passing (informational only):",
      int(res[(res["group"] == "high") & res["passes"] & ~res["primary"]].shape[0]), "of", n_confirm - 1)
print("NOTE: rest-group cells are descriptive; the primary SVM 1-day cell is the only pass/fail decision.")

out = {"constants": {"test_start": str(TEST_START.date()), "test_end": str(TEST_END.date()), "top_q": TOP_Q,
                     "min_per_group": MIN_PER_GROUP, "cost_bps_per_fill": COST_BPS, "cost_bps_per_pair": COST_PAIR,
                     "n_shuffle": N_SHUFFLE, "primary": list(PRIMARY), "n_confirmatory": n_confirm,
                     "n_cells_total": len(res), "false_pass_prob_confirmatory": round(1 - 0.95 ** n_confirm, 4)},
       "bigmove_model_used": used_model, "overall_pass_primary_only": bool(prim["passes"]),
       "results": json.loads(res.to_json(orient="records"))}
json.dump(out, open("/kaggle/working/newsxbigmove_results.json", "w"), indent=1)
res.to_csv("/kaggle/working/newsxbigmove_results.csv", index=False)
print("saved /kaggle/working/newsxbigmove_results.json and .csv")
