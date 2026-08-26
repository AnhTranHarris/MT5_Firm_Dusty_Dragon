from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from dusty_dragon.execution.transport import ExecutionReceipt, ExecutionTransport
from dusty_dragon.persistence.authorization_lease import (
    AuthorizationLeaseRepository,
    LeaseConsumeStatus,
)
from dusty_dragon.persistence.execution_audit import ExecutionAuditRepository
from dusty_dragon.persistence.execution_reconciliation import (
    ExecutionReconciliationRecord,
    ExecutionReconciliationRepository,
)


@dataclass(frozen=True, slots=True)
class ExecutionAttempt:
    lease_status: LeaseConsumeStatus
    receipt: ExecutionReceipt | None
    audit_event_id: str
    reconciliation: ExecutionReconciliationRecord | None
    transport_error: str | None = None

    @property
    def submitted(self) -> bool:
        return self.lease_status is LeaseConsumeStatus.CONSUMED and self.receipt is not None

    @property
    def requires_broker_reconciliation(self) -> bool:
        return self.reconciliation is not None


class ExecutionService:
    """Consume authority, invoke transport, audit outcome, and track unresolved broker truth."""

    def __init__(
        self,
        lease_repository: AuthorizationLeaseRepository,
        audit_repository: ExecutionAuditRepository,
        reconciliation_repository: ExecutionReconciliationRepository,
        transport: ExecutionTransport,
    ) -> None:
        self._lease_repository = lease_repository
        self._audit_repository = audit_repository
        self._reconciliation_repository = reconciliation_repository
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
                reconciliation=None,
            )

        receipt: ExecutionReceipt | None = None
        transport_error: str | None = None
        reconciliation: ExecutionReconciliationRecord | None = None
        try:
            receipt = self._transport.submit(consumed.lease.order)
        except Exception as exc:  # uncertain broker outcome must never be retried blindly
            transport_error = f"{type(exc).__name__}: {exc}"
            reconciliation = self._reconciliation_repository.open_for_transport_error(
                lease_id=lease_id,
                order=consumed.lease.order,
                opened_at_utc=consumed_at_utc,
            )
        else:
            reconciliation = self._reconciliation_repository.open_for_receipt(
                lease_id=lease_id,
                order=consumed.lease.order,
                receipt=receipt,
                opened_at_utc=consumed_at_utc,
            )

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
            reconciliation=reconciliation,
            transport_error=transport_error,
        )
