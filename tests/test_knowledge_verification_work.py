from datetime import UTC, datetime, timedelta
from uuid import UUID

from dusty_dragon.knowledge.institutional import (
    EvidenceReference,
    KnowledgeFinding,
    KnowledgeScope,
    KnowledgeScopeLevel,
)
from dusty_dragon.knowledge.verification_work import (
    KnowledgeVerificationTaskPlanner,
    VerificationMode,
)
from dusty_dragon.research.task_graph import ResearchTaskGraph


def observed_finding() -> KnowledgeFinding:
    now = datetime(2026, 8, 25, tzinfo=UTC)
    return KnowledgeFinding(
        source_desk_id="generalist-01",
        claim_code="KRONOS_TREND_SUPPORT",
        statement="Kronos trend evidence retained positive edge after costs.",
        scope=KnowledgeScope(level=KnowledgeScopeLevel.FIRM),
        evidence=[
            EvidenceReference(
                archive_ref="drive://dusty-dragon/boforex/EURUSD/M15/2026/08",
                checksum_sha256="a" * 64,
                seed=42,
                sample_size=240,
                runs=12,
                window_start=now - timedelta(days=30),
                window_end=now - timedelta(days=1),
                regime="trend_low_vol",
            )
        ],
        confidence=0.82,
        estimated_capital_effect_pct=0.12,
        kronos_related=True,
        created_at=now,
    )


def test_one_desk_phase_uses_research_replication_not_fake_peers(tmp_path):
    finding = observed_finding()
    graph = ResearchTaskGraph(tmp_path / "research.sqlite")
    plan = KnowledgeVerificationTaskPlanner(graph).plan(finding)

    assert plan.mode == VerificationMode.INDEPENDENT_RESEARCH
    assert len(plan.items) == 2
    assert all(not item.counts_as_peer for item in plan.items)
    assert all(item.verification_identity.startswith("research-replication:") for item in plan.items)
    assert len({item.seed for item in plan.items}) == 2
    assert 42 not in {item.seed for item in plan.items}

    tasks = graph.all()
    assert len(tasks) == 2
    for task in tasks:
        assert task.task_type == "knowledge_verification"
        assert task.priority == 65
        assert task.payload["counts_as_peer"] is False
        assert task.payload["promotion_authority"] is False
        assert task.payload["execution_authority"] is False
        assert task.payload["runs_per_symbol"] == 12
        assert task.payload["prior_week_min"] == 1
        assert task.payload["prior_week_max"] == 8
        assert task.payload["include_unused_symbol_counterfactuals"] is True
        assert task.payload["kronos_related"] is True


def test_real_peer_desks_are_used_only_when_enough_exist(tmp_path):
    finding = observed_finding()
    graph = ResearchTaskGraph(tmp_path / "research.sqlite")
    plan = KnowledgeVerificationTaskPlanner(graph).plan(
        finding,
        available_peer_desk_ids=(
            "generalist-01",
            "generalist-02",
            "generalist-03",
            "generalist-03",
        ),
    )

    assert plan.mode == VerificationMode.PEER_DESK
    assert [item.verification_identity for item in plan.items] == [
        "generalist-02",
        "generalist-03",
    ]
    assert all(item.counts_as_peer for item in plan.items)

    for task in graph.all():
        assert task.payload["verification_mode"] == VerificationMode.PEER_DESK.value
        assert task.payload["counts_as_peer"] is True
        assert task.payload["source_desk_id"] == "generalist-01"


def test_one_real_peer_is_insufficient_and_falls_back_to_research_replication(tmp_path):
    finding = observed_finding()
    graph = ResearchTaskGraph(tmp_path / "research.sqlite")
    plan = KnowledgeVerificationTaskPlanner(graph).plan(
        finding,
        available_peer_desk_ids=("generalist-02",),
    )

    assert plan.mode == VerificationMode.INDEPENDENT_RESEARCH
    assert all(not item.counts_as_peer for item in plan.items)


def test_verification_work_references_exact_finding_and_archive(tmp_path):
    finding = observed_finding()
    graph = ResearchTaskGraph(tmp_path / "research.sqlite")
    plan = KnowledgeVerificationTaskPlanner(graph).plan(finding)

    task_ids = {UUID(item.task_id) for item in plan.items}
    tasks = {task.id: task for task in graph.all()}
    assert task_ids == set(tasks)
    for task in tasks.values():
        assert task.payload["finding_id"] == str(finding.id)
        assert task.payload["archive_refs"] == [
            "drive://dusty-dragon/boforex/EURUSD/M15/2026/08"
        ]
        assert task.payload["source_checksums"] == ["a" * 64]
        assert task.payload["source_regimes"] == ["trend_low_vol"]
        assert task.payload["scope"] == {"level": "firm", "style": None, "sector": None, "symbol": None}
