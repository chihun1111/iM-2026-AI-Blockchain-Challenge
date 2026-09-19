from __future__ import annotations

import json

import pytest

from backend.app.config import ROOT
from backend.app.readiness import validate_candidate_register, validate_gemini_approval_plan


def test_current_v32_register_stays_reference_only():
    result = validate_candidate_register(ROOT / "data" / "real" / "data_candidates.json")
    assert result["candidate_place_count"] == 3
    assert result["candidate_menu_count"] == 7
    assert result["verified_menu_ids"] == []
    assert result["s04_source_acquired"] is True
    assert result["s04_place_matching_completed"] is True
    assert result["place_blockers"] == {}
    assert result["scope_blockers"] == ["spatial_mapping_status"]
    assert result["behavior_ready"] is False
    assert result["importable"] is False


def test_candidate_cannot_be_promoted_with_unknown_mandatory_cost(tmp_path):
    source = json.loads((ROOT / "data" / "real" / "data_candidates.json").read_text(encoding="utf-8"))
    menu = source["menu_candidates"][0]
    menu.update({
        "eligible_for_verified_budget": True,
        "price_krw": menu["published_price_krw"],
        "confirmed_on": "2026-09-19",
        "confirmed_by_role": "점포 운영자",
        "portion": "1인분",
        "minimum_order": 1,
        "usage_basis": "점포 확인",
        "source_url": "https://example.test/confirmed-menu",
    })
    path = tmp_path / "data_candidates.json"
    path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(RuntimeError, match="mandatory_cost"):
        validate_candidate_register(path)


def test_current_gemini_plan_is_valid_but_not_enabled():
    result = validate_gemini_approval_plan(ROOT / "config" / "gemini_approval_plan.json")
    assert result["enabled"] is False
    assert "data_api_gate" in result["blockers"]
