from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field

from dusty_dragon.analytics.performance import FirmPerformanceAnalyzer, FirmPerformanceSummary
from dusty_dragon.backtest.weekend_protocol import WeekendProtocolResult
from dusty_dragon.scheduler.weekly_clock import FirmPhase
from dusty_dragon.storage.outcome_store import TradeOutcomeStore


class ResearchPriority(BaseModel):
    code: str
    severity: str
    explanation: str


class WeekendRobustnessSummary(BaseModel):
    cross_symbol_tests: int = Field(ge=0)
    cross_symbol_positive_rate: float | None = Field(default=None, ge=0, le=1)
    prior_week_tests: int = Field(ge=0)
    prior_week_positive_rate: float | None = Field(default=None, ge=0, le=1)
    classification: str


class WeekendResearchBrief(BaseModel):
    generated_at: datetime
    phase: FirmPhase
    strategy_version: str
    performance: FirmPerformanceSummary
    priorities: list[ResearchPriority] = Field(default_factory=list)
    eligible_for_challenger_research: bool
    robustness: WeekendRobustnessSummary | None = None


@dataclass(frozen=True)
class WeekendResearchService:
    """Compress immutable outcomes and robustness tests into weekend research.

    Vibe-Trading roadmap: metrics and validation remain reusable financial
    research infrastructure rather than hidden inside execution.

    Automaton roadmap: scheduled workers consume durable evidence and emit
    explicit next tasks. They do not rewrite the champion in place.

    Kronos roadmap: forecast calibration remains separately measurable from
    profitability and from generalization across symbols/time windows.
    """

    outcome_store: TradeOutcomeStore
    analyzer: FirmPerformanceAnalyzer
    strategy_version: str = "generalist-v0"
    minimum_outcomes_for_research: int = 20

    def __post_init__(self) -> None:
        if self.minimum_outcomes_for_research <= 0:
            raise ValueError("minimum_outcomes_for_research must be positive")

    def run(
        self,
        *,
        phase: FirmPhase,
        observed_at: datetime,
        protocol_result: WeekendProtocolResult | None = None,
    ) -> WeekendResearchBrief:
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
        robustness = self._robustness(protocol_result) if protocol_result is not None else None
        priorities = self._priorities(performance, robustness)
        return WeekendResearchBrief(
            generated_at=observed_at,
            phase=phase,
            strategy_version=self.strategy_version,
            performance=performance,
            priorities=priorities,
            eligible_for_challenger_research=(
                performance.trade_count >= self.minimum_outcomes_for_research
            ),
            robustness=robustness,
        )

    @staticmethod
    def _robustness(protocol: WeekendProtocolResult) -> WeekendRobustnessSummary:
        cross_scores = [
            result.walk_forward.mean_signed_return_pct
            for result in protocol.cross_symbol_results
            if result.walk_forward.mean_signed_return_pct is not None
        ]
        prior_scores = [
            result.walk_forward.mean_signed_return_pct
            for result in protocol.prior_week_results
            if result.walk_forward.mean_signed_return_pct is not None
        ]
        cross_positive = (
            sum(score > 0 for score in cross_scores) / len(cross_scores)
            if cross_scores
            else None
        )
        prior_positive = (
            sum(score > 0 for score in prior_scores) / len(prior_scores)
            if prior_scores
            else None
        )

        if cross_positive is not None and prior_positive is not None:
            if cross_positive >= 0.60 and prior_positive >= 0.60:
                classification = "generalizing"
            elif cross_positive < 0.40 and prior_positive < 0.40:
                classification = "overfit_risk"
            elif cross_positive >= 0.60 and prior_positive < 0.40:
                classification = "time_specific_risk"
            elif cross_positive < 0.40 and prior_positive >= 0.60:
                classification = "symbol_specific_risk"
            else:
                classification = "mixed"
        else:
            classification = "insufficient_robustness_evidence"

        return WeekendRobustnessSummary(
            cross_symbol_tests=len(cross_scores),
            cross_symbol_positive_rate=cross_positive,
            prior_week_tests=len(prior_scores),
            prior_week_positive_rate=prior_positive,
            classification=classification,
        )

    @staticmethod
    def _priorities(
        performance: FirmPerformanceSummary,
        robustness: WeekendRobustnessSummary | None,
    ) -> list[ResearchPriority]:
        priorities: list[ResearchPriority] = []
        if performance.trade_count == 0:
            priorities.append(
                ResearchPriority(
                    code="INSUFFICIENT_OUTCOMES",
                    severity="info",
                    explanation="No realized trades are available for evidence-based research yet.",
                )
            )

        if performance.trade_count > 0 and performance.expectancy_r <= 0:
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

        if robustness is not None:
            if robustness.classification == "overfit_risk":
                priorities.append(
                    ResearchPriority(
                        code="OVERFIT_RISK",
                        severity="high",
                        explanation=(
                            "The strategy is weak across both unused symbols and sampled prior "
                            "weeks; do not promote without broader robustness evidence."
                        ),
                    )
                )
            elif robustness.classification == "time_specific_risk":
                priorities.append(
                    ResearchPriority(
                        code="TEMPORAL_ROBUSTNESS",
                        severity="high",
                        explanation=(
                            "Cross-symbol results generalize better than prior-week replays; "
                            "investigate time/regime dependence before promotion."
                        ),
                    )
                )
            elif robustness.classification == "symbol_specific_risk":
                priorities.append(
                    ResearchPriority(
                        code="CROSS_SYMBOL_GENERALIZATION",
                        severity="high",
                        explanation=(
                            "Prior-week replays generalize better than unused-symbol tests; "
                            "investigate symbol-specific dependence before promotion."
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
