import { useState } from "react";
import type {
  Atmosphere,
  BudgetResult,
  ConditionForm,
  ParseResult,
  PlaceResult,
  RecommendationItem,
  RecommendationResult,
  SavedPlace,
} from "../types";
import { atmosphereOptions, label, money, moneyRange } from "./presentation";

export function HomeScreen({
  rawText,
  setRawText,
  busy,
  parse,
  externalAiEnabled,
  externalAiConsent,
  setExternalAiConsent,
}: {
  rawText: string;
  setRawText: (value: string) => void;
  busy: boolean;
  parse: () => Promise<void>;
  externalAiEnabled: boolean;
  externalAiConsent: boolean;
  setExternalAiConsent: (value: boolean) => void;
}) {
  const examples = [
    "동성로 2명 인당 2만원 저녁 7시 식사",
    "동성로 두 명 총 4만원 내일 저녁 7시 한식",
    "동성로 혼자 총 1만원 혼밥하기 좋은 한식당",
  ];
  return (
    <section className="hero-grid" aria-labelledby="home-title">
      <div className="hero-card">
        <div className="hero-icon" aria-hidden="true">◎</div>
        <p className="eyebrow">1단계 · 입력과 조건 확인</p>
        <h2 id="home-title">이번 소비의 기준을<br />자연스럽게 적어 주세요.</h2>
        <p>예산·목적·인원·방문 시각을 읽고, 확인이 필요한 값은 먼저 보여 드립니다.</p>
        <label htmlFor="query">검색 문장</label>
        <textarea
          id="query"
          value={rawText}
          onChange={(event) => setRawText(event.target.value)}
          maxLength={500}
          rows={5}
          placeholder="예: 동성로에서 친구랑 저녁 먹을 건데 인당 2만원 안 넘는 곳"
        />
        <div className="field-hint"><span>최대 500자</span><span>{rawText.length}/500</span></div>
        {externalAiEnabled ? (
          <label className="compare-check">
            <input
              type="checkbox"
              checked={externalAiConsent}
              onChange={(event) => setExternalAiConsent(event.target.checked)}
            />
            식별정보 없는 이 문장만 Gemini에 보내 조건 JSON을 추출하는 데 동의합니다.
          </label>
        ) : (
          <p className="small-note">Gemini는 승인 전이며 현재 입력은 외부 AI로 전송되지 않습니다.</p>
        )}
        <button className="primary-button wide" onClick={() => void parse()} disabled={busy}>
          {busy ? "조건을 읽는 중…" : "조건 분석하기"}
        </button>
      </div>
      <aside className="side-stack" aria-label="사용 안내">
        <div className="info-card">
          <p className="eyebrow">이렇게 작동합니다</p>
          <ol>
            <li><b>조건 확인</b><span>추정·누락 값을 직접 확인</span></li>
            <li><b>추천 비교</b><span>검증 가격 계산, 영업 정보는 확인된 경우만 사용</span></li>
            <li><b>근거 확인</b><span>가격·기간·상권 집계를 분리해 표시</span></li>
          </ol>
        </div>
        <div className="info-card">
          <p className="eyebrow">예시 문장</p>
          {examples.map((example) => (
            <button key={example} className="example-button" onClick={() => setRawText(example)}>
              {example}<span aria-hidden="true">↗</span>
            </button>
          ))}
        </div>
      </aside>
    </section>
  );
}

