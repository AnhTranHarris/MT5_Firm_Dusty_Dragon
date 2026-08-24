from datetime import datetime, timedelta, timezone

import pytest

from dusty_dragon.brokers.contracts import MarketBar
from dusty_dragon.intelligence.kronos_bridge import bars_to_kronos_frame, split_kronos_inputs


def bar(minutes: int, *, symbol: str = "EURUSD", timeframe: str = "M15") -> MarketBar:
    opened_at = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc) + timedelta(minutes=minutes)
    return MarketBar(
        symbol=symbol,
        timeframe=timeframe,
        opened_at=opened_at,
        open=1.1000,
        high=1.1020,
        low=1.0990,
        close=1.1010,
        tick_volume=100 + minutes,
        spread_points=20,
        real_volume=0,
    )


def test_bridge_sorts_and_preserves_provenance():
    frame = bars_to_kronos_frame([bar(15), bar(0)])

    assert list(frame.columns) == ["timestamps", "open", "high", "low", "close", "volume"]
    assert frame.iloc[0]["timestamps"] < frame.iloc[1]["timestamps"]
    assert frame.attrs["symbol"] == "EURUSD"
    assert frame.attrs["timeframe"] == "M15"
    assert frame.attrs["volume_source"] == "mt5_tick_volume"


def test_split_matches_kronos_ohlcv_shape():
    frame = bars_to_kronos_frame([bar(0), bar(15)])

    features, timestamps = split_kronos_inputs(frame)

    assert list(features.columns) == ["open", "high", "low", "close", "volume"]
    assert len(features) == len(timestamps) == 2
    assert str(timestamps.dt.tz) == "UTC"


def test_bridge_rejects_mixed_symbols():
    with pytest.raises(ValueError):
        bars_to_kronos_frame([bar(0), bar(15, symbol="GBPUSD")])


def test_bridge_rejects_mixed_timeframes():
    with pytest.raises(ValueError):
        bars_to_kronos_frame([bar(0), bar(15, timeframe="H1")])


def test_bridge_rejects_duplicate_timestamps():
    with pytest.raises(ValueError):
        bars_to_kronos_frame([bar(0), bar(0)])
