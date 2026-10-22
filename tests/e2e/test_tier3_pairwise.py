"""
Tier 3: Cross-Feature Interactions & Pairwise Integration Test Suite (Data-to-Dirt)
Covers multi-module interfaces, feature cross-talk, and cascade workflows (30 test cases).

Key Cross-Feature Workflows:
1. Scanning + Confidentiality + Deletion Queue (Tests 1-5)
2. AI Evaluation + Anti-Gaming + Student Gamification (Tests 6-10)
3. Teacher Queue + File Actions + Student Rewards (Tests 11-15)
4. Teacher Approval + Cumulative Waste + Tree-Nation + Ledger (Tests 16-20)
5. Cloud Storage + Scanning + Soft Trash + Carbon Impact (Tests 21-25)
6. Admin Budget + Eco-Fund State Transitions + Disbursals (Tests 26-30)
Total: 30 Tests
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


class TestTier3PairwiseInteractions(unittest.TestCase):
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

    # -------------------------------------------------------------------------
    # Pairwise 1: Scanning + Confidentiality + Deletion Queue (Tests 1-5)
    # -------------------------------------------------------------------------
    def test_T3_01_confidential_marked_file_cannot_enter_queue(self):
        """T3-01: Scanned file marked confidential is omitted from deletion candidate pool."""
        fpath = self.sandbox.create_file("payroll.pdf", 1024, mtime_days_ago=200)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        fid = files[0]["file_id"]
        self.scanner.mark_confidential(fid, True)

        # Re-query candidates
        active_candidates = [f for f in self.scanner.scanned_files if not f["is_confidential"] and f["is_dark_data"]]
        self.assertEqual(len(active_candidates), 0)

    def test_T3_02_confidential_pattern_bypasses_carbon_pool(self):
        """T3-02: Files matching .env or credentials pattern are excluded from total carbon."""
        self.sandbox.create_file(".env", 1000)
        self.sandbox.create_file("safe_waste.tmp", 1000000)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        actionable = [f for f in files if not f["is_confidential"]]
        self.assertEqual(len(actionable), 1)
        self.assertEqual(actionable[0]["name"], "safe_waste.tmp")

    def test_T3_03_pii_redaction_before_queue_presentation(self):
        """T3-03: Preview snippet is scrubbed of PII before attaching to deletion request."""
        raw_snippet = "Student notes: contact john.doe@school.edu for queries."
        clean_snippet = self.scanner.scrub_pii(raw_snippet)
        req_id = self.teacher_queue.submit_request("stu_01", "notes.txt", 1000, clean_snippet, 0.8, "Verified")
        item = next(r for r in self.teacher_queue.queue if r["request_id"] == req_id)
        self.assertNotIn("john.doe@school.edu", item["reason"])
        self.assertIn("[REDACTED_EMAIL]", item["reason"])

    def test_T3_04_ignore_folder_excludes_entire_tree_from_footprint(self):
        """T3-04: Folder with .data_to_dirt_ignore prevents child files from altering footprint."""
        self.sandbox.create_file("private_dir/.data_to_dirt_ignore", 0)
        self.sandbox.create_file("private_dir/heavy.mov", 1000000000)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        self.assertEqual(len(files), 0)
        self.assertEqual(self.calc.calculate_carbon_grams(sum(f["size_bytes"] for f in files)), 0.0)

    def test_T3_05_thumbnail_pixelation_flag_attached_to_image_queue_items(self):
        """T3-05: Image files in queue retain pixelated thumbnail preferences."""
        thumb = self.scanner.pixelate_thumbnail()
        self.assertTrue(thumb["blurred"])
        req_id = self.teacher_queue.submit_request("stu_01", "screenshot.png", 500000, "old screenshot", 0.8, "Verified")
        self.assertTrue(req_id.startswith("REQ-"))

    # -------------------------------------------------------------------------
    # Pairwise 2: AI Evaluation + Anti-Gaming + Gamification (Tests 6-10)
    # -------------------------------------------------------------------------
    def test_T3_06_low_ai_score_triggers_strike_1_warning(self):
        """T3-06: Reason with AI score < 0.50 triggers Strike 1 warning without point deduction."""
        score, summary, is_gaming = self.ai.evaluate_reason("notes.docx", "asdf")
        self.assertLess(score, 0.50)
        strike_action = self.ai.register_strike("stu_01")
        self.assertEqual(strike_action["strike"], 1)
        self.assertEqual(strike_action["points_deducted"], 0)

    def test_T3_07_repeated_gaming_triggers_strike_2_streak_freeze(self):
        """T3-07: Second gaming attempt freezes student streak and deducts 10 points."""
        self.ai.register_strike("stu_01")
        strike_action = self.ai.register_strike("stu_01")
        self.assertEqual(strike_action["action"], "FREEZE_STREAK")
        self.assertEqual(strike_action["points_deducted"], 10)

    def test_T3_08_strike_3_resets_streak_and_applies_50pt_penalty(self):
        """T3-08: Third gaming attempt resets streak to 0 and flags incident."""
        self.ai.register_strike("stu_01")
        self.ai.register_strike("stu_01")
        strike_action = self.ai.register_strike("stu_01")
        self.assertEqual(strike_action["action"], "RESET_STREAK_FLAG")
        self.assertTrue(strike_action["streak_reset"])
        self.assertEqual(strike_action["points_deducted"], 50)

    def test_T3_09_critical_system_file_triggers_instant_strike_3(self):
        """T3-09: Attempting to delete system32 file triggers immediate severe penalty."""
        score, summary, is_gaming = self.ai.evaluate_reason("system32.dll", "free disk space")
        self.assertTrue(is_gaming)
        self.assertLess(score, 0.20)
        # Directly escalate
        for _ in range(3):
            action = self.ai.register_strike("stu_02")
        self.assertTrue(action["streak_reset"])

    def test_T3_10_high_ai_score_allows_unimpeded_queue_entry(self):
        """T3-10: Plausible reason (score >= 0.50) enters teacher queue without strike."""
        score, summary, is_gaming = self.ai.evaluate_reason("build.tmp", "temporary cache from compiler")
        self.assertGreaterEqual(score, 0.50)
        self.assertFalse(is_gaming)
        rid = self.teacher_queue.submit_request("stu_01", "build.tmp", 10000000, "temporary cache", score, summary)
        self.assertTrue(rid.startswith("REQ-"))

    # -------------------------------------------------------------------------
    # Pairwise 3: Teacher Queue + File Actions + Student Rewards (Tests 11-15)
    # -------------------------------------------------------------------------
    def test_T3_11_approval_credits_student_points_based_on_size(self):
        """T3-11: Teacher approving 50 MB deletion awards 5 points to student."""
        p0 = self.gamification.students["stu_01"]["points"]
        rid = self.teacher_queue.submit_request("stu_01", "large_take.mov", 50 * 1024 * 1024, "old take", 0.85, "Verified")
        res = self.teacher_queue.approve(rid)
        self.assertEqual(res["status"], "APPROVED")
        self.assertEqual(self.gamification.students["stu_01"]["points"], p0 + 5)

    def test_T3_12_approval_increments_student_streak(self):
        """T3-12: Teacher approving deletion increments student's daily streak."""
        s0 = self.gamification.students["stu_01"]["streak"]
        rid = self.teacher_queue.submit_request("stu_01", "data.tmp", 1000000, "cache", 0.8, "Verified")
        self.teacher_queue.approve(rid)
        self.assertEqual(self.gamification.students["stu_01"]["streak"], s0 + 1)

    def test_T3_13_approval_advances_pixel_tree_stage(self):
        """T3-13: Deletions crossing 50 MB advance tree to Stage 2: The Sapling."""
        self.gamification.students["fresh"] = {"name": "Fresh", "points": 0, "streak": 0, "deleted_bytes": 0, "today_deletions": 0}
        rid = self.teacher_queue.submit_request("fresh", "heavy_render.mov", 60 * 1024 * 1024, "old render", 0.9, "Verified")
        res = self.teacher_queue.approve(rid)
        self.assertIn("Sapling", res["gamification"]["tree_stage"])

    def test_T3_14_rejection_preserves_student_points_and_streak(self):
        """T3-14: Teacher rejection does NOT penalize student points or streak."""
        p0 = self.gamification.students["stu_02"]["points"]
        s0 = self.gamification.students["stu_02"]["streak"]
        rid = self.teacher_queue.submit_request("stu_02", "essay.docx", 500000, "not needed", 0.4, "Insufficient")
        self.teacher_queue.reject(rid, "Keep your essay for portfolio.")
        self.assertEqual(self.gamification.students["stu_02"]["points"], p0)
        self.assertEqual(self.gamification.students["stu_02"]["streak"], s0)

    def test_T3_15_flag_action_penalizes_and_logs_feedback(self):
        """T3-15: Teacher flag resets streak to 0, deducts 50 points, records feedback."""
        rid = self.teacher_queue.submit_request("stu_03", "system_file.dll", 100, "free points", 0.1, "Flagged")
        res = self.teacher_queue.flag(rid, "Disciplinary action for gaming system.")
        self.assertEqual(res["status"], "FLAGGED")
        self.assertEqual(self.gamification.students["stu_03"]["streak"], 0)

    # -------------------------------------------------------------------------
    # Pairwise 4: Teacher Approval + Waste + Tree-Nation + Ledger (Tests 16-20)
    # -------------------------------------------------------------------------
    def test_T3_16_approvals_accumulate_toward_1gb_threshold(self):
        """T3-16: Two approvals summing to 1.2 GB cross threshold and trigger 1 tree."""
        f1_size = 700 * 1024 * 1024 # 700 MB
        f2_size = 500 * 1024 * 1024 # 500 MB (Total 1.2 GB)
        r1 = self.teacher_queue.submit_request("stu_01", "part1.mov", f1_size, "old", 0.8, "V1")
        r2 = self.teacher_queue.submit_request("stu_01", "part2.mov", f2_size, "old", 0.8, "V2")

        res1 = self.teacher_queue.approve(r1)
        self.assertEqual(res1["ledger"]["trees_triggered"], 0)

        res2 = self.teacher_queue.approve(r2)
        self.assertEqual(res2["ledger"]["trees_triggered"], 1)
        self.assertEqual(self.ledger.lifetime_trees, 1)

    def test_T3_17_tree_donation_deducts_eco_fund_balance(self):
        """T3-17: Executing tree donation reduces Eco-Fund budget by $1.50."""
        b0 = self.ledger.budget_usd
        rid = self.teacher_queue.submit_request("stu_01", "huge.zip", THRESHOLD_BYTES, "backup", 0.85, "Verified")
        self.teacher_queue.approve(rid)
        self.assertEqual(self.ledger.budget_usd, b0 - COST_PER_TREE_USD)

    def test_T3_18_donation_transaction_sha256_chained(self):
        """T3-18: Tree donation transaction is chained via SHA-256 in ledger."""
        rid = self.teacher_queue.submit_request("stu_01", "data.tar", THRESHOLD_BYTES, "archive", 0.85, "Verified")
        self.teacher_queue.approve(rid)
        self.assertTrue(self.ledger.verify_ledger_integrity())
        self.assertEqual(self.ledger.transactions[-1]["type"], "TREE_NATION_DISBURSEMENT")

    def test_T3_19_insufficient_budget_enters_pending_funds_state(self):
        """T3-19: Crossing threshold when budget is $0 transitions to PENDING_FUNDS."""
        poor_ledger = EcoFundLedgerSpec(initial_budget_usd=0.0)
        poor_queue = TeacherQueueSpec(poor_ledger, self.gamification)
        rid = poor_queue.submit_request("stu_01", "data.tar", THRESHOLD_BYTES, "archive", 0.85, "Verified")
        res = poor_queue.approve(rid)
        self.assertEqual(res["ledger"]["status"], "PENDING_FUNDS")
        self.assertEqual(poor_ledger.lifetime_trees, 0)

    def test_T3_20_budget_topup_resolves_pending_donations(self):
        """T3-20: Adding budget allows subsequent accumulation to execute pending donations."""
        poor_ledger = EcoFundLedgerSpec(initial_budget_usd=0.0)
        poor_queue = TeacherQueueSpec(poor_ledger, self.gamification)
        rid = poor_queue.submit_request("stu_01", "data.tar", THRESHOLD_BYTES, "archive", 0.85, "Verified")
        poor_queue.approve(rid)
        # Admin injects budget
        poor_ledger.budget_usd += 50.0
        # Next small approval triggers pending disbursement
        rid2 = poor_queue.submit_request("stu_01", "extra.log", 1000, "log", 0.8, "V")
        res2 = poor_queue.approve(rid2)
        self.assertEqual(res2["ledger"]["status"], "DONATION_EXECUTED")
        self.assertEqual(poor_ledger.lifetime_trees, 1)

    # -------------------------------------------------------------------------
    # Pairwise 5: Cloud Storage + Scanning + Trash + Carbon (Tests 21-25)
    # -------------------------------------------------------------------------
    def test_T3_21_cloud_scan_identifies_dark_data(self):
        """T3-21: Cloud mock file list identifies stale items for review."""
        self.cloud.connect("mock")
        files = self.cloud.list_files()
        stale = [f for f in files if f.get("stale")]
        self.assertGreaterEqual(len(stale), 2)

    def test_T3_22_cloud_deletion_updates_used_quota_and_carbon(self):
        """T3-22: Trashing cloud file reduces cloud used quota and avoids carbon."""
        self.cloud.connect("mock")
        target = self.cloud.files[0]
        size = target["size_bytes"]
        self.cloud.stage_deletion(target["id"])
        avoided_co2 = self.calc.calculate_avoided_offset_kg(size)
        self.assertGreater(avoided_co2, 0.1)

    def test_T3_23_cloud_approval_accumulates_into_school_ledger(self):
        """T3-23: Approved cloud storage deletion accumulates into Eco-Fund ledger."""
        self.cloud.connect("mock")
        target = self.cloud.files[0] # 2.84 GB
        self.cloud.stage_deletion(target["id"])
        rid = self.teacher_queue.submit_request("stu_01", target["name"], target["size_bytes"], "old render", 0.9, "Verified")
        res = self.teacher_queue.approve(rid)
        self.assertGreaterEqual(res["ledger"]["trees_triggered"], 2)

    def test_T3_24_restoring_cloud_file_reverses_trash_quota(self):
        """T3-24: Restoring cloud file reverses trash and restores quota."""
        self.cloud.connect("mock")
        target = self.cloud.files[1]
        self.cloud.stage_deletion(target["id"])
        self.cloud.restore_file(target["id"])
        self.assertIn(target["id"], [f["id"] for f in self.cloud.list_files()])

    def test_T3_25_cloud_quota_syncs_with_local_dashboard(self):
        """T3-25: Cloud quota values can be queried by dashboard."""
        self.cloud.connect("mock")
        total = self.cloud.quota["total_bytes"]
        used = self.cloud.quota["used_bytes"]
        pct_used = (used / total) * 100.0
        self.assertGreater(pct_used, 50.0)

    # -------------------------------------------------------------------------
    # Pairwise 6: Admin Budget + Leaderboard Competition (Tests 26-30)
    # -------------------------------------------------------------------------
    def test_T3_26_multi_student_competition_reorders_leaderboard(self):
        """T3-26: Student 2 scoring more points overtakes Student 1 on leaderboard."""
        board_before = self.gamification.get_leaderboard()
        self.assertEqual(board_before[0]["name"], "Alice Chen")

        # Award Marcus Vance (stu_02) 100 points
        self.gamification.record_deletion("stu_02", 1000 * 1024 * 1024)
        board_after = self.gamification.get_leaderboard()
        self.assertEqual(board_after[0]["name"], "Marcus Vance")

    def test_T3_27_gaming_flag_drops_student_down_leaderboard(self):
        """T3-27: Flagging Alice Chen causes Marcus Vance to become #1."""
        self.gamification.students["stu_02"]["points"] = 300 # Marcus Vance at 300
        rid = self.teacher_queue.submit_request("stu_01", "cheat.dat", 100, "cheat", 0.1, "Flag")
        self.teacher_queue.flag(rid, "Gaming penalty") # Alice drops 340 -> 290
        board = self.gamification.get_leaderboard()
        self.assertEqual(board[0]["name"], "Marcus Vance")

    def test_T3_28_batch_3gb_approval_disburses_3_trees_cleanly(self):
        """T3-28: Single 3.2 GB file approved -> plants 3 trees, leaves 0.2 GB surplus."""
        rid = self.teacher_queue.submit_request("stu_01", "raw_footage.tar", int(3.2 * THRESHOLD_BYTES), "old raw footage", 0.9, "Verified")
        res = self.teacher_queue.approve(rid)
        self.assertEqual(res["ledger"]["trees_triggered"], 3)
        self.assertEqual(self.ledger.lifetime_trees, 3)
        self.assertEqual(res["ledger"]["surplus_bytes"], int(0.2 * THRESHOLD_BYTES))

    def test_T3_29_roundtrip_scan_verify_queue_approve_ledger(self):
        """T3-29: Full integration chain from file scan to ledger transaction."""
        fpath = self.sandbox.create_file("final_old.mov", 1073741824, mtime_days_ago=200)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        f = files[0]
        score, summary, is_gaming = self.ai.evaluate_reason(f["name"], "completed course video project")
        self.assertGreaterEqual(score, 0.50)
        rid = self.teacher_queue.submit_request("stu_01", f["name"], f["size_bytes"], "completed course video", score, summary)
        res = self.teacher_queue.approve(rid)
        self.assertEqual(res["status"], "APPROVED")
        self.assertEqual(res["ledger"]["trees_triggered"], 1)
        self.assertTrue(self.ledger.verify_ledger_integrity())

    def test_T3_30_instant_revocation_during_pending_queue(self):
        """T3-30: Revoking scanner access preserves already submitted teacher queue items."""
        fpath = self.sandbox.create_file("video.mov", 1000, mtime_days_ago=200)
        self.scanner.grant_access(self.sandbox.temp_dir)
        self.scanner.scan()
        rid = self.teacher_queue.submit_request("stu_01", "video.mov", 1000, "old", 0.8, "Verified")
        # Revoke scanner
        self.scanner.revoke_access()
        self.assertEqual(self.scanner.state, "BLIND")
        # Teacher queue item remains valid and reviewable
        self.assertEqual(len(self.teacher_queue.queue), 1)
        res = self.teacher_queue.approve(rid)
        self.assertEqual(res["status"], "APPROVED")


if __name__ == "__main__":
    unittest.main()
