from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


VERIFIED_MENU_FIELDS = (
    "confirmed_on",
    "confirmed_by_role",
    "price_krw",
    "portion",
    "minimum_order",
    "mandatory_cost",
    "usage_basis",
)
SHA256_PATTERN = re.compile(r"^[0-9A-F]{64}$")
S04_SOURCE_ID = "S04-SEMAS-COMMERCIAL-STORE-CATALOG"


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"파일을 찾을 수 없습니다: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"JSON 형식이 올바르지 않습니다: {path.name} ({exc})") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON 최상위 값은 객체여야 합니다: {path.name}")
    return value


def validate_candidate_register(path: Path) -> dict[str, Any]:
    document = _read_object(path)
    if document.get("schema_version") != "3.2":
        raise RuntimeError("data_candidates.json schema_version은 3.2여야 합니다.")
    scope = document.get("scope")
    if not isinstance(scope, dict):
        raise RuntimeError("scope 객체가 없습니다.")
    if any(scope.get(field) is not None for field in ("boundary", "administrative_code", "radius_m")):
        raise RuntimeError("공식 확인 전에는 상권 경계·행정코드·반경을 채울 수 없습니다.")

    sources = document.get("sources")
    places = document.get("places")
    menus = document.get("menu_candidates")
    if not all(isinstance(value, list) and value for value in (sources, places, menus)):
        raise RuntimeError("sources, places, menu_candidates는 비어 있지 않은 배열이어야 합니다.")
    source_ids = [row.get("source_id") for row in sources]
    place_ids = [row.get("candidate_place_id") for row in places]
    menu_ids = [row.get("candidate_menu_id") for row in menus]
    for label, values in (("source_id", source_ids), ("candidate_place_id", place_ids), ("candidate_menu_id", menu_ids)):
        if any(not isinstance(value, str) or not value for value in values) or len(values) != len(set(values)):
            raise RuntimeError(f"{label}가 비어 있거나 중복되었습니다.")

    source_set = set(source_ids)
    place_set = set(place_ids)
    s04_sources = [row for row in sources if row.get("source_id") == S04_SOURCE_ID]
    if len(s04_sources) != 1:
        raise RuntimeError(f"{S04_SOURCE_ID} 출처는 정확히 하나여야 합니다.")
    s04_source = s04_sources[0]
    s04_acquired = s04_source.get("source_file_acquired") is True
    s04_matching_completed = s04_source.get("place_matching_completed") is True
    if s04_acquired:
        for field in ("source_file_local_path", "source_entry_name"):
            if not isinstance(s04_source.get(field), str) or not s04_source[field]:
                raise RuntimeError(f"S04 원본을 확보했지만 {field}가 없습니다.")
        for field in ("source_file_size_bytes", "source_entry_size_bytes", "source_entry_rows"):
            if not isinstance(s04_source.get(field), int) or s04_source[field] <= 0:
                raise RuntimeError(f"S04 원본을 확보했지만 {field}가 양수 정수가 아닙니다.")
        for field in ("source_file_sha256", "source_entry_sha256"):
            if not isinstance(s04_source.get(field), str) or not SHA256_PATTERN.fullmatch(s04_source[field]):
                raise RuntimeError(f"S04 원본을 확보했지만 {field}가 SHA-256 형식이 아닙니다.")
    if s04_matching_completed and not s04_acquired:
        raise RuntimeError("S04 원본 없이 점포 매칭을 완료 처리할 수 없습니다.")
    for place in places:
        if place.get("source_id") not in source_set:
            raise RuntimeError(f"장소 출처 참조가 유효하지 않습니다: {place.get('candidate_place_id')}")
    scope_blockers = [
        field for field in ("spatial_mapping_status", "category_mapping_status")
        if scope.get(field) not in {"CONFIRMED", "MATCHED"}
    ]
    place_blockers: dict[str, list[str]] = {}
    for place in places:
        missing: list[str] = []
        if not place.get("public_place_id"):
            missing.append("public_place_id")
        if place.get("official_store_match_status") not in {"MATCHED", "CONFIRMED"}:
            missing.append("official_store_match")
        elif place.get("official_store_source_id") != S04_SOURCE_ID:
            raise RuntimeError(f"장소의 공식 점포 출처가 S04가 아닙니다: {place.get('candidate_place_id')}")
        elif place.get("official_middle_category_code") != "I201" or place.get("official_middle_category_name") != "한식":
            raise RuntimeError(f"장소의 S04 한식 업종 매핑이 올바르지 않습니다: {place.get('candidate_place_id')}")
        elif any(place.get(field) in (None, "") for field in ("branch_address", "longitude", "latitude")):
            raise RuntimeError(f"장소의 S04 주소·위경도가 불완전합니다: {place.get('candidate_place_id')}")
        if missing:
            place_blockers[str(place["candidate_place_id"])] = missing
    verified_menu_ids: list[str] = []
    menu_blockers: dict[str, list[str]] = {}
    for menu in menus:
        menu_id = str(menu.get("candidate_menu_id"))
        if menu.get("candidate_place_id") not in place_set or menu.get("source_id") not in source_set:
            raise RuntimeError(f"메뉴의 장소 또는 출처 참조가 유효하지 않습니다: {menu_id}")
        missing_keys = [field for field in (*VERIFIED_MENU_FIELDS, "source_url", "evidence_file") if field not in menu]
        if missing_keys:
            raise RuntimeError(f"{menu_id} 검증 필드 키 누락: {', '.join(missing_keys)}")
        missing = [field for field in VERIFIED_MENU_FIELDS if menu.get(field) is None or menu.get(field) == ""]
        if not menu.get("source_url") and not menu.get("evidence_file"):
            missing.append("source_url_or_evidence_file")
        if menu.get("eligible_for_verified_budget") is True:
            if missing:
                raise RuntimeError(f"{menu_id}는 검증 필드가 없어 예산 후보가 될 수 없습니다: {', '.join(missing)}")
            if not isinstance(menu.get("price_krw"), int) or menu["price_krw"] <= 0:
                raise RuntimeError(f"{menu_id}.price_krw는 양수 정수여야 합니다.")
            if not isinstance(menu.get("minimum_order"), int) or menu["minimum_order"] <= 0:
                raise RuntimeError(f"{menu_id}.minimum_order는 양수 정수여야 합니다.")
            if not isinstance(menu.get("mandatory_cost"), int) or menu["mandatory_cost"] < 0:
                raise RuntimeError(f"{menu_id}.mandatory_cost는 확인된 0 이상의 정수여야 합니다.")
            try:
                datetime.fromisoformat(str(menu["confirmed_on"]))
            except ValueError as exc:
                raise RuntimeError(f"{menu_id}.confirmed_on은 ISO 8601 날짜/시각이어야 합니다.") from exc
            verified_menu_ids.append(menu_id)
        elif missing:
            menu_blockers[menu_id] = missing

    behavior = document.get("behavior_data_candidate")
    if not isinstance(behavior, dict):
        raise RuntimeError("behavior_data_candidate 객체가 없습니다.")
    behavior_blockers: list[str] = []
    if int(behavior.get("source_files_acquired", 0)) <= 0:
        behavior_blockers.append("source_files")
    if int(behavior.get("rows_acquired", 0)) <= 0:
        behavior_blockers.append("rows")
    if behavior.get("data_dictionary_acquired") is not True:
        behavior_blockers.append("data_dictionary")
    for field in ("analysis_permission", "export_permission", "submission_use_permission", "public_web_permission"):
        if behavior.get(field) in (None, "", "NOT_ACQUIRED", "UNKNOWN"):
            behavior_blockers.append(field)
    if behavior.get("eligible_for_area_evidence") is True and behavior_blockers:
        raise RuntimeError("행동 데이터 권한·실파일·사전이 없어 상권 근거로 사용할 수 없습니다.")
    if behavior.get("gemini_transmission_allowed") is not False:
        raise RuntimeError("카드 원본·집계의 Gemini 전송은 false여야 합니다.")

    return {
        "schema_version": "3.2",
        "candidate_place_count": len(places),
        "candidate_menu_count": len(menus),
        "verified_menu_ids": verified_menu_ids,
        "s04_source_acquired": s04_acquired,
        "s04_place_matching_completed": s04_matching_completed and not place_blockers,
        "scope_blockers": scope_blockers,
        "place_blockers": place_blockers,
        "menu_blockers": menu_blockers,
        "behavior_ready": not behavior_blockers,
        "behavior_blockers": behavior_blockers,
        "importable": bool(verified_menu_ids) and not behavior_blockers and not scope_blockers and not place_blockers,
    }


