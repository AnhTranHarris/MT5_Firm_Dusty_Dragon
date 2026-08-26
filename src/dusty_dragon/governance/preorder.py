from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from dusty_dragon.brokers.health import BrokerHealthSnapshot
from dusty_dragon.brokers.reconciliation import ReconciliationResult
from dusty_dragon.domain.models import ApprovedOrder, OrderIntent
from dusty_dragon.portfolio.governor import PortfolioDecision
from dusty_dragon.risk.desk import DeskRiskDecision


class PreOrderStatus(StrEnum):
    APPROVED = "APPROVED"
    DESK_RISK_REJECTED = "DESK_RISK_REJECTED"
    PORTFOLIO_RISK_REJECTED = "PORTFOLIO_RISK_REJECTED"
    RECONCILIATION_REJECTED = "RECONCILIATION_REJECTED"
    BROKER_HEALTH_REJECTED = "BROKER_HEALTH_REJECTED"
    PENDING_EXECUTION_REJECTED = "PENDING_EXECUTION_REJECTED"
    INVALID_INTENT = "INVALID_INTENT"


@dataclass(frozen=True, slots=True)
class PreOrderDecision:
    status: PreOrderStatus
    approved_order: ApprovedOrder | None
    reasons: tuple[str, ...]

    @property
    def approved(self) -> bool:
        return self.status is PreOrderStatus.APPROVED and self.approved_order is not None


def authorize_preorder(
    intent: OrderIntent,
    *,
    desk_risk: DeskRiskDecision,
    portfolio: PortfolioDecision,
    reconciliation: ReconciliationResult,
    broker_health: BrokerHealthSnapshot,
    policy_id: str,
    has_pending_execution: bool = False,
) -> PreOrderDecision:
    """Authorize capital exposure only when every independent safety authority passes."""

    if not policy_id.strip() or intent.requested_risk_fraction <= 0:
        return PreOrderDecision(
            status=PreOrderStatus.INVALID_INTENT,
            approved_order=None,
            reasons=("policy_id and positive requested risk are required",),
        )

    if has_pending_execution:
        return PreOrderDecision(
            status=PreOrderStatus.PENDING_EXECUTION_REJECTED,
            approved_order=None,
            reasons=("desk has unresolved broker execution outcome",),
        )

    if not desk_risk.may_add_new_risk:
        reasons = desk_risk.reasons or ("desk risk governor blocked new risk",)
        return PreOrderDecision(
            status=PreOrderStatus.DESK_RISK_REJECTED,
            approved_order=None,
            reasons=reasons,
        )

    if not portfolio.allowed:
        return PreOrderDecision(
            status=PreOrderStatus.PORTFOLIO_RISK_REJECTED,
            approved_order=None,
            reasons=(portfolio.reason,),
        )

    if not reconciliation.safe_for_new_orders:
        reasons = reconciliation.reasons or ("broker reconciliation is not safe",)
        return PreOrderDecision(
            status=PreOrderStatus.RECONCILIATION_REJECTED,
            approved_order=None,
            reasons=reasons,
        )

    if not broker_health.safe_for_new_orders:
        return PreOrderDecision(
            status=PreOrderStatus.BROKER_HEALTH_REJECTED,
            approved_order=None,
            reasons=(f"broker operational health is {broker_health.state}",),
        )

    return PreOrderDecision(
        status=PreOrderStatus.APPROVED,
        approved_order=ApprovedOrder(
            desk_id=intent.desk_id,
            instrument_id=intent.instrument_id,
            side=intent.side,
            approved_risk_fraction=intent.requested_risk_fraction,
            policy_id=policy_id,
        ),
        reasons=(),
    )
