export type Region = "dongseongro" | "suseongmot";
export type Category = "restaurant" | "cafe";
export type Purpose = "meal" | "cafe" | "date" | "friends";
export type Atmosphere = "quiet" | "conversation" | "lively" | "solo_friendly";
export type BudgetType = "per_person" | "total";

export interface Meta {
  request_id: string;
  snapshot_id: string;
  policy_version: string;
  data_mode: string;
  parser_mode: string;
  explanation_mode: string;
  map_mode: string;
  reference_now: string;
  regions: Region[];
  categories: Category[];
  atmosphere_tags: Atmosphere[];
  llm: { provider: string | null; model: string | null; configured: boolean; enabled: boolean };
  warnings: string[];
}

export interface Health {
  request_id: string;
  status: "ok" | "degraded";
  config_valid: boolean;
  db_access: boolean;
  snapshot: { snapshot_id: string; data_mode: string; is_mock: boolean } | null;
  adapters: {
    llm: { provider: string | null; model: string | null; configured: boolean; enabled: boolean };
    map: { mode: string; enabled: boolean };
  };
  warnings: string[];
}

export interface ParseResult {
  request_id: string;
  parser_mode: string;
  draft: Draft;
  field_meta: Record<string, { origin: string; reason_code?: string | null }>;
  missing_fields: string[];
  confirmation_required: string[];
  warnings: string[];
  snapshot_id: string;
  policy_version: string;
  data_mode: string;
  reference_now: string;
}

export interface Draft {
  schema_version: "2.0";
  region_id: Region | null;
  category: Category | null;
  purpose: Purpose | null;
  party_size: number | null;
  budget: { type: BudgetType | null; amount: number | null; currency: "KRW" };
  visit_at: string | null;
  atmosphere_preferences: Atmosphere[];
  required_atmosphere: Atmosphere[];
  priority_profile: "balanced";
  origin: null;
  radius_m: number;
  confirmed: false;
}

export interface Conditions {
  schema_version: "2.0";
  region_id: Region;
  category: Category;
  purpose: Purpose;
  party_size: number;
  budget: { type: BudgetType; amount: number; currency: "KRW" };
  visit_at: string;
  atmosphere_preferences: Atmosphere[];
  required_atmosphere: Atmosphere[];
  priority_profile: "balanced";
  origin: null;
  radius_m: number;
  confirmed: true;
}

export interface DataAsOf {
  price: string | null;
  opening_hours: string | null;
  atmosphere: string | null;
  area_metrics: string | null;
}

export interface RecommendationItem {
  place_id: string;
  name: string;
  region_id: Region;
  category: Category;
  cost_min: number | null;
  cost_max: number | null;
  per_person_min: number | null;
  per_person_max: number | null;
  remaining_min: number | null;
  remaining_max: number | null;
  budget_status: "fits" | "exceeds" | "unknown";
  evidence_ids: string[];
  opening_status: "open" | "closed" | "unknown";
  is_mock: boolean;
  data_as_of: DataAsOf;
  reasons: string[];
  data_status_reason: string | null;
}

export interface RecommendationResult {
  request_id: string;
  snapshot_id: string;
  policy_version: string;
  data_mode: string;
  reference_now: string;
  warnings: string[];
  items: RecommendationItem[];
  insufficient_data_items: RecommendationItem[];
  excluded_counts: Record<string, number>;
  active_features: string[];
}

export interface PlaceResult {
  request_id: string;
  snapshot_id: string;
  policy_version: string;
  data_mode: string;
  reference_now: string;
  warnings: string[];
  place: {
    place_id: string;
    name: string;
    region_id: Region;
    area_id: string;
    category: Category;
    address_label: string;
    coordinates: { latitude: number; longitude: number } | null;
    party_min: number;
    party_max: number;
    purpose_tags: string[];
    atmosphere_tags: Atmosphere[];
    opening_weekly: Array<{ weekday: number; intervals: string[][] }>;
    opening_observed_at: string;
    opening_hours_eligible_for_filter: boolean;
    atmosphere_observed_at: string;
    source_id: string;
    is_mock: boolean;
  };
  price: {
    bundle_id: string;
    place_id: string;
    unit: string;
    label: string;
    unit_min: number;
    unit_max: number;
    fixed_fee_min: number;
    fixed_fee_max: number;
    currency: "KRW";
    included: string[];
    excluded: string[];
    observed_at: string;
    source_id: string;
    is_mock: boolean;
    menu_items: Array<{
      menu_item_id: string;
      place_id: string;
      name: string;
      price_krw: number;
      pricing_unit: "per_person";
      minimum_order: number;
      portion: string;
      mandatory_cost: number;
      confirmed_on: string;
      confirmed_by_role: string;
      usage_basis: string;
      source_url: string | null;
      evidence_file: string | null;
      is_budget_candidate: boolean;
      source_id: string;
      is_mock: boolean;
    }>;
  } | null;
  evidence: Array<{
    evidence_id: string;
    place_id: string | null;
    area_id: string | null;
    source_id: string;
    claim_type: string;
    value: unknown;
    unit: string | null;
    observed_at: string;
    period_start: string | null;
    period_end: string | null;
    aggregation_unit: string | null;
    is_mock: boolean;
  }>;
  area_timeseries: Array<{
    metric_id: string;
    week_start: string;
    week_end: string;
    day_group: string;
    txn_count: number;
    merchant_count: number;
    footfall_count: number | null;
    time_bucket: string;
    source_id: string;
    metric_definition_version: string;
    coverage_status: string;
    is_mock: boolean;
  }>;
}

export interface BudgetResult {
  request_id: string;
  snapshot_id: string;
  policy_version: string;
  data_mode: string;
  reference_now: string;
  warnings: string[];
  comparison_mode: "alternatives";
  total_budget: number;
  items: Array<{
    place_id: string;
    bundle_id: string | null;
    party_size: number;
    cost_min: number | null;
    cost_max: number | null;
    per_person_min: number | null;
    per_person_max: number | null;
    remaining_min: number | null;
    remaining_max: number | null;
    budget_status: "fits" | "exceeds" | "unknown";
    reason_code: string | null;
    source_id: string | null;
    assumptions: string[];
    is_mock: boolean;
    observed_at: string | null;
    menu_calculations: Array<{
      role: "minimum" | "maximum" | "range";
      menu_item_id: string;
      name: string;
      unit_price: number;
      quantity: number;
      subtotal: number;
      mandatory_cost: number;
      total_price: number;
    }>;
  }>;
}

export interface SavedPlace {
  place_id: string;
  snapshot_id: string;
  saved_at: string;
}

export interface ConditionForm {
  region_id: Region | "";
  category: Category | "";
  purpose: Purpose | "";
  party_size: string;
  budget_type: BudgetType | "";
  budget_amount: string;
  visit_at: string;
  atmosphere_preferences: Atmosphere[];
  required_atmosphere: Atmosphere[];
  priority_profile: "balanced";
}
