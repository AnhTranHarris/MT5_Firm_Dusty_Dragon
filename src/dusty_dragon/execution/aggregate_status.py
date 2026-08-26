from __future__ import annotations

from dataclasses import dataclass

from dusty_dragon.execution.status import DemoExecutionStatus


@dataclass(frozen=True, slots=True)
class LayerExecutionStatus:
    """Reporting-only aggregate; summed capital never implies transfer authority."""

    layer: int
    desks: tuple[DemoExecutionStatus, ...]
    desk_count: int
    ready_count: int
    faulted_count: int
    pending_execution_count: int
    total_balance: float
    total_equity: float
    total_free_margin: float
    execution_ready: bool


@dataclass(frozen=True, slots=True)
class FirmExecutionStatus:
    """Firm-wide reporting snapshot composed only from immutable layer snapshots."""

    layers: tuple[LayerExecutionStatus, ...]
    layer_count: int
    desk_count: int
    ready_count: int
    faulted_count: int
    pending_execution_count: int
    total_balance: float
    total_equity: float
    total_free_margin: float
    execution_ready: bool


def build_layer_execution_status(
    layer: int,
    desks: tuple[DemoExecutionStatus, ...],
) -> LayerExecutionStatus:
    if layer < 0:
        raise ValueError("layer must be non-negative")
    desk_count = len(desks)
    ready_count = sum(status.execution_ready for status in desks)
    faulted_count = sum(status.session_faulted for status in desks)
    pending_execution_count = sum(status.unresolved_execution_count for status in desks)
    return LayerExecutionStatus(
        layer=layer,
        desks=desks,
        desk_count=desk_count,
        ready_count=ready_count,
        faulted_count=faulted_count,
        pending_execution_count=pending_execution_count,
        total_balance=sum(status.balance for status in desks),
        total_equity=sum(status.equity for status in desks),
        total_free_margin=sum(status.free_margin for status in desks),
        execution_ready=desk_count > 0 and ready_count == desk_count,
    )


def build_firm_execution_status(
    layers: tuple[LayerExecutionStatus, ...],
) -> FirmExecutionStatus:
    desk_count = sum(layer.desk_count for layer in layers)
    ready_count = sum(layer.ready_count for layer in layers)
    faulted_count = sum(layer.faulted_count for layer in layers)
    pending_execution_count = sum(layer.pending_execution_count for layer in layers)
    return FirmExecutionStatus(
        layers=layers,
        layer_count=len(layers),
        desk_count=desk_count,
        ready_count=ready_count,
        faulted_count=faulted_count,
        pending_execution_count=pending_execution_count,
        total_balance=sum(layer.total_balance for layer in layers),
        total_equity=sum(layer.total_equity for layer in layers),
        total_free_margin=sum(layer.total_free_margin for layer in layers),
        execution_ready=bool(layers) and all(layer.execution_ready for layer in layers),
    )
