from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from dusty_dragon.research.executor import TaskHandler
from dusty_dragon.research.task_graph import ResearchTask

PayloadRunner = Callable[[dict[str, Any]], Any]
DependentRunner = Callable[[dict[str, Any], Any], Any]


@dataclass(frozen=True)
class ResearchStageHandlers:
    """Bind the durable DAG to explicit quantitative research capabilities.

    Vibe-Trading roadmap: campaign, cost/regime, and comparison are separate
    financial stages. Automaton roadmap: handlers are bounded worker tools.
    Kronos roadmap: any Kronos-backed campaign work is injected through the
    campaign runner and receives no scheduling, execution, or promotion power.
    """

    campaign_runner: PayloadRunner
    cost_regime_runner: DependentRunner
    champion_comparison_runner: DependentRunner
    sunday_validation_runner: DependentRunner

    def handlers(self) -> dict[str, TaskHandler]:
        return {
            "backtest_campaign": self._campaign,
            "cost_regime_evaluation": self._cost_regime,
            "champion_comparison": self._champion_comparison,
            "sunday_validation": self._sunday_validation,
        }

    def _campaign(self, task: ResearchTask, dependencies: dict[UUID, Any]) -> Any:
        if dependencies:
            raise ValueError("backtest campaign must not receive dependency outputs")
        runs = int(task.payload.get("runs_per_symbol", 0))
        if not 10 <= runs <= 20:
            raise ValueError("backtest campaign requires 10-20 runs per symbol")
        if task.payload.get("prior_week_min") != 1 or task.payload.get("prior_week_max") != 8:
            raise ValueError("backtest campaign prior-week range must remain 1-8")
        if task.payload.get("include_unused_symbol_counterfactuals") is not True:
            raise ValueError("backtest campaign must include unused-symbol counterfactuals")
        return self.campaign_runner(task.payload)

    def _cost_regime(self, task: ResearchTask, dependencies: dict[UUID, Any]) -> Any:
        prior = self._single_dependency(dependencies, "cost/regime evaluation")
        return self.cost_regime_runner(task.payload, prior)

    def _champion_comparison(
        self, task: ResearchTask, dependencies: dict[UUID, Any]
    ) -> Any:
        prior = self._single_dependency(dependencies, "champion comparison")
        return self.champion_comparison_runner(task.payload, prior)

    def _sunday_validation(
        self, task: ResearchTask, dependencies: dict[UUID, Any]
    ) -> Any:
        if task.payload.get("promotion_authority") is not False:
            raise PermissionError("Sunday validation must not have promotion authority")
        prior = self._single_dependency(dependencies, "Sunday validation")
        return self.sunday_validation_runner(task.payload, prior)

    @staticmethod
    def _single_dependency(dependencies: dict[UUID, Any], stage: str) -> Any:
        if len(dependencies) != 1:
            raise ValueError(f"{stage} requires exactly one dependency result")
        return next(iter(dependencies.values()))
