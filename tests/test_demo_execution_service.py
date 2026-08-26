from datetime import UTC, datetime, timedelta

import pytest

from dusty_dragon.brokers.mt5_write import (
    DryRunMT5WriteAdapter,
    MT5ExecutionParameters,
    MT5RawWriteResult,
)
from dusty_dragon.domain.accounts import AccountSnapshot
from dusty_dragon.domain.market import AccountEnvironment, AssetClass, Instrument, InstrumentSpec
from dusty_dragon.domain.models import ApprovedOrder
from dusty_dragon.execution.demo_gate import ExecutionMode
from dusty_dragon.execution.demo_service import DemoExecutionService
from dusty_dragon.execution.transport import ExecutionStatus
from dusty_dragon.governance.execution_arm import DemoExecutionArm


class FakeTransport:
    def __init__(self) -> None:
        self.requests = []

    def submit_request(self, request):
        self.requests.append(request)
        return MT5RawWriteResult(10008, "77", "placed")


def account(environment: AccountEnvironment = AccountEnvironment.DEMO) -> AccountSnapshot:
    return AccountSnapshot(
        account_id="A1",
        desk_id="DEMO-01",
        broker_id="B1",
        environment=environment,
        observed_at_utc=datetime(2026, 8, 26, 19, 0, tzinfo=UTC),
        balance=20_000.0,
        equity=20_000.0,
        margin=0.0,
        free_margin=20_000.0,
    )


def instrument(broker_id: str = "B1") -> Instrument:
    return Instrument(
        instrument_id="FX.EURUSD@B1",
        broker_id=broker_id,
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
        effective_from_utc=datetime(2026, 8, 26, 19, 0, tzinfo=UTC),
    )


def order() -> ApprovedOrder:
    return ApprovedOrder(
        desk_id="DEMO-01",
        instrument_id="FX.EURUSD@B1",
        side="BUY",
        approved_risk_fraction=0.01,
        policy_id="financial_v1",
    )


def parameters() -> MT5ExecutionParameters:
    return MT5ExecutionParameters(volume=0.01, reference_price=1.17)


def active_arm(now: datetime) -> DemoExecutionArm:
    return DemoExecutionArm(
        desk_id="DEMO-01",
        account_id="A1",
        armed_at_utc=now - timedelta(seconds=1),
        expires_at_utc=now + timedelta(seconds=30),
    )


def service() -> tuple[DemoExecutionService, FakeTransport]:
    transport = FakeTransport()
    return DemoExecutionService(DryRunMT5WriteAdapter(transport)), transport


def test_dry_run_requires_demo_account_but_not_arm() -> None:
    executor, transport = service()
    receipt = executor.submit(
        order(),
        account=account(),
        instrument=instrument(),
        spec=spec(),
        parameters=parameters(),
        now_utc=datetime(2026, 8, 26, 19, 1, tzinfo=UTC),
    )

    assert receipt.status is ExecutionStatus.ACCEPTED
    assert len(transport.requests) == 1


def test_demo_write_requires_active_arm() -> None:
    executor, transport = service()
    now = datetime(2026, 8, 26, 19, 1, tzinfo=UTC)

    with pytest.raises(PermissionError, match="disarmed"):
        executor.submit(
            order(),
            account=account(),
            instrument=instrument(),
            spec=spec(),
            parameters=parameters(),
            mode=ExecutionMode.DEMO_WRITE,
            now_utc=now,
        )

    assert transport.requests == []

    receipt = executor.submit(
        order(),
        account=account(),
        instrument=instrument(),
        spec=spec(),
        parameters=parameters(),
        mode=ExecutionMode.DEMO_WRITE,
        arm=active_arm(now),
        now_utc=now,
    )

    assert receipt.status is ExecutionStatus.ACCEPTED
    assert len(transport.requests) == 1


def test_live_account_and_identity_mismatches_fail_before_transport() -> None:
    executor, transport = service()
    now = datetime(2026, 8, 26, 19, 1, tzinfo=UTC)

    with pytest.raises(PermissionError, match="LIVE_ACCOUNT_BLOCKED"):
        executor.submit(
            order(),
            account=account(AccountEnvironment.LIVE),
            instrument=instrument(),
            spec=spec(),
            parameters=parameters(),
            now_utc=now,
        )

    with pytest.raises(PermissionError, match="broker do not match"):
        executor.submit(
            order(),
            account=account(),
            instrument=instrument("B2"),
            spec=spec(),
            parameters=parameters(),
            now_utc=now,
        )

    assert transport.requests == []
