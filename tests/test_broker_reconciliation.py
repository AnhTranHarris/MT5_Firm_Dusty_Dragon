from __future__ import annotations

from datetime import UTC, datetime

from dusty_dragon.brokers.reconciliation import (
    ReconciliationStatus,
    reconcile_account,
)
from dusty_dragon.domain.accounts import (
    AccountSnapshot,
    PositionSide,
    PositionSnapshot,
)
from dusty_dragon.domain.market import AccountEnvironment


def _account(*, equity: float = 5_100.0) -> AccountSnapshot:
    return AccountSnapshot(
        account_id="ACC-1",
        desk_id="GENERALIST-01",
        broker_id="BROKER_A",
        environment=AccountEnvironment.DEMO,
        observed_at_utc=datetime(2026, 8, 26, 14, 0, tzinfo=UTC),
        balance=5_000.0,
        equity=equity,
        margin=100.0,
        free_margin=5_000.0,
    )


def _position(*, volume: float = 0.01) -> PositionSnapshot:
    return PositionSnapshot(
        position_id="POS-1",
        account_id="ACC-1",
        instrument_id="FX.EURUSD@BROKER_A",
        side=PositionSide.LONG,
        volume=volume,
        open_price=1.17,
        current_price=1.171,
        unrealized_pnl=10.0,
        observed_at_utc=datetime(2026, 8, 26, 14, 0, tzinfo=UTC),
    )


def test_exact_broker_reconciliation_allows_new_orders() -> None:
    result = reconcile_account(
        expected=_account(),
        observed=_account(),
        expected_positions=(_position(),),
        observed_positions=(_position(),),
    )
    assert result.status is ReconciliationStatus.MATCH
    assert result.safe_for_new_orders


def test_equity_or_position_drift_blocks_new_orders() -> None:
    result = reconcile_account(
        expected=_account(),
        observed=_account(equity=5_099.0),
        expected_positions=(_position(),),
        observed_positions=(_position(volume=0.02),),
    )
    assert result.status is ReconciliationStatus.DRIFT
    assert not result.safe_for_new_orders
    assert "equity drift" in result.reasons
    assert "position POS-1 volume drift" in result.reasons


def test_position_assigned_to_wrong_account_is_invalid() -> None:
    invalid_position = PositionSnapshot(
        position_id="POS-1",
        account_id="ACC-OTHER",
        instrument_id="FX.EURUSD@BROKER_A",
        side=PositionSide.LONG,
        volume=0.01,
        open_price=1.17,
        current_price=1.171,
        unrealized_pnl=10.0,
        observed_at_utc=datetime(2026, 8, 26, 14, 0, tzinfo=UTC),
    )
    result = reconcile_account(
        expected=_account(),
        observed=_account(),
        expected_positions=(_position(),),
        observed_positions=(invalid_position,),
    )
    assert result.status is ReconciliationStatus.INVALID
    assert not result.safe_for_new_orders
