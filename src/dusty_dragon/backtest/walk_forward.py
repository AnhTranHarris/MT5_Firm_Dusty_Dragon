from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, Field

from dusty_dragon.brokers.contracts import MarketBar
from dusty_dragon.intelligence.kronos_forecast import KronosForecast
from dusty_dragon.intelligence.research_signal import (
    GeneralistResearchEngine,
    SignalDecision,
)


class HistoricalForecastProvider(Protocol):
    def forecast(self, bars: list[MarketBar], horizon_bars: int) -> KronosForecast: ...


class WalkForwardResult(BaseModel):
    windows: int = Field(ge=0)
    trade_signals: int = Field(ge=0)
    abstentions: int = Field(ge=0)
    directional_wins: int = Field(ge=0)
    directional_losses: int = Field(ge=0)
    directional_accuracy: float | None = Field(default=None, ge=0, le=1)
    mean_signed_return_pct: float | None = None


@dataclass(frozen=True)
class SignalWalkForwardEvaluator:
    """Evaluate research decisions sequentially without future-data leakage.

    Vibe-Trading roadmap: validation is reusable infrastructure separate from
    the live strategy path.

    Kronos roadmap: the forecast provider sees historical bars only. Production
    can inject KronosForecastService; CI and challenger screening can inject a
    deterministic provider without loading model weights.

    Automaton roadmap: weekend workers may consume this result as evidence, but
    they cannot promote a strategy merely because they generated it.
    """

    research_engine: GeneralistResearchEngine
    forecast_provider: HistoricalForecastProvider
    horizon_bars: int = 4
    minimum_history_bars: int = 32

    def __post_init__(self) -> None:
        if self.horizon_bars <= 0:
            raise ValueError("horizon_bars must be positive")
        if self.minimum_history_bars < self.research_engine.trend_lookback_bars:
            raise ValueError("minimum history must cover research lookback")

    def evaluate(self, bars: list[MarketBar]) -> WalkForwardResult:
        minimum_total = self.minimum_history_bars + self.horizon_bars
        if len(bars) < minimum_total:
            raise ValueError(
                f"walk-forward requires at least {minimum_total} bars; received {len(bars)}"
            )
        self._validate_series(bars)

        signals = 0
        abstentions = 0
        wins = 0
        losses = 0
        signed_returns: list[float] = []
        windows = 0

        last_origin = len(bars) - self.horizon_bars - 1
        for origin in range(self.minimum_history_bars - 1, last_origin + 1):
            history = bars[: origin + 1]
            forecast = self.forecast_provider.forecast(history, self.horizon_bars)
            signal = self.research_engine.evaluate(history, forecast)
            windows += 1

            if signal.decision == SignalDecision.ABSTAIN:
                abstentions += 1
                continue

            signals += 1
            current_close = history[-1].close
            realized_close = bars[origin + self.horizon_bars].close
            market_return_pct = ((realized_close / current_close) - 1.0) * 100.0
            sign = 1.0 if signal.decision == SignalDecision.BUY else -1.0
            signed_return = market_return_pct * sign
            signed_returns.append(signed_return)
            if signed_return > 0:
                wins += 1
            else:
                losses += 1

        accuracy = wins / signals if signals else None
        mean_signed = sum(signed_returns) / len(signed_returns) if signed_returns else None
        return WalkForwardResult(
            windows=windows,
            trade_signals=signals,
            abstentions=abstentions,
            directional_wins=wins,
            directional_losses=losses,
            directional_accuracy=accuracy,
            mean_signed_return_pct=mean_signed,
        )

    @staticmethod
    def _validate_series(bars: list[MarketBar]) -> None:
        first = bars[0]
        previous_time = first.opened_at
        for bar in bars:
            if bar.symbol != first.symbol or bar.timeframe != first.timeframe:
                raise ValueError("walk-forward bars must be one symbol and timeframe")
            if bar is not first and bar.opened_at <= previous_time:
                raise ValueError("walk-forward bars must be strictly chronological")
            previous_time = bar.opened_at
