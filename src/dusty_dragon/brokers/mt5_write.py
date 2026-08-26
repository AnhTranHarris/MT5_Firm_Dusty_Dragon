from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from dusty_dragon.domain.market import Instrument, InstrumentSpec
from dusty_dragon.domain.models import ApprovedOrder
from dusty_dragon.execution.transport import ExecutionReceipt, ExecutionStatus


@dataclass(frozen=True, slots=True)
class MT5ExecutionParameters:
    """Broker mechanics produced after capital authority, never inferred by the adapter."""

    volume: float
    reference_price: float
    stop_loss: float | None = None
    take_profit: float | None = None
    deviation_points: int = 0


@dataclass(frozen=True, slots=True)
class MT5WriteRequest:
    symbol: str
    side: str
    volume: float
    reference_price: float
    stop_loss: float | None
    take_profit: float | None
    deviation_points: int


@dataclass(frozen=True, slots=True)
class MT5RawWriteResult:
    retcode: int
    order_id: str | None
    comment: str


class MT5DryRunTransport(Protocol):
    """Test-only boundary matching the shape needed by a future order_send wrapper."""

    def submit_request(self, request: MT5WriteRequest) -> MT5RawWriteResult: ...


def build_mt5_write_request(
    order: ApprovedOrder,
    *,
    instrument: Instrument,
    spec: InstrumentSpec,
    parameters: MT5ExecutionParameters,
) -> MT5WriteRequest:
    """Validate broker mechanics without changing the approved capital decision."""

    if order.instrument_id != instrument.instrument_id:
        raise ValueError("approved order and instrument identity do not match")
    if spec.instrument_id != instrument.instrument_id:
        raise ValueError("instrument specification identity does not match")
    if order.side not in {"BUY", "SELL"}:
        raise ValueError("MT5 write boundary supports BUY or SELL only")
    if parameters.reference_price <= 0:
        raise ValueError("reference_price must be positive")
    if parameters.deviation_points < 0:
        raise ValueError("deviation_points cannot be negative")

    _validate_volume(parameters.volume, spec)
    _validate_protective_prices(order.side, parameters)

    return MT5WriteRequest(
        symbol=instrument.broker_symbol,
        side=order.side,
        volume=parameters.volume,
        reference_price=parameters.reference_price,
        stop_loss=parameters.stop_loss,
        take_profit=parameters.take_profit,
        deviation_points=parameters.deviation_points,
    )


def normalize_mt5_write_result(result: MT5RawWriteResult) -> ExecutionReceipt:
    """Normalize MT5 retcodes conservatively; unknown outcomes remain ambiguous."""

    if result.retcode in {10008, 10009}:  # TRADE_RETCODE_PLACED / DONE
        status = ExecutionStatus.ACCEPTED
    elif result.retcode in _KNOWN_REJECTION_RETCODES:
        status = ExecutionStatus.REJECTED
    else:
        status = ExecutionStatus.AMBIGUOUS

    return ExecutionReceipt(
        status=status,
        broker_order_id=result.order_id,
        message=f"MT5 retcode={result.retcode}: {result.comment}",
    )


@dataclass(slots=True)
class DryRunMT5WriteAdapter:
    """Exercise request/response behavior without importing or calling MetaTrader5."""

    transport: MT5DryRunTransport

    def submit(
        self,
        order: ApprovedOrder,
        *,
        instrument: Instrument,
        spec: InstrumentSpec,
        parameters: MT5ExecutionParameters,
    ) -> ExecutionReceipt:
        request = build_mt5_write_request(
            order,
            instrument=instrument,
            spec=spec,
            parameters=parameters,
        )
        return normalize_mt5_write_result(self.transport.submit_request(request))


def _validate_volume(volume: float, spec: InstrumentSpec) -> None:
    if volume < spec.min_volume or volume > spec.max_volume:
        raise ValueError("volume is outside broker limits")

    volume_decimal = Decimal(str(volume))
    minimum = Decimal(str(spec.min_volume))
    step = Decimal(str(spec.volume_step))
    if (volume_decimal - minimum) % step != 0:
        raise ValueError("volume does not align with broker volume_step")


def _validate_protective_prices(side: str, parameters: MT5ExecutionParameters) -> None:
    for name, value in (
        ("stop_loss", parameters.stop_loss),
        ("take_profit", parameters.take_profit),
    ):
        if value is not None and value <= 0:
            raise ValueError(f"{name} must be positive when supplied")

    price = parameters.reference_price
    if side == "BUY":
        if parameters.stop_loss is not None and parameters.stop_loss >= price:
            raise ValueError("BUY stop_loss must be below reference_price")
        if parameters.take_profit is not None and parameters.take_profit <= price:
            raise ValueError("BUY take_profit must be above reference_price")
    else:
        if parameters.stop_loss is not None and parameters.stop_loss <= price:
            raise ValueError("SELL stop_loss must be above reference_price")
        if parameters.take_profit is not None and parameters.take_profit >= price:
            raise ValueError("SELL take_profit must be below reference_price")


_KNOWN_REJECTION_RETCODES = frozenset(
    {
        10004,  # REQUOTE
        10006,  # REJECT
        10007,  # CANCEL
        10013,  # INVALID
        10014,  # INVALID_VOLUME
        10015,  # INVALID_PRICE
        10016,  # INVALID_STOPS
        10018,  # MARKET_CLOSED
        10019,  # NO_MONEY
        10020,  # PRICE_CHANGED
        10021,  # PRICE_OFF
        10024,  # TOO_MANY_REQUESTS
        10026,  # SERVER_DISABLES_AT
        10027,  # CLIENT_DISABLES_AT
        10030,  # INVALID_FILL
    }
)