export function ConditionsScreen({
  form,
  setForm,
  parseResult,
  busy,
  recommend,
}: {
  form: ConditionForm;
  setForm: (value: ConditionForm) => void;
  parseResult: ParseResult;
  busy: boolean;
  recommend: () => Promise<void>;
}) {
  const update = <K extends keyof ConditionForm>(key: K, value: ConditionForm[K]) => setForm({ ...form, [key]: value });
  const isFilled = (key: string) => {
    const value = form[key as keyof ConditionForm];
    return Array.isArray(value) ? value.length > 0 : value !== "" && value !== null && value !== undefined;
  };
  const pendingConfirmation = parseResult.confirmation_required.filter((key) => !isFilled(key));
  const metaOrigin = (key: string, origin: string) => origin === "missing" && isFilled(key) ? "explicit" : origin;
  const toggleAtmosphere = (value: Atmosphere, required: boolean) => {
    if (required) {
      const nextRequired = form.required_atmosphere.includes(value)
        ? form.required_atmosphere.filter((item) => item !== value)
        : [...form.required_atmosphere, value];
      const nextPreferences = form.atmosphere_preferences.includes(value)
        ? form.atmosphere_preferences
        : [...form.atmosphere_preferences, value];
      setForm({ ...form, atmosphere_preferences: nextPreferences, required_atmosphere: nextRequired });
      return;
    }
    const nextPreferences = form.atmosphere_preferences.includes(value)
      ? form.atmosphere_preferences.filter((item) => item !== value)
      : [...form.atmosphere_preferences, value];
    setForm({
      ...form,
      atmosphere_preferences: nextPreferences,
      required_atmosphere: nextPreferences.includes(value)
        ? form.required_atmosphere
        : form.required_atmosphere.filter((item) => item !== value),
    });
  };
  return (
    <section className="content-grid" aria-labelledby="conditions-title">
      <div className="form-card">
        <div className="form-intro">
          <div><p className="eyebrow">1단계 · 입력과 조건 확인</p><h2 id="conditions-title">입력한 조건을 고쳐도 괜찮아요.</h2></div>
          <span className="parser-pill">{parseResult.parser_mode === "rules" ? "규칙 파서" : "Gemini 초안"}</span>
        </div>
        <div className="field-grid">
          <label htmlFor="region">지역<select id="region" value={form.region_id} onChange={(event) => update("region_id", event.target.value as ConditionForm["region_id"])}><option value="">선택해 주세요</option><option value="dongseongro">동성로·중앙로역 일대</option></select></label>
          <label htmlFor="category">업종<select id="category" value={form.category} onChange={(event) => update("category", event.target.value as ConditionForm["category"])}><option value="">선택해 주세요</option><option value="restaurant">한식 음식점</option></select></label>
          <label htmlFor="purpose">목적<select id="purpose" value={form.purpose} onChange={(event) => update("purpose", event.target.value as ConditionForm["purpose"])}><option value="">선택해 주세요</option><option value="meal">식사</option><option value="date">데이트</option><option value="friends">친구 모임</option></select></label>
          <label htmlFor="party-size">확정 인원<input id="party-size" type="number" min="1" max="6" value={form.party_size} onChange={(event) => update("party_size", event.target.value)} placeholder="1~6명" /></label>
          <label htmlFor="budget-type">예산 단위<select id="budget-type" value={form.budget_type} onChange={(event) => update("budget_type", event.target.value as ConditionForm["budget_type"])}><option value="">선택해 주세요</option><option value="per_person">1인 기준</option><option value="total">전체 기준</option></select></label>
          <label htmlFor="budget-amount">예산 금액<input id="budget-amount" type="number" min="1" max="10000000" value={form.budget_amount} onChange={(event) => update("budget_amount", event.target.value)} placeholder="원화 정수" /></label>
          <label htmlFor="visit-at">방문 날짜와 시각<input id="visit-at" type="datetime-local" value={form.visit_at} onChange={(event) => update("visit_at", event.target.value)} /></label>
          <label htmlFor="priority-profile">정렬 기준<select id="priority-profile" value={form.priority_profile} onChange={(event) => update("priority_profile", event.target.value as ConditionForm["priority_profile"])}><option value="balanced">검증 메뉴·예산·목적</option></select></label>
        </div>
        <fieldset><legend>선호 분위기</legend><div className="check-grid">{atmosphereOptions.map((item) => <label className="check-label" key={item}><input type="checkbox" checked={form.atmosphere_preferences.includes(item)} onChange={() => toggleAtmosphere(item, false)} />{label(item)}</label>)}</div></fieldset>
        <fieldset><legend>반드시 필요한 분위기</legend><div className="check-grid">{atmosphereOptions.map((item) => <label className="check-label" key={item}><input type="checkbox" checked={form.required_atmosphere.includes(item)} onChange={() => toggleAtmosphere(item, true)} />{label(item)}</label>)}</div><p className="field-hint">필수 분위기를 고르면 선호 분위기에도 함께 포함됩니다.</p></fieldset>
        <div className="condition-summary"><b>분석 메모</b><div>{Object.entries(parseResult.field_meta).map(([key, value]) => { const origin = metaOrigin(key, value.origin); return <span className={`meta-chip ${origin}`} key={key}>{key} · {origin === "inferred" ? "추정" : origin === "explicit" ? "입력" : origin === "default" ? "기본값" : "확인 필요"}</span>; })}</div></div>
        <button className="primary-button wide" onClick={() => void recommend()} disabled={busy}>{busy ? "추천을 계산하는 중…" : "이 조건으로 추천 보기"}</button>
      </div>
      <aside className="side-stack" aria-label="조건 확인 보조 정보">
        <div className="info-card"><p className="eyebrow">확인이 필요한 값</p>{pendingConfirmation.length ? <ul className="plain-list">{pendingConfirmation.map((item) => <li key={item}>{item}</li>)}</ul> : <p>모든 핵심 조건이 입력되었습니다.</p>}<p className="small-note">확정 전에는 추천을 요청하지 않습니다.</p></div>
        <div className="info-card"><p className="eyebrow">계약 경계</p><p className="quoted">초안은 참고용이고, 금액·순위·추천은 확정된 조건으로 서버가 계산합니다.</p></div>
      </aside>
    </section>
  );
}

