# 프론트엔드 HTML 구조

이 폴더는 React 화면을 구현할 때 공유하는 HTML/DOM 구조 문서와 정적 골격이다. 실제 브라우저 렌더링은 `frontend/src/App.tsx`가 상태를 조정하고, 아래 컴포넌트가 마크업을 렌더링한다.

## 구조 원칙

- `AppLayout.tsx`: 모든 화면에 공통인 `<header>`, DEMO 안내, 단계 내비게이션, 제목·알림, `<footer>`를 담당한다.
- `Screens.tsx`: 3단계 시연 동선 안의 세부 상태와 카드·폼·표를 담당한다.
- `App.tsx`: API 호출·화면 전환·저장/비교 상태만 담당한다. 화면 마크업을 직접 추가하지 않는다.
- `styles.css`: 위 구조의 클래스와 반응형 레이아웃을 담당한다.

## DOM 트리

```text
div.app-shell
├─ a.skip-link
├─ header.topbar
│  ├─ button.brand
│  └─ div.top-meta[aria-label="실행 상태"]
├─ main.page-wrap
│  ├─ div.demo-banner[role="note"]
│  ├─ nav.stepper[aria-label="진행 단계"]
│  ├─ section.page-heading
│  ├─ div.alert.error[role="alert"]?        # 오류가 있을 때만
│  ├─ div.alert.notice[role="status"]?      # 안내가 있을 때만
│  └─ section.screen
│     ├─ 1단계 입력·조건: section.hero-grid / section.content-grid
│     │  ├─ div.hero-card: textarea#query + 분석 버튼
│     │  └─ aside.side-stack: 작동 방식·예시 문장
│     │  ├─ div.form-card: 조건 폼·분석 메모·추천 버튼
│     │  └─ aside.side-stack: 확인 필요 값·원문
│     ├─ 2단계 추천: section.results-workspace
│     │  ├─ div.results-main: 정렬·추천 카드·경고
│     │  │  └─ article.recommendation-card × 최대 5
│     │  └─ aside.results-aside: 지도 대기 상태·비교 패널
│     └─ 3단계 근거·예산: section.detail-section / section.budget-section
│     │  ├─ div.detail-header: 장소 제목·저장·비교
│        ├─ div.detail-grid: 개별 메뉴 가격 카드·근거 카드
│     │  └─ div.detail-card.table-card: 8주 상권 표
│        ├─ div.budget-intro: 확정 총예산
│        ├─ div.budget-grid
│        │  └─ article.budget-card × 최대 3
│        └─ div.saved-card: 저장 목록·전체 삭제
└─ footer.footer
```

## 파일 매핑

| 영역 | 구현 파일 | 주요 계약 |
|---|---|---|
| 문서 골격 | `app-shell.html` | 공통 시맨틱 구조와 placeholder |
| 공통 레이아웃 | `src/ui/AppLayout.tsx` | `Meta`, `Screen` |
| 3단계 시연 마크업 | `src/ui/Screens.tsx` | `src/types.ts`의 화면 모델 |
| 상태·API 연결 | `src/App.tsx` | `src/api/client.ts` |
| 스타일 | `src/styles.css` | 클래스 기반 레이아웃 |

정적 `app-shell.html`은 브라우저에 직접 배포하는 별도 앱이 아니라, React JSX를 검토·협업할 때 사용하는 구조 기준표다.
