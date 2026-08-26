from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from enum import StrEnum
from zoneinfo import ZoneInfo


class FirmPhase(StrEnum):
    TRADING = "trading"
    WEEKEND_RESEARCH = "weekend_research"
    SUNDAY_VALIDATION = "sunday_validation"


@dataclass(frozen=True)
class FirmWeeklyClock:
    """Classify Dusty Dragon's user-defined weekly operating phase.

    Automaton reference: heartbeat/scheduler logic decides which expensive
    capabilities should wake rather than keeping the entire agent continuously
    active.

    Vibe-Trading reference: research and trading workflows remain separate
    operational concerns.

    Kronos may run forecasts during trading or research, but this clock never
    grants models execution authority.

    These are firm policy defaults in America/Chicago, not a claim about a
    broker's actual session calendar. The MT5 broker division will later verify
    symbol sessions before execution.
    """

    timezone_name: str = "America/Chicago"
    sunday_trading_start: time = time(16, 0)
    friday_new_trade_cutoff: time = time(15, 0)
    sunday_validation_start: time = time(14, 0)

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)

    def phase_at(self, moment: datetime) -> FirmPhase:
        if moment.tzinfo is None:
            raise ValueError("weekly clock requires a timezone-aware datetime")
        local = moment.astimezone(self.timezone)
        weekday = local.weekday()  # Monday=0 ... Sunday=6
        local_time = local.timetz().replace(tzinfo=None)

        if weekday in {0, 1, 2, 3}:
            return FirmPhase.TRADING
        if weekday == 4:
            return (
                FirmPhase.TRADING
                if local_time < self.friday_new_trade_cutoff
                else FirmPhase.WEEKEND_RESEARCH
            )
        if weekday == 5:
            return FirmPhase.WEEKEND_RESEARCH

        if local_time < self.sunday_validation_start:
            return FirmPhase.WEEKEND_RESEARCH
        if local_time < self.sunday_trading_start:
            return FirmPhase.SUNDAY_VALIDATION
        return FirmPhase.TRADING

    def trading_enabled(self, moment: datetime) -> bool:
        return self.phase_at(moment) == FirmPhase.TRADING

    def research_enabled(self, moment: datetime) -> bool:
        return self.phase_at(moment) in {
            FirmPhase.WEEKEND_RESEARCH,
            FirmPhase.SUNDAY_VALIDATION,
        }
