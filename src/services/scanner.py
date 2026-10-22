"""Data-to-Dirt Privacy-First Local File Scanner Service.

Enforces zero-trust filesystem access:
1. Blind initial state (no files in memory or descriptors open until explicit user permission).
2. Scoped directory traversal extracting filesystem metadata only (zero content read during scan).
3. Dark data heuristic classifier (stale >180d, heavy >500MB, duplicates, cache/artifacts).
4. Strict confidential file marking and exclusion guarantees.
5. PII text preview redaction and image thumbnail blurring.
6. Immediate memory wipe and revocation protocol.
"""

import os
import re
import time
import fnmatch
import hashlib
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Callable, Any

from src.analyzer.engine import AnalysisEngine
from src.fileclean_core.config import Config
from pathlib import Path

# Dark Data Heuristic Constants
STALE_THRESHOLD_SECONDS: float = 180.0 * 86400.0  # 180 days in seconds
HEAVY_FILE_THRESHOLD_BYTES: int = 500 * 1024 * 1024  # 500 MiB (524,288,000 bytes)

# Default patterns automatically classified as confidential / sensitive
DEFAULT_CONFIDENTIAL_PATTERNS: List[str] = [
    "*.env*",
    "*id_rsa*",
    "*id_ed25519*",
    "*.pem",
    "*.key",
    "*.pfx",
    "*.p12",
    "*.kdbx",
    "*password*",
    "*credential*",
    "*secret*",
    "*token*",
    ".git*",
    ".bash_history",
    ".zsh_history",
]

# Transient / Temp file patterns
TEMP_CACHE_PATTERNS: List[str] = [
    "*.tmp",
    "*.temp",
    "*.bak",
    "*.swp",
    "*.log",
    "*.cache",
    "*.pyc",
    "*.pyo",
    "Thumbs.db",
    ".DS_Store",
]

# MIME classification extensions
EXTENSION_MIME_MAP: Dict[str, str] = {
    # Video
    "mp4": "video", "mov": "video", "avi": "video", "mkv": "video",
    "wmv": "video", "flv": "video", "webm": "video", "m4v": "video",
    # Audio
    "mp3": "audio", "wav": "audio", "flac": "audio", "aac": "audio",
    "ogg": "audio", "m4a": "audio", "wma": "audio",
    # Image
    "png": "image", "jpg": "image", "jpeg": "image", "gif": "image",
    "webp": "image", "bmp": "image", "svg": "image", "tiff": "image", "raw": "image",
    # Archive
    "zip": "archive", "tar": "archive", "gz": "archive", "7z": "archive",
    "rar": "archive", "bz2": "archive", "xz": "archive", "dmg": "archive", "iso": "archive",
    # Document
    "pdf": "document", "doc": "document", "docx": "document", "ppt": "document",
    "pptx": "document", "xls": "document", "xlsx": "document", "txt": "document",
    "md": "document", "rtf": "document", "csv": "document", "json": "document",
    # Code
    "py": "code", "js": "code", "ts": "code", "html": "code", "css": "code",
    "c": "code", "cpp": "code", "h": "code", "hpp": "code", "rs": "code",
    "go": "code", "java": "code", "rb": "code", "sh": "code",
}


class ScanState(Enum):
    """Finite State Machine states for the privacy scanner."""
    BLIND = "BLIND"
    PROMPTING = "PROMPTING"
    ACCESS_ACTIVE_SCOPED = "ACCESS_ACTIVE_SCOPED"
    SCANNING = "SCANNING"
    COMPLETED = "COMPLETED"
    REVOKED = "REVOKED"
    ERROR = "ERROR"


class PermissionRequiredError(Exception):
    """Raised when an operation is attempted before explicit user permission is granted."""
    pass


class ConfidentialFileError(Exception):
    """Raised when an operation attempts to select, delete, or inspect a confidential file."""
    pass


