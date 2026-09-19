# 계약 보완안과 적용 결과

> v3.2 현재 계약은 `frontend-backend-contract.md`가 우선한다. 아래 내용 중 v2.1 범위·Gemini 게이트 설명은 이력으로만 보존한다.

검토 DOCX의 보완 표를 저장소 모델·OpenAPI·프론트 DTO 순서로 반영한 기록이다.

## 적용

- 공통 성공 메타 `request_id`, `snapshot_id`, `policy_version`, `data_mode`, `reference_now`, `warnings`를 필수로 유지했다.
- `HealthResponse`와 `MetaResponse`를 추가해 초기 상태와 어댑터 상태를 구조화했다.
- parse 초안을 `ParseDraft`와 `DraftBudget`로 분리하고 `confirmed=false`를 강제했다.
- 장소 상세를 공개 DTO로 제한하고 가격·근거·상권 집계에 `source_id`, `observed_at`, `is_mock`, 집계 범위 필드를 명시했다.
- 모든 주요 오류 상태를 공통 `ErrorResponse`로 문서화했고, 서버는 stack trace·provider 응답·키를 노출하지 않는다.
- 백엔드 모델 변경 후 `scripts/export_openapi.py`가 `contracts/`와 호환 `schemas/` 양쪽을 재생성한다.
- 프론트 client는 공통 성공 envelope와 오류 envelope를 최소 검사하며, 서버 금액·잔여·순위를 계산하지 않는다.
- Gemini 후보 응답은 공유 `RegionId`/`Category`/`Purpose`/`Atmosphere`/`BudgetType`/`PriorityProfile` enum으로 다시 검증하고, `ALLOW_EXTERNAL_CALLS`와 `ALLOW_PAID_CALLS`가 모두 켜져야 외부 호출을 허용한다.
- `scripts/verify_gemini.py`는 비밀값을 명령행·출력에 노출하지 않고, 환경이 없으면 `NOT_RUN`으로 종료해 다음 실호출 재개 지점을 고정한다.

## 보류

- 실제 출처 기관·공개 링크·권리 정보: 현재 demo 데이터에 값이 없어 추가하지 않는다.
- 지도·사진·지역혜택·결제·실시간 데이터: 외부 권한과 데이터 계약이 확정될 때 별도 변경으로 승인한다.
- Gemini 실호출: 서버 어댑터·제한된 후보 스키마·공유 enum 검증·timeout·fallback·비용 승인 게이트 준비만 완료했으며, API 키를 채팅이나 프론트에 요구하지 않는다.
