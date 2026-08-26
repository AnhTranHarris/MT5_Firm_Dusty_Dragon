from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from dusty_dragon.domain.accounts import AccountSnapshot
from dusty_dragon.execution.demo_stack import DemoExecutionStack


class DemoOperatorCommand(StrEnum):
    SHUTDOWN_EXECUTION = "SHUTDOWN_EXECUTION"
    REQUEST_SESSION_REBUILD = "REQUEST_SESSION_REBUILD"


@dataclass(frozen=True, slots=True)
class DemoOperatorRequest:
    command: DemoOperatorCommand
    desk_id: str


@dataclass(frozen=True, slots=True)
class DemoOperatorResult:
    command: DemoOperatorCommand
    desk_id: str
    accepted: bool
    session_closed: bool
    requires_stack_rebuild: bool
    message: str


@dataclass(slots=True)
class DemoOperatorService:
    """PC-only command boundary; never grants capital authority or LIVE execution."""

    stack: DemoExecutionStack
    account: AccountSnapshot

    def execute(self, request: DemoOperatorRequest) -> DemoOperatorResult:
        if request.desk_id != self.account.desk_id:
            return DemoOperatorResult(
                command=request.command,
                desk_id=request.desk_id,
                accepted=False,
                session_closed=not self.stack.session.opened,
                requires_stack_rebuild=False,
                message="desk_id does not match the bound demo execution stack",
            )

        self.stack.close()
        rebuild = request.command is DemoOperatorCommand.REQUEST_SESSION_REBUILD
        message = (
            "session closed; construct a new verified demo execution stack"
            if rebuild
            else "demo execution session shut down"
        )
        return DemoOperatorResult(
            command=request.command,
            desk_id=request.desk_id,
            accepted=True,
            session_closed=True,
            requires_stack_rebuild=rebuild,
            message=message,
        )