export function ResultsScreen({
  result,
  selected,
  toggleCompare,
  openPlace,
  openBudget,
}: {
  result: RecommendationResult;
  selected: string[];
  toggleCompare: (id: string) => void;
  openPlace: (id: string) => Promise<void>;
  openBudget: () => Promise<void>;
}) {
  const [sort, setSort] = useState<"recommend" | "price">("recommend");
  const items = [...result.items].sort((a, b) => sort === "price"
    ? (a.cost_max ?? Number.POSITIVE_INFINITY) - (b.cost_max ?? Number.POSITIVE_INFINITY) || a.place_id.localeCompare(b.place_id)
    : 0);
  const selectedItems = result.items.filter((item) => selected.includes(item.place_id));
  return (
    <section className="results-workspace" aria-labelledby="results-title">
      <div className="results-main">
        <div className="result-toolbar">
          <div><p className="eyebrow">2단계 · 최대 3개 추천</p><p id="results-title" className="result-count">추천 <b>{result.items.length}곳</b><span> · 비교 선택 {selected.length}/3</span></p></div>
          <div className="toolbar-actions"><label className="sr-only" htmlFor="result-sort">정렬 기준</label><select id="result-sort" value={sort} onChange={(event) => setSort(event.target.value as typeof sort)}><option value="recommend">추천순</option><option value="price">예상 상한 낮은 순</option></select><button className="secondary-button" onClick={() => void openBudget()} disabled={!selected.length}>예산 비교 열기</button></div>
        </div>
        {result.items.length ? <div className="recommendation-grid">{items.map((item, index) => <RecommendationCard key={item.place_id} item={item} rank={index + 1} selected={selected.includes(item.place_id)} toggleCompare={toggleCompare} openPlace={openPlace} />)}</div> : <div className="empty-state"><h2>조건에 맞는 후보가 없습니다.</h2><p>지역·예산·필수 분위기를 자동으로 완화하지 않았습니다. 조건 확인으로 돌아가 직접 수정해 주세요.</p></div>}
        {result.insufficient_data_items.length > 0 && <details className="insufficient"><summary>정보 부족으로 분리된 후보 {result.insufficient_data_items.length}개</summary>{result.insufficient_data_items.map((item) => <p key={item.place_id}><b>{item.name}</b> · 가격 또는 상권 근거 부족으로 분리했습니다. <small>{item.data_status_reason || "DATA_INSUFFICIENT"}</small></p>)}</details>}
        <div className="warning-list">{result.warnings.map((warning) => <span key={warning}>ⓘ {warning}</span>)}</div>
      </div>
      <aside className="results-aside" aria-label="추천 상태와 비교">
        <section className="map-panel">
          <div className="panel-heading"><div><p className="eyebrow">탐색 상태</p><h2>목록과 근거를 한눈에</h2></div><span className="status-tag unknown">지도 대기</span></div>
          <div className="map-empty"><span className="map-symbol" aria-hidden="true">⌖</span><strong>지도를 연결할 수 없습니다</strong><p>현재 서버 응답에는 좌표가 없어 목록과 근거 중심으로 보여 드립니다.</p></div>
          <p className="map-disclaimer">가상 좌표·핀·경로를 만들지 않습니다.</p>
        </section>
        <section className="compare-panel">
          <div className="panel-heading"><div><p className="eyebrow">선택한 대안</p><h2>예산 비교</h2></div><span className="compare-count">{selected.length}/3</span></div>
          <div className="compare-slots">{selectedItems.length ? selectedItems.map((item) => <button className="compare-slot" key={item.place_id} onClick={() => void openPlace(item.place_id)}><span className="place-symbol small" aria-hidden="true">{item.name.slice(-1)}</span><span><b>{item.name}</b><small>{moneyRange(item.cost_min, item.cost_max)}</small></span><span aria-hidden="true">↗</span></button>) : <p className="empty-copy">추천 카드에서 비교할 장소를 골라 주세요.</p>}</div>
          <button className="primary-button wide" onClick={() => void openBudget()} disabled={!selected.length}>선택 대안 비교하기</button>
          <p className="small-note">선택한 장소들의 비용을 합산하지 않고, 같은 확정 조건으로 각각 계산합니다.</p>
        </section>
      </aside>
    </section>
  );
}

