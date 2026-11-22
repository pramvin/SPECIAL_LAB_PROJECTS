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


class YahooFundamentalsTest(unittest.TestCase):
    def test_insiders_count_only_open_market_buys_and_sales_in_six_months(self):
        import pandas as pd

        frame = pd.DataFrame({
            "Start Date": ["2026-11-01", "2026-10-01", "2026-10-02", "2025-01-01", "2026-09-01"],
            "Text": ["Sale at price 100", "Purchase at price 90", "Sale at price 100", "Sale at price 50",
                     "Stock Award(Grant)"],
            "Value": [2_000_000, 500_000, 1_000_000, 9_000_000, None]})

        class Handle:
            insider_transactions = frame

        items = sources._yf_insider_items(Handle(), "2026-11-20")
        self.assertEqual(items["insider_sells_6m"]["value"], 2)
        self.assertEqual(items["insider_buys_6m"]["value"], 1)
        self.assertEqual(items["insider_sell_value_6m"]["value"], 3.0)

    def test_statements_give_four_quarters_in_millions(self):
        import pandas as pd

        cols = pd.to_datetime(["2026-09-30", "2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30"])
        income = pd.DataFrame([[6e9, 5e9, 4e9, 3e9, 2e9]], index=["Total Revenue"], columns=cols)

        class Handle:
            quarterly_income_stmt = income
            quarterly_cashflow = pd.DataFrame()
            quarterly_balance_sheet = pd.DataFrame()

        items = sources._yf_statement_items(Handle())
        self.assertEqual(items["revenue_q0"]["value"], 6000.0)
        self.assertIn("2026-09-30", items["revenue_q0"]["label"])
        self.assertNotIn("revenue_q4", items)

    def test_macro_without_a_fred_key_falls_back_to_market_series(self):
        import os
        from unittest import mock

        with mock.patch.dict(os.environ, {"FRED_API_KEY": ""}), \
                mock.patch.object(sources, "fetch_yf_macro", return_value={"status": "ok", "reason": None,
                                                                          "items": [1]}) as fallback:
            self.assertEqual(sources.fetch_macro(None, "2026-11-20")["items"], [1])
            fallback.assert_called_once()


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


class VerdictFieldsTest(unittest.TestCase):
    def test_keeps_valid_lights_and_drops_bad_ones(self):
        from agents import validate

        got = validate.verdict_fields({
            "headline": "Uptrend intact, buy in two steps. See metric:rsi14.",
            "checks": {"trend": {"light": "green", "line": "Up, 14% above 200-day"},
                       "business": {"light": "purple", "line": "ignored"},
                       "risk": {"light": "amber", "line": ""}},
            "how_to_act": "Start with 60 to 70%.", "change_if": "A close below 237.98."},
            {14.0, 237.98})
        self.assertNotIn("metric", got["headline"])
        self.assertEqual(list(got["checks"]), ["trend"])
        self.assertEqual(got["change_if"], "A close below 237.98.")

    def test_a_line_with_an_unseen_number_is_blanked_not_fatal(self):
        from agents import validate

        got = validate.verdict_fields({"headline": "It will hit 987.65 soon."}, {254.33})
        self.assertEqual(got["headline"], "")

    def test_missing_fields_give_an_empty_verdict(self):
        from agents import validate

        self.assertEqual(validate.verdict_fields({}, set())["checks"], {})

    def test_api_cleans_the_stored_verdict(self):
        from app import agents_api

        self.assertEqual(agents_api._verdict(None), {})
        self.assertEqual(agents_api._verdict({"checks": {"trend": {"light": "bad", "line": "x"}}}), {})
        got = agents_api._verdict({"headline": "h", "checks": {"risk": {"light": "red", "line": "l"}}})
        self.assertEqual(got["checks"], {"risk": {"light": "red", "line": "l"}})


class StripInternalTest(unittest.TestCase):
    def test_bracketed_metric_names_are_removed_but_normal_brackets_stay(self):
        from agents import validate

        got = validate.strip_internal("Return (r60) and trend (ma200_gap, sma200) hold; RSI is high (overbought).")
        self.assertEqual(got, "Return and trend hold; RSI is high (overbought).")


if __name__ == "__main__":
    unittest.main()
