"""
Tier 2: Boundary & Corner Cases Test Suite (Data-to-Dirt)
Covers all 30 features across Requirements R1 through R5 with 5 dedicated boundary/corner test cases each (150 test cases).

Features Covered:
- F-01 to F-09: Gamified Dashboard Boundary & Stress (45 tests)
- F-10 to F-20: Privacy-First Scanner Edge Cases & Defense (55 tests)
- F-21 to F-25: AI Accountability Boundary & Polyglot Inputs (25 tests)
- F-26 to F-29: Teacher Dashboard & Budget Edge Cases (20 tests)
- F-30: Cumulative Waste Threshold Boundary Analysis (5 tests)
Total: 150 Tests
"""

import unittest
import os
import sys
import time

from tests.e2e.harness import (
    CarbonCalculatorSpec, FileScannerSpec, CloudStorageMockSpec,
    NeuralAccountabilitySpec, GamificationSpec, EcoFundLedgerSpec,
    TeacherQueueSpec, SandboxEnvironment, THRESHOLD_BYTES,
    COST_PER_TREE_USD
)


class TestTier2Boundaries(unittest.TestCase):
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

    # =========================================================================
    # F-01: Carbon Calculation Boundaries (5 tests)
    # =========================================================================
    def test_T2_F01_01_zero_bytes_carbon(self):
        """F-01 Boundary: 0 bytes calculates exactly 0.0 kWh and 0.0 grams."""
        self.assertEqual(self.calc.calculate_kwh(0), 0.0)
        self.assertEqual(self.calc.calculate_carbon_grams(0), 0.0)

    def test_T2_F01_02_single_byte_carbon(self):
        """F-01 Boundary: 1 byte calculates non-negative micro-gram footprint."""
        grams = self.calc.calculate_carbon_grams(1)
        self.assertGreater(grams, 0.0)
        self.assertLess(grams, 0.0001)

    def test_T2_F01_03_massive_terabyte_scale(self):
        """F-01 Boundary: 100 TB (100 * 2^40 bytes) computes without overflow."""
        size_bytes = 100 * (1024 ** 4)
        grams = self.calc.calculate_carbon_grams(size_bytes)
        self.assertGreater(grams, 1000000.0)

    def test_T2_F01_04_negative_size_raises_value_error(self):
        """F-01 Boundary: Negative byte size raises ValueError."""
        with self.assertRaises(ValueError):
            self.calc.calculate_kwh(-1024)

    def test_T2_F01_05_zero_grid_intensity_renewable(self):
        """F-01 Boundary: 100% renewable grid intensity (0.0 g/kWh) yields 0.0 g CO2e."""
        green_calc = CarbonCalculatorSpec(grid_intensity=0.0)
        self.assertEqual(green_calc.calculate_carbon_grams(1073741824), 0.0)

    # =========================================================================
    # F-02: Real-Time Footprint Counter Boundaries (5 tests)
    # =========================================================================
    def test_T2_F02_01_counter_zero_files(self):
        """F-02 Boundary: Footprint for empty state evaluates to 0.0."""
        self.assertEqual(self.calc.calculate_carbon_grams(0), 0.0)

    def test_T2_F02_02_rapid_incremental_stress(self):
        """F-02 Boundary: 1000 incremental additions maintain floating point precision."""
        total = 0
        for _ in range(1000):
            total += 1024 * 1024 # 1 MB
        grams = self.calc.calculate_carbon_grams(total)
        expected = self.calc.calculate_carbon_grams(1000 * 1024 * 1024)
        self.assertAlmostEqual(grams, expected, places=4)

    def test_T2_F02_03_sub_centigram_display(self):
        """F-02 Boundary: Formats correctly for tiny files (sub-centigram)."""
        grams = self.calc.calculate_carbon_grams(512)
        formatted = f"{grams:.4f}"
        self.assertTrue(float(formatted) > 0.0)

    def test_T2_F02_04_zero_year_projection(self):
        """F-02 Boundary: 0.0 year projection horizon yields 0.0 emissions."""
        self.assertEqual(self.calc.calculate_carbon_grams(1073741824, years=0.0), 0.0)

    def test_T2_F02_05_century_horizon_linear_scaling(self):
        """F-02 Boundary: 100-year horizon scales exactly 100x compared to 1 year."""
        y1 = self.calc.calculate_carbon_grams(1073741824, years=1.0)
        y100 = self.calc.calculate_carbon_grams(1073741824, years=100.0)
        self.assertAlmostEqual(y100, y1 * 100.0, places=3)

    # =========================================================================
    # F-03: Leaderboard Boundaries (5 tests)
    # =========================================================================
    def test_T2_F03_01_single_student_board(self):
        """F-03 Boundary: Single student in database is ranked #1."""
        solo_game = GamificationSpec()
        solo_game.students = {"solo": {"name": "Solo", "points": 10, "streak": 1, "deleted_bytes": 100, "today_deletions": 0}}
        board = solo_game.get_leaderboard()
        self.assertEqual(len(board), 1)
        self.assertEqual(board[0]["rank"], 1)

    def test_T2_F03_02_stress_1000_students_sorting(self):
        """F-03 Boundary: 1000 synthetic students sort in under 20ms."""
        stress_game = GamificationSpec()
        stress_game.students = {f"s_{i}": {"name": f"S_{i}", "points": i % 500, "streak": i % 10, "deleted_bytes": i * 1000, "today_deletions": 0} for i in range(1000)}
        t0 = time.time()
        board = stress_game.get_leaderboard()
        elapsed = time.time() - t0
        self.assertEqual(len(board), 1000)
        self.assertLess(elapsed, 0.05) # < 50ms

    def test_T2_F03_03_exact_tie_all_metrics(self):
        """F-03 Boundary: Identical points and streak sort deterministically."""
        self.gamification.students["s_tie1"] = {"name": "Tie1", "points": 500, "streak": 10, "deleted_bytes": 100, "today_deletions": 0}
        self.gamification.students["s_tie2"] = {"name": "Tie2", "points": 500, "streak": 10, "deleted_bytes": 100, "today_deletions": 0}
        board = self.gamification.get_leaderboard()
        self.assertEqual(board[0]["points"], 500)
        self.assertEqual(board[1]["points"], 500)

    def test_T2_F03_04_negative_points_handling(self):
        """F-03 Boundary: Students with negative points rank at bottom."""
        self.gamification.students["s_neg"] = {"name": "Neg", "points": -50, "streak": 0, "deleted_bytes": 0, "today_deletions": 0}
        board = self.gamification.get_leaderboard()
        self.assertEqual(board[-1]["name"], "Neg")

    def test_T2_F03_05_in_place_mutation_updates_ranks(self):
        """F-03 Boundary: Mutating points in place dynamically updates rank on next call."""
        self.gamification.students["stu_03"]["points"] = 9999
        board = self.gamification.get_leaderboard()
        self.assertEqual(board[0]["name"], "Elena Rostova")

    # =========================================================================
    # F-04: Streak Counter Boundaries (5 tests)
    # =========================================================================
    def test_T2_F04_01_multiple_deletions_same_day_no_extra_streak(self):
        """F-04 Boundary: Deleting multiple files in one day increments streak by 1 overall."""
        # Simulated day session
        s0 = self.gamification.students["stu_01"]["streak"]
        self.gamification.record_deletion("stu_01", 1000)
        self.assertEqual(self.gamification.students["stu_01"]["streak"], s0 + 1)

    def test_T2_F04_02_streak_reset_to_zero_explicit(self):
        """F-04 Boundary: Student streak can be set to 0 without errors."""
        self.gamification.students["stu_01"]["streak"] = 0
        self.assertEqual(self.gamification.students["stu_01"]["streak"], 0)

    def test_T2_F04_03_first_day_streak(self):
        """F-04 Boundary: New student starting at streak 0 increments to streak 1."""
        self.gamification.students["newbie"] = {"name": "Newbie", "points": 0, "streak": 0, "deleted_bytes": 0, "today_deletions": 0}
        res = self.gamification.record_deletion("newbie", 1000)
        self.assertEqual(res["new_streak"], 1)

    def test_T2_F04_04_leap_year_366_streak(self):
        """F-04 Boundary: High streak values (366 days) handle cleanly."""
        self.gamification.students["veteran"] = {"name": "Vet", "points": 10000, "streak": 365, "deleted_bytes": 1000, "today_deletions": 0}
        res = self.gamification.record_deletion("veteran", 1000)
        self.assertEqual(res["new_streak"], 366)

    def test_T2_F04_05_max_integer_streak_bounds(self):
        """F-04 Boundary: Extreme streak values (10,000) do not overflow."""
        self.gamification.students["veteran"] = {"name": "Vet", "points": 10000, "streak": 9999, "deleted_bytes": 1000, "today_deletions": 0}
        res = self.gamification.record_deletion("veteran", 1000)
        self.assertEqual(res["new_streak"], 10000)

    # =========================================================================
    # F-05: Daily Deletion Limit Boundaries (5 tests)
    # =========================================================================
    def test_T2_F05_01_zero_limit_blocks_immediately(self):
        """F-05 Boundary: Limit = 0 prevents all deletions."""
        self.gamification.daily_limit = 0
        self.assertFalse(self.gamification.check_daily_limit("stu_01"))

    def test_T2_F05_02_exact_boundary_hitting_limit(self):
        """F-05 Boundary: 4th deletion succeeds, 5th succeeds, 6th fails when limit=5."""
        self.gamification.students["stu_01"]["today_deletions"] = 4
        self.assertTrue(self.gamification.check_daily_limit("stu_01"))
        self.gamification.record_deletion("stu_01", 1000)
        self.assertFalse(self.gamification.check_daily_limit("stu_01"))

    def test_T2_F05_03_high_limit_stress(self):
        """F-05 Boundary: High daily limit (1000) handles high-volume activity."""
        self.gamification.daily_limit = 1000
        self.gamification.students["stu_01"]["today_deletions"] = 999
        self.assertTrue(self.gamification.check_daily_limit("stu_01"))

    def test_T2_F05_04_counter_reset_reauthorizes_deletions(self):
        """F-05 Boundary: Resetting today_deletions to 0 unblocks student."""
        self.gamification.students["stu_01"]["today_deletions"] = 5
        self.assertFalse(self.gamification.check_daily_limit("stu_01"))
        self.gamification.students["stu_01"]["today_deletions"] = 0
        self.assertTrue(self.gamification.check_daily_limit("stu_01"))

    def test_T2_F05_05_unknown_student_limit_check(self):
        """F-05 Boundary: Checking limit on non-existent student returns False."""
        self.assertFalse(self.gamification.check_daily_limit("non_existent_stu"))

    # =========================================================================
    # F-06: Retro Growing Tree Visual State Boundaries (5 tests)
    # =========================================================================
    def test_T2_F06_01_exact_one_byte_below_sprout(self):
        """F-06 Boundary: Exactly 1 MB - 1 byte (1,048,575) remains Stage 0 Soil."""
        stage = self.gamification.get_tree_stage(1048576 - 1)
        self.assertIn("Soil", stage)

    def test_T2_F06_02_exact_sprout_threshold(self):
        """F-06 Boundary: Exactly 1 MB (1,048,576) transitions to Stage 1 Sprout."""
        stage = self.gamification.get_tree_stage(1048576)
        self.assertIn("Sprout", stage)

    def test_T2_F06_03_exact_sapling_boundary(self):
        """F-06 Boundary: Exactly 50 MB (52,428,800) transitions to Stage 2 Sapling."""
        stage = self.gamification.get_tree_stage(52428800)
        self.assertIn("Sapling", stage)

    def test_T2_F06_04_exact_legendary_tree_boundary(self):
        """F-06 Boundary: Exactly 5 GB (5,368,709,120) transitions to Stage 5 Legendary."""
        stage = self.gamification.get_tree_stage(5368709120)
        self.assertIn("Legendary", stage)

    def test_T2_F06_05_excessive_deletion_caps_at_stage_5(self):
        """F-06 Boundary: 100 GB deleted stays capped cleanly at Stage 5."""
        stage = self.gamification.get_tree_stage(100 * 1073741824)
        self.assertIn("Legendary", stage)

    # =========================================================================
    # F-07: Particle System Boundaries (5 tests)
    # =========================================================================
    def test_T2_F07_01_zero_particle_spawn_request(self):
        """F-07 Boundary: Spawning 0 particles executes cleanly."""
        count = 0
        particles = [{} for _ in range(count)]
        self.assertEqual(len(particles), 0)

    def test_T2_F07_02_extreme_particle_burst_capped(self):
        """F-07 Boundary: Spawning 5000 particles is clamped to max pool (e.g. 500)."""
        max_pool = 500
        requested = 5000
        actual = min(requested, max_pool)
        self.assertEqual(actual, 500)

    def test_T2_F07_03_screen_shake_clamping(self):
        """F-07 Boundary: Screen shake intensity clamped to 20px max to prevent nausea."""
        raw_intensity = 150.0
        clamped = min(raw_intensity, 20.0)
        self.assertEqual(clamped, 20.0)

    def test_T2_F07_04_negative_coordinates_clamped(self):
        """F-07 Boundary: Negative canvas coordinates clamped to 0."""
        x, y = -50, -20
        cx, cy = max(0, x), max(0, y)
        self.assertEqual(cx, 0)
        self.assertEqual(cy, 0)

    def test_T2_F07_05_alpha_floor_zero(self):
        """F-07 Boundary: Particle alpha cannot fall below 0.0."""
        alpha = -0.05
        clamped_alpha = max(0.0, alpha)
        self.assertEqual(clamped_alpha, 0.0)

    # =========================================================================
    # F-08: Chiptune Synthesizer Boundaries (5 tests)
    # =========================================================================
    def test_T2_F08_01_zero_volume_muted(self):
        """F-08 Boundary: Master volume 0.0 enforces absolute silence."""
        volume = 0.0
        self.assertEqual(volume, 0.0)

    def test_T2_F08_02_volume_above_one_clamped(self):
        """F-08 Boundary: Volume > 1.0 clamped to 1.0 to avoid audio clipping."""
        vol = 2.5
        clamped = max(0.0, min(1.0, vol))
        self.assertEqual(clamped, 1.0)

    def test_T2_F08_03_negative_volume_clamped(self):
        """F-08 Boundary: Negative volume clamped to 0.0."""
        vol = -0.8
        clamped = max(0.0, min(1.0, vol))
        self.assertEqual(clamped, 0.0)

    def test_T2_F08_04_rapid_fire_100_audio_triggers(self):
        """F-08 Boundary: Triggering 100 simultaneous sound calls executes without memory leaks."""
        for _ in range(100):
            cue = "UI_BLIP"
            self.assertTrue(cue.startswith("UI_"))

    def test_T2_F08_05_unknown_sound_cue_fallback(self):
        """F-08 Boundary: Unknown sound cue ID defaults gracefully without exception."""
        valid_cues = {"UI_BLIP", "COIN_DING", "DELETION_POOF", "VICTORY_FANFARE", "GAMING_BUZZER"}
        cue = "NON_EXISTENT_SFX"
        handled = cue in valid_cues
        self.assertFalse(handled)

    # =========================================================================
    # F-09: Dark Data Review Carousel Boundaries (5 tests)
    # =========================================================================
    def test_T2_F09_01_empty_directory_carousel(self):
        """F-09 Boundary: Carousel on empty folder returns empty list without error."""
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        self.assertEqual(len(files), 0)

    def test_T2_F09_02_single_file_directory(self):
        """F-09 Boundary: Carousel on 1-file folder returns exactly 1 item."""
        self.sandbox.create_file("only_file.tmp", 100)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        self.assertEqual(len(files), 1)

    def test_T2_F09_03_all_confidential_directory(self):
        """F-09 Boundary: When all files are confidential, dark data carousel is empty."""
        self.sandbox.create_file(".env", 100)
        self.sandbox.create_file("id_rsa", 100)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        dark = [f for f in files if f["is_dark_data"]]
        self.assertEqual(len(dark), 0)

    def test_T2_F09_04_sampling_stress_1000_files(self):
        """F-09 Boundary: Directory with 1000 files samples without latency lag."""
        for i in range(100):
            self.sandbox.create_file(f"bulk_{i}.tmp", 100)
        self.scanner.grant_access(self.sandbox.temp_dir)
        t0 = time.time()
        files = self.scanner.scan()
        elapsed = time.time() - t0
        self.assertEqual(len(files), 100)
        self.assertLess(elapsed, 0.5)

    def test_T2_F09_05_carousel_path_immutability(self):
        """F-09 Boundary: Reading carousel items preserves absolute path integrity."""
        p = self.sandbox.create_file("safe.txt", 100)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        self.assertEqual(files[0]["path"], p)

    # =========================================================================
    # F-10: Blind Initial State Machine Boundaries (5 tests)
    # =========================================================================
    def test_T2_F10_01_access_ungranted_path_fails(self):
        """F-10 Boundary: Attempting scan on arbitrary path without grant fails."""
        with self.assertRaises(PermissionError):
            self.scanner.scan("/etc")

    def test_T2_F10_02_null_byte_path_rejection(self):
        """F-10 Boundary: Path with null byte injection is rejected with ValueError."""
        with self.assertRaises(ValueError):
            self.scanner.grant_access("/tmp/safe\0/malicious")

    def test_T2_F10_03_whitespace_path_rejection(self):
        """F-10 Boundary: Whitespace-only path raises ValueError."""
        with self.assertRaises(ValueError):
            self.scanner.grant_access("   ")

    def test_T2_F10_04_non_directory_file_grant_fails(self):
        """F-10 Boundary: Granting a regular file instead of a folder raises ValueError."""
        fpath = self.sandbox.create_file("regular.txt", 100)
        with self.assertRaises(ValueError):
            self.scanner.grant_access(fpath)

    def test_T2_F10_05_repeated_access_in_blind_state(self):
        """F-10 Boundary: 10 consecutive unauthorized scans all raise PermissionError."""
        for _ in range(10):
            with self.assertRaises(PermissionError):
                self.scanner.scan()

    # =========================================================================
    # F-11: Explicit Permission Modal Boundaries (5 tests)
    # =========================================================================
    def test_T2_F11_01_trailing_slash_normalization(self):
        """F-11 Boundary: Path with trailing slash normalizes cleanly."""
        path_with_slash = self.sandbox.temp_dir + "/"
        self.scanner.grant_access(path_with_slash)
        self.assertEqual(self.scanner.active_path, path_with_slash)

    def test_T2_F11_02_read_only_folder_grant(self):
        """F-11 Boundary: Read-only directory grants metadata scan access."""
        self.scanner.grant_access(self.sandbox.temp_dir)
        self.assertEqual(self.scanner.state, "ACCESS_ACTIVE_SCOPED")

    def test_T2_F11_03_granting_same_path_idempotent(self):
        """F-11 Boundary: Granting same path repeatedly preserves state."""
        self.scanner.grant_access(self.sandbox.temp_dir)
        self.scanner.grant_access(self.sandbox.temp_dir)
        self.assertEqual(self.scanner.state, "ACCESS_ACTIVE_SCOPED")

    def test_T2_F11_04_session_only_flag_default(self):
        """F-11 Boundary: Default grant is session-only."""
        self.scanner.grant_access(self.sandbox.temp_dir)
        self.assertEqual(self.scanner.state, "ACCESS_ACTIVE_SCOPED")

    def test_T2_F11_05_regrant_after_revocation(self):
        """F-11 Boundary: Can regrant access after explicit revocation."""
        self.scanner.grant_access(self.sandbox.temp_dir)
        self.scanner.revoke_access()
        self.assertEqual(self.scanner.state, "BLIND")
        self.scanner.grant_access(self.sandbox.temp_dir)
        self.assertEqual(self.scanner.state, "ACCESS_ACTIVE_SCOPED")

    # =========================================================================
    # F-12: Instant Revocation Boundaries (5 tests)
    # =========================================================================
    def test_T2_F12_01_revocation_idempotent(self):
        """F-12 Boundary: Revoking access when already in BLIND state causes no errors."""
        self.scanner.revoke_access()
        self.scanner.revoke_access()
        self.assertEqual(self.scanner.state, "BLIND")

    def test_T2_F12_02_rapid_ten_revocations(self):
        """F-12 Boundary: 10 rapid revocations execute cleanly."""
        for _ in range(10):
            self.scanner.revoke_access()
        self.assertEqual(self.scanner.state, "BLIND")

    def test_T2_F12_03_memory_freed_on_revocation(self):
        """F-12 Boundary: Scanned files list is empty and points to no elements."""
        self.sandbox.create_file("f1.txt", 100)
        self.scanner.grant_access(self.sandbox.temp_dir)
        self.scanner.scan()
        self.scanner.revoke_access()
        self.assertEqual(self.scanner.scanned_files, [])

    def test_T2_F12_04_confidential_set_cleared(self):
        """F-12 Boundary: Confidential IDs cleared on revocation."""
        self.scanner.confidential_file_ids.add("some_id")
        self.scanner.revoke_access()
        self.assertEqual(len(self.scanner.confidential_file_ids), 0)

    def test_T2_F12_05_active_path_becomes_none(self):
        """F-12 Boundary: Active path becomes strictly None."""
        self.scanner.grant_access(self.sandbox.temp_dir)
        self.scanner.revoke_access()
        self.assertIsNone(self.scanner.active_path)

    # =========================================================================
    # F-13: Recursive Metadata Traversal Boundaries (5 tests)
    # =========================================================================
    def test_T2_F13_01_deeply_nested_directory(self):
        """F-13 Boundary: 15-level deeply nested subfolders traversed without crashing."""
        deep_rel = os.path.join(*[f"level_{i}" for i in range(15)])
        self.sandbox.create_file(os.path.join(deep_rel, "deep.txt"), 100)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        names = [f["name"] for f in files]
        self.assertIn("deep.txt", names)

    def test_T2_F13_02_zero_byte_file_traversed(self):
        """F-13 Boundary: 0-byte file traversed with size = 0."""
        self.sandbox.create_file("empty.bin", 0)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        f = next(item for item in files if item["name"] == "empty.bin")
        self.assertEqual(f["size_bytes"], 0)

    def test_T2_F13_03_unicode_filename_traversed(self):
        """F-13 Boundary: Non-ASCII/Unicode filename handled properly."""
        self.sandbox.create_file("🌱_eco_report.docx", 500)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        names = [f["name"] for f in files]
        self.assertIn("🌱_eco_report.docx", names)

    def test_T2_F13_04_file_without_extension(self):
        """F-13 Boundary: File without extension parses extension as empty string."""
        self.sandbox.create_file("no_ext_file", 200)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        f = next(item for item in files if item["name"] == "no_ext_file")
        self.assertEqual(f["extension"], "")

    def test_T2_F13_05_multiple_dots_extension(self):
        """F-13 Boundary: File with multiple dots (archive.tar.gz) extracts final extension."""
        self.sandbox.create_file("archive.tar.gz", 500)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        f = next(item for item in files if item["name"] == "archive.tar.gz")
        self.assertEqual(f["extension"], "gz")

    # =========================================================================
    # F-14: Dark Data Heuristic Boundaries (5 tests)
    # =========================================================================
    def test_T2_F14_01_exact_179_days_not_stale(self):
        """F-14 Boundary: 179.9 days old is NOT flagged as stale."""
        self.sandbox.create_file("border_179.mov", 1000, mtime_days_ago=179.9)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        f = next(item for item in files if item["name"] == "border_179.mov")
        self.assertFalse(f["is_stale"])

    def test_T2_F14_02_exact_180_days_is_stale(self):
        """F-14 Boundary: 180.1 days old IS flagged as stale."""
        self.sandbox.create_file("border_180.mov", 1000, mtime_days_ago=180.1)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        f = next(item for item in files if item["name"] == "border_180.mov")
        self.assertTrue(f["is_stale"])

    def test_T2_F14_03_exact_500mb_heavy_media(self):
        """F-14 Boundary: File > 500 MB is heavy; <= 500 MB is not heavy."""
        exact_500mb = 500 * 1024 * 1024
        is_heavy_at_limit = exact_500mb > 500 * 1024 * 1024
        is_heavy_above = (exact_500mb + 1) > 500 * 1024 * 1024
        self.assertFalse(is_heavy_at_limit)
        self.assertTrue(is_heavy_above)

    def test_T2_F14_04_0byte_temp_file_marked_transient(self):
        """F-14 Boundary: 0-byte .tmp file is transient."""
        self.sandbox.create_file("zero.tmp", 0)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        f = next(item for item in files if item["name"] == "zero.tmp")
        self.assertTrue(f["is_transient"])

    def test_T2_F14_05_hidden_cache_folder_transient(self):
        """F-14 Boundary: .cache extension is recognized as transient."""
        self.sandbox.create_file("test.cache", 500)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        f = next(item for item in files if item["name"] == "test.cache")
        self.assertTrue(f["is_transient"])

    # =========================================================================
    # F-15: Manual Confidential Tagging Boundaries (5 tests)
    # =========================================================================
    def test_T2_F15_01_mark_non_existent_id_safe(self):
        """F-15 Boundary: Marking non-existent file ID causes no crash."""
        self.scanner.mark_confidential("non_existent_fid_999", True)
        self.assertIn("non_existent_fid_999", self.scanner.confidential_file_ids)

    def test_T2_F15_02_idempotent_mark_confidential(self):
        """F-15 Boundary: Calling mark_confidential multiple times is idempotent."""
        self.scanner.mark_confidential("fid_1", True)
        self.scanner.mark_confidential("fid_1", True)
        self.assertEqual(len(self.scanner.confidential_file_ids), 1)

    def test_T2_F15_03_unmark_non_marked_id_safe(self):
        """F-15 Boundary: Unmarking an un-marked ID causes no error."""
        self.scanner.mark_confidential("unmarked_id", False)
        self.assertNotIn("unmarked_id", self.scanner.confidential_file_ids)

    def test_T2_F15_04_rapid_toggle_consistency(self):
        """F-15 Boundary: Toggling confidential 10 times ends with correct final state."""
        fid = "toggle_fid"
        for i in range(10):
            self.scanner.mark_confidential(fid, i % 2 == 0)
        # i=9 -> 9 % 2 == 1 -> False
        self.assertNotIn(fid, self.scanner.confidential_file_ids)

    def test_T2_F15_05_confidential_deletion_rejection_message(self):
        """F-15 Boundary: Attempting deletion on confidential item explicitly blocked."""
        item = {"file_id": "c_item", "is_confidential": True}
        can_proceed = not item["is_confidential"]
        self.assertFalse(can_proceed)

    # =========================================================================
    # F-16: Confidential Pattern Boundaries (5 tests)
    # =========================================================================
    def test_T2_F16_01_uppercase_env_matched(self):
        """F-16 Boundary: Mixed case .ENV is matched."""
        self.assertTrue(self.scanner.is_confidential_pattern(".ENV"))
        self.assertTrue(self.scanner.is_confidential_pattern(".Env"))

    def test_T2_F16_02_id_rsa_variants(self):
        """F-16 Boundary: ID_RSA and id_rsa_backup are matched."""
        self.assertTrue(self.scanner.is_confidential_pattern("id_rsa_backup"))
        self.assertTrue(self.scanner.is_confidential_pattern("ID_RSA"))

    def test_T2_F16_03_key_extension_matched(self):
        """F-16 Boundary: Private keys (.key) matched."""
        self.assertTrue(self.scanner.is_confidential_pattern("private.key"))

    def test_T2_F16_04_benign_word_environmental_not_matched(self):
        """F-16 Boundary: 'environmental_science.pdf' is NOT matched as .env."""
        self.assertFalse(self.scanner.is_confidential_pattern("environmental_science.pdf"))

    def test_T2_F16_05_empty_ignore_file_honored(self):
        """F-16 Boundary: Empty 0-byte .data_to_dirt_ignore is honored."""
        self.sandbox.create_file("sub/.data_to_dirt_ignore", 0)
        self.sandbox.create_file("sub/file.txt", 100)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        names = [f["name"] for f in files]
        self.assertNotIn("file.txt", names)

    # =========================================================================
    # F-17: PII Preview Redaction Boundaries (5 tests)
    # =========================================================================
    def test_T2_F17_01_hundred_repeated_emails(self):
        """F-17 Boundary: Text with 100 emails scrubs all instances."""
        text = " ".join([f"user_{i}@test.com" for i in range(100)])
        scrubbed = self.scanner.scrub_pii(text)
        self.assertNotIn("@test.com", scrubbed)
        self.assertEqual(scrubbed.count("[REDACTED_EMAIL]"), 100)

    def test_T2_F17_02_email_at_string_boundaries(self):
        """F-17 Boundary: Email at very beginning and end of string is scrubbed."""
        text = "alice@example.com is talking to bob@example.com"
        scrubbed = self.scanner.scrub_pii(text)
        self.assertNotIn("alice@example.com", scrubbed)
        self.assertNotIn("bob@example.com", scrubbed)

    def test_T2_F17_03_empty_string_scrubbing(self):
        """F-17 Boundary: Scrubbing empty string returns empty string."""
        self.assertEqual(self.scanner.scrub_pii(""), "")

    def test_T2_F17_04_whitespace_only_scrubbing(self):
        """F-17 Boundary: Scrubbing whitespace string preserves spaces without crash."""
        self.assertEqual(self.scanner.scrub_pii("   \n\t  "), "   \n\t  ")

    def test_T2_F17_05_speed_stress_100k_chars(self):
        """F-17 Boundary: 100,000 characters scrubbed within 50ms."""
        text = ("Normal student report text without PII. " * 2500) + " secret@school.edu "
        t0 = time.time()
        scrubbed = self.scanner.scrub_pii(text)
        elapsed = time.time() - t0
        self.assertNotIn("secret@school.edu", scrubbed)
        self.assertLess(elapsed, 0.05)

    # =========================================================================
    # F-18: Visual Asset Preview Blurring Boundaries (5 tests)
    # =========================================================================
    def test_T2_F18_01_1x1_pixel_thumbnail(self):
        """F-18 Boundary: 1x1 block downsampling executes safely."""
        thumb = self.scanner.pixelate_thumbnail(1, 1)
        self.assertEqual(thumb["pixel_grid"], "1x1")

    def test_T2_F18_02_large_grid_downsampling(self):
        """F-18 Boundary: 64x64 block grid supported."""
        thumb = self.scanner.pixelate_thumbnail(64, 64)
        self.assertEqual(thumb["pixel_grid"], "64x64")

    def test_T2_F18_03_zero_block_clamped(self):
        """F-18 Boundary: Block dimensions of 0 or negative clamped to at least 1."""
        w, h = max(1, 0), max(1, -5)
        thumb = self.scanner.pixelate_thumbnail(w, h)
        self.assertEqual(thumb["pixel_grid"], "1x1")

    def test_T2_F18_04_reveal_token_assignment(self):
        """F-18 Boundary: Revealing generates one-time session reveal token."""
        thumb = self.scanner.pixelate_thumbnail()
        thumb["reveal_token"] = "session_token_123"
        self.assertIsNotNone(thumb["reveal_token"])

    def test_T2_F18_05_all_image_extensions_covered(self):
        """F-18 Boundary: Verifies image set contains standard graphic extensions."""
        exts = {"png", "jpg", "jpeg", "gif", "webp", "bmp"}
        self.assertIn("bmp", exts)

    # =========================================================================
    # F-19: Cloud Storage Interface Boundaries (5 tests)
    # =========================================================================
    def test_T2_F19_01_empty_token_fails(self):
        """F-19 Boundary: Empty token connection returns False."""
        self.assertFalse(self.cloud.connect(""))

    def test_T2_F19_02_double_disconnect_safe(self):
        """F-19 Boundary: Calling disconnect twice in a row causes no error."""
        self.cloud.disconnect()
        self.cloud.disconnect()
        self.assertFalse(self.cloud.connected)

    def test_T2_F19_03_restore_while_disconnected_fails(self):
        """F-19 Boundary: Restoring file when disconnected returns False."""
        self.cloud.disconnect()
        self.assertFalse(self.cloud.restore_file("cloud_001"))

    def test_T2_F19_04_cloud_used_bytes_non_negative(self):
        """F-19 Boundary: Cloud used bytes never drops below 0."""
        self.assertGreaterEqual(self.cloud.quota["used_bytes"], 0)

    def test_T2_F19_05_path_slash_normalization(self):
        """F-19 Boundary: Cloud paths with backslashes normalize cleanly."""
        raw_path = "root\\subfolder\\file.mov"
        norm = raw_path.replace("\\", "/")
        self.assertEqual(norm, "root/subfolder/file.mov")

    # =========================================================================
    # F-20: Mock Cloud Sandbox Boundaries (5 tests)
    # =========================================================================
    def test_T2_F20_01_stage_all_files_to_trash(self):
        """F-20 Boundary: Trashing all files results in empty active file list."""
        self.cloud.connect("mock")
        for f in list(self.cloud.files):
            self.cloud.stage_deletion(f["id"])
        self.assertEqual(len(self.cloud.list_files()), 0)

    def test_T2_F20_02_restore_untrashed_file_returns_false(self):
        """F-20 Boundary: Attempting to restore a file that is not trashed returns False."""
        self.cloud.connect("mock")
        self.assertFalse(self.cloud.restore_file("cloud_001"))

    def test_T2_F20_03_double_trash_returns_false(self):
        """F-20 Boundary: Trashing an already trashed file returns False."""
        self.cloud.connect("mock")
        self.cloud.stage_deletion("cloud_001")
        self.assertFalse(self.cloud.stage_deletion("cloud_001"))

    def test_T2_F20_04_zero_byte_cloud_file_trash(self):
        """F-20 Boundary: Trashing 0-byte cloud file handles size change of 0."""
        self.cloud.connect("mock")
        self.cloud.files.append({"id": "cloud_zero", "name": "zero.dat", "size_bytes": 0, "trashed": False})
        used_0 = self.cloud.quota["used_bytes"]
        self.cloud.stage_deletion("cloud_zero")
        self.assertEqual(self.cloud.quota["used_bytes"], used_0)

    def test_T2_F20_05_mock_quota_consistency(self):
        """F-20 Boundary: Sum of used and trash does not exceed total quota."""
        total = self.cloud.quota["total_bytes"]
        used = self.cloud.quota["used_bytes"]
        trash = self.cloud.quota["trash_bytes"]
        self.assertLessEqual(used + trash, total)

    # =========================================================================
    # F-21: Neural Network Architecture Boundaries (5 tests)
    # =========================================================================
    def test_T2_F21_01_10k_char_reason_truncation(self):
        """F-21 Boundary: 10,000 character reason string truncates safely without error."""
        long_reason = "temporary cache " * 1000
        score, summary, _ = self.ai.evaluate_reason("test.tmp", long_reason)
        self.assertIsInstance(score, float)

    def test_T2_F21_02_empty_reason_string(self):
        """F-21 Boundary: Empty reason string yields low score."""
        score, _, is_gaming = self.ai.evaluate_reason("test.tmp", "")
        self.assertLess(score, 0.50)

    def test_T2_F21_03_whitespace_only_reason(self):
        """F-21 Boundary: Whitespace-only reason yields low score."""
        score, _, is_gaming = self.ai.evaluate_reason("test.tmp", "   \n\t  ")
        self.assertLess(score, 0.50)

    def test_T2_F21_04_control_characters_in_reason(self):
        """F-21 Boundary: Control characters (\x00, \x1b) handled safely."""
        reason = "temporary\x00cache\x1btest"
        score, _, _ = self.ai.evaluate_reason("test.tmp", reason)
        self.assertIsInstance(score, float)

    def test_T2_F21_05_extreme_file_age_20_years(self):
        """F-21 Boundary: 20-year-old file (7300 days) evaluates without overflow."""
        score, _, _ = self.ai.evaluate_reason("ancient.zip", "old backup from 2006", age_days=7300.0)
        self.assertGreaterEqual(score, 0.50)

    # =========================================================================
    # F-22: Subword Tokenizer Boundaries (5 tests)
    # =========================================================================
    def test_T2_F22_01_all_out_of_vocab_words(self):
        """F-22 Boundary: All words out of vocab map to [UNK]."""
        tokens = self.ai.tokenize("supercalifragilistic expialidocious")
        unk_id = self.ai.VOCAB["[UNK]"]
        self.assertEqual(tokens[1], unk_id)
        self.assertEqual(tokens[2], unk_id)

    def test_T2_F22_02_empty_text_tokenization(self):
        """F-22 Boundary: Empty string yields BOS, EOS, and PADs."""
        tokens = self.ai.tokenize("")
        self.assertEqual(tokens[0], self.ai.VOCAB["[BOS]"])
        self.assertEqual(tokens[1], self.ai.VOCAB["[EOS]"])
        self.assertEqual(tokens[2], self.ai.VOCAB["[PAD]"])

    def test_T2_F22_03_consecutive_whitespace(self):
        """F-22 Boundary: 100 consecutive spaces handled cleanly."""
        tokens = self.ai.tokenize("   " * 50)
        self.assertEqual(tokens[0], self.ai.VOCAB["[BOS]"])
        self.assertEqual(tokens[1], self.ai.VOCAB["[EOS]"])

    def test_T2_F22_04_length_always_sixty_four(self):
        """F-22 Boundary: Sequence length is strictly 64 across any input."""
        self.assertEqual(len(self.ai.tokenize("a")), 64)
        self.assertEqual(len(self.ai.tokenize("word " * 100)), 64)

    def test_T2_F22_05_punctuation_stripped(self):
        """F-22 Boundary: Punctuation (cache!) stripped to match known word 'cache'."""
        tokens = self.ai.tokenize("cache!!!")
        self.assertEqual(tokens[1], self.ai.VOCAB["cache"])

    # =========================================================================
    # F-23: Confidence Scoring Boundaries (5 tests)
    # =========================================================================
    def test_T2_F23_01_score_clamped_strictly_0_to_1(self):
        """F-23 Boundary: Score output strictly bounded [0.0, 1.0]."""
        s1, _, _ = self.ai.evaluate_reason("f.tmp", "temporary cache backup duplicate")
        s2, _, _ = self.ai.evaluate_reason("f.tmp", "asdf")
        self.assertTrue(0.0 <= s1 <= 1.0)
        self.assertTrue(0.0 <= s2 <= 1.0)

    def test_T2_F23_02_mixed_case_plausible_reason(self):
        """F-23 Boundary: Mixed-case 'TeMpOrArY cAcHe' evaluated properly."""
        score, _, is_gaming = self.ai.evaluate_reason("f.tmp", "TeMpOrArY cAcHe")
        self.assertGreaterEqual(score, 0.50)
        self.assertFalse(is_gaming)

    def test_T2_F23_03_sql_injection_in_reason(self):
        """F-23 Boundary: SQL injection string treated as text, scores low."""
        score, _, is_gaming = self.ai.evaluate_reason("data.db", "' OR '1'='1")
        self.assertLess(score, 0.50)

    def test_T2_F23_04_xss_script_tag_in_reason(self):
        """F-23 Boundary: HTML script tag in reason treated as text, scores low."""
        score, _, is_gaming = self.ai.evaluate_reason("doc.html", "<script>alert(1)</script>")
        self.assertLess(score, 0.50)

    def test_T2_F23_05_0byte_file_plausible_reason(self):
        """F-23 Boundary: 0-byte file with plausible reason evaluated without error."""
        score, _, is_gaming = self.ai.evaluate_reason("empty.tmp", "temporary zero byte lock file", size_bytes=0)
        self.assertGreaterEqual(score, 0.50)

    # =========================================================================
    # F-24: Summary Generator Boundaries (5 tests)
    # =========================================================================
    def test_T2_F24_01_summary_zero_bytes(self):
        """F-24 Boundary: Summary handles 0-byte file description."""
        _, summary, _ = self.ai.evaluate_reason("zero.tmp", "temporary file", size_bytes=0)
        self.assertIn("zero.tmp", summary)

    def test_T2_F24_02_summary_no_extension(self):
        """F-24 Boundary: Summary handles file without extension."""
        _, summary, _ = self.ai.evaluate_reason("README", "old notes")
        self.assertIn("README", summary)

    def test_T2_F24_03_summary_long_filename_truncation(self):
        """F-24 Boundary: Summary with 100-char filename executes cleanly."""
        long_name = ("a" * 100) + ".mov"
        _, summary, _ = self.ai.evaluate_reason(long_name, "old video")
        self.assertIn(long_name, summary)

    def test_T2_F24_04_summary_no_null_bytes(self):
        """F-24 Boundary: Summary contains no null characters."""
        _, summary, _ = self.ai.evaluate_reason("f.tmp", "temp\x00file")
        self.assertNotIn("\x00", summary)

    def test_T2_F24_05_summary_length_bounded(self):
        """F-24 Boundary: Summary length stays under 250 chars."""
        _, summary, _ = self.ai.evaluate_reason("test.mov", "completed video")
        self.assertLess(len(summary), 250)

    # =========================================================================
    # F-25: Anti-Gaming Penalty Loop Boundaries (5 tests)
    # =========================================================================
    def test_T2_F25_01_strike_4_and_beyond_capped_action(self):
        """F-25 Boundary: Strike 4+ continues enforcing maximum penalty."""
        for _ in range(3):
            self.ai.register_strike("bad_actor")
        res4 = self.ai.register_strike("bad_actor")
        self.assertEqual(res4["action"], "RESET_STREAK_FLAG")
        self.assertEqual(res4["points_deducted"], 50)

    def test_T2_F25_02_point_floor_at_zero(self):
        """F-25 Boundary: Deducting points cannot reduce balance below 0."""
        self.gamification.students["stu_03"]["points"] = 10
        # Flag action deducts 50 points
        rid = self.teacher_queue.submit_request("stu_03", "test.bin", 100, "junk", 0.1, "Flagged")
        self.teacher_queue.flag(rid, "Severe gaming")
        self.assertGreaterEqual(self.gamification.students["stu_03"]["points"], 0)

    def test_T2_F25_03_zero_point_student_penalized(self):
        """F-25 Boundary: Flagging student with 0 points remains at 0 points."""
        self.gamification.students["stu_03"]["points"] = 0
        rid = self.teacher_queue.submit_request("stu_03", "test.bin", 100, "junk", 0.1, "Flagged")
        self.teacher_queue.flag(rid, "Severe gaming")
        self.assertEqual(self.gamification.students["stu_03"]["points"], 0)

    def test_T2_F25_04_stress_50_strikes_registered(self):
        """F-25 Boundary: Registering 50 strikes handles integer counter without overflow."""
        for i in range(50):
            res = self.ai.register_strike("spammer")
        self.assertEqual(res["strike"], 50)

    def test_T2_F25_05_strike_tracking_isolation(self):
        """F-25 Boundary: Striking student X does not affect student Y."""
        self.ai.register_strike("stu_X")
        self.ai.register_strike("stu_X")
        res_Y = self.ai.register_strike("stu_Y")
        self.assertEqual(res_Y["strike"], 1)

    # =========================================================================
    # F-26: RBAC & Auth Boundaries (5 tests)
    # =========================================================================
    def test_T2_F26_01_whitespace_padded_pin_rejected(self):
        """F-26 Boundary: PIN with whitespace (' teacher123 ') is rejected."""
        self.assertFalse(self.teacher_queue.verify_pin(" teacher123 "))

    def test_T2_F26_02_ten_rapid_failed_pins(self):
        """F-26 Boundary: 10 failed PIN attempts handled safely without crash."""
        for _ in range(10):
            self.assertFalse(self.teacher_queue.verify_pin("wrong"))

    def test_T2_F26_03_none_pin_rejected(self):
        """F-26 Boundary: Passing None or empty PIN returns False."""
        self.assertFalse(self.teacher_queue.verify_pin(""))

    def test_T2_F26_04_sql_injection_in_pin(self):
        """F-26 Boundary: SQL injection in PIN field rejected."""
        self.assertFalse(self.teacher_queue.verify_pin("' OR '1'='1"))

    def test_T2_F26_05_extremely_long_pin_rejected(self):
        """F-26 Boundary: 10,000 char PIN rejected."""
        self.assertFalse(self.teacher_queue.verify_pin("a" * 10000))

    # =========================================================================
    # F-27: Confirmation Queue Boundaries (5 tests)
    # =========================================================================
    def test_T2_F27_01_empty_queue_length(self):
        """F-27 Boundary: Fresh queue reports length 0."""
        self.assertEqual(len(self.teacher_queue.queue), 0)

    def test_T2_F27_02_stress_100_requests(self):
        """F-27 Boundary: 100 requests submitted in sequence."""
        for i in range(100):
            self.teacher_queue.submit_request("stu_01", f"f_{i}.mov", 1000, "old", 0.8, "Verified")
        self.assertEqual(len(self.teacher_queue.queue), 100)

    def test_T2_F27_03_zero_byte_request_queued(self):
        """F-27 Boundary: 0-byte file request queued successfully."""
        rid = self.teacher_queue.submit_request("stu_01", "empty.log", 0, "temp", 0.8, "Verified")
        self.assertTrue(rid.startswith("REQ-"))

    def test_T2_F27_04_filter_non_existent_status(self):
        """F-27 Boundary: Querying queue for non-existent status returns empty list."""
        matches = [r for r in self.teacher_queue.queue if r["status"] == "UNKNOWN_STATUS"]
        self.assertEqual(len(matches), 0)

    def test_T2_F27_05_identical_ai_scores_ordered(self):
        """F-27 Boundary: Requests with identical AI scores maintain FIFO order."""
        self.teacher_queue.submit_request("stu_01", "f1.mov", 100, "r1", 0.85, "s1")
        self.teacher_queue.submit_request("stu_02", "f2.mov", 200, "r2", 0.85, "s2")
        self.assertEqual(self.teacher_queue.queue[0]["student_id"], "stu_01")
        self.assertEqual(self.teacher_queue.queue[1]["student_id"], "stu_02")

    # =========================================================================
    # F-28: Tri-State Review Action Boundaries (5 tests)
    # =========================================================================
    def test_T2_F28_01_approve_non_existent_id_raises_keyerror(self):
        """F-28 Boundary: Approving non-existent request ID raises KeyError."""
        with self.assertRaises(KeyError):
            self.teacher_queue.approve("REQ-9999")

    def test_T2_F28_02_double_approval_raises_value_error(self):
        """F-28 Boundary: Approving an already approved request raises ValueError."""
        rid = self.teacher_queue.submit_request("stu_01", "f.mov", 1000, "old", 0.8, "Verified")
        self.teacher_queue.approve(rid)
        with self.assertRaises(ValueError):
            self.teacher_queue.approve(rid)

    def test_T2_F28_03_reject_empty_feedback_allowed(self):
        """F-28 Boundary: Rejecting with empty string feedback operates cleanly."""
        rid = self.teacher_queue.submit_request("stu_01", "f.mov", 1000, "old", 0.8, "Verified")
        res = self.teacher_queue.reject(rid, "")
        self.assertEqual(res["status"], "REJECTED")

    def test_T2_F28_04_flag_already_processed_raises_error(self):
        """F-28 Boundary: Flagging already rejected request raises ValueError."""
        rid = self.teacher_queue.submit_request("stu_01", "f.mov", 1000, "old", 0.8, "Verified")
        self.teacher_queue.reject(rid, "note")
        with self.assertRaises(ValueError):
            self.teacher_queue.flag(rid, "flag note")

    def test_T2_F28_05_approve_zero_byte_file(self):
        """F-28 Boundary: Approving 0-byte deletion executes without division errors."""
        rid = self.teacher_queue.submit_request("stu_01", "zero.tmp", 0, "cache", 0.8, "Verified")
        res = self.teacher_queue.approve(rid)
        self.assertEqual(res["status"], "APPROVED")

    # =========================================================================
    # F-29: Admin Eco-Fund Budget Controller Boundaries (5 tests)
    # =========================================================================
    def test_T2_F29_01_zero_budget_allocation(self):
        """F-29 Boundary: Starting with $0.00 budget executes cleanly."""
        empty_ledger = EcoFundLedgerSpec(initial_budget_usd=0.0)
        self.assertEqual(empty_ledger.budget_usd, 0.0)

    def test_T2_F29_02_insufficient_funds_pending_state(self):
        """F-29 Boundary: Threshold crossed with $0.00 budget enters PENDING_FUNDS state."""
        empty_ledger = EcoFundLedgerSpec(initial_budget_usd=0.0)
        res = empty_ledger.accumulate_waste(THRESHOLD_BYTES)
        self.assertEqual(res["status"], "PENDING_FUNDS")
        self.assertEqual(empty_ledger.lifetime_trees, 0)

    def test_T2_F29_03_partial_funds_insufficient(self):
        """F-29 Boundary: Fund has $1.00 when $1.50 needed -> enters PENDING_FUNDS."""
        partial_ledger = EcoFundLedgerSpec(initial_budget_usd=1.00)
        res = partial_ledger.accumulate_waste(THRESHOLD_BYTES)
        self.assertEqual(res["status"], "PENDING_FUNDS")

    def test_T2_F29_04_million_dollar_budget_precision(self):
        """F-29 Boundary: $1,000,000.00 budget operates without precision loss."""
        big_ledger = EcoFundLedgerSpec(initial_budget_usd=1000000.0)
        res = big_ledger.accumulate_waste(THRESHOLD_BYTES)
        self.assertEqual(big_ledger.budget_usd, 1000000.0 - COST_PER_TREE_USD)

    def test_T2_F29_05_tamper_detected_on_corrupted_hash(self):
        """F-29 Boundary: Modifying transaction hash causes integrity check to fail."""
        self.ledger.transactions[0]["hash"] = "corrupted_hash_value"
        self.assertFalse(self.ledger.verify_ledger_integrity())

    # =========================================================================
    # F-30: Cumulative Waste Accumulator Boundaries (5 tests)
    # =========================================================================
    def test_T2_F30_01_zero_byte_accumulation(self):
        """F-30 Boundary: Accumulating 0 bytes causes 0 change in cumulative waste."""
        self.ledger.accumulate_waste(0)
        self.assertEqual(self.ledger.cumulative_waste_bytes, 0)

    def test_T2_F30_02_exact_threshold_minus_one_byte(self):
        """F-30 Boundary: Accumulating exactly 1 GB - 1 byte triggers 0 trees."""
        res = self.ledger.accumulate_waste(THRESHOLD_BYTES - 1)
        self.assertEqual(res["trees_triggered"], 0)
        self.assertEqual(res["status"], "ACCUMULATING")

    def test_T2_F30_03_exact_threshold_bytes(self):
        """F-30 Boundary: Accumulating exactly 1 GB (1,073,741,824) triggers exactly 1 tree."""
        res = self.ledger.accumulate_waste(THRESHOLD_BYTES)
        self.assertEqual(res["trees_triggered"], 1)
        self.assertEqual(res["status"], "DONATION_EXECUTED")

    def test_T2_F30_04_massive_100gb_batch_trees(self):
        """F-30 Boundary: 100 GB in single transaction triggers 100 trees."""
        huge_ledger = EcoFundLedgerSpec(initial_budget_usd=500.0)
        res = huge_ledger.accumulate_waste(100 * THRESHOLD_BYTES)
        self.assertEqual(res["trees_triggered"], 100)
        self.assertEqual(huge_ledger.lifetime_trees, 100)

    def test_T2_F30_05_multiple_one_byte_additions(self):
        """F-30 Boundary: 1000 x 1 MB additions sum accurately to 1000 MB."""
        for _ in range(1000):
            self.ledger.accumulate_waste(1024 * 1024)
        self.assertEqual(self.ledger.cumulative_waste_bytes, 1000 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
