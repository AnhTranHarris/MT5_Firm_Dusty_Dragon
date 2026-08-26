from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from dusty_dragon.domain.models import ApprovedOrder
from dusty_dragon.execution.transport import ExecutionReceipt, ExecutionStatus


class ExecutionReconciliationState(StrEnum):
    UNRESOLVED = "UNRESOLVED"
    CONFIRMED_EXECUTED = "CONFIRMED_EXECUTED"
    CONFIRMED_NOT_EXECUTED = "CONFIRMED_NOT_EXECUTED"


class ExecutionReconciliationSource(StrEnum):
    ACCEPTED = "ACCEPTED"
    AMBIGUOUS = "AMBIGUOUS"
    TRANSPORT_ERROR = "TRANSPORT_ERROR"


@dataclass(frozen=True, slots=True)
class ExecutionReconciliationRecord:
    reconciliation_id: str
    lease_id: str
    desk_id: str
    instrument_id: str
    broker_order_id: str | None
    source_status: ExecutionReconciliationSource
    state: ExecutionReconciliationState
    opened_at_utc: datetime
    resolved_at_utc: datetime | None
    resolution_evidence_id: str | None


@dataclass(slots=True)
class ExecutionReconciliationRepository:
    """Track broker-write outcomes that require independent broker evidence."""

    connection: sqlite3.Connection

    def open_for_receipt(
        self,
        *,
        lease_id: str,
        order: ApprovedOrder,
        receipt: ExecutionReceipt,
        opened_at_utc: datetime,
    ) -> ExecutionReconciliationRecord | None:
        if not receipt.requires_reconciliation:
            return None
        source = (
            ExecutionReconciliationSource.ACCEPTED
            if receipt.status is ExecutionStatus.ACCEPTED
            else ExecutionReconciliationSource.AMBIGUOUS
        )
        return self._open(
            lease_id=lease_id,
            order=order,
            broker_order_id=receipt.broker_order_id,
            source_status=source,
            opened_at_utc=opened_at_utc,
        )

    def open_for_transport_error(
        self,
        *,
        lease_id: str,
        order: ApprovedOrder,
        opened_at_utc: datetime,
    ) -> ExecutionReconciliationRecord:
        return self._open(
            lease_id=lease_id,
            order=order,
            broker_order_id=None,
            source_status=ExecutionReconciliationSource.TRANSPORT_ERROR,
            opened_at_utc=opened_at_utc,
        )

    def resolve(
        self,
        reconciliation_id: str,
        *,
        state: ExecutionReconciliationState,
        evidence_id: str,
        resolved_at_utc: datetime,
    ) -> ExecutionReconciliationRecord:
        if state is ExecutionReconciliationState.UNRESOLVED:
            raise ValueError("resolution state must be terminal")
        if not evidence_id.strip():
            raise ValueError("evidence_id is required")
        _require_utc(resolved_at_utc, "resolved_at_utc")

        with self.connection:
            cursor = self.connection.execute(
                """
                UPDATE execution_reconciliations
                SET state = ?, resolved_at_utc = ?, resolution_evidence_id = ?
                WHERE reconciliation_id = ? AND state = 'UNRESOLVED'
                """,
                (
                    state.value,
                    resolved_at_utc.isoformat(),
                    evidence_id,
                    reconciliation_id,
                ),
            )
        if cursor.rowcount != 1:
            raise LookupError("unresolved execution reconciliation not found")
        record = self.get(reconciliation_id)
        if record is None:
            raise RuntimeError("resolved execution reconciliation disappeared")
        return record

    def get(self, reconciliation_id: str) -> ExecutionReconciliationRecord | None:
        row = self.connection.execute(
            "SELECT * FROM execution_reconciliations WHERE reconciliation_id = ?",
            (reconciliation_id,),
        ).fetchone()
        return None if row is None else _record_from_row(row)

    def unresolved_for_desk(self, desk_id: str) -> tuple[ExecutionReconciliationRecord, ...]:
        rows = self.connection.execute(
            """
            SELECT * FROM execution_reconciliations
            WHERE desk_id = ? AND state = 'UNRESOLVED'
            ORDER BY opened_at_utc, reconciliation_id
            """,
            (desk_id,),
        ).fetchall()
        return tuple(_record_from_row(row) for row in rows)

    def _open(
        self,
        *,
        lease_id: str,
        order: ApprovedOrder,
        broker_order_id: str | None,
        source_status: ExecutionReconciliationSource,
        opened_at_utc: datetime,
    ) -> ExecutionReconciliationRecord:
        if not lease_id.strip():
            raise ValueError("lease_id is required")
        _require_utc(opened_at_utc, "opened_at_utc")
        record = ExecutionReconciliationRecord(
            reconciliation_id=f"execution-reconciliation-{uuid4()}",
            lease_id=lease_id,
            desk_id=order.desk_id,
            instrument_id=order.instrument_id,
            broker_order_id=broker_order_id,
            source_status=source_status,
            state=ExecutionReconciliationState.UNRESOLVED,
            opened_at_utc=opened_at_utc,
            resolved_at_utc=None,
            resolution_evidence_id=None,
        )
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO execution_reconciliations(
                    reconciliation_id, lease_id, desk_id, instrument_id,
                    broker_order_id, source_status, state, opened_at_utc,
                    resolved_at_utc, resolution_evidence_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
                """,
                (
                    record.reconciliation_id,
                    record.lease_id,
                    record.desk_id,
                    record.instrument_id,
                    record.broker_order_id,
                    record.source_status.value,
                    record.state.value,
                    record.opened_at_utc.isoformat(),
                ),
            )
        return record


def _record_from_row(row: sqlite3.Row) -> ExecutionReconciliationRecord:
    resolved = row["resolved_at_utc"]
    return ExecutionReconciliationRecord(
        reconciliation_id=str(row["reconciliation_id"]),
        lease_id=str(row["lease_id"]),
        desk_id=str(row["desk_id"]),
        instrument_id=str(row["instrument_id"]),
        broker_order_id=str(row["broker_order_id"]) if row["broker_order_id"] else None,
        source_status=ExecutionReconciliationSource(str(row["source_status"])),
        state=ExecutionReconciliationState(str(row["state"])),
        opened_at_utc=datetime.fromisoformat(str(row["opened_at_utc"])),
        resolved_at_utc=datetime.fromisoformat(str(resolved)) if resolved else None,
        resolution_evidence_id=(
            str(row["resolution_evidence_id"]) if row["resolution_evidence_id"] else None
        ),
    )


def _require_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be timezone-aware UTC")
