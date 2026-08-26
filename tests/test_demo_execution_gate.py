from datetime import UTC, datetime

from dusty_dragon.domain.accounts import AccountSnapshot
from dusty_dragon.domain.market import AccountEnvironment
from dusty_dragon.execution.demo_gate import ExecutionMode, authorize_demo_execution


def account(environment: AccountEnvironment) -> AccountSnapshot:
    return AccountSnapshot(
        account_id="A1",
        desk_id="DEMO-01",
        broker_id="B1",
        environment=environment,
        observed_at_utc=datetime(2026, 8, 26, 15, 30, tzinfo=UTC),
        balance=20_000.0,
        equity=20_000.0,
        margin=0.0,
        free_margin=20_000.0,
    )


def test_demo_defaults_to_dry_run() -> None:
    decision = authorize_demo_execution(account(AccountEnvironment.DEMO))

    assert decision.allowed is True
    assert decision.mode is ExecutionMode.DRY_RUN
    assert decision.reason == "DEMO_DRY_RUN_ALLOWED"


def test_demo_write_requires_explicit_mode() -> None:
    decision = authorize_demo_execution(
        account(AccountEnvironment.DEMO),
        mode=ExecutionMode.DEMO_WRITE,
    )

    assert decision.allowed is True
    assert decision.reason == "DEMO_WRITE_ALLOWED"


def test_live_account_is_blocked_even_in_dry_run_mode() -> None:
    decision = authorize_demo_execution(account(AccountEnvironment.LIVE))

    assert decision.allowed is False
    assert decision.reason == "LIVE_ACCOUNT_BLOCKED"


def test_live_account_is_blocked_in_demo_write_mode() -> None:
    decision = authorize_demo_execution(
        account(AccountEnvironment.LIVE),
        mode=ExecutionMode.DEMO_WRITE,
    )

    assert decision.allowed is False
    assert decision.reason == "LIVE_ACCOUNT_BLOCKED"
