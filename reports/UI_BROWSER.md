# 브라우저 UI 검수 보고서

확인일: 2026-09-19

상태: `PASS_WITH_FOLLOWUPS`

## 실행 환경

- 백엔드·프런트: `.venv\Scripts\python.exe scripts/dev.py --seed --host 127.0.0.1 --port 8000`
- 프런트: Vite `7.1.5`, `http://127.0.0.1:5173/`
- 브라우저: Playwright CLI headed session `sobi-v21`
- 캡처: `output/playwright/home-v21-360-fixed.png`, `output/playwright/home-v21-1280-fixed.png`

## 실제 흐름

1. S01 빈 입력으로 실행해 `role=alert` 오류를 확인했다.
2. 예시 문장을 선택해 실제 `POST /api/parse-query`로 S02 초안을 받았다.
3. 확정 조건으로 실제 `POST /api/recommendations`를 호출해 서버 순서의 5개 카드를 확인했다.
4. S03에서 최대 3개를 선택하고 지도 대기 상태·비교 패널·비합산 안내를 확인했다.
5. S05에서 실제 `POST /api/budget/estimate` 응답의 총예산 40,000원과 대안별 비용·잔여금액을 확인했다.
6. 당시 장소 상세에서 실제 `GET /api/places/{id}`의 가격 구성, 출처 ID, 근거 3건, 합성 상권 집계를 확인했다. 최신 v3.2 표시는 `V32_BROWSER.md`를 우선한다.
7. 저장 버튼으로 native origin `localStorage`에 장소 ID·스냅샷·시각만 기록되고, 새로고침 후 값이 남는 것을 확인했다.

## 반응형·접근성

| 뷰포트 | 결과 |
|---|---|
| 360×800 | 가로 넘침 없음 |
| 390×800 | 가로 넘침 없음 |
| 768×900 | 가로 넘침 없음 |
| 1280×900 | 가로 넘침 없음 |

`document.documentElement.scrollWidth`와 `document.body.scrollWidth`가 각 viewport의 `innerWidth`보다 크지 않았다. 본문 건너뛰기 링크, 명시적 label, 오류/상태 영역, 3px 포커스 링을 확인했다. 콘솔은 Errors 0 / Warnings 0이며 React DevTools 안내 info만 있었다.

## 범위 한계

실제 Gemini 호출·지도·실데이터와 스크린리더/확대 조합의 수동 검수는 `NOT_RUN`이다. 좌표가 없는 demo에서 지도 핀·경로·사진을 만들지 않고 상태를 표시한 것은 의도된 계약 동작이다.
