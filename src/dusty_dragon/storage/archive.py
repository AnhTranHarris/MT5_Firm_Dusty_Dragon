from __future__ import annotations

import gzip
import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field


class ArchivePartition(BaseModel):
    """Stable logical partition for large historical datasets."""

    broker: str
    symbol: str
    timeframe: str
    year: int = Field(ge=1970)
    month: int = Field(ge=1, le=12)

    @property
    def relative_path(self) -> str:
        return f"{self.broker}/{self.symbol}/{self.timeframe}/{self.year:04d}/{self.month:02d}"


class ArchiveManifest(BaseModel):
    archive_id: str
    partition: ArchivePartition
    file_name: str
    record_count: int = Field(ge=0)
    compressed_bytes: int = Field(ge=0)
    sha256: str
    created_at: datetime
    format: str = "jsonl.gz"
    remote_file_id: str | None = None


class ArchiveStore(Protocol):
    def put(self, local_file: Path, manifest: ArchiveManifest) -> ArchiveManifest: ...


@dataclass(frozen=True)
class HistoricalDataArchiver:
    """Stage compact immutable chunks before remote archival.

    Git stores only code. Large market-history chunks are compressed locally,
    checksummed, and handed to an ArchiveStore such as Google Drive.
    """

    staging_root: Path

    def stage_jsonl_gz(
        self,
        records: Iterable[dict[str, Any]],
        partition: ArchivePartition,
    ) -> tuple[Path, ArchiveManifest]:
        created_at = datetime.now(UTC)
        directory = self.staging_root / partition.relative_path
        directory.mkdir(parents=True, exist_ok=True)
        timestamp = created_at.strftime("%Y%m%dT%H%M%SZ")
        file_name = f"history-{timestamp}.jsonl.gz"
        path = directory / file_name

        count = 0
        with gzip.open(path, "wt", encoding="utf-8", newline="\n") as handle:
            for record in records:
                handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
                handle.write("\n")
                count += 1

        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        archive_id = hashlib.sha256(
            f"{partition.relative_path}:{file_name}:{digest}".encode()
        ).hexdigest()[:24]
        manifest = ArchiveManifest(
            archive_id=archive_id,
            partition=partition,
            file_name=file_name,
            record_count=count,
            compressed_bytes=path.stat().st_size,
            sha256=digest,
            created_at=created_at,
        )
        return path, manifest

    @staticmethod
    def verify(path: Path, manifest: ArchiveManifest) -> None:
        if not path.is_file():
            raise FileNotFoundError(path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != manifest.sha256:
            raise ValueError("archive checksum mismatch")
        if path.stat().st_size != manifest.compressed_bytes:
            raise ValueError("archive size mismatch")
