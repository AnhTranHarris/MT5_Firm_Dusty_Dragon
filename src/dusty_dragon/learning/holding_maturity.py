from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum


class HoldingStage(StrEnum):
    INTRADAY = "intraday"
    OVERNIGHT = "overnight"
    MULTI_DAY = "multi_day"
    WEEKLY = "weekly"


class TradeQuality(StrEnum):
    ACCEPTED = "accepted"
    MARGINAL = "marginal"
    FAILED = "failed"


@dataclass(frozen=True)
class StageTradeAssessment:
    stage: HoldingStage
    pnl: float
    quality: TradeQuality
    catastrophic_reset: bool = False
    destroyed_gain_fraction: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.destroyed_gain_fraction <= 1.0:
            raise ValueError("destroyed_gain_fraction must be between 0 and 1")

    @property
    def is_loss(self) -> bool:
        return self.pnl < 0

    @property
    def is_acceptable_loss(self) -> bool:
        return self.is_loss and self.quality == TradeQuality.ACCEPTED


@dataclass
class StageState:
    stage: HoldingStage
    qualification_trades: int = 0
    accepted_trades: int = 0
    qualification_pnl: float = 0.0
    authorized: bool = False
    qualified: bool = False
    probation: bool = False
    recent: deque[StageTradeAssessment] = field(default_factory=lambda: deque(maxlen=50))

    @property
    def acceptance_rate(self) -> float:
        if self.qualification_trades == 0:
            return 0.0
        return self.accepted_trades / self.qualification_trades


@dataclass(frozen=True)
class MaturityPolicy:
    qualification_target: int = 5_000
    acceptance_threshold: float = 0.85
    probation_window: int = 50
    catastrophic_gain_destruction: float = 0.50

    def __post_init__(self) -> None:
        if self.qualification_target <= 0:
            raise ValueError("qualification_target must be positive")
        if not 0.0 < self.acceptance_threshold <= 1.0:
            raise ValueError("acceptance_threshold must be between 0 and 1")
        if self.probation_window != 50:
            raise ValueError("probation_window is fixed at 50 trades")
        if not 0.0 < self.catastrophic_gain_destruction <= 1.0:
            raise ValueError("catastrophic_gain_destruction must be between 0 and 1")


@dataclass
class HoldingMaturityEngine:
    """Evidence-based authorization ladder for holding-duration capabilities.

    Capital growth is mandatory for graduation. Trade-quality acceptance and
    risk discipline constrain how that growth is achieved, but cannot substitute
    for a profitable qualification period.

    Qualification progress may reset or a stage may be demoted, but historical
    trade knowledge is never deleted. This engine tracks authorization only; it
    does not place trades, size orders, or alter strategy logic.
    """

    policy: MaturityPolicy = field(default_factory=MaturityPolicy)
    states: dict[HoldingStage, StageState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.states:
            self.states = {stage: StageState(stage=stage) for stage in HoldingStage}
            self.states[HoldingStage.INTRADAY].authorized = True

    def record(self, assessment: StageTradeAssessment) -> None:
        state = self.states[assessment.stage]
        if not state.authorized:
            raise PermissionError(f"holding stage {assessment.stage} is not authorized")

        state.qualification_trades += 1
        state.qualification_pnl += assessment.pnl
        if assessment.quality == TradeQuality.ACCEPTED:
            state.accepted_trades += 1
        state.recent.append(assessment)

        if self._requires_reset(assessment):
            self._reset_stage(state)
            return

        if len(state.recent) == self.policy.probation_window and self._probation_failed(state):
            self._demote(state.stage)
            return

        if self._ready_to_qualify(state):
            state.qualified = True
            state.probation = False
            next_stage = self._next_stage(state.stage)
            if next_stage is not None:
                self.states[next_stage].authorized = True

    def _requires_reset(self, assessment: StageTradeAssessment) -> bool:
        return assessment.catastrophic_reset or (
            assessment.destroyed_gain_fraction >= self.policy.catastrophic_gain_destruction
        )

    def _probation_failed(self, state: StageState) -> bool:
        window = list(state.recent)
        if len(window) < self.policy.probation_window:
            return False

        if all(item.is_loss for item in window):
            return True

        losses = [item for item in window if item.is_loss]
        if losses:
            acceptable_losses = sum(item.is_acceptable_loss for item in losses)
            if acceptable_losses / len(losses) < 0.50:
                return True

        gross_gains = sum(item.pnl for item in window if item.pnl > 0)
        gross_losses = -sum(item.pnl for item in window if item.pnl < 0)
        return gross_losses > gross_gains

    def _ready_to_qualify(self, state: StageState) -> bool:
        return (
            state.qualification_trades >= self.policy.qualification_target
            and state.acceptance_rate >= self.policy.acceptance_threshold
            and state.qualification_pnl > 0
        )

    def _reset_stage(self, state: StageState) -> None:
        state.qualification_trades = 0
        state.accepted_trades = 0
        state.qualification_pnl = 0.0
        state.qualified = False
        state.probation = True
        state.recent.clear()

    def _demote(self, stage: HoldingStage) -> None:
        previous = self._previous_stage(stage)
        state = self.states[stage]
        self._reset_stage(state)
        if previous is None:
            state.authorized = True
            return

        state.authorized = False
        previous_state = self.states[previous]
        previous_state.authorized = True
        previous_state.qualified = False
        previous_state.probation = True
        previous_state.qualification_trades = 0
        previous_state.accepted_trades = 0
        previous_state.qualification_pnl = 0.0
        previous_state.recent.clear()

        for higher in self._higher_stages(stage):
            higher_state = self.states[higher]
            higher_state.authorized = False
            higher_state.qualified = False

    @staticmethod
    def _next_stage(stage: HoldingStage) -> HoldingStage | None:
        order = list(HoldingStage)
        index = order.index(stage)
        return order[index + 1] if index + 1 < len(order) else None

    @staticmethod
    def _previous_stage(stage: HoldingStage) -> HoldingStage | None:
        order = list(HoldingStage)
        index = order.index(stage)
        return order[index - 1] if index > 0 else None

    @staticmethod
    def _higher_stages(stage: HoldingStage) -> list[HoldingStage]:
        order = list(HoldingStage)
        return order[order.index(stage) + 1 :]
