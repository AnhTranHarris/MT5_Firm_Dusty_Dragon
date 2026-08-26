from dataclasses import dataclass
from datetime import UTC, datetime

from dusty_dragon.brokers.mt5_write import DryRunMT5WriteAdapter, MT5RawWriteResult
from dusty_dragon.domain.accounts import AccountSnapshot
from dusty_dragon.domain.market import AccountEnvironment
from dusty_dragon.execution.demo_stack import build_demo_execution_stack
from dusty_dragon.persistence.authorization_lease import AuthorizationLeaseRepository
from dusty_dragon.persistence.execution_audit import ExecutionAuditRepository
from dusty_dragon.persistence.execution_reconciliation import ExecutionReconciliationRepository
from dusty_dragon.persistence.sqlite import connect, initialize


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
        self.initialize_calls: list[tuple[int, int]] = []
        self.shutdown_calls = 0

    def initialize(self, *, login: int, timeout: int) -> bool:
        self.initialize_calls.append((login, timeout))
        return True

    def shutdown(self) -> None:
        self.shutdown_calls += 1

    def account_info(self):
        return self.account

    def symbol_info(self, symbol):
        return SymbolInfo()

    def order_check(self, request):
        return Result(retcode=0, comment="Done")

    def order_send(self, request):
        return Result(retcode=10009, comment="Done")

    def last_error(self):
        return (1, "fake error")


class FakeDryRunTransport:
    def submit_request(self, request):
        return MT5RawWriteResult(10008, "DRY-1", "placed")


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


def repositories():
    connection = connect(":memory:")
    initialize(connection)
    return (
        AuthorizationLeaseRepository(connection),
        ExecutionAuditRepository(connection),
        ExecutionReconciliationRepository(connection),
    )


def test_stack_defaults_native_write_to_disabled() -> None:
    lease_repository, audit_repository, reconciliation_repository = repositories()
    mt5 = FakeMT5()
    stack = build_demo_execution_stack(
        mt5=mt5,
        expected_account=account(),
        dry_run_adapter=DryRunMT5WriteAdapter(FakeDryRunTransport()),
        lease_repository=lease_repository,
        audit_repository=audit_repository,
        reconciliation_repository=reconciliation_repository,
    )

    assert stack.native_write_enabled is False
    assert stack.session.opened
    assert mt5.initialize_calls == [(25115284, 60_000)]
    assert stack.executor.lease_repository is lease_repository
    assert stack.executor.audit_repository is audit_repository
    assert stack.executor.reconciliation_repository is reconciliation_repository

    stack.close()
    stack.close()
    assert mt5.shutdown_calls == 1


def test_stack_can_explicitly_enable_native_demo_write() -> None:
    lease_repository, audit_repository, reconciliation_repository = repositories()
    stack = build_demo_execution_stack(
        mt5=FakeMT5(),
        expected_account=account(),
        dry_run_adapter=DryRunMT5WriteAdapter(FakeDryRunTransport()),
        lease_repository=lease_repository,
        audit_repository=audit_repository,
        reconciliation_repository=reconciliation_repository,
        enable_native_write=True,
        magic=314159,
    )

    assert stack.native_write_enabled is True


def test_stack_refuses_live_expected_account_before_mt5_initialize() -> None:
    lease_repository, audit_repository, reconciliation_repository = repositories()
    mt5 = FakeMT5()

    try:
        build_demo_execution_stack(
            mt5=mt5,
            expected_account=account(AccountEnvironment.LIVE),
            dry_run_adapter=DryRunMT5WriteAdapter(FakeDryRunTransport()),
            lease_repository=lease_repository,
            audit_repository=audit_repository,
            reconciliation_repository=reconciliation_repository,
        )
    except PermissionError as exc:
        assert "not DEMO" in str(exc)
    else:
        raise AssertionError("live expected account must fail closed")

    assert mt5.initialize_calls == []
