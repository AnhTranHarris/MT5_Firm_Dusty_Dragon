from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class AccountEnvironment(StrEnum):
    DEMO = "DEMO"
    LIVE = "LIVE"


class AssetClass(StrEnum):
    FX = "FX"
    METAL = "METAL"
    ENERGY = "ENERGY"
    INDEX = "INDEX"
    COMMODITY = "COMMODITY"
    CRYPTO = "CRYPTO"
    EQUITY = "EQUITY"
    OTHER = "OTHER"


class VolumeType(StrEnum):
    TICK = "TICK"
    REAL = "REAL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class Broker:
    broker_id: str
    name: str

    def __post_init__(self) -> None:
        if not self.broker_id.strip():
            raise ValueError("broker_id is required")
        if not self.name.strip():
            raise ValueError("broker name is required")


@dataclass(frozen=True, slots=True)
class Instrument:
    instrument_id: str
    broker_id: str
    broker_symbol: str
    asset_class: AssetClass
    base_currency: str | None = None
    quote_currency: str | None = None

    def __post_init__(self) -> None:
        if not self.instrument_id.strip():
            raise ValueError("instrument_id is required")
        if not self.broker_id.strip():
            raise ValueError("broker_id is required")
        if not self.broker_symbol.strip():
            raise ValueError("broker_symbol is required")


@dataclass(frozen=True, slots=True)
class InstrumentSpec:
    instrument_id: str
    digits: int
    tick_size: float
    tick_value: float
    contract_size: float
    min_volume: float
    max_volume: float
    volume_step: float
    effective_from_utc: datetime

    def __post_init__(self) -> None:
        if self.digits < 0:
            raise ValueError("digits cannot be negative")
        for name, value in (
            ("tick_size", self.tick_size),
            ("contract_size", self.contract_size),
            ("min_volume", self.min_volume),
            ("max_volume", self.max_volume),
            ("volume_step", self.volume_step),
        ):
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if self.tick_value < 0:
            raise ValueError("tick_value cannot be negative")
        if self.max_volume < self.min_volume:
            raise ValueError("max_volume cannot be below min_volume")
        _require_utc(self.effective_from_utc)


@dataclass(frozen=True, slots=True)
class MarketBar:
    instrument_id: str
    timeframe: str
    ts_open_utc: datetime
    ts_close_utc: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    volume_type: VolumeType
    source: str
    is_complete: bool = True

    def __post_init__(self) -> None:
        _require_utc(self.ts_open_utc)
        _require_utc(self.ts_close_utc)
        if self.ts_close_utc <= self.ts_open_utc:
            raise ValueError("bar close timestamp must be after open timestamp")
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise ValueError("OHLC prices must be positive")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high price violates OHLC geometry")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low price violates OHLC geometry")
        if self.volume < 0:
            raise ValueError("volume cannot be negative")


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("timestamps must be timezone-aware UTC")
