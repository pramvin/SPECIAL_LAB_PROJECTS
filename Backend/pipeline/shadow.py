"""Shadow portfolios: several ways to pick a Top 5, logged every day and scored against SPY.

We cannot know in advance which recipe for narrowing the ranked list to five stocks is any good, and no
backtest of ours has shown that picking direction works. So each day every recipe below writes down its five
stocks (nothing is bought, nothing is shown to users) and later we measure what those stocks did. The point is a
fair comparison, including two random controls.

Recipes (horizon 1w only, all start from the rule score in `recommendations`)
- rules          top 5 by rule score, at most 2 per sector                       (the current method)
- calm           from the top 30 by score, the 5 with the smallest daily range (ATR %)
- bigmove        from the top 30, the 5 with the highest big-move chance (`bigmove_p`; skipped if fewer than 5 have it)
- no_earnings    like `rules`, but skipping stocks that report earnings within 5 days (`pipeline.earnings` data)
- volume         from the top 30, the 5 whose last daily volume is highest vs their previous 30-day average
- ai_veto        like `rules`, but skipping stocks whose latest AI review says Underweight or Sell
- random_top30   5 random stocks from the top 30 by score (control: does choosing inside the top 30 matter?)
- random_pool    5 random stocks from everything that passed the filters (control: does the score matter?)
Random picks are seeded by the date and recipe name, so a rerun repeats them.

Measurement
- entry = the daily close of the ranking date (`recommendations.as_of`); that is not a price anyone could trade
  at, so read the numbers as a comparison between recipes, not as profit
- return after 1 and 5 trading days (closes in `prices`), minus SPY over the same dates ("excess")
- picks are logged only if the ranking is at most 4 days old; run `pipeline.ingest` and `pipeline.rank` first
  (they refresh prices and REPLACE all recommendations, so they are not part of the hourly job)

Decision rule, fixed before any data: a recipe is a candidate for the real Top 5 only after 40 logged days, and only
if its mean 5-day excess return beats both `rules` and the two random controls. Fewer days are counts, not a result.

Run from Backend/ (the hourly wrapper `pipeline.collect_hourly` runs it every hour, it is idempotent):
  .venv/bin/python -m pipeline.shadow            # log today's picks if new, score the ones that have matured
  .venv/bin/python -m pipeline.shadow --report   # mean excess return per recipe
"""
import argparse
import os
import random
from datetime import date, datetime, timedelta, timezone

from app.dbcompat import connect, table_names

