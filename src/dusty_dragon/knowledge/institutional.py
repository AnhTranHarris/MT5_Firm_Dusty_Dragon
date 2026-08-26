from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from dusty_dragon.organization.expansion_roadmap import TradingDesk


class KnowledgeScopeLevel(StrEnum):
    FIRM = "firm"
    STYLE = "style"
    SECTOR = "sector"
    SYMBOL = "symbol"


class KnowledgeStatus(StrEnum):
    OBSERVED = "observed"
    PEER_TESTING = "peer_testing"
    VALIDATED = "validated"
    REJECTED = "rejected"


class FreshnessState(StrEnum):
    FRESH = "fresh"
    AGING = "aging"
    STALE = "stale"


class KnowledgeScope(BaseModel):
    level: KnowledgeScopeLevel
    style: str | None = None
    sector: str | None = None
    symbol: str | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> KnowledgeScope:
        if self.level == KnowledgeScopeLevel.FIRM and any(
            (self.style, self.sector, self.symbol)
        ):
            raise ValueError("firm knowledge cannot carry specialization labels")
        if self.level in {
            KnowledgeScopeLevel.STYLE,
            KnowledgeScopeLevel.SECTOR,
            KnowledgeScopeLevel.SYMBOL,
        } and not self.style:
            raise ValueError("specialized knowledge requires a style")
        if self.level in {
            KnowledgeScopeLevel.SECTOR,
            KnowledgeScopeLevel.SYMBOL,
        } and not self.sector:
            raise ValueError("sector and symbol knowledge require a sector")
        if self.level == KnowledgeScopeLevel.SYMBOL and not self.symbol:
            raise ValueError("symbol knowledge requires a symbol")
        return self

    def applies_to(self, desk: TradingDesk) -> bool:
        if self.level == KnowledgeScopeLevel.FIRM:
            return True
        if desk.style != self.style:
            return False
        if self.level == KnowledgeScopeLevel.STYLE:
            return True
        if desk.sector != self.sector:
            return False
        if self.level == KnowledgeScopeLevel.SECTOR:
            return True
        return desk.symbol == self.symbol


class EvidenceReference(BaseModel):
    """Reproducible support for a finding, never executable authority."""

    archive_ref: str
    checksum_sha256: str
    seed: int
    sample_size: int = Field(ge=1)
    runs: int = Field(ge=1)
    window_start: datetime
    window_end: datetime
    regime: str | None = None

    @model_validator(mode="after")
    def validate_window(self) -> EvidenceReference:
        if self.window_end <= self.window_start:
            raise ValueError("evidence window_end must be after window_start")
        return self


