from __future__ import annotations

def place_detail(db, settings, snapshot_id: str, place_id: str) -> dict | None:
    place = db.place(snapshot_id, place_id)
    if not place:
        return None
    price = db.price(snapshot_id, place_id)
    menu_items = db.menu_items(snapshot_id, place_id)
    evidence = db.evidence_for_place(snapshot_id, place_id)
    series = db.metrics_for_area(snapshot_id, place["area_id"], place["category"])
    public_place = {
        "place_id": place["place_id"],
        "name": place["name"],
        "region_id": place["region_id"],
        "area_id": place["area_id"],
        "category": place["category"],
        "address_label": place["address_label"],
        "coordinates": place["coordinates"],
        "party_min": place["party_min"],
        "party_max": place["party_max"],
        "purpose_tags": place["purpose_tags"],
        "atmosphere_tags": place["atmosphere_tags"],
        "opening_weekly": place["opening_weekly"],
        "opening_observed_at": place["opening_observed_at"],
        "opening_hours_eligible_for_filter": bool(place["opening_hours_eligible_for_filter"]),
        "atmosphere_observed_at": place["atmosphere_observed_at"],
        "source_id": place["source_id"],
        "is_mock": bool(place["is_mock"]),
    }
    public_price = None
    if price is not None:
        public_price = {
            "bundle_id": price["bundle_id"],
            "place_id": price["place_id"],
            "unit": price["unit"],
            "label": price["label"],
            "unit_min": price["unit_min"],
            "unit_max": price["unit_max"],
            "fixed_fee_min": price["fixed_fee_min"],
            "fixed_fee_max": price["fixed_fee_max"],
            "currency": price["currency"],
            "observed_at": price["observed_at"],
            "included": price["included"],
            "excluded": price["excluded"],
            "source_id": price["source_id"],
            "is_mock": bool(price["is_mock"]),
            "menu_items": [
                {
                    "menu_item_id": item["menu_item_id"],
                    "place_id": item["place_id"],
                    "name": item["name"],
                    "price_krw": item["price_krw"],
                    "pricing_unit": item["pricing_unit"],
                    "minimum_order": item["min_order_qty"],
                    "portion": item["portion"],
                    "mandatory_cost": item["mandatory_cost"],
                    "confirmed_on": item["confirmed_on"] or item["observed_at"],
                    "confirmed_by_role": item["confirmed_by_role"],
                    "usage_basis": item["usage_basis"],
                    "source_url": item["source_url"],
                    "evidence_file": item["evidence_file"],
                    "is_budget_candidate": bool(item["is_budget_candidate"]),
                    "source_id": item["source_id"],
                    "is_mock": bool(item["is_mock"]),
                }
                for item in menu_items
            ],
        }
    public_evidence = [
        {key: item[key] for key in (
            "evidence_id", "place_id", "area_id", "source_id", "claim_type", "value", "unit",
            "observed_at", "period_start", "period_end", "aggregation_unit", "is_mock",
        )}
        for item in evidence
    ]
    public_series = [
        {key: item[key] for key in (
            "metric_id", "area_id", "category", "day_group", "time_bucket", "week_start", "week_end",
            "txn_count", "merchant_count", "footfall_count", "source_id", "metric_definition_version",
            "coverage_status", "is_mock",
        )}
        for item in series
    ]
    return {
        "place": public_place,
        "price": public_price,
        "evidence": public_evidence,
        "area_timeseries": public_series,
    }
