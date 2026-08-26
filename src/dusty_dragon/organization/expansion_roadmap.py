from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class DeskTier(StrEnum):
    GENERALIST = "generalist"
    STYLE = "style"
    SECTOR = "sector"
    SYMBOL = "symbol"


class DeskStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    QUALIFIED = "qualified"


class TradingDesk(BaseModel):
    """One independently accountable MT5 trading desk inside Dusty Dragon."""

    desk_id: str
    slot: int = Field(ge=1, le=6)
    tier: DeskTier
    style: str | None = None
    sector: str | None = None
    symbol: str | None = None
    broker_division: str
    status: DeskStatus = DeskStatus.PLANNED
    average_equity_30d: float = Field(default=0.0, ge=0)
    sustained_days: int = Field(default=0, ge=0)
    healthy: bool = True

    @model_validator(mode="after")
    def validate_taxonomy(self) -> TradingDesk:
        if self.tier == DeskTier.GENERALIST and any((self.style, self.sector, self.symbol)):
            raise ValueError("generalist desks cannot carry specialization labels")
        if self.tier in {DeskTier.STYLE, DeskTier.SECTOR, DeskTier.SYMBOL} and not self.style:
            raise ValueError("specialized desks require a trading style")
        if self.tier in {DeskTier.SECTOR, DeskTier.SYMBOL} and not self.sector:
            raise ValueError("sector and symbol desks require a sector")
        if self.tier == DeskTier.SYMBOL and not self.symbol:
            raise ValueError("symbol desks require a symbol")
        return self

    @property
    def expansion_qualified(self) -> bool:
        return (
            self.status == DeskStatus.QUALIFIED
            and self.average_equity_30d >= 500_000
            and self.sustained_days >= 30
            and self.healthy
        )


class ExpansionNode(BaseModel):
    """A six-desk corporate unit filled breadth-first before deeper specialization."""

    node_id: str
    tier: DeskTier
    style: str | None = None
    sector: str | None = None
    symbol: str | None = None
    desks: list[TradingDesk] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_slots(self) -> ExpansionNode:
        slots = [desk.slot for desk in self.desks]
        if len(slots) != len(set(slots)):
            raise ValueError("desk slots must be unique within an expansion node")
        if len(self.desks) > 6:
            raise ValueError("each expansion node is limited to six desks")
        return self

    @property
    def qualified_slots(self) -> int:
        return sum(desk.expansion_qualified for desk in self.desks)

    @property
    def is_full(self) -> bool:
        return self.qualified_slots == 6


class ExpansionRecommendation(BaseModel):
    eligible: bool
    reason: str
    tier: DeskTier | None = None
    style: str | None = None
    sector: str | None = None
    symbol: str | None = None
    next_slot: int | None = Field(default=None, ge=1, le=6)


@dataclass(frozen=True)
class CorporateExpansionRoadmap:
    """Breadth-first roadmap for Dusty Dragon's long-horizon corporate maturity.

    The roadmap is advisory only. It cannot open brokerage accounts, place
    trades, clone credentials, or promote strategies. Human setup remains
    mandatory for each new MT5 account.

    Expansion principles:
    - Six qualified desks fill every node.
    - A desk qualifies to sponsor expansion only after >= $500k 30-day average
      equity sustained for at least 30 days while healthy.
    - Breadth comes before depth: generalists -> common styles -> sectors ->
      symbols. A deeper specialization is not requested until the configured
      breadth layer is complete.
    - New desks inherit firm knowledge, not another desk's account state,
      maturity counters, risk ledger, or credentials.
    """

    common_styles: tuple[str, ...] = (
        "scalping",
        "swing",
        "breakout",
        "reversal",
        "trend",
        "momentum",
    )

    def next_recommendation(
        self,
        nodes: list[ExpansionNode],
        *,
        sectors: tuple[str, ...] = (),
        symbols_by_sector: dict[str, tuple[str, ...]] | None = None,
    ) -> ExpansionRecommendation:
        symbols_by_sector = symbols_by_sector or {}

        generalist = self._find(nodes, DeskTier.GENERALIST)
        if generalist is None:
            return ExpansionRecommendation(
                eligible=True,
                reason="initialize the six-desk Generalist Trading Division",
                tier=DeskTier.GENERALIST,
                next_slot=1,
            )
        if not generalist.is_full:
            return self._next_slot_recommendation(generalist)

        # Breadth-first style layer: fill every common style before sector depth.
        for style in self.common_styles:
            node = self._find(nodes, DeskTier.STYLE, style=style)
            if node is None:
                return ExpansionRecommendation(
                    eligible=True,
                    reason=f"generalist division is full; begin {style} style breadth",
                    tier=DeskTier.STYLE,
                    style=style,
                    next_slot=1,
                )
            if not node.is_full:
                return self._next_slot_recommendation(node)

        # Then breadth-first sector specialization across styles.
        for sector in sectors:
            for style in self.common_styles:
                node = self._find(nodes, DeskTier.SECTOR, style=style, sector=sector)
                if node is None:
                    return ExpansionRecommendation(
                        eligible=True,
                        reason=f"style layer is full; begin {style}/{sector} specialization",
                        tier=DeskTier.SECTOR,
                        style=style,
                        sector=sector,
                        next_slot=1,
                    )
                if not node.is_full:
                    return self._next_slot_recommendation(node)

        # Finally deepen to popular symbols, still breadth-first by sector/style.
        for sector in sectors:
            for symbol in symbols_by_sector.get(sector, ()): 
                for style in self.common_styles:
                    node = self._find(
                        nodes,
                        DeskTier.SYMBOL,
                        style=style,
                        sector=sector,
                        symbol=symbol,
                    )
                    if node is None:
                        return ExpansionRecommendation(
                            eligible=True,
                            reason=f"sector layer is full; begin {style}/{sector}/{symbol}",
                            tier=DeskTier.SYMBOL,
                            style=style,
                            sector=sector,
                            symbol=symbol,
                            next_slot=1,
                        )
                    if not node.is_full:
                        return self._next_slot_recommendation(node)

        return ExpansionRecommendation(
            eligible=False,
            reason="configured corporate expansion roadmap is fully populated",
        )

    @staticmethod
    def _next_slot_recommendation(node: ExpansionNode) -> ExpansionRecommendation:
        occupied = {desk.slot for desk in node.desks if desk.expansion_qualified}
        next_slot = next(slot for slot in range(1, 7) if slot not in occupied)
        return ExpansionRecommendation(
            eligible=True,
            reason=f"{node.node_id} has {node.qualified_slots}/6 qualified desks",
            tier=node.tier,
            style=node.style,
            sector=node.sector,
            symbol=node.symbol,
            next_slot=next_slot,
        )

    @staticmethod
    def _find(
        nodes: list[ExpansionNode],
        tier: DeskTier,
        *,
        style: str | None = None,
        sector: str | None = None,
        symbol: str | None = None,
    ) -> ExpansionNode | None:
        for node in nodes:
            if (
                node.tier == tier
                and node.style == style
                and node.sector == sector
                and node.symbol == symbol
            ):
                return node
        return None
