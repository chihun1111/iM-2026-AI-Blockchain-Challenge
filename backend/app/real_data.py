from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import Settings
from .db import Database, _json


DATA_FILES = ("sources.json", "areas.json", "places.json", "menu_items.json", "area_metrics.json")
INVALID_PERMISSION_STATES = {"", "unknown", "pending", "denied", "unverified", "미확인", "검토중", "거부"}


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"실데이터 파일이 없습니다: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"JSON 형식이 올바르지 않습니다: {path.name} ({exc})") from exc


def _require_fields(row: dict[str, Any], fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in row or row[field] in (None, "")]
    if missing:
        raise RuntimeError(f"{label} 필수 필드 누락: {', '.join(missing)}")


def _unique(rows: list[dict[str, Any]], key: str, label: str) -> set[str]:
    values = [str(row.get(key, "")) for row in rows]
    if any(not value for value in values):
        raise RuntimeError(f"{label}.{key}는 비어 있을 수 없습니다.")
    if len(values) != len(set(values)):
        raise RuntimeError(f"{label}.{key}가 중복되었습니다.")
    return set(values)


def _iso(value: str, label: str) -> None:
    try:
        datetime.fromisoformat(value)
    except ValueError as exc:
        raise RuntimeError(f"{label}은 ISO 8601 날짜/시각이어야 합니다: {value}") from exc