@dataclass
class ScannedFileMetadata:
    """Metadata container for an enumerated filesystem asset.

    Zero file content is stored in this struct; strictly filesystem attributes.
    """
    file_id: str
    file_name: str
    absolute_path: str
    relative_path: str
    size_bytes: int
    extension: str
    mime_category: str
    last_modified_epoch_s: float
    last_accessed_epoch_s: float
    is_confidential: bool = False
    is_dark_data_candidate: bool = False
    dark_data_reason: str = ""
    preview_blurred: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to a serializable dictionary."""
        return {
            "file_id": self.file_id,
            "file_name": self.file_name,
            "absolute_path": self.absolute_path,
            "relative_path": self.relative_path,
            "size_bytes": self.size_bytes,
            "extension": self.extension,
            "mime_category": self.mime_category,
            "last_modified_epoch_s": self.last_modified_epoch_s,
            "last_accessed_epoch_s": self.last_accessed_epoch_s,
            "is_confidential": self.is_confidential,
            "is_dark_data_candidate": self.is_dark_data_candidate,
            "dark_data_reason": self.dark_data_reason,
            "preview_blurred": self.preview_blurred,
        }


# Compiled PII Regular Expressions for Previews
PII_EMAIL_REGEX = re.compile(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b")
PII_PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]+|\(?\d{2,4}\)?[-.\s]+)?\d{3,4}[-.\s]+\d{4}\b")
PII_CARD_REGEX = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
PII_SECRET_REGEX = re.compile(
    r"(?i)(api[_-]?key|secret|token|password|auth[_-]?token|bearer)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{6,})['\"]?"
)


def redact_text(text: str) -> str:
    """Scrub Personally Identifiable Information (PII) from raw text snippets."""
    if not text:
        return ""
    # Redact secret / API token values first
    scrubbed = PII_SECRET_REGEX.sub(r"\1=[REDACTED_SECRET]", text)
    # Redact credit card numbers
    scrubbed = PII_CARD_REGEX.sub("[REDACTED_CARD]", scrubbed)
    # Redact email addresses
    scrubbed = PII_EMAIL_REGEX.sub("[REDACTED_EMAIL]", scrubbed)
    # Redact phone numbers
    scrubbed = PII_PHONE_REGEX.sub("[REDACTED_PHONE]", scrubbed)
    return scrubbed


class FileScanner:
    """Zero-telemetry, privacy-first filesystem scanner engine."""

    def __init__(
        self,
        confidential_patterns: Optional[List[str]] = None,
        stale_threshold_days: float = 180.0,
        heavy_threshold_bytes: int = HEAVY_FILE_THRESHOLD_BYTES,
    ):
        self._state: ScanState = ScanState.BLIND
        self._active_path: Optional[str] = None
        self._session_only: bool = True
        self._cancel_requested: bool = False

        self._confidential_patterns = list(
            confidential_patterns or DEFAULT_CONFIDENTIAL_PATTERNS
        )
        self._stale_threshold_seconds = stale_threshold_days * 86400.0
        self._heavy_threshold_bytes = heavy_threshold_bytes

        # Internal metadata cache (file_id -> ScannedFileMetadata)
        self._scanned_files: List[ScannedFileMetadata] = []
        self._file_map: Dict[str, ScannedFileMetadata] = {}

        # Initialize AnalysisEngine
        self.config = Config()
        self.config.enable_ai = False  # Or True, depending on tests
        self.analysis_engine = AnalysisEngine(self.config)


    # -------------------------------------------------------------------------
    # State & Permission Lifecycle
    # -------------------------------------------------------------------------

    def get_state(self) -> ScanState:
        """Return the current scanner state machine status."""
        return self._state

    def is_access_granted(self) -> bool:
        """Check if user has explicitly granted active folder access."""
        return self._state in (
            ScanState.ACCESS_ACTIVE_SCOPED,
            ScanState.SCANNING,
            ScanState.COMPLETED,
        )

    def request_access(self, folder_path: str, session_only: bool = True) -> bool:
        """Prompt user and record explicit folder grant.

        Transitions state from BLIND -> ACCESS_ACTIVE_SCOPED.
        """
        if not folder_path or not str(folder_path).strip():
            raise ValueError("folder_path cannot be empty.")

        # Strip surrounding quotes and whitespace
        clean_path = str(folder_path).strip().strip("'\"")
        if not clean_path:
            raise ValueError("folder_path cannot be empty.")

        resolved = os.path.abspath(os.path.expanduser(clean_path))
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"Selected folder does not exist: {folder_path}")
        if not os.path.isdir(resolved):
            raise NotADirectoryError(f"Selected path is not a directory: {folder_path}")

        # Actively test directory readability to catch permission and macOS TCC restrictions early
        try:
            with os.scandir(resolved) as it:
                pass
        except PermissionError as err:
            raise PermissionError(
                f"Permission denied accessing '{resolved}'. "
                f"Please verify folder permissions or grant terminal/app access in "
                f"macOS System Settings -> Privacy & Security -> Files and Folders: {err}"
            ) from err
        except OSError as err:
            raise PermissionError(
                f"Cannot read directory '{resolved}': {err}"
            ) from err

        self._active_path = resolved
        self._session_only = session_only
        self._state = ScanState.ACCESS_ACTIVE_SCOPED
        self._cancel_requested = False
        return True

    def revoke_access(self) -> int:
        """Instant Revocation Protocol.

        Immediately closes directory handles, zeroes in-memory metadata,
        and reverts the scanner to the BLIND state.
        Returns the number of file metadata records wiped from memory.
        """
        self._cancel_requested = True
        purged_count = len(self._scanned_files)

        # Secure in-memory wipe
        self._scanned_files.clear()
        self._file_map.clear()
        self._active_path = None
        self._state = ScanState.REVOKED

        # Transition cleanly back to BLIND
        self._state = ScanState.BLIND
        return purged_count

    # -------------------------------------------------------------------------
    # Scoped Traversal & Metadata Extraction Engine
    # -------------------------------------------------------------------------

    def scan(
        self,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        reference_time: Optional[float] = None,
    ) -> List[ScannedFileMetadata]:
        """Perform recursive metadata traversal of the scoped directory.

        Invariants enforced:
        - Must be in ACCESS_ACTIVE_SCOPED or COMPLETED state.
        - Zero file content read into memory.
        - Automatic skip of .data_to_dirt_ignore directories.
        - Symlink loop protection (symlinks are not followed).
        - Catches PermissionError gracefully without crashing.
        """
        if not self.is_access_granted() or not self._active_path:
            raise PermissionRequiredError(
                "Cannot scan while in BLIND state. User must explicitly grant folder access."
            )

        self._state = ScanState.SCANNING
        self._cancel_requested = False
        self._scanned_files.clear()
        self._file_map.clear()

        now = reference_time if reference_time is not None else time.time()
        scanned_items: List[ScannedFileMetadata] = []
        files_by_size: Dict[int, List[ScannedFileMetadata]] = {}

        visited_dirs: Set[str] = set()

        try:
            def on_walk_error(err: OSError):
                # Detect permission and TCC denial on root or subdirectories
                if isinstance(err, PermissionError) or getattr(err, "errno", None) in (1, 13):
                    target_name = getattr(err, "filename", None) or self._active_path
                    raise PermissionError(
                        f"Permission denied during scan of '{target_name}'. "
                        f"Please check directory permissions or macOS TCC access: {err}"
                    ) from err
                raise err

            for root, dirs, files in os.walk(self._active_path, followlinks=False, onerror=on_walk_error):
                if self._cancel_requested:
                    break

                # Symlink and cycle prevention: resolve canonical path
                try:
                    real_root = os.path.realpath(root)
                    if real_root in visited_dirs:
                        dirs.clear()  # Stop descending duplicate or cyclic path
                        continue
                    visited_dirs.add(real_root)
                except OSError:
                    dirs.clear()
                    continue

                # Check for explicit ignore directory token (.data_to_dirt_ignore)
                if ".data_to_dirt_ignore" in files:
                    dirs.clear()  # Skip entire subtree
                    continue

                # Filter out ignored/hidden directories (e.g. .git, node_modules)
                filtered_dirs = []
                for d in dirs:
                    # Do not recurse into symlinked directories
                    full_dir = os.path.join(root, d)
                    if os.path.islink(full_dir):
                        continue
                    filtered_dirs.append(d)
                dirs[:] = filtered_dirs

                for fname in files:
                    if self._cancel_requested:
                        break

                    file_path = os.path.join(root, fname)

                    # Symlink protection on files: do not follow dangling or cyclic symlinks
                    if os.path.islink(file_path):
                        continue

                    try:
                        # Extract metadata strictly via stat - zero content reading
                        stat_res = os.stat(file_path)
                    except (PermissionError, FileNotFoundError, OSError):
                        # Gracefully skip unreadable files
                        continue

                    size = stat_res.st_size
                    mtime = stat_res.st_mtime
                    # Fallback atime to mtime if atime not maintained or 0
                    atime = stat_res.st_atime if stat_res.st_atime > 0 else mtime

                    rel_path = os.path.relpath(file_path, self._active_path)
                    ext = os.path.splitext(fname)[1].lstrip(".").lower()
                    mime_cat = EXTENSION_MIME_MAP.get(ext, "other")

                    # Deterministic file ID based on canonical attributes
                    id_seed = f"{rel_path}:{size}:{mtime}".encode("utf-8")
                    file_id = f"f_{hashlib.sha256(id_seed).hexdigest()[:16]}"

                    # Automatic Confidential Pattern Check
                    is_confidential = self._matches_confidential_pattern(fname, rel_path)

                    metadata = ScannedFileMetadata(
                        file_id=file_id,
                        file_name=fname,
                        absolute_path=file_path,
                        relative_path=rel_path,
                        size_bytes=size,
                        extension=ext,
                        mime_category=mime_cat,
                        last_modified_epoch_s=mtime,
                        last_accessed_epoch_s=atime,
                        is_confidential=is_confidential,
                        is_dark_data_candidate=False,
                        dark_data_reason="",
                        preview_blurred=True,
                    )

                    scanned_items.append(metadata)

                    # Group non-empty files by size for fast zero-IO duplicate detection
                    if size > 0:
                        files_by_size.setdefault(size, []).append(metadata)

                    if progress_callback and len(scanned_items) % 50 == 0:
                        progress_callback({
                            "files_scanned": len(scanned_items),
                            "current_file": fname,
                        })

            # Apply Dark Data Heuristics across all collected metadata
            self._apply_dark_data_heuristics(scanned_items, files_by_size, now)

            # Store in scanner instance
            self._scanned_files = scanned_items
            self._file_map = {item.file_id: item for item in scanned_items}
            self._state = ScanState.COMPLETED
            return list(self._scanned_files)

        except Exception as exc:
            self._state = ScanState.ERROR
            self._scanned_files.clear()
            self._file_map.clear()
            raise exc

    # -------------------------------------------------------------------------
    # Dark Data Heuristic Engine
    # -------------------------------------------------------------------------

    def _matches_confidential_pattern(self, file_name: str, rel_path: str) -> bool:
        """Check if a filename or path matches confidential filters."""
        # Hidden files starting with '.'
        if file_name.startswith("."):
            return True
        for pat in self._confidential_patterns:
            if fnmatch.fnmatch(file_name.lower(), pat.lower()):
                return True
            if fnmatch.fnmatch(rel_path.lower(), pat.lower()):
                return True
        return False

    def _apply_dark_data_heuristics(
        self,
        items: List[ScannedFileMetadata],
        files_by_size: Dict[int, List[ScannedFileMetadata]],
        current_time: float,
    ) -> None:
        """Classify files using both basic rules and advanced AnalysisEngine."""
        
        # 1. Base heuristics (ensures tests and core functionality always work)
        for item in items:
            reasons: List[str] = []
            
            # Stale Relic Heuristic
            effective_timestamp = max(item.last_modified_epoch_s, item.last_accessed_epoch_s)
            age_seconds = current_time - effective_timestamp
            if age_seconds > self._stale_threshold_seconds:
                days = int(age_seconds / 86400.0)
                reasons.append(f"Stale relic (age: {days} days > 180d)")
                
            # Heavy Media Bloat
            if item.size_bytes >= self._heavy_threshold_bytes:
                mb_size = round(item.size_bytes / (1024.0 * 1024.0), 1)
                reasons.append(f"Heavy file bloat ({mb_size} MB >= 500 MB)")
                
            # Transient Trash / Temp Artifacts
            for pat in TEMP_CACHE_PATTERNS:
                if fnmatch.fnmatch(item.file_name.lower(), pat.lower()):
                    reasons.append("Temporary cache/artifact")
                    break
                    
            # Duplicate Heuristic (identical size with another file)
            if item.size_bytes > 0 and len(files_by_size.get(item.size_bytes, [])) > 1:
                duplicate_count = len(files_by_size[item.size_bytes])
                reasons.append(f"Potential duplicate ({duplicate_count} files match {item.size_bytes} bytes)")
                
            if reasons:
                item.is_dark_data_candidate = True
                item.dark_data_reason = " | ".join(reasons)

        # 2. Advanced AnalysisEngine heuristics
        if not self._active_path:
            return
            
        try:
            scan_result = self.analysis_engine.scan(Path(self._active_path))
            
            issues_by_path = {}
            for issue in scan_result.issues:
                path_str = str(issue.path)
                if path_str not in issues_by_path:
                    issues_by_path[path_str] = []
                issues_by_path[path_str].append(issue)
                
            for item in items:
                path_str = item.absolute_path
                if path_str in issues_by_path:
                    issues = issues_by_path[path_str]
                    
                    reasons = []
                    # Keep existing reasons
                    if item.dark_data_reason:
                        reasons.append(item.dark_data_reason)
                        
                    for issue in issues:
                        reason = f"🤖 [AI] {issue.category.value.title()}: {issue.reason}"
                        if issue.confidence.value != "low":
                            reason += f" [{issue.confidence.value.upper()} conf]"
                        if issue.ai_explanation:
                            reason += f" - AI says: {issue.ai_explanation}"
                        reasons.append(reason)
                        
                    if reasons:
                        item.is_dark_data_candidate = True
                        item.dark_data_reason = " | ".join(reasons)
                        
        except Exception as e:
            print(f"AnalysisEngine failed, using basic rules only: {e}")

    # -------------------------------------------------------------------------
    # Confidential File Guarantees & Operations
    # -------------------------------------------------------------------------

    def mark_confidential(self, file_id: str, is_confidential: bool = True) -> bool:
        """Explicitly tag a file as confidential.

        Guarantees:
        - File is excluded from deletion candidates.
        - Deletion and inspection operations are strictly blocked.
        """
        item = self._file_map.get(file_id)
        if not item:
            raise KeyError(f"File ID not found: {file_id}")

        item.is_confidential = is_confidential
        return True

    def get_scanned_files(self) -> List[ScannedFileMetadata]:
        """Return shallow copy of all currently scanned files."""
        return list(self._scanned_files)

    def get_deletion_candidates(self) -> List[ScannedFileMetadata]:
        """Return dark data candidates eligible for deletion.

        Confidential files are STRICTLY filtered out.
        """
        return [
            item
            for item in self._scanned_files
            if item.is_dark_data_candidate and not item.is_confidential
        ]

    def assert_can_operate(self, file_id: str) -> ScannedFileMetadata:
        """Verify that a file exists and is NOT marked confidential.

        Raises ConfidentialFileError if marked confidential.
        """
        item = self._file_map.get(file_id)
        if not item:
            raise KeyError(f"File ID not found: {file_id}")
        if item.is_confidential:
            raise ConfidentialFileError(
                f"Operation forbidden: file '{item.file_name}' (ID: {file_id}) is marked CONFIDENTIAL."
            )
        return item

    # -------------------------------------------------------------------------
    # Preview Redaction & Blurring
    # -------------------------------------------------------------------------

    def set_preview_blurred(self, file_id: str, blurred: bool) -> bool:
        """Toggle preview blurring/pixelation preference for a file."""
        item = self.assert_can_operate(file_id)
        item.preview_blurred = blurred
        return True

    def is_preview_blurred(self, file_id: str) -> bool:
        """Check if preview is currently blurred."""
        item = self.assert_can_operate(file_id)
        return item.preview_blurred

    def get_safe_preview_text(self, file_id: str, max_chars: int = 500) -> str:
        """Generate a privacy-scrubbed preview of a text or document file.

        Enforces:
        - Raises ConfidentialFileError if marked confidential.
        - Reads only up to max_chars.
        - Applies deterministic PII regex redaction.
        """
        item = self.assert_can_operate(file_id)

        if not os.path.exists(item.absolute_path):
            raise FileNotFoundError(f"File path does not exist: {item.absolute_path}")

        try:
            with open(item.absolute_path, "r", encoding="utf-8", errors="replace") as f:
                raw_snippet = f.read(max_chars)
            return redact_text(raw_snippet)
        except Exception as exc:
            return f"[Preview error: {str(exc)}]"

    def get_preview_metadata(self, file_id: str) -> Dict[str, Any]:
        """Generate safe UI preview instructions without transmitting private media."""
        item = self.assert_can_operate(file_id)
        return {
            "file_id": item.file_id,
            "file_name": item.file_name,
            "mime_category": item.mime_category,
            "size_bytes": item.size_bytes,
            "preview_blurred": item.preview_blurred,
            "blur_filter": "blur(12px)" if item.preview_blurred else "none",
            "pixelation_blocks": 16 if item.preview_blurred else 1,
        }
