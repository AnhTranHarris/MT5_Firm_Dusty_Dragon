from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from dusty_dragon.domain.accounts import AccountSnapshot, PositionSnapshot


class ReconciliationStatus(StrEnum):
    MATCH = "MATCH"
    DRIFT = "DRIFT"
    INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    status: ReconciliationStatus
    reasons: tuple[str, ...]

    @property
    def safe_for_new_orders(self) -> bool:
        return self.status is ReconciliationStatus.MATCH


def reconcile_account(
    *,
    expected: AccountSnapshot,
    observed: AccountSnapshot,
    expected_positions: tuple[PositionSnapshot, ...],
    observed_positions: tuple[PositionSnapshot, ...],
    money_tolerance: float = 0.01,
) -> ReconciliationResult:
    """Compare sovereign ledger expectations with broker truth and fail closed on drift."""

    if money_tolerance < 0:
        raise ValueError("money_tolerance cannot be negative")

    reasons: list[str] = []
    if expected.account_id != observed.account_id:
        reasons.append("account_id mismatch")
    if expected.desk_id != observed.desk_id:
        reasons.append("desk_id mismatch")
    if expected.broker_id != observed.broker_id:
        reasons.append("broker_id mismatch")
    if expected.environment is not observed.environment:
        reasons.append("account environment mismatch")

    for field_name in ("balance", "equity", "margin", "free_margin"):
        expected_value = getattr(expected, field_name)
        observed_value = getattr(observed, field_name)
        if abs(expected_value - observed_value) > money_tolerance:
            reasons.append(f"{field_name} drift")

    expected_map = _position_map(expected_positions, expected.account_id)
    observed_map = _position_map(observed_positions, observed.account_id)
    if expected_map is None or observed_map is None:
        return ReconciliationResult(
            status=ReconciliationStatus.INVALID,
            reasons=("position account identity is invalid",),
        )

    if expected_map.keys() != observed_map.keys():
        reasons.append("position set drift")
    else:
        for position_id, expected_position in expected_map.items():
            observed_position = observed_map[position_id]
            if expected_position.instrument_id != observed_position.instrument_id:
                reasons.append(f"position {position_id} instrument drift")
            if expected_position.side is not observed_position.side:
                reasons.append(f"position {position_id} side drift")
            if expected_position.volume != observed_position.volume:
                reasons.append(f"position {position_id} volume drift")

    if reasons:
        return ReconciliationResult(
            status=ReconciliationStatus.DRIFT,
            reasons=tuple(reasons),
        )
    return ReconciliationResult(status=ReconciliationStatus.MATCH, reasons=())


def _position_map(
    positions: tuple[PositionSnapshot, ...],
    account_id: str,
) -> dict[str, PositionSnapshot] | None:
    result: dict[str, PositionSnapshot] = {}
    for position in positions:
        if position.account_id != account_id or position.position_id in result:
            return None
        result[position.position_id] = position
    return result
