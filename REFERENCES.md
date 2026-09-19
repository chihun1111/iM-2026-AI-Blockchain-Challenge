# 공식 참고자료

확인일: 2026-09-19. 아래 자료는 해당 기술·데이터 항목에 대한 근거다. 프로젝트의 가중치·임계값·목표 수치·중단 정책은 자체 설계 결정이며 성능·법적 적합성을 외부 문서가 보증하지 않는다.

| ID | 공식 자료 | 확인한 적용 범위 |
|---|---|---|
| R1 | https://www.data.go.kr/data/15012005/openapi.do | 상가업소번호·상호·주소·업종·위경도 등 기초 상가 항목 |
| R2 | https://docs.pydantic.dev/latest/concepts/json_schema/ | 모델의 JSON Schema 계약. 현재 공식 문서 경로로 리디렉션될 수 있음 |
| R3 | https://fastapi.tiangolo.com/tutorial/testing/ | TestClient 기반 테스트 구성 |
| R4 | https://playwright.dev/docs/test-assertions | 브라우저 상태·요소 검증 |
| R5 | https://apis.map.kakao.com/web/guide/ | JavaScript 지도키·도메인 설정 |
| R6 | https://vite.dev/guide/env-and-mode | VITE_ 변수가 클라이언트에 노출된다는 점 |
| R7 | https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html | 최소 권한·입출력 검증·프롬프트 주입 대응 |
| R8 | https://ai.google.dev/api/generate-content | Gemini `models.generateContent` REST 경로, JSON 응답 설정, 서버 API 키 헤더 확인 |

실제 연동은 당일 제공기관 문서와 계정 권한을 다시 확인해야 한다. 데이터 사이트가 카드사를 출처로 적었다는 사실은 개별 가맹점 결제·개인 방문 데이터가 해당 API에 제공된다는 뜻이 아니다.
