# ruff: noqa: I001
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from dusty_dragon.research.executor import ResearchTaskResult
from dusty_dragon.runtime.compute_governor import (
    ComputeDecision,
    ComputeSnapshot,
    TradingPriorityComputeGovernor,
)
from dusty_dragon.runtime.research_runtime import ResearchRuntimeController
from dusty_dragon.scheduler.research_clock import ResearchClock, ResearchMode


TZ = ZoneInfo("America/Chicago")


class FakeExecutor:
    def __init__(self) -> None:
        self.quotas: list[int] = []

    def run_until_idle(self, *, max_tasks: int = 100) -> list[ResearchTaskResult]:
        self.quotas.append(max_tasks)
        return [
            ResearchTaskResult(
                task_id=uuid4(),
                task_type="backtest_campaign",
                strategy_version="generalist-v0",
                output={"ok": True},
            )
            for _ in range(max_tasks)
        ]


def at(year: int, month: int, day: int, hour: int) -> datetime:
    return datetime(year, month, day, hour, 0, tzinfo=TZ)


def controller(executor: FakeExecutor) -> ResearchRuntimeController:
    return ResearchRuntimeController(
        clock=ResearchClock(),
        governor=TradingPriorityComputeGovernor(normal_workers=4, heavy_workers=8),
        executor=executor,  # type: ignore[arg-type]
    )


def quiet() -> ComputeSnapshot:
    return ComputeSnapshot(
        cpu_utilization=0.20,
        memory_utilization=0.30,
        gpu_utilization=0.10,
        trading_busy=False,
    )


def test_off_schedule_does_not_claim_research_tasks():
    executor = FakeExecutor()
    result = controller(executor).heartbeat(at(2026, 8, 24, 12), quiet())

    assert result.mode == ResearchMode.OFF
    assert result.budget.decision == ComputeDecision.PAUSED
    assert result.completed_count == 0
    assert executor.quotas == []


def test_daily_window_runs_bounded_normal_research_quota():
    executor = FakeExecutor()
    result = controller(executor).heartbeat(at(2026, 8, 24, 18), quiet())

    assert result.mode == ResearchMode.DAILY_BACKTEST
    assert result.budget.decision == ComputeDecision.FULL
    assert result.completed_count == 4
    assert executor.quotas == [4]


def test_saturday_heavy_window_uses_larger_research_quota():
    executor = FakeExecutor()
    result = controller(executor).heartbeat(at(2026, 8, 29, 10), quiet())

    assert result.mode == ResearchMode.SATURDAY_HEAVY_BACKTEST
    assert result.completed_count == 8
    assert executor.quotas == [8]


def test_trading_busy_throttles_research_but_does_not_disable_it():
    executor = FakeExecutor()
    snapshot = quiet().model_copy(update={"trading_busy": True})
    result = controller(executor).heartbeat(at(2026, 8, 24, 18), snapshot)

    assert result.budget.decision == ComputeDecision.THROTTLED
    assert result.completed_count == 2
    assert executor.quotas == [2]


def test_machine_pressure_pauses_research_without_touching_task_queue():
    executor = FakeExecutor()
    snapshot = quiet().model_copy(update={"cpu_utilization": 0.95})
    result = controller(executor).heartbeat(at(2026, 8, 24, 18), snapshot)

    assert result.budget.decision == ComputeDecision.PAUSED
    assert result.completed_count == 0
    assert executor.quotas == []
