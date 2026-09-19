from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any


KST = timezone(timedelta(hours=9))


NUMBER_WORDS = {
    "한": 1, "하나": 1, "혼자": 1, "일": 1,
    "두": 2, "둘": 2, "이": 2,
    "세": 3, "셋": 3, "삼": 3,
    "네": 4, "넷": 4, "사": 4,
    "다섯": 5, "오": 5,
    "여섯": 6, "육": 6,
}


def _amount_from_match(raw: str) -> int | None:
    compact = re.sub(r"\s+", "", raw.replace(",", ""))
    if not compact:
        return None
    if compact.endswith("대"):
        return None
    if compact in {"만오천", "만오천원", "1만5천", "1만5천원"}:
        return 15000
    m = re.fullmatch(r"(\d+(?:\.\d+)?)만(?:(\d+)천)?(?:원)?", compact)
    if m:
        major = int(float(m.group(1)) * 10000)
        return major + int(m.group(2) or 0) * 1000
    m = re.fullmatch(r"(\d+)천(?:원)?", compact)
    if m:
        return int(m.group(1)) * 1000
    m = re.fullmatch(r"(\d+)(?:원)?", compact)
    return int(m.group(1)) if m else None


def _extract_amount(text: str) -> tuple[int | None, str | None]:
    # Explicit money tokens, including 3만5천원 and 20,000원.
    patterns = [
        r"(\d+(?:\.\d+)?\s*만\s*(?:\d+\s*천)?\s*원?\s*대?)",
        r"(만오천\s*원?\s*대?)",
        r"(\d{1,3}(?:,\d{3})+\s*원)",
        r"(\d+\s*원)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            raw = match.group(1)
            return _amount_from_match(raw), raw
    return None, None


def _extract_party(text: str) -> tuple[int | None, str, str | None]:
    if re.search(r"혼자|혼밥", text):
        return 1, "explicit", None
    for word, number in NUMBER_WORDS.items():
        if re.search(rf"{re.escape(word)}\s*(?:명|명이|명과|이)", text):
            return number, "explicit", None
    match = re.search(r"(?<![\d,])([1-6])\s*명", text)
    if match:
        return int(match.group(1)), "explicit", None
    if re.search(r"친구(?:랑|와|과)|친구", text):
        return 2, "inferred", "AMBIGUOUS_COMPANION_COUNT"
    if re.search(r"\b우리\b|우리", text):
        return None, "missing", "MISSING_PARTY_SIZE"
    return None, "missing", "MISSING_PARTY_SIZE"


def _extract_datetime(text: str, reference_now: datetime) -> tuple[str | None, str | None]:
    if reference_now.tzinfo is None:
        reference_now = reference_now.replace(tzinfo=KST)
    base_date = reference_now.date()
    explicit_date = re.search(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", text)
    if explicit_date:
        base_date = datetime(int(explicit_date.group(1)), int(explicit_date.group(2)), int(explicit_date.group(3)), tzinfo=KST).date()
    elif "내일" in text:
        base_date = (reference_now + timedelta(days=1)).date()
    elif "오늘" in text or "지금" in text:
        base_date = reference_now.date()

    if "지금" in text:
        return reference_now.isoformat(), "explicit"
    match = re.search(r"(?:(오전|오후|저녁|아침|점심)\s*)?(\d{1,2})\s*시", text)
    if not match:
        return None, "missing"
    modifier, raw_hour = match.groups()
    hour = int(raw_hour)
    if modifier in {"오후", "저녁"} and hour < 12:
        hour += 12
    if modifier == "정오":
        hour = 12
    if not 0 <= hour <= 23:
        return None, "invalid"
    dt = datetime(base_date.year, base_date.month, base_date.day, hour, tzinfo=KST)
    return dt.isoformat(), "explicit"


def parse_query(text: str, reference_now: datetime) -> dict[str, Any]:
    region_id: str | None = None
    if "동성로" in text:
        region_id = "dongseongro"
    elif re.search(r"수성못|해운대|강남|홍대", text):
        region_id = None

    category: str | None = None
    if re.search(r"식당|음식점|식사|밥|혼밥|한식", text) and not re.search(r"카페", text):
        category = "restaurant"

    purpose: str | None = None
    if "데이트" in text:
        purpose = "date"
    elif "친구" in text:
        purpose = "friends"
    elif category == "restaurant":
        purpose = "meal"

    party_size, party_origin, party_reason = _extract_party(text)
    amount, amount_raw = _extract_amount(text)
    budget_type: str | None = None
    budget_origin = "missing"
    if re.search(r"인당|1인당|1인", text):
        budget_type, budget_origin = "per_person", "explicit"
    elif re.search(r"총\s*예산|전체\s*예산|총|전체", text):
        budget_type, budget_origin = "total", "explicit"
    amount_origin = "explicit" if amount is not None else "missing"
    if amount_raw and amount is None:
        amount_origin = "missing"

    atmospheres: list[str] = []
    if re.search(r"조용|차분", text):
        atmospheres.append("quiet")
    if re.search(r"대화|이야기", text):
        atmospheres.append("conversation")
    if re.search(r"활기|시끌|북적", text):
        atmospheres.append("lively")
    if re.search(r"혼밥|혼자.*좋", text):
        atmospheres.append("solo_friendly")
    required = list(atmospheres) if re.search(r"반드시|꼭|필수|무조건", text) else []

    visit_at, visit_origin = _extract_datetime(text, reference_now)
    popularity_requested = bool(re.search(r"사람들이? 많이|많이 이용|활발|인기", text))
    priority = "balanced"

    field_meta: dict[str, dict[str, str]] = {}
    for field, origin in [("region_id", "explicit" if region_id else "missing"), ("category", "explicit" if category else "missing"), ("purpose", "inferred" if purpose else "missing"), ("party_size", party_origin), ("budget.type", budget_origin), ("budget.amount", amount_origin), ("visit_at", visit_origin), ("priority_profile", "default")]:
        if origin != "missing":
            field_meta[field] = {"origin": origin}
        elif field in {"region_id", "category", "party_size", "budget.type", "budget.amount", "visit_at"}:
            field_meta[field] = {"origin": "missing"}
    if party_reason:
        field_meta["party_size"]["reason_code"] = party_reason

    draft = {
        "schema_version": "2.0",
        "region_id": region_id,
        "category": category,
        "purpose": purpose,
        "party_size": party_size,
        "budget": {"type": budget_type, "amount": amount, "currency": "KRW"},
        "visit_at": visit_at,
        "atmosphere_preferences": atmospheres,
        "required_atmosphere": required,
        "priority_profile": priority,
        "origin": None,
        "radius_m": 2000,
        "confirmed": False,
    }
    missing = []
    for field, value in [("region_id", region_id), ("category", category), ("party_size", party_size), ("budget.type", budget_type), ("budget.amount", amount), ("visit_at", visit_at)]:
        if value is None:
            missing.append(field)
    confirmation = list(missing)
    if party_origin == "inferred" and "party_size" not in confirmation:
        confirmation.append("party_size")
    if not region_id and "region_id" not in confirmation:
        confirmation.append("region_id")
    warnings = ["규칙 기반 조건 분석 · 외부 AI 미연결"]
    if "수성못" in text:
        warnings.append("수성못은 현재 프로토타입 범위에서 제외되어 지역을 확정하지 않았습니다.")
    if "카페" in text:
        warnings.append("카페는 현재 프로토타입 범위에서 제외되어 업종을 확정하지 않았습니다.")
    if popularity_requested:
        warnings.append("과거 상권 집계는 점포별 인기·이용강도 순위에 사용하지 않습니다.")
    return {
        "draft": draft,
        "field_meta": field_meta,
        "missing_fields": missing,
        "confirmation_required": confirmation,
        "warnings": warnings,
        "parser_mode": "rules",
    }
