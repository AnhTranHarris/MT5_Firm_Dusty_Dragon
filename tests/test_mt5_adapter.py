from types import SimpleNamespace

import pytest

from dusty_dragon.brokers.mt5_adapter import MT5BrokerAdapter, MT5UnavailableError
from dusty_dragon.domain.trades import Side, TradeProposal


class FakeMT5:
    POSITION_TYPE_BUY = 0

    def __init__(self) -> None:
        self.initialized = False
        self.shutdown_called = False

    def initialize(self, **kwargs):
        self.initialized = True
        self.initialize_kwargs = kwargs
        return True

    def shutdown(self):
        self.shutdown_called = True

    def last_error(self):
        return (0, "ok")

    def symbols_get(self):
        return [SimpleNamespace(name="USDJPY"), SimpleNamespace(name="EURUSD")]

    def symbol_info(self, symbol):
        if symbol != "EURUSD":
            return None
        return SimpleNamespace(
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            point=0.00001,
            digits=5,
            trade_mode=4,
        )

    def symbol_info_tick(self, symbol):
        if symbol != "EURUSD":
            return None
        return SimpleNamespace(time=1_700_000_000, bid=1.1000, ask=1.1002)

    def positions_get(self):
        return [
            SimpleNamespace(
                ticket=10,
                symbol="EURUSD",
                type=0,
                volume=0.01,
                price_open=1.09,
                sl=1.08,
                tp=1.12,
                profit=12.5,
            )
        ]


def proposal() -> TradeProposal:
    return TradeProposal(
        strategy_version="test-v1",
        symbol="EURUSD",
        side=Side.BUY,
        entry_price=1.1002,
        stop_loss=1.0950,
        take_profit=1.1100,
        risk_pct=0.25,
        confidence=0.70,
        timeframe="M15",
        thesis="test",
    )


def test_requires_connection():
    adapter = MT5BrokerAdapter(mt5_module=FakeMT5())
    with pytest.raises(MT5UnavailableError):
        adapter.symbols()


def test_symbol_discovery_and_specification():
    fake = FakeMT5()
    adapter = MT5BrokerAdapter(mt5_module=fake)
    adapter.connect()

    assert adapter.symbols() == ("EURUSD", "USDJPY")
    spec = adapter.symbol_spec("EURUSD")
    assert spec.volume_min == 0.01
    assert spec.volume_step == 0.01


def test_paper_execution_never_calls_order_send():
    fake = FakeMT5()
    adapter = MT5BrokerAdapter(mt5_module=fake)
    adapter.connect()

    result = adapter.execute_paper(proposal(), 0.01)

    assert result.accepted is True
    assert result.executed_volume == 0.01
    assert result.executed_price == 1.1002
    assert not hasattr(fake, "order_send")


def test_volume_below_minimum_is_raised_to_broker_minimum():
    fake = FakeMT5()
    adapter = MT5BrokerAdapter(mt5_module=fake)
    adapter.connect()

    result = adapter.execute_paper(proposal(), 0.001)
    assert result.executed_volume == 0.01


def test_unknown_symbol_fails_closed():
    fake = FakeMT5()
    adapter = MT5BrokerAdapter(mt5_module=fake)
    adapter.connect()

    with pytest.raises(MT5UnavailableError):
        adapter.symbol_spec("NOTREAL")
