from dataclasses import dataclass

import pytest

from dusty_dragon.brokers.mt5_native_write import (
    MetaTrader5OrderSendTransport,
    MT5WriteCapability,
)
from dusty_dragon.brokers.mt5_write import MT5WriteRequest


@dataclass
class Result:
    retcode: int
    comment: str
    order: int = 0


@dataclass
class SymbolInfo:
    visible: bool = True
    filling_mode: int = 1
    trade_exemode: int = 0


class FakeMT5:
    TRADE_ACTION_DEAL = 1
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TIME_GTC = 0
    ORDER_FILLING_FOK = 0
    ORDER_FILLING_IOC = 1
    ORDER_FILLING_RETURN = 2
    SYMBOL_FILLING_FOK = 1
    SYMBOL_FILLING_IOC = 2
    SYMBOL_TRADE_EXECUTION_MARKET = 2

    def __init__(self) -> None:
        self.check_calls: list[dict[str, object]] = []
        self.send_calls: list[dict[str, object]] = []
        self.symbol = SymbolInfo()
        self.check_result: Result | None = Result(retcode=0, comment="Done")
        self.send_result: Result | None = Result(retcode=10009, comment="Done", order=42)

    def symbol_info(self, symbol: str) -> SymbolInfo | None:
        return self.symbol if symbol == "EURUSD" else None

    def order_check(self, request: dict[str, object]) -> Result | None:
        self.check_calls.append(request)
        return self.check_result

    def order_send(self, request: dict[str, object]) -> Result | None:
        self.send_calls.append(request)
        return self.send_result

    def last_error(self) -> object:
        return (1, "fake error")


def request() -> MT5WriteRequest:
    return MT5WriteRequest(
        symbol="EURUSD",
        side="BUY",
        volume=0.01,
        reference_price=1.1,
        stop_loss=1.09,
        take_profit=1.12,
        deviation_points=10,
    )


def test_native_transport_is_disabled_by_default() -> None:
    mt5 = FakeMT5()
    transport = MetaTrader5OrderSendTransport(mt5)

    with pytest.raises(PermissionError, match="disabled"):
        transport.submit_request(request())

    assert mt5.check_calls == []
    assert mt5.send_calls == []


def test_native_transport_checks_before_send() -> None:
    mt5 = FakeMT5()
    transport = MetaTrader5OrderSendTransport(
        mt5,
        capability=MT5WriteCapability(enabled=True),
        magic=314159,
    )

    result = transport.submit_request(request())

    assert len(mt5.check_calls) == 1
    assert len(mt5.send_calls) == 1
    assert mt5.check_calls[0] == mt5.send_calls[0]
    assert mt5.send_calls[0]["type_filling"] == mt5.ORDER_FILLING_FOK
    assert mt5.send_calls[0]["magic"] == 314159
    assert result.order_id == "42"


def test_order_check_rejection_blocks_order_send() -> None:
    mt5 = FakeMT5()
    mt5.check_result = Result(retcode=10019, comment="No money")
    transport = MetaTrader5OrderSendTransport(mt5, MT5WriteCapability(enabled=True))

    with pytest.raises(ValueError, match="order_check rejected"):
        transport.submit_request(request())

    assert len(mt5.check_calls) == 1
    assert mt5.send_calls == []


def test_missing_order_check_result_blocks_order_send() -> None:
    mt5 = FakeMT5()
    mt5.check_result = None
    transport = MetaTrader5OrderSendTransport(mt5, MT5WriteCapability(enabled=True))

    with pytest.raises(RuntimeError, match="order_check returned no result"):
        transport.submit_request(request())

    assert mt5.send_calls == []


def test_market_execution_without_supported_filling_mode_fails_closed() -> None:
    mt5 = FakeMT5()
    mt5.symbol = SymbolInfo(
        visible=True,
        filling_mode=0,
        trade_exemode=mt5.SYMBOL_TRADE_EXECUTION_MARKET,
    )
    transport = MetaTrader5OrderSendTransport(mt5, MT5WriteCapability(enabled=True))

    with pytest.raises(ValueError, match="no supported filling mode"):
        transport.submit_request(request())

    assert mt5.check_calls == []
    assert mt5.send_calls == []


def test_non_market_execution_can_use_return_filling() -> None:
    mt5 = FakeMT5()
    mt5.symbol = SymbolInfo(visible=True, filling_mode=0, trade_exemode=0)
    transport = MetaTrader5OrderSendTransport(mt5, MT5WriteCapability(enabled=True))

    transport.submit_request(request())

    assert mt5.send_calls[0]["type_filling"] == mt5.ORDER_FILLING_RETURN


def test_hidden_symbol_fails_before_order_check() -> None:
    mt5 = FakeMT5()
    mt5.symbol.visible = False
    transport = MetaTrader5OrderSendTransport(mt5, MT5WriteCapability(enabled=True))

    with pytest.raises(PermissionError, match="not visible"):
        transport.submit_request(request())

    assert mt5.check_calls == []
    assert mt5.send_calls == []
