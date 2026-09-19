from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


SEOUL = timezone(timedelta(hours=9), name="Asia/Seoul")


class GeminiBudgetExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class UsageReservation:
    reservation_id: str
    reserved_usd: float


class GeminiUsageLedger:
    """Local, prompt-free reservation ledger for the approved Gemini budget.

    It is deliberately conservative: a request with unknown provider usage
    keeps its full reservation. The ledger limits only this application's
    calls, so the approval plan still recommends a dedicated provider project.
    """

    def __init__(self, settings):
        self.settings = settings
        plan = settings.gemini_approval
        self.cost_plan = plan["cost_plan"]
        self.approval = plan["approval"]

    def _connect(self) -> sqlite3.Connection:
        self.settings.database_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.settings.database_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS gemini_usage_ledger (
                reservation_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                local_date TEXT NOT NULL,
                model TEXT NOT NULL,
                reserved_usd REAL NOT NULL CHECK (reserved_usd >= 0),
                actual_usd REAL,
                input_tokens INTEGER,
                output_tokens INTEGER,
                status TEXT NOT NULL
            )
            """
        )
        return conn

    @property
    def max_attempts(self) -> int:
        return int(self.cost_plan["max_attempts"])

    @property
    def reservation_cost(self) -> float:
        return (
            int(self.cost_plan["max_input_tokens_per_attempt"])
            * float(self.cost_plan["input_usd_per_million_tokens"])
            + int(self.cost_plan["max_output_tokens_per_attempt"])
            * float(self.cost_plan["output_usd_per_million_tokens_including_thinking"])
        ) / 1_000_000

    def reserve(self, model: str) -> UsageReservation:
        now = datetime.now(SEOUL)
        local_date = now.date().isoformat()
        reserve_usd = self.reservation_cost
        daily_limit = float(self.approval["approved_daily_limit_usd"])
        total_limit = float(self.approval["approved_project_total_limit_usd"])
        reservation_id = str(uuid.uuid4())
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            total = float(
                conn.execute(
                    "SELECT COALESCE(SUM(COALESCE(actual_usd, reserved_usd)), 0) FROM gemini_usage_ledger"
                ).fetchone()[0]
            )
            daily = float(
                conn.execute(
                    """
                    SELECT COALESCE(SUM(COALESCE(actual_usd, reserved_usd)), 0)
                    FROM gemini_usage_ledger WHERE local_date = ?
                    """,
                    (local_date,),
                ).fetchone()[0]
            )
            epsilon = 1e-12
            if total + reserve_usd > total_limit + epsilon:
                raise GeminiBudgetExceeded("Gemini 프로젝트 총 한도를 초과할 수 있어 호출하지 않았습니다.")
            if daily + reserve_usd > daily_limit + epsilon:
                raise GeminiBudgetExceeded("Gemini 일 한도를 초과할 수 있어 호출하지 않았습니다.")
            conn.execute(
                """
                INSERT INTO gemini_usage_ledger
                  (reservation_id, created_at, local_date, model, reserved_usd, status)
                VALUES (?, ?, ?, ?, ?, 'RESERVED')
                """,
                (reservation_id, now.isoformat(), local_date, model, reserve_usd),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return UsageReservation(reservation_id=reservation_id, reserved_usd=reserve_usd)

    def settle(self, reservation_id: str, usage: dict | None) -> bool:
        if not isinstance(usage, dict):
            return False
        input_tokens = usage.get("promptTokenCount")
        output_tokens = usage.get("candidatesTokenCount")
        thinking_tokens = usage.get("thoughtsTokenCount", 0)
        try:
            input_count = int(input_tokens)
            if output_tokens is None and usage.get("totalTokenCount") is not None:
                output_count = max(int(usage["totalTokenCount"]) - input_count, 0)
            else:
                output_count = int(output_tokens) + int(thinking_tokens or 0)
        except (TypeError, ValueError):
            return False
        if input_count < 0 or output_count < 0:
            return False
        actual_usd = (
            input_count * float(self.cost_plan["input_usd_per_million_tokens"])
            + output_count * float(self.cost_plan["output_usd_per_million_tokens_including_thinking"])
        ) / 1_000_000
        conn = self._connect()
        try:
            conn.execute(
                """
                UPDATE gemini_usage_ledger
                SET actual_usd = ?, input_tokens = ?, output_tokens = ?, status = 'SETTLED'
                WHERE reservation_id = ?
                """,
                (actual_usd, input_count, output_count, reservation_id),
            )
            conn.commit()
        finally:
            conn.close()
        return True

    def keep_reserved(self, reservation_id: str) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                UPDATE gemini_usage_ledger SET status = 'UNKNOWN_FAILURE'
                WHERE reservation_id = ? AND status = 'RESERVED'
                """,
                (reservation_id,),
            )
            conn.commit()
        finally:
            conn.close()

    def totals(self) -> dict[str, float]:
        today = datetime.now(SEOUL).date().isoformat()
        conn = self._connect()
        try:
            total = float(
                conn.execute(
                    "SELECT COALESCE(SUM(COALESCE(actual_usd, reserved_usd)), 0) FROM gemini_usage_ledger"
                ).fetchone()[0]
            )
            daily = float(
                conn.execute(
                    """
                    SELECT COALESCE(SUM(COALESCE(actual_usd, reserved_usd)), 0)
                    FROM gemini_usage_ledger WHERE local_date = ?
                    """,
                    (today,),
                ).fetchone()[0]
            )
            return {"total_usd": total, "daily_usd": daily}
        finally:
            conn.close()
