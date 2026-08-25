from datetime import UTC, datetime, timedelta

from dusty_dragon.backtest.weekend_protocol import WeekendBacktestProtocol
from dusty_dragon.backtest.walk_forward import SignalWalkForwardEvaluator
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


def test_cross_symbol_uses_same_reference_window():
    start = datetime(2026, 8, 17, tzinfo=UTC)
    reference = bars("EURUSD", start, 16)
    unused = {
        "GBPUSD": bars("GBPUSD", start, 16),
        "USDJPY": bars("USDJPY", start, 16),
    }
    historical = bars("EURUSD", start - timedelta(weeks=8), 16 * 8)

    result = protocol().run(
        traded_symbol="EURUSD",
        reference_bars=reference,
        unused_symbol_bars=unused,
        prior_history_bars=historical,
        random_seed=7,
    )

    assert {item.tested_symbol for item in result.cross_symbol_results} == {
        "GBPUSD",
        "USDJPY",
    }
    assert all(
        item.reference_started_at == reference[0].opened_at
        for item in result.cross_symbol_results
    )


def test_prior_week_replay_is_seeded_between_one_and_eight_weeks():
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
    )
    second = protocol().run(
        traded_symbol="EURUSD",
        reference_bars=reference,
        unused_symbol_bars={},
        prior_history_bars=historical,
        random_seed=19,
    )

    assert first.prior_week_results
    weeks_back = first.prior_week_results[0].replay_weeks_back
    assert weeks_back is not None and 1 <= weeks_back <= 8
    assert second.prior_week_results[0].replay_weeks_back == weeks_back


def test_sampling_unused_symbols_is_reproducible():
    start = datetime(2026, 8, 17, tzinfo=UTC)
    reference = bars("EURUSD", start, 16)
    unused = {symbol: bars(symbol, start, 16) for symbol in ["GBPUSD", "USDJPY", "AUDUSD"]}
    historical = bars("EURUSD", start - timedelta(weeks=8), 8 * 7 * 24 * 4)

    result = protocol().run(
        traded_symbol="EURUSD",
        reference_bars=reference,
        unused_symbol_bars=unused,
        prior_history_bars=historical,
        random_seed=3,
        unused_symbol_sample_size=2,
    )

    assert len(result.cross_symbol_results) == 2
