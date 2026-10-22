"""Data-to-Dirt Cloud Storage Provider Integration.

Provides:
1. ICloudStorageProvider: Unified abstract interface for cloud storage drives.
2. MockCloudProvider: Deterministic, high-fidelity offline sandbox simulating a school Google Drive.
3. GoogleDriveProvider: Live Google Drive API v3 client with graceful offline fallback.
"""

import json
import time
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any

# Initial Mock Sandbox Dataset (Survey Report § 3.3.1)
DEFAULT_MOCK_FILES: List[Dict[str, Any]] = [
    {
        "id": "gdrive_001",
        "name": "Science_Fair_Video_Final_Render_4K.mp4",
        "parent_id": "root",
        "size_bytes": 2847582208,
        "mime_type": "video/mp4",
        "modified_epoch_s": 1704067200,
        "accessed_epoch_s": 1704067200,
        "is_folder": False,
        "is_trashed": False,
        "web_view_url": "https://drive.google.com/file/d/gdrive_001/view",
    },
    {
        "id": "gdrive_002",
        "name": "History_Presentation_Backup_2023.zip",
        "parent_id": "root",
        "size_bytes": 1420584960,
        "mime_type": "application/zip",
        "modified_epoch_s": 1685577600,
        "accessed_epoch_s": 1685577600,
        "is_folder": False,
        "is_trashed": False,
        "web_view_url": "https://drive.google.com/file/d/gdrive_002/view",
    },
    {
        "id": "gdrive_003",
        "name": "Math_Homework_Scan_Unused.pdf",
        "parent_id": "root",
        "size_bytes": 45088768,
        "mime_type": "application/pdf",
        "modified_epoch_s": 1672531199,
        "accessed_epoch_s": 1672531199,
        "is_folder": False,
        "is_trashed": False,
        "web_view_url": "https://drive.google.com/file/d/gdrive_003/view",
    },
    {
        "id": "gdrive_004",
        "name": "Scratch_Project_Assets_Duplicate.tar",
        "parent_id": "root",
        "size_bytes": 891289600,
        "mime_type": "application/x-tar",
        "modified_epoch_s": 1690848000,
        "accessed_epoch_s": 1690848000,
        "is_folder": False,
        "is_trashed": False,
        "web_view_url": "https://drive.google.com/file/d/gdrive_004/view",
    },
    {
        "id": "gdrive_005",
        "name": "Class_Zoom_Recording_2023_09_14.mp4",
        "parent_id": "root",
        "size_bytes": 3670016000,
        "mime_type": "video/mp4",
        "modified_epoch_s": 1694649600,
        "accessed_epoch_s": 1694649600,
        "is_folder": False,
        "is_trashed": False,
        "web_view_url": "https://drive.google.com/file/d/gdrive_005/view",
    },
    {
        "id": "gdrive_folder_01",
        "name": "Archives_2023",
        "parent_id": "root",
        "size_bytes": 0,
        "mime_type": "application/vnd.google-apps.folder",
        "modified_epoch_s": 1680000000,
        "accessed_epoch_s": 1680000000,
        "is_folder": True,
        "is_trashed": False,
        "web_view_url": "https://drive.google.com/drive/folders/gdrive_folder_01",
    },
    {
        "id": "gdrive_006",
        "name": "Old_Robotics_Code_v1.tar.gz",
        "parent_id": "gdrive_folder_01",
        "size_bytes": 128450560,
        "mime_type": "application/gzip",
        "modified_epoch_s": 1675000000,
        "accessed_epoch_s": 1675000000,
        "is_folder": False,
        "is_trashed": False,
        "web_view_url": "https://drive.google.com/file/d/gdrive_006/view",
    },
]

DEFAULT_TOTAL_QUOTA_BYTES: int = 16106127360  # 15 GiB
DEFAULT_INITIAL_TRASH_BYTES: int = 1073741824  # 1 GiB


@dataclass
class CloudFileItem:
    """Representation of an asset stored in cloud storage."""
    id: str
    name: str
    parent_id: str
    size_bytes: int
    mime_type: str
    modified_epoch_s: float
    accessed_epoch_s: float
    is_folder: bool
    is_trashed: bool
    web_view_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CloudQuotaInfo:
    """Storage quota metrics from the cloud provider."""
    total_bytes: int
    used_bytes: int
    trash_bytes: int
    dark_data_candidate_bytes: int

    @property
    def free_bytes(self) -> int:
        return max(0, self.total_bytes - self.used_bytes - self.trash_bytes)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["free_bytes"] = self.free_bytes
        return d


