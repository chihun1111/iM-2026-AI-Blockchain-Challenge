# 앱 테스트 보고서 v3.2

확인일: 2026-09-19
상태: `PROTOTYPE_INPUT_REQUIRED`

## 실행 결과

| 검증 묶음 | 상태 | 관측 결과 |
|---|---|---|
| v3.2 후보·승인 준비도 | PASS_EXPECTED_BLOCKERS | 3개 장소·7개 메뉴 후보, 검증 메뉴 0개, 카드 파일 0개/0행, Gemini 미승인을 정확히 출력 |
| S04 공공 점포 원본 | PASS | 공식 ZIP/대구 CSV 크기·SHA-256, 118,357행, 세 점포 상호/지점명+주소·ID·업종·좌표 일치 |
| demo manifest·DB | PASS | sources=2, areas=8, places=40, price_bundles=40, area_metrics=768, FK 오류 0 |
| 규칙 파서 30문장 | PASS | 72/72 필드, 범위 밖 수성못·카페 null 처리 포함 |
| 백엔드 도메인·API·Gemini gate | PASS | 33 passed, 동시 비용 예약 포함, 외부 라이브러리 deprecation warning 1개 |
| real 반입·메뉴 계산 | PASS_SYNTHETIC_FIXTURE_ONLY | 메뉴별 최소 주문·필수비용, 총/인당 예산, 1원 경계, 인원 변경, 정보 부족 reason code 검증 |
| OpenAPI | PASS | 백엔드 모델에서 `contracts/`·`schemas/` 동시 재생성 |
| 프런트 production build | PASS | TypeScript와 Vite build exit 0 |
| 실제 localhost HTTP | PASS | CORS, health/meta/parse/recommendations/place/budget 200, 추천 3건, 409/413 envelope |
| 로컬 브라우저 3단계 | PASS_DEMO_ONLY | 입력·조건 → 추천 3개 → 근거 → 예산 비교, 평일/주말·시간대 표시 |
| 브라우저 console | PASS | warning/error 0건 |
| 실제 데이터 흐름 | NOT_RUN | S04 점포 매칭은 완료했으나 실제 메뉴·카드 집계/권한 미확보 |
| 실제 Gemini 호출 | NOT_RUN | `UNAPPROVED`, `llm_enabled=false`, 데이터 API gate 미통과 |

## 재현 명령

```powershell
.venv\Scripts\python.exe scripts\verify.py --all
.venv\Scripts\python.exe scripts\verify_http.py
.venv\Scripts\python.exe scripts\check_v32_readiness.py
.venv\Scripts\python.exe scripts\verify_s04_matches.py
```

`verify.py --all`은 준비도, demo seed, 파서, pytest, OpenAPI, 프런트 빌드를 실행한다. 실제 Gemini 호출은 포함하지 않는다. 승인 이후에만 `scripts\verify_gemini.py --require-configured`를 사용한다.

## 해석 경계

S04 원본 점포 매칭 통과와 합성 demo/synthetic real fixture 통과는 현재 메뉴·카드 집계·권리 확보 또는 Gemini 연결 성공을 뜻하지 않는다. 실제 메뉴·카드 파일로 같은 API와 브라우저 검사를 다시 통과하기 전에는 데이터 API 완료나 전체 프로토타입 완료로 표현하지 않는다.
