from dusty_dragon.organization.expansion_roadmap import (
    CorporateExpansionRoadmap,
    DeskStatus,
    DeskTier,
    ExpansionNode,
    TradingDesk,
)


def qualified_desk(*, slot: int, tier: DeskTier, node_id: str, style=None, sector=None, symbol=None):
    return TradingDesk(
        desk_id=f"{node_id}-{slot}",
        slot=slot,
        tier=tier,
        style=style,
        sector=sector,
        symbol=symbol,
        broker_division="boforex",
        status=DeskStatus.QUALIFIED,
        average_equity_30d=500_000,
        sustained_days=30,
        healthy=True,
    )


def full_node(*, node_id: str, tier: DeskTier, style=None, sector=None, symbol=None):
    return ExpansionNode(
        node_id=node_id,
        tier=tier,
        style=style,
        sector=sector,
        symbol=symbol,
        desks=[
            qualified_desk(
                slot=slot,
                tier=tier,
                node_id=node_id,
                style=style,
                sector=sector,
                symbol=symbol,
            )
            for slot in range(1, 7)
        ],
    )


def test_new_firm_starts_with_generalist_desk_one():
    result = CorporateExpansionRoadmap().next_recommendation([])

    assert result.tier == DeskTier.GENERALIST
    assert result.next_slot == 1


def test_desk_requires_sustained_500k_average_equity_to_qualify_for_expansion():
    desk = qualified_desk(slot=1, tier=DeskTier.GENERALIST, node_id="generalist")
    desk.average_equity_30d = 499_999

    assert desk.expansion_qualified is False

    desk.average_equity_30d = 500_000
    desk.sustained_days = 29
    assert desk.expansion_qualified is False

    desk.sustained_days = 30
    assert desk.expansion_qualified is True


def test_generalist_node_must_fill_all_six_slots_before_style_expansion():
    generalist = full_node(node_id="generalist", tier=DeskTier.GENERALIST)
    generalist.desks[-1].status = DeskStatus.ACTIVE

    result = CorporateExpansionRoadmap().next_recommendation([generalist])

    assert result.tier == DeskTier.GENERALIST
    assert result.next_slot == 6


def test_style_layer_expands_horizontally_before_sector_niche():
    roadmap = CorporateExpansionRoadmap(common_styles=("scalping", "swing", "breakout"))
    nodes = [
        full_node(node_id="generalist", tier=DeskTier.GENERALIST),
        full_node(node_id="scalping", tier=DeskTier.STYLE, style="scalping"),
    ]

    result = roadmap.next_recommendation(nodes, sectors=("metals",))

    assert result.tier == DeskTier.STYLE
    assert result.style == "swing"
    assert result.sector is None


def test_sector_layer_begins_only_after_all_common_styles_are_full():
    roadmap = CorporateExpansionRoadmap(common_styles=("scalping", "swing"))
    nodes = [
        full_node(node_id="generalist", tier=DeskTier.GENERALIST),
        full_node(node_id="scalping", tier=DeskTier.STYLE, style="scalping"),
        full_node(node_id="swing", tier=DeskTier.STYLE, style="swing"),
    ]

    result = roadmap.next_recommendation(nodes, sectors=("metals", "energy"))

    assert result.tier == DeskTier.SECTOR
    assert result.style == "scalping"
    assert result.sector == "metals"
    assert result.next_slot == 1


def test_sector_breadth_completes_before_symbol_specialization():
    roadmap = CorporateExpansionRoadmap(common_styles=("scalping", "swing"))
    nodes = [
        full_node(node_id="generalist", tier=DeskTier.GENERALIST),
        full_node(node_id="scalping", tier=DeskTier.STYLE, style="scalping"),
        full_node(node_id="swing", tier=DeskTier.STYLE, style="swing"),
        full_node(node_id="scalping-metals", tier=DeskTier.SECTOR, style="scalping", sector="metals"),
        full_node(node_id="swing-metals", tier=DeskTier.SECTOR, style="swing", sector="metals"),
        full_node(node_id="scalping-energy", tier=DeskTier.SECTOR, style="scalping", sector="energy"),
        full_node(node_id="swing-energy", tier=DeskTier.SECTOR, style="swing", sector="energy"),
    ]

    result = roadmap.next_recommendation(
        nodes,
        sectors=("metals", "energy"),
        symbols_by_sector={"metals": ("XAUUSD", "XAGUSD")},
    )

    assert result.tier == DeskTier.SYMBOL
    assert result.style == "scalping"
    assert result.sector == "metals"
    assert result.symbol == "XAUUSD"


def test_new_desk_does_not_inherit_other_desk_account_state():
    first = qualified_desk(slot=1, tier=DeskTier.GENERALIST, node_id="generalist")
    second = TradingDesk(
        desk_id="generalist-2",
        slot=2,
        tier=DeskTier.GENERALIST,
        broker_division="boforex",
    )

    assert first.average_equity_30d == 500_000
    assert second.average_equity_30d == 0
    assert second.status == DeskStatus.PLANNED
