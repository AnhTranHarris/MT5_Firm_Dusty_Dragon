from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from dusty_dragon.brokers.health import BrokerHealthSnapshot
from dusty_dragon.brokers.reconciliation import ReconciliationResult
from dusty_dragon.domain.models import OrderIntent
from dusty_dragon.governance.preorder import PreOrderDecision, authorize_preorder
from dusty_dragon.persistence.preorder_audit import PreOrderAuditRepository
from dusty_dragon.portfolio.governor import PortfolioDecision
from dusty_dragon.risk.desk import DeskRiskDecision


@dataclass(frozen=True, slots=True)
class AuditedPreOrderDecision:
    decision: PreOrderDecision
    audit_event_id: str


class PreOrderAuthorizationService:
    """Sovereign authorization boundary: decide first, then immutably audit the decision."""

    def __init__(self, audit_repository: PreOrderAuditRepository, *, policy_id: str) -> None:
        if not policy_id.strip():
            raise ValueError("policy_id is required")
        self._audit_repository = audit_repository
        self._policy_id = policy_id

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
        decision = authorize_preorder(
            intent,
            desk_risk=desk_risk,
            portfolio=portfolio,
            reconciliation=reconciliation,
            broker_health=broker_health,
            policy_id=self._policy_id,
        )
        event_id = self._audit_repository.record(
            intent=intent,
            decision=decision,
            policy_id=self._policy_id,
            occurred_at_utc=occurred_at_utc,
        )
        return AuditedPreOrderDecision(decision=decision, audit_event_id=event_id)
