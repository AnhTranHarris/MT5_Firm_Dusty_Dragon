from dusty_dragon.config import Settings
from dusty_dragon.domain.trades import AccountSnapshot, GuardDecision, Side, TradeProposal
from dusty_dragon.risk.order_guard import OrderGuard


def proposal(risk_pct: float = 0.25) -> TradeProposal:
    return TradeProposal(
        strategy_version="generalist-v0",
        symbol="EURUSD",
        side=Side.BUY,
        entry_price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1100,
        risk_pct=risk_pct,
        confidence=0.60,
        timeframe="M15",
        thesis="Test proposal",
    )


def account(**overrides) -> AccountSnapshot:
    values = {
        "balance": 10_000,
        "equity": 10_000,
        "open_risk_pct": 0,
        "daily_drawdown_pct": 0,
        "weekly_drawdown_pct": 0,
    }
    values.update(overrides)
    return AccountSnapshot(**values)


def test_allows_valid_paper_proposal():
    guard = OrderGuard(Settings())
    result = guard.evaluate(proposal(), account())
    assert result.decision == GuardDecision.ALLOW
    assert result.reasons == []


def test_rejects_excess_risk():
    guard = OrderGuard(Settings(risk_per_trade_pct=0.25))
    result = guard.evaluate(proposal(risk_pct=0.50), account())
    assert result.decision == GuardDecision.DENY


def test_kill_switch_fails_closed():
    guard = OrderGuard(Settings())
    result = guard.evaluate(proposal(), account(), kill_switch=True)
    assert result.decision == GuardDecision.DENY
    assert "kill switch is active" in result.reasons


def test_stale_data_fails_closed():
    guard = OrderGuard(Settings())
    result = guard.evaluate(proposal(), account(), market_data_fresh=False)
    assert result.decision == GuardDecision.DENY
