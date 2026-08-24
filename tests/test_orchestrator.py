from datetime import UTC, datetime, timedelta

from dusty_dragon.brokers.contracts import MarketBar, Quote, SymbolSpec
from dusty_dragon.config import Settings
from dusty_dragon.domain.trades import AccountSnapshot
from dusty_dragon.intelligence.kronos_forecast import KronosForecast
from dusty_dragon.intelligence.research_signal import GeneralistResearchEngine
from dusty_dragon.reporting.delivery import ReportDeliveryError
from dusty_dragon.risk.order_guard import OrderGuard
from dusty_dragon.storage.trade_ledger import TradeLedger
from dusty_dragon.trading.orchestrator import DecisionCycleStatus, PaperTradingOrchestrator
from dusty_dragon.trading.paper_execution import PaperExecutionEngine


class FakeBroker:
    def __init__(self, *, rising: bool = True) -> None:
        start = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
        self._bars = []
        for index in range(12):
            delta = index * 0.0002 * (1 if rising else -1)
            close = 1.1000 + delta
            self._bars.append(
                MarketBar(
                    symbol="EURUSD",
                    timeframe="M15",
                    opened_at=start + timedelta(minutes=15 * index),
                    open=close - 0.0001,
                    high=close + 0.0002,
                    low=close - 0.0002,
                    close=close,
                    tick_volume=100 + index,
                    spread_points=8.0,
                    real_volume=0.0,
                )
            )

    def bars(self, symbol: str, timeframe: str, count: int):
        assert symbol == "EURUSD"
        assert timeframe == "M15"
        return self._bars[-count:]

    def quote(self, symbol: str) -> Quote:
        return Quote(
            symbol=symbol,
            captured_at=datetime(2026, 8, 24, 15, 0, tzinfo=UTC),
            bid=1.1020,
            ask=1.1022,
        )

    def symbol_spec(self, symbol: str) -> SymbolSpec:
        return SymbolSpec(
            symbol=symbol,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            point=0.00001,
            digits=5,
        )


class FakeForecastService:
    def __init__(self, return_pct: float = 0.20) -> None:
        self.return_pct = return_pct

    def forecast(self, bars: list[MarketBar], horizon_bars: int) -> KronosForecast:
        starting = bars[-1].close
        predicted = starting * (1 + self.return_pct / 100.0)
        return KronosForecast(
            symbol=bars[-1].symbol,
            timeframe=bars[-1].timeframe,
            horizon_bars=horizon_bars,
            starting_close=starting,
            predicted_close=predicted,
            predicted_return_pct=self.return_pct,
            predicted_high=max(starting, predicted) + 0.0005,
            predicted_low=min(starting, predicted) - 0.0005,
            forecast_rows=horizon_bars,
            volume_source="tick_volume",
        )


class FailingSink:
    def send(self, report) -> None:
        raise ReportDeliveryError("email unavailable")


def account() -> AccountSnapshot:
    return AccountSnapshot(balance=10_000, equity=10_000)


def orchestrator(tmp_path, *, rising=True, return_pct=0.20, sink=None):
    broker = FakeBroker(rising=rising)
    return PaperTradingOrchestrator(
        broker=broker,
        forecast_service=FakeForecastService(return_pct),
        research_engine=GeneralistResearchEngine(),
        order_guard=OrderGuard(Settings()),
        paper_execution=PaperExecutionEngine(broker),
        ledger=TradeLedger(tmp_path / "ledger.sqlite3"),
        report_sink=sink,
        bar_count=12,
    )


def test_full_cycle_forecast_research_guard_fill_and_ledger(tmp_path):
    cycle = orchestrator(tmp_path)

    result = cycle.run("EURUSD", "M15", account(), risk_pct=0.25)

    assert result.status == DecisionCycleStatus.PAPER_FILLED
    assert result.report is not None
    assert result.report.execution is not None
    assert result.report.execution.executed_volume == 0.01
    assert result.record_hash is not None
    assert cycle.ledger.verify_chain() is True


def test_guard_denial_is_still_audited_but_not_filled(tmp_path):
    cycle = orchestrator(tmp_path)

    result = cycle.run(
        "EURUSD",
        "M15",
        account(),
        risk_pct=0.25,
        kill_switch=True,
    )

    assert result.status == DecisionCycleStatus.DENIED
    assert result.report is not None
    assert result.report.execution is None
    assert "kill switch is active" in result.report.guard.reasons
    assert result.record_hash is not None


def test_conflicting_research_abstains_without_creating_trade_report(tmp_path):
    cycle = orchestrator(tmp_path, rising=False, return_pct=0.20)

    result = cycle.run("EURUSD", "M15", account(), risk_pct=0.25)

    assert result.status == DecisionCycleStatus.ABSTAIN
    assert result.report is None
    assert result.record_hash is None


def test_email_failure_does_not_erase_audited_trade_decision(tmp_path):
    cycle = orchestrator(tmp_path, sink=FailingSink())

    result = cycle.run("EURUSD", "M15", account(), risk_pct=0.25)

    assert result.status == DecisionCycleStatus.PAPER_FILLED
    assert result.record_hash is not None
    assert result.delivery_error == "email unavailable"
    assert cycle.ledger.verify_chain() is True
