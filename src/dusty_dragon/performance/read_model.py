from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from math import isfinite


@dataclass(frozen=True, slots=True)
class EquityObservation:
    """One authoritative account-equity sample in deposit currency."""

    observed_at_utc: datetime
    equity: float
    balance: float

    def __post_init__(self) -> None:
        _require_utc(self.observed_at_utc, "observed_at_utc")
        _require_finite_nonnegative(self.equity, "equity")
        _require_finite_nonnegative(self.balance, "balance")


@dataclass(frozen=True, slots=True)
class CapitalFlowObservation:
    """External cash movement that must not be reported as trading return."""

    observed_at_utc: datetime
    amount: float
    reference: str

    def __post_init__(self) -> None:
        _require_utc(self.observed_at_utc, "observed_at_utc")
        if not isfinite(self.amount):
            raise ValueError("amount must be finite")
        if not self.reference.strip():
            raise ValueError("reference must be non-empty")


@dataclass(frozen=True, slots=True)
class PerformancePoint:
    observed_at_utc: datetime
    equity: float
    cumulative_return_pct: float


def build_time_weighted_curve(
    observations: tuple[EquityObservation, ...],
    flows: tuple[CapitalFlowObservation, ...] = (),
) -> tuple[PerformancePoint, ...]:
    """Build a flow-adjusted chained return curve from persisted equity samples.

    External cash flows occurring after the previous sample and at/before the
    current sample are removed from the current equity before calculating that
    sub-period return. This prevents deposits, withdrawals, demo resets, and
    other owner/broker capital adjustments from masquerading as trading P&L.

    Production collectors should persist account_info() equity/balance samples
    and normalize capital-flow events separately. The UI consumes only these
    canonical points; it must never calculate authoritative returns from raw
    MetaTrader objects in JavaScript.
    """

    if not observations:
        return ()

    ordered = tuple(sorted(observations, key=lambda item: item.observed_at_utc))
    if len({item.observed_at_utc for item in ordered}) != len(ordered):
        raise ValueError("equity observations must have unique timestamps")

    ordered_flows = tuple(sorted(flows, key=lambda item: item.observed_at_utc))
    if ordered[0].equity <= 0:
        raise ValueError("first equity observation must be positive")

    points = [
        PerformancePoint(
            observed_at_utc=ordered[0].observed_at_utc,
            equity=ordered[0].equity,
            cumulative_return_pct=0.0,
        )
    ]
    cumulative_factor = 1.0
    flow_index = 0

    while (
        flow_index < len(ordered_flows)
        and ordered_flows[flow_index].observed_at_utc <= ordered[0].observed_at_utc
    ):
        flow_index += 1

    for previous, current in zip(ordered, ordered[1:]):
        if previous.equity <= 0:
            raise ValueError("equity observation preceding a return period must be positive")

        period_flow = 0.0
        while (
            flow_index < len(ordered_flows)
            and ordered_flows[flow_index].observed_at_utc <= current.observed_at_utc
        ):
            flow = ordered_flows[flow_index]
            if flow.observed_at_utc > previous.observed_at_utc:
                period_flow += flow.amount
            flow_index += 1

        adjusted_ending_equity = current.equity - period_flow
        subperiod_return = adjusted_ending_equity / previous.equity - 1.0
        cumulative_factor *= 1.0 + subperiod_return

        points.append(
            PerformancePoint(
                observed_at_utc=current.observed_at_utc,
                equity=current.equity,
                cumulative_return_pct=(cumulative_factor - 1.0) * 100.0,
            )
        )

    return tuple(points)


def _require_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be timezone-aware UTC")


def _require_finite_nonnegative(value: float, field_name: str) -> None:
    if not isfinite(value) or value < 0:
        raise ValueError(f"{field_name} must be finite and non-negative")
