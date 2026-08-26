import json
from datetime import UTC, datetime

import pytest

from dusty_dragon.domain.models import ApprovedOrder, OrderIntent
from dusty_dragon.governance.preorder import PreOrderDecision, PreOrderStatus
from dusty_dragon.persistence.preorder_audit import PreOrderAuditRepository
from dusty_dragon.persistence.sqlite import connect, initialize


def intent() -> OrderIntent:
    return OrderIntent(
        desk_id="GENERALIST-01",
        instrument_id="FX.EURUSD@B1",
        side="BUY",
        requested_risk_fraction=0.01,
    )


def approved_decision() -> PreOrderDecision:
    return PreOrderDecision(
        status=PreOrderStatus.APPROVED,
        approved_order=ApprovedOrder(
            desk_id="GENERALIST-01",
            instrument_id="FX.EURUSD@B1",
            side="BUY",
            approved_risk_fraction=0.01,
            policy_id="financial_v1",
        ),
        reasons=(),
    )


def test_records_approved_authorization_as_immutable_audit_event() -> None:
    connection = connect(":memory:")
    initialize(connection)
    repository = PreOrderAuditRepository(connection)
    occurred_at = datetime(2026, 8, 26, 11, 15, tzinfo=UTC)

    event_id = repository.record(
        intent=intent(),
        decision=approved_decision(),
        policy_id="financial_v1",
        occurred_at_utc=occurred_at,
    )

    row = connection.execute(
        "SELECT event_type, actor, subject_id, policy_id, payload_json "
        "FROM audit_events WHERE event_id = ?",
        (event_id,),
    ).fetchone()
    payload = json.loads(row["payload_json"])

    assert row["event_type"] == "PREORDER_AUTHORIZATION"
    assert row["actor"] == "DUSTY_CORE"
    assert row["subject_id"] == "GENERALIST-01"
    assert row["policy_id"] == "financial_v1"
    assert payload["status"] == "APPROVED"
    assert payload["approved_order"]["approved_risk_fraction"] == 0.01


def test_records_veto_without_manufacturing_approved_order() -> None:
    connection = connect(":memory:")
    initialize(connection)
    repository = PreOrderAuditRepository(connection)
    decision = PreOrderDecision(
        status=PreOrderStatus.PORTFOLIO_RISK_REJECTED,
        approved_order=None,
        reasons=("aggregate portfolio capacity unavailable",),
    )

    event_id = repository.record(
        intent=intent(),
        decision=decision,
        policy_id="financial_v1",
        occurred_at_utc=datetime(2026, 8, 26, 11, 16, tzinfo=UTC),
    )
    row = connection.execute(
        "SELECT payload_json FROM audit_events WHERE event_id = ?",
        (event_id,),
    ).fetchone()
    payload = json.loads(row["payload_json"])

    assert payload["status"] == "PORTFOLIO_RISK_REJECTED"
    assert payload["approved_order"] is None
    assert payload["reasons"] == ["aggregate portfolio capacity unavailable"]


def test_rejects_non_utc_audit_timestamp() -> None:
    connection = connect(":memory:")
    initialize(connection)
    repository = PreOrderAuditRepository(connection)

    with pytest.raises(ValueError, match="timezone-aware UTC"):
        repository.record(
            intent=intent(),
            decision=approved_decision(),
            policy_id="financial_v1",
            occurred_at_utc=datetime(2026, 8, 26, 11, 17),
        )