class KnowledgeFinding(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    source_desk_id: str
    claim_code: str
    statement: str
    scope: KnowledgeScope
    evidence: list[EvidenceReference] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    estimated_capital_effect_pct: float | None = None
    kronos_related: bool = False
    status: KnowledgeStatus = KnowledgeStatus.OBSERVED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_verified_at: datetime | None = None

    def freshness(
        self,
        now: datetime,
        *,
        aging_after_days: int = 30,
        stale_after_days: int = 90,
    ) -> FreshnessState:
        if aging_after_days <= 0 or stale_after_days <= aging_after_days:
            raise ValueError("freshness thresholds must satisfy 0 < aging < stale")
        anchor = self.last_verified_at or self.created_at
        age = now - anchor
        if age >= timedelta(days=stale_after_days):
            return FreshnessState.STALE
        if age >= timedelta(days=aging_after_days):
            return FreshnessState.AGING
        return FreshnessState.FRESH


class KnowledgeVerification(BaseModel):
    finding_id: UUID
    verifier_desk_id: str
    reproduced: bool
    confidence: float = Field(ge=0.0, le=1.0)
    counts_as_peer: bool = True
    net_capital_effect_pct: float | None = None
    evidence_ref: str | None = None
    verified_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    notes: str = ""


@dataclass(frozen=True)
class KnowledgeValidationPolicy:
    min_peer_verifications: int = 2
    min_reproduction_rate: float = 0.67

    def __post_init__(self) -> None:
        if self.min_peer_verifications < 1:
            raise ValueError("min_peer_verifications must be positive")
        if not 0 < self.min_reproduction_rate <= 1:
            raise ValueError("min_reproduction_rate must be in (0, 1]")

    def status_for(
        self,
        finding: KnowledgeFinding,
        verifications: list[KnowledgeVerification],
    ) -> KnowledgeStatus:
        eligible = [
            item
            for item in verifications
            if not item.counts_as_peer or item.verifier_desk_id != finding.source_desk_id
        ]
        if not eligible:
            return KnowledgeStatus.OBSERVED

        if len(eligible) >= self.min_peer_verifications:
            overall_rate = sum(item.reproduced for item in eligible) / len(eligible)
            if overall_rate < self.min_reproduction_rate:
                return KnowledgeStatus.REJECTED

        peer = [item for item in eligible if item.counts_as_peer]
        if len(peer) < self.min_peer_verifications:
            return KnowledgeStatus.PEER_TESTING

        peer_rate = sum(item.reproduced for item in peer) / len(peer)
        if peer_rate >= self.min_reproduction_rate:
            return KnowledgeStatus.VALIDATED
        return KnowledgeStatus.REJECTED


@dataclass
class InstitutionalKnowledgeStore:
    """SQLite-backed, evidence-gated knowledge shared across Trading Desks.

    This store has no trading, sizing, strategy-promotion, brokerage-account, or
    credential authority. It records claims, provenance, peer reproduction and
    freshness so one human-owned firm can reuse lessons without blindly copying
    one desk's anecdote.
    """

    path: Path
    validation_policy: KnowledgeValidationPolicy = KnowledgeValidationPolicy()

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_findings (
                    id TEXT PRIMARY KEY,
                    finding_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_verifications (
                    finding_id TEXT NOT NULL,
                    verifier_desk_id TEXT NOT NULL,
                    verification_json TEXT NOT NULL,
                    PRIMARY KEY(finding_id, verifier_desk_id)
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def publish(self, finding: KnowledgeFinding) -> KnowledgeFinding:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO knowledge_findings(id, finding_json) VALUES (?, ?)",
                (str(finding.id), finding.model_dump_json()),
            )
        return finding

    def verify(self, verification: KnowledgeVerification) -> KnowledgeFinding:
        finding = self.get(verification.finding_id)
        if finding is None:
            raise ValueError(f"finding not found: {verification.finding_id}")
        if verification.counts_as_peer and verification.verifier_desk_id == finding.source_desk_id:
            raise ValueError("source desk cannot count as peer verification")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO knowledge_verifications(
                    finding_id, verifier_desk_id, verification_json
                ) VALUES (?, ?, ?)
                ON CONFLICT(finding_id, verifier_desk_id) DO UPDATE SET
                    verification_json = excluded.verification_json
                """,
                (
                    str(verification.finding_id),
                    verification.verifier_desk_id,
                    verification.model_dump_json(),
                ),
            )
        verifications = self.verifications(finding.id)
        status = self.validation_policy.status_for(finding, verifications)
        last_verified = max(item.verified_at for item in verifications)
        updated = finding.model_copy(
            update={"status": status, "last_verified_at": last_verified}
        )
        self._replace(updated)
        return updated

    def get(self, finding_id: UUID) -> KnowledgeFinding | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT finding_json FROM knowledge_findings WHERE id = ?",
                (str(finding_id),),
            ).fetchone()
        return KnowledgeFinding.model_validate_json(row[0]) if row else None

    def verifications(self, finding_id: UUID) -> list[KnowledgeVerification]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT verification_json
                FROM knowledge_verifications
                WHERE finding_id = ?
                ORDER BY verifier_desk_id
                """,
                (str(finding_id),),
            ).fetchall()
        return [KnowledgeVerification.model_validate_json(row[0]) for row in rows]

    def usable_for(
        self,
        desk: TradingDesk,
        *,
        now: datetime | None = None,
        include_aging: bool = True,
        include_stale: bool = False,
    ) -> list[KnowledgeFinding]:
        now = now or datetime.now(UTC)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT finding_json FROM knowledge_findings"
            ).fetchall()
        usable: list[KnowledgeFinding] = []
        for row in rows:
            finding = KnowledgeFinding.model_validate_json(row[0])
            if finding.status != KnowledgeStatus.VALIDATED:
                continue
            if not finding.scope.applies_to(desk):
                continue
            freshness = finding.freshness(now)
            if freshness == FreshnessState.STALE and not include_stale:
                continue
            if freshness == FreshnessState.AGING and not include_aging:
                continue
            usable.append(finding)
        return sorted(usable, key=lambda item: (item.scope.level, item.claim_code))

    def _replace(self, finding: KnowledgeFinding) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE knowledge_findings SET finding_json = ? WHERE id = ?",
                (finding.model_dump_json(), str(finding.id)),
            )
