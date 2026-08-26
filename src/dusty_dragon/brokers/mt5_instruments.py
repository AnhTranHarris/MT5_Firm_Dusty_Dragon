from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from dusty_dragon.domain.market import AssetClass, Instrument, InstrumentSpec


class MT5InstrumentTransport(Protocol):
    """Read-only access to MT5 symbol metadata."""

    def symbol_info(self, symbol: str) -> Mapping[str, Any] | None: ...


@dataclass(frozen=True, slots=True)
class MT5InstrumentRegistration:
    instrument: Instrument
    spec: InstrumentSpec


class MT5InstrumentAdapter:
    """Normalize broker-native MT5 symbol metadata into Dusty domain objects."""

    def __init__(self, transport: MT5InstrumentTransport, broker_id: str) -> None:
        if not broker_id.strip():
            raise ValueError("broker_id is required")
        self._transport = transport
        self._broker_id = broker_id

    def read_instrument(
        self,
        broker_symbol: str,
        *,
        instrument_id: str,
        asset_class: AssetClass,
        base_currency: str | None = None,
        quote_currency: str | None = None,
        effective_from_utc: datetime | None = None,
    ) -> MT5InstrumentRegistration:
        if not broker_symbol.strip():
            raise ValueError("broker_symbol is required")
        raw = self._transport.symbol_info(broker_symbol)
        if raw is None:
            raise ValueError(f"MT5 symbol is unavailable: {broker_symbol}")

        effective_from = effective_from_utc or datetime.now(UTC)
        instrument = Instrument(
            instrument_id=instrument_id,
            broker_id=self._broker_id,
            broker_symbol=broker_symbol,
            asset_class=asset_class,
            base_currency=base_currency,
            quote_currency=quote_currency,
        )
        spec = InstrumentSpec(
            instrument_id=instrument_id,
            digits=_required_int(raw, "digits"),
            tick_size=_positive_float(raw, "trade_tick_size"),
            tick_value=_nonnegative_float(raw, "trade_tick_value"),
            contract_size=_positive_float(raw, "trade_contract_size"),
            min_volume=_positive_float(raw, "volume_min"),
            max_volume=_positive_float(raw, "volume_max"),
            volume_step=_positive_float(raw, "volume_step"),
            effective_from_utc=effective_from,
        )
        return MT5InstrumentRegistration(instrument=instrument, spec=spec)


def _required_int(raw: Mapping[str, Any], key: str) -> int:
    if key not in raw or raw[key] is None:
        raise ValueError(f"missing MT5 symbol field: {key}")
    try:
        value = int(raw[key])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid MT5 integer symbol field: {key}") from exc
    if value < 0:
        raise ValueError(f"MT5 symbol field must be nonnegative: {key}")
    return value


def _positive_float(raw: Mapping[str, Any], key: str) -> float:
    value = _number(raw, key)
    if value <= 0:
        raise ValueError(f"MT5 symbol field must be positive: {key}")
    return value


def _nonnegative_float(raw: Mapping[str, Any], key: str) -> float:
    value = _number(raw, key)
    if value < 0:
        raise ValueError(f"MT5 symbol field must be nonnegative: {key}")
    return value


def _number(raw: Mapping[str, Any], key: str) -> float:
    if key not in raw or raw[key] is None:
        raise ValueError(f"missing MT5 symbol field: {key}")
    try:
        return float(raw[key])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid MT5 numeric symbol field: {key}") from exc
