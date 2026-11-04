"""Run from Backend/:  .venv/bin/python -m unittest tests.test_matching -v"""
import unittest

from app import matching as m


def row(t, sector, atr, score=60):
    return {"ticker": t, "sector": sector, "atr_pct": atr, "score": score}


class MatchingTest(unittest.TestCase):
    def test_cosine_basics(self):
        self.assertAlmostEqual(m.cosine([1, 0], [1, 0]), 1.0)
        self.assertAlmostEqual(m.cosine([1, 0], [0, 1]), 0.0)
        self.assertEqual(m.cosine([0, 0], [1, 1]), 0.0)

    def test_tech_fan_gets_tech_first_at_equal_score(self):
        rows = [row("XOM", "energy", 2.0), row("MSFT", "tech", 2.0), row("JPM", "finance", 2.0)]
        top = m.rank_for_user(rows, ["tech"], "moderate")
        self.assertEqual(top[0]["ticker"], "MSFT")
        self.assertIn("Matches your Technology interest", top[0]["match_reasons"])

    def test_conservative_prefers_calm_aggressive_prefers_wild(self):
        rows = [row("CALM", "tech", 0.8), row("WILD", "tech", 5.5)]
        self.assertEqual(m.rank_for_user(rows, ["tech"], "conservative")[0]["ticker"], "CALM")
        self.assertEqual(m.rank_for_user(rows, ["tech"], "aggressive")[0]["ticker"], "WILD")

    def test_any_sector_is_neutral(self):
        a = m.fit("tech", 2.0, ["any"], "moderate")
        b = m.fit("energy", 2.0, ["any"], "moderate")
        self.assertAlmostEqual(a, b)

    def test_unknown_sector_and_missing_atr_do_not_crash(self):
        self.assertTrue(0 <= m.fit("Utilities", None, ["tech"], "moderate") <= 1)

    def test_strong_score_can_beat_a_weak_sector_match(self):
        rows = [row("GOOD", "energy", 2.0, score=99), row("MEH", "tech", 2.0, score=20)]
        self.assertEqual(m.rank_for_user(rows, ["tech"], "moderate")[0]["ticker"], "GOOD")

    def test_legacy_consumer_key_covers_both_consumer_sectors(self):
        rows = [row("KO", "consumer_staples", 1.5), row("AMZN", "consumer_discretionary", 1.5), row("XOM", "energy", 1.5)]
        top = m.rank_for_user(rows, ["consumer"], "moderate")
        self.assertEqual({t["ticker"] for t in top[:2]}, {"KO", "AMZN"})

    def test_new_gics_sectors_are_matched(self):
        rows = [row("NEE", "utilities", 1.5), row("MSFT", "tech", 1.5)]
        self.assertEqual(m.rank_for_user(rows, ["utilities"], "moderate")[0]["ticker"], "NEE")

    def test_top_n_and_inputs_not_mutated(self):
        rows = [row(str(i), "tech", 2.0, score=i) for i in range(30)]
        out = m.rank_for_user(rows, ["tech"], "moderate", top_n=5)
        self.assertEqual(len(out), 5)
        self.assertNotIn("fit", rows[0])


if __name__ == "__main__":
    unittest.main()
