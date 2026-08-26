from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class WeeklyRiskState(StrEnum):
    NORMAL = "NORMAL"
    CAUTION = "CAUTION"
    DEFENSIVE = "DEFENSIVE"
    HALT = "HALT"
    QUARANTINE = "QUARANTINE"


class DailyRiskAction(StrEnum):
    NORMAL = "NORMAL"
    BLOCK_NEW_RISK = "BLOCK_NEW_RISK"
    EMERGENCY_HALT = "EMERGENCY_HALT"


@dataclass(frozen=True, slots=True)
class DeskRiskPolicy:
    per_trade_risk_min: float
    per_trade_risk_max: float
    daily_loss_normal: float
    daily_loss_emergency: float
    active_exposure_max: float
    weekly_caution_drawdown: float
    weekly_defensive_drawdown: float
    weekly_halt_drawdown: float
    weekly_catastrophic_drawdown: float

    def __post_init__(self) -> None:
        fractions = (
            self.per_trade_risk_min,
            self.per_trade_risk_max,
            self.daily_loss_normal,
            self.daily_loss_emergency,
            self.active_exposure_max,
            self.weekly_caution_drawdown,
            self.weekly_defensive_drawdown,
            self.weekly_halt_drawdown,
            self.weekly_catastrophic_drawdown,
        )
        if any(not 0.0 <= value <= 1.0 for value in fractions):
            raise ValueError("risk policy fractions must be between 0 and 1")
        if not 0.0 < self.per_trade_risk_min <= self.per_trade_risk_max:
            raise ValueError("per-trade risk bounds are invalid")
        if not self.daily_loss_normal < self.daily_loss_emergency:
            raise ValueError("daily loss thresholds must be strictly increasing")
        if not (
            self.weekly_caution_drawdown
            < self.weekly_defensive_drawdown
            < self.weekly_halt_drawdown
            < self.weekly_catastrophic_drawdown
        ):
            raise ValueError("weekly drawdown thresholds must be strictly increasing")

    @classmethod
    def from_mapping(cls, desk: Mapping[str, Any]) -> DeskRiskPolicy:
        return cls(
            per_trade_risk_min=float(desk["per_trade_risk_min"]),
            per_trade_risk_max=float(desk["per_trade_risk_max"]),
            daily_loss_normal=float(desk["daily_loss_normal"]),
            daily_loss_emergency=float(desk["daily_loss_emergency"]),
            active_exposure_max=float(desk["active_exposure_max"]),
            weekly_caution_drawdown=float(desk["weekly_caution_drawdown"]),
            weekly_defensive_drawdown=float(desk["weekly_defensive_drawdown_low"]),
            weekly_halt_drawdown=float(desk["weekly_halt_drawdown_low"]),
            weekly_catastrophic_drawdown=float(desk["weekly_catastrophic_drawdown"]),
        )


@dataclass(frozen=True, slots=True)
class DeskRiskSnapshot:
    requested_trade_risk: float
    active_exposure: float
    daily_loss_fraction: float
    weekly_drawdown_fraction: float

    def __post_init__(self) -> None:
        for name, value in (
            ("requested_trade_risk", self.requested_trade_risk),
            ("active_exposure", self.active_exposure),
            ("daily_loss_fraction", self.daily_loss_fraction),
            ("weekly_drawdown_fraction", self.weekly_drawdown_fraction),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class DeskRiskDecision:
    weekly_state: WeeklyRiskState
    daily_action: DailyRiskAction
    trade_risk_compliant: bool
    exposure_compliant: bool
    may_add_new_risk: bool
    reasons: tuple[str, ...]


class DeskRiskGovernor:
    def __init__(self, policy: DeskRiskPolicy) -> None:
        self._policy = policy

    def evaluate(self, snapshot: DeskRiskSnapshot) -> DeskRiskDecision:
        weekly_state = self._weekly_state(snapshot.weekly_drawdown_fraction)
        daily_action = self._daily_action(snapshot.daily_loss_fraction)
        trade_risk_compliant = (
            self._policy.per_trade_risk_min
            <= snapshot.requested_trade_risk
            <= self._policy.per_trade_risk_max
        )
        exposure_compliant = snapshot.active_exposure <= self._policy.active_exposure_max

        reasons: list[str] = []
        if not trade_risk_compliant:
            reasons.append("requested trade risk is outside policy bounds")
        if not exposure_compliant:
            reasons.append("active exposure exceeds policy maximum")
        if daily_action is not DailyRiskAction.NORMAL:
            reasons.append(f"daily risk action is {daily_action}")
        if weekly_state is not WeeklyRiskState.NORMAL:
            reasons.append(f"weekly risk state is {weekly_state}")

        may_add_new_risk = (
            trade_risk_compliant
            and exposure_compliant
            and daily_action is DailyRiskAction.NORMAL
            and weekly_state in {WeeklyRiskState.NORMAL, WeeklyRiskState.CAUTION}
        )
        return DeskRiskDecision(
            weekly_state=weekly_state,
            daily_action=daily_action,
            trade_risk_compliant=trade_risk_compliant,
            exposure_compliant=exposure_compliant,
            may_add_new_risk=may_add_new_risk,
            reasons=tuple(reasons),
        )

    def _daily_action(self, daily_loss_fraction: float) -> DailyRiskAction:
        if daily_loss_fraction >= self._policy.daily_loss_emergency:
            return DailyRiskAction.EMERGENCY_HALT
        if daily_loss_fraction >= self._policy.daily_loss_normal:
            return DailyRiskAction.BLOCK_NEW_RISK
        return DailyRiskAction.NORMAL

    def _weekly_state(self, weekly_drawdown_fraction: float) -> WeeklyRiskState:
        if weekly_drawdown_fraction >= self._policy.weekly_catastrophic_drawdown:
            return WeeklyRiskState.QUARANTINE
        if weekly_drawdown_fraction >= self._policy.weekly_halt_drawdown:
            return WeeklyRiskState.HALT
        if weekly_drawdown_fraction >= self._policy.weekly_defensive_drawdown:
            return WeeklyRiskState.DEFENSIVE
        if weekly_drawdown_fraction >= self._policy.weekly_caution_drawdown:
            return WeeklyRiskState.CAUTION
        return WeeklyRiskState.NORMAL
