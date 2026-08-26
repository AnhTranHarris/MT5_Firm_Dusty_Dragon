from datetime import UTC, datetime, timedelta

import pytest

from dusty_dragon.knowledge.institutional import (
    EvidenceReference,
    FreshnessState,
    InstitutionalKnowledgeStore,
    KnowledgeFinding,
    KnowledgeScope,
    KnowledgeScopeLevel,
    KnowledgeStatus,
    KnowledgeVerification,
)
from dusty_dragon.organization.expansion_roadmap import DeskStatus, DeskTier, TradingDesk


def desk(
    desk_id: str,
    *,
    tier: DeskTier = DeskTier.GENERALIST,
    style: str | None = None,
    sector: str | None = None,
    symbol: str | None = None,
) -> TradingDesk:
    return TradingDesk(
        desk_id=desk_id,
        slot=1,
        tier=tier,
        style=style,
        sector=sector,
        symbol=symbol,
        broker_division="boforex",
        status=DeskStatus.ACTIVE,
    )


def evidence(now: datetime) -> EvidenceReference:
    return EvidenceReference(
        archive_ref="drive://dusty-dragon/boforex/EURUSD/M15/2026/08",
        checksum_sha256="a" * 64,
        seed=42,
        sample_size=2400,
        runs=12,
        window_start=now - timedelta(days=30),
        window_end=now - timedelta(days=1),
        regime="trend_low_vol",
    )


def finding(now: datetime, scope: KnowledgeScope | None = None) -> KnowledgeFinding:
    return KnowledgeFinding(
        source_desk_id="generalist-01",
        claim_code="KRONOS_TREND_SUPPORT",
        statement="Kronos adds useful directional evidence in this tested regime.",
        scope=scope or KnowledgeScope(level=KnowledgeScopeLevel.FIRM),
        evidence=[evidence(now)],
        confidence=0.82,
        estimated_capital_effect_pct=0.35,
        kronos_related=True,
        created_at=now,
    )


def test_finding_requires_peer_reproduction_before_validation(tmp_path):
    now = datetime(2026, 8, 25, tzinfo=UTC)
    store = InstitutionalKnowledgeStore(tmp_path / "knowledge.sqlite")
    item = store.publish(finding(now))

    assert item.status == KnowledgeStatus.OBSERVED

    first = store.verify(
        KnowledgeVerification(
            finding_id=item.id,
            verifier_desk_id="generalist-02",
            reproduced=True,
            confidence=0.80,
            verified_at=now + timedelta(hours=1),
        )
    )
    assert first.status == KnowledgeStatus.PEER_TESTING

    second = store.verify(
        KnowledgeVerification(
            finding_id=item.id,
            verifier_desk_id="generalist-03",
            reproduced=True,
            confidence=0.78,
            verified_at=now + timedelta(hours=2),
        )
    )
    assert second.status == KnowledgeStatus.VALIDATED


def test_source_desk_cannot_self_validate(tmp_path):
    now = datetime(2026, 8, 25, tzinfo=UTC)
    store = InstitutionalKnowledgeStore(tmp_path / "knowledge.sqlite")
    item = store.publish(finding(now))

    with pytest.raises(ValueError, match="source desk"):
        store.verify(
            KnowledgeVerification(
                finding_id=item.id,
                verifier_desk_id="generalist-01",
                reproduced=True,
                confidence=1.0,
            )
        )


def test_failed_peer_reproduction_rejects_finding(tmp_path):
    now = datetime(2026, 8, 25, tzinfo=UTC)
    store = InstitutionalKnowledgeStore(tmp_path / "knowledge.sqlite")
    item = store.publish(finding(now))

    for verifier in ("generalist-02", "generalist-03"):
        updated = store.verify(
            KnowledgeVerification(
                finding_id=item.id,
                verifier_desk_id=verifier,
                reproduced=False,
                confidence=0.75,
                verified_at=now + timedelta(hours=1),
            )
        )

    assert updated.status == KnowledgeStatus.REJECTED


def test_scope_inheritance_is_breadth_safe(tmp_path):
    now = datetime(2026, 8, 25, tzinfo=UTC)
    store = InstitutionalKnowledgeStore(tmp_path / "knowledge.sqlite")
    scope = KnowledgeScope(
        level=KnowledgeScopeLevel.SECTOR,
        style="scalping",
        sector="metals",
    )
    item = store.publish(finding(now, scope))
    for verifier in ("scalping-metals-02", "scalping-metals-03"):
        store.verify(
            KnowledgeVerification(
                finding_id=item.id,
                verifier_desk_id=verifier,
                reproduced=True,
                confidence=0.8,
                verified_at=now + timedelta(hours=1),
            )
        )

    xau = desk(
        "xau-01",
        tier=DeskTier.SYMBOL,
        style="scalping",
        sector="metals",
        symbol="XAUUSD",
    )
    eurusd = desk(
        "eurusd-01",
        tier=DeskTier.SYMBOL,
        style="scalping",
        sector="fx",
        symbol="EURUSD",
    )
    generalist = desk("generalist-04")

    assert [entry.id for entry in store.usable_for(xau, now=now + timedelta(days=1))] == [
        item.id
    ]
    assert store.usable_for(eurusd, now=now + timedelta(days=1)) == []
    assert store.usable_for(generalist, now=now + timedelta(days=1)) == []


def test_stale_validated_knowledge_fails_closed_by_default(tmp_path):
    created = datetime(2026, 1, 1, tzinfo=UTC)
    store = InstitutionalKnowledgeStore(tmp_path / "knowledge.sqlite")
    item = store.publish(finding(created))
    for verifier in ("generalist-02", "generalist-03"):
        store.verify(
            KnowledgeVerification(
                finding_id=item.id,
                verifier_desk_id=verifier,
                reproduced=True,
                confidence=0.8,
                verified_at=created,
            )
        )

    current = datetime(2026, 8, 25, tzinfo=UTC)
    saved = store.get(item.id)
    assert saved is not None
    assert saved.freshness(current) == FreshnessState.STALE
    assert store.usable_for(desk("generalist-04"), now=current) == []
    assert store.usable_for(desk("generalist-04"), now=current, include_stale=True)


def test_knowledge_has_no_execution_or_promotion_authority():
    fields = KnowledgeFinding.model_fields
    forbidden = {
        "lot_size",
        "order",
        "execute",
        "promotion_authority",
        "broker_credentials",
        "account_password",
    }
    assert forbidden.isdisjoint(fields)
