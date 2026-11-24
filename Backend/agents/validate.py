"""Parse and validate each click-analysis role's JSON output."""
from __future__ import annotations

import re


class ValidationError(ValueError):
    pass


NEWS_DIRECTIONS = ("positive", "neutral", "negative", "mixed")
SOCIAL_DIRECTIONS = NEWS_DIRECTIONS + ("no_data",)
MOMENTUM = ("improving", "flat", "weakening")
VOLUME = ("above_average", "normal", "below_average")
SENTIMENTS = ("positive", "neutral", "negative")

_ID_TOKEN = re.compile(r"\b(?:news|metric|social):[A-Za-z0-9_.:\-]+")
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")  # unsigned: "418-430" is a range, not 418 and -430


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


_BARE = re.compile(r"\s*\(\s*[a-z][a-z0-9_]*(?:\s*,\s*[a-z][a-z0-9_]*)*\s*\)")


def strip_internal(text: str) -> str:
    """Remove bracketed internal metric names such as "(r60)" or "(ma200_gap, sma200)" from prose."""
    def drop(match):
        names = [t.strip() for t in match.group(0).strip(" ()").split(",")]
        return "" if all(re.search(r"[\d_]", n) for n in names) else match.group(0)

    text = re.sub(r"\s*\(\s*" + _ID_TOKEN.pattern + r"(?:\s*,\s*" + _ID_TOKEN.pattern + r")*\s*\)", "", text)
    return _BARE.sub(drop, text)


def _unseen_number(text: str, allowed: set[float]) -> bool:
    for match in _NUMBER.findall(_DATE.sub(" ", _ID_TOKEN.sub(" ", text))):
        try:
            value = float(match.replace(",", ""))
        except ValueError:
            continue
        if not _number_allowed(value, allowed):
            return True
    return False


def clean_text(text: str, numbers: set[float], where: str) -> str:
    """Drop only the sentences that use a number not in the context; fail only when nothing is left."""
    kept = [s for s in re.split(r"(?<=[.!?])\s+", strip_internal(text).strip())
            if not _unseen_number(s, numbers)]
    if not kept:
        raise ValidationError(f"{where} uses a number not in the context")
    return " ".join(kept)


def _safe_text(value, numbers: set[float]) -> str:
    """A short optional line; "" when missing or when every sentence has an unseen number."""
    if not isinstance(value, str) or not value.strip():
        return ""
    try:
        return clean_text(value, numbers, "text")
    except ValidationError:
        return ""


def _string(data: dict, key: str, where: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{where}.{key} must be a non-empty string")
    return value.strip()


def _evidence_list(value, allowed: set[str], where: str) -> list[str]:
    if not isinstance(value, list):
        raise ValidationError(f"{where}.evidence must be a list")
    ids = []
    for item in value:
        if not isinstance(item, str):
            raise ValidationError(f"{where}.evidence items must be strings")
        if item not in allowed and (" " in item or len(item) > 60):
            # the model pasted a sentence into the list: keep only the allowed ids written inside it
            ids.extend(i for i in dict.fromkeys(_ID_TOKEN.findall(item)) if i in allowed and i not in ids)
            continue
        if item not in allowed:
            raise ValidationError(f"{where} cites an evidence id not in the context: {item}")
        ids.append(item)
    if not ids:
        raise ValidationError(f"{where} needs at least one evidence id")
    return ids


def _direction(data: dict, role: str, allowed: tuple[str, ...]) -> str:
    direction = data.get("direction")
    if direction not in allowed:
        raise ValidationError(f"{role}.direction must be one of {list(allowed)}")
    return direction


def _market(data: dict, allowed: set[str], numbers: set[float], levels: dict | None) -> dict:
    summary = clean_text(_string(data, "summary", "market"), numbers, "market.summary")
    evidence = _evidence_list(data.get("evidence"), allowed, "market")
    levels = levels or {"support": [], "resistance": []}

    def picks(key: str) -> list[dict]:
        wanted = {round(float(item["price"]), 2) for item in levels.get(key) or []}
        out = []
        for item in data.get(key) or []:
            if not isinstance(item, dict):
                continue
            try:
                price = round(float(item.get("price")), 2)
            except (TypeError, ValueError):
                continue
            if price not in wanted:
                continue  # the model may only choose a level the code computed
            out.append({"price": price, "why": _safe_text(item.get("why"), numbers)})
        return out[:3]

    def label(key: str, values: tuple[str, ...], fallback: str) -> dict:
        raw = data.get(key) if isinstance(data.get(key), dict) else {}
        label = raw.get("label") if raw.get("label") in values else fallback
        return {"label": label, "why": _safe_text(raw.get("why"), numbers)}

    return {
        "summary": summary,
        "evidence": evidence,
        "support": picks("support"),
        "resistance": picks("resistance"),
        "momentum": label("momentum", MOMENTUM, "flat"),
        "volume": label("volume", VOLUME, "normal"),
    }


def _news(data: dict, allowed: set[str], numbers: set[float]) -> dict:
    direction = _direction(data, "news", NEWS_DIRECTIONS)
    summary = clean_text(_string(data, "summary", "news"), numbers, "news.summary")
    return {"direction": direction, "summary": summary,
            "evidence": _evidence_list(data.get("evidence"), allowed, "news")}


def _social(data: dict, allowed: set[str], numbers: set[float]) -> dict:
    direction = _direction(data, "social", SOCIAL_DIRECTIONS)
    summary = clean_text(_string(data, "summary", "social"), numbers, "social.summary")
    items = []
    for item in data.get("items") or []:
        if not isinstance(item, dict):
            continue
        item_id, sentiment = item.get("id"), item.get("sentiment")
        if item_id in allowed and sentiment in SENTIMENTS:
            items.append({"id": item_id, "sentiment": sentiment})
    return {"direction": direction, "summary": summary,
            "evidence": _evidence_list(data.get("evidence"), allowed, "social"), "items": items}


def validate(role: str, data: dict, raw: str, allowed: set[str], numbers: set[float],
             levels: dict | None = None) -> dict:
    if not isinstance(data, dict) or not data:
        raise ValidationError(f"{role} did not return a JSON object")
    if role == "market":
        return _market(data, allowed, numbers, levels)
    if role == "news":
        return _news(data, allowed, numbers)
    if role == "social":
        return _social(data, allowed, numbers)
    raise ValidationError(f"unknown role {role}")
