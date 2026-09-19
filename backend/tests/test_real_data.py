from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import date, timedelta

from fastapi.testclient import TestClient

from backend.app.api import create_app
from backend.app.config import ROOT, load_settings
from backend.app.db import Database
from backend.app.real_data import import_real_package, load_and_validate_real_package


def _write(path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _real_package(path) -> None:
    sources = [
        {"source_id": "SRC-PLACE", "name": "장소 원본", "kind": "place", "provider": "테스트 제공자", "permission_status": "public", "observed_at": "2026-09-18T10:00:00+09:00", "scope": "동성로 음식점", "note": "테스트", "source_uri": "https://example.test/places", "rights_evidence": "공개 이용 조건 확인", "is_mock": False},
        {"source_id": "SRC-MENU", "name": "메뉴 원본", "kind": "menu", "provider": "테스트 제공자", "permission_status": "approved", "observed_at": "2026-09-18T10:00:00+09:00", "scope": "검증 메뉴", "note": "테스트", "source_uri": "https://example.test/menu", "rights_evidence": "제공자 승인", "is_mock": False},
        {"source_id": "SRC-BEHAVIOR", "name": "행동 집계", "kind": "aggregate", "provider": "테스트 제공자", "permission_status": "authorized", "observed_at": "2026-09-18T10:00:00+09:00", "scope": "상권 주간 집계", "note": "테스트", "source_uri": "https://example.test/aggregate", "rights_evidence": "분석 및 화면 공개 허용", "is_mock": False},
    ]
    areas = [{"area_id": "REAL-D01", "region_id": "dongseongro", "name": "동성로", "boundary_type": "provided", "centroid": None, "is_mock": False}]
    opening = [{"weekday": weekday, "intervals": [["11:00", "23:00"]]} for weekday in range(7)]
    places = [{
        "place_id": "REAL-P01", "name": "검증 식당", "region_id": "dongseongro", "area_id": "REAL-D01", "category": "restaurant",
        "address_label": "대구 중구 검증로 1", "coordinates": None, "party_min": 1, "party_max": 6,
        "purpose_tags": ["meal", "friends"], "atmosphere_tags": ["conversation"], "opening_weekly": opening,
        "opening_exceptions": [], "opening_observed_at": "2026-09-18T10:00:00+09:00", "opening_hours_eligible_for_filter": True, "atmosphere_observed_at": "2026-09-18T10:00:00+09:00",
        "source_id": "SRC-PLACE", "is_mock": False,
    }]
    menu_items = [
        {"menu_item_id": "MENU-LOW", "place_id": "REAL-P01", "name": "기본 메뉴", "price_krw": 12000, "pricing_unit": "per_person", "minimum_order": 1, "portion": "1인분", "mandatory_cost": 1000, "confirmed_on": "2026-09-18T10:00:00+09:00", "confirmed_by_role": "점포 운영자", "usage_basis": "점포가 게시한 현재 메뉴 확인", "source_url": "https://example.test/menu/current", "evidence_file": None, "is_budget_candidate": True, "source_id": "SRC-MENU", "is_mock": False},
        {"menu_item_id": "MENU-HIGH", "place_id": "REAL-P01", "name": "대표 메뉴", "price_krw": 18000, "pricing_unit": "per_person", "minimum_order": 2, "portion": "1인분", "mandatory_cost": 2000, "confirmed_on": "2026-09-18T10:00:00+09:00", "confirmed_by_role": "점포 운영자", "usage_basis": "점포가 게시한 현재 메뉴 확인", "source_url": "https://example.test/menu/current", "evidence_file": None, "is_budget_candidate": True, "source_id": "SRC-MENU", "is_mock": False},
    ]
    metrics = []
    first = date(2026, 7, 20)
    for index in range(8):
        start = first + timedelta(days=7 * index)
        metrics.append({
            "metric_id": f"METRIC-{index + 1}", "area_id": "REAL-D01", "category": "restaurant", "day_group": "weekday", "time_bucket": "dinner",
            "week_start": start.isoformat(), "week_end": (start + timedelta(days=6)).isoformat(), "txn_count": 200 + index * 10,
            "merchant_count": 10, "footfall_count": None, "source_id": "SRC-BEHAVIOR", "metric_definition_version": "test-v1",
            "coverage_status": "complete", "is_mock": False,
        })
    values = {"sources.json": sources, "areas.json": areas, "places.json": places, "menu_items.json": menu_items, "area_metrics.json": metrics}
    for name, value in values.items():
        _write(path / name, value)
    manifest = {
        "snapshot_id": "real-test-20260919", "data_mode": "real", "is_mock": False,
        "reference_now": "2026-09-19T18:00:00+09:00", "window_start": "2026-07-20", "window_end": "2026-09-13",
        "region_id": "dongseongro", "category": "restaurant",
        "counts": {"sources": 3, "areas": 1, "places": 1, "menu_items": 2, "area_metrics": 8},
        "files": {name: {"sha256": hashlib.sha256((path / name).read_bytes()).hexdigest()} for name in values},
    }
    _write(path / "manifest.json", manifest)


def _settings(tmp_path):
    data_dir = tmp_path / "real"
    data_dir.mkdir()
    _real_package(data_dir)
    return replace(load_settings(ROOT), data_mode="real", data_dir=data_dir, database_path=tmp_path / "consumer_compass_real.sqlite3")


def test_real_package_validation_and_import(tmp_path):
    settings = _settings(tmp_path)
    checked = load_and_validate_real_package(settings.data_dir)
    assert checked["counts"]["menu_items"] == 2
    imported = import_real_package(settings)
    assert imported["price_bundles"] == 1
    db = Database(settings)
    assert db.active_snapshot()["is_mock"] == 0
    assert [item["name"] for item in db.menu_items(imported["snapshot_id"], "REAL-P01")] == ["기본 메뉴", "대표 메뉴"]


def test_real_api_uses_verified_menu_calculation(tmp_path):
    settings = _settings(tmp_path)
    import_real_package(settings)
    with TestClient(create_app(settings)) as client:
        place = client.get("/api/places/REAL-P01", params={"snapshot_id": "real-test-20260919"})
        assert place.status_code == 200
        assert len(place.json()["price"]["menu_items"]) == 2
        assert place.json()["price"]["menu_items"][0]["mandatory_cost"] == 1000
        conditions = {
            "schema_version": "2.0", "region_id": "dongseongro", "category": "restaurant", "purpose": "meal",
            "party_size": 2, "budget": {"type": "per_person", "amount": 20000, "currency": "KRW"},
            "visit_at": "2026-09-19T19:00:00+09:00", "atmosphere_preferences": [], "required_atmosphere": [],
            "priority_profile": "balanced", "origin": None, "radius_m": 2000, "confirmed": True,
        }
        budget = client.post("/api/budget/estimate", json={"conditions": conditions, "snapshot_id": "real-test-20260919", "place_ids": ["REAL-P01"]})
        assert budget.status_code == 200
        item = budget.json()["items"][0]
        assert (item["cost_min"], item["cost_max"], item["budget_status"]) == (25000, 38000, "fits")
        assert item["menu_calculations"][0]["mandatory_cost"] == 1000
        assert [value["role"] for value in item["menu_calculations"]] == ["minimum", "maximum"]
        assert item["is_mock"] is False


def _conditions(*, party_size=2, budget_type="total", amount=38000):
    return {
        "schema_version": "2.0", "region_id": "dongseongro", "category": "restaurant", "purpose": "meal",
        "party_size": party_size, "budget": {"type": budget_type, "amount": amount, "currency": "KRW"},
        "visit_at": "2026-09-21T19:00:00+09:00", "atmosphere_preferences": [], "required_atmosphere": [],
        "priority_profile": "balanced", "origin": None, "radius_m": 2000, "confirmed": True,
    }


def test_real_api_budget_boundaries_party_change_and_no_result(tmp_path):
    settings = _settings(tmp_path)
    import_real_package(settings)
    with TestClient(create_app(settings)) as client:
        exact_per_person = client.post("/api/budget/estimate", json={
            "conditions": _conditions(budget_type="per_person", amount=19000),
            "snapshot_id": "real-test-20260919", "place_ids": ["REAL-P01"],
        })
        assert exact_per_person.status_code == 200
        assert exact_per_person.json()["total_budget"] == 38000
        assert exact_per_person.json()["items"][0]["budget_status"] == "fits"

        changed_party = client.post("/api/budget/estimate", json={
            "conditions": _conditions(party_size=3, amount=56000),
            "snapshot_id": "real-test-20260919", "place_ids": ["REAL-P01"],
        })
        assert changed_party.status_code == 200
        assert (changed_party.json()["items"][0]["cost_min"], changed_party.json()["items"][0]["cost_max"]) == (37000, 56000)

        one_won_short = client.post("/api/recommendations", json={
            "conditions": _conditions(amount=37999), "snapshot_id": "real-test-20260919",
        })
        assert one_won_short.status_code == 200
        assert one_won_short.json()["items"] == []
        assert one_won_short.json()["excluded_counts"]["budget"] == 1


def test_real_api_surfaces_missing_price_and_area_evidence(tmp_path):
    settings = _settings(tmp_path)
    import_real_package(settings)
    db = Database(settings)
    with db.connection() as conn:
        conn.execute("DELETE FROM price_bundles WHERE snapshot_id = ? AND place_id = ?", ("real-test-20260919", "REAL-P01"))
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/budget/estimate", json={
            "conditions": _conditions(), "snapshot_id": "real-test-20260919", "place_ids": ["REAL-P01"],
        })
        assert response.status_code == 200
        assert response.json()["items"][0]["budget_status"] == "unknown"
        assert response.json()["items"][0]["reason_code"] == "PRICE_MISSING"

    import_real_package(settings)
    with db.connection() as conn:
        conn.execute("DELETE FROM area_metrics WHERE snapshot_id = ?", ("real-test-20260919",))
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/recommendations", json={
            "conditions": _conditions(), "snapshot_id": "real-test-20260919",
        })
        assert response.status_code == 200
        assert response.json()["items"] == []
        assert response.json()["insufficient_data_items"][0]["data_status_reason"] == "AREA_EVIDENCE_MISSING"


def test_real_api_rejects_wrong_snapshot_and_unknown_place(tmp_path):
    settings = _settings(tmp_path)
    import_real_package(settings)
    with TestClient(create_app(settings)) as client:
        mismatch = client.post("/api/recommendations", json={"conditions": _conditions(), "snapshot_id": "not-current"})
        assert mismatch.status_code == 409
        unknown = client.get("/api/places/NO-SUCH", params={"snapshot_id": "real-test-20260919"})
        assert unknown.status_code == 404
