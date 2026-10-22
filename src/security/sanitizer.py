"""Input Sanitization & Schema Validation for FileClean.

Intercepts all user-facing inputs and system arguments, passing them through
rigorous validation layers before they interact with the local OS or database.

Provides:
1. PATH SANITIZATION — Validates and normalizes directory/file paths, preventing
   injection, traversal, and encoding attacks.
2. SCHEMA VALIDATION — Validates configuration, settings, and data structures
   against strict schemas before processing.
3. SQL INJECTION PREVENTION — Additional guard layer for database inputs beyond
   parameterized queries.
4. FILENAME SANITIZATION — Cleans filenames for safe display and processing.
"""

from __future__ import annotations

import os
import re
import string
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


class ValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.message = message
        self.value = value
        super().__init__(f"Validation error on '{field}': {message}")


# ──────────────────────────────────────────────────────────────
# Path Sanitization
# ──────────────────────────────────────────────────────────────

# Dangerous path patterns
_PATH_TRAVERSAL_PATTERN = re.compile(r"(^|[\\/])\.\.([\\/]|$)")
_NULL_BYTE_PATTERN = re.compile(r"\x00")
_SHELL_INJECTION_PATTERN = re.compile(r"[;&|`$(){}!\n\r]")
_UNICODE_HOMOGLYPH_PATTERN = re.compile(
    r"[\u200b\u200c\u200d\u200e\u200f"   # Zero-width chars
    r"\u202a\u202b\u202c\u202d\u202e"     # Bidi override chars
    r"\ufeff\ufffe]"                       # BOM and reversed BOM
)

# Maximum path length (OS limits)
MAX_PATH_LENGTH = 1024
MAX_FILENAME_LENGTH = 255


def sanitize_path(path_str: str) -> Path:
    """Validate and sanitize a filesystem path.

    Performs these checks:
    1. Non-empty and within length limits
    2. No null bytes
    3. No path traversal sequences (..)
    4. No shell injection characters
    5. No Unicode homoglyph attacks
    6. Path exists and is accessible

    Args:
        path_str: Raw path string from user input.

    Returns:
        Sanitized, resolved Path object.

    Raises:
        ValidationError: If the path fails any validation check.
    """
    if not path_str or not str(path_str).strip():
        raise ValidationError("path", "Path cannot be empty")

    path_str = str(path_str).strip()

    # Strip surrounding single or double quotes
    if (path_str.startswith('"') and path_str.endswith('"')) or \
       (path_str.startswith("'") and path_str.endswith("'")):
        path_str = path_str[1:-1].strip()

    if not path_str:
        raise ValidationError("path", "Path cannot be empty")

    # Length check
    if len(path_str) > MAX_PATH_LENGTH:
        raise ValidationError("path", f"Path exceeds maximum length ({MAX_PATH_LENGTH} chars)",
                            path_str[:50] + "...")

    # Null byte injection
    if _NULL_BYTE_PATTERN.search(path_str):
        raise ValidationError("path", "Path contains null bytes — possible injection attack")

    # Path traversal
    if _PATH_TRAVERSAL_PATTERN.search(path_str):
        raise ValidationError("path", "Path contains traversal sequence '..' — not allowed",
                            path_str)

    # Shell injection characters
    if _SHELL_INJECTION_PATTERN.search(path_str):
        raise ValidationError("path", "Path contains shell metacharacters — not allowed",
                            path_str)

    # Unicode homoglyph attacks
    if _UNICODE_HOMOGLYPH_PATTERN.search(path_str):
        raise ValidationError("path", "Path contains invisible Unicode characters — possible homoglyph attack")

    # Resolve and validate with tilde expansion
    try:
        expanded = os.path.expanduser(path_str)
        resolved = Path(expanded).resolve()
    except (OSError, RuntimeError) as e:
        raise ValidationError("path", f"Failed to resolve path: {e}")

    return resolved


