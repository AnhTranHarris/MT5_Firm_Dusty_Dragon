from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


class TradeProposal(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    strategy_version: str
    symbol: str
    side: Side
    entry_price: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    take_profit: float = Field(gt=0)
    risk_pct: float = Field(gt=0)
    confidence: float = Field(ge=0, le=1)
    timeframe: str
    thesis: str
    evidence: dict[str, float | str | bool] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_price_geometry(self) -> TradeProposal:
        if self.side == Side.BUY:
            if not self.stop_loss < self.entry_price < self.take_profit:
                raise ValueError("BUY requires stop_loss < entry_price < take_profit")
        elif not self.take_profit < self.entry_price < self.stop_loss:
            raise ValueError("SELL requires take_profit < entry_price < stop_loss")
        return self

    @property
    def reward_to_risk(self) -> float:
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.take_profit - self.entry_price)
        return reward / risk


class AccountSnapshot(BaseModel):
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    balance: float = Field(gt=0)
    equity: float = Field(gt=0)
    open_risk_pct: float = Field(default=0, ge=0)
    daily_drawdown_pct: float = Field(default=0, ge=0)
    weekly_drawdown_pct: float = Field(default=0, ge=0)


class GuardDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


class GuardResult(BaseModel):
    decision: GuardDecision
    reasons: list[str] = Field(default_factory=list)
