from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config import load_settings  # noqa: E402
from backend.app.real_data import import_real_package, load_and_validate_real_package  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="권리·해시·범위를 확인한 실제 데이터 패키지를 검사하거나 반입합니다.")
    parser.add_argument("--check", action="store_true", help="DB를 변경하지 않고 파일 계약만 검사")
    args = parser.parse_args()
    settings = load_settings(ROOT)
    if args.check:
        result = load_and_validate_real_package(settings.data_dir)
        print(json.dumps({"valid": True, "snapshot_id": result["manifest"]["snapshot_id"], "counts": result["counts"]}, ensure_ascii=False, indent=2))
        return 0
    result = import_real_package(settings)
    print(json.dumps({"imported": True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
