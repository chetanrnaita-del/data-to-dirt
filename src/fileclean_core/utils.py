"""Utility functions for FileClean."""

from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path


def format_size(size_bytes: int) -> str:
    """Convert bytes to a human-readable string.

    Examples:
        >>> format_size(0)
        '0 B'
        >>> format_size(1024)
        '1.0 KB'
        >>> format_size(1073741824)
        '1.0 GB'
    """
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    if unit_index == 0:
        return f"{int(size)} B"
    return f"{size:.1f} {units[unit_index]}"


def hash_file(path: Path, algorithm: str = "sha256", chunk_size: int = 8192) -> str:
    """Compute the hash of a file using chunked reading for memory efficiency.

    Args:
        path: Path to the file to hash.
        algorithm: Hash algorithm to use (default: sha256).
        chunk_size: Size of chunks to read at a time.

    Returns:
        Hex digest string of the file hash.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        PermissionError: If the file can't be read.
    """
    h = hashlib.new(algorithm)
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except (FileNotFoundError, PermissionError, OSError):
        return ""


def get_file_age_days(path: Path, use_access_time: bool = False) -> float:
    """Get the age of a file in days since last modification or access.

    Args:
        path: Path to the file.
        use_access_time: If True, use last access time instead of modification time.

    Returns:
        Number of days since the file was last modified/accessed.
    """
    stat = path.stat()
    timestamp = stat.st_atime if use_access_time else stat.st_mtime
    age_seconds = time.time() - timestamp
    return age_seconds / 86400  # seconds to days


def is_hidden(path: Path) -> bool:
    """Check if a file or directory is hidden.

    On Unix-like systems, hidden files start with a dot.
    On Windows, checks the file attributes.
    """
    if path.name.startswith("."):
        return True

    # Windows hidden attribute check
    try:
        import ctypes
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))  # type: ignore[attr-defined]
        if attrs != -1:
            FILE_ATTRIBUTE_HIDDEN = 0x2
            return bool(attrs & FILE_ATTRIBUTE_HIDDEN)
    except (AttributeError, OSError):
        pass

    return False


# Regex patterns for detecting copy/duplicate filenames
COPY_PATTERNS = re.compile(
    r"""
    (?:
        \bcopy\b           |  # "Copy", "copy"
        \bcopia\b          |  # Spanish/Italian copy
        \bcopie\b          |  # French copy
        \bKopie\b          |  # German copy
        \(\d+\)            |  # "(1)", "(2)", etc.
        \s-\s\d+           |  # " - 1", " - 2"
        _copy\d*           |  # "_copy", "_copy2"
        \s+copy\s*\d*      |  # " copy", " copy 2"
        _\d{1,2}$          |  # "_1", "_02" at end
        [_\-\s]v\d+        |  # "_v2", "-v2", " v2"
        \bv\d+             |  # "v2", "v3"
        _final             |  # "_final"
        _FINAL             |  # "_FINAL"
        \bfinal\b          |  # "final"
        _old               |  # "_old"
        _backup            |  # "_backup"
        _bak               |  # "_bak"
        \bbackup\b            # "backup"
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Patterns indicating temporary files
TEMP_PATTERNS = re.compile(
    r"""
    (?:
        ^~\$               |  # Office temp files
        ^~                 |  # General temp prefix
        \.tmp$             |  # .tmp extension
        \.temp$            |  # .temp extension
        \.bak$             |  # .bak extension
        \.swp$             |  # Vim swap
        \.swo$             |  # Vim swap
        \.part$            |  # Partial download
        \.crdownload$      |  # Chrome partial download
        \.partial$            # Partial file
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)


def has_copy_pattern(filename: str) -> bool:
    """Check if a filename contains patterns suggesting it's a copy/duplicate."""
    stem = Path(filename).stem
    return bool(COPY_PATTERNS.search(stem))


def has_temp_pattern(filename: str) -> bool:
    """Check if a filename indicates a temporary file."""
    return bool(TEMP_PATTERNS.search(filename))


# Mapping of file extensions to general MIME categories
MIME_CATEGORIES: dict[str, str] = {
    # Documents
    ".doc": "document", ".docx": "document", ".pdf": "document",
    ".txt": "document", ".rtf": "document", ".odt": "document",
    ".xls": "document", ".xlsx": "document", ".ods": "document",
    ".ppt": "document", ".pptx": "document", ".odp": "document",
    ".md": "document", ".tex": "document", ".csv": "document",
    # Images
    ".jpg": "image", ".jpeg": "image", ".png": "image",
    ".gif": "image", ".bmp": "image", ".svg": "image",
    ".webp": "image", ".tiff": "image", ".ico": "image",
    ".heic": "image", ".heif": "image", ".raw": "image",
    # Videos
    ".mp4": "video", ".avi": "video", ".mkv": "video",
    ".mov": "video", ".wmv": "video", ".flv": "video",
    ".webm": "video", ".m4v": "video",
    # Audio
    ".mp3": "audio", ".wav": "audio", ".flac": "audio",
    ".aac": "audio", ".ogg": "audio", ".wma": "audio",
    ".m4a": "audio",
    # Archives
    ".zip": "archive", ".tar": "archive", ".gz": "archive",
    ".bz2": "archive", ".7z": "archive", ".rar": "archive",
    ".xz": "archive", ".tgz": "archive",
    # Code
    ".py": "code", ".js": "code", ".ts": "code",
    ".java": "code", ".c": "code", ".cpp": "code",
    ".h": "code", ".hpp": "code", ".cs": "code",
    ".go": "code", ".rs": "code", ".rb": "code",
    ".php": "code", ".swift": "code", ".kt": "code",
    ".html": "code", ".css": "code", ".scss": "code",
    ".json": "code", ".xml": "code", ".yaml": "code",
    ".yml": "code", ".toml": "code", ".ini": "code",
    ".sh": "code", ".bash": "code", ".zsh": "code",
    # Executables
    ".exe": "executable", ".msi": "executable", ".dmg": "executable",
    ".app": "executable", ".deb": "executable", ".rpm": "executable",
    ".appimage": "executable",
    # System / junk
    ".tmp": "junk", ".temp": "junk", ".bak": "junk",
    ".swp": "junk", ".swo": "junk", ".log": "junk",
    ".cache": "junk", ".pyc": "junk", ".pyo": "junk",
    ".class": "junk", ".o": "junk", ".obj": "junk",
}


def get_mime_category(extension: str) -> str:
    """Get the general MIME category for a file extension."""
    return MIME_CATEGORIES.get(extension.lower(), "other")


# Parent directory name to category mapping
DIR_CATEGORIES: dict[str, str] = {
    "downloads": "downloads",
    "download": "downloads",
    "desktop": "desktop",
    "documents": "documents",
    "pictures": "pictures",
    "photos": "pictures",
    "videos": "videos",
    "movies": "videos",
    "music": "music",
    "trash": "trash",
    ".trash": "trash",
    "tmp": "temp",
    "temp": "temp",
    "cache": "cache",
    ".cache": "cache",
    "node_modules": "cache",
    "__pycache__": "cache",
    "build": "build",
    "dist": "build",
    "target": "build",
    "bin": "build",
    "obj": "build",
}


def get_parent_dir_category(path: Path) -> str:
    """Categorize the parent directory of a file."""
    for parent in path.parents:
        name_lower = parent.name.lower()
        if name_lower in DIR_CATEGORIES:
            return DIR_CATEGORIES[name_lower]
    return "other"
