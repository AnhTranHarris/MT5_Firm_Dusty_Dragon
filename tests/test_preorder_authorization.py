from dusty_dragon.brokers.health import BrokerHealthSnapshot, BrokerHealthState
from dusty_dragon.brokers.reconciliation import ReconciliationResult, ReconciliationStatus
from dusty_dragon.domain.models import OrderIntent, SignalDisposition
from dusty_dragon.governance.preorder import PreOrderStatus, authorize_preorder
from dusty_dragon.portfolio.governor import PortfolioDecision
from dusty_dragon.risk.desk import DailyRiskAction, DeskRiskDecision, WeeklyRiskState


def intent() -> OrderIntent:
    return OrderIntent(
        desk_id="GENERALIST-01",
        instrument_id="FX.EURUSD@B1",
        side="BUY",
        requested_risk_fraction=0.01,
    )


def desk_decision(*, allowed: bool = True) -> DeskRiskDecision:
    return DeskRiskDecision(
        weekly_state=WeeklyRiskState.NORMAL,
        daily_action=DailyRiskAction.NORMAL,
        trade_risk_compliant=allowed,
        exposure_compliant=allowed,
        may_add_new_risk=allowed,
        reasons=() if allowed else ("desk risk blocked",),
    )


def portfolio_decision(*, allowed: bool = True) -> PortfolioDecision:
    return PortfolioDecision(
        allowed=allowed,
        disposition=(
            SignalDisposition.APPROVED
            if allowed
            else SignalDisposition.PORTFOLIO_CAPACITY_REJECTED
        ),
        reason=(
            "desk signal and portfolio capacity both valid"
            if allowed
            else "valid desk signal rejected by aggregate portfolio capacity"
        ),
    )


def reconciliation(*, allowed: bool = True) -> ReconciliationResult:
    return ReconciliationResult(
        status=ReconciliationStatus.MATCH if allowed else ReconciliationStatus.DRIFT,
        reasons=() if allowed else ("equity drift",),
    )


def broker_health(*, allowed: bool = True) -> BrokerHealthSnapshot:
    return BrokerHealthSnapshot(
        state=BrokerHealthState.HEALTHY if allowed else BrokerHealthState.RESTRICTED,
        consecutive_drift_count=0 if allowed else 2,
        safe_for_new_orders=allowed,
    )


def authorize(**overrides):
    return authorize_preorder(
        intent(),
        desk_risk=overrides.get("desk_risk", desk_decision()),
        portfolio=overrides.get("portfolio", portfolio_decision()),
        reconciliation=overrides.get("reconciliation", reconciliation()),
        broker_health=overrides.get("broker_health", broker_health()),
        policy_id="financial_v1",
    )


def test_all_independent_gates_must_pass_to_create_approved_order() -> None:
    result = authorize()

    assert result.status is PreOrderStatus.APPROVED
    assert result.approved
    assert result.approved_order is not None
    assert result.approved_order.desk_id == "GENERALIST-01"
    assert result.approved_order.approved_risk_fraction == 0.01


def test_desk_risk_veto_blocks_order() -> None:
    result = authorize(desk_risk=desk_decision(allowed=False))

    assert result.status is PreOrderStatus.DESK_RISK_REJECTED
    assert result.approved_order is None


def test_portfolio_veto_blocks_order_without_marking_bad_signal() -> None:
    portfolio = portfolio_decision(allowed=False)
    result = authorize(portfolio=portfolio)

    assert portfolio.disposition is SignalDisposition.PORTFOLIO_CAPACITY_REJECTED
    assert result.status is PreOrderStatus.PORTFOLIO_RISK_REJECTED
    assert result.approved_order is None


def test_reconciliation_drift_blocks_order() -> None:
    result = authorize(reconciliation=reconciliation(allowed=False))

    assert result.status is PreOrderStatus.RECONCILIATION_REJECTED
    assert result.reasons == ("equity drift",)
    assert result.approved_order is None


def test_broker_health_veto_blocks_order_even_with_matching_reconciliation() -> None:
    result = authorize(broker_health=broker_health(allowed=False))

    assert result.status is PreOrderStatus.BROKER_HEALTH_REJECTED
    assert result.approved_order is None


def test_non_positive_requested_risk_fails_closed() -> None:
    invalid = OrderIntent(
        desk_id="GENERALIST-01",
        instrument_id="FX.EURUSD@B1",
        side="BUY",
        requested_risk_fraction=0.0,
    )

    result = authorize_preorder(
        invalid,
        desk_risk=desk_decision(),
        portfolio=portfolio_decision(),
        reconciliation=reconciliation(),
        broker_health=broker_health(),
        policy_id="financial_v1",
    )

    assert result.status is PreOrderStatus.INVALID_INTENT
    assert result.approved_order is None
