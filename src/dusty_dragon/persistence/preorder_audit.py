from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from dusty_dragon.domain.models import OrderIntent
from dusty_dragon.governance.preorder import PreOrderDecision


@dataclass(slots=True)
class PreOrderAuditRepository:
    """Persist immutable sovereign authorization decisions in the audit ledger."""

    connection: sqlite3.Connection

    def record(
        self,
        *,
        intent: OrderIntent,
        decision: PreOrderDecision,
        policy_id: str,
        occurred_at_utc: datetime | None = None,
    ) -> str:
        if not policy_id.strip():
            raise ValueError("policy_id is required")

        occurred_at = occurred_at_utc or datetime.now(UTC)
        if occurred_at.tzinfo is None or occurred_at.utcoffset() != UTC.utcoffset(occurred_at):
            raise ValueError("occurred_at_utc must be timezone-aware UTC")

        event_id = f"preorder-{uuid4()}"
        approved = decision.approved_order
        payload = json.dumps(
            {
                "status": decision.status.value,
                "reasons": list(decision.reasons),
                "intent": {
                    "desk_id": intent.desk_id,
                    "instrument_id": intent.instrument_id,
                    "side": intent.side,
                    "requested_risk_fraction": intent.requested_risk_fraction,
                },
                "approved_order": None
                if approved is None
                else {
                    "desk_id": approved.desk_id,
                    "instrument_id": approved.instrument_id,
                    "side": approved.side,
                    "approved_risk_fraction": approved.approved_risk_fraction,
                    "policy_id": approved.policy_id,
                },
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
                    "PREORDER_AUTHORIZATION",
                    "DUSTY_CORE",
                    intent.desk_id,
                    policy_id,
                    payload,
                ),
            )
        return event_id
