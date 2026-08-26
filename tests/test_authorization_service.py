import json
from datetime import UTC, datetime

from dusty_dragon.brokers.health import BrokerHealthSnapshot, BrokerHealthState
from dusty_dragon.brokers.reconciliation import ReconciliationResult, ReconciliationStatus
from dusty_dragon.domain.models import OrderIntent, SignalDisposition
from dusty_dragon.governance.authorization_service import PreOrderAuthorizationService
from dusty_dragon.governance.preorder import PreOrderStatus
from dusty_dragon.persistence.preorder_audit import PreOrderAuditRepository
from dusty_dragon.persistence.sqlite import connect, initialize
from dusty_dragon.portfolio.governor import PortfolioDecision
from dusty_dragon.risk.desk import DailyRiskAction, DeskRiskDecision, WeeklyRiskState


def healthy_inputs():
    desk_risk = DeskRiskDecision(
        weekly_state=WeeklyRiskState.NORMAL,
        daily_action=DailyRiskAction.NORMAL,
        trade_risk_compliant=True,
        exposure_compliant=True,
        may_add_new_risk=True,
        reasons=(),
    )
    portfolio = PortfolioDecision(
        allowed=True,
        disposition=SignalDisposition.APPROVED,
        reason="desk signal and portfolio capacity both valid",
    )
    reconciliation = ReconciliationResult(status=ReconciliationStatus.MATCH, reasons=())
    broker_health = BrokerHealthSnapshot(
        state=BrokerHealthState.HEALTHY,
        consecutive_drift_count=0,
        safe_for_new_orders=True,
    )
    return desk_risk, portfolio, reconciliation, broker_health


def test_authorization_service_always_records_decision() -> None:
    connection = connect(":memory:")
    initialize(connection)
    service = PreOrderAuthorizationService(
        PreOrderAuditRepository(connection),
        policy_id="financial_v1",
    )
    intent = OrderIntent(
        desk_id="GENERALIST-01",
        instrument_id="FX.EURUSD@B1",
        side="BUY",
        requested_risk_fraction=0.01,
    )
    desk_risk, portfolio, reconciliation, broker_health = healthy_inputs()

    result = service.authorize(
        intent,
        desk_risk=desk_risk,
        portfolio=portfolio,
        reconciliation=reconciliation,
        broker_health=broker_health,
        occurred_at_utc=datetime(2026, 8, 26, 11, 25, tzinfo=UTC),
    )

    assert result.decision.status is PreOrderStatus.APPROVED
    row = connection.execute(
        "SELECT payload_json FROM audit_events WHERE event_id = ?",
        (result.audit_event_id,),
    ).fetchone()
    assert json.loads(row["payload_json"])["status"] == "APPROVED"


def test_veto_is_audited_and_never_returns_approved_order() -> None:
    connection = connect(":memory:")
    initialize(connection)
    service = PreOrderAuthorizationService(
        PreOrderAuditRepository(connection),
        policy_id="financial_v1",
    )
    intent = OrderIntent(
        desk_id="GENERALIST-01",
        instrument_id="FX.EURUSD@B1",
        side="BUY",
        requested_risk_fraction=0.01,
    )
    desk_risk, portfolio, reconciliation, _ = healthy_inputs()
    broker_health = BrokerHealthSnapshot(
        state=BrokerHealthState.RESTRICTED,
        consecutive_drift_count=2,
        safe_for_new_orders=False,
    )

    result = service.authorize(
        intent,
        desk_risk=desk_risk,
        portfolio=portfolio,
        reconciliation=reconciliation,
        broker_health=broker_health,
        occurred_at_utc=datetime(2026, 8, 26, 11, 26, tzinfo=UTC),
    )

    assert result.decision.status is PreOrderStatus.BROKER_HEALTH_REJECTED
    assert result.decision.approved_order is None
    row = connection.execute(
        "SELECT payload_json FROM audit_events WHERE event_id = ?",
        (result.audit_event_id,),
    ).fetchone()
    assert json.loads(row["payload_json"])["status"] == "BROKER_HEALTH_REJECTED"
