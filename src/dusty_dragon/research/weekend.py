from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field

from dusty_dragon.analytics.performance import FirmPerformanceAnalyzer, FirmPerformanceSummary
from dusty_dragon.scheduler.weekly_clock import FirmPhase
from dusty_dragon.storage.outcome_store import TradeOutcomeStore


class ResearchPriority(BaseModel):
    code: str
    severity: str
    explanation: str


class WeekendResearchBrief(BaseModel):
    generated_at: datetime
    phase: FirmPhase
    strategy_version: str
    performance: FirmPerformanceSummary
    priorities: list[ResearchPriority] = Field(default_factory=list)
    eligible_for_challenger_research: bool


@dataclass(frozen=True)
class WeekendResearchService:
    """Compress immutable trade outcomes into a weekend research observation.

    Vibe-Trading roadmap: financial metrics are reusable inputs to research and
    backtesting rather than hidden inside strategy execution.

    Automaton roadmap: a scheduled worker consumes compact persistent state and
    produces explicit next tasks. This service is deterministic groundwork for
    the later AI hypothesis/challenger worker.

    Kronos roadmap: forecast accuracy/error is evaluated independently of trade
    profitability, allowing future retraining or weighting experiments to target
    the actual failure mode.
    """

    outcome_store: TradeOutcomeStore
    analyzer: FirmPerformanceAnalyzer
    strategy_version: str = "generalist-v0"
    minimum_outcomes_for_research: int = 20

    def __post_init__(self) -> None:
        if self.minimum_outcomes_for_research <= 0:
            raise ValueError("minimum_outcomes_for_research must be positive")

    def run(self, *, phase: FirmPhase, observed_at: datetime) -> WeekendResearchBrief:
        if phase not in {FirmPhase.WEEKEND_RESEARCH, FirmPhase.SUNDAY_VALIDATION}:
            raise ValueError("weekend research service may only run outside trading phase")
        if observed_at.tzinfo is None:
            raise ValueError("weekend research requires timezone-aware observed_at")

        outcomes = [
            outcome
            for outcome in self.outcome_store.all()
            if outcome.strategy_version == self.strategy_version
        ]
        performance = self.analyzer.summarize(outcomes)
        priorities = self._priorities(performance)
        return WeekendResearchBrief(
            generated_at=observed_at,
            phase=phase,
            strategy_version=self.strategy_version,
            performance=performance,
            priorities=priorities,
            eligible_for_challenger_research=(
                performance.trade_count >= self.minimum_outcomes_for_research
            ),
        )

    @staticmethod
    def _priorities(performance: FirmPerformanceSummary) -> list[ResearchPriority]:
        priorities: list[ResearchPriority] = []
        if performance.trade_count == 0:
            priorities.append(
                ResearchPriority(
                    code="INSUFFICIENT_OUTCOMES",
                    severity="info",
                    explanation="No realized trades are available for evidence-based research yet.",
                )
            )
            return priorities

        if performance.expectancy_r <= 0:
            priorities.append(
                ResearchPriority(
                    code="NONPOSITIVE_EXPECTANCY",
                    severity="high",
                    explanation=(
                        "Realized expectancy is not positive; prioritize signal, entry, exit, "
                        "and regime hypotheses before considering promotion."
                    ),
                )
            )
        if performance.forecast_samples >= 10:
            accuracy = performance.forecast_direction_accuracy
            if accuracy is not None and accuracy < 0.50:
                priorities.append(
                    ResearchPriority(
                        code="KRONOS_DIRECTION_CALIBRATION",
                        severity="high",
                        explanation=(
                            "Kronos directional accuracy is below 50% on recorded outcomes; "
                            "test horizon, regime weighting, and forecast filtering."
                        ),
                    )
                )
        if performance.max_drawdown_r >= 5.0:
            priorities.append(
                ResearchPriority(
                    code="DRAWDOWN_CONTROL",
                    severity="high",
                    explanation=(
                        "Peak-to-trough drawdown is at least 5R; investigate exposure, stop, "
                        "session, and correlated-loss controls."
                    ),
                )
            )
        if not priorities:
            priorities.append(
                ResearchPriority(
                    code="ROBUSTNESS_VALIDATION",
                    severity="normal",
                    explanation=(
                        "No primary failure threshold is breached; prioritize robustness, "
                        "walk-forward, and regime validation before changing the champion."
                    ),
                )
            )
        return priorities
