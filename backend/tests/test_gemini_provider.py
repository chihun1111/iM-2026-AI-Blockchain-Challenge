from __future__ import annotations

import copy
from dataclasses import replace

from fastapi.testclient import TestClient

from backend.app.api import create_app


def _provider_result() -> dict:
    return {
        "draft": {
            "schema_version": "2.0",
            "region_id": "dongseongro",
            "category": "restaurant",
            "purpose": "meal",
            "party_size": 2,
            "budget": {"type": "per_person", "amount": 20000, "currency": "KRW"},
            "visit_at": "2026-09-19T19:00:00+09:00",
            "atmosphere_preferences": [],
            "required_atmosphere": [],
            "priority_profile": "balanced",
            "origin": None,
            "radius_m": 2000,
            "confirmed": False,
        },
        "field_meta": {
            "region_id": {"origin": "provider"},
            "category": {"origin": "provider"},
            "party_size": {"origin": "provider"},
            "budget.type": {"origin": "provider"},
            "budget.amount": {"origin": "provider"},
            "visit_at": {"origin": "provider"},
        },
        "missing_fields": [],
        "confirmation_required": [],
        "warnings": ["Gemini 조건 초안 · 서버 스키마·예산·확정 상태 검증 필요"],
        "parser_mode": "gemini",
    }


def _gemini_settings(demo_app):
    plan = copy.deepcopy(demo_app.state.settings.gemini_approval)
    plan["status"] = "APPROVED"
    plan["llm_enabled"] = True
    plan["data_api_gate"] = {"required": True, "status": "PASSED", "evidence": ["test:data-api"]}
    plan["proposal"]["model"] = "gemini-test-model"
    plan["approval"] = {
        "approved": True,
        "approved_by": "test-approver",
        "approved_at": "2026-09-19T12:00:00+09:00",
        "approved_model": "gemini-test-model",
        "approved_transmission_scope": list(plan["proposal"]["transmission_allowed"]),
        "approved_project_total_limit_usd": 5.0,
        "approved_daily_limit_usd": 1.0,
    }
    return replace(
        demo_app.state.settings,
        parser_mode="gemini",
        allow_external_calls=True,
        allow_paid_calls=True,
        llm_provider="gemini",
        llm_model="gemini-test-model",
        gemini_api_key="secret-for-test",
        gemini_approval=plan,
    )


def test_parse_query_uses_provider_result_after_api_contract(monkeypatch, demo_app):
    app = create_app(_gemini_settings(demo_app))
    monkeypatch.setattr("backend.app.api.parse_with_provider", lambda settings, text, **kwargs: _provider_result())

    with TestClient(app) as client:
        response = client.post("/api/parse-query", json={"text": "동성로 저녁 식사", "external_ai_consent": True})
        health = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["parser_mode"] == "gemini"
    assert response.json()["draft"]["region_id"] == "dongseongro"
    assert health.status_code == 200
    assert health.json()["adapters"]["llm"]["enabled"] is True
    assert "secret-for-test" not in health.text


def test_parse_query_falls_back_to_rules_when_provider_fails(monkeypatch, demo_app):
    app = create_app(_gemini_settings(demo_app))

    def fail_provider(settings, text, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr("backend.app.api.parse_with_provider", fail_provider)

    with TestClient(app) as client:
        response = client.post("/api/parse-query", json={"text": "동성로 친구랑 저녁 식사 인당 2만원", "external_ai_consent": True})

    assert response.status_code == 200
    assert response.json()["parser_mode"] == "rules"
    assert any("규칙 파서로 전환" in warning for warning in response.json()["warnings"])
