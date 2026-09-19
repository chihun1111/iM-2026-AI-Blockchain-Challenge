from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


CONDITIONS = {
    "schema_version": "2.0",
    "region_id": "dongseongro",
    "category": "restaurant",
    "purpose": "meal",
    "party_size": 2,
    "budget": {"type": "per_person", "amount": 20_000, "currency": "KRW"},
    "visit_at": "2026-09-19T19:00:00+09:00",
    "atmosphere_preferences": [],
    "required_atmosphere": [],
    "priority_profile": "balanced",
    "origin": None,
    "radius_m": 2_000,
    "confirmed": True,
}


def call(base_url: str, path: str, method: str = "GET", payload: Any = None, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], Any]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request_headers = {"Accept": "application/json", **(headers or {})}
    if body is not None:
        request_headers.setdefault("Content-Type", "application/json")
    request = Request(f"{base_url.rstrip('/')}{path}", data=body, headers=request_headers, method=method)
    def decode(raw: bytes) -> Any:
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return None
    try:
        with urlopen(request, timeout=10) as response:
            raw = response.read()
            return response.status, dict(response.headers.items()), decode(raw)
    except HTTPError as error:
        raw = error.read()
        return error.code, dict(error.headers.items()), decode(raw)
    except URLError as error:
        raise RuntimeError(f"HTTP 서버에 연결할 수 없습니다: {error}") from error


def assert_common(payload: Any, label: str) -> None:
    assert isinstance(payload, dict), f"{label}: object response expected"
    assert isinstance(payload.get("request_id"), str) and payload["request_id"], f"{label}: request_id missing"
    assert isinstance(payload.get("warnings"), list), f"{label}: warnings missing"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    results: list[dict[str, Any]] = []

    status, headers, _ = call(
        args.base_url,
        "/api/meta",
        method="OPTIONS",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert status == 200, f"CORS preflight status={status}"
    assert headers.get("access-control-allow-origin") == "http://127.0.0.1:5173", "CORS origin is not allowed"
    results.append({"check": "cors_preflight", "status": status, "allow_origin": headers.get("access-control-allow-origin")})

    for path in ("/api/health", "/api/meta"):
        status, headers, payload = call(args.base_url, path, headers={"Origin": "http://127.0.0.1:5173"})
        assert status == 200, f"{path}: status={status}"
        assert_common(payload, path)
        assert headers.get("access-control-allow-origin") == "http://127.0.0.1:5173", f"{path}: CORS header missing"
        results.append({"check": path, "status": status, "request_id": payload["request_id"]})

    status, _, parse_payload = call(args.base_url, "/api/parse-query", "POST", {"text": "동성로 2명 인당 2만원 저녁 7시 식사"}, {"Origin": "http://127.0.0.1:5173"})
    assert status == 200 and parse_payload["draft"]["confirmed"] is False, "parse response is not an unconfirmed draft"
    assert_common(parse_payload, "parse")
    results.append({"check": "parse", "status": status, "parser_mode": parse_payload["parser_mode"]})

    snapshot_id = parse_payload["snapshot_id"]
    recommendation_request = {"conditions": CONDITIONS, "snapshot_id": snapshot_id}
    status, _, recommendation_payload = call(args.base_url, "/api/recommendations", "POST", recommendation_request, {"Origin": "http://127.0.0.1:5173"})
    assert status == 200 and len(recommendation_payload["items"]) <= 3, "recommendation response is invalid"
    assert_common(recommendation_payload, "recommendations")
    place_ids = [item["place_id"] for item in recommendation_payload["items"][:2]]
    assert place_ids, "recommendations returned no places"
    results.append({"check": "recommendations", "status": status, "count": len(recommendation_payload["items"])})

    status, _, place_payload = call(args.base_url, f"/api/places/{place_ids[0]}?snapshot_id={snapshot_id}", headers={"Origin": "http://127.0.0.1:5173"})
    assert status == 200 and "source_id" in place_payload["place"], "place DTO is not typed/public"
    assert_common(place_payload, "place")
    results.append({"check": "place", "status": status, "place_id": place_ids[0]})

    status, _, budget_payload = call(args.base_url, "/api/budget/estimate", "POST", {**recommendation_request, "place_ids": place_ids}, {"Origin": "http://127.0.0.1:5173"})
    assert status == 200 and budget_payload["comparison_mode"] == "alternatives", "budget response is invalid"
    assert_common(budget_payload, "budget")
    results.append({"check": "budget", "status": status, "items": len(budget_payload["items"])})

    status, _, stale_payload = call(args.base_url, "/api/recommendations", "POST", {"conditions": CONDITIONS, "snapshot_id": "stale-snapshot"})
    assert status == 409 and set(stale_payload) == {"request_id", "error"}, "409 envelope is not consistent"
    results.append({"check": "snapshot_mismatch", "status": status, "code": stale_payload["error"]["code"]})

    oversized = {"text": "x" * 17_000}
    status, _, oversized_payload = call(args.base_url, "/api/parse-query", "POST", oversized)
    assert status == 413 and oversized_payload["error"]["code"] == "REQUEST_TOO_LARGE", "413 envelope is not consistent"
    results.append({"check": "request_size", "status": status, "code": oversized_payload["error"]["code"]})

    print(json.dumps({"status": "PASS", "base_url": args.base_url, "checks": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
