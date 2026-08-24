from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from dusty_dragon.brokers.contracts import MarketBar
from dusty_dragon.intelligence.kronos_forecast import KronosForecastService


class FakePredictor:
    def __init__(self, prediction: pd.DataFrame) -> None:
        self.prediction = prediction
        self.call = None

    def predict(self, **kwargs):
        self.call = kwargs
        return self.prediction.copy()


def bar(index: int) -> MarketBar:
    price = 1.1000 + index * 0.0001
    return MarketBar(
        symbol="EURUSD",
        timeframe="M15",
        opened_at=datetime(2026, 8, 24, 12, 0, tzinfo=UTC) + timedelta(minutes=15 * index),
        open=price,
        high=price + 0.0003,
        low=price - 0.0002,
        close=price + 0.0001,
        tick_volume=100 + index,
        spread_points=20,
        real_volume=0,
    )


def prediction() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": [1.1004, 1.1007],
            "high": [1.1009, 1.1012],
            "low": [1.1002, 1.1005],
            "close": [1.1007, 1.1010],
            "volume": [110, 120],
        }
    )


def test_forecast_wraps_upstream_predictor_without_creating_trade_logic() -> None:
    predictor = FakePredictor(prediction())
    service = KronosForecastService(predictor=predictor)

    result = service.forecast([bar(0), bar(1), bar(2)], horizon_bars=2)

    assert result.symbol == "EURUSD"
    assert result.timeframe == "M15"
    assert result.predicted_close == pytest.approx(1.1010)
    assert result.predicted_high == pytest.approx(1.1012)
    assert result.predicted_low == pytest.approx(1.1002)
    assert result.volume_source == "mt5_tick_volume"
    assert predictor.call is not None
    assert predictor.call["pred_len"] == 2
    assert predictor.call["T"] == 1.0
    assert predictor.call["top_p"] == 0.9
    assert len(predictor.call["y_timestamp"]) == 2


def test_future_timestamps_follow_observed_bar_interval() -> None:
    predictor = FakePredictor(prediction())
    service = KronosForecastService(predictor=predictor)

    service.forecast([bar(0), bar(1), bar(2)], horizon_bars=2)

    future = predictor.call["y_timestamp"]
    assert future.iloc[0] == datetime(2026, 8, 24, 12, 45, tzinfo=UTC)
    assert future.iloc[1] == datetime(2026, 8, 24, 13, 0, tzinfo=UTC)


def test_prediction_with_wrong_row_count_fails_closed() -> None:
    predictor = FakePredictor(prediction().iloc[:1])
    service = KronosForecastService(predictor=predictor)

    with pytest.raises(ValueError, match="expected 2"):
        service.forecast([bar(0), bar(1), bar(2)], horizon_bars=2)


def test_prediction_with_invalid_ohlc_fails_closed() -> None:
    invalid = prediction()
    invalid.loc[0, "low"] = 1.2
    predictor = FakePredictor(invalid)
    service = KronosForecastService(predictor=predictor)

    with pytest.raises(ValueError, match="low above high"):
        service.forecast([bar(0), bar(1), bar(2)], horizon_bars=2)


def test_forecast_requires_at_least_two_historical_timestamps() -> None:
    predictor = FakePredictor(prediction())
    service = KronosForecastService(predictor=predictor)

    with pytest.raises(ValueError, match="at least two"):
        service.forecast([bar(0)], horizon_bars=2)
