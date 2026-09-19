from __future__ import annotations

import json


def conditions():
    return {
        "schema_version": "2.0", "region_id": "dongseongro", "category": "restaurant", "purpose": "meal",
        "party_size": 2, "budget": {"type": "per_person", "amount": 20000, "currency": "KRW"},
        "visit_at": "2026-09-19T19:00:00+09:00", "atmosphere_preferences": [], "required_atmosphere": [],
        "priority_profile": "balanced", "origin": None, "radius_m": 2000, "confirmed": True,
    }


def test_api_contract_and_common_metadata(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["db_access"] is True
    meta = client.get("/api/meta")
    assert meta.status_code == 200
    assert meta.json()["snapshot_id"] == "demo-v2-20260919"
    parse = client.post("/api/parse-query", json={"text": "동성로 친구랑 저녁 식사 인당 2만원"})
    assert parse.status_code == 200
    assert parse.json()["parser_mode"] == "rules"
    assert "party_size" in parse.json()["confirmation_required"]

    body = {"conditions": conditions(), "snapshot_id": "demo-v2-20260919"}
    recommendations = client.post("/api/recommendations", json=body)
    assert recommendations.status_code == 200
    assert len(recommendations.json()["items"]) <= 5
    assert all("score" not in item for item in recommendations.json()["items"])

    place = client.get("/api/places/DEMO-D01-01", params={"snapshot_id": "demo-v2-20260919"})
    assert place.status_code == 200
    assert place.json()["place"]["is_mock"] is True
    assert place.json()["price"]["unit_max"] == 18000

    budget = client.post("/api/budget/estimate", json={**body, "place_ids": ["DEMO-D01-01", "DEMO-D01-02"]})
    assert budget.status_code == 200
    assert budget.json()["total_budget"] == 40000
    assert budget.json()["items"][0]["cost_max"] == 36000


def test_api_errors_and_server_recalculation(client):
    bad_snapshot = client.post("/api/recommendations", json={"conditions": conditions(), "snapshot_id": "old-snapshot"})
    assert bad_snapshot.status_code == 409
    assert set(bad_snapshot.json()) == {"request_id", "error"}
    assert bad_snapshot.json()["error"]["code"] == "SNAPSHOT_MISMATCH"

    missing = client.get("/api/places/no-such-place", params={"snapshot_id": "demo-v2-20260919"})
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "PLACE_NOT_FOUND"

    fake_client_price = {"conditions": conditions(), "snapshot_id": "demo-v2-20260919", "place_ids": ["DEMO-D01-01"], "cost_max": 1}
    rejected = client.post("/api/budget/estimate", json=fake_client_price)
    assert rejected.status_code == 422

    too_long = client.post("/api/parse-query", json={"text": "x" * 501})
    assert too_long.status_code == 422
    huge = client.post("/api/parse-query", content=b"x" * 17000, headers={"content-type": "application/json"})
    assert huge.status_code == 413


def test_openapi_contains_six_api_paths(client):
    schema = client.get("/openapi.json").json()
    expected = {"/api/health", "/api/meta", "/api/parse-query", "/api/recommendations", "/api/places/{place_id}", "/api/budget/estimate"}
    assert expected.issubset(schema["paths"])
