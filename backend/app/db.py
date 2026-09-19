from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from .config import Settings


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id TEXT PRIMARY KEY,
    data_mode TEXT NOT NULL,
    reference_now TEXT NOT NULL,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    is_mock INTEGER NOT NULL CHECK (is_mock IN (0, 1)),
    manifest_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    provider TEXT NOT NULL,
    permission_status TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    scope TEXT NOT NULL,
    note TEXT,
    is_mock INTEGER NOT NULL CHECK (is_mock IN (0, 1)),
    source_uri TEXT,
    rights_evidence TEXT
);
CREATE TABLE IF NOT EXISTS areas (
    area_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
    region_id TEXT NOT NULL,
    name TEXT NOT NULL,
    boundary_type TEXT NOT NULL,
    centroid_json TEXT,
    is_mock INTEGER NOT NULL CHECK (is_mock IN (0, 1)),
    PRIMARY KEY (area_id, snapshot_id)
);
CREATE TABLE IF NOT EXISTS places (
    place_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
    name TEXT NOT NULL,
    region_id TEXT NOT NULL,
    area_id TEXT NOT NULL,
    category TEXT NOT NULL,
    address_label TEXT NOT NULL,
    coordinates_json TEXT,
    party_min INTEGER NOT NULL,
    party_max INTEGER NOT NULL,
    purpose_tags_json TEXT NOT NULL,
    atmosphere_tags_json TEXT NOT NULL,
    opening_weekly_json TEXT NOT NULL,
    opening_exceptions_json TEXT NOT NULL,
    opening_observed_at TEXT NOT NULL,
    opening_hours_eligible_for_filter INTEGER NOT NULL DEFAULT 1 CHECK (opening_hours_eligible_for_filter IN (0, 1)),
    atmosphere_observed_at TEXT NOT NULL,
    bundle_id TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    is_mock INTEGER NOT NULL CHECK (is_mock IN (0, 1)),
    PRIMARY KEY (place_id, snapshot_id),
    FOREIGN KEY (area_id, snapshot_id) REFERENCES areas(area_id, snapshot_id)
);
CREATE TABLE IF NOT EXISTS price_bundles (
    bundle_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
    place_id TEXT NOT NULL,
    unit TEXT NOT NULL,
    label TEXT NOT NULL,
    unit_min INTEGER NOT NULL CHECK (unit_min > 0),
    unit_max INTEGER NOT NULL CHECK (unit_max >= unit_min),
    fixed_fee_min INTEGER NOT NULL CHECK (fixed_fee_min >= 0),
    fixed_fee_max INTEGER NOT NULL CHECK (fixed_fee_max >= fixed_fee_min),
    currency TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    included_json TEXT NOT NULL,
    excluded_json TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    is_mock INTEGER NOT NULL CHECK (is_mock IN (0, 1)),
    PRIMARY KEY (bundle_id, snapshot_id),
    FOREIGN KEY (place_id, snapshot_id) REFERENCES places(place_id, snapshot_id)
);
CREATE TABLE IF NOT EXISTS menu_items (
    menu_item_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
    place_id TEXT NOT NULL,
    name TEXT NOT NULL,
    price_krw INTEGER NOT NULL CHECK (price_krw > 0),
    pricing_unit TEXT NOT NULL CHECK (pricing_unit = 'per_person'),
    min_order_qty INTEGER NOT NULL CHECK (min_order_qty > 0),
    portion TEXT,
    mandatory_cost INTEGER CHECK (mandatory_cost >= 0),
    confirmed_on TEXT,
    confirmed_by_role TEXT,
    usage_basis TEXT,
    source_url TEXT,
    evidence_file TEXT,
    is_budget_candidate INTEGER NOT NULL CHECK (is_budget_candidate IN (0, 1)),
    observed_at TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    is_mock INTEGER NOT NULL CHECK (is_mock IN (0, 1)),
    PRIMARY KEY (menu_item_id, snapshot_id),
    FOREIGN KEY (place_id, snapshot_id) REFERENCES places(place_id, snapshot_id)
);
CREATE TABLE IF NOT EXISTS area_metrics (
    metric_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
    area_id TEXT NOT NULL,
    category TEXT NOT NULL,
    day_group TEXT NOT NULL,
    time_bucket TEXT NOT NULL,
    week_start TEXT NOT NULL,
    week_end TEXT NOT NULL,
    txn_count INTEGER NOT NULL CHECK (txn_count >= 0),
    merchant_count INTEGER NOT NULL CHECK (merchant_count >= 0),
    footfall_count INTEGER,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    metric_definition_version TEXT NOT NULL,
    coverage_status TEXT NOT NULL,
    is_mock INTEGER NOT NULL CHECK (is_mock IN (0, 1)),
    PRIMARY KEY (metric_id, snapshot_id),
    UNIQUE (snapshot_id, area_id, category, day_group, time_bucket, week_start),
    FOREIGN KEY (area_id, snapshot_id) REFERENCES areas(area_id, snapshot_id)
);
CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
    place_id TEXT,
    area_id TEXT,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    claim_type TEXT NOT NULL,
    value_json TEXT NOT NULL,
    unit TEXT,
    observed_at TEXT NOT NULL,
    period_start TEXT,
    period_end TEXT,
    aggregation_unit TEXT,
    is_mock INTEGER NOT NULL CHECK (is_mock IN (0, 1)),
    PRIMARY KEY (evidence_id, snapshot_id),
    CHECK (place_id IS NOT NULL OR area_id IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_places_snapshot_region_category ON places(snapshot_id, region_id, category);
CREATE INDEX IF NOT EXISTS idx_metrics_lookup ON area_metrics(snapshot_id, area_id, category, day_group, time_bucket);
CREATE INDEX IF NOT EXISTS idx_evidence_place ON evidence(snapshot_id, place_id);
CREATE INDEX IF NOT EXISTS idx_menu_items_place ON menu_items(snapshot_id, place_id);
"""


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Database:
    def __init__(self, settings: Settings):
        self.settings = settings

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        self.settings.database_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.settings.database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connection() as conn:
            conn.executescript(SCHEMA)
            source_columns = {row[1] for row in conn.execute("PRAGMA table_info(sources)").fetchall()}
            if "source_uri" not in source_columns:
                conn.execute("ALTER TABLE sources ADD COLUMN source_uri TEXT")
            if "rights_evidence" not in source_columns:
                conn.execute("ALTER TABLE sources ADD COLUMN rights_evidence TEXT")
            menu_columns = {row[1] for row in conn.execute("PRAGMA table_info(menu_items)").fetchall()}
            for name, definition in (
                ("portion", "TEXT"),
                ("mandatory_cost", "INTEGER CHECK (mandatory_cost >= 0)"),
                ("confirmed_on", "TEXT"),
                ("confirmed_by_role", "TEXT"),
                ("usage_basis", "TEXT"),
                ("source_url", "TEXT"),
                ("evidence_file", "TEXT"),
            ):
                if name not in menu_columns:
                    conn.execute(f"ALTER TABLE menu_items ADD COLUMN {name} {definition}")
            place_columns = {row[1] for row in conn.execute("PRAGMA table_info(places)").fetchall()}
            if "opening_hours_eligible_for_filter" not in place_columns:
                conn.execute(
                    "ALTER TABLE places ADD COLUMN opening_hours_eligible_for_filter INTEGER NOT NULL DEFAULT 1 CHECK (opening_hours_eligible_for_filter IN (0, 1))"
                )

    def can_seed_demo(self) -> tuple[bool, str]:
        path = self.settings.database_path.resolve()
        var_dir = (self.settings.root / "var").resolve()
        try:
            path.relative_to(var_dir)
        except ValueError:
            return False, "데모 seed는 프로젝트 var/ 아래 SQLite DB에서만 허용됩니다."
        lowered = path.name.lower()
        if any(token in lowered for token in ("prod", "production", "real", "live")):
            return False, "운영·실데이터로 보이는 DB 이름에는 데모 seed를 실행할 수 없습니다."
        if self.settings.data_mode != "demo":
            return False, "DATA_MODE=demo에서만 데모 seed를 실행할 수 있습니다."
        return True, "ok"

    def seed_demo(self) -> dict[str, Any]:
        allowed, reason = self.can_seed_demo()
        if not allowed:
            raise RuntimeError(reason)
        self.initialize()
        data_dir = self.settings.data_dir
        files = {name: data_dir / name for name in ["sources.json", "areas.json", "places.json", "price_bundles.json", "area_metrics.json", "manifest.json"]}
        payload = {key: json.loads(path.read_text(encoding="utf-8")) for key, path in files.items()}
        manifest = payload["manifest.json"]
        snapshot_id = manifest["snapshot_id"]
        with self.connection() as conn:
            conn.execute("DELETE FROM evidence WHERE snapshot_id = ?", (snapshot_id,))
            conn.execute("DELETE FROM area_metrics WHERE snapshot_id = ?", (snapshot_id,))
            conn.execute("DELETE FROM menu_items WHERE snapshot_id = ?", (snapshot_id,))
            conn.execute("DELETE FROM price_bundles WHERE snapshot_id = ?", (snapshot_id,))
            conn.execute("DELETE FROM places WHERE snapshot_id = ?", (snapshot_id,))
            conn.execute("DELETE FROM areas WHERE snapshot_id = ?", (snapshot_id,))
            conn.execute("DELETE FROM snapshots WHERE snapshot_id = ?", (snapshot_id,))
            conn.executemany(
                """
                INSERT OR REPLACE INTO sources
                (source_id, name, kind, provider, permission_status, observed_at, scope, note, is_mock)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        x["source_id"], x["name"], x["kind"], x["provider"], x["permission_status"],
                        x["observed_at"], x["scope"], x.get("note"), int(x["is_mock"]),
                    )
                    for x in payload["sources.json"]
                ],
            )
            conn.execute(
                "INSERT INTO snapshots VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    snapshot_id, manifest["data_mode"], manifest["reference_now"], manifest["window_start"],
                    manifest["window_end"], int(manifest["is_mock"]), _json(manifest),
                ),
            )
            conn.executemany(
                "INSERT INTO areas VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (x["area_id"], snapshot_id, x["region_id"], x["name"], x["boundary_type"], _json(x.get("centroid")), int(x["is_mock"]))
                    for x in payload["areas.json"]
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
                        x["place_id"], snapshot_id, x["name"], x["region_id"], x["area_id"], x["category"],
                        x["address_label"], _json(x.get("coordinates")), x["party_min"], x["party_max"],
                        _json(x["purpose_tags"]), _json(x["atmosphere_tags"]), _json(x["opening_weekly"]),
                        _json(x["opening_exceptions"]), x["opening_observed_at"],
                        int(x.get("opening_hours_eligible_for_filter", True)), x["atmosphere_observed_at"],
                        x["bundle_id"], x["source_id"], int(x["is_mock"]),
                    )
                    for x in payload["places.json"]
                ],
            )
            conn.executemany(
                "INSERT INTO price_bundles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        x["bundle_id"], snapshot_id, x["place_id"], x["unit"], x["label"], x["unit_min"],
                        x["unit_max"], x["fixed_fee_min"], x["fixed_fee_max"], x["currency"], x["observed_at"],
                        _json(x["included"]), _json(x["excluded"]), x["source_id"], int(x["is_mock"]),
                    )
                    for x in payload["price_bundles.json"]
                ],
            )
            conn.executemany(
                "INSERT INTO area_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        x["metric_id"], snapshot_id, x["area_id"], x["category"], x["day_group"], x["time_bucket"],
                        x["week_start"], x["week_end"], x["txn_count"], x["merchant_count"], x.get("footfall_count"),
                        x["source_id"], x["metric_definition_version"], x["coverage_status"], int(x["is_mock"]),
                    )
                    for x in payload["area_metrics.json"]
                ],
            )
            for place in payload["places.json"]:
                place_id = place["place_id"]
                conn.execute(
                    "INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        f"E-PRICE-{place_id}", snapshot_id, place_id, None, place["source_id"], "PRICE_RANGE",
                        _json({"unit_min": next(x["unit_min"] for x in payload["price_bundles.json"] if x["place_id"] == place_id), "unit_max": next(x["unit_max"] for x in payload["price_bundles.json"] if x["place_id"] == place_id)}),
                        "KRW_PER_PERSON", place["opening_observed_at"], None, None, "place_price_bundle", 1,
                    ),
                )
                for claim, tags, observed, unit in [
                    ("PURPOSE_MATCH", place["purpose_tags"], place["opening_observed_at"], "purpose_tag"),
                    ("ATMOSPHERE_TAG", place["atmosphere_tags"], place["atmosphere_observed_at"], "atmosphere_tag"),
                ]:
                    conn.execute(
                        "INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (f"E-{claim}-{place_id}", snapshot_id, place_id, None, place["source_id"], claim, _json(tags), unit, observed, None, None, "place", 1),
                    )
            for metric in payload["area_metrics.json"]:
                conn.execute(
                    "INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        f"E-METRIC-{metric['metric_id']}", snapshot_id, None, metric["area_id"], metric["source_id"], "AREA_ACTIVITY",
                        _json({"txn_count": metric["txn_count"], "merchant_count": metric["merchant_count"], "category": metric["category"], "day_group": metric["day_group"], "time_bucket": metric["time_bucket"]}),
                        "txn_per_merchant_per_week", metric["week_end"], metric["week_start"], metric["week_end"], "area_category_week_daygroup_timebucket", 1,
                    ),
                )
        return self.verify_demo()

    def verify_demo(self) -> dict[str, Any]:
        self.initialize()
        expected = {"sources": 2, "areas": 8, "places": 40, "price_bundles": 40, "area_metrics": 768}
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM snapshots ORDER BY snapshot_id DESC LIMIT 1").fetchone()
            if row is None:
                raise RuntimeError("활성 스냅샷이 없습니다. 먼저 seed_demo를 실행하세요.")
            counts = {}
            for table in expected:
                counts[table] = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
            if counts != expected:
                raise RuntimeError(f"데모 행 수가 기대값과 다릅니다: {counts} != {expected}")
            fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
            duplicate_metric_keys = conn.execute(
                "SELECT COUNT(*) - COUNT(DISTINCT snapshot_id || '|' || area_id || '|' || category || '|' || day_group || '|' || time_bucket || '|' || week_start) FROM area_metrics"
            ).fetchone()[0]
            if fk_errors or duplicate_metric_keys:
                raise RuntimeError("외래키 또는 집계 복합키 검증에 실패했습니다.")
            return {"snapshot_id": row["snapshot_id"], "counts": counts, "foreign_key_errors": len(fk_errors)}

    def snapshot(self, snapshot_id: str) -> sqlite3.Row | None:
        with self.connection() as conn:
            return conn.execute("SELECT * FROM snapshots WHERE snapshot_id = ?", (snapshot_id,)).fetchone()

    def active_snapshot(self) -> sqlite3.Row | None:
        with self.connection() as conn:
            return conn.execute("SELECT * FROM snapshots ORDER BY snapshot_id DESC LIMIT 1").fetchone()

    @staticmethod
    def _decode(row: sqlite3.Row, fields: tuple[str, ...]) -> dict[str, Any]:
        result = dict(row)
        for field in fields:
            if result.get(field) is not None:
                result[field[:-5] if field.endswith("_json") else field] = json.loads(result.pop(field))
        return result

    def list_places(self, snapshot_id: str, region_id: str | None = None, category: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM places WHERE snapshot_id = ?"
        args: list[Any] = [snapshot_id]
        if region_id:
            sql += " AND region_id = ?"
            args.append(region_id)
        if category:
            sql += " AND category = ?"
            args.append(category)
        sql += " ORDER BY place_id"
        with self.connection() as conn:
            rows = conn.execute(sql, args).fetchall()
        return [self._decode(row, ("coordinates_json", "purpose_tags_json", "atmosphere_tags_json", "opening_weekly_json", "opening_exceptions_json")) for row in rows]

    def place(self, snapshot_id: str, place_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM places WHERE snapshot_id = ? AND place_id = ?", (snapshot_id, place_id)).fetchone()
        return self._decode(row, ("coordinates_json", "purpose_tags_json", "atmosphere_tags_json", "opening_weekly_json", "opening_exceptions_json")) if row else None

    def price(self, snapshot_id: str, place_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM price_bundles WHERE snapshot_id = ? AND place_id = ?", (snapshot_id, place_id)).fetchone()
        return self._decode(row, ("included_json", "excluded_json")) if row else None

    def menu_items(self, snapshot_id: str, place_id: str, budget_candidates_only: bool = False) -> list[dict[str, Any]]:
        sql = "SELECT * FROM menu_items WHERE snapshot_id = ? AND place_id = ?"
        args: list[Any] = [snapshot_id, place_id]
        if budget_candidates_only:
            sql += " AND is_budget_candidate = 1"
        sql += " ORDER BY price_krw, menu_item_id"
        with self.connection() as conn:
            rows = conn.execute(sql, args).fetchall()
        return [dict(row) for row in rows]

    def metrics(self, snapshot_id: str, area_id: str, category: str, day_group: str, time_bucket: str) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM area_metrics WHERE snapshot_id = ? AND area_id = ? AND category = ? AND day_group = ? AND time_bucket = ? ORDER BY week_start",
                (snapshot_id, area_id, category, day_group, time_bucket),
            ).fetchall()
        return [dict(row) for row in rows]

    def metrics_for_area(self, snapshot_id: str, area_id: str, category: str) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM area_metrics
                WHERE snapshot_id = ? AND area_id = ? AND category = ?
                ORDER BY week_start, day_group, time_bucket, metric_id
                """,
                (snapshot_id, area_id, category),
            ).fetchall()
        return [dict(row) for row in rows]

    def all_metrics(self, snapshot_id: str, category: str, day_group: str, time_bucket: str) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM area_metrics WHERE snapshot_id = ? AND category = ? AND day_group = ? AND time_bucket = ? ORDER BY area_id, week_start",
                (snapshot_id, category, day_group, time_bucket),
            ).fetchall()
        return [dict(row) for row in rows]

    def evidence_for_place(self, snapshot_id: str, place_id: str) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM evidence WHERE snapshot_id = ? AND place_id = ? ORDER BY evidence_id", (snapshot_id, place_id)).fetchall()
        return [self._decode(row, ("value_json",)) for row in rows]

    def evidence(self, snapshot_id: str, evidence_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM evidence WHERE snapshot_id = ? AND evidence_id = ?", (snapshot_id, evidence_id)).fetchone()
        return self._decode(row, ("value_json",)) if row else None