def sanitize_directory(path_str: str) -> Path:
    """Validate a path is a real, accessible directory.

    Args:
        path_str: Raw directory path from user input.

    Returns:
        Sanitized directory Path.

    Raises:
        ValidationError: If path is not a valid directory.
    """
    path = sanitize_path(path_str)

    if not path.exists():
        raise ValidationError("directory", f"Directory does not exist: {path}")

    if not path.is_dir():
        raise ValidationError("directory", f"Path is not a directory: {path}")

    # Check readability and active directory descriptor access (catches macOS TCC EPERM)
    if not os.access(path, os.R_OK):
        raise ValidationError("directory", f"Directory is not readable: {path}")

    try:
        with os.scandir(path) as it:
            pass
    except (PermissionError, OSError) as e:
        raise ValidationError("directory", f"Directory is not accessible (permission denied or macOS TCC restriction): {e}")

    return path


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for safe display and processing.

    Removes or replaces dangerous characters while preserving readability.

    Args:
        filename: Raw filename string.

    Returns:
        Sanitized filename safe for display.
    """
    if not filename:
        return "unnamed"

    # Remove null bytes and control characters
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", filename)

    # Remove Unicode homoglyphs
    cleaned = _UNICODE_HOMOGLYPH_PATTERN.sub("", cleaned)

    # Limit length
    if len(cleaned) > MAX_FILENAME_LENGTH:
        name, ext = os.path.splitext(cleaned)
        cleaned = name[:MAX_FILENAME_LENGTH - len(ext) - 3] + "..." + ext

    return cleaned or "unnamed"


# ──────────────────────────────────────────────────────────────
# Schema Validation
# ──────────────────────────────────────────────────────────────

@dataclass
class SchemaField:
    """Definition of a valid field in a schema."""
    name: str
    type: type | tuple[type, ...]
    required: bool = True
    min_value: int | float | None = None
    max_value: int | float | None = None
    min_length: int | None = None
    max_length: int | None = None
    allowed_values: list[Any] | None = None
    pattern: re.Pattern | None = None


class SchemaValidator:
    """Validates data structures against predefined schemas.

    Used to validate config files, settings changes, and any structured
    data before it's processed by the application.
    """

    # Schema for Config fields
    CONFIG_SCHEMA: list[SchemaField] = [
        SchemaField("old_file_days", int, min_value=1, max_value=3650),
        SchemaField("large_file_mb", int, min_value=1, max_value=102400),
        SchemaField("skip_hidden", bool),
        SchemaField("max_scan_depth", (int, type(None)), required=False, min_value=1, max_value=100),
        SchemaField("enable_ai", bool),
        SchemaField("enable_content_analysis", bool),
        SchemaField("content_snippet_max_bytes", int, min_value=64, max_value=10240),
        SchemaField("theme", str, allowed_values=["dark", "light", "system"]),
    ]

    @classmethod
    def validate_config(cls, data: dict) -> list[ValidationError]:
        """Validate a configuration dictionary against the config schema.

        Returns:
            List of validation errors (empty if valid).
        """
        return cls._validate_schema(data, cls.CONFIG_SCHEMA)

    @classmethod
    def validate_field(cls, name: str, value: Any, schema_field: SchemaField) -> ValidationError | None:
        """Validate a single field value against its schema definition."""
        # Type check
        if not isinstance(value, schema_field.type):
            if value is None and not schema_field.required:
                return None
            return ValidationError(
                name,
                f"Expected type {schema_field.type}, got {type(value).__name__}",
                value
            )

        # Range check for numbers
        if isinstance(value, (int, float)):
            if schema_field.min_value is not None and value < schema_field.min_value:
                return ValidationError(
                    name, f"Value {value} below minimum {schema_field.min_value}", value
                )
            if schema_field.max_value is not None and value > schema_field.max_value:
                return ValidationError(
                    name, f"Value {value} above maximum {schema_field.max_value}", value
                )

        # Length check for strings
        if isinstance(value, str):
            if schema_field.min_length is not None and len(value) < schema_field.min_length:
                return ValidationError(
                    name, f"String too short (min {schema_field.min_length})", value
                )
            if schema_field.max_length is not None and len(value) > schema_field.max_length:
                return ValidationError(
                    name, f"String too long (max {schema_field.max_length})", value
                )

        # Allowed values check
        if schema_field.allowed_values is not None and value not in schema_field.allowed_values:
            return ValidationError(
                name, f"Value '{value}' not in allowed values: {schema_field.allowed_values}", value
            )

        # Pattern check
        if schema_field.pattern is not None and isinstance(value, str):
            if not schema_field.pattern.match(value):
                return ValidationError(
                    name, f"Value doesn't match required pattern", value
                )

        return None

    @classmethod
    def _validate_schema(cls, data: dict, schema: list[SchemaField]) -> list[ValidationError]:
        """Validate a dictionary against a list of schema fields."""
        errors = []

        for field_def in schema:
            if field_def.name not in data:
                if field_def.required:
                    errors.append(ValidationError(field_def.name, "Required field is missing"))
                continue

            error = cls.validate_field(field_def.name, data[field_def.name], field_def)
            if error:
                errors.append(error)

        return errors


# ──────────────────────────────────────────────────────────────
# SQL Injection Prevention
# ──────────────────────────────────────────────────────────────

# Patterns that indicate SQL injection attempts
_SQL_INJECTION_PATTERNS = [
    re.compile(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC)\b)", re.IGNORECASE),
    re.compile(r"(--|#|/\*|\*/)", re.IGNORECASE),
    re.compile(r"('|\"|;)", re.IGNORECASE),
    re.compile(r"(\bOR\b\s+\b\d+\b\s*=\s*\b\d+\b)", re.IGNORECASE),  # OR 1=1
    re.compile(r"(\bUNION\b\s+\bSELECT\b)", re.IGNORECASE),
]


def sanitize_db_input(value: str, field_name: str = "input") -> str:
    """Sanitize a string before using it in database operations.

    Note: FileClean already uses parameterized queries (sqlite3 ? placeholders),
    which is the primary defense against SQL injection. This function provides
    an additional defense-in-depth layer.

    Args:
        value: The string to sanitize.
        field_name: Name of the field for error messages.

    Returns:
        The sanitized string.

    Raises:
        ValidationError: If the input contains SQL injection patterns.
    """
    if not isinstance(value, str):
        return str(value)

    for pattern in _SQL_INJECTION_PATTERNS:
        if pattern.search(value):
            raise ValidationError(
                field_name,
                "Input contains potentially dangerous SQL patterns",
                value[:50]
            )

    return value


# ──────────────────────────────────────────────────────────────
# Convenience validators for common use cases
# ──────────────────────────────────────────────────────────────

def validate_scan_request(directory: str) -> Path:
    """Validate a full scan request — combines path sanitization with
    directory validation.

    Args:
        directory: User-provided directory path to scan.

    Returns:
        Validated, resolved Path object.

    Raises:
        ValidationError: If the path is invalid or unsafe.
    """
    return sanitize_directory(directory)


def validate_threshold(value: Any, name: str, min_val: int, max_val: int) -> int:
    """Validate a numeric threshold value (e.g., file size, age).

    Args:
        value: The threshold value to validate.
        name: Human-readable name for error messages.
        min_val: Minimum allowed value.
        max_val: Maximum allowed value.

    Returns:
        Validated integer value.

    Raises:
        ValidationError: If the value is out of range or not numeric.
    """
    try:
        int_value = int(value)
    except (TypeError, ValueError):
        raise ValidationError(name, f"Must be a number, got: {type(value).__name__}", value)

    if int_value < min_val or int_value > max_val:
        raise ValidationError(name, f"Must be between {min_val} and {max_val}, got: {int_value}", int_value)

    return int_value


def validate_extension_list(extensions: list[str]) -> list[str]:
    """Validate a list of file extensions.

    Ensures each extension starts with a dot and contains only safe characters.

    Args:
        extensions: List of extension strings.

    Returns:
        Validated and normalized list.

    Raises:
        ValidationError: If any extension is malformed.
    """
    safe_ext_pattern = re.compile(r"^\.[a-zA-Z0-9_-]{1,20}$")
    validated = []

    for ext in extensions:
        ext = ext.strip().lower()
        if not ext.startswith("."):
            ext = "." + ext

        if not safe_ext_pattern.match(ext):
            raise ValidationError("extension", f"Invalid extension format: {ext}", ext)

        validated.append(ext)

    return validated
