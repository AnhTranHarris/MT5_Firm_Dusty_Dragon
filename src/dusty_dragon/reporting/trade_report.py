from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from dusty_dragon.brokers.contracts import ExecutionResult
from dusty_dragon.domain.trades import GuardResult, TradeProposal


class TradeReport(BaseModel):
    """Immutable explanation payload for one proposed paper trade.

    Architecture references:
    - Vibe-Trading governance/live audit records: preserve decision provenance.
    - Automaton audit logging: persist actions and outcomes for later learning.
    - Kronos: model evidence belongs in ``proposal.evidence`` rather than being
      converted directly into an order.
    """

    report_version: str = "trade-report/v1"
    trade_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    proposal: TradeProposal
    guard: GuardResult
    execution: ExecutionResult | None = None
    broker_division: str
    account_label: str
    model_versions: dict[str, str] = Field(default_factory=dict)
    data_provenance: dict[str, str] = Field(default_factory=dict)
    observations: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_decision(
        cls,
        proposal: TradeProposal,
        guard: GuardResult,
        *,
        broker_division: str,
        account_label: str,
        execution: ExecutionResult | None = None,
        model_versions: dict[str, str] | None = None,
        data_provenance: dict[str, str] | None = None,
        observations: dict[str, Any] | None = None,
    ) -> TradeReport:
        return cls(
            trade_id=proposal.id,
            proposal=proposal,
            guard=guard,
            execution=execution,
            broker_division=broker_division,
            account_label=account_label,
            model_versions=model_versions or {},
            data_provenance=data_provenance or {},
            observations=observations or {},
        )

    @staticmethod
    def _optional_metric(label: str, value: float | None, suffix: str = "") -> str | None:
        if value is None:
            return None
        return f"- **{label}:** {value:.5f}{suffix}"

    def _execution_lines(self) -> list[str]:
        if self.execution is None:
            return ["- No simulated execution was recorded."]

        lines = [
            f"- **Status:** {'accepted' if self.execution.accepted else 'rejected'}",
            f"- **Requested volume:** {self.execution.requested_volume:.5f} lots",
        ]
        optional = [
            self._optional_metric("Executed volume", self.execution.executed_volume, " lots"),
            self._optional_metric("Executed price", self.execution.executed_price),
            self._optional_metric("Spread", self.execution.spread_points, " points"),
            self._optional_metric("Slippage", self.execution.slippage_points, " points"),
            self._optional_metric("Estimated commission", self.execution.estimated_commission),
            self._optional_metric("Estimated swap", self.execution.estimated_swap),
            self._optional_metric("Gross P/L", self.execution.gross_pnl),
            self._optional_metric("Net P/L", self.execution.net_pnl),
        ]
        lines.extend(line for line in optional if line is not None)
        if self.execution.message:
            lines.append(f"- **Execution note:** {self.execution.message}")
        return lines

    def to_markdown(self) -> str:
        execution_status = "not executed"
        if self.execution is not None:
            execution_status = "accepted" if self.execution.accepted else "rejected"

        evidence_lines = [
            f"- **{key}:** {value}" for key, value in sorted(self.proposal.evidence.items())
        ]
        if not evidence_lines:
            evidence_lines = ["- No model/signal evidence recorded yet."]

        guard_reasons = [f"- {reason}" for reason in self.guard.reasons]
        if not guard_reasons:
            guard_reasons = ["- All configured guard checks passed."]

        return "\n".join(
            [
                f"# Trade Report {self.trade_id}",
                "",
                f"- **Broker division:** {self.broker_division}",
                f"- **Account:** {self.account_label}",
                f"- **Symbol:** {self.proposal.symbol}",
                f"- **Side:** {self.proposal.side.value}",
                f"- **Timeframe:** {self.proposal.timeframe}",
                f"- **Strategy:** {self.proposal.strategy_version}",
                f"- **Confidence:** {self.proposal.confidence:.2%}",
                f"- **Risk budget:** {self.proposal.risk_pct:.3f}%",
                f"- **Reward/risk:** {self.proposal.reward_to_risk:.2f}",
                f"- **Guard decision:** {self.guard.decision.value}",
                f"- **Execution:** {execution_status}",
                "",
                "## Why the bot considered this trade",
                "",
                self.proposal.thesis,
                "",
                "## Evidence",
                "",
                *evidence_lines,
                "",
                "## Guard review",
                "",
                *guard_reasons,
                "",
                "## Paper execution and friction",
                "",
                *self._execution_lines(),
            ]
        )
