from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from dusty_dragon.brokers.mt5_write import (
    DryRunMT5WriteAdapter,
    MT5ExecutionParameters,
)
from dusty_dragon.domain.accounts import AccountSnapshot
from dusty_dragon.domain.market import Instrument, InstrumentSpec
from dusty_dragon.domain.models import ApprovedOrder
from dusty_dragon.execution.demo_gate import ExecutionMode, authorize_demo_execution
from dusty_dragon.execution.transport import ExecutionReceipt
from dusty_dragon.governance.execution_arm import DemoExecutionArm, require_active_demo_arm


@dataclass(slots=True)
class DemoExecutionService:
    """Compose demo-only safety gates before any MT5-shaped transport is reached."""

    adapter: DryRunMT5WriteAdapter

    def submit(
        self,
        order: ApprovedOrder,
        *,
        account: AccountSnapshot,
        instrument: Instrument,
        spec: InstrumentSpec,
        parameters: MT5ExecutionParameters,
        mode: ExecutionMode = ExecutionMode.DRY_RUN,
        arm: DemoExecutionArm | None = None,
        now_utc: datetime,
    ) -> ExecutionReceipt:
        if order.desk_id != account.desk_id:
            raise PermissionError("approved order desk does not own broker account")
        if account.broker_id != instrument.broker_id:
            raise PermissionError("broker account and instrument broker do not match")

        decision = authorize_demo_execution(account, mode=mode)
        if not decision.allowed:
            raise PermissionError(decision.reason)

        if mode is ExecutionMode.DEMO_WRITE:
            require_active_demo_arm(
                arm,
                desk_id=order.desk_id,
                account_id=account.account_id,
                now_utc=now_utc,
            )

        return self.adapter.submit(
            order,
            instrument=instrument,
            spec=spec,
            parameters=parameters,
        )
