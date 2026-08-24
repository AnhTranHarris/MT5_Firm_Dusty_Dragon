from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, Field, model_validator

from dusty_dragon.domain.trades import Side, TradeProposal


class SymbolSpec(BaseModel):
    symbol: str
    volume_min: float = Field(gt=0)
    volume_max: float = Field(gt=0)
    volume_step: float = Field(gt=0)
    point: float = Field(gt=0)
    digits: int = Field(ge=0)
    trade_mode: int | None = None
    contract_size: float | None = Field(default=None, gt=0)
    tick_size: float | None = Field(default=None, gt=0)
    tick_value: float | None = Field(default=None, ge=0)
    profit_currency: str | None = None


class Quote(BaseModel):
    symbol: str
    captured_at: datetime
    bid: float = Field(gt=0)
    ask: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_market(self) -> Quote:
        if self.ask < self.bid:
            raise ValueError("quote ask cannot be below bid")
        return self

    @property
    def spread(self) -> float:
        return self.ask - self.bid


class MarketBar(BaseModel):
    symbol: str
    timeframe: str
    opened_at: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    tick_volume: float = Field(ge=0)
    spread_points: float = Field(ge=0)
    real_volume: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_ohlc_geometry(self) -> MarketBar:
        if self.low > self.high:
            raise ValueError("market bar low cannot exceed high")
        if not self.low <= self.open <= self.high:
            raise ValueError("market bar open must lie within low/high")
        if not self.low <= self.close <= self.high:
            raise ValueError("market bar close must lie within low/high")
        return self


class BrokerAccountState(BaseModel):
    captured_at: datetime
    login: int | None = None
    currency: str
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float | None = None


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
    spread_points: float | None = Field(default=None, ge=0)
    slippage_points: float | None = Field(default=None, ge=0)
    estimated_commission: float | None = Field(default=None, ge=0)
    estimated_swap: float | None = None
    gross_pnl: float | None = None
    net_pnl: float | None = None


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

    def bars(self, symbol: str, timeframe: str, count: int) -> Sequence[MarketBar]: ...

    def account_state(self) -> BrokerAccountState: ...

    def positions(self) -> Sequence[Position]: ...

    def execute_paper(self, proposal: TradeProposal, volume: float) -> ExecutionResult: ...
