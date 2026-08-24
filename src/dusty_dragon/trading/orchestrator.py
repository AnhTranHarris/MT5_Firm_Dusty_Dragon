from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel

from dusty_dragon.brokers.contracts import BrokerAdapter, MarketBar
from dusty_dragon.domain.trades import AccountSnapshot, GuardDecision, GuardResult
from dusty_dragon.intelligence.kronos_forecast import KronosForecast
from dusty_dragon.intelligence.research_signal import (
    GeneralistResearchEngine,
    ResearchSignal,
    SignalDecision,
)
from dusty_dragon.portfolio.exposure import FirmPortfolioGovernor, PortfolioDecision
from dusty_dragon.reporting.delivery import ReportDeliveryError, ReportSink
from dusty_dragon.reporting.trade_report import TradeReport
from dusty_dragon.risk.order_guard import OrderGuard
from dusty_dragon.storage.trade_ledger import TradeLedger
from dusty_dragon.trading.paper_execution import PaperExecutionEngine


class DecisionCycleStatus(str):
    ABSTAIN = "abstain"
    DENIED = "denied"
    PAPER_FILLED = "paper_filled"


class DecisionCycleResult(BaseModel):
    status: str
    signal: ResearchSignal
    forecast: KronosForecast
    report: TradeReport | None = None
    record_hash: str | None = None
    delivery_error: str | None = None


class ForecastServiceLike(Protocol):
    def forecast(self, bars: list[MarketBar], horizon_bars: int) -> KronosForecast: ...


@dataclass(frozen=True)
class PaperTradingOrchestrator:
    """Coordinate one complete governed paper-trading decision cycle.

    Roadmap synthesis:
    - Kronos supplies forecast evidence only.
    - Vibe-Trading inspires the research -> portfolio -> risk -> execution ordering.
    - Automaton inspires explicit orchestration, centralized policy capabilities,
      durable audit state, and replaceable services rather than a monolithic loop.

    The orchestrator cannot place live orders: its execution dependency is the
    deterministic PaperExecutionEngine, which itself never calls order_send.
    """

    broker: BrokerAdapter
    forecast_service: ForecastServiceLike
    research_engine: GeneralistResearchEngine
    portfolio_governor: FirmPortfolioGovernor
    order_guard: OrderGuard
    paper_execution: PaperExecutionEngine
    ledger: TradeLedger
    report_sink: ReportSink | None = None
    broker_division: str = "boforex"
    account_label: str = "paper-01"
    requested_volume: float = 0.01
    strategy_version: str = "generalist-v0"
    bar_count: int = 128
    forecast_horizon_bars: int = 4

    def run(
        self,
        symbol: str,
        timeframe: str,
        account: AccountSnapshot,
        *,
        risk_pct: float,
        kill_switch: bool = False,
        market_data_fresh: bool = True,
        symbol_allowed: bool = True,
    ) -> DecisionCycleResult:
        bars = list(self.broker.bars(symbol, timeframe, self.bar_count))
        forecast = self.forecast_service.forecast(bars, self.forecast_horizon_bars)
        signal = self.research_engine.evaluate(bars, forecast)

        if signal.decision == SignalDecision.ABSTAIN:
            return DecisionCycleResult(
                status=DecisionCycleStatus.ABSTAIN,
                signal=signal,
                forecast=forecast,
            )

        quote = self.broker.quote(symbol)
        proposal = self.research_engine.proposal_from_signal(
            signal,
            quote,
            risk_pct=risk_pct,
            strategy_version=self.strategy_version,
        )
        if proposal is None:
            raise RuntimeError("non-abstain research signal did not produce a proposal")

        portfolio_review = self.portfolio_governor.evaluate(
            proposal,
            list(self.broker.positions()),
            proposed_volume=self.requested_volume,
        )
        trade_guard = self.order_guard.evaluate(
            proposal,
            account,
            kill_switch=kill_switch,
            market_data_fresh=market_data_fresh,
            symbol_allowed=symbol_allowed,
        )
        guard = self._combine_governance(trade_guard, portfolio_review.decision, portfolio_review.reasons)

        execution = None
        status = DecisionCycleStatus.DENIED
        if guard.decision == GuardDecision.ALLOW:
            execution = self.paper_execution.open(proposal, self.requested_volume)
            status = DecisionCycleStatus.PAPER_FILLED

        report = TradeReport.from_decision(
            proposal,
            guard,
            broker_division=self.broker_division,
            account_label=self.account_label,
            execution=execution,
            model_versions={"kronos": "upstream-adapter"},
            data_provenance={"market_data": "broker-adapter"},
            observations={
                "signal_decision": signal.decision.value,
                "signal_confidence": signal.confidence,
                "forecast_return_pct": forecast.predicted_return_pct,
                "portfolio_current_net_lots": portfolio_review.current_net_lots,
                "portfolio_projected_net_lots": portfolio_review.projected_net_lots,
            },
        )
        record_hash = self.ledger.append(report)
        delivery_error = self._deliver(report)

        return DecisionCycleResult(
            status=status,
            signal=signal,
            forecast=forecast,
            report=report,
            record_hash=record_hash,
            delivery_error=delivery_error,
        )

    @staticmethod
    def _combine_governance(
        trade_guard: GuardResult,
        portfolio_decision: PortfolioDecision,
        portfolio_reasons: list[str],
    ) -> GuardResult:
        reasons = list(trade_guard.reasons)
        reasons.extend(f"firm portfolio: {reason}" for reason in portfolio_reasons)
        denied = (
            trade_guard.decision == GuardDecision.DENY
            or portfolio_decision == PortfolioDecision.DENY
        )
        return GuardResult(
            decision=GuardDecision.DENY if denied else GuardDecision.ALLOW,
            reasons=reasons,
        )

    def _deliver(self, report: TradeReport) -> str | None:
        if self.report_sink is None:
            return None
        try:
            self.report_sink.send(report)
        except ReportDeliveryError as exc:
            # Audit persistence takes precedence over a human-notification outage.
            return str(exc)
        return None
