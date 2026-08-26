from datetime import UTC, datetime

from dusty_dragon.domain.market import AccountEnvironment
from dusty_dragon.execution.aggregate_status import (
    build_firm_execution_status,
    build_layer_execution_status,
)
from dusty_dragon.execution.status import DemoExecutionStatus
from dusty_dragon.execution.status_serialization import execution_status_to_dict


def test_firm_status_serializes_to_json_safe_primitives() -> None:
    desk = DemoExecutionStatus(
        desk_id="DEMO-01",
        account_id="25115284",
        broker_id="B1",
        environment=AccountEnvironment.DEMO,
        observed_at_utc=datetime(2026, 8, 26, 20, 55, tzinfo=UTC),
        balance=20_000.0,
        equity=20_100.0,
        free_margin=19_900.0,
        session_open=True,
        session_faulted=False,
        session_fault_reason=None,
        native_write_enabled=False,
        unresolved_execution_count=0,
        execution_ready=True,
    )
    firm = build_firm_execution_status((build_layer_execution_status(0, (desk,)),))

    payload = execution_status_to_dict(firm)

    assert payload["execution_ready"] is True
    assert payload["layers"][0]["layer"] == 0
    serialized_desk = payload["layers"][0]["desks"][0]
    assert serialized_desk["environment"] == "DEMO"
    assert serialized_desk["observed_at_utc"] == "2026-08-26T20:55:00+00:00"
    assert serialized_desk["balance"] == 20_000.0
