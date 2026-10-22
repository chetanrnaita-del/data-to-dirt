"""
Data-to-Dirt — Seed 50 Student IDs across 5 Teacher Accounts
Populates Cloud Firestore (database 'datatodirt') and local app_state.json.
Each teacher has exactly 10 students strictly associated with their class.
"""

import json
import time
from pathlib import Path
from src.services.firebase_db import firestore_db

TEACHERS = [
    {
        "teacher_id": "teacher_bio101",
        "name": "Dr. Evelyn Reed (Biology)",
        "class_code": "bio101",
        "pin": "teacher123",
        "students": [
            ("STU-BIO-001", "Maya Lin"),
            ("STU-BIO-002", "Liam Tanaka"),
            ("STU-BIO-003", "Sophia Martinez"),
            ("STU-BIO-004", "Ethan Dubois"),
            ("STU-BIO-005", "Chloe Zhang"),
            ("STU-BIO-006", "Noah Al-Mansoor"),
            ("STU-BIO-007", "Emma Kowalski"),
            ("STU-BIO-008", "Lucas Silva"),
            ("STU-BIO-009", "Olivia Rossi"),
            ("STU-BIO-010", "Benjamin Vance"),
        ]
    },
    {
        "teacher_id": "teacher_env201",
        "name": "Prof. Marcus Green (Environmental Science)",
        "class_code": "env201",
        "pin": "teacher123",
        "students": [
            ("STU-ENV-001", "Daniel Park"),
            ("STU-ENV-002", "Isabella Santos"),
            ("STU-ENV-003", "Alexander Wright"),
            ("STU-ENV-004", "Mia Johansson"),
            ("STU-ENV-005", "William Chen"),
            ("STU-ENV-006", "Charlotte Mueller"),
            ("STU-ENV-007", "Henry O'Connor"),
            ("STU-ENV-008", "Amara Diallo"),
            ("STU-ENV-009", "James Becker"),
            ("STU-ENV-010", "Grace Kim"),
        ]
    },
    {
        "teacher_id": "teacher_cs301",
        "name": "Ms. Clara Patel (Computer Science)",
        "class_code": "cs301",
        "pin": "teacher123",
        "students": [
            ("STU-CS-001", "Aiden Gupta"),
            ("STU-CS-002", "Zoe Campbell"),
            ("STU-CS-003", "Leo Fernandez"),
            ("STU-CS-004", "Ava Robinson"),
            ("STU-CS-005", "Mason Takahashi"),
            ("STU-CS-006", "Harper Nelson"),
            ("STU-CS-007", "Elijah Morales"),
            ("STU-CS-008", "Evelyn Hughes"),
            ("STU-CS-009", "Logan Weber"),
            ("STU-CS-010", "Abigail Taylor"),
        ]
    },
    {
        "teacher_id": "teacher_chem102",
        "name": "Dr. Arthur Thorne (Chemistry)",
        "class_code": "chem102",
        "pin": "teacher123",
        "students": [
            ("STU-CHM-001", "Oliver Brooks"),
            ("STU-CHM-002", "Scarlett Murphy"),
            ("STU-CHM-003", "Sebastian Diaz"),
            ("STU-CHM-004", "Emily Fischer"),
            ("STU-CHM-005", "Jackson Bennett"),
            ("STU-CHM-006", "Layla Moreau"),
            ("STU-CHM-007", "Carter Jenkins"),
            ("STU-CHM-008", "Penelope Zhao"),
            ("STU-CHM-009", "Wyatt Larson"),
            ("STU-CHM-010", "Nora Keller"),
        ]
    },
    {
        "teacher_id": "teacher_earth204",
        "name": "Mr. Samuel Woods (Earth Systems)",
        "class_code": "earth204",
        "pin": "teacher123",
        "students": [
            ("STU-EAR-001", "Julian Meyer"),
            ("STU-EAR-002", "Lily Hansen"),
            ("STU-EAR-003", "Gabriel Ortiz"),
            ("STU-EAR-004", "Hannah Schwartz"),
            ("STU-EAR-005", "Owen Navarro"),
            ("STU-EAR-006", "Victoria Rossi"),
            ("STU-EAR-007", "Caleb Novak"),
            ("STU-EAR-008", "Stella Bergman"),
            ("STU-EAR-009", "Luke Wagner"),
            ("STU-EAR-010", "Maya Lindstrom"),
        ]
    }
]


def seed_all():
    print(f"[+] Starting seed: 5 Teachers, 50 Students...")
    print(f"[+] Firestore connected: {firestore_db.is_connected}")

    all_students_list = []
    
    # 1. Iterate through each teacher and their 10 students
    for t_idx, t in enumerate(TEACHERS, start=1):
        t_id = t["teacher_id"]
        t_name = t["name"]
        class_code = t["class_code"]
        print(f"\n[Teacher {t_idx}/5] {t_name} (Class: {class_code})")

        # Save teacher in Firestore
        if firestore_db.is_connected:
            try:
                firestore_db.db.collection("users").document(t_id).set({
                    "user_id": t_id,
                    "teacher_id": t_id,
                    "name": t_name,
                    "role": "teacher",
                    "class_code": class_code,
                    "students_count": len(t["students"]),
                    "created_at_iso": time.strftime("%Y-%m-%d %H:%M:%S")
                })
                # Also save class document
                firestore_db.db.collection("classes").document(class_code).set({
                    "class_code": class_code,
                    "teacher_id": t_id,
                    "teacher_name": t_name,
                    "students_count": len(t["students"]),
                    "created_at_iso": time.strftime("%Y-%m-%d %H:%M:%S")
                }, merge=True)
            except Exception as e:
                print(f"  [!] Teacher {t_id} firestore error: {e}")

        # Seed 10 students
        for sid, sname in t["students"]:
            rec = {
                "user_id": sid,
                "student_id": sid,
                "name": sname,
                "role": "student",
                "class_code": class_code,
                "created_by": t_name,
                "bytes_cleared": 0,
                "carbon_offset_g": 0.0,
                "eco_points": 0,
                "trees": 0,
                "streak_days": 1,
                "daily_deletions_today": 0,
                "daily_deletion_limit": 5,
                "strikes": 0,
                "created_at_iso": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            all_students_list.append(rec)

            if firestore_db.is_connected:
                try:
                    firestore_db.db.collection("users").document(sid).set(rec)
                    print(f"  [✓] Firestore: {sid} ({sname})")
                except Exception as e:
                    print(f"  [!] Firestore write error for {sid}: {e}")

    # 2. Update local app_state.json with all 50 students and teachers
    state_path = Path("data/app_state.json")
    if state_path.exists():
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
    else:
        state = {}

    state["students"] = all_students_list
    state["teachers"] = [
        {"teacher_id": t["teacher_id"], "name": t["name"], "class_code": t["class_code"]}
        for t in TEACHERS
    ]

    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    print(f"\n[✓] Successfully persisted {len(all_students_list)} students to local app_state.json and Cloud Firestore!")


if __name__ == "__main__":
    seed_all()
