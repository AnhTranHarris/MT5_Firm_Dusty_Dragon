from datetime import UTC, datetime, timedelta

from dusty_dragon.domain.models import ApprovedOrder
from dusty_dragon.persistence.authorization_lease import (
    AuthorizationLeaseRepository,
    LeaseConsumeStatus,
)
from dusty_dragon.persistence.sqlite import connect, initialize


def repository() -> AuthorizationLeaseRepository:
    connection = connect(":memory:")
    initialize(connection)
    with connection:
        connection.execute("INSERT INTO brokers(broker_id, name) VALUES (?, ?)", ("B1", "Broker 1"))
        connection.execute(
            """
            INSERT INTO desks(desk_id, layer, specialization, created_at_utc)
            VALUES (?, ?, ?, ?)
            """,
            ("GENERALIST-01", 1, "GENERALIST", "2026-08-26T11:00:00+00:00"),
        )
        connection.execute(
            """
            INSERT INTO instruments(
                instrument_id, broker_id, broker_symbol, asset_class, base_currency, quote_currency
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("FX.EURUSD@B1", "B1", "EURUSD", "FX", "EUR", "USD"),
        )
    return AuthorizationLeaseRepository(connection)


def order() -> ApprovedOrder:
    return ApprovedOrder(
        desk_id="GENERALIST-01",
        instrument_id="FX.EURUSD@B1",
        side="BUY",
        approved_risk_fraction=0.01,
        policy_id="financial_v1",
    )


def test_lease_is_fresh_then_atomically_consumed_once() -> None:
    repo = repository()
    authorized_at = datetime(2026, 8, 26, 11, 30, tzinfo=UTC)
    lease = repo.issue(
        order(),
        operations_policy_id="operations_v1",
        audit_event_id="audit-1",
        authorized_at_utc=authorized_at,
        ttl_seconds=10,
    )

    assert lease.is_fresh_at(authorized_at + timedelta(seconds=9))

    first = repo.consume(
        lease.lease_id,
        consumed_at_utc=authorized_at + timedelta(seconds=9),
    )
    second = repo.consume(
        lease.lease_id,
        consumed_at_utc=authorized_at + timedelta(seconds=9, milliseconds=1),
    )

    assert first.status is LeaseConsumeStatus.CONSUMED
    assert first.lease is not None and first.lease.consumed
    assert second.status is LeaseConsumeStatus.ALREADY_CONSUMED


def test_expired_lease_cannot_be_consumed() -> None:
    repo = repository()
    authorized_at = datetime(2026, 8, 26, 11, 30, tzinfo=UTC)
    lease = repo.issue(
        order(),
        operations_policy_id="operations_v1",
        audit_event_id="audit-2",
        authorized_at_utc=authorized_at,
        ttl_seconds=10,
    )

    result = repo.consume(
        lease.lease_id,
        consumed_at_utc=authorized_at + timedelta(seconds=11),
    )

    assert result.status is LeaseConsumeStatus.EXPIRED
    assert result.lease is not None and not result.lease.consumed


def test_missing_lease_fails_closed() -> None:
    repo = repository()

    result = repo.consume(
        "missing",
        consumed_at_utc=datetime(2026, 8, 26, 11, 30, tzinfo=UTC),
    )

    assert result.status is LeaseConsumeStatus.NOT_FOUND
    assert result.lease is None