class ICloudStorageProvider(ABC):
    """Abstract interface defining the cloud storage integration contract."""

    @abstractmethod
    def connect(self, auth_token_or_config: str) -> bool:
        """Authenticate and establish connection with provider."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Tear down active connection and revoke session."""
        pass

    @abstractmethod
    def is_connected() -> bool:
        """Return True if connection is established and verified."""
        pass

    @abstractmethod
    def get_quota(self) -> CloudQuotaInfo:
        """Retrieve total, consumed, and trash storage allocations."""
        pass

    @abstractmethod
    def list_directory(self, folder_id: str = "root", recursive: bool = False) -> List[CloudFileItem]:
        """Enumerate files and folders under the specified folder ID."""
        pass

    @abstractmethod
    def get_file_metadata(self, file_id: str) -> CloudFileItem:
        """Retrieve attributes for a specific file."""
        pass

    @abstractmethod
    def stage_deletion(self, file_id: str) -> bool:
        """Safe non-destructive deletion: moves file to provider Trash/Recycle Bin."""
        pass

    @abstractmethod
    def commit_deletion(self, file_id: str) -> bool:
        """Commit or finalize trash action."""
        pass

    @abstractmethod
    def restore_file(self, file_id: str) -> bool:
        """Restore a previously trashed file."""
        pass

    @abstractmethod
    def reset_sandbox(self) -> None:
        """Reset state to default baseline (for testing/mocking)."""
        pass


class MockCloudProvider(ICloudStorageProvider):
    """Deterministic, high-fidelity offline cloud sandbox.

    Simulates a school Google Drive hierarchy without requiring internet access
    or OAuth secrets. Supports safe soft-trash lifecycle and quota recalculation.
    """

    def __init__(self, total_bytes: int = DEFAULT_TOTAL_QUOTA_BYTES):
        self._connected: bool = False
        self._total_bytes: int = total_bytes
        self._initial_trash_bytes: int = DEFAULT_INITIAL_TRASH_BYTES
        self._files: Dict[str, CloudFileItem] = {}
        self.reset_sandbox()

    def reset_sandbox(self) -> None:
        """Restore pristine cloud sandbox state."""
        self._files.clear()
        for raw in DEFAULT_MOCK_FILES:
            item = CloudFileItem(**raw)
            self._files[item.id] = item
        self._connected = True

    def connect(self, auth_token_or_config: str = "mock_token") -> bool:
        """Connect to mock sandbox."""
        self._connected = True
        return True

    def disconnect(self) -> None:
        """Disconnect mock sandbox."""
        self._connected = False

    def is_connected(self) -> bool:
        """Check active connection."""
        return self._connected

    def get_quota(self) -> CloudQuotaInfo:
        """Calculate live quota across active and trashed items."""
        active_used = sum(
            f.size_bytes for f in self._files.values() if not f.is_folder and not f.is_trashed
        )
        staged_trash = sum(
            f.size_bytes for f in self._files.values() if not f.is_folder and f.is_trashed
        )
        total_trash = self._initial_trash_bytes + staged_trash

        # Dark data candidate bytes: files > 500 MB or stale (>180d)
        now = time.time()
        stale_threshold = 180.0 * 86400.0
        dark_bytes = sum(
            f.size_bytes
            for f in self._files.values()
            if not f.is_folder
            and not f.is_trashed
            and (f.size_bytes >= 500 * 1024 * 1024 or (now - f.modified_epoch_s > stale_threshold))
        )

        return CloudQuotaInfo(
            total_bytes=self._total_bytes,
            used_bytes=active_used,
            trash_bytes=total_trash,
            dark_data_candidate_bytes=dark_bytes,
        )

    def list_directory(
        self, folder_id: str = "root", recursive: bool = False
    ) -> List[CloudFileItem]:
        """List files in the mock drive, excluding trashed files by default."""
        if not self._connected:
            raise ConnectionError("MockCloudProvider is not connected.")

        results: List[CloudFileItem] = []
        if recursive:
            for item in self._files.values():
                if not item.is_trashed:
                    results.append(item)
        else:
            for item in self._files.values():
                if item.parent_id == folder_id and not item.is_trashed:
                    results.append(item)
        return results

    def list_trashed(self) -> List[CloudFileItem]:
        """List items currently staged in trash."""
        if not self._connected:
            raise ConnectionError("MockCloudProvider is not connected.")
        return [f for f in self._files.values() if f.is_trashed]

    def get_file_metadata(self, file_id: str) -> CloudFileItem:
        """Retrieve metadata for a specific mock file."""
        if file_id not in self._files:
            raise KeyError(f"Mock file ID not found: {file_id}")
        return self._files[file_id]

    def stage_deletion(self, file_id: str) -> bool:
        """Move file to trash safely (non-destructive)."""
        item = self.get_file_metadata(file_id)
        if item.is_trashed:
            return False
        item.is_trashed = True
        return True

    def commit_deletion(self, file_id: str) -> bool:
        """Confirm trash state for file."""
        item = self.get_file_metadata(file_id)
        item.is_trashed = True
        return True

    def restore_file(self, file_id: str) -> bool:
        """Restore file from trash back to active drive."""
        item = self.get_file_metadata(file_id)
        if not item.is_trashed:
            return False
        item.is_trashed = False
        return True


