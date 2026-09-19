# 실제 데이터 입력 계약 v3.2

현재 상태는 일부 입력 대기다. `data_candidates.json`에는 S04 2026-06 원본의 3개 점포 매칭이 완료됐지만, 메뉴 7개는 공개 웹 가격 참조일 뿐 현재 검증 가격이 아니므로 아직 real DB에 반입할 수 없다. 공개 가격을 자동 승격하거나 누락값을 0으로 채우지 않는다.

## 고정 범위

- 동성로·중앙로역 일대 시범 상권
- 한식 음식점
- 후보 장소: 국일따로국밥, 개정 본점, 마산설렁탕

위 3곳은 프로젝트의 명시 목록이며 공모전 최소 개수 요건이 아니다. 공식 상권 경계·행정동 코드·반경은 데이터 사전과 원천 공간코드 확인 전에는 만들지 않는다.

## 후보 준비도 확인

```powershell
.venv\Scripts\python.exe scripts\check_v32_readiness.py
```

현재 명령은 S04 원본 확보·점포/한식 업종 매칭 완료, 메뉴 7개의 누락 필드, 미정 공간 결합 기준, 카드 실파일·사전·권한 상태를 정확히 출력하고 `importable=false`를 반환해야 정상이다.

S04 로컬 원본의 해시·행 수·정확 매칭을 다시 검사하려면 다음 명령을 사용한다. 원본 ZIP은 `data/real/raw/`에 두며 Git에 포함하지 않는다.

```powershell
.venv\Scripts\python.exe scripts\verify_s04_matches.py
```

## real 패키지 파일

- `sources.json`
- `areas.json`
- `places.json`
- `menu_items.json`
- `area_metrics.json`
- `manifest.json`

`manifest.json`의 `region_id`는 `dongseongro`, `category`는 `restaurant`만 허용한다. 원본 행 수와 SHA-256은 다음 명령으로 갱신한다.

```powershell
.venv\Scripts\python.exe scripts\build_real_manifest.py
```

## 검증 메뉴 필드

예산 후보 메뉴마다 다음 값이 필요하다.

| 필드 | 조건 |
|---|---|
| `menu_item_id`, `place_id`, `name`, `source_id` | 안정적인 내부 ID와 참조 |
| `price_krw` | 확인된 현재 가격, 양수 정수 |
| `pricing_unit` | 현재는 `per_person` |
| `portion` | 제공 단위 텍스트 |
| `minimum_order` | 확인된 최소 주문 수량, 양수 정수 |
| `mandatory_cost` | 확인된 필수비용. 확인된 0원만 `0`, 미확인은 허용하지 않음 |
| `confirmed_on` | ISO 8601 확인일/시각 |
| `confirmed_by_role` | 확인자 역할만 기록, 개인 연락처 금지 |
| `usage_basis` | 분석·화면 표시·제출 시연에 사용할 수 있는 근거 |
| `source_url` 또는 `evidence_file` | 둘 중 하나 필수. 파일은 이 폴더 내부 상대 경로 |
| `is_budget_candidate`, `is_mock` | 예산 사용 여부, 실제 자료는 `false` |

서버 계산식은 `price_krw × max(party_size, minimum_order) + mandatory_cost`다. 메뉴별 필수비용을 계산하며 서로 다른 메뉴의 최저 가격과 다른 메뉴의 필수비용을 섞지 않는다.

## 장소와 영업정보

S04 상가(상권)정보_20260630 대구 CSV에서 3곳의 점포 ID·주소·한식 업종·위경도를 상호/지점명+도로명주소로 매칭했다. 세 점포는 행정동 두 곳에 걸쳐 있으므로 이를 하나의 공식 상권 경계나 대표 행정동 코드로 바꾸지 않는다. `opening_hours_eligible_for_filter=false`이면 추천은 가능하지만 영업 상태는 `unknown`으로 표시하고 시간 필터에 사용하지 않는다. 영업시간을 검증했다는 근거가 있을 때만 `true`로 둔다.

## 과거 상권 소비활동

조건부 대상은 신한카드 `지역별매출및이용고객정보`다. 다음 항목을 받은 뒤에만 `area_metrics.json`으로 정규화한다.

- 실제 파일과 데이터 사전·코드표
- 대구 포함 범위, 공간코드, 한식 업종코드
- 실제 기간·시간 단위·금액/건수 단위
- 실측/추정 방식, 결측·비공개값 의미
- 분석, 결과 반출, 코드/데이터 ZIP, 화면·영상, 공개 웹 각각의 허용 범위

원본 열 이름이나 제공되지 않은 시간대를 만들지 않는다. 상권 집계는 세 점포의 공통 과거 참고 근거일 뿐 점포 순위, 개별 점포 매출, 단골 수, 현재 인기 또는 실시간 혼잡이 아니다. 카드 원본·집계는 Gemini에 보내지 않는다.

## 반입

```powershell
$env:DATA_MODE="real"
$env:DATA_DIR="data/real"
$env:DATABASE_URL="sqlite:///./var/consumer_compass_real.db"
.venv\Scripts\python.exe scripts\import_real_data.py --check
.venv\Scripts\python.exe scripts\import_real_data.py
```

현재 후보 파일만으로 위 반입 명령을 실행해 완료 처리하지 않는다. 검증 메뉴, S04 매칭, 상권 집계와 사용권이 모두 준비된 뒤 manifest를 만들고 검사한다.
