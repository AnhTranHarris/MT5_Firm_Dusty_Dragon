from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from dusty_dragon.brokers.reconciliation import ReconciliationResult


@dataclass(slots=True)
class ReconciliationAuditRepository:
    """Persist immutable reconciliation outcomes in the institutional audit ledger."""

    connection: sqlite3.Connection

    def record(
        self,
        *,
        account_id: str,
        result: ReconciliationResult,
        policy_id: str,
        occurred_at_utc: datetime | None = None,
    ) -> str:
        if not account_id.strip():
            raise ValueError("account_id is required")
        if not policy_id.strip():
            raise ValueError("policy_id is required")

        occurred_at = occurred_at_utc or datetime.now(UTC)
        if occurred_at.tzinfo is None or occurred_at.utcoffset() != UTC.utcoffset(occurred_at):
            raise ValueError("occurred_at_utc must be timezone-aware UTC")

        event_id = f"reconciliation-{uuid4()}"
        payload = json.dumps(
            {
                "status": result.status.value,
                "reasons": list(result.reasons),
                "safe_for_new_orders": result.safe_for_new_orders,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO audit_events(
                    event_id, occurred_at_utc, event_type, actor,
                    subject_id, policy_id, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    occurred_at.isoformat(),
                    "BROKER_RECONCILIATION",
                    "DUSTY_CORE",
                    account_id,
                    policy_id,
                    payload,
                ),
            )
        return event_id
