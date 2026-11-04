# Big-move model: P(stock's next-5-day move is in the day's top 20% vs the market, either direction), from chart features only.
# RUN ON KAGGLE (Internet ON; CPU is enough, sklearn does not use the GPU). One cell per block marked "# CELL n".
# CELL 1 must first contain the full text of Backend/pipeline/bigmove_features.py (paste it above the code below).
# Data: current S&P 500 members (survivors only), yfinance adjusted prices ~10 years. Decision day t, entry = close t+1, outcome = close t+6.
# Split by time with a 10-trading-day gap: train 2017-2021, calibrate 2022, test 2023 to the latest day.
# Output: /kaggle/working/bigmove_model.joblib and /kaggle/working/bigmove_metrics.json

# CELL 1: pin sklearn to the version the backend venv uses (the saved model must load there), then universe + 10 years of prices
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "scikit-learn==1.9.1"], check=True)
import io, json, time
import numpy as np
import pandas as pd
import requests
import yfinance as yf

html = requests.get("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", headers={"User-Agent": "PlanWiseAI-student-project/0.1"}, timeout=30).text
tickers = pd.read_html(io.StringIO(html))[0]["Symbol"].str.replace(".", "-", regex=False).str.strip().unique().tolist()
print(len(tickers), "tickers")
closes, vols = [], []
for i in range(0, len(tickers), 100):
    raw = yf.download(tickers[i:i + 100], start="2016-06-01", interval="1d", auto_adjust=True, progress=False, threads=True)
    closes.append(raw["Close"])
    vols.append(raw["Volume"])
    time.sleep(1)
close = pd.concat(closes, axis=1).sort_index()
volume = pd.concat(vols, axis=1).sort_index()
close = close.loc[:, close.notna().sum() > 500]
volume = volume[close.columns]
print(close.shape, close.index.min().date(), close.index.max().date())

# CELL 2: features + label
X = build_features(close, volume)
y = big_move_label(close)
D = X.join(y.rename("big5"), how="inner").dropna()
D = D[D.index.get_level_values(0) >= "2017-01-01"]
dts = D.index.get_level_values(0)
print(D.shape, "rows | base rate", round(D["big5"].mean(), 3))
gap = pd.Timedelta(days=14)
m_tr = dts < pd.Timestamp("2022-01-01") - gap
m_va = (dts >= pd.Timestamp("2022-01-01")) & (dts < pd.Timestamp("2023-01-01") - gap)
m_te = dts >= pd.Timestamp("2023-01-01")
print("train", m_tr.sum(), "| calibrate", m_va.sum(), "| test", m_te.sum())

# CELL 3: fit, calibrate, test (plus two controls)
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
import sklearn

def make():
    return HistGradientBoostingClassifier(max_depth=4, learning_rate=0.05, max_iter=200, l2_regularization=1.0, random_state=0)

Xv, yv = D[FEATURES].values, D["big5"].values
model = make().fit(Xv[m_tr], yv[m_tr])
pva, pte = model.predict_proba(Xv[m_va])[:, 1], model.predict_proba(Xv[m_te])[:, 1]
cal = IsotonicRegression(out_of_bounds="clip").fit(pva, yv[m_va])
pcal = cal.predict(pte)
yte = yv[m_te]
yrs = dts[m_te].year
metrics = {"auc_test": roc_auc_score(yte, pte), "auc_by_year": {int(k): roc_auc_score(yte[yrs == k], pte[yrs == k]) for k in sorted(set(yrs))}}
metrics["baseline_auc_vol20_only"] = roc_auc_score(yte, D["vol20"].values[m_te])  # trivial rule: more volatile = bigger move
shuf = np.random.RandomState(0).permutation(yv[m_tr])
metrics["control_auc_shuffled_labels"] = roc_auc_score(yte, make().fit(Xv[m_tr], shuf).predict_proba(Xv[m_te])[:, 1])
base = yv[m_tr].mean()
metrics["brier_skill"] = 1 - brier_score_loss(yte, pcal) / brier_score_loss(yte, np.full(len(yte), base))
tb = pd.DataFrame({"p": pcal, "y": yte})
tb["group"] = pd.qcut(tb["p"].rank(method="first"), 10, labels=False) + 1
cal_tab = tb.groupby("group").agg(predicted=("p", "mean"), actual=("y", "mean"), rows=("y", "size")).round(3)
print(json.dumps(metrics, indent=1, default=float))
print(cal_tab.to_string())
print("test base rate", round(yte.mean(), 3), "| top group actual", round(cal_tab["actual"].iloc[-1], 3))

# CELL 4: save (the model is the one evaluated above)
import joblib
bundle = {"model": model, "calibrator": cal, "features": FEATURES, "horizon_days": HORIZON, "base_rate": float(base),
          "trained_through": str(dts[m_tr].max().date()), "calibrated_on": "2022", "tested": "2023 to " + str(dts.max().date()),
          "sklearn": sklearn.__version__, "metrics": metrics, "calibration": cal_tab.reset_index().to_dict("records")}
joblib.dump(bundle, "/kaggle/working/bigmove_model.joblib")
json.dump({k: v for k, v in bundle.items() if k not in ("model", "calibrator")}, open("/kaggle/working/bigmove_metrics.json", "w"), indent=1, default=float)
print("saved")
