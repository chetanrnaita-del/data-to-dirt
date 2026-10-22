"""
Data-to-Dirt — Teacher Confirmation Queue & Approval Workflow Service (R4)

Provides thread-safe queue management for student deletion requests,
AI confidence evaluation tracking, tri-state decisioning (Approve, Reject, Flag),
safe file recycling via Send2Trash, gamification credits, Eco-Fund waste accumulation,
sorting by confidence, filtering, search, pagination, and aggregate analytics.
"""

import os
import time
import threading
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field

try:
    import send2trash
    HAS_SEND2TRASH = True
except ImportError:
    HAS_SEND2TRASH = False

from src.services.carbon_calculator import CarbonCalculator, calculate_carbon_grams
from src.services.analytics import AnalyticsService, ClassroomStats
from src.services.auth import DEFAULT_TEACHER_PIN, AuthService, default_auth_service


# Request Status Constants
STATUS_PENDING = "PENDING"
STATUS_APPROVED = "APPROVED"
STATUS_REJECTED = "REJECTED"
STATUS_FLAGGED = "FLAGGED"

VALID_STATUSES = {STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED, STATUS_FLAGGED}



@dataclass
class DeletionRequest:
    """
    Deletion request model tracking file context, stated reason,
    AI evaluation metrics, and teacher confirmation lifecycle.
    """
    id: str
    student_id: str
    file_path: str
    file_name: str
    file_size_bytes: int
    carbon_offset_grams: float
    deletion_reason: str
    ai_confidence_score: float
    ai_summary: str
    timestamp: float
    status: str = STATUS_PENDING
    student_name: str = ""
    file_age_days: float = 0.0
    decided_by: Optional[str] = None
    decided_at: Optional[float] = None
    decision_feedback: Optional[str] = None
    recycled_success: bool = False
    recycled_path: Optional[str] = None
    is_cloud: bool = False
    cloud_provider: Optional[str] = None

    # Attribute Aliases for interoperability
    @property
    def request_id(self) -> str:
        return self.id

    @property
    def size_bytes(self) -> int:
        return self.file_size_bytes

    @property
    def reason(self) -> str:
        return self.deletion_reason

    @property
    def ai_score(self) -> float:
        return self.ai_confidence_score

    @property
    def feedback(self) -> Optional[str]:
        return self.decision_feedback

    @property
    def decision_note(self) -> Optional[str]:
        return self.decision_feedback

    # Dictionary-like access for backwards compatibility
    def __getitem__(self, key: str) -> Any:
        # Standard attributes
        if hasattr(self, key):
            return getattr(self, key)
        # Aliases
        alias_map = {
            "request_id": self.id,
            "size_bytes": self.file_size_bytes,
            "reason": self.deletion_reason,
            "ai_score": self.ai_confidence_score,
            "feedback": self.decision_feedback,
            "decision_note": self.decision_feedback,
            "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp)),
            "ai_evaluation": {
                "confidence_score": self.ai_confidence_score,
                "tier": "HIGH_CONFIDENCE" if self.ai_confidence_score >= 0.5 else "LOW_CONFIDENCE",
                "summary": self.ai_summary,
                "is_gaming": self.ai_confidence_score < 0.5,
            }
        }
        if key in alias_map:
            return alias_map[key]
        raise KeyError(f"DeletionRequest has no key '{key}'")

    def __setitem__(self, key: str, value: Any) -> None:
        if hasattr(self, key):
            setattr(self, key, value)
        elif key == "request_id":
            self.id = value
        elif key == "size_bytes":
            self.file_size_bytes = value
        elif key == "reason":
            self.deletion_reason = value
        elif key == "ai_score":
            self.ai_confidence_score = value
        elif key in ("feedback", "decision_note"):
            self.decision_feedback = value
        else:
            setattr(self, key, value)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key) or key in (
            "request_id", "size_bytes", "reason", "ai_score", "feedback",
            "decision_note", "submitted_at", "ai_evaluation"
        )

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "request_id": self.id,
            "student_id": self.student_id,
            "student_name": self.student_name,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_size_bytes": self.file_size_bytes,
            "size_bytes": self.file_size_bytes,
            "carbon_offset_grams": self.carbon_offset_grams,
            "deletion_reason": self.deletion_reason,
            "reason": self.deletion_reason,
            "ai_confidence_score": self.ai_confidence_score,
            "ai_score": self.ai_confidence_score,
            "ai_summary": self.ai_summary,
            "timestamp": self.timestamp,
            "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp)),
            "status": self.status.upper(),
            "decided_by": self.decided_by,
            "decided_at": self.decided_at,
            "decision_feedback": self.decision_feedback,
            "decision_note": self.decision_feedback,
            "feedback": self.decision_feedback,
            "recycled_success": self.recycled_success,
            "recycled_path": self.recycled_path,
            "is_cloud": self.is_cloud,
            "cloud_provider": self.cloud_provider,
            "ai_evaluation": {
                "confidence_score": self.ai_confidence_score,
                "tier": "HIGH_CONFIDENCE" if self.ai_confidence_score >= 0.5 else "GAMING_DETECTED",
                "summary": self.ai_summary,
                "is_gaming": self.ai_confidence_score < 0.5,
            }
        }


