from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from dusty_dragon.brokers.mt5_read import BrokerReadState, MT5ReadAdapter
from dusty_dragon.brokers.reconciliation import ReconciliationResult, reconcile_account
from dusty_dragon.persistence.observations import ObservationRepository


@dataclass(frozen=True, slots=True)
class BrokerObservationResult:
    observed: BrokerReadState
    reconciliation: ReconciliationResult


class BrokerObservationService:
    """Read, persist, and reconcile broker truth without any execution authority."""

    def __init__(
        self,
        adapter: MT5ReadAdapter,
        repository: ObservationRepository,
        *,
        policy_id: str,
    ) -> None:
        if not policy_id.strip():
            raise ValueError("policy_id is required")
        self._adapter = adapter
        self._repository = repository
        self._policy_id = policy_id

    def observe_and_reconcile(
        self,
        expected: BrokerReadState,
        *,
        observed_at_utc: datetime | None = None,
    ) -> BrokerObservationResult:
        observed = self._adapter.read_state(observed_at_utc)
        self._repository.persist_equity_snapshot(observed.account, policy_id=self._policy_id)
        reconciliation = reconcile_account(
            expected=expected.account,
            observed=observed.account,
            expected_positions=expected.positions,
            observed_positions=observed.positions,
        )
        return BrokerObservationResult(observed=observed, reconciliation=reconciliation)
