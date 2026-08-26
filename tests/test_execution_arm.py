from datetime import UTC, datetime, timedelta

import pytest

from dusty_dragon.governance.execution_arm import DemoExecutionArm, require_active_demo_arm


def arm() -> DemoExecutionArm:
    armed_at = datetime(2026, 8, 26, 16, 0, tzinfo=UTC)
    return DemoExecutionArm(
        desk_id="DEMO-01",
        account_id="ACCOUNT-01",
        armed_at_utc=armed_at,
        expires_at_utc=armed_at + timedelta(seconds=30),
    )


def test_matching_unexpired_arm_passes() -> None:
    require_active_demo_arm(
        arm(),
        desk_id="DEMO-01",
        account_id="ACCOUNT-01",
        now_utc=datetime(2026, 8, 26, 16, 0, 15, tzinfo=UTC),
    )


def test_missing_arm_fails_closed() -> None:
    with pytest.raises(PermissionError, match="disarmed"):
        require_active_demo_arm(
            None,
            desk_id="DEMO-01",
            account_id="ACCOUNT-01",
            now_utc=datetime(2026, 8, 26, 16, 0, 15, tzinfo=UTC),
        )


def test_expired_arm_fails_closed() -> None:
    with pytest.raises(PermissionError, match="expired"):
        require_active_demo_arm(
            arm(),
            desk_id="DEMO-01",
            account_id="ACCOUNT-01",
            now_utc=datetime(2026, 8, 26, 16, 0, 30, tzinfo=UTC),
        )


def test_arm_cannot_cross_desks_or_accounts() -> None:
    now = datetime(2026, 8, 26, 16, 0, 10, tzinfo=UTC)
    with pytest.raises(PermissionError, match="mismatched"):
        require_active_demo_arm(
            arm(),
            desk_id="DEMO-02",
            account_id="ACCOUNT-01",
            now_utc=now,
        )
    with pytest.raises(PermissionError, match="mismatched"):
        require_active_demo_arm(
            arm(),
            desk_id="DEMO-01",
            account_id="ACCOUNT-02",
            now_utc=now,
        )


def test_arm_requires_utc_and_positive_window() -> None:
    naive = datetime(2026, 8, 26, 16, 0)
    with pytest.raises(ValueError, match="UTC"):
        DemoExecutionArm(
            desk_id="DEMO-01",
            account_id="ACCOUNT-01",
            armed_at_utc=naive,
            expires_at_utc=datetime(2026, 8, 26, 16, 0, 30, tzinfo=UTC),
        )

    now = datetime(2026, 8, 26, 16, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="after arming"):
        DemoExecutionArm(
            desk_id="DEMO-01",
            account_id="ACCOUNT-01",
            armed_at_utc=now,
            expires_at_utc=now,
        )
