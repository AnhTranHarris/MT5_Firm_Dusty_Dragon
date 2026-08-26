from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field

from dusty_dragon.analytics.firm_health import FirmHealthReport
from dusty_dragon.research.executor import ResearchTaskExecutor, ResearchTaskResult
from dusty_dragon.research.priority_policy import ResearchPriorityPolicy
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
    reprioritized_tasks: int = Field(default=0, ge=0)

    @property
    def completed_count(self) -> int:
        return len(self.completed_task_ids)


@dataclass
class ResearchRuntimeController:
    """Run the durable research DAG under schedule, health, and compute policy.

    The controller keeps four responsibilities separate:
    - ResearchClock decides *when* research is scheduled.
    - Firm health may change *what pending research matters most*.
    - TradingPriorityComputeGovernor decides *how much* research capacity is safe.
    - ResearchTaskExecutor executes the highest-priority runnable durable task.

    HEALTHY, CAUTION, or HALT never disable the research department. They may
    only reorder pending work. Machine pressure may temporarily pause execution
    to protect trading and system stability. Completed evidence is never
    reprioritized or rewritten.

    `max_parallel_workers` is currently used as a bounded tasks-per-heartbeat
    quota because ResearchTaskExecutor is deliberately sequential. A future
    worker pool may consume the same budget without changing this contract.
    """

    clock: ResearchClock
    governor: TradingPriorityComputeGovernor
    executor: ResearchTaskExecutor
    priority_policy: ResearchPriorityPolicy | None = None

    def heartbeat(
        self,
        moment: datetime,
        snapshot: ComputeSnapshot,
        *,
        health_report: FirmHealthReport | None = None,
    ) -> ResearchHeartbeatResult:
        mode = self.clock.mode_at(moment)
        budget = self.governor.budget(mode, snapshot)

        reprioritized = 0
        if health_report is not None and self.priority_policy is not None:
            reprioritized = self.priority_policy.apply(
                self.executor.graph,
                health_report,
            )

        if budget.max_parallel_workers == 0:
            return ResearchHeartbeatResult(
                mode=mode,
                budget=budget,
                reprioritized_tasks=reprioritized,
            )

        completed: list[ResearchTaskResult] = self.executor.run_until_idle(
            max_tasks=budget.max_parallel_workers
        )
        return ResearchHeartbeatResult(
            mode=mode,
            budget=budget,
            completed_task_ids=[str(result.task_id) for result in completed],
            reprioritized_tasks=reprioritized,
        )
