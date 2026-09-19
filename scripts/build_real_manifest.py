from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "real"
FILES = ("sources.json", "areas.json", "places.json", "menu_items.json", "area_metrics.json")


def main() -> int:
    manifest_path = DATA_DIR / "manifest.json"
    if not manifest_path.exists():
        raise RuntimeError("먼저 data/real/manifest.json에 snapshot_id, reference_now, 기간, region_id, category를 작성하세요.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = ("snapshot_id", "reference_now", "window_start", "window_end", "region_id", "category")
    missing = [key for key in required if not manifest.get(key)]
    if missing:
        raise RuntimeError(f"manifest 기본 필드 누락: {', '.join(missing)}")
    values = {}
    for name in FILES:
        path = DATA_DIR / name
        if not path.exists():
            raise RuntimeError(f"실데이터 파일이 없습니다: {name}")
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, list):
            raise RuntimeError(f"{name}은 JSON 배열이어야 합니다.")
        if any(row.get("is_mock") is not False for row in value):
            raise RuntimeError(f"{name}에는 is_mock=false인 행만 허용됩니다.")
        values[name] = value
    manifest.update(
        {
            "data_mode": "real",
            "is_mock": False,
            "counts": {
                "sources": len(values["sources.json"]),
                "areas": len(values["areas.json"]),
                "places": len(values["places.json"]),
                "menu_items": len(values["menu_items.json"]),
                "area_metrics": len(values["area_metrics.json"]),
            },
            "files": {
                name: {"sha256": hashlib.sha256((DATA_DIR / name).read_bytes()).hexdigest()}
                for name in FILES
            },
        }
    )
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
