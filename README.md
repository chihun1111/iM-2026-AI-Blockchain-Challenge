# 소비나침반 프로토타입 v3.2

> 동성로·중앙로역 일대 / 한식 음식점 3개 후보의 검증 메뉴 API와 승인 기반 Gemini 연결 준비에 집중한다. 제출 서류·접수는 사용자 담당이다. 필요한 실제 입력은 `USER_ACTIONS.md`, 계약은 `contracts/`, 데이터 형식은 `data/real/README.md`에 있다.

팀 기적의 인큐4 | 2026.09.19 | 기본 실행은 합성 demo, 목표는 검증 실데이터 프로토타입

백엔드 6개 API, demo SQLite, 규칙 파서, 검증 메뉴/필수비용 계산, 3단계 React 흐름과 Gemini 실행 게이트가 구현되어 있다. S04 2026-06 공공 점포 원본에서 3곳의 점포·한식 업종 매칭은 완료했다. 실제 현재 메뉴와 승인 카드 집계가 없으므로 현재 화면은 합성 demo다. Gemini 승인안도 미승인이고 실제 호출은 없다.

## 사용하는 방법

새 프로젝트 폴더에 압축을 푼 뒤 개발 에이전트에게 `START_AGENT_PROMPT.md` 내용을 전달합니다. 기존 저장소에 넣는 경우 기존 `AGENTS.md`, `README.md`, `.env.example` 등의 파일을 덮어쓰지 말고 별도 `handoff/` 폴더에 보관하여 경로를 명시합니다. 기존 AGENTS와 충돌하는 정책은 자동으로 덮어쓰지 않습니다.

에이전트는 AGENTS → SPEC → TASKS → 정책·스키마 → 검수 기준 순서로 읽습니다. Word 문서는 사람이 검토하기 위한 같은 설계의 판본입니다. 세부 실행 규칙은 `AGENTS.md`, 기계 판독 가능한 값은 `config/policy.v2.json`과 `schemas/`를 사용하되 내용이 충돌하면 임의 선택하지 않고 보고해야 합니다.

## 핵심 파일

| 파일 | 역할 |
|---|---|
| `START_AGENT_PROMPT.md` | 최초 실행 시 그대로 전달할 지시문 |
| `AGENTS.md` | 권한 경계, 중단, 제한된 수정, 진행 보고, 재개 규칙 |
| `SPEC.md` | 화면·데이터·예산·추천·API·품질 명세 |
| `TASKS.md` | T00~T08 필수 작업과 X01~X03 선택 연동 |
| `config/policy.v2.json` | v3.2 실행 범위·모드·검증 정책(호환 파일명 유지) |
| `schemas/` / `examples/` | 확정 조건·에이전트 상태 스키마와 API 예시 |
| `frontend/structure/` | React 화면의 HTML/DOM 구조 기준과 정적 골격 |
| `contracts/` | 프론트–백엔드 계약서·OpenAPI·대표 JSON 예시 |
| `design/` | v2.1 디자인 명세와 제공 미리보기 연결 파일 |
| `data/demo/` | 실제 자료가 아닌 회귀 테스트용 합성 데이터 |
| `data/real/data_candidates.json` | S04와 매칭된 3개 장소·7개 공개 가격 참조 후보와 미확보 메뉴 검증 필드 |
| `tests/` | 인수 사례와 자연어 평가 30문장 |
| `AGENT_STATUS.json` | v3.2 진행 상태와 실자료 재개 위치 |
| `BLOCKERS.md` / `DECISIONS.md` | 문제·미확보 정보와 범위 결정 |
| `templates/` | 중단·종료·재개 보고 형식 |
| `.env.example` | 비밀값을 포함하지 않는 설정 예시 |
| `REFERENCES.md` | 외부 기술·데이터 공식 참고자료 |

## 외부 키가 없을 때

P0는 외부 AI·지도·실데이터 없이 실행하도록 구현합니다. UI에는 규칙 기반 분석, 가상 데이터, 고정 시연 시각을 명확히 표시합니다. 이것을 실제 AI·실제 금융 데이터 서비스 완료로 보고하지 않습니다. X01~X03은 관련 계정·권한·자료·승인이 확보되기 전에는 미연동입니다.

현재 `BLOCKERS.md`의 실제 메뉴·카드 집계/권한·Gemini 승인 항목은 확인된 미확보 상태다. 공공 점포 원본 매칭은 완료됐지만 공식 상권 경계는 선언하지 않았고, 전체 실제 연동 완료로 간주하지 않는다.

## 현재 구현 범위

### 실행 환경 설치