def load_and_validate_real_package(data_dir: Path) -> dict[str, Any]:
    manifest = _read_json(data_dir / "manifest.json")
    payload = {name: _read_json(data_dir / name) for name in DATA_FILES}
    if not isinstance(manifest, dict) or any(not isinstance(payload[name], list) for name in DATA_FILES):
        raise RuntimeError("manifest는 객체, 나머지 실데이터 파일은 배열이어야 합니다.")
    if manifest.get("data_mode") != "real" or manifest.get("is_mock") is not False:
        raise RuntimeError("실데이터 manifest는 data_mode=real, is_mock=false여야 합니다.")
    _require_fields(
        manifest,
        ("snapshot_id", "reference_now", "window_start", "window_end", "region_id", "category", "counts", "files"),
        "manifest",
    )
    _iso(str(manifest["reference_now"]), "manifest.reference_now")
    if manifest["region_id"] != "dongseongro":
        raise RuntimeError("현재 프로토타입이 지원하는 region_id가 아닙니다.")
    if manifest["category"] != "restaurant":
        raise RuntimeError("현재 프로토타입이 지원하는 category가 아닙니다.")

    counts = {
        "sources": len(payload["sources.json"]),
        "areas": len(payload["areas.json"]),
        "places": len(payload["places.json"]),
        "menu_items": len(payload["menu_items.json"]),
        "area_metrics": len(payload["area_metrics.json"]),
    }
    if counts != manifest["counts"]:
        raise RuntimeError(f"manifest 행 수 불일치: {counts} != {manifest['counts']}")
    for name in DATA_FILES:
        file_meta = manifest["files"].get(name)
        if not isinstance(file_meta, dict) or not file_meta.get("sha256"):
            raise RuntimeError(f"manifest.files에 {name} SHA-256이 없습니다.")
        digest = hashlib.sha256((data_dir / name).read_bytes()).hexdigest()
        if digest != file_meta["sha256"]:
            raise RuntimeError(f"원본 해시 불일치: {name}")

    sources = payload["sources.json"]
    areas = payload["areas.json"]
    places = payload["places.json"]
    menu_items = payload["menu_items.json"]
    metrics = payload["area_metrics.json"]
    if not sources or not places or not menu_items or not metrics:
        raise RuntimeError("출처·장소·메뉴·집계 행동 데이터는 각각 1행 이상 필요합니다.")
    if len(areas) != 1:
        raise RuntimeError("제출 프로토타입 범위는 상권 1곳이어야 합니다.")
    for name, rows in payload.items():
        if any(row.get("is_mock") is not False for row in rows):
            raise RuntimeError(f"{name}의 모든 행은 is_mock=false여야 합니다.")

    source_ids = _unique(sources, "source_id", "sources")
    area_ids = _unique(areas, "area_id", "areas")
    place_ids = _unique(places, "place_id", "places")
    _unique(menu_items, "menu_item_id", "menu_items")
    _unique(metrics, "metric_id", "area_metrics")
    for source in sources:
        _require_fields(source, ("source_id", "name", "kind", "provider", "permission_status", "observed_at", "scope", "source_uri", "rights_evidence"), "source")
        if str(source["permission_status"]).strip().lower() in INVALID_PERMISSION_STATES:
            raise RuntimeError(f"사용권 상태가 확인되지 않은 출처입니다: {source['source_id']}")
        _iso(str(source["observed_at"]), f"source[{source['source_id']}].observed_at")

    area = areas[0]
    _require_fields(area, ("area_id", "region_id", "name", "boundary_type"), "area")
    if area["region_id"] != manifest["region_id"]:
        raise RuntimeError("area.region_id와 manifest.region_id가 다릅니다.")
    if area_ids != {area["area_id"]}:
        raise RuntimeError("상권 ID 검증에 실패했습니다.")

    for place in places:
        _require_fields(
            place,
            (
                "place_id", "name", "region_id", "area_id", "category", "address_label", "party_min", "party_max",
                "purpose_tags", "atmosphere_tags", "opening_weekly", "opening_exceptions", "opening_observed_at",
                "opening_hours_eligible_for_filter", "atmosphere_observed_at", "source_id",
            ),
            "place",
        )
        if place["region_id"] != manifest["region_id"] or place["category"] != manifest["category"]:
            raise RuntimeError(f"범위 밖 장소입니다: {place['place_id']}")
        if place["area_id"] not in area_ids or place["source_id"] not in source_ids:
            raise RuntimeError(f"장소의 상권 또는 출처 참조가 유효하지 않습니다: {place['place_id']}")
        if not 1 <= int(place["party_min"]) <= int(place["party_max"]) <= 6:
            raise RuntimeError(f"장소 인원 범위가 올바르지 않습니다: {place['place_id']}")
        if not isinstance(place["opening_hours_eligible_for_filter"], bool):
            raise RuntimeError(f"opening_hours_eligible_for_filter는 boolean이어야 합니다: {place['place_id']}")
        _iso(str(place["opening_observed_at"]), f"place[{place['place_id']}].opening_observed_at")
        _iso(str(place["atmosphere_observed_at"]), f"place[{place['place_id']}].atmosphere_observed_at")

    candidates_by_place: dict[str, list[dict[str, Any]]] = {place_id: [] for place_id in place_ids}
    for item in menu_items:
        _require_fields(
            item,
            (
                "menu_item_id", "place_id", "name", "price_krw", "pricing_unit", "minimum_order",
                "portion", "mandatory_cost", "confirmed_on", "confirmed_by_role", "usage_basis",
                "is_budget_candidate", "source_id",
            ),
            "menu_item",
        )
        if item["place_id"] not in place_ids or item["source_id"] not in source_ids:
            raise RuntimeError(f"메뉴의 장소 또는 출처 참조가 유효하지 않습니다: {item['menu_item_id']}")
        if item["pricing_unit"] != "per_person":
            raise RuntimeError(f"현재 지원하는 메뉴 단위는 per_person뿐입니다: {item['menu_item_id']}")
        if int(item["price_krw"]) <= 0 or int(item["minimum_order"]) <= 0:
            raise RuntimeError(f"메뉴 가격·최소 주문 수량은 양수여야 합니다: {item['menu_item_id']}")
        if not isinstance(item["mandatory_cost"], int) or item["mandatory_cost"] < 0:
            raise RuntimeError(f"메뉴 필수 비용은 확인된 0 이상의 정수여야 합니다: {item['menu_item_id']}")
        if not item.get("source_url") and not item.get("evidence_file"):
            raise RuntimeError(f"메뉴에는 source_url 또는 evidence_file이 필요합니다: {item['menu_item_id']}")
        if item.get("evidence_file"):
            evidence_path = (data_dir / str(item["evidence_file"])).resolve()
            try:
                evidence_path.relative_to(data_dir.resolve())
            except ValueError as exc:
                raise RuntimeError(f"메뉴 evidence_file은 실데이터 폴더 안의 상대 경로여야 합니다: {item['menu_item_id']}") from exc
            if not evidence_path.is_file():
                raise RuntimeError(f"메뉴 evidence_file을 찾을 수 없습니다: {item['menu_item_id']}")
        if not isinstance(item["is_budget_candidate"], bool):
            raise RuntimeError(f"is_budget_candidate는 boolean이어야 합니다: {item['menu_item_id']}")
        _iso(str(item["confirmed_on"]), f"menu_item[{item['menu_item_id']}].confirmed_on")
        if item["is_budget_candidate"]:
            candidates_by_place[item["place_id"]].append(item)
    if not any(candidates_by_place.values()):
        raise RuntimeError("예산 계산에 사용할 검증 메뉴가 1개 이상 필요합니다.")
    for place_id, items in candidates_by_place.items():
        if len({item["source_id"] for item in items}) > 1:
            raise RuntimeError(f"한 장소의 예산 후보 메뉴는 동일한 출처여야 합니다: {place_id}")

    for metric in metrics:
        _require_fields(
            metric,
            (
                "metric_id", "area_id", "category", "day_group", "time_bucket", "week_start", "week_end",
                "txn_count", "merchant_count", "source_id", "metric_definition_version", "coverage_status",
            ),
            "area_metric",
        )
        if metric["area_id"] not in area_ids or metric["category"] != manifest["category"] or metric["source_id"] not in source_ids:
            raise RuntimeError(f"집계 데이터 범위 또는 출처가 유효하지 않습니다: {metric['metric_id']}")
        if int(metric["txn_count"]) < 0 or int(metric["merchant_count"]) < 0:
            raise RuntimeError(f"집계값은 음수가 될 수 없습니다: {metric['metric_id']}")
        if metric.get("footfall_count") is not None and int(metric["footfall_count"]) < 0:
            raise RuntimeError(f"유동량은 음수가 될 수 없습니다: {metric['metric_id']}")

    return {"manifest": manifest, "payload": payload, "counts": counts, "candidates_by_place": candidates_by_place}


