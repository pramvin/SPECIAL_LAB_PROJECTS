"""Run from Backend/:  .venv/bin/python -m unittest tests.test_agent_metrics -v"""
import unittest

from agents import sources


def rows(n=60, close=100.0, high=101.0, low=99.0):
    return [{"close": close, "high": high, "low": low, "volume": 1000} for _ in range(n)]


class AtrMetricTest(unittest.TestCase):
    def test_atr_percent_is_shown_once_not_times_100_twice(self):
        # every day: range 2, previous close 100 -> ATR 2 on a price of 100 = 2%
        m = sources.compute_metrics(rows())
        self.assertAlmostEqual(m["atr14_pct"], 0.02)
        self.assertEqual(sources.metric_display("atr14_pct", m["atr14_pct"]), "2.00%")

    def test_absolute_atr_is_kept_in_price_units(self):
        self.assertAlmostEqual(sources.compute_metrics(rows())["_atr"], 2.0)

    def test_agrees_with_the_rank_step_value_for_the_same_prices(self):
        # rank.py stores atr_pct in percent (2.0); the agent's displayed ATR must say the same number
        shown = sources.metric_display("atr14_pct", sources.compute_metrics(rows())["atr14_pct"])
        self.assertEqual(float(shown.rstrip("%")), 2.0)


class IndicatorMenuTest(unittest.TestCase):
    """The TradingAgents market analyst's indicator list is all available as metrics."""

    def test_full_indicator_set_on_a_long_series(self):
        data = [{"close": 100.0 + i * 0.1, "high": 101.0 + i * 0.1, "low": 99.0 + i * 0.1, "volume": 1000}
                for i in range(250)]
        m = sources.compute_metrics(data)
        for key in ("ema10", "sma50", "sma200", "macd_line", "macd_signal", "macd_hist",
                    "boll", "boll_ub", "boll_lb", "vwma20", "atr14"):
            self.assertIn(key, m, key)
        self.assertAlmostEqual(m["sma50"], sum(d["close"] for d in data[-50:]) / 50, places=3)
        self.assertGreater(m["boll_ub"], m["boll"])
        self.assertGreater(m["boll"], m["boll_lb"])
        self.assertAlmostEqual(m["macd_hist"], m["macd_line"] - m["macd_signal"], places=3)
        self.assertAlmostEqual(m["atr14"], 2.0, places=3)

    def test_short_history_has_no_200_day_average(self):
        self.assertNotIn("sma200", sources.compute_metrics(rows(60)))


class CleanTextTest(unittest.TestCase):
    def test_only_the_sentence_with_an_unseen_number_is_dropped(self):
        from agents import validate

        text = "The price is 254.33 today. Support sits near 987.65 per share. Momentum is fading."
        got = validate.clean_text(text, {254.33}, "x")
        self.assertEqual(got, "The price is 254.33 today. Momentum is fading.")

    def test_fails_when_nothing_is_left(self):
        from agents import validate

        with self.assertRaises(validate.ValidationError):
            validate.clean_text("It will reach 987.65.", {254.33}, "x")


class EvidenceListTest(unittest.TestCase):
    def test_a_sentence_pasted_into_the_list_keeps_only_its_allowed_ids(self):
        from agents import validate

        got = validate._evidence_list(
            ["RSI is 65.80 (metric:rsi14) and the trend holds (metric:ma50_gap, news:99)"],
            {"metric:rsi14", "metric:ma50_gap"}, "x")
        self.assertEqual(got, ["metric:rsi14", "metric:ma50_gap"])

    def test_a_short_unknown_id_is_still_rejected(self):
        from agents import validate

        with self.assertRaises(validate.ValidationError):
            validate._evidence_list(["metric:nope"], {"metric:rsi14"}, "x")


class StripInternalTest(unittest.TestCase):
    def test_bracketed_metric_names_are_removed_but_normal_brackets_stay(self):
        from agents import validate

        got = validate.strip_internal("Return (r60) and trend (ma200_gap, sma200) hold; RSI is high (overbought).")
        self.assertEqual(got, "Return and trend hold; RSI is high (overbought).")


if __name__ == "__main__":
    unittest.main()
