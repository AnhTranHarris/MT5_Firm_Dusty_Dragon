from dataclasses import dataclass
from datetime import UTC, datetime

from dusty_dragon.domain.accounts import AccountSnapshot
from dusty_dragon.domain.market import AccountEnvironment
from dusty_dragon.execution.operator import (
    DemoOperatorCommand,
    DemoOperatorRequest,
    DemoOperatorService,
)


@dataclass
class FakeSession:
    opened: bool = True


@dataclass
class FakeStack:
    session: FakeSession
    close_calls: int = 0

    def close(self) -> None:
        self.close_calls += 1
        self.session.opened = False


def account() -> AccountSnapshot:
    return AccountSnapshot(
        account_id="25115284",
        desk_id="DEMO-01",
        broker_id="B1",
        environment=AccountEnvironment.DEMO,
        observed_at_utc=datetime(2026, 8, 26, 21, 0, tzinfo=UTC),
        balance=20_000.0,
        equity=20_000.0,
        margin=0.0,
        free_margin=20_000.0,
    )


def test_wrong_desk_command_is_rejected_without_mutation() -> None:
    stack = FakeStack(FakeSession())
    service = DemoOperatorService(stack=stack, account=account())

    result = service.execute(
        DemoOperatorRequest(DemoOperatorCommand.SHUTDOWN_EXECUTION, "DEMO-99")
    )

    assert not result.accepted
    assert stack.close_calls == 0
    assert stack.session.opened


def test_shutdown_closes_bound_demo_stack_without_requesting_rebuild() -> None:
    stack = FakeStack(FakeSession())
    service = DemoOperatorService(stack=stack, account=account())

    result = service.execute(
        DemoOperatorRequest(DemoOperatorCommand.SHUTDOWN_EXECUTION, "DEMO-01")
    )

    assert result.accepted
    assert result.session_closed
    assert not result.requires_stack_rebuild
    assert stack.close_calls == 1


def test_rebuild_request_closes_stack_and_requires_fresh_construction() -> None:
    stack = FakeStack(FakeSession())
    service = DemoOperatorService(stack=stack, account=account())

    result = service.execute(
        DemoOperatorRequest(DemoOperatorCommand.REQUEST_SESSION_REBUILD, "DEMO-01")
    )

    assert result.accepted
    assert result.session_closed
    assert result.requires_stack_rebuild
    assert "new verified demo execution stack" in result.message
    assert stack.close_calls == 1


def test_operator_contract_has_no_live_or_write_enable_command() -> None:
    assert {command.value for command in DemoOperatorCommand} == {
        "SHUTDOWN_EXECUTION",
        "REQUEST_SESSION_REBUILD",
    }
