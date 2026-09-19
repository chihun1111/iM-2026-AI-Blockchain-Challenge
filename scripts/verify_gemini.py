"""Run a secret-safe Gemini adapter smoke check when server env is configured.

This command intentionally does not accept an API key argument and never
prints the key, request headers, or raw provider response. Without the
required server environment it reports NOT_RUN and exits successfully unless
--require-configured is supplied.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.adapters.gemini import GeminiAdapter  # noqa: E402
from backend.app.config import load_settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="비밀값을 노출하지 않는 Gemini 실연결 스모크 검사")
    parser.add_argument(
        "--text",
        default="동성로에서 친구와 저녁 식사를 할 건데 인당 2만원 이내로 추천해줘",
        help="Gemini로 보낼 테스트 문장. 개인정보·민감정보를 넣지 마세요.",
    )
    parser.add_argument(
        "--require-configured",
        action="store_true",
        help="서버 환경이 준비되지 않았으면 실패 코드로 종료",
    )
    args = parser.parse_args()

    settings = load_settings(ROOT)
    if not settings.gemini_configured:
        result = {"status": "NOT_RUN", "reason": "서버 전용 GEMINI_API_KEY가 없습니다. GOOGLE_API_KEY는 이 앱에서 사용하지 않습니다."}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if args.require_configured else 0
    if not settings.external_adapter_enabled:
        result = {
            "status": "NOT_RUN",
            "reason": "Gemini 실행 게이트가 닫혀 있습니다.",
            "gate_reasons": list(settings.gemini_gate_reasons),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if args.require_configured else 0

    try:
        response = GeminiAdapter(settings).parse(args.text, settings.reference_now)
    except Exception as exc:  # pragma: no cover - live provider path
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(
        json.dumps(
            {
                "status": "PASS",
                "model": response.model,
                "attempts": response.attempts,
                "candidate_fields": sorted(response.candidate.keys()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
