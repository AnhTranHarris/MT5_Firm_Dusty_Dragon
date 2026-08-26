from __future__ import annotations

from collections.abc import Iterable

from dusty_dragon.domain.models import (
    ApprovedOrder,
    CohortOutcome,
    DeskExpansionEvidence,
    DeskHealth,
    DeskQualification,
    GraduationLevel,
    OrderIntent,
    RiskAssessment,
)

_GRADUATION_ORDER = {
    GraduationLevel.INTRADAY: 0,
    GraduationLevel.HOLD_2D: 1,
    GraduationLevel.MULTIDAY: 2,
    GraduationLevel.WEEKLY: 3,
    GraduationLevel.MULTIWEEK: 4,
}


def cohort_credit(
    desks: Iterable[DeskQualification],
    *,
    minimum_level: GraduationLevel,
) -> int:
    """Return atomic cohort credit: all admitted desks pass or the cohort earns zero."""

    members = tuple(desks)
    if not members:
        return 0

    required_rank = _GRADUATION_ORDER[minimum_level]
    for desk in members:
        if desk.outcome is not CohortOutcome.PASS:
            return 0
        if _GRADUATION_ORDER[desk.graduation_level] < required_rank:
            return 0
    return len(members)


def live_expansion_eligible(
    desks: Iterable[DeskExpansionEvidence],
    *,
    minimum_equity: float,
    maintenance_days: int,
) -> bool:
    """Require every existing desk to independently maintain the live capital-chain gate."""

    members = tuple(desks)
    if not members or maintenance_days <= 0:
        return False

    for desk in members:
        if desk.health is not DeskHealth.NORMAL:
            return False
        if not desk.risk_compliant or desk.unresolved_critical_incident:
            return False
        if len(desk.closes) < maintenance_days:
            return False
        qualifying_window = desk.closes[-maintenance_days:]
        if any(not close.healthy for close in qualifying_window):
            return False
        if any(close.closing_equity < minimum_equity for close in qualifying_window):
            return False

    return True


def authorize_order(
    intent: OrderIntent,
    *,
    desk_risk: RiskAssessment,
    portfolio_risk: RiskAssessment,
    policy_id: str,
) -> ApprovedOrder | None:
    """Create ApprovedOrder only after both independent governance gates pass."""

    if not desk_risk.passed or not portfolio_risk.passed:
        return None
    if intent.requested_risk_fraction <= 0:
        return None

    return ApprovedOrder(
        desk_id=intent.desk_id,
        instrument_id=intent.instrument_id,
        side=intent.side,
        approved_risk_fraction=intent.requested_risk_fraction,
        policy_id=policy_id,
    )


def demo_compressed_capital(current_capital: float, factor: float) -> float:
    """Calculate requested Sunday demo capital; this is an external flow, not trading P&L."""

    if current_capital < 0:
        raise ValueError("current_capital cannot be negative")
    if not 0 < factor <= 1:
        raise ValueError("compression factor must be in (0, 1]")
    return current_capital * factor
