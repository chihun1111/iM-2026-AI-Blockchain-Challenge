# 앱 테스트 보고서

확인일: 2026-09-19

상태: `DONE_WITH_FOLLOWUPS`

## 실행 결과

| 검증 묶음 | 상태 | 실행 명령/범위 | 관측 결과 |
|---|---|---|---|
| 원본 데이터·manifest·DB | PASS | `.venv\Scripts\python.exe scripts/seed_demo.py --check` | sources=2, areas=8, places=40, price_bundles=40, area_metrics=768, FK 오류 0 |
| 규칙 파서 30문장 | PASS | `.venv\Scripts\python.exe scripts/evaluate_parser.py` | 72/72 필드, 정확도 1.0 |
| 백엔드 도메인·API·Gemini provider 테스트 | PASS | `.venv\Scripts\python.exe -m pytest -q` | 18 passed, 외부 라이브러리 deprecation warning 1개 |
| 명시 DTO/OpenAPI | PASS | `.venv\Scripts\python.exe scripts/export_openapi.py` | Health/Meta/ParseDraft/Place/Price/Evidence/Metric/Error DTO 생성, `contracts/`·`schemas/` 동시 갱신 |
| 프런트 타입·정식 build | PASS | `frontend\npm.cmd run build` | `tsc -b`와 Vite 7.1.5 production build exit 0 |
| 실제 HTTP·CORS·계산 | PASS | `.venv\Scripts\python.exe scripts/verify_http.py` | preflight 200, health/meta/parse/recommendations/place/budget 200, 추천 5건, 409/413 envelope 확인 |
| 실제 브라우저 S01~S05 | PASS | Playwright headed `sobi-v21`, `http://127.0.0.1:5173/` | 빈 입력 오류, 조건 확정, 추천 5건, 지도 대기, 3개 비교, 장소 근거, 예산 계산 확인 |
| native localStorage | PASS | 실제 origin 브라우저에서 reload 후 `consumer-compass-saved-v2` 확인 | 장소 ID·스냅샷·저장 시각만 저장됨 |
| 반응형·가로 넘침 | PASS | 360/390/768/1280px viewport | `scrollWidth <= innerWidth`, 실제 화면 캡처를 `output/playwright/`에 저장 |
| 키보드·콘솔 | PASS | Tab/focus와 새 브라우저 콘솔 | 포커스 링 확인, Errors 0 / Warnings 0 (React DevTools info만 존재) |
| 기본 보안 점검 | PASS_WITH_DEMO_LIMITS | `reports/SECURITY_REVIEW.md` | 외부 호출 기본 비활성, 키 서버 전용, raw HTML 주입 없음 |
| 실제 Gemini 호출 | NOT_RUN | 비공개 키·원문 전송 범위·실제 비용 승인 없음 | 서버 어댑터·공유 enum 스키마·비용 승인 게이트·fallback 준비 완료 |
| 지도·실데이터·스크린리더 수동 검수 | NOT_RUN | P0 외부 연동/수동 검수 범위 | 좌표·사진을 만들지 않고 미연결 상태로 표시 |

## 재현 명령

```powershell
.venv\Scripts\python.exe scripts/verify.py --all
.venv\Scripts\python.exe scripts/verify_http.py
```

`verify.py --all`는 seed 검사, 파서 평가, pytest, OpenAPI 생성, 프런트엔드 production build를 실행한다. `verify_http.py`는 이미 실행 중인 localhost 서버를 대상으로 실제 HTTP/CORS와 오류 envelope를 별도 검사한다. `verify_gemini.py --require-configured`는 환경변수가 있을 때만 실제 Gemini 어댑터를 호출한다. 일반 테스트는 네트워크를 모킹해 서버 헤더·공유 enum 검증·비용 승인 게이트·401/403 무재시도·timeout 1회 재시도·규칙 fallback을 확인한다.

## 해석 경계

고정 디자인 HTML의 가상 fetch 성공이나 서버가 없는 DOM 대역 검사는 실제 API 계산·CORS·저장소·Gemini 검증으로 승격하지 않는다. 미실행 항목은 `NOT_RUN`으로 유지한다.
