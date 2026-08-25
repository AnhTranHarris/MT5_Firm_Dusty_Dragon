from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from dusty_dragon.storage.archive import ArchiveManifest, ArchiveStore, HistoricalDataArchiver


class DriveArchiveClient(Protocol):
    """Small high-level boundary around a Google Drive implementation."""

    def account_email(self) -> str: ...

    def ensure_folder_path(self, parts: list[str]) -> str: ...

    def upload_file(self, local_file: Path, parent_folder_id: str, file_name: str) -> str: ...


@dataclass(frozen=True)
class GoogleDriveArchiveStore(ArchiveStore):
    client: DriveArchiveClient
    expected_account_email: str
    root_folder_name: str = "Dusty Dragon Firm Data"

    def put(self, local_file: Path, manifest: ArchiveManifest) -> ArchiveManifest:
        HistoricalDataArchiver.verify(local_file, manifest)
        actual_email = self.client.account_email().strip().lower()
        expected_email = self.expected_account_email.strip().lower()
        if actual_email != expected_email:
            raise PermissionError(
                f"Google Drive account mismatch: expected {expected_email}, got {actual_email}"
            )

        partition = manifest.partition
        folder_id = self.client.ensure_folder_path(
            [
                self.root_folder_name,
                "historical",
                partition.broker,
                partition.symbol,
                partition.timeframe,
                f"{partition.year:04d}",
                f"{partition.month:02d}",
            ]
        )
        remote_id = self.client.upload_file(local_file, folder_id, manifest.file_name)
        return manifest.model_copy(update={"remote_file_id": remote_id})


class GoogleApiDriveClient:
    """OAuth-backed Google Drive v3 client loaded only when archival is enabled.

    The Google credentials and token files are local runtime secrets and must
    never be committed. The first run launches Google's installed-app OAuth
    flow; later runs reuse the local refresh token.
    """

    def __init__(self, *, client_secrets_file: Path, token_file: Path) -> None:
        self.client_secrets_file = client_secrets_file
        self.token_file = token_file
        self._service = self._build_service()

    def _build_service(self):
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as exc:  # pragma: no cover - optional runtime dependency
            raise RuntimeError(
                "Google Drive archival requires the 'drive' optional dependencies"
            ) from exc

        scopes = ["https://www.googleapis.com/auth/drive.file"]
        credentials = None
        if self.token_file.exists():
            credentials = Credentials.from_authorized_user_file(str(self.token_file), scopes)
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        if not credentials or not credentials.valid:
            flow = InstalledAppFlow.from_client_secrets_file(str(self.client_secrets_file), scopes)
            credentials = flow.run_local_server(port=0)
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(credentials.to_json(), encoding="utf-8")
        return build("drive", "v3", credentials=credentials, cache_discovery=False)

    def account_email(self) -> str:
        result = self._service.about().get(fields="user(emailAddress)").execute()
        return str(result["user"]["emailAddress"])

    def ensure_folder_path(self, parts: list[str]) -> str:
        parent = "root"
        for name in parts:
            escaped = name.replace("'", "\\'")
            query = (
                "mimeType='application/vnd.google-apps.folder' "
                f"and name='{escaped}' and '{parent}' in parents and trashed=false"
            )
            files = self._service.files().list(q=query, fields="files(id,name)").execute()["files"]
            if files:
                parent = str(files[0]["id"])
                continue
            body = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent],
            }
            created = self._service.files().create(body=body, fields="id").execute()
            parent = str(created["id"])
        return parent

    def upload_file(self, local_file: Path, parent_folder_id: str, file_name: str) -> str:
        try:
            from googleapiclient.http import MediaFileUpload
        except ImportError as exc:  # pragma: no cover - optional runtime dependency
            raise RuntimeError(
                "Google Drive archival requires the 'drive' optional dependencies"
            ) from exc

        media = MediaFileUpload(str(local_file), mimetype="application/gzip", resumable=True)
        metadata = {"name": file_name, "parents": [parent_folder_id]}
        created = self._service.files().create(
            body=metadata,
            media_body=media,
            fields="id",
        ).execute()
        return str(created["id"])
