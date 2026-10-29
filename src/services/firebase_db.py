"""
================================================================================
DATA-TO-DIRT: Cloud Firestore Database Service
Handles 2,000 - 3,000+ users, class codes, teachers, deletion queues & stats.
================================================================================
"""

import os
import sys
import time
import json
import base64
from typing import Dict, Any, List, Optional
from pathlib import Path

# Try importing Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    try:
        from google.cloud.firestore_v1.base_query import FieldFilter
    except ImportError:
        FieldFilter = None
    HAS_FIREBASE = True
except ImportError:
    HAS_FIREBASE = False
    FieldFilter = None


class FirestoreDB:
    def __init__(self):
        self.db = None
        self.is_connected = False
        self._init_firebase()

    def _init_firebase(self):
        if os.environ.get("TEST_MODE") == "1" or "unittest" in sys.modules or "pytest" in sys.modules:
            print("[i] Running in test environment. Cloud Firestore is isolated in standby mode to protect production data.")
            self.is_connected = False
            return

        if not HAS_FIREBASE:
            print("[-] firebase-admin not installed. Running in local fallback mode.")
            return

        # 1. Check if service account JSON or Base64 is passed via environment variable
        env_b64 = os.environ.get("FIREBASE_KEY_BASE64")
        env_key_json = os.environ.get("FIREBASE_KEY_JSON")
        if env_b64:
            try:
                env_key_json = base64.b64decode(env_b64).decode("utf-8")
            except Exception as b_err:
                print(f"[!] FIREBASE_KEY_BASE64 decode notice: {b_err}")

        if env_key_json:
            try:
                cert_dict = json.loads(env_key_json)
                if "private_key" in cert_dict and isinstance(cert_dict["private_key"], str):
                    cert_dict["private_key"] = cert_dict["private_key"].replace("\\n", "\n")
                cred = credentials.Certificate(cert_dict)
                if not firebase_admin._apps:
                    firebase_admin.initialize_app(cred)
                db_name = os.environ.get("FIREBASE_DATABASE_ID", "datatodirt")
                try:
                    self.db = firestore.client(database_id=db_name)
                except Exception:
                    self.db = firestore.client()
                self.is_connected = True
                print(f"[✓] Connected to Cloud Firestore database '{db_name}' using environment variable credentials")
                return
            except Exception as e:
                print(f"[!] FIREBASE_KEY_JSON parse notice: {e}")

        # 2. Check for service account key file in common locations (including Render /etc/secrets)
        key_paths = [
            Path("/etc/secrets/firebase_key.json"),
            Path("/etc/secrets/serviceAccountKey.json"),
            Path("firebase_key.json"),
            Path("firebase_key.json.json"),
            Path("serviceAccountKey.json"),
            Path(".env_firebase.json"),
            Path("data/firebase_key.json"),
            Path(os.environ.get("FIREBASE_KEY_PATH", "firebase_key.json"))
        ]

        key_file = None
        for p in key_paths:
            if p.exists():
                key_file = str(p)
                break

        try:
            if key_file:
                cred = credentials.Certificate(key_file)
                if not firebase_admin._apps:
                    firebase_admin.initialize_app(cred)
                
                # Connect directly to custom Firestore database 'datatodirt'
                db_name = os.environ.get("FIREBASE_DATABASE_ID", "datatodirt")
                try:
                    self.db = firestore.client(database_id=db_name)
                    self.is_connected = True
                    print(f"[✓] Connected to Cloud Firestore database '{db_name}' using key: {key_file}")
                except Exception as db_err:
                    self.db = firestore.client()
                    self.is_connected = True
                    print(f"[✓] Connected to default Cloud Firestore using key: {key_file} ({db_err})")
            else:
                # Try default application credentials if running in GCP or gcloud logged in
                try:
                    if not firebase_admin._apps:
                        firebase_admin.initialize_app()
                    self.db = firestore.client()
                    self.is_connected = True
                    print("[✓] Connected to Cloud Firestore using Default Application Credentials!")
                except Exception:
                    print("[!] No firebase_key.json found. FirestoreDB is in standby mode.")
                    print("[i] To activate Cloud Firestore: Download your serviceAccountKey.json from Firebase Console and save it as 'firebase_key.json' in the project root.")
        except Exception as e:
            print(f"[!] Firestore initialization failed: {e}")
            self.is_connected = False

    # --------------------------------------------------------------------------
    # User Management (Supports 3,000+ Students, Teachers & Admins)
    # --------------------------------------------------------------------------

    def get_or_create_user(self, user_id: str, role: str = "student", class_code: str = "", name: str = "") -> Dict[str, Any]:
        """Fetches or registers a user (Student/Teacher/Admin) with class codes and tracking."""
        if not self.is_connected:
            return {
                "user_id": user_id,
                "role": role,
                "class_code": class_code or "default",
                "name": name or user_id,
                "bytes_cleared": 0,
                "eco_points": 0,
                "trees": 0,
                "streak_days": 1,
                "daily_deletions_today": 0,
                "daily_deletion_limit": 5,
                "strikes": 0
            }

        doc_ref = self.db.collection("users").document(user_id)
        doc = doc_ref.get()

        if doc.exists:
            data = doc.to_dict()
            today = time.strftime("%Y-%m-%d")
            # Enforce individual daily deletion reset per user when new calendar day arrives
            if data.get("last_deletion_date") != today:
                data["daily_deletions_today"] = 0
                data["last_deletion_date"] = today
                try:
                    doc_ref.update({
                        "daily_deletions_today": 0,
                        "last_deletion_date": today,
                        "last_active": firestore.SERVER_TIMESTAMP
                    })
                except Exception:
                    pass
            else:
                try:
                    doc_ref.update({"last_active": firestore.SERVER_TIMESTAMP})
                except Exception:
                    pass
            return data

        # Create new user record
        today = time.strftime("%Y-%m-%d")
        new_user = {
            "user_id": user_id,
            "name": name or user_id,
            "role": role,
            "class_code": class_code.lower().strip() or "general",
            "bytes_cleared": 0,
            "carbon_offset_g": 0.0,
            "eco_points": 0,
            "trees": 0,
            "streak_days": 1,
            "daily_deletions_today": 0,
            "daily_deletion_limit": 5,
            "last_deletion_date": today,
            "strikes": 0,
            "created_at": firestore.SERVER_TIMESTAMP,
            "last_active": firestore.SERVER_TIMESTAMP
        }
        doc_ref.set(new_user)

        # Update class directory
        self._update_class_stats(new_user["class_code"], student_delta=1)
        return new_user

    def create_student_record(self, student_id: str, name: str, class_code: str, created_by: str = "Teacher") -> Dict[str, Any]:
        """Creates and stores a new student record in Firebase Firestore and class directory."""
        clean_id = (student_id or "").strip()
        clean_name = (name or "").strip() or clean_id
        clean_class = (class_code or "").strip().lower() or "general"
        
        if not clean_id:
            import uuid
            clean_id = f"STU-{uuid.uuid4().hex[:6].upper()}"
            
        record = {
            "user_id": clean_id,
            "student_id": clean_id,
            "name": clean_name,
            "role": "student",
            "class_code": clean_class,
            "created_by": created_by,
            "bytes_cleared": 0,
            "carbon_offset_g": 0.0,
            "eco_points": 0,
            "trees": 0,
            "streak_days": 1,
            "daily_deletions_today": 0,
            "daily_deletion_limit": 5,
            "last_deletion_date": time.strftime("%Y-%m-%d"),
            "strikes": 0,
            "created_at_iso": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        if self.is_connected:
            try:
                doc_ref = self.db.collection("users").document(clean_id)
                existing = doc_ref.get()
                if existing.exists:
                    return {"status": "error", "message": f"Student ID '{clean_id}' already exists."}
                
                db_payload = dict(record)
                db_payload["created_at"] = firestore.SERVER_TIMESTAMP
                db_payload["last_active"] = firestore.SERVER_TIMESTAMP
                doc_ref.set(db_payload)
                self._update_class_stats(clean_class, student_delta=1)
            except Exception as e:
                print(f"[!] Firestore create_student_record error: {e}")

        return {"status": "success", "student": record}

    def create_teacher_record(self, teacher_id: str, name: str, class_code: str, pin: str = "teacher123", created_by: str = "Admin") -> Dict[str, Any]:
        """Creates and stores a new teacher record in Firebase Firestore."""
        clean_id = (teacher_id or "").strip()
        clean_name = (name or "").strip() or clean_id
        clean_class = (class_code or "").strip().lower() or "all"
        clean_pin = (pin or "").strip() or "teacher123"

        if not clean_id:
            import uuid
            clean_id = f"TCH-{uuid.uuid4().hex[:6].upper()}"

        record = {
            "user_id": clean_id,
            "teacher_id": clean_id,
            "name": clean_name,
            "role": "teacher",
            "class_code": clean_class,
            "pin": clean_pin,
            "password": clean_pin,
            "created_by": created_by,
            "created_at_iso": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        if self.is_connected:
            try:
                doc_ref = self.db.collection("users").document(clean_id)
                existing = doc_ref.get()
                if existing.exists:
                    return {"status": "error", "message": f"Teacher ID '{clean_id}' already exists."}

                db_payload = dict(record)
                db_payload["created_at"] = firestore.SERVER_TIMESTAMP
                db_payload["last_active"] = firestore.SERVER_TIMESTAMP
                doc_ref.set(db_payload)
            except Exception as e:
                print(f"[!] Firestore create_teacher_record error: {e}")

        return {"status": "success", "teacher": record}

    def get_teachers_list(self, limit: int = 250) -> List[Dict[str, Any]]:
        """Retrieves registered teacher directory from Cloud Firestore."""
        if not self.is_connected:
            return []

        try:
            if FieldFilter:
                query = self.db.collection("users").where(filter=FieldFilter("role", "==", "teacher"))
            else:
                query = self.db.collection("users").where("role", "==", "teacher")
            docs = query.limit(limit).stream()
            teachers = []
            for d in docs:
                data = d.to_dict()
                created_at = data.get("created_at_iso")
                if not created_at and "created_at" in data:
                    created_at = str(data["created_at"])
                teachers.append({
                    "teacher_id": data.get("teacher_id") or data.get("user_id") or d.id,
                    "name": data.get("name", ""),
                    "class_code": data.get("class_code", ""),
                    "role": "teacher",
                    "pin": data.get("pin", "teacher123"),
                    "created_at_iso": created_at or "",
                    "created_by": data.get("created_by", "Admin")
                })
            return teachers
        except Exception as e:
            print(f"[!] Firestore get_teachers error: {e}")
            return []

    def get_students_list(self, class_code: str = "", limit: int = 250) -> List[Dict[str, Any]]:
        """Retrieves registered student directory from Cloud Firestore."""
        if not self.is_connected:
            return []

        try:
            clean_class = class_code.lower().strip() if class_code else ""
            if clean_class in ["all", "*", "any", "admin2026", "admin"]:
                clean_class = ""

            if FieldFilter:
                query = self.db.collection("users").where(filter=FieldFilter("role", "==", "student"))
                if clean_class:
                    query = query.where(filter=FieldFilter("class_code", "==", clean_class))
            else:
                query = self.db.collection("users").where("role", "==", "student")
                if clean_class:
                    query = query.where("class_code", "==", clean_class)
            docs = query.limit(limit).stream()
            students = []
            for d in docs:
                data = d.to_dict()
                created_at = data.get("created_at_iso")
                if not created_at and "created_at" in data:
                    created_at = str(data["created_at"])
                students.append({
                    "student_id": data.get("student_id") or data.get("user_id") or d.id,
                    "name": data.get("name", ""),
                    "class_code": data.get("class_code", ""),
                    "eco_points": data.get("eco_points", 0),
                    "bytes_cleared": data.get("bytes_cleared", 0),
                    "trees": data.get("trees", 0),
                    "created_by": data.get("created_by", "Teacher"),
                    "created_at": created_at or "Active"
                })
            return students
        except Exception as e:
            print(f"[!] Firestore get_students_list error: {e}")
            return []

    def update_user_stats(self, user_id: str, bytes_delta: int, points_delta: int, trees_delta: int = 0):
        """Atomically updates an individual student's carbon, data and tree progress and daily deletions."""
        if not self.is_connected or not user_id:
            return

        doc_ref = self.db.collection("users").document(user_id)
        doc = doc_ref.get()
        if not doc.exists:
            return

        user_data = doc.to_dict()
        today = time.strftime("%Y-%m-%d")
        last_date = user_data.get("last_deletion_date")

        # If today is a new calendar day for this individual student, reset their deletions to 1 for today
        if last_date != today:
            doc_ref.update({
                "bytes_cleared": firestore.Increment(bytes_delta),
                "eco_points": firestore.Increment(points_delta),
                "trees": firestore.Increment(trees_delta),
                "daily_deletions_today": 1,
                "last_deletion_date": today,
                "last_active": firestore.SERVER_TIMESTAMP
            })
        else:
            doc_ref.update({
                "bytes_cleared": firestore.Increment(bytes_delta),
                "eco_points": firestore.Increment(points_delta),
                "trees": firestore.Increment(trees_delta),
                "daily_deletions_today": firestore.Increment(1),
                "last_deletion_date": today,
                "last_active": firestore.SERVER_TIMESTAMP
            })

        # Update class aggregation (bytes & trees only, NEVER daily deletions)
        class_code = user_data.get("class_code", "general")
        self._update_class_stats(class_code, bytes_delta=bytes_delta, trees_delta=trees_delta)

    # --------------------------------------------------------------------------
    # Class & Teacher Aggregations
    # --------------------------------------------------------------------------

    def _update_class_stats(self, class_code: str, student_delta: int = 0, bytes_delta: int = 0, trees_delta: int = 0):
        if not self.is_connected or not class_code:
            return
        class_ref = self.db.collection("classes").document(class_code)
        class_ref.set({
            "class_code": class_code,
            "students_count": firestore.Increment(student_delta),
            "total_bytes_cleared": firestore.Increment(bytes_delta),
            "total_trees_planted": firestore.Increment(trees_delta),
            "last_updated": firestore.SERVER_TIMESTAMP
        }, merge=True)

    def get_class_leaderboard(self, class_code: str = "", limit: int = 25) -> List[Dict[str, Any]]:
        """Returns leaderboard sorted by eco_points for a specific class or global."""
        if not self.is_connected:
            return []

        if FieldFilter:
            query = self.db.collection("users").where(filter=FieldFilter("role", "==", "student"))
            if class_code:
                query = query.where(filter=FieldFilter("class_code", "==", class_code.lower().strip()))
        else:
            query = self.db.collection("users").where("role", "==", "student")
            if class_code:
                query = query.where("class_code", "==", class_code.lower().strip())

        query = query.order_by("eco_points", direction=firestore.Query.DESCENDING).limit(limit)
        docs = query.stream()

        leaderboard = []
        for i, d in enumerate(docs):
            u = d.to_dict()
            leaderboard.append({
                "rank": i + 1,
                "user_id": u.get("user_id"),
                "name": u.get("name", u.get("user_id")),
                "class_code": u.get("class_code", ""),
                "eco_points": u.get("eco_points", 0),
                "data_cleared_bytes": u.get("bytes_cleared", 0),
                "streak_days": u.get("streak_days", 1),
                "trees": u.get("trees", 0)
            })
        return leaderboard

    # --------------------------------------------------------------------------
    # Teacher Deletion Queue
    # --------------------------------------------------------------------------

    def submit_deletion_request(self, req_data: Dict[str, Any]) -> str:
        """Saves a pending deletion review request into Firestore."""
        if not self.is_connected:
            return ""

        req_id = req_data.get("request_id") or f"REQ-{int(time.time()*1000)}"
        doc_ref = self.db.collection("deletion_queue").document(req_id)
        payload = dict(req_data)
        payload["request_id"] = req_id
        payload["created_at"] = firestore.SERVER_TIMESTAMP
        payload["status"] = "PENDING"
        doc_ref.set(payload)
        return req_id

    def get_teacher_queue(self, class_code: str = "", status: str = "PENDING", limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves requests awaiting verification by teachers."""
        if not self.is_connected:
            return []

        query = self.db.collection("deletion_queue")
        if status:
            if FieldFilter:
                query = query.where(filter=FieldFilter("status", "==", status))
            else:
                query = query.where("status", "==", status)
        if class_code:
            if FieldFilter:
                query = query.where(filter=FieldFilter("class_code", "==", class_code.lower().strip()))
            else:
                query = query.where("class_code", "==", class_code.lower().strip())

        docs = query.limit(limit).stream()
        return [d.to_dict() for d in docs]

    def update_deletion_status(self, request_id: str, action: str, reviewer_id: str = "") -> bool:
        """Approves, rejects, or flags a student's deletion submission."""
        if not self.is_connected:
            return False

        doc_ref = self.db.collection("deletion_queue").document(request_id)
        status_map = {
            "approve": "APPROVED",
            "reject": "REJECTED",
            "flag": "FLAGGED"
        }
        new_status = status_map.get(action, "REVIEWED")

        doc_ref.update({
            "status": new_status,
            "reviewed_by": reviewer_id,
            "reviewed_at": firestore.SERVER_TIMESTAMP
        })
        return True


# Global Firestore Singleton
firestore_db = FirestoreDB()
