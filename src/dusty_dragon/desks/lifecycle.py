from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DeskLifecycleState(StrEnum):
    NEW = "NEW"
    BOOTSTRAPPING = "BOOTSTRAPPING"
    INTRADAY = "INTRADAY"
    HOLD_2D = "HOLD_2D"
    MULTIDAY = "MULTIDAY"
    WEEKLY = "WEEKLY"
    MULTIWEEK = "MULTIWEEK"
    CAUTION = "CAUTION"
    DEFENSIVE = "DEFENSIVE"
    HALTED = "HALTED"
    QUARANTINED = "QUARANTINED"
    REHABILITATING = "REHABILITATING"
    REQUALIFYING = "REQUALIFYING"
    RETIRED = "RETIRED"


_GRADUATION_STATES = (
    DeskLifecycleState.INTRADAY,
    DeskLifecycleState.HOLD_2D,
    DeskLifecycleState.MULTIDAY,
    DeskLifecycleState.WEEKLY,
    DeskLifecycleState.MULTIWEEK,
)

_ALLOWED_TRANSITIONS: dict[DeskLifecycleState, frozenset[DeskLifecycleState]] = {
    DeskLifecycleState.NEW: frozenset(
        {DeskLifecycleState.BOOTSTRAPPING, DeskLifecycleState.RETIRED}
    ),
    DeskLifecycleState.BOOTSTRAPPING: frozenset(
        {DeskLifecycleState.INTRADAY, DeskLifecycleState.HALTED, DeskLifecycleState.RETIRED}
    ),
    DeskLifecycleState.INTRADAY: frozenset(
        {
            DeskLifecycleState.HOLD_2D,
            DeskLifecycleState.CAUTION,
            DeskLifecycleState.HALTED,
            DeskLifecycleState.QUARANTINED,
            DeskLifecycleState.RETIRED,
        }
    ),
    DeskLifecycleState.HOLD_2D: frozenset(
        {
            DeskLifecycleState.MULTIDAY,
            DeskLifecycleState.CAUTION,
            DeskLifecycleState.HALTED,
            DeskLifecycleState.QUARANTINED,
            DeskLifecycleState.RETIRED,
        }
    ),
    DeskLifecycleState.MULTIDAY: frozenset(
        {
            DeskLifecycleState.WEEKLY,
            DeskLifecycleState.CAUTION,
            DeskLifecycleState.HALTED,
            DeskLifecycleState.QUARANTINED,
            DeskLifecycleState.RETIRED,
        }
    ),
    DeskLifecycleState.WEEKLY: frozenset(
        {
            DeskLifecycleState.MULTIWEEK,
            DeskLifecycleState.CAUTION,
            DeskLifecycleState.HALTED,
            DeskLifecycleState.QUARANTINED,
            DeskLifecycleState.RETIRED,
        }
    ),
    DeskLifecycleState.MULTIWEEK: frozenset(
        {
            DeskLifecycleState.CAUTION,
            DeskLifecycleState.HALTED,
            DeskLifecycleState.QUARANTINED,
            DeskLifecycleState.RETIRED,
        }
    ),
    DeskLifecycleState.CAUTION: frozenset(
        {
            DeskLifecycleState.DEFENSIVE,
            DeskLifecycleState.REQUALIFYING,
            DeskLifecycleState.HALTED,
            DeskLifecycleState.QUARANTINED,
            DeskLifecycleState.RETIRED,
        }
    ),
    DeskLifecycleState.DEFENSIVE: frozenset(
        {
            DeskLifecycleState.REQUALIFYING,
            DeskLifecycleState.HALTED,
            DeskLifecycleState.QUARANTINED,
            DeskLifecycleState.RETIRED,
        }
    ),
    DeskLifecycleState.HALTED: frozenset(
        {
            DeskLifecycleState.REQUALIFYING,
            DeskLifecycleState.QUARANTINED,
            DeskLifecycleState.RETIRED,
        }
    ),
    DeskLifecycleState.QUARANTINED: frozenset(
        {DeskLifecycleState.REHABILITATING, DeskLifecycleState.RETIRED}
    ),
    DeskLifecycleState.REHABILITATING: frozenset(
        {DeskLifecycleState.REQUALIFYING, DeskLifecycleState.RETIRED}
    ),
    DeskLifecycleState.REQUALIFYING: frozenset(
        {DeskLifecycleState.INTRADAY, DeskLifecycleState.HALTED, DeskLifecycleState.RETIRED}
    ),
    DeskLifecycleState.RETIRED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class DeskLifecycle:
    desk_id: str
    state: DeskLifecycleState

    def transition(self, target: DeskLifecycleState) -> "DeskLifecycle":
        if target not in _ALLOWED_TRANSITIONS[self.state]:
            raise ValueError(f"invalid desk lifecycle transition: {self.state} -> {target}")
        return DeskLifecycle(desk_id=self.desk_id, state=target)

    @property
    def may_add_new_risk(self) -> bool:
        return self.state in _GRADUATION_STATES

    @property
    def graduation_rank(self) -> int | None:
        try:
            return _GRADUATION_STATES.index(self.state)
        except ValueError:
            return None
