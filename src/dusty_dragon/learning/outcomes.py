from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from dusty_dragon.domain.trades import Side
from dusty_dragon.reporting.trade_report import TradeReport


class OutcomeClass(StrEnum):
    WIN = "win"
    LOSS = "loss"
    FLAT = "flat"


class TradeOutcome(BaseModel):
    """Immutable realized outcome linked to one audited trade decision.

    Roadmap synthesis:
    - Kronos: preserve forecast-vs-realized error for calibration.
    - Vibe-Trading: expose reusable trade statistics such as return and R-multiple.
    - Automaton: create durable feedback that future learning workers can consume.
    """

    outcome_version: str = "trade-outcome/v1"
    trade_id: UUID
    closed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    symbol: str
    side: Side
    strategy_version: str
    entry_price: float = Field(gt=0)
    exit_price: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    gross_return_pct: float
    realized_r: float
    outcome_class: OutcomeClass
    forecast_return_pct: float | None = None
    forecast_error_pct: float | None = None
    forecast_direction_correct: bool | None = None
    maximum_favorable_excursion_r: float | None = None
    maximum_adverse_excursion_r: float | None = None

    @classmethod
    def from_report(
        cls,
        report: TradeReport,
        *,
        exit_price: float,
        closed_at: datetime | None = None,
        maximum_favorable_excursion_r: float | None = None,
        maximum_adverse_excursion_r: float | None = None,
    ) -> TradeOutcome:
        if report.execution is None or not report.execution.accepted:
            raise ValueError("trade outcome requires an accepted execution")
        if report.execution.executed_price is None:
            raise ValueError("trade outcome requires an executed entry price")
        if exit_price <= 0:
            raise ValueError("exit_price must be positive")

        entry = report.execution.executed_price
        side_sign = 1.0 if report.proposal.side == Side.BUY else -1.0
        signed_move = (exit_price - entry) * side_sign
        risk_distance = abs(entry - report.proposal.stop_loss)
        if risk_distance <= 0:
            raise ValueError("executed entry and stop loss must define positive risk")

        realized_r = signed_move / risk_distance
        gross_return_pct = (signed_move / entry) * 100.0
        if realized_r > 1e-12:
            outcome_class = OutcomeClass.WIN
        elif realized_r < -1e-12:
            outcome_class = OutcomeClass.LOSS
        else:
            outcome_class = OutcomeClass.FLAT

        raw_forecast = report.observations.get("forecast_return_pct")
        forecast_return_pct = float(raw_forecast) if raw_forecast is not None else None
        forecast_error_pct = None
        direction_correct = None
        if forecast_return_pct is not None:
            realized_market_return_pct = ((exit_price / entry) - 1.0) * 100.0
            forecast_error_pct = realized_market_return_pct - forecast_return_pct
            if abs(forecast_return_pct) > 1e-12 and abs(realized_market_return_pct) > 1e-12:
                direction_correct = (forecast_return_pct > 0) == (realized_market_return_pct > 0)

        return cls(
            trade_id=report.trade_id,
            closed_at=closed_at or datetime.now(UTC),
            symbol=report.proposal.symbol,
            side=report.proposal.side,
            strategy_version=report.proposal.strategy_version,
            entry_price=entry,
            exit_price=exit_price,
            stop_loss=report.proposal.stop_loss,
            gross_return_pct=gross_return_pct,
            realized_r=realized_r,
            outcome_class=outcome_class,
            forecast_return_pct=forecast_return_pct,
            forecast_error_pct=forecast_error_pct,
            forecast_direction_correct=direction_correct,
            maximum_favorable_excursion_r=maximum_favorable_excursion_r,
            maximum_adverse_excursion_r=maximum_adverse_excursion_r,
        )
