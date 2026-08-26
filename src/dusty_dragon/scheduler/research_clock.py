from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from enum import StrEnum
from zoneinfo import ZoneInfo


class ResearchMode(StrEnum):
    OFF = "off"
    DAILY_BACKTEST = "daily_backtest"
    SATURDAY_HEAVY_BACKTEST = "saturday_heavy_backtest"
    ADAPTATION_LAB = "adaptation_lab"


@dataclass(frozen=True)
class ResearchClock:
    """Independent schedule for Dusty Dragon's continuous research department.

    Trading and research are parallel capabilities. This clock never disables
    trading and never grants research execution or promotion authority.

    Roadmap synthesis:
    - Automaton: durable scheduled work runs independently of the main agent loop.
    - Vibe-Trading: research/backtest work stays operationally separate from live
      execution and is validated before strategy lifecycle changes.
    - Kronos: historical experiments calibrate or challenge forecast confidence;
      they do not replace the Kronos forecasting boundary.

    Default policy uses America/Chicago:
    - Mon-Fri 16:00-24:00: daily backtesting.
    - Saturday 08:00-16:00: eight-hour heavy backtesting block.
    - Saturday 20:00-Sunday 08:00: challenger/adaptation laboratory.

    Saturday times are explicit policy defaults and may be configured later
    without changing research or trading code.
    """

    timezone_name: str = "America/Chicago"
    weekday_backtest_start: time = time(16, 0)
    weekday_backtest_end: time = time(0, 0)
    saturday_backtest_start: time = time(8, 0)
    saturday_backtest_end: time = time(16, 0)
    adaptation_start: time = time(20, 0)
    sunday_adaptation_end: time = time(8, 0)

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)

    def mode_at(self, moment: datetime) -> ResearchMode:
        if moment.tzinfo is None:
            raise ValueError("research clock requires a timezone-aware datetime")
        local = moment.astimezone(self.timezone)
        weekday = local.weekday()  # Monday=0 ... Sunday=6
        local_time = local.timetz().replace(tzinfo=None)

        if weekday in {0, 1, 2, 3, 4}:
            if self._in_overnight_window(
                local_time,
                self.weekday_backtest_start,
                self.weekday_backtest_end,
            ):
                return ResearchMode.DAILY_BACKTEST
            return ResearchMode.OFF

        if weekday == 5:
            if self.saturday_backtest_start <= local_time < self.saturday_backtest_end:
                return ResearchMode.SATURDAY_HEAVY_BACKTEST
            if local_time >= self.adaptation_start:
                return ResearchMode.ADAPTATION_LAB
            return ResearchMode.OFF

        if local_time < self.sunday_adaptation_end:
            return ResearchMode.ADAPTATION_LAB
        return ResearchMode.OFF

    def research_enabled(self, moment: datetime) -> bool:
        return self.mode_at(moment) != ResearchMode.OFF

    @staticmethod
    def _in_overnight_window(value: time, start: time, end: time) -> bool:
        if start == end:
            return True
        if start < end:
            return start <= value < end
        return value >= start or value < end
