# v2.1 계약 검토 기록

출처: `소비나침반_디자인_API계약_검토서_v2.1.docx`의 계약 대조 표와 현재 저장소. 원본 첨부물의 `contracts/REVIEW.md` 경로는 제공되지 않아 이 파일을 저장소 기준의 정규 검토 기록으로 작성했다.

| ID | 쟁점 | 현재 상태 | 증거/조치 |
|---|---|---|---|
| B-01 | 백엔드 원본·생성기 경로 확인 필요 | 해소 | `backend/`, `scripts/export_openapi.py`가 존재하고 생성 파일을 갱신함 |
| C-01 | 오류 envelope와 OpenAPI 기본 `detail` 불일치 | 해소 | 주요 오류 응답을 `ErrorResponse`로 명시하고 404/409/413/422/500/503 문서화 |
| C-02 | `health/meta` 200 응답 schema가 비어 있음 | 해소 | `HealthResponse`, `MetaResponse` 추가 |
| C-03 | `draft/place/price/evidence/metrics`가 넓은 object | 해소 | `ParseDraft`, `PlaceData`, `PriceData`, `EvidenceData`, `AreaMetricData` 추가 |
| C-04 | parse 예시에 선택 필드·기본값이 누락됨 | 해소 | `contracts/examples/parse.response.json`을 명시 DTO와 동기화 |
| C-05 | 409 오래된 결과 처리 | 해소 | 프론트가 종속 상태를 비우고 meta를 재조회하며 자동 재전송하지 않음 |
| C-06 | 수정 중인 조건과 추천/예산 요청 맥락 혼선 | 해소 | 확정 조건과 snapshot을 요청 시 고정하고 409에서 결과를 초기화 |
| C-07 | `required_atmosphere ⊆ atmosphere_preferences` 확인 약함 | 해소 | 서버 validator와 S02 선택 제어 모두 적용 |
| C-08 | 가격 출처 식별자 부족 | 해소(현재 demo) | 장소 상세 공개 DTO에 `source_id`, `observed_at`, `is_mock` 추가. 실제 링크/기관은 데이터 입력 전 미확인 상태 |
| C-09 | 저장값 오염·저장소 쓰기 실패 방어 | 해소 | 타입/필수값 정제, 최대 20개 제한, 읽기·쓰기 예외를 임시 메모리 상태로 처리 |
| C-10 | 잘못된 성공 JSON의 프론트 방어 부족 | 해소 | client가 공통 `request_id`·`warnings` envelope를 검사하고 502로 실패 |
| V-01 | 고정 대역 UI를 실제 연동으로 오인할 위험 | 해소 | `scripts/verify_http.py`로 실제 서버/CORS/계산/오류 계약을 분리 검증 |
| V-02 | 대상 OS 정식 build 미확인 | 해소(Windows) | `npm.cmd run build`에서 `tsc -b`와 Vite build exit 0 |
| V-03 | 전체 화면 확대·스크린리더 검수 | 미실행 | NOT_RUN. 브라우저 자동 검증과 별개로 후속 수동 검수 필요 |
| V-04 | Gemini 실제 호출 | 미실행 | 키·외부 전송·비용 승인 없이 실행하지 않음. 서버 어댑터와 fallback만 준비 |

## 정직성 규칙

검토용 HTML의 고정 응답 성공, JSON 구조 검사, 서버가 없는 DOM 검사는 실제 계산·CORS·native storage·Gemini 검증으로 승격하지 않는다. 미실행 항목은 `NOT_RUN`으로 유지한다.
