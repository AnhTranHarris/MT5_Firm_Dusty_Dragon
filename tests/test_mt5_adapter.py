from types import SimpleNamespace

import pytest

from dusty_dragon.brokers.mt5_adapter import MT5BrokerAdapter, MT5UnavailableError
from dusty_dragon.domain.trades import Side, TradeProposal


class FakeMT5:
    POSITION_TYPE_BUY = 0
    TIMEFRAME_M15 = 15

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

    def copy_rates_from_pos(self, symbol, timeframe, start_pos, count):
        if symbol != "EURUSD" or timeframe != self.TIMEFRAME_M15:
            return None
        rows = [
            {
                "time": 1_700_000_000,
                "open": 1.1000,
                "high": 1.1010,
                "low": 1.0990,
                "close": 1.1005,
                "tick_volume": 100,
                "spread": 20,
                "real_volume": 0,
            },
            {
                "time": 1_700_000_900,
                "open": 1.1005,
                "high": 1.1020,
                "low": 1.1000,
                "close": 1.1015,
                "tick_volume": 120,
                "spread": 18,
                "real_volume": 0,
            },
        ]
        return rows[:count]

    def account_info(self):
        return SimpleNamespace(
            login=123456,
            currency="USD",
            balance=10_000.0,
            equity=10_025.0,
            margin=25.0,
            margin_free=10_000.0,
            margin_level=40_100.0,
        )

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


def connected_adapter() -> MT5BrokerAdapter:
    adapter = MT5BrokerAdapter(mt5_module=FakeMT5())
    adapter.connect()
    return adapter


def test_requires_connection():
    adapter = MT5BrokerAdapter(mt5_module=FakeMT5())
    with pytest.raises(MT5UnavailableError):
        adapter.symbols()


def test_symbol_discovery_and_specification():
    adapter = connected_adapter()

    assert adapter.symbols() == ("EURUSD", "USDJPY")
    spec = adapter.symbol_spec("EURUSD")
    assert spec.volume_min == 0.01
    assert spec.volume_step == 0.01


def test_read_only_market_bars_are_normalized():
    adapter = connected_adapter()

    bars = adapter.bars("EURUSD", "M15", 2)

    assert len(bars) == 2
    assert bars[0].symbol == "EURUSD"
    assert bars[0].timeframe == "M15"
    assert bars[1].close == 1.1015
    assert bars[1].spread_points == 18


def test_account_state_is_platform_neutral():
    adapter = connected_adapter()

    account = adapter.account_state()

    assert account.login == 123456
    assert account.currency == "USD"
    assert account.balance == 10_000.0
    assert account.equity == 10_025.0


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
    adapter = connected_adapter()

    result = adapter.execute_paper(proposal(), 0.001)
    assert result.executed_volume == 0.01


def test_volume_step_normalization_never_increases_requested_exposure():
    adapter = connected_adapter()

    result = adapter.execute_paper(proposal(), 0.019)
    assert result.executed_volume == 0.01


def test_unknown_symbol_fails_closed():
    adapter = connected_adapter()

    with pytest.raises(MT5UnavailableError):
        adapter.symbol_spec("NOTREAL")


def test_unsupported_timeframe_fails_closed():
    adapter = connected_adapter()

    with pytest.raises(ValueError):
        adapter.bars("EURUSD", "M2", 10)
