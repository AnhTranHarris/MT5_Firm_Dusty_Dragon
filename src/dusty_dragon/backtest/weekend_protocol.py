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
    run_number: int = Field(default=1, ge=1)
    random_seed: int
    walk_forward: WalkForwardResult


class WeekendProtocolResult(BaseModel):
    random_seed: int
    runs_per_symbol: int = Field(ge=1)
    cross_symbol_results: list[WeekendExperimentResult] = Field(default_factory=list)
    prior_week_results: list[WeekendExperimentResult] = Field(default_factory=list)


@dataclass(frozen=True)
class WeekendBacktestProtocol:
    """Run reproducible multi-run counterfactual weekend experiments.

    Each symbol is evaluated repeatedly across varied historical windows. This
    deliberately builds a distribution of observations instead of promoting a
    strategy from one favorable slice.

    Cross-symbol experiments use symbols the firm did not trade. Prior-week
    experiments replay the traded symbol at randomly selected offsets from one
    to eight weeks before the reference window. Every random choice is seeded
    and recorded so Sunday validation can reproduce Saturday research.
    """

    evaluator: SignalWalkForwardEvaluator
    prior_week_min: int = 1
    prior_week_max: int = 8
    default_runs_per_symbol: int = 12
    minimum_runs_per_symbol: int = 10
    maximum_runs_per_symbol: int = 20

    def __post_init__(self) -> None:
        if self.prior_week_min < 1:
            raise ValueError("prior_week_min must be at least 1")
        if self.prior_week_max > 8:
            raise ValueError("prior_week_max cannot exceed 8")
        if self.prior_week_min > self.prior_week_max:
            raise ValueError("prior week range is invalid")
        if not self.minimum_runs_per_symbol <= self.default_runs_per_symbol <= self.maximum_runs_per_symbol:
            raise ValueError("default runs must fall inside configured campaign bounds")

    def run(
        self,
        *,
        traded_symbol: str,
        reference_bars: list[MarketBar],
        unused_symbol_bars: dict[str, list[MarketBar]],
        prior_history_bars: list[MarketBar],
        random_seed: int,
        unused_symbol_sample_size: int | None = None,
        runs_per_symbol: int | None = None,
    ) -> WeekendProtocolResult:
        self._validate_reference(traded_symbol, reference_bars)
        runs = runs_per_symbol or self.default_runs_per_symbol
        if not self.minimum_runs_per_symbol <= runs <= self.maximum_runs_per_symbol:
            raise ValueError(
                f"runs_per_symbol must be between {self.minimum_runs_per_symbol} "
                f"and {self.maximum_runs_per_symbol}"
            )

        rng = random.Random(random_seed)
        reference_start = reference_bars[0].opened_at
        reference_end = reference_bars[-1].opened_at
        reference_duration = reference_end - reference_start

        candidates = sorted(symbol for symbol in unused_symbol_bars if symbol != traded_symbol)
        if unused_symbol_sample_size is not None:
            if unused_symbol_sample_size <= 0:
                raise ValueError("unused_symbol_sample_size must be positive")
            sample_count = min(unused_symbol_sample_size, len(candidates))
            candidates = sorted(rng.sample(candidates, sample_count))

        cross_symbol_results: list[WeekendExperimentResult] = []
        for symbol in candidates:
            bars = unused_symbol_bars[symbol]
            available_starts = self._candidate_window_starts(
                bars,
                duration=reference_duration,
                fallback_start=reference_start,
            )
            for run_number in range(1, runs + 1):
                start = rng.choice(available_starts)
                end = start + reference_duration
                window = self._same_window(bars, start, end)
                if not window:
                    continue
                result = self.evaluator.evaluate(window)
                cross_symbol_results.append(
                    WeekendExperimentResult(
                        experiment_type=WeekendExperimentType.CROSS_SYMBOL,
                        source_symbol=traded_symbol,
                        tested_symbol=symbol,
                        reference_started_at=start,
                        reference_ended_at=end,
                        run_number=run_number,
                        random_seed=random_seed,
                        walk_forward=result,
                    )
                )

        prior_week_results: list[WeekendExperimentResult] = []
        for run_number in range(1, runs + 1):
            weeks_back = rng.randint(self.prior_week_min, self.prior_week_max)
            replay_start = reference_start - timedelta(weeks=weeks_back)
            replay_end = reference_end - timedelta(weeks=weeks_back)
            replay_window = self._same_window(prior_history_bars, replay_start, replay_end)
            if not replay_window:
                continue
            result = self.evaluator.evaluate(replay_window)
            prior_week_results.append(
                WeekendExperimentResult(
                    experiment_type=WeekendExperimentType.PRIOR_WEEK_REPLAY,
                    source_symbol=traded_symbol,
                    tested_symbol=traded_symbol,
                    reference_started_at=replay_start,
                    reference_ended_at=replay_end,
                    replay_weeks_back=weeks_back,
                    run_number=run_number,
                    random_seed=random_seed,
                    walk_forward=result,
                )
            )

        return WeekendProtocolResult(
            random_seed=random_seed,
            runs_per_symbol=runs,
            cross_symbol_results=cross_symbol_results,
            prior_week_results=prior_week_results,
        )

    @staticmethod
    def _candidate_window_starts(
        bars: list[MarketBar], *, duration: timedelta, fallback_start: datetime
    ) -> list[datetime]:
        if not bars:
            return [fallback_start]
        latest_start = bars[-1].opened_at - duration
        starts = [bar.opened_at for bar in bars if bar.opened_at <= latest_start]
        return starts or [fallback_start]

    @staticmethod
    def _same_window(bars: list[MarketBar], start: datetime, end: datetime) -> list[MarketBar]:
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
