from datetime import UTC, datetime

import pytest

from dusty_dragon.brokers.mt5_read import MT5ReadAdapter, MT5ReadContext
from dusty_dragon.domain.accounts import PositionSide
from dusty_dragon.domain.market import AccountEnvironment


class FakeMT5Transport:
    def __init__(self, account: dict[str, object], positions: list[dict[str, object]]) -> None:
        self._account = account
        self._positions = positions

    def account_info(self) -> dict[str, object]:
        return self._account

    def positions_get(self) -> list[dict[str, object]]:
        return self._positions


def context() -> MT5ReadContext:
    return MT5ReadContext(
        desk_id="GENERALIST-01",
        account_id="BROKER-A-DEMO-01",
        broker_id="BROKER-A",
        environment=AccountEnvironment.DEMO,
        symbol_to_instrument={"EURUSD.a": "FX.EURUSD@BROKER-A"},
    )


def account_info() -> dict[str, object]:
    return {
        "balance": 20_000.0,
        "equity": 20_025.0,
        "margin": 100.0,
        "margin_free": 19_925.0,
    }


def test_adapter_normalizes_account_and_positions() -> None:
    transport = FakeMT5Transport(
        account_info(),
        [
            {
                "ticket": 42,
                "symbol": "EURUSD.a",
                "type": 0,
                "volume": 0.01,
                "price_open": 1.1000,
                "price_current": 1.1025,
                "profit": 25.0,
            }
        ],
    )
    observed_at = datetime(2026, 8, 26, 9, 0, tzinfo=UTC)

    state = MT5ReadAdapter(transport, context()).read_state(observed_at)

    assert state.account.desk_id == "GENERALIST-01"
    assert state.account.equity == 20_025.0
    assert len(state.positions) == 1
    assert state.positions[0].instrument_id == "FX.EURUSD@BROKER-A"
    assert state.positions[0].side is PositionSide.LONG


def test_short_position_is_normalized() -> None:
    transport = FakeMT5Transport(
        account_info(),
        [
            {
                "ticket": 43,
                "symbol": "EURUSD.a",
                "type": 1,
                "volume": 0.01,
                "price_open": 1.1000,
                "price_current": 1.0990,
                "profit": 10.0,
            }
        ],
    )

    state = MT5ReadAdapter(transport, context()).read_state(
        datetime(2026, 8, 26, 9, 0, tzinfo=UTC)
    )

    assert state.positions[0].side is PositionSide.SHORT


def test_unknown_symbol_fails_closed() -> None:
    transport = FakeMT5Transport(
        account_info(),
        [
            {
                "ticket": 44,
                "symbol": "UNKNOWN",
                "type": 0,
                "volume": 0.01,
                "price_open": 1.0,
                "price_current": 1.0,
                "profit": 0.0,
            }
        ],
    )

    with pytest.raises(ValueError, match="unregistered MT5 symbol"):
        MT5ReadAdapter(transport, context()).read_state(datetime(2026, 8, 26, 9, 0, tzinfo=UTC))


def test_missing_account_field_fails_closed() -> None:
    broken = account_info()
    del broken["equity"]
    transport = FakeMT5Transport(broken, [])

    with pytest.raises(ValueError, match="missing MT5 field: equity"):
        MT5ReadAdapter(transport, context()).read_state(datetime(2026, 8, 26, 9, 0, tzinfo=UTC))


def test_unsupported_position_type_fails_closed() -> None:
    transport = FakeMT5Transport(
        account_info(),
        [
            {
                "ticket": 45,
                "symbol": "EURUSD.a",
                "type": 9,
                "volume": 0.01,
                "price_open": 1.0,
                "price_current": 1.0,
                "profit": 0.0,
            }
        ],
    )

    with pytest.raises(ValueError, match="unsupported MT5 position type"):
        MT5ReadAdapter(transport, context()).read_state(datetime(2026, 8, 26, 9, 0, tzinfo=UTC))
