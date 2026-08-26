from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum


class WorkTier(IntEnum):
    SAFETY = 0
    TRADING = 1
    EVIDENCE = 2
    VALIDATION = 3
    RESEARCH = 4


class ResourceClass(StrEnum):
    LIGHT = "LIGHT"
    MODERATE = "MODERATE"
    HEAVY = "HEAVY"
    VERY_HEAVY = "VERY_HEAVY"
    ACCELERATOR_REQUIRED = "ACCELERATOR_REQUIRED"


class ResourcePressure(StrEnum):
    NORMAL = "NORMAL"
    ELEVATED = "ELEVATED"
    URGENT = "URGENT"


class SchedulingAction(StrEnum):
    RUN = "RUN"
    THROTTLE = "THROTTLE"
    QUEUE = "QUEUE"
    REJECT_UNSUPPORTED = "REJECT_UNSUPPORTED"


@dataclass(frozen=True, slots=True)
class ResourceSnapshot:
    cpu_fraction: float
    memory_fraction: float
    disk_io_fraction: float
    accelerator_available: bool = False

    def __post_init__(self) -> None:
        for name, value in (
            ("cpu_fraction", self.cpu_fraction),
            ("memory_fraction", self.memory_fraction),
            ("disk_io_fraction", self.disk_io_fraction),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class ResourcePolicy:
    elevated_threshold: float = 0.75
    urgent_threshold: float = 0.90

    def __post_init__(self) -> None:
        if not 0.0 < self.elevated_threshold < self.urgent_threshold <= 1.0:
            raise ValueError("resource thresholds must satisfy 0 < elevated < urgent <= 1")


@dataclass(frozen=True, slots=True)
class WorkRequest:
    job_id: str
    tier: WorkTier
    resource_class: ResourceClass


@dataclass(frozen=True, slots=True)
class SchedulingDecision:
    job_id: str
    pressure: ResourcePressure
    action: SchedulingAction
    reason: str


class ResourceGovernor:
    """Deterministic admission control that protects safety and trading workloads."""

    def __init__(self, policy: ResourcePolicy | None = None) -> None:
        self._policy = policy or ResourcePolicy()

    def pressure(self, snapshot: ResourceSnapshot) -> ResourcePressure:
        peak = max(
            snapshot.cpu_fraction,
            snapshot.memory_fraction,
            snapshot.disk_io_fraction,
        )
        if peak >= self._policy.urgent_threshold:
            return ResourcePressure.URGENT
        if peak >= self._policy.elevated_threshold:
            return ResourcePressure.ELEVATED
        return ResourcePressure.NORMAL

    def decide(self, request: WorkRequest, snapshot: ResourceSnapshot) -> SchedulingDecision:
        pressure = self.pressure(snapshot)

        if (
            request.resource_class is ResourceClass.ACCELERATOR_REQUIRED
            and not snapshot.accelerator_available
        ):
            return SchedulingDecision(
                job_id=request.job_id,
                pressure=pressure,
                action=SchedulingAction.REJECT_UNSUPPORTED,
                reason="required accelerator is unavailable",
            )

        if request.tier in {WorkTier.SAFETY, WorkTier.TRADING}:
            return SchedulingDecision(
                job_id=request.job_id,
                pressure=pressure,
                action=SchedulingAction.RUN,
                reason="protected workload",
            )

        if pressure is ResourcePressure.NORMAL:
            return SchedulingDecision(
                job_id=request.job_id,
                pressure=pressure,
                action=SchedulingAction.RUN,
                reason="resources available",
            )

        if pressure is ResourcePressure.ELEVATED:
            action = (
                SchedulingAction.THROTTLE
                if request.tier in {WorkTier.EVIDENCE, WorkTier.VALIDATION}
                else SchedulingAction.QUEUE
            )
            return SchedulingDecision(
                job_id=request.job_id,
                pressure=pressure,
                action=action,
                reason="elevated resource pressure",
            )

        action = (
            SchedulingAction.THROTTLE
            if request.tier is WorkTier.EVIDENCE
            else SchedulingAction.QUEUE
        )
        return SchedulingDecision(
            job_id=request.job_id,
            pressure=pressure,
            action=action,
            reason="urgent resource pressure",
        )
