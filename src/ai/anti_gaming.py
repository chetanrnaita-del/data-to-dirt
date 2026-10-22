"""
Anti-Gaming Penalty Engine for Data-to-Dirt.
Detects nonsensical strings, gaming patterns, score-farming, and high-risk file manipulations.
Enforces a 3-strike escalation loop with progressive disciplinary penalties.
"""

import math
import re
from typing import Any, Dict, List, Optional, Tuple


class AntiGamingEngine:
    """
    3-Strike Escalation Loop and Gaming Pattern Detector.
    Tracks strikes per student and applies progressive penalties:
      - Strike 1: Warning alert, request rejected, 0 points deducted, streak unchanged.
      - Strike 2: Streak frozen, -10 eco-points deducted.
      - Strike 3+: Streak reset to 0, -50 eco-points deducted, incident flagged for teacher.
      - Severe / Exploit: Immediate Strike 3 escalation.
    """

    # Regex patterns for gaming and score farming
    GAMING_KEYWORDS_REGEX = re.compile(
        r"\b(asdf|qwer|zxcv|lkjh|poiu|idk|stuff|points|score|farm|farming|tree|trees|free|give|need|cheat|cheatcode|bypass|bot|hack|grind|grinding|yolo|spam|pls|please)\b",
        re.IGNORECASE
    )

    # Regex patterns for score-farming phrases
    SCORE_FARMING_REGEX = re.compile(
        r"(give\s+(me\s+)?(points|score|trees?)|farm(ing)?\s+(points|score|trees?)|need\s+(points|trees?|score)|free\s+points|beat\s+leaderboard|win\s+game)",
        re.IGNORECASE
    )

    # High-risk system files / security targets
    SYSTEM_TARGETS_REGEX = re.compile(
        r"\b(system32|kernel|dll|sys|boot|passwd|shadow|id_rsa|credentials|api_key|secret_key|\.key|\.kdbx)\b",
        re.IGNORECASE
    )

    # Common keyboard mash sequences
    KEYBOARD_MASHES = {
        "asdf", "asdfgh", "asdfghjkl", "qwerty", "qwer", "zxcv", "lkjh",
        "poiu", "poiuyt", "zxcvbnm", "mnbvcxz", "qazwsx", "edcrfv", "12345"
    }

    def __init__(self):
        self.strikes: Dict[str, int] = {}
        self.incident_log: List[Dict[str, Any]] = []

    def calculate_char_entropy(self, text: str) -> float:
        """Computes Shannon entropy of character distribution."""
        if not text:
            return 0.0
        length = len(text)
        counts = {}
        for ch in text.lower():
            counts[ch] = counts.get(ch, 0) + 1
        entropy = 0.0
        for count in counts.values():
            p = count / length
            entropy -= p * math.log2(p)
        return entropy

    def is_gibberish(self, text: str) -> Tuple[bool, str]:
        """
        Determines whether a string is gibberish, keyboard mash, or nonsensical input.
        Returns (is_gibberish, reason_msg).
        """
        clean = text.strip().lower()
        if not clean:
            return True, "Empty reason submitted."

        # Check for keyboard mashes
        for mash in self.KEYBOARD_MASHES:
            if mash in clean:
                return True, f"Detected keyboard mash sequence: '{mash}'"

        # Check repeated characters like "aaaaa", "zzzzz", "..."
        if re.search(r"(.)\1{3,}", clean):
            return True, "Excessive repeated identical characters detected."

        words = clean.split()
        if len(words) == 1:
            word = words[0]
            # Single very short or single character
            if len(word) <= 2:
                return True, "Single abbreviated token is insufficient justification."
            # Low effort single-word fillers
            if word in {"idk", "stuff", "junk", "delete", "test", "remove", "no", "yes", "clean", "none"}:
                return True, f"Vague single-word submission: '{word}'"

        # Check consonant vs vowel ratio for strings without spaces
        alpha_only = re.sub(r"[^a-z]", "", clean)
        if len(alpha_only) >= 6:
            vowels = sum(1 for c in alpha_only if c in "aeiou")
            vowel_ratio = vowels / len(alpha_only)
            if vowel_ratio < 0.12 or vowel_ratio > 0.85:
                return True, f"Unnatural character distribution (vowel ratio: {vowel_ratio:.2f})"

        return False, ""

    def inspect_reason(self, reason: str, filename: str = "") -> Tuple[bool, List[str], str]:
        """
        Inspects deletion reason and filename for gaming patterns, system threats, and gibberish.
        Returns (is_gaming, detected_flags, summary_explanation).
        """
        flags = []
        explanation = ""

        # 1. System file threat
        fn_match = self.SYSTEM_TARGETS_REGEX.search(filename)
        reason_match = self.SYSTEM_TARGETS_REGEX.search(reason)
        if fn_match or reason_match:
            target = fn_match.group(0) if fn_match else reason_match.group(0)
            flags.append("SYSTEM_SECURITY_RISK")
            explanation = f"Critical: Attempted deletion of critical system target '{target}'."
            return True, flags, explanation

        # 2. Score farming regex
        if self.SCORE_FARMING_REGEX.search(reason):
            flags.append("SCORE_FARMING")
            explanation = "Flagged: Explicit score farming or eco-points solicitation detected."
            return True, flags, explanation

        # 3. Gibberish check
        gibberish, gib_msg = self.is_gibberish(reason)
        if gibberish:
            flags.append("GIBBERISH_NONSENSE")
            explanation = f"Flagged: {gib_msg}"
            return True, flags, explanation

        # 4. Gaming keyword match without legitimate justification
        gaming_kw = self.GAMING_KEYWORDS_REGEX.search(reason)
        legit_kw = re.search(r"\b(cache|temp|tmp|duplicate|backup|archive|old|obsolete|completed|finished)\b", reason, re.IGNORECASE)
        if gaming_kw and not legit_kw:
            flags.append("GAMING_KEYWORD")
            explanation = f"Flagged: Contains suspicious gaming keyword '{gaming_kw.group(0)}' without valid justification."
            return True, flags, explanation

        return False, flags, "Validation passed: No gaming indicators detected."

    def register_strike(self, student_id: str, is_severe: bool = False) -> Dict[str, Any]:
        """
        Registers a strike against a student with 3-strike escalation:
          - Strike 1: WARNING (0 points deducted, streak unchanged)
          - Strike 2: FREEZE_STREAK (-10 points deducted, streak unchanged)
          - Strike 3+: RESET_STREAK_FLAG (-50 points deducted, streak reset)
        If is_severe is True, jumps immediately to Strike 3.
        """
        if is_severe:
            current_strike = max(self.strikes.get(student_id, 0) + 1, 3)
        else:
            current_strike = self.strikes.get(student_id, 0) + 1

        self.strikes[student_id] = current_strike

        if current_strike == 1:
            action = "WARNING"
            points = 0
            streak_reset = False
            msg = "Strike 1: Warning issued. Request rejected without point penalty. Please submit legitimate rationale."
            flagged = False
        elif current_strike == 2:
            action = "FREEZE_STREAK"
            points = 10
            streak_reset = False
            msg = "Strike 2: Streak frozen! -10 Eco-points deducted. Further gaming will reset your entire streak."
            flagged = False
        else:
            action = "RESET_STREAK_FLAG"
            points = 50
            streak_reset = True
            msg = f"Strike {current_strike}: Severe infraction! Streak reset to 0, -50 Eco-points deducted, incident queued for teacher review."
            flagged = True

        incident = {
            "student_id": student_id,
            "strike": current_strike,
            "action": action,
            "points_deducted": points,
            "streak_reset": streak_reset,
            "flagged": flagged,
            "message": msg
        }
        self.incident_log.append(incident)
        return incident

    def get_student_strikes(self, student_id: str) -> int:
        """Returns the current strike count for a student."""
        return self.strikes.get(student_id, 0)

    def reset_strikes(self, student_id: str) -> None:
        """Resets the strike counter for a student upon teacher pardon."""
        if student_id in self.strikes:
            del self.strikes[student_id]
