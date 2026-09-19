from __future__ import annotations

from collections import defaultdict
from typing import Any

from .budget import BudgetResult, calculate_budget
from .evidence import evidence_ids, render_reasons
from .opening import day_group, opening_status, time_bucket


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def percentile(value: float, values: list[float], minimum_count: int = 5) -> float | None:
    if len(values) < minimum_count:
        return None
    smaller = sum(x < value for x in values)
    equal = sum(x == value for x in values)
    return (smaller + 0.5 * equal) / len(values)


def _metrics_for_place(db, snapshot_id: str, place: dict, conditions) -> tuple[dict[str, Any] | None, list[str]]:
    bucket = time_bucket(conditions.visit_at)
    if bucket is None:
        return None, []
    rows = db.metrics(snapshot_id, place["area_id"], place["category"], day_group(conditions.visit_at), bucket)
    usable = [
        row for row in rows
        if str(row.get("coverage_status", "")).lower() not in {"missing", "suppressed", "unavailable", "비공개", "결측"}
    ]
    if not usable:
        return None, []
    usable.sort(key=lambda row: (row["week_start"], row["metric_id"]))
    metric_ids = [row["metric_id"] for row in usable]
    return {
        "period_start": min(row["week_start"] for row in usable),
        "period_end": max(row["week_end"] for row in usable),
        "aggregation_unit": "area_category_period",
        "metric_ids": metric_ids,
    }, metric_ids


def _item(place: dict, budget: BudgetResult, conditions, db, snapshot_id: str, activity: dict | None, metric_ids: list[str]) -> dict[str, Any]:
    return {
        "place_id": place["place_id"],
        "name": place["name"],
        "region_id": place["region_id"],
        "category": place["category"],
        "cost_min": budget.cost_min,
        "cost_max": budget.cost_max,
        "per_person_min": budget.per_person_min,
        "per_person_max": budget.per_person_max,
        "remaining_min": budget.remaining_min,
        "remaining_max": budget.remaining_max,
        "budget_status": budget.status,
        "evidence_ids": evidence_ids(db, snapshot_id, place["place_id"], metric_ids),
        "opening_status": opening_status(place, conditions.visit_at) if place.get("opening_hours_eligible_for_filter") else "unknown",
        "is_mock": bool(place["is_mock"]),
        "data_as_of": {"price": None, "opening_hours": place.get("opening_observed_at"), "atmosphere": place.get("atmosphere_observed_at"), "area_metrics": None},
        "reasons": render_reasons(place, budget, conditions, activity),
        "data_status_reason": budget.reason or ("AREA_EVIDENCE_MISSING" if activity is None else None),
    }


def rank_recommendations(settings, db, conditions) -> dict[str, Any]:
    snapshot = db.active_snapshot()
    snapshot_id = snapshot["snapshot_id"]
    places = db.list_places(snapshot_id, conditions.region_id, conditions.category)
    excluded = defaultdict(int)
    candidates: list[tuple[dict, BudgetResult, dict | None, list[str]]] = []
    insufficient: list[dict[str, Any]] = []
    for place in places:
        if not (place["party_min"] <= conditions.party_size <= place["party_max"]):
            excluded["party_size"] += 1
            continue
        if not set(conditions.required_atmosphere).issubset(set(place.get("atmosphere_tags", []))):
            excluded["required_atmosphere"] += 1
            continue
        status = opening_status(place, conditions.visit_at) if place.get("opening_hours_eligible_for_filter") else "unknown"
        if status == "closed":
            excluded["closed"] += 1
            continue
        bundle = db.price(snapshot_id, place["place_id"])
        menu_items = db.menu_items(snapshot_id, place["place_id"], budget_candidates_only=True)
        budget = calculate_budget(settings, conditions, bundle, menu_items, snapshot["reference_now"])
        if budget.status == "exceeds":
            excluded["budget"] += 1
            continue
        activity, metric_ids = _metrics_for_place(db, snapshot_id, place, conditions)
        if budget.status == "unknown" or (time_bucket(conditions.visit_at) is not None and not activity):
            insufficient.append(_item(place, budget, conditions, db, snapshot_id, activity, metric_ids))
            continue
        candidates.append((place, budget, activity, metric_ids))

    profile = settings.policy["ranking"]["profiles"][conditions.priority_profile]
    active = ["budget", "purpose"]
    if conditions.atmosphere_preferences:
        active.append("atmosphere")
    weights = {feature: profile[feature] for feature in active}
    denominator = sum(weights.values()) or 1
    weights = {feature: weight / denominator for feature, weight in weights.items()}
    scored: list[tuple[float, int, str, dict[str, Any]]] = []
    for place, budget, activity, metric_ids in candidates:
        components: dict[str, float] = {"budget": _clamp((budget.total_budget - budget.cost_max) / budget.total_budget), "purpose": 1.0 if conditions.purpose in place.get("purpose_tags", []) else 0.0}
        if "atmosphere" in active:
            components["atmosphere"] = len(set(conditions.atmosphere_preferences) & set(place.get("atmosphere_tags", []))) / len(conditions.atmosphere_preferences)
        score = sum(components[k] * weights[k] for k in active)
        item = _item(place, budget, conditions, db, snapshot_id, activity, metric_ids)
        item["data_as_of"]["price"] = db.price(snapshot_id, place["place_id"]).get("observed_at")
        metric_rows = db.metrics(snapshot_id, place["area_id"], place["category"], day_group(conditions.visit_at), time_bucket(conditions.visit_at))
        item["data_as_of"]["area_metrics"] = max((row["week_end"] for row in metric_rows), default=None)
        scored.append((score, budget.cost_max or 0, place["place_id"], item))
    scored.sort(key=lambda x: (-round(x[0], 6), x[1], x[2]))
    insufficient.sort(key=lambda x: x["place_id"])
    return {
        "items": [x[3] for x in scored[: settings.policy["scope"]["max_results"]]],
        "insufficient_data_items": insufficient[: settings.policy["scope"]["max_results"]],
        "excluded_counts": dict(excluded),
        "active_features": active,
        "warnings": (
            ["가상 데이터 기반 결과입니다.", "실제 지도·LLM·실데이터 미연결 상태입니다."]
            if bool(snapshot["is_mock"])
            else ["검증된 스냅샷 기반 결과입니다. 출처와 기준일을 함께 확인하세요."]
        ) + ["과거 상권 소비활동은 점포별 순위·매출·현재 인기·실시간 혼잡이 아닌 공통 참고 근거입니다."],
    }
