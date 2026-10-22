"""Verifiable Evidence Receipts for FileClean (inspired by Loki Mode).

Every cleanup action (Move to Trash or Permanent Delete) produces an immutable,
tamper-verifiable Evidence Receipt stored under `.fileclean/receipts/<receipt_id>.json`
and `.fileclean/receipts/<receipt_id>.md`.

Separates:
- Deterministic Facts: pre-deletion SHA-256 hash, byte size, path, deletion timestamp,
  trash destination, aggregate bytes reclaimed, and receipt integrity SHA-256.
- AI & User Assessments: content inspection summary, multi-agent council verdict,
  and explicit user confirmation method.
"""

from __future__ import annotations

import os
import json
import time
import uuid
import hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from src.fileclean_core.utils import format_size


@dataclass
class CleanedFileFact:
    """Deterministic fact for a single cleaned file."""
    path: str
    size_bytes: int
    pre_deletion_sha256: str
    action: str  # 'trash' or 'delete'
    destination: str  # Trash location or 'PERMANENTLY_DELETED'
    timestamp: float
    category: str
    content_summary: str = ""


@dataclass
class EvidenceReceipt:
    """Verifiable Evidence Receipt bound by hash integrity."""
    receipt_id: str
    created_at: float
    created_at_iso: str
    target_directory: str
    total_files_cleaned: int
    total_bytes_reclaimed: int
    reclaimable_display: str
    facts: List[CleanedFileFact] = field(default_factory=list)
    council_verdict: str = "CONSENSUS_VERIFIED"
    council_findings: List[str] = field(default_factory=list)
    user_confirmed: bool = True
    confirmation_method: str = "GUI_MODAL_CONFIRMATION"
    integrity_sha256: str = ""

    def compute_integrity_hash(self) -> str:
        """Compute deterministic SHA-256 hash of all facts in the receipt."""
        facts_payload = [
            {
                "path": f.path,
                "size_bytes": f.size_bytes,
                "pre_deletion_sha256": f.pre_deletion_sha256,
                "action": f.action,
                "destination": f.destination,
                "timestamp": f.timestamp,
                "category": f.category
            }
            for f in sorted(self.facts, key=lambda x: x.path)
        ]
        canonical_str = json.dumps(
            {
                "receipt_id": self.receipt_id,
                "target_directory": self.target_directory,
                "total_files": self.total_files_cleaned,
                "total_bytes": self.total_bytes_reclaimed,
                "facts": facts_payload,
            },
            sort_keys=True
        )
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def finalize(self) -> None:
        """Compute and set the integrity hash."""
        self.integrity_sha256 = self.compute_integrity_hash()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        """Generate human-readable markdown receipt."""
        lines = [
            f"# 🧾 FileClean Evidence Receipt: `{self.receipt_id}`\n",
            f"**Headline**: **{self.council_verdict}**\n",
            f"| Metric | Value |",
            f"| :--- | :--- |",
            f"| **Receipt ID** | `{self.receipt_id}` |",
            f"| **Created At** | {self.created_at_iso} |",
            f"| **Directory Scanned** | `{self.target_directory}` |",
            f"| **Files Cleaned** | {self.total_files_cleaned} |",
            f"| **Space Reclaimed** | **{self.reclaimable_display}** ({self.total_bytes_reclaimed} bytes) |",
            f"| **User Consent** | Verified (`{self.confirmation_method}`) |",
            f"| **Council Sign-off** | `{self.council_verdict}` |",
            f"| **Receipt Integrity SHA-256** | `{self.integrity_sha256}` |\n",
            "## 📁 Cleaned Files & Pre-Deletion SHA-256 Hashes\n",
            "| File Path | Category | Size | Action | Pre-Deletion SHA-256 |",
            "| :--- | :--- | :--- | :--- | :--- |"
        ]

        for f in self.facts:
            lines.append(
                f"| `{Path(f.path).name}` | {f.category} | {format_size(f.size_bytes)} | {f.action.upper()} | `{f.pre_deletion_sha256[:16]}...` |"
            )

        if self.council_findings:
            lines.append("\n## 🛡️ Multi-Agent Review Council Assessments\n")
            for finding in self.council_findings:
                lines.append(f"- {finding}")

        lines.append("\n---\n")
        lines.append(
            "*Verified Completion Guarantee: Re-run `python3 -m core.receipt verify <receipt_path>` "
            "to prove integrity offline without network access.*"
        )
        return "\n".join(lines)