DB_PATH = os.environ.get("PLANWISE_DB", os.path.join(os.path.dirname(__file__), "..", "planwise.db"))
N_PICKS = 5
POOL = 30
PER_SECTOR = 2
EARNINGS_DAYS = 5
MAX_AGE_DAYS = 4
VETO_RATINGS = ("Underweight", "Sell")
RECIPES = ["rules", "calm", "bigmove", "no_earnings", "volume", "ai_veto", "random_top30", "random_pool"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS shadow_picks (
  recipe TEXT NOT NULL,
  as_of TEXT NOT NULL,
  ticker TEXT NOT NULL,
  rank INTEGER NOT NULL,
  entry REAL NOT NULL,
  ret_1d REAL, spy_1d REAL,
  ret_5d REAL, spy_5d REAL,
  logged_at TEXT NOT NULL,
  scored_at TEXT,
  PRIMARY KEY (recipe, as_of, ticker)
);
"""


def top_n(cands: list[dict], n: int = N_PICKS, per_sector: int = PER_SECTOR) -> list[str]:
    """Best `n` by the order given, at most `per_sector` from one sector."""
    out, used = [], {}
    for c in cands:
        if used.get(c["sector"], 0) >= per_sector:
            continue
        used[c["sector"]] = used.get(c["sector"], 0) + 1
        out.append(c["ticker"])
        if len(out) == n:
            break
    return out


def pick(recipe: str, cands: list[dict], ctx: dict, as_of: str) -> list[str]:
    """Tickers for one recipe. `cands` is sorted by score, best first. An empty list means 'skip today'."""
    pool = cands[:POOL]
    if recipe == "rules":
        return top_n(cands)
    if recipe == "calm":
        return [c["ticker"] for c in sorted((c for c in pool if c["atr_pct"] is not None), key=lambda c: c["atr_pct"])][:N_PICKS]
    if recipe == "bigmove":
        have = [c for c in pool if c["bigmove_p"] is not None]
        return [c["ticker"] for c in sorted(have, key=lambda c: -c["bigmove_p"])][:N_PICKS] if len(have) >= N_PICKS else []
    if recipe == "no_earnings":
        return top_n([c for c in cands if c["ticker"] not in ctx["earnings_soon"]])
    if recipe == "volume":
        have = [c for c in pool if ctx["volume_ratio"].get(c["ticker"]) is not None]
        return ([c["ticker"] for c in sorted(have, key=lambda c: -ctx["volume_ratio"][c["ticker"]])][:N_PICKS]
                if len(have) >= N_PICKS else [])
    if recipe == "ai_veto":
        return top_n([c for c in cands if c["ticker"] not in ctx["ai_bad"]])
    if recipe in ("random_top30", "random_pool"):
        source = pool if recipe == "random_top30" else cands
        return random.Random(f"{as_of}:{recipe}").sample([c["ticker"] for c in source], min(N_PICKS, len(source)))
    raise ValueError(recipe)


def load_candidates(conn, as_of: str) -> list[dict]:
    rows = conn.execute(
        "SELECT ticker, sector, score, atr_pct, bigmove_p, entry FROM recommendations "
        "WHERE horizon = '1w' AND as_of = ? ORDER BY score DESC, ticker", (as_of,)).fetchall()
    return [dict(zip(("ticker", "sector", "score", "atr_pct", "bigmove_p", "entry"), r)) for r in rows]


def volume_ratio(conn, ticker: str, as_of: str) -> float | None:
    """Last daily volume up to `as_of` divided by the average of the 30 days before it."""
    vols = [r[0] for r in conn.execute(
        "SELECT volume FROM prices WHERE ticker = ? AND date <= ? ORDER BY date DESC LIMIT 31", (ticker, as_of)).fetchall()]
    if len(vols) < 21:
        return None
    base = sum(vols[1:]) / len(vols[1:])
    return vols[0] / base if base else None


def build_context(conn, cands: list[dict], as_of: str) -> dict:
    tables = table_names(conn)
    tickers = [c["ticker"] for c in cands]
    soon: set[str] = set()
    if "earnings_events" in tables:
        from pipeline.earnings import upcoming

        soon = set(upcoming(conn, tickers, date.fromisoformat(as_of), EARNINGS_DAYS))
    bad: set[str] = set()
    if "agent_runs" in tables:
        rows = conn.execute(
            "SELECT ticker, rating FROM agent_runs WHERE id IN (SELECT MAX(id) FROM agent_runs "
            "WHERE horizon = '1w' AND status IN ('ok', 'partial') GROUP BY ticker)").fetchall()
        bad = {t for t, rating in rows if rating in VETO_RATINGS}
    vr = {c["ticker"]: volume_ratio(conn, c["ticker"], as_of) for c in cands[:POOL]}
    return {"earnings_soon": soon, "ai_bad": bad, "volume_ratio": vr}


def log_picks(conn, now: datetime | None = None) -> dict:
    """Write today's picks of every recipe once per ranking date."""
    now = now or datetime.now(timezone.utc)
    conn.executescript(SCHEMA)
    row = conn.execute("SELECT MAX(as_of) FROM recommendations WHERE horizon = '1w'").fetchone()
    as_of = row[0] if row else None
    if not as_of:
        return {"status": "no recommendations"}
    if date.fromisoformat(as_of) < now.date() - timedelta(days=MAX_AGE_DAYS):
        return {"status": "stale", "as_of": as_of}
    if conn.execute("SELECT COUNT(*) FROM shadow_picks WHERE as_of = ?", (as_of,)).fetchone()[0]:
        return {"status": "already logged", "as_of": as_of}
    cands = load_candidates(conn, as_of)
    ctx = build_context(conn, cands, as_of)
    entry = {c["ticker"]: c["entry"] for c in cands}
    rows, per_recipe = [], {}
    for recipe in RECIPES:
        tickers = pick(recipe, cands, ctx, as_of)
        per_recipe[recipe] = len(tickers)
        rows += [(recipe, as_of, t, i + 1, entry[t], now.isoformat()) for i, t in enumerate(tickers)]
    with conn:
        conn.executemany(
            "INSERT INTO shadow_picks (recipe, as_of, ticker, rank, entry, logged_at) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (recipe, as_of, ticker) DO NOTHING", rows)
    return {"status": "logged", "as_of": as_of, "picks": per_recipe}


def fetch_spy() -> dict[str, float]:
    """{YYYY-MM-DD: SPY close} for the last year."""
    import yfinance as yf

    s = yf.Ticker("SPY").history(period="1y", auto_adjust=True)["Close"].dropna()
    return {d: float(v) for d, v in zip(s.index.strftime("%Y-%m-%d"), s.values)}


def _spy_return(spy: dict[str, float], start: str, end: str) -> float | None:
    """SPY return from the last close on or before `start` to the close on `end`."""
    base_days = [d for d in spy if d <= start]
    if not base_days or end not in spy:
        return None
    return spy[end] / spy[max(base_days)] - 1


def score_matured(conn, get_spy=fetch_spy, now: datetime | None = None) -> dict:
    """Fill the 1-day and 5-day returns of every logged pick whose trading days have passed."""
    now = now or datetime.now(timezone.utc)
    conn.executescript(SCHEMA)
    pend = conn.execute(
        "SELECT recipe, as_of, ticker, entry, ret_1d, ret_5d FROM shadow_picks WHERE ret_5d IS NULL ORDER BY as_of").fetchall()
    stats = {"pending": len(pend), "updated": 0}
    cache: dict[tuple, list] = {}
    spy = None
    updates = []
    for recipe, as_of, ticker, entry, r1, r5 in pend:
        key = (ticker, as_of)
        if key not in cache:
            cache[key] = conn.execute(
                "SELECT date, close FROM prices WHERE ticker = ? AND date > ? ORDER BY date LIMIT 5", (ticker, as_of)).fetchall()
        bars = cache[key]
        if not bars:
            continue
        if spy is None:
            spy = get_spy()
        new = {}
        for slot, idx, old in (("1d", 0, r1), ("5d", 4, r5)):
            if old is not None or len(bars) <= idx:
                continue
            day, close = bars[idx][0], bars[idx][1]
            s = _spy_return(spy, as_of, day)
            if s is not None and entry:
                new[slot] = (close / entry - 1, s)
        if new:
            updates.append((
                new["1d"][0] if "1d" in new else None, new["1d"][1] if "1d" in new else None,
                new["5d"][0] if "5d" in new else None, new["5d"][1] if "5d" in new else None,
                now.isoformat(), recipe, as_of, ticker))
    if updates:
        with conn:
            conn.executemany(
                "UPDATE shadow_picks SET ret_1d = COALESCE(?, ret_1d), spy_1d = COALESCE(?, spy_1d), "
                "ret_5d = COALESCE(?, ret_5d), spy_5d = COALESCE(?, spy_5d), scored_at = ? "
                "WHERE recipe = ? AND as_of = ? AND ticker = ?", updates)
    stats["updated"] = len(updates)
    return stats


def summarize(conn) -> dict[str, dict]:
    """Per recipe: scored picks, logged days, mean excess return after 1 and 5 days, share beating SPY."""
    rows = conn.execute(
        "SELECT recipe, as_of, ret_1d, spy_1d, ret_5d, spy_5d FROM shadow_picks").fetchall()
    per: dict[str, dict] = {r: {"d1": [], "d5": [], "days5": {}} for r in RECIPES}
    for recipe, as_of, r1, s1, r5, s5 in rows:
        if recipe not in per:
            continue
        if r1 is not None and s1 is not None:
            per[recipe]["d1"].append(r1 - s1)
        if r5 is not None and s5 is not None:
            per[recipe]["d5"].append(r5 - s5)
            per[recipe]["days5"].setdefault(as_of, []).append(r5 - s5)
    mean = lambda v: sum(v) / len(v) if v else None  # noqa: E731
    out = {}
    base = {d: mean(v) for d, v in per["rules"]["days5"].items()}
    for recipe, p in per.items():
        day_means = {d: mean(v) for d, v in p["days5"].items()}
        common = [d for d in day_means if d in base]
        out[recipe] = {
            "n1": len(p["d1"]), "n5": len(p["d5"]), "days5": len(day_means),
            "mean1": mean(p["d1"]), "mean5": mean(p["d5"]),
            "beat5": (sum(1 for x in p["d5"] if x > 0) / len(p["d5"])) if p["d5"] else None,
            "vs_rules": mean([day_means[d] - base[d] for d in common]) if common else None,
        }
    return out


def report(conn) -> None:
    conn.executescript(SCHEMA)
    logged = conn.execute("SELECT COUNT(DISTINCT as_of), MIN(as_of), MAX(as_of) FROM shadow_picks").fetchone()
    print(f"days logged: {logged[0]} ({logged[1]} to {logged[2]})")
    res = summarize(conn)
    f = lambda v: "     -" if v is None else f"{v * 100:+6.2f}%"  # noqa: E731
    print("recipe          picks1d  1d excess   picks5d  days  5d excess  beat SPY  vs rules")
    for recipe in sorted(res, key=lambda r: -(res[r]["mean5"] if res[r]["mean5"] is not None else -9)):
        r = res[recipe]
        beat = "      -" if r["beat5"] is None else f"{r['beat5'] * 100:6.0f}%"
        print(f"{recipe:<14}  {r['n1']:>7}  {f(r['mean1'])}   {r['n5']:>7}  {r['days5']:>4}  {f(r['mean5'])}  {beat}  {f(r['vs_rules'])}")
    print("excess = return minus SPY over the same days; read as counts until 40 logged days")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="print mean excess return per recipe")
    args = ap.parse_args()
    from agents import config

    config.load_env()  # DATABASE_URL (Neon) unless PLANWISE_DB points at a SQLite file
    conn = connect(DB_PATH)
    conn.executescript(SCHEMA)
    if args.report:
        report(conn)
        return
    logged = log_picks(conn)
    note = ""
    if logged["status"] == "stale":
        note = " (ranking is old: run pipeline.ingest and pipeline.rank to start logging)"
    elif logged["status"] == "logged":
        note = " " + ", ".join(f"{k}={v}" for k, v in logged["picks"].items())
    print(f"shadow: log = {logged['status']}{note}")
    s = score_matured(conn)
    print(f"shadow: {s['pending']} picks waiting for returns, {s['updated']} updated")


if __name__ == "__main__":
    main()
