from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from dusty_dragon.domain.market import AccountEnvironment


class PositionSide(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True, slots=True)
class AccountSnapshot:
    account_id: str
    desk_id: str
    broker_id: str
    environment: AccountEnvironment
    observed_at_utc: datetime
    balance: float
    equity: float
    margin: float
    free_margin: float

    def __post_init__(self) -> None:
        _require_text("account_id", self.account_id)
        _require_text("desk_id", self.desk_id)
        _require_text("broker_id", self.broker_id)
        _require_utc(self.observed_at_utc)
        if self.balance < 0 or self.equity < 0:
            raise ValueError("balance and equity cannot be negative")
        if self.margin < 0 or self.free_margin < 0:
            raise ValueError("margin values cannot be negative")


@dataclass(frozen=True, slots=True)
class PositionSnapshot:
    position_id: str
    account_id: str
    instrument_id: str
    side: PositionSide
    volume: float
    open_price: float
    current_price: float
    unrealized_pnl: float
    observed_at_utc: datetime

    def __post_init__(self) -> None:
        _require_text("position_id", self.position_id)
        _require_text("account_id", self.account_id)
        _require_text("instrument_id", self.instrument_id)
        if self.volume <= 0:
            raise ValueError("position volume must be positive")
        if self.open_price <= 0 or self.current_price <= 0:
            raise ValueError("position prices must be positive")
        _require_utc(self.observed_at_utc)


def _require_text(name: str, value: str) -> None:
    if not value.strip():
        raise ValueError(f"{name} is required")


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("timestamps must be timezone-aware UTC")
