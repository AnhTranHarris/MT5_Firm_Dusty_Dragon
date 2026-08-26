from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, Field

from dusty_dragon.learning.strategy_lineage import StrategyRecord
from dusty_dragon.research.challenger_worker import (
    ChallengerHypothesis,
    ChallengerResearchWorker,
)
from dusty_dragon.research.factors import FactorSnapshot
from dusty_dragon.research.task_graph import ResearchTask, ResearchTaskGraph
from dusty_dragon.research.weekend import WeekendResearchBrief


class ChallengerTaskChain(BaseModel):
    challenger_id: UUID
    challenger_version: str
    hypothesis_code: str
    task_ids: list[UUID] = Field(default_factory=list)


class ResearchPipelinePlan(BaseModel):
    eligible: bool
    champion_id: UUID
    chains: list[ChallengerTaskChain] = Field(default_factory=list)


@dataclass(frozen=True)
class DurableChallengerResearchPipeline:
    """Translate weekend evidence into lineage-safe, durable research DAGs.

    Automaton roadmap: research work is persisted as dependency-aware tasks
    that can survive process restarts and be retried independently.

    Vibe-Trading roadmap: each quantitative stage is explicit and auditable.
    Kronos roadmap: forecast experiments remain research inputs; no forecast
    task can promote a strategy or execute an order.
    """

    worker: ChallengerResearchWorker
    graph: ResearchTaskGraph
    runs_per_symbol: int = 12

    def __post_init__(self) -> None:
        if not 10 <= self.runs_per_symbol <= 20:
            raise ValueError("runs_per_symbol must be between 10 and 20")

    def plan(
        self,
        *,
        champion: StrategyRecord,
        brief: WeekendResearchBrief,
        factor_snapshot: FactorSnapshot | None = None,
    ) -> ResearchPipelinePlan:
        """Create challengers and enqueue their research chains.

        Creating a challenger is a lineage transaction, not a research result.
        Promotion remains impossible until downstream validation gates finish.
        """
        result = self.worker.run(
            champion=champion,
            brief=brief,
            factor_snapshot=factor_snapshot,
        )
        if not result.eligible:
            return ResearchPipelinePlan(eligible=False, champion_id=champion.id)

        hypothesis_by_code = {item.code: item for item in result.hypotheses}
        chains: list[ChallengerTaskChain] = []
        for challenger in result.challengers:
            research = challenger.config.get("research", {})
            code = str(research.get("hypothesis_code", "UNKNOWN"))
            hypothesis = hypothesis_by_code.get(code)
            chains.append(
                self._enqueue_chain(
                    champion=champion,
                    challenger=challenger,
                    hypothesis=hypothesis,
                    factor_snapshot=factor_snapshot,
                )
            )
        return ResearchPipelinePlan(
            eligible=True,
            champion_id=champion.id,
            chains=chains,
        )

    def _enqueue_chain(
        self,
        *,
        champion: StrategyRecord,
        challenger: StrategyRecord,
        hypothesis: ChallengerHypothesis | None,
        factor_snapshot: FactorSnapshot | None,
    ) -> ChallengerTaskChain:
        common = {
            "champion_id": str(champion.id),
            "champion_version": champion.version,
            "challenger_id": str(challenger.id),
            "challenger_version": challenger.version,
            "hypothesis_code": hypothesis.code if hypothesis else "UNKNOWN",
            "hypothesis_explanation": hypothesis.explanation if hypothesis else "",
        }
        if factor_snapshot is not None:
            common["observed_regime"] = factor_snapshot.regime

        campaign = self._add_task(
            task_type="backtest_campaign",
            strategy_version=challenger.version,
            payload={
                **common,
                "runs_per_symbol": self.runs_per_symbol,
                "prior_week_min": 1,
                "prior_week_max": 8,
                "include_unused_symbol_counterfactuals": True,
            },
        )
        cost_regime = self._add_task(
            task_type="cost_regime_evaluation",
            strategy_version=challenger.version,
            payload=common,
            depends_on=[campaign.id],
        )
        comparison = self._add_task(
            task_type="champion_comparison",
            strategy_version=challenger.version,
            payload=common,
            depends_on=[cost_regime.id],
        )
        sunday = self._add_task(
            task_type="sunday_validation",
            strategy_version=challenger.version,
            payload={**common, "promotion_authority": False},
            depends_on=[comparison.id],
        )
        return ChallengerTaskChain(
            challenger_id=challenger.id,
            challenger_version=challenger.version,
            hypothesis_code=common["hypothesis_code"],
            task_ids=[campaign.id, cost_regime.id, comparison.id, sunday.id],
        )

    def _add_task(
        self,
        *,
        task_type: str,
        strategy_version: str,
        payload: dict,
        depends_on: list[UUID] | None = None,
    ) -> ResearchTask:
        task = ResearchTask(
            task_type=task_type,
            strategy_version=strategy_version,
            payload=payload,
            depends_on=depends_on or [],
        )
        return self.graph.add(task)
