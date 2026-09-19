from __future__ import annotations

import copy
from dataclasses import replace
import io
import sqlite3
import urllib.error

import pytest

from backend.app.adapters.gemini import GeminiAdapter
from backend.app.config import ROOT, load_settings
from backend.app.gemini_usage import GeminiBudgetExceeded


def _approved_settings(base, *, allow_paid_calls=True, model="gemini-test-model"):
    plan = copy.deepcopy(base.gemini_approval)
    plan["status"] = "APPROVED"
    plan["llm_enabled"] = True
    plan["data_api_gate"] = {"required": True, "status": "PASSED", "evidence": ["test:data-api"]}
    plan["proposal"]["model"] = model
    plan["approval"] = {
        "approved": True,
        "approved_by": "test-approver",
        "approved_at": "2026-09-19T12:00:00+09:00",
        "approved_model": model,
        "approved_transmission_scope": list(plan["proposal"]["transmission_allowed"]),
        "approved_project_total_limit_usd": 5.0,
        "approved_daily_limit_usd": 1.0,
    }
    return replace(
        base,
        allow_external_calls=True,
        allow_paid_calls=allow_paid_calls,
        llm_provider="gemini",
        llm_model=model,
        gemini_api_key="secret-for-test",
        gemini_approval=plan,
    )


def test_gemini_is_opt_in_and_does_not_call_without_key(demo_app):
    adapter = GeminiAdapter(demo_app.state.settings)
    assert adapter.configured is False
    with pytest.raises(RuntimeError, match="활성화되지 않았습니다"):
        adapter.parse("동성로 2명 인당 2만원 식사", demo_app.state.settings.reference_now)


def test_gemini_request_uses_server_header(monkeypatch, demo_app):
    settings = _approved_settings(demo_app.state.settings)
    adapter = GeminiAdapter(settings)
    seen = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"candidates":[{"content":{"parts":[{"text":"{\\"region_id\\":\\"dongseongro\\",\\"category\\":\\"restaurant\\"}"}]}}]}'

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["key_header"] = request.get_header("X-goog-api-key")
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result = adapter.parse("동성로 식사", settings.reference_now)
    assert result.candidate["region_id"] == "dongseongro"
    assert "secret-for-test" not in seen["url"]
    assert seen["key_header"] == "secret-for-test"


def test_gemini_requires_cost_approval_even_with_server_key(demo_app):
    settings = _approved_settings(demo_app.state.settings, allow_paid_calls=False)
    adapter = GeminiAdapter(settings)
    assert adapter.configured is False
    with pytest.raises(RuntimeError, match="활성화되지 않았습니다"):
        adapter.parse("동성로 식사", settings.reference_now)


def test_unapproved_plan_blocks_even_when_switches_and_key_exist(demo_app):
    settings = replace(
        demo_app.state.settings,
        allow_external_calls=True,
        allow_paid_calls=True,
        gemini_api_key="secret-for-test",
    )
    assert settings.external_adapter_enabled is False
    assert "GEMINI_APPROVAL_NOT_GRANTED" in settings.gemini_gate_reasons


def test_google_api_key_is_detected_but_ignored(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "must-not-be-used")
    settings = load_settings(ROOT)
    assert settings.google_api_key_present is True
    assert settings.gemini_configured is False
    assert settings.effective_gemini_key is None


def test_gemini_rejects_values_outside_shared_contract(monkeypatch, demo_app):
    settings = _approved_settings(demo_app.state.settings)
    adapter = GeminiAdapter(settings)

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"candidates":[{"content":{"parts":[{"text":"{\\"category\\":\\"bar\\"}"}]}}]}'

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: Response())
    with pytest.raises(RuntimeError, match="Gemini 응답을 처리하지 못했습니다"):
        adapter.parse("동성로 식사", settings.reference_now)


@pytest.mark.parametrize("status_code", [401, 403])
def test_gemini_auth_failures_are_not_retried(monkeypatch, demo_app, status_code):
    settings = _approved_settings(demo_app.state.settings)
    adapter = GeminiAdapter(settings)
    calls = []

    def fail_once(request, timeout):
        calls.append(1)
        raise urllib.error.HTTPError(request.full_url, status_code, "denied", {}, io.BytesIO())

    monkeypatch.setattr("urllib.request.urlopen", fail_once)
    with pytest.raises(RuntimeError, match=rf"Gemini 호출 실패\({status_code}\)"):
        adapter.parse("동성로 식사", settings.reference_now)
    assert len(calls) == 1


def test_gemini_transient_timeout_retries_once(monkeypatch, demo_app):
    settings = _approved_settings(demo_app.state.settings)
    adapter = GeminiAdapter(settings)
    calls = []

    def timeout_twice(request, timeout):
        calls.append(1)
        raise TimeoutError("simulated timeout")

    monkeypatch.setattr("urllib.request.urlopen", timeout_twice)
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    with pytest.raises(RuntimeError, match="Gemini 응답을 처리하지 못했습니다"):
        adapter.parse("동성로 식사", settings.reference_now)
    assert len(calls) == 2
    conn = sqlite3.connect(settings.database_path)
    try:
        rows = conn.execute("SELECT status, actual_usd FROM gemini_usage_ledger ORDER BY created_at").fetchall()
    finally:
        conn.close()
    assert rows == [("UNKNOWN_FAILURE", None), ("UNKNOWN_FAILURE", None)]


def test_gemini_settles_known_usage_without_storing_prompt(monkeypatch, demo_app):
    settings = _approved_settings(demo_app.state.settings)
    adapter = GeminiAdapter(settings)

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"candidates":[{"content":{"parts":[{"text":"{\\"region_id\\":\\"dongseongro\\"}"}]}}],"usageMetadata":{"promptTokenCount":100,"candidatesTokenCount":20,"thoughtsTokenCount":5}}'

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: Response())
    adapter.parse("동성로 식사", settings.reference_now)
    conn = sqlite3.connect(settings.database_path)
    try:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(gemini_usage_ledger)")]
        row = conn.execute(
            "SELECT status, input_tokens, output_tokens, actual_usd FROM gemini_usage_ledger"
        ).fetchone()
    finally:
        conn.close()
    assert "prompt" not in columns
    assert row[:3] == ("SETTLED", 100, 25)
    assert row[3] == pytest.approx((100 * 0.3 + 25 * 2.5) / 1_000_000)


def test_gemini_reserves_before_call_and_stops_at_cap(monkeypatch, demo_app):
    settings = _approved_settings(demo_app.state.settings)
    plan = copy.deepcopy(settings.gemini_approval)
    plan["approval"]["approved_project_total_limit_usd"] = 0.0007
    plan["approval"]["approved_daily_limit_usd"] = 0.0007
    settings = replace(settings, gemini_approval=plan)
    called = []
    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: called.append(1))
    with pytest.raises(GeminiBudgetExceeded):
        GeminiAdapter(settings).parse("동성로 식사", settings.reference_now)
    assert called == []


def test_sensitive_identifier_is_blocked_before_reservation(monkeypatch, demo_app):
    settings = _approved_settings(demo_app.state.settings)
    called = []
    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: called.append(1))
    with pytest.raises(RuntimeError, match="전송하지 않았습니다"):
        GeminiAdapter(settings).parse("연락처 010-1234-5678 동성로 식사", settings.reference_now)
    assert called == []
    conn = sqlite3.connect(settings.database_path)
    try:
        table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='gemini_usage_ledger'"
        ).fetchone()
    finally:
        conn.close()
    assert table is None
