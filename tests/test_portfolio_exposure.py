from dusty_dragon.brokers.contracts import Position
from dusty_dragon.domain.trades import Side, TradeProposal
from dusty_dragon.portfolio.exposure import (
    FirmPortfolioGovernor,
    PortfolioDecision,
    currency_exposure_from_positions,
    parse_fx_symbol,
)


def proposal(symbol: str = "EURUSD", side: Side = Side.BUY) -> TradeProposal:
    if side == Side.BUY:
        stop, entry, target = 1.0950, 1.1000, 1.1100
    else:
        target, entry, stop = 1.0900, 1.1000, 1.1050
    return TradeProposal(
        strategy_version="generalist-v0",
        symbol=symbol,
        side=side,
        entry_price=entry,
        stop_loss=stop,
        take_profit=target,
        risk_pct=0.25,
        confidence=0.70,
        timeframe="M15",
        thesis="test",
    )


def position(symbol: str, side: Side, volume: float) -> Position:
    return Position(
        ticket=1,
        symbol=symbol,
        side=side,
        volume=volume,
        price_open=1.1000,
    )


def test_parse_fx_symbol_tolerates_common_suffixes():
    assert parse_fx_symbol("EURUSDm").base == "EUR"
    assert parse_fx_symbol("EURUSD.pro").quote == "USD"


def test_position_exposure_tracks_base_and_quote_direction():
    exposure = currency_exposure_from_positions(
        [position("EURUSD", Side.BUY, 0.01), position("GBPUSD", Side.SELL, 0.02)]
    )

    assert exposure["EUR"] == 0.01
    assert exposure["GBP"] == -0.02
    assert exposure["USD"] == 0.01


def test_governor_allows_trade_inside_currency_limits():
    governor = FirmPortfolioGovernor(max_abs_currency_net_lots=0.05)

    review = governor.evaluate(
        proposal(),
        [position("EURGBP", Side.BUY, 0.01)],
        proposed_volume=0.01,
    )

    assert review.decision == PortfolioDecision.ALLOW
    assert review.projected_net_lots["EUR"] == 0.02


def test_governor_denies_trade_that_concentrates_common_currency():
    governor = FirmPortfolioGovernor(max_abs_currency_net_lots=0.02)

    review = governor.evaluate(
        proposal("EURUSD", Side.BUY),
        [position("GBPUSD", Side.BUY, 0.02)],
        proposed_volume=0.01,
    )

    assert review.decision == PortfolioDecision.DENY
    assert any("USD" in reason for reason in review.reasons)


def test_unparseable_existing_position_fails_closed():
    governor = FirmPortfolioGovernor()
    weird = Position(
        ticket=2,
        symbol="NOT_A_PAIR",
        side=Side.BUY,
        volume=0.01,
        price_open=1.0,
    )

    review = governor.evaluate(proposal(), [weird], proposed_volume=0.01)

    assert review.decision == PortfolioDecision.DENY
    assert "portfolio exposure unavailable" in review.reasons[0]
