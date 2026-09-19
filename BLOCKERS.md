# 프로토타입 블로커 v3.2

제출 서류·접수·업로드는 사용자 담당이며 이 목록에 포함하지 않는다.

## BLK-V32-MENU 현재 메뉴·주문조건

- 상태: OPEN
- 영향: 3개 점포의 검증 예산 추천과 actual 데이터 API 통과
- 현재: 대구푸드 공개 페이지의 7개 게시 가격만 후보로 기록. 현재 적용 가격이 아니며 모두 `eligible_for_verified_budget=false`.
- 필요한 값: 점포/지점 주소, 메뉴명, `price_krw`, `portion`, `minimum_order`, `mandatory_cost`, `confirmed_on`, `confirmed_by_role`, `usage_basis`, `source_url` 또는 로컬 `evidence_file`.
- 주의: 미확인 필수비용을 0으로 채우지 않는다. 사진을 외부에 재게시하면 별도 권한이 필요하다.
- 독립 진행 완료: 후보 검증기, 필수비용 null 차단, 메뉴별 계산, 정보 부족 reason code.
- 재개: `data/real/data_candidates.json` 검증 필드 입력 → `scripts/check_v32_readiness.py`.

## BLK-V32-PLACE 공공 점포 원천과 코드 매핑

- 상태: OPEN
- 영향: 공식 점포 ID, 공간·업종 결합, 검증 가능한 장소 목록
- 현재: S04 카탈로그만 확인. 원본 CSV 미취득, 3개 점포 매칭 미완료, 경계·행정코드·반경 미정.
- 필요한 파일/필드: 소상공인시장진흥공단 상가(상권)정보_20260630 대구 원본, 데이터 사전, 상호명·업종코드/명·도로명주소·위경도·공공 점포 ID.
- 독립 진행 완료: 후보 내부 ID와 공공 ID 분리, 임의 경계/반경 차단.
- 재개: 원본 해시 고정 → 주소·상호 매칭 → 공간/한식 코드 확인 → `places.json`, `areas.json` 작성.

## BLK-V32-BEHAVIOR 카드 집계와 사용권

- 상태: OPEN
- 영향: 과거 상권 소비활동 참고 근거와 actual 데이터 API 통과
- 현재: 신한카드 `지역별매출및이용고객정보` 카탈로그만 확인. 실파일 0개, 0행, 사전/권한 미확보.
- 필요한 입력: 승인 파일, 데이터 사전·코드표, 대구 범위, 공간·한식 코드, 실제 기간·시간/금액/건수 단위, 측정/추정 방식, 결측·비공개값 의미.
- 필요한 권한: 분석, 가공 결과 반출, 코드/데이터 ZIP, 화면·시연 영상, 공개 웹 각각.
- 제한: 원본·집계를 Gemini에 전송하지 않음. 같은 지역·업종 값으로 점포 순위를 나누지 않음.
- 독립 진행 완료: 상권 점수 제거, 실제 기간 표시, 근거 없음 분리 처리.
- 재개: 권한 기록 → 허용된 행만 `area_metrics.json` 정규화 → 반입 검사.

## BLK-V32-GEMINI 승인 및 실호출

- 상태: WAITING_FOR_DATA_API
- 영향: 실제 AI 조건 추출
- 현재: `gemini-3.5-flash-lite` 유료안은 미승인, `llm_enabled=false`, 데이터 API 게이트 `NOT_PASSED`. 실호출 없음.
- 먼저 필요한 결과: 위 세 데이터 블로커 해소 후 actual 서버 API·브라우저 인수 증빙.
- 그다음 필요한 승인: 승인자·일시·모델·전송 범위·총 US$5/일 US$1 이하 한도.
- 키: 승인 후 사용자가 서버 `GEMINI_API_KEY`에 직접 설정. 채팅·Git·프런트·로그에 넣지 않음.
- 독립 진행 완료: 승인 게이트, 요청별 동의, 식별정보 차단, 동시성 안전 비용 예약/정산, 재시도 합산, unknown usage 예약 유지.
- 재개: `config/gemini_approval_plan.json` 승인 기록 → 환경변수 설정 → `scripts/verify_gemini.py --require-configured`.
