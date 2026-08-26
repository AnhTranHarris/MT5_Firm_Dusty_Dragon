from datetime import UTC, datetime, timedelta

from dusty_dragon.brokers.mt5_native_write import (
    MT5PreflightError,
    MT5SubmissionUncertainError,
)
from dusty_dragon.brokers.mt5_write import MT5ExecutionParameters
from dusty_dragon.domain.accounts import AccountSnapshot
from dusty_dragon.domain.market import AccountEnvironment, AssetClass, Instrument, InstrumentSpec
from dusty_dragon.domain.models import ApprovedOrder
from dusty_dragon.execution.demo_gate import ExecutionMode
from dusty_dragon.execution.demo_lease_service import DemoLeaseExecutionService
from dusty_dragon.execution.demo_service import DemoExecutionService
from dusty_dragon.execution.transport import ExecutionReceipt, ExecutionStatus
from dusty_dragon.governance.execution_arm import DemoExecutionArm
from dusty_dragon.persistence.authorization_lease import (
    AuthorizationLeaseRepository,
    LeaseConsumeStatus,
)
from dusty_dragon.persistence.execution_audit import ExecutionAuditRepository
from dusty_dragon.persistence.execution_reconciliation import (
    ExecutionReconciliationRepository,
    ExecutionReconciliationSource,
)
from dusty_dragon.persistence.sqlite import connect, initialize


class FakeAdapter:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.orders: list[ApprovedOrder] = []

    def submit(self, order, *, instrument, spec, parameters):
        self.orders.append(order)
        if self.error is not None:
            raise self.error
        return ExecutionReceipt(
            status=ExecutionStatus.ACCEPTED,
            broker_order_id="DEMO-ORDER-1",
            message="accepted",
        )


def repositories():
    connection = connect(":memory:")
    initialize(connection)
    with connection:
        connection.execute("INSERT INTO brokers(broker_id, name) VALUES (?, ?)", ("B1", "Broker 1"))
        connection.execute(
            "INSERT INTO desks(desk_id, layer, specialization, created_at_utc) "
            "VALUES (?, ?, ?, ?)",
            ("DEMO-01", 0, "GENERALIST", "2026-08-26T20:00:00+00:00"),
        )
        connection.execute(
            "INSERT INTO instruments("
            "instrument_id, broker_id, broker_symbol, asset_class, base_currency, quote_currency"
            ") VALUES (?, ?, ?, ?, ?, ?)",
            ("FX.EURUSD@B1", "B1", "EURUSD", "FX", "EUR", "USD"),
        )
    lease_repository = AuthorizationLeaseRepository(connection)
    return (
        lease_repository,
        ExecutionAuditRepository(connection),
        ExecutionReconciliationRepository(connection),
    )


def issue(repository: AuthorizationLeaseRepository, *, ttl_seconds: int = 10):
    return repository.issue(
        ApprovedOrder(
            desk_id="DEMO-01",
            instrument_id="FX.EURUSD@B1",
            side="BUY",
            approved_risk_fraction=0.01,
            policy_id="financial_v1",
        ),
        operations_policy_id="operations_v1",
        audit_event_id="preorder-demo-test",
        authorized_at_utc=datetime(2026, 8, 26, 20, 0, tzinfo=UTC),
        ttl_seconds=ttl_seconds,
    )


def account() -> AccountSnapshot:
    return AccountSnapshot(
        account_id="A1",
        desk_id="DEMO-01",
        broker_id="B1",
        environment=AccountEnvironment.DEMO,
        observed_at_utc=datetime(2026, 8, 26, 20, 0, tzinfo=UTC),
        balance=20_000.0,
        equity=20_000.0,
        margin=0.0,
        free_margin=20_000.0,
    )


def instrument() -> Instrument:
    return Instrument(
        instrument_id="FX.EURUSD@B1",
        broker_id="B1",
        broker_symbol="EURUSD",
        asset_class=AssetClass.FX,
        base_currency="EUR",
        quote_currency="USD",
    )


def spec() -> InstrumentSpec:
    return InstrumentSpec(
        instrument_id="FX.EURUSD@B1",
        digits=5,
        tick_size=0.00001,
        tick_value=1.0,
        contract_size=100000.0,
        min_volume=0.01,
        max_volume=100.0,
        volume_step=0.01,
        effective_from_utc=datetime(2026, 8, 26, 20, 0, tzinfo=UTC),
    )


