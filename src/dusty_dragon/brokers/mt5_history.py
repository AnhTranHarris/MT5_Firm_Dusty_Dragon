from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol


class BrokerOrderHistoryStatus(StrEnum):
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class BrokerOrderHistoryRecord:
    broker_order_id: str
    status: BrokerOrderHistoryStatus
    observed_at_utc: datetime


@dataclass(frozen=True, slots=True)
class BrokerDealHistoryRecord:
    broker_deal_id: str
    broker_order_id: str
    observed_at_utc: datetime


@dataclass(frozen=True, slots=True)
class BrokerExecutionHistory:
    orders: tuple[BrokerOrderHistoryRecord, ...]
    deals: tuple[BrokerDealHistoryRecord, ...]
    queried_at_utc: datetime


class MT5HistoryTransport(Protocol):
    """Read-only MT5 history boundary used to verify uncertain execution outcomes."""

    def history_orders_get(self, date_from: datetime, date_to: datetime) -> Sequence[Mapping[str, Any]]: ...

    def history_deals_get(self, date_from: datetime, date_to: datetime) -> Sequence[Mapping[str, Any]]: ...


class MT5HistoryAdapter:
    """Normalize broker order/deal history without granting any write authority."""

    def __init__(self, transport: MT5HistoryTransport) -> None:
        self._transport = transport

    def read_execution_history(
        self,
        *,
        date_from_utc: datetime,
        date_to_utc: datetime,
    ) -> BrokerExecutionHistory:
        _require_utc(date_from_utc, "date_from_utc")
        _require_utc(date_to_utc, "date_to_utc")
        if date_to_utc < date_from_utc:
            raise ValueError("date_to_utc must not precede date_from_utc")

        orders = tuple(
            self._normalize_order(raw)
            for raw in self._transport.history_orders_get(date_from_utc, date_to_utc)
        )
        deals = tuple(
            self._normalize_deal(raw)
            for raw in self._transport.history_deals_get(date_from_utc, date_to_utc)
        )
        return BrokerExecutionHistory(
            orders=orders,
            deals=deals,
            queried_at_utc=date_to_utc,
        )

    def _normalize_order(self, raw: Mapping[str, Any]) -> BrokerOrderHistoryRecord:
        return BrokerOrderHistoryRecord(
            broker_order_id=str(_required_int(raw, "ticket")),
            status=_normalize_order_status(_required_int(raw, "state")),
            observed_at_utc=_timestamp_utc(raw, "time_done"),
        )

    def _normalize_deal(self, raw: Mapping[str, Any]) -> BrokerDealHistoryRecord:
        return BrokerDealHistoryRecord(
            broker_deal_id=str(_required_int(raw, "ticket")),
            broker_order_id=str(_required_int(raw, "order")),
            observed_at_utc=_timestamp_utc(raw, "time"),
        )


def _normalize_order_status(state: int) -> BrokerOrderHistoryStatus:
    # MT5 ORDER_STATE_FILLED=4, CANCELED=2, REJECTED=3. Other terminal/nonterminal states
    # remain UNKNOWN so Dusty never manufactures certainty from an unfamiliar broker state.
    if state == 4:
        return BrokerOrderHistoryStatus.FILLED
    if state == 2:
        return BrokerOrderHistoryStatus.CANCELED
    if state == 3:
        return BrokerOrderHistoryStatus.REJECTED
    return BrokerOrderHistoryStatus.UNKNOWN


def _timestamp_utc(raw: Mapping[str, Any], key: str) -> datetime:
    timestamp = _required_int(raw, key)
    return datetime.fromtimestamp(timestamp, tz=UTC)


def _required_int(raw: Mapping[str, Any], key: str) -> int:
    if key not in raw or raw[key] is None:
        raise ValueError(f"missing MT5 history field: {key}")
    try:
        return int(raw[key])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid MT5 history integer field: {key}") from exc


def _require_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be timezone-aware UTC")
