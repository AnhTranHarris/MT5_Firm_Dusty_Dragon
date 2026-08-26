from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from dusty_dragon.domain.market import AccountEnvironment
from dusty_dragon.execution.read_service import FirmExecutionReadService
from dusty_dragon.execution.status import DemoExecutionStatus


@dataclass
class FakeProvider:
    layer: int
    status: DemoExecutionStatus

    def snapshot(self) -> DemoExecutionStatus:
        return self.status


def status(desk_id: str, *, ready: bool = True) -> DemoExecutionStatus:
    return DemoExecutionStatus(
        desk_id=desk_id,
        account_id=f"ACCOUNT-{desk_id}",
        broker_id="B1",
        environment=AccountEnvironment.DEMO,
        observed_at_utc=datetime(2026, 8, 26, 21, 5, tzinfo=UTC),
        balance=20_000.0,
        equity=20_000.0,
        free_margin=20_000.0,
        session_open=True,
        session_faulted=False,
        session_fault_reason=None,
        native_write_enabled=False,
        unresolved_execution_count=0,
        execution_ready=ready,
    )


def test_read_service_groups_providers_by_layer_and_returns_pure_payload() -> None:
    service = FirmExecutionReadService(
        providers=(
            FakeProvider(1, status("DESK-03", ready=False)),
            FakeProvider(0, status("DESK-01")),
            FakeProvider(0, status("DESK-02")),
        )
    )

    snapshot = service.snapshot()
    payload = service.payload()

    assert tuple(layer.layer for layer in snapshot.layers) == (0, 1)
    assert snapshot.desk_count == 3
    assert not snapshot.execution_ready
    assert payload["layers"][0]["desk_count"] == 2
    assert payload["layers"][1]["desks"][0]["desk_id"] == "DESK-03"


def test_duplicate_desk_identity_fails_closed() -> None:
    service = FirmExecutionReadService(
        providers=(
            FakeProvider(0, status("DESK-01")),
            FakeProvider(1, status("DESK-01")),
        )
    )

    with pytest.raises(ValueError, match="duplicate desk status provider"):
        service.snapshot()


def test_negative_provider_layer_fails_closed() -> None:
    service = FirmExecutionReadService(providers=(FakeProvider(-1, status("DESK-01")),))

    with pytest.raises(ValueError, match="layer must be non-negative"):
        service.snapshot()
