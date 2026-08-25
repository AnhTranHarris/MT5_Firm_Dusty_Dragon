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
    TRADING_CLOSED = "trading_closed"
    MANUAL_RESEARCH = "manual_research"


class FirmRuntimeResult(BaseModel):
    phase: FirmPhase
    action: str
    payload: Any = None


@dataclass(frozen=True)
class FirmRuntime:
    """Route trading authority without owning the research schedule.

    The original runtime used one weekly phase to choose either trading *or*
    research. Dusty Dragon now operates those as parallel departments:

    - FirmWeeklyClock still governs when new trading cycles are permitted.
    - ResearchClock + ResearchRuntimeController independently govern continuous
      research and machine-resource budgets.

    A closed trading window therefore blocks trading; it never wakes research as
    a side effect. Manual research dispatch remains available for diagnostics and
    compatibility, but scheduled research belongs to ResearchRuntimeController.

    Kronos remains downstream inside trading/research capabilities and receives
    no execution, scheduling, or promotion authority here.
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
            return FirmRuntimeResult(
                phase=phase,
                action=RuntimeAction.TRADING_CLOSED,
                payload=None,
            )

        payload = self.trading.run(*args, **kwargs)
        return FirmRuntimeResult(
            phase=phase,
            action=RuntimeAction.TRADE_CYCLE,
            payload=payload,
        )

    def dispatch_research(self, observed_at: datetime) -> FirmRuntimeResult:
        """Run the legacy/manual research capability without schedule authority.

        Continuous scheduled research must use ResearchRuntimeController. This
        method intentionally does not reject FirmPhase.TRADING because trading
        and research may coexist.
        """
        phase = self.weekly_clock.phase_at(observed_at)
        payload = self.research.run(phase=phase, observed_at=observed_at)
        return FirmRuntimeResult(
            phase=phase,
            action=RuntimeAction.MANUAL_RESEARCH,
            payload=payload,
        )
