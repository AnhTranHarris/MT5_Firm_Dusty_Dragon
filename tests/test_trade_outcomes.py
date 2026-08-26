from datetime import UTC, datetime

import pytest

from dusty_dragon.brokers.contracts import ExecutionResult
from dusty_dragon.domain.trades import GuardDecision, GuardResult, Side, TradeProposal
from dusty_dragon.learning.outcomes import OutcomeClass, TradeOutcome
from dusty_dragon.reporting.trade_report import TradeReport
from dusty_dragon.storage.outcome_store import TradeOutcomeStore


def report(side: Side = Side.BUY) -> TradeReport:
    if side == Side.BUY:
        stop, entry, target = 1.0950, 1.1000, 1.1100
    else:
        target, entry, stop = 1.0900, 1.1000, 1.1050
    proposal = TradeProposal(
        strategy_version="generalist-v0",
        symbol="EURUSD",
        side=side,
        entry_price=entry,
        stop_loss=stop,
        take_profit=target,
        risk_pct=0.25,
        confidence=0.70,
        timeframe="M15",
        thesis="test thesis",
    )
    return TradeReport.from_decision(
        proposal,
        GuardResult(decision=GuardDecision.ALLOW),
        broker_division="boforex",
        account_label="paper-01",
        execution=ExecutionResult(
            accepted=True,
            message="paper fill",
            requested_volume=0.01,
            executed_volume=0.01,
            executed_price=entry,
        ),
        observations={"forecast_return_pct": 0.20},
    )


def test_buy_outcome_computes_positive_r_and_forecast_calibration():
    outcome = TradeOutcome.from_report(
        report(),
        exit_price=1.1050,
        closed_at=datetime(2026, 8, 24, 18, 0, tzinfo=UTC),
    )

    assert outcome.outcome_class == OutcomeClass.WIN
    assert outcome.realized_r == pytest.approx(1.0)
    assert outcome.gross_return_pct > 0
    assert outcome.forecast_direction_correct is True
    assert outcome.forecast_error_pct is not None


def test_sell_outcome_scores_falling_market_as_win():
    outcome = TradeOutcome.from_report(report(Side.SELL), exit_price=1.0950)

    assert outcome.outcome_class == OutcomeClass.WIN
    assert outcome.realized_r == pytest.approx(1.0)
    assert outcome.gross_return_pct > 0


def test_unexecuted_report_cannot_create_outcome():
    executed = report()
    rejected = executed.model_copy(update={"execution": None})

    with pytest.raises(ValueError, match="accepted execution"):
        TradeOutcome.from_report(rejected, exit_price=1.1050)


def test_outcome_store_is_append_once_and_integrity_checked(tmp_path):
    store = TradeOutcomeStore(tmp_path / "outcomes.sqlite3")
    outcome = TradeOutcome.from_report(report(), exit_price=1.1050)

    record_hash = store.append(outcome)
    loaded = store.get(str(outcome.trade_id))

    assert len(record_hash) == 64
    assert loaded is not None
    assert loaded.trade_id == outcome.trade_id
    assert loaded.realized_r == pytest.approx(outcome.realized_r)

    with pytest.raises(ValueError, match="already recorded"):
        store.append(outcome)
