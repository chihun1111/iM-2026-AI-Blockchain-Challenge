import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, api } from "./api/client";
import type { Category, ConditionForm, Conditions, Draft, Meta, ParseResult, PlaceResult, Purpose, Region, SavedPlace } from "./types";
import { AppLayout } from "./ui/AppLayout";
import { BudgetScreen, ConditionsScreen, HomeScreen, PlaceScreen, ResultsScreen } from "./ui/Screens";
import { type Screen } from "./ui/types";
import type { BudgetResult, RecommendationResult } from "./types";

const SAVED_KEY = "consumer-compass-saved-v2";

function toLocalDateTime(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 16);
  const parts = new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Seoul", dateStyle: "short", timeStyle: "short" }).formatToParts(date);
  const get = (type: string) => parts.find((part) => part.type === type)?.value || "";
  return `${get("year")}-${get("month")}-${get("day")}T${get("hour")}:${get("minute")}`;
}

function toKstIso(value: string): string {
  return `${value}:00+09:00`;
}

function formFromDraft(draft: Draft): ConditionForm {
  return {
    region_id: draft.region_id || "",
    category: draft.category || "",
    purpose: draft.purpose || "",
    party_size: draft.party_size?.toString() || "",
    budget_type: draft.budget.type || "",
    budget_amount: draft.budget.amount?.toString() || "",
    visit_at: toLocalDateTime(draft.visit_at),
    atmosphere_preferences: draft.atmosphere_preferences || [],
    required_atmosphere: draft.required_atmosphere || [],
    priority_profile: draft.priority_profile || "balanced",
  };
}

function conditionFromForm(form: ConditionForm): Conditions {
  return {
    schema_version: "2.0",
    region_id: form.region_id as Region,
    category: form.category as Category,
    purpose: form.purpose as Purpose,
    party_size: Number(form.party_size),
    budget: { type: form.budget_type as "per_person" | "total", amount: Number(form.budget_amount), currency: "KRW" },
    visit_at: toKstIso(form.visit_at),
    atmosphere_preferences: form.atmosphere_preferences,
    required_atmosphere: form.required_atmosphere,
    priority_profile: form.priority_profile,
    origin: null,
    radius_m: 2000,
    confirmed: true,
  };
}

function isSavedPlace(value: unknown): value is SavedPlace {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<SavedPlace>;
  return typeof item.place_id === "string" && typeof item.snapshot_id === "string" && typeof item.saved_at === "string";
}

function initialSaved(): SavedPlace[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(SAVED_KEY) || "[]") as SavedPlace[];
    return Array.isArray(parsed) ? parsed.filter(isSavedPlace).slice(0, 20) : [];
  } catch {
    return [];
  }
}

function saveToStorage(items: SavedPlace[]): boolean {
  try {
    localStorage.setItem(SAVED_KEY, JSON.stringify(items.slice(0, 20)));
    return true;
  } catch {
    return false;
  }
}

function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return error instanceof Error ? error.message : "요청을 처리하지 못했습니다.";
  const fields = error.fields
    .filter((field) => field.path || field.message)
    .map((field) => [field.path, field.message].filter(Boolean).join(" · "))
    .filter(Boolean);
  return fields.length ? `${error.message} (${fields.join(", ")})` : error.message;
}

