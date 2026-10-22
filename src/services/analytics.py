"""
Data-to-Dirt — Teacher & Admin Classroom Analytics Service (R4)

Computes classroom aggregate statistics, carbon offsets, ecological equivalencies,
anti-gaming incident registers, and audit reports for educators and administrators.
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


# Constants for Ecological Equivalencies
CO2_GRAMS_PER_CAR_KM = 170.0          # Average gasoline passenger vehicle
CO2_GRAMS_PER_PHONE_CHARGE = 8.22     # Smartphone full recharge (EPA)
CO2_GRAMS_PER_LED_HOUR = 4.06         # 10W LED bulb for 1 hour
BYTES_PER_GB = 1073741824.0           # 1 GiB
TREE_DONATION_THRESHOLD_BYTES = 1073741824


@dataclass
class ClassroomStats:
    total_requests: int = 0
    pending_count: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    flagged_count: int = 0
    total_data_cleaned_bytes: int = 0
    total_data_cleaned_gb: float = 0.0
    total_carbon_offset_grams: float = 0.0
    total_carbon_offset_kg: float = 0.0
    active_students_count: int = 0
    total_trees_funded: int = 0
    gaming_incident_rate_pct: float = 0.0
    approval_rate_pct: float = 0.0
    car_km_avoided: float = 0.0
    smartphone_charges_avoided: float = 0.0
    incident_log: List[Dict[str, Any]] = field(default_factory=list)
    top_students: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "pending_count": self.pending_count,
            "approved_count": self.approved_count,
            "rejected_count": self.rejected_count,
            "flagged_count": self.flagged_count,
            "total_data_cleaned_bytes": self.total_data_cleaned_bytes,
            "total_data_cleaned_gb": round(self.total_data_cleaned_gb, 4),
            "total_carbon_offset_grams": round(self.total_carbon_offset_grams, 2),
            "total_carbon_offset_kg": round(self.total_carbon_offset_kg, 4),
            "active_students_count": self.active_students_count,
            "total_trees_funded": self.total_trees_funded,
            "gaming_incident_rate_pct": round(self.gaming_incident_rate_pct, 1),
            "approval_rate_pct": round(self.approval_rate_pct, 1),
            "car_km_avoided": round(self.car_km_avoided, 1),
            "smartphone_charges_avoided": round(self.smartphone_charges_avoided, 1),
            "incident_log": self.incident_log,
            "top_students": self.top_students,
        }


class AnalyticsService:
    """Aggregates classroom and school-wide dark data cleanup metrics."""

    @staticmethod
    def calculate_analytics(
        requests: List[Any],
        students: Optional[Dict[str, Any]] = None,
        trees_funded: Optional[int] = None,
    ) -> ClassroomStats:
        """
        Calculates aggregate statistics from a list of deletion requests and optional student profiles.
        """
        stats = ClassroomStats()
        stats.total_requests = len(requests)

        student_bytes: Dict[str, int] = {}
        unique_students = set()
        decided_count = 0

        for req in requests:
            # Handle both DeletionRequest objects and plain dicts
            r_dict = req.to_dict() if hasattr(req, "to_dict") else dict(req)

            status = str(r_dict.get("status", "")).lower()
            student_id = r_dict.get("student_id", "anonymous")
            unique_students.add(student_id)

            size_bytes = int(r_dict.get("file_size_bytes") or r_dict.get("size_bytes") or 0)
            carbon_g = float(r_dict.get("carbon_offset_grams") or 0.0)

            if status == "pending":
                stats.pending_count += 1
            elif status == "approved":
                stats.approved_count += 1
                decided_count += 1
                stats.total_data_cleaned_bytes += size_bytes
                stats.total_carbon_offset_grams += carbon_g
                student_bytes[student_id] = student_bytes.get(student_id, 0) + size_bytes
            elif status == "rejected":
                stats.rejected_count += 1
                decided_count += 1
            elif status == "flagged":
                stats.flagged_count += 1
                decided_count += 1
                stats.incident_log.append({
                    "request_id": r_dict.get("id") or r_dict.get("request_id"),
                    "student_id": student_id,
                    "file_name": r_dict.get("file_name", "unknown"),
                    "reason": r_dict.get("deletion_reason") or r_dict.get("reason", ""),
                    "ai_score": r_dict.get("ai_confidence_score") or r_dict.get("ai_score", 0.0),
                    "feedback": r_dict.get("decision_feedback") or r_dict.get("feedback") or r_dict.get("decision_note", ""),
                    "timestamp": r_dict.get("timestamp") or r_dict.get("submitted_at") or time.time(),
                    "decided_by": r_dict.get("decided_by", "teacher"),
                })

        stats.active_students_count = len(unique_students)
        stats.total_data_cleaned_gb = stats.total_data_cleaned_bytes / BYTES_PER_GB
        stats.total_carbon_offset_kg = stats.total_carbon_offset_grams / 1000.0

        if trees_funded is not None:
            stats.total_trees_funded = trees_funded
        else:
            stats.total_trees_funded = stats.total_data_cleaned_bytes // TREE_DONATION_THRESHOLD_BYTES

        if stats.total_requests > 0:
            stats.gaming_incident_rate_pct = (stats.flagged_count / stats.total_requests) * 100.0
        if decided_count > 0:
            stats.approval_rate_pct = (stats.approved_count / decided_count) * 100.0

        # Equivalencies
        stats.car_km_avoided = stats.total_carbon_offset_grams / CO2_GRAMS_PER_CAR_KM
        stats.smartphone_charges_avoided = stats.total_carbon_offset_grams / CO2_GRAMS_PER_PHONE_CHARGE

        # Ranked Top Students
        top_list = []
        for sid, b_cleared in sorted(student_bytes.items(), key=lambda x: x[1], reverse=True)[:10]:
            top_list.append({
                "student_id": sid,
                "data_cleared_bytes": b_cleared,
                "data_cleared_gb": round(b_cleared / BYTES_PER_GB, 3),
            })
        stats.top_students = top_list

        return stats

    @staticmethod
    def export_csv_report(stats: ClassroomStats) -> str:
        """Generates a CSV formatted environmental audit report."""
        lines = [
            "Metric,Value,Unit",
            f"Total Deletion Requests,{stats.total_requests},count",
            f"Approved Deletions,{stats.approved_count},count",
            f"Rejected Requests,{stats.rejected_count},count",
            f"Flagged Gaming Incidents,{stats.flagged_count},count",
            f"Total Data Cleared,{stats.total_data_cleaned_gb:.4f},GB",
            f"Total Carbon Offset,{stats.total_carbon_offset_kg:.4f},kg CO2e",
            f"Trees Funded,{stats.total_trees_funded},trees",
            f"Active Students,{stats.active_students_count},students",
            f"Passenger Car Distance Avoided,{stats.car_km_avoided:.2f},km",
            f"Smartphone Charges Avoided,{stats.smartphone_charges_avoided:.1f},charges",
        ]
        return "\n".join(lines)
