from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from dusty_dragon.backtest.campaign_evaluator import CampaignEvaluation
from dusty_dragon.knowledge.institutional import (
    EvidenceReference,
    KnowledgeFinding,
    KnowledgeScope,
)


@dataclass(frozen=True)
class CampaignKnowledgeDraftFactory:
    """Convert completed quantitative research into an unvalidated knowledge draft.

    The bridge is intentionally one-way and authority-free: research may propose
    a finding, but only peer reproduction inside InstitutionalKnowledgeStore can
    validate it for reuse by other Trading Desks.
    """

    def draft(
        self,
        *,
        source_desk_id: str,
        claim_code: str,
        statement: str,
        scope: KnowledgeScope,
        evaluation: CampaignEvaluation,
        archive_refs: list[str],
        checksum_sha256: str,
        seed: int,
        window_start: datetime,
        window_end: datetime,
        kronos_related: bool,
    ) -> KnowledgeFinding:
        if evaluation.experiment_count <= 0:
            raise ValueError("knowledge draft requires completed experiments")
        if evaluation.mean_cost_adjusted_return_pct is None:
            raise ValueError("knowledge draft requires cost-adjusted return evidence")
        if evaluation.profitable_after_cost_rate is None:
            raise ValueError("knowledge draft requires profitable-after-cost rate")
        if not archive_refs:
            raise ValueError("knowledge draft requires at least one archive reference")

        sample_size = sum(item.trade_signals for item in evaluation.experiments)
        if sample_size <= 0:
            raise ValueError("knowledge draft requires observed trade signals")

        regimes = sorted({item.regime for item in evaluation.experiments})
        regime = regimes[0] if len(regimes) == 1 else "mixed"
        evidence = [
            EvidenceReference(
                archive_ref=archive_ref,
                checksum_sha256=checksum_sha256,
                seed=seed,
                sample_size=sample_size,
                runs=evaluation.experiment_count,
                window_start=window_start,
                window_end=window_end,
                regime=regime,
            )
            for archive_ref in archive_refs
        ]
        return KnowledgeFinding(
            source_desk_id=source_desk_id,
            claim_code=claim_code,
            statement=statement,
            scope=scope,
            evidence=evidence,
            confidence=evaluation.profitable_after_cost_rate,
            estimated_capital_effect_pct=evaluation.mean_cost_adjusted_return_pct,
            kronos_related=kronos_related,
        )
