"""
Data-to-Dirt E2E Test Suite — Core Harness & Authoritative Contract Specifications

This harness provides:
1. Mathematical constants and formulations directly from ORIGINAL_REQUEST.md and Survey Reports.
2. Temporary sandbox directory generation for clean, isolated file operations.
3. Authoritative contract specifications and validators for all 30 features (F-01 through F-30).
4. Dynamic importer for connecting tests to actual `src` implementation modules as they become available.
"""

import os
import sys
import math
import time
import json
import re
import hashlib
import tempfile
import shutil
from typing import Dict, List, Optional, Tuple, Any

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# =====================================================================
# 1. Authoritative Constants (ORIGINAL_REQUEST.md & Survey Reports)
# =====================================================================
KWH_PER_GB_PER_YEAR = 0.28            # Standard Enterprise Storage (Survey 2)
GRID_INTENSITY_GCO2_PER_KWH = 405.7   # Singapore EMA Factor (Survey 2)
ANNUAL_CO2_PER_GB_G = KWH_PER_GB_PER_YEAR * GRID_INTENSITY_GCO2_PER_KWH # 113.596 g CO2e / GB / yr
TREE_ABSORPTION_KG_YEAR = 20.0        # Tree-Nation agroforestry standard (20 kg / yr)
THRESHOLD_BYTES = 1073741824          # 1.0 GB = 2^30 bytes
COST_PER_TREE_USD = 1.50              # Default Tree-Nation cost
CLOUD_SAVINGS_PER_GB_MONTH_USD = 0.02 # Projected cloud savings
SMARTPHONE_CHARGE_GCO2 = 8.22         # EPA metric
CAR_KM_GCO2 = 170.0                   # Standard gasoline passenger car
DEFAULT_TEACHER_PIN = "teacher123"
DAILY_DELETION_LIMIT_DEFAULT = 5

# =====================================================================
# 2. Dynamic Module Importer & Loader
# =====================================================================
def get_src_module(module_path: str) -> Optional[Any]:
    """
    Safely attempts to import a module from `src`.
    Returns the module if found, or None if not yet implemented.
    """
    try:
        __import__(module_path)
        return sys.modules[module_path]
    except (ImportError, ModuleNotFoundError):
        return None

