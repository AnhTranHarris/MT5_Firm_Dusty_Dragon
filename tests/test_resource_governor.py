import pytest

from dusty_dragon.scheduler.resource_governor import (
    ResourceClass,
    ResourceGovernor,
    ResourcePolicy,
    ResourcePressure,
    ResourceSnapshot,
    SchedulingAction,
    WorkRequest,
    WorkTier,
)


def test_resource_snapshot_rejects_invalid_fraction() -> None:
    with pytest.raises(ValueError):
        ResourceSnapshot(cpu_fraction=1.01, memory_fraction=0.5, disk_io_fraction=0.5)


def test_policy_requires_ordered_thresholds() -> None:
    with pytest.raises(ValueError):
        ResourcePolicy(elevated_threshold=0.90, urgent_threshold=0.80)


def test_protected_workloads_run_under_urgent_pressure() -> None:
    governor = ResourceGovernor()
    snapshot = ResourceSnapshot(cpu_fraction=0.95, memory_fraction=0.40, disk_io_fraction=0.30)

    for tier in (WorkTier.SAFETY, WorkTier.TRADING):
        decision = governor.decide(
            WorkRequest(job_id=f"job-{tier.name}", tier=tier, resource_class=ResourceClass.LIGHT),
            snapshot,
        )
        assert decision.pressure is ResourcePressure.URGENT
        assert decision.action is SchedulingAction.RUN


def test_research_queues_under_elevated_pressure() -> None:
    governor = ResourceGovernor()
    snapshot = ResourceSnapshot(cpu_fraction=0.80, memory_fraction=0.40, disk_io_fraction=0.30)
    request = WorkRequest(
        job_id="research-1",
        tier=WorkTier.RESEARCH,
        resource_class=ResourceClass.HEAVY,
    )

    decision = governor.decide(request, snapshot)

    assert decision.pressure is ResourcePressure.ELEVATED
    assert decision.action is SchedulingAction.QUEUE


def test_validation_throttles_under_elevated_and_queues_under_urgent() -> None:
    governor = ResourceGovernor()
    request = WorkRequest(
        job_id="validation-1",
        tier=WorkTier.VALIDATION,
        resource_class=ResourceClass.MODERATE,
    )

    elevated = governor.decide(
        request,
        ResourceSnapshot(cpu_fraction=0.76, memory_fraction=0.20, disk_io_fraction=0.20),
    )
    urgent = governor.decide(
        request,
        ResourceSnapshot(cpu_fraction=0.91, memory_fraction=0.20, disk_io_fraction=0.20),
    )

    assert elevated.action is SchedulingAction.THROTTLE
    assert urgent.action is SchedulingAction.QUEUE


def test_evidence_is_preserved_under_urgent_pressure() -> None:
    governor = ResourceGovernor()
    request = WorkRequest(
        job_id="audit-1",
        tier=WorkTier.EVIDENCE,
        resource_class=ResourceClass.LIGHT,
    )
    snapshot = ResourceSnapshot(cpu_fraction=0.95, memory_fraction=0.95, disk_io_fraction=0.95)

    decision = governor.decide(request, snapshot)

    assert decision.action is SchedulingAction.THROTTLE


def test_accelerator_required_work_fails_closed_without_accelerator() -> None:
    governor = ResourceGovernor()
    request = WorkRequest(
        job_id="gpu-1",
        tier=WorkTier.RESEARCH,
        resource_class=ResourceClass.ACCELERATOR_REQUIRED,
    )
    snapshot = ResourceSnapshot(cpu_fraction=0.10, memory_fraction=0.10, disk_io_fraction=0.10)

    decision = governor.decide(request, snapshot)

    assert decision.action is SchedulingAction.REJECT_UNSUPPORTED
