import json
from datetime import UTC, datetime

from dusty_dragon.brokers.reconciliation import ReconciliationResult, ReconciliationStatus
from dusty_dragon.persistence.reconciliation_audit import ReconciliationAuditRepository
from dusty_dragon.persistence.sqlite import connect, initialize


def test_reconciliation_audit_is_persisted_with_fail_closed_flag() -> None:
    connection = connect(":memory:")
    initialize(connection)
    repository = ReconciliationAuditRepository(connection)
    result = ReconciliationResult(
        status=ReconciliationStatus.DRIFT,
        reasons=("equity drift", "position set drift"),
    )

    event_id = repository.record(
        account_id="A1",
        result=result,
        policy_id="operations_v1",
        occurred_at_utc=datetime(2026, 8, 26, 10, 0, tzinfo=UTC),
    )

    row = connection.execute(
        "SELECT * FROM audit_events WHERE event_id = ?",
        (event_id,),
    ).fetchone()
    payload = json.loads(row["payload_json"])
    assert row["event_type"] == "BROKER_RECONCILIATION"
    assert row["subject_id"] == "A1"
    assert payload["status"] == "DRIFT"
    assert payload["safe_for_new_orders"] is False
    assert payload["reasons"] == ["equity drift", "position set drift"]


def test_match_audit_records_safe_for_new_orders() -> None:
    connection = connect(":memory:")
    initialize(connection)
    repository = ReconciliationAuditRepository(connection)

    event_id = repository.record(
        account_id="A1",
        result=ReconciliationResult(status=ReconciliationStatus.MATCH, reasons=()),
        policy_id="operations_v1",
    )

    row = connection.execute(
        "SELECT payload_json FROM audit_events WHERE event_id = ?",
        (event_id,),
    ).fetchone()
    payload = json.loads(row["payload_json"])
    assert payload["safe_for_new_orders"] is True
