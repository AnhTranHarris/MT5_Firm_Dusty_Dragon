from pathlib import Path

import pytest

from dusty_dragon.storage.archive import ArchivePartition, HistoricalDataArchiver
from dusty_dragon.storage.google_drive_archive import GoogleDriveArchiveStore


class FakeDriveClient:
    def __init__(self, email: str = "forex.isekai@gmail.com") -> None:
        self.email = email
        self.folders: list[list[str]] = []
        self.uploads: list[tuple[Path, str, str]] = []

    def account_email(self) -> str:
        return self.email

    def ensure_folder_path(self, parts: list[str]) -> str:
        self.folders.append(parts)
        return "folder-123"

    def upload_file(self, local_file: Path, parent_folder_id: str, file_name: str) -> str:
        self.uploads.append((local_file, parent_folder_id, file_name))
        return "drive-file-456"


def test_archiver_stages_compressed_partition_with_checksum(tmp_path):
    archiver = HistoricalDataArchiver(tmp_path)
    partition = ArchivePartition(
        broker="boforex", symbol="EURUSD", timeframe="M15", year=2026, month=8
    )

    path, manifest = archiver.stage_jsonl_gz(
        [{"time": "2026-08-24T00:00:00Z", "close": 1.10}], partition
    )

    assert path.exists()
    assert manifest.record_count == 1
    assert manifest.compressed_bytes > 0
    assert len(manifest.sha256) == 64
    HistoricalDataArchiver.verify(path, manifest)


def test_drive_store_verifies_expected_account_and_uses_partition_path(tmp_path):
    archiver = HistoricalDataArchiver(tmp_path)
    partition = ArchivePartition(
        broker="boforex", symbol="USDJPY", timeframe="H1", year=2026, month=7
    )
    path, manifest = archiver.stage_jsonl_gz([{"close": 145.0}], partition)
    client = FakeDriveClient()
    store = GoogleDriveArchiveStore(client, expected_account_email="forex.isekai@gmail.com")

    remote = store.put(path, manifest)

    assert remote.remote_file_id == "drive-file-456"
    assert client.folders == [
        ["Dusty Dragon Firm Data", "historical", "boforex", "USDJPY", "H1", "2026", "07"]
    ]
    assert client.uploads[0][1] == "folder-123"


def test_drive_store_refuses_wrong_google_account(tmp_path):
    archiver = HistoricalDataArchiver(tmp_path)
    partition = ArchivePartition(
        broker="boforex", symbol="EURUSD", timeframe="M15", year=2026, month=8
    )
    path, manifest = archiver.stage_jsonl_gz([{"close": 1.10}], partition)
    store = GoogleDriveArchiveStore(
        FakeDriveClient("someone.else@example.com"),
        expected_account_email="forex.isekai@gmail.com",
    )

    with pytest.raises(PermissionError, match="account mismatch"):
        store.put(path, manifest)


def test_checksum_tampering_is_detected_before_upload(tmp_path):
    archiver = HistoricalDataArchiver(tmp_path)
    partition = ArchivePartition(
        broker="boforex", symbol="EURUSD", timeframe="M15", year=2026, month=8
    )
    path, manifest = archiver.stage_jsonl_gz([{"close": 1.10}], partition)
    path.write_bytes(path.read_bytes() + b"tamper")
    client = FakeDriveClient()
    store = GoogleDriveArchiveStore(client, expected_account_email="forex.isekai@gmail.com")

    with pytest.raises(ValueError, match="checksum mismatch"):
        store.put(path, manifest)
    assert client.uploads == []
