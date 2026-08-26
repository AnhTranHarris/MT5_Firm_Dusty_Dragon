from __future__ import annotations

import pytest

from dusty_dragon.desks.lifecycle import DeskLifecycle, DeskLifecycleState


def test_desk_graduation_progression_is_sequential() -> None:
    desk = DeskLifecycle("GENERALIST-01", DeskLifecycleState.NEW)
    desk = desk.transition(DeskLifecycleState.BOOTSTRAPPING)
    desk = desk.transition(DeskLifecycleState.INTRADAY)
    assert desk.may_add_new_risk
    assert desk.graduation_rank == 0

    with pytest.raises(ValueError, match="invalid desk lifecycle transition"):
        desk.transition(DeskLifecycleState.MULTIDAY)

    desk = desk.transition(DeskLifecycleState.HOLD_2D)
    desk = desk.transition(DeskLifecycleState.MULTIDAY)
    assert desk.graduation_rank == 2


def test_quarantine_requires_rehabilitation_and_requalification() -> None:
    desk = DeskLifecycle("GENERALIST-01", DeskLifecycleState.INTRADAY)
    desk = desk.transition(DeskLifecycleState.QUARANTINED)
    assert not desk.may_add_new_risk

    with pytest.raises(ValueError, match="invalid desk lifecycle transition"):
        desk.transition(DeskLifecycleState.INTRADAY)

    desk = desk.transition(DeskLifecycleState.REHABILITATING)
    desk = desk.transition(DeskLifecycleState.REQUALIFYING)
    desk = desk.transition(DeskLifecycleState.INTRADAY)
    assert desk.may_add_new_risk
    assert desk.graduation_rank == 0


def test_halted_or_defensive_desks_cannot_add_new_risk() -> None:
    for state in (
        DeskLifecycleState.CAUTION,
        DeskLifecycleState.DEFENSIVE,
        DeskLifecycleState.HALTED,
        DeskLifecycleState.QUARANTINED,
        DeskLifecycleState.REHABILITATING,
        DeskLifecycleState.REQUALIFYING,
    ):
        assert not DeskLifecycle("GENERALIST-01", state).may_add_new_risk
