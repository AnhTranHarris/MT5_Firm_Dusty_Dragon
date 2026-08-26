# ruff: noqa: I001

from datetime import datetime
from zoneinfo import ZoneInfo

from dusty_dragon.scheduler.research_clock import ResearchClock, ResearchMode


TZ = ZoneInfo("America/Chicago")


def moment(year: int, month: int, day: int, hour: int) -> datetime:
    return datetime(year, month, day, hour, 0, tzinfo=TZ)


def test_weekday_research_runs_four_pm_to_midnight():
    clock = ResearchClock()

    assert clock.mode_at(moment(2026, 8, 24, 15)) == ResearchMode.OFF
    assert clock.mode_at(moment(2026, 8, 24, 16)) == ResearchMode.DAILY_BACKTEST
    assert clock.mode_at(moment(2026, 8, 24, 23)) == ResearchMode.DAILY_BACKTEST
    assert clock.mode_at(moment(2026, 8, 25, 0)) == ResearchMode.OFF


def test_saturday_has_eight_hour_heavy_backtest_block():
    clock = ResearchClock()

    assert clock.mode_at(moment(2026, 8, 29, 7)) == ResearchMode.OFF
    assert clock.mode_at(moment(2026, 8, 29, 8)) == ResearchMode.SATURDAY_HEAVY_BACKTEST
    assert clock.mode_at(moment(2026, 8, 29, 15)) == ResearchMode.SATURDAY_HEAVY_BACKTEST
    assert clock.mode_at(moment(2026, 8, 29, 16)) == ResearchMode.OFF


def test_adaptation_lab_runs_saturday_night_to_sunday_morning():
    clock = ResearchClock()

    assert clock.mode_at(moment(2026, 8, 29, 20)) == ResearchMode.ADAPTATION_LAB
    assert clock.mode_at(moment(2026, 8, 30, 7)) == ResearchMode.ADAPTATION_LAB
    assert clock.mode_at(moment(2026, 8, 30, 8)) == ResearchMode.OFF


def test_research_clock_rejects_naive_datetime():
    clock = ResearchClock()

    try:
        clock.mode_at(datetime(2026, 8, 24, 16, 0))  # noqa: DTZ001
    except ValueError as exc:
        assert "timezone-aware" in str(exc)
    else:
        raise AssertionError("naive datetime should be rejected")