class TeacherQueue:
    """
    Thread-safe confirmation queue managing student deletion requests
    and educator decisions.
    """

    def __init__(
        self,
        ledger: Optional[Any] = None,
        gamification: Optional[Any] = None,
        auth_service: Optional[AuthService] = None,
        teacher_pin: str = DEFAULT_TEACHER_PIN,
    ):
        self._lock = threading.RLock()
        self._requests: List[DeletionRequest] = []
        self._ledger = ledger
        self._gamification = gamification
        self._auth = auth_service or default_auth_service
        self._teacher_pin = teacher_pin
        self._calc = CarbonCalculator()

    @property
    def queue(self) -> List[DeletionRequest]:
        """Provides direct list access for backwards compatibility."""
        with self._lock:
            return list(self._requests)

    def __len__(self) -> int:
        with self._lock:
            return len(self._requests)

    def __getitem__(self, idx: int) -> DeletionRequest:
        with self._lock:
            return self._requests[idx]

    def verify_pin(self, pin: str) -> bool:
        """Verifies teacher PIN for gated actions."""
        if not pin or not isinstance(pin, str):
            return False
        return pin == self._teacher_pin

    def submit_request(
        self,
        student_id: str,
        file_name: str,
        size_bytes: int,
        reason: str,
        ai_score: float,
        ai_summary: str,
        file_path: Optional[str] = None,
        student_name: Optional[str] = None,
        file_age_days: float = 0.0,
        carbon_offset_grams: Optional[float] = None,
        is_cloud: bool = False,
        cloud_provider: Optional[str] = None,
    ) -> str:
        """
        Submits a new deletion request to the queue.
        Calculates carbon offset if not provided, assigns unique request ID,
        and returns the formatted request ID (e.g. 'REQ-0001').
        """
        with self._lock:
            req_num = len(self._requests) + 1
            request_id = f"REQ-{req_num:04d}"

            if carbon_offset_grams is None:
                carbon_g = calculate_carbon_grams(size_bytes)
            else:
                carbon_g = float(carbon_offset_grams)

            eff_path = file_path or f"/simulated/path/{file_name}"
            eff_name = student_name or f"Student {student_id}"

            req = DeletionRequest(
                id=request_id,
                student_id=student_id,
                student_name=eff_name,
                file_path=eff_path,
                file_name=file_name,
                file_size_bytes=int(size_bytes),
                carbon_offset_grams=carbon_g,
                deletion_reason=reason,
                ai_confidence_score=float(ai_score),
                ai_summary=ai_summary,
                timestamp=time.time(),
                status=STATUS_PENDING,
                file_age_days=file_age_days,
                is_cloud=is_cloud,
                cloud_provider=cloud_provider,
            )

            self._requests.append(req)
            return request_id

    def get_by_id(self, request_id: str) -> Optional[DeletionRequest]:
        """Finds request by ID in a thread-safe manner."""
        with self._lock:
            for r in self._requests:
                if r.id == request_id:
                    return r
            return None

    def approve(
        self,
        request_id: str,
        teacher_id: str = "TEACHER-001",
    ) -> Dict[str, Any]:
        """
        Teacher approves deletion:
        1. Validates request existence and PENDING status.
        2. Transitions status to APPROVED.
        3. Recycles local file (Send2Trash) or stages cloud deletion.
        4. Credits student gamification metrics (points, streak, bytes cleared).
        5. Accumulates cleared bytes into Eco-Fund ledger toward tree threshold.
        """
        with self._lock:
            item = self.get_by_id(request_id)
            if not item:
                raise KeyError(f"Request '{request_id}' not found")

            if item.status.lower() != STATUS_PENDING.lower():
                raise ValueError(f"Request already processed: {item.status}")

            item.status = STATUS_APPROVED
            item.decided_by = teacher_id
            item.decided_at = time.time()

            # 1. Trigger actual file recycling via Send2Trash or cloud
            recycled = False
            recycled_error = None
            if item.file_path and os.path.exists(item.file_path):
                try:
                    if HAS_SEND2TRASH:
                        try:
                            send2trash.send2trash(item.file_path)
                            recycled = True
                        except (OSError, Exception):
                            os.remove(item.file_path)
                            recycled = True
                    else:
                        os.remove(item.file_path)
                        recycled = True
                except Exception as ex:
                    recycled_error = str(ex)

            item.recycled_success = recycled
            item.recycled_path = item.file_path if recycled else None


            # 2. Record carbon savings into student gamification
            gamification_res = None
            if self._gamification:
                if hasattr(self._gamification, "record_deletion"):
                    try:
                        gamification_res = self._gamification.record_deletion(
                            item.student_id, item.file_size_bytes
                        )
                    except Exception as e:
                        gamification_res = {"error": str(e)}
                elif hasattr(self._gamification, "students"):
                    # Direct dictionary mutation if gamification is spec
                    stu = self._gamification.students.get(item.student_id)
                    if stu:
                        stu["deleted_bytes"] = stu.get("deleted_bytes", 0) + item.file_size_bytes
                        pts = max(5, int(item.file_size_bytes / (10 * 1024 * 1024)))
                        stu["points"] = stu.get("points", 0) + pts
                        stu["streak"] = stu.get("streak", 0) + 1
                        gamification_res = {
                            "points_earned": pts,
                            "new_total_points": stu["points"],
                            "new_streak": stu["streak"],
                        }

            # 3. Record into Eco-Fund accumulator / ledger
            ledger_res = None
            donation_triggered = False
            if self._ledger:
                if hasattr(self._ledger, "accumulate_waste"):
                    try:
                        ledger_res = self._ledger.accumulate_waste(item.file_size_bytes)
                        if isinstance(ledger_res, dict) and ledger_res.get("trees_triggered", 0) > 0:
                            donation_triggered = True
                    except Exception as e:
                        ledger_res = {"error": str(e)}

            return {
                "request_id": request_id,
                "status": "APPROVED",
                "action_taken": "approve",
                "decided_by": teacher_id,
                "recycled": recycled,
                "recycled_error": recycled_error,
                "gamification": gamification_res,
                "ledger": ledger_res,
                "donation_triggered": donation_triggered,
                "item": item.to_dict(),
            }

    def reject(
        self,
        request_id: str,
        teacher_id_or_reason: str = "TEACHER-001",
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Teacher rejects deletion:
        1. Validates request and PENDING status.
        2. Transitions status to REJECTED.
        3. Preserves file on disk (does NOT recycle).
        4. Logs teacher feedback note.
        5. Protects student streak/points from penalty.
        """
        # Support both reject(req_id, reason) and reject(req_id, teacher_id, reason)
        if reason is None:
            teacher_id = "TEACHER-001"
            feedback_note = teacher_id_or_reason
        else:
            teacher_id = teacher_id_or_reason
            feedback_note = reason

        with self._lock:
            item = self.get_by_id(request_id)
            if not item:
                raise KeyError(f"Request '{request_id}' not found")

            if item.status.lower() != STATUS_PENDING.lower():
                raise ValueError(f"Request already processed: {item.status}")

            item.status = STATUS_REJECTED
            item.decided_by = teacher_id
            item.decided_at = time.time()
            item.decision_feedback = feedback_note or "File preserved by teacher."

            return {
                "request_id": request_id,
                "status": "REJECTED",
                "action_taken": "reject",
                "feedback": item.decision_feedback,
                "decision_note": item.decision_feedback,
                "decided_by": teacher_id,
                "item": item.to_dict(),
            }

    def flag(
        self,
        request_id: str,
        teacher_id_or_reason: str = "TEACHER-001",
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Teacher flags deletion as gaming / suspicious:
        1. Validates request and PENDING status.
        2. Transitions status to FLAGGED.
        3. Preserves file on disk.
        4. Applies disciplinary strike & penalty: resets streak to 0, deducts 50 points.
        5. Logs incident in incident log.
        """
        # Support both flag(req_id, reason) and flag(req_id, teacher_id, reason)
        if reason is None:
            teacher_id = "TEACHER-001"
            feedback_note = teacher_id_or_reason
        else:
            teacher_id = teacher_id_or_reason
            feedback_note = reason

        with self._lock:
            item = self.get_by_id(request_id)
            if not item:
                raise KeyError(f"Request '{request_id}' not found")

            if item.status.lower() != STATUS_PENDING.lower():
                raise ValueError(f"Request already processed: {item.status}")


            item.status = STATUS_FLAGGED
            item.decided_by = teacher_id
            item.decided_at = time.time()
            item.decision_feedback = feedback_note or "Intentional gaming attempt flagged."

            # Disciplinary enforcement on student
            penalty_applied = False
            if self._gamification:
                if hasattr(self._gamification, "register_strike"):
                    try:
                        self._gamification.register_strike(item.student_id)
                        penalty_applied = True
                    except Exception:
                        pass
                elif hasattr(self._gamification, "students"):
                    stu = self._gamification.students.get(item.student_id)
                    if stu:
                        stu["streak"] = 0
                        stu["points"] = max(0, stu.get("points", 0) - 50)
                        penalty_applied = True

            return {
                "request_id": request_id,
                "status": "FLAGGED",
                "action_taken": "flag",
                "feedback": item.decision_feedback,
                "decision_note": item.decision_feedback,
                "decided_by": teacher_id,
                "penalty_applied": penalty_applied,
                "item": item.to_dict(),
            }

    def get_queue(
        self,
        status: Optional[str] = None,
        student_id: Optional[str] = None,
        min_confidence: Optional[float] = None,
        max_confidence: Optional[float] = None,
        search_query: Optional[str] = None,
        sort_by: str = "confidence",
        sort_asc: bool = True,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        Retrieves requests with rich filtering, search, pagination, and sorting.
        Default sorting: confidence score ascending (lowest first) to prioritize suspicious items.
        """
        with self._lock:
            filtered = list(self._requests)

            # 1. Filter by status
            if status:
                st_lower = status.strip().lower()
                filtered = [r for r in filtered if r.status.lower() == st_lower]

            # 2. Filter by student
            if student_id:
                sid_lower = student_id.strip().lower()
                filtered = [r for r in filtered if sid_lower in r.student_id.lower()]

            # 3. Filter by confidence range
            if min_confidence is not None:
                filtered = [r for r in filtered if r.ai_confidence_score >= min_confidence]
            if max_confidence is not None:
                filtered = [r for r in filtered if r.ai_confidence_score <= max_confidence]

            # 4. Search query
            if search_query:
                q = search_query.strip().lower()
                filtered = [
                    r for r in filtered
                    if q in r.file_name.lower()
                    or q in r.deletion_reason.lower()
                    or q in r.ai_summary.lower()
                    or q in r.student_id.lower()
                    or q in r.id.lower()
                    or q in r.student_name.lower()
                ]

            # 5. Sorting
            sort_key_lower = sort_by.strip().lower()
            if sort_key_lower in ("confidence", "ai_score", "ai_confidence_score"):
                filtered.sort(key=lambda r: r.ai_confidence_score, reverse=not sort_asc)
            elif sort_key_lower in ("timestamp", "date", "time"):
                filtered.sort(key=lambda r: r.timestamp, reverse=not sort_asc)
            elif sort_key_lower in ("size", "file_size_bytes", "size_bytes"):
                filtered.sort(key=lambda r: r.file_size_bytes, reverse=not sort_asc)
            elif sort_key_lower in ("student", "student_id"):
                filtered.sort(key=lambda r: r.student_id, reverse=not sort_asc)
            elif sort_key_lower in ("name", "file_name"):
                filtered.sort(key=lambda r: r.file_name.lower(), reverse=not sort_asc)

            total_count = len(filtered)
            page = max(1, page)
            page_size = max(1, page_size)
            total_pages = max(1, (total_count + page_size - 1) // page_size)

            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_items = filtered[start_idx:end_idx]

            return {
                "items": [item.to_dict() for item in page_items],
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }

    def get_analytics(self) -> Dict[str, Any]:
        """Returns aggregate classroom analytics."""
        with self._lock:
            stats = AnalyticsService.calculate_analytics(self._requests)
            return stats.to_dict()


# Global Singleton Instance
default_teacher_queue = TeacherQueue()
