import json
from datetime import UTC, datetime

from dusty_dragon.domain.models import ApprovedOrder
from dusty_dragon.execution.service import ExecutionService
from dusty_dragon.execution.transport import ExecutionReceipt, ExecutionStatus
from dusty_dragon.persistence.authorization_lease import (
    AuthorizationLeaseRepository,
    LeaseConsumeStatus,
)
from dusty_dragon.persistence.execution_audit import ExecutionAuditRepository
from dusty_dragon.persistence.sqlite import connect, initialize


class FakeExecutionTransport:
    def __init__(self, *, status: ExecutionStatus = ExecutionStatus.ACCEPTED) -> None:
        self.orders: list[ApprovedOrder] = []
        self.status = status

    def submit(self, order: ApprovedOrder) -> ExecutionReceipt:
        self.orders.append(order)
        return ExecutionReceipt(
            status=self.status,
            broker_order_id="FAKE-1" if self.status is ExecutionStatus.ACCEPTED else None,
            message=f"fake transport {self.status.value.lower()}",
        )


class FailingExecutionTransport:
    def __init__(self) -> None:
        self.orders: list[ApprovedOrder] = []

    def submit(self, order: ApprovedOrder) -> ExecutionReceipt:
        self.orders.append(order)
        raise RuntimeError("connection lost after submission")


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


def service(repository, transport) -> ExecutionService:
    return ExecutionService(
        repository,
        ExecutionAuditRepository(repository.connection),
        transport,
    )


def test_fresh_lease_is_consumed_audited_and_submitted_once() -> None:
    repository = seeded_repository()
    lease = issue(repository)
    transport = FakeExecutionTransport()
    execution = service(repository, transport)

    result = execution.execute(
        lease.lease_id,
        consumed_at_utc=datetime(2026, 8, 26, 13, 0, 5, tzinfo=UTC),
    )

    assert result.lease_status is LeaseConsumeStatus.CONSUMED
    assert result.submitted
    assert result.requires_broker_reconciliation
    assert len(transport.orders) == 1
    row = repository.connection.execute(
        "SELECT payload_json FROM audit_events WHERE event_id = ?",
        (result.audit_event_id,),
    ).fetchone()
    assert json.loads(row["payload_json"])["receipt"]["status"] == "ACCEPTED"


def test_expired_and_missing_leases_never_reach_transport() -> None:
    repository = seeded_repository()
    lease = issue(repository)
    transport = FakeExecutionTransport()
    execution = service(repository, transport)

    expired = execution.execute(
        lease.lease_id,
        consumed_at_utc=datetime(2026, 8, 26, 13, 0, 11, tzinfo=UTC),
    )
    missing = execution.execute(
        "missing",
        consumed_at_utc=datetime(2026, 8, 26, 13, 0, 5, tzinfo=UTC),
    )

    assert expired.lease_status is LeaseConsumeStatus.EXPIRED
    assert missing.lease_status is LeaseConsumeStatus.NOT_FOUND
    assert transport.orders == []


def test_replayed_lease_never_reaches_transport_twice() -> None:
    repository = seeded_repository()
    lease = issue(repository)
    transport = FakeExecutionTransport()
    execution = service(repository, transport)
    execution_time = datetime(2026, 8, 26, 13, 0, 5, tzinfo=UTC)

    first = execution.execute(lease.lease_id, consumed_at_utc=execution_time)
    second = execution.execute(lease.lease_id, consumed_at_utc=execution_time)

    assert first.lease_status is LeaseConsumeStatus.CONSUMED
    assert second.lease_status is LeaseConsumeStatus.ALREADY_CONSUMED
    assert len(transport.orders) == 1


def test_explicit_rejection_is_audited_without_reconciliation_requirement() -> None:
    repository = seeded_repository()
    lease = issue(repository)
    transport = FakeExecutionTransport(status=ExecutionStatus.REJECTED)

    result = service(repository, transport).execute(
        lease.lease_id,
        consumed_at_utc=datetime(2026, 8, 26, 13, 0, 5, tzinfo=UTC),
    )

    assert result.receipt is not None
    assert result.receipt.status is ExecutionStatus.REJECTED
    assert not result.requires_broker_reconciliation


def test_ambiguous_response_requires_broker_reconciliation() -> None:
    repository = seeded_repository()
    lease = issue(repository)
    transport = FakeExecutionTransport(status=ExecutionStatus.AMBIGUOUS)

    result = service(repository, transport).execute(
        lease.lease_id,
        consumed_at_utc=datetime(2026, 8, 26, 13, 0, 5, tzinfo=UTC),
    )

    assert result.receipt is not None
    assert result.receipt.status is ExecutionStatus.AMBIGUOUS
    assert result.requires_broker_reconciliation


def test_transport_failure_is_audited_as_uncertain_and_never_blindly_retried() -> None:
    repository = seeded_repository()
    lease = issue(repository)
    transport = FailingExecutionTransport()
    execution = service(repository, transport)
    execution_time = datetime(2026, 8, 26, 13, 0, 5, tzinfo=UTC)

    first = execution.execute(lease.lease_id, consumed_at_utc=execution_time)
    replay = execution.execute(lease.lease_id, consumed_at_utc=execution_time)

    assert first.transport_error == "RuntimeError: connection lost after submission"
    assert first.requires_broker_reconciliation
    assert replay.lease_status is LeaseConsumeStatus.ALREADY_CONSUMED
    assert len(transport.orders) == 1
