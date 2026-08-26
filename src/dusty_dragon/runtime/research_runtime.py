from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field

from dusty_dragon.research.executor import ResearchTaskExecutor, ResearchTaskResult
from dusty_dragon.runtime.compute_governor import (
    ComputeSnapshot,
    ResearchComputeBudget,
    TradingPriorityComputeGovernor,
)
from dusty_dragon.scheduler.research_clock import ResearchClock, ResearchMode


class ResearchHeartbeatResult(BaseModel):
    """Observable result of one scheduled research heartbeat."""

    mode: ResearchMode
    budget: ResearchComputeBudget
    completed_task_ids: list[str] = Field(default_factory=list)

    @property
    def completed_count(self) -> int:
        return len(self.completed_task_ids)


@dataclass
class ResearchRuntimeController:
    """Run the durable research DAG under schedule and machine-resource policy.

    The controller combines three intentionally separate concerns:
    - ResearchClock decides *when* research is scheduled.
    - TradingPriorityComputeGovernor decides *how much* research capacity is safe.
    - ResearchTaskExecutor decides *what runnable durable task* executes next.

    Firm health is intentionally absent. HEALTHY, CAUTION, or HALT may change
    trading risk and research priority, but they never disable the research
    department. Machine pressure may temporarily pause research to protect the
    trading process and system stability.

    `max_parallel_workers` is currently used as a bounded tasks-per-heartbeat
    quota because ResearchTaskExecutor is deliberately sequential. A future
    worker pool may consume the same budget without changing this contract.
    """

    clock: ResearchClock
    governor: TradingPriorityComputeGovernor
    executor: ResearchTaskExecutor

    def heartbeat(
        self,
        moment: datetime,
        snapshot: ComputeSnapshot,
    ) -> ResearchHeartbeatResult:
        mode = self.clock.mode_at(moment)
        budget = self.governor.budget(mode, snapshot)

        if budget.max_parallel_workers == 0:
            return ResearchHeartbeatResult(mode=mode, budget=budget)

        completed: list[ResearchTaskResult] = self.executor.run_until_idle(
            max_tasks=budget.max_parallel_workers
        )
        return ResearchHeartbeatResult(
            mode=mode,
            budget=budget,
            completed_task_ids=[str(result.task_id) for result in completed],
        )
