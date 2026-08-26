from datetime import UTC, datetime

from dusty_dragon.domain.market import AccountEnvironment
from dusty_dragon.execution.aggregate_status import (
    build_firm_execution_status,
    build_layer_execution_status,
)
from dusty_dragon.execution.status import DemoExecutionStatus


def desk(
    desk_id: str,
    *,
    balance: float,
    ready: bool = True,
    faulted: bool = False,
    unresolved: int = 0,
) -> DemoExecutionStatus:
    return DemoExecutionStatus(
        desk_id=desk_id,
        account_id=f"ACCOUNT-{desk_id}",
        broker_id="B1",
        environment=AccountEnvironment.DEMO,
        observed_at_utc=datetime(2026, 8, 26, 20, 50, tzinfo=UTC),
        balance=balance,
        equity=balance - 10.0,
        free_margin=balance - 20.0,
        session_open=not faulted,
        session_faulted=faulted,
        session_fault_reason="fault" if faulted else None,
        native_write_enabled=False,
        unresolved_execution_count=unresolved,
        execution_ready=ready,
    )


def test_layer_aggregate_preserves_desks_and_reports_operational_blockers() -> None:
    statuses = (
        desk("DEMO-01", balance=20_000.0),
        desk("DEMO-02", balance=21_000.0, ready=False, unresolved=1),
    )

    layer = build_layer_execution_status(0, statuses)

    assert layer.desks == statuses
    assert layer.desk_count == 2
    assert layer.ready_count == 1
    assert layer.pending_execution_count == 1
    assert layer.total_balance == 41_000.0
    assert layer.total_equity == 40_980.0
    assert not layer.execution_ready


def test_firm_readiness_requires_every_represented_layer_to_be_ready() -> None:
    layer_zero = build_layer_execution_status(
        0,
        (desk("DEMO-01", balance=20_000.0),),
    )
    layer_one = build_layer_execution_status(
        1,
        (desk("LIVE-SIM-01", balance=5_000.0, ready=False, faulted=True),),
    )

    firm = build_firm_execution_status((layer_zero, layer_one))

    assert firm.layer_count == 2
    assert firm.desk_count == 2
    assert firm.ready_count == 1
    assert firm.faulted_count == 1
    assert firm.total_balance == 25_000.0
    assert not firm.execution_ready


def test_empty_layer_and_firm_are_not_execution_ready() -> None:
    layer = build_layer_execution_status(0, ())
    firm = build_firm_execution_status(())

    assert layer.desk_count == 0
    assert not layer.execution_ready
    assert firm.layer_count == 0
    assert not firm.execution_ready
