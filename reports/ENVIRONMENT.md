# 실행 환경

확인일: 2026-09-19

## 확인된 환경

| 항목 | 값 |
|---|---|
| OS / 셸 | Windows / PowerShell |
| 작업 경로 | `D:\work\Sobi\소비나침반_에이전트_패키지_v2.0` |
| Python | 3.12.14 |
| Node.js / npm | v24.19.0 / npm bundled 확인. Vite 프런트엔드 빌드·브라우저 검수에 사용 |
| Git | 작업 폴더가 Git 저장소가 아님 |
| 기본 DB | `var/consumer_compass_demo.db` |
| 바인딩 | `127.0.0.1` 전용 개발 서버 |

## Python 의존성

`requirements.txt`를 기준으로 생성했고, 실제 설치 결과는 `requirements.lock`에 고정했습니다.

- FastAPI 0.116.1
- Uvicorn 0.35.0
- HTTPX 0.28.1
- pytest 8.4.1
- jsonschema 4.25.1
- Pydantic 2.13.5

## 프런트엔드 의존성

- React 19.1.1 / ReactDOM 19.1.1
- Vite 7.1.5
- TypeScript 5.9.2

## 권한과 외부 호출

- `GEMINI_API_KEY`, `LLM_API_KEY`, 지도 키의 값은 읽거나 기록하지 않았습니다. 현재 환경에서 존재하지 않음을 확인했습니다.
- 기본 `ALLOW_EXTERNAL_CALLS=false`로 외부 호출은 실행하지 않았습니다.
- 실제 공개 배포·원격 push·유료 호출은 실행하지 않았습니다.
