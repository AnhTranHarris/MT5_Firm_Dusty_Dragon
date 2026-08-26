from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from dusty_dragon.brokers.mt5_history import (
    BrokerExecutionHistory,
    BrokerOrderHistoryStatus,
)
from dusty_dragon.persistence.execution_reconciliation import (
    ExecutionReconciliationRecord,
    ExecutionReconciliationRepository,
    ExecutionReconciliationState,
)


@dataclass(frozen=True, slots=True)
class ExecutionResolutionResult:
    record: ExecutionReconciliationRecord
    resolved: bool


class ExecutionReconciliationService:
    """Resolve pending execution outcomes only from strong broker evidence."""

    def __init__(self, repository: ExecutionReconciliationRepository) -> None:
        self._repository = repository

    def resolve_from_history(
        self,
        reconciliation_id: str,
        *,
        history: BrokerExecutionHistory,
        resolved_at_utc: datetime,
    ) -> ExecutionResolutionResult:
        record = self._repository.get(reconciliation_id)
        if record is None:
            raise LookupError("execution reconciliation not found")
        if record.state is not ExecutionReconciliationState.UNRESOLVED:
            return ExecutionResolutionResult(record=record, resolved=False)
        if record.broker_order_id is None:
            return ExecutionResolutionResult(record=record, resolved=False)

        matching_deal = next(
            (
                deal
                for deal in history.deals
                if deal.broker_order_id == record.broker_order_id
            ),
            None,
        )
        if matching_deal is not None:
            resolved = self._repository.resolve(
                reconciliation_id,
                state=ExecutionReconciliationState.CONFIRMED_EXECUTED,
                evidence_id=f"broker-deal:{matching_deal.broker_deal_id}",
                resolved_at_utc=resolved_at_utc,
            )
            return ExecutionResolutionResult(record=resolved, resolved=True)

        matching_order = next(
            (
                order
                for order in history.orders
                if order.broker_order_id == record.broker_order_id
            ),
            None,
        )
        if matching_order is None:
            return ExecutionResolutionResult(record=record, resolved=False)

        if matching_order.status is BrokerOrderHistoryStatus.FILLED:
            resolved = self._repository.resolve(
                reconciliation_id,
                state=ExecutionReconciliationState.CONFIRMED_EXECUTED,
                evidence_id=(
                    f"broker-order:{matching_order.broker_order_id}:filled"
                ),
                resolved_at_utc=resolved_at_utc,
            )
            return ExecutionResolutionResult(record=resolved, resolved=True)

        if matching_order.status in {
            BrokerOrderHistoryStatus.CANCELED,
            BrokerOrderHistoryStatus.REJECTED,
        }:
            resolved = self._repository.resolve(
                reconciliation_id,
                state=ExecutionReconciliationState.CONFIRMED_NOT_EXECUTED,
                evidence_id=(
                    f"broker-order:{matching_order.broker_order_id}:"
                    f"{matching_order.status.value.lower()}"
                ),
                resolved_at_utc=resolved_at_utc,
            )
            return ExecutionResolutionResult(record=resolved, resolved=True)

        return ExecutionResolutionResult(record=record, resolved=False)
