from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Protocol

from dusty_dragon.execution.aggregate_status import (
    FirmExecutionStatus,
    build_firm_execution_status,
    build_layer_execution_status,
)
from dusty_dragon.execution.status import DemoExecutionStatus
from dusty_dragon.execution.status_serialization import execution_status_to_dict


class DeskExecutionStatusProvider(Protocol):
    layer: int

    def snapshot(self) -> DemoExecutionStatus: ...


@dataclass(slots=True)
class FirmExecutionReadService:
    """Read-only firm status boundary shared by website and PC presentation layers."""

    providers: tuple[DeskExecutionStatusProvider, ...]

    def snapshot(self) -> FirmExecutionStatus:
        grouped: dict[int, list[DemoExecutionStatus]] = defaultdict(list)
        seen_desk_ids: set[str] = set()
        for provider in self.providers:
            if provider.layer < 0:
                raise ValueError("provider layer must be non-negative")
            status = provider.snapshot()
            if status.desk_id in seen_desk_ids:
                raise ValueError(f"duplicate desk status provider: {status.desk_id}")
            seen_desk_ids.add(status.desk_id)
            grouped[provider.layer].append(status)

        layers = tuple(
            build_layer_execution_status(layer, tuple(grouped[layer]))
            for layer in sorted(grouped)
        )
        return build_firm_execution_status(layers)

    def payload(self) -> dict[str, object]:
        return execution_status_to_dict(self.snapshot())
