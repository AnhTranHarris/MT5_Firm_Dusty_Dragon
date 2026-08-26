from __future__ import annotations

import math
from dataclasses import dataclass

from pydantic import BaseModel, Field

from dusty_dragon.learning.outcomes import OutcomeClass, TradeOutcome


class FirmPerformanceSummary(BaseModel):
    trade_count: int = Field(ge=0)
    wins: int = Field(ge=0)
    losses: int = Field(ge=0)
    flats: int = Field(ge=0)
    win_rate: float = Field(ge=0, le=1)
    total_r: float
    expectancy_r: float
    profit_factor_r: float | None
    max_drawdown_r: float = Field(ge=0)
    forecast_samples: int = Field(ge=0)
    forecast_direction_accuracy: float | None = Field(default=None, ge=0, le=1)
    mean_forecast_error_pct: float | None = None


@dataclass(frozen=True)
class FirmPerformanceAnalyzer:
    """Aggregate immutable outcomes into reusable firm-level diagnostics.

    Vibe-Trading reference: metrics are centralized reusable infrastructure.
    Automaton reference: this compact summary is suitable as a weekend worker
    observation rather than forcing a learning agent to reread every raw trade.
    Kronos reference: forecast accuracy remains a separate metric from P/L.
    """

    def summarize(self, outcomes: list[TradeOutcome]) -> FirmPerformanceSummary:
        if not outcomes:
            return FirmPerformanceSummary(
                trade_count=0,
                wins=0,
                losses=0,
                flats=0,
                win_rate=0.0,
                total_r=0.0,
                expectancy_r=0.0,
                profit_factor_r=None,
                max_drawdown_r=0.0,
                forecast_samples=0,
            )

        ordered = sorted(outcomes, key=lambda item: (item.closed_at, str(item.trade_id)))
        wins = sum(item.outcome_class == OutcomeClass.WIN for item in ordered)
        losses = sum(item.outcome_class == OutcomeClass.LOSS for item in ordered)
        flats = len(ordered) - wins - losses
        total_r = sum(item.realized_r for item in ordered)
        gross_wins = sum(max(item.realized_r, 0.0) for item in ordered)
        gross_losses = abs(sum(min(item.realized_r, 0.0) for item in ordered))
        profit_factor = gross_wins / gross_losses if gross_losses > 1e-12 else None

        forecasted = [
            item
            for item in ordered
            if item.forecast_direction_correct is not None and item.forecast_error_pct is not None
        ]
        accuracy = None
        mean_error = None
        if forecasted:
            accuracy = sum(bool(item.forecast_direction_correct) for item in forecasted) / len(forecasted)
            mean_error = sum(float(item.forecast_error_pct) for item in forecasted) / len(forecasted)

        values = {
            "total_r": total_r,
            "expectancy_r": total_r / len(ordered),
            "max_drawdown_r": self._max_drawdown_r(ordered),
        }
        if not all(math.isfinite(value) for value in values.values()):
            raise ValueError("performance metrics contain non-finite values")

        return FirmPerformanceSummary(
            trade_count=len(ordered),
            wins=wins,
            losses=losses,
            flats=flats,
            win_rate=wins / len(ordered),
            total_r=total_r,
            expectancy_r=total_r / len(ordered),
            profit_factor_r=profit_factor,
            max_drawdown_r=values["max_drawdown_r"],
            forecast_samples=len(forecasted),
            forecast_direction_accuracy=accuracy,
            mean_forecast_error_pct=mean_error,
        )

    @staticmethod
    def _max_drawdown_r(outcomes: list[TradeOutcome]) -> float:
        cumulative = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for outcome in outcomes:
            cumulative += outcome.realized_r
            peak = max(peak, cumulative)
            max_drawdown = max(max_drawdown, peak - cumulative)
        return max_drawdown
