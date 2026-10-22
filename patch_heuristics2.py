import re
with open('src/services/scanner.py', 'r') as f:
    content = f.read()

heuristics_current = '''    def _apply_dark_data_heuristics(
        self,
        items: List[ScannedFileMetadata],
        files_by_size: Dict[int, List[ScannedFileMetadata]],
        current_time: float,
    ) -> None:
        """Classify files using the advanced AnalysisEngine."""
        
        # We need the base directory to run the AnalysisEngine
        if not self._active_path:
            return
            
        try:
            # 1. Run the deep analysis engine
            scan_result = self.analysis_engine.scan(Path(self._active_path))
            
            # 2. Map issues to files by absolute path
            issues_by_path = {}
            for issue in scan_result.issues:
                path_str = str(issue.path)
                if path_str not in issues_by_path:
                    issues_by_path[path_str] = []
                issues_by_path[path_str].append(issue)
                
            # 3. Apply the advanced heuristics to our items
            for item in items:
                path_str = item.absolute_path
                if path_str in issues_by_path:
                    issues = issues_by_path[path_str]
                    
                    reasons = []
                    for issue in issues:
                        reason = f"{issue.category.value.title()}: {issue.reason}"
                        if issue.confidence.value != "low":
                            reason += f" [{issue.confidence.value.upper()} conf]"
                        if issue.ai_explanation:
                            reason += f" - AI says: {issue.ai_explanation}"
                        reasons.append(reason)
                        
                    if reasons:
                        item.is_dark_data_candidate = True
                        item.dark_data_reason = " | ".join(reasons)
                        
        except Exception as e:
            print(f"AnalysisEngine failed, falling back: {e}")
            # Simple fallback if the engine fails
            for item in items:
                reasons = []
                if item.size_bytes >= self._heavy_threshold_bytes:
                    reasons.append("Heavy file bloat")
                if reasons:
                    item.is_dark_data_candidate = True
                    item.dark_data_reason = " | ".join(reasons)'''

heuristics_hybrid = '''    def _apply_dark_data_heuristics(
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
            print(f"AnalysisEngine failed, using basic rules only: {e}")'''

content = content.replace(heuristics_current, heuristics_hybrid)
with open('src/services/scanner.py', 'w') as f:
    f.write(content)

