import type {
  BudgetResult,
  Conditions,
  Health,
  Meta,
  ParseResult,
  PlaceResult,
  RecommendationResult,
} from "../types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  code: string;
  fields: Array<{ path?: string; message?: string }>;

  constructor(status: number, payload: unknown) {
    const error = isRecord(payload) && isRecord(payload.error) ? payload.error : {};
    super(typeof error.message === "string" ? error.message : "API 요청을 처리하지 못했습니다.");
    this.status = status;
    this.code = typeof error.code === "string" ? error.code : "UNKNOWN_ERROR";
    this.fields = Array.isArray(error.fields)
      ? error.fields.filter((item): item is { path?: string; message?: string } => isRecord(item))
      : [];
  }
}

function isRecord(value: unknown): value is Record<string, any> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function contractError(message: string): ApiError {
  return new ApiError(502, { error: { code: "INVALID_API_RESPONSE", message, fields: [] } });
}

function assertResponseEnvelope<T>(payload: unknown, path: string): T {
  if (!isRecord(payload) || typeof payload.request_id !== "string" || !Array.isArray(payload.warnings)) {
    throw contractError(`API 응답 형식이 올바르지 않습니다: ${path}`);
  }
  return payload as T;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, payload);
  return assertResponseEnvelope<T>(payload, path);
}

export const api = {
  health: () => request<Health>("/api/health"),
  meta: () => request<Meta>("/api/meta"),
  parseQuery: (text: string, externalAiConsent = false) => request<ParseResult>("/api/parse-query", {
    method: "POST",
    body: JSON.stringify({ text, external_ai_consent: externalAiConsent }),
  }),
  recommendations: (conditions: Conditions, snapshotId: string) =>
    request<RecommendationResult>("/api/recommendations", { method: "POST", body: JSON.stringify({ conditions, snapshot_id: snapshotId }) }),
  place: (placeId: string, snapshotId: string) => request<PlaceResult>(`/api/places/${encodeURIComponent(placeId)}?snapshot_id=${encodeURIComponent(snapshotId)}`),
  budget: (conditions: Conditions, snapshotId: string, placeIds: string[]) =>
    request<BudgetResult>("/api/budget/estimate", { method: "POST", body: JSON.stringify({ conditions, snapshot_id: snapshotId, place_ids: placeIds }) }),
};
