from __future__ import annotations

from dataclasses import dataclass

from dusty_dragon.brokers.contracts import BrokerAdapter, ExecutionResult
from dusty_dragon.brokers.volume import normalize_volume_down
from dusty_dragon.domain.trades import Side, TradeProposal


@dataclass(frozen=True)
class PaperExecutionAssumptions:
    """Explicit paper-fill assumptions used when broker-side values are unavailable.

    Vibe-Trading's backtest/cost architecture is the primary design reference:
    simulated performance must carry its costs and assumptions with it. Kronos
    supplies forecast evidence upstream; Automaton-style learning consumes the
    resulting execution/outcome records downstream.
    """

    slippage_points: float = 0.0
    commission_per_lot_round_turn: float = 0.0
    swap_per_lot: float = 0.0

    def __post_init__(self) -> None:
        if self.slippage_points < 0:
            raise ValueError("slippage_points cannot be negative")
        if self.commission_per_lot_round_turn < 0:
            raise ValueError("commission cannot be negative")


@dataclass(frozen=True)
class PaperExecutionEngine:
    broker: BrokerAdapter
    assumptions: PaperExecutionAssumptions = PaperExecutionAssumptions()

    def open(self, proposal: TradeProposal, requested_volume: float) -> ExecutionResult:
        """Create a deterministic simulated opening fill without sending a broker order."""
        spec = self.broker.symbol_spec(proposal.symbol)
        quote = self.broker.quote(proposal.symbol)
        volume = normalize_volume_down(requested_volume, spec)

        slippage_price = self.assumptions.slippage_points * spec.point
        if proposal.side == Side.BUY:
            fill_price = quote.ask + slippage_price
        else:
            fill_price = quote.bid - slippage_price

        spread_points = quote.spread / spec.point
        commission = self.assumptions.commission_per_lot_round_turn * volume / 2.0
        swap = self.assumptions.swap_per_lot * volume

        return ExecutionResult(
            accepted=True,
            message="paper fill simulated; no broker order sent",
            requested_volume=requested_volume,
            executed_volume=volume,
            executed_price=round(fill_price, spec.digits),
            spread_points=spread_points,
            slippage_points=self.assumptions.slippage_points,
            estimated_commission=commission,
            estimated_swap=swap,
        )
