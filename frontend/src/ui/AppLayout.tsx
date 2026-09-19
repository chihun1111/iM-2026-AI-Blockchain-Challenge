import type { ReactNode } from "react";
import type { Meta } from "../types";
import { type Screen } from "./types";

interface AppLayoutProps {
  meta: Meta | null;
  screen: Screen;
  screenTitle: string;
  busy: boolean;
  error: string | null;
  notice: string | null;
  availableScreens: Screen[];
  onHome: () => void;
  onScreenChange: (screen: Screen) => void;
  onRefreshMeta: () => void;
  onClearError: () => void;
  onClearNotice: () => void;
  children: ReactNode;
}

export function AppLayout({
  meta,
  screen,
  screenTitle,
  busy,
  error,
  notice,
  availableScreens,
  onHome,
  onScreenChange,
  onRefreshMeta,
  onClearError,
  onClearNotice,
  children,
}: AppLayoutProps) {
  const phases: Array<{ label: string; screens: Screen[]; target: Screen }> = [
    {
      label: "입력·조건",
      screens: ["home", "conditions"],
      target: availableScreens.includes("conditions") ? "conditions" : "home",
    },
    { label: "추천", screens: ["results"], target: "results" },
    {
      label: "근거·예산",
      screens: ["place", "budget"],
      target: availableScreens.includes("budget") ? "budget" : "place",
    },
  ];

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">본문으로 건너뛰기</a>
      <header className="topbar">
        <button className="brand" onClick={onHome} aria-label="소비나침반 첫 화면으로 이동">
          <span className="brand-mark" aria-hidden="true">↗</span>
          <span>소비나침반</span>
        </button>
        <div className="top-meta" aria-label="실행 상태">
          <span className="mode-badge">{meta?.data_mode === "demo" ? "DEMO" : meta?.data_mode || "연결 중"}</span>
          <span>{meta ? `기준 ${meta.reference_now.replace("T", " ").slice(0, 16)}` : "API 확인 중"}</span>
        </div>
      </header>

      <main id="main-content" className="page-wrap">
        {meta?.data_mode === "demo" ? (
          <div className="demo-banner" role="note">
            <strong>시연용 가상 데이터</strong>
            <span>실제 매장·카드매출·실시간 혼잡·지도 데이터가 아닙니다.</span>
            <span className="banner-detail">정책 {meta.policy_version} · 스냅샷 {meta.snapshot_id}</span>
          </div>
        ) : (
          <div className="demo-banner" role="note">
            <strong>{meta ? "연결된 데이터 모드" : "데이터 연결 확인 중"}</strong>
            <span>{meta ? "화면의 출처·기준일·집계 단위를 확인해 주세요." : "API 상태를 확인하고 있습니다."}</span>
            {meta && <span className="banner-detail">정책 {meta.policy_version} · 스냅샷 {meta.snapshot_id}</span>}
          </div>
        )}

        <nav className="stepper" aria-label="진행 단계">
          {phases.map((phase, index) => {
            const active = phase.screens.includes(screen);
            const enabled = phase.screens.some((item) => availableScreens.includes(item));
            return (
              <button
                key={phase.label}
                className={active ? "step active" : "step"}
                onClick={() => onScreenChange(phase.target)}
                disabled={!enabled}
                aria-current={active ? "step" : undefined}
              >
                <span>{index + 1}</span>{phase.label}
              </button>
            );
          })}
        </nav>

        <section className="page-heading">
          <div>
            <p className="eyebrow">소비 결정을 위한 작은 기준표</p>
            <h1>{screenTitle}</h1>
          </div>
          <button className="text-button" onClick={onRefreshMeta} disabled={busy}>상태 새로고침</button>
        </section>

        {error && <div className="alert error" role="alert"><strong>확인이 필요합니다.</strong><span>{error}</span><button className="icon-button" onClick={onClearError} aria-label="오류 닫기">×</button></div>}
        {notice && <div className="alert notice" role="status"><span>{notice}</span><button className="icon-button" onClick={onClearNotice} aria-label="알림 닫기">×</button></div>}

        {children}
      </main>

      <footer className="footer"><span>규칙 기반 조건 분석 · 템플릿 설명 · 지도 연결 안 됨</span><span>외부 AI는 사용자가 승인한 뒤 서버에서만 연결합니다.</span></footer>
    </div>
  );
}
