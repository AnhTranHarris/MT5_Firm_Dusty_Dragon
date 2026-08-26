from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from dusty_dragon.brokers.mt5_native_write import (
    MT5PreflightError,
    MT5SubmissionUncertainError,
)
from dusty_dragon.brokers.mt5_write import MT5ExecutionParameters
from dusty_dragon.domain.accounts import AccountSnapshot
from dusty_dragon.domain.market import Instrument, InstrumentSpec
from dusty_dragon.execution.demo_gate import ExecutionMode
from dusty_dragon.execution.demo_service import DemoExecutionService
from dusty_dragon.execution.service import ExecutionAttempt
from dusty_dragon.execution.transport import ExecutionReceipt
from dusty_dragon.governance.execution_arm import DemoExecutionArm
from dusty_dragon.persistence.authorization_lease import (
    AuthorizationLeaseRepository,
    LeaseConsumeStatus,
)
from dusty_dragon.persistence.execution_audit import ExecutionAuditRepository
from dusty_dragon.persistence.execution_reconciliation import (
    ExecutionReconciliationRecord,
    ExecutionReconciliationRepository,
)


@dataclass(slots=True)
class DemoLeaseExecutionService:
    """Consume one-time capital authority before entering the demo execution boundary."""

    lease_repository: AuthorizationLeaseRepository
    audit_repository: ExecutionAuditRepository
    reconciliation_repository: ExecutionReconciliationRepository
    demo_service: DemoExecutionService

    def execute(
        self,
        lease_id: str,
        *,
        account: AccountSnapshot,
        instrument: Instrument,
        spec: InstrumentSpec,
        parameters: MT5ExecutionParameters,
        mode: ExecutionMode = ExecutionMode.DRY_RUN,
        arm: DemoExecutionArm | None = None,
        consumed_at_utc: datetime,
    ) -> ExecutionAttempt:
        consumed = self.lease_repository.consume(
            lease_id,
            consumed_at_utc=consumed_at_utc,
        )
        if not consumed.consumed or consumed.lease is None:
            event_id = self._record(
                lease_id=lease_id,
                lease_status=consumed.status,
                receipt=None,
                error=None,
                occurred_at_utc=consumed_at_utc,
            )
            return ExecutionAttempt(
                lease_status=consumed.status,
                receipt=None,
                audit_event_id=event_id,
                reconciliation=None,
            )

        receipt: ExecutionReceipt | None = None
        error: str | None = None
        reconciliation: ExecutionReconciliationRecord | None = None
        try:
            receipt = self.demo_service.submit(
                consumed.lease.order,
                account=account,
                instrument=instrument,
                spec=spec,
                parameters=parameters,
                mode=mode,
                arm=arm,
                now_utc=consumed_at_utc,
            )
        except (PermissionError, ValueError, MT5PreflightError) as exc:
            error = f"{type(exc).__name__}: {exc}"
        except MT5SubmissionUncertainError as exc:
            error = f"{type(exc).__name__}: {exc}"
            reconciliation = self._open_uncertain(
                lease_id=lease_id,
                order=consumed.lease.order,
                opened_at_utc=consumed_at_utc,
            )
        except Exception as exc:  # unknown demo-write failure cannot prove broker non-submission
            error = f"{type(exc).__name__}: {exc}"
            if mode is ExecutionMode.DEMO_WRITE:
                reconciliation = self._open_uncertain(
                    lease_id=lease_id,
                    order=consumed.lease.order,
                    opened_at_utc=consumed_at_utc,
                )
        else:
            reconciliation = self.reconciliation_repository.open_for_receipt(
                lease_id=lease_id,
                order=consumed.lease.order,
                receipt=receipt,
                opened_at_utc=consumed_at_utc,
            )

        event_id = self._record(
            lease_id=lease_id,
            lease_status=LeaseConsumeStatus.CONSUMED,
            receipt=receipt,
            error=error,
            occurred_at_utc=consumed_at_utc,
        )
        return ExecutionAttempt(
            lease_status=LeaseConsumeStatus.CONSUMED,
            receipt=receipt,
            audit_event_id=event_id,
            reconciliation=reconciliation,
            transport_error=error,
        )

    def _open_uncertain(self, *, lease_id, order, opened_at_utc):
        return self.reconciliation_repository.open_for_transport_error(
            lease_id=lease_id,
            order=order,
            opened_at_utc=opened_at_utc,
        )

    def _record(
        self,
        *,
        lease_id: str,
        lease_status: LeaseConsumeStatus,
        receipt: ExecutionReceipt | None,
        error: str | None,
        occurred_at_utc: datetime,
    ) -> str:
        return self.audit_repository.record(
            lease_id=lease_id,
            lease_status=lease_status,
            receipt=receipt,
            transport_error=error,
            occurred_at_utc=occurred_at_utc,
        )
