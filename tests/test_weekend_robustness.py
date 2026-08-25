from datetime import UTC, datetime
from uuid import uuid4

from dusty_dragon.analytics.performance import FirmPerformanceAnalyzer
from dusty_dragon.backtest.weekend_protocol import WeekendExperimentResult, WeekendProtocolResult
from dusty_dragon.backtest.walk_forward import WalkForwardResult
from dusty_dragon.learning.outcomes import OutcomeClass, TradeOutcome
from dusty_dragon.research.weekend import WeekendResearchService
from dusty_dragon.scheduler.weekly_clock import FirmPhase
from dusty_dragon.storage.outcome_store import TradeOutcomeStore
from dusty_dragon.domain.trades import Side


def experiment(kind: str, symbol: str, mean_return: float):
    now = datetime(2026, 8, 23, tzinfo=UTC)
    return WeekendExperimentResult(
        experiment_type=kind,
        source_symbol="EURUSD",
        tested_symbol=symbol,
        reference_started_at=now,
        reference_ended_at=now,
        random_seed=1,
        walk_forward=WalkForwardResult(
            windows=10,
            trade_signals=5,
            abstentions=5,
            directional_wins=3,
            directional_losses=2,
            directional_accuracy=0.6,
            mean_signed_return_pct=mean_return,
        ),
    )


def seed_outcome(store: TradeOutcomeStore):
    store.append(
        TradeOutcome(
            trade_id=uuid4(),
            symbol="EURUSD",
            side=Side.BUY,
            strategy_version="generalist-v0",
            entry_price=1.10,
            exit_price=1.11,
            stop_loss=1.09,
            gross_return_pct=0.9,
            realized_r=1.0,
            outcome_class=OutcomeClass.WIN,
        )
    )


def test_overfit_risk_is_flagged(tmp_path):
    store = TradeOutcomeStore(tmp_path / "outcomes.sqlite3")
    seed_outcome(store)
    protocol = WeekendProtocolResult(
        random_seed=1,
        cross_symbol_results=[experiment("cross_symbol", "GBPUSD", -0.1)],
        prior_week_results=[experiment("prior_week_replay", "EURUSD", -0.1)],
    )
    service = WeekendResearchService(store, FirmPerformanceAnalyzer())

    brief = service.run(
        phase=FirmPhase.WEEKEND_RESEARCH,
        observed_at=datetime(2026, 8, 29, 12, tzinfo=UTC),
        protocol_result=protocol,
    )

    assert brief.robustness is not None
    assert brief.robustness.classification == "overfit_risk"
    assert "OVERFIT_RISK" in {priority.code for priority in brief.priorities}


def test_generalizing_results_do_not_create_overfit_priority(tmp_path):
    store = TradeOutcomeStore(tmp_path / "outcomes.sqlite3")
    seed_outcome(store)
    protocol = WeekendProtocolResult(
        random_seed=2,
        cross_symbol_results=[experiment("cross_symbol", "GBPUSD", 0.1)],
        prior_week_results=[experiment("prior_week_replay", "EURUSD", 0.1)],
    )
    service = WeekendResearchService(store, FirmPerformanceAnalyzer())

    brief = service.run(
        phase=FirmPhase.SUNDAY_VALIDATION,
        observed_at=datetime(2026, 8, 30, 15, tzinfo=UTC),
        protocol_result=protocol,
    )

    assert brief.robustness is not None
    assert brief.robustness.classification == "generalizing"
    assert "OVERFIT_RISK" not in {priority.code for priority in brief.priorities}
