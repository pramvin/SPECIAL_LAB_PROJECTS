"""Parse and validate each role's JSON output.

Adapted from TauricResearch/TradingAgents (Apache-2.0), agents/rating.py
(`extract_rating` fallback) and agents/structured.py (retry shape).
"""
from __future__ import annotations

import re
import unicodedata

from . import config


class ValidationError(ValueError):
    pass


RATINGS = set(config.RATINGS)
SIGNALS = set(config.SIGNALS)

_ID_TOKEN = re.compile(r"\b(?:news|metric|fund|sec|social|macro|rule|agent|memory):[A-Za-z0-9_.:\-]+")
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")  # unsigned: "418-430" is a range, not 418 and -430
_RATING_LABEL = re.compile(
    r"(?<![a-z])rating\b[^:\-\u2010-\u2015]*[:\-\u2010-\u2015][\s*]*(\w+)", re.IGNORECASE)


def extract_rating(text: str) -> str | None:
    """The first labelled 5-tier rating in free text, or None."""
    if not text:
        return None
    norm = unicodedata.normalize("NFKC", text)
    for value in _RATING_LABEL.findall(norm):
        if value.lower() in {r.lower() for r in config.RATINGS}:
            return value.capitalize()
    return None


def numbers_in(text: str) -> set[float]:
    if not text:
        return set()
    text = _ID_TOKEN.sub(" ", text)
    text = _DATE.sub(" ", text)
    out = set()
    for match in _NUMBER.findall(text):
        try:
            out.add(abs(float(match.replace(",", ""))))
        except ValueError:
            continue
    return out


CONVENTIONAL = {30.0, 50.0, 70.0, 80.0, 100.0, 200.0}


def _number_allowed(value: float, allowed: set[float]) -> bool:
    value = abs(value)
    allowed = {abs(a) for a in allowed}
    if value.is_integer() and 1990 <= value <= 2035:
        return True  # a year
    if value.is_integer() and 1 <= value <= 20:
        return True  # a list counter
    if value in CONVENTIONAL:
        return True  # textbook thresholds such as RSI 30/70 or the 50/200-day averages
    for candidate in allowed:
        if (round(candidate, 0) == round(value, 0)
                or round(candidate, 1) == round(value, 1)
                or round(candidate, 2) == round(value, 2)):
            return True
        if candidate != 0 and abs(value - candidate) / abs(candidate) <= 0.005:
            return True
    return False


def check_numbers(text: str, allowed: set[float], where: str) -> None:
    if not text:
        return
    for match in _NUMBER.findall(_DATE.sub(" ", _ID_TOKEN.sub(" ", text))):
        try:
            value = float(match.replace(",", ""))
        except ValueError:
            continue
        if not _number_allowed(value, allowed):
            raise ValidationError(f"{where} uses a number not in the context: {match}")


def _string(data: dict, key: str, where: str, required: bool = True) -> str:
    value = data.get(key)
    if value is None and not required:
        return ""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{where}.{key} must be a non-empty string")
    return value.strip()


def _evidence_list(value, allowed: set[str], where: str, required: bool = True) -> list[str]:
    if value is None and not required:
        return []
    if not isinstance(value, list):
        raise ValidationError(f"{where}.evidence must be a list")
    ids = []
    for item in value:
        if not isinstance(item, str):
            raise ValidationError(f"{where}.evidence items must be strings")
        if item not in allowed:
            raise ValidationError(f"{where} cites an evidence id not in the context: {item}")
        ids.append(item)
    if required and not ids:
        raise ValidationError(f"{where} needs at least one evidence id")
    return ids


def _points(data: dict, key: str, allowed: set[str], numbers: set[float],
            where: str, minimum: int = 0, maximum: int | None = None) -> list[dict]:
    raw = data.get(key)
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        raise ValidationError(f"{where}.{key} must be a list")
    points = []
    for index, point in enumerate(raw):
        if not isinstance(point, dict):
            raise ValidationError(f"{where}.{key}[{index}] must be an object")
        text = _string(point, "text", f"{where}.{key}[{index}]")
        try:
            check_numbers(text, numbers, f"{where}.{key}[{index}].text")
        except ValidationError:
            continue  # a point with an invented number is dropped, never shown; the rest stay
        evidence = _evidence_list(point.get("evidence"), allowed, f"{where}.{key}[{index}]")
        if evidence:
            points.append({"text": text, "evidence": evidence})
    if len(points) < minimum:
        raise ValidationError(f"{where}.{key} needs at least {minimum} points with evidence")
    if maximum is not None:
        points = points[:maximum]
    return points


