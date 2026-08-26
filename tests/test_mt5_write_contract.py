from datetime import UTC, datetime

import pytest

from dusty_dragon.brokers.mt5_write import (
    DryRunMT5WriteAdapter,
    MT5ExecutionParameters,
    MT5RawWriteResult,
    build_mt5_write_request,
    normalize_mt5_write_result,
)
from dusty_dragon.domain.market import AssetClass, Instrument, InstrumentSpec
from dusty_dragon.domain.models import ApprovedOrder
from dusty_dragon.execution.transport import ExecutionStatus


class FakeDryRunTransport:
    def __init__(self, result: MT5RawWriteResult) -> None:
        self.result = result
        self.requests = []

    def submit_request(self, request):
        self.requests.append(request)
        return self.result


def instrument() -> Instrument:
    return Instrument(
        instrument_id="FX.EURUSD@B1",
        broker_id="B1",
        broker_symbol="EURUSD",
        asset_class=AssetClass.FX,
        base_currency="EUR",
        quote_currency="USD",
    )


def spec() -> InstrumentSpec:
    return InstrumentSpec(
        instrument_id="FX.EURUSD@B1",
        digits=5,
        tick_size=0.00001,
        tick_value=1.0,
        contract_size=100000.0,
        min_volume=0.01,
        max_volume=100.0,
        volume_step=0.01,
        effective_from_utc=datetime(2026, 8, 26, 15, 0, tzinfo=UTC),
    )


def approved_order(side: str = "BUY") -> ApprovedOrder:
    return ApprovedOrder(
        desk_id="GENERALIST-01",
        instrument_id="FX.EURUSD@B1",
        side=side,
        approved_risk_fraction=0.01,
        policy_id="financial_v1",
    )


def test_request_builder_preserves_validated_broker_mechanics() -> None:
    request = build_mt5_write_request(
        approved_order(),
        instrument=instrument(),
        spec=spec(),
        parameters=MT5ExecutionParameters(
            volume=0.03,
            reference_price=1.17000,
            stop_loss=1.16500,
            take_profit=1.18000,
            deviation_points=10,
        ),
    )

    assert request.symbol == "EURUSD"
    assert request.side == "BUY"
    assert request.volume == 0.03
    assert request.stop_loss == 1.16500
    assert request.take_profit == 1.18000


def test_invalid_volume_step_fails_closed_without_rounding() -> None:
    with pytest.raises(ValueError, match="volume_step"):
        build_mt5_write_request(
            approved_order(),
            instrument=instrument(),
            spec=spec(),
            parameters=MT5ExecutionParameters(volume=0.015, reference_price=1.17),
        )


def test_invalid_buy_stop_fails_closed() -> None:
    with pytest.raises(ValueError, match="BUY stop_loss"):
        build_mt5_write_request(
            approved_order(),
            instrument=instrument(),
            spec=spec(),
            parameters=MT5ExecutionParameters(
                volume=0.01,
                reference_price=1.17,
                stop_loss=1.18,
            ),
        )


def test_instrument_identity_mismatch_fails_closed() -> None:
    wrong = Instrument(
        instrument_id="FX.GBPUSD@B1",
        broker_id="B1",
        broker_symbol="GBPUSD",
        asset_class=AssetClass.FX,
        base_currency="GBP",
        quote_currency="USD",
    )
    with pytest.raises(ValueError, match="identity"):
        build_mt5_write_request(
            approved_order(),
            instrument=wrong,
            spec=spec(),
            parameters=MT5ExecutionParameters(volume=0.01, reference_price=1.17),
        )


def test_retcode_normalization_is_conservative() -> None:
    accepted = normalize_mt5_write_result(MT5RawWriteResult(10009, "42", "done"))
    rejected = normalize_mt5_write_result(MT5RawWriteResult(10019, None, "no money"))
    ambiguous = normalize_mt5_write_result(MT5RawWriteResult(19999, None, "unknown"))

    assert accepted.status is ExecutionStatus.ACCEPTED
    assert accepted.broker_order_id == "42"
    assert rejected.status is ExecutionStatus.REJECTED
    assert ambiguous.status is ExecutionStatus.AMBIGUOUS


def test_dry_run_adapter_calls_fake_transport_once() -> None:
    transport = FakeDryRunTransport(MT5RawWriteResult(10008, "77", "placed"))
    adapter = DryRunMT5WriteAdapter(transport)

    receipt = adapter.submit(
        approved_order("SELL"),
        instrument=instrument(),
        spec=spec(),
        parameters=MT5ExecutionParameters(
            volume=0.02,
            reference_price=1.17,
            stop_loss=1.18,
            take_profit=1.16,
        ),
    )

    assert receipt.status is ExecutionStatus.ACCEPTED
    assert receipt.broker_order_id == "77"
    assert len(transport.requests) == 1
