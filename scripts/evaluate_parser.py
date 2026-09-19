from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.domain.parser import parse_query  # noqa: E402


def get_path(value: dict, path: str):
    current = value
    for part in path.split("."):
        current = current[part]
    return current


def main() -> int:
    data = json.loads((ROOT / "tests" / "parse_cases.json").read_text(encoding="utf-8"))
    total = passed = confirmation_errors = 0
    failures = []
    for case in data["cases"]:
        result = parse_query(case["text"], datetime.fromisoformat(case["reference_now"]))
        for path, expected in case["expected_fields"].items():
            total += 1
            actual = get_path(result["draft"], path)
            if actual == expected or (isinstance(expected, list) and set(actual or []) == set(expected)):
                passed += 1
            else:
                failures.append({"id": case["id"], "field": path, "expected": expected, "actual": actual})
        required = set(case["confirmation_required_contains"])
        if not required.issubset(set(result["confirmation_required"])):
            confirmation_errors += 1
            failures.append({"id": case["id"], "field": "confirmation_required", "expected_contains": sorted(required), "actual": result["confirmation_required"]})
    accuracy = passed / total if total else 0
    payload = {"cases": len(data["cases"]), "fields_total": total, "fields_passed": passed, "accuracy": accuracy, "confirmation_errors": confirmation_errors, "failures": failures}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if accuracy >= 0.9 and confirmation_errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
