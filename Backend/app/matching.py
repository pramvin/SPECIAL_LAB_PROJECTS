"""Match stocks to a user's questionnaire answers (content-based, cosine similarity).

Pure functions, no I/O. Stock vector = sector one-hot + a calm/wild pair from ATR%.
User vector = chosen sectors + the calm/wild preference of their risk level.
Horizon is NOT matched here: it is a hard filter done by the caller.

Every constant below is a guess, not backtested or validated on real users.
"""
import math

SECTORS = [
    "tech", "communication", "healthcare", "finance", "energy", "consumer_discretionary",
    "consumer_staples", "industrials", "materials", "real_estate", "utilities", "other",
]
SECTOR_LABELS = {
    "tech": "Technology", "communication": "Communication", "healthcare": "Healthcare",
    "finance": "Finance", "energy": "Energy", "consumer_discretionary": "Consumer Discretionary",
    "consumer_staples": "Consumer Staples", "industrials": "Industrials", "materials": "Materials",
    "real_estate": "Real Estate", "utilities": "Utilities", "other": "Other sectors",
}
# Profiles saved before the 11-sector form used a single "consumer" key.
LEGACY_SECTORS = {"consumer": ["consumer_discretionary", "consumer_staples"]}


def expand_sectors(sectors: list[str]) -> list[str]:
    return [k for s in sectors for k in LEGACY_SECTORS.get(s, [s])]

ATR_CAP = 6.0  # ATR% at/above this counts as fully "wild" (max seen in the current data is 6.0)
TARGET_VOL = {"conservative": 0.2, "moderate": 0.5, "aggressive": 0.8}  # wanted volatility, 0 calm .. 1 wild
W_SECTOR = 1.0
W_RISK = 1.0
FIT_WEIGHT = 0.3  # share of fit in the final score; the rest is the stock's own score


def volatility(atr_pct: float | None) -> float:
    """ATR% -> 0 (calm) .. 1 (wild). Unknown -> 0.5 (neutral)."""
    if atr_pct is None:
        return 0.5
    return min(max(atr_pct / ATR_CAP, 0.0), 1.0)


def _risk_block(v: float) -> list[float]:
    # Two dims (wild, calm): a single dim would make cosine ignore the volatility level.
    return [W_RISK * v, W_RISK * (1 - v)]


def stock_vector(sector: str, atr_pct: float | None) -> list[float]:
    key = sector if sector in SECTORS else "other"
    return [W_SECTOR * (s == key) for s in SECTORS] + _risk_block(volatility(atr_pct))


def user_vector(sectors: list[str], risk_level: str) -> list[float]:
    sectors = expand_sectors(sectors)
    picked = set(SECTORS) if (not sectors or "any" in sectors) else set(sectors)
    return [W_SECTOR * (s in picked) for s in SECTORS] + _risk_block(TARGET_VOL[risk_level])


def cosine(a: list[float], b: list[float]) -> float:
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0


def fit(sector: str, atr_pct: float | None, sectors: list[str], risk_level: str) -> float:
    return cosine(stock_vector(sector, atr_pct), user_vector(sectors, risk_level))


def final_score(score: float, fit_value: float) -> float:
    return (1 - FIT_WEIGHT) * score + FIT_WEIGHT * 100 * fit_value


def match_reasons(sector: str, atr_pct: float | None, sectors: list[str], risk_level: str) -> list[str]:
    out = []
    sectors = expand_sectors(sectors)
    if sectors and "any" not in sectors and sector in sectors:
        out.append(f"Matches your {SECTOR_LABELS[sector]} interest")
    if atr_pct is not None:
        gap = abs(volatility(atr_pct) - TARGET_VOL[risk_level])
        if gap <= 0.2:
            out.append(f"Typical daily range {atr_pct:.1f}% fits your {risk_level} risk level")
    return out


def matches_interest(sector: str, sectors: list[str]) -> bool:
    return not sectors or "any" in sectors or sector in expand_sectors(sectors)


def rank_for_user(rows: list[dict], sectors: list[str], risk_level: str, top_n: int = 20) -> list[dict]:
    """rows need: sector, atr_pct, score. Returns copies sorted by final score with fit/match_reasons added."""
    scored = []
    for r in rows:
        f = fit(r["sector"], r.get("atr_pct"), sectors, risk_level)
        scored.append({**r, "fit": round(f, 3), "final_score": final_score(r["score"], f),
                       "match_reasons": match_reasons(r["sector"], r.get("atr_pct"), sectors, risk_level)})
    scored.sort(key=lambda x: -x["final_score"])
    return scored[:top_n]
