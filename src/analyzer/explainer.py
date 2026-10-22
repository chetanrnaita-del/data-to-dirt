from __future__ import annotations

from pathlib import Path
from typing import List, Tuple, Optional

from src.analyzer.models import FileMetadata
from src.analyzer.content_inspector import ContentInspector
from src.fileclean_core.utils import format_size


class FileExplainer:
    """Intelligent on-ground file explainer with deep content inspection fallback."""

    def __init__(self, model_path: Path | None = None):
        if model_path is None:
            base_dir = Path(__file__).resolve().parent.parent
            candidates = [
                base_dir / "models" / "explainer.gguf",
                base_dir / "training" / "models" / "explainer.gguf",
            ]
            for candidate in candidates:
                if candidate.exists():
                    model_path = candidate
                    break

        self.model_path = model_path
        self.llm = None
        self.inspector = ContentInspector()

        if self.is_available():
            try:
                from llama_cpp import Llama
                self.llm = Llama(model_path=str(self.model_path), verbose=False)
            except Exception:
                pass

    def is_available(self) -> bool:
        return self.model_path is not None and self.model_path.exists()

    def explain(
        self,
        metadata: FileMetadata,
        category: str,
        original_path: Optional[Path] = None,
        reason: str = ""
    ) -> str:
        """Generate a contextual explanation for why a file was flagged."""
        # 1. Try local GGUF model if present
        if self.is_available() and self.llm:
            try:
                prompt = f"""<|system|>
You are an expert file analyst. Explain concisely (1-3 sentences) why the user might want to review or delete this file.
<|user|>
File: {metadata.name}
Path: {metadata.path}
Category: {category}
Size: {metadata.size} bytes
Days unused: {metadata.days_since_accessed:.1f}
<|assistant|>"""
                response = self.llm(prompt, max_tokens=100, stop=["<|user|>"])
                return response["choices"][0]["text"].strip()
            except Exception:
                pass

        # 2. Ground-Truth Contextual Analysis
        return self._ground_explanation(metadata, category, original_path, reason)

    def explain_batch(self, items: List[Tuple[FileMetadata, str]]) -> List[str]:
        return [self.explain(meta, cat) for meta, cat in items]

    def _ground_explanation(
        self,
        metadata: FileMetadata,
        category: str,
        original_path: Optional[Path] = None,
        reason: str = ""
    ) -> str:
        """Synthesize a unique, content-grounded explanation from actual filesystem facts."""
        cat_lower = category.lower()

        if cat_lower == "duplicate":
            if original_path:
                return (
                    f"Exact SHA-256 byte-for-byte twin of `{original_path.name}`. "
                    f"Removing this clone frees {format_size(metadata.size)} while preserving your master copy untouched."
                )
            return (
                f"Exact cryptographic duplicate sharing identical SHA-256 content with another file on disk. "
                f"Safe to remove because one master copy remains safe."
            )

        if cat_lower == "junk":
            content = self.inspector.inspect(metadata.path)
            if content.is_empty:
                return f"Zero-byte empty file ({metadata.extension or 'no extension'}) with no stored data. 100% safe to remove."
            if content.is_auto_generated:
                reasons = ", ".join(content.disposable_reasons) or "runtime dump"
                return f"Auto-generated artifact ({reasons}). Safe to clear."
            if metadata.extension.lower() in (".tmp", ".temp"):
                return f"Abandoned temporary cache ({format_size(metadata.size)}) left behind after previous app sessions."
            if metadata.name.lower() == ".ds_store":
                return "macOS Finder folder view metadata. Safe to delete; macOS recreates defaults automatically."
            if metadata.extension.lower() in (".pyc", ".pyo"):
                return "Compiled Python bytecode. Python will recompile fresh bytecode on your next script execution."
            return f"System or app junk ({metadata.extension}). Safe to clean up without affecting your personal documents."

        if cat_lower == "old":
            days = int(metadata.days_since_accessed)
            return (
                f"Untouched on disk for over {days} days (in `{metadata.path.parent.name}/`). "
                f"Review to archive or delete if no longer required."
            )

        if cat_lower == "large":
            size_str = format_size(metadata.size)
            return (
                f"Heavy disk consumer taking {size_str} ({metadata.mime_category or metadata.extension}). "
                f"Cleaning or archiving this single file provides significant space relief."
            )

        if cat_lower == "ai_suggestion":
            return (
                f"Review Council flagged this file as redundant ({reason or 'low affinity pattern'}). "
                f"Safe to review and clean."
            )

        return f"Flagged for review based on {reason or 'heuristic inspection'}."
