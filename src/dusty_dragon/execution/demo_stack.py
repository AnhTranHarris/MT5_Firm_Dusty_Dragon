from __future__ import annotations

from dataclasses import dataclass

from dusty_dragon.brokers.mt5_runtime import (
    MetaTrader5RuntimeModule,
    build_native_demo_write_adapter,
)
from dusty_dragon.domain.accounts import AccountSnapshot
from dusty_dragon.execution.demo_lease_service import DemoLeaseExecutionService
from dusty_dragon.execution.demo_service import DemoExecutionService, MT5OrderAdapter
from dusty_dragon.persistence.authorization_lease import AuthorizationLeaseRepository
from dusty_dragon.persistence.execution_audit import ExecutionAuditRepository
from dusty_dragon.persistence.execution_reconciliation import ExecutionReconciliationRepository


@dataclass(frozen=True, slots=True)
class DemoExecutionStack:
    """Fully composed demo execution boundary with sovereign lease enforcement."""

    executor: DemoLeaseExecutionService
    native_write_enabled: bool


def build_demo_execution_stack(
    *,
    mt5: MetaTrader5RuntimeModule,
    expected_account: AccountSnapshot,
    dry_run_adapter: MT5OrderAdapter,
    lease_repository: AuthorizationLeaseRepository,
    audit_repository: ExecutionAuditRepository,
    reconciliation_repository: ExecutionReconciliationRepository,
    enable_native_write: bool = False,
    magic: int = 0,
) -> DemoExecutionStack:
    """Assemble demo execution without exposing an independent native-write shortcut."""

    native_adapter = build_native_demo_write_adapter(
        mt5,
        expected_account=expected_account,
        enable_write=enable_native_write,
        magic=magic,
    )
    demo_service = DemoExecutionService(
        dry_run_adapter=dry_run_adapter,
        demo_write_adapter=native_adapter,
    )
    executor = DemoLeaseExecutionService(
        lease_repository=lease_repository,
        audit_repository=audit_repository,
        reconciliation_repository=reconciliation_repository,
        demo_service=demo_service,
    )
    return DemoExecutionStack(
        executor=executor,
        native_write_enabled=enable_native_write,
    )
