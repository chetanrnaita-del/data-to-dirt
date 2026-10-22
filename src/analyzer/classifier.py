from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from src.analyzer.models import FileMetadata, FileIssue, IssueCategory, Confidence, IssueSource

class FileClassifier:
    def __init__(self, model_path: Path | None = None):
        if model_path is None:
            # Check default locations
            base_dir = Path(__file__).resolve().parent.parent
            candidates = [
                base_dir / "models" / "classifier.joblib",
                base_dir / "training" / "models" / "classifier.joblib",
            ]
            for candidate in candidates:
                if candidate.exists():
                    model_path = candidate
                    break

        self.model_path = model_path
        self.model = None
        self.encoders = {}
        self.feature_names = []

        if self.is_available():
            try:
                import joblib
                data = joblib.load(self.model_path)
                if isinstance(data, dict):
                    self.model = data.get("model")
                    self.encoders = data.get("encoders", {})
                    self.feature_names = data.get("feature_names", [])
                else:
                    self.model = data
            except Exception as e:
                self.model = None

    def is_available(self) -> bool:
        return self.model_path is not None and self.model_path.exists()

    def _prepare_dataframe(self, metadata: List[FileMetadata]):
        import pandas as pd
        import numpy as np

        features = [m.to_feature_dict() for m in metadata]
        df = pd.DataFrame(features)

        categorical_features = ['extension', 'parent_dir_category', 'mime_category']
        for feat in categorical_features:
            if feat in df.columns:
                le = self.encoders.get(feat)
                if le is not None:
                    known_classes = set(le.classes_)
                    # Map unseen labels to the first known class or mode
                    default_val = le.classes_[0] if len(le.classes_) > 0 else ""
                    df[feat] = df[feat].astype(str).map(
                        lambda val: val if val in known_classes else default_val
                    )
                    df[feat] = le.transform(df[feat].astype(str))
                else:
                    df[feat] = 0

        if self.feature_names:
            # Ensure columns align with model feature names
            for col in self.feature_names:
                if col not in df.columns:
                    df[col] = 0
            df = df[self.feature_names]

        return df

    def predict(self, metadata: List[FileMetadata]) -> List[FileIssue]:
        if not self.is_available() or not self.model or not metadata:
            return []

        try:
            df = self._prepare_dataframe(metadata)
            predictions = self.model.predict(df)
            probabilities = self.model.predict_proba(df)

            issues = []
            for meta, pred, prob_arr in zip(metadata, predictions, probabilities):
                if pred == "keep":
                    continue

                prob = float(max(prob_arr))
                if prob > 0.9:
                    conf = Confidence.HIGH
                elif prob > 0.7:
                    conf = Confidence.MEDIUM
                else:
                    conf = Confidence.LOW

                if pred == "duplicate":
                    category = IssueCategory.AI_SUGGESTION
                    reason = f"Potential revision/copy marker detected in filename ({prob*100:.0f}% confidence)"
                else:
                    try:
                        category = IssueCategory(pred)
                    except ValueError:
                        category = IssueCategory.AI_SUGGESTION
                    reason = f"AI model classified as {pred} ({prob*100:.0f}% confidence)"

                issues.append(FileIssue(
                    path=meta.path,
                    category=category,
                    reason=f"AI model classified as {pred} ({prob*100:.0f}% confidence)",
                    size=meta.size,
                    confidence=conf,
                    source=IssueSource.CLASSIFIER
                ))
            return issues
        except Exception as e:
            return []

    def predict_single(self, metadata: FileMetadata) -> Tuple[str, float]:
        if not self.is_available() or not self.model:
            return "keep", 0.0

        try:
            df = self._prepare_dataframe([metadata])
            pred = self.model.predict(df)[0]
            prob = max(self.model.predict_proba(df)[0])
            return str(pred), float(prob)
        except Exception:
            return "keep", 0.0