function RecommendationCard({
  item,
  rank,
  selected,
  toggleCompare,
  openPlace,
}: {
  item: RecommendationItem;
  rank: number;
  selected: boolean;
  toggleCompare: (id: string) => void;
  openPlace: (id: string) => Promise<void>;
}) {
  const statusLabel = item.budget_status === "fits" ? "예산 상한 충족" : item.budget_status === "exceeds" ? "예산 초과" : "가격 확인 필요";
  return (
    <article className={`recommendation-card ${selected ? "selected" : ""}`}>
      <div className="card-topline"><span className="rank">{String(rank).padStart(2, "0")}</span><span className="mock-tag">{item.is_mock ? "가상 장소" : "검증 장소"}</span><span className={`status-tag ${item.budget_status}`}>{statusLabel}</span></div>
      <button className="card-title" onClick={() => void openPlace(item.place_id)}><span className="place-symbol" aria-hidden="true">{item.name.slice(-1)}</span><span className="title-text">{item.name}<small>{label(item.region_id)} · {label(item.category)} · {item.opening_status === "open" ? "방문 시각 영업" : "영업 확인 필요"}</small></span><span aria-hidden="true">↗</span></button>
      <div className="price-range"><span><small>1인 예상</small>{moneyRange(item.per_person_min, item.per_person_max)}</span><strong><small>확정 인원 예상</small>{moneyRange(item.cost_min, item.cost_max)}</strong></div>
      <div className="reason-list">{item.reasons.map((reason) => <span key={reason}>✓ {reason}</span>)}</div>
      <div className="card-meta"><span>가격 기준일 {item.data_as_of.price || "미확인"}</span><span>{item.evidence_ids.length}개 근거</span></div>
      <div className="card-footer"><label className="compare-check"><input type="checkbox" checked={selected} onChange={() => toggleCompare(item.place_id)} />비교에 추가</label><button className="text-button" onClick={() => void openPlace(item.place_id)}>근거 보기</button></div>
    </article>
  );
}

