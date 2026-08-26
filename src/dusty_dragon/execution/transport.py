from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from dusty_dragon.domain.models import ApprovedOrder


class ExecutionStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class ExecutionReceipt:
    status: ExecutionStatus
    broker_order_id: str | None
    message: str


class ExecutionTransport(Protocol):
    """Broker-neutral write boundary. Implementations receive only consumed authority."""

    def submit(self, order: ApprovedOrder) -> ExecutionReceipt: ...
