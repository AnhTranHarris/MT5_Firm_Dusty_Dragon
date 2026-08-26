from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class DemoExecutionArm:
    """Ephemeral authority prerequisite for demo broker writes.

    This object is intentionally not persisted. A process restart therefore returns
    Dusty Dragon to a disarmed state by construction.
    """

    desk_id: str
    account_id: str
    armed_at_utc: datetime
    expires_at_utc: datetime

    def __post_init__(self) -> None:
        if not self.desk_id.strip():
            raise ValueError("desk_id is required")
        if not self.account_id.strip():
            raise ValueError("account_id is required")
        _require_utc(self.armed_at_utc)
        _require_utc(self.expires_at_utc)
        if self.expires_at_utc <= self.armed_at_utc:
            raise ValueError("execution arm expiry must be after arming time")

    def is_active_for(
        self,
        *,
        desk_id: str,
        account_id: str,
        now_utc: datetime,
    ) -> bool:
        _require_utc(now_utc)
        return (
            desk_id == self.desk_id
            and account_id == self.account_id
            and self.armed_at_utc <= now_utc < self.expires_at_utc
        )


def require_active_demo_arm(
    arm: DemoExecutionArm | None,
    *,
    desk_id: str,
    account_id: str,
    now_utc: datetime,
) -> None:
    """Fail closed unless a matching, non-expired ephemeral arm is present."""

    if arm is None:
        raise PermissionError("demo execution is disarmed")
    if not arm.is_active_for(desk_id=desk_id, account_id=account_id, now_utc=now_utc):
        raise PermissionError("demo execution arm is missing, mismatched, or expired")


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("timestamps must be timezone-aware UTC")
