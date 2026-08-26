from __future__ import annotations

from dataclasses import dataclass

from dusty_dragon.learning.challenger_evaluator import ChallengerComparison
from dusty_dragon.learning.strategy_lineage import PromotionEvidence


@dataclass(frozen=True)
class CampaignPromotionGate:
    """Translate quantitative challenger evidence into lineage promotion gates.

    A passing campaign comparison satisfies the historical backtest and direct
    champion-comparison gates only. Walk-forward, paper-forward, and capital-
    growth evidence stay independent requirements, preventing weekend research
    from promoting itself or promoting a tidy but unprofitable strategy.
    """

    def evidence(
        self,
        comparison: ChallengerComparison,
        *,
        walk_forward_passed: bool = False,
        paper_passed: bool = False,
        capital_growth_passed: bool = False,
    ) -> PromotionEvidence:
        passed = comparison.passed
        notes = self._notes(comparison)
        return PromotionEvidence(
            backtest_passed=passed,
            walk_forward_passed=walk_forward_passed,
            paper_passed=paper_passed,
            compared_to_champion=passed,
            capital_growth_passed=capital_growth_passed,
            notes=notes,
        )

    @staticmethod
    def _notes(comparison: ChallengerComparison) -> str:
        if comparison.passed:
            improvement = comparison.improvement_pct_points
            detail = (
                f"cost-adjusted campaign comparison passed; improvement={improvement:.6f} pct points"
                if improvement is not None
                else "cost-adjusted campaign comparison passed"
            )
            return detail
        return "campaign comparison failed: " + "; ".join(comparison.reasons)
