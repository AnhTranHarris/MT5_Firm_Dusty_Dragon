# ruff: noqa: I001
from datetime import datetime
from zoneinfo import ZoneInfo

from dusty_dragon.runtime.firm_runtime import FirmRuntime, RuntimeAction
from dusty_dragon.scheduler.weekly_clock import FirmPhase, FirmWeeklyClock


CT = ZoneInfo("America/Chicago")


class TradingSpy:
    def __init__(self) -> None:
        self.calls = 0

    def run(self, *args, **kwargs):
        self.calls += 1
        return {"args": args, "kwargs": kwargs}


class ResearchSpy:
    def __init__(self) -> None:
        self.calls: list[tuple[FirmPhase, datetime]] = []

    def run(self, *, phase: FirmPhase, observed_at: datetime):
        self.calls.append((phase, observed_at))
        return {"phase": phase.value}


def runtime():
    trading = TradingSpy()
    research = ResearchSpy()
    return FirmRuntime(FirmWeeklyClock(), trading, research), trading, research


def test_trading_phase_dispatches_trading_capability():
    firm, trading, research = runtime()
    observed = datetime(2026, 8, 24, 10, tzinfo=CT)

    result = firm.dispatch_trading(observed, "EURUSD", risk_pct=0.25)

    assert result.phase == FirmPhase.TRADING
    assert result.action == RuntimeAction.TRADE_CYCLE
    assert trading.calls == 1
    assert research.calls == []


def test_closed_trading_window_does_not_auto_run_research():
    firm, trading, research = runtime()
    observed = datetime(2026, 8, 29, 12, tzinfo=CT)

    result = firm.dispatch_trading(observed, "EURUSD", risk_pct=0.25)

    assert result.phase == FirmPhase.WEEKEND_RESEARCH
    assert result.action == RuntimeAction.TRADING_CLOSED
    assert result.payload is None
    assert trading.calls == 0
    assert research.calls == []


def test_manual_research_remains_available_on_weekend():
    firm, trading, research = runtime()
    observed = datetime(2026, 8, 30, 15, tzinfo=CT)

    result = firm.dispatch_research(observed)

    assert result.phase == FirmPhase.SUNDAY_VALIDATION
    assert result.action == RuntimeAction.MANUAL_RESEARCH
    assert trading.calls == 0
    assert research.calls[0][0] == FirmPhase.SUNDAY_VALIDATION


def test_manual_research_is_not_blocked_just_because_trading_is_open():
    firm, trading, research = runtime()
    observed = datetime(2026, 8, 24, 10, tzinfo=CT)

    result = firm.dispatch_research(observed)

    assert result.phase == FirmPhase.TRADING
    assert result.action == RuntimeAction.MANUAL_RESEARCH
    assert trading.calls == 0
    assert research.calls[0][0] == FirmPhase.TRADING
