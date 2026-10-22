from __future__ import annotations

import fnmatch
from collections import defaultdict
from typing import List
from pathlib import Path

from src.analyzer.models import FileMetadata, FileIssue, IssueCategory, Confidence, IssueSource
from src.fileclean_core.config import Config
from src.fileclean_core.utils import hash_file

class DuplicateFinder:
    def detect(self, files: List[FileMetadata], config: Config) -> List[FileIssue]:
        issues = []
        
        # Group by size
        size_groups = defaultdict(list)
        for f in files:
            size_groups[f.size].append(f)
            
        for size, group in size_groups.items():
            # Skip empty or negligible files (e.g. 0-byte or <16 byte stubs)
            if len(group) < 2 or size < 16:
                continue
                
            hash_groups = defaultdict(list)
            for f in group:
                try:
                    f.content_hash = hash_file(f.path)
                    hash_groups[f.content_hash].append(f)
                except (PermissionError, OSError):
                    continue
                    
            for file_hash, hgroup in hash_groups.items():
                if len(hgroup) < 2:
                    continue
                
                # Keep the one with the shortest path or oldest modification as original
                hgroup.sort(key=lambda x: (len(str(x.path)), x.days_since_modified))
                original = hgroup[0]
                
                for f in hgroup[1:]:
                    issues.append(FileIssue(
                        path=f.path,
                        category=IssueCategory.DUPLICATE,
                        reason=f"Identical content to '{original.name}' (SHA-256 match)",
                        size=f.size,
                        confidence=Confidence.HIGH,
                        source=IssueSource.RULE,
                        group_id=file_hash,
                        original_path=original.path
                    ))
        return issues

class JunkDetector:
    def detect(self, files: List[FileMetadata], config: Config) -> List[FileIssue]:
        issues = []
        known_os_junk = {".ds_store", "thumbs.db", "desktop.ini", "ehthumbs.db"}
        
        for f in files:
            name_lower = f.name.lower()
            is_junk = False
            reason = ""
            
            if f.extension in config.junk_extensions:
                is_junk = True
                reason = "Junk extension"
            elif f.is_in_known_junk_dir:
                is_junk = True
                reason = "In known junk directory"
            elif name_lower in known_os_junk:
                is_junk = True
                reason = "OS junk file"
            else:
                for pattern in config.junk_patterns:
                    if fnmatch.fnmatch(f.name, pattern) or fnmatch.fnmatch(name_lower, pattern):
                        is_junk = True
                        reason = "Matches junk pattern"
                        break
                        
            if is_junk:
                issues.append(FileIssue(
                    path=f.path,
                    category=IssueCategory.JUNK,
                    reason=reason,
                    size=f.size,
                    confidence=Confidence.HIGH,
                    source=IssueSource.RULE
                ))
        return issues

class OldFileDetector:
    def detect(self, files: List[FileMetadata], config: Config) -> List[FileIssue]:
        issues = []
        for f in files:
            if f.days_since_modified > config.old_file_days and f.days_since_accessed > config.old_file_days:
                min_days = min(f.days_since_modified, f.days_since_accessed)
                if min_days > config.old_file_days * 2:
                    conf = Confidence.HIGH
                else:
                    conf = Confidence.MEDIUM
                    
                issues.append(FileIssue(
                    path=f.path,
                    category=IssueCategory.OLD,
                    reason=f"Unused for {int(min_days)} days",
                    size=f.size,
                    confidence=conf,
                    source=IssueSource.RULE
                ))
        return issues

class LargeFileDetector:
    def detect(self, files: List[FileMetadata], config: Config) -> List[FileIssue]:
        issues = []
        gb = 1024 * 1024 * 1024
        mb500 = 500 * 1024 * 1024
        for f in files:
            if f.size > config.large_file_bytes:
                if f.size > gb:
                    conf = Confidence.HIGH
                elif f.size > mb500:
                    conf = Confidence.MEDIUM
                else:
                    conf = Confidence.LOW
                    
                issues.append(FileIssue(
                    path=f.path,
                    category=IssueCategory.LARGE,
                    reason="Large file",
                    size=f.size,
                    confidence=conf,
                    source=IssueSource.RULE
                ))
        return issues
