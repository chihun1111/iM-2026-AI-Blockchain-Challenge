from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .adapters.parser_provider import parse_with_provider
from .config import Settings, load_settings
from .db import Database
from .domain.budget import calculate_budget, total_budget
from .domain.place import place_detail
from .domain.ranking import rank_recommendations
from .models import (
    BudgetEstimateRequest,
    BudgetResponse,
    Conditions,
    ErrorResponse,
    HealthResponse,
    MetaResponse,
    ParseQueryRequest,
    ParseResponse,
    PlaceResponse,
    RecommendationRequest,
    RecommendationResponse,
)


class APIError(Exception):
    def __init__(self, status_code: int, code: str, message: str, retryable: bool = False, fields: list[dict[str, str]] | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retryable = retryable
        self.fields = fields or []


ERROR_RESPONSES = {
    404: {"model": ErrorResponse, "description": "요청한 리소스를 찾을 수 없습니다."},
    409: {"model": ErrorResponse, "description": "스냅샷이 현재 결과와 일치하지 않습니다."},
    413: {"model": ErrorResponse, "description": "요청 본문이 정책상 허용된 크기를 초과했습니다."},
    422: {"model": ErrorResponse, "description": "요청 형식 또는 값이 올바르지 않습니다."},
    500: {"model": ErrorResponse, "description": "처리 중 서버 오류가 발생했습니다."},
    503: {"model": ErrorResponse, "description": "활성 스냅샷 또는 의존 서비스를 사용할 수 없습니다."},
}


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


def _error_response(request: Request, error: APIError) -> JSONResponse:
    payload = {
        "request_id": _request_id(request),
        "error": {
            "code": error.code,
            "message": error.message,
            "retryable": error.retryable,
            "fields": error.fields,
        },
    }
    return JSONResponse(status_code=error.status_code, content=payload)


def _validation_fields(exc: RequestValidationError | ValidationError) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    for item in exc.errors():
        loc = ".".join(str(x) for x in item.get("loc", []) if x != "body") or "body"
        fields.append({"path": loc, "message": str(item.get("msg", "입력값이 올바르지 않습니다."))})
    return fields


def _manifest(db: Database) -> dict[str, Any] | None:
    row = db.active_snapshot()
    if not row:
        return None
    try:
        return json.loads(row["manifest_json"])
    except (TypeError, json.JSONDecodeError):
        return None


def _common(settings: Settings, db: Database, request: Request, warnings: list[str] | None = None) -> dict[str, Any]:
    row = db.active_snapshot()
    manifest = _manifest(db)
    if not row or not manifest:
        raise APIError(503, "SNAPSHOT_UNAVAILABLE", "활성 데이터 스냅샷을 사용할 수 없습니다.", retryable=True)
    return {
        "request_id": _request_id(request),
        "snapshot_id": row["snapshot_id"],
        "policy_version": settings.policy_version,
        "data_mode": row["data_mode"],
        "reference_now": row["reference_now"],
        "warnings": warnings or [],
    }


def _resolve_snapshot(settings: Settings, db: Database, snapshot_id: str) -> None:
    row = db.active_snapshot()
    if not row:
        raise APIError(503, "SNAPSHOT_UNAVAILABLE", "활성 스냅샷이 없습니다.", retryable=True)
    if snapshot_id != row["snapshot_id"] or row["data_mode"] != settings.data_mode:
        raise APIError(409, "SNAPSHOT_MISMATCH", "데이터가 갱신되었습니다. 최신 스냅샷을 다시 조회하세요.", retryable=True)


def _validate_conditions(settings: Settings, conditions: Conditions, reference_now: str | None = None) -> None:
    if conditions.region_id not in settings.policy["scope"]["regions"]:
        raise APIError(422, "REGION_OUT_OF_SCOPE", "현재 프로토타입은 동성로·중앙로역 일대만 지원합니다.", fields=[{"path": "conditions.region_id", "message": "dongseongro만 사용할 수 있습니다."}])
    if conditions.category not in settings.policy["scope"]["categories"]:
        raise APIError(422, "CATEGORY_OUT_OF_SCOPE", "현재 프로토타입은 한식 음식점만 지원합니다.", fields=[{"path": "conditions.category", "message": "restaurant만 사용할 수 있습니다."}])
    if conditions.priority_profile not in settings.policy["ranking"]["profiles"]:
        raise APIError(422, "RANKING_PROFILE_OUT_OF_SCOPE", "상권 집계는 점포 순위 기준으로 사용하지 않습니다.", fields=[{"path": "conditions.priority_profile", "message": "balanced만 사용할 수 있습니다."}])
    if settings.data_mode == "demo" and conditions.origin is not None:
        raise APIError(422, "DEMO_ORIGIN_UNSUPPORTED", "demo 모드에서는 출발 위치를 사용할 수 없습니다.", fields=[{"path": "conditions.origin", "message": "null이어야 합니다."}])
    # Asia/Seoul is a fixed UTC+09:00 zone; using an explicit offset keeps the
    # bundled runtime self-contained when system tzdata is unavailable.
    kst = timezone(timedelta(hours=9))
    reference = datetime.fromisoformat(reference_now or settings.reference_now).astimezone(kst)
    visit = conditions.visit_at.astimezone(kst)
    if visit < reference or visit > reference + timedelta(days=settings.policy["clock"]["max_visit_days_ahead"]):
        raise APIError(422, "VISIT_AT_OUT_OF_RANGE", "방문 시각은 기준 시각부터 30일 이내여야 합니다.", fields=[{"path": "conditions.visit_at", "message": "허용 범위를 확인하세요."}])


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    db = Database(settings)
    db.initialize()
    app = FastAPI(title="소비나침반 API", version="3.2.0", description="동성로 한식 프로토타입 API와 승인 기반 Gemini 조건 추출 준비")
    app.state.settings = settings
    app.state.db = db

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Request-ID"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.policy["validation"]["max_request_bytes"]:
            return _error_response(request, APIError(413, "REQUEST_TOO_LARGE", "요청 본문은 16KB 이하여야 합니다."))
        response = await call_next(request)
        response.headers["X-Request-ID"] = _request_id(request)
        return response

    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError):
        return _error_response(request, exc)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return _error_response(request, APIError(422, "VALIDATION_ERROR", "요청 형식 또는 값이 올바르지 않습니다.", fields=_validation_fields(exc)))

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception):
        # Do not expose stack traces, paths, provider responses, or secrets.
        return _error_response(request, APIError(500, "INTERNAL_ERROR", "처리 중 오류가 발생했습니다.", retryable=True))

    @app.get("/api/health", response_model=HealthResponse, responses={500: ERROR_RESPONSES[500], 503: ERROR_RESPONSES[503]})
    async def health(request: Request):
        snapshot = db.active_snapshot()
        db_access = False
        try:
            db.initialize()
            db_access = snapshot is not None
        except Exception:
            db_access = False
        return {
            "request_id": _request_id(request),
            "status": "ok" if db_access else "degraded",
            "config_valid": True,
            "db_access": db_access,
            "snapshot": {"snapshot_id": snapshot["snapshot_id"], "data_mode": snapshot["data_mode"], "is_mock": bool(snapshot["is_mock"])} if snapshot else None,
            "adapters": {
                "llm": {"provider": settings.llm_provider, "configured": settings.gemini_configured, "enabled": settings.external_adapter_enabled, "model": settings.llm_model},
                "map": {"mode": settings.map_mode, "enabled": settings.map_mode != "off"},
            },
            "warnings": (["P0 demo 실행: 외부 호출은 기본 비활성입니다."] if snapshot and bool(snapshot["is_mock"]) else ["실데이터 모드: 출처·기준일·집계 단위를 확인하세요."]),
        }

    @app.get("/api/meta", response_model=MetaResponse, responses={500: ERROR_RESPONSES[500], 503: ERROR_RESPONSES[503]})
    async def meta(request: Request):
        common = _common(settings, db, request)
        return {
            **common,
            "regions": settings.policy["scope"]["regions"],
            "categories": settings.policy["scope"]["categories"],
            "atmosphere_tags": ["quiet", "conversation", "lively", "solo_friendly"],
            "data_mode": common["data_mode"],
            "parser_mode": settings.parser_mode,
            "explanation_mode": settings.explanation_mode,
            "map_mode": settings.map_mode,
            "llm": {"provider": settings.llm_provider, "model": settings.llm_model, "configured": settings.gemini_configured, "enabled": settings.external_adapter_enabled},
        }

    @app.post(
        "/api/parse-query",
        response_model=ParseResponse,
        responses={code: ERROR_RESPONSES[code] for code in (413, 422, 500, 503)},
    )
    async def parse_query(request: Request, payload: ParseQueryRequest):
        try:
            result = parse_with_provider(
                settings,
                payload.text,
                external_ai_consent=payload.external_ai_consent,
            )
        except Exception:
            # An optional provider failure never turns the P0 path into a hard failure.
            from .domain.parser import parse_query as rules_parse

            snapshot = db.active_snapshot()
            result = rules_parse(payload.text, datetime.fromisoformat(snapshot["reference_now"] if snapshot else settings.reference_now))
            result["warnings"].append("선택 LLM 호출 실패로 규칙 파서로 전환했습니다.")
        common = _common(settings, db, request)
        return ParseResponse(
            request_id=common["request_id"], snapshot_id=common["snapshot_id"], policy_version=common["policy_version"],
            data_mode=common["data_mode"], reference_now=common["reference_now"], warnings=result["warnings"],
            parser_mode=result["parser_mode"], draft=result["draft"], field_meta=result["field_meta"],
            missing_fields=result["missing_fields"], confirmation_required=result["confirmation_required"],
        )

    @app.post(
        "/api/recommendations",
        response_model=RecommendationResponse,
        responses={code: ERROR_RESPONSES[code] for code in (409, 422, 500, 503)},
    )
    async def recommendations(request: Request, payload: RecommendationRequest):
        _resolve_snapshot(settings, db, payload.snapshot_id)
        snapshot = db.active_snapshot()
        _validate_conditions(settings, payload.conditions, snapshot["reference_now"] if snapshot else None)
        result = rank_recommendations(settings, db, payload.conditions)
        common = _common(settings, db, request, result["warnings"])
        return RecommendationResponse(**common, items=result["items"], insufficient_data_items=result["insufficient_data_items"], excluded_counts=result["excluded_counts"], active_features=result["active_features"])

    @app.get(
        "/api/places/{place_id}",
        response_model=PlaceResponse,
        responses={code: ERROR_RESPONSES[code] for code in (404, 409, 422, 500, 503)},
    )
    async def place(request: Request, place_id: str, snapshot_id: str = Query(min_length=1, max_length=100)):
        _resolve_snapshot(settings, db, snapshot_id)
        result = place_detail(db, settings, snapshot_id, place_id)
        if result is None:
            raise APIError(404, "PLACE_NOT_FOUND", "해당 장소를 찾을 수 없습니다.")
        common = _common(settings, db, request)
        return PlaceResponse(**common, **result)

    @app.post(
        "/api/budget/estimate",
        response_model=BudgetResponse,
        responses={code: ERROR_RESPONSES[code] for code in (404, 409, 413, 422, 500, 503)},
    )
    async def budget_estimate(request: Request, payload: BudgetEstimateRequest):
        _resolve_snapshot(settings, db, payload.snapshot_id)
        snapshot = db.active_snapshot()
        _validate_conditions(settings, payload.conditions, snapshot["reference_now"] if snapshot else None)
        result_items: list[dict[str, Any]] = []
        for place_id in payload.place_ids:
            place = db.place(payload.snapshot_id, place_id)
            if place is None:
                raise APIError(404, "PLACE_NOT_FOUND", f"장소를 찾을 수 없습니다: {place_id}")
            bundle = db.price(payload.snapshot_id, place_id)
            menu_items = db.menu_items(payload.snapshot_id, place_id, budget_candidates_only=True)
            result = calculate_budget(settings, payload.conditions, bundle, menu_items, snapshot["reference_now"] if snapshot else None)
            result_items.append({
                "place_id": place_id,
                "bundle_id": bundle.get("bundle_id") if bundle else None,
                "party_size": payload.conditions.party_size,
                "cost_min": result.cost_min,
                "cost_max": result.cost_max,
                "per_person_min": result.per_person_min,
                "per_person_max": result.per_person_max,
                "remaining_min": result.remaining_min,
                "remaining_max": result.remaining_max,
                "budget_status": result.status,
                "reason_code": result.reason,
                "source_id": bundle.get("source_id") if bundle else None,
                "assumptions": (
                    ["검증 메뉴 가격 × max(인원, 최소 주문) + 확인된 필수비용", "선택 메뉴 외 추가 주문·할인 미적용"]
                    if result.menu_calculations
                    else ["1인 기본 구성 × 확정 인원", "추가 주문·주류 제외", "확인되지 않은 할인 미적용"]
                ),
                "is_mock": bool(place["is_mock"]),
                "observed_at": bundle.get("observed_at") if bundle else None,
                "menu_calculations": list(result.menu_calculations),
            })
        mode_warning = "가상 데이터 기반 예산 계산입니다." if snapshot and bool(snapshot["is_mock"]) else "검증 가능한 메뉴만 서버에서 계산했으며 정보가 부족하면 unknown으로 반환합니다."
        common = _common(settings, db, request, ["각 장소를 선택했을 때의 예상 지출입니다. 여러 장소의 금액을 합산하지 않습니다.", mode_warning])
        return BudgetResponse(**common, comparison_mode="alternatives", total_budget=total_budget(payload.conditions.budget.type, payload.conditions.budget.amount, payload.conditions.party_size), items=result_items)

    return app


app = create_app()
