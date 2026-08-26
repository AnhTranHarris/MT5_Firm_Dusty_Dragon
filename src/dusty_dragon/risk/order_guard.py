from __future__ import annotations

from dataclasses import dataclass

from dusty_dragon.config import Settings, TradingMode
from dusty_dragon.domain.trades import (
    AccountSnapshot,
    GuardDecision,
    GuardResult,
    TradeProposal,
)


@dataclass(frozen=True)
class OrderGuard:
    settings: Settings

    def evaluate(
        self,
        proposal: TradeProposal,
        account: AccountSnapshot,
        *,
        kill_switch: bool = False,
        market_data_fresh: bool = True,
        symbol_allowed: bool = True,
    ) -> GuardResult:
        reasons: list[str] = []

        if self.settings.trading_mode != TradingMode.PAPER:
            reasons.append("initial release only permits paper trading")
        if kill_switch:
            reasons.append("kill switch is active")
        if not market_data_fresh:
            reasons.append("market data is stale or unavailable")
        if not symbol_allowed:
            reasons.append("symbol is outside the configured trading universe")
        if proposal.risk_pct > self.settings.risk_per_trade_pct:
            reasons.append("proposal exceeds maximum risk per trade")
        if account.open_risk_pct + proposal.risk_pct > self.settings.max_open_risk_pct:
            reasons.append("proposal exceeds maximum aggregate open risk")
        if account.daily_drawdown_pct >= self.settings.daily_drawdown_halt_pct:
            reasons.append("daily drawdown halt threshold reached")
        if account.weekly_drawdown_pct >= self.settings.weekly_drawdown_halt_pct:
            reasons.append("weekly drawdown halt threshold reached")

        if reasons:
            return GuardResult(decision=GuardDecision.DENY, reasons=reasons)
        return GuardResult(decision=GuardDecision.ALLOW)
