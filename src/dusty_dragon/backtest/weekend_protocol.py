from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta

from pydantic import BaseModel, Field

from dusty_dragon.backtest.walk_forward import SignalWalkForwardEvaluator, WalkForwardResult
from dusty_dragon.brokers.contracts import MarketBar


class WeekendExperimentType(str):
    CROSS_SYMBOL = "cross_symbol"
    PRIOR_WEEK_REPLAY = "prior_week_replay"


class WeekendExperimentResult(BaseModel):
    experiment_type: str
    source_symbol: str
    tested_symbol: str
    reference_started_at: datetime
    reference_ended_at: datetime
    replay_weeks_back: int | None = Field(default=None, ge=1, le=8)
    random_seed: int
    walk_forward: WalkForwardResult


class WeekendProtocolResult(BaseModel):
    random_seed: int
    cross_symbol_results: list[WeekendExperimentResult] = Field(default_factory=list)
    prior_week_results: list[WeekendExperimentResult] = Field(default_factory=list)


@dataclass(frozen=True)
class WeekendBacktestProtocol:
    """Run reproducible counterfactual weekend experiments.

    Cross-symbol experiments hold the historical time window constant and test
    symbols that were not traded. Prior-week experiments hold the traded symbol
    constant and replay a randomly selected offset from one to eight weeks ago.

    Randomness is seeded and recorded so research is reproducible. The caller
    supplies historical bars; this layer never reaches into future/live data.
    """

    evaluator: SignalWalkForwardEvaluator
    prior_week_min: int = 1
    prior_week_max: int = 8

    def __post_init__(self) -> None:
        if self.prior_week_min < 1:
            raise ValueError("prior_week_min must be at least 1")
        if self.prior_week_max > 8:
            raise ValueError("prior_week_max cannot exceed 8")
        if self.prior_week_min > self.prior_week_max:
            raise ValueError("prior week range is invalid")

    def run(
        self,
        *,
        traded_symbol: str,
        reference_bars: list[MarketBar],
        unused_symbol_bars: dict[str, list[MarketBar]],
        prior_history_bars: list[MarketBar],
        random_seed: int,
        unused_symbol_sample_size: int | None = None,
    ) -> WeekendProtocolResult:
        self._validate_reference(traded_symbol, reference_bars)
        rng = random.Random(random_seed)
        reference_start = reference_bars[0].opened_at
        reference_end = reference_bars[-1].opened_at

        candidates = sorted(
            symbol for symbol in unused_symbol_bars if symbol != traded_symbol
        )
        if unused_symbol_sample_size is not None:
            if unused_symbol_sample_size <= 0:
                raise ValueError("unused_symbol_sample_size must be positive")
            sample_count = min(unused_symbol_sample_size, len(candidates))
            candidates = sorted(rng.sample(candidates, sample_count))

        cross_symbol_results: list[WeekendExperimentResult] = []
        for symbol in candidates:
            window = self._same_window(
                unused_symbol_bars[symbol], reference_start, reference_end
            )
            if not window:
                continue
            result = self.evaluator.evaluate(window)
            cross_symbol_results.append(
                WeekendExperimentResult(
                    experiment_type=WeekendExperimentType.CROSS_SYMBOL,
                    source_symbol=traded_symbol,
                    tested_symbol=symbol,
                    reference_started_at=reference_start,
                    reference_ended_at=reference_end,
                    random_seed=random_seed,
                    walk_forward=result,
                )
            )

        weeks_back = rng.randint(self.prior_week_min, self.prior_week_max)
        replay_start = reference_start - timedelta(weeks=weeks_back)
        replay_end = reference_end - timedelta(weeks=weeks_back)
        replay_window = self._same_window(prior_history_bars, replay_start, replay_end)
        prior_week_results: list[WeekendExperimentResult] = []
        if replay_window:
            result = self.evaluator.evaluate(replay_window)
            prior_week_results.append(
                WeekendExperimentResult(
                    experiment_type=WeekendExperimentType.PRIOR_WEEK_REPLAY,
                    source_symbol=traded_symbol,
                    tested_symbol=traded_symbol,
                    reference_started_at=replay_start,
                    reference_ended_at=replay_end,
                    replay_weeks_back=weeks_back,
                    random_seed=random_seed,
                    walk_forward=result,
                )
            )

        return WeekendProtocolResult(
            random_seed=random_seed,
            cross_symbol_results=cross_symbol_results,
            prior_week_results=prior_week_results,
        )

    @staticmethod
    def _same_window(
        bars: list[MarketBar], start: datetime, end: datetime
    ) -> list[MarketBar]:
        return [bar for bar in bars if start <= bar.opened_at <= end]

    @staticmethod
    def _validate_reference(traded_symbol: str, bars: list[MarketBar]) -> None:
        if not bars:
            raise ValueError("reference_bars cannot be empty")
        if any(bar.symbol != traded_symbol for bar in bars):
            raise ValueError("reference bars must belong to traded_symbol")
        previous = None
        for bar in bars:
            if previous is not None and bar.opened_at <= previous:
                raise ValueError("reference bars must be strictly chronological")
            previous = bar.opened_at
