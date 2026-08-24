from datetime import UTC, datetime

import pytest

from dusty_dragon.brokers.contracts import BrokerAccountState, Position, Quote, SymbolSpec
from dusty_dragon.domain.trades import Side, TradeProposal
from dusty_dragon.trading.paper_execution import PaperExecutionAssumptions, PaperExecutionEngine


class FakeBroker:
    def connect(self) -> None:
        return None

    def close(self) -> None:
        return None

    def symbols(self):
        return ("EURUSD",)

    def symbol_spec(self, symbol: str) -> SymbolSpec:
        assert symbol == "EURUSD"
        return SymbolSpec(
            symbol="EURUSD",
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            point=0.00001,
            digits=5,
            contract_size=100_000,
            tick_size=0.00001,
            tick_value=1.0,
            profit_currency="USD",
        )

    def quote(self, symbol: str) -> Quote:
        assert symbol == "EURUSD"
        return Quote(
            symbol="EURUSD",
            captured_at=datetime(2026, 8, 24, 18, 0, tzinfo=UTC),
            bid=1.10000,
            ask=1.10020,
        )

    def bars(self, symbol: str, timeframe: str, count: int):
        raise NotImplementedError

    def account_state(self) -> BrokerAccountState:
        raise NotImplementedError

    def positions(self) -> tuple[Position, ...]:
        return ()

    def execute_paper(self, proposal: TradeProposal, volume: float):
        raise AssertionError("PaperExecutionEngine must not delegate an order to broker execution")


def proposal(side: Side) -> TradeProposal:
    if side == Side.BUY:
        stop_loss, take_profit = 1.09500, 1.11000
    else:
        stop_loss, take_profit = 1.10500, 1.09000
    return TradeProposal(
        strategy_version="paper-test-v1",
        symbol="EURUSD",
        side=side,
        entry_price=1.10010,
        stop_loss=stop_loss,
        take_profit=take_profit,
        risk_pct=0.25,
        confidence=0.65,
        timeframe="M15",
        thesis="deterministic test setup",
    )


def test_buy_fill_uses_ask_plus_slippage() -> None:
    engine = PaperExecutionEngine(
        FakeBroker(),
        PaperExecutionAssumptions(slippage_points=2.0),
    )

    result = engine.open(proposal(Side.BUY), 0.01)

    assert result.executed_price == pytest.approx(1.10022)
    assert result.spread_points == pytest.approx(20.0)
    assert result.slippage_points == 2.0


def test_sell_fill_uses_bid_minus_slippage() -> None:
    engine = PaperExecutionEngine(
        FakeBroker(),
        PaperExecutionAssumptions(slippage_points=2.0),
    )

    result = engine.open(proposal(Side.SELL), 0.01)

    assert result.executed_price == pytest.approx(1.09998)


def test_volume_rounds_down_without_increasing_exposure() -> None:
    engine = PaperExecutionEngine(FakeBroker())

    result = engine.open(proposal(Side.BUY), 0.019)

    assert result.executed_volume == 0.01


def test_half_round_turn_commission_is_recorded_at_entry() -> None:
    engine = PaperExecutionEngine(
        FakeBroker(),
        PaperExecutionAssumptions(commission_per_lot_round_turn=7.0),
    )

    result = engine.open(proposal(Side.BUY), 0.01)

    assert result.estimated_commission == pytest.approx(0.035)


def test_negative_slippage_assumption_is_rejected() -> None:
    with pytest.raises(ValueError):
        PaperExecutionAssumptions(slippage_points=-1.0)
