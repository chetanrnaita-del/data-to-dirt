from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

from src.analyzer.models import ScanResult, FileIssue, IssueCategory, Confidence
from src.analyzer.features import extract_batch, extract_metadata
from src.analyzer.rules import DuplicateFinder, JunkDetector, OldFileDetector, LargeFileDetector
from src.analyzer.classifier import FileClassifier
from src.analyzer.explainer import FileExplainer
from src.analyzer.content_inspector import ContentInspector
from src.analyzer.user_profile import UserProfile
from src.analyzer.council import ReviewCouncil
from src.fileclean_core.config import Config
from src.fileclean_core.platform import is_system_dir
from src.security.sandbox import PathSandbox, OperationType, AccessDecision
from src.security.sanitizer import validate_scan_request, ValidationError

class AnalysisEngine:
    def __init__(self, config: Config, user_profile: Optional[UserProfile] = None):
        self.config = config
        self.classifier = FileClassifier(Path(config.classifier_path) if config.classifier_path else None)
        self.explainer = FileExplainer(Path(config.ai_model_path) if config.ai_model_path else None)
        self.sandbox = PathSandbox()
        self.content_inspector = ContentInspector()
        self.user_profile = user_profile or UserProfile()
        self.council = ReviewCouncil()
        
        self.rule_detectors = [
            DuplicateFinder(),
            JunkDetector(),
            OldFileDetector(),
            LargeFileDetector()
        ]

    def scan(self, directory: Path, progress_callback: Optional[Callable] = None) -> ScanResult:
        start_time = time.time()
        
        # Security: Validate and sanitize the scan directory
        # Propagate ValidationError so invalid/unreadable scan requests are not silently treated as empty folders
        directory = validate_scan_request(str(directory))
        
        # Security: Authorize this directory as a scan root in the sandbox
        self.sandbox.authorize_scan_root(directory)
        self.sandbox.reset_session_limits()
        
        all_files = []
        
        if progress_callback:
            progress_callback(0, 0, "Discovering files...")
            
        def walk_dir(path: Path, current_depth: int):
            if self.config.max_scan_depth is not None and current_depth > self.config.max_scan_depth:
                return
            if is_system_dir(path):
                return
                
            try:
                for item in path.iterdir():
                    if self.config.skip_hidden and item.name.startswith("."):
                        continue
                        
                    if item.is_dir():
                        if not item.is_symlink():
                            walk_dir(item, current_depth + 1)
                    elif item.is_file():
                        all_files.append(item)
            except (PermissionError, FileNotFoundError) as exc:
                if current_depth == 0:
                    raise PermissionError(f"Cannot read directory '{path}': {exc}") from exc
                pass
                
        walk_dir(directory, 0)
        
        total_files = len(all_files)
        
        if progress_callback:
            progress_callback(0, total_files, "Extracting features...")
            
        metadata_list = []
        for i, file_path in enumerate(all_files):
            meta = extract_metadata(directory, file_path, self.config)
            if meta:
                metadata_list.append(meta)
            if progress_callback and i % 100 == 0:
                progress_callback(i, total_files, "Extracting features...")
                
        if progress_callback:
            progress_callback(total_files, total_files, "Running rule detectors...")
            
        issues = []
        for detector in self.rule_detectors:
            issues.extend(detector.detect(metadata_list, self.config))
            
        if self.config.enable_ai and self.classifier.is_available():
            if progress_callback:
                progress_callback(total_files, total_files, "Running ML classifier...")
            ml_issues = self.classifier.predict(metadata_list)
            issues.extend(ml_issues)
            
        # Deduplicate issues: group by path, keep highest confidence
        issue_map = {}
        for issue in issues:
            existing = issue_map.get(issue.path)
            if existing:
                conf_val = {"high": 3, "medium": 2, "low": 1}
                if conf_val.get(issue.confidence.value, 0) > conf_val.get(existing.confidence.value, 0):
                    issue_map[issue.path] = issue
            else:
                issue_map[issue.path] = issue
                
        candidate_issues = list(issue_map.values())
        
        # Step 4: Look INSIDE files & Apply Learned User Preferences
        # ONLY recommend files when content confirms disposable status and user habits do not protect it
        if progress_callback:
            progress_callback(total_files, total_files, "Inspecting file contents & verifying user habits...")

        final_issues = []
        for issue in candidate_issues:
            # 1. User Profile & Learned Habit Check
            is_protected, prot_reason = self.user_profile.evaluate_file_safety(issue.path)
            if is_protected:
                # User habits or explicit rules protect this file -> Suppress recommendation!
                continue

            # 2. Deep Content Inspection
            content_info = self.content_inspector.inspect(issue.path)

            # Never recommend deleting non-duplicate files with personal, sensitive, or valuable content
            if content_info.contains_valuable_signals and issue.category != IssueCategory.DUPLICATE:
                continue

            # 3. Multi-Agent Review Council Evaluation (Security, Preservationist, Waste)
            council_eval = self.council.evaluate_candidate(issue, content_info, self.user_profile)
            if not council_eval.is_approved_for_recommendation:
                # Objections from Security Auditor or Data Preservationist
                continue

            # Verified byte duplicates (SHA-256)
            if issue.category == IssueCategory.DUPLICATE:
                final_issues.append(issue)
                continue

            # If content reveals auto-generated logs, crash dumps, stubs, or placeholders
            if content_info.is_auto_generated or content_info.is_placeholder or content_info.is_empty:
                if content_info.disposable_reasons:
                    issue.reason = f"{issue.reason} (Content: {content_info.disposable_reasons[0]})"
                final_issues.append(issue)
            elif issue.category in (IssueCategory.JUNK, IssueCategory.LARGE, IssueCategory.OLD):
                final_issues.append(issue)
            elif issue.category == IssueCategory.AI_SUGGESTION:
                if content_info.disposable_confidence >= 0.50:
                    final_issues.append(issue)
        
        if self.config.enable_ai:
            if progress_callback:
                progress_callback(total_files, total_files, "Generating AI explanations...")
            for issue in final_issues:
                meta = next((m for m in metadata_list if m.path == issue.path), None)
                if meta:
                    issue.ai_explanation = self.explainer.explain(
                        meta,
                        issue.category.value,
                        original_path=issue.original_path,
                        reason=issue.reason
                    )
                        
        end_time = time.time()
        
        total_size = sum(m.size for m in metadata_list)
        
        return ScanResult(
            directory=directory,
            total_files=len(metadata_list),
            total_size=total_size,
            issues=final_issues,
            scan_duration=end_time - start_time,
            ai_enabled=self.config.enable_ai
        )
