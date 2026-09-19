from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config import load_settings  # noqa: E402
from backend.app.db import Database  # noqa: E402


def check_source_files(settings) -> dict:
    data_dir = settings.data_dir
    names = ["sources.json", "areas.json", "places.json", "price_bundles.json", "area_metrics.json"]
    values = {name: json.loads((data_dir / name).read_text(encoding="utf-8")) for name in names}
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    counts = {"sources": len(values["sources.json"]), "areas": len(values["areas.json"]), "places": len(values["places.json"]), "price_bundles": len(values["price_bundles.json"]), "area_metrics": len(values["area_metrics.json"])}
    if counts != manifest["counts"]:
        raise RuntimeError(f"manifest 행 수 불일치: {counts} != {manifest['counts']}")
    hashes = {}
    for name in names:
        digest = hashlib.sha256((data_dir / name).read_bytes()).hexdigest()
        hashes[name] = digest
        if digest != manifest["files"][name]["sha256"]:
            raise RuntimeError(f"파일 해시 불일치: {name}")
    if any(not row.get("is_mock") for rows in values.values() for row in rows):
        raise RuntimeError("demo 데이터에 is_mock=false 행이 있습니다.")
    return {"snapshot_id": manifest["snapshot_id"], "counts": counts, "hashes": hashes}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="원본 manifest·해시·행 수와 기존 DB를 검사")
    args = parser.parse_args()
    settings = load_settings(ROOT)
    source_result = check_source_files(settings)
    db = Database(settings)
    if args.check:
        result = {"source": source_result}
        if settings.database_path.exists():
            result["database"] = db.verify_demo()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    result = db.seed_demo()
    print(json.dumps({"seeded": True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
