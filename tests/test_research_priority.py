import sqlite3
from pathlib import Path

from dusty_dragon.analytics.firm_health import (
    FirmHealthReport,
    FirmHealthStatus,
    ResearchPriority,
)
from dusty_dragon.research.priority_policy import ResearchPriorityPolicy
from dusty_dragon.research.task_graph import ResearchTask, ResearchTaskGraph


def report(status: FirmHealthStatus, *reasons: str) -> FirmHealthReport:
    return FirmHealthReport(
        status=status,
        trading_risk_multiplier=0.0 if status == FirmHealthStatus.HALT else 0.5,
        research_priority=(
            ResearchPriority.URGENT
            if status == FirmHealthStatus.HALT
            else ResearchPriority.ELEVATED
            if status == FirmHealthStatus.CAUTION
            else ResearchPriority.NORMAL
        ),
        research_enabled=True,
        reasons=list(reasons),
    )


def test_higher_priority_runnable_task_claims_first(tmp_path: Path):
    graph = ResearchTaskGraph(tmp_path / "tasks.db")
    low = graph.add(ResearchTask(task_type="explore", strategy_version="v1", priority=20))
    high = graph.add(ResearchTask(task_type="diagnose", strategy_version="v1", priority=90))

    claimed = graph.claim_next()

    assert claimed is not None
    assert claimed.id == high.id
    assert graph.get(low.id).priority == 20


def test_halt_prioritizes_capital_and_cost_diagnostics(tmp_path: Path):
    graph = ResearchTaskGraph(tmp_path / "tasks.db")
    cost = graph.add(
        ResearchTask(
            task_type="cost_regime_evaluation",
            strategy_version="challenger-v1",
            payload={"hypothesis_code": "DRAWDOWN_CONTROL"},
        )
    )
    sunday = graph.add(
        ResearchTask(task_type="sunday_validation", strategy_version="challenger-v1")
    )

    policy = ResearchPriorityPolicy()
    changed = policy.apply(
        graph,
        report(
            FirmHealthStatus.HALT,
            "maximum drawdown reached halt threshold",
            "execution costs are degrading realized edge",
        ),
    )

    assert changed == 2
    assert graph.get(cost.id).priority == 100
    assert graph.get(sunday.id).priority == 85
    assert graph.claim_next().id == cost.id


def test_policy_does_not_reprioritize_running_task(tmp_path: Path):
    graph = ResearchTaskGraph(tmp_path / "tasks.db")
    task = graph.add(
        ResearchTask(task_type="backtest_campaign", strategy_version="v1", priority=40)
    )
    assert graph.claim_next().id == task.id

    changed = ResearchPriorityPolicy().apply(
        graph,
        report(FirmHealthStatus.HALT, "account capital is not growing"),
    )

    assert changed == 0
    assert graph.get(task.id).priority == 40


def test_existing_database_is_migrated_without_losing_tasks(tmp_path: Path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE research_tasks (
                id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                strategy_version TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                depends_json TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL,
                max_attempts INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_error TEXT
            )
            """
        )
        connection.execute(
            """
            INSERT INTO research_tasks VALUES (
                '00000000-0000-0000-0000-000000000001', 'legacy', 'v0', '{}', '[]',
                'pending', 0, 3, '2026-08-25T00:00:00+00:00',
                '2026-08-25T00:00:00+00:00', NULL
            )
            """
        )

    graph = ResearchTaskGraph(path)
    tasks = graph.all()

    assert len(tasks) == 1
    assert tasks[0].task_type == "legacy"
    assert tasks[0].priority == 50
