# 패키지 정합성 검증 결과

검사일: 2026-09-19

**범위: 구현 명세·JSON 스키마·가상 데이터·예시의 내부 정합성만 검사했습니다. 앱 실행·기능·성능·브라우저·외부 연동 테스트 결과가 아닙니다.**

검사 결과: 41개 PASS / 0개 FAIL.

| 검사 | 결과 |
|---|---|
| 모든 JSON 파일 구문 | PASS |
| places 행 수 | PASS |
| places 가상 데이터 표시 | PASS |
| price_bundles 행 수 | PASS |
| price_bundles 가상 데이터 표시 | PASS |
| areas 행 수 | PASS |
| areas 가상 데이터 표시 | PASS |
| area_metrics 행 수 | PASS |
| area_metrics 가상 데이터 표시 | PASS |
| sources 행 수 | PASS |
| sources 가상 데이터 표시 | PASS |
| sources.json SHA-256 | PASS |
| areas.json SHA-256 | PASS |
| places.json SHA-256 | PASS |
| price_bundles.json SHA-256 | PASS |
| area_metrics.json SHA-256 | PASS |
| 고유 장소·구역·출처·가격 키 | PASS |
| 장소 외래키 | PASS |
| 가격 외래키·최소/최대 | PASS |
| 집계 외래키 | PASS |
| 집계 복합키 고유성 | PASS |
| 완료 주 8개 | PASS |
| 주간 길이·요일 | PASS |
| 가상 실제 좌표·주소 미포함 | PASS |
| 업종 수·지역별 20개 | PASS |
| 정책 가중치 합계 | PASS |
| conditions.schema.json 스키마 자체 검증 | PASS |
| agent_status.schema.json 스키마 자체 검증 | PASS |
| 확정 조건 예시 스키마 일치 | PASS |
| 에이전트 상태 템플릿 스키마 일치 | PASS |
| 조건 거부 party_size=0 | PASS |
| 조건 거부 party_size=7 | PASS |
| 조건 거부 confirmed=False | PASS |
| 소수 금액 스키마 거부 | PASS |
| 0원 예산 스키마 거부 | PASS |
| 예산 예시 산술 | PASS |
| 인수 사례 49개 고유 ID | PASS |
| 자연어 사례 30개 고유 ID | PASS |
| 앱 검증은 미실행 상태 유지 | PASS |
| 필수 인계 파일 존재 | PASS |
| 문서에 내부 도구 인용 토큰 없음 | PASS |

앱 테스트와 작업 상태는 NOT_RUN / NOT_STARTED로 유지했습니다. 이 보고서의 PASS를 제품 테스트 통과로 전용하지 마십시오.
