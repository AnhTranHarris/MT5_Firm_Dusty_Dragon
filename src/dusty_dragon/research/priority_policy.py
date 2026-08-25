from __future__ import annotations

from dataclasses import dataclass

from dusty_dragon.analytics.firm_health import FirmHealthReport, FirmHealthStatus
from dusty_dragon.research.task_graph import ResearchTask, ResearchTaskGraph, ResearchTaskStatus


@dataclass(frozen=True)
class ResearchPriorityPolicy:
    """Reorder pending research around the firm's most urgent economic problems.

    Priority changes alter *which* research runs first, never whether research
    exists and never the meaning of completed evidence. Running/succeeded/failed
    tasks are immutable to this policy.

    Automaton roadmap: degraded operating conditions defer non-essential work and
    elevate health-recovery tasks.
    Vibe-Trading roadmap: deployment/research decisions are evidence- and risk-led.
    Kronos roadmap: forecast calibration can be prioritized, but cannot replace
    financial/risk governance or gain execution authority.
    """

    normal_base: int = 50
    elevated_base: int = 70
    urgent_base: int = 90

    def apply(self, graph: ResearchTaskGraph, report: FirmHealthReport) -> int:
        changed = 0
        for task in graph.all():
            if task.status != ResearchTaskStatus.PENDING:
                continue
            priority = self.priority_for(task, report)
            if priority != task.priority:
                graph.set_priority(task.id, priority)
                changed += 1
        return changed

    def priority_for(self, task: ResearchTask, report: FirmHealthReport) -> int:
        base = self._base(report.status)
        reasons = " ".join(report.reasons).lower()
        task_type = task.task_type.lower()
        hypothesis = str(task.payload.get("hypothesis_code", "")).lower()

        boost = 0
        if any(term in reasons for term in ("capital", "drawdown", "expectancy")):
            if task_type in {
                "backtest_campaign",
                "cost_regime_evaluation",
                "champion_comparison",
            }:
                boost += 8
            if any(term in hypothesis for term in ("drawdown", "risk", "expectancy", "robust")):
                boost += 8

        if "execution costs" in reasons and task_type == "cost_regime_evaluation":
            boost += 12

        if "kronos" in reasons:
            if "kronos" in hypothesis or "forecast" in hypothesis:
                boost += 10
            if task_type == "backtest_campaign":
                boost += 4

        if any(term in reasons for term in ("archive", "task queue")):
            if task_type in {"archive_health_check", "research_queue_health_check"}:
                boost += 12

        # Validation must not jump ahead merely because the firm is unhealthy.
        if task_type == "sunday_validation":
            boost -= 5

        return max(0, min(100, base + boost))

    def _base(self, status: FirmHealthStatus) -> int:
        if status == FirmHealthStatus.HALT:
            return self.urgent_base
        if status == FirmHealthStatus.CAUTION:
            return self.elevated_base
        return self.normal_base
