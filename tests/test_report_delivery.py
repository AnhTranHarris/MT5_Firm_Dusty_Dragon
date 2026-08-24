from __future__ import annotations

from email.message import EmailMessage
from types import TracebackType
from typing import ClassVar, Self

from dusty_dragon.config import Settings
from dusty_dragon.domain.trades import GuardDecision, GuardResult, Side, TradeProposal
from dusty_dragon.reporting.delivery import EmailReportSink
from dusty_dragon.reporting.trade_report import TradeReport


class FakeSMTP:
    instances: ClassVar[list[FakeSMTP]] = []

    def __init__(self, host: str, port: int, timeout: int) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.login_args: tuple[str, str] | None = None
        self.message: EmailMessage | None = None
        self.__class__.instances.append(self)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    def login(self, username: str, password: str) -> None:
        self.login_args = (username, password)

    def send_message(self, message: EmailMessage) -> None:
        self.message = message


def report() -> TradeReport:
    proposal = TradeProposal(
        strategy_version="test-v1",
        symbol="EURUSD",
        side=Side.BUY,
        entry_price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1100,
        risk_pct=0.25,
        confidence=0.72,
        timeframe="M15",
        thesis="Kronos and supporting research agree on a bullish setup.",
        evidence={"kronos_confidence": 0.72},
    )
    return TradeReport.from_decision(
        proposal,
        GuardResult(decision=GuardDecision.ALLOW),
        broker_division="boforex",
        account_label="paper-001",
    )


def test_email_sink_is_disabled_by_default() -> None:
    FakeSMTP.instances.clear()
    sink = EmailReportSink(Settings(_env_file=None), smtp_factory=FakeSMTP)

    sink.send(report())

    assert FakeSMTP.instances == []


def test_email_sink_uses_required_recipient_and_broker_subject() -> None:
    FakeSMTP.instances.clear()
    settings = Settings(
        _env_file=None,
        report_email_enabled=True,
        report_smtp_username="sender@example.com",
        report_smtp_password="local-secret",
        broker_display_name="BoForex",
    )
    sink = EmailReportSink(settings, smtp_factory=FakeSMTP)

    sink.send(report())

    assert len(FakeSMTP.instances) == 1
    smtp = FakeSMTP.instances[0]
    assert smtp.login_args == ("sender@example.com", "local-secret")
    assert smtp.message is not None
    assert smtp.message["To"] == "forex.isekai@gmail.com"
    assert smtp.message["Subject"] == "Dusty Dragon Bot Firm — BoForex"
    assert "Why the bot considered this trade" in smtp.message.get_content()
