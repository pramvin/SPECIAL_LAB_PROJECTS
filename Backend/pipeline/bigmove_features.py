"""Chart features for the big-move model.

Pure pandas. The SAME file is used to train on Kaggle (paste it into a cell) and to score in
pipeline/rank.py, so training and serving cannot drift apart.

Input: wide DataFrames (index = trading date, columns = ticker) of adjusted close and volume.
Output: one row per (date, ticker), every feature minus that day's median over all stocks.
"""
import numpy as np
import pandas as pd

FEATURES = ["r1", "r5", "r20", "r60", "vol5", "vol20", "ma50", "rsi", "macd", "volx"]
HORIZON = 5  # trading days; entry = close of the next day, outcome = close 5 days after that


def build_features(close: pd.DataFrame, volume: pd.DataFrame) -> pd.DataFrame:
    r1 = close.pct_change(fill_method=None)
    up = r1.clip(lower=0).rolling(14).mean()
    dn = (-r1.clip(upper=0)).rolling(14).mean()
    raw = {
        "r1": r1,
        "r5": close.pct_change(5, fill_method=None),
        "r20": close.pct_change(20, fill_method=None),
        "r60": close.pct_change(60, fill_method=None),
        "vol5": r1.rolling(5).std(),
        "vol20": r1.rolling(20).std(),
        "ma50": close / close.rolling(50).mean() - 1,
        "rsi": 100 - 100 / (1 + up / dn),
        "macd": (close.ewm(span=12).mean() - close.ewm(span=26).mean()) / close,
        "volx": volume / volume.rolling(20).mean(),
    }
    rel = {k: v.replace([np.inf, -np.inf], np.nan).sub(v.replace([np.inf, -np.inf], np.nan).median(axis=1), axis=0)
           for k, v in raw.items()}
    out = pd.concat({k: v.stack() for k, v in rel.items()}, axis=1).dropna()
    return out[FEATURES]


def big_move_label(close: pd.DataFrame) -> pd.Series:
    """1 if the stock's 5-day move (from next close) differs from that day's median by an amount in the day's top 20%."""
    y = close.shift(-(HORIZON + 1)) / close.shift(-1) - 1
    dev = y.sub(y.median(axis=1), axis=0).abs()
    big = dev.gt(dev.quantile(0.8, axis=1), axis=0).astype(float).where(dev.notna())
    return big.stack().dropna().astype(int)
