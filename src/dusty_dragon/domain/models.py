from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DeskHealth(StrEnum):
    NORMAL = "NORMAL"
    CAUTION = "CAUTION"
    DEFENSIVE = "DEFENSIVE"
    HALTED = "HALTED"
    QUARANTINED = "QUARANTINED"


class CohortOutcome(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    INVALID = "INVALID"


class GraduationLevel(StrEnum):
    INTRADAY = "INTRADAY"
    HOLD_2D = "HOLD_2D"
    MULTIDAY = "MULTIDAY"
    WEEKLY = "WEEKLY"
    MULTIWEEK = "MULTIWEEK"


class SignalDisposition(StrEnum):
    APPROVED = "APPROVED"
    DESK_RISK_REJECTED = "DESK_RISK_REJECTED"
    PORTFOLIO_CAPACITY_REJECTED = "PORTFOLIO_CAPACITY_REJECTED"
    BAD_SIGNAL = "BAD_SIGNAL"


@dataclass(frozen=True, slots=True)
class DeskQualification:
    desk_id: str
    outcome: CohortOutcome
    graduation_level: GraduationLevel


@dataclass(frozen=True, slots=True)
class EquityClose:
    trading_day: str
    closing_equity: float
    healthy: bool = True


@dataclass(frozen=True, slots=True)
class DeskExpansionEvidence:
    desk_id: str
    closes: tuple[EquityClose, ...]
    health: DeskHealth = DeskHealth.NORMAL
    risk_compliant: bool = True
    unresolved_critical_incident: bool = False


@dataclass(frozen=True, slots=True)
class OrderIntent:
    desk_id: str
    instrument_id: str
    side: str
    requested_risk_fraction: float


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    passed: bool
    reason: str


@dataclass(frozen=True, slots=True)
class ApprovedOrder:
    """Capital-authorized order created only by sovereign governance code."""

    desk_id: str
    instrument_id: str
    side: str
    approved_risk_fraction: float
    policy_id: str
