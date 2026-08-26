from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from dusty_dragon.analytics.capital_growth import CapitalGrowthObjective
from dusty_dragon.domain.trades import Side
from dusty_dragon.learning.outcomes import OutcomeClass, TradeOutcome


def outcome(realized_r: float, index: int) -> TradeOutcome:
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
    )


def test_positive_r_sequence_compounds_capital_upward():
    summary = CapitalGrowthObjective(risk_per_trade_pct=1.0).evaluate(
        [outcome(1.0, 0), outcome(1.0, 1), outcome(-0.5, 2), outcome(2.0, 3)],
        starting_capital=10_000,
    )

    assert summary.ending_capital > 10_000
    assert summary.net_growth > 0
    assert summary.net_growth_pct > 0
    assert summary.profitable is True
    assert summary.capital_preserved is True


def test_disciplined_but_negative_sequence_is_not_profitable():
    summary = CapitalGrowthObjective(risk_per_trade_pct=1.0).evaluate(
        [outcome(-0.2, index) for index in range(10)],
        starting_capital=10_000,
    )

    assert summary.ending_capital < 10_000
    assert summary.net_growth < 0
    assert summary.profitable is False


def test_drawdown_constraint_can_fail_even_when_account_finishes_profitable():
    objective = CapitalGrowthObjective(risk_per_trade_pct=10.0, maximum_drawdown_pct=5.0)
    summary = objective.evaluate(
        [outcome(1.0, 0), outcome(-1.0, 1), outcome(2.0, 2)],
        starting_capital=10_000,
    )

    assert summary.profitable is True
    assert summary.max_drawdown_pct == pytest.approx(10.0)
    assert summary.capital_preserved is False


def test_invalid_starting_capital_is_rejected():
    with pytest.raises(ValueError):
        CapitalGrowthObjective().evaluate([], starting_capital=0)
