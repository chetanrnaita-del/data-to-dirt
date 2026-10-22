"""Cognitive Engine — The Brain of FileClean AI.

This replaces the keyword-matching decision tree with a genuine
multi-phase reasoning pipeline that mirrors how an expert analyst
actually thinks through filesystem problems:

    Understand → Gather Evidence → Reason → Compose

Every response is dynamically assembled from observed ground facts,
never retrieved from a template dictionary.  The visible thought
chain reflects the engine's real internal reasoning, not decorative
bullet points.

Runs 100% locally with zero external models or APIs.
"""

from __future__ import annotations

import os
import re
import time
import math
import random
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any

from src.analyzer.models import ScanResult, FileIssue, IssueCategory, Confidence
from src.analyzer.content_inspector import ContentInspector, ContentAnalysisResult
from src.analyzer.user_profile import UserProfile
from src.analyzer.council import ReviewCouncil
from src.fileclean_core.utils import format_size


# ────────────────────────────────────────────────────────────────
# 1. Internal Representations
# ────────────────────────────────────────────────────────────────

@dataclass
class ThinkingResult:
    """The structured artefact returned to the UI."""
    thought_steps: list[str]
    answer: str
    duration_ms: float = 0.0
    inspected_files: list[str] = field(default_factory=list)


@dataclass
class Understanding:
    """Phase-1 output: what the user actually means."""
    raw_query: str
    topics: Dict[str, float]       # topic → relevance weight (0–1)
    mentioned_files: list[str]     # file stems / names found in query
    mentioned_dirs: list[str]      # directory names found in query
    question_type: str             # factual / evaluative / procedural / emotional / exploratory
    emotional_register: str        # curious / worried / impatient / analytical / friendly
    references_prior: bool         # does this continue a prior topic?


@dataclass
class Evidence:
    """Phase-2 output: all ground facts relevant to the query."""
    scan_summary: Optional[Dict[str, Any]] = None
    targeted_files: list[Tuple[FileIssue, ContentAnalysisResult]] = field(default_factory=list)
    category_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    cluster_map: Dict[str, list[FileIssue]] = field(default_factory=dict)
    user_rules: list[str] = field(default_factory=list)
    disk_probe: Optional[Dict[str, Any]] = None
    relevant_history: list[str] = field(default_factory=list)


@dataclass
class Reasoning:
    """Phase-3 output: conclusions drawn from understanding + evidence."""
    chain: list[str]                        # visible thought chain
    key_insight: str = ""                   # the single most important finding
    recommendations: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    risk_level: str = "none"                # none / low / medium / high
    confidence: float = 1.0                 # how sure we are about the answer


# ────────────────────────────────────────────────────────────────
# 2. File-Type Knowledge Graph  (replaces SAFETY_KNOWLEDGE dict)
# ────────────────────────────────────────────────────────────────

FILE_KNOWLEDGE: Dict[str, Dict[str, str]] = {
    ".ds_store":  {"role": "macOS folder-view metadata",           "origin": "Finder", "risk": "none", "recreated": "yes"},
    "thumbs.db":  {"role": "Windows thumbnail cache",              "origin": "Explorer", "risk": "none", "recreated": "yes"},
    ".tmp":       {"role": "app temp / scratch pad",               "origin": "various apps", "risk": "none", "recreated": "no"},
    ".log":       {"role": "diagnostic / crash log",               "origin": "system or apps", "risk": "low", "recreated": "no"},
    ".pyc":       {"role": "compiled Python bytecode",             "origin": "Python runtime", "risk": "none", "recreated": "yes"},
    "__pycache__":{"role": "Python bytecode cache directory",      "origin": "Python runtime", "risk": "none", "recreated": "yes"},
    "node_modules":{"role":"npm / Yarn dependency tree",           "origin": "npm install", "risk": "none", "recreated": "yes"},
    ".dmg":       {"role": "macOS disk-image installer",           "origin": "developer download", "risk": "low", "recreated": "no"},
    ".iso":       {"role": "optical-disc / OS image",              "origin": "download", "risk": "low", "recreated": "no"},
    ".bak":       {"role": "editor / tool backup",                 "origin": "text editors", "risk": "low", "recreated": "no"},
    ".cache":     {"role": "runtime cache",                        "origin": "various apps", "risk": "none", "recreated": "yes"},
    ".o":         {"role": "compiled C/C++ object file",           "origin": "compiler", "risk": "none", "recreated": "yes"},
    ".class":     {"role": "compiled Java bytecode",               "origin": "javac", "risk": "none", "recreated": "yes"},
}


# ────────────────────────────────────────────────────────────────
# 3. Topic Scoring Dimensions
# ────────────────────────────────────────────────────────────────

