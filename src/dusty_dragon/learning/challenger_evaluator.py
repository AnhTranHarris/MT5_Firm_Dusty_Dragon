from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from dusty_dragon.backtest.campaign_evaluator import CampaignEvaluation


class ChallengerComparison(BaseModel):
    passed: bool
    champion_mean_return_pct: float | None = None
    challenger_mean_return_pct: float | None = None
    improvement_pct_points: float | None = None
    champion_profitable_rate: float | None = Field(default=None, ge=0, le=1)
    challenger_profitable_rate: float | None = Field(default=None, ge=0, le=1)
    challenger_worst_return_pct: float | None = None
    reasons: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class ChallengerCampaignComparator:
    """Gate challenger campaigns against the frozen champion.

    Vibe-Trading roadmap: strategy selection must consider cost-adjusted return,
    robustness, and downside rather than gross profit alone.

    Automaton roadmap: descendants compete through explicit evidence instead of
    mutating the active parent in place.

    Kronos roadmap: both strategies are evaluated through the same forecast and
    campaign infrastructure so forecast changes are measured rather than assumed.
    """

    minimum_experiments: int = 10
    minimum_profitable_rate: float = 0.60
    minimum_mean_improvement_pct_points: float = 0.0
    maximum_worst_return_pct: float = -0.25
    maximum_profitable_rate_regression: float = 0.05

    def __post_init__(self) -> None:
        if self.minimum_experiments <= 0:
            raise ValueError("minimum_experiments must be positive")
        if not 0 <= self.minimum_profitable_rate <= 1:
            raise ValueError("minimum_profitable_rate must be between 0 and 1")
        if not 0 <= self.maximum_profitable_rate_regression <= 1:
            raise ValueError("maximum profitable-rate regression must be between 0 and 1")

    def compare(
        self,
        champion: CampaignEvaluation,
        challenger: CampaignEvaluation,
    ) -> ChallengerComparison:
        reasons: list[str] = []
        if champion.experiment_count < self.minimum_experiments:
            reasons.append("champion campaign has insufficient experiments")
        if challenger.experiment_count < self.minimum_experiments:
            reasons.append("challenger campaign has insufficient experiments")

        champion_mean = champion.mean_cost_adjusted_return_pct
        challenger_mean = challenger.mean_cost_adjusted_return_pct
        improvement = None
        if champion_mean is None or challenger_mean is None:
            reasons.append("cost-adjusted mean return is unavailable")
        else:
            improvement = challenger_mean - champion_mean
            if challenger_mean <= 0:
                reasons.append("challenger cost-adjusted mean return is not positive")
            if improvement <= self.minimum_mean_improvement_pct_points:
                reasons.append("challenger does not improve cost-adjusted mean return")

        champion_rate = champion.profitable_after_cost_rate
        challenger_rate = challenger.profitable_after_cost_rate
        if challenger_rate is None:
            reasons.append("challenger profitable-run rate is unavailable")
        else:
            if challenger_rate < self.minimum_profitable_rate:
                reasons.append("challenger profitable-run rate is below threshold")
            if champion_rate is not None and (
                challenger_rate + self.maximum_profitable_rate_regression < champion_rate
            ):
                reasons.append("challenger profitable-run rate regresses too far")

        worst = challenger.worst_cost_adjusted_return_pct
        if worst is None:
            reasons.append("challenger worst-run return is unavailable")
        elif worst < self.maximum_worst_return_pct:
            reasons.append("challenger worst-run return breaches downside threshold")

        self._check_regime_regressions(champion, challenger, reasons)
        return ChallengerComparison(
            passed=not reasons,
            champion_mean_return_pct=champion_mean,
            challenger_mean_return_pct=challenger_mean,
            improvement_pct_points=improvement,
            champion_profitable_rate=champion_rate,
            challenger_profitable_rate=challenger_rate,
            challenger_worst_return_pct=worst,
            reasons=reasons,
        )

    @staticmethod
    def _check_regime_regressions(
        champion: CampaignEvaluation,
        challenger: CampaignEvaluation,
        reasons: list[str],
    ) -> None:
        shared_regimes = set(champion.regime_mean_returns) & set(
            challenger.regime_mean_returns
        )
        if not shared_regimes:
            reasons.append("champion and challenger have no shared regime evidence")
            return
        materially_worse = [
            regime
            for regime in sorted(shared_regimes)
            if challenger.regime_mean_returns[regime]
            < champion.regime_mean_returns[regime] - 0.10
        ]
        if materially_worse:
            reasons.append(
                "challenger materially regresses in regimes: " + ", ".join(materially_worse)
            )
