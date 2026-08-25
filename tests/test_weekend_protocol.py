from datetime import UTC, datetime, timedelta

import pytest

from dusty_dragon.backtest.walk_forward import SignalWalkForwardEvaluator
from dusty_dragon.backtest.weekend_protocol import WeekendBacktestProtocol
from dusty_dragon.brokers.contracts import MarketBar
from dusty_dragon.intelligence.kronos_forecast import KronosForecast
from dusty_dragon.intelligence.research_signal import GeneralistResearchEngine


class DeterministicForecast:
    def forecast(self, bars: list[MarketBar], horizon_bars: int) -> KronosForecast:
        start = bars[-1].close
        predicted = start * 1.001
        return KronosForecast(
            symbol=bars[-1].symbol,
            timeframe=bars[-1].timeframe,
            horizon_bars=horizon_bars,
            starting_close=start,
            predicted_close=predicted,
            predicted_return_pct=0.1,
            predicted_high=predicted + 0.001,
            predicted_low=start - 0.001,
            forecast_rows=horizon_bars,
            volume_source="tick_volume",
        )


def bars(symbol: str, start: datetime, count: int, rising: bool = True):
    result = []
    for index in range(count):
        direction = 1 if rising else -1
        close = 1.1 + direction * index * 0.0002
        result.append(
            MarketBar(
                symbol=symbol,
                timeframe="M15",
                opened_at=start + timedelta(minutes=15 * index),
                open=close - 0.0001,
                high=close + 0.0002,
                low=close - 0.0002,
                close=close,
                tick_volume=100 + index,
                spread_points=8.0,
                real_volume=0.0,
            )
        )
    return result


def protocol():
    evaluator = SignalWalkForwardEvaluator(
        research_engine=GeneralistResearchEngine(),
        forecast_provider=DeterministicForecast(),
        horizon_bars=4,
        minimum_history_bars=8,
    )
    return WeekendBacktestProtocol(evaluator)


def test_multi_run_campaign_builds_repeated_symbol_evidence():
    reference_start = datetime(2026, 8, 17, tzinfo=UTC)
    reference = bars("EURUSD", reference_start, 16)
    long_unused = {
        "GBPUSD": bars("GBPUSD", reference_start - timedelta(weeks=8), 8 * 7 * 24 * 4),
        "USDJPY": bars("USDJPY", reference_start - timedelta(weeks=8), 8 * 7 * 24 * 4),
    }
    historical = bars("EURUSD", reference_start - timedelta(weeks=8), 8 * 7 * 24 * 4)

    result = protocol().run(
        traded_symbol="EURUSD",
        reference_bars=reference,
        unused_symbol_bars=long_unused,
        prior_history_bars=historical,
        random_seed=7,
        runs_per_symbol=10,
    )

    assert result.runs_per_symbol == 10
    assert len(result.cross_symbol_results) == 20
    assert len(result.prior_week_results) == 10
    assert {item.run_number for item in result.prior_week_results} == set(range(1, 11))


def test_campaign_uses_varied_historical_windows_for_unused_symbol():
    reference_start = datetime(2026, 8, 17, tzinfo=UTC)
    reference = bars("EURUSD", reference_start, 16)
    history_start = reference_start - timedelta(weeks=8)
    unused = {"GBPUSD": bars("GBPUSD", history_start, 8 * 7 * 24 * 4)}
    historical = bars("EURUSD", history_start, 8 * 7 * 24 * 4)

    result = protocol().run(
        traded_symbol="EURUSD",
        reference_bars=reference,
        unused_symbol_bars=unused,
        prior_history_bars=historical,
        random_seed=13,
        runs_per_symbol=12,
    )

    starts = {item.reference_started_at for item in result.cross_symbol_results}
    assert len(starts) > 1


def test_prior_week_replays_are_seeded_and_bounded():
    reference_start = datetime(2026, 8, 17, tzinfo=UTC)
    reference = bars("EURUSD", reference_start, 16)
    history_start = reference_start - timedelta(weeks=8)
    historical = bars("EURUSD", history_start, 8 * 7 * 24 * 4)

    first = protocol().run(
        traded_symbol="EURUSD",
        reference_bars=reference,
        unused_symbol_bars={},
        prior_history_bars=historical,
        random_seed=19,
        runs_per_symbol=10,
    )
    second = protocol().run(
        traded_symbol="EURUSD",
        reference_bars=reference,
        unused_symbol_bars={},
        prior_history_bars=historical,
        random_seed=19,
        runs_per_symbol=10,
    )

    first_offsets = [item.replay_weeks_back for item in first.prior_week_results]
    second_offsets = [item.replay_weeks_back for item in second.prior_week_results]
    assert first_offsets == second_offsets
    assert all(offset is not None and 1 <= offset <= 8 for offset in first_offsets)
    assert len(set(first_offsets)) > 1


def test_run_count_is_restricted_to_ten_through_twenty():
    reference_start = datetime(2026, 8, 17, tzinfo=UTC)
    reference = bars("EURUSD", reference_start, 16)
    historical = bars("EURUSD", reference_start - timedelta(weeks=8), 8 * 7 * 24 * 4)

    with pytest.raises(ValueError, match="runs_per_symbol"):
        protocol().run(
            traded_symbol="EURUSD",
            reference_bars=reference,
            unused_symbol_bars={},
            prior_history_bars=historical,
            random_seed=1,
            runs_per_symbol=9,
        )
    with pytest.raises(ValueError, match="runs_per_symbol"):
        protocol().run(
            traded_symbol="EURUSD",
            reference_bars=reference,
            unused_symbol_bars={},
            prior_history_bars=historical,
            random_seed=1,
            runs_per_symbol=21,
        )
