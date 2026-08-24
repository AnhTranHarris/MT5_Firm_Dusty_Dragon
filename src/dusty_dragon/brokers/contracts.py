from __future__ import annotations

from datetime import datetime
from typing import Protocol, Sequence

from pydantic import BaseModel, Field

from dusty_dragon.domain.trades import Side, TradeProposal


class SymbolSpec(BaseModel):
    symbol: str
    volume_min: float = Field(gt=0)
    volume_max: float = Field(gt=0)
    volume_step: float = Field(gt=0)
    point: float = Field(gt=0)
    digits: int = Field(ge=0)
    trade_mode: int | None = None


class Quote(BaseModel):
    symbol: str
    captured_at: datetime
    bid: float = Field(gt=0)
    ask: float = Field(gt=0)

    @property
    def spread(self) -> float:
        return self.ask - self.bid


class Position(BaseModel):
    ticket: int
    symbol: str
    side: Side
    volume: float = Field(gt=0)
    price_open: float = Field(gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    take_profit: float | None = Field(default=None, gt=0)
    profit: float = 0.0


class ExecutionResult(BaseModel):
    accepted: bool
    broker_order_id: int | None = None
    broker_deal_id: int | None = None
    retcode: int | None = None
    message: str = ""
    requested_volume: float
    executed_volume: float | None = None
    executed_price: float | None = None


class BrokerAdapter(Protocol):
    """Platform-neutral boundary for broker/terminal integrations.

    MT5 is the first transport, but strategy, Kronos forecasting, Vibe-inspired
    research, and Automaton-inspired learning must depend on this interface
    rather than MetaTrader5-specific objects.
    """

    def connect(self) -> None: ...

    def close(self) -> None: ...

    def symbols(self) -> Sequence[str]: ...

    def symbol_spec(self, symbol: str) -> SymbolSpec: ...

    def quote(self, symbol: str) -> Quote: ...

    def positions(self) -> Sequence[Position]: ...

    def execute_paper(self, proposal: TradeProposal, volume: float) -> ExecutionResult: ...
