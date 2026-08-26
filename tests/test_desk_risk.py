from pathlib import Path

import pytest

from dusty_dragon.policies.loader import load_policy
from dusty_dragon.risk.desk import (
    DailyRiskAction,
    DeskRiskGovernor,
    DeskRiskPolicy,
    DeskRiskSnapshot,
    WeeklyRiskState,
)


def governor() -> DeskRiskGovernor:
    bundle = load_policy(Path("policies/financial_v1.toml"))
    return DeskRiskGovernor(DeskRiskPolicy.from_mapping(bundle.desk))


def test_risk_policy_loads_from_versioned_financial_policy() -> None:
    bundle = load_policy(Path("policies/financial_v1.toml"))
    policy = DeskRiskPolicy.from_mapping(bundle.desk)

    assert policy.per_trade_risk_min == 0.01
    assert policy.per_trade_risk_max == 0.02
    assert policy.weekly_catastrophic_drawdown == 0.25


def test_invalid_risk_snapshot_fraction_fails_closed() -> None:
    with pytest.raises(ValueError):
        DeskRiskSnapshot(
            requested_trade_risk=0.01,
            active_exposure=0.20,
            daily_loss_fraction=-0.01,
            weekly_drawdown_fraction=0.0,
        )


def test_normal_risk_state_allows_new_risk() -> None:
    decision = governor().evaluate(
        DeskRiskSnapshot(
            requested_trade_risk=0.01,
            active_exposure=0.20,
            daily_loss_fraction=0.01,
            weekly_drawdown_fraction=0.02,
        )
    )

    assert decision.weekly_state is WeeklyRiskState.NORMAL
    assert decision.daily_action is DailyRiskAction.NORMAL
    assert decision.may_add_new_risk is True


def test_daily_normal_loss_threshold_blocks_new_risk() -> None:
    decision = governor().evaluate(
        DeskRiskSnapshot(
            requested_trade_risk=0.01,
            active_exposure=0.20,
            daily_loss_fraction=0.03,
            weekly_drawdown_fraction=0.02,
        )
    )

    assert decision.daily_action is DailyRiskAction.BLOCK_NEW_RISK
    assert decision.may_add_new_risk is False


def test_daily_emergency_threshold_halts() -> None:
    decision = governor().evaluate(
        DeskRiskSnapshot(
            requested_trade_risk=0.01,
            active_exposure=0.20,
            daily_loss_fraction=0.05,
            weekly_drawdown_fraction=0.02,
        )
    )

    assert decision.daily_action is DailyRiskAction.EMERGENCY_HALT
    assert decision.may_add_new_risk is False


@pytest.mark.parametrize(
    ("drawdown", "expected"),
    [
        (0.05, WeeklyRiskState.CAUTION),
        (0.08, WeeklyRiskState.DEFENSIVE),
        (0.10, WeeklyRiskState.HALT),
        (0.25, WeeklyRiskState.QUARANTINE),
    ],
)
def test_weekly_drawdown_state_boundaries(drawdown: float, expected: WeeklyRiskState) -> None:
    decision = governor().evaluate(
        DeskRiskSnapshot(
            requested_trade_risk=0.01,
            active_exposure=0.20,
            daily_loss_fraction=0.0,
            weekly_drawdown_fraction=drawdown,
        )
    )

    assert decision.weekly_state is expected


def test_defensive_or_worse_blocks_incremental_risk() -> None:
    decision = governor().evaluate(
        DeskRiskSnapshot(
            requested_trade_risk=0.01,
            active_exposure=0.20,
            daily_loss_fraction=0.0,
            weekly_drawdown_fraction=0.08,
        )
    )

    assert decision.weekly_state is WeeklyRiskState.DEFENSIVE
    assert decision.may_add_new_risk is False


def test_trade_risk_above_graduation_ceiling_is_rejected() -> None:
    decision = governor().evaluate(
        DeskRiskSnapshot(
            requested_trade_risk=0.021,
            active_exposure=0.20,
            daily_loss_fraction=0.0,
            weekly_drawdown_fraction=0.0,
        )
    )

    assert decision.trade_risk_compliant is False
    assert decision.may_add_new_risk is False


def test_exposure_above_policy_maximum_is_rejected() -> None:
    decision = governor().evaluate(
        DeskRiskSnapshot(
            requested_trade_risk=0.01,
            active_exposure=0.301,
            daily_loss_fraction=0.0,
            weekly_drawdown_fraction=0.0,
        )
    )

    assert decision.exposure_compliant is False
    assert decision.may_add_new_risk is False
