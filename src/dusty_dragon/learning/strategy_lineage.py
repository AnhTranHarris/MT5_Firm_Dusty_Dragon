from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class StrategyStatus(StrEnum):
    CHAMPION = "champion"
    CHALLENGER = "challenger"
    REJECTED = "rejected"
    RETIRED = "retired"


class StrategyRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    version: str
    parent_id: UUID | None = None
    generation: int = Field(ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: StrategyStatus
    config: dict[str, Any] = Field(default_factory=dict)


class PromotionEvidence(BaseModel):
    """Minimum validation gates required before a challenger can be champion."""

    backtest_passed: bool = False
    walk_forward_passed: bool = False
    paper_passed: bool = False
    compared_to_champion: bool = False
    notes: str = ""

    @property
    def complete(self) -> bool:
        return all(
            (
                self.backtest_passed,
                self.walk_forward_passed,
                self.paper_passed,
                self.compared_to_champion,
            )
        )
