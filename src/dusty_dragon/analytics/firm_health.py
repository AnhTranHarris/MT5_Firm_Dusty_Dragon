from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, Field

from dusty_dragon.analytics.capital_growth import CapitalGrowthSummary
from dusty_dragon.analytics.performance import FirmPerformanceSummary


class FirmHealthStatus(StrEnum):
    HEALTHY = "healthy"
    CAUTION = "caution"
    HALT = "halt"


class ResearchPriority(StrEnum):
    NORMAL = "normal"
    ELEVATED = "elevated"
    URGENT = "urgent"


class FirmHealthInputs(BaseModel):
    growth: CapitalGrowthSummary
    performance: FirmPerformanceSummary
    mt5_connected: bool = True
    archive_healthy: bool = True
    research_queue_healthy: bool = True
    kronos_calibration_degrading: bool = False
    execution_cost_regression: bool = False


class FirmHealthReport(BaseModel):
    status: FirmHealthStatus
    trading_risk_multiplier: float = Field(ge=0, le=1)
    research_priority: ResearchPriority
    research_enabled: bool = True
    reasons: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class FirmHealthGrowthMonitor:
    """Classify firm health without ever disabling research.

    Capital growth is the primary business outcome. Drawdown, expectancy,
    infrastructure, model calibration, and execution quality constrain whether
    trading may continue at full risk.

    Vibe-Trading roadmap: risk, drawdown, costs, and portfolio performance must
    govern deployment decisions.
    Automaton roadmap: health signals should alter operational behavior while
    durable background work continues.
    Kronos roadmap: model calibration is diagnostic evidence; it cannot override
    firm profitability or execution governance.
    """

    caution_drawdown_pct: float = 5.0
    halt_drawdown_pct: float = 10.0
    caution_expectancy_r: float = 0.0
    caution_risk_multiplier: float = 0.50

    def __post_init__(self) -> None:
        if not 0 < self.caution_drawdown_pct < self.halt_drawdown_pct <= 100:
            raise ValueError("drawdown thresholds must be ordered within (0, 100]")
        if not 0 <= self.caution_risk_multiplier <= 1:
            raise ValueError("caution_risk_multiplier must be between 0 and 1")

    def evaluate(self, inputs: FirmHealthInputs) -> FirmHealthReport:
        reasons: list[str] = []
        halt = False
        caution = False

        if not inputs.mt5_connected:
            halt = True
            reasons.append("MT5 connectivity unavailable")
        if not inputs.growth.capital_preserved:
            halt = True
            reasons.append("capital preservation constraint breached")
        if inputs.growth.max_drawdown_pct >= self.halt_drawdown_pct:
            halt = True
            reasons.append("maximum drawdown reached halt threshold")

        if not inputs.growth.profitable:
            caution = True
            reasons.append("account capital is not growing")
        if inputs.performance.expectancy_r <= self.caution_expectancy_r:
            caution = True
            reasons.append("trade expectancy is non-positive")
        if inputs.growth.max_drawdown_pct >= self.caution_drawdown_pct:
            caution = True
            reasons.append("drawdown reached caution threshold")
        if inputs.kronos_calibration_degrading:
            caution = True
            reasons.append("Kronos calibration is degrading")
        if inputs.execution_cost_regression:
            caution = True
            reasons.append("execution costs are degrading realized edge")
        if not inputs.archive_healthy:
            caution = True
            reasons.append("historical archive health is degraded")
        if not inputs.research_queue_healthy:
            caution = True
            reasons.append("research task queue health is degraded")

        if halt:
            return FirmHealthReport(
                status=FirmHealthStatus.HALT,
                trading_risk_multiplier=0.0,
                research_priority=ResearchPriority.URGENT,
                research_enabled=True,
                reasons=reasons,
            )
        if caution:
            return FirmHealthReport(
                status=FirmHealthStatus.CAUTION,
                trading_risk_multiplier=self.caution_risk_multiplier,
                research_priority=ResearchPriority.ELEVATED,
                research_enabled=True,
                reasons=reasons,
            )
        return FirmHealthReport(
            status=FirmHealthStatus.HEALTHY,
            trading_risk_multiplier=1.0,
            research_priority=ResearchPriority.NORMAL,
            research_enabled=True,
            reasons=["capital is growing within firm risk constraints"],
        )
