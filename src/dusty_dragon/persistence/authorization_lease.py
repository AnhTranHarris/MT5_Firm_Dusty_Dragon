from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import uuid4

from dusty_dragon.domain.models import ApprovedOrder


class LeaseConsumeStatus(StrEnum):
    CONSUMED = "CONSUMED"
    EXPIRED = "EXPIRED"
    ALREADY_CONSUMED = "ALREADY_CONSUMED"
    NOT_FOUND = "NOT_FOUND"


@dataclass(frozen=True, slots=True)
class AuthorizationLease:
    lease_id: str
    order: ApprovedOrder
    operations_policy_id: str
    audit_event_id: str
    authorized_at_utc: datetime
    expires_at_utc: datetime
    consumed_at_utc: datetime | None = None

    @property
    def consumed(self) -> bool:
        return self.consumed_at_utc is not None

    def is_fresh_at(self, now_utc: datetime) -> bool:
        _require_utc(now_utc, "now_utc")
        return not self.consumed and now_utc <= self.expires_at_utc


@dataclass(frozen=True, slots=True)
class LeaseConsumeResult:
    status: LeaseConsumeStatus
    lease: AuthorizationLease | None

    @property
    def consumed(self) -> bool:
        return self.status is LeaseConsumeStatus.CONSUMED


@dataclass(slots=True)
class AuthorizationLeaseRepository:
    """Persist short-lived, single-use authority separately from immutable order approval."""

    connection: sqlite3.Connection

    def issue(
        self,
        order: ApprovedOrder,
        *,
        operations_policy_id: str,
        audit_event_id: str,
        authorized_at_utc: datetime,
        ttl_seconds: int,
    ) -> AuthorizationLease:
        if not operations_policy_id.strip():
            raise ValueError("operations_policy_id is required")
        if not audit_event_id.strip():
            raise ValueError("audit_event_id is required")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        _require_utc(authorized_at_utc, "authorized_at_utc")

        expires_at = authorized_at_utc + timedelta(seconds=ttl_seconds)
        lease = AuthorizationLease(
            lease_id=f"authorization-{uuid4()}",
            order=order,
            operations_policy_id=operations_policy_id,
            audit_event_id=audit_event_id,
            authorized_at_utc=authorized_at_utc,
            expires_at_utc=expires_at,
        )
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO authorization_leases(
                    lease_id, desk_id, instrument_id, side, approved_risk_fraction,
                    financial_policy_id, operations_policy_id, authorized_at_utc,
                    expires_at_utc, consumed_at_utc, audit_event_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
                """,
                (
                    lease.lease_id,
                    order.desk_id,
                    order.instrument_id,
                    order.side,
                    order.approved_risk_fraction,
                    order.policy_id,
                    operations_policy_id,
                    authorized_at_utc.isoformat(),
                    expires_at.isoformat(),
                    audit_event_id,
                ),
            )
        return lease

    def consume(self, lease_id: str, *, consumed_at_utc: datetime) -> LeaseConsumeResult:
        if not lease_id.strip():
            raise ValueError("lease_id is required")
        _require_utc(consumed_at_utc, "consumed_at_utc")

        with self.connection:
            cursor = self.connection.execute(
                """
                UPDATE authorization_leases
                SET consumed_at_utc = ?
                WHERE lease_id = ?
                  AND consumed_at_utc IS NULL
                  AND expires_at_utc >= ?
                """,
                (consumed_at_utc.isoformat(), lease_id, consumed_at_utc.isoformat()),
            )

        lease = self.get(lease_id)
        if cursor.rowcount == 1:
            return LeaseConsumeResult(status=LeaseConsumeStatus.CONSUMED, lease=lease)
        if lease is None:
            return LeaseConsumeResult(status=LeaseConsumeStatus.NOT_FOUND, lease=None)
        if lease.consumed:
            return LeaseConsumeResult(status=LeaseConsumeStatus.ALREADY_CONSUMED, lease=lease)
        return LeaseConsumeResult(status=LeaseConsumeStatus.EXPIRED, lease=lease)

    def get(self, lease_id: str) -> AuthorizationLease | None:
        row = self.connection.execute(
            "SELECT * FROM authorization_leases WHERE lease_id = ?",
            (lease_id,),
        ).fetchone()
        if row is None:
            return None
        return _lease_from_row(row)


def _lease_from_row(row: sqlite3.Row) -> AuthorizationLease:
    consumed_at = row["consumed_at_utc"]
    return AuthorizationLease(
        lease_id=str(row["lease_id"]),
        order=ApprovedOrder(
            desk_id=str(row["desk_id"]),
            instrument_id=str(row["instrument_id"]),
            side=str(row["side"]),
            approved_risk_fraction=float(row["approved_risk_fraction"]),
            policy_id=str(row["financial_policy_id"]),
        ),
        operations_policy_id=str(row["operations_policy_id"]),
        audit_event_id=str(row["audit_event_id"]),
        authorized_at_utc=datetime.fromisoformat(str(row["authorized_at_utc"])),
        expires_at_utc=datetime.fromisoformat(str(row["expires_at_utc"])),
        consumed_at_utc=datetime.fromisoformat(str(consumed_at)) if consumed_at else None,
    )


def _require_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be timezone-aware UTC")
