from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.readiness import validate_candidate_register, validate_gemini_approval_plan  # noqa: E402


def main() -> int:
    result = {
        "candidate_register": validate_candidate_register(ROOT / "data" / "real" / "data_candidates.json"),
        "gemini_approval": validate_gemini_approval_plan(ROOT / "config" / "gemini_approval_plan.json"),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
