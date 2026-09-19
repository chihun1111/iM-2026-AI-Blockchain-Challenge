from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


RegionId = Literal["dongseongro", "suseongmot"]
Category = Literal["restaurant", "cafe"]
Purpose = Literal["meal", "cafe", "date", "friends"]
Atmosphere = Literal["quiet", "conversation", "lively", "solo_friendly"]
BudgetType = Literal["per_person", "total"]
PriorityProfile = Literal["balanced"]
BudgetStatus = Literal["fits", "exceeds", "unknown"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Budget(StrictModel):
    type: BudgetType
    amount: int = Field(ge=1, le=10_000_000)
    currency: Literal["KRW"]


class Origin(StrictModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class Conditions(StrictModel):
    schema_version: Literal["2.0"]
    region_id: RegionId
    category: Category
    purpose: Purpose
    party_size: int = Field(ge=1, le=6)
    budget: Budget
    visit_at: datetime
    atmosphere_preferences: list[Atmosphere] = Field(default_factory=list)
    required_atmosphere: list[Atmosphere] = Field(default_factory=list)
    priority_profile: PriorityProfile
    origin: Origin | None = None
    radius_m: int = Field(ge=100, le=10_000)
    confirmed: Literal[True]

    @field_validator("visit_at")
    @classmethod
    def visit_has_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("visit_at은 시간대가 있는 ISO 8601 값이어야 합니다.")
        return value

    @model_validator(mode="after")
    def validate_cross_fields(self) -> "Conditions":
        if not set(self.required_atmosphere).issubset(set(self.atmosphere_preferences)):
            raise ValueError("required_atmosphere는 atmosphere_preferences의 부분집합이어야 합니다.")
        return self


class ParseQueryRequest(StrictModel):
    text: str = Field(max_length=500)
    external_ai_consent: bool = False

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text는 비어 있을 수 없습니다.")
        return value


class RecommendationRequest(StrictModel):
    conditions: Conditions
    snapshot_id: str = Field(min_length=1, max_length=100)


class BudgetEstimateRequest(StrictModel):
    conditions: Conditions
    snapshot_id: str = Field(min_length=1, max_length=100)
    place_ids: list[str] = Field(min_length=1, max_length=3)

    @field_validator("place_ids")
    @classmethod
    def unique_place_ids(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("place_ids는 중복될 수 없습니다.")
        return value


class CommonResponse(StrictModel):
    request_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    data_mode: str = Field(min_length=1)
    reference_now: str = Field(min_length=1)
    warnings: list[str]


class AdapterStatus(StrictModel):
    provider: str | None
    model: str | None
    configured: bool
    enabled: bool


class MapAdapterStatus(StrictModel):
    mode: str
    enabled: bool


class HealthAdapters(StrictModel):
    llm: AdapterStatus
    map: MapAdapterStatus


class HealthSnapshot(StrictModel):
    snapshot_id: str
    data_mode: str
    is_mock: bool


class HealthResponse(StrictModel):
    request_id: str = Field(min_length=1)
    status: Literal["ok", "degraded"]
    config_valid: bool
    db_access: bool
    snapshot: HealthSnapshot | None
    adapters: HealthAdapters
    warnings: list[str]


class MetaResponse(CommonResponse):
    regions: list[RegionId]
    categories: list[Category]
    atmosphere_tags: list[Atmosphere]
    parser_mode: str
    explanation_mode: str
    map_mode: str
    llm: AdapterStatus


class DraftBudget(StrictModel):
    type: BudgetType | None
    amount: int | None = Field(ge=1, le=10_000_000)
    currency: Literal["KRW"]


class ParseDraft(StrictModel):
    schema_version: Literal["2.0"]
    region_id: RegionId | None
    category: Category | None
    purpose: Purpose | None
    party_size: int | None = Field(ge=1, le=6)
    budget: DraftBudget
    visit_at: str | None
    atmosphere_preferences: list[Atmosphere]
    required_atmosphere: list[Atmosphere]
    priority_profile: PriorityProfile
    origin: Origin | None
    radius_m: int = Field(ge=100, le=10_000)
    confirmed: Literal[False]


class FieldMeta(StrictModel):
    origin: Literal["explicit", "inferred", "default", "missing", "provider"]
    reason_code: str | None = None


class ParseResponse(CommonResponse):
    parser_mode: str
    draft: ParseDraft
    field_meta: dict[str, FieldMeta]
    missing_fields: list[str]
    confirmation_required: list[str]


class DataAsOf(StrictModel):
    price: str | None
    opening_hours: str | None
    atmosphere: str | None
    area_metrics: str | None


class RecommendationItem(StrictModel):
    place_id: str
    name: str
    region_id: RegionId
    category: Category
    cost_min: int | None
    cost_max: int | None
    per_person_min: int | None
    per_person_max: int | None
    remaining_min: int | None
    remaining_max: int | None
    budget_status: BudgetStatus
    evidence_ids: list[str]
    opening_status: Literal["open", "closed", "unknown"]
    is_mock: bool
    data_as_of: DataAsOf
    reasons: list[str]
    data_status_reason: str | None


class RecommendationResponse(CommonResponse):
    items: list[RecommendationItem]
    insufficient_data_items: list[RecommendationItem]
    excluded_counts: dict[str, int]
    active_features: list[str]


class OpeningDay(StrictModel):
    weekday: int = Field(ge=0, le=6)
    intervals: list[list[str]]


class PlaceData(StrictModel):
    place_id: str
    name: str
    region_id: RegionId
    area_id: str
    category: Category
    address_label: str
    coordinates: Origin | None
    party_min: int = Field(ge=1, le=6)
    party_max: int = Field(ge=1, le=6)
    purpose_tags: list[str]
    atmosphere_tags: list[Atmosphere]
    opening_weekly: list[OpeningDay]
    opening_observed_at: str
    opening_hours_eligible_for_filter: bool
    atmosphere_observed_at: str
    source_id: str
    is_mock: bool


class MenuItemData(StrictModel):
    menu_item_id: str
    place_id: str
    name: str
    price_krw: int = Field(gt=0)
    pricing_unit: Literal["per_person"]
    minimum_order: int = Field(gt=0)
    portion: str
    mandatory_cost: int = Field(ge=0)
    confirmed_on: str
    confirmed_by_role: str
    usage_basis: str
    source_url: str | None
    evidence_file: str | None
    is_budget_candidate: bool
    source_id: str
    is_mock: bool


class PriceData(StrictModel):
    bundle_id: str
    place_id: str
    unit: str
    label: str
    unit_min: int = Field(ge=0)
    unit_max: int = Field(ge=0)
    fixed_fee_min: int = Field(ge=0)
    fixed_fee_max: int = Field(ge=0)
    currency: Literal["KRW"]
    observed_at: str
    included: list[str]
    excluded: list[str]
    source_id: str
    is_mock: bool
    menu_items: list[MenuItemData]


class EvidenceData(StrictModel):
    evidence_id: str
    place_id: str | None
    area_id: str | None
    source_id: str
    claim_type: str
    value: Any
    unit: str | None
    observed_at: str
    period_start: str | None
    period_end: str | None
    aggregation_unit: str | None
    is_mock: bool


class AreaMetricData(StrictModel):
    metric_id: str
    area_id: str
    category: Category
    day_group: str
    time_bucket: str
    week_start: str
    week_end: str
    txn_count: int = Field(ge=0)
    merchant_count: int = Field(ge=0)
    footfall_count: int | None = Field(default=None, ge=0)
    source_id: str
    metric_definition_version: str
    coverage_status: str
    is_mock: bool


class PlaceResponse(CommonResponse):
    place: PlaceData
    price: PriceData | None
    evidence: list[EvidenceData]
    area_timeseries: list[AreaMetricData]


class MenuCalculationData(StrictModel):
    role: Literal["minimum", "maximum", "range"]
    menu_item_id: str
    name: str
    unit_price: int = Field(gt=0)
    quantity: int = Field(gt=0)
    subtotal: int = Field(gt=0)
    mandatory_cost: int = Field(ge=0)
    total_price: int = Field(gt=0)


class BudgetItem(StrictModel):
    place_id: str
    bundle_id: str | None
    party_size: int
    cost_min: int | None
    cost_max: int | None
    per_person_min: int | None
    per_person_max: int | None
    remaining_min: int | None
    remaining_max: int | None
    budget_status: BudgetStatus
    reason_code: str | None
    source_id: str | None
    assumptions: list[str]
    is_mock: bool
    observed_at: str | None
    menu_calculations: list[MenuCalculationData]


class BudgetResponse(CommonResponse):
    comparison_mode: Literal["alternatives"]
    total_budget: int
    items: list[BudgetItem]


class ErrorField(StrictModel):
    path: str
    message: str


class ErrorBody(StrictModel):
    code: str
    message: str
    retryable: bool
    fields: list[ErrorField]


class ErrorResponse(StrictModel):
    request_id: str
    error: ErrorBody
