from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from dusty_dragon.domain.accounts import AccountSnapshot
from dusty_dragon.domain.market import AccountEnvironment
from dusty_dragon.execution.demo_stack import DemoExecutionStack
from dusty_dragon.persistence.execution_reconciliation import ExecutionReconciliationRepository


@dataclass(frozen=True, slots=True)
class DemoExecutionStatus:
    """UI-safe read model for one demo desk execution boundary."""

    desk_id: str
    account_id: str
    broker_id: str
    environment: AccountEnvironment
    observed_at_utc: datetime
    balance: float
    equity: float
    free_margin: float
    session_open: bool
    session_faulted: bool
    session_fault_reason: str | None
    native_write_enabled: bool
    unresolved_execution_count: int
    execution_ready: bool


def build_demo_execution_status(
    *,
    stack: DemoExecutionStack,
    account: AccountSnapshot,
    reconciliation_repository: ExecutionReconciliationRepository,
) -> DemoExecutionStatus:
    """Build a broker-neutral snapshot suitable for PC and website presentation layers."""

    unresolved_count = len(reconciliation_repository.unresolved_for_desk(account.desk_id))
    session = stack.session
    execution_ready = (
        account.environment is AccountEnvironment.DEMO
        and session.opened
        and not session.faulted
        and unresolved_count == 0
    )
    return DemoExecutionStatus(
        desk_id=account.desk_id,
        account_id=account.account_id,
        broker_id=account.broker_id,
        environment=account.environment,
        observed_at_utc=account.observed_at_utc,
        balance=account.balance,
        equity=account.equity,
        free_margin=account.free_margin,
        session_open=session.opened,
        session_faulted=session.faulted,
        session_fault_reason=session.fault_reason,
        native_write_enabled=stack.native_write_enabled,
        unresolved_execution_count=unresolved_count,
        execution_ready=execution_ready,
    )