def validate_gemini_approval_plan(path: Path) -> dict[str, Any]:
    plan = _read_object(path)
    if plan.get("schema_version") != "3.2":
        raise RuntimeError("Gemini 승인안 schema_version은 3.2여야 합니다.")
    proposal = plan.get("proposal")
    cost = plan.get("cost_plan")
    key_policy = plan.get("key_policy")
    gate = plan.get("data_api_gate")
    approval = plan.get("approval")
    if not all(isinstance(value, dict) for value in (proposal, cost, key_policy, gate, approval)):
        raise RuntimeError("Gemini 승인안의 필수 객체가 누락되었습니다.")
    if proposal.get("model") != "gemini-3.5-flash-lite":
        raise RuntimeError("v3.2 제안 모델과 다릅니다.")
    if key_policy.get("required_server_variable") != "GEMINI_API_KEY" or key_policy.get("google_api_key_is_not_used_by_this_app") is not True:
        raise RuntimeError("Gemini 키 정책이 v3.2와 다릅니다.")
    for field in (
        "project_total_limit",
        "daily_limit",
        "input_usd_per_million_tokens",
        "output_usd_per_million_tokens_including_thinking",
        "max_input_tokens_per_attempt",
        "max_output_tokens_per_attempt",
        "max_attempts",
    ):
        if not isinstance(cost.get(field), (int, float)) or cost[field] <= 0:
            raise RuntimeError(f"cost_plan.{field}는 양수여야 합니다.")
    enabled = plan.get("status") == "APPROVED" and plan.get("llm_enabled") is True
    blockers: list[str] = []
    if gate.get("status") != "PASSED" or not gate.get("evidence"):
        blockers.append("data_api_gate")
    for field in (
        "approved_by",
        "approved_at",
        "approved_model",
        "approved_transmission_scope",
        "approved_project_total_limit_usd",
        "approved_daily_limit_usd",
    ):
        if approval.get(field) in (None, "", []):
            blockers.append(field)
    if approval.get("approved") is not True:
        blockers.append("approved")
    if enabled and blockers:
        raise RuntimeError("Gemini를 활성화했지만 승인 기록 또는 데이터 API 게이트가 불완전합니다.")
    return {"schema_version": "3.2", "enabled": enabled and not blockers, "blockers": blockers}
