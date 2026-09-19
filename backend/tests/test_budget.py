from __future__ import annotations

from datetime import datetime

from backend.app.config import ROOT, load_settings
from backend.app.domain.budget import calculate_budget
from backend.app.models import Conditions


def make_conditions(amount=20000, budget_type="per_person", party_size=2):
    return Conditions(
        schema_version="2.0", region_id="dongseongro", category="restaurant", purpose="meal",
        party_size=party_size, budget={"type": budget_type, "amount": amount, "currency": "KRW"},
        visit_at=datetime.fromisoformat("2026-09-19T19:00:00+09:00"), atmosphere_preferences=[], required_atmosphere=[],
        priority_profile="balanced", origin=None, radius_m=2000, confirmed=True,
    )


def test_budget_boundary_and_fixed_fee():
    settings = load_settings(ROOT)
    bundle = {"unit_min": 15000, "unit_max": 18000, "fixed_fee_min": 0, "fixed_fee_max": 0, "observed_at": "2026-09-18T12:00:00+09:00"}
    result = calculate_budget(settings, make_conditions(), bundle)
    assert (result.total_budget, result.cost_min, result.cost_max, result.remaining_min, result.remaining_max, result.status) == (40000, 30000, 36000, 4000, 10000, "fits")
    assert calculate_budget(settings, make_conditions(amount=35999, budget_type="total"), bundle).status == "exceeds"
    fee_bundle = {**bundle, "fixed_fee_min": 5000, "fixed_fee_max": 5000}
    assert calculate_budget(settings, make_conditions(amount=40000, budget_type="total"), fee_bundle).cost_max == 41000


def test_budget_unknown_for_stale_price():
    settings = load_settings(ROOT)
    bundle = {"unit_min": 15000, "unit_max": 18000, "fixed_fee_min": 0, "fixed_fee_max": 0, "observed_at": "2026-01-01T12:00:00+09:00"}
    assert calculate_budget(settings, make_conditions(), bundle).status == "unknown"


def test_verified_menu_does_not_treat_unknown_mandatory_cost_as_zero():
    settings = load_settings(ROOT)
    bundle = {"unit_min": 12000, "unit_max": 12000, "fixed_fee_min": 0, "fixed_fee_max": 0, "observed_at": "2026-09-18T12:00:00+09:00"}
    menu = [{
        "menu_item_id": "MENU-1", "name": "검증 전 메뉴", "price_krw": 12000,
        "min_order_qty": 1, "mandatory_cost": None, "is_budget_candidate": 1,
    }]
    result = calculate_budget(settings, make_conditions(), bundle, menu)
    assert result.status == "unknown"
    assert result.reason == "MANDATORY_FEE_UNKNOWN"
