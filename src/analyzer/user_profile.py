"""User Profile & Behavioral Preference Learner for FileClean.

Learns from user actions (what they keep vs delete) and conversational instructions:
- Identifies user domain (e.g., developer, student, designer)
- Maintains explicit rules (protected directories, protected keywords)
- Tracks learned preference weights for file types and locations
- Evaluates whether a file should be recommended based on learned user habits
"""

from __future__ import annotations

import re
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from src.fileclean_core.database import FeedbackDatabase


@dataclass
class UserRule:
    """An explicit rule taught by the user."""
    rule_type: str  # 'protect_dir', 'protect_keyword', 'always_flag_ext', 'always_flag_dir'
    target: str     # e.g. '~/Documents/Taxes', 'invoice', '.log'
    reason: str


class UserProfile:
    """Learns and maintains a deep understanding of user habits and preferences."""

    def __init__(self, db: Optional[FeedbackDatabase] = None):
        self.db = db or FeedbackDatabase()
        self._init_profile_schema()
        self._load_profile()

    def _init_profile_schema(self) -> None:
        """Initialize tables for learned preferences and user rules."""
        with self.db._connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS user_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_type TEXT NOT NULL,
                    target TEXT NOT NULL UNIQUE,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS user_domain_profile (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );

                CREATE TABLE IF NOT EXISTS learned_affinities (
                    feature_type TEXT NOT NULL,
                    feature_value TEXT NOT NULL,
                    keep_count INTEGER DEFAULT 0,
                    delete_count INTEGER DEFAULT 0,
                    PRIMARY KEY (feature_type, feature_value)
                );
            """)

    def _load_profile(self) -> None:
        """Load explicit rules into memory for fast lookup."""
        self.protected_dirs: List[Path] = []
        self.protected_keywords: List[str] = [
            "invoice", "tax", "resume", "cv", "contract", "receipt",
            "password", "backup_important", "family", "wedding"
        ]
        self.purge_keywords: List[str] = [
            "tmp", "temp", "cache", "build", "dist", "scratch"
        ]

        with self.db._connection() as conn:
            rows = conn.execute("SELECT rule_type, target FROM user_rules").fetchall()
            for r in rows:
                rtype, target = r["rule_type"], r["target"]
                if rtype == "protect_dir":
                    self.protected_dirs.append(Path(target).expanduser().resolve())
                elif rtype == "protect_keyword":
                    self.protected_keywords.append(target.lower())
                elif rtype in ("always_flag_ext", "always_flag_dir"):
                    self.purge_keywords.append(target.lower())

    def record_user_decision(self, file_path: Path, user_action: str, category: str) -> None:
        """Learn from a user's decision (user kept or deleted a file)."""
        is_keep = user_action == "keep"
        ext = file_path.suffix.lower()
        parent_name = file_path.parent.name.lower()

        with self.db._connection() as conn:
            # 1. Update extension affinity
            if ext:
                self._update_affinity(conn, "ext", ext, is_keep)

            # 2. Update directory affinity
            self._update_affinity(conn, "dir", parent_name, is_keep)

            # 3. Update category affinity
            self._update_affinity(conn, "category", category, is_keep)

            # 4. Check if we can infer user domain (e.g., developer if working with code)
            if ext in [".py", ".ts", ".js", ".rs", ".go", ".cpp", ".java"]:
                conn.execute(
                    "INSERT OR REPLACE INTO user_domain_profile (key, value) VALUES ('is_developer', 'true')"
                )

    def _update_affinity(self, conn: sqlite3.Connection, feature_type: str, feature_value: str, is_keep: bool) -> None:
        keep_inc = 1 if is_keep else 0
        del_inc = 0 if is_keep else 1

        conn.execute("""
            INSERT INTO learned_affinities (feature_type, feature_value, keep_count, delete_count)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(feature_type, feature_value) DO UPDATE SET
                keep_count = keep_count + ?,
                delete_count = delete_count + ?
        """, (feature_type, feature_value, keep_inc, del_inc, keep_inc, del_inc))

    def evaluate_file_safety(self, file_path: Path) -> Tuple[bool, str]:
        """Check if a file is protected by user preferences or habits.
        Returns:
            (is_protected, reason)
        """
        # Check 1: Protected directories
        resolved = file_path.resolve()
        for pdir in self.protected_dirs:
            try:
                resolved.relative_to(pdir)
                return True, f"Inside user-protected directory: {pdir}"
            except ValueError:
                continue

        # Check 2: Protected keywords in path or name
        path_str = str(file_path).lower()
        for kw in self.protected_keywords:
            if kw in path_str:
                return True, f"Contains user-protected keyword '{kw}'"

        # Check 3: Learned habit — check if user has repeatedly kept this extension or folder
        affinity = self.get_affinity_score("ext", file_path.suffix.lower())
        if affinity > 0.60:
            return True, f"Based on your habits: you typically keep {file_path.suffix} files"

        return False, ""

    def get_affinity_score(self, feature_type: str, feature_value: str) -> float:
        """Returns affinity score between -1.0 (strongly delete) and +1.0 (strongly keep)."""
        with self.db._connection() as conn:
            row = conn.execute(
                "SELECT keep_count, delete_count FROM learned_affinities WHERE feature_type = ? AND feature_value = ?",
                (feature_type, feature_value)
            ).fetchone()
            if not row:
                return 0.0
            k, d = row["keep_count"], row["delete_count"]
            total = k + d
            if total < 2:
                return 0.0
            return (k - d) / total

    def teach_instruction(self, instruction: str) -> str:
        """Parse natural language instruction from the user and update the profile."""
        inst_lower = instruction.lower().strip()

        # 1. Role declaration: "I am a developer" / "I'm a designer"
        if "developer" in inst_lower or "programmer" in inst_lower or "engineer" in inst_lower:
            self._set_domain("developer")
            return "👨‍💻 Profile updated: Recognized you as a **developer**. I will take extra care to protect code repositories, scripts, and active projects."

        # 2. Protect folder: "never touch /path", "never delete anything in my notes folder", "protect ~/Documents"
        if any(w in inst_lower for w in ["folder", "dir", "directory", "/", "~"]) and "in the name" not in inst_lower:
            dir_match = re.search(
                r"(?:never touch|don't delete|never delete|protect|keep)\s+(?:anything\s+in\s+|all\s+in\s+|everything\s+in\s+|my\s+|in\s+)?([~/a-zA-Z0-9_\-\.\s]+?)(?:\s+folder|\s+dir|\s+directory)?$",
                inst_lower
            )
            if dir_match:
                raw_dir = dir_match.group(1).strip()
                if raw_dir.startswith("in "):
                    raw_dir = raw_dir[3:].strip()
                if raw_dir.startswith("my "):
                    raw_dir = raw_dir[3:].strip()
                if raw_dir and raw_dir not in ["anything", "all", "everything", "files"]:
                    target_path = Path(raw_dir).expanduser()
                    self._save_rule("protect_dir", str(target_path), f"User instruction: '{instruction}'")
                    self._load_profile()
                    return f"🛡️ Understood! I will **never recommend deleting** anything inside `{target_path}`."

        # 3. Protect keyword: "never delete files with invoice", "always keep all my tax files", "protect my backup files"
        kw_match = re.search(
            r"(?:never delete|protect|always keep|don't delete|keep)\s+(?:(?:all|my|any|of|the)\s+)*(?:files\s+with\s+|files\s+named\s+|files\s+containing\s+)?['\"]?([a-zA-Z0-9_\-]+)['\"]?(?:\s+files|\s+in\s+the\s+name)?",
            inst_lower
        )
        if kw_match:
            kw = kw_match.group(1).strip().lower()
            if kw and kw not in ["anything", "files", "all", "them", "everything", "it", "my", "our", "the"]:
                self._save_rule("protect_keyword", kw, f"User instruction: '{instruction}'")
                self._load_profile()
                return f"🛡️ Got it! Any files containing the keyword **'{kw}'** are now permanently protected."

        # 4. Always purge: "always flag node_modules" or "clean up all .log files"
        purge_match = re.search(r"(?:always flag|always clean|delete all|purge)\s+['\"]?([a-zA-Z0-9_\-\.]+)['\"]?", inst_lower)
        if purge_match:
            target = purge_match.group(1).strip().lower()
            self._save_rule("always_flag_dir" if not target.startswith(".") else "always_flag_ext", target, f"User instruction: '{instruction}'")
            self._load_profile()
            return f"🗑️ Understood! I have learned that you consider **'{target}'** disposable and will prioritize flagging it."

        return ""

    def _save_rule(self, rule_type: str, target: str, reason: str) -> None:
        with self.db._connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO user_rules (rule_type, target, reason) VALUES (?, ?, ?)",
                (rule_type, target, reason)
            )

    def _set_domain(self, domain: str) -> None:
        with self.db._connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO user_domain_profile (key, value) VALUES ('domain', ?)",
                (domain,)
            )

    def get_profile_summary(self) -> Dict[str, Any]:
        """Return a readable overview of what FileClean has learned about the user."""
        with self.db._connection() as conn:
            rules_count = conn.execute("SELECT COUNT(*) FROM user_rules").fetchone()[0]
            learned_count = conn.execute("SELECT COUNT(*) FROM learned_affinities").fetchone()[0]
            domain_row = conn.execute("SELECT value FROM user_domain_profile WHERE key = 'domain'").fetchone()

        return {
            "explicit_rules_count": rules_count,
            "learned_features_count": learned_count,
            "user_domain": domain_row[0] if domain_row else "General User",
            "protected_keywords": list(self.protected_keywords),
            "protected_directories": [str(d) for d in self.protected_dirs]
        }
