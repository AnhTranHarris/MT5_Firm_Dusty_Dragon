from datetime import UTC, datetime

import pytest

from dusty_dragon.domain.models import ApprovedOrder
from dusty_dragon.execution.transport import ExecutionReceipt, ExecutionStatus
from dusty_dragon.persistence.authorization_lease import AuthorizationLeaseRepository
from dusty_dragon.persistence.execution_reconciliation import (
    ExecutionReconciliationRepository,
    ExecutionReconciliationSource,
    ExecutionReconciliationState,
)
from dusty_dragon.persistence.sqlite import connect, initialize


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


def issued_order(connection):
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
        audit_event_id="preorder-1",
        authorized_at_utc=datetime(2026, 8, 26, 14, 0, tzinfo=UTC),
        ttl_seconds=10,
    )
    return order, lease


def test_accepted_receipt_opens_unresolved_reconciliation() -> None:
    connection = seeded_connection()
    order, lease = issued_order(connection)
    repository = ExecutionReconciliationRepository(connection)

    record = repository.open_for_receipt(
        lease_id=lease.lease_id,
        order=order,
        receipt=ExecutionReceipt(
            status=ExecutionStatus.ACCEPTED,
            broker_order_id="BROKER-42",
            message="accepted",
        ),
        opened_at_utc=datetime(2026, 8, 26, 14, 0, 5, tzinfo=UTC),
    )

    assert record is not None
    assert record.source_status is ExecutionReconciliationSource.ACCEPTED
    assert record.state is ExecutionReconciliationState.UNRESOLVED
    assert repository.unresolved_for_desk("GENERALIST-01") == (record,)


def test_explicit_rejection_does_not_open_reconciliation() -> None:
    connection = seeded_connection()
    order, lease = issued_order(connection)
    repository = ExecutionReconciliationRepository(connection)

    record = repository.open_for_receipt(
        lease_id=lease.lease_id,
        order=order,
        receipt=ExecutionReceipt(
            status=ExecutionStatus.REJECTED,
            broker_order_id=None,
            message="rejected",
        ),
        opened_at_utc=datetime(2026, 8, 26, 14, 0, 5, tzinfo=UTC),
    )

    assert record is None
    assert repository.unresolved_for_desk("GENERALIST-01") == ()


def test_transport_error_remains_unresolved_until_independent_evidence() -> None:
    connection = seeded_connection()
    order, lease = issued_order(connection)
    repository = ExecutionReconciliationRepository(connection)
    record = repository.open_for_transport_error(
        lease_id=lease.lease_id,
        order=order,
        opened_at_utc=datetime(2026, 8, 26, 14, 0, 5, tzinfo=UTC),
    )

    resolved = repository.resolve(
        record.reconciliation_id,
        state=ExecutionReconciliationState.CONFIRMED_EXECUTED,
        evidence_id="broker-deal-9001",
        resolved_at_utc=datetime(2026, 8, 26, 14, 0, 8, tzinfo=UTC),
    )

    assert record.source_status is ExecutionReconciliationSource.TRANSPORT_ERROR
    assert resolved.state is ExecutionReconciliationState.CONFIRMED_EXECUTED
    assert resolved.resolution_evidence_id == "broker-deal-9001"
    assert repository.unresolved_for_desk("GENERALIST-01") == ()


def test_reconciliation_cannot_be_resolved_twice() -> None:
    connection = seeded_connection()
    order, lease = issued_order(connection)
    repository = ExecutionReconciliationRepository(connection)
    record = repository.open_for_transport_error(
        lease_id=lease.lease_id,
        order=order,
        opened_at_utc=datetime(2026, 8, 26, 14, 0, 5, tzinfo=UTC),
    )
    repository.resolve(
        record.reconciliation_id,
        state=ExecutionReconciliationState.CONFIRMED_NOT_EXECUTED,
        evidence_id="broker-history-empty-1",
        resolved_at_utc=datetime(2026, 8, 26, 14, 0, 8, tzinfo=UTC),
    )

    with pytest.raises(LookupError, match="unresolved execution reconciliation not found"):
        repository.resolve(
            record.reconciliation_id,
            state=ExecutionReconciliationState.CONFIRMED_EXECUTED,
            evidence_id="late-conflict",
            resolved_at_utc=datetime(2026, 8, 26, 14, 0, 9, tzinfo=UTC),
        )
