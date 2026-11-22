"""Run from Backend/:  .venv/bin/python -m unittest tests.test_shadow -v"""
import os
import sqlite3
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone

from pipeline import earnings, shadow

AS_OF = "2026-11-16"  # a Monday
NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
SECTORS = ["tech", "tech", "tech", "finance", "finance", "energy"]


def cand(ticker, sector="tech", score=50, atr=3.0, big=0.3):
    return {"ticker": ticker, "sector": sector, "score": score, "atr_pct": atr, "bigmove_p": big, "entry": 100.0}


def ctx(**kw):
    base = {"earnings_soon": set(), "ai_bad": set(), "volume_ratio": {}}
    base.update(kw)
    return base


class PickTest(unittest.TestCase):
    def setUp(self):
        # 12 stocks, best score first; T00-T02 tech, T03-T05 finance, T06-T08 energy, T09-T11 health
        self.cands = [cand(f"T{i:02d}", ["tech", "finance", "energy", "health"][i // 3], score=90 - i,
                           atr=1.0 + i * 0.1, big=0.1 + i * 0.01) for i in range(12)]

    def test_rules_caps_two_per_sector(self):
        self.assertEqual(shadow.pick("rules", self.cands, ctx(), AS_OF), ["T00", "T01", "T03", "T04", "T06"])

    def test_calm_takes_smallest_atr_in_the_top_30(self):
        self.assertEqual(shadow.pick("calm", self.cands, ctx(), AS_OF), ["T00", "T01", "T02", "T03", "T04"])
        wild_first = [dict(c, atr_pct=10 - i) for i, c in enumerate(self.cands)]
        self.assertEqual(shadow.pick("calm", wild_first, ctx(), AS_OF)[0], "T11")

    def test_bigmove_needs_five_values_else_skips(self):
        self.assertEqual(shadow.pick("bigmove", self.cands, ctx(), AS_OF)[0], "T11")
        few = [dict(c, bigmove_p=None) for c in self.cands]
        few[0]["bigmove_p"] = 0.5
        self.assertEqual(shadow.pick("bigmove", few, ctx(), AS_OF), [])

    def test_no_earnings_and_ai_veto_skip_flagged_stocks(self):
        got = shadow.pick("no_earnings", self.cands, ctx(earnings_soon={"T00", "T01"}), AS_OF)
        self.assertNotIn("T00", got)
        self.assertEqual(got[:2], ["T02", "T03"])
        got = shadow.pick("ai_veto", self.cands, ctx(ai_bad={"T00"}), AS_OF)
        self.assertEqual(got[0], "T01")

    def test_volume_uses_highest_ratio_and_needs_five(self):
        ratios = {c["ticker"]: float(i) for i, c in enumerate(self.cands)}
        self.assertEqual(shadow.pick("volume", self.cands, ctx(volume_ratio=ratios), AS_OF)[0], "T11")
        self.assertEqual(shadow.pick("volume", self.cands, ctx(volume_ratio={"T00": 1.0}), AS_OF), [])

    def test_random_is_repeatable_and_controls_differ(self):
        a = shadow.pick("random_top30", self.cands, ctx(), AS_OF)
        self.assertEqual(a, shadow.pick("random_top30", self.cands, ctx(), AS_OF))
        self.assertEqual(len(set(a)), 5)
        self.assertNotEqual(a, shadow.pick("random_pool", self.cands, ctx(), AS_OF))
        self.assertNotEqual(a, shadow.pick("random_top30", self.cands, ctx(), "2026-11-17"))


class DbBase(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(
            "CREATE TABLE recommendations (id INTEGER PRIMARY KEY, ticker TEXT, sector TEXT, horizon TEXT, entry REAL, "
            "score INTEGER, atr_pct REAL, bigmove_p REAL, as_of TEXT);"
            "CREATE TABLE prices (ticker TEXT, date TEXT, close REAL, volume INTEGER, PRIMARY KEY (ticker, date));"
            "CREATE TABLE agent_runs (id INTEGER PRIMARY KEY, ticker TEXT, horizon TEXT, status TEXT, rating TEXT);"
        )
        self.conn.executescript(earnings.SCHEMA)
        self.conn.executescript(shadow.SCHEMA)
        base = date.fromisoformat(AS_OF)
        for i in range(12):
            t = f"T{i:02d}"
            self.conn.execute("INSERT INTO recommendations (ticker, sector, horizon, entry, score, atr_pct, bigmove_p, as_of) "
                              "VALUES (?,?,?,?,?,?,?,?)", (t, ["tech", "finance", "energy", "health"][i // 3], "1w", 100.0,
                                                           90 - i, 1.0 + i * 0.1, 0.1 + i * 0.01, AS_OF))
            for k in range(-40, 8):  # 40 days of history, then 7 days after the ranking date
                d = (base + timedelta(days=k)).isoformat()
                close = 100.0 if k <= 0 else 100.0 + k * (1 if i == 0 else 0)  # T00 rises 1 per day after the ranking
                self.conn.execute("INSERT INTO prices VALUES (?,?,?,?)", (t, d, close, 1000 + i))
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.path)


class LogTest(DbBase):
    def test_logs_all_recipes_once(self):
        r = shadow.log_picks(self.conn, NOW)
        self.assertEqual(r["status"], "logged")
        self.assertEqual(r["picks"]["rules"], 5)
        self.assertEqual(shadow.log_picks(self.conn, NOW)["status"], "already logged")
        n = self.conn.execute("SELECT COUNT(*) FROM shadow_picks WHERE recipe = 'rules'").fetchone()[0]
        self.assertEqual(n, 5)

    def test_stale_ranking_is_not_logged(self):
        r = shadow.log_picks(self.conn, NOW + timedelta(days=10))
        self.assertEqual(r["status"], "stale")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM shadow_picks").fetchone()[0], 0)

    def test_context_from_earnings_and_ai_tables(self):
        self.conn.execute("INSERT INTO earnings_events (ticker, event_date, fetched_at) VALUES ('T00', '2026-11-18', 'x')")
        self.conn.execute("INSERT INTO agent_runs (ticker, horizon, status, rating) VALUES ('T01', '1w', 'ok', 'Sell')")
        shadow.log_picks(self.conn, NOW)
        ne = [r[0] for r in self.conn.execute("SELECT ticker FROM shadow_picks WHERE recipe = 'no_earnings'")]
        av = [r[0] for r in self.conn.execute("SELECT ticker FROM shadow_picks WHERE recipe = 'ai_veto'")]
        self.assertNotIn("T00", ne)
        self.assertIn("T00", av)
        self.assertNotIn("T01", av)

    def test_no_recommendations(self):
        self.conn.execute("DELETE FROM recommendations")
        self.assertEqual(shadow.log_picks(self.conn, NOW)["status"], "no recommendations")

    def test_volume_ratio_from_daily_prices(self):
        self.assertAlmostEqual(shadow.volume_ratio(self.conn, "T00", AS_OF), 1.0)
        self.assertIsNone(shadow.volume_ratio(self.conn, "T00", "2026-09-30"))  # too little history


class ScoreTest(DbBase):
    def spy(self):
        base = date.fromisoformat(AS_OF)
        return {(base + timedelta(days=k)).isoformat(): 500.0 + 5.0 * max(k, 0) for k in range(-40, 8)}

    def test_returns_fill_as_trading_days_pass_and_subtract_spy(self):
        shadow.log_picks(self.conn, NOW)
        shadow.score_matured(self.conn, self.spy, NOW)
        row = self.conn.execute("SELECT ret_1d, spy_1d, ret_5d FROM shadow_picks WHERE ticker = 'T00' AND recipe = 'rules'").fetchone()
        self.assertAlmostEqual(row[0], 0.01)            # 100 -> 101
        self.assertAlmostEqual(row[1], 5.0 / 500.0)      # SPY 500 -> 505
        self.assertAlmostEqual(row[2], 0.05)             # 100 -> 105 after five bars

    def test_waits_for_enough_bars_and_never_overwrites(self):
        shadow.log_picks(self.conn, NOW)
        self.conn.execute("DELETE FROM prices WHERE date > '2026-11-18'")  # only two bars after the ranking date
        shadow.score_matured(self.conn, self.spy, NOW)
        row = self.conn.execute("SELECT ret_1d, ret_5d FROM shadow_picks WHERE ticker = 'T00' AND recipe = 'rules'").fetchone()
        self.assertIsNotNone(row[0])
        self.assertIsNone(row[1])
        self.conn.execute("UPDATE shadow_picks SET ret_1d = 9.99")
        shadow.score_matured(self.conn, self.spy, NOW)
        self.assertEqual(self.conn.execute("SELECT MAX(ret_1d) FROM shadow_picks").fetchone()[0], 9.99)

    def test_missing_spy_day_leaves_the_slot_empty(self):
        shadow.log_picks(self.conn, NOW)
        shadow.score_matured(self.conn, lambda: {}, NOW)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM shadow_picks WHERE ret_1d IS NOT NULL").fetchone()[0], 0)

    def test_report_numbers(self):
        shadow.log_picks(self.conn, NOW)
        shadow.score_matured(self.conn, self.spy, NOW)
        res = shadow.summarize(self.conn)
        self.assertEqual(res["rules"]["days5"], 1)
        self.assertEqual(res["rules"]["n5"], 5)
        # rules picks T00 (+5%, SPY +5%), the other four stay flat (-5% excess against SPY +5%)
        self.assertAlmostEqual(res["rules"]["mean5"], (0.0 + 4 * -0.05) / 5)
        self.assertAlmostEqual(res["rules"]["beat5"], 0.0)
        self.assertAlmostEqual(res["rules"]["vs_rules"], 0.0)


if __name__ == "__main__":
    unittest.main()
