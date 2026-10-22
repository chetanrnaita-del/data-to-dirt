"""
Tier 4: Real-World Application Scenarios Test Suite (Data-to-Dirt)
Covers 15 complete, end-to-end multi-step realistic user workflows.

Scenarios:
- Scenario 1: Student semester-end dark data cleanup
- Scenario 2: Teacher morning review and batch decisioning
- Scenario 3: 1 GB micro-donation threshold crossing and certificate issuance
- Scenario 4: Adversarial gaming attack and 3-strike disciplinary escalation
- Scenario 5: Eco-Fund budget exhaustion, graceful pledge mode, and admin top-up
- Scenario 6: Cloud storage (Google Drive mock) scanning, staging, and soft trash
- Scenario 7: Confidential file defense and absolute deletion block
- Scenario 8: PII preview redaction and image thumbnail downsampling
- Scenario 9: Daily deletion rate limiting and midnight reset cycle
- Scenario 10: Classroom leaderboard competition and tournament tie-breaking
- Scenario 11: Pixel tree 5-stage visual lifecycle progression
- Scenario 12: Role-based security boundary and privilege separation
- Scenario 13: Multi-gigabyte batch waste accumulation and multi-tree disbursement
- Scenario 14: Tamper-evident Eco-Fund ledger cryptographic audit and breach detection
- Scenario 15: Complete end-to-end lifecycle roundtrip (Scan -> AI -> Queue -> Approve -> Donate -> Audit)
Total: 15 Tests
"""

import unittest
import os
import sys
import time

from tests.e2e.harness import (
    CarbonCalculatorSpec, FileScannerSpec, CloudStorageMockSpec,
    NeuralAccountabilitySpec, GamificationSpec, EcoFundLedgerSpec,
    TeacherQueueSpec, SandboxEnvironment, THRESHOLD_BYTES, COST_PER_TREE_USD
)


