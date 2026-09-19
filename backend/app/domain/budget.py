from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

from ..config import Settings


@dataclass(frozen=True)
class BudgetResult:
    total_budget: int
    cost_min: int | None
    cost_max: int | None
    per_person_min: int | None
    per_person_max: int | None
    remaining_min: int | None
    remaining_max: int | None
    status: str
    reason: str | None = None
    menu_calculations: tuple[dict, ...] = ()


def total_budget(budget_type: str, amount: int, party_size: int) -> int:
    return amount * party_size if budget_type == "per_person" else amount


def _fresh_enough(observed_at: str | None, reference_now: datetime, max_days: int) -> bool:
    if not observed_at:
        return False
    try:
        observed = datetime.fromisoformat(observed_at)
    except ValueError:
        return False
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    if reference_now.tzinfo is None:
        reference_now = reference_now.replace(tzinfo=timezone.utc)
    age = (reference_now - observed).total_seconds()
    return 0 <= age <= max_days * 86400


def calculate_budget(
    settings: Settings,
    conditions,
    bundle: dict | None,
    menu_items: list[dict] | None = None,
    reference_now: str | None = None,
) -> BudgetResult:
    budget_limit = total_budget(conditions.budget.type, conditions.budget.amount, conditions.party_size)
    if not bundle:
        return BudgetResult(budget_limit, None, None, None, None, None, None, "unknown", "PRICE_MISSING")
    reference = datetime.fromisoformat(reference_now or settings.reference_now)
    if not _fresh_enough(bundle.get("observed_at"), reference, settings.policy["freshness_days"]["price"]):
        return BudgetResult(budget_limit, None, None, None, None, None, None, "unknown", "PRICE_STALE")
    required_fee_known = bundle.get("fixed_fee_min") is not None and bundle.get("fixed_fee_max") is not None
    if not required_fee_known:
        return BudgetResult(budget_limit, None, None, None, None, None, None, "unknown", "MANDATORY_FEE_UNKNOWN")
    calculations: tuple[dict, ...] = ()
    verified_candidates = [item for item in (menu_items or []) if item.get("is_budget_candidate")]
    if verified_candidates:
        if any(item.get("mandatory_cost") is None for item in verified_candidates):
            return BudgetResult(
                budget_limit, None, None, None, None, None, None,
                "unknown", "MANDATORY_FEE_UNKNOWN",
            )
        calculated = []
        for item in verified_candidates:
            quantity = max(conditions.party_size, int(item["min_order_qty"]))
            subtotal = int(item["price_krw"]) * quantity
            mandatory_cost = int(item["mandatory_cost"])
            calculated.append((subtotal + mandatory_cost, subtotal, mandatory_cost, quantity, item))
        calculated.sort(key=lambda value: (value[0], value[4]["menu_item_id"]))
        low_total, low_subtotal, low_fee, low_quantity, low_item = calculated[0]
        high_total, high_subtotal, high_fee, high_quantity, high_item = calculated[-1]
        cost_min = low_total
        cost_max = high_total
        if low_item["menu_item_id"] == high_item["menu_item_id"]:
            calculations = ({
                "role": "range",
                "menu_item_id": low_item["menu_item_id"],
                "name": low_item["name"],
                "unit_price": int(low_item["price_krw"]),
                "quantity": low_quantity,
                "subtotal": low_subtotal,
                "mandatory_cost": low_fee,
                "total_price": low_total,
            },)
        else:
            calculations = (
                {
                    "role": "minimum",
                    "menu_item_id": low_item["menu_item_id"],
                    "name": low_item["name"],
                    "unit_price": int(low_item["price_krw"]),
                    "quantity": low_quantity,
                    "subtotal": low_subtotal,
                    "mandatory_cost": low_fee,
                    "total_price": low_total,
                },
                {
                    "role": "maximum",
                    "menu_item_id": high_item["menu_item_id"],
                    "name": high_item["name"],
                    "unit_price": int(high_item["price_krw"]),
                    "quantity": high_quantity,
                    "subtotal": high_subtotal,
                    "mandatory_cost": high_fee,
                    "total_price": high_total,
                },
            )
    else:
        cost_min = int(bundle["unit_min"]) * conditions.party_size + int(bundle["fixed_fee_min"])
        cost_max = int(bundle["unit_max"]) * conditions.party_size + int(bundle["fixed_fee_max"])
    status = "fits" if cost_max <= budget_limit else "exceeds"
    return BudgetResult(
        total_budget=budget_limit,
        cost_min=cost_min,
        cost_max=cost_max,
        per_person_min=math.floor(cost_min / conditions.party_size),
        per_person_max=math.ceil(cost_max / conditions.party_size),
        remaining_min=budget_limit - cost_max,
        remaining_max=budget_limit - cost_min,
        status=status,
        menu_calculations=calculations,
    )
