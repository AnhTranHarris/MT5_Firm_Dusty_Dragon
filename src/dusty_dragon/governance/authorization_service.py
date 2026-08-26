from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from dusty_dragon.brokers.health import BrokerHealthSnapshot
from dusty_dragon.brokers.reconciliation import ReconciliationResult
from dusty_dragon.domain.models import OrderIntent
from dusty_dragon.governance.preorder import PreOrderDecision, authorize_preorder
from dusty_dragon.persistence.authorization_lease import (
    AuthorizationLease,
    AuthorizationLeaseRepository,
)
from dusty_dragon.persistence.execution_reconciliation import ExecutionReconciliationRepository
from dusty_dragon.persistence.preorder_audit import PreOrderAuditRepository
from dusty_dragon.portfolio.governor import PortfolioDecision
from dusty_dragon.risk.desk import DeskRiskDecision


@dataclass(frozen=True, slots=True)
class AuditedPreOrderDecision:
    decision: PreOrderDecision
    audit_event_id: str
    authorization_lease: AuthorizationLease | None


class PreOrderAuthorizationService:
    """Sovereign boundary: decide, audit, then issue short-lived execution authority."""

    def __init__(
        self,
        audit_repository: PreOrderAuditRepository,
        lease_repository: AuthorizationLeaseRepository,
        *,
        financial_policy_id: str,
        operations_policy_id: str,
        lease_ttl_seconds: int,
        execution_reconciliation_repository: ExecutionReconciliationRepository | None = None,
    ) -> None:
        if not financial_policy_id.strip():
            raise ValueError("financial_policy_id is required")
        if not operations_policy_id.strip():
            raise ValueError("operations_policy_id is required")
        if lease_ttl_seconds <= 0:
            raise ValueError("lease_ttl_seconds must be positive")
        self._audit_repository = audit_repository
        self._lease_repository = lease_repository
        self._execution_reconciliation_repository = execution_reconciliation_repository
        self._financial_policy_id = financial_policy_id
        self._operations_policy_id = operations_policy_id
        self._lease_ttl_seconds = lease_ttl_seconds

    def authorize(
        self,
        intent: OrderIntent,
        *,
        desk_risk: DeskRiskDecision,
        portfolio: PortfolioDecision,
        reconciliation: ReconciliationResult,
        broker_health: BrokerHealthSnapshot,
        occurred_at_utc: datetime | None = None,
    ) -> AuditedPreOrderDecision:
        occurred_at = occurred_at_utc or datetime.now(UTC)
        has_pending_execution = False
        if self._execution_reconciliation_repository is not None:
            pending = self._execution_reconciliation_repository.unresolved_for_desk(intent.desk_id)
            has_pending_execution = bool(pending)

        decision = authorize_preorder(
            intent,
            desk_risk=desk_risk,
            portfolio=portfolio,
            reconciliation=reconciliation,
            broker_health=broker_health,
            policy_id=self._financial_policy_id,
            has_pending_execution=has_pending_execution,
        )
        event_id = self._audit_repository.record(
            intent=intent,
            decision=decision,
            policy_id=self._financial_policy_id,
            occurred_at_utc=occurred_at,
        )

        lease: AuthorizationLease | None = None
        if decision.approved_order is not None:
            lease = self._lease_repository.issue(
                decision.approved_order,
                operations_policy_id=self._operations_policy_id,
                audit_event_id=event_id,
                authorized_at_utc=occurred_at,
                ttl_seconds=self._lease_ttl_seconds,
            )

        return AuditedPreOrderDecision(
            decision=decision,
            audit_event_id=event_id,
            authorization_lease=lease,
        )
