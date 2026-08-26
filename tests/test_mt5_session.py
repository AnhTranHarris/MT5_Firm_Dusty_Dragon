from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from dusty_dragon.brokers.mt5_session import MT5DemoSession
from dusty_dragon.domain.accounts import AccountSnapshot
from dusty_dragon.domain.market import AccountEnvironment


@dataclass
class AccountInfo:
    login: int = 25115284
    trade_mode: int = 0
    trade_allowed: bool = True
    trade_expert: bool = True


class FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO = 0

    def __init__(self) -> None:
        self.account = AccountInfo()
        self.initialize_result = True
        self.initialize_calls: list[tuple[int, int]] = []
        self.shutdown_calls = 0

    def initialize(self, *, login: int, timeout: int) -> bool:
        self.initialize_calls.append((login, timeout))
        return self.initialize_result

    def shutdown(self) -> None:
        self.shutdown_calls += 1

    def account_info(self):
        return self.account

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


def test_open_binds_expected_login_and_close_is_idempotent() -> None:
    mt5 = FakeMT5()
    session = MT5DemoSession(mt5, account())

    session.open()
    assert session.opened
    assert mt5.initialize_calls == [(25115284, 60_000)]

    session.close()
    session.close()
    assert not session.opened
    assert mt5.shutdown_calls == 1


def test_live_snapshot_and_initialize_failure_fail_closed() -> None:
    mt5 = FakeMT5()

    with pytest.raises(PermissionError, match="snapshot is not DEMO"):
        MT5DemoSession(mt5, account(AccountEnvironment.LIVE)).open()
    assert mt5.initialize_calls == []

    mt5.initialize_result = False
    with pytest.raises(RuntimeError, match="initialize failed"):
        MT5DemoSession(mt5, account()).open()
    assert mt5.shutdown_calls == 0


def test_post_initialize_login_drift_closes_session() -> None:
    mt5 = FakeMT5()
    mt5.account.login = 99999999
    session = MT5DemoSession(mt5, account())

    with pytest.raises(PermissionError, match="login drifted"):
        session.open()

    assert not session.opened
    assert mt5.shutdown_calls == 1


def test_runtime_validation_detects_environment_and_permission_drift() -> None:
    mt5 = FakeMT5()
    session = MT5DemoSession(mt5, account())
    session.open()
    mt5.account.trade_mode = 2
    with pytest.raises(PermissionError, match="no longer demo"):
        session.validate_current()

    mt5 = FakeMT5()
    session = MT5DemoSession(mt5, account())
    session.open()
    mt5.account.trade_allowed = False
    with pytest.raises(PermissionError, match="no longer allows trading"):
        session.validate_current()

    mt5 = FakeMT5()
    session = MT5DemoSession(mt5, account())
    session.open()
    mt5.account.trade_expert = False
    with pytest.raises(PermissionError, match="no longer allows expert trading"):
        session.validate_current()


def test_fault_latch_cannot_be_cleared_by_terminal_recovery() -> None:
    mt5 = FakeMT5()
    session = MT5DemoSession(mt5, account())
    session.open()

    mt5.account.trade_mode = 2
    with pytest.raises(PermissionError, match="no longer demo"):
        session.validate_current()

    assert session.faulted
    assert not session.opened
    assert session.fault_reason == "connected MT5 account is no longer demo"
    assert mt5.shutdown_calls == 1

    mt5.account.trade_mode = mt5.ACCOUNT_TRADE_MODE_DEMO
    with pytest.raises(RuntimeError, match="fault is latched"):
        session.open()
    assert mt5.initialize_calls == [(25115284, 60_000)]


def test_recovery_requires_new_verified_session() -> None:
    mt5 = FakeMT5()
    failed_session = MT5DemoSession(mt5, account())
    failed_session.open()
    mt5.account.trade_allowed = False

    with pytest.raises(PermissionError, match="no longer allows trading"):
        failed_session.validate_current()

    mt5.account.trade_allowed = True
    recovered_session = MT5DemoSession(mt5, account())
    recovered_session.open()

    assert recovered_session.opened
    assert not recovered_session.faulted
    assert mt5.initialize_calls == [(25115284, 60_000), (25115284, 60_000)]


def test_context_manager_always_shuts_down() -> None:
    mt5 = FakeMT5()

    with MT5DemoSession(mt5, account()) as session:
        assert session.opened

    assert mt5.shutdown_calls == 1
