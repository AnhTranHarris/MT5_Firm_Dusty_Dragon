from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from dusty_dragon.execution.transport import ExecutionReceipt, ExecutionTransport
from dusty_dragon.persistence.authorization_lease import (
    AuthorizationLeaseRepository,
    LeaseConsumeStatus,
)
from dusty_dragon.persistence.execution_audit import ExecutionAuditRepository


@dataclass(frozen=True, slots=True)
class ExecutionAttempt:
    lease_status: LeaseConsumeStatus
    receipt: ExecutionReceipt | None
    audit_event_id: str
    transport_error: str | None = None

    @property
    def submitted(self) -> bool:
        return self.lease_status is LeaseConsumeStatus.CONSUMED and self.receipt is not None

    @property
    def requires_broker_reconciliation(self) -> bool:
        if self.transport_error is not None:
            return True
        return self.receipt is not None and self.receipt.requires_reconciliation


class ExecutionService:
    """Consume one-time authority, invoke transport, and immutably audit the outcome."""

    def __init__(
        self,
        lease_repository: AuthorizationLeaseRepository,
        audit_repository: ExecutionAuditRepository,
        transport: ExecutionTransport,
    ) -> None:
        self._lease_repository = lease_repository
        self._audit_repository = audit_repository
        self._transport = transport

    def execute(self, lease_id: str, *, consumed_at_utc: datetime) -> ExecutionAttempt:
        consumed = self._lease_repository.consume(
            lease_id,
            consumed_at_utc=consumed_at_utc,
        )
        if not consumed.consumed or consumed.lease is None:
            event_id = self._audit_repository.record(
                lease_id=lease_id,
                lease_status=consumed.status,
                receipt=None,
                transport_error=None,
                occurred_at_utc=consumed_at_utc,
            )
            return ExecutionAttempt(
                lease_status=consumed.status,
                receipt=None,
                audit_event_id=event_id,
            )

        receipt: ExecutionReceipt | None = None
        transport_error: str | None = None
        try:
            receipt = self._transport.submit(consumed.lease.order)
        except Exception as exc:  # transport uncertainty must be reconciled, never retried blindly
            transport_error = f"{type(exc).__name__}: {exc}"

        event_id = self._audit_repository.record(
            lease_id=lease_id,
            lease_status=LeaseConsumeStatus.CONSUMED,
            receipt=receipt,
            transport_error=transport_error,
            occurred_at_utc=consumed_at_utc,
        )
        return ExecutionAttempt(
            lease_status=LeaseConsumeStatus.CONSUMED,
            receipt=receipt,
            audit_event_id=event_id,
            transport_error=transport_error,
        )
