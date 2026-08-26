import json
from datetime import UTC, datetime

from dusty_dragon.brokers.health import BrokerHealthSnapshot, BrokerHealthState
from dusty_dragon.brokers.reconciliation import ReconciliationResult, ReconciliationStatus
from dusty_dragon.domain.models import OrderIntent, SignalDisposition
from dusty_dragon.governance.authorization_service import PreOrderAuthorizationService
from dusty_dragon.governance.preorder import PreOrderStatus
from dusty_dragon.persistence.authorization_lease import AuthorizationLeaseRepository
from dusty_dragon.persistence.preorder_audit import PreOrderAuditRepository
from dusty_dragon.persistence.sqlite import connect, initialize
from dusty_dragon.portfolio.governor import PortfolioDecision
from dusty_dragon.risk.desk import DailyRiskAction, DeskRiskDecision, WeeklyRiskState


def seeded_connection():
    connection = connect(":memory:")
    initialize(connection)
    with connection:
        connection.execute("INSERT INTO brokers(broker_id, name) VALUES (?, ?)", ("B1", "Broker 1"))
        connection.execute(
            "INSERT INTO desks(desk_id, layer, specialization, created_at_utc) "
            "VALUES (?, ?, ?, ?)",
            ("GENERALIST-01", 1, "GENERALIST", "2026-08-26T11:00:00+00:00"),
        )
        connection.execute(
            "INSERT INTO instruments("
            "instrument_id, broker_id, broker_symbol, asset_class, base_currency, quote_currency"
            ") VALUES (?, ?, ?, ?, ?, ?)",
            ("FX.EURUSD@B1", "B1", "EURUSD", "FX", "EUR", "USD"),
        )
    return connection


def service(connection) -> PreOrderAuthorizationService:
    return PreOrderAuthorizationService(
        PreOrderAuditRepository(connection),
        AuthorizationLeaseRepository(connection),
        financial_policy_id="financial_v1",
        operations_policy_id="operations_v1",
        lease_ttl_seconds=10,
    )


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


def test_approved_decision_is_audited_and_receives_short_lived_lease() -> None:
    connection = seeded_connection()
    authorization = service(connection)
    intent = OrderIntent(
        desk_id="GENERALIST-01",
        instrument_id="FX.EURUSD@B1",
        side="BUY",
        requested_risk_fraction=0.01,
    )
    desk_risk, portfolio, reconciliation, broker_health = healthy_inputs()
    occurred_at = datetime(2026, 8, 26, 11, 25, tzinfo=UTC)

    result = authorization.authorize(
        intent,
        desk_risk=desk_risk,
        portfolio=portfolio,
        reconciliation=reconciliation,
        broker_health=broker_health,
        occurred_at_utc=occurred_at,
    )

    assert result.decision.status is PreOrderStatus.APPROVED
    assert result.authorization_lease is not None
    assert result.authorization_lease.audit_event_id == result.audit_event_id
    assert result.authorization_lease.authorized_at_utc == occurred_at
    assert result.authorization_lease.expires_at_utc.timestamp() - occurred_at.timestamp() == 10
    row = connection.execute(
        "SELECT payload_json FROM audit_events WHERE event_id = ?",
        (result.audit_event_id,),
    ).fetchone()
    assert json.loads(row["payload_json"])["status"] == "APPROVED"


def test_veto_is_audited_and_never_receives_execution_lease() -> None:
    connection = seeded_connection()
    authorization = service(connection)
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

    result = authorization.authorize(
        intent,
        desk_risk=desk_risk,
        portfolio=portfolio,
        reconciliation=reconciliation,
        broker_health=broker_health,
        occurred_at_utc=datetime(2026, 8, 26, 11, 26, tzinfo=UTC),
    )

    assert result.decision.status is PreOrderStatus.BROKER_HEALTH_REJECTED
    assert result.decision.approved_order is None
    assert result.authorization_lease is None
    row = connection.execute(
        "SELECT payload_json FROM audit_events WHERE event_id = ?",
        (result.audit_event_id,),
    ).fetchone()
    assert json.loads(row["payload_json"])["status"] == "BROKER_HEALTH_REJECTED"
    lease_count = connection.execute("SELECT COUNT(*) AS count FROM authorization_leases").fetchone()
    assert lease_count["count"] == 0
