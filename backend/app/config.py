from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _resolve_path(raw: str, root: Path) -> Path:
    value = raw.strip()
    if value.startswith("sqlite:///"):
        value = value[len("sqlite:///") :]
    path = Path(value)
    return path if path.is_absolute() else (root / path).resolve()


@dataclass(frozen=True)
class Settings:
    root: Path
    policy_path: Path
    data_dir: Path
    database_path: Path
    data_mode: str
    parser_mode: str
    explanation_mode: str
    map_mode: str
    allow_external_calls: bool
    allow_paid_calls: bool
    cors_origins: tuple[str, ...]
    llm_provider: str | None
    llm_model: str | None
    llm_api_key: str | None
    gemini_api_key: str | None
    google_api_key_present: bool
    gemini_base_url: str
    gemini_timeout_ms: int
    gemini_approval_path: Path
    gemini_approval: dict[str, Any]
    policy: dict[str, Any]

    @property
    def snapshot_id(self) -> str:
        return str(self.policy.get("snapshot_id") or "demo-v2-20260919")

    @property
    def policy_version(self) -> str:
        return str(self.policy["policy_version"])

    @property
    def reference_now(self) -> str:
        return str(self.policy["clock"]["demo_now"])

    @property
    def gemini_configured(self) -> bool:
        # v3.2 key policy deliberately ignores GOOGLE_API_KEY and generic
        # LLM_API_KEY so another project's credential cannot win implicitly.
        return bool(self.gemini_api_key)

    @property
    def effective_gemini_key(self) -> str | None:
        return self.gemini_api_key

    @property
    def gemini_gate_reasons(self) -> tuple[str, ...]:
        plan = self.gemini_approval
        proposal = plan.get("proposal") if isinstance(plan.get("proposal"), dict) else {}
        gate = plan.get("data_api_gate") if isinstance(plan.get("data_api_gate"), dict) else {}
        approval = plan.get("approval") if isinstance(plan.get("approval"), dict) else {}
        cost = plan.get("cost_plan") if isinstance(plan.get("cost_plan"), dict) else {}
        reasons: list[str] = []
        if self.llm_provider != "gemini":
            reasons.append("PROVIDER_NOT_GEMINI")
        if plan.get("status") != "APPROVED" or plan.get("llm_enabled") is not True:
            reasons.append("GEMINI_APPROVAL_NOT_GRANTED")
        if gate.get("status") != "PASSED" or not gate.get("evidence"):
            reasons.append("DATA_API_GATE_NOT_PASSED")
        if approval.get("approved") is not True or not approval.get("approved_by") or not approval.get("approved_at"):
            reasons.append("APPROVAL_RECORD_INCOMPLETE")
        else:
            try:
                datetime.fromisoformat(str(approval["approved_at"]))
            except ValueError:
                reasons.append("APPROVAL_TIME_INVALID")
        approved_model = approval.get("approved_model")
        if not approved_model or approved_model != proposal.get("model") or approved_model != self.llm_model:
            reasons.append("MODEL_NOT_APPROVED")
        allowed_scope = proposal.get("transmission_allowed")
        approved_scope = approval.get("approved_transmission_scope")
        if (
            not isinstance(allowed_scope, list)
            or not isinstance(approved_scope, list)
            or not approved_scope
            or any(item not in allowed_scope for item in approved_scope)
        ):
            reasons.append("TRANSMISSION_SCOPE_NOT_APPROVED")
        total_limit = approval.get("approved_project_total_limit_usd")
        daily_limit = approval.get("approved_daily_limit_usd")
        try:
            limits_valid = (
                0 < float(daily_limit) <= float(cost.get("daily_limit"))
                and 0 < float(total_limit) <= float(cost.get("project_total_limit"))
                and float(daily_limit) <= float(total_limit)
            )
        except (TypeError, ValueError):
            limits_valid = False
        if not limits_valid:
            reasons.append("COST_LIMIT_NOT_APPROVED")
        return tuple(reasons)

    @property
    def external_adapter_enabled(self) -> bool:
        # External calls can incur provider charges. Keep both the network
        # switch and the explicit cost approval enabled before a provider is
        # reachable from the request path.
        return (
            self.allow_external_calls
            and self.allow_paid_calls
            and self.gemini_configured
            and not self.gemini_gate_reasons
        )


def load_settings(root: Path | None = None) -> Settings:
    project_root = (root or ROOT).resolve()
    policy_path = _resolve_path(os.getenv("POLICY_PATH", "config/policy.v2.json"), project_root)
    if not policy_path.exists():
        raise RuntimeError(f"정책 파일을 찾을 수 없습니다: {policy_path}")
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    gemini_approval_path = _resolve_path(
        os.getenv("GEMINI_APPROVAL_PATH", "config/gemini_approval_plan.json"), project_root
    )
    if gemini_approval_path.exists():
        gemini_approval = json.loads(gemini_approval_path.read_text(encoding="utf-8"))
    else:
        # Missing approval state must fail closed without making local/demo
        # startup depend on an external integration file.
        gemini_approval = {
            "status": "MISSING",
            "llm_enabled": False,
            "data_api_gate": {"status": "NOT_PASSED", "evidence": []},
            "proposal": {},
            "cost_plan": {},
            "approval": {},
        }
    database_path = _resolve_path(
        os.getenv("DATABASE_URL", "sqlite:///./var/consumer_compass_demo.db"), project_root
    )
    origins = tuple(x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if x.strip())
    data_mode = os.getenv("DATA_MODE", policy["execution"]["data_mode"])
    data_dir = _resolve_path(os.getenv("DATA_DIR", f"data/{data_mode}"), project_root)
    return Settings(
        root=project_root,
        policy_path=policy_path,
        data_dir=data_dir,
        database_path=database_path,
        data_mode=data_mode,
        parser_mode=os.getenv("PARSER_MODE", policy["execution"]["parser_mode"]),
        explanation_mode=os.getenv("EXPLANATION_MODE", policy["execution"]["explanation_mode"]),
        map_mode=os.getenv("MAP_MODE", policy["execution"]["map_mode"]),
        allow_external_calls=_bool_env("ALLOW_EXTERNAL_CALLS", policy["execution"]["external_calls_enabled"]),
        allow_paid_calls=_bool_env("ALLOW_PAID_CALLS", policy["execution"]["paid_calls_approved"]),
        cors_origins=origins,
        llm_provider=os.getenv("LLM_PROVIDER") or ("gemini" if gemini_approval.get("proposal", {}).get("model") else None),
        llm_model=(
            os.getenv("GEMINI_MODEL")
            or os.getenv("LLM_MODEL")
            or gemini_approval.get("proposal", {}).get("model")
            or None
        ),
        llm_api_key=os.getenv("LLM_API_KEY") or None,
        gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
        google_api_key_present=bool(os.getenv("GOOGLE_API_KEY")),
        gemini_base_url=os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/"),
        gemini_timeout_ms=int(os.getenv("GEMINI_TIMEOUT_MS", "5000")),
        gemini_approval_path=gemini_approval_path,
        gemini_approval=gemini_approval,
        policy=policy,
    )
