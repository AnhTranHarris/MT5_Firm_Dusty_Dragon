from __future__ import annotations

from dataclasses import dataclass

from dusty_dragon.domain.models import SignalDisposition


@dataclass(frozen=True, slots=True)
class PortfolioDecision:
    allowed: bool
    disposition: SignalDisposition
    reason: str


def evaluate_incremental_risk(*, desk_signal_valid: bool, portfolio_capacity_available: bool) -> PortfolioDecision:
    """Classify a signal without contaminating strategy-quality evidence."""

    if not desk_signal_valid:
        return PortfolioDecision(
            allowed=False,
            disposition=SignalDisposition.BAD_SIGNAL,
            reason="desk signal failed strategy/desk validation",
        )

    if not portfolio_capacity_available:
        return PortfolioDecision(
            allowed=False,
            disposition=SignalDisposition.PORTFOLIO_CAPACITY_REJECTED,
            reason="valid desk signal rejected by aggregate portfolio capacity",
        )

    return PortfolioDecision(
        allowed=True,
        disposition=SignalDisposition.APPROVED,
        reason="desk signal and portfolio capacity both valid",
    )
