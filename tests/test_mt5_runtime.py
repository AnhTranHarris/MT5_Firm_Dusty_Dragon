"""QC coverage for the native MT5 demo-account runtime guard."""

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from dusty_dragon.brokers.mt5_runtime import build_native_demo_write_adapter
from dusty_dragon.brokers.mt5_write import MT5ExecutionParameters
from dusty_dragon.domain.accounts import AccountSnapshot
from dusty_dragon.domain.market import (
    AccountEnvironment,
    AssetClass,
    Instrument,
    InstrumentSpec,
)
from dusty_dragon.domain.models import ApprovedOrder


@dataclass
class AccountInfo:
    login: int = 25115284
    trade_mode: int = 0
    trade_allowed: bool = True
    trade_expert: bool = True


@dataclass
class SymbolInfo:
    visible: bool = True
    filling_mode: int = 1
    trade_exemode: int = 0


@dataclass
class Result:
    retcode: int
    comment: str
    order: int = 42


class FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO = 0
    TRADE_ACTION_DEAL = 1
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TIME_GTC = 0
    ORDER_FILLING_FOK = 0
    ORDER_FILLING_IOC = 1
    ORDER_FILLING_RETURN = 2
    SYMBOL_FILLING_FOK = 1
    SYMBOL_FILLING_IOC = 2
    SYMBOL_TRADE_EXECUTION_MARKET = 2

    def __init__(self) -> None:
        self.account = AccountInfo()
        self.send_calls = 0

    def account_info(self):
        return self.account

    def symbol_info(self, symbol):
        return SymbolInfo() if symbol == "EURUSD" else None

    def order_check(self, request):
        return Result(retcode=0, comment="Done")

    def order_send(self, request):
        self.send_calls += 1
        return Result(retcode=10009, comment="Done")

    def last_error(self):
        return (1, "fake error")


def account(environment: AccountEnvironment = AccountEnvironment.DEMO) -> AccountSnapshot:
    return AccountSnapshot(
        account_id="25115284",
        desk_id="DEMO-01",
        broker_id="B1",
        environment=environment,
        observed_at_utc=datetime(2026, 8, 26, 20, 30, tzinfo=UTC),
        balance=20_000.0,
        equity=20_000.0,
        margin=0.0,
        free_margin=20_000.0,
    )


def order() -> ApprovedOrder:
    return ApprovedOrder(
        desk_id="DEMO-01",
        instrument_id="FX.EURUSD@B1",
        side="BUY",
        approved_risk_fraction=0.01,
        policy_id="financial_v1",
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
        effective_from_utc=datetime(2026, 8, 26, 20, 30, tzinfo=UTC),
    )


def test_runtime_guard_blocks_live_dusty_snapshot() -> None:
    mt5 = FakeMT5()

    with pytest.raises(PermissionError, match="snapshot is not DEMO"):
        build_native_demo_write_adapter(mt5, expected_account=account(AccountEnvironment.LIVE))

    assert mt5.send_calls == 0


def test_runtime_guard_blocks_native_live_account_and_login_mismatch() -> None:
    mt5 = FakeMT5()
    mt5.account.trade_mode = 2

    with pytest.raises(PermissionError, match="not a demo account"):
        build_native_demo_write_adapter(mt5, expected_account=account())

    mt5.account.trade_mode = mt5.ACCOUNT_TRADE_MODE_DEMO
    mt5.account.login = 99999999
    with pytest.raises(PermissionError, match="login does not match"):
        build_native_demo_write_adapter(mt5, expected_account=account())


def test_runtime_guard_requires_native_trading_permissions() -> None:
    mt5 = FakeMT5()
    mt5.account.trade_allowed = False

    with pytest.raises(PermissionError, match="does not allow trading"):
        build_native_demo_write_adapter(mt5, expected_account=account())

    mt5.account.trade_allowed = True
    mt5.account.trade_expert = False
    with pytest.raises(PermissionError, match="expert trading"):
        build_native_demo_write_adapter(mt5, expected_account=account())


def test_native_write_capability_remains_disabled_by_default() -> None:
    mt5 = FakeMT5()
    adapter = build_native_demo_write_adapter(mt5, expected_account=account())

    with pytest.raises(PermissionError, match="capability is disabled"):
        adapter.submit(
            order(),
            instrument=instrument(),
            spec=spec(),
            parameters=MT5ExecutionParameters(volume=0.01, reference_price=1.17),
        )

    assert mt5.send_calls == 0


def test_explicit_native_write_enablement_can_reach_fake_order_send() -> None:
    mt5 = FakeMT5()
    adapter = build_native_demo_write_adapter(
        mt5,
        expected_account=account(),
        enable_write=True,
        magic=314159,
    )

    receipt = adapter.submit(
        order(),
        instrument=instrument(),
        spec=spec(),
        parameters=MT5ExecutionParameters(volume=0.01, reference_price=1.17),
    )

    assert receipt.broker_order_id == "42"
    assert mt5.send_calls == 1