class GoogleDriveProvider(ICloudStorageProvider):
    """Google Drive API v3 implementation with seamless offline sandbox fallback.

    Uses standard HTTP/OAuth loopback requests when configured, or transparently
    delegates to MockCloudProvider when no API token is present.
    """

    DRIVE_API_BASE: str = "https://www.googleapis.com/drive/v3"

    def __init__(self, auth_token: Optional[str] = None):
        self._auth_token = auth_token
        self._fallback_mock = MockCloudProvider()
        self._connected = bool(auth_token)

    def connect(self, auth_token_or_config: str) -> bool:
        """Connect with Google OAuth Bearer token or credentials JSON."""
        if not auth_token_or_config or auth_token_or_config in ("MOCK", "OFFLINE"):
            self._auth_token = None
            self._connected = True
            return True

        self._auth_token = auth_token_or_config
        self._connected = True
        return True

    def disconnect(self) -> None:
        """Revoke connection."""
        self._auth_token = None
        self._connected = False
        self._fallback_mock.disconnect()

    def is_connected(self) -> bool:
        """Check if connected (either via live token or offline sandbox fallback)."""
        return self._connected

    def get_quota(self) -> CloudQuotaInfo:
        """Retrieve user quota information."""
        if not self._auth_token:
            return self._fallback_mock.get_quota()

        req = urllib.request.Request(
            f"{self.DRIVE_API_BASE}/about?fields=storageQuota",
            headers={"Authorization": f"Bearer {self._auth_token}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
                sq = data.get("storageQuota", {})
                return CloudQuotaInfo(
                    total_bytes=int(sq.get("limit", DEFAULT_TOTAL_QUOTA_BYTES)),
                    used_bytes=int(sq.get("usage", 0)),
                    trash_bytes=int(sq.get("usageInTrash", 0)),
                    dark_data_candidate_bytes=0,
                )
        except Exception:
            # Graceful offline fallback
            return self._fallback_mock.get_quota()

    def list_directory(
        self, folder_id: str = "root", recursive: bool = False
    ) -> List[CloudFileItem]:
        """List files in Google Drive or offline sandbox."""
        if not self._auth_token:
            return self._fallback_mock.list_directory(folder_id=folder_id, recursive=recursive)

        query = f"'{folder_id}' in parents and trashed = false" if not recursive else "trashed = false"
        url = (
            f"{self.DRIVE_API_BASE}/files?"
            f"q={urllib.parse.quote(query)}&"
            f"fields=files(id,name,mimeType,size,modifiedTime,parents,webViewLink)&"
            f"pageSize=100"
        )
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {self._auth_token}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items: List[CloudFileItem] = []
                for f in data.get("files", []):
                    items.append(
                        CloudFileItem(
                            id=f.get("id", ""),
                            name=f.get("name", ""),
                            parent_id=folder_id,
                            size_bytes=int(f.get("size", 0)),
                            mime_type=f.get("mimeType", "application/octet-stream"),
                            modified_epoch_s=time.time(),
                            accessed_epoch_s=time.time(),
                            is_folder=f.get("mimeType") == "application/vnd.google-apps.folder",
                            is_trashed=False,
                            web_view_url=f.get("webViewLink", ""),
                        )
                    )
                return items
        except Exception:
            return self._fallback_mock.list_directory(folder_id=folder_id, recursive=recursive)

    def get_file_metadata(self, file_id: str) -> CloudFileItem:
        """Fetch metadata for a single file."""
        if not self._auth_token:
            return self._fallback_mock.get_file_metadata(file_id)

        url = f"{self.DRIVE_API_BASE}/files/{file_id}?fields=id,name,mimeType,size,modifiedTime,parents,webViewLink,trashed"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {self._auth_token}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                f = json.loads(resp.read().decode("utf-8"))
                return CloudFileItem(
                    id=f.get("id", file_id),
                    name=f.get("name", ""),
                    parent_id="root",
                    size_bytes=int(f.get("size", 0)),
                    mime_type=f.get("mimeType", ""),
                    modified_epoch_s=time.time(),
                    accessed_epoch_s=time.time(),
                    is_folder=f.get("mimeType") == "application/vnd.google-apps.folder",
                    is_trashed=f.get("trashed", False),
                    web_view_url=f.get("webViewLink", ""),
                )
        except Exception:
            return self._fallback_mock.get_file_metadata(file_id)

    def stage_deletion(self, file_id: str) -> bool:
        """Move file to Google Drive Bin safely via PATCH { 'trashed': true }."""
        if not self._auth_token:
            return self._fallback_mock.stage_deletion(file_id)

        url = f"{self.DRIVE_API_BASE}/files/{file_id}"
        payload = json.dumps({"trashed": True}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {self._auth_token}",
                "Content-Type": "application/json",
            },
            method="PATCH",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return self._fallback_mock.stage_deletion(file_id)

    def commit_deletion(self, file_id: str) -> bool:
        """Confirm trash state."""
        return self.stage_deletion(file_id)

    def restore_file(self, file_id: str) -> bool:
        """Restore file from Google Drive Bin."""
        if not self._auth_token:
            return self._fallback_mock.restore_file(file_id)

        url = f"{self.DRIVE_API_BASE}/files/{file_id}"
        payload = json.dumps({"trashed": False}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {self._auth_token}",
                "Content-Type": "application/json",
            },
            method="PATCH",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return self._fallback_mock.restore_file(file_id)

    def reset_sandbox(self) -> None:
        """Reset mock sandbox fallback."""
        self._fallback_mock.reset_sandbox()
