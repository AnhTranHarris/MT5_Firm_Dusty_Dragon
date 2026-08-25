from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import sqrt

from pydantic import BaseModel, Field

from dusty_dragon.backtest.weekend_protocol import (
    WeekendExperimentResult,
    WeekendProtocolResult,
)
from dusty_dragon.brokers.contracts import MarketBar


class RegimeLabel(str):
    TREND_LOW_VOL = "trend_low_vol"
    TREND_HIGH_VOL = "trend_high_vol"
    RANGE_LOW_VOL = "range_low_vol"
    RANGE_HIGH_VOL = "range_high_vol"


class ExperimentEvaluation(BaseModel):
    experiment_type: str
    tested_symbol: str
    run_number: int = Field(ge=1)
    regime: str
    raw_mean_signed_return_pct: float | None = None
    estimated_cost_pct_per_trade: float = Field(ge=0)
    cost_adjusted_mean_return_pct: float | None = None
    directional_accuracy: float | None = Field(default=None, ge=0, le=1)
    trade_signals: int = Field(ge=0)


class CampaignEvaluation(BaseModel):
    experiment_count: int = Field(ge=0)
    profitable_after_cost_count: int = Field(ge=0)
    profitable_after_cost_rate: float | None = Field(default=None, ge=0, le=1)
    mean_cost_adjusted_return_pct: float | None = None
    worst_cost_adjusted_return_pct: float | None = None
    regime_mean_returns: dict[str, float] = Field(default_factory=dict)
    symbol_mean_returns: dict[str, float] = Field(default_factory=dict)
    experiments: list[ExperimentEvaluation] = Field(default_factory=list)


@dataclass(frozen=True)
class CostRegimeCampaignEvaluator:
    """Evaluate weekend experiments after explicit friction and regime tagging.

    Vibe-Trading roadmap: research performance must be evaluated after explicit
    transaction-cost assumptions and segmented by market conditions.

    Kronos roadmap: forecast usefulness can later be calibrated by regime rather
    than reduced to one global accuracy number.

    Automaton roadmap: weekend workers consume this compact evidence to create
    challenger hypotheses; they do not infer hidden assumptions from raw P/L.

    Costs are deliberately estimates, not claims about actual broker fills. The
    caller supplies point size and optional slippage/commission assumptions for
    each symbol. Live/paper execution remains the authoritative source of actual
    observed friction.
    """

    default_point_size: float = 0.00001
    slippage_points: float = 0.0
    commission_pct_per_trade: float = 0.0
    trend_threshold_pct: float = 0.10
    high_volatility_threshold_pct: float = 0.05

    def __post_init__(self) -> None:
        if self.default_point_size <= 0:
            raise ValueError("default_point_size must be positive")
        if self.slippage_points < 0:
            raise ValueError("slippage_points cannot be negative")
        if self.commission_pct_per_trade < 0:
            raise ValueError("commission_pct_per_trade cannot be negative")
        if self.trend_threshold_pct <= 0 or self.high_volatility_threshold_pct <= 0:
            raise ValueError("regime thresholds must be positive")

    def evaluate(
        self,
        protocol: WeekendProtocolResult,
        *,
        bars_by_symbol: dict[str, list[MarketBar]],
        point_size_by_symbol: dict[str, float] | None = None,
    ) -> CampaignEvaluation:
        point_sizes = point_size_by_symbol or {}
        evaluations: list[ExperimentEvaluation] = []
        for experiment in [*protocol.cross_symbol_results, *protocol.prior_week_results]:
            bars = self._window_bars(experiment, bars_by_symbol)
            if not bars:
                continue
            evaluations.append(
                self._evaluate_experiment(
                    experiment,
                    bars,
                    point_size=point_sizes.get(
                        experiment.tested_symbol, self.default_point_size
                    ),
                )
            )

        adjusted = [
            item.cost_adjusted_mean_return_pct
            for item in evaluations
            if item.cost_adjusted_mean_return_pct is not None
        ]
        profitable = sum(value > 0 for value in adjusted)
        return CampaignEvaluation(
            experiment_count=len(evaluations),
            profitable_after_cost_count=profitable,
            profitable_after_cost_rate=(profitable / len(adjusted) if adjusted else None),
            mean_cost_adjusted_return_pct=(sum(adjusted) / len(adjusted) if adjusted else None),
            worst_cost_adjusted_return_pct=(min(adjusted) if adjusted else None),
            regime_mean_returns=self._group_means(evaluations, key="regime"),
            symbol_mean_returns=self._group_means(evaluations, key="tested_symbol"),
            experiments=evaluations,
        )

    def _evaluate_experiment(
        self,
        experiment: WeekendExperimentResult,
        bars: list[MarketBar],
        *,
        point_size: float,
    ) -> ExperimentEvaluation:
        if point_size <= 0:
            raise ValueError("point size must be positive")
        mean_price = sum(bar.close for bar in bars) / len(bars)
        mean_spread_points = sum(bar.spread_points for bar in bars) / len(bars)
        friction_price = (mean_spread_points + self.slippage_points) * point_size
        cost_pct = (friction_price / mean_price) * 100.0 + self.commission_pct_per_trade
        raw = experiment.walk_forward.mean_signed_return_pct
        adjusted = raw - cost_pct if raw is not None else None
        return ExperimentEvaluation(
            experiment_type=experiment.experiment_type,
            tested_symbol=experiment.tested_symbol,
            run_number=experiment.run_number,
            regime=self._classify_regime(bars),
            raw_mean_signed_return_pct=raw,
            estimated_cost_pct_per_trade=cost_pct,
            cost_adjusted_mean_return_pct=adjusted,
            directional_accuracy=experiment.walk_forward.directional_accuracy,
            trade_signals=experiment.walk_forward.trade_signals,
        )

    def _classify_regime(self, bars: list[MarketBar]) -> str:
        start = bars[0].close
        end = bars[-1].close
        trend_pct = abs((end / start - 1.0) * 100.0)
        returns = [
            (bars[index].close / bars[index - 1].close - 1.0) * 100.0
            for index in range(1, len(bars))
        ]
        if returns:
            mean = sum(returns) / len(returns)
            variance = sum((value - mean) ** 2 for value in returns) / len(returns)
            realized_volatility = sqrt(variance)
        else:
            realized_volatility = 0.0
        trending = trend_pct >= self.trend_threshold_pct
        high_vol = realized_volatility >= self.high_volatility_threshold_pct
        if trending and high_vol:
            return RegimeLabel.TREND_HIGH_VOL
        if trending:
            return RegimeLabel.TREND_LOW_VOL
        if high_vol:
            return RegimeLabel.RANGE_HIGH_VOL
        return RegimeLabel.RANGE_LOW_VOL

    @staticmethod
    def _window_bars(
        experiment: WeekendExperimentResult,
        bars_by_symbol: dict[str, list[MarketBar]],
    ) -> list[MarketBar]:
        return [
            bar
            for bar in bars_by_symbol.get(experiment.tested_symbol, [])
            if experiment.reference_started_at <= bar.opened_at <= experiment.reference_ended_at
        ]

    @staticmethod
    def _group_means(
        evaluations: list[ExperimentEvaluation], *, key: str
    ) -> dict[str, float]:
        groups: dict[str, list[float]] = defaultdict(list)
        for item in evaluations:
            value = item.cost_adjusted_mean_return_pct
            if value is None:
                continue
            groups[str(getattr(item, key))].append(value)
        return {
            group: sum(values) / len(values)
            for group, values in sorted(groups.items())
            if values
        }