export function PlaceScreen({ place, saved, savePlace, toggleCompare, selected, back }: { place: PlaceResult | null; saved: SavedPlace[]; savePlace: (id: string) => void; toggleCompare: (id: string) => void; selected: string[]; back: () => void }) {
  if (!place) return <div className="loading-card"><span className="spinner" /> 장소 정보를 불러오는 중입니다.</div>;
  const isSaved = saved.some((item) => item.place_id === place.place.place_id);
  return (
    <section className="detail-section" aria-labelledby="place-title">
      <button className="back-button" onClick={back}>← 추천 목록으로</button>
      <div className="detail-header"><div className="detail-heading"><span className="detail-symbol" aria-hidden="true">{place.place.name.slice(-1)}</span><div><span className="mock-tag">{place.place.is_mock ? "가상 장소 · 실제 주소 없음" : "검증 장소"}</span><h2 id="place-title">{place.place.name}</h2><p>{label(place.place.region_id)} · {label(place.place.category)} · {place.place.area_id}</p><p className="small-note">{place.place.address_label} · {place.place.coordinates ? "서버 좌표 제공" : "좌표 미제공"}</p></div></div><div className="detail-actions"><button className="secondary-button" onClick={() => toggleCompare(place.place.place_id)}>{selected.includes(place.place.place_id) ? "비교에서 빼기" : "비교에 추가"}</button><button className="primary-button" onClick={() => savePlace(place.place.place_id)}>{isSaved ? "저장됨" : "저장"}</button></div></div>
      <div className="detail-grid"><div className="detail-card"><p className="eyebrow">가격 구성</p>{place.price ? <><div className="detail-price">{moneyRange(place.price.unit_min, place.price.unit_max)}<small> {place.price.label}</small></div>{(place.price.menu_items || []).length ? <ul className="evidence-list">{(place.price.menu_items || []).map((item) => <li key={item.menu_item_id}><b>{item.name}</b><span>{money(item.price_krw)} · {item.portion}{item.minimum_order > 1 ? ` · 최소 ${item.minimum_order}개` : ""} · 필수비용 {money(item.mandatory_cost)}</span><small>{item.confirmed_on} · {item.confirmed_by_role} 확인 · 출처 ID {item.source_id} · {item.is_budget_candidate ? "예산 계산 사용" : "참고 메뉴"}</small></li>)}</ul> : <p className="small-note">개별 메뉴 근거가 없는 가격 범위 데이터입니다.</p>}<p>확인된 필수 비용: {moneyRange(place.price.fixed_fee_min, place.price.fixed_fee_max)}</p><p className="small-note">제외: {place.price.excluded.join(", ")}</p><p className="small-note">가격 확인일 {place.price.observed_at} · 출처 ID {place.price.source_id}</p></> : <p>가격 정보를 확인할 수 없습니다.</p>}</div><div className="detail-card"><p className="eyebrow">근거와 범위</p>{place.evidence.length ? <ul className="evidence-list">{place.evidence.map((item) => <li key={item.evidence_id}><b>{item.claim_type}</b><span>{JSON.stringify(item.value)}</span><small>{item.observed_at} · {item.aggregation_unit || "장소 기준"} · 출처 ID {item.source_id} · {item.is_mock ? "가상" : "실제"}</small></li>)}</ul> : <p>확인된 근거가 없습니다.</p>}</div></div>
      <div className="detail-card table-card"><div className="table-heading"><div><p className="eyebrow">과거 상권 소비활동 참고</p><h3>점포 자체 매출이나 현재 인기·실시간 혼잡이 아닙니다.</h3></div><span className="small-note">{place.place.is_mock ? "합성 demo 지역·업종 집계" : "승인된 관측 기간의 지역·업종 집계"} · {place.area_timeseries.length}행</span></div><div className="table-scroll"><table><caption className="sr-only">과거 상권 소비활동 집계</caption><thead><tr><th>관측 기간</th><th>시간 단위</th><th>결제건수</th><th>관측 가맹점</th></tr></thead><tbody>{place.area_timeseries.map((row) => <tr key={row.metric_id}><td>{row.week_start}~{row.week_end}</td><td>{label(row.day_group)} · {label(row.time_bucket)}</td><td>{row.txn_count.toLocaleString()}</td><td>{row.merchant_count}</td></tr>)}</tbody></table></div></div><p className="warning-line">{place.warnings.join(" ")}</p>
    </section>
  );
}

