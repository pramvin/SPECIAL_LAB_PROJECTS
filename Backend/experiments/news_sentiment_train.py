# News sentiment model for the app: 3-class tf-idf + LinearSVC, trained on Kaggle CPU only.
#
# RUN ON KAGGLE (Internet ON; CPU is enough). One cell per block marked "# P5x".
# Dataset: the usual Benzinga raw_analyst_ratings.csv (2011 to mid-2020).
# Output: /kaggle/working/news_sentiment_model.joblib, a dict with:
#   model (sklearn Pipeline[TfidfVectorizer, LinearSVC]), trained_through, sklearn_version, name
#
# LABELS ARE DICTIONARY SIGNS, NOT MARKET TRUTH. A headline is labeled bullish / neutral / bearish by
# the sign of its Hu & Liu + McDonald word score. These labels were NEVER checked by humans, and a
# neutral label means "no listed positive/negative word matched", not "no market effect". The model
# reproduces the dictionary; it does not add a new signal.
#
# Text preprocessing is plain tf-idf with English stop words and NO nltk stemmer, so serving only
# needs scikit-learn. Training is 2011-2018; the served model stops 14 days before 2019.

# P50. Setup, dictionary labels, dedupe
import glob, os, re, subprocess, sys

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pysentiment2", "scikit-learn==1.9.1"], check=True)
import joblib
import numpy as np
import pandas as pd
import sklearn
import pysentiment2 as ps
import nltk
nltk.download("opinion_lexicon", quiet=True)
from nltk.corpus import opinion_lexicon as ol
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

NAME = "news_sentiment_svm"
VAL_START = pd.Timestamp("2018-01-01")
TRAIN_END = pd.Timestamp("2018-12-18")  # 2019-01-01 minus a 14-day gap
OUT = "/kaggle/working/news_sentiment_model.joblib"

lm = pd.read_csv(os.path.dirname(ps.__file__) + "/static/LM.csv")
lmc = {c.lower(): c for c in lm.columns}
pos_words = set(ol.positive()) | set(lm.loc[lm[lmc["positive"]] > 0, lmc["word"]].str.lower())
neg_words = set(ol.negative()) | set(lm.loc[lm[lmc["negative"]] > 0, lmc["word"]].str.lower())
tok = lambda s: re.findall(r"[a-z]+", s.lower())

path = glob.glob("/kaggle/input/**/raw_analyst_ratings.csv", recursive=True)[0]
bz = pd.read_csv(path, usecols=["headline", "date"])
bz["headline"] = bz["headline"].astype(str).str.strip()
bz["date"] = pd.to_datetime(bz["date"], utc=True, format="mixed")
bz = bz[(bz["date"] >= "2011-01-01") & (bz["headline"] != "")].copy()
bz = bz.drop_duplicates("headline").copy()
bz["day"] = bz["date"].dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
bz["score"] = bz["headline"].map(lambda s: sum(w in pos_words for w in tok(s)) - sum(w in neg_words for w in tok(s)))
bz["label"] = np.where(bz["score"] > 0, "bullish", np.where(bz["score"] < 0, "bearish", "neutral"))
print(len(bz), "unique headlines |", bz["day"].min().date(), "to", bz["day"].max().date())
print(bz["label"].value_counts().to_string())

# P51. Honest 2018 check: train on pre-2018, predict 2018 up to the 14-day gap, compare to majority class
fit = bz["day"] < VAL_START
val = (bz["day"] >= VAL_START) & (bz["day"] < TRAIN_END)
print("fit rows", int(fit.sum()), "| 2018 validation rows", int(val.sum()))

def make_model():
    return Pipeline([
        ("tfidf", TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=(1, 1), min_df=3, sublinear_tf=True)),
        ("svc", LinearSVC()),
    ])

eval_model = make_model()
eval_model.fit(bz.loc[fit, "headline"], bz.loc[fit, "label"])
val_pred = eval_model.predict(bz.loc[val, "headline"])
val_true = bz.loc[val, "label"]
majority = val_true.value_counts().idxmax()
acc = accuracy_score(val_true, val_pred)
base = accuracy_score(val_true, np.full(len(val_true), majority))
print("2018 accuracy", round(acc, 3), "| majority baseline", round(base, 3), f"({majority})")

# P52. Final served model: all labels before TRAIN_END, saved bundle
train = bz["day"] < TRAIN_END
model = make_model()
model.fit(bz.loc[train, "headline"], bz.loc[train, "label"])
trained_through = str(bz.loc[train, "day"].max().date())
bundle = {"model": model, "trained_through": trained_through, "sklearn_version": sklearn.__version__, "name": NAME}
joblib.dump(bundle, OUT)
size_mb = os.path.getsize(OUT) / 1e6
print("train rows", int(train.sum()), "| features", len(model.named_steps["tfidf"].vocabulary_),
      "| trained through", trained_through)
print("saved", OUT, "|", round(size_mb, 2), "MB", "(target <= ~5 MB)")
if size_mb > 5:
    print("WARNING: model file is over 5 MB")

# P53. Per-class accuracy and 10 validation examples (dictionary label vs prediction)
print("\nPer-class report on the 2018 check (dictionary label = truth for this test):")
print(classification_report(val_true, val_pred, digits=3, zero_division=0))
ex = bz.loc[val, ["headline", "label"]].copy()
ex["predicted"] = val_pred
ex = ex.sample(min(10, len(ex)), random_state=0)
print("\n10 validation headlines:")
for _, r in ex.iterrows():
    print(f"  [{r['label']} -> {r['predicted']}] {r['headline'][:110]}")
