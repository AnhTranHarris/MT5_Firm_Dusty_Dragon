from dataclasses import dataclass
from datetime import UTC, datetime

from dusty_dragon.domain.market import AccountEnvironment
from dusty_dragon.execution.operator import DemoOperatorCommand
from dusty_dragon.execution.read_service import FirmExecutionReadService
from dusty_dragon.execution.status import DemoExecutionStatus


@dataclass
class Provider:
    layer: int = 0

    def snapshot(self) -> DemoExecutionStatus:
        return DemoExecutionStatus(
            desk_id="DEMO-01",
            account_id="25115284",
            broker_id="B1",
            environment=AccountEnvironment.DEMO,
            observed_at_utc=datetime(2026, 8, 26, 21, 10, tzinfo=UTC),
            balance=20_000.0,
            equity=20_000.0,
            free_margin=20_000.0,
            session_open=True,
            session_faulted=False,
            session_fault_reason=None,
            native_write_enabled=False,
            unresolved_execution_count=0,
            execution_ready=True,
        )


def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key) for key in value}
        for item in value.values():
            keys.update(_all_keys(item))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for item in value:
            keys.update(_all_keys(item))
        return keys
    return set()


def test_website_read_boundary_exposes_data_not_runtime_infrastructure() -> None:
    service = FirmExecutionReadService(providers=(Provider(),))
    payload = service.payload()
    forbidden_keys = {
        "mt5",
        "connection",
        "repository",
        "transport",
        "authorization_lease",
        "approved_order",
        "stack",
    }

    assert forbidden_keys.isdisjoint(_all_keys(payload))
    assert not hasattr(service, "execute")
    assert not hasattr(service, "order_send")


def test_pc_operator_contract_cannot_enable_live_or_place_trades() -> None:
    commands = {command.value for command in DemoOperatorCommand}

    assert commands == {"SHUTDOWN_EXECUTION", "REQUEST_SESSION_REBUILD"}
    assert all("LIVE" not in command for command in commands)
    assert all("TRADE" not in command for command in commands)
    assert all("WRITE" not in command for command in commands)


def test_execution_ready_remains_visible_as_safety_not_capital_authority() -> None:
    payload = FirmExecutionReadService(providers=(Provider(),)).payload()
    desk_payload = payload["layers"][0]["desks"][0]

    assert desk_payload["execution_ready"] is True
    assert "approved_order" not in desk_payload
    assert "authorization_lease" not in desk_payload