# =====================================================================
# 3. Sandbox Filesystem Test Environment
# =====================================================================
class SandboxEnvironment:
    """Creates an isolated directory tree with synthetic files for tests."""
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="d2d_e2e_sandbox_")

    def create_file(self, rel_path: str, size_bytes: int = 1024, content: Optional[bytes] = None, mtime_days_ago: float = 0.0) -> str:
        full_path = os.path.join(self.temp_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            if content is not None:
                f.write(content)
            else:
                if size_bytes > 0:
                    # Write sparse or repeated block
                    chunk = b"X" * min(size_bytes, 4096)
                    written = 0
                    while written < size_bytes:
                        to_write = min(len(chunk), size_bytes - written)
                        f.write(chunk[:to_write])
                        written += to_write
        if mtime_days_ago > 0:
            target_mtime = time.time() - (mtime_days_ago * 86400)
            os.utime(full_path, (target_mtime, target_mtime))
        return full_path

    def cleanup(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

# =====================================================================
# 4. Authoritative Contract Models & Reference Specs (R1 - R5)
# =====================================================================

class CarbonCalculatorSpec:
    """F-01 & F-02: Stored Data Carbon Footprint & Equivalencies."""
    def __init__(self, kwh_per_gb: float = KWH_PER_GB_PER_YEAR, grid_intensity: float = GRID_INTENSITY_GCO2_PER_KWH):
        self.kwh_per_gb = kwh_per_gb
        self.grid_intensity = grid_intensity

    def calculate_kwh(self, size_bytes: int, years: float = 1.0) -> float:
        if size_bytes < 0:
            raise ValueError("File size cannot be negative")
        size_gb = size_bytes / 1073741824.0
        return size_gb * self.kwh_per_gb * years

    def calculate_carbon_grams(self, size_bytes: int, years: float = 1.0) -> float:
        kwh = self.calculate_kwh(size_bytes, years)
        return kwh * self.grid_intensity

    def calculate_avoided_offset_kg(self, deleted_bytes: int, years: float = 1.0) -> float:
        grams = self.calculate_carbon_grams(deleted_bytes, years)
        return grams / 1000.0

    def calculate_tree_equivalents(self, deleted_bytes: int, years: float = 1.0) -> float:
        kg = self.calculate_avoided_offset_kg(deleted_bytes, years)
        return kg / TREE_ABSORPTION_KG_YEAR

    def calculate_smartphone_charges(self, deleted_bytes: int) -> float:
        grams = self.calculate_carbon_grams(deleted_bytes)
        return grams / SMARTPHONE_CHARGE_GCO2

    def calculate_car_km(self, deleted_bytes: int) -> float:
        grams = self.calculate_carbon_grams(deleted_bytes)
        return grams / CAR_KM_GCO2


class FileScannerSpec:
    """F-10 through F-18: Privacy-First File Scanner & Heuristics."""
    CONFIDENTIAL_PATTERNS = [
        re.compile(r"^\.env(\..+)?$", re.IGNORECASE),
        re.compile(r".*id_rsa.*", re.IGNORECASE),
        re.compile(r".*password.*", re.IGNORECASE),
        re.compile(r".*credentials.*", re.IGNORECASE),
        re.compile(r".*\.pem$", re.IGNORECASE),
        re.compile(r".*\.key$", re.IGNORECASE),
        re.compile(r".*\.kdbx$", re.IGNORECASE),
    ]

    PII_SCRUBBERS = [
        (re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"), "[REDACTED_EMAIL]"),
        (re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"), "[REDACTED_PHONE]"),
        (re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), "[REDACTED_CARD]"),
        (re.compile(r"(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE), r"\1=[REDACTED_SECRET]"),
    ]

    def __init__(self):
        self.state = "BLIND"
        self.active_path: Optional[str] = None
        self.scanned_files: List[Dict[str, Any]] = []
        self.confidential_file_ids: set = set()

    def grant_access(self, path: str, session_only: bool = True):
        if not path or not os.path.isdir(path):
            raise ValueError("Invalid directory path")
        self.active_path = path
        self.state = "ACCESS_ACTIVE_SCOPED"

    def revoke_access(self):
        self.state = "BLIND"
        self.active_path = None
        self.scanned_files.clear()
        self.confidential_file_ids.clear()

    def is_confidential_pattern(self, filename: str) -> bool:
        return any(p.match(filename) for p in self.CONFIDENTIAL_PATTERNS)

    def scrub_pii(self, text: str) -> str:
        scrubbed = text
        for pattern, replacement in self.PII_SCRUBBERS:
            scrubbed = pattern.sub(replacement, scrubbed)
        return scrubbed

    def pixelate_thumbnail(self, width: int = 16, height: int = 16) -> Dict[str, Any]:
        return {"blurred": True, "pixel_grid": f"{width}x{height}", "reveal_token": None}

    def scan(self, directory: Optional[str] = None) -> List[Dict[str, Any]]:
        target = directory or self.active_path
        if self.state != "ACCESS_ACTIVE_SCOPED" or not target:
            raise PermissionError("Access not granted or scanner in BLIND state")
        
        results = []
        visited_inodes = set()

        for root, dirs, files in os.walk(target, followlinks=False):
            # Check for .data_to_dirt_ignore
            if ".data_to_dirt_ignore" in files:
                dirs.clear() # Skip recursion
                continue

            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    stat_res = os.stat(fpath)
                except (PermissionError, FileNotFoundError):
                    continue

                # Symlink cycle check
                inode_key = (stat_res.st_dev, stat_res.st_ino)
                if inode_key in visited_inodes:
                    continue
                visited_inodes.add(inode_key)

                size = stat_res.st_size
                mtime = stat_res.st_mtime
                age_days = (time.time() - mtime) / 86400.0
                ext = os.path.splitext(fname)[1].lstrip(".").lower()
                fid = hashlib.sha256(f"{fpath}:{size}:{mtime}".encode()).hexdigest()[:16]

                is_conf = self.is_confidential_pattern(fname) or fid in self.confidential_file_ids

                # Dark Data Heuristics
                is_stale = age_days > 180.0
                is_heavy = size > 500 * 1024 * 1024
                is_transient = ext in ["tmp", "bak", "log", "cache"]

                item = {
                    "file_id": fid,
                    "name": fname,
                    "path": fpath,
                    "size_bytes": size,
                    "extension": ext,
                    "modified_epoch": mtime,
                    "age_days": round(age_days, 2),
                    "is_confidential": is_conf,
                    "is_stale": is_stale,
                    "is_heavy": is_heavy,
                    "is_transient": is_transient,
                    "is_dark_data": (is_stale or is_heavy or is_transient) and not is_conf
                }
                results.append(item)

        self.scanned_files = results
        return results

    def mark_confidential(self, file_id: str, is_confidential: bool = True):
        if is_confidential:
            self.confidential_file_ids.add(file_id)
        else:
            self.confidential_file_ids.discard(file_id)
        for f in self.scanned_files:
            if f["file_id"] == file_id:
                f["is_confidential"] = is_confidential
                if is_confidential:
                    f["is_dark_data"] = False


class CloudStorageMockSpec:
    """F-19 & F-20: Pluggable Cloud Storage Mock Provider."""
    def __init__(self):
        self.connected = False
        self.quota = {
            "total_bytes": 16106127360, # 15 GB
            "used_bytes": 13958643712,  # ~13 GB
            "trash_bytes": 1073741824   # 1 GB
        }
        self.files = [
            {"id": "cloud_001", "name": "Raw_4K_Video_Render.mov", "size_bytes": 2847582208, "trashed": False, "stale": True},
            {"id": "cloud_002", "name": "Semester_1_Backup.zip", "size_bytes": 1420584960, "trashed": False, "stale": True},
            {"id": "cloud_003", "name": "Math_Homework_Final.pdf", "size_bytes": 45088768, "trashed": False, "stale": False},
            {"id": "cloud_004", "name": "Duplicate_Asset_Pack.tar", "size_bytes": 891289600, "trashed": False, "stale": True},
        ]

    def connect(self, token: str = "mock_token") -> bool:
        self.connected = bool(token)
        return self.connected

    def disconnect(self):
        self.connected = False

    def list_files(self) -> List[Dict[str, Any]]:
        if not self.connected:
            raise ConnectionError("Cloud provider not connected")
        return [f for f in self.files if not f["trashed"]]

    def stage_deletion(self, file_id: str) -> bool:
        if not self.connected:
            raise ConnectionError("Cloud provider not connected")
        for f in self.files:
            if f["id"] == file_id and not f["trashed"]:
                f["trashed"] = True
                self.quota["used_bytes"] -= f["size_bytes"]
                self.quota["trash_bytes"] += f["size_bytes"]
                return True
        return False

    def restore_file(self, file_id: str) -> bool:
        for f in self.files:
            if f["id"] == file_id and f["trashed"]:
                f["trashed"] = False
                self.quota["used_bytes"] += f["size_bytes"]
                self.quota["trash_bytes"] -= f["size_bytes"]
                return True
        return False


class NeuralAccountabilitySpec:
    """F-21 through F-25: On-Device Neural Accountability Engine."""
    VOCAB = {
        "[PAD]": 0, "[UNK]": 1, "[BOS]": 2, "[EOS]": 3, "[SEP]": 4,
        "cache": 10, "temp": 11, "tmp": 12, "duplicate": 13, "copy": 14, "raw": 15,
        "render": 16, "draft": 17, "export": 18, "backup": 19, "old": 20, "obsolete": 21,
        "asdf": 100, "points": 101, "score": 102, "free": 103, "farm": 104, "need": 105,
        "system32": 200, "kernel": 201, "password": 202, "secret": 203
    }

    GAMING_REGEX = re.compile(r"\b(asdf|qwer|idk|stuff|points|score|farm|tree|free|give|need)\b", re.IGNORECASE)
    SYSTEM_REGEX = re.compile(r"\b(system32|kernel|dll|sys|boot|passwd)\b", re.IGNORECASE)

    def __init__(self):
        self.strikes: Dict[str, int] = {}

    def tokenize(self, text: str, max_length: int = 64) -> List[int]:
        tokens = [self.VOCAB["[BOS]"]]
        clean = re.sub(r"[^\w\s]", "", text.lower())
        for word in clean.split():
            tokens.append(self.VOCAB.get(word, self.VOCAB["[UNK]"]))
        tokens.append(self.VOCAB["[EOS]"])
        if len(tokens) < max_length:
            tokens.extend([self.VOCAB["[PAD]"]] * (max_length - len(tokens)))
        return tokens[:max_length]

    def evaluate_reason(self, filename: str, reason: str, size_bytes: int = 1024, age_days: float = 30.0) -> Tuple[float, str, bool]:
        """Returns (confidence_score, summary, is_gaming)."""
        # Hard check for system destructive deletion
        if self.SYSTEM_REGEX.search(filename) or self.SYSTEM_REGEX.search(reason):
            return 0.05, "Critical: High-risk system asset deletion attempted.", True

        # Check for pure gaming / gibberish keywords
        gaming_match = self.GAMING_REGEX.search(reason)
        words = reason.strip().split()
        if len(words) < 2 or (gaming_match and not ("cache" in reason or "backup" in reason)):
            return 0.18, "Flagged: Detected gamification keyword or low-effort reasoning.", True

        # Plausible reasoning patterns
        plausible_terms = ["temporary", "temp", "cache", "duplicate", "redundant", "old", "backup", "finished", "draft", "completed"]
        match_count = sum(1 for term in plausible_terms if term in reason.lower())
        
        if match_count >= 1:
            base_score = 0.75 + min(0.20, match_count * 0.05)
            summary = f"Verified: Plausible deletion reason for {filename}. Context aligns with stated justification."
            return round(base_score, 2), summary, False
        else:
            return 0.42, f"Insufficient: Justification for {filename} requires more detail.", False

    def register_strike(self, student_id: str) -> Dict[str, Any]:
        count = self.strikes.get(student_id, 0) + 1
        self.strikes[student_id] = count
        if count == 1:
            return {"strike": 1, "action": "WARNING", "points_deducted": 0, "streak_reset": False}
        elif count == 2:
            return {"strike": 2, "action": "FREEZE_STREAK", "points_deducted": 10, "streak_reset": False}
        else:
            return {"strike": count, "action": "RESET_STREAK_FLAG", "points_deducted": 50, "streak_reset": True}


class GamificationSpec:
    """F-03 through F-06: Leaderboards, Streaks, Limits, and Tree Progression."""
    STAGE_THRESHOLDS = [
        (0, "Stage 0: Prepared Soil"),
        (1048576, "Stage 1: The Sprout"),           # 1 MB
        (52428800, "Stage 2: The Sapling"),         # 50 MB
        (262144000, "Stage 3: Young Oak"),          # 250 MB
        (1073741824, "Stage 4: Ancient Tree"),      # 1 GB
        (5368709120, "Stage 5: Legendary Eco-Tree") # 5 GB
    ]

    def __init__(self):
        self.students: Dict[str, Dict[str, Any]] = {
            "stu_01": {"name": "Alice Chen", "points": 340, "streak": 7, "deleted_bytes": 4500000000, "today_deletions": 0},
            "stu_02": {"name": "Marcus Vance", "points": 280, "streak": 5, "deleted_bytes": 2800000000, "today_deletions": 0},
            "stu_03": {"name": "Elena Rostova", "points": 190, "streak": 3, "deleted_bytes": 1200000000, "today_deletions": 0},
        }
        self.daily_limit = DAILY_DELETION_LIMIT_DEFAULT

    def get_leaderboard(self) -> List[Dict[str, Any]]:
        ranked = sorted(self.students.values(), key=lambda s: (s["points"], s["streak"]), reverse=True)
        for i, s in enumerate(ranked):
            s["rank"] = i + 1
        return ranked

    def check_daily_limit(self, student_id: str) -> bool:
        s = self.students.get(student_id)
        if not s:
            return False
        return s["today_deletions"] < self.daily_limit

    def record_deletion(self, student_id: str, bytes_deleted: int) -> Dict[str, Any]:
        s = self.students.get(student_id)
        if not s:
            raise KeyError(f"Student {student_id} not found")
        if not self.check_daily_limit(student_id):
            raise ValueError("Daily deletion limit reached")

        s["today_deletions"] += 1
        s["deleted_bytes"] += bytes_deleted
        points_earned = max(5, int(bytes_deleted / (10 * 1024 * 1024))) # 1 pt per 10 MB, min 5
        s["points"] += points_earned
        s["streak"] += 1 # Increments on valid deletion

        tree_stage = self.get_tree_stage(s["deleted_bytes"])
        return {
            "student_id": student_id,
            "points_earned": points_earned,
            "new_total_points": s["points"],
            "new_streak": s["streak"],
            "tree_stage": tree_stage
        }

    def get_tree_stage(self, total_bytes: int) -> str:
        current_stage = self.STAGE_THRESHOLDS[0][1]
        for threshold, stage_name in self.STAGE_THRESHOLDS:
            if total_bytes >= threshold:
                current_stage = stage_name
        return current_stage


class EcoFundLedgerSpec:
    """F-29 & F-30: Eco-Fund Accounting & Cumulative Waste Threshold."""
    def __init__(self, initial_budget_usd: float = 100.0, threshold_bytes: int = THRESHOLD_BYTES):
        self.budget_usd = initial_budget_usd
        self.threshold_bytes = threshold_bytes
        self.cumulative_waste_bytes = 0
        self.donated_bytes = 0
        self.lifetime_trees = 0
        self.transactions: List[Dict[str, Any]] = []
        self._record_tx("BUDGET_ALLOCATION", initial_budget_usd, "Initial classroom Eco-Fund budget")

    def _get_last_hash(self) -> str:
        if not self.transactions:
            return "0" * 64
        return self.transactions[-1]["hash"]

    def _record_tx(self, tx_type: str, amount_usd: float, notes: str, extra: Optional[Dict] = None) -> Dict[str, Any]:
        prev_hash = self._get_last_hash()
        tx = {
            "tx_id": f"tx_{len(self.transactions) + 1:04d}",
            "prev_hash": prev_hash,
            "timestamp": time.time(),
            "type": tx_type,
            "amount_usd": amount_usd,
            "balance_after": self.budget_usd,
            "notes": notes
        }
        if extra:
            tx.update(extra)
        # Compute SHA-256
        tx_repr = f"{tx['tx_id']}:{prev_hash}:{tx['type']}:{tx['amount_usd']}:{tx['balance_after']}"
        tx["hash"] = hashlib.sha256(tx_repr.encode()).hexdigest()
        self.transactions.append(tx)
        return tx

    def verify_ledger_integrity(self) -> bool:
        for i, tx in enumerate(self.transactions):
            expected_prev = "0" * 64 if i == 0 else self.transactions[i - 1]["hash"]
            if tx["prev_hash"] != expected_prev:
                return False
            tx_repr = f"{tx['tx_id']}:{tx['prev_hash']}:{tx['type']}:{tx['amount_usd']}:{tx['balance_after']}"
            if hashlib.sha256(tx_repr.encode()).hexdigest() != tx["hash"]:
                return False
        return True

    def accumulate_waste(self, approved_bytes: int) -> Dict[str, Any]:
        self.cumulative_waste_bytes += approved_bytes
        surplus = self.cumulative_waste_bytes - self.donated_bytes
        trees_to_plant = surplus // self.threshold_bytes

        result = {
            "approved_bytes": approved_bytes,
            "cumulative_waste": self.cumulative_waste_bytes,
            "surplus_bytes": surplus,
            "trees_triggered": 0,
            "status": "ACCUMULATING"
        }

        if trees_to_plant > 0:
            total_cost = trees_to_plant * COST_PER_TREE_USD
            if self.budget_usd >= total_cost:
                self.budget_usd -= total_cost
                self.donated_bytes += trees_to_plant * self.threshold_bytes
                self.lifetime_trees += trees_to_plant
                remaining_surplus = self.cumulative_waste_bytes - self.donated_bytes
                self._record_tx(
                    "TREE_NATION_DISBURSEMENT",
                    -total_cost,
                    f"Planted {trees_to_plant} trees via Tree-Nation",
                    {"trees_planted": trees_to_plant, "cost_usd": total_cost}
                )
                result.update({
                    "trees_triggered": trees_to_plant,
                    "cost_usd": total_cost,
                    "remaining_budget": self.budget_usd,
                    "surplus_bytes": remaining_surplus,
                    "status": "DONATION_EXECUTED"
                })
            else:
                result["status"] = "PENDING_FUNDS"
        return result


class TeacherQueueSpec:
    """F-26 through F-28: Teacher Confirmation Queue & Decision Actions."""
    def __init__(self, ledger: EcoFundLedgerSpec, gamification: GamificationSpec):
        self.queue: List[Dict[str, Any]] = []
        self.ledger = ledger
        self.gamification = gamification
        self.teacher_pin = DEFAULT_TEACHER_PIN

    def verify_pin(self, pin: str) -> bool:
        return pin == self.teacher_pin

    def submit_request(self, student_id: str, file_name: str, size_bytes: int, reason: str, ai_score: float, ai_summary: str) -> str:
        req_id = f"REQ-{len(self.queue) + 1:04d}"
        item = {
            "request_id": req_id,
            "student_id": student_id,
            "file_name": file_name,
            "size_bytes": size_bytes,
            "reason": reason,
            "ai_score": ai_score,
            "ai_summary": ai_summary,
            "status": "PENDING",
            "decision_note": None
        }
        self.queue.append(item)
        return req_id

    def approve(self, request_id: str) -> Dict[str, Any]:
        item = next((r for r in self.queue if r["request_id"] == request_id), None)
        if not item:
            raise KeyError("Request not found")
        if item["status"] != "PENDING":
            raise ValueError(f"Request already processed: {item['status']}")

        item["status"] = "APPROVED"
        # Credit student gamification
        g_result = self.gamification.record_deletion(item["student_id"], item["size_bytes"])
        # Accumulate waste in ledger
        l_result = self.ledger.accumulate_waste(item["size_bytes"])

        return {
            "request_id": request_id,
            "status": "APPROVED",
            "gamification": g_result,
            "ledger": l_result
        }

    def reject(self, request_id: str, feedback_note: str) -> Dict[str, Any]:
        item = next((r for r in self.queue if r["request_id"] == request_id), None)
        if not item:
            raise KeyError("Request not found")
        if item["status"] != "PENDING":
            raise ValueError(f"Request already processed: {item['status']}")

        item["status"] = "REJECTED"
        item["decision_note"] = feedback_note
        return {"request_id": request_id, "status": "REJECTED", "feedback": feedback_note}

    def flag(self, request_id: str, feedback_note: str) -> Dict[str, Any]:
        item = next((r for r in self.queue if r["request_id"] == request_id), None)
        if not item:
            raise KeyError("Request not found")
        if item["status"] != "PENDING":
            raise ValueError(f"Request already processed: {item['status']}")

        item["status"] = "FLAGGED"
        item["decision_note"] = feedback_note
        # Disciplinary penalty
        student = self.gamification.students.get(item["student_id"])
        if student:
            student["streak"] = 0
            student["points"] = max(0, student["points"] - 50)

        return {"request_id": request_id, "status": "FLAGGED", "feedback": feedback_note}
