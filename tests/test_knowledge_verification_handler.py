from datetime import UTC, datetime, timedelta

import pytest

from dusty_dragon.backtest.campaign_evaluator import (
    CampaignEvaluation,
    ExperimentEvaluation,
)
from dusty_dragon.knowledge.institutional import (
    EvidenceReference,
    InstitutionalKnowledgeStore,
    KnowledgeFinding,
    KnowledgeScope,
    KnowledgeScopeLevel,
    KnowledgeStatus,
)
from dusty_dragon.knowledge.verification_handler import (
    KnowledgeVerificationTaskHandler,
    VerificationResearchResult,
)
from dusty_dragon.research.task_graph import ResearchTask


def finding(*, effect: float = 0.10) -> KnowledgeFinding:
    now = datetime.now(UTC)
    return KnowledgeFinding(
        source_desk_id="generalist-01",
        claim_code="EURUSD_TREND_EDGE",
        statement="The tested configuration has a post-cost edge.",
        scope=KnowledgeScope(level=KnowledgeScopeLevel.FIRM),
        evidence=[
            EvidenceReference(
                archive_ref="drive://source",
                checksum_sha256="a" * 64,
                seed=42,
                sample_size=100,
                runs=12,
                window_start=now - timedelta(days=14),
                window_end=now - timedelta(days=7),
                regime="trend_low_vol",
            )
        ],
        confidence=0.75,
        estimated_capital_effect_pct=effect,
        kronos_related=True,
    )


def evaluation(*, effect: float, profitable_rate: float, signals: int = 10) -> CampaignEvaluation:
    experiments = [
        ExperimentEvaluation(
            experiment_type="prior_week",
            tested_symbol="EURUSD",
            run_number=1,
            regime="trend_low_vol",
            estimated_cost_pct_per_trade=0.01,
            cost_adjusted_mean_return_pct=effect,
            directional_accuracy=0.60,
            trade_signals=signals,
        )
    ]
    return CampaignEvaluation(
        experiment_count=1,
        profitable_after_cost_count=int(profitable_rate > 0),
        profitable_after_cost_rate=profitable_rate,
        mean_cost_adjusted_return_pct=effect,
        worst_cost_adjusted_return_pct=effect,
        experiments=experiments,
    )


def task(item: KnowledgeFinding, *, identity: str, peer: bool) -> ResearchTask:
    return ResearchTask(
        task_type="knowledge_verification",
        strategy_version=f"knowledge:{item.claim_code}",
        payload={
            "finding_id": str(item.id),
            "verification_mode": "peer_desk" if peer else "independent_research",
            "verification_identity": identity,
            "counts_as_peer": peer,
            "runs_per_symbol": 12,
            "prior_week_min": 1,
            "prior_week_max": 8,
            "include_unused_symbol_counterfactuals": True,
            "promotion_authority": False,
            "execution_authority": False,
        },
    )


def test_non_peer_reproduction_cannot_validate_but_can_advance_testing(tmp_path):
    store = InstitutionalKnowledgeStore(tmp_path / "knowledge.sqlite")
    item = store.publish(finding())
    handler = KnowledgeVerificationTaskHandler(
        store,
        lambda _: VerificationResearchResult(
            evaluation=evaluation(effect=0.12, profitable_rate=0.75),
            evidence_ref="drive://replica-1",
        ),
    )

    output = handler(task(item, identity="research-replication:1", peer=False), {})

    assert output["reproduced"] is True
    assert output["knowledge_status"] == KnowledgeStatus.PEER_TESTING.value
    stored = store.verifications(item.id)
    assert stored[0].counts_as_peer is False


def test_two_real_peer_reproductions_validate(tmp_path):
    store = InstitutionalKnowledgeStore(tmp_path / "knowledge.sqlite")
    item = store.publish(finding())
    handler = KnowledgeVerificationTaskHandler(
        store,
        lambda _: VerificationResearchResult(
            evaluation=evaluation(effect=0.08, profitable_rate=0.80),
            evidence_ref="drive://peer-proof",
        ),
    )

    first = handler(task(item, identity="generalist-02", peer=True), {})
    second = handler(task(item, identity="generalist-03", peer=True), {})

    assert first["knowledge_status"] == KnowledgeStatus.PEER_TESTING.value
    assert second["knowledge_status"] == KnowledgeStatus.VALIDATED.value


def test_repeated_negative_reproduction_rejects_positive_claim(tmp_path):
    store = InstitutionalKnowledgeStore(tmp_path / "knowledge.sqlite")
    item = store.publish(finding())
    handler = KnowledgeVerificationTaskHandler(
        store,
        lambda _: VerificationResearchResult(
            evaluation=evaluation(effect=-0.09, profitable_rate=0.20),
            evidence_ref="drive://negative-proof",
        ),
    )

    handler(task(item, identity="research-replication:1", peer=False), {})
    second = handler(task(item, identity="research-replication:2", peer=False), {})

    assert second["reproduced"] is False
    assert second["knowledge_status"] == KnowledgeStatus.REJECTED.value


def test_negative_claim_reproduces_on_negative_post_cost_effect(tmp_path):
    store = InstitutionalKnowledgeStore(tmp_path / "knowledge.sqlite")
    item = store.publish(finding(effect=-0.10))
    handler = KnowledgeVerificationTaskHandler(
        store,
        lambda _: VerificationResearchResult(
            evaluation=evaluation(effect=-0.07, profitable_rate=0.25),
            evidence_ref="drive://negative-edge",
        ),
    )

    output = handler(task(item, identity="research-replication:1", peer=False), {})

    assert output["reproduced"] is True
    assert output["confidence"] == pytest.approx(0.75)


def test_handler_fails_closed_on_execution_authority(tmp_path):
    store = InstitutionalKnowledgeStore(tmp_path / "knowledge.sqlite")
    item = store.publish(finding())
    handler = KnowledgeVerificationTaskHandler(
        store,
        lambda _: VerificationResearchResult(
            evaluation=evaluation(effect=0.10, profitable_rate=0.80),
            evidence_ref="drive://proof",
        ),
    )
    invalid = task(item, identity="research-replication:1", peer=False)
    invalid.payload["execution_authority"] = True

    with pytest.raises(PermissionError):
        handler(invalid, {})


def test_handler_rejects_zero_signal_research(tmp_path):
    store = InstitutionalKnowledgeStore(tmp_path / "knowledge.sqlite")
    item = store.publish(finding())
    handler = KnowledgeVerificationTaskHandler(
        store,
        lambda _: VerificationResearchResult(
            evaluation=evaluation(effect=0.10, profitable_rate=0.80, signals=0),
            evidence_ref="drive://empty",
        ),
    )

    with pytest.raises(ValueError, match="observed trade signals"):
        handler(task(item, identity="research-replication:1", peer=False), {})
