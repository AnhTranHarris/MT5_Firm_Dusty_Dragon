from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, Field

from dusty_dragon.brokers.contracts import MarketBar, Quote
from dusty_dragon.domain.trades import Side, TradeProposal
from dusty_dragon.intelligence.kronos_forecast import KronosForecast


class SignalDecision(StrEnum):
    BUY = "buy"
    SELL = "sell"
    ABSTAIN = "abstain"


class ResearchSignal(BaseModel):
    """Explainable research result; deliberately not an executable order."""

    symbol: str
    timeframe: str
    decision: SignalDecision
    confidence: float = Field(ge=0, le=1)
    forecast_return_pct: float
    trend_return_pct: float
    agreement: bool
    thesis: str
    evidence: dict[str, float | str | bool] = Field(default_factory=dict)


@dataclass(frozen=True)
class GeneralistResearchEngine:
    """Combine Kronos evidence with a simple observed-price trend filter.

    Kronos remains a forecasting input rather than an order authority. The
    engine abstains unless independent observed-price evidence agrees with the
    forecast and both exceed explicit thresholds. This keeps the decision path
    auditable and gives later Automaton-style learning a stable signal record.
    """

    minimum_forecast_return_pct: float = 0.05
    minimum_trend_return_pct: float = 0.02
    trend_lookback_bars: int = 8
    minimum_confidence: float = 0.55

    def evaluate(self, bars: list[MarketBar], forecast: KronosForecast) -> ResearchSignal:
        if len(bars) < self.trend_lookback_bars:
            raise ValueError("insufficient bars for research trend lookback")
        if bars[-1].symbol != forecast.symbol or bars[-1].timeframe != forecast.timeframe:
            raise ValueError("forecast and market bars must describe the same instrument")

        window = bars[-self.trend_lookback_bars :]
        trend_return = ((window[-1].close / window[0].close) - 1.0) * 100.0
        forecast_return = forecast.predicted_return_pct

        forecast_direction = self._direction(forecast_return, self.minimum_forecast_return_pct)
        trend_direction = self._direction(trend_return, self.minimum_trend_return_pct)
        agreement = forecast_direction != SignalDecision.ABSTAIN and forecast_direction == trend_direction

        forecast_strength = min(abs(forecast_return) / max(self.minimum_forecast_return_pct, 1e-9), 2.0)
        trend_strength = min(abs(trend_return) / max(self.minimum_trend_return_pct, 1e-9), 2.0)
        confidence = min(1.0, 0.25 * forecast_strength + 0.25 * trend_strength + (0.5 if agreement else 0.0))
        decision = forecast_direction if agreement and confidence >= self.minimum_confidence else SignalDecision.ABSTAIN

        thesis = (
            f"Kronos forecasts {forecast_return:.4f}% while the observed "
            f"{self.trend_lookback_bars}-bar trend is {trend_return:.4f}%. "
        )
        thesis += "Independent evidence agrees." if agreement else "Evidence does not agree; abstain."

        return ResearchSignal(
            symbol=forecast.symbol,
            timeframe=forecast.timeframe,
            decision=decision,
            confidence=confidence,
            forecast_return_pct=forecast_return,
            trend_return_pct=trend_return,
            agreement=agreement,
            thesis=thesis,
            evidence={
                "kronos_predicted_close": forecast.predicted_close,
                "kronos_predicted_high": forecast.predicted_high,
                "kronos_predicted_low": forecast.predicted_low,
                "kronos_horizon_bars": forecast.horizon_bars,
                "kronos_return_pct": forecast_return,
                "trend_return_pct": trend_return,
                "trend_lookback_bars": self.trend_lookback_bars,
                "evidence_agreement": agreement,
            },
        )

    def proposal_from_signal(
        self,
        signal: ResearchSignal,
        quote: Quote,
        *,
        risk_pct: float,
        stop_distance_pct: float = 0.20,
        reward_to_risk: float = 2.0,
        strategy_version: str = "generalist-v0",
    ) -> TradeProposal | None:
        if signal.decision == SignalDecision.ABSTAIN:
            return None
        if quote.symbol != signal.symbol:
            raise ValueError("quote and signal symbols must match")
        if risk_pct <= 0 or stop_distance_pct <= 0 or reward_to_risk <= 0:
            raise ValueError("risk, stop distance, and reward/risk must be positive")

        side = Side.BUY if signal.decision == SignalDecision.BUY else Side.SELL
        entry = quote.ask if side == Side.BUY else quote.bid
        stop_distance = entry * (stop_distance_pct / 100.0)
        reward_distance = stop_distance * reward_to_risk
        if side == Side.BUY:
            stop_loss = entry - stop_distance
            take_profit = entry + reward_distance
        else:
            stop_loss = entry + stop_distance
            take_profit = entry - reward_distance

        return TradeProposal(
            strategy_version=strategy_version,
            symbol=signal.symbol,
            side=side,
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_pct=risk_pct,
            confidence=signal.confidence,
            timeframe=signal.timeframe,
            thesis=signal.thesis,
            evidence=signal.evidence,
        )

    @staticmethod
    def _direction(value: float, threshold: float) -> SignalDecision:
        if value >= threshold:
            return SignalDecision.BUY
        if value <= -threshold:
            return SignalDecision.SELL
        return SignalDecision.ABSTAIN
