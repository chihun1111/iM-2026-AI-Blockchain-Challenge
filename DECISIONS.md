# 결정 기록

본 문서의 DEFAULT_SPEC는 실행서의 제안 기본값이지 실제 사용권·외부 비용의 승인 증거가 아니다.

| ID | 상태 | 결정 | 영향 |
|---|---|---|---|
| D-001 | DEFAULT_SPEC | P0_DEMO부터 구현 | 외부 연동 없이 기본 흐름 검증 가능 |
| D-002 | DEFAULT_SPEC | 시연 지역 2개, 점포 40개, 1~6명 | 범위 확장은 별도 결정 |
| D-003 | DEFAULT_SPEC | 규칙 파서·템플릿 설명·지도 off | 실제 AI·실지도 완료로 표시 금지 |
| D-004 | DEFAULT_SPEC | 예상 상한 기준 예산 판정 | 일부 메뉴가 저렴해도 상한 초과는 추천 제외 |
| D-005 | DEFAULT_SPEC | 대안 3개 비교, 방문 코스 합산 제외 | 여러 장소를 모두 방문한다고 해석하지 않음 |
| D-006 | DEFAULT_SPEC | real/demo 격리·불변 스냅샷 | 실패 시 무단 가상 대체 금지 |
| D-007 | DEFAULT_SPEC | 정책 임계값은 config/policy.v2.json | 법적·통계적 보장으로 표현 금지 |
| D-008 | DEFAULT_SPEC | 막히면 영향별 중단·독립 진행·종료 재요청 | 필수 미완료 전체 완료 선언 금지 |
| D-009 | NOT_APPROVED | 외부 유료 호출·실데이터 사용·공개 배포 | 사용자 및 실행 환경 권한 확인 전 금지 |
| D-010 | USER_REQUEST | 필요한 API를 먼저 완료하고 Gemini는 후속 연결. 현재는 서버 전용 어댑터·환경변수·검증 경로만 준비 | P0 규칙 파서·외부 호출 비활성 유지, X01 실호출은 후속 작업 |
| D-011 | IMPLEMENTED | Gemini REST 키는 URL query가 아니라 `x-goog-api-key` 서버 헤더로 전송하고 JSON 응답을 다시 검증 | 키가 URL·클라이언트 번들·일반 응답에 노출되지 않도록 함 |
| D-012 | IMPLEMENTED | API 계약을 고정한 뒤 S01~S05 React 흐름과 브라우저 검수를 완료하고 외부 연동은 후속으로 유지 | P0 데모는 독립 실행 가능하며 `DONE_WITH_FOLLOWUPS`로 인계 |
| D-013 | IMPLEMENTED · 2026-09-19 | v2.1 디자인은 제공 HTML을 복제하지 않고 `design/DESIGN_SPEC.md`와 React UI 토큰·목록/상태/비교 패널로 병합 | 좌표·사진·출처 링크가 없는 상태는 그대로 표시하며 `frontend/src/ui/`, `frontend/src/styles.css`, `reports/UI_BROWSER.md`에 반영 |
| D-014 | IMPLEMENTED · 2026-09-19 | 계약 검토 보완은 백엔드 Pydantic 모델 → 생성 OpenAPI → 프론트 DTO/가드 → 실제 HTTP 검증 순서로 적용 | `contracts/REVIEW.md`, `contracts/PROPOSED_CHANGES.md`, `scripts/verify_http.py`, generated schema가 회귀 기준 |
| D-015 | IMPLEMENTED · 2026-09-19 | Gemini 외부 호출은 키와 네트워크 허용뿐 아니라 명시적 비용 승인(`ALLOW_PAID_CALLS`)도 함께 요구하고, provider 후보는 공유 계약 enum으로 재검증 | `backend/app/config.py`, `backend/app/adapters/gemini.py`, `backend/tests/test_gemini_adapter.py`, `backend/tests/test_gemini_provider.py` |
| D-016 | USER_REQUEST · 2026-09-19 | v3.1 제출 최소범위를 현재 목표로 삼고 기존 P0 합성 데모는 참고 구현으로만 보존 | 실데이터·실제 AI·계산·오류 사례가 없으면 완료 선언 금지 |
| D-017 | SCOPE_GATE · 2026-09-19 | 실제 범위는 사용자가 확정할 대구 상권 1곳과 원천 분류에 맞는 업종 1개로 제한 | 임의 지역·업종·가짜 행을 추가하지 않으며 `data/real/README.md` 입력 후 구현 |
| D-018 | VERIFIED · 2026-09-19 | 공식 공고·양식·FAQ·실제 접수 화면을 각각 감사하고 HWPX/ZIP/영상 규격 불일치를 별도 블로커로 기록 | `contest/SUBMISSION_AUDIT.md`; 사용자 승인 전 제출 금지 |
| D-019 | IMPLEMENTED · 2026-09-19 | 사용자가 조건을 바꾸면 이전 추천·상세·예산과 선택을 무효화하고 선행 결과 없는 단계 이동을 막음 | `frontend/src/App.tsx`, `frontend/src/ui/AppLayout.tsx`, `reports/V31_UI_REGRESSION.md` |
| D-020 | PROPOSED · 2026-09-19 | 실제 가격 응답은 단순 범위가 아니라 계산에 사용된 개별 메뉴·수량·출처·기준일을 보존 | 입력 자료 확정 뒤 `contracts/v3.1-submission-contract.md`를 구현 계약으로 승격 |
| D-021 | USER_REQUEST · 2026-09-19 | 제출 서류·접수·업로드는 사용자가 담당하고 에이전트는 제출용 프로토타입 구현에만 집중 | 제출 관련 감사 자료는 보존하되 활성 작업·블로커에서 제외 |
| D-022 | IMPLEMENTED · 2026-09-19 | 프로토타입 기본 범위를 동성로 음식점으로 두고 사용자 동선을 입력·조건, 추천, 근거·예산의 3단계로 표시 | `frontend/src/ui/AppLayout.tsx`, `frontend/src/ui/Screens.tsx` |
| D-023 | IMPLEMENTED · 2026-09-19 | 실제 메뉴 항목·최소 주문 수량을 저장하고 서버가 인원별 최소/최대 비용을 계산하며, 출처 URI·권리 근거·해시를 통과한 real 패키지만 반입 | `backend/app/real_data.py`, `backend/app/domain/budget.py`, `scripts/import_real_data.py`, `backend/tests/test_real_data.py` |
| D-024 | USER_REQUEST · 2026-09-19 | v3.2 범위를 동성로·중앙로역 일대 / 한식 음식점과 국일따로국밥·개정 본점·마산설렁탕 후보로 고정 | D-002의 2개 지역·40개 데모 범위와 D-017의 미정 범위를 프로토타입 구현에서 대체. 3곳은 공모전 최소 요건이 아님 |
| D-025 | IMPLEMENTED · 2026-09-19 | 대구푸드 게시 가격은 참조 후보로만 보존하고, 현재 가격·제공 단위·최소 주문·필수비용·확인일·이용 근거·증빙이 모두 있어야 예산 후보로 승격 | `data/real/data_candidates.json`, `backend/app/readiness.py`, `backend/app/real_data.py` |
| D-026 | IMPLEMENTED · 2026-09-19 | 같은 지역·업종의 과거 상권 집계는 점포 순위 특성에서 제거하고 공통 참고 근거로만 사용 | `backend/app/domain/ranking.py`, `backend/app/domain/evidence.py`, `frontend/src/ui/Screens.tsx` |
| D-027 | IMPLEMENTED · 2026-09-19 | Gemini는 승인안·데이터 API gate·요청별 동의·비식별 검사·비용 사전예약이 모두 통과해야 하며 앱은 `GEMINI_API_KEY`만 사용 | `config/gemini_approval_plan.json`, `backend/app/config.py`, `backend/app/gemini_usage.py`, `backend/app/adapters/gemini.py` |
| D-028 | NOT_APPROVED · 2026-09-19 | Google Gemini Developer API / `gemini-3.5-flash-lite` 유료 사용, 총 US$5·일 US$1 제안 | 데이터 API 실제 통과 후 승인자·일시·전송 범위·한도를 기록하기 전에는 `llm_enabled=false` 유지 |
| D-029 | VERIFIED · 2026-09-19 | S04 2026-06 공식 ZIP/대구 CSV 해시를 고정하고 상호·지점명+도로명주소가 정확히 일치한 3건만 공공 점포로 매칭 | 세 곳의 `I201 한식` 업종과 점 위치는 확인했지만 두 행정동에 걸치므로 공식 상권 경계·대표 행정동·임의 반경은 선언하지 않음 |

새 결정은 날짜, 결정자/출처, 대안, 영향 파일, 승인 범위, 정책 버전, 회귀 테스트를 함께 기록한다. 이전 결정을 삭제하여 변경 이력을 숨기지 않는다.
