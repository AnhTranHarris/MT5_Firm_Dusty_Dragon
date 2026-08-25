from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, Field

from dusty_dragon.scheduler.research_clock import ResearchMode


class ComputeDecision(StrEnum):
    FULL = "full"
    THROTTLED = "throttled"
    PAUSED = "paused"


class ComputeSnapshot(BaseModel):
    cpu_utilization: float = Field(ge=0, le=1)
    memory_utilization: float = Field(ge=0, le=1)
    gpu_utilization: float | None = Field(default=None, ge=0, le=1)
    trading_busy: bool = False


class ResearchComputeBudget(BaseModel):
    decision: ComputeDecision
    max_parallel_workers: int = Field(ge=0)
    kronos_gpu_allowed: bool
    reason: str


@dataclass(frozen=True)
class TradingPriorityComputeGovernor:
    """Protect trading resources while allowing continuous research.

    Research is never disabled because the firm is healthy/cautious/halted;
    only schedule and machine-resource pressure affect its compute budget.
    Trading always has priority over backtesting and Kronos research workloads.
    """

    normal_workers: int = 4
    heavy_workers: int = 8
    cpu_throttle_at: float = 0.70
    cpu_pause_at: float = 0.90
    memory_throttle_at: float = 0.75
    memory_pause_at: float = 0.90
    gpu_throttle_at: float = 0.75

    def __post_init__(self) -> None:
        if self.normal_workers <= 0 or self.heavy_workers <= 0:
            raise ValueError("worker limits must be positive")
        for value in (
            self.cpu_throttle_at,
            self.cpu_pause_at,
            self.memory_throttle_at,
            self.memory_pause_at,
            self.gpu_throttle_at,
        ):
            if not 0 < value <= 1:
                raise ValueError("utilization thresholds must be in (0, 1]")
        if self.cpu_throttle_at >= self.cpu_pause_at:
            raise ValueError("CPU throttle threshold must be below pause threshold")
        if self.memory_throttle_at >= self.memory_pause_at:
            raise ValueError("memory throttle threshold must be below pause threshold")

    def budget(
        self,
        mode: ResearchMode,
        snapshot: ComputeSnapshot,
    ) -> ResearchComputeBudget:
        if mode == ResearchMode.OFF:
            return ResearchComputeBudget(
                decision=ComputeDecision.PAUSED,
                max_parallel_workers=0,
                kronos_gpu_allowed=False,
                reason="research schedule is inactive",
            )

        if (
            snapshot.cpu_utilization >= self.cpu_pause_at
            or snapshot.memory_utilization >= self.memory_pause_at
        ):
            return ResearchComputeBudget(
                decision=ComputeDecision.PAUSED,
                max_parallel_workers=0,
                kronos_gpu_allowed=False,
                reason="machine pressure exceeds research pause threshold",
            )

        base_workers = (
            self.heavy_workers
            if mode == ResearchMode.SATURDAY_HEAVY_BACKTEST
            else self.normal_workers
        )
        gpu_allowed = (
            snapshot.gpu_utilization is None
            or snapshot.gpu_utilization < self.gpu_throttle_at
        )

        overloaded = (
            snapshot.trading_busy
            or snapshot.cpu_utilization >= self.cpu_throttle_at
            or snapshot.memory_utilization >= self.memory_throttle_at
            or not gpu_allowed
        )
        if overloaded:
            return ResearchComputeBudget(
                decision=ComputeDecision.THROTTLED,
                max_parallel_workers=max(1, base_workers // 2),
                kronos_gpu_allowed=gpu_allowed and not snapshot.trading_busy,
                reason="research throttled to preserve trading/system headroom",
            )

        return ResearchComputeBudget(
            decision=ComputeDecision.FULL,
            max_parallel_workers=base_workers,
            kronos_gpu_allowed=gpu_allowed,
            reason="research may use scheduled compute budget",
        )
