from __future__ import annotations

from datetime import datetime

from .gemini import GeminiAdapter
from ..domain.parser import parse_query


def parse_with_provider(
    settings,
    text: str,
    reference_now: str | None = None,
    external_ai_consent: bool = False,
) -> dict:
    effective_reference = reference_now or settings.reference_now
    if settings.parser_mode != "gemini" or not settings.external_adapter_enabled or not external_ai_consent:
        result = parse_query(text, datetime.fromisoformat(effective_reference))
        if settings.parser_mode == "gemini" and settings.external_adapter_enabled and not external_ai_consent:
            result["warnings"].append("외부 AI 전송 동의가 없어 규칙 파서를 사용했습니다.")
        return result
    result = GeminiAdapter(settings).parse(text, effective_reference)
    candidate = result.candidate
    provider_warnings = ["Gemini 조건 초안 · 서버 스키마·예산·확정 상태 검증 필요"]
    if candidate.get("region_id") not in settings.policy["scope"]["regions"]:
        candidate["region_id"] = None
        provider_warnings.append("지원 범위 밖 지역은 확정하지 않았습니다.")
    if candidate.get("category") not in settings.policy["scope"]["categories"]:
        candidate["category"] = None
        provider_warnings.append("지원 범위 밖 업종은 확정하지 않았습니다.")
    candidate["priority_profile"] = "balanced"
    # Provider output is still untrusted. Convert it into the same draft shape
    # and run the deterministic fields/confirmation contract locally.
    draft = {
        "schema_version": "2.0",
        "region_id": candidate.get("region_id"),
        "category": candidate.get("category"),
        "purpose": candidate.get("purpose"),
        "party_size": candidate.get("party_size"),
        "budget": {"type": candidate.get("budget_type"), "amount": candidate.get("budget_amount"), "currency": "KRW"},
        "visit_at": candidate.get("visit_at"),
        "atmosphere_preferences": candidate.get("atmosphere_preferences", []),
        "required_atmosphere": candidate.get("required_atmosphere", []),
        "priority_profile": candidate.get("priority_profile") or "balanced",
        "origin": None,
        "radius_m": 2000,
        "confirmed": False,
    }
    missing = [
        field for field, value in [
            ("region_id", draft["region_id"]),
            ("category", draft["category"]),
            ("party_size", draft["party_size"]),
            ("budget.type", draft["budget"]["type"]),
            ("budget.amount", draft["budget"]["amount"]),
            ("visit_at", draft["visit_at"]),
        ] if value is None
    ]
    return {
        "draft": draft,
        "field_meta": {field: {"origin": "provider"} for field in ["region_id", "category", "party_size", "budget.type", "budget.amount", "visit_at"] if field not in missing},
        "missing_fields": missing,
        "confirmation_required": missing,
        "warnings": provider_warnings,
        "parser_mode": "gemini",
    }
