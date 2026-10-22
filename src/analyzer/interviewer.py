"""Interactive AI Interviewer & Dynamic File Bifurcation for FileClean.

Asks the user targeted onboarding questions (role, critical keywords, protected directories)
and dynamically bifurcates the scan candidate list in real time:
- Automatically saves new rules and learned affinities into the user profile.
- Filters and removes safeguarded files from the active cleanup list immediately.
- Explains which files were safeguarded and why.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Callable

from src.analyzer.models import ScanResult, FileIssue
from src.analyzer.user_profile import UserProfile


@dataclass
class InterviewQuestion:
    step: int
    question: str
    suggestions: List[str]
    context_hint: str


class AIInterviewer:
    """Orchestrates an interactive user interview and performs dynamic list bifurcation."""

    QUESTIONS: List[InterviewQuestion] = [
        InterviewQuestion(
            step=1,
            question="🎯 **Question 1 of 3: Primary Work Domain**\nWhat do you primarily use this computer for?",
            suggestions=["Software Developer", "Designer / Media", "Finance / Accounting", "Student / Researcher", "General Everyday Use"],
            context_hint="This helps me understand what kind of files are critical to your daily work."
        ),
        InterviewQuestion(
            step=2,
            question="🏷️ **Question 2 of 3: Critical Keywords**\nWhat important keywords or tags designate files I should **NEVER delete**?",
            suggestions=["invoice, tax, receipt", "thesis, research, draft", "client, contract, proposal", "family, photos, wedding"],
            context_hint="Any files matching these words will be immediately removed from the cleanup list and protected permanently."
        ),
        InterviewQuestion(
            step=3,
            question="📁 **Question 3 of 3: Protected Folders**\nAre there any specific project folders or directories that should be **100% off-limits**?",
            suggestions=["~/Documents/Important", "~/Projects", "~/Documents/Tax", "No specific folders"],
            context_hint="I will never scan or suggest deleting anything inside these paths."
        ),
    ]

    def __init__(self, user_profile: UserProfile, on_bifurcate: Optional[Callable[[List[FileIssue], List[FileIssue]], None]] = None):
        self.profile = user_profile
        self.on_bifurcate = on_bifurcate
        self.current_step = 0  # 0 = idle, 1..3 = active question
        self.is_active = False

    def start_interview(self) -> str:
        """Begin the guided interview."""
        self.current_step = 1
        self.is_active = True
        q = self.QUESTIONS[0]
        sugg_text = "\n".join(f"  • *\"{s}\"*" for s in q.suggestions)
        return (
            f"👋 **Let's personalize your cleanup rules!**\n"
            f"To ensure I understand what you value, I'll ask you 3 quick questions. "
            f"Based on your answers, I will **dynamically remove your important files from the cleanup list**.\n\n"
            f"{q.question}\n\n"
            f"**Common options**:\n{sugg_text}\n\n"
            f"*(Type your answer below or pick an option!)*"
        )

    def process_response(self, user_text: str, current_scan: Optional[ScanResult] = None) -> str:
        """Process user answer to current question, advance state, and bifurcate if needed."""
        text = user_text.strip()
        if not self.is_active:
            return self.start_interview()

        # Step 1: Process Domain / Role
        if self.current_step == 1:
            domain = self._extract_domain(text)
            self.profile._set_domain(domain)
            self.current_step = 2
            q2 = self.QUESTIONS[1]
            sugg_text = "\n".join(f"  • *\"{s}\"*" for s in q2.suggestions)
            return (
                f"✅ **Saved**: Set your profile as **{domain}**!\n\n"
                f"{q2.question}\n\n"
                f"**Suggested examples**:\n{sugg_text}\n\n"
                f"*(Enter keywords separated by commas)*"
            )

        # Step 2: Process Keywords and BIFURCATE active scan immediately!
        elif self.current_step == 2:
            extracted_keywords = self._extract_keywords(text)
            for kw in extracted_keywords:
                self.profile._save_rule("protect_keyword", kw, f"Interview response: '{text}'")
            self.profile._load_profile()

            # Dynamic Bifurcation on active scan
            bifurcation_report = ""
            if current_scan and extracted_keywords:
                safeguarded, remaining = self.bifurcate_and_prune(current_scan, extracted_keywords)
                if safeguarded:
                    names = ", ".join(f"`{f.path.name}`" for f in safeguarded[:5])
                    more = f" and {len(safeguarded) - 5} more" if len(safeguarded) > 5 else ""
                    bifurcation_report = (
                        f"\n\n⚡ **Dynamic Pruning Applied**:\n"
                        f"I immediately bifurcated your scan and **safeguarded {len(safeguarded)} files** matching `{', '.join(extracted_keywords)}` "
                        f"({names}{more}). They have been removed from the cleanup list!"
                    )

            self.current_step = 3
            q3 = self.QUESTIONS[2]
            sugg_text = "\n".join(f"  • *\"{s}\"*" for s in q3.suggestions)
            kws_joined = ", ".join(f"`{k}`" for k in extracted_keywords)
            return (
                f"🛡️ **Saved Protected Keywords**: {kws_joined} are now permanently protected!{bifurcation_report}\n\n"
                f"{q3.question}\n\n"
                f"**Suggested examples**:\n{sugg_text}"
            )

        # Step 3: Process Folder Protection
        elif self.current_step == 3:
            folders = self._extract_folders(text)
            for f in folders:
                self.profile._save_rule("protect_dir", str(Path(f).expanduser().resolve()), f"Interview response: '{text}'")
            self.profile._load_profile()

            # Final bifurcation pass if directories were specified
            bifurcation_report = ""
            if current_scan and folders:
                safeguarded, remaining = self.bifurcate_and_prune(current_scan)
                if safeguarded:
                    bifurcation_report = f"\n⚡ Safeguarded {len(safeguarded)} additional files located in exempt directories."

            self.current_step = 0
            self.is_active = False
            summary = self.profile.get_profile_summary()
            return (
                f"🎉 **Personalization Complete!**\n"
                f"FileClean has updated your preferences:{bifurcation_report}\n\n"
                f"• **Role**: **{summary['user_domain']}**\n"
                f"• **Protected Keywords**: {', '.join(f'`{k}`' for k in summary['protected_keywords'])}\n"
                f"• **Exempt Folders**: {len(summary['protected_directories'])} directories protected\n\n"
                f"Your active scan list has been refreshed. I will never recommend deleting anything matching these rules!"
            )

        return "Interview complete! Ask me any questions about your files or disk cleanup."

    def bifurcate_and_prune(
        self,
        scan_result: ScanResult,
        new_keywords: Optional[List[str]] = None
    ) -> Tuple[List[FileIssue], List[FileIssue]]:
        """Bifurcates current scan issues into safeguarded vs remaining issues.
        Prunes safeguarded files from scan_result.issues."""
        safeguarded: List[FileIssue] = []
        remaining: List[FileIssue] = []

        keywords = list(self.profile.protected_keywords)
        if new_keywords:
            keywords.extend([k.lower() for k in new_keywords])

        for issue in scan_result.issues:
            # Check 1: User profile rules
            is_prot, reason = self.profile.evaluate_file_safety(issue.path)
            if is_prot:
                safeguarded.append(issue)
                continue

            # Check 2: Direct match with new keywords
            path_str = str(issue.path).lower()
            matched = False
            for kw in keywords:
                if kw and kw in path_str:
                    safeguarded.append(issue)
                    matched = True
                    break

            if not matched:
                remaining.append(issue)

        # Prune the active scan result
        scan_result.issues = remaining

        # Trigger UI callback if registered
        if self.on_bifurcate:
            self.on_bifurcate(safeguarded, remaining)

        return safeguarded, remaining

    def _extract_domain(self, text: str) -> str:
        t = text.lower()
        if any(w in t for w in ["dev", "code", "software", "program"]):
            return "Software Developer"
        elif any(w in t for w in ["design", "art", "media", "video", "photo", "audio"]):
            return "Designer / Media Creator"
        elif any(w in t for w in ["finance", "account", "tax", "money", "audit", "biz"]):
            return "Finance & Business"
        elif any(w in t for w in ["student", "research", "phd", "academic", "university"]):
            return "Student / Researcher"
        return text.title() if len(text) < 30 else "General User"

    def _extract_keywords(self, text: str) -> List[str]:
        # Split on commas or common separators
        cleaned = re.sub(r"(?:never delete|protect|keep|my keywords are|important|files with)\s*", "", text, flags=re.IGNORECASE)
        tokens = [t.strip().strip("'\"").lower() for t in re.split(r"[,;\n]+", cleaned)]
        return [t for t in tokens if len(t) >= 2 and t not in ["none", "no", "nothing", "all", "the"]]

    def _extract_folders(self, text: str) -> List[str]:
        t_clean = text.lower().strip()
        if t_clean in ["no", "none", "nothing", "no folders", "n/a", "no specific folders", "skip"]:
            return []
        tokens = [t.strip().strip("'\"") for t in re.split(r"[,;\n]+", text)]
        return [t for t in tokens if len(t) >= 2 and ("/" in t or "~" in t or "\\" in t or len(t.split()) <= 3)]
