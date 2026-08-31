from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel, Field

from dusty_dragon.backtest.campaign_evaluator import CampaignEvaluation
from dusty_dragon.knowledge.institutional import (
    InstitutionalKnowledgeStore,
    KnowledgeStatus,
    KnowledgeVerification,
)
from dusty_dragon.research.task_graph import ResearchTask


class VerificationResearchResult(BaseModel):
    """Completed reproduction research plus durable provenance."""

    evaluation: CampaignEvaluation
    evidence_ref: str


class VerificationHandlerResult(BaseModel):
    finding_id: str
    verification_identity: str
    counts_as_peer: bool
    reproduced: bool
    confidence: float = Field(ge=0.0, le=1.0)
    net_capital_effect_pct: float
    knowledge_status: KnowledgeStatus
    evidence_ref: str


VerificationResearchRunner = Callable[[ResearchTask], VerificationResearchResult]


@dataclass(frozen=True)
class KnowledgeVerificationTaskHandler:
    """Execute one durable knowledge-reproduction task without trading authority.

    Vibe-Trading roadmap: reproduction is judged after explicit cost/regime
    evaluation and requires observable economic evidence, not narrative agreement.

    Automaton roadmap: a durable task produces durable state that survives the
    worker invocation; failures remain retryable through the shared task graph.

    Kronos roadmap: Kronos-related findings are hypotheses to reproduce. Forecast
    involvement grants no execution, sizing, strategy-promotion, or validation
    shortcut.
    """

    knowledge: InstitutionalKnowledgeStore
    runner: VerificationResearchRunner
    minimum_profitable_rate: float = 0.50
    minimum_effect_abs_pct: float = 1e-9

    def __post_init__(self) -> None:
        if not 0.0 <= self.minimum_profitable_rate <= 1.0:
            raise ValueError("minimum_profitable_rate must be between 0 and 1")
        if self.minimum_effect_abs_pct <= 0:
            raise ValueError("minimum_effect_abs_pct must be positive")

    def __call__(self, task: ResearchTask, _dependencies: dict) -> dict:
        if task.task_type != "knowledge_verification":
            raise ValueError("handler only accepts knowledge_verification tasks")
        self._validate_task_contract(task)

        finding = self.knowledge.get(task.payload["finding_id"])
        if finding is None:
            raise ValueError(f"finding not found: {task.payload['finding_id']}")
        if str(finding.id) != str(task.payload["finding_id"]):
            raise ValueError("verification finding identity mismatch")
        if finding.estimated_capital_effect_pct is None:
            raise ValueError("finding lacks estimated capital effect")
        if abs(finding.estimated_capital_effect_pct) < self.minimum_effect_abs_pct:
            raise ValueError("finding capital effect is too small to reproduce safely")

        result = self.runner(task)
        evaluation = result.evaluation
        if not result.evidence_ref:
            raise ValueError("verification research requires durable evidence provenance")
        if evaluation.experiment_count <= 0:
            raise ValueError("verification research requires completed experiments")
        if evaluation.mean_cost_adjusted_return_pct is None:
            raise ValueError("verification research requires post-cost capital effect")
        if evaluation.profitable_after_cost_rate is None:
            raise ValueError("verification research requires profitable-after-cost rate")
        trade_signals = sum(item.trade_signals for item in evaluation.experiments)
        if trade_signals <= 0:
            raise ValueError("verification research requires observed trade signals")

        reproduced, confidence = self._reproduction_score(
            original_effect=finding.estimated_capital_effect_pct,
            observed_effect=evaluation.mean_cost_adjusted_return_pct,
            profitable_rate=evaluation.profitable_after_cost_rate,
        )
        verification = KnowledgeVerification(
            finding_id=finding.id,
            verifier_desk_id=str(task.payload["verification_identity"]),
            reproduced=reproduced,
            confidence=confidence,
            counts_as_peer=bool(task.payload["counts_as_peer"]),
            net_capital_effect_pct=evaluation.mean_cost_adjusted_return_pct,
            evidence_ref=result.evidence_ref,
            notes=(
                f"mode={task.payload['verification_mode']}; "
                f"experiments={evaluation.experiment_count}; trade_signals={trade_signals}"
            ),
        )
        updated = self.knowledge.verify(verification)
        return VerificationHandlerResult(
            finding_id=str(finding.id),
            verification_identity=verification.verifier_desk_id,
            counts_as_peer=verification.counts_as_peer,
            reproduced=reproduced,
            confidence=confidence,
            net_capital_effect_pct=evaluation.mean_cost_adjusted_return_pct,
            knowledge_status=updated.status,
            evidence_ref=result.evidence_ref,
        ).model_dump(mode="json")

    def _reproduction_score(
        self,
        *,
        original_effect: float,
        observed_effect: float,
        profitable_rate: float,
    ) -> tuple[bool, float]:
        if original_effect > 0:
            reproduced = (
                observed_effect > self.minimum_effect_abs_pct
                and profitable_rate >= self.minimum_profitable_rate
            )
            return reproduced, profitable_rate
        reproduced = (
            observed_effect < -self.minimum_effect_abs_pct
            and profitable_rate <= 1.0 - self.minimum_profitable_rate
        )
        return reproduced, 1.0 - profitable_rate

    @staticmethod
    def _validate_task_contract(task: ResearchTask) -> None:
        required = {
            "finding_id",
            "verification_mode",
            "verification_identity",
            "counts_as_peer",
            "runs_per_symbol",
            "prior_week_min",
            "prior_week_max",
            "include_unused_symbol_counterfactuals",
            "promotion_authority",
            "execution_authority",
        }
        missing = sorted(required.difference(task.payload))
        if missing:
            raise ValueError(f"verification task missing required fields: {missing}")
        if bool(task.payload["promotion_authority"]):
            raise PermissionError("knowledge verification cannot promote a strategy")
        if bool(task.payload["execution_authority"]):
            raise PermissionError("knowledge verification cannot execute trades")
        if not 10 <= int(task.payload["runs_per_symbol"]) <= 20:
            raise ValueError("verification runs_per_symbol must be between 10 and 20")
        if int(task.payload["prior_week_min"]) != 1 or int(task.payload["prior_week_max"]) != 8:
            raise ValueError("verification historical replay range must remain 1-8 weeks")
        if not bool(task.payload["include_unused_symbol_counterfactuals"]):
            raise ValueError("verification requires unused-symbol counterfactuals")
