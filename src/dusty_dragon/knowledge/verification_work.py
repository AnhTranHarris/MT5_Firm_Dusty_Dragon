from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256

from pydantic import BaseModel, Field

from dusty_dragon.knowledge.institutional import KnowledgeFinding
from dusty_dragon.research.task_graph import ResearchTask, ResearchTaskGraph


class VerificationMode(StrEnum):
    INDEPENDENT_RESEARCH = "independent_research"
    PEER_DESK = "peer_desk"


class VerificationWorkItem(BaseModel):
    task_id: str
    mode: VerificationMode
    verification_identity: str
    counts_as_peer: bool
    seed: int = Field(ge=0)


class VerificationWorkPlan(BaseModel):
    finding_id: str
    required_verifications: int = Field(ge=1)
    mode: VerificationMode
    items: list[VerificationWorkItem] = Field(default_factory=list)


@dataclass(frozen=True)
class KnowledgeVerificationTaskPlanner:
    """Create durable reproduction work for observed institutional knowledge.

    Vibe-Trading roadmap: a finding must remain evidence-gated and reproducible.
    Automaton roadmap: verification is durable bounded work, not transient agent
    context. Kronos roadmap: a Kronos-related finding is tested as evidence and
    receives no direct execution or promotion authority.

    During the one-desk phase, independent research replays are explicitly NOT
    counted as peer-desk verification. Once real additional Trading Desks exist,
    their desk IDs can be supplied and true peer verification work is emitted.
    """

    graph: ResearchTaskGraph
    required_verifications: int = 2
    runs_per_symbol: int = 12
    priority: int = 65

    def __post_init__(self) -> None:
        if self.required_verifications < 1:
            raise ValueError("required_verifications must be positive")
        if not 10 <= self.runs_per_symbol <= 20:
            raise ValueError("runs_per_symbol must be between 10 and 20")
        if not 0 <= self.priority <= 100:
            raise ValueError("priority must be between 0 and 100")

    def plan(
        self,
        finding: KnowledgeFinding,
        *,
        available_peer_desk_ids: tuple[str, ...] = (),
    ) -> VerificationWorkPlan:
        peers = tuple(
            dict.fromkeys(
                desk_id
                for desk_id in available_peer_desk_ids
                if desk_id and desk_id != finding.source_desk_id
            )
        )
        if len(peers) >= self.required_verifications:
            mode = VerificationMode.PEER_DESK
            identities = peers[: self.required_verifications]
        else:
            mode = VerificationMode.INDEPENDENT_RESEARCH
            identities = tuple(
                f"research-replication:{finding.id}:{index}"
                for index in range(1, self.required_verifications + 1)
            )

        source_seeds = {reference.seed for reference in finding.evidence}
        items: list[VerificationWorkItem] = []
        for index, identity in enumerate(identities, start=1):
            seed = self._independent_seed(finding, index, source_seeds)
            task = ResearchTask(
                task_type="knowledge_verification",
                strategy_version=f"knowledge:{finding.claim_code}",
                priority=self.priority,
                payload={
                    "finding_id": str(finding.id),
                    "claim_code": finding.claim_code,
                    "statement": finding.statement,
                    "source_desk_id": finding.source_desk_id,
                    "verification_mode": mode.value,
                    "verification_identity": identity,
                    "counts_as_peer": mode == VerificationMode.PEER_DESK,
                    "seed": seed,
                    "runs_per_symbol": self.runs_per_symbol,
                    "prior_week_min": 1,
                    "prior_week_max": 8,
                    "include_unused_symbol_counterfactuals": True,
                    "archive_refs": [reference.archive_ref for reference in finding.evidence],
                    "source_checksums": [
                        reference.checksum_sha256 for reference in finding.evidence
                    ],
                    "source_regimes": [reference.regime for reference in finding.evidence],
                    "scope": finding.scope.model_dump(mode="json"),
                    "kronos_related": finding.kronos_related,
                    "promotion_authority": False,
                    "execution_authority": False,
                },
            )
            self.graph.add(task)
            items.append(
                VerificationWorkItem(
                    task_id=str(task.id),
                    mode=mode,
                    verification_identity=identity,
                    counts_as_peer=mode == VerificationMode.PEER_DESK,
                    seed=seed,
                )
            )

        return VerificationWorkPlan(
            finding_id=str(finding.id),
            required_verifications=self.required_verifications,
            mode=mode,
            items=items,
        )

    @staticmethod
    def _independent_seed(
        finding: KnowledgeFinding,
        index: int,
        source_seeds: set[int],
    ) -> int:
        digest = sha256(f"{finding.id}:{finding.claim_code}:{index}".encode()).digest()
        seed = int.from_bytes(digest[:4], "big") & 0x7FFFFFFF
        while seed in source_seeds:
            seed = (seed + 1) & 0x7FFFFFFF
        return seed
