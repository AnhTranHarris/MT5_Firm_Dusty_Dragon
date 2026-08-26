import pytest

from dusty_dragon.runtime.compute_governor import (
    ComputeDecision,
    ComputeSnapshot,
    TradingPriorityComputeGovernor,
)
from dusty_dragon.scheduler.research_clock import ResearchMode


def snapshot(
    *,
    cpu: float = 0.30,
    memory: float = 0.40,
    gpu: float | None = 0.20,
    trading_busy: bool = False,
) -> ComputeSnapshot:
    return ComputeSnapshot(
        cpu_utilization=cpu,
        memory_utilization=memory,
        gpu_utilization=gpu,
        trading_busy=trading_busy,
    )


def test_inactive_research_gets_no_compute():
    budget = TradingPriorityComputeGovernor().budget(ResearchMode.OFF, snapshot())

    assert budget.decision == ComputeDecision.PAUSED
    assert budget.max_parallel_workers == 0
    assert budget.kronos_gpu_allowed is False


def test_heavy_saturday_gets_larger_budget_when_machine_is_healthy():
    governor = TradingPriorityComputeGovernor(normal_workers=4, heavy_workers=8)

    normal = governor.budget(ResearchMode.DAILY_BACKTEST, snapshot())
    heavy = governor.budget(ResearchMode.SATURDAY_HEAVY_BACKTEST, snapshot())

    assert normal.decision == ComputeDecision.FULL
    assert normal.max_parallel_workers == 4
    assert heavy.max_parallel_workers == 8


def test_trading_activity_throttles_research_and_reserves_gpu():
    budget = TradingPriorityComputeGovernor(normal_workers=4).budget(
        ResearchMode.DAILY_BACKTEST,
        snapshot(trading_busy=True),
    )

    assert budget.decision == ComputeDecision.THROTTLED
    assert budget.max_parallel_workers == 2
    assert budget.kronos_gpu_allowed is False


def test_extreme_machine_pressure_pauses_research():
    budget = TradingPriorityComputeGovernor().budget(
        ResearchMode.SATURDAY_HEAVY_BACKTEST,
        snapshot(cpu=0.95),
    )

    assert budget.decision == ComputeDecision.PAUSED
    assert budget.max_parallel_workers == 0


def test_high_gpu_load_throttles_without_disabling_cpu_research():
    budget = TradingPriorityComputeGovernor(normal_workers=4).budget(
        ResearchMode.DAILY_BACKTEST,
        snapshot(gpu=0.90),
    )

    assert budget.decision == ComputeDecision.THROTTLED
    assert budget.max_parallel_workers == 2
    assert budget.kronos_gpu_allowed is False


def test_invalid_threshold_order_is_rejected():
    with pytest.raises(ValueError, match="CPU throttle"):
        TradingPriorityComputeGovernor(cpu_throttle_at=0.95, cpu_pause_at=0.90)
