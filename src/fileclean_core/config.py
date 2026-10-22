"""Application configuration management for FileClean."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path


# Known junk file extensions
DEFAULT_JUNK_EXTENSIONS: list[str] = [
    ".tmp", ".temp", ".bak", ".old", ".orig", ".swp", ".swo",
    ".log", ".log1", ".log2",
    ".cache", ".crdownload", ".part", ".partial",
    ".pyc", ".pyo",
    ".class",
    ".o", ".obj",
    ".DS_Store", ".Spotlight-V100", ".Trashes", ".fseventsd",
    "Thumbs.db", "desktop.ini", "ehthumbs.db",
    ".sass-cache",
]

# Known junk directory names
DEFAULT_JUNK_DIRECTORIES: list[str] = [
    "__pycache__",
    "node_modules",
    ".cache",
    ".tmp",
    ".temp",
    ".Trash",
    ".Trash-1000",
    "Thumbs.db",
    ".sass-cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".eggs",
    "*.egg-info",
    "dist",
    "build",
    ".gradle",
    ".idea",
    ".vscode",
    "__MACOSX",
]

# Known junk filename patterns (glob-style)
DEFAULT_JUNK_PATTERNS: list[str] = [
    "~$*",           # Office temp files
    "~*.tmp",        # Generic temp
    "*.part",        # Partial downloads
    ".~lock.*",      # LibreOffice locks
    "._*",           # macOS resource forks
    ".nfs*",         # NFS temp files
]


@dataclass
class Config:
    """Application configuration with sensible defaults.

    Attributes:
        old_file_days: Threshold in days to consider a file 'old'.
        large_file_mb: Threshold in MB to consider a file 'large'.
        junk_extensions: File extensions considered junk.
        junk_directories: Directory names considered junk.
        junk_patterns: Filename glob patterns considered junk.
        skip_hidden: Whether to skip hidden files during scan.
        max_scan_depth: Maximum directory depth to scan (None = unlimited).
        ai_model_path: Path to the GGUF model file for AI explanations.
        classifier_path: Path to the trained classifier (.joblib).
        enable_ai: Whether AI analysis is enabled.
        enable_content_analysis: Allow AI to read text file snippets.
        content_snippet_max_bytes: Max bytes to read for content analysis.
        theme: GUI theme ('dark' or 'light').
        feedback_db_path: Path to the SQLite feedback database.
    """
    old_file_days: int = 180
    large_file_mb: int = 100
    junk_extensions: list[str] = field(default_factory=lambda: list(DEFAULT_JUNK_EXTENSIONS))
    junk_directories: list[str] = field(default_factory=lambda: list(DEFAULT_JUNK_DIRECTORIES))
    junk_patterns: list[str] = field(default_factory=lambda: list(DEFAULT_JUNK_PATTERNS))
    skip_hidden: bool = False
    max_scan_depth: int | None = None
    ai_model_path: str | None = None
    classifier_path: str | None = None
    enable_ai: bool = True
    enable_content_analysis: bool = False
    content_snippet_max_bytes: int = 512
    theme: str = "dark"
    feedback_db_path: str | None = None

    @property
    def large_file_bytes(self) -> int:
        """Large file threshold in bytes."""
        return self.large_file_mb * 1024 * 1024

    def save(self, path: Path) -> None:
        """Save configuration to a JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> Config:
        """Load configuration from a JSON file. Returns defaults if file doesn't exist."""
        if not path.exists():
            return cls()
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        except (json.JSONDecodeError, TypeError):
            return cls()

    @staticmethod
    def default_config_path() -> Path:
        """Return the default config file path based on OS."""
        import platform
        system = platform.system()
        if system == "Darwin":
            base = Path(__file__).resolve().parent.parent.parent / ".data"
        elif system == "Windows":
            base = Path.home() / "AppData" / "Local" / "FileClean"
        else:
            base = Path.home() / ".config" / "fileclean"
        return base / "config.json"

    @staticmethod
    def default_data_dir() -> Path:
        """Return the default data directory for models, DB, etc."""
        import platform
        system = platform.system()
        if system == "Darwin":
            base = Path(__file__).resolve().parent.parent.parent / ".data"
        elif system == "Windows":
            base = Path.home() / "AppData" / "Local" / "FileClean"
        else:
            base = Path.home() / ".local" / "share" / "fileclean"
        return base