def import_real_package(settings: Settings) -> dict[str, Any]:
    if settings.data_mode != "real":
        raise RuntimeError("실데이터 반입은 DATA_MODE=real에서만 허용됩니다.")
    if settings.data_dir.name.lower() == "demo":
        raise RuntimeError("실데이터 반입 경로로 data/demo를 사용할 수 없습니다.")
    if "demo" in settings.database_path.name.lower():
        raise RuntimeError("실데이터를 demo 이름의 DB에 반입할 수 없습니다.")
    validated = load_and_validate_real_package(settings.data_dir)
    manifest = validated["manifest"]
    payload = validated["payload"]
    candidates_by_place = validated["candidates_by_place"]
    snapshot_id = manifest["snapshot_id"]
    db = Database(settings)
    db.initialize()

    with db.connection() as conn:
        conn.execute("DELETE FROM evidence WHERE snapshot_id = ?", (snapshot_id,))
        conn.execute("DELETE FROM area_metrics WHERE snapshot_id = ?", (snapshot_id,))
        conn.execute("DELETE FROM menu_items WHERE snapshot_id = ?", (snapshot_id,))
        conn.execute("DELETE FROM price_bundles WHERE snapshot_id = ?", (snapshot_id,))
        conn.execute("DELETE FROM places WHERE snapshot_id = ?", (snapshot_id,))
        conn.execute("DELETE FROM areas WHERE snapshot_id = ?", (snapshot_id,))
        conn.execute("DELETE FROM snapshots WHERE snapshot_id = ?", (snapshot_id,))

        conn.executemany(
            """
            INSERT INTO sources
              (source_id, name, kind, provider, permission_status, observed_at, scope, note, is_mock, source_uri, rights_evidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
              name=excluded.name, kind=excluded.kind, provider=excluded.provider,
              permission_status=excluded.permission_status, observed_at=excluded.observed_at,
              scope=excluded.scope, note=excluded.note, is_mock=excluded.is_mock,
              source_uri=excluded.source_uri, rights_evidence=excluded.rights_evidence
            """,
            [
                (
                    row["source_id"], row["name"], row["kind"], row["provider"], row["permission_status"],
                    row["observed_at"], row["scope"], row.get("note"), 0, row["source_uri"], row["rights_evidence"],
                )
                for row in payload["sources.json"]
            ],
        )
        conn.execute(
            "INSERT INTO snapshots VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                snapshot_id, "real", manifest["reference_now"], manifest["window_start"], manifest["window_end"],
                0, _json(manifest),
            ),
        )
        conn.executemany(
            "INSERT INTO areas VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    row["area_id"], snapshot_id, row["region_id"], row["name"], row["boundary_type"],
                    _json(row.get("centroid")), 0,
                )
                for row in payload["areas.json"]
            ],
        )
        conn.executemany(
            """
            INSERT INTO places
              (place_id, snapshot_id, name, region_id, area_id, category, address_label,
               coordinates_json, party_min, party_max, purpose_tags_json, atmosphere_tags_json,
               opening_weekly_json, opening_exceptions_json, opening_observed_at,
               opening_hours_eligible_for_filter, atmosphere_observed_at, bundle_id, source_id, is_mock)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["place_id"], snapshot_id, row["name"], row["region_id"], row["area_id"], row["category"],
                    row["address_label"], _json(row.get("coordinates")), int(row["party_min"]), int(row["party_max"]),
                    _json(row["purpose_tags"]), _json(row["atmosphere_tags"]), _json(row["opening_weekly"]),
                    _json(row["opening_exceptions"]), row["opening_observed_at"],
                    int(row["opening_hours_eligible_for_filter"]), row["atmosphere_observed_at"],
                    row.get("bundle_id") or f"BUNDLE-{row['place_id']}", row["source_id"], 0,
                )
                for row in payload["places.json"]
            ],
        )

        bundle_rows = []
        for place in payload["places.json"]:
            candidates = candidates_by_place[place["place_id"]]
            if not candidates:
                continue
            candidates = sorted(candidates, key=lambda row: (int(row["price_krw"]), row["menu_item_id"]))
            bundle_rows.append(
                (
                    place.get("bundle_id") or f"BUNDLE-{place['place_id']}", snapshot_id, place["place_id"],
                    "per_person", "검증 메뉴 1인 기준", int(candidates[0]["price_krw"]), int(candidates[-1]["price_krw"]),
                    min(int(row["mandatory_cost"]) for row in candidates),
                    max(int(row["mandatory_cost"]) for row in candidates),
                    "KRW", max(row["confirmed_on"] for row in candidates),
                    _json([row["name"] for row in candidates]), _json(["추가 주문", "음료·주류", "할인·쿠폰"]),
                    candidates[0]["source_id"], 0,
                )
            )
        conn.executemany("INSERT INTO price_bundles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", bundle_rows)
        conn.executemany(
            """
            INSERT INTO menu_items
              (menu_item_id, snapshot_id, place_id, name, price_krw, pricing_unit, min_order_qty,
               portion, mandatory_cost, confirmed_on, confirmed_by_role, usage_basis, source_url,
               evidence_file, is_budget_candidate, observed_at, source_id, is_mock)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["menu_item_id"], snapshot_id, row["place_id"], row["name"], int(row["price_krw"]),
                    row["pricing_unit"], int(row["minimum_order"]), row["portion"], int(row["mandatory_cost"]),
                    row["confirmed_on"], row["confirmed_by_role"], row["usage_basis"], row.get("source_url"),
                    row.get("evidence_file"), int(row["is_budget_candidate"]), row["confirmed_on"], row["source_id"], 0,
                )
                for row in payload["menu_items.json"]
            ],
        )
        conn.executemany(
            "INSERT INTO area_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    row["metric_id"], snapshot_id, row["area_id"], row["category"], row["day_group"], row["time_bucket"],
                    row["week_start"], row["week_end"], int(row["txn_count"]), int(row["merchant_count"]),
                    int(row["footfall_count"]) if row.get("footfall_count") is not None else None,
                    row["source_id"], row["metric_definition_version"], row["coverage_status"], 0,
                )
                for row in payload["area_metrics.json"]
            ],
        )

        for place in payload["places.json"]:
            candidates = candidates_by_place[place["place_id"]]
            if candidates:
                conn.execute(
                    "INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        f"E-PRICE-{place['place_id']}", snapshot_id, place["place_id"], None, candidates[0]["source_id"],
                        "PRICE_RANGE", _json({
                            "menu_item_ids": [row["menu_item_id"] for row in candidates],
                            "unit_min": min(int(row["price_krw"]) for row in candidates),
                            "unit_max": max(int(row["price_krw"]) for row in candidates),
                            "mandatory_cost_min": min(int(row["mandatory_cost"]) for row in candidates),
                            "mandatory_cost_max": max(int(row["mandatory_cost"]) for row in candidates),
                        }),
                        "KRW_PER_PERSON", max(row["confirmed_on"] for row in candidates), None, None, "verified_menu_items", 0,
                    ),
                )
            for claim, tags, observed, unit in (
                ("PURPOSE_MATCH", place["purpose_tags"], place["opening_observed_at"], "purpose_tag"),
                ("ATMOSPHERE_TAG", place["atmosphere_tags"], place["atmosphere_observed_at"], "atmosphere_tag"),
            ):
                conn.execute(
                    "INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (f"E-{claim}-{place['place_id']}", snapshot_id, place["place_id"], None, place["source_id"], claim, _json(tags), unit, observed, None, None, "place", 0),
                )
        for metric in payload["area_metrics.json"]:
            conn.execute(
                "INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"E-METRIC-{metric['metric_id']}", snapshot_id, None, metric["area_id"], metric["source_id"], "AREA_ACTIVITY",
                    _json({"txn_count": metric["txn_count"], "merchant_count": metric["merchant_count"], "footfall_count": metric.get("footfall_count"), "category": metric["category"], "day_group": metric["day_group"], "time_bucket": metric["time_bucket"]}),
                    "aggregate_count", metric["week_end"], metric["week_start"], metric["week_end"], "area_category_week_daygroup_timebucket", 0,
                ),
            )
        fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
        if fk_errors:
            raise RuntimeError(f"실데이터 외래키 검증 실패: {len(fk_errors)}건")

    return {"snapshot_id": snapshot_id, "counts": validated["counts"], "price_bundles": len(bundle_rows)}
