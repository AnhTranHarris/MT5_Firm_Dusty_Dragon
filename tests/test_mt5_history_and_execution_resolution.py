from datetime import UTC, datetime

from dusty_dragon.brokers.mt5_history import (
    BrokerExecutionHistory,
    BrokerOrderHistoryRecord,
    BrokerOrderHistoryStatus,
    MT5HistoryAdapter,
)
from dusty_dragon.domain.models import ApprovedOrder
from dusty_dragon.execution.reconciliation_service import ExecutionReconciliationService
from dusty_dragon.execution.transport import ExecutionReceipt, ExecutionStatus
from dusty_dragon.persistence.authorization_lease import AuthorizationLeaseRepository
from dusty_dragon.persistence.execution_reconciliation import (
    ExecutionReconciliationRepository,
    ExecutionReconciliationState,
)
from dusty_dragon.persistence.sqlite import connect, initialize


class FakeHistoryTransport:
    def history_orders_get(self, date_from, date_to):
        return (
            {"ticket": 42, "state": 4, "time_done": 1_777_000_000},
            {"ticket": 43, "state": 2, "time_done": 1_777_000_001},
        )

    def history_deals_get(self, date_from, date_to):
        return ({"ticket": 9001, "order": 42, "time": 1_777_000_002},)


def seeded_connection():
    connection = connect(":memory:")
    initialize(connection)
    with connection:
        connection.execute("INSERT INTO brokers(broker_id, name) VALUES (?, ?)", ("B1", "Broker 1"))
        connection.execute(
            "INSERT INTO desks(desk_id, layer, specialization, created_at_utc) "
            "VALUES (?, ?, ?, ?)",
            ("GENERALIST-01", 1, "GENERALIST", "2026-08-26T14:00:00+00:00"),
        )
        connection.execute(
            "INSERT INTO instruments("
            "instrument_id, broker_id, broker_symbol, asset_class, base_currency, quote_currency"
            ") VALUES (?, ?, ?, ?, ?, ?)",
            ("FX.EURUSD@B1", "B1", "EURUSD", "FX", "EUR", "USD"),
        )
    return connection


def opened_reconciliation(connection, *, broker_order_id: str | None):
    order = ApprovedOrder(
        desk_id="GENERALIST-01",
        instrument_id="FX.EURUSD@B1",
        side="BUY",
        approved_risk_fraction=0.01,
        policy_id="financial_v1",
    )
    lease = AuthorizationLeaseRepository(connection).issue(
        order,
        operations_policy_id="operations_v1",
        audit_event_id=f"preorder-{broker_order_id or 'none'}",
        authorized_at_utc=datetime(2026, 8, 26, 14, 0, tzinfo=UTC),
        ttl_seconds=10,
    )
    repository = ExecutionReconciliationRepository(connection)
    if broker_order_id is None:
        return repository.open_for_transport_error(
            lease_id=lease.lease_id,
            order=order,
            opened_at_utc=datetime(2026, 8, 26, 14, 0, 5, tzinfo=UTC),
        )
    record = repository.open_for_receipt(
        lease_id=lease.lease_id,
        order=order,
        receipt=ExecutionReceipt(
            status=ExecutionStatus.ACCEPTED,
            broker_order_id=broker_order_id,
            message="accepted",
        ),
        opened_at_utc=datetime(2026, 8, 26, 14, 0, 5, tzinfo=UTC),
    )
    assert record is not None
    return record


def test_mt5_history_adapter_normalizes_orders_and_deals() -> None:
    adapter = MT5HistoryAdapter(FakeHistoryTransport())
    history = adapter.read_execution_history(
        date_from_utc=datetime(2026, 8, 26, 13, 59, tzinfo=UTC),
        date_to_utc=datetime(2026, 8, 26, 14, 1, tzinfo=UTC),
    )

    assert history.orders[0].broker_order_id == "42"
    assert history.orders[0].status is BrokerOrderHistoryStatus.FILLED
    assert history.orders[1].status is BrokerOrderHistoryStatus.CANCELED
    assert history.deals[0].broker_order_id == "42"


def test_matching_deal_confirms_execution() -> None:
    connection = seeded_connection()
    record = opened_reconciliation(connection, broker_order_id="42")
    history = MT5HistoryAdapter(FakeHistoryTransport()).read_execution_history(
        date_from_utc=datetime(2026, 8, 26, 13, 59, tzinfo=UTC),
        date_to_utc=datetime(2026, 8, 26, 14, 1, tzinfo=UTC),
    )

    result = ExecutionReconciliationService(
        ExecutionReconciliationRepository(connection)
    ).resolve_from_history(
        record.reconciliation_id,
        history=history,
        resolved_at_utc=datetime(2026, 8, 26, 14, 1, tzinfo=UTC),
    )

    assert result.resolved
    assert result.record.state is ExecutionReconciliationState.CONFIRMED_EXECUTED
    assert result.record.resolution_evidence_id == "broker-deal:9001"


def test_canceled_order_confirms_not_executed() -> None:
    connection = seeded_connection()
    record = opened_reconciliation(connection, broker_order_id="43")
    history = MT5HistoryAdapter(FakeHistoryTransport()).read_execution_history(
        date_from_utc=datetime(2026, 8, 26, 13, 59, tzinfo=UTC),
        date_to_utc=datetime(2026, 8, 26, 14, 1, tzinfo=UTC),
    )

    result = ExecutionReconciliationService(
        ExecutionReconciliationRepository(connection)
    ).resolve_from_history(
        record.reconciliation_id,
        history=history,
        resolved_at_utc=datetime(2026, 8, 26, 14, 1, tzinfo=UTC),
    )

    assert result.resolved
    assert result.record.state is ExecutionReconciliationState.CONFIRMED_NOT_EXECUTED


def test_transport_error_without_broker_order_id_is_not_guessed() -> None:
    connection = seeded_connection()
    record = opened_reconciliation(connection, broker_order_id=None)
    history = BrokerExecutionHistory(
        orders=(
            BrokerOrderHistoryRecord(
                broker_order_id="99",
                status=BrokerOrderHistoryStatus.FILLED,
                observed_at_utc=datetime(2026, 8, 26, 14, 0, 6, tzinfo=UTC),
            ),
        ),
        deals=(),
        queried_at_utc=datetime(2026, 8, 26, 14, 1, tzinfo=UTC),
    )

    result = ExecutionReconciliationService(
        ExecutionReconciliationRepository(connection)
    ).resolve_from_history(
        record.reconciliation_id,
        history=history,
        resolved_at_utc=datetime(2026, 8, 26, 14, 1, tzinfo=UTC),
    )

    assert not result.resolved
    assert result.record.state is ExecutionReconciliationState.UNRESOLVED
