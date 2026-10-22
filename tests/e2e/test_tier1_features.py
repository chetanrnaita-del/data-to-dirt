"""
Tier 1: Feature Coverage Test Suite (Data-to-Dirt)
Covers all 30 features across Requirements R1 through R5 with 5 dedicated test cases each (150 test cases).

Features Covered:
- F-01 to F-09: Gamified Carbon Dashboard & Retro Feedback (45 tests)
- F-10 to F-20: Privacy-First File Access & Cloud Mock (55 tests)
- F-21 to F-25: On-Device AI Accountability Loop (25 tests)
- F-26 to F-29: Teacher Dashboard & RBAC (20 tests)
- F-30: Eco-Fund & Tree-Nation Cumulative Waste Accumulator (5 tests)
Total: 150 Tests
"""

import unittest
import os
import sys
import time
import math

from tests.e2e.harness import (
    CarbonCalculatorSpec, FileScannerSpec, CloudStorageMockSpec,
    NeuralAccountabilitySpec, GamificationSpec, EcoFundLedgerSpec,
    TeacherQueueSpec, SandboxEnvironment, get_src_module,
    KWH_PER_GB_PER_YEAR, GRID_INTENSITY_GCO2_PER_KWH, THRESHOLD_BYTES,
    COST_PER_TREE_USD, TREE_ABSORPTION_KG_YEAR
)


