from dataclasses import dataclass
from datetime import UTC, datetime

from dusty_dragon.domain.accounts import AccountSnapshot
from dusty_dragon.domain.market import AccountEnvironment
from dusty_dragon.domain.models import ApprovedOrder
from dusty_dragon.execution.status import build_demo_execution_status
from dusty_dragon.persistence.execution_reconciliation import ExecutionReconciliationRepository
from dusty_dragon.persistence.sqlite import connect, initialize


@dataclass
class FakeSession:
    opened: bool = True
    faulted: bool = False
    fault_reason: str | None = None


@dataclass
class FakeStack:
    session: FakeSession
    native_write_enabled: bool = False


def account() -> AccountSnapshot:
    return AccountSnapshot(
        account_id="25115284",
        desk_id="DEMO-01",
        broker_id="B1",
        environment=AccountEnvironment.DEMO,
        observed_at_utc=datetime(2026, 8, 26, 20, 45, tzinfo=UTC),
        balance=20_500.0,
        equity=20_450.0,
        margin=100.0,
        free_margin=20_350.0,
    )


def repository() -> ExecutionReconciliationRepository:
    connection = connect(":memory:")
    initialize(connection)
    return ExecutionReconciliationRepository(connection)


def test_status_is_ready_when_session_is_healthy_and_no_execution_is_pending() -> None:
    repo = repository()
    status = build_demo_execution_status(
        stack=FakeStack(FakeSession()),
        account=account(),
        reconciliation_repository=repo,
    )

    assert status.desk_id == "DEMO-01"
    assert status.balance == 20_500.0
    assert status.equity == 20_450.0
    assert status.session_open
    assert status.unresolved_execution_count == 0
    assert status.execution_ready


def test_unresolved_execution_blocks_ready_status_without_hiding_account_metrics() -> None:
    repo = repository()
    order = ApprovedOrder(
        desk_id="DEMO-01",
        instrument_id="FX.EURUSD@B1",
        side="BUY",
        approved_risk_fraction=0.01,
        policy_id="financial_v1",
    )
    repo.open_for_transport_error(
        lease_id="lease-1",
        order=order,
        opened_at_utc=datetime(2026, 8, 26, 20, 46, tzinfo=UTC),
    )

    status = build_demo_execution_status(
        stack=FakeStack(FakeSession()),
        account=account(),
        reconciliation_repository=repo,
    )

    assert status.unresolved_execution_count == 1
    assert not status.execution_ready
    assert status.free_margin == 20_350.0


def test_faulted_session_is_visible_and_not_execution_ready() -> None:
    repo = repository()
    session = FakeSession(
        opened=False,
        faulted=True,
        fault_reason="connected MT5 login drifted from bound Dusty account",
    )

    status = build_demo_execution_status(
        stack=FakeStack(session, native_write_enabled=True),
        account=account(),
        reconciliation_repository=repo,
    )

    assert status.session_faulted
    assert "login drifted" in (status.session_fault_reason or "")
    assert status.native_write_enabled
    assert not status.execution_ready
