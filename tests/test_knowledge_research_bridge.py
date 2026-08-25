from datetime import UTC, datetime, timedelta

import pytest

from dusty_dragon.backtest.campaign_evaluator import CampaignEvaluation, ExperimentEvaluation
from dusty_dragon.knowledge.institutional import (
    KnowledgeScope,
    KnowledgeScopeLevel,
    KnowledgeStatus,
)
from dusty_dragon.knowledge.research_bridge import CampaignKnowledgeDraftFactory


def evaluation() -> CampaignEvaluation:
    experiments = [
        ExperimentEvaluation(
            experiment_type="prior_week_replay",
            tested_symbol="EURUSD",
            run_number=index,
            regime="trend_low_vol",
            raw_mean_signed_return_pct=0.12,
            estimated_cost_pct_per_trade=0.02,
            cost_adjusted_mean_return_pct=0.10,
            directional_accuracy=0.62,
            trade_signals=20,
        )
        for index in range(1, 13)
    ]
    return CampaignEvaluation(
        experiment_count=12,
        profitable_after_cost_count=10,
        profitable_after_cost_rate=10 / 12,
        mean_cost_adjusted_return_pct=0.10,
        worst_cost_adjusted_return_pct=-0.03,
        regime_mean_returns={"trend_low_vol": 0.10},
        symbol_mean_returns={"EURUSD": 0.10},
        experiments=experiments,
    )


def test_campaign_becomes_observed_not_validated_knowledge():
    start = datetime(2026, 8, 1, tzinfo=UTC)
    item = CampaignKnowledgeDraftFactory().draft(
        source_desk_id="generalist-01",
        claim_code="KRONOS_EURUSD_TREND",
        statement="Kronos-supported EURUSD trend setups retained edge after costs.",
        scope=KnowledgeScope(level=KnowledgeScopeLevel.FIRM),
        evaluation=evaluation(),
        archive_refs=["drive://dusty-dragon/boforex/EURUSD/M15/2026/08"],
        checksum_sha256="b" * 64,
        seed=77,
        window_start=start,
        window_end=start + timedelta(days=20),
        kronos_related=True,
    )

    assert item.status == KnowledgeStatus.OBSERVED
    assert item.confidence == pytest.approx(10 / 12)
    assert item.estimated_capital_effect_pct == pytest.approx(0.10)
    assert item.evidence[0].sample_size == 240
    assert item.evidence[0].runs == 12
    assert item.evidence[0].regime == "trend_low_vol"


def test_bridge_refuses_unsupported_research_drafts():
    start = datetime(2026, 8, 1, tzinfo=UTC)
    empty = CampaignEvaluation(
        experiment_count=0,
        profitable_after_cost_count=0,
    )

    with pytest.raises(ValueError, match="completed experiments"):
        CampaignKnowledgeDraftFactory().draft(
            source_desk_id="generalist-01",
            claim_code="UNSUPPORTED",
            statement="No evidence.",
            scope=KnowledgeScope(level=KnowledgeScopeLevel.FIRM),
            evaluation=empty,
            archive_refs=["drive://placeholder"],
            checksum_sha256="c" * 64,
            seed=1,
            window_start=start,
            window_end=start + timedelta(days=1),
            kronos_related=False,
        )
