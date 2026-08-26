from datetime import UTC, datetime, timedelta

import pytest

from dusty_dragon.brokers.contracts import MarketBar
from dusty_dragon.research.factors import FactorEngine


def make_bars(*, step: float = 0.0002, spread: float = 8.0) -> list[MarketBar]:
    start = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
    bars: list[MarketBar] = []
    for index in range(24):
        close = 1.1000 + index * step
        bars.append(
            MarketBar(
                symbol="EURUSD",
                timeframe="M15",
                opened_at=start + timedelta(minutes=15 * index),
                open=close - 0.0001,
                high=close + 0.0002,
                low=close - 0.0002,
                close=close,
                tick_volume=100 + index,
                spread_points=spread,
                real_volume=0,
            )
        )
    return bars


def test_factor_engine_produces_portable_snapshot():
    snapshot = FactorEngine().evaluate(make_bars())

    assert snapshot.symbol == "EURUSD"
    assert snapshot.timeframe == "M15"
    assert snapshot.trend_return_pct > 0
    assert snapshot.momentum_return_pct > 0
    assert snapshot.average_spread_points == pytest.approx(8.0)
    assert snapshot.regime in {
        "trend_low_vol",
        "trend_high_vol",
        "range_low_vol",
        "range_high_vol",
    }


def test_factor_engine_rejects_mixed_symbols():
    bars = make_bars()
    bars[-1] = bars[-1].model_copy(update={"symbol": "GBPUSD"})

    with pytest.raises(ValueError, match="one symbol"):
        FactorEngine().evaluate(bars)


def test_factor_engine_requires_enough_history():
    with pytest.raises(ValueError, match="requires at least"):
        FactorEngine().evaluate(make_bars()[:10])