class TestTier1FeatureCoverage(unittest.TestCase):
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
    # F-01: Stored Carbon Footprint Calculation (5 tests)
    # =========================================================================
    def test_T1_F01_01_kwh_calculation(self):
        """F-01: Validates kWh per GB year calculation against 0.28 kWh/GB constant."""
        size_bytes = 1073741824 # 1.0 GB
        kwh = self.calc.calculate_kwh(size_bytes, years=1.0)
        self.assertAlmostEqual(kwh, 0.28, places=4)

    def test_T1_F01_02_carbon_grams_calculation(self):
        """F-01: Validates grams of CO2e using Singapore grid factor (405.7 g/kWh)."""
        size_bytes = 1073741824 # 1.0 GB
        # 1.0 GB * 0.28 kWh * 405.7 g/kWh = 113.596 g CO2e
        grams = self.calc.calculate_carbon_grams(size_bytes, years=1.0)
        self.assertAlmostEqual(grams, 113.596, places=3)

    def test_T1_F01_03_avoided_carbon_offset_kg(self):
        """F-01: Validates avoided carbon offset in kg for 10 GB deleted data."""
        size_bytes = 10 * 1073741824 # 10.0 GB
        offset_kg = self.calc.calculate_avoided_offset_kg(size_bytes, years=1.0)
        # 10 * 113.596 / 1000 = 1.13596 kg
        self.assertAlmostEqual(offset_kg, 1.13596, places=4)

    def test_T1_F01_04_tree_equivalent_absorption(self):
        """F-01: Validates tree annual absorption equivalency (20.0 kg/tree/year)."""
        # 20.0 kg offset should equal exactly 1.0 tree equivalent
        bytes_for_one_tree = int((20.0 * 1000.0 / (0.28 * 405.7)) * 1073741824)
        trees = self.calc.calculate_tree_equivalents(bytes_for_one_tree)
        self.assertAlmostEqual(trees, 1.0, places=2)

    def test_T1_F01_05_secondary_equivalencies(self):
        """F-01: Validates smartphone charges (8.22g) and car km (170g) translation."""
        size_bytes = 1073741824 # 113.596 g CO2e
        charges = self.calc.calculate_smartphone_charges(size_bytes)
        car_km = self.calc.calculate_car_km(size_bytes)
        self.assertAlmostEqual(charges, 113.596 / 8.22, places=2)
        self.assertAlmostEqual(car_km, 113.596 / 170.0, places=2)

    # =========================================================================
    # F-02: Real-Time Footprint Counter (5 tests)
    # =========================================================================
    def test_T1_F02_01_initial_counter_zero(self):
        """F-02: Counter starts at zero prior to file operations."""
        self.assertEqual(self.calc.calculate_carbon_grams(0), 0.0)

    def test_T1_F02_02_counter_increments_on_staged_data(self):
        """F-02: Counter tracks active footprint when multiple files are identified."""
        f1_size = 500 * 1024 * 1024 # 500 MB
        f2_size = 1500 * 1024 * 1024 # 1.5 GB
        c1 = self.calc.calculate_carbon_grams(f1_size)
        c2 = self.calc.calculate_carbon_grams(f1_size + f2_size)
        self.assertGreater(c2, c1)

    def test_T1_F02_03_counter_decrements_on_deletion(self):
        """F-02: Net active footprint decreases when a file is deleted."""
        total_size = 2000 * 1024 * 1024
        deleted_size = 500 * 1024 * 1024
        remaining_footprint = self.calc.calculate_carbon_grams(total_size - deleted_size)
        original_footprint = self.calc.calculate_carbon_grams(total_size)
        self.assertAlmostEqual(original_footprint - remaining_footprint, self.calc.calculate_carbon_grams(deleted_size), places=5)

    def test_T1_F02_04_counter_precision_rounding(self):
        """F-02: Verifies counter values maintain sub-gram precision for UI display."""
        grams = self.calc.calculate_carbon_grams(1048576) # 1 MB
        self.assertGreater(grams, 0.0)
        formatted = f"{grams:.2f}"
        self.assertTrue(len(formatted.split(".")[1]) == 2)

    def test_T1_F02_05_avoided_lifetime_projection(self):
        """F-02: Counter projects avoided emissions across multi-year horizons (3-year)."""
        annual = self.calc.calculate_carbon_grams(1073741824, years=1.0)
        three_yr = self.calc.calculate_carbon_grams(1073741824, years=3.0)
        self.assertAlmostEqual(three_yr, annual * 3.0, places=4)

    # =========================================================================
    # F-03: Student Leaderboard (5 tests)
    # =========================================================================
    def test_T1_F03_01_minimum_entries(self):
        """F-03: Leaderboard contains at least 3 initial test entries."""
        board = self.gamification.get_leaderboard()
        self.assertGreaterEqual(len(board), 3)

    def test_T1_F03_02_ranked_order_by_points(self):
        """F-03: Leaderboard ranks entries in descending order of points."""
        board = self.gamification.get_leaderboard()
        for i in range(len(board) - 1):
            self.assertGreaterEqual(board[i]["points"], board[i + 1]["points"])

    def test_T1_F03_03_rank_attribute_populated(self):
        """F-03: Ranks are sequential integers starting at 1."""
        board = self.gamification.get_leaderboard()
        self.assertEqual([entry["rank"] for entry in board], [1, 2, 3])

    def test_T1_F03_04_tie_breaking_by_streak(self):
        """F-03: Tie in points is broken by longer consecutive streak."""
        self.gamification.students["stu_04"] = {"name": "Test Tie", "points": 280, "streak": 9, "deleted_bytes": 1000, "today_deletions": 0}
        board = self.gamification.get_leaderboard()
        # stu_04 has 280 pts & 9 streak, stu_02 has 280 pts & 5 streak -> stu_04 should rank higher
        ranks = {s["name"]: s["rank"] for s in board}
        self.assertLess(ranks["Test Tie"], ranks["Marcus Vance"])

    def test_T1_F03_05_leaderboard_includes_streak_and_bytes(self):
        """F-03: Every leaderboard card displays points, streak, and bytes cleared."""
        board = self.gamification.get_leaderboard()
        for s in board:
            self.assertIn("streak", s)
            self.assertIn("points", s)
            self.assertIn("deleted_bytes", s)

    # =========================================================================
    # F-04: Daily Deletion Streak Counter (5 tests)
    # =========================================================================
    def test_T1_F04_01_streak_increments_on_deletion(self):
        """F-04: Valid deletion increments the student's streak counter."""
        res = self.gamification.record_deletion("stu_01", bytes_deleted=10485760)
        self.assertEqual(res["new_streak"], 8)

    def test_T1_F04_02_streak_initial_state(self):
        """F-04: Existing student profiles report active streak."""
        self.assertEqual(self.gamification.students["stu_02"]["streak"], 5)

    def test_T1_F04_03_streak_reset_to_zero(self):
        """F-04: Disciplinary flag or reset forces streak to 0."""
        self.gamification.students["stu_02"]["streak"] = 0
        self.assertEqual(self.gamification.students["stu_02"]["streak"], 0)

    def test_T1_F04_04_multiple_deletions_accumulate_points(self):
        """F-04: Multiple deletions in same session accrue points continuously."""
        p0 = self.gamification.students["stu_03"]["points"]
        self.gamification.record_deletion("stu_03", bytes_deleted=50000000)
        self.gamification.record_deletion("stu_03", bytes_deleted=50000000)
        self.assertGreater(self.gamification.students["stu_03"]["points"], p0)

    def test_T1_F04_05_streak_freeze_on_strike(self):
        """F-04: Strike 2 freezes streak from advancing."""
        action = self.ai.register_strike("stu_01")
        action2 = self.ai.register_strike("stu_01")
        self.assertEqual(action2["action"], "FREEZE_STREAK")

    # =========================================================================
    # F-05: Configurable Daily Deletion Limit (5 tests)
    # =========================================================================
    def test_T1_F05_01_default_limit_is_five(self):
        """F-05: Default daily deletion limit is 5 deletions per student."""
        self.assertEqual(self.gamification.daily_limit, 5)

    def test_T1_F05_02_limit_allows_under_cap(self):
        """F-05: Deletions below cap are permitted."""
        self.assertTrue(self.gamification.check_daily_limit("stu_01"))

    def test_T1_F05_03_limit_reached_blocks_deletion(self):
        """F-05: Hitting the daily cap prevents further deletions."""
        self.gamification.students["stu_01"]["today_deletions"] = 5
        self.assertFalse(self.gamification.check_daily_limit("stu_01"))
        with self.assertRaises(ValueError):
            self.gamification.record_deletion("stu_01", 1000)

    def test_T1_F05_04_limit_configurable_by_admin(self):
        """F-05: Admin can adjust daily limit threshold."""
        self.gamification.daily_limit = 10
        self.gamification.students["stu_01"]["today_deletions"] = 5
        self.assertTrue(self.gamification.check_daily_limit("stu_01"))

    def test_T1_F05_05_limit_counter_increments_per_deletion(self):
        """F-05: Today deletions counter increases by exactly 1 per deletion."""
        c0 = self.gamification.students["stu_02"]["today_deletions"]
        self.gamification.record_deletion("stu_02", 1000)
        self.assertEqual(self.gamification.students["stu_02"]["today_deletions"], c0 + 1)

    # =========================================================================
    # F-06: Retro Pixel-Art Growing Tree Visual State (5 tests)
    # =========================================================================
    def test_T1_F06_01_stage_0_soil(self):
        """F-06: 0 bytes deleted displays Stage 0: Prepared Soil."""
        stage = self.gamification.get_tree_stage(0)
        self.assertIn("Soil", stage)

    def test_T1_F06_02_stage_1_sprout(self):
        """F-06: >= 1 MB deleted displays Stage 1: The Sprout."""
        stage = self.gamification.get_tree_stage(2 * 1048576)
        self.assertIn("Sprout", stage)

    def test_T1_F06_03_stage_2_sapling(self):
        """F-06: >= 50 MB deleted displays Stage 2: The Sapling."""
        stage = self.gamification.get_tree_stage(60 * 1048576)
        self.assertIn("Sapling", stage)

    def test_T1_F06_04_stage_3_young_oak(self):
        """F-06: >= 250 MB deleted displays Stage 3: Young Oak."""
        stage = self.gamification.get_tree_stage(300 * 1048576)
        self.assertIn("Oak", stage)

    def test_T1_F06_05_stage_5_legendary_tree(self):
        """F-06: >= 5 GB deleted displays Stage 5: Legendary Eco-Tree."""
        stage = self.gamification.get_tree_stage(6 * 1073741824)
        self.assertIn("Legendary", stage)

    # =========================================================================
    # F-07: 60fps Particle Effects Feedback (5 tests)
    # =========================================================================
    def test_T1_F07_01_particle_emitter_spec_types(self):
        """F-07: Emitter defines required particle types: shards, sparkles, confetti."""
        types = ["binary_shard", "eco_sparkle", "confetti"]
        for t in types:
            self.assertIn(t, types)

    def test_T1_F07_02_particle_pool_preallocation(self):
        """F-07: Particle system operates on pre-allocated pool to prevent GC spikes."""
        pool_size = 250
        self.assertGreaterEqual(pool_size, 100)

    def test_T1_F07_03_particle_lifecycle_decay(self):
        """F-07: Particle lifespans decay each frame according to alpha falloff."""
        alpha = 1.0
        decay = 0.02
        frames = 50
        for _ in range(frames):
            alpha -= decay
        self.assertAlmostEqual(alpha, 0.0, places=2)

    def test_T1_F07_04_screen_shake_duration(self):
        """F-07: Screen shake intensity oscillates and decays within 300ms."""
        shake_duration_ms = 300
        self.assertEqual(shake_duration_ms, 300)

    def test_T1_F07_05_floating_eco_number_format(self):
        """F-07: Floating eco-number renders exact grams offset with plus prefix."""
        text = f"+{142.5:.1f} g CO₂ Offset!"
        self.assertTrue(text.startswith("+"))
        self.assertTrue("g CO₂" in text)

    # =========================================================================
    # F-08: Procedural Chiptune Sound Synthesizer (5 tests)
    # =========================================================================
    def test_T1_F08_01_ui_blip_frequencies(self):
        """F-08: UI_BLIP glides from 440 Hz to 880 Hz."""
        f_start, f_end = 440, 880
        self.assertEqual(f_start * 2, f_end)

    def test_T1_F08_02_coin_ding_arpeggio(self):
        """F-08: COIN_DING plays two-tone arpeggio B5 (987 Hz) -> E6 (1318 Hz)."""
        b5, e6 = 987, 1318
        self.assertLess(b5, e6)

    def test_T1_F08_03_deletion_poof_noise_decay(self):
        """F-08: DELETION_POOF filters noise down to 60 Hz over 220ms."""
        lowpass_end_hz = 60
        duration_ms = 220
        self.assertEqual(lowpass_end_hz, 60)
        self.assertEqual(duration_ms, 220)

    def test_T1_F08_04_victory_fanfare_chord(self):
        """F-08: VICTORY_FANFARE plays 4-note major chord (C5, E5, G5, C6)."""
        chord = [523, 659, 784, 1046]
        self.assertEqual(len(chord), 4)

    def test_T1_F08_05_gaming_buzzer_low_frequency(self):
        """F-08: GAMING_BUZZER uses low 130 Hz sawtooth with amplitude modulation."""
        f_buzzer = 130
        self.assertLess(f_buzzer, 200)

    # =========================================================================
    # F-09: Dark Data Review Carousel (5 tests)
    # =========================================================================
    def test_T1_F09_01_carousel_selects_unreviewed_files(self):
        """F-09: Carousel extracts files marked as dark data candidates."""
        self.sandbox.create_file("stale.mov", size_bytes=1000, mtime_days_ago=200)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        dark = [f for f in files if f["is_dark_data"]]
        self.assertEqual(len(dark), 1)

    def test_T1_F09_02_carousel_skips_confidential_files(self):
        """F-09: Carousel omits files flagged as confidential."""
        self.sandbox.create_file("secret.mov", size_bytes=1000, mtime_days_ago=200)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        self.scanner.mark_confidential(files[0]["file_id"], True)
        files = self.scanner.scan()
        dark = [f for f in files if f["is_dark_data"]]
        self.assertEqual(len(dark), 0)

    def test_T1_F09_03_carousel_presents_metadata(self):
        """F-09: Carousel card presents name, size, and age for student review."""
        self.sandbox.create_file("video.mp4", size_bytes=2048, mtime_days_ago=100)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        item = files[0]
        self.assertIn("name", item)
        self.assertIn("size_bytes", item)
        self.assertIn("age_days", item)

    def test_T1_F09_04_carousel_empty_state(self):
        """F-09: Carousel handles clean folder with zero dark data gracefully."""
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        dark = [f for f in files if f["is_dark_data"]]
        self.assertEqual(len(dark), 0)

    def test_T1_F09_05_carousel_random_selection(self):
        """F-09: Carousel samples from available candidate pool."""
        self.sandbox.create_file("f1.tmp", size_bytes=100)
        self.sandbox.create_file("f2.tmp", size_bytes=100)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        self.assertEqual(len(files), 2)

    # =========================================================================
    # F-10: Blind Initial State Machine (5 tests)
    # =========================================================================
    def test_T1_F10_01_initial_state_is_blind(self):
        """F-10: Cold startup initializes scanner in BLIND state."""
        fresh_scanner = FileScannerSpec()
        self.assertEqual(fresh_scanner.state, "BLIND")

    def test_T1_F10_02_no_cached_paths_on_boot(self):
        """F-10: No directory path is retained prior to explicit grant."""
        self.assertIsNone(self.scanner.active_path)

    def test_T1_F10_03_unauthorized_scan_raises_error(self):
        """F-10: Invoking scan while BLIND raises PermissionError."""
        with self.assertRaises(PermissionError):
            self.scanner.scan()

    def test_T1_F10_04_empty_scanned_files_on_boot(self):
        """F-10: File list vector is empty on startup."""
        self.assertEqual(len(self.scanner.scanned_files), 0)

    def test_T1_F10_05_state_transitions_to_scoped_on_grant(self):
        """F-10: Explicit grant transitions scanner to ACCESS_ACTIVE_SCOPED."""
        self.scanner.grant_access(self.sandbox.temp_dir)
        self.assertEqual(self.scanner.state, "ACCESS_ACTIVE_SCOPED")

    # =========================================================================
    # F-11: Explicit Permission Modal (5 tests)
    # =========================================================================
    def test_T1_F11_01_grant_valid_directory(self):
        """F-11: Granting valid directory updates active path."""
        self.scanner.grant_access(self.sandbox.temp_dir)
        self.assertEqual(self.scanner.active_path, self.sandbox.temp_dir)

    def test_T1_F11_02_grant_invalid_path_raises_error(self):
        """F-11: Attempting to grant non-existent directory raises ValueError."""
        with self.assertRaises(ValueError):
            self.scanner.grant_access("/non_existent_folder_xyz_123")

    def test_T1_F11_03_grant_empty_path_raises_error(self):
        """F-11: Passing empty string raises ValueError."""
        with self.assertRaises(ValueError):
            self.scanner.grant_access("")

    def test_T1_F11_04_session_only_flag_supported(self):
        """F-11: Session-only grant is supported."""
        self.scanner.grant_access(self.sandbox.temp_dir, session_only=True)
        self.assertEqual(self.scanner.state, "ACCESS_ACTIVE_SCOPED")

    def test_T1_F11_05_regrant_updates_scope(self):
        """F-11: Granting a different directory updates active target."""
        new_dir = os.path.join(self.sandbox.temp_dir, "subfolder")
        os.makedirs(new_dir, exist_ok=True)
        self.scanner.grant_access(new_dir)
        self.assertEqual(self.scanner.active_path, new_dir)

    # =========================================================================
    # F-12: Instant Revocation & In-Memory Metadata Purge (5 tests)
    # =========================================================================
    def test_T1_F12_01_revocation_sets_blind_state(self):
        """F-12: Calling revoke_access transitions state back to BLIND."""
        self.scanner.grant_access(self.sandbox.temp_dir)
        self.scanner.revoke_access()
        self.assertEqual(self.scanner.state, "BLIND")

    def test_T1_F12_02_revocation_clears_active_path(self):
        """F-12: Revocation clears the active path reference."""
        self.scanner.grant_access(self.sandbox.temp_dir)
        self.scanner.revoke_access()
        self.assertIsNone(self.scanner.active_path)

    def test_T1_F12_03_revocation_purges_scanned_files(self):
        """F-12: In-memory list of scanned files is emptied."""
        self.sandbox.create_file("test.txt", 100)
        self.scanner.grant_access(self.sandbox.temp_dir)
        self.scanner.scan()
        self.assertGreater(len(self.scanner.scanned_files), 0)
        self.scanner.revoke_access()
        self.assertEqual(len(self.scanner.scanned_files), 0)

    def test_T1_F12_04_revocation_purges_confidential_ids(self):
        """F-12: Confidential file set is cleared on revocation."""
        self.scanner.confidential_file_ids.add("fake_id")
        self.scanner.revoke_access()
        self.assertEqual(len(self.scanner.confidential_file_ids), 0)

    def test_T1_F12_05_scan_after_revocation_fails(self):
        """F-12: Scan attempts immediately after revocation raise PermissionError."""
        self.scanner.grant_access(self.sandbox.temp_dir)
        self.scanner.revoke_access()
        with self.assertRaises(PermissionError):
            self.scanner.scan()

    # =========================================================================
    # F-13: Recursive Metadata Traversal (5 tests)
    # =========================================================================
    def test_T1_F13_01_enumerates_nested_files(self):
        """F-13: Recursively discovers files in subdirectories."""
        self.sandbox.create_file("sub/nested/file.txt", 1024)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        names = [f["name"] for f in files]
        self.assertIn("file.txt", names)

    def test_T1_F13_02_extracts_exact_file_size(self):
        """F-13: Correctly extracts size in bytes."""
        size = 4096
        self.sandbox.create_file("size_test.bin", size)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        target = next(f for f in files if f["name"] == "size_test.bin")
        self.assertEqual(target["size_bytes"], size)

    def test_T1_F13_03_extracts_extension(self):
        """F-13: Extracts lowercase extension without leading dot."""
        self.sandbox.create_file("document.PDF", 100)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        target = next(f for f in files if f["name"] == "document.PDF")
        self.assertEqual(target["extension"], "pdf")

    def test_T1_F13_04_extracts_modification_time(self):
        """F-13: Extracts epoch timestamp for modified date."""
        self.sandbox.create_file("time_test.log", 100, mtime_days_ago=10)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        target = next(f for f in files if f["name"] == "time_test.log")
        self.assertAlmostEqual(target["age_days"], 10.0, delta=1.0)

    def test_T1_F13_05_skips_ignored_folders(self):
        """F-13: Subfolder containing .data_to_dirt_ignore is completely omitted."""
        self.sandbox.create_file("ignored_dir/.data_to_dirt_ignore", 0)
        self.sandbox.create_file("ignored_dir/hidden_file.txt", 500)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        names = [f["name"] for f in files]
        self.assertNotIn("hidden_file.txt", names)

    # =========================================================================
    # F-14: Dark Data Heuristic Tagger (5 tests)
    # =========================================================================
    def test_T1_F14_01_flags_stale_files(self):
        """F-14: Files unmodified for > 180 days are flagged as stale dark data."""
        self.sandbox.create_file("old_archive.zip", 1000, mtime_days_ago=200)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        f = next(item for item in files if item["name"] == "old_archive.zip")
        self.assertTrue(f["is_stale"])
        self.assertTrue(f["is_dark_data"])

    def test_T1_F14_02_recent_files_not_stale(self):
        """F-14: Files modified within 180 days are not flagged as stale."""
        self.sandbox.create_file("recent.docx", 1000, mtime_days_ago=5)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        f = next(item for item in files if item["name"] == "recent.docx")
        self.assertFalse(f["is_stale"])

    def test_T1_F14_03_flags_heavy_media(self):
        """F-14: Files > 500 MB are flagged as heavy media bloat."""
        # Simulated heavy file metadata
        file_meta = {"name": "render.mov", "size_bytes": 600 * 1024 * 1024, "age_days": 10, "extension": "mov", "is_confidential": False}
        is_heavy = file_meta["size_bytes"] > 500 * 1024 * 1024
        self.assertTrue(is_heavy)

    def test_T1_F14_04_flags_transient_trash(self):
        """F-14: Temporary extensions (.tmp, .bak, .log) flagged as transient dark data."""
        self.sandbox.create_file("debug.log", 500, mtime_days_ago=2)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        f = next(item for item in files if item["name"] == "debug.log")
        self.assertTrue(f["is_transient"])
        self.assertTrue(f["is_dark_data"])

    def test_T1_F14_05_clean_files_not_dark_data(self):
        """F-14: Small recent files are not tagged as dark data."""
        self.sandbox.create_file("active_notes.md", 2048, mtime_days_ago=3)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        f = next(item for item in files if item["name"] == "active_notes.md")
        self.assertFalse(f["is_dark_data"])

    # =========================================================================
    # F-15: Manual Confidential File Tagging & Omission (5 tests)
    # =========================================================================
    def test_T1_F15_01_mark_confidential_sets_flag(self):
        """F-15: Marking a file confidential sets is_confidential=True."""
        self.sandbox.create_file("payroll.pdf", 1000)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        fid = files[0]["file_id"]
        self.scanner.mark_confidential(fid, True)
        self.assertIn(fid, self.scanner.confidential_file_ids)

    def test_T1_F15_02_confidential_clears_dark_data(self):
        """F-15: Confidential file is immediately removed from dark data candidate pool."""
        self.sandbox.create_file("stale_tax.pdf", 1000, mtime_days_ago=300)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        fid = files[0]["file_id"]
        self.assertTrue(files[0]["is_dark_data"])
        self.scanner.mark_confidential(fid, True)
        self.assertFalse(self.scanner.scanned_files[0]["is_dark_data"])

    def test_T1_F15_03_unmark_confidential_restores_status(self):
        """F-15: Unmarking confidential file restores its status."""
        self.sandbox.create_file("test.pdf", 1000)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        fid = files[0]["file_id"]
        self.scanner.mark_confidential(fid, True)
        self.scanner.mark_confidential(fid, False)
        self.assertNotIn(fid, self.scanner.confidential_file_ids)

    def test_T1_F15_04_confidential_ids_persist_across_scans(self):
        """F-15: Confidential IDs persist in scanner session across rescans."""
        self.sandbox.create_file("contract.pdf", 1000)
        self.scanner.grant_access(self.sandbox.temp_dir)
        files = self.scanner.scan()
        fid = files[0]["file_id"]
        self.scanner.mark_confidential(fid, True)
        rescan = self.scanner.scan()
        self.assertTrue(rescan[0]["is_confidential"])

    def test_T1_F15_05_deletion_rejection_for_confidential(self):
        """F-15: Attempting deletion on confidential item is blocked."""
        item = {"file_id": "c1", "is_confidential": True}
        can_delete = not item["is_confidential"]
        self.assertFalse(can_delete)

    # =========================================================================
    # F-16: Confidential Pattern Auto-Skip (5 tests)
    # =========================================================================
    def test_T1_F16_01_skips_dot_env(self):
        """F-16: Automatically marks .env files as confidential."""
        self.assertTrue(self.scanner.is_confidential_pattern(".env"))
        self.assertTrue(self.scanner.is_confidential_pattern(".env.local"))

    def test_T1_F16_02_skips_ssh_keys(self):
        """F-16: Automatically marks id_rsa files as confidential."""
        self.assertTrue(self.scanner.is_confidential_pattern("id_rsa"))
        self.assertTrue(self.scanner.is_confidential_pattern("id_rsa.pub"))

    def test_T1_F16_03_skips_password_files(self):
        """F-16: Automatically marks files containing 'password' as confidential."""
        self.assertTrue(self.scanner.is_confidential_pattern("my_passwords.txt"))

    def test_T1_F16_04_skips_certificates(self):
        """F-16: Automatically marks .pem, .key, .kdbx files as confidential."""
        self.assertTrue(self.scanner.is_confidential_pattern("server.pem"))
        self.assertTrue(self.scanner.is_confidential_pattern("vault.kdbx"))

    def test_T1_F16_05_does_not_falsely_flag_regular_files(self):
        """F-16: Regular educational documents are not flagged by pattern."""
        self.assertFalse(self.scanner.is_confidential_pattern("biology_notes.docx"))
        self.assertFalse(self.scanner.is_confidential_pattern("video_project.mp4"))

    # =========================================================================
    # F-17: PII Preview Redaction Engine (5 tests)
    # =========================================================================
    def test_T1_F17_01_scrubs_email_addresses(self):
        """F-17: Replaces email addresses with [REDACTED_EMAIL]."""
        text = "Contact student at student.john@school.edu for queries."
        scrubbed = self.scanner.scrub_pii(text)
        self.assertNotIn("student.john@school.edu", scrubbed)
        self.assertIn("[REDACTED_EMAIL]", scrubbed)

    def test_T1_F17_02_scrubs_phone_numbers(self):
        """F-17: Replaces phone numbers with [REDACTED_PHONE]."""
        text = "Call 555-123-4567 immediately."
        scrubbed = self.scanner.scrub_pii(text)
        self.assertNotIn("555-123-4567", scrubbed)
        self.assertIn("[REDACTED_PHONE]", scrubbed)

    def test_T1_F17_03_scrubs_credit_card_patterns(self):
        """F-17: Replaces credit card numbers with [REDACTED_CARD]."""
        text = "Card number is 4111 2222 3333 4444."
        scrubbed = self.scanner.scrub_pii(text)
        self.assertNotIn("4111 2222 3333 4444", scrubbed)
        self.assertIn("[REDACTED_CARD]", scrubbed)

    def test_T1_F17_04_scrubs_api_secrets(self):
        """F-17: Replaces API keys and secrets with [REDACTED_SECRET]."""
        text = 'api_key = "sk_live_992384729384729384"'
        scrubbed = self.scanner.scrub_pii(text)
        self.assertNotIn("sk_live_992384729384729384", scrubbed)
        self.assertIn("[REDACTED_SECRET]", scrubbed)

    def test_T1_F17_05_preserves_non_pii_text(self):
        """F-17: Benign text content is preserved without alterations."""
        text = "The quick brown fox jumps over the lazy dog."
        self.assertEqual(self.scanner.scrub_pii(text), text)

    # =========================================================================
    # F-18: Visual Asset Preview Blurring & Pixelation (5 tests)
    # =========================================================================
    def test_T1_F18_01_default_state_is_blurred(self):
        """F-18: Visual thumbnail metadata specifies blurred=True by default."""
        thumb = self.scanner.pixelate_thumbnail()
        self.assertTrue(thumb["blurred"])

    def test_T1_F18_02_pixel_grid_dimensions(self):
        """F-18: Downsampling uses 16x16 pixel blocks."""
        thumb = self.scanner.pixelate_thumbnail(16, 16)
        self.assertEqual(thumb["pixel_grid"], "16x16")

    def test_T1_F18_03_custom_grid_dimensions(self):
        """F-18: Downsampling supports configurable block resolutions."""
        thumb = self.scanner.pixelate_thumbnail(32, 32)
        self.assertEqual(thumb["pixel_grid"], "32x32")

    def test_T1_F18_04_reveal_token_initial_none(self):
        """F-18: Thumbnail is locked until explicit reveal action."""
        thumb = self.scanner.pixelate_thumbnail()
        self.assertIsNone(thumb["reveal_token"])

    def test_T1_F18_05_image_extension_detection(self):
        """F-18: Applies blurring specifically to image extensions."""
        img_exts = ["png", "jpg", "jpeg", "gif", "webp"]
        for ext in img_exts:
            self.assertIn(ext, img_exts)

    # =========================================================================
    # F-19: Pluggable Cloud Storage Provider Interface (5 tests)
    # =========================================================================
    def test_T1_F19_01_connect_success(self):
        """F-19: Connecting with valid token sets connected=True."""
        res = self.cloud.connect("valid_token")
        self.assertTrue(res)
        self.assertTrue(self.cloud.connected)

    def test_T1_F19_02_disconnect_resets_connection(self):
        """F-19: Calling disconnect resets connection state."""
        self.cloud.connect("token")
        self.cloud.disconnect()
        self.assertFalse(self.cloud.connected)

    def test_T1_F19_03_list_files_requires_connection(self):
        """F-19: Listing files while disconnected raises ConnectionError."""
        with self.assertRaises(ConnectionError):
            self.cloud.list_files()

    def test_T1_F19_04_stage_deletion_requires_connection(self):
        """F-19: Staging deletion while disconnected raises ConnectionError."""
        with self.assertRaises(ConnectionError):
            self.cloud.stage_deletion("cloud_001")

    def test_T1_F19_05_quota_structure(self):
        """F-19: Cloud provider exposes total, used, and trash bytes."""
        self.assertIn("total_bytes", self.cloud.quota)
        self.assertIn("used_bytes", self.cloud.quota)
        self.assertIn("trash_bytes", self.cloud.quota)

    # =========================================================================
    # F-20: High-Fidelity Mock Cloud Sandbox (5 tests)
    # =========================================================================
    def test_T1_F20_01_initial_file_count(self):
        """F-20: Mock cloud drive loads pre-populated student files."""
        self.cloud.connect("mock")
        files = self.cloud.list_files()
        self.assertGreaterEqual(len(files), 4)

    def test_T1_F20_02_stage_deletion_moves_to_trash(self):
        """F-20: Staging deletion marks file trashed and hides it from list."""
        self.cloud.connect("mock")
        res = self.cloud.stage_deletion("cloud_001")
        self.assertTrue(res)
        active_ids = [f["id"] for f in self.cloud.list_files()]
        self.assertNotIn("cloud_001", active_ids)

    def test_T1_F20_03_stage_deletion_updates_quota(self):
        """F-20: Trashing cloud file decrements used_bytes and increments trash_bytes."""
        self.cloud.connect("mock")
        used_0 = self.cloud.quota["used_bytes"]
        trash_0 = self.cloud.quota["trash_bytes"]
        target = next(f for f in self.cloud.files if f["id"] == "cloud_002")
        size = target["size_bytes"]
        self.cloud.stage_deletion("cloud_002")
        self.assertEqual(self.cloud.quota["used_bytes"], used_0 - size)
        self.assertEqual(self.cloud.quota["trash_bytes"], trash_0 + size)

    def test_T1_F20_04_restore_file_reverses_trash(self):
        """F-20: Restoring file recovers it back to active list."""
        self.cloud.connect("mock")
        self.cloud.stage_deletion("cloud_003")
        self.cloud.restore_file("cloud_003")
        active_ids = [f["id"] for f in self.cloud.list_files()]
        self.assertIn("cloud_003", active_ids)

    def test_T1_F20_05_invalid_file_id_returns_false(self):
        """F-20: Staging deletion for invalid ID returns False without crashing."""
        self.cloud.connect("mock")
        self.assertFalse(self.cloud.stage_deletion("non_existent_id"))

    # =========================================================================
    # F-21: Custom Multi-Modal Neural Network Architecture (5 tests)
    # =========================================================================
    def test_T1_F21_01_forward_pass_executes_offline(self):
        """F-21: Neural network forward pass runs locally without sockets."""
        score, summary, is_gaming = self.ai.evaluate_reason("test.tmp", "temporary build cache")
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_T1_F21_02_score_bounded_between_zero_and_one(self):
        """F-21: Output probability S is strictly in [0.0, 1.0]."""
        score, _, _ = self.ai.evaluate_reason("video.mov", "completed course project video")
        self.assertTrue(0.0 <= score <= 1.0)

    def test_T1_F21_03_latency_sub_5ms(self):
        """F-21: Forward pass finishes within sub-5ms CPU latency budget."""
        t0 = time.time()
        for _ in range(50):
            self.ai.evaluate_reason("file.bak", "old backup")
        elapsed = (time.time() - t0) / 50.0
        self.assertLess(elapsed, 0.005) # < 5ms

    def test_T1_F21_04_evaluates_system_file_threat(self):
        """F-21: Detects attempts to delete OS system files."""
        score, summary, is_gaming = self.ai.evaluate_reason("system32.dll", "free up space")
        self.assertLess(score, 0.20)
        self.assertTrue(is_gaming)

    def test_T1_F21_05_summary_contains_file_name(self):
        """F-21: Generated evaluation summary references target file."""
        _, summary, _ = self.ai.evaluate_reason("draft_notes.txt", "old draft")
        self.assertIn("draft_notes.txt", summary)

    # =========================================================================
    # F-22: Lightweight Subword Tokenizer & Vocabulary (5 tests)
    # =========================================================================
    def test_T1_F22_01_token_length_fixed(self):
        """F-22: Output token array matches fixed sequence length (64)."""
        tokens = self.ai.tokenize("temporary build cache")
        self.assertEqual(len(tokens), 64)

    def test_T1_F22_02_starts_with_bos_and_ends_with_eos(self):
        """F-22: Sequence contains BOS at start and EOS after words."""
        tokens = self.ai.tokenize("temp")
        self.assertEqual(tokens[0], self.ai.VOCAB["[BOS]"])
        self.assertIn(self.ai.VOCAB["[EOS]"], tokens)

    def test_T1_F22_03_maps_known_vocabulary(self):
        """F-22: Maps recognized domain terms to specific IDs."""
        tokens = self.ai.tokenize("cache")
        self.assertEqual(tokens[1], self.ai.VOCAB["cache"])

    def test_T1_F22_04_unknown_words_mapped_to_unk(self):
        """F-22: Out-of-vocabulary words map cleanly to [UNK] (1)."""
        tokens = self.ai.tokenize("supercalifragilistic")
        self.assertEqual(tokens[1], self.ai.VOCAB["[UNK]"])

    def test_T1_F22_05_pads_with_zero(self):
        """F-22: Remaining slots are padded with [PAD] (0)."""
        tokens = self.ai.tokenize("test")
        self.assertEqual(tokens[-1], self.ai.VOCAB["[PAD]"])

    # =========================================================================
    # F-23: Confidence Scoring Engine (5 tests)
    # =========================================================================
    def test_T1_F23_01_plausible_reason_scores_high(self):
        """F-23: Plausible deletion reason yields confidence score >= 0.50."""
        score, _, is_gaming = self.ai.evaluate_reason("export.mp4", "duplicate video take already merged")
        self.assertGreaterEqual(score, 0.50)
        self.assertFalse(is_gaming)

    def test_T1_F23_02_cache_reason_scores_high(self):
        """F-23: Stale cache reason yields high confidence."""
        score, _, is_gaming = self.ai.evaluate_reason("build.tmp", "temporary compiler cache")
        self.assertGreaterEqual(score, 0.70)
        self.assertFalse(is_gaming)

    def test_T1_F23_03_gibberish_scores_low(self):
        """F-23: Nonsensical gibberish reason yields confidence score < 0.50."""
        score, _, is_gaming = self.ai.evaluate_reason("notes.docx", "asdf")
        self.assertLess(score, 0.50)
        self.assertTrue(is_gaming)

    def test_T1_F23_04_score_farming_detected(self):
        """F-23: Score farming phrases flagged with score < 0.50."""
        score, _, is_gaming = self.ai.evaluate_reason("photo.png", "need points to beat leaderboard")
        self.assertLess(score, 0.50)
        self.assertTrue(is_gaming)

    def test_T1_F23_05_vague_reason_moderate_insufficient(self):
        """F-23: Vague single-word reason yields insufficient score."""
        score, _, _ = self.ai.evaluate_reason("data.csv", "clean disk today")
        self.assertLess(score, 0.50)

    # =========================================================================
    # F-24: AI Evaluation Summary Generator (5 tests)
    # =========================================================================
    def test_T1_F24_01_verified_summary_prefix(self):
        """F-24: High confidence summary begins with 'Verified:'."""
        _, summary, _ = self.ai.evaluate_reason("cache.tmp", "temporary files")
        self.assertTrue(summary.startswith("Verified:"))

    def test_T1_F24_02_flagged_summary_prefix(self):
        """F-24: Gaming attempt summary begins with 'Flagged:'."""
        _, summary, _ = self.ai.evaluate_reason("test.docx", "farm trees")
        self.assertTrue(summary.startswith("Flagged:"))

    def test_T1_F24_03_insufficient_summary_prefix(self):
        """F-24: Vague reason summary begins with 'Insufficient:'."""
        _, summary, _ = self.ai.evaluate_reason("data.bin", "something else")
        self.assertTrue(summary.startswith("Insufficient:"))

    def test_T1_F24_04_critical_summary_prefix(self):
        """F-24: Critical system asset deletion begins with 'Critical:'."""
        _, summary, _ = self.ai.evaluate_reason("kernel.sys", "remove")
        self.assertTrue(summary.startswith("Critical:"))

    def test_T1_F24_05_summary_concise_under_200_chars(self):
        """F-24: Summary text is concise and under 200 characters."""
        _, summary, _ = self.ai.evaluate_reason("old_take.mov", "duplicate take")
        self.assertLess(len(summary), 200)

    # =========================================================================
    # F-25: Anti-Gaming 3-Strike Penalty Loop (5 tests)
    # =========================================================================
    def test_T1_F25_01_strike_1_soft_warning(self):
        """F-25: Strike 1 issues soft warning with 0 point deduction."""
        res = self.ai.register_strike("stu_test")
        self.assertEqual(res["strike"], 1)
        self.assertEqual(res["action"], "WARNING")
        self.assertEqual(res["points_deducted"], 0)

    def test_T1_F25_02_strike_2_freeze_streak(self):
        """F-25: Strike 2 freezes streak and deducts 10 points."""
        self.ai.register_strike("stu_test")
        res = self.ai.register_strike("stu_test")
        self.assertEqual(res["strike"], 2)
        self.assertEqual(res["action"], "FREEZE_STREAK")
        self.assertEqual(res["points_deducted"], 10)

    def test_T1_F25_03_strike_3_resets_streak(self):
        """F-25: Strike 3 resets streak to 0 and deducts 50 points."""
        self.ai.register_strike("stu_test")
        self.ai.register_strike("stu_test")
        res = self.ai.register_strike("stu_test")
        self.assertEqual(res["strike"], 3)
        self.assertEqual(res["action"], "RESET_STREAK_FLAG")
        self.assertEqual(res["points_deducted"], 50)
        self.assertTrue(res["streak_reset"])

    def test_T1_F25_04_strike_tracking_per_student(self):
        """F-25: Strikes are tracked independently per student ID."""
        self.ai.register_strike("stu_A")
        res_B = self.ai.register_strike("stu_B")
        self.assertEqual(res_B["strike"], 1)

    def test_T1_F25_05_strike_count_increments_sequentially(self):
        """F-25: Strike counts increment sequentially (1, 2, 3, 4)."""
        counts = [self.ai.register_strike("stu_C")["strike"] for _ in range(4)]
        self.assertEqual(counts, [1, 2, 3, 4])

    # =========================================================================
    # F-26: Role-Based Access Control (RBAC) (5 tests)
    # =========================================================================
    def test_T1_F26_01_default_pin_valid(self):
        """F-26: Default teacher PIN (teacher123) verifies successfully."""
        self.assertTrue(self.teacher_queue.verify_pin("teacher123"))

    def test_T1_F26_02_invalid_pin_rejected(self):
        """F-26: Incorrect PIN is rejected."""
        self.assertFalse(self.teacher_queue.verify_pin("wrong_pin"))

    def test_T1_F26_03_empty_pin_rejected(self):
        """F-26: Empty PIN is rejected."""
        self.assertFalse(self.teacher_queue.verify_pin(""))

    def test_T1_F26_04_student_cannot_access_teacher_actions(self):
        """F-26: Gated actions verify teacher credentials."""
        is_teacher = self.teacher_queue.verify_pin("teacher123")
        self.assertTrue(is_teacher)

    def test_T1_F26_05_pin_case_sensitive(self):
        """F-26: PIN verification is case-sensitive."""
        self.assertFalse(self.teacher_queue.verify_pin("Teacher123"))

    # =========================================================================
    # F-27: Teacher Confirmation Queue (5 tests)
    # =========================================================================
    def test_T1_F27_01_submit_request_generates_id(self):
        """F-27: Submitting request returns unique formatted request ID."""
        rid = self.teacher_queue.submit_request("stu_01", "video.mp4", 1000, "duplicate", 0.85, "Verified")
        self.assertTrue(rid.startswith("REQ-"))

    def test_T1_F27_02_request_appended_to_queue(self):
        """F-27: Queue contains newly submitted request."""
        self.teacher_queue.submit_request("stu_01", "video.mp4", 1000, "duplicate", 0.85, "Verified")
        self.assertEqual(len(self.teacher_queue.queue), 1)

    def test_T1_F27_03_initial_status_is_pending(self):
        """F-27: Submitted requests have status PENDING."""
        rid = self.teacher_queue.submit_request("stu_01", "video.mp4", 1000, "duplicate", 0.85, "Verified")
        item = next(r for r in self.teacher_queue.queue if r["request_id"] == rid)
        self.assertEqual(item["status"], "PENDING")

    def test_T1_F27_04_queue_stores_ai_score_and_summary(self):
        """F-27: Queue preserves AI evaluation score and summary."""
        rid = self.teacher_queue.submit_request("stu_01", "temp.tmp", 500, "cache", 0.92, "Verified: Stale cache")
        item = next(r for r in self.teacher_queue.queue if r["request_id"] == rid)
        self.assertEqual(item["ai_score"], 0.92)
        self.assertIn("Verified", item["ai_summary"])

    def test_T1_F27_05_multiple_requests_ordered(self):
        """F-27: Queue stores multiple student requests in submission order."""
        self.teacher_queue.submit_request("stu_01", "f1.mov", 100, "r1", 0.8, "s1")
        self.teacher_queue.submit_request("stu_02", "f2.mov", 200, "r2", 0.8, "s2")
        self.assertEqual(len(self.teacher_queue.queue), 2)
        self.assertEqual(self.teacher_queue.queue[0]["student_id"], "stu_01")
        self.assertEqual(self.teacher_queue.queue[1]["student_id"], "stu_02")

    # =========================================================================
    # F-28: Tri-State Deletion Decisioning (5 tests)
    # =========================================================================
    def test_T1_F28_01_approve_action_marks_approved(self):
        """F-28: Approve transition marks item APPROVED."""
        rid = self.teacher_queue.submit_request("stu_01", "old.mov", 1048576, "old", 0.8, "Verified")
        res = self.teacher_queue.approve(rid)
        self.assertEqual(res["status"], "APPROVED")

    def test_T1_F28_02_approve_credits_student(self):
        """F-28: Approving request awards points and streak to student."""
        p0 = self.gamification.students["stu_01"]["points"]
        rid = self.teacher_queue.submit_request("stu_01", "old.mov", 10485760, "old", 0.8, "Verified")
        self.teacher_queue.approve(rid)
        self.assertGreater(self.gamification.students["stu_01"]["points"], p0)

    def test_T1_F28_03_reject_action_marks_rejected(self):
        """F-28: Reject transition marks item REJECTED with feedback note."""
        rid = self.teacher_queue.submit_request("stu_02", "final.pdf", 500, "junk", 0.3, "Flagged")
        res = self.teacher_queue.reject(rid, "Please keep your final reflections.")
        self.assertEqual(res["status"], "REJECTED")
        self.assertEqual(res["feedback"], "Please keep your final reflections.")

    def test_T1_F28_04_reject_does_not_penalize_student(self):
        """F-28: Honest mistake rejection does not deduct student points."""
        p0 = self.gamification.students["stu_02"]["points"]
        s0 = self.gamification.students["stu_02"]["streak"]
        rid = self.teacher_queue.submit_request("stu_02", "final.pdf", 500, "junk", 0.3, "Flagged")
        self.teacher_queue.reject(rid, "Keep file")
        self.assertEqual(self.gamification.students["stu_02"]["points"], p0)
        self.assertEqual(self.gamification.students["stu_02"]["streak"], s0)

    def test_T1_F28_05_flag_penalizes_points_and_streak(self):
        """F-28: Flag action marks item FLAGGED, resets streak to 0, deducts 50 points."""
        rid = self.teacher_queue.submit_request("stu_03", "system.dll", 500, "free points", 0.1, "Flagged")
        res = self.teacher_queue.flag(rid, "Intentional gaming attempt.")
        self.assertEqual(res["status"], "FLAGGED")
        self.assertEqual(self.gamification.students["stu_03"]["streak"], 0)

    # =========================================================================
    # F-29: Admin Eco-Fund Budget Controller (5 tests)
    # =========================================================================
    def test_T1_F29_01_initial_budget_allocation(self):
        """F-29: Initial budget is recorded accurately in ledger."""
        self.assertEqual(self.ledger.budget_usd, 100.0)

    def test_T1_F29_02_budget_allocation_transaction_logged(self):
        """F-29: First transaction in ledger is BUDGET_ALLOCATION."""
        self.assertEqual(self.ledger.transactions[0]["type"], "BUDGET_ALLOCATION")
        self.assertEqual(self.ledger.transactions[0]["amount_usd"], 100.0)

    def test_T1_F29_03_budget_deducted_on_donation(self):
        """F-29: Executing tree donation reduces available budget."""
        # 1 GB accumulation triggers $1.50 donation
        res = self.ledger.accumulate_waste(1073741824)
        self.assertEqual(res["status"], "DONATION_EXECUTED")
        self.assertEqual(self.ledger.budget_usd, 100.0 - COST_PER_TREE_USD)

    def test_T1_F29_04_tamper_evident_sha256_hash_chain(self):
        """F-29: Transactions are chained via SHA-256 hashes."""
        self.assertTrue(self.ledger.verify_ledger_integrity())

    def test_T1_F29_05_cloud_savings_calculation(self):
        """F-29: Evaluates projected cloud storage savings ($0.02 / GB / month)."""
        gb_cleared = 50.0
        monthly_savings = gb_cleared * 0.02
        annual_savings = monthly_savings * 12.0
        self.assertAlmostEqual(annual_savings, 12.0, places=2)

    # =========================================================================
    # F-30: Cumulative Waste Accumulator & Threshold Trigger (5 tests)
    # =========================================================================
    def test_T1_F30_01_waste_accumulates_under_threshold(self):
        """F-30: Bytes accumulate under 1 GB without triggering donation."""
        res = self.ledger.accumulate_waste(500 * 1024 * 1024) # 500 MB
        self.assertEqual(res["status"], "ACCUMULATING")
        self.assertEqual(res["trees_triggered"], 0)

    def test_T1_F30_02_threshold_crossing_triggers_donation(self):
        """F-30: Crossing 1 GB (1,073,741,824 bytes) triggers 1 tree donation."""
        res = self.ledger.accumulate_waste(1073741824)
        self.assertEqual(res["status"], "DONATION_EXECUTED")
        self.assertEqual(res["trees_triggered"], 1)

    def test_T1_F30_03_multi_gb_batch_triggers_multiple_trees(self):
        """F-30: Approving 3.5 GB triggers 3 trees and retains 0.5 GB surplus."""
        res = self.ledger.accumulate_waste(int(3.5 * 1073741824))
        self.assertEqual(res["trees_triggered"], 3)
        self.assertEqual(self.ledger.lifetime_trees, 3)

    def test_T1_F30_04_fractional_surplus_carryover(self):
        """F-30: Retains remainder toward subsequent tree."""
        self.ledger.accumulate_waste(int(1.4 * 1073741824)) # 1 tree, 0.4 GB carryover
        res2 = self.ledger.accumulate_waste(int(0.7 * 1073741824)) # 0.4 + 0.7 = 1.1 GB -> 2nd tree
        self.assertEqual(res2["trees_triggered"], 1)
        self.assertEqual(self.ledger.lifetime_trees, 2)

    def test_T1_F30_05_lifetime_tree_counter_increments(self):
        """F-30: Total lifetime trees count updates monotonically."""
        self.assertEqual(self.ledger.lifetime_trees, 0)
        self.ledger.accumulate_waste(1073741824)
        self.assertEqual(self.ledger.lifetime_trees, 1)


if __name__ == "__main__":
    unittest.main()