export function BudgetScreen({ result, selected, saved, clearSaved, openPlace, back }: { result: BudgetResult | null; selected: string[]; saved: SavedPlace[]; clearSaved: () => void; openPlace: (id: string) => Promise<void>; back: () => void }) {
  return (
    <section className="budget-section" aria-labelledby="budget-title">
      <button className="back-button" onClick={back}>← 추천 목록으로</button>
      <div className="budget-intro"><div><p className="eyebrow">3단계 · 근거와 예산</p><h2 id="budget-title">각 장소를 선택했을 때의 예상 지출입니다.</h2><p>여러 장소의 금액을 합산하지 않고, 같은 조건으로 각각 다시 계산했습니다.</p></div>{result && <div className="budget-total"><span>확정 총예산</span><strong>{money(result.total_budget)}</strong><small>서버 계산 · {selected.length}개 대안</small></div>}</div>
      {result ? <div className="budget-grid">{result.items.map((item) => <article className="budget-card" key={item.place_id}><div className="card-topline"><span className="mock-tag">{item.is_mock ? "가상 계산" : "메뉴 계산"}</span><span className={`status-tag ${item.budget_status}`}>{item.budget_status === "fits" ? "예산 안" : item.budget_status === "exceeds" ? "예산 초과" : "확인 필요"}</span></div><button className="card-title" onClick={() => void openPlace(item.place_id)}><span className="place-symbol" aria-hidden="true">{item.place_id.slice(-1)}</span><span className="title-text">{item.place_id}<small>개별 대안 · {item.party_size}명</small></span><span aria-hidden="true">↗</span></button><div className="budget-numbers"><span>예상 비용<strong>{moneyRange(item.cost_min, item.cost_max)}</strong></span><span>잔여 금액<strong className={item.remaining_min != null && item.remaining_min < 0 ? "negative" : ""}>{moneyRange(item.remaining_min, item.remaining_max)}</strong></span></div>{(item.menu_calculations || []).length ? <ul className="plain-list">{(item.menu_calculations || []).map((calculation) => <li key={`${calculation.role}-${calculation.menu_item_id}`}>{calculation.role === "minimum" ? "최소" : calculation.role === "maximum" ? "최대" : "기준"} · {calculation.name} {money(calculation.unit_price)} × {calculation.quantity} + 필수비용 {money(calculation.mandatory_cost)} = {money(calculation.total_price)}</li>)}</ul> : <ul className="plain-list">{item.assumptions.map((assumption) => <li key={assumption}>{assumption}</li>)}</ul>}{item.reason_code && <p className="warning-line">계산 보류: {item.reason_code}</p>}<p className="small-note">가격 기준일 {item.observed_at || "미확인"} · 출처 ID {item.source_id || "미확인"}</p></article>)}</div> : <div className="empty-state"><h2>비교할 장소를 선택해 주세요.</h2><p>추천 목록에서 최대 3개를 선택할 수 있습니다.</p></div>}
      <div className="saved-card"><div><p className="eyebrow">저장 목록</p><h3>{saved.length}개 저장됨</h3><p className="small-note">장소 ID·스냅샷·저장 시각만 브라우저에 보관합니다.</p></div><button className="text-button danger" onClick={clearSaved} disabled={!saved.length}>전체 삭제</button></div>
    </section>
  );
}
