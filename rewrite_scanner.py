import re
with open('src/services/scanner.py', 'r') as f:
    content = f.read()

# We need to import AnalysisEngine and Config at the top
imports = """
from src.analyzer.engine import AnalysisEngine
from src.fileclean_core.config import Config
from pathlib import Path
"""
content = content.replace("from typing import List, Dict, Optional, Set, Callable, Any\n", "from typing import List, Dict, Optional, Set, Callable, Any\n" + imports)

# We need to modify FileScanner.__init__ to initialize AnalysisEngine
init_orig = """    def __init__(
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
        self._file_map: Dict[str, ScannedFileMetadata] = {}"""

init_new = """    def __init__(
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
"""
content = content.replace(init_orig, init_new)

with open('src/services/scanner.py', 'w') as f:
    f.write(content)
