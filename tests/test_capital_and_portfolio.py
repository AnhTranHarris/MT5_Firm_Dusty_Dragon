from dusty_dragon.capital.ledger import (
    CapitalFlow,
    CapitalFlowType,
    DeskLedgerSnapshot,
    apply_external_flow,
)
from dusty_dragon.domain.models import SignalDisposition
from dusty_dragon.portfolio.governor import evaluate_incremental_risk


def test_external_capital_flow_does_not_change_trading_pnl() -> None:
    before = DeskLedgerSnapshot(
        desk_id="DEMO-01",
        starting_capital=20_000,
        realized_trading_pnl=1_000,
        unrealized_trading_pnl=250,
        net_external_flows=0,
    )
    flow = CapitalFlow(
        desk_id="DEMO-01",
        flow_type=CapitalFlowType.DEMO_COMPRESSION,
        amount=-5_250,
        reference="Sunday capital compression",
    )

    after = apply_external_flow(before, flow)

    assert after.realized_trading_pnl == 1_000
    assert after.unrealized_trading_pnl == 250
    assert after.net_external_flows == -5_250
    assert after.balance == 15_750
    assert after.equity == 16_000


def test_cross_desk_capital_flow_is_rejected() -> None:
    snapshot = DeskLedgerSnapshot("D1", 5_000, 0, 0, 0)
    flow = CapitalFlow("D2", CapitalFlowType.DEPOSIT, 100, "invalid subsidy")

    try:
        apply_external_flow(snapshot, flow)
    except ValueError as exc:
        assert "does not match" in str(exc)
    else:
        raise AssertionError("cross-desk capital flow must fail")


def test_portfolio_veto_preserves_valid_signal_classification() -> None:
    decision = evaluate_incremental_risk(
        desk_signal_valid=True,
        portfolio_capacity_available=False,
    )

    assert not decision.allowed
    assert decision.disposition is SignalDisposition.PORTFOLIO_CAPACITY_REJECTED


def test_bad_desk_signal_is_not_mislabeled_as_portfolio_rejection() -> None:
    decision = evaluate_incremental_risk(
        desk_signal_valid=False,
        portfolio_capacity_available=True,
    )

    assert not decision.allowed
    assert decision.disposition is SignalDisposition.BAD_SIGNAL
