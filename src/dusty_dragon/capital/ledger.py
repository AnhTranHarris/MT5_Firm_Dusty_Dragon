from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CapitalFlowType(StrEnum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    DEMO_RESET = "DEMO_RESET"
    DEMO_COMPRESSION = "DEMO_COMPRESSION"


@dataclass(frozen=True, slots=True)
class CapitalFlow:
    desk_id: str
    flow_type: CapitalFlowType
    amount: float
    reference: str


@dataclass(frozen=True, slots=True)
class DeskLedgerSnapshot:
    desk_id: str
    starting_capital: float
    realized_trading_pnl: float
    unrealized_trading_pnl: float
    net_external_flows: float

    @property
    def balance(self) -> float:
        return self.starting_capital + self.realized_trading_pnl + self.net_external_flows

    @property
    def equity(self) -> float:
        return self.balance + self.unrealized_trading_pnl

    @property
    def trading_return_base(self) -> float:
        """Capital base excluding external-flow amounts from trading performance."""

        return self.starting_capital


def apply_external_flow(snapshot: DeskLedgerSnapshot, flow: CapitalFlow) -> DeskLedgerSnapshot:
    """Apply owner/broker capital adjustment without changing trading P&L."""

    if flow.desk_id != snapshot.desk_id:
        raise ValueError("capital flow desk_id does not match ledger")

    return DeskLedgerSnapshot(
        desk_id=snapshot.desk_id,
        starting_capital=snapshot.starting_capital,
        realized_trading_pnl=snapshot.realized_trading_pnl,
        unrealized_trading_pnl=snapshot.unrealized_trading_pnl,
        net_external_flows=snapshot.net_external_flows + flow.amount,
    )
