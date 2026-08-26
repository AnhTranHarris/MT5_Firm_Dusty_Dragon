from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from dusty_dragon.domain.accounts import AccountSnapshot
from dusty_dragon.domain.market import AccountEnvironment


class ExecutionMode(StrEnum):
    DRY_RUN = "DRY_RUN"
    DEMO_WRITE = "DEMO_WRITE"


@dataclass(frozen=True, slots=True)
class DemoExecutionDecision:
    allowed: bool
    mode: ExecutionMode
    reason: str


def authorize_demo_execution(
    account: AccountSnapshot,
    *,
    mode: ExecutionMode = ExecutionMode.DRY_RUN,
) -> DemoExecutionDecision:
    """Allow execution only inside an explicitly demo-scoped account boundary."""

    if account.environment is not AccountEnvironment.DEMO:
        return DemoExecutionDecision(
            allowed=False,
            mode=mode,
            reason="LIVE_ACCOUNT_BLOCKED",
        )

    if mode is ExecutionMode.DRY_RUN:
        return DemoExecutionDecision(
            allowed=True,
            mode=mode,
            reason="DEMO_DRY_RUN_ALLOWED",
        )

    if mode is ExecutionMode.DEMO_WRITE:
        return DemoExecutionDecision(
            allowed=True,
            mode=mode,
            reason="DEMO_WRITE_ALLOWED",
        )

    return DemoExecutionDecision(
        allowed=False,
        mode=mode,
        reason="UNSUPPORTED_EXECUTION_MODE",
    )
