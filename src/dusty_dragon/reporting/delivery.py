from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage
from smtplib import SMTP_SSL
from typing import Protocol

from dusty_dragon.config import Settings
from dusty_dragon.reporting.trade_report import TradeReport


class ReportDeliveryError(RuntimeError):
    pass


class ReportSink(Protocol):
    """External destination for human-readable reports.

    The trading engine persists structured records locally, then hands a report
    to a sink. This keeps transport concerns outside strategy/risk code and makes
    future sinks (Gmail API, Slack, dashboard, object storage) replaceable.
    """

    def send(self, report: TradeReport) -> None: ...


@dataclass(frozen=True)
class EmailReportSink:
    settings: Settings
    smtp_factory: type[SMTP_SSL] = SMTP_SSL

    def send(self, report: TradeReport) -> None:
        if not self.settings.report_email_enabled:
            return

        self.settings.require_report_email_credentials()
        username = self.settings.report_smtp_username
        password = self.settings.report_smtp_password
        if username is None or password is None:
            raise ReportDeliveryError("report email credentials were not resolved")

        message = EmailMessage()
        message["From"] = username
        message["To"] = self.settings.report_email_recipient
        message["Subject"] = self.settings.report_subject
        message.set_content(report.to_markdown(), subtype="plain", charset="utf-8")

        try:
            with self.smtp_factory(
                self.settings.report_smtp_host,
                self.settings.report_smtp_port,
                timeout=20,
            ) as smtp:
                smtp.login(username, password)
                smtp.send_message(message)
        except Exception as exc:
            raise ReportDeliveryError("failed to deliver human-readable trade report") from exc