Windows PowerShell 기준입니다.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock
.venv\Scripts\python.exe scripts/seed_demo.py
```

번들 Python 3.12 런타임을 사용하는 경우에도 같은 명령에서 `py -3.12` 대신 해당 Python 실행 파일을 지정할 수 있습니다.

### API 서버

```powershell
.venv\Scripts\python.exe scripts/dev.py --seed
```

이 명령은 백엔드 API(`127.0.0.1:8000`)와 프런트엔드(`127.0.0.1:5173`)를 함께 시작합니다. API만 실행하려면 `--no-web`을 붙입니다. OpenAPI 문서는 다음 명령으로 생성합니다.

```powershell
.venv\Scripts\python.exe scripts/export_openapi.py
```

현재 제공하는 API는 다음 6개입니다. 실제 데이터는 `scripts/import_real_data.py`가 별도 real DB에 반입하며, 개별 메뉴 가격과 최소 주문 수량은 서버 계산에 사용됩니다.

| 메서드 | 경로 | 역할 |
|---|---|---|
| GET | `/api/health` | 설정·DB·활성 스냅샷·선택 어댑터 상태 |
| GET | `/api/meta` | 지원 범위·모드·기준시각·정책·스냅샷 |
| POST | `/api/parse-query` | 규칙 기반 조건 초안과 확인 필요 필드 |
| POST | `/api/recommendations` | 서버 계산 예산 필터·추천·근거 |
| GET | `/api/places/{place_id}?snapshot_id=...` | 장소·검증 메뉴·과거 상권 참고 근거 |
| POST | `/api/budget/estimate` | 최대 3개 대안의 개별 예산 계산 |

서버는 클라이언트가 보낸 가격을 신뢰하지 않고 `place_id`와 스냅샷의 가격을 다시 계산합니다. 데모 데이터에는 `is_mock=true`와 가상 데이터 경고가 유지됩니다. 프론트–백엔드 계약의 한 곳짜리 인계본은 `contracts/`에서 확인합니다.

### React 화면

개발 서버 명령은 백엔드와 Vite 프런트엔드를 함께 시작합니다. 브라우저에서 `http://127.0.0.1:5173/`을 열면 다음 흐름을 사용할 수 있습니다.

1. 입력·조건: 짧은 문장 분석과 누락값 수동 확인
2. 추천: 검증 메뉴·예산·목적으로 최대 3개 대안 비교
3. 근거·예산: 메뉴별 수량·필수비용과 실제 관측 기간의 상권 참고 근거

실제 지도는 연결하지 않고, 저장소에는 장소 ID·스냅샷 ID·저장 시각만 기록합니다. v2.1의 목록·상태·비교 패널 구조는 `frontend/src/ui/Screens.tsx`에 반영했고, 디자인 기준은 `design/DESIGN_SPEC.md`에 정리했습니다. 브라우저 검수 결과는 `reports/UI_BROWSER.md`와 `output/playwright/`에 남깁니다.

### Gemini 연결 준비

현재 기본값은 `PARSER_MODE=rules`, `ALLOW_EXTERNAL_CALLS=false`입니다. 실제 Gemini 호출을 시작할 때만 서버의 비공개 환경에 다음 값을 설정합니다. 키를 채팅·프런트엔드 `VITE_` 변수·소스·로그에 넣지 않습니다.

```text
PARSER_MODE=gemini
LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_API_KEY=<비공개 서버 환경변수>
ALLOW_EXTERNAL_CALLS=true
ALLOW_PAID_CALLS=true
```

`backend/app/adapters/gemini.py`는 `x-goog-api-key` 서버 헤더와 구조화 JSON을 사용한다. 호출하려면 `config/gemini_approval_plan.json`의 데이터 API gate·승인자·시각·모델·전송 범위·총/일 한도, 두 실행 스위치, 서버 `GEMINI_API_KEY`, 요청별 전송 동의가 모두 필요하다. 앱은 `GOOGLE_API_KEY`를 사용하지 않는다. 호출 전 최대 비용을 예약하고, 재시도와 사용량 불명 실패를 보수적으로 합산한다.

환경변수를 서버에 설정한 뒤에는 다음 명령으로 키·헤더·원문을 출력하지 않는 직접 연결 스모크 검사를 실행할 수 있습니다. 키를 명령행 인자로 전달하지 않습니다.

```powershell
.venv\Scripts\python.exe scripts\verify_gemini.py --require-configured
```

### 검증

```powershell
.venv\Scripts\python.exe scripts/verify.py --all
```

이 명령은 v3.2 후보/승인 준비도, demo 원본 해시·행 수, 자연어 사례, 백엔드 계약 테스트, OpenAPI 생성, 프런트엔드 빌드를 순서대로 실행한다. 실제 Gemini 호출은 포함하지 않는다.

로컬에 보관한 S04 원본 ZIP과 3개 점포 매칭은 별도로 검증한다.

```powershell
.venv\Scripts\python.exe scripts\verify_s04_matches.py
```

실행 중인 서버의 실제 HTTP/CORS·계산·오류 envelope는 별도로 확인합니다.

```powershell
.venv\Scripts\python.exe scripts/verify_http.py
```

## 검증 결과의 범위

합성 fixture 기준 API 계약과 프런트 빌드는 통과했고 S04 점포 매칭도 원본으로 검증했다. 실제 메뉴·카드 집계/권한 및 Gemini 실호출은 미완료다. `reports/FINAL_REPORT.md`, `BLOCKERS.md`, `USER_ACTIONS.md`에 필요한 정확한 필드와 재개 순서를 기록했다.

# iM-2026-AI-Blockchain-Challenge
