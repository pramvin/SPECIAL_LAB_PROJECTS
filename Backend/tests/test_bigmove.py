"""Run from Backend/:  .venv/bin/python -m unittest tests.test_bigmove -v

Uses a fake model/calibrator, so no sklearn or model file is needed.
"""
import os
import tempfile
import unittest
from unittest import mock

import numpy as np
import pandas as pd

from pipeline import bigmove
from pipeline.bigmove_features import FEATURES


class FakeModel:
    def __init__(self, prob=0.6):
        self.prob = prob
        self.seen = None

    def predict_proba(self, X):
        self.seen = X
        n = len(X)
        return np.column_stack([np.full(n, 1 - self.prob), np.full(n, self.prob)])


class FakeCalibrator:
    def __init__(self, offset=0.1):
        self.offset = offset

    def predict(self, p):
        return np.clip(np.asarray(p) + self.offset, 0, 1)


def frames(days=120):
    """Two tickers, steadily rising prices, enough history for every feature."""
    dates = pd.bdate_range("2024-01-01", periods=days)
    close = pd.DataFrame(
        {"AAA": np.linspace(100, 140, days), "BBB": np.linspace(50, 60, days)}, index=dates
    )
    volume = pd.DataFrame(1_000_000.0, index=dates, columns=close.columns)
    return close, volume


def bundle(**kw):
    b = {"model": FakeModel(), "calibrator": FakeCalibrator(), "features": list(FEATURES)}
    b.update(kw)
    return b


class LoadBundleTest(unittest.TestCase):
    def test_missing_file_returns_none(self):
        missing = os.path.join(tempfile.gettempdir(), "definitely-not-here-bigmove.joblib")
        self.assertFalse(os.path.exists(missing))
        self.assertIsNone(bigmove.load_bundle(missing))

    def test_missing_sklearn_returns_none(self):
        with mock.patch.object(bigmove, "_joblib", return_value=None):
            self.assertIsNone(bigmove.load_bundle(bigmove.MODEL_PATH))
        self.assertTrue(bigmove.MODEL_PATH.endswith(os.path.join("models", "bigmove_model.joblib")))


class ScoreTest(unittest.TestCase):
    def test_no_bundle_or_empty_prices_returns_empty(self):
        close, volume = frames()
        self.assertEqual(bigmove.score(None, close, volume), {})
        self.assertEqual(bigmove.score(bundle(), pd.DataFrame(), volume), {})

    def test_scores_latest_row_only_and_applies_calibrator(self):
        close, volume = frames()
        b = bundle()
        out = bigmove.score(b, close, volume)
        self.assertEqual(set(out), {"AAA", "BBB"})
        self.assertEqual(b["model"].seen.shape, (2, len(FEATURES)))
        # 0.6 raw -> calibrator adds 0.1, one probability per ticker
        self.assertAlmostEqual(out["AAA"], 0.7)
        self.assertAlmostEqual(out["BBB"], 0.7)

    def test_feature_order_follows_the_bundle(self):
        close, volume = frames()
        b = bundle(features=list(reversed(FEATURES)))
        bigmove.score(b, close, volume)
        self.assertEqual(b["model"].seen.shape[1], len(FEATURES))

    def test_ticker_without_volume_is_skipped(self):
        close, volume = frames()
        out = bigmove.score(bundle(), close, volume[["AAA"]])
        self.assertEqual(set(out), {"AAA"})

    def test_dropna_removes_incomplete_ticker(self):
        close, volume = frames()
        close.loc[close.index[-1], "BBB"] = np.nan
        out = bigmove.score(bundle(), close, volume)
        self.assertEqual(set(out), {"AAA"})

    def test_probabilities_stay_in_range(self):
        close, volume = frames()
        out = bigmove.score(bundle(calibrator=FakeCalibrator(offset=5.0)), close, volume)
        self.assertTrue(all(0.0 <= p <= 1.0 for p in out.values()))


if __name__ == "__main__":
    unittest.main()