def _analyst(data: dict, allowed: set[str], numbers: set[float], role: str) -> dict:
    signal = data.get("signal")
    if signal not in SIGNALS:
        raise ValidationError(f"{role}.signal must be one of {sorted(SIGNALS)}")
    summary = _string(data, "summary", role)
    check_numbers(summary, numbers, f"{role}.summary")
    gaps = data.get("data_gaps") or []
    if not isinstance(gaps, list) or any(not isinstance(g, str) for g in gaps):
        raise ValidationError(f"{role}.data_gaps must be a list of strings")
    minimum = 0 if signal == "no_data" else 1
    points = _points(data, "points", allowed, numbers, role, minimum=minimum, maximum=6)
    return {"signal": signal, "summary": summary, "points": points, "data_gaps": [g.strip() for g in gaps if g.strip()]}


def _rating(data: dict, raw: str, role: str) -> str:
    rating = data.get("rating", data.get("lean"))
    if rating in RATINGS:
        return rating
    fallback = extract_rating(raw)
    if fallback:
        return fallback
    raise ValidationError(f"{role} has no valid rating")


def _sanity_trader(output: dict, entry, atr) -> dict:
    stop, target = output.get("suggested_stop"), output.get("suggested_target")
    stop = float(stop) if isinstance(stop, (int, float)) and not isinstance(stop, bool) else None
    target = float(target) if isinstance(target, (int, float)) and not isinstance(target, bool) else None
    if entry is None:
        output["suggested_stop"] = output["suggested_target"] = None
        return output
    entry = float(entry)
    limit = 4 * float(atr) if atr else None
    if (stop is None or not stop < entry or (limit is not None and abs(entry - stop) > limit)):
        stop = None
    if (target is None or not target > entry or (limit is not None and abs(target - entry) > limit)):
        target = None
    output["suggested_stop"], output["suggested_target"] = stop, target
    return output


def validate(role: str, data: dict, raw: str, allowed: set[str], numbers: set[float],
             rules: dict | None = None, atr: float | None = None) -> dict:
    if not isinstance(data, dict) or not data:
        raise ValidationError(f"{role} did not return a JSON object")

    if role in ("market", "news", "fundamentals", "social"):
        return _analyst(data, allowed, numbers, role)

    if role in ("bull", "bear"):
        points = _points(data, "points", allowed, numbers, role, minimum=2, maximum=4)
        return {"points": points}

    if role == "research_manager":
        lean = _rating(data, raw, role)
        rationale = _string(data, "rationale", role)
        check_numbers(rationale, numbers, f"{role}.rationale")
        evidence = _evidence_list(data.get("evidence"), allowed, role)
        return {"lean": lean, "rationale": rationale, "evidence": evidence}

    if role == "trader":
        stance = data.get("stance")
        if stance not in ("enter", "wait", "avoid"):
            raise ValidationError("trader.stance must be enter, wait or avoid")
        rationale = _string(data, "rationale", role)
        check_numbers(rationale, numbers, f"{role}.rationale")
        evidence = _evidence_list(data.get("evidence"), allowed, role)
        out = {"stance": stance, "rationale": rationale, "evidence": evidence,
               "suggested_stop": data.get("suggested_stop"),
               "suggested_target": data.get("suggested_target")}
        return _sanity_trader(out, (rules or {}).get("entry"), atr)

    if role in ("aggressive", "conservative", "neutral"):
        view = _string(data, "view", role)
        check_numbers(view, numbers, f"{role}.view")
        evidence = _evidence_list(data.get("evidence"), allowed, role)
        pct = data.get("suggested_position_pct")
        if not isinstance(pct, (int, float)) or isinstance(pct, bool) or not 0 <= pct <= 30:
            pct = None
        return {"view": view, "suggested_position_pct": pct, "evidence": evidence}

    if role == "triage":
        rating = _rating(data, raw, role)
        confidence = data.get("confidence")
        if confidence not in config.CONFIDENCES:
            raise ValidationError(f"triage.confidence must be one of {list(config.CONFIDENCES)}")
        summary = _string(data, "summary", role)
        check_numbers(summary, numbers, f"{role}.summary")
        points = _points(data, "points", allowed, numbers, role, minimum=1, maximum=3)
        return {"rating": rating, "confidence": confidence, "summary": summary, "points": points}

    if role == "portfolio_manager":
        rating = _rating(data, raw, role)
        summary = _string(data, "summary", role)
        check_numbers(summary, numbers, f"{role}.summary")
        risks = _points(data, "key_risks", allowed, numbers, role, minimum=0, maximum=6)
        evidence = _evidence_list(data.get("evidence"), allowed, role)
        return {"rating": rating, "summary": summary, "key_risks": risks, "evidence": evidence}

    raise ValidationError(f"unknown role {role}")
