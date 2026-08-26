from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from dusty_dragon.brokers.health import BrokerHealthMonitor, BrokerHealthSnapshot
from dusty_dragon.brokers.mt5_read import BrokerReadState, MT5ReadAdapter
from dusty_dragon.brokers.reconciliation import ReconciliationResult, reconcile_account
from dusty_dragon.persistence.expected_state import ExpectedStateRepository
from dusty_dragon.persistence.observations import ObservationRepository
from dusty_dragon.persistence.reconciliation_audit import ReconciliationAuditRepository


@dataclass(frozen=True, slots=True)
class BrokerObservationResult:
    observed: BrokerReadState
    reconciliation: ReconciliationResult
    health: BrokerHealthSnapshot
    audit_event_id: str


class BrokerObservationService:
    """Observe broker truth, reconcile against durable Dusty state, and audit the result."""

    def __init__(
        self,
        adapter: MT5ReadAdapter,
        observation_repository: ObservationRepository,
        expected_state_repository: ExpectedStateRepository,
        audit_repository: ReconciliationAuditRepository,
        health_monitor: BrokerHealthMonitor,
        *,
        observation_policy_id: str,
        operations_policy_id: str,
    ) -> None:
        if not observation_policy_id.strip():
            raise ValueError("observation_policy_id is required")
        if not operations_policy_id.strip():
            raise ValueError("operations_policy_id is required")
        self._adapter = adapter
        self._observation_repository = observation_repository
        self._expected_state_repository = expected_state_repository
        self._audit_repository = audit_repository
        self._health_monitor = health_monitor
        self._observation_policy_id = observation_policy_id
        self._operations_policy_id = operations_policy_id

    def observe_and_reconcile(
        self,
        account_id: str,
        *,
        observed_at_utc: datetime | None = None,
    ) -> BrokerObservationResult:
        expected = self._expected_state_repository.load(account_id)
        observed = self._adapter.read_state(observed_at_utc)
        if observed.account.account_id != account_id:
            raise ValueError("adapter account does not match requested expected state")

        self._observation_repository.persist_equity_snapshot(
            observed.account,
            policy_id=self._observation_policy_id,
        )
        reconciliation = reconcile_account(
            expected=expected.account,
            observed=observed.account,
            expected_positions=expected.positions,
            observed_positions=observed.positions,
        )
        audit_event_id = self._audit_repository.record(
            account_id=account_id,
            result=reconciliation,
            policy_id=self._operations_policy_id,
            occurred_at_utc=observed.account.observed_at_utc,
        )
        health = self._health_monitor.observe(reconciliation.status)
        return BrokerObservationResult(
            observed=observed,
            reconciliation=reconciliation,
            health=health,
            audit_event_id=audit_event_id,
        )
