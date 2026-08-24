from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from dusty_dragon.scheduler.weekly_clock import FirmPhase, FirmWeeklyClock


CT = ZoneInfo("America/Chicago")


def moment(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=CT)


def test_weekday_is_trading_phase():
    clock = FirmWeeklyClock()

    assert clock.phase_at(moment(2026, 8, 24, 10)) == FirmPhase.TRADING  # Monday


def test_friday_cutoff_switches_to_weekend_research():
    clock = FirmWeeklyClock()

    assert clock.phase_at(moment(2026, 8, 28, 14, 59)) == FirmPhase.TRADING
    assert clock.phase_at(moment(2026, 8, 28, 15, 0)) == FirmPhase.WEEKEND_RESEARCH


def test_saturday_is_research_phase():
    assert FirmWeeklyClock().phase_at(moment(2026, 8, 29, 12)) == FirmPhase.WEEKEND_RESEARCH


def test_sunday_moves_from_research_to_validation_to_trading():
    clock = FirmWeeklyClock()

    assert clock.phase_at(moment(2026, 8, 30, 10)) == FirmPhase.WEEKEND_RESEARCH
    assert clock.phase_at(moment(2026, 8, 30, 15)) == FirmPhase.SUNDAY_VALIDATION
    assert clock.phase_at(moment(2026, 8, 30, 16)) == FirmPhase.TRADING


def test_naive_datetime_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        FirmWeeklyClock().phase_at(datetime(2026, 8, 24, 10))
