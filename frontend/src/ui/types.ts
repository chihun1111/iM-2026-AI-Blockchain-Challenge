export type Screen = "home" | "conditions" | "results" | "place" | "budget";

export const screenLabels: Record<Screen, string> = {
  home: "입력",
  conditions: "조건 확인",
  results: "추천",
  place: "근거",
  budget: "예산",
};
