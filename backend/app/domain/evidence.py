from __future__ import annotations


CLAIM_TYPES = {
    "PRICE_RANGE",
    "BUDGET_FIT",
    "PURPOSE_MATCH",
    "ATMOSPHERE_TAG",
    "AREA_ACTIVITY",
    "AREA_TREND",
}


def render_reasons(place: dict, budget, conditions, activity: dict | None) -> list[str]:
    reasons: list[str] = []
    if budget.status == "fits":
        reasons.append("예산 상한 충족")
    if conditions.purpose in place.get("purpose_tags", []):
        reasons.append("요청 목적과 태그 일치")
    matched = [x for x in conditions.atmosphere_preferences if x in place.get("atmosphere_tags", [])]
    if matched:
        reasons.append("선호 분위기 태그 확인: " + ", ".join(matched))
    if activity:
        reasons.append("과거 상권 소비활동 참고 근거 연결")
    return reasons[:3]


def evidence_ids(db, snapshot_id: str, place_id: str, activity_metric_ids: list[str] | None = None) -> list[str]:
    ids = [f"E-PRICE-{place_id}", f"E-PURPOSE_MATCH-{place_id}", f"E-ATMOSPHERE_TAG-{place_id}"]
    if activity_metric_ids:
        ids.append(f"E-METRIC-{activity_metric_ids[-1]}")
    valid: list[str] = []
    for evidence_id in ids:
        row = db.evidence(snapshot_id, evidence_id)
        if row and row.get("claim_type") in CLAIM_TYPES:
            valid.append(evidence_id)
    return valid[:4]
