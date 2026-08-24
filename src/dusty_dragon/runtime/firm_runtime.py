from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel

from dusty_dragon.scheduler.weekly_clock import FirmPhase, FirmWeeklyClock


class TradingCapability(Protocol):
    def run(self, *args: Any, **kwargs: Any) -> Any: ...


class ResearchCapability(Protocol):
    def run(self, *, phase: FirmPhase, observed_at: datetime) -> Any: ...


class RuntimeAction(str):
    TRADE_CYCLE = "trade_cycle"
    WEEKEND_RESEARCH = "weekend_research"
    SUNDAY_VALIDATION = "sunday_validation"


class FirmRuntimeResult(BaseModel):
    phase: FirmPhase
    action: str
    payload: Any = None


@dataclass(frozen=True)
class FirmRuntime:
    """Route the firm to the capability allowed by its current lifecycle phase.

    Automaton roadmap: its heartbeat daemon wakes explicit capabilities rather
    than embedding scheduling inside the reasoning loop. Dusty Dragon mirrors
    that separation in Python.

    Vibe-Trading roadmap: live/trading operations and research are separate
    operational domains with governance boundaries.

    Kronos remains inside downstream trading/research capabilities. The runtime
    clock cannot convert a forecast into an order and does not know model APIs.
    """

    weekly_clock: FirmWeeklyClock
    trading: TradingCapability
    research: ResearchCapability

    def dispatch_trading(
        self,
        observed_at: datetime,
        *args: Any,
        **kwargs: Any,
    ) -> FirmRuntimeResult:
        phase = self.weekly_clock.phase_at(observed_at)
        if phase != FirmPhase.TRADING:
            return self._dispatch_nontrading(phase, observed_at)

        payload = self.trading.run(*args, **kwargs)
        return FirmRuntimeResult(
            phase=phase,
            action=RuntimeAction.TRADE_CYCLE,
            payload=payload,
        )

    def dispatch_research(self, observed_at: datetime) -> FirmRuntimeResult:
        phase = self.weekly_clock.phase_at(observed_at)
        if phase == FirmPhase.TRADING:
            raise RuntimeError("research dispatch is not permitted during the trading phase")
        return self._dispatch_nontrading(phase, observed_at)

    def _dispatch_nontrading(self, phase: FirmPhase, observed_at: datetime) -> FirmRuntimeResult:
        payload = self.research.run(phase=phase, observed_at=observed_at)
        action = (
            RuntimeAction.SUNDAY_VALIDATION
            if phase == FirmPhase.SUNDAY_VALIDATION
            else RuntimeAction.WEEKEND_RESEARCH
        )
        return FirmRuntimeResult(phase=phase, action=action, payload=payload)
