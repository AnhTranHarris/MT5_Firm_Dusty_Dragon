from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import PurePosixPath


class DatasetStatus(StrEnum):
    BUILDING = "BUILDING"
    FROZEN = "FROZEN"
    SUPERSEDED = "SUPERSEDED"


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    dataset_id: str
    instrument_id: str
    timeframe: str
    uri: str
    sha256: str
    row_count: int
    start_utc: datetime
    end_utc: datetime
    status: DatasetStatus = DatasetStatus.FROZEN
    schema_version: str = "market_bar_v1"

    def __post_init__(self) -> None:
        if not self.dataset_id.strip():
            raise ValueError("dataset_id is required")
        if not self.instrument_id.strip():
            raise ValueError("instrument_id is required")
        if self.row_count <= 0:
            raise ValueError("row_count must be positive")
        if len(self.sha256) != 64 or any(char not in "0123456789abcdef" for char in self.sha256):
            raise ValueError("sha256 must be 64 lowercase hexadecimal characters")
        if not self.uri.startswith("dusty://market/"):
            raise ValueError("market datasets must use dusty://market/ URIs")
        if PurePosixPath(self.uri.removeprefix("dusty://market/")).is_absolute():
            raise ValueError("dataset URI must be relative to the Dusty market store")
        _require_utc(self.start_utc)
        _require_utc(self.end_utc)
        if self.end_utc <= self.start_utc:
            raise ValueError("dataset end must be after dataset start")

    @property
    def immutable(self) -> bool:
        return self.status is DatasetStatus.FROZEN


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("timestamps must be timezone-aware UTC")
