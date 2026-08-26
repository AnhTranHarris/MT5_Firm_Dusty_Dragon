from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from dusty_dragon.execution.transport import ExecutionReceipt
from dusty_dragon.persistence.authorization_lease import LeaseConsumeStatus


@dataclass(slots=True)
class ExecutionAuditRepository:
    connection: sqlite3.Connection

    def record(
        self,
        *,
        lease_id: str,
        lease_status: LeaseConsumeStatus,
        receipt: ExecutionReceipt | None,
        transport_error: str | None,
        occurred_at_utc: datetime,
    ) -> str:
        invalid_timezone = (
            occurred_at_utc.tzinfo is None
            or occurred_at_utc.utcoffset() != UTC.utcoffset(occurred_at_utc)
        )
        if invalid_timezone:
            raise ValueError("occurred_at_utc must be timezone-aware UTC")

        event_id = f"execution-{uuid4()}"
        payload = json.dumps(
            {
                "lease_id": lease_id,
                "lease_status": lease_status.value,
                "receipt": None
                if receipt is None
                else {
                    "status": receipt.status.value,
                    "broker_order_id": receipt.broker_order_id,
                    "message": receipt.message,
                    "requires_reconciliation": receipt.requires_reconciliation,
                },
                "transport_error": transport_error,
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
                ) VALUES (?, ?, ?, ?, ?, NULL, ?)
                """,
                (
                    event_id,
                    occurred_at_utc.isoformat(),
                    "EXECUTION_ATTEMPT",
                    "DUSTY_EXECUTION_GATE",
                    lease_id,
                    payload,
                ),
            )
        return event_id
