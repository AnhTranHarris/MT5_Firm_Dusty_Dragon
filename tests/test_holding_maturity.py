import pytest

from dusty_dragon.learning.holding_maturity import (
    HoldingMaturityEngine,
    HoldingStage,
    MaturityPolicy,
    StageTradeAssessment,
    TradeQuality,
)


def accepted(stage: HoldingStage, pnl: float = 1.0) -> StageTradeAssessment:
    return StageTradeAssessment(stage=stage, pnl=pnl, quality=TradeQuality.ACCEPTED)


def test_intraday_is_initially_authorized():
    engine = HoldingMaturityEngine()

    assert engine.states[HoldingStage.INTRADAY].authorized is True
    assert engine.states[HoldingStage.OVERNIGHT].authorized is False


def test_stage_graduates_at_target_with_85_percent_acceptance():
    engine = HoldingMaturityEngine(policy=MaturityPolicy(qualification_target=20))

    for _ in range(17):
        engine.record(accepted(HoldingStage.INTRADAY))
    for _ in range(3):
        engine.record(
            StageTradeAssessment(
                stage=HoldingStage.INTRADAY,
                pnl=-0.2,
                quality=TradeQuality.MARGINAL,
            )
        )

    assert engine.states[HoldingStage.INTRADAY].qualified is True
    assert engine.states[HoldingStage.OVERNIGHT].authorized is True


def test_catastrophic_trade_resets_current_stage_progress_only():
    engine = HoldingMaturityEngine(policy=MaturityPolicy(qualification_target=100))
    for _ in range(10):
        engine.record(accepted(HoldingStage.INTRADAY))

    engine.record(
        StageTradeAssessment(
            stage=HoldingStage.INTRADAY,
            pnl=-5.0,
            quality=TradeQuality.FAILED,
            destroyed_gain_fraction=0.50,
        )
    )

    state = engine.states[HoldingStage.INTRADAY]
    assert state.qualification_trades == 0
    assert state.accepted_trades == 0
    assert state.probation is True
    assert state.authorized is True


def test_fifty_consecutive_acceptable_losses_trigger_demotion():
    engine = HoldingMaturityEngine(policy=MaturityPolicy(qualification_target=1))
    engine.record(accepted(HoldingStage.INTRADAY))
    assert engine.states[HoldingStage.OVERNIGHT].authorized is True

    for _ in range(49):
        engine.record(accepted(HoldingStage.OVERNIGHT, pnl=-0.1))
    engine.record(accepted(HoldingStage.OVERNIGHT, pnl=-0.1))

    assert engine.states[HoldingStage.OVERNIGHT].authorized is False
    assert engine.states[HoldingStage.INTRADAY].authorized is True
    assert engine.states[HoldingStage.INTRADAY].qualified is False
    assert engine.states[HoldingStage.INTRADAY].probation is True


def test_majority_unacceptable_losses_trigger_demotion():
    engine = HoldingMaturityEngine(policy=MaturityPolicy(qualification_target=1))
    engine.record(accepted(HoldingStage.INTRADAY))

    for _ in range(24):
        engine.record(accepted(HoldingStage.OVERNIGHT, pnl=0.2))
    for index in range(26):
        engine.record(
            StageTradeAssessment(
                stage=HoldingStage.OVERNIGHT,
                pnl=-0.1,
                quality=(
                    TradeQuality.ACCEPTED if index < 12 else TradeQuality.FAILED
                ),
            )
        )

    assert engine.states[HoldingStage.OVERNIGHT].authorized is False


def test_negative_capital_window_triggers_demotion():
    engine = HoldingMaturityEngine(policy=MaturityPolicy(qualification_target=1))
    engine.record(accepted(HoldingStage.INTRADAY))

    for _ in range(25):
        engine.record(accepted(HoldingStage.OVERNIGHT, pnl=0.1))
    for _ in range(25):
        engine.record(accepted(HoldingStage.OVERNIGHT, pnl=-0.2))

    assert engine.states[HoldingStage.OVERNIGHT].authorized is False


def test_unauthorized_stage_cannot_record_trades():
    engine = HoldingMaturityEngine()

    with pytest.raises(PermissionError):
        engine.record(accepted(HoldingStage.WEEKLY))
