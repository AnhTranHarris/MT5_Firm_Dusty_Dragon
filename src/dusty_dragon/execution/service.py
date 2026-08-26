from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from dusty_dragon.execution.transport import ExecutionReceipt, ExecutionTransport
from dusty_dragon.persistence.authorization_lease import (
    AuthorizationLeaseRepository,
    LeaseConsumeStatus,
)


@dataclass(frozen=True, slots=True)
class ExecutionAttempt:
    lease_status: LeaseConsumeStatus
    receipt: ExecutionReceipt | None

    @property
    def submitted(self) -> bool:
        return self.lease_status is LeaseConsumeStatus.CONSUMED and self.receipt is not None


class ExecutionService:
    """Consume one-time authority before invoking any broker write transport."""

    def __init__(
        self,
        lease_repository: AuthorizationLeaseRepository,
        transport: ExecutionTransport,
    ) -> None:
        self._lease_repository = lease_repository
        self._transport = transport

    def execute(self, lease_id: str, *, consumed_at_utc: datetime) -> ExecutionAttempt:
        consumed = self._lease_repository.consume(
            lease_id,
            consumed_at_utc=consumed_at_utc,
        )
        if not consumed.consumed or consumed.lease is None:
            return ExecutionAttempt(lease_status=consumed.status, receipt=None)

        receipt = self._transport.submit(consumed.lease.order)
        return ExecutionAttempt(
            lease_status=LeaseConsumeStatus.CONSUMED,
            receipt=receipt,
        )
