from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from dusty_dragon.learning.outcomes import TradeOutcome


class CapitalGrowthSummary(BaseModel):
    starting_capital: float = Field(gt=0)
    ending_capital: float = Field(gt=0)
    net_growth: float
    net_growth_pct: float
    max_drawdown_pct: float = Field(ge=0)
    profitable: bool
    capital_preserved: bool
    growth_to_drawdown: float | None = None


@dataclass(frozen=True)
class CapitalGrowthObjective:
    """Evaluate whether a strategy actually grows account equity.

    Firm priority: capital growth is the primary business outcome. Risk and
    drawdown controls are constraints on *how* that growth is achieved, not a
    substitute for profitability.

    Vibe-Trading roadmap: evaluate performance and drawdown from an equity curve.
    Automaton roadmap: emit compact objective evidence that workers can reason
    over without rereading raw trades.
    Kronos roadmap: forecast accuracy is intentionally absent from this score;
    a predictive model only matters if the resulting strategy grows capital.

    Until Dusty Dragon records authoritative cash P/L for every closed trade,
    the equity curve is estimated from realized R and a fixed risk budget per
    trade. This makes the assumption explicit and deterministic for paper/research
    evaluation. Actual broker cash P/L will supersede this estimate later.
    """

    risk_per_trade_pct: float = 0.25
    maximum_drawdown_pct: float = 10.0

    def __post_init__(self) -> None:
        if not 0 < self.risk_per_trade_pct <= 100:
            raise ValueError("risk_per_trade_pct must be between 0 and 100")
        if not 0 < self.maximum_drawdown_pct <= 100:
            raise ValueError("maximum_drawdown_pct must be between 0 and 100")

    def evaluate(
        self,
        outcomes: list[TradeOutcome],
        *,
        starting_capital: float,
    ) -> CapitalGrowthSummary:
        if starting_capital <= 0:
            raise ValueError("starting_capital must be positive")

        ordered = sorted(outcomes, key=lambda item: (item.closed_at, str(item.trade_id)))
        equity = starting_capital
        peak = starting_capital
        max_drawdown_pct = 0.0
        risk_fraction = self.risk_per_trade_pct / 100.0

        for outcome in ordered:
            trade_return = outcome.realized_r * risk_fraction
            if trade_return <= -1.0:
                equity = 0.0
                break
            equity *= 1.0 + trade_return
            peak = max(peak, equity)
            if peak > 0:
                drawdown_pct = ((peak - equity) / peak) * 100.0
                max_drawdown_pct = max(max_drawdown_pct, drawdown_pct)

        net_growth = equity - starting_capital
        net_growth_pct = (net_growth / starting_capital) * 100.0
        ratio = None
        if max_drawdown_pct > 1e-12:
            ratio = net_growth_pct / max_drawdown_pct
        elif net_growth_pct > 0:
            ratio = float("inf")

        return CapitalGrowthSummary(
            starting_capital=starting_capital,
            ending_capital=max(equity, 1e-12),
            net_growth=net_growth,
            net_growth_pct=net_growth_pct,
            max_drawdown_pct=max_drawdown_pct,
            profitable=net_growth > 0,
            capital_preserved=max_drawdown_pct <= self.maximum_drawdown_pct and equity > 0,
            growth_to_drawdown=ratio,
        )