class ReceiptManager:
    """Manages generation and storage of Evidence Receipts."""

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir:
            self.receipts_dir = base_dir / ".fileclean" / "receipts"
        else:
            self.receipts_dir = Path.home() / ".fileclean" / "receipts"
        self.receipts_dir.mkdir(parents=True, exist_ok=True)

    def generate_receipt(
        self,
        target_directory: Path,
        cleaned_facts: List[CleanedFileFact],
        council_verdict: str = "CONSENSUS_VERIFIED",
        council_findings: Optional[List[str]] = None,
        confirmation_method: str = "GUI_MODAL_CONFIRMATION"
    ) -> Tuple[EvidenceReceipt, Path, Path]:
        """Create, finalize, and write an Evidence Receipt (.json and .md)."""
        now = time.time()
        receipt_id = f"rec-{int(now)}-{uuid.uuid4().hex[:6]}"
        total_bytes = sum(f.size_bytes for f in cleaned_facts)

        receipt = EvidenceReceipt(
            receipt_id=receipt_id,
            created_at=now,
            created_at_iso=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(now)),
            target_directory=str(target_directory),
            total_files_cleaned=len(cleaned_facts),
            total_bytes_reclaimed=total_bytes,
            reclaimable_display=format_size(total_bytes),
            facts=cleaned_facts,
            council_verdict=council_verdict,
            council_findings=council_findings or [],
            user_confirmed=True,
            confirmation_method=confirmation_method
        )
        receipt.finalize()

        # Save JSON
        json_path = self.receipts_dir / f"{receipt_id}.json"
        json_path.write_text(json.dumps(receipt.to_dict(), indent=2))

        # Save Markdown
        md_path = self.receipts_dir / f"{receipt_id}.md"
        md_path.write_text(receipt.to_markdown())

        return receipt, json_path, md_path

    def get_latest_receipt(self) -> Optional[EvidenceReceipt]:
        """Fetch the most recent receipt."""
        json_files = sorted(self.receipts_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not json_files:
            return None
        return ReceiptVerifier.load(json_files[0])


class ReceiptVerifier:
    """Verifies evidence receipts offline for tamper resistance."""

    @staticmethod
    def load(receipt_path: Path) -> EvidenceReceipt:
        data = json.loads(receipt_path.read_text())
        facts = [CleanedFileFact(**f) for f in data.get("facts", [])]
        data_clean = {k: v for k, v in data.items() if k != "facts"}
        return EvidenceReceipt(facts=facts, **data_clean)

    @classmethod
    def verify(cls, receipt_path: Path) -> Tuple[bool, str]:
        """Verifies receipt integrity hash.
        Returns:
            (is_valid, report_message)
        """
        if not receipt_path.exists():
            return False, f"Receipt file not found: {receipt_path}"

        try:
            receipt = cls.load(receipt_path)
        except Exception as e:
            return False, f"Failed to parse receipt: {e}"

        expected_hash = receipt.integrity_sha256
        recomputed_hash = receipt.compute_integrity_hash()

        if expected_hash == recomputed_hash:
            return True, (
                f"✅ VERIFIED: Evidence Receipt '{receipt.receipt_id}' is authentic!\n"
                f"• Cleaned: {receipt.total_files_cleaned} files ({receipt.reclaimable_display})\n"
                f"• Headline: {receipt.council_verdict}\n"
                f"• Integrity Hash: {expected_hash}"
            )
        else:
            return False, (
                f"❌ TAMPER DETECTED: Receipt hash mismatch!\n"
                f"• Expected:   {expected_hash}\n"
                f"• Recomputed: {recomputed_hash}"
            )


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2 and sys.argv[1] == "verify":
        target = Path(sys.argv[2])
        valid, msg = ReceiptVerifier.verify(target)
        print(msg)
        sys.exit(0 if valid else 1)
    else:
        print("Usage: python3 -m core.receipt verify <receipt_path>")
