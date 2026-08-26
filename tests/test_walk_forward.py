from datetime import UTC, datetime, timedelta

import pytest

from dusty_dragon.backtest.walk_forward import SignalWalkForwardEvaluator
from dusty_dragon.brokers.contracts import MarketBar
from dusty_dragon.intelligence.kronos_forecast import KronosForecast
from dusty_dragon.intelligence.research_signal import GeneralistResearchEngine


def bars(*, rising: bool = True, count: int = 60) -> list[MarketBar]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    result = []
    for index in range(count):
        delta = index * 0.0002 * (1 if rising else -1)
        close = 1.1000 + delta
        result.append(
            MarketBar(
                symbol="EURUSD",
                timeframe="M15",
                opened_at=start + timedelta(minutes=15 * index),
                open=close - 0.0001,
                high=close + 0.0002,
                low=close - 0.0002,
                close=close,
                tick_volume=100,
                spread_points=8.0,
                real_volume=0.0,
            )
        )
    return result


class BullishForecastProvider:
    def __init__(self) -> None:
        self.history_ends = []

    def forecast(self, history: list[MarketBar], horizon_bars: int) -> KronosForecast:
        self.history_ends.append(history[-1].opened_at)
        starting = history[-1].close
        predicted = starting * 1.002
        return KronosForecast(
            symbol=history[-1].symbol,
            timeframe=history[-1].timeframe,
            horizon_bars=horizon_bars,
            starting_close=starting,
            predicted_close=predicted,
            predicted_return_pct=0.20,
            predicted_high=predicted + 0.0002,
            predicted_low=starting - 0.0002,
            forecast_rows=horizon_bars,
            volume_source="tick_volume",
        )


def test_rising_market_with_bullish_evidence_scores_directional_wins():
    provider = BullishForecastProvider()
    evaluator = SignalWalkForwardEvaluator(
        GeneralistResearchEngine(),
        provider,
        horizon_bars=4,
        minimum_history_bars=32,
    )
    history = bars(rising=True)

    result = evaluator.evaluate(history)

    assert result.trade_signals > 0
    assert result.directional_losses == 0
    assert result.directional_accuracy == pytest.approx(1.0)
    assert result.mean_signed_return_pct is not None
    assert result.mean_signed_return_pct > 0
    assert max(provider.history_ends) < history[-1].opened_at


def test_conflicting_forecast_and_trend_abstains_in_falling_market():
    evaluator = SignalWalkForwardEvaluator(
        GeneralistResearchEngine(),
        BullishForecastProvider(),
        horizon_bars=4,
        minimum_history_bars=32,
    )

    result = evaluator.evaluate(bars(rising=False))

    assert result.trade_signals == 0
    assert result.abstentions == result.windows
    assert result.directional_accuracy is None


def test_insufficient_history_fails_closed():
    evaluator = SignalWalkForwardEvaluator(
        GeneralistResearchEngine(),
        BullishForecastProvider(),
        horizon_bars=4,
        minimum_history_bars=32,
    )

    with pytest.raises(ValueError, match="requires at least"):
        evaluator.evaluate(bars(count=35))
