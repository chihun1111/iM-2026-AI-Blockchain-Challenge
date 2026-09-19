from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTER_PATH = ROOT / "data" / "real" / "data_candidates.json"

SOURCE_ID = "S04-SEMAS-COMMERCIAL-STORE-CATALOG"
REQUIRED_HEADERS = {
    "상가업소번호",
    "상호명",
    "지점명",
    "상권업종중분류코드",
    "상권업종중분류명",
    "상권업종소분류코드",
    "상권업종소분류명",
    "행정동코드",
    "행정동명",
    "법정동코드",
    "법정동명",
    "도로명주소",
    "경도",
    "위도",
}
EXPECTED_MATCHES = {
    "CAND-HANSIK-001": {"store_name": "국일따로국밥", "branch_name": "", "road_address": "대구광역시 중구 국채보상로 571"},
    "CAND-HANSIK-002": {"store_name": "개정", "branch_name": "본점", "road_address": "대구광역시 중구 동성로3길 52"},
    "CAND-HANSIK-003": {"store_name": "마산설렁탕", "branch_name": "", "road_address": "대구광역시 중구 경상감영1길 41"},
}
REGISTER_FIELD_MAP = {
    "public_place_id": "상가업소번호",
    "official_store_name": "상호명",
    "official_branch_name": "지점명",
    "official_category_code": "상권업종소분류코드",
    "official_category_name": "상권업종소분류명",
    "official_middle_category_code": "상권업종중분류코드",
    "official_middle_category_name": "상권업종중분류명",
    "administrative_dong_code": "행정동코드",
    "administrative_dong_name": "행정동명",
    "legal_dong_code": "법정동코드",
    "legal_dong_name": "법정동명",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _load_register() -> dict[str, Any]:
    value = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("data_candidates.json 최상위 값은 객체여야 합니다.")
    return value


def verify() -> dict[str, Any]:
    register = _load_register()
    source = next((row for row in register.get("sources", []) if row.get("source_id") == SOURCE_ID), None)
    if not isinstance(source, dict):
        raise RuntimeError(f"{SOURCE_ID} 출처가 없습니다.")

    zip_path = ROOT / str(source.get("source_file_local_path", ""))
    if not zip_path.is_file():
        raise RuntimeError(f"S04 원본 ZIP을 찾을 수 없습니다: {zip_path}")
    actual_zip_hash = sha256_file(zip_path)
    if actual_zip_hash != source.get("source_file_sha256"):
        raise RuntimeError("S04 원본 ZIP SHA-256이 후보부 기록과 다릅니다.")
    if zip_path.stat().st_size != source.get("source_file_size_bytes"):
        raise RuntimeError("S04 원본 ZIP 크기가 후보부 기록과 다릅니다.")

    entry_name = str(source.get("source_entry_name", ""))
    matches: dict[str, dict[str, str]] = {}
    entry_digest = hashlib.sha256()
    rows_scanned = 0
    with zipfile.ZipFile(zip_path) as archive:
        if entry_name not in archive.namelist():
            raise RuntimeError(f"S04 대구 CSV가 ZIP에 없습니다: {entry_name}")
        entry_info = archive.getinfo(entry_name)
        if entry_info.file_size != source.get("source_entry_size_bytes"):
            raise RuntimeError("S04 대구 CSV 크기가 후보부 기록과 다릅니다.")
        with archive.open(entry_name) as binary:
            for chunk in iter(lambda: binary.read(1024 * 1024), b""):
                entry_digest.update(chunk)
        if entry_digest.hexdigest().upper() != source.get("source_entry_sha256"):
            raise RuntimeError("S04 대구 CSV SHA-256이 후보부 기록과 다릅니다.")

        with archive.open(entry_name) as binary:
            text = io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")
            reader = csv.DictReader(text)
            headers = set(reader.fieldnames or [])
            missing_headers = sorted(REQUIRED_HEADERS - headers)
            if missing_headers:
                raise RuntimeError(f"S04 필수 헤더가 없습니다: {', '.join(missing_headers)}")
            for row in reader:
                rows_scanned += 1
                for candidate_id, expected in EXPECTED_MATCHES.items():
                    if (
                        row["상호명"] == expected["store_name"]
                        and row["지점명"] == expected["branch_name"]
                        and row["도로명주소"] == expected["road_address"]
                    ):
                        if candidate_id in matches:
                            raise RuntimeError(f"S04에서 {candidate_id}가 중복 매칭되었습니다.")
                        matches[candidate_id] = row

    if rows_scanned != source.get("source_entry_rows"):
        raise RuntimeError("S04 대구 CSV 행 수가 후보부 기록과 다릅니다.")
    missing_matches = sorted(set(EXPECTED_MATCHES) - set(matches))
    if missing_matches:
        raise RuntimeError(f"S04 점포 매칭 실패: {', '.join(missing_matches)}")

    places = {str(row.get("candidate_place_id")): row for row in register.get("places", [])}
    output_matches: list[dict[str, Any]] = []
    for candidate_id in EXPECTED_MATCHES:
        source_row = matches[candidate_id]
        place = places.get(candidate_id)
        if not isinstance(place, dict):
            raise RuntimeError(f"후보부 장소가 없습니다: {candidate_id}")
        for register_field, source_field in REGISTER_FIELD_MAP.items():
            if str(place.get(register_field, "")) != source_row[source_field]:
                raise RuntimeError(f"{candidate_id}.{register_field} 값이 S04 원본과 다릅니다.")
        for coordinate in ("longitude", "latitude"):
            source_field = "경도" if coordinate == "longitude" else "위도"
            if float(place.get(coordinate)) != float(source_row[source_field]):
                raise RuntimeError(f"{candidate_id}.{coordinate} 값이 S04 원본과 다릅니다.")
        if place.get("official_store_source_id") != SOURCE_ID or place.get("official_store_match_status") != "MATCHED":
            raise RuntimeError(f"{candidate_id}의 S04 매칭 상태가 올바르지 않습니다.")
        output_matches.append(
            {
                "candidate_place_id": candidate_id,
                "public_place_id": source_row["상가업소번호"],
                "store": " ".join(part for part in (source_row["상호명"], source_row["지점명"]) if part),
                "road_address": source_row["도로명주소"],
                "middle_category": f'{source_row["상권업종중분류코드"]} {source_row["상권업종중분류명"]}',
                "small_category": f'{source_row["상권업종소분류코드"]} {source_row["상권업종소분류명"]}',
            }
        )

    return {
        "status": "PASS",
        "source_file": str(zip_path.relative_to(ROOT)),
        "source_file_sha256": actual_zip_hash,
        "source_entry": entry_name,
        "source_entry_rows": rows_scanned,
        "matches": output_matches,
        "boundary_status": "UNDEFINED_PROJECT_SCOPE",
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        result = verify()
    except RuntimeError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
