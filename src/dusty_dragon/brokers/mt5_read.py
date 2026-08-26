from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from dusty_dragon.domain.accounts import AccountSnapshot, PositionSide, PositionSnapshot
from dusty_dragon.domain.market import AccountEnvironment


class MT5ReadTransport(Protocol):
    """Minimal read-only transport implemented by the future MetaTrader5 wrapper."""

    def account_info(self) -> Mapping[str, Any]: ...

    def positions_get(self) -> Sequence[Mapping[str, Any]]: ...


@dataclass(frozen=True, slots=True)
class MT5ReadContext:
    desk_id: str
    account_id: str
    broker_id: str
    environment: AccountEnvironment
    symbol_to_instrument: Mapping[str, str]

    def __post_init__(self) -> None:
        if not self.desk_id.strip():
            raise ValueError("desk_id is required")
        if not self.account_id.strip():
            raise ValueError("account_id is required")
        if not self.broker_id.strip():
            raise ValueError("broker_id is required")


@dataclass(frozen=True, slots=True)
class BrokerReadState:
    account: AccountSnapshot
    positions: tuple[PositionSnapshot, ...]


class MT5ReadAdapter:
    """Normalizes MT5 observations into Dusty-owned broker-neutral domain objects."""

    def __init__(self, transport: MT5ReadTransport, context: MT5ReadContext) -> None:
        self._transport = transport
        self._context = context

    def read_state(self, observed_at_utc: datetime | None = None) -> BrokerReadState:
        observed_at = observed_at_utc or datetime.now(UTC)
        account_raw = self._transport.account_info()
        positions_raw = self._transport.positions_get()

        account = AccountSnapshot(
            account_id=self._context.account_id,
            desk_id=self._context.desk_id,
            broker_id=self._context.broker_id,
            environment=self._context.environment,
            observed_at_utc=observed_at,
            balance=_required_float(account_raw, "balance"),
            equity=_required_float(account_raw, "equity"),
            margin=_required_float(account_raw, "margin"),
            free_margin=_required_float(account_raw, "margin_free"),
        )
        positions = tuple(
            self._normalize_position(raw, observed_at)
            for raw in sorted(positions_raw, key=lambda item: str(item.get("ticket", "")))
        )
        return BrokerReadState(account=account, positions=positions)

    def _normalize_position(
        self,
        raw: Mapping[str, Any],
        observed_at_utc: datetime,
    ) -> PositionSnapshot:
        symbol = _required_text(raw, "symbol")
        try:
            instrument_id = self._context.symbol_to_instrument[symbol]
        except KeyError as exc:
            raise ValueError(f"unregistered MT5 symbol: {symbol}") from exc

        position_type = _required_int(raw, "type")
        if position_type == 0:
            side = PositionSide.LONG
        elif position_type == 1:
            side = PositionSide.SHORT
        else:
            raise ValueError(f"unsupported MT5 position type: {position_type}")

        return PositionSnapshot(
            position_id=str(_required_int(raw, "ticket")),
            account_id=self._context.account_id,
            instrument_id=instrument_id,
            side=side,
            volume=_required_float(raw, "volume"),
            open_price=_required_float(raw, "price_open"),
            current_price=_required_float(raw, "price_current"),
            unrealized_pnl=_required_float(raw, "profit"),
            observed_at_utc=observed_at_utc,
        )


def _required_text(raw: Mapping[str, Any], key: str) -> str:
    value = str(raw.get(key, "")).strip()
    if not value:
        raise ValueError(f"missing MT5 field: {key}")
    return value


def _required_float(raw: Mapping[str, Any], key: str) -> float:
    if key not in raw or raw[key] is None:
        raise ValueError(f"missing MT5 field: {key}")
    try:
        return float(raw[key])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid MT5 numeric field: {key}") from exc


def _required_int(raw: Mapping[str, Any], key: str) -> int:
    if key not in raw or raw[key] is None:
        raise ValueError(f"missing MT5 field: {key}")
    try:
        return int(raw[key])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid MT5 integer field: {key}") from exc
