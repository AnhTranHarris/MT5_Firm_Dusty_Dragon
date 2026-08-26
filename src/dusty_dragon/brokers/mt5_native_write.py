from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from dusty_dragon.brokers.mt5_write import MT5RawWriteResult, MT5WriteRequest


class MT5PreflightError(RuntimeError):
    """Request was blocked before MT5 order_send could be invoked."""


class MT5SubmissionUncertainError(RuntimeError):
    """MT5 order_send may have reached the broker, but the client lacks certainty."""


class MetaTrader5WriteModule(Protocol):
    TRADE_ACTION_DEAL: int
    ORDER_TYPE_BUY: int
    ORDER_TYPE_SELL: int
    ORDER_TIME_GTC: int
    ORDER_FILLING_FOK: int
    ORDER_FILLING_IOC: int
    ORDER_FILLING_RETURN: int
    SYMBOL_FILLING_FOK: int
    SYMBOL_FILLING_IOC: int
    SYMBOL_TRADE_EXECUTION_MARKET: int

    def symbol_info(self, symbol: str) -> Any: ...

    def order_check(self, request: dict[str, object]) -> Any: ...

    def order_send(self, request: dict[str, object]) -> Any: ...

    def last_error(self) -> object: ...


@dataclass(frozen=True, slots=True)
class MT5WriteCapability:
    """Explicit runtime capability; broker writes are disabled by default."""

    enabled: bool = False


@dataclass(slots=True)
class MetaTrader5OrderSendTransport:
    """Thin native MT5 transport with preflight checks and no capital authority."""

    mt5: MetaTrader5WriteModule
    capability: MT5WriteCapability = MT5WriteCapability()
    magic: int = 0
    comment: str = "dusty-dragon-demo"

    def submit_request(self, request: MT5WriteRequest) -> MT5RawWriteResult:
        if not self.capability.enabled:
            raise PermissionError("native MT5 write capability is disabled")

        native_request = self._build_native_request(request)
        try:
            check_result = self.mt5.order_check(native_request)
        except Exception as exc:
            raise MT5PreflightError(f"MT5 order_check failed: {exc}") from exc
        if check_result is None:
            raise MT5PreflightError(
                f"MT5 order_check returned no result: {self.mt5.last_error()!r}"
            )
        if int(check_result.retcode) != 0:
            raise MT5PreflightError(
                "MT5 order_check rejected request: "
                f"retcode={check_result.retcode}, comment={check_result.comment}"
            )

        try:
            result = self.mt5.order_send(native_request)
        except Exception as exc:
            raise MT5SubmissionUncertainError(f"MT5 order_send failed: {exc}") from exc
        if result is None:
            raise MT5SubmissionUncertainError(
                f"MT5 order_send returned no result: {self.mt5.last_error()!r}"
            )

        order_value = getattr(result, "order", None)
        order_id = None if order_value in {None, 0} else str(order_value)
        return MT5RawWriteResult(
            retcode=int(result.retcode),
            order_id=order_id,
            comment=str(getattr(result, "comment", "")),
        )

    def _build_native_request(self, request: MT5WriteRequest) -> dict[str, object]:
        symbol_info = self.mt5.symbol_info(request.symbol)
        if symbol_info is None:
            raise MT5PreflightError(f"MT5 symbol is unavailable: {request.symbol}")
        if not bool(getattr(symbol_info, "visible", False)):
            raise PermissionError(f"MT5 symbol is not visible in Market Watch: {request.symbol}")

        order_type = (
            self.mt5.ORDER_TYPE_BUY if request.side == "BUY" else self.mt5.ORDER_TYPE_SELL
        )
        native_request: dict[str, object] = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": request.symbol,
            "volume": request.volume,
            "type": order_type,
            "price": request.reference_price,
            "deviation": request.deviation_points,
            "magic": self.magic,
            "comment": self.comment,
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self._select_filling_mode(symbol_info),
        }
        if request.stop_loss is not None:
            native_request["sl"] = request.stop_loss
        if request.take_profit is not None:
            native_request["tp"] = request.take_profit
        return native_request

    def _select_filling_mode(self, symbol_info: Any) -> int:
        filling_flags = int(getattr(symbol_info, "filling_mode", 0))
        if filling_flags & self.mt5.SYMBOL_FILLING_FOK:
            return self.mt5.ORDER_FILLING_FOK
        if filling_flags & self.mt5.SYMBOL_FILLING_IOC:
            return self.mt5.ORDER_FILLING_IOC

        execution_mode = int(getattr(symbol_info, "trade_exemode", -1))
        if execution_mode != self.mt5.SYMBOL_TRADE_EXECUTION_MARKET:
            return self.mt5.ORDER_FILLING_RETURN

        raise MT5PreflightError("MT5 symbol exposes no supported filling mode")
