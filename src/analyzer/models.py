"""Data models for FileClean analysis results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class IssueCategory(str, Enum):
    """Categories of file issues detected by the analyzer."""
    DUPLICATE = "duplicate"
    JUNK = "junk"
    OLD = "old"
    LARGE = "large"
    AI_SUGGESTION = "ai_suggestion"


class Confidence(str, Enum):
    """Confidence level of a file issue detection."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueSource(str, Enum):
    """Source that detected the file issue."""
    RULE = "rule"
    CLASSIFIER = "classifier"
    AI = "ai"


@dataclass
class FileIssue:
    """Represents a single issue detected for a file.

    Attributes:
        path: Absolute path to the file.
        category: The type of issue (duplicate, junk, old, large, ai_suggestion).
        reason: Short human-readable explanation.
        size: File size in bytes.
        confidence: How confident the detection is.
        source: Whether this came from rules, ML classifier, or AI explainer.
        group_id: For duplicates — hash to group identical files together.
        ai_explanation: Detailed AI-generated reasoning (if available).
    """
    path: Path
    category: IssueCategory
    reason: str
    size: int
    confidence: Confidence = Confidence.HIGH
    source: IssueSource = IssueSource.RULE
    group_id: str | None = None
    original_path: Path | None = None
    ai_explanation: str | None = None

    @property
    def size_display(self) -> str:
        """Return human-readable file size."""
        from src.fileclean_core.utils import format_size
        return format_size(self.size)


@dataclass
class ScanResult:
    """Aggregated results from a full directory scan.

    Attributes:
        directory: The root directory that was scanned.
        total_files: Total number of files scanned.
        total_size: Total size of all scanned files in bytes.
        issues: List of all detected file issues.
        scan_duration: How long the scan took in seconds.
        ai_enabled: Whether AI analysis was used.
    """
    directory: Path
    total_files: int = 0
    total_size: int = 0
    issues: list[FileIssue] = field(default_factory=list)
    scan_duration: float = 0.0
    ai_enabled: bool = False

    @property
    def reclaimable_space(self) -> int:
        """Total space that can be reclaimed by removing all flagged files."""
        return sum(issue.size for issue in self.issues)

    @property
    def reclaimable_display(self) -> str:
        """Human-readable reclaimable space."""
        from src.fileclean_core.utils import format_size
        return format_size(self.reclaimable_space)

    def issues_by_category(self, category: IssueCategory) -> list[FileIssue]:
        """Filter issues by category."""
        return [i for i in self.issues if i.category == category]

    @property
    def duplicate_count(self) -> int:
        return len(self.issues_by_category(IssueCategory.DUPLICATE))

    @property
    def junk_count(self) -> int:
        return len(self.issues_by_category(IssueCategory.JUNK))

    @property
    def old_count(self) -> int:
        return len(self.issues_by_category(IssueCategory.OLD))

    @property
    def large_count(self) -> int:
        return len(self.issues_by_category(IssueCategory.LARGE))

    @property
    def ai_suggestion_count(self) -> int:
        return len(self.issues_by_category(IssueCategory.AI_SUGGESTION))


@dataclass
class FileMetadata:
    """Extracted metadata for a single file, used as input to the classifier.

    Attributes:
        path: Absolute file path.
        name: File name without directory.
        extension: File extension (lowercase, with dot).
        size: File size in bytes.
        days_since_modified: Days since last modification.
        days_since_accessed: Days since last access.
        depth: Depth in directory tree relative to scan root.
        name_length: Length of the filename.
        has_copy_pattern: Whether name contains copy/duplicate patterns.
        has_temp_pattern: Whether name/extension indicates a temp file.
        is_hidden: Whether the file is hidden (starts with dot or OS-hidden).
        sibling_count: Number of files in the same directory.
        duplicate_hash_count: Number of files with the same content hash.
        parent_dir_category: Category of the parent directory.
        mime_category: General MIME type category.
        is_in_known_junk_dir: Whether file is inside a known junk directory.
        content_hash: SHA256 hash of file contents (computed lazily).
    """
    path: Path
    name: str = ""
    extension: str = ""
    size: int = 0
    days_since_modified: float = 0.0
    days_since_accessed: float = 0.0
    depth: int = 0
    name_length: int = 0
    has_copy_pattern: bool = False
    has_temp_pattern: bool = False
    is_hidden: bool = False
    sibling_count: int = 0
    duplicate_hash_count: int = 1
    parent_dir_category: str = "other"
    mime_category: str = "other"
    is_in_known_junk_dir: bool = False
    content_hash: str | None = None

    def to_feature_dict(self) -> dict:
        """Convert to a dictionary of features for the ML classifier."""
        return {
            "extension": self.extension,
            "size": self.size,
            "days_since_modified": self.days_since_modified,
            "days_since_accessed": self.days_since_accessed,
            "depth": self.depth,
            "name_length": self.name_length,
            "has_copy_pattern": int(self.has_copy_pattern),
            "has_temp_pattern": int(self.has_temp_pattern),
            "is_hidden": int(self.is_hidden),
            "sibling_count": self.sibling_count,
            "duplicate_hash_count": self.duplicate_hash_count,
            "parent_dir_category": self.parent_dir_category,
            "mime_category": self.mime_category,
            "is_in_known_junk_dir": int(self.is_in_known_junk_dir),
        }
