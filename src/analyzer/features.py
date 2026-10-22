from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from src.analyzer.models import FileMetadata
from src.fileclean_core.utils import (
    get_file_age_days,
    is_hidden,
    has_copy_pattern,
    has_temp_pattern,
    get_mime_category,
    get_parent_dir_category,
)
from src.fileclean_core.config import Config

def extract_metadata(root_dir: Path, file_path: Path, config: Optional[Config] = None) -> Optional[FileMetadata]:
    """Extract FileMetadata from a file path."""
    try:
        stat = file_path.stat()
    except (PermissionError, FileNotFoundError):
        return None

    try:
        depth = len(file_path.relative_to(root_dir).parents) - 1
    except ValueError:
        depth = 0
        
    is_junk_dir = False
    if config and config.junk_directories:
        for parent in file_path.parents:
            if parent == file_path.root:
                break
            if parent.name in config.junk_directories:
                is_junk_dir = True
                break

    try:
        sibling_count = sum(1 for _ in file_path.parent.iterdir() if _.is_file())
    except (PermissionError, FileNotFoundError):
        sibling_count = 0

    days_mod = get_file_age_days(file_path, use_access_time=False)
    days_acc = get_file_age_days(file_path, use_access_time=True)

    return FileMetadata(
        path=file_path,
        name=file_path.name,
        extension=file_path.suffix.lower(),
        size=stat.st_size,
        days_since_modified=days_mod,
        days_since_accessed=days_acc,
        depth=depth,
        name_length=len(file_path.name),
        has_copy_pattern=has_copy_pattern(file_path.name),
        has_temp_pattern=has_temp_pattern(file_path.name),
        is_hidden=is_hidden(file_path),
        sibling_count=sibling_count,
        parent_dir_category=get_parent_dir_category(file_path),
        mime_category=get_mime_category(file_path.suffix.lower()),
        is_in_known_junk_dir=is_junk_dir,
    )

def extract_batch(root_dir: Path, file_paths: List[Path], config: Optional[Config] = None) -> List[FileMetadata]:
    """Extract FileMetadata for a batch of file paths."""
    results = []
    for p in file_paths:
        meta = extract_metadata(root_dir, p, config)
        if meta:
            results.append(meta)
    return results
