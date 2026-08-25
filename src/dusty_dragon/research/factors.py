from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from pydantic import BaseModel, Field

from dusty_dragon.brokers.contracts import MarketBar


class FactorSnapshot(BaseModel):
    """Portable market-factor evidence derived from one symbol/timeframe series."""

    symbol: str
    timeframe: str
    trend_return_pct: float
    momentum_return_pct: float
    realized_volatility_pct: float = Field(ge=0)
    mean_reversion_zscore: float
    average_spread_points: float = Field(ge=0)
    regime: str


@dataclass(frozen=True)
class FactorEngine:
    """Produce transparent factor evidence for research and challenger design.

    Vibe-Trading roadmap: factors are reusable research inputs, not execution
    commands. Kronos remains a separate forecasting signal so forecast value can
    be measured independently. Automaton-style workers consume this snapshot as
    evidence when proposing bounded challenger mutations.
    """

    trend_lookback_bars: int = 16
    momentum_lookback_bars: int = 4
    zscore_lookback_bars: int = 20
    trend_threshold_pct: float = 0.10
    high_volatility_threshold_pct: float = 0.05

    def __post_init__(self) -> None:
        if min(self.trend_lookback_bars, self.momentum_lookback_bars, self.zscore_lookback_bars) < 2:
            raise ValueError("factor lookbacks must be at least 2 bars")
        if self.trend_threshold_pct <= 0 or self.high_volatility_threshold_pct <= 0:
            raise ValueError("regime thresholds must be positive")

    def evaluate(self, bars: list[MarketBar]) -> FactorSnapshot:
        required = max(
            self.trend_lookback_bars,
            self.momentum_lookback_bars,
            self.zscore_lookback_bars,
        )
        if len(bars) < required:
            raise ValueError(f"factor engine requires at least {required} bars")
        self._validate_series(bars)

        trend = self._return_pct(bars[-self.trend_lookback_bars].close, bars[-1].close)
        momentum = self._return_pct(
            bars[-self.momentum_lookback_bars].close,
            bars[-1].close,
        )
        closes = [bar.close for bar in bars[-self.zscore_lookback_bars :]]
        mean_close = sum(closes) / len(closes)
        variance = sum((close - mean_close) ** 2 for close in closes) / len(closes)
        std = sqrt(variance)
        zscore = (closes[-1] - mean_close) / std if std > 0 else 0.0

        returns = [
            self._return_pct(bars[index - 1].close, bars[index].close)
            for index in range(len(bars) - self.zscore_lookback_bars + 1, len(bars))
        ]
        if returns:
            mean_return = sum(returns) / len(returns)
            return_variance = sum((value - mean_return) ** 2 for value in returns) / len(returns)
            realized_volatility = sqrt(return_variance)
        else:
            realized_volatility = 0.0

        spread = sum(bar.spread_points for bar in bars[-self.zscore_lookback_bars :]) / self.zscore_lookback_bars
        regime = self._regime(trend, realized_volatility)
        last = bars[-1]
        return FactorSnapshot(
            symbol=last.symbol,
            timeframe=last.timeframe,
            trend_return_pct=trend,
            momentum_return_pct=momentum,
            realized_volatility_pct=realized_volatility,
            mean_reversion_zscore=zscore,
            average_spread_points=spread,
            regime=regime,
        )

    def _regime(self, trend_return_pct: float, volatility_pct: float) -> str:
        trending = abs(trend_return_pct) >= self.trend_threshold_pct
        high_vol = volatility_pct >= self.high_volatility_threshold_pct
        if trending and high_vol:
            return "trend_high_vol"
        if trending:
            return "trend_low_vol"
        if high_vol:
            return "range_high_vol"
        return "range_low_vol"

    @staticmethod
    def _return_pct(start: float, end: float) -> float:
        return ((end / start) - 1.0) * 100.0

    @staticmethod
    def _validate_series(bars: list[MarketBar]) -> None:
        first = bars[0]
        previous = first.opened_at
        for index, bar in enumerate(bars):
            if bar.symbol != first.symbol or bar.timeframe != first.timeframe:
                raise ValueError("factor bars must be one symbol and timeframe")
            if index and bar.opened_at <= previous:
                raise ValueError("factor bars must be strictly chronological")
            previous = bar.opened_at
