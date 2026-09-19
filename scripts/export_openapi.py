from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.api import create_app  # noqa: E402
from backend.app.config import load_settings  # noqa: E402


def main() -> int:
    settings = load_settings(ROOT)
    document = json.dumps(create_app(settings).openapi(), ensure_ascii=False, indent=2) + "\n"
    outputs = [ROOT / "schemas" / "openapi.generated.json", ROOT / "contracts" / "openapi.generated.json"]
    for output in outputs:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(document, encoding="utf-8")
    print("\n".join(str(output) for output in outputs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
