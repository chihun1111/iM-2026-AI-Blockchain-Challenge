# 프론트–백엔드 계약서 v3.2

정책 버전: `cc-policy-3.2.0`  
프로토타입 범위: 동성로·중앙로역 일대 / 한식 음식점  
실데이터 상태: 입력 대기. 현재 기본 실행은 합성 demo이며 실제로 표시하지 않는다.

## 공통 규칙

- 개발 프런트: `http://127.0.0.1:5173`
- 개발 API: `http://127.0.0.1:8000`
- 프런트는 `VITE_API_BASE_URL`을 사용하고 금액·순위·예산 상태를 재계산하지 않는다.
- 모든 성공 응답은 `request_id`, `snapshot_id`, `policy_version`, `data_mode`, `reference_now`, `warnings`를 포함한다.
- 후속 요청은 직전 `snapshot_id`를 그대로 보내며 불일치 시 `409 SNAPSHOT_MISMATCH`를 처리한다.
- 현재 허용 조건은 `region_id=dongseongro`, `category=restaurant`, `priority_profile=balanced`뿐이다.
- 상권 경계·행정동 코드·반경은 확인된 원천 매핑 전까지 실제 범위로 주장하지 않는다.

오류 envelope는 다음과 같다.

```json
{
  "request_id": "uuid",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "요청 형식 또는 값이 올바르지 않습니다.",
    "retryable": false,
    "fields": [{"path": "conditions.visit_at", "message": "허용 범위를 확인하세요."}]
  }
}
```

추가 범위 오류는 `REGION_OUT_OF_SCOPE`, `CATEGORY_OUT_OF_SCOPE`, `RANKING_PROFILE_OUT_OF_SCOPE`다.

## 엔드포인트

| 메서드 | 경로 | 역할 |
|---|---|---|
| GET | `/api/health` | DB·스냅샷·외부 어댑터 실행 가능 상태 |
| GET | `/api/meta` | 지원 범위와 현재 스냅샷 |
| POST | `/api/parse-query` | 짧은 문장을 조건 초안으로 변환 |
| POST | `/api/recommendations` | 검증 메뉴·예산·목적으로 후보 비교 |
| GET | `/api/places/{place_id}` | 장소·메뉴 검증정보·과거 상권 참고 근거 |
| POST | `/api/budget/estimate` | 선택한 각 장소의 예산을 독립 계산 |

### POST `/api/parse-query`

```json
{
  "text": "동성로에서 2명이 저녁 7시에 한식, 인당 2만원 이하",
  "external_ai_consent": false
}
```

`external_ai_consent` 기본값은 `false`다. Gemini 게이트가 열렸더라도 이 값이 `true`가 아니면 원문을 외부로 보내지 않고 규칙 파서를 사용한다. 전화번호·이메일·주민번호·계좌/카드번호·정밀 좌표 패턴이 감지되면 동의 여부와 관계없이 외부 전송을 중단한다.

### POST `/api/recommendations`

확정 조건의 핵심은 다음과 같다.

```json
{
  "schema_version": "2.0",
  "region_id": "dongseongro",
  "category": "restaurant",
  "purpose": "meal",
  "party_size": 2,
  "budget": {"type": "per_person", "amount": 20000, "currency": "KRW"},
  "visit_at": "2026-09-21T19:00:00+09:00",
  "atmosphere_preferences": [],
  "required_atmosphere": [],
  "priority_profile": "balanced",
  "origin": null,
  "radius_m": 2000,
  "confirmed": true
}
```

- `items`는 최대 3개다. 3은 현재 프로젝트 목록 범위이며 공모전 최소 개수 요건이 아니다.
- 상권 집계는 점포 간 점수 또는 순위에 사용하지 않는다.
- 가격·필수비용 또는 상권 근거가 없으면 `insufficient_data_items`로 분리하고 `data_status_reason`에 `PRICE_MISSING`, `PRICE_STALE`, `MANDATORY_FEE_UNKNOWN`, `AREA_EVIDENCE_MISSING` 등을 반환한다.
- 영업시간이 검증된 장소만 시간 필터에 사용한다. 미검증 장소는 `opening_status=unknown`이며 영업 중이라고 주장하지 않는다.

### GET `/api/places/{place_id}`

`price.menu_items[]`는 다음 검증 필드를 반환한다.

- `price_krw`, `portion`, `minimum_order`, `mandatory_cost`
- `confirmed_on`, `confirmed_by_role`, `usage_basis`
- `source_url` 또는 `evidence_file`, `source_id`
- `is_budget_candidate`, `is_mock`

`mandatory_cost=0`은 확인된 0원일 때만 허용한다. 미확인값을 0으로 변환하지 않는다. `area_timeseries`는 승인된 실제 관측 기간을 그대로 표시하며 점포 매출·현재 인기·실시간 혼잡으로 표현하지 않는다.

### POST `/api/budget/estimate`

서버는 메뉴마다 아래 식을 계산한다.

```text
quantity = max(party_size, minimum_order)
subtotal = price_krw × quantity
total_price = subtotal + mandatory_cost
```

응답 `menu_calculations[]`는 `unit_price`, `quantity`, `subtotal`, `mandatory_cost`, `total_price`를 포함한다. `reason_code`는 계산 불가 사유를 보존한다. 총예산과 인당 예산, 1원 경계, 인원 변경, 결과 없음, 가격/상권 근거 부족, 스냅샷 불일치, 없는 ID는 서버 회귀 테스트 대상이다.

## Gemini 실행 게이트

Gemini는 짧은 비식별 소비조건 문장을 조건 JSON으로 추출하는 역할만 맡는다. 가격·예산·순위·상권 근거 문장은 서버의 검증 데이터와 코드가 처리한다.

호출 전 모든 조건이 필요하다.

1. `config/gemini_approval_plan.json`의 `status=APPROVED`, `llm_enabled=true`.
2. `data_api_gate.status=PASSED`와 비어 있지 않은 검증 증빙.
3. 승인자·승인시각·승인 모델·전송 범위·총/일 한도.
4. `ALLOW_EXTERNAL_CALLS=true`, `ALLOW_PAID_CALLS=true`.
5. 서버 전용 `GEMINI_API_KEY`. 이 앱은 `GOOGLE_API_KEY`와 일반 `LLM_API_KEY`를 Gemini 키로 사용하지 않는다.
6. 요청별 `external_ai_consent=true`.

호출 전 최대 과금액을 SQLite ledger에 원자적으로 예약한다. 재시도마다 별도 예약하고, 실제 usage를 알 수 있는 성공 응답은 정산한다. 사용량을 알 수 없는 실패는 예약액을 유지한다. ledger에는 원문·키·provider 원응답을 저장하지 않는다.

현재 승인안은 `UNAPPROVED`, 데이터 API 게이트는 `NOT_PASSED`, `llm_enabled=false`이므로 실제 Gemini 호출은 불가능하다.

## 변경 순서

백엔드 모델 → 생성 OpenAPI → 프런트 타입/표시 → 예시 → 테스트 순서로 맞춘다. 생성 OpenAPI만 고친 상태를 구현 완료로 판정하지 않는다.