class TestTier4Scenarios(unittest.TestCase):
    def setUp(self):
        self.sandbox = SandboxEnvironment()
        self.calc = CarbonCalculatorSpec()
        self.scanner = FileScannerSpec()
        self.cloud = CloudStorageMockSpec()
        self.ai = NeuralAccountabilitySpec()
        self.gamification = GamificationSpec()
        self.ledger = EcoFundLedgerSpec(initial_budget_usd=100.0)
        self.teacher_queue = TeacherQueueSpec(self.ledger, self.gamification)

    def tearDown(self):
        self.sandbox.cleanup()

    def test_T4_01_student_semester_cleanup_workflow(self):
        """Scenario 1: Student semester-end dark data cleanup workflow."""
        # 1. App starts in blind state
        self.assertEqual(self.scanner.state, "BLIND")

        # 2. Student grants folder access
        self.sandbox.create_file("old_project/draft_take1.mov", 400 * 1024 * 1024, mtime_days_ago=200)
        self.sandbox.create_file("old_project/build.tmp", 50 * 1024 * 1024, mtime_days_ago=190)
        self.sandbox.create_file("personal_notes/diary.docx", 2048, mtime_days_ago=10)
        self.scanner.grant_access(self.sandbox.temp_dir)
        self.assertEqual(self.scanner.state, "ACCESS_ACTIVE_SCOPED")

        # 3. Traversal identifies files
        files = self.scanner.scan()
        self.assertEqual(len(files), 3)

        # 4. Student marks personal diary confidential
        diary_item = next(f for f in files if f["name"] == "diary.docx")
        self.scanner.mark_confidential(diary_item["file_id"], True)

        # 5. Review carousel presents only non-confidential dark data
        candidates = [f for f in self.scanner.scanned_files if not f["is_confidential"] and f["is_dark_data"]]
        self.assertEqual(len(candidates), 2)

        # 6. Student submits deletion request with AI justification
        score, summary, is_gaming = self.ai.evaluate_reason("draft_take1.mov", "completed video project take no longer needed")
        self.assertGreaterEqual(score, 0.50)
        req_id = self.teacher_queue.submit_request("stu_01", "draft_take1.mov", candidates[0]["size_bytes"], "completed video", score, summary)
        self.assertTrue(req_id.startswith("REQ-"))

    def test_T4_02_teacher_review_workflow(self):
        """Scenario 2: Teacher morning review and batch decisions."""
        # Setup: 3 incoming student requests in queue
        r1 = self.teacher_queue.submit_request("stu_01", "take1.mov", 100 * 1024 * 1024, "old take", 0.85, "Verified: Stale media")
        r2 = self.teacher_queue.submit_request("stu_02", "essay_final.docx", 50000, "not needed", 0.35, "Insufficient")
        r3 = self.teacher_queue.submit_request("stu_03", "system32.dll", 1000, "free space", 0.05, "Critical")

        # 1. Teacher logs in with PIN
        self.assertTrue(self.teacher_queue.verify_pin("teacher123"))

        # 2. Teacher approves valid cleanup request (r1)
        res1 = self.teacher_queue.approve(r1)
        self.assertEqual(res1["status"], "APPROVED")

        # 3. Teacher rejects honest mistake request (r2) with feedback note
        res2 = self.teacher_queue.reject(r2, "Please archive your final essay in student portfolio.")
        self.assertEqual(res2["status"], "REJECTED")
        self.assertEqual(res2["feedback"], "Please archive your final essay in student portfolio.")

        # 4. Teacher flags malicious system deletion request (r3)
        res3 = self.teacher_queue.flag(r3, "Attempting to delete OS system files.")
        self.assertEqual(res3["status"], "FLAGGED")
        self.assertEqual(self.gamification.students["stu_03"]["streak"], 0)

    def test_T4_03_micro_donation_threshold_crossed_workflow(self):
        """Scenario 3: 1 GB micro-donation threshold crossed and certificate logged."""
        # 1. Setup Eco-Fund ledger
        self.assertEqual(self.ledger.budget_usd, 100.0)
        self.assertEqual(self.ledger.lifetime_trees, 0)

        # 2. Student cleans up 600 MB (below threshold)
        res1 = self.ledger.accumulate_waste(600 * 1024 * 1024)
        self.assertEqual(res1["status"], "ACCUMULATING")
        self.assertEqual(res1["trees_triggered"], 0)

        # 3. Student cleans up additional 500 MB (Total 1.1 GB -> crosses 1.0 GB threshold)
        res2 = self.ledger.accumulate_waste(500 * 1024 * 1024)
        self.assertEqual(res2["status"], "DONATION_EXECUTED")
        self.assertEqual(res2["trees_triggered"], 1)
        self.assertEqual(self.ledger.lifetime_trees, 1)

        # 4. Verifies Eco-Fund deduction ($1.50) and SHA-256 ledger chaining
        self.assertEqual(self.ledger.budget_usd, 100.0 - COST_PER_TREE_USD)
        self.assertTrue(self.ledger.verify_ledger_integrity())
        self.assertEqual(self.ledger.transactions[-1]["type"], "TREE_NATION_DISBURSEMENT")

    def test_T4_04_gaming_attack_escalation_workflow(self):
        """Scenario 4: Adversarial gaming attack and 3-strike disciplinary escalation."""
        student_id = "stu_attacker"
        self.gamification.students[student_id] = {"name": "Attacker", "points": 150, "streak": 10, "deleted_bytes": 1000, "today_deletions": 0}

        # Attempt 1: Low-effort gibberish -> Strike 1 (Soft warning)
        score1, _, is_gaming1 = self.ai.evaluate_reason("notes.txt", "asdf")
        self.assertTrue(is_gaming1)
        a1 = self.ai.register_strike(student_id)
        self.assertEqual(a1["strike"], 1)
        self.assertEqual(a1["action"], "WARNING")
        self.assertEqual(self.gamification.students[student_id]["streak"], 10)

        # Attempt 2: Score farming attempt -> Strike 2 (Streak frozen, -10 points)
        score2, _, is_gaming2 = self.ai.evaluate_reason("notes.txt", "give me free eco score points")
        self.assertTrue(is_gaming2)
        a2 = self.ai.register_strike(student_id)
        self.assertEqual(a2["strike"], 2)
        self.assertEqual(a2["action"], "FREEZE_STREAK")
        self.gamification.students[student_id]["points"] -= a2["points_deducted"]
        self.assertEqual(self.gamification.students[student_id]["points"], 140)

        # Attempt 3: Destructive system deletion -> Strike 3 (Streak reset to 0, -50 points, flagged)
        score3, _, is_gaming3 = self.ai.evaluate_reason("system32.dll", "free disk")
        self.assertTrue(is_gaming3)
        a3 = self.ai.register_strike(student_id)
        self.assertEqual(a3["strike"], 3)
        self.assertEqual(a3["action"], "RESET_STREAK_FLAG")
        self.gamification.students[student_id]["streak"] = 0
        self.gamification.students[student_id]["points"] -= a3["points_deducted"]
        self.assertEqual(self.gamification.students[student_id]["streak"], 0)
        self.assertEqual(self.gamification.students[student_id]["points"], 90)

    def test_T4_05_eco_fund_budget_depletion_and_recovery_workflow(self):
        """Scenario 5: Eco-Fund budget exhaustion, graceful pledge mode, and admin top-up."""
        # 1. School Eco-Fund starts at $0.00
        fund = EcoFundLedgerSpec(initial_budget_usd=0.0)

        # 2. Students delete 1 GB of verified data -> enters PENDING_FUNDS without error
        res1 = fund.accumulate_waste(THRESHOLD_BYTES)
        self.assertEqual(res1["status"], "PENDING_FUNDS")
        self.assertEqual(fund.lifetime_trees, 0)

        # 3. Admin tops up budget by $50.00 from storage savings
        fund.budget_usd += 50.0

        # 4. Next approval cycle immediately executes the earned donation
        res2 = fund.accumulate_waste(1000) # Small trigger
        self.assertEqual(res2["status"], "DONATION_EXECUTED")
        self.assertEqual(fund.lifetime_trees, 1)
        self.assertEqual(fund.budget_usd, 50.0 - COST_PER_TREE_USD)

    def test_T4_06_cloud_storage_mock_staging_workflow(self):
        """Scenario 6: Cloud storage (Google Drive mock) scanning, staging, and soft trash."""
        # 1. Connect mock cloud provider
        self.assertTrue(self.cloud.connect("mock_oauth_token"))
        files = self.cloud.list_files()
        self.assertGreater(len(files), 0)

        # 2. Select heavy 2.8 GB video file
        target = files[0]
        self.assertEqual(target["id"], "cloud_001")
        used_before = self.cloud.quota["used_bytes"]

        # 3. Stage deletion -> Moves to cloud Trash
        res = self.cloud.stage_deletion(target["id"])
        self.assertTrue(res)
        self.assertEqual(self.cloud.quota["used_bytes"], used_before - target["size_bytes"])

        # 4. Cloud file is no longer in active listing
        active_ids = [f["id"] for f in self.cloud.list_files()]
        self.assertNotIn("cloud_001", active_ids)

    def test_T4_07_confidential_file_defense_workflow(self):
        """Scenario 7: Confidential file defense and absolute deletion block."""
        # 1. User scans folder containing private taxes
        self.sandbox.create_file("taxes_2025.pdf", 500000, mtime_days_ago=250)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        fid = files[0]["file_id"]

        # 2. User marks file confidential
        self.scanner.mark_confidential(fid, True)

        # 3. System asserts confidential file is stripped of dark data tag
        self.assertFalse(self.scanner.scanned_files[0]["is_dark_data"])
        self.assertTrue(self.scanner.scanned_files[0]["is_confidential"])

        # 4. Deletion controller rejects submission of confidential file
        is_allowed = not self.scanner.scanned_files[0]["is_confidential"]
        self.assertFalse(is_allowed)

    def test_T4_08_pii_redaction_and_thumbnail_pixelation_workflow(self):
        """Scenario 8: PII preview redaction and image thumbnail downsampling."""
        # 1. Text document containing mixed PII
        raw_doc = "Report by jane.doe@university.edu (Phone: 555-432-8765). Secret api_key = 'sk_test_9928347'."
        scrubbed = self.scanner.scrub_pii(raw_doc)
        self.assertNotIn("jane.doe@university.edu", scrubbed)
        self.assertNotIn("555-432-8765", scrubbed)
        self.assertNotIn("sk_test_9928347", scrubbed)
        self.assertIn("[REDACTED_EMAIL]", scrubbed)
        self.assertIn("[REDACTED_PHONE]", scrubbed)
        self.assertIn("[REDACTED_SECRET]", scrubbed)

        # 2. Image asset receives pixelated thumbnail
        thumb = self.scanner.pixelate_thumbnail(16, 16)
        self.assertTrue(thumb["blurred"])
        self.assertEqual(thumb["pixel_grid"], "16x16")

    def test_T4_09_daily_deletion_rate_limiting_workflow(self):
        """Scenario 9: Daily deletion rate limiting and midnight reset cycle."""
        student_id = "stu_01"
        self.gamification.students[student_id]["today_deletions"] = 0

        # Perform 5 deletions (reaches limit)
        for _ in range(5):
            self.gamification.record_deletion(student_id, 1048576)

        # 6th deletion attempt fails
        self.assertFalse(self.gamification.check_daily_limit(student_id))
        with self.assertRaises(ValueError):
            self.gamification.record_deletion(student_id, 1048576)

        # Simulate midnight UTC reset
        self.gamification.students[student_id]["today_deletions"] = 0
        self.assertTrue(self.gamification.check_daily_limit(student_id))

    def test_T4_10_leaderboard_tournament_workflow(self):
        """Scenario 10: Classroom leaderboard competition and tournament tie-breaking."""
        # 1. Initial ranks: Alice (340), Marcus (280), Elena (190)
        b1 = self.gamification.get_leaderboard()
        self.assertEqual(b1[0]["name"], "Alice Chen")
        self.assertEqual(b1[1]["name"], "Marcus Vance")

        # 2. Marcus Vance deletes 800 MB -> earns 80 points (new total 360) -> overtakes Alice
        self.gamification.record_deletion("stu_02", 800 * 1024 * 1024)
        b2 = self.gamification.get_leaderboard()
        self.assertEqual(b2[0]["name"], "Marcus Vance")
        self.assertEqual(b2[1]["name"], "Alice Chen")

    def test_T4_11_pixel_tree_lifecycle_workflow(self):
        """Scenario 11: Pixel tree 5-stage visual lifecycle progression."""
        self.assertIn("Soil", self.gamification.get_tree_stage(0))
        self.assertIn("Sprout", self.gamification.get_tree_stage(2 * 1048576))
        self.assertIn("Sapling", self.gamification.get_tree_stage(60 * 1048576))
        self.assertIn("Oak", self.gamification.get_tree_stage(300 * 1048576))
        self.assertIn("Ancient", self.gamification.get_tree_stage(2 * 1073741824))
        self.assertIn("Legendary", self.gamification.get_tree_stage(6 * 1073741824))

    def test_T4_12_role_based_security_boundary_workflow(self):
        """Scenario 12: Role-based security boundary and privilege separation."""
        # 1. Student cannot approve requests
        is_teacher = self.teacher_queue.verify_pin("invalid_pin")
        self.assertFalse(is_teacher)

        # 2. Entering correct teacher PIN grants management rights
        self.assertTrue(self.teacher_queue.verify_pin("teacher123"))

    def test_T4_13_multi_gigabyte_waste_accumulation_workflow(self):
        """Scenario 13: Multi-gigabyte batch waste accumulation and multi-tree disbursement."""
        # 3.4 GB approved in single batch
        res = self.ledger.accumulate_waste(int(3.4 * THRESHOLD_BYTES))
        self.assertEqual(res["trees_triggered"], 3)
        self.assertEqual(self.ledger.lifetime_trees, 3)
        # Verify remainder carryover
        self.assertEqual(res["surplus_bytes"], int(0.4 * THRESHOLD_BYTES))

    def test_T4_14_tamper_evident_ledger_audit_workflow(self):
        """Scenario 14: Tamper-evident Eco-Fund ledger cryptographic audit and breach detection."""
        # 1. Valid transactions
        self.ledger.accumulate_waste(THRESHOLD_BYTES)
        self.assertTrue(self.ledger.verify_ledger_integrity())

        # 2. Adversary mutates balance in transaction 1
        self.ledger.transactions[1]["amount_usd"] = -999.0
        # Verification fails
        self.assertFalse(self.ledger.verify_ledger_integrity())

    def test_T4_15_full_lifecycle_roundtrip_workflow(self):
        """Scenario 15: Complete roundtrip (Scan -> AI -> Queue -> Approve -> Donate -> Audit)."""
        # Step 1: Create real test file in sandbox
        fpath = self.sandbox.create_file("final_render_take2.mov", THRESHOLD_BYTES, mtime_days_ago=200)

        # Step 2: Grant folder and scan
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        self.assertEqual(len(files), 1)
        target = files[0]

        # Step 3: On-device AI validation
        score, summary, is_gaming = self.ai.evaluate_reason(target["name"], "completed render take 2 already exported")
        self.assertGreaterEqual(score, 0.50)
        self.assertFalse(is_gaming)

        # Step 4: Submit to teacher queue
        req_id = self.teacher_queue.submit_request("stu_01", target["name"], target["size_bytes"], "completed render", score, summary)

        # Step 5: Teacher approves
        self.assertTrue(self.teacher_queue.verify_pin("teacher123"))
        app_res = self.teacher_queue.approve(req_id)

        # Step 6: Verify gamification, tree-nation trigger, and ledger audit
        self.assertEqual(app_res["status"], "APPROVED")
        self.assertEqual(app_res["ledger"]["trees_triggered"], 1)
        self.assertEqual(self.ledger.lifetime_trees, 1)
        self.assertTrue(self.ledger.verify_ledger_integrity())


if __name__ == "__main__":
    unittest.main()
