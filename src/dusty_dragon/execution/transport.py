from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from dusty_dragon.domain.models import ApprovedOrder


class ExecutionStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True, slots=True)
class ExecutionReceipt:
    status: ExecutionStatus
    broker_order_id: str | None
    message: str

    @property
    def requires_reconciliation(self) -> bool:
        """Broker acceptance or ambiguity must be verified against subsequent broker truth."""

        return self.status in {ExecutionStatus.ACCEPTED, ExecutionStatus.AMBIGUOUS}


class ExecutionTransport(Protocol):
    """Broker-neutral write boundary. Implementations receive only consumed authority."""

    def submit(self, order: ApprovedOrder) -> ExecutionReceipt: ...
