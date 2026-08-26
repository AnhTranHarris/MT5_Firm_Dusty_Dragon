from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from dusty_dragon.brokers.reconciliation import ReconciliationStatus


class BrokerHealthState(StrEnum):
    HEALTHY = "HEALTHY"
    WATCH = "WATCH"
    RESTRICTED = "RESTRICTED"
    HALTED = "HALTED"


@dataclass(frozen=True, slots=True)
class BrokerHealthPolicy:
    drift_watch_count: int
    drift_restrict_count: int
    drift_halt_count: int
    invalid_halts_immediately: bool
    match_resets_drift_count: bool

    def __post_init__(self) -> None:
        if not (
            1 <= self.drift_watch_count < self.drift_restrict_count < self.drift_halt_count
        ):
            raise ValueError("broker health drift thresholds must be strictly increasing")

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> BrokerHealthPolicy:
        return cls(
            drift_watch_count=int(raw["drift_watch_count"]),
            drift_restrict_count=int(raw["drift_restrict_count"]),
            drift_halt_count=int(raw["drift_halt_count"]),
            invalid_halts_immediately=bool(raw["invalid_halts_immediately"]),
            match_resets_drift_count=bool(raw["match_resets_drift_count"]),
        )


@dataclass(frozen=True, slots=True)
class BrokerHealthSnapshot:
    state: BrokerHealthState
    consecutive_drift_count: int
    safe_for_new_orders: bool


class BrokerHealthMonitor:
    """Escalate repeated broker reconciliation failures without changing broker state."""

    def __init__(self, policy: BrokerHealthPolicy) -> None:
        self._policy = policy
        self._consecutive_drift_count = 0
        self._state = BrokerHealthState.HEALTHY

    def observe(self, status: ReconciliationStatus) -> BrokerHealthSnapshot:
        if status is ReconciliationStatus.MATCH:
            if self._policy.match_resets_drift_count:
                self._consecutive_drift_count = 0
            self._state = BrokerHealthState.HEALTHY
        elif status is ReconciliationStatus.INVALID:
            self._consecutive_drift_count += 1
            if self._policy.invalid_halts_immediately:
                self._state = BrokerHealthState.HALTED
            else:
                self._state = self._state_for_drift_count(self._consecutive_drift_count)
        else:
            self._consecutive_drift_count += 1
            self._state = self._state_for_drift_count(self._consecutive_drift_count)

        return BrokerHealthSnapshot(
            state=self._state,
            consecutive_drift_count=self._consecutive_drift_count,
            safe_for_new_orders=self._state is BrokerHealthState.HEALTHY,
        )

    def _state_for_drift_count(self, count: int) -> BrokerHealthState:
        if count >= self._policy.drift_halt_count:
            return BrokerHealthState.HALTED
        if count >= self._policy.drift_restrict_count:
            return BrokerHealthState.RESTRICTED
        if count >= self._policy.drift_watch_count:
            return BrokerHealthState.WATCH
        return BrokerHealthState.HEALTHY
