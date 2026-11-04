# %% 7. Paper-style ML on headlines (RUN ON KAGGLE, as a new cell AFTER fnspid_explore.py in the same session)
# Needs `lab`, `c_tick`, `c_title`, `TRAIN_END` from fnspid_explore.py. Kept flat on purpose (no indented blocks).
# Paper (Joshi et al. 2016): tf-idf + Naive Bayes / Random Forest / SVM. Difference: label = real 1-week price move, not a word-count dictionary.
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import LinearSVC
from sklearn.metrics import accuracy_score, f1_score
d = lab.drop_duplicates(subset=[c_tick, c_title]).copy()
cut = pd.Timestamp(TRAIN_END, tz="UTC")
tr, te = d[d["_d"] <= cut], d[d["_d"] > cut]
vec = TfidfVectorizer(lowercase=True, stop_words="english", min_df=3, ngram_range=(1, 2), max_features=30000)
Xtr, Xte = vec.fit_transform(tr[c_title].astype(str)), vec.transform(te[c_title].astype(str))
ytr, yte = tr["up"].astype(int).values, te["up"].astype(int).values
base = max(yte.mean(), 1 - yte.mean())
models = {"NaiveBayes": MultinomialNB(), "LinearSVM": LinearSVC(C=0.5), "RandomForest": RandomForestClassifier(n_estimators=100, min_samples_leaf=3, n_jobs=-1, random_state=0)}
preds = {n: m.fit(Xtr, ytr).predict(Xte) for n, m in models.items()}
shuf = LinearSVC(C=0.5).fit(Xtr, np.random.default_rng(0).permutation(ytr)).predict(Xte)
rows = [f"{n:13s} acc {accuracy_score(yte, p):.3f} | macro-F1 {f1_score(yte, p, average='macro'):.3f} | predicts up {p.mean():.2f}" for n, p in preds.items()]
rows.append(f"shuffled-label acc {accuracy_score(yte, shuf):.3f}  (control: trained on random labels)")
print(f"train {len(tr):,} | test {len(te):,} (duplicates removed) | always-up baseline {base:.3f}", *rows, sep=chr(10))
# Why no one-line `for`: the Kaggle editor auto-indents the next line and breaks a typed-in cell.
