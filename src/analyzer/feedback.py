from __future__ import annotations

from typing import Tuple, List, Dict, Any

from src.analyzer.models import FileIssue
from src.analyzer.user_profile import UserProfile
from src.fileclean_core.database import FeedbackDatabase

class FeedbackCollector:
    def __init__(self, db: FeedbackDatabase):
        self.db = db
        self.profile = UserProfile(self.db)

    def record_decision(self, issue: FileIssue, user_action: str) -> None:
        self.db.record_feedback(
            file_path=str(issue.path),
            extension=issue.path.suffix.lower(),
            size=issue.size,
            days_since_modified=0.0,
            days_since_accessed=0.0,
            category=issue.category.value,
            predicted_action="delete",
            user_action=user_action,
            confidence=issue.confidence.value,
            source=issue.source.value
        )
        self.profile.record_user_decision(issue.path, user_action, issue.category.value)

    def get_training_data(self) -> Tuple[List[Dict[str, Any]], List[str]]:
        feedback = self.db.get_all_feedback()
        features = []
        labels = []
        for f in feedback:
            features.append({
                "extension": f.get("extension", ""),
                "size": f.get("size", 0),
                "days_since_modified": f.get("days_since_modified", 0.0),
                "days_since_accessed": f.get("days_since_accessed", 0.0),
                "category": f.get("category", "")
            })
            labels.append(f.get("user_action", "keep"))
        return features, labels

    def should_retrain(self) -> bool:
        count = self.db.get_feedback_count()
        return count >= 100

    def get_stats(self) -> Dict[str, Any]:
        return self.db.get_accuracy_stats()
