from datetime import UTC, datetime, timedelta

from dusty_dragon.knowledge.institutional import (
    EvidenceReference,
    InstitutionalKnowledgeStore,
    KnowledgeFinding,
    KnowledgeScope,
    KnowledgeScopeLevel,
    KnowledgeStatus,
    KnowledgeVerification,
)


def finding() -> KnowledgeFinding:
    now = datetime(2026, 8, 25, tzinfo=UTC)
    return KnowledgeFinding(
        source_desk_id="generalist-01",
        claim_code="REPRO_AUTHORITY_BOUNDARY",
        statement="A reproducible claim still requires true peer-desk validation.",
        scope=KnowledgeScope(level=KnowledgeScopeLevel.FIRM),
        evidence=[
            EvidenceReference(
                archive_ref="drive://dusty-dragon/research/source",
                checksum_sha256="d" * 64,
                seed=10,
                sample_size=200,
                runs=12,
                window_start=now - timedelta(days=20),
                window_end=now - timedelta(days=1),
            )
        ],
        confidence=0.8,
        created_at=now,
    )


def test_positive_research_replays_cannot_peer_validate(tmp_path):
    store = InstitutionalKnowledgeStore(tmp_path / "knowledge.sqlite")
    item = store.publish(finding())

    for index in (1, 2):
        updated = store.verify(
            KnowledgeVerification(
                finding_id=item.id,
                verifier_desk_id=f"research-replication:{index}",
                reproduced=True,
                confidence=0.85,
                counts_as_peer=False,
            )
        )

    assert updated.status == KnowledgeStatus.PEER_TESTING


def test_repeated_independent_failure_can_reject_weak_claim(tmp_path):
    store = InstitutionalKnowledgeStore(tmp_path / "knowledge.sqlite")
    item = store.publish(finding())

    for index in (1, 2):
        updated = store.verify(
            KnowledgeVerification(
                finding_id=item.id,
                verifier_desk_id=f"research-replication:{index}",
                reproduced=False,
                confidence=0.8,
                counts_as_peer=False,
            )
        )

    assert updated.status == KnowledgeStatus.REJECTED


def test_two_real_peer_desks_can_validate_after_research_reproduction(tmp_path):
    store = InstitutionalKnowledgeStore(tmp_path / "knowledge.sqlite")
    item = store.publish(finding())

    store.verify(
        KnowledgeVerification(
            finding_id=item.id,
            verifier_desk_id="research-replication:1",
            reproduced=True,
            confidence=0.8,
            counts_as_peer=False,
        )
    )
    for desk_id in ("generalist-02", "generalist-03"):
        updated = store.verify(
            KnowledgeVerification(
                finding_id=item.id,
                verifier_desk_id=desk_id,
                reproduced=True,
                confidence=0.8,
                counts_as_peer=True,
            )
        )

    assert updated.status == KnowledgeStatus.VALIDATED


def test_source_desk_can_run_non_peer_replication_but_not_peer_validate(tmp_path):
    store = InstitutionalKnowledgeStore(tmp_path / "knowledge.sqlite")
    item = store.publish(finding())

    updated = store.verify(
        KnowledgeVerification(
            finding_id=item.id,
            verifier_desk_id="generalist-01",
            reproduced=True,
            confidence=0.8,
            counts_as_peer=False,
        )
    )
    assert updated.status == KnowledgeStatus.PEER_TESTING