def parameters() -> MT5ExecutionParameters:
    return MT5ExecutionParameters(volume=0.01, reference_price=1.17)


def arm(now: datetime) -> DemoExecutionArm:
    return DemoExecutionArm(
        desk_id="DEMO-01",
        account_id="A1",
        armed_at_utc=now - timedelta(seconds=1),
        expires_at_utc=now + timedelta(seconds=30),
    )


def service(dry_adapter, write_adapter=None):
    lease_repository, audit_repository, reconciliation_repository = repositories()
    return (
        DemoLeaseExecutionService(
            lease_repository,
            audit_repository,
            reconciliation_repository,
            DemoExecutionService(dry_adapter, write_adapter),
        ),
        lease_repository,
    )


def test_missing_or_expired_lease_never_reaches_demo_adapter() -> None:
    dry_adapter = FakeAdapter()
    execution, repository = service(dry_adapter)
    lease = issue(repository)

    missing = execution.execute(
        "missing",
        account=account(),
        instrument=instrument(),
        spec=spec(),
        parameters=parameters(),
        consumed_at_utc=datetime(2026, 8, 26, 20, 0, 5, tzinfo=UTC),
    )
    expired = execution.execute(
        lease.lease_id,
        account=account(),
        instrument=instrument(),
        spec=spec(),
        parameters=parameters(),
        consumed_at_utc=datetime(2026, 8, 26, 20, 0, 11, tzinfo=UTC),
    )

    assert missing.lease_status is LeaseConsumeStatus.NOT_FOUND
    assert expired.lease_status is LeaseConsumeStatus.EXPIRED
    assert dry_adapter.orders == []


def test_fresh_lease_is_consumed_before_dry_run_submission() -> None:
    dry_adapter = FakeAdapter()
    execution, repository = service(dry_adapter)
    lease = issue(repository)

    result = execution.execute(
        lease.lease_id,
        account=account(),
        instrument=instrument(),
        spec=spec(),
        parameters=parameters(),
        consumed_at_utc=datetime(2026, 8, 26, 20, 0, 5, tzinfo=UTC),
    )

    assert result.lease_status is LeaseConsumeStatus.CONSUMED
    assert result.receipt is not None
    assert result.receipt.status is ExecutionStatus.ACCEPTED
    assert result.reconciliation is not None
    assert len(dry_adapter.orders) == 1


def test_demo_write_preflight_failure_is_audited_without_broker_uncertainty() -> None:
    dry_adapter = FakeAdapter()
    write_adapter = FakeAdapter(error=MT5PreflightError("order_check rejected"))
    execution, repository = service(dry_adapter, write_adapter)
    lease = issue(repository)
    now = datetime(2026, 8, 26, 20, 0, 5, tzinfo=UTC)

    result = execution.execute(
        lease.lease_id,
        account=account(),
        instrument=instrument(),
        spec=spec(),
        parameters=parameters(),
        mode=ExecutionMode.DEMO_WRITE,
        arm=arm(now),
        consumed_at_utc=now,
    )

    assert result.lease_status is LeaseConsumeStatus.CONSUMED
    assert result.reconciliation is None
    assert result.transport_error == "MT5PreflightError: order_check rejected"
    assert dry_adapter.orders == []
    assert len(write_adapter.orders) == 1


def test_demo_write_uncertain_submission_opens_reconciliation_and_cannot_replay() -> None:
    dry_adapter = FakeAdapter()
    write_adapter = FakeAdapter(error=MT5SubmissionUncertainError("connection lost"))
    execution, repository = service(dry_adapter, write_adapter)
    lease = issue(repository)
    now = datetime(2026, 8, 26, 20, 0, 5, tzinfo=UTC)

    first = execution.execute(
        lease.lease_id,
        account=account(),
        instrument=instrument(),
        spec=spec(),
        parameters=parameters(),
        mode=ExecutionMode.DEMO_WRITE,
        arm=arm(now),
        consumed_at_utc=now,
    )
    replay = execution.execute(
        lease.lease_id,
        account=account(),
        instrument=instrument(),
        spec=spec(),
        parameters=parameters(),
        mode=ExecutionMode.DEMO_WRITE,
        arm=arm(now),
        consumed_at_utc=now,
    )

    assert first.reconciliation is not None
    assert first.reconciliation.source_status is ExecutionReconciliationSource.TRANSPORT_ERROR
    assert replay.lease_status is LeaseConsumeStatus.ALREADY_CONSUMED
    assert len(write_adapter.orders) == 1
