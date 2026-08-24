from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from dusty_dragon.analytics.performance import FirmPerformanceAnalyzer
from dusty_dragon.domain.trades import Side
from dusty_dragon.learning.outcomes import OutcomeClass, TradeOutcome
from dusty_dragon.research.weekend import WeekendResearchService
from dusty_dragon.scheduler.weekly_clock import FirmPhase
from dusty_dragon.storage.outcome_store import TradeOutcomeStore


def make_outcome(index: int, realized_r: float, forecast_correct: bool) -> TradeOutcome:
    outcome_class = OutcomeClass.WIN if realized_r > 0 else OutcomeClass.LOSS
    return TradeOutcome(
        trade_id=uuid4(),
        closed_at=datetime(2026, 8, 24, tzinfo=UTC) + timedelta(hours=index),
        symbol="EURUSD",
        side=Side.BUY,
        strategy_version="generalist-v0",
        entry_price=1.1000,
        exit_price=1.1010,
        stop_loss=1.0950,
        gross_return_pct=0.1,
        realized_r=realized_r,
        outcome_class=outcome_class,
        forecast_return_pct=0.2,
        forecast_error_pct=-0.1,
        forecast_direction_correct=forecast_correct,
    )


def service(tmp_path, *, minimum: int = 20) -> WeekendResearchService:
    store = TradeOutcomeStore(tmp_path / "outcomes.sqlite3")
    return WeekendResearchService(
        outcome_store=store,
        analyzer=FirmPerformanceAnalyzer(),
        minimum_outcomes_for_research=minimum,
    )


def test_empty_weekend_brief_does_not_invent_research_edge(tmp_path):
    research = service(tmp_path)

    brief = research.run(
        phase=FirmPhase.WEEKEND_RESEARCH,
        observed_at=datetime(2026, 8, 29, 12, tzinfo=UTC),
    )

    assert brief.performance.trade_count == 0
    assert brief.eligible_for_challenger_research is False
    assert brief.priorities[0].code == "INSUFFICIENT_OUTCOMES"


def test_evidence_threshold_unlocks_challenger_research_and_flags_failures(tmp_path):
    research = service(tmp_path, minimum=20)
    for index in range(20):
        research.outcome_store.append(
            make_outcome(index, realized_r=-0.5, forecast_correct=index < 8)
        )

    brief = research.run(
        phase=FirmPhase.WEEKEND_RESEARCH,
        observed_at=datetime(2026, 8, 29, 12, tzinfo=UTC),
    )
    codes = {priority.code for priority in brief.priorities}

    assert brief.eligible_for_challenger_research is True
    assert "NONPOSITIVE_EXPECTANCY" in codes
    assert "KRONOS_DIRECTION_CALIBRATION" in codes
    assert "DRAWDOWN_CONTROL" in codes


def test_trading_phase_cannot_run_weekend_research(tmp_path):
    research = service(tmp_path)

    with pytest.raises(ValueError, match="outside trading phase"):
        research.run(
            phase=FirmPhase.TRADING,
            observed_at=datetime(2026, 8, 24, 12, tzinfo=UTC),
        )
