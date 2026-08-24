from datetime import UTC, datetime, timedelta

import pytest

from dusty_dragon.brokers.contracts import MarketBar, Quote
from dusty_dragon.intelligence.kronos_forecast import KronosForecast
from dusty_dragon.intelligence.research_signal import (
    GeneralistResearchEngine,
    SignalDecision,
)


def bars(*, rising: bool = True) -> list[MarketBar]:
    start = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
    result = []
    for index in range(10):
        delta = index * 0.0002 * (1 if rising else -1)
        close = 1.1000 + delta
        result.append(
            MarketBar(
                symbol="EURUSD",
                timeframe="M15",
                opened_at=start + timedelta(minutes=15 * index),
                open=close - 0.0001,
                high=close + 0.0002,
                low=close - 0.0002,
                close=close,
                tick_volume=100 + index,
                spread_points=8.0,
                real_volume=0.0,
            )
        )
    return result


def forecast(return_pct: float) -> KronosForecast:
    starting = 1.1018
    predicted = starting * (1 + return_pct / 100)
    return KronosForecast(
        symbol="EURUSD",
        timeframe="M15",
        horizon_bars=4,
        starting_close=starting,
        predicted_close=predicted,
        predicted_return_pct=return_pct,
        predicted_high=max(starting, predicted) + 0.0005,
        predicted_low=min(starting, predicted) - 0.0005,
        forecast_rows=4,
        volume_source="tick_volume",
    )


def test_agreeing_bullish_evidence_produces_buy_signal():
    engine = GeneralistResearchEngine()
    signal = engine.evaluate(bars(rising=True), forecast(0.20))

    assert signal.decision == SignalDecision.BUY
    assert signal.agreement is True
    assert signal.confidence >= engine.minimum_confidence


def test_disagreement_abstains_instead_of_forcing_trade():
    engine = GeneralistResearchEngine()
    signal = engine.evaluate(bars(rising=False), forecast(0.20))

    assert signal.decision == SignalDecision.ABSTAIN
    assert signal.agreement is False


def test_weak_forecast_abstains():
    engine = GeneralistResearchEngine()
    signal = engine.evaluate(bars(rising=True), forecast(0.01))

    assert signal.decision == SignalDecision.ABSTAIN


def test_signal_can_become_broker_neutral_trade_proposal():
    engine = GeneralistResearchEngine()
    signal = engine.evaluate(bars(rising=True), forecast(0.20))
    quote = Quote(
        symbol="EURUSD",
        captured_at=datetime(2026, 8, 24, 15, 0, tzinfo=UTC),
        bid=1.1018,
        ask=1.1020,
    )

    proposal = engine.proposal_from_signal(signal, quote, risk_pct=0.25)

    assert proposal is not None
    assert proposal.side.value == "buy"
    assert proposal.entry_price == quote.ask
    assert proposal.reward_to_risk == pytest.approx(2.0)
    assert proposal.evidence["evidence_agreement"] is True


def test_abstain_signal_cannot_become_proposal():
    engine = GeneralistResearchEngine()
    signal = engine.evaluate(bars(rising=False), forecast(0.20))
    quote = Quote(
        symbol="EURUSD",
        captured_at=datetime(2026, 8, 24, 15, 0, tzinfo=UTC),
        bid=1.1000,
        ask=1.1002,
    )

    assert engine.proposal_from_signal(signal, quote, risk_pct=0.25) is None