function App() {
  const [screen, setScreen] = useState<Screen>("home");
  const [meta, setMeta] = useState<Meta | null>(null);
  const [rawText, setRawText] = useState("동성로에서 2명이 저녁 7시에 한식, 인당 2만원 이하");
  const [externalAiConsent, setExternalAiConsent] = useState(false);
  const [parseResult, setParseResult] = useState<ParseResult | null>(null);
  const [form, setForm] = useState<ConditionForm | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationResult | null>(null);
  const [place, setPlace] = useState<PlaceResult | null>(null);
  const [budget, setBudget] = useState<BudgetResult | null>(null);
  const [selectedPlaceIds, setSelectedPlaceIds] = useState<string[]>([]);
  const [saved, setSaved] = useState<SavedPlace[]>(initialSaved);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const requestVersion = useRef(0);

  const refreshMeta = useCallback(async () => {
    try {
      const result = await api.meta();
      setMeta(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "API 서버에 연결할 수 없습니다.");
    }
  }, []);

  useEffect(() => {
    void refreshMeta();
  }, [refreshMeta]);

  const execute = useCallback(async <T,>(job: () => Promise<T>, onSuccess: (value: T) => void) => {
    const version = ++requestVersion.current;
    setBusy(true);
    setError(null);
    try {
      const value = await job();
      if (version === requestVersion.current) onSuccess(value);
    } catch (err) {
      if (version !== requestVersion.current) return;
      if (err instanceof ApiError && err.status === 409) {
        setMeta(null);
        setParseResult(null);
        setForm(null);
        setRecommendations(null);
        setPlace(null);
        setBudget(null);
        setSelectedPlaceIds([]);
        setScreen("home");
        setError(null);
        setNotice("데이터가 갱신되었습니다. 최신 상태를 확인했으니 조건을 다시 분석해 주세요.");
        void refreshMeta();
      } else {
        setError(errorMessage(err));
      }
    } finally {
      if (version === requestVersion.current) setBusy(false);
    }
  }, []);

  const parse = async () => {
    if (!rawText.trim()) {
      setError("검색 문장을 입력해 주세요.");
      return;
    }
    await execute(() => api.parseQuery(rawText, externalAiConsent), (result) => {
      setParseResult(result);
      setForm(formFromDraft(result.draft));
      setRecommendations(null);
      setPlace(null);
      setBudget(null);
      setSelectedPlaceIds([]);
      setScreen("conditions");
      setNotice("조건 초안을 확인하고 필요한 값을 보완해 주세요.");
    });
  };

  const conditions = useMemo(() => (form ? conditionFromForm(form) : null), [form]);

  const updateForm = useCallback((next: ConditionForm) => {
    const changed = !form || JSON.stringify(form) !== JSON.stringify(next);
    const hasDerivedResult = Boolean(recommendations || place || budget || selectedPlaceIds.length);
    setForm(next);
    if (!changed || !hasDerivedResult) return;

    requestVersion.current += 1;
    setBusy(false);
    setRecommendations(null);
    setPlace(null);
    setBudget(null);
    setSelectedPlaceIds([]);
    setScreen("conditions");
    setNotice("조건이 변경되어 이전 추천과 예산 결과를 무효화했습니다. 새 조건으로 다시 추천해 주세요.");
  }, [budget, form, place, recommendations, selectedPlaceIds.length]);

  const availableScreens = useMemo<Screen[]>(() => {
    const available: Screen[] = ["home"];
    if (form && parseResult) available.push("conditions");
    if (recommendations) available.push("results");
    if (place) available.push("place");
    if (budget) available.push("budget");
    if (!available.includes(screen)) available.push(screen);
    return available;
  }, [budget, form, parseResult, place, recommendations, screen]);

  const changeScreen = useCallback((target: Screen) => {
    if (!availableScreens.includes(target)) {
      setNotice("먼저 앞 단계의 조건 확인과 추천을 완료해 주세요.");
      return;
    }
    setScreen(target);
  }, [availableScreens]);

  const recommend = async () => {
    if (!form || !meta) return;
    const missing: string[] = [];
    if (!form.region_id) missing.push("지역");
    if (!form.category) missing.push("업종");
    if (!form.purpose) missing.push("목적");
    if (!form.party_size) missing.push("인원");
    if (!form.budget_type || !form.budget_amount) missing.push("예산");
    if (!form.visit_at) missing.push("방문 시각");
    if (missing.length) {
      setError(`다음 값을 입력해 주세요: ${missing.join(", ")}`);
      return;
    }
    const nextConditions = conditionFromForm(form);
    await execute(() => api.recommendations(nextConditions, meta.snapshot_id), (result) => {
      setRecommendations(result);
      setSelectedPlaceIds([]);
      setScreen("results");
      setNotice(result.items.length ? "조건에 맞는 추천을 확인해 보세요." : "조건에 맞는 후보가 없습니다. 조건을 직접 수정해 보세요.");
    });
  };

  const openPlace = async (placeId: string) => {
    if (!meta) return;
    setScreen("place");
    await execute(() => api.place(placeId, meta.snapshot_id), (result) => setPlace(result));
  };

  const toggleCompare = (placeId: string) => {
    setSelectedPlaceIds((current) => {
      if (current.includes(placeId)) return current.filter((id) => id !== placeId);
      if (current.length >= 3) {
        setNotice("대안 비교는 최대 3개까지 가능합니다.");
        return current;
      }
      return [...current, placeId];
    });
  };

  const openBudget = async () => {
    if (!conditions || !meta) {
      setError("먼저 조건을 확정하고 추천을 실행해 주세요.");
      return;
    }
    if (!selectedPlaceIds.length) {
      setError("비교할 장소를 하나 이상 선택해 주세요.");
      return;
    }
    setScreen("budget");
    await execute(() => api.budget(conditions, meta.snapshot_id, selectedPlaceIds), (result) => setBudget(result));
  };

  const savePlace = (placeId: string) => {
    if (!meta) return;
    const next = [{ place_id: placeId, snapshot_id: meta.snapshot_id, saved_at: new Date().toISOString() }, ...saved.filter((item) => item.place_id !== placeId)];
    setSaved(next.slice(0, 20));
    setNotice(saveToStorage(next) ? "저장했습니다. 저장 목록에는 장소 ID와 스냅샷만 보관됩니다." : "저장소를 사용할 수 없어 이번 세션에만 임시 저장했습니다.");
  };

  const clearSaved = () => {
    setSaved([]);
    setNotice(saveToStorage([]) ? "저장 목록을 모두 삭제했습니다." : "브라우저 저장소를 사용할 수 없어 현재 화면의 저장 목록만 비웠습니다.");
  };

  const screenTitle: Record<Screen, string> = { home: "어디에서 어떻게 쓸지 알려 주세요", conditions: "조건을 확인해 주세요", results: "조건에 맞는 선택지", place: "장소와 근거", budget: "대안별 예산 비교" };

  return (
    <AppLayout
      meta={meta}
      screen={screen}
      screenTitle={screenTitle[screen]}
      busy={busy}
      error={error}
      notice={notice}
      onHome={() => setScreen("home")}
      availableScreens={availableScreens}
      onScreenChange={changeScreen}
      onRefreshMeta={() => void refreshMeta()}
      onClearError={() => setError(null)}
      onClearNotice={() => setNotice(null)}
    >
      {screen === "home" && <HomeScreen
        rawText={rawText}
        setRawText={setRawText}
        busy={busy}
        parse={parse}
        externalAiEnabled={Boolean(meta?.llm.enabled)}
        externalAiConsent={externalAiConsent}
        setExternalAiConsent={setExternalAiConsent}
      />}
      {screen === "conditions" && form && parseResult && <ConditionsScreen form={form} setForm={updateForm} parseResult={parseResult} busy={busy} recommend={recommend} />}
      {screen === "results" && recommendations && <ResultsScreen result={recommendations} selected={selectedPlaceIds} toggleCompare={toggleCompare} openPlace={openPlace} openBudget={openBudget} />}
      {screen === "place" && <PlaceScreen place={place} saved={saved} savePlace={savePlace} toggleCompare={toggleCompare} selected={selectedPlaceIds} back={() => setScreen("results")} />}
      {screen === "budget" && <BudgetScreen result={budget} selected={selectedPlaceIds} saved={saved} clearSaved={clearSaved} openPlace={openPlace} back={() => setScreen("results")} />}
    </AppLayout>
  );
}

export default App;
