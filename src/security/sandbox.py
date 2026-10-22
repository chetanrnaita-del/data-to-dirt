"""Strict Context Isolation & Path Sandboxing for FileClean.

Since FileClean is a Python desktop app (not Electron/Tauri), traditional CSP
doesn't apply. Instead, this module enforces equivalent security boundaries:

1. PATH SANDBOXING — Restricts all file operations to user-approved directories,
   preventing path traversal, symlink escapes, and access to system-critical paths.

2. OPERATION GUARDS — Wraps all destructive operations (delete, trash, move) with
   mandatory validation and audit logging.

3. PERMISSION BOUNDARIES — Separates UI context from system operations. The UI
   layer can only request operations through the sandbox; it cannot directly
   access the filesystem for destructive actions.

4. AI MODEL ISOLATION — Ensures AI inference runs in a restricted context with
   no access to file contents beyond what's explicitly permitted.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable

from src.fileclean_core.platform import get_system_dirs, get_os

logger = logging.getLogger("fileclean.security")


class OperationType(str, Enum):
    """Types of file operations the sandbox tracks."""
    READ = "read"
    SCAN = "scan"
    TRASH = "trash"
    DELETE = "delete"
    HASH = "hash"
    AI_READ = "ai_read"  # AI reading file snippets


class AccessDecision(str, Enum):
    """Result of a sandbox access check."""
    ALLOWED = "allowed"
    DENIED_SYSTEM_DIR = "denied_system_dir"
    DENIED_OUTSIDE_SCOPE = "denied_outside_scope"
    DENIED_SYMLINK_ESCAPE = "denied_symlink_escape"
    DENIED_PATH_TRAVERSAL = "denied_path_traversal"
    DENIED_RATE_LIMITED = "denied_rate_limited"
    DENIED_BLOCKLISTED = "denied_blocklisted"


@dataclass
class AccessAuditEntry:
    """Audit log entry for a file access attempt."""
    timestamp: str
    operation: OperationType
    path: str
    decision: AccessDecision
    reason: str


@dataclass
class SandboxConfig:
    """Configuration for the security sandbox.

    Attributes:
        allowed_roots: Directories the user has approved for scanning.
        max_delete_per_session: Maximum files that can be deleted in one session.
        max_delete_size_bytes: Maximum total bytes that can be deleted in one session.
        require_confirmation_above_mb: Files larger than this require extra confirmation.
        ai_content_max_bytes: Maximum bytes AI can read from a single file.
        ai_allowed_extensions: File extensions AI is allowed to read content from.
        enable_symlink_following: Whether to follow symlinks (False = safer).
        enable_audit_logging: Whether to log all access attempts.
    """
    allowed_roots: list[Path] = field(default_factory=list)
    max_delete_per_session: int = 500
    max_delete_size_bytes: int = 10 * 1024 * 1024 * 1024  # 10 GB
    require_confirmation_above_mb: int = 500
    ai_content_max_bytes: int = 512
    ai_allowed_extensions: list[str] = field(default_factory=lambda: [
        ".txt", ".md", ".json", ".csv", ".xml", ".yaml", ".yml",
        ".log", ".ini", ".cfg", ".conf", ".toml",
        ".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".go", ".rs",
        ".html", ".css", ".scss", ".sh", ".bash",
    ])
    enable_symlink_following: bool = False
    enable_audit_logging: bool = True


class PathSandbox:
    """Enforces strict path-based security boundaries for all file operations.

    All file access in FileClean must go through this sandbox. It ensures:
    - No access to system-critical directories
    - No path traversal attacks (../../etc/passwd)
    - No symlink escapes to restricted areas
    - Rate limiting on destructive operations
    - Full audit logging of all access decisions
    """

    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()
        self._system_dirs = [d.resolve() for d in get_system_dirs()]
        self._audit_log: list[AccessAuditEntry] = []
        self._session_delete_count = 0
        self._session_delete_bytes = 0
        self._blocklisted_paths: set[str] = set()

        # Additional hardcoded protected paths
        home = Path.home()
        self._protected_paths = [
            home / ".ssh",
            home / ".gnupg",
            home / ".aws",
            home / ".config" / "gcloud",
            home / ".kube",
            home / ".gitconfig",
            home / ".env",
            home / ".bashrc",
            home / ".zshrc",
            home / ".profile",
        ]

    def authorize_scan_root(self, path: Path) -> None:
        """Explicitly authorize a directory as a scan root.

        Called when the user selects a directory via the UI.
        """
        resolved = path.resolve()
        if not self._is_system_path(resolved):
            self.config.allowed_roots.append(resolved)
            logger.info(f"Authorized scan root: {resolved}")

    def check_access(self, path: Path, operation: OperationType) -> tuple[AccessDecision, str]:
        """Check if an operation on a path is permitted.

        Returns:
            (decision, reason) tuple.
        """
        try:
            resolved = path.resolve()
        except (OSError, RuntimeError):
            return self._deny(path, operation, AccessDecision.DENIED_PATH_TRAVERSAL,
                            "Failed to resolve path — possible traversal attack")

        # 1. Block path traversal patterns in the original path string
        path_str = str(path)
        if ".." in path_str.split(os.sep):
            return self._deny(path, operation, AccessDecision.DENIED_PATH_TRAVERSAL,
                            f"Path contains traversal pattern: {path_str}")

        # 2. Block system directories
        if self._is_system_path(resolved):
            return self._deny(path, operation, AccessDecision.DENIED_SYSTEM_DIR,
                            f"Path is inside a protected system directory")

        # 3. Block protected user paths
        if self._is_protected_user_path(resolved):
            return self._deny(path, operation, AccessDecision.DENIED_BLOCKLISTED,
                            f"Path is inside a protected user directory (credentials/config)")

        # 4. Check symlink escape
        if not self.config.enable_symlink_following and path.is_symlink():
            link_target = path.resolve()
            if not self._is_within_allowed_roots(link_target):
                return self._deny(path, operation, AccessDecision.DENIED_SYMLINK_ESCAPE,
                                f"Symlink points outside allowed scope: {link_target}")

        # 5. Check blocklist
        if str(resolved) in self._blocklisted_paths:
            return self._deny(path, operation, AccessDecision.DENIED_BLOCKLISTED,
                            "Path has been blocklisted")

        # 6. For destructive operations, check scope and rate limits
        if operation in (OperationType.TRASH, OperationType.DELETE):
            if not self._is_within_allowed_roots(resolved):
                return self._deny(path, operation, AccessDecision.DENIED_OUTSIDE_SCOPE,
                                "Destructive operation outside authorized scan scope")

            if self._session_delete_count >= self.config.max_delete_per_session:
                return self._deny(path, operation, AccessDecision.DENIED_RATE_LIMITED,
                                f"Session delete limit reached ({self.config.max_delete_per_session})")

            if self._session_delete_bytes >= self.config.max_delete_size_bytes:
                return self._deny(path, operation, AccessDecision.DENIED_RATE_LIMITED,
                                f"Session delete size limit reached")

        # 7. For AI content reading, check extension whitelist
        if operation == OperationType.AI_READ:
            ext = resolved.suffix.lower()
            if ext not in self.config.ai_allowed_extensions:
                return self._deny(path, operation, AccessDecision.DENIED_BLOCKLISTED,
                                f"AI content analysis not allowed for extension: {ext}")

        # All checks passed
        self._log_access(path, operation, AccessDecision.ALLOWED, "Access permitted")
        return AccessDecision.ALLOWED, "Access permitted"

    def record_deletion(self, path: Path, size_bytes: int) -> None:
        """Record a successful deletion for rate limiting."""
        self._session_delete_count += 1
        self._session_delete_bytes += size_bytes

    def reset_session_limits(self) -> None:
        """Reset session-based rate limits (e.g., on new scan)."""
        self._session_delete_count = 0
        self._session_delete_bytes = 0

    def blocklist_path(self, path: Path) -> None:
        """Add a path to the blocklist (user marked as 'keep')."""
        self._blocklisted_paths.add(str(path.resolve()))

    def get_audit_log(self) -> list[AccessAuditEntry]:
        """Return the complete audit log for this session."""
        return list(self._audit_log)

    def get_audit_summary(self) -> dict:
        """Return a summary of access decisions in this session."""
        allowed = sum(1 for e in self._audit_log if e.decision == AccessDecision.ALLOWED)
        denied = sum(1 for e in self._audit_log if e.decision != AccessDecision.ALLOWED)
        return {
            "total_checks": len(self._audit_log),
            "allowed": allowed,
            "denied": denied,
            "deletions_this_session": self._session_delete_count,
            "bytes_deleted_this_session": self._session_delete_bytes,
        }

    # ── Internal helpers ─────────────────────────────────────

    def _is_system_path(self, resolved: Path) -> bool:
        """Check if a path is inside a system directory."""
        for sys_dir in self._system_dirs:
            try:
                resolved.relative_to(sys_dir)
                return True
            except ValueError:
                continue
        return False

    def _is_protected_user_path(self, resolved: Path) -> bool:
        """Check if a path is inside a protected user directory."""
        for protected in self._protected_paths:
            try:
                resolved.relative_to(protected.resolve())
                return True
            except ValueError:
                continue
        return False

    def _is_within_allowed_roots(self, resolved: Path) -> bool:
        """Check if a path is inside any authorized scan root."""
        for root in self.config.allowed_roots:
            try:
                resolved.relative_to(root)
                return True
            except ValueError:
                continue
        return False

    def _deny(self, path: Path, operation: OperationType,
              decision: AccessDecision, reason: str) -> tuple[AccessDecision, str]:
        """Log a denial and return the decision."""
        self._log_access(path, operation, decision, reason)
        logger.warning(f"ACCESS DENIED: {operation.value} on {path} — {reason}")
        return decision, reason

    def _log_access(self, path: Path, operation: OperationType,
                    decision: AccessDecision, reason: str) -> None:
        """Add an entry to the audit log."""
        if self.config.enable_audit_logging:
            self._audit_log.append(AccessAuditEntry(
                timestamp=datetime.now().isoformat(),
                operation=operation,
                path=str(path),
                decision=decision,
                reason=reason,
            ))


class SecureFileOperations:
    """Wraps all destructive file operations with sandbox checks.

    The UI layer uses this class instead of directly calling os.remove()
    or send2trash. Every operation is validated through the PathSandbox first.
    """

    def __init__(self, sandbox: PathSandbox):
        self.sandbox = sandbox

    def safe_trash(self, path: Path) -> tuple[bool, str]:
        """Move a file to trash after sandbox validation.

        Returns:
            (success, message) tuple.
        """
        if not path.exists():
            return True, f"File already removed: {path.name}"

        decision, reason = self.sandbox.check_access(path, OperationType.TRASH)
        if decision != AccessDecision.ALLOWED:
            return False, f"🚫 Blocked: {reason}"

        try:
            import send2trash
            size = path.stat().st_size if path.exists() else 0
            send2trash.send2trash(str(path))
            self.sandbox.record_deletion(path, size)
            return True, f"✅ Moved to trash: {path.name}"
        except Exception as e:
            return False, f"❌ Error trashing {path.name}: {e}"

    def safe_delete(self, path: Path) -> tuple[bool, str]:
        """Permanently delete a file after sandbox validation.

        Returns:
            (success, message) tuple.
        """
        if not path.exists():
            return True, f"File already removed: {path.name}"

        decision, reason = self.sandbox.check_access(path, OperationType.DELETE)
        if decision != AccessDecision.ALLOWED:
            return False, f"🚫 Blocked: {reason}"

        try:
            size = path.stat().st_size if path.exists() else 0
            os.remove(path)
            self.sandbox.record_deletion(path, size)
            return True, f"🗑 Deleted: {path.name}"
        except Exception as e:
            return False, f"❌ Error deleting {path.name}: {e}"

    def safe_read_content(self, path: Path, max_bytes: int | None = None) -> tuple[bool, str]:
        """Read file content for AI analysis after sandbox validation.

        Returns:
            (success, content_or_error) tuple.
        """
        decision, reason = self.sandbox.check_access(path, OperationType.AI_READ)
        if decision != AccessDecision.ALLOWED:
            return False, f"🚫 Blocked: {reason}"

        max_bytes = max_bytes or self.sandbox.config.ai_content_max_bytes
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_bytes)
            return True, content
        except Exception as e:
            return False, f"❌ Error reading {path.name}: {e}"
