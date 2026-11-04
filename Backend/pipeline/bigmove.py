"""Serve the big-move model: chance a stock's next-5-day move is in the day's top 20%.

The model file is optional. When it is missing, or sklearn is not installed, load_bundle()
returns None and the pipeline stores NULL, so the UI simply hides the badge.

Training code: experiments/bigmove_train.py. Features: pipeline/bigmove_features.py.
"""
import os

from .bigmove_features import FEATURES, build_features

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "bigmove_model.joblib"
)


def _joblib():
    try:
        import joblib
        import sklearn  # noqa: F401  (the saved bundle was trained with sklearn)
    except Exception:
        return None
    return joblib


def load_bundle(path: str | None = None):
    """Load the model bundle, or None when the file or the sklearn stack is absent."""
    joblib = _joblib()
    if joblib is None:
        return None
    p = path or MODEL_PATH
    if not os.path.isfile(p):
        return None
    try:
        return joblib.load(p)
    except Exception:
        return None


def score(bundle, close, volume) -> dict[str, float]:
    """Return {ticker: probability} for the latest date in the wide close/volume frames."""
    if not bundle or close is None or volume is None or close.empty:
        return {}
    volume = volume.reindex(columns=close.columns)
    try:
        X = build_features(close, volume)
    except Exception:
        return {}
    if X.empty:
        return {}
    latest = X.xs(X.index.get_level_values(0).max(), level=0)
    cols = bundle.get("features") or FEATURES
    latest = latest.reindex(columns=cols).dropna()
    if latest.empty:
        return {}
    proba = bundle["model"].predict_proba(latest.to_numpy(dtype=float))[:, 1]
    calibrator = bundle.get("calibrator")
    if calibrator is not None:
        proba = calibrator.predict(proba)
    return {str(t): float(p) for t, p in zip(latest.index, proba)}
