from __future__ import annotations

from pydantic import BaseModel

from dusty_dragon.organization.expansion_roadmap import ExpansionRecommendation


class ExpansionNotice(BaseModel):
    """Human-action request produced by the corporate expansion roadmap."""

    recommendation: ExpansionRecommendation
    recipient: str = "forex.isekai@gmail.com"

    @property
    def subject(self) -> str:
        return "Dusty Dragon Trading Firm — Expansion Request"

    def to_text(self) -> str:
        recommendation = self.recommendation
        if not recommendation.eligible:
            return "Dusty Dragon has no currently eligible corporate expansion request."

        path = [
            value
            for value in (
                recommendation.style,
                recommendation.sector,
                recommendation.symbol,
            )
            if value
        ]
        specialization = " / ".join(path) if path else "Generalist"
        return (
            "Dusty Dragon has identified the next human-managed MT5 expansion step.\n\n"
            f"Tier: {recommendation.tier.value if recommendation.tier else 'unknown'}\n"
            f"Specialization: {specialization}\n"
            f"Requested desk slot: {recommendation.next_slot}\n"
            f"Reason: {recommendation.reason}\n\n"
            "Create/configure the brokerage account manually. Dusty Dragon must not create "
            "brokerage accounts or copy credentials automatically. After the new account is "
            "connected and verified, it may be registered as a new independent Trading Desk "
            "that inherits validated firm knowledge but not another desk's account state."
        )
