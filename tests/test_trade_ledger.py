import sqlite3

from dusty_dragon.brokers.contracts import ExecutionResult
from dusty_dragon.domain.trades import GuardDecision, GuardResult, Side, TradeProposal
from dusty_dragon.reporting.trade_report import TradeReport
from dusty_dragon.storage.trade_ledger import TradeLedger


def proposal() -> TradeProposal:
    return TradeProposal(
        strategy_version="generalist-v0",
        symbol="EURUSD",
        side=Side.BUY,
        entry_price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1100,
        risk_pct=0.25,
        confidence=0.72,
        timeframe="M15",
        thesis="Trend and forecast evidence align.",
        evidence={"kronos_direction": "bullish", "trend_score": 0.78},
    )


def report() -> TradeReport:
    trade = proposal()
    return TradeReport.from_decision(
        trade,
        GuardResult(decision=GuardDecision.ALLOW),
        broker_division="boforex",
        account_label="paper-01",
        execution=ExecutionResult(
            accepted=True,
            message="paper fill",
            requested_volume=0.01,
            executed_volume=0.01,
            executed_price=1.1002,
            spread_points=20.0,
            slippage_points=2.0,
            estimated_commission=0.035,
            estimated_swap=0.0,
        ),
        model_versions={"kronos": "pending-integration"},
        data_provenance={"market_data": "mt5"},
    )


def test_markdown_explains_why_trade_was_considered() -> None:
    rendered = report().to_markdown()

    assert "Why the bot considered this trade" in rendered
    assert "Trend and forecast evidence align." in rendered
    assert "kronos_direction" in rendered
    assert "Guard decision:** allow" in rendered


def test_markdown_explains_paper_execution_friction() -> None:
    rendered = report().to_markdown()

    assert "Paper execution and friction" in rendered
    assert "Executed volume:** 0.01000 lots" in rendered
    assert "Spread:** 20.00000 points" in rendered
    assert "Slippage:** 2.00000 points" in rendered
    assert "Estimated commission:** 0.03500" in rendered


def test_ledger_round_trip_and_chain_verification(tmp_path) -> None:
    ledger = TradeLedger(tmp_path / "ledger.sqlite3")
    original = report()

    record_hash = ledger.append(original)
    loaded = ledger.reports_for_trade(str(original.trade_id))

    assert len(record_hash) == 64
    assert len(loaded) == 1
    assert loaded[0].trade_id == original.trade_id
    assert ledger.verify_chain() is True


def test_ledger_detects_tampering(tmp_path) -> None:
    path = tmp_path / "ledger.sqlite3"
    ledger = TradeLedger(path)
    ledger.append(report())

    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE trade_reports SET payload_json = ? WHERE sequence = 1",
            ('{"tampered":true}',),
        )

    assert ledger.verify_chain() is False
