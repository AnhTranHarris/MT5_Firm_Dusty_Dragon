from datetime import UTC, datetime, timedelta

import pytest

from dusty_dragon.backtest.campaign_evaluator import CostRegimeCampaignEvaluator
from dusty_dragon.backtest.walk_forward import WalkForwardResult
from dusty_dragon.backtest.weekend_protocol import (
    WeekendExperimentResult,
    WeekendProtocolResult,
)
from dusty_dragon.brokers.contracts import MarketBar


def bars(symbol: str, *, volatile: bool = False) -> list[MarketBar]:
    start = datetime(2026, 8, 17, tzinfo=UTC)
    result = []
    for index in range(20):
        if volatile:
            close = 1.10 + (0.002 if index % 2 else -0.002) + index * 0.0002
        else:
            close = 1.10 + index * 0.0002
        result.append(
            MarketBar(
                symbol=symbol,
                timeframe="M15",
                opened_at=start + timedelta(minutes=15 * index),
                open=close,
                high=close + 0.0003,
                low=close - 0.0003,
                close=close,
                tick_volume=100,
                spread_points=8.0,
                real_volume=0.0,
            )
        )
    return result


def experiment(symbol: str, mean_return: float) -> WeekendExperimentResult:
    series = bars(symbol)
    return WeekendExperimentResult(
        experiment_type="cross_symbol",
        source_symbol="EURUSD",
        tested_symbol=symbol,
        reference_started_at=series[0].opened_at,
        reference_ended_at=series[-1].opened_at,
        run_number=1,
        random_seed=7,
        walk_forward=WalkForwardResult(
            windows=10,
            trade_signals=5,
            abstentions=5,
            directional_wins=4,
            directional_losses=1,
            directional_accuracy=0.8,
            mean_signed_return_pct=mean_return,
        ),
    )


def test_cost_adjustment_reduces_apparent_edge():
    series = bars("EURUSD")
    protocol = WeekendProtocolResult(
        random_seed=7,
        runs_per_symbol=10,
        cross_symbol_results=[experiment("EURUSD", 0.10)],
    )
    evaluator = CostRegimeCampaignEvaluator(default_point_size=0.00001)

    result = evaluator.evaluate(protocol, bars_by_symbol={"EURUSD": series})

    assert result.experiment_count == 1
    item = result.experiments[0]
    assert item.estimated_cost_pct_per_trade > 0
    assert item.cost_adjusted_mean_return_pct is not None
    assert item.cost_adjusted_mean_return_pct < item.raw_mean_signed_return_pct


def test_cost_can_turn_small_raw_edge_negative():
    series = bars("EURUSD")
    protocol = WeekendProtocolResult(
        random_seed=7,
        runs_per_symbol=10,
        cross_symbol_results=[experiment("EURUSD", 0.001)],
    )
    evaluator = CostRegimeCampaignEvaluator(default_point_size=0.0001)

    result = evaluator.evaluate(protocol, bars_by_symbol={"EURUSD": series})

    assert result.profitable_after_cost_count == 0
    assert result.worst_cost_adjusted_return_pct is not None
    assert result.worst_cost_adjusted_return_pct < 0


def test_regime_is_attached_and_grouped():
    normal = bars("EURUSD")
    volatile = bars("GBPUSD", volatile=True)
    protocol = WeekendProtocolResult(
        random_seed=7,
        runs_per_symbol=10,
        cross_symbol_results=[
            experiment("EURUSD", 0.10),
            WeekendExperimentResult(
                experiment_type="cross_symbol",
                source_symbol="EURUSD",
                tested_symbol="GBPUSD",
                reference_started_at=volatile[0].opened_at,
                reference_ended_at=volatile[-1].opened_at,
                run_number=1,
                random_seed=7,
                walk_forward=WalkForwardResult(
                    windows=10,
                    trade_signals=5,
                    abstentions=5,
                    directional_wins=3,
                    directional_losses=2,
                    directional_accuracy=0.6,
                    mean_signed_return_pct=0.05,
                ),
            ),
        ],
    )
    evaluator = CostRegimeCampaignEvaluator(
        default_point_size=0.00001,
        high_volatility_threshold_pct=0.05,
    )

    result = evaluator.evaluate(
        protocol,
        bars_by_symbol={"EURUSD": normal, "GBPUSD": volatile},
    )

    assert len(result.regime_mean_returns) >= 1
    assert {item.tested_symbol for item in result.experiments} == {"EURUSD", "GBPUSD"}
    assert all(item.regime for item in result.experiments)


def test_invalid_cost_configuration_fails_closed():
    with pytest.raises(ValueError):
        CostRegimeCampaignEvaluator(default_point_size=0)
