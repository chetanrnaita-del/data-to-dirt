"""Autonomous Multi-Agent Review Council for FileClean (inspired by Loki Mode).

Provides an independent 3-agent review council that evaluates candidate files:
1. 🛡️ Security & Privacy Auditor: Detects credentials, private keys, database dumps, secrets, and system hooks.
2. 🏛️ Data Preservationist: Protects unique human work, historical notes, un-backed drafts, and creative writing.
3. 🗑️ Waste & Redundancy Inspector: Confirms exact SHA-256 twins, empty stubs, cache, and crash logs.

Enforces blind, independent voting with anti-sycophancy rules:
- Any high-confidence objection from Security or the Preservationist halts cleanup recommendation!
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from src.analyzer.models import FileIssue, IssueCategory, Confidence
from src.analyzer.content_inspector import ContentAnalysisResult
from src.analyzer.user_profile import UserProfile


class AgentVote(str, Enum):
    APPROVE_CLEANUP = "APPROVE_CLEANUP"
    PROTECT_FILE = "PROTECT_FILE"
    NEEDS_USER_REVIEW = "NEEDS_USER_REVIEW"


class CouncilVerdict(str, Enum):
    CONSENSUS_VERIFIED = "CONSENSUS_VERIFIED"
    VERIFIED_WITH_GAPS = "VERIFIED_WITH_GAPS"
    BLOCKED = "BLOCKED"


@dataclass
class ReviewerOpinion:
    agent_name: str
    vote: AgentVote
    confidence: float
    rationale: str


@dataclass
class CouncilEvaluation:
    issue: FileIssue
    verdict: CouncilVerdict
    opinions: List[ReviewerOpinion] = field(default_factory=list)
    consensus_summary: str = ""

    @property
    def is_approved_for_recommendation(self) -> bool:
        return self.verdict in (CouncilVerdict.CONSENSUS_VERIFIED, CouncilVerdict.VERIFIED_WITH_GAPS)


class SecurityAuditor:
    """Agent 1: Security & Privacy Auditor."""
    NAME = "Security & Privacy Auditor"

    SECRET_EXTENSIONS = {".key", ".pem", ".p12", ".pfx", ".kdbx", ".env", ".id_rsa", ".credentials"}
    SECRET_KEYWORDS = [r"password", r"secret", r"api[_-]?key", r"private[_-]?key", r"token", r"bearer", r"auth"]

    def evaluate(self, issue: FileIssue, content: ContentAnalysisResult) -> ReviewerOpinion:
        ext = issue.path.suffix.lower()
        name = issue.path.name.lower()

        # 1. Secret extensions
        if ext in self.SECRET_EXTENSIONS or name.startswith(".env"):
            return ReviewerOpinion(
                agent_name=self.NAME,
                vote=AgentVote.PROTECT_FILE,
                confidence=0.99,
                rationale=f"Security Risk: Filename or extension '{ext}' indicates sensitive credentials."
            )

        # 2. Sensitive content signals
        if content.is_readable and content.extracted_snippet:
            for pattern in self.SECRET_KEYWORDS:
                if re.search(pattern, content.extracted_snippet, re.IGNORECASE):
                    return ReviewerOpinion(
                        agent_name=self.NAME,
                        vote=AgentVote.PROTECT_FILE,
                        confidence=0.95,
                        rationale="Security Risk: Detected credential/secret pattern inside file content."
                    )

        # 3. Safe OS artifacts
        if issue.category == IssueCategory.DUPLICATE or issue.category == IssueCategory.JUNK:
            return ReviewerOpinion(
                agent_name=self.NAME,
                vote=AgentVote.APPROVE_CLEANUP,
                confidence=0.90,
                rationale="No sensitive credentials, tokens, or security vulnerabilities found."
            )

        return ReviewerOpinion(
            agent_name=self.NAME,
            vote=AgentVote.APPROVE_CLEANUP,
            confidence=0.80,
            rationale="File does not appear to contain security-critical data."
        )


class DataPreservationist:
    """Agent 2: Data Preservationist."""
    NAME = "Data Preservationist"

    PRESERVE_EXTENSIONS = {".docx", ".pdf", ".pages", ".xlsx", ".pptx", ".key", ".psd", ".sketch", ".fig"}

    def evaluate(self, issue: FileIssue, content: ContentAnalysisResult, profile: UserProfile) -> ReviewerOpinion:
        # Check 1: User profile protections
        is_prot, prot_reason = profile.evaluate_file_safety(issue.path)
        if is_prot:
            return ReviewerOpinion(
                agent_name=self.NAME,
                vote=AgentVote.PROTECT_FILE,
                confidence=0.98,
                rationale=f"Preservation Rule: {prot_reason}."
            )

        # Check 2: Byte Duplicate (original is safe)
        if issue.category == IssueCategory.DUPLICATE:
            return ReviewerOpinion(
                agent_name=self.NAME,
                vote=AgentVote.APPROVE_CLEANUP,
                confidence=0.95,
                rationale="Duplicate copy confirmed. The original master copy will remain safely preserved."
            )

        # Check 3: Valuable human work inside content
        if content.contains_valuable_signals:
            return ReviewerOpinion(
                agent_name=self.NAME,
                vote=AgentVote.PROTECT_FILE,
                confidence=0.95,
                rationale="Preservation Alert: Content contains contracts, receipts, or personal documents."
            )

        # Check 4: Substantive unique text documents
        if content.is_readable and content.words_count >= 15 and not content.is_auto_generated:
            return ReviewerOpinion(
                agent_name=self.NAME,
                vote=AgentVote.NEEDS_USER_REVIEW,
                confidence=0.75,
                rationale=f"Substantive prose ({content.words_count} words). May represent original thoughts or notes."
            )

        # Empty or auto-generated
        if content.is_empty or content.is_auto_generated or content.is_placeholder:
            return ReviewerOpinion(
                agent_name=self.NAME,
                vote=AgentVote.APPROVE_CLEANUP,
                confidence=0.90,
                rationale="Content is auto-generated or placeholder. No unique human creative work at risk."
            )

        return ReviewerOpinion(
            agent_name=self.NAME,
            vote=AgentVote.APPROVE_CLEANUP,
            confidence=0.70,
            rationale="No irreplaceable personal data detected."
        )


class WasteInspector:
    """Agent 3: Waste & Redundancy Inspector."""
    NAME = "Waste & Redundancy Inspector"

    def evaluate(self, issue: FileIssue, content: ContentAnalysisResult) -> ReviewerOpinion:
        # 1. Exact byte duplicates
        if issue.category == IssueCategory.DUPLICATE:
            return ReviewerOpinion(
                agent_name=self.NAME,
                vote=AgentVote.APPROVE_CLEANUP,
                confidence=0.99,
                rationale="100% byte redundancy: identical SHA-256 match with another file in the folder."
            )

        # 2. Auto-generated junk or empty files
        if content.is_auto_generated or content.is_empty:
            return ReviewerOpinion(
                agent_name=self.NAME,
                vote=AgentVote.APPROVE_CLEANUP,
                confidence=0.95,
                rationale=f"Zero utility: {content.content_summary}."
            )

        # 3. Known junk categories (.tmp, .DS_Store, cache)
        if issue.category == IssueCategory.JUNK:
            return ReviewerOpinion(
                agent_name=self.NAME,
                vote=AgentVote.APPROVE_CLEANUP,
                confidence=0.90,
                rationale="Transient OS cache or temporary scratch file."
            )

        # 4. Large or old file with substantive content
        if issue.category in (IssueCategory.LARGE, IssueCategory.OLD):
            return ReviewerOpinion(
                agent_name=self.NAME,
                vote=AgentVote.NEEDS_USER_REVIEW,
                confidence=0.65,
                rationale=f"Stale resource consuming {issue.size_display}. Suitable for reclamation upon user review."
            )

        return ReviewerOpinion(
            agent_name=self.NAME,
            vote=AgentVote.APPROVE_CLEANUP,
            confidence=0.70,
            rationale="Candidate resource identified for disk optimization."
        )


class ReviewCouncil:
    """Orchestrates independent review and anti-sycophancy consensus."""

    def __init__(self):
        self.security = SecurityAuditor()
        self.preservationist = DataPreservationist()
        self.waste = WasteInspector()

    def evaluate_candidate(
        self,
        issue: FileIssue,
        content: ContentAnalysisResult,
        profile: UserProfile
    ) -> CouncilEvaluation:
        # Collect blind independent opinions
        op1 = self.security.evaluate(issue, content)
        op2 = self.preservationist.evaluate(issue, content, profile)
        op3 = self.waste.evaluate(issue, content)
        opinions = [op1, op2, op3]

        # Anti-sycophancy check: Did Security or Preservationist object?
        for op in [op1, op2]:
            if op.vote == AgentVote.PROTECT_FILE and op.confidence >= 0.70:
                return CouncilEvaluation(
                    issue=issue,
                    verdict=CouncilVerdict.BLOCKED,
                    opinions=opinions,
                    consensus_summary=f"BLOCKED by {op.agent_name}: {op.rationale}"
                )

        # Count approvals
        approve_count = sum(1 for op in opinions if op.vote == AgentVote.APPROVE_CLEANUP)
        review_count = sum(1 for op in opinions if op.vote == AgentVote.NEEDS_USER_REVIEW)

        if approve_count == 3:
            verdict = CouncilVerdict.CONSENSUS_VERIFIED
            summary = "Unanimous Council consensus (3/3): Confirmed safe for cleanup."
        elif approve_count >= 2:
            verdict = CouncilVerdict.VERIFIED_WITH_GAPS
            summary = f"Majority Council approval ({approve_count}/3): Recommended with advisory review."
        else:
            verdict = CouncilVerdict.BLOCKED
            summary = "Council failed to achieve consensus: Recommended to keep safe."

        return CouncilEvaluation(
            issue=issue,
            verdict=verdict,
            opinions=opinions,
            consensus_summary=summary
        )