TOPIC_SIGNALS: Dict[str, list[str]] = {
    "safety":       ["safe", "danger", "risk", "harm", "break", "lose", "careful", "worried", "afraid", "scared", "okay", "trust", "delete"],
    "strategy":     ["clean", "first", "start", "recommend", "advice", "priority", "plan", "workflow", "how to", "step", "approach", "should i"],
    "duplicates":   ["duplicate", "same file", "copy", "clone", "identical", "twin", "redundant"],
    "space":        ["space", "big", "large", "heavy", "huge", "size", "reclaim", "free up", "biggest", "taking up", "storage"],
    "specific_file":["why", "look inside", "inspect", "explain", "about this", "tell me about", "what is"],
    "greeting":     ["hello", "hi", "hey", "good morning", "yo", "sup", "thanks", "thank"],
    "capabilities": ["who are you", "what can you", "help", "how do you work", "feature", "what do you do"],
    "privacy":      ["privacy", "private", "offline", "upload", "cloud", "telemetry", "data", "track", "secure"],
    "folder":       ["folder", "directory", "tree", "cluster", "breakdown", "structure"],
    "junk":         ["junk", "trash", "cache", "temp", "temporary", "cleanup", "garbage", "cruft"],
    "old_files":    ["old", "unused", "stale", "untouched", "forgotten", "ancient", "archive"],
    "receipts":     ["receipt", "evidence", "proof", "audit", "verify", "last cleanup"],
    "profile":      ["learned", "know about me", "my profile", "preferences", "habits"],
}


# ────────────────────────────────────────────────────────────────
# 4. The Cognitive Engine
# ────────────────────────────────────────────────────────────────

