from datetime import UTC, datetime

from dusty_dragon.analytics.performance import FirmPerformanceSummary
from dusty_dragon.research.challenger_worker import ChallengerResearchWorker
from dusty_dragon.research.pipeline import DurableChallengerResearchPipeline
from dusty_dragon.research.task_graph import ResearchTaskGraph, ResearchTaskStatus
from dusty_dragon.research.weekend import ResearchPriority, WeekendResearchBrief
from dusty_dragon.scheduler.weekly_clock import FirmPhase
from dusty_dragon.storage.strategy_registry import StrategyRegistry


def brief(*, eligible: bool = True) -> WeekendResearchBrief:
    return WeekendResearchBrief(
        generated_at=datetime(2026, 8, 29, 12, tzinfo=UTC),
        phase=FirmPhase.WEEKEND_RESEARCH,
        strategy_version="generalist-v0",
        performance=FirmPerformanceSummary(
            trade_count=30,
            wins=14,
            losses=16,
            flats=0,
            win_rate=14 / 30,
            total_r=-1.0,
            expectancy_r=-1 / 30,
            profit_factor_r=0.9,
            max_drawdown_r=3.0,
            forecast_samples=20,
            forecast_direction_accuracy=0.40,
            mean_forecast_error_pct=0.2,
        ),
        priorities=[
            ResearchPriority(
                code="KRONOS_DIRECTION_CALIBRATION",
                severity="high",
                explanation="test horizon and weighting",
            )
        ],
        eligible_for_challenger_research=eligible,
    )


def test_pipeline_creates_durable_dependency_chain_per_challenger(tmp_path):
    registry = StrategyRegistry(tmp_path / "strategies.sqlite3")
    graph = ResearchTaskGraph(tmp_path / "research.sqlite3")
    champion = registry.register_founder(
        "generalist-v0",
        {
            "signals": {"kronos_weight": 0.40, "minimum_confidence": 0.55},
            "kronos": {"horizon_bars": 4},
            "risk": {"risk_pct": 0.25},
        },
    )
    pipeline = DurableChallengerResearchPipeline(
        ChallengerResearchWorker(registry, maximum_challengers=2),
        graph,
        runs_per_symbol=12,
    )

    plan = pipeline.plan(champion=champion, brief=brief())

    assert plan.eligible is True
    assert len(plan.chains) == 2
    assert len(graph.all()) == 8
    assert registry.champion().id == champion.id

    chain = plan.chains[0]
    tasks = [graph.get(task_id) for task_id in chain.task_ids]
    assert [task.task_type for task in tasks if task is not None] == [
        "backtest_campaign",
        "cost_regime_evaluation",
        "champion_comparison",
        "sunday_validation",
    ]
    assert tasks[0].payload["runs_per_symbol"] == 12
    assert tasks[0].payload["prior_week_min"] == 1
    assert tasks[0].payload["prior_week_max"] == 8
    assert tasks[3].payload["promotion_authority"] is False
    assert tasks[1].depends_on == [tasks[0].id]
    assert tasks[2].depends_on == [tasks[1].id]
    assert tasks[3].depends_on == [tasks[2].id]


def test_pipeline_dependency_chain_releases_one_stage_at_a_time(tmp_path):
    registry = StrategyRegistry(tmp_path / "strategies.sqlite3")
    graph = ResearchTaskGraph(tmp_path / "research.sqlite3")
    champion = registry.register_founder("generalist-v0", {"signals": {}})
    pipeline = DurableChallengerResearchPipeline(
        ChallengerResearchWorker(registry, maximum_challengers=1),
        graph,
    )
    plan = pipeline.plan(champion=champion, brief=brief())
    chain = plan.chains[0]

    first = graph.claim_next()
    assert first is not None
    assert first.id == chain.task_ids[0]
    assert first.status == ResearchTaskStatus.RUNNING
    assert graph.claim_next() is None

    graph.succeed(first.id)
    second = graph.claim_next()
    assert second is not None
    assert second.id == chain.task_ids[1]


def test_pipeline_does_not_enqueue_without_research_eligibility(tmp_path):
    registry = StrategyRegistry(tmp_path / "strategies.sqlite3")
    graph = ResearchTaskGraph(tmp_path / "research.sqlite3")
    champion = registry.register_founder("generalist-v0", {"signals": {}})
    pipeline = DurableChallengerResearchPipeline(ChallengerResearchWorker(registry), graph)

    plan = pipeline.plan(champion=champion, brief=brief(eligible=False))

    assert plan.eligible is False
    assert plan.chains == []
    assert graph.all() == []
    assert registry.children(champion.id) == []


def test_pipeline_rejects_campaign_sizes_outside_governed_range(tmp_path):
    registry = StrategyRegistry(tmp_path / "strategies.sqlite3")
    graph = ResearchTaskGraph(tmp_path / "research.sqlite3")
    worker = ChallengerResearchWorker(registry)

    for invalid in (9, 21):
        try:
            DurableChallengerResearchPipeline(worker, graph, runs_per_symbol=invalid)
        except ValueError as exc:
            assert "between 10 and 20" in str(exc)
        else:
            raise AssertionError("invalid campaign size should be rejected")
