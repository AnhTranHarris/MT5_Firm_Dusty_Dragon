from datetime import UTC, datetime

import pytest

from dusty_dragon.performance import (
    CapitalFlowObservation,
    EquityObservation,
    build_time_weighted_curve,
)


def at(day: int) -> datetime:
    return datetime(2026, 8, day, 12, tzinfo=UTC)


def test_curve_excludes_external_deposit_from_trading_return() -> None:
    observations = (
        EquityObservation(at(1), equity=10_000.0, balance=10_000.0),
        EquityObservation(at(2), equity=10_500.0, balance=10_500.0),
        EquityObservation(at(3), equity=15_750.0, balance=15_750.0),
    )
    flows = (
        CapitalFlowObservation(at(3), amount=5_000.0, reference="owner-deposit"),
    )

    curve = build_time_weighted_curve(observations, flows)

    assert curve[0].cumulative_return_pct == pytest.approx(0.0)
    assert curve[1].cumulative_return_pct == pytest.approx(5.0)
    # Day 3 contains a $5k deposit plus another 2.38095% trading gain.
    assert curve[2].cumulative_return_pct == pytest.approx(7.5)


def test_curve_handles_withdrawal_without_reporting_false_loss() -> None:
    observations = (
        EquityObservation(at(1), equity=10_000.0, balance=10_000.0),
        EquityObservation(at(2), equity=9_500.0, balance=9_500.0),
    )
    flows = (
        CapitalFlowObservation(at(2), amount=-500.0, reference="owner-withdrawal"),
    )

    curve = build_time_weighted_curve(observations, flows)

    assert curve[-1].cumulative_return_pct == pytest.approx(0.0)


def test_curve_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        EquityObservation(
            datetime(2026, 8, 1, 12),
            equity=10_000.0,
            balance=10_000.0,
        )


def test_curve_rejects_duplicate_observation_timestamps() -> None:
    observations = (
        EquityObservation(at(1), equity=10_000.0, balance=10_000.0),
        EquityObservation(at(1), equity=10_100.0, balance=10_100.0),
    )

    with pytest.raises(ValueError, match="unique timestamps"):
        build_time_weighted_curve(observations)
