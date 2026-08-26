from datetime import UTC, datetime

from dusty_dragon.domain.models import ApprovedOrder
from dusty_dragon.execution.service import ExecutionService
from dusty_dragon.execution.transport import ExecutionReceipt, ExecutionStatus
from dusty_dragon.persistence.authorization_lease import (
    AuthorizationLeaseRepository,
    LeaseConsumeStatus,
)
from dusty_dragon.persistence.sqlite import connect, initialize


class FakeExecutionTransport:
    def __init__(self) -> None:
        self.orders: list[ApprovedOrder] = []

    def submit(self, order: ApprovedOrder) -> ExecutionReceipt:
        self.orders.append(order)
        return ExecutionReceipt(
            status=ExecutionStatus.ACCEPTED,
            broker_order_id="FAKE-1",
            message="accepted by fake transport",
        )


def seeded_repository() -> AuthorizationLeaseRepository:
    connection = connect(":memory:")
    initialize(connection)
    with connection:
        connection.execute("INSERT INTO brokers(broker_id, name) VALUES (?, ?)", ("B1", "Broker 1"))
        connection.execute(
            "INSERT INTO desks(desk_id, layer, specialization, created_at_utc) "
            "VALUES (?, ?, ?, ?)",
            ("GENERALIST-01", 1, "GENERALIST", "2026-08-26T13:00:00+00:00"),
        )
        connection.execute(
            "INSERT INTO instruments("
            "instrument_id, broker_id, broker_symbol, asset_class, base_currency, quote_currency"
            ") VALUES (?, ?, ?, ?, ?, ?)",
            ("FX.EURUSD@B1", "B1", "EURUSD", "FX", "EUR", "USD"),
        )
    return AuthorizationLeaseRepository(connection)


def issue(repository: AuthorizationLeaseRepository, *, ttl_seconds: int = 10):
    order = ApprovedOrder(
        desk_id="GENERALIST-01",
        instrument_id="FX.EURUSD@B1",
        side="BUY",
        approved_risk_fraction=0.01,
        policy_id="financial_v1",
    )
    return repository.issue(
        order,
        operations_policy_id="operations_v1",
        audit_event_id="preorder-test",
        authorized_at_utc=datetime(2026, 8, 26, 13, 0, tzinfo=UTC),
        ttl_seconds=ttl_seconds,
    )


def test_fresh_lease_is_consumed_before_transport_submission() -> None:
    repository = seeded_repository()
    lease = issue(repository)
    transport = FakeExecutionTransport()
    service = ExecutionService(repository, transport)

    result = service.execute(
        lease.lease_id,
        consumed_at_utc=datetime(2026, 8, 26, 13, 0, 5, tzinfo=UTC),
    )

    assert result.lease_status is LeaseConsumeStatus.CONSUMED
    assert result.submitted
    assert len(transport.orders) == 1
    assert transport.orders[0] == lease.order


def test_expired_lease_never_reaches_transport() -> None:
    repository = seeded_repository()
    lease = issue(repository)
    transport = FakeExecutionTransport()
    service = ExecutionService(repository, transport)

    result = service.execute(
        lease.lease_id,
        consumed_at_utc=datetime(2026, 8, 26, 13, 0, 11, tzinfo=UTC),
    )

    assert result.lease_status is LeaseConsumeStatus.EXPIRED
    assert not result.submitted
    assert transport.orders == []


def test_replayed_lease_never_reaches_transport_twice() -> None:
    repository = seeded_repository()
    lease = issue(repository)
    transport = FakeExecutionTransport()
    service = ExecutionService(repository, transport)
    execution_time = datetime(2026, 8, 26, 13, 0, 5, tzinfo=UTC)

    first = service.execute(lease.lease_id, consumed_at_utc=execution_time)
    second = service.execute(lease.lease_id, consumed_at_utc=execution_time)

    assert first.lease_status is LeaseConsumeStatus.CONSUMED
    assert second.lease_status is LeaseConsumeStatus.ALREADY_CONSUMED
    assert len(transport.orders) == 1


def test_missing_lease_never_reaches_transport() -> None:
    repository = seeded_repository()
    transport = FakeExecutionTransport()
    service = ExecutionService(repository, transport)

    result = service.execute(
        "missing",
        consumed_at_utc=datetime(2026, 8, 26, 13, 0, 5, tzinfo=UTC),
    )

    assert result.lease_status is LeaseConsumeStatus.NOT_FOUND
    assert not result.submitted
    assert transport.orders == []
