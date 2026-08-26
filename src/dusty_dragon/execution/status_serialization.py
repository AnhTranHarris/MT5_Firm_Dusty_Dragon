from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from dusty_dragon.execution.aggregate_status import FirmExecutionStatus, LayerExecutionStatus
from dusty_dragon.execution.status import DemoExecutionStatus

ExecutionStatusModel = DemoExecutionStatus | LayerExecutionStatus | FirmExecutionStatus


def execution_status_to_dict(status: ExecutionStatusModel) -> dict[str, Any]:
    """Serialize an immutable execution read model without exposing runtime infrastructure."""

    value = _to_primitive(status)
    if not isinstance(value, dict):
        raise TypeError("execution status must serialize to a mapping")
    return value


def _to_primitive(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {key: _to_primitive(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _to_primitive(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_primitive(item) for item in value]
    return value
