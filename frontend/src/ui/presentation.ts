import type { Atmosphere } from "../types";

export const labels: Record<string, string> = {
  dongseongro: "동성로",
  suseongmot: "수성못",
  restaurant: "식당",
  cafe: "카페",
  meal: "식사",
  date: "데이트",
  friends: "친구 모임",
  balanced: "균형형",
  quiet: "조용한",
  conversation: "대화하기 좋은",
  lively: "활기찬",
  solo_friendly: "혼밥하기 좋은",
  per_person: "1인 예산",
  total: "전체 예산",
  weekday: "평일",
  weekend: "주말",
  lunch: "점심",
  afternoon: "오후",
  dinner: "저녁",
};

export const atmosphereOptions: Atmosphere[] = ["quiet", "conversation", "lively", "solo_friendly"];

export function label(value: string | null | undefined): string {
  return value ? labels[value] || value : "미입력";
}

export function money(value: number | null | undefined): string {
  return value == null ? "확인 필요" : `${value.toLocaleString("ko-KR")}원`;
}

export function moneyRange(min: number | null | undefined, max: number | null | undefined): string {
  if (min == null && max == null) return "확인 필요";
  if (min == null) return `최대 ${money(max)}`;
  if (max == null) return `최소 ${money(min)}`;
  return min === max ? money(min) : `${money(min)}~${money(max)}`;
}
