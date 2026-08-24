from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from dusty_dragon.analytics.performance import FirmPerformanceAnalyzer
from dusty_dragon.domain.trades import Side
from dusty_dragon.learning.outcomes import OutcomeClass, TradeOutcome


def outcome(
    realized_r: float,
    *,
    index: int,
    forecast_correct: bool | None = None,
    forecast_error: float | None = None,
) -> TradeOutcome:
    classification = OutcomeClass.FLAT
    if realized_r > 0:
        classification = OutcomeClass.WIN
    elif realized_r < 0:
        classification = OutcomeClass.LOSS
    return TradeOutcome(
        trade_id=uuid4(),
        closed_at=datetime(2026, 8, 24, 12, 0, tzinfo=UTC) + timedelta(hours=index),
        symbol="EURUSD",
        side=Side.BUY,
        strategy_version="generalist-v0",
        entry_price=1.1000,
        exit_price=1.1010,
        stop_loss=1.0950,
        gross_return_pct=0.1,
        realized_r=realized_r,
        outcome_class=classification,
        forecast_return_pct=0.2 if forecast_correct is not None else None,
        forecast_error_pct=forecast_error,
        forecast_direction_correct=forecast_correct,
    )


def test_empty_summary_is_stable():
    summary = FirmPerformanceAnalyzer().summarize([])

    assert summary.trade_count == 0
    assert summary.total_r == 0
    assert summary.profit_factor_r is None


def test_summary_calculates_expectancy_profit_factor_and_drawdown():
    outcomes = [
        outcome(1.0, index=0, forecast_correct=True, forecast_error=0.1),
        outcome(-0.5, index=1, forecast_correct=False, forecast_error=-0.3),
        outcome(-1.0, index=2),
        outcome(2.0, index=3, forecast_correct=True, forecast_error=0.2),
    ]

    summary = FirmPerformanceAnalyzer().summarize(outcomes)

    assert summary.trade_count == 4
    assert summary.wins == 2
    assert summary.losses == 2
    assert summary.win_rate == pytest.approx(0.5)
    assert summary.total_r == pytest.approx(1.5)
    assert summary.expectancy_r == pytest.approx(0.375)
    assert summary.profit_factor_r == pytest.approx(2.0)
    assert summary.max_drawdown_r == pytest.approx(1.5)
    assert summary.forecast_samples == 3
    assert summary.forecast_direction_accuracy == pytest.approx(2 / 3)
    assert summary.mean_forecast_error_pct == pytest.approx(0.0)
