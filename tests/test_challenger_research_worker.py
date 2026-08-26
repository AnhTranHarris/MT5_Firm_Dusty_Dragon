from datetime import UTC, datetime

from dusty_dragon.analytics.performance import FirmPerformanceSummary
from dusty_dragon.research.challenger_worker import ChallengerResearchWorker
from dusty_dragon.research.factors import FactorSnapshot
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


def test_worker_creates_bounded_descendants_without_promoting(tmp_path):
    registry = StrategyRegistry(tmp_path / "strategies.sqlite3")
    champion = registry.register_founder(
        "generalist-v0",
        {
            "signals": {"kronos_weight": 0.40, "minimum_confidence": 0.55},
            "kronos": {"horizon_bars": 4},
            "risk": {"risk_pct": 0.25},
        },
    )
    snapshot = FactorSnapshot(
        symbol="EURUSD",
        timeframe="M15",
        trend_return_pct=0.2,
        momentum_return_pct=0.05,
        realized_volatility_pct=0.08,
        mean_reversion_zscore=1.2,
        average_spread_points=8.0,
        regime="trend_high_vol",
    )

    result = ChallengerResearchWorker(registry, maximum_challengers=3).run(
        champion=champion,
        brief=brief(),
        factor_snapshot=snapshot,
    )

    assert result.eligible is True
    assert len(result.challengers) == 3
    assert registry.champion().id == champion.id
    assert all(challenger.parent_id == champion.id for challenger in result.challengers)
    assert all(challenger.status.value == "challenger" for challenger in result.challengers)
    assert result.challengers[0].config["signals"]["kronos_weight"] == 0.25


def test_worker_does_nothing_without_evidence_eligibility(tmp_path):
    registry = StrategyRegistry(tmp_path / "strategies.sqlite3")
    champion = registry.register_founder("generalist-v0", {"signals": {}})

    result = ChallengerResearchWorker(registry).run(
        champion=champion,
        brief=brief(eligible=False),
    )

    assert result.eligible is False
    assert result.challengers == []
    assert registry.children(champion.id) == []
