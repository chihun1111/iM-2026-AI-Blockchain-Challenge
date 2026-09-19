# 소비나침반 프로토타입 v3.2 진행 보고

## 완료

- 동성로·중앙로역 일대 / 한식 음식점으로 실행 범위를 제한하고 카페·수성못·전체 대구 확장을 UI와 서버 정책에서 제외했다.
- 3개 장소와 7개 공개 게시 가격을 실제 검증 가격과 분리한 후보부로 기록했다. 현재 모두 예산 추천에 사용할 수 없다.
- 메뉴별 현재 가격·제공 단위·최소 주문·필수비용·확인일·확인자 역할·이용 근거·증빙을 요구하는 승격 검사를 구현했다.
- 검증 패키지에서는 `가격 × max(인원, 최소 주문) + 확인된 필수비용`으로 계산한다. 필수비용 null은 0원이 아니라 `MANDATORY_FEE_UNKNOWN`이다.
- 총/인당 예산, 1원 경계, 인원 변경, 결과 없음, 가격 부족, 상권 근거 부족, 스냅샷 불일치, 없는 ID를 합성 검증 fixture의 실제 FastAPI 요청으로 통과했다.
- 상권 집계를 점포 순위에서 제거하고 실제 기간의 공통 과거 참고 근거로만 표시한다.
- Gemini는 승인 파일·데이터 API 통과·모델/전송/비용 승인·서버 키·요청별 동의가 모두 있어야 호출하도록 준비했다. 비용은 호출 전 예약하며 unknown usage 실패는 예약을 유지한다.
- 백엔드 32개 테스트와 프런트 production build를 통과했다.

## 미완료·미검증

- 필수: 최신 메뉴·주문조건 실증빙, S04 원본 CSV/점포 매칭, 신한카드 실파일·사전·사용권이 없어 실제 데이터 API는 아직 통과하지 않았다.
- 필수: 실제 데이터로 추천·상세·예산·정보 부족 흐름을 서버와 브라우저에서 실행하지 않았다.
- 후속 승인: Gemini 사용안은 미승인이고 `llm_enabled=false`다. 실제 키 호출·한국어 품질·과금 사용량은 미검증이다.
- 현재 실행 화면은 합성 demo이며 이를 실제 장소·매출·현재 인기라고 볼 수 없다.

## 필요한 입력

- 세 점포별 `price_krw`, `portion`, `minimum_order`, `mandatory_cost`, `confirmed_on`, `confirmed_by_role`, `usage_basis`, `source_url` 또는 `evidence_file`.
- S04 대구 원본과 데이터 사전, 점포 ID·주소·업종·위경도 매칭 결과.
- 승인된 신한카드 집계 파일, 데이터 사전/코드표, 실제 범위·기간·단위·측정 방식, 분석/반출/ZIP/화면·영상/공개 웹 권한.
- 위 자료로 데이터 API 통과 후 Gemini 승인자·시각·모델·전송 범위·총/일 한도. 키 값은 요청하지 않는다.

## 재개 위치

1. [data_candidates.json](../data/real/data_candidates.json)의 null 검증 필드를 실제 근거로 채운다.
2. `.venv\Scripts\python.exe scripts\check_v32_readiness.py`로 후보·권한·승인 상태를 확인한다.
3. `sources.json`, `areas.json`, `places.json`, `menu_items.json`, `area_metrics.json`을 작성하고 manifest 해시를 생성한다.
4. `scripts/import_real_data.py --check`와 actual DB 반입 후 API·브라우저 인수 시나리오를 실행한다.
5. 실제 데이터 API 증빙을 승인 파일에 기록한 뒤에만 Gemini 승인과 `scripts/verify_gemini.py --require-configured`로 진행한다.