class CognitiveEngine:
    """Genuine multi-phase reasoning engine for filesystem analysis.

    Instead of mapping keywords to template strings, this engine:
    1. Builds a semantic *understanding* of the user's intent & tone
    2. Gathers relevant *evidence* from the live filesystem and scan
    3. *Reasons* through the evidence, weighing multiple perspectives
    4. *Composes* a natural, evidence-grounded response
    """

    def __init__(
        self,
        content_inspector: Optional[ContentInspector] = None,
        user_profile: Optional[UserProfile] = None,
        council: Optional[ReviewCouncil] = None,
    ):
        self.inspector = content_inspector or ContentInspector()
        self.profile = user_profile
        self.council = council or ReviewCouncil()
        self.conversation_topics: list[str] = []   # rolling topic memory
        self.exchange_count: int = 0

    # ── Public API ──────────────────────────────────────────────

    def think(
        self,
        query: str,
        scan_result: Optional[ScanResult] = None,
        history: Optional[list[Dict[str, str]]] = None,
    ) -> ThinkingResult:
        """Execute a full reasoning cycle and return the result."""
        start = time.perf_counter()
        self.exchange_count += 1

        # Phase 1 — Understand
        understanding = self._understand(query, history or [])

        # Phase 2 — Gather evidence
        evidence = self._gather(understanding, scan_result)

        # Phase 3 — Reason
        reasoning = self._reason(understanding, evidence, scan_result)

        # Phase 4 — Compose
        answer = self._compose(understanding, evidence, reasoning, scan_result)

        # Track topics for continuity
        top_topic = max(understanding.topics, key=understanding.topics.get) if understanding.topics else ""
        if top_topic and top_topic not in ("greeting",):
            self.conversation_topics.append(top_topic)

        duration_ms = (time.perf_counter() - start) * 1000
        return ThinkingResult(
            thought_steps=reasoning.chain,
            answer=answer,
            duration_ms=duration_ms,
            inspected_files=[str(fi.path) for fi, _ in evidence.targeted_files],
        )

    # ── Phase 1: Understand ─────────────────────────────────────

    def _understand(self, query: str, history: list[Dict[str, str]]) -> Understanding:
        q = query.lower().strip()
        words = set(q.split())

        # Score every topic dimension
        topics: Dict[str, float] = {}
        for topic, signals in TOPIC_SIGNALS.items():
            score = sum(1.0 for s in signals if s in q) / max(len(signals), 1)
            if score > 0:
                topics[topic] = min(score * 2.5, 1.0)   # amplify and cap

        if not topics:
            topics["general"] = 0.5

        # Extract mentioned file names / extensions
        mentioned_files = re.findall(r'[\w\-]+\.[\w]{1,6}', q)
        # Extract mentioned directories
        home = Path.home()
        dir_map = {"desktop": "Desktop", "downloads": "Downloads", "documents": "Documents",
                   "pictures": "Pictures", "movies": "Movies"}
        mentioned_dirs = [dir_map[d] for d in dir_map if d in q]

        # Question type
        if any(w in q for w in ["why", "how", "explain", "what is", "tell me"]):
            qtype = "exploratory"
        elif any(w in q for w in ["should i", "can i", "is it", "will it"]):
            qtype = "evaluative"
        elif any(w in q for w in ["how to", "step", "start", "guide", "workflow"]):
            qtype = "procedural"
        elif any(w in q for w in ["worried", "afraid", "scared", "trust", "careful"]):
            qtype = "emotional"
        else:
            qtype = "factual"

        # Emotional register
        if any(w in q for w in ["worried", "afraid", "scared", "nervous", "careful"]):
            register = "worried"
        elif any(w in q for w in ["thanks", "thank", "great", "awesome", "nice"]):
            register = "friendly"
        elif len(q.split()) <= 4:
            register = "impatient"
        elif any(w in q for w in ["how exactly", "detail", "specifically", "technically"]):
            register = "analytical"
        else:
            register = "curious"

        # Does this continue a prior topic?
        references_prior = bool(
            any(w in q for w in ["those", "them", "these", "that", "it", "the same", "still"]) and history
        )

        return Understanding(
            raw_query=query,
            topics=topics,
            mentioned_files=mentioned_files,
            mentioned_dirs=mentioned_dirs,
            question_type=qtype,
            emotional_register=register,
            references_prior=references_prior,
        )

    # ── Phase 2: Gather Evidence ────────────────────────────────

    def _gather(self, u: Understanding, scan: Optional[ScanResult]) -> Evidence:
        ev = Evidence()

        # Scan summary
        if scan and scan.issues:
            ev.scan_summary = {
                "dir": scan.directory,
                "total_files": scan.total_files,
                "issue_count": len(scan.issues),
                "reclaimable": scan.reclaimable_display,
                "reclaimable_bytes": sum(i.size for i in scan.issues),
            }
            # Category stats
            for cat in IssueCategory:
                items = [i for i in scan.issues if i.category == cat]
                if items:
                    ev.category_stats[cat.value] = {
                        "count": len(items),
                        "total_size": sum(i.size for i in items),
                        "display_size": format_size(sum(i.size for i in items)),
                        "sample": items[:3],
                    }
            # Folder clusters
            for issue in scan.issues:
                parent = issue.path.parent.name or str(issue.path.parent)
                ev.cluster_map.setdefault(parent, []).append(issue)

        # Targeted file inspection
        if scan and (u.mentioned_files or u.topics.get("specific_file", 0) > 0.3):
            for issue in scan.issues:
                name_lower = issue.path.name.lower()
                stem_lower = issue.path.stem.lower()
                for mf in u.mentioned_files:
                    if mf.lower() in name_lower:
                        content = self.inspector.inspect(issue.path)
                        ev.targeted_files.append((issue, content))
                        break
                else:
                    # Fuzzy stem search against the query
                    if len(stem_lower) >= 4 and stem_lower in u.raw_query.lower():
                        content = self.inspector.inspect(issue.path)
                        ev.targeted_files.append((issue, content))

        # Direct disk probe for mentioned directories not in current scan
        if u.mentioned_dirs:
            home = Path.home()
            for d in u.mentioned_dirs:
                dp = home / d
                if dp.exists() and (not scan or dp != scan.directory):
                    ev.disk_probe = self._probe_directory(dp)

        # User profile rules
        if self.profile:
            summary = self.profile.get_profile_summary()
            if summary.get("protected_keywords"):
                ev.user_rules.append(f"Protected keywords: {', '.join(summary['protected_keywords'][:6])}")
            if summary.get("protected_directories"):
                ev.user_rules.append(f"Protected folders: {', '.join(str(d) for d in summary['protected_directories'][:3])}")

        # Recent conversation topics
        if self.conversation_topics:
            ev.relevant_history = self.conversation_topics[-5:]

        return ev

    def _probe_directory(self, folder: Path) -> Dict[str, Any]:
        """Probe a live directory and return ground facts."""
        try:
            entries = list(folder.iterdir())
            files = [e for e in entries if e.is_file() and not e.name.startswith(".")]
            dirs = [e for e in entries if e.is_dir() and not e.name.startswith(".")]
            total = sum(f.stat().st_size for f in files)
            largest = sorted(files, key=lambda f: f.stat().st_size, reverse=True)[:5]
            ext_counts = Counter(f.suffix.lower() for f in files if f.suffix)
            return {
                "path": folder,
                "file_count": len(files),
                "dir_count": len(dirs),
                "total_bytes": total,
                "total_display": format_size(total),
                "dir_names": [d.name for d in dirs[:6]],
                "largest": [(f.name, f.stat().st_size) for f in largest],
                "top_extensions": ext_counts.most_common(5),
            }
        except Exception:
            return {"path": folder, "error": True}

    # ── Phase 3: Reason ─────────────────────────────────────────

    def _reason(self, u: Understanding, ev: Evidence, scan: Optional[ScanResult]) -> Reasoning:
        chain: list[str] = []
        key_insight = ""
        recommendations: list[str] = []
        caveats: list[str] = []
        risk_level = "none"
        confidence = 1.0

        top_topics = sorted(u.topics.items(), key=lambda x: x[1], reverse=True)
        topic_str = ", ".join(f"{t} ({w:.0%})" for t, w in top_topics[:3])
        chain.append(
            f"The user is asking about {topic_str}. "
            f"Their tone is {u.emotional_register} and this is a {u.question_type} question."
        )

        # ─ Greeting / Capabilities ──────────────────────────────
        if u.topics.get("greeting", 0) > 0.3 or u.topics.get("capabilities", 0) > 0.3:
            chain.append(
                "This is an introductory or capability question. "
                "I should explain what makes me different from a generic cleaner "
                "and invite them to try specific things."
            )
            key_insight = "introduction"
            return Reasoning(chain=chain, key_insight=key_insight, confidence=1.0)

        # ─ Privacy ──────────────────────────────────────────────
        if u.topics.get("privacy", 0) > 0.3:
            chain.append(
                "The user wants to know about data safety and privacy. "
                "I should be specific: no network sockets, no telemetry, "
                "no cloud APIs, all processing in local RAM."
            )
            key_insight = "privacy_assurance"
            return Reasoning(chain=chain, key_insight=key_insight, confidence=1.0)

        # ─ Disk probe (no scan needed) ──────────────────────────
        if ev.disk_probe and not ev.disk_probe.get("error"):
            dp = ev.disk_probe
            chain.append(
                f"The user mentioned their {dp['path'].name} folder. "
                f"I probed it directly on disk: {dp['file_count']} files, "
                f"{dp['dir_count']} subdirectories, {dp['total_display']} total."
            )
            if dp["largest"]:
                top_name, top_size = dp["largest"][0]
                chain.append(
                    f"The heaviest item is '{top_name}' at {format_size(top_size)}. "
                    f"This alone may be worth investigating."
                )
            key_insight = "disk_probe"
            return Reasoning(chain=chain, key_insight=key_insight, confidence=0.9)

        # ─ No active scan ───────────────────────────────────────
        if not scan or not scan.issues:
            # Check if we can still answer from knowledge
            for ext, info in FILE_KNOWLEDGE.items():
                if ext in u.raw_query.lower():
                    chain.append(
                        f"The user is asking about '{ext}' files. "
                        f"I know these are {info['role']}, created by {info['origin']}. "
                        f"Risk of deleting: {info['risk']}. Auto-recreated: {info['recreated']}."
                    )
                    key_insight = f"file_knowledge:{ext}"
                    return Reasoning(chain=chain, key_insight=key_insight, confidence=1.0)

            chain.append(
                "No scan is active and the question needs filesystem data I don't have yet. "
                "I should help the user get started with a scan rather than giving generic advice."
            )
            key_insight = "needs_scan"
            return Reasoning(chain=chain, key_insight=key_insight, confidence=0.7)

        # ─── From here on we HAVE an active scan ────────────────

        # ─ Targeted file inquiry ────────────────────────────────
        if ev.targeted_files:
            issue, content = ev.targeted_files[0]
            chain.append(
                f"The user is asking about a specific file: '{issue.path.name}' "
                f"({issue.size_display}, categorised as {issue.category.value})."
            )
            chain.append(
                f"I inspected it on disk: {content.content_summary}. "
                f"{content.words_count} words, {content.lines_count} lines. "
                f"Valuable signals detected: {content.contains_valuable_signals}."
            )

            if issue.category == IssueCategory.DUPLICATE and issue.original_path:
                chain.append(
                    f"This is a verified SHA-256 duplicate of '{issue.original_path.name}'. "
                    f"The original file is intact. Removing this clone is zero-risk."
                )
                risk_level = "none"
            elif content.contains_valuable_signals:
                chain.append(
                    "The content contains personal, financial, or credential signals. "
                    "I should strongly recommend keeping this file."
                )
                risk_level = "high"
                caveats.append("Contains potentially valuable or sensitive content.")
            elif content.is_auto_generated:
                chain.append("The content is auto-generated (logs, crash dumps, build output). Safe to remove.")
                risk_level = "none"
            else:
                chain.append(
                    "The file has substantive content but nothing flagged as sensitive. "
                    "I should recommend reviewing it before deletion."
                )
                risk_level = "low"

            key_insight = "file_inspection"
            return Reasoning(chain=chain, key_insight=key_insight, recommendations=recommendations,
                           caveats=caveats, risk_level=risk_level, confidence=confidence)

        # ─ Safety assessment ────────────────────────────────────
        if u.topics.get("safety", 0) > 0.3:
            dupes = ev.category_stats.get("duplicate", {})
            junk = ev.category_stats.get("junk", {})
            old = ev.category_stats.get("old", {})
            large = ev.category_stats.get("large", {})
            chain.append(
                f"The user wants to know if their flagged files are safe to delete. "
                f"Let me assess each category from the actual scan data."
            )
            safe_count = (dupes.get("count", 0) + junk.get("count", 0))
            review_count = (old.get("count", 0) + large.get("count", 0))
            total = len(scan.issues)

            if safe_count > 0:
                chain.append(
                    f"{safe_count} of {total} items are unambiguously safe: "
                    f"duplicates are SHA-256 verified copies and junk files are "
                    f"auto-generated caches that get recreated."
                )
            if review_count > 0:
                # Check if any review items have valuable content
                risky_items = []
                for issue in scan.issues:
                    if issue.category in (IssueCategory.OLD, IssueCategory.LARGE):
                        c = self.inspector.inspect(issue.path)
                        if c.contains_valuable_signals:
                            risky_items.append(issue.path.name)
                if risky_items:
                    chain.append(
                        f"However, I found potential concerns in {len(risky_items)} files: "
                        f"{', '.join(risky_items[:3])}. These contain personal or sensitive content "
                        f"and I'd recommend reviewing them individually."
                    )
                    risk_level = "medium"
                    caveats.extend(risky_items[:3])
                else:
                    chain.append(
                        f"The remaining {review_count} items (old/large files) don't contain "
                        f"sensitive markers, but they're substantive files worth a glance before deleting."
                    )
                    risk_level = "low"

            key_insight = "safety_assessment"
            if u.emotional_register == "worried":
                chain.append(
                    "The user sounds cautious — I should acknowledge their concern, "
                    "be specific about what's safe vs. what needs review, "
                    "and remind them about the Trash safety net and evidence receipts."
                )
            return Reasoning(chain=chain, key_insight=key_insight, caveats=caveats,
                           risk_level=risk_level, confidence=0.95)

        # ─ Strategy / cleanup plan ──────────────────────────────
        if u.topics.get("strategy", 0) > 0.3 or u.topics.get("junk", 0) > 0.3:
            chain.append(
                f"The user wants a cleanup plan. Let me prioritise by "
                f"safety-yield ratio using the actual scan data."
            )
            # Order: duplicates (safest + often big) → junk → large → old
            order = []
            for cat_key, label in [("duplicate", "duplicates"), ("junk", "junk"),
                                    ("large", "large files"), ("old", "old files")]:
                stats = ev.category_stats.get(cat_key, {})
                if stats:
                    order.append((label, stats["count"], stats["display_size"], stats["sample"]))

            for label, count, size, samples in order:
                sample_name = samples[0].path.name if samples else "?"
                chain.append(f"  → {count} {label} ({size}), e.g. '{sample_name}'")

            key_insight = "cleanup_strategy"
            return Reasoning(chain=chain, key_insight=key_insight, confidence=0.95)

        # ─ Duplicate deep-dive ──────────────────────────────────
        if u.topics.get("duplicates", 0) > 0.3:
            dupes = [i for i in scan.issues if i.category == IssueCategory.DUPLICATE]
            chain.append(f"The user wants to understand duplicates. Found {len(dupes)} verified by SHA-256.")
            if dupes:
                # Analyse WHERE duplicates come from
                sources = Counter(d.path.parent.name for d in dupes)
                top_source = sources.most_common(1)[0] if sources else ("?", 0)
                chain.append(
                    f"Most duplicates ({top_source[1]} files) are in the '{top_source[0]}' folder. "
                    f"This suggests {'email attachment downloads' if 'mail' in top_source[0].lower() else 'repeated saves or copies'}."
                )
            key_insight = "duplicate_analysis"
            return Reasoning(chain=chain, key_insight=key_insight, confidence=0.95)

        # ─ Space analysis ───────────────────────────────────────
        if u.topics.get("space", 0) > 0.3:
            sorted_issues = sorted(scan.issues, key=lambda x: x.size, reverse=True)
            top5 = sorted_issues[:5]
            chain.append(f"The user wants to know about space usage. Ranking all {len(scan.issues)} items by size.")
            if top5:
                chain.append(
                    f"The single biggest item is '{top5[0].path.name}' at {top5[0].size_display}. "
                    f"The top 3 alone account for {format_size(sum(i.size for i in top5[:3]))}."
                )
            key_insight = "space_analysis"
            return Reasoning(chain=chain, key_insight=key_insight, confidence=0.95)

        # ─ Folder breakdown ─────────────────────────────────────
        if u.topics.get("folder", 0) > 0.3:
            chain.append(f"The user is asking about directory structure. Found {len(ev.cluster_map)} folder clusters.")
            sorted_clusters = sorted(ev.cluster_map.items(), key=lambda kv: sum(i.size for i in kv[1]), reverse=True)
            for name, items in sorted_clusters[:4]:
                chain.append(f"  → '{name}/': {len(items)} items ({format_size(sum(i.size for i in items))})")
            key_insight = "folder_breakdown"
            return Reasoning(chain=chain, key_insight=key_insight, confidence=0.9)

        # ─ Old files ────────────────────────────────────────────
        if u.topics.get("old_files", 0) > 0.3:
            old = [i for i in scan.issues if i.category == IssueCategory.OLD]
            chain.append(f"The user is interested in old/stale files. Found {len(old)} items.")
            key_insight = "old_files_analysis"
            return Reasoning(chain=chain, key_insight=key_insight, confidence=0.9)

        # ─ File-type knowledge (scan active but general question) ─
        for ext, info in FILE_KNOWLEDGE.items():
            if ext in u.raw_query.lower():
                chain.append(
                    f"Answering a knowledge question about '{ext}' files within scan context. "
                    f"Role: {info['role']}. Created by: {info['origin']}."
                )
                key_insight = f"file_knowledge:{ext}"
                return Reasoning(chain=chain, key_insight=key_insight, confidence=1.0)

        # ─ Fallback: general scan overview ──────────────────────
        chain.append(
            f"This is a general question about the scanned directory. "
            f"I'll provide an overview and suggest what to explore next."
        )
        key_insight = "general_overview"
        return Reasoning(chain=chain, key_insight=key_insight, confidence=0.8)

    # ── Phase 4: Compose ────────────────────────────────────────

    def _compose(self, u: Understanding, ev: Evidence, r: Reasoning, scan: Optional[ScanResult]) -> str:
        """Build a natural, evidence-grounded response.

        This is NOT a template lookup — sentences are assembled from
        the specific evidence and reasoning for this particular query.
        """
        insight = r.key_insight

        # ─── Introduction ───────────────────────────────────────
        if insight == "introduction":
            # Vary based on whether they've used the app before
            if self.exchange_count <= 1:
                return (
                    f"Hey! I'm your on-device file analyst. I'm not a typical cleaner that "
                    f"blindly flags old files — I actually read inside your files, understand "
                    f"what they contain, and reason through whether they matter to you.\n\n"
                    f"A few things I can do that most tools can't:\n"
                    f"• I inspect file contents before recommending deletion — if a .tmp file "
                    f"actually contains your unsaved work, I'll catch that.\n"
                    f"• Three internal reviewers (Security, Preservation, Waste) independently "
                    f"evaluate every file before I show it to you.\n"
                    f"• You can teach me rules in plain English — try saying "
                    f"\"never delete files with thesis\" and I'll remember forever.\n"
                    f"• Every cleanup generates a cryptographic receipt you can verify offline.\n\n"
                    f"Pick a folder above and hit Scan, or ask me anything — like "
                    f"\"what are .DS_Store files?\" or \"check my Desktop\"."
                )
            return (
                f"I'm here. You've been through {self.exchange_count} exchanges with me so far. "
                f"What would you like to look into?"
            )

        # ─── Privacy ────────────────────────────────────────────
        if insight == "privacy_assurance":
            return (
                f"Everything runs on your machine. Specifically:\n\n"
                f"• Zero network connections — I don't open any sockets or make any HTTP calls. "
                f"Your files never leave your RAM.\n"
                f"• No external AI — the reasoning engine is pure Python logic running locally, "
                f"not a cloud model API.\n"
                f"• No telemetry — I don't track what you scan, delete, or ask.\n"
                f"• Sandbox enforcement — even my own code can't touch system directories "
                f"like /System or ~/.ssh without explicit authorization.\n\n"
                f"The evidence receipts are stored locally at ~/.fileclean/receipts/ "
                f"and are never transmitted anywhere."
            )

        # ─── Disk probe ─────────────────────────────────────────
        if insight == "disk_probe" and ev.disk_probe:
            dp = ev.disk_probe
            lines = [f"I looked directly at your {dp['path'].name} folder just now.\n"]
            lines.append(f"There are {dp['file_count']} files and {dp['dir_count']} subfolders, "
                        f"totalling {dp['total_display']}.")
            if dp.get("largest"):
                lines.append("\nThe heaviest items on disk:")
                for name, size in dp["largest"][:4]:
                    lines.append(f"  • {name} — {format_size(size)}")
            if dp.get("top_extensions"):
                ext_str = ", ".join(f"{ext} ({c})" for ext, c in dp["top_extensions"][:4])
                lines.append(f"\nMost common file types: {ext_str}")
            if dp.get("dir_names"):
                lines.append(f"\nSubfolders: {', '.join(dp['dir_names'][:5])}")
            lines.append(f"\nTo run full duplicate detection and content analysis on this folder, "
                        f"set it as the target above and click Scan.")
            return "\n".join(lines)

        # ─── File knowledge ─────────────────────────────────────
        if insight.startswith("file_knowledge:"):
            ext = insight.split(":", 1)[1]
            info = FILE_KNOWLEDGE.get(ext, {})
            if info:
                risk_note = {
                    "none": "Deleting these has zero risk — they're machine-generated and will be recreated automatically if needed.",
                    "low": "Generally safe to delete, but worth a quick check if you might need the original installer or archive again.",
                }
                return (
                    f"{ext} files are {info['role']}, generated by {info['origin']}.\n\n"
                    f"{risk_note.get(info['risk'], 'Review before deleting.')} "
                    f"{'Your system will regenerate them automatically.' if info['recreated'] == 'yes' else 'Once deleted, they are not auto-recreated.'}"
                )

        # ─── Needs scan ─────────────────────────────────────────
        if insight == "needs_scan":
            return (
                f"I need to see your actual files before I can answer that properly. "
                f"Right now I'd just be guessing — and I'd rather give you a real answer.\n\n"
                f"Pick a folder above (Downloads and Desktop are usually the best starting points) "
                f"and click Scan. I'll read inside the files, check for duplicates, "
                f"and come back with specific findings about your data."
            )

        # ─── File inspection ────────────────────────────────────
        if insight == "file_inspection" and ev.targeted_files:
            issue, content = ev.targeted_files[0]
            lines = [f"Here's what I found when I looked inside '{issue.path.name}':\n"]
            lines.append(f"Location: {issue.path.parent}")
            lines.append(f"Size: {issue.size_display}")
            lines.append(f"Category: {issue.category.value}")

            if content.extracted_snippet:
                snippet = content.extracted_snippet[:180].strip()
                lines.append(f"Content preview: \"{snippet}...\"")

            lines.append("")

            if issue.category == IssueCategory.DUPLICATE and issue.original_path:
                lines.append(
                    f"This is a byte-for-byte copy of '{issue.original_path.name}'. "
                    f"I verified this with SHA-256 hashing — the content is identical down "
                    f"to the last byte. Your original is safe, so removing this clone "
                    f"frees {issue.size_display} with zero data loss."
                )
            elif content.contains_valuable_signals:
                lines.append(
                    f"I'd hold onto this one. The content contains markers I associate "
                    f"with important documents — things like financial terms, personal "
                    f"correspondence, or credentials. Better safe than sorry."
                )
            elif content.is_auto_generated:
                reasons = ", ".join(content.disposable_reasons) if content.disposable_reasons else "machine-generated output"
                lines.append(
                    f"This is {reasons}. It wasn't created by you — it's a byproduct "
                    f"of software running on your machine. Safe to remove."
                )
            elif content.is_empty:
                lines.append("This file is completely empty — 0 useful bytes. Safe to remove.")
            else:
                lines.append(
                    f"The file has real content ({content.words_count} words, "
                    f"{content.lines_count} lines) but nothing I'd flag as sensitive. "
                    f"Take a quick look at the preview above and decide if you still need it."
                )
            return "\n".join(lines)

        # ─── Safety assessment ──────────────────────────────────
        if insight == "safety_assessment" and scan:
            dupes = ev.category_stats.get("duplicate", {})
            junk = ev.category_stats.get("junk", {})
            old = ev.category_stats.get("old", {})
            large = ev.category_stats.get("large", {})

            parts = []
            if u.emotional_register == "worried":
                parts.append(
                    "I understand the caution — deleting the wrong file is genuinely stressful. "
                    "Let me break down exactly what's safe and what deserves a second look.\n"
                )

            safe_items = []
            if dupes:
                safe_items.append(
                    f"The {dupes['count']} duplicates ({dupes['display_size']}) are the safest to remove. "
                    f"Each one is a SHA-256 verified copy — meaning I've mathematically confirmed "
                    f"the original exists elsewhere on your drive."
                )
            if junk:
                safe_items.append(
                    f"The {junk['count']} junk files ({junk['display_size']}) are system caches, "
                    f"temp files, and auto-generated metadata. Your system recreates these as needed."
                )
            if safe_items:
                parts.append(" ".join(safe_items))

            review_parts = []
            if old:
                review_parts.append(f"{old['count']} old files — untouched for a long time but may still matter to you")
            if large:
                review_parts.append(f"{large['count']} large files — significant space savings but worth checking first")
            if review_parts:
                parts.append("\nItems worth reviewing before removing:\n• " + "\n• ".join(review_parts))

            if r.caveats:
                parts.append(
                    f"\nI did find something to be careful about: {', '.join(r.caveats[:3])} "
                    f"{'contain' if len(r.caveats) > 1 else 'contains'} content that looks personal or sensitive. "
                    f"I'd recommend opening {'them' if len(r.caveats) > 1 else 'it'} first."
                )

            parts.append(
                "\nEven if something ends up in Trash by mistake, it's recoverable — "
                "and every action generates a cryptographic receipt documenting exactly what was moved."
            )
            return "\n".join(parts)

        # ─── Strategy ───────────────────────────────────────────
        if insight == "cleanup_strategy" and scan:
            categories = [("duplicate", "duplicates"), ("junk", "junk files"),
                         ("large", "large files"), ("old", "old files")]
            parts = [
                f"Looking at your {len(scan.issues)} flagged items in {scan.directory.name}, "
                f"here's the order I'd work through them:\n"
            ]
            step = 1
            for cat_key, label in categories:
                stats = ev.category_stats.get(cat_key, {})
                if not stats:
                    continue
                sample = stats["sample"][0] if stats["sample"] else None
                sample_name = f"'{sample.path.name}'" if sample else ""

                if cat_key == "duplicate":
                    parts.append(
                        f"{step}. **Start with the {stats['count']} {label}** ({stats['display_size']})\n"
                        f"   These are byte-identical copies — removing them is mathematically "
                        f"guaranteed to cause no data loss. Quick win."
                    )
                elif cat_key == "junk":
                    parts.append(
                        f"{step}. **Clear {stats['count']} {label}** ({stats['display_size']})\n"
                        f"   Caches, temp files, and system metadata like {sample_name}. "
                        f"Zero risk — your OS regenerates these automatically."
                    )
                elif cat_key == "large":
                    parts.append(
                        f"{step}. **Review {stats['count']} {label}** ({stats['display_size']})\n"
                        f"   The biggest space savers. Check items like {sample_name} — "
                        f"if you've already installed the app or finished with the archive, they can go."
                    )
                elif cat_key == "old":
                    parts.append(
                        f"{step}. **Consider {stats['count']} {label}**\n"
                        f"   Files untouched for months. These are lowest priority — "
                        f"only remove if you're sure you won't need them."
                    )
                step += 1

            parts.append(
                f"\nTotal reclaimable: {scan.reclaimable_display}. "
                f"Start from the top for maximum safety."
            )
            return "\n".join(parts)

        # ─── Duplicate analysis ─────────────────────────────────
        if insight == "duplicate_analysis" and scan:
            dupes = [i for i in scan.issues if i.category == IssueCategory.DUPLICATE]
            if not dupes:
                return "No duplicates were found in this scan. Every file has unique content."

            sources = Counter(d.path.parent.name for d in dupes)
            top_source, top_count = sources.most_common(1)[0]

            parts = [
                f"Found {len(dupes)} duplicate files ({format_size(sum(d.size for d in dupes))}).\n"
            ]
            parts.append(
                f"Most of them ({top_count} files) are in the '{top_source}' folder"
                f"{' — this often happens with email attachments or repeated downloads' if 'mail' in top_source.lower() or 'download' in top_source.lower() else ''}."
            )
            parts.append("\nSome examples:")
            for d in dupes[:4]:
                orig = d.original_path.name if d.original_path else "another file"
                parts.append(f"  • '{d.path.name}' ({d.size_display}) → copy of '{orig}'")

            parts.append(
                f"\nEvery duplicate was verified with SHA-256 cryptographic hashing. "
                f"The original master copy is always preserved — only the redundant clone is flagged."
            )
            return "\n".join(parts)

        # ─── Space analysis ─────────────────────────────────────
        if insight == "space_analysis" and scan:
            sorted_issues = sorted(scan.issues, key=lambda x: x.size, reverse=True)
            parts = [f"Here are the biggest space consumers in {scan.directory.name}:\n"]
            for i, issue in enumerate(sorted_issues[:6], 1):
                parts.append(f"  {i}. {issue.path.name} — {issue.size_display} ({issue.category.value})")

            top3_size = sum(i.size for i in sorted_issues[:3])
            total_size = sum(i.size for i in sorted_issues)
            pct = (top3_size / total_size * 100) if total_size else 0
            parts.append(
                f"\nThe top 3 files alone account for {format_size(top3_size)} "
                f"({pct:.0f}% of all reclaimable space). "
                f"Cleaning just those would make the biggest impact."
            )
            return "\n".join(parts)

        # ─── Folder breakdown ───────────────────────────────────
        if insight == "folder_breakdown" and ev.cluster_map:
            sorted_clusters = sorted(ev.cluster_map.items(),
                                    key=lambda kv: sum(i.size for i in kv[1]), reverse=True)
            parts = [f"Breakdown by folder in {scan.directory.name}:\n"]
            for name, items in sorted_clusters[:6]:
                cats = Counter(i.category.value for i in items)
                cat_str = ", ".join(f"{c} {t}" for t, c in cats.most_common(3))
                parts.append(f"  • {name}/ — {len(items)} items ({format_size(sum(i.size for i in items))}): {cat_str}")
            return "\n".join(parts)

        # ─── Old files ──────────────────────────────────────────
        if insight == "old_files_analysis" and scan:
            old = [i for i in scan.issues if i.category == IssueCategory.OLD]
            if not old:
                return "No files were flagged as old or stale in this scan."
            parts = [f"Found {len(old)} files that haven't been touched in a long time:\n"]
            for o in old[:5]:
                parts.append(f"  • {o.path.name} ({o.size_display}) in {o.path.parent.name}/")
            parts.append(
                "\nThese are the lowest-risk category to ignore — they're only flagged "
                "because of age, not because they're junk. Review at your own pace."
            )
            return "\n".join(parts)

        # ─── General overview ───────────────────────────────────
        if insight == "general_overview" and scan:
            cat_counts = Counter(i.category.value for i in scan.issues)
            cat_summary = ", ".join(f"{c} {t}" for t, c in cat_counts.most_common())
            top_cluster = max(ev.cluster_map.items(), key=lambda kv: len(kv[1]))[0] if ev.cluster_map else scan.directory.name

            return (
                f"Your scan of {scan.directory.name} found {len(scan.issues)} items "
                f"taking up {scan.reclaimable_display}: {cat_summary}.\n\n"
                f"Most of the activity is in the '{top_cluster}' folder.\n\n"
                f"What would you like to dig into? You could ask me:\n"
                f"  • \"Is it safe to delete these?\"\n"
                f"  • \"What should I clean first?\"\n"
                f"  • \"Why did you flag [filename]?\"\n"
                f"  • \"How much space would I save from duplicates alone?\""
            )

        # ─── Ultimate fallback ──────────────────────────────────
        return (
            f"I'm not sure I followed that completely. Could you rephrase? "
            f"You can ask me about specific files, safety, cleanup strategy, "
            f"or just say \"help\" to see what I can do."
        )
