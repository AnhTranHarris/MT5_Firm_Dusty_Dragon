from datetime import UTC, datetime

import pytest

from dusty_dragon.brokers.mt5_instruments import MT5InstrumentAdapter
from dusty_dragon.domain.market import AssetClass


class FakeInstrumentTransport:
    def __init__(self, symbols: dict[str, dict[str, object]]) -> None:
        self._symbols = symbols

    def symbol_info(self, symbol: str) -> dict[str, object] | None:
        return self._symbols.get(symbol)


def valid_symbol() -> dict[str, object]:
    return {
        "digits": 5,
        "trade_tick_size": 0.00001,
        "trade_tick_value": 1.0,
        "trade_contract_size": 100_000.0,
        "volume_min": 0.01,
        "volume_max": 100.0,
        "volume_step": 0.01,
    }


def test_instrument_adapter_normalizes_mt5_specification() -> None:
    adapter = MT5InstrumentAdapter(
        FakeInstrumentTransport({"EURUSD.a": valid_symbol()}),
        broker_id="BROKER-A",
    )
    effective_at = datetime(2026, 8, 26, 9, 30, tzinfo=UTC)

    registration = adapter.read_instrument(
        "EURUSD.a",
        instrument_id="FX.EURUSD@BROKER-A",
        asset_class=AssetClass.FX,
        base_currency="EUR",
        quote_currency="USD",
        effective_from_utc=effective_at,
    )

    assert registration.instrument.broker_symbol == "EURUSD.a"
    assert registration.instrument.broker_id == "BROKER-A"
    assert registration.spec.instrument_id == "FX.EURUSD@BROKER-A"
    assert registration.spec.tick_size == pytest.approx(0.00001)
    assert registration.spec.min_volume == pytest.approx(0.01)
    assert registration.spec.effective_from_utc == effective_at


def test_unavailable_symbol_fails_closed() -> None:
    adapter = MT5InstrumentAdapter(FakeInstrumentTransport({}), broker_id="BROKER-A")

    with pytest.raises(ValueError, match="MT5 symbol is unavailable"):
        adapter.read_instrument(
            "EURUSD.a",
            instrument_id="FX.EURUSD@BROKER-A",
            asset_class=AssetClass.FX,
        )


def test_missing_required_spec_field_fails_closed() -> None:
    symbol = valid_symbol()
    del symbol["volume_step"]
    adapter = MT5InstrumentAdapter(
        FakeInstrumentTransport({"EURUSD.a": symbol}),
        broker_id="BROKER-A",
    )

    with pytest.raises(ValueError, match="missing MT5 symbol field: volume_step"):
        adapter.read_instrument(
            "EURUSD.a",
            instrument_id="FX.EURUSD@BROKER-A",
            asset_class=AssetClass.FX,
        )


def test_nonpositive_execution_spec_fails_closed() -> None:
    symbol = valid_symbol()
    symbol["volume_min"] = 0.0
    adapter = MT5InstrumentAdapter(
        FakeInstrumentTransport({"EURUSD.a": symbol}),
        broker_id="BROKER-A",
    )

    with pytest.raises(ValueError, match="must be positive: volume_min"):
        adapter.read_instrument(
            "EURUSD.a",
            instrument_id="FX.EURUSD@BROKER-A",
            asset_class=AssetClass.FX,
        )
