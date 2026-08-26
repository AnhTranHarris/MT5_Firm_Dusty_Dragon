import json
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from dusty_dragon.domain.accounts import AccountSnapshot
from dusty_dragon.domain.market import AccountEnvironment
from dusty_dragon.execution.read_service import (
    DemoDeskExecutionStatusProvider,
    FirmExecutionReadService,
)
from dusty_dragon.execution.status import DemoExecutionStatus
from dusty_dragon.persistence.execution_reconciliation import ExecutionReconciliationRepository
from dusty_dragon.persistence.sqlite import connect, initialize


@dataclass
class FakeProvider:
    layer: int
    status: DemoExecutionStatus

    def snapshot(self) -> DemoExecutionStatus:
        return self.status


@dataclass
class FakeSession:
    opened: bool = True
    faulted: bool = False
    fault_reason: str | None = None


@dataclass
class FakeRuntimeStack:
    session: FakeSession
    native_write_enabled: bool = False


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


def runtime_account() -> AccountSnapshot:
    return AccountSnapshot(
        account_id="25115284",
        desk_id="DEMO-01",
        broker_id="B1",
        environment=AccountEnvironment.DEMO,
        observed_at_utc=datetime(2026, 8, 26, 21, 5, tzinfo=UTC),
        balance=20_500.0,
        equity=20_450.0,
        margin=100.0,
        free_margin=20_350.0,
    )


def reconciliation_repository() -> ExecutionReconciliationRepository:
    connection = connect(":memory:")
    initialize(connection)
    return ExecutionReconciliationRepository(connection)


def test_read_service_groups_and_sorts_providers_into_versioned_payload() -> None:
    service = FirmExecutionReadService(
        providers=(
            FakeProvider(1, status("DESK-03", ready=False)),
            FakeProvider(0, status("DESK-02")),
            FakeProvider(0, status("DESK-01")),
        )
    )

    snapshot = service.snapshot()
    payload = service.payload()

    assert tuple(layer.layer for layer in snapshot.layers) == (0, 1)
    assert tuple(desk.desk_id for desk in snapshot.layers[0].desks) == ("DESK-01", "DESK-02")
    assert snapshot.desk_count == 3
    assert not snapshot.execution_ready
    assert payload["contract_version"] == "1"
    assert payload["layers"][0]["desk_count"] == 2
    assert payload["layers"][0]["desks"][0]["desk_id"] == "DESK-01"
    assert payload["layers"][1]["desks"][0]["desk_id"] == "DESK-03"


def test_concrete_demo_provider_reaches_json_safe_firm_payload() -> None:
    provider = DemoDeskExecutionStatusProvider(
        layer=0,
        stack=FakeRuntimeStack(FakeSession()),
        account=runtime_account(),
        reconciliation_repository=reconciliation_repository(),
    )
    service = FirmExecutionReadService(providers=(provider,))

    payload = service.payload()

    assert payload["contract_version"] == "1"
    assert payload["desk_count"] == 1
    assert payload["layers"][0]["desks"][0]["desk_id"] == "DEMO-01"
    assert payload["layers"][0]["desks"][0]["environment"] == "DEMO"
    json.dumps(payload)


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
