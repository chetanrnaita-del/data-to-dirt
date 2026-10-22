"""Comprehensive Unit Tests for Privacy-First File Scanner Service.

Validates:
- Blind initial state machine (zero filesystem access until explicit user permission).
- Scoped directory traversal extracting strictly metadata (zero content read during scan).
- Symlink loop protection and .data_to_dirt_ignore handling.
- Dark data heuristic tagging (stale >180d, heavy >500MB, duplicate sizes, cache artifacts).
- Confidential file marking, auto-pattern detection, and strict deletion exclusion.
- PII text preview redaction (emails, phones, cards, secrets) and preview blurring.
- Immediate revocation protocol and in-memory metadata wipe.
"""

import os
import time
import tempfile
import unittest
from src.services.scanner import (
    FileScanner,
    ScanState,
    ScannedFileMetadata,
    PermissionRequiredError,
    ConfidentialFileError,
    redact_text,
    HEAVY_FILE_THRESHOLD_BYTES,
)


class TestFileScanner(unittest.TestCase):
    """Test suite for FileScanner privacy guarantees, traversal, and heuristics."""

    def setUp(self):
        self.scanner = FileScanner()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root_path = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    # -------------------------------------------------------------------------
    # 1. Blind Initial State & Permission Lifecycle
    # -------------------------------------------------------------------------

    def test_blind_initial_state(self):
        """Scanner starts in BLIND state with zero files in memory."""
        self.assertEqual(self.scanner.get_state(), ScanState.BLIND)
        self.assertFalse(self.scanner.is_access_granted())
        self.assertEqual(len(self.scanner.get_scanned_files()), 0)

    def test_scan_in_blind_state_raises_permission_required(self):
        """Scanning without explicit user grant must raise PermissionRequiredError."""
        with self.assertRaises(PermissionRequiredError):
            self.scanner.scan()

    def test_request_access_invalid_paths(self):
        """Requesting access on non-existent or file paths raises appropriate errors."""
        with self.assertRaises(ValueError):
            self.scanner.request_access("")

        with self.assertRaises(FileNotFoundError):
            self.scanner.request_access(os.path.join(self.root_path, "does_not_exist"))

        # Create a file and verify NotADirectoryError
        test_file = os.path.join(self.root_path, "regular_file.txt")
        with open(test_file, "w") as f:
            f.write("sample")
        with self.assertRaises(NotADirectoryError):
            self.scanner.request_access(test_file)

    def test_request_access_valid_directory(self):
        """Valid folder path transitions scanner to ACCESS_ACTIVE_SCOPED."""
        granted = self.scanner.request_access(self.root_path, session_only=True)
        self.assertTrue(granted)
        self.assertTrue(self.scanner.is_access_granted())
        self.assertEqual(self.scanner.get_state(), ScanState.ACCESS_ACTIVE_SCOPED)

    def test_request_access_nonexistent_directory_raises_file_not_found(self):
        """Requesting access on a non-existent directory raises FileNotFoundError and remains BLIND."""
        fake_path = os.path.join(self.root_path, "missing_subdir_12345")
        with self.assertRaises(FileNotFoundError) as ctx:
            self.scanner.request_access(fake_path)

        self.assertIn("does not exist", str(ctx.exception).lower())
        self.assertEqual(self.scanner.get_state(), ScanState.BLIND)
        self.assertFalse(self.scanner.is_access_granted())
        self.assertEqual(len(self.scanner.get_scanned_files()), 0)

    def test_request_access_restricted_directory_raises_permission_error(self):
        """Requesting access on an unreadable directory raises PermissionError and remains BLIND."""
        restricted_dir = os.path.join(self.root_path, "restricted_access_dir")
        os.makedirs(restricted_dir, exist_ok=True)
        os.chmod(restricted_dir, 0o000)
        try:
            # Skip if running as root (UID 0 ignores 000 permissions)
            if hasattr(os, "getuid") and os.getuid() == 0:
                self.skipTest("Running as root; filesystem permission bit 000 is bypassed by superuser.")

            with self.assertRaises(PermissionError) as ctx:
                self.scanner.request_access(restricted_dir)

            err_msg = str(ctx.exception).lower()
            self.assertTrue(
                "permission denied" in err_msg or "operation not permitted" in err_msg,
                f"Expected permission error message, got: {ctx.exception}"
            )
            self.assertEqual(self.scanner.get_state(), ScanState.BLIND)
            self.assertFalse(self.scanner.is_access_granted())
        finally:
            os.chmod(restricted_dir, 0o755)

    def test_scan_unreadable_directory_sets_error_state_and_raises(self):
        """Scanning an unreadable directory raises PermissionError and sets ScanState.ERROR."""
        scan_dir = os.path.join(self.root_path, "scan_perm_error_dir")
        os.makedirs(scan_dir, exist_ok=True)

        # Grant access while directory is readable
        self.scanner.request_access(scan_dir)
        self.assertEqual(self.scanner.get_state(), ScanState.ACCESS_ACTIVE_SCOPED)

        # Revoke read permissions right before scanning to test scan() traversal error capture
        os.chmod(scan_dir, 0o000)
        try:
            if hasattr(os, "getuid") and os.getuid() == 0:
                self.skipTest("Running as root; filesystem permission bit 000 is bypassed by superuser.")

            with self.assertRaises(PermissionError):
                self.scanner.scan()

            self.assertEqual(self.scanner.get_state(), ScanState.ERROR)
            self.assertEqual(len(self.scanner.get_scanned_files()), 0)
        finally:
            os.chmod(scan_dir, 0o755)

    def test_request_access_tilde_and_quotes(self):
        """Requesting access strips wrapping quotes and expands tilde correctly."""
        quoted_path = f'"{self.root_path}"'
        self.assertTrue(self.scanner.request_access(quoted_path))
        self.assertEqual(self.scanner._active_path, self.root_path)

        home_dir = os.path.expanduser("~")
        if os.path.isdir(home_dir):
            self.assertTrue(self.scanner.request_access("~"))
            self.assertEqual(self.scanner._active_path, home_dir)

    # -------------------------------------------------------------------------
    # 2. Scoped Traversal & Metadata Extraction (Zero Content Reading)
    # -------------------------------------------------------------------------

    def test_metadata_extraction_integrity(self):
        """Verify scanner extracts name, size, mtime, atime, mime without reading content."""
        # Create varied test files
        video_file = os.path.join(self.root_path, "presentation.mp4")
        with open(video_file, "wb") as f:
            f.write(b"0" * 4096)

        doc_dir = os.path.join(self.root_path, "subdocs")
        os.makedirs(doc_dir, exist_ok=True)
        doc_file = os.path.join(doc_dir, "notes.pdf")
        with open(doc_file, "wb") as f:
            f.write(b"1" * 2048)

        self.scanner.request_access(self.root_path)
        items = self.scanner.scan()

        self.assertEqual(self.scanner.get_state(), ScanState.COMPLETED)
        self.assertEqual(len(items), 2)

        file_map = {item.file_name: item for item in items}

        # Assert presentation.mp4
        self.assertIn("presentation.mp4", file_map)
        mp4_item = file_map["presentation.mp4"]
        self.assertEqual(mp4_item.size_bytes, 4096)
        self.assertEqual(mp4_item.extension, "mp4")
        self.assertEqual(mp4_item.mime_category, "video")
        self.assertTrue(mp4_item.file_id.startswith("f_"))
        self.assertFalse(mp4_item.is_confidential)

        # Assert notes.pdf
        self.assertIn("notes.pdf", file_map)
        pdf_item = file_map["notes.pdf"]
        self.assertEqual(pdf_item.size_bytes, 2048)
        self.assertEqual(pdf_item.extension, "pdf")
        self.assertEqual(pdf_item.mime_category, "document")
        self.assertEqual(pdf_item.relative_path, os.path.join("subdocs", "notes.pdf"))

    # -------------------------------------------------------------------------
    # 3. Symlink Loop Protection & Ignore Files
    # -------------------------------------------------------------------------

    def test_symlink_safety(self):
        """Scanner ignores symlinks and prevents infinite recursion cycles."""
        target_dir = os.path.join(self.root_path, "real_folder")
        os.makedirs(target_dir, exist_ok=True)
        sample_file = os.path.join(target_dir, "sample.txt")
        with open(sample_file, "w") as f:
            f.write("content")

        # Create recursive symlink cycle
        symlink_path = os.path.join(target_dir, "loop_link")
        try:
            os.symlink(self.root_path, symlink_path)
        except OSError:
            self.skipTest("Symlinks not supported on this filesystem.")

        self.scanner.request_access(self.root_path)
        items = self.scanner.scan()

        # Should complete without infinite recursion and enumerate only real sample.txt
        names = [item.file_name for item in items]
        self.assertIn("sample.txt", names)
        self.assertNotIn("loop_link", names)

    def test_data_to_dirt_ignore_directory(self):
        """Subdirectories containing .data_to_dirt_ignore are completely skipped."""
        ignored_folder = os.path.join(self.root_path, "ignored_dir")
        os.makedirs(ignored_folder, exist_ok=True)

        with open(os.path.join(ignored_folder, ".data_to_dirt_ignore"), "w") as f:
            f.write("# ignore this entire directory")

        with open(os.path.join(ignored_folder, "secret_data.csv"), "w") as f:
            f.write("1,2,3")

        allowed_file = os.path.join(self.root_path, "allowed.txt")
        with open(allowed_file, "w") as f:
            f.write("public")

        self.scanner.request_access(self.root_path)
        items = self.scanner.scan()

        names = [item.file_name for item in items]
        self.assertIn("allowed.txt", names)
        self.assertNotIn("secret_data.csv", names)

    # -------------------------------------------------------------------------
    # 4. Dark Data Heuristics
    # -------------------------------------------------------------------------

    def test_stale_relic_heuristic(self):
        """Files unmodified & unaccessed for >180 days are tagged as dark data."""
        stale_file = os.path.join(self.root_path, "ancient_paper.docx")
        with open(stale_file, "w") as f:
            f.write("old term paper")

        # Set mtime & atime to 200 days ago
        now = time.time()
        two_hundred_days_ago = now - (200.0 * 86400.0)
        os.utime(stale_file, (two_hundred_days_ago, two_hundred_days_ago))

        fresh_file = os.path.join(self.root_path, "fresh_paper.docx")
        with open(fresh_file, "w") as f:
            f.write("recent paper")

        self.scanner.request_access(self.root_path)
        items = self.scanner.scan(reference_time=now)
        file_map = {item.file_name: item for item in items}

        self.assertTrue(file_map["ancient_paper.docx"].is_dark_data_candidate)
        self.assertIn("Stale relic", file_map["ancient_paper.docx"].dark_data_reason)

        self.assertFalse(file_map["fresh_paper.docx"].is_dark_data_candidate)

    def test_heavy_file_heuristic(self):
        """Files >= 500 MB threshold are tagged as heavy media bloat."""
        custom_scanner = FileScanner(heavy_threshold_bytes=1000)  # Use 1000 bytes for fast test
        heavy_file = os.path.join(self.root_path, "render.raw")
        with open(heavy_file, "wb") as f:
            f.write(b"x" * 1500)

        custom_scanner.request_access(self.root_path)
        items = custom_scanner.scan()
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0].is_dark_data_candidate)
        self.assertIn("Heavy file bloat", items[0].dark_data_reason)

    def test_duplicate_file_heuristic(self):
        """Files with matching non-zero sizes are flagged as potential duplicates."""
        dup1 = os.path.join(self.root_path, "photo_copy1.jpg")
        dup2 = os.path.join(self.root_path, "photo_copy2.jpg")
        unique = os.path.join(self.root_path, "unique.jpg")

        with open(dup1, "wb") as f:
            f.write(b"a" * 500)
        with open(dup2, "wb") as f:
            f.write(b"b" * 500)
        with open(unique, "wb") as f:
            f.write(b"c" * 600)

        self.scanner.request_access(self.root_path)
        items = self.scanner.scan()
        file_map = {item.file_name: item for item in items}

        self.assertTrue(file_map["photo_copy1.jpg"].is_dark_data_candidate)
        self.assertIn("Potential duplicate", file_map["photo_copy1.jpg"].dark_data_reason)
        self.assertTrue(file_map["photo_copy2.jpg"].is_dark_data_candidate)

        # Unique file has no duplicate reason
        self.assertNotIn("Potential duplicate", file_map["unique.jpg"].dark_data_reason)

    def test_transient_cache_heuristic(self):
        """Temporary files like .tmp and .log are flagged as dark data."""
        tmp_file = os.path.join(self.root_path, "build.tmp")
        with open(tmp_file, "w") as f:
            f.write("transient")

        self.scanner.request_access(self.root_path)
        items = self.scanner.scan()
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0].is_dark_data_candidate)
        self.assertIn("Temporary cache/artifact", items[0].dark_data_reason)

    # -------------------------------------------------------------------------
    # 5. Confidential File Marking & Exclusion Guarantees
    # -------------------------------------------------------------------------

    def test_automatic_confidential_pattern_detection(self):
        """Sensitive patterns (.env, id_rsa, passwords) are automatically tagged confidential."""
        env_file = os.path.join(self.root_path, ".env.production")
        with open(env_file, "w") as f:
            f.write("SECRET_KEY=123")

        rsa_file = os.path.join(self.root_path, "id_rsa_backup")
        with open(rsa_file, "w") as f:
            f.write("PRIVATE KEY")

        pwd_file = os.path.join(self.root_path, "mypasswords.txt")
        with open(pwd_file, "w") as f:
            f.write("credentials")

        self.scanner.request_access(self.root_path)
        items = self.scanner.scan()
        file_map = {item.file_name: item for item in items}

        self.assertTrue(file_map[".env.production"].is_confidential)
        self.assertTrue(file_map["id_rsa_backup"].is_confidential)
        self.assertTrue(file_map["mypasswords.txt"].is_confidential)

    def test_manual_confidential_marking_and_exclusion(self):
        """Manually marked confidential files are strictly excluded from deletion candidates."""
        test_file = os.path.join(self.root_path, "family_tax_document.pdf")
        with open(test_file, "w") as f:
            f.write("tax info")

        # Also set it as stale so it would otherwise be a dark data candidate
        now = time.time()
        os.utime(test_file, (now - 300 * 86400, now - 300 * 86400))

        self.scanner.request_access(self.root_path)
        items = self.scanner.scan(reference_time=now)
        item = items[0]

        # Prior to marking confidential, it is a candidate
        self.assertIn(item, self.scanner.get_deletion_candidates())

        # Mark confidential
        self.scanner.mark_confidential(item.file_id, is_confidential=True)
        self.assertTrue(item.is_confidential)

        # Must be strictly omitted from deletion candidates
        candidates = self.scanner.get_deletion_candidates()
        self.assertNotIn(item, candidates)

        # Operating or deleting on confidential file raises ConfidentialFileError
        with self.assertRaises(ConfidentialFileError):
            self.scanner.assert_can_operate(item.file_id)

    # -------------------------------------------------------------------------
    # 6. PII Text Preview Redaction & Blurring
    # -------------------------------------------------------------------------

    def test_pii_text_redaction_regex(self):
        """Verify emails, phone numbers, credit cards, and API secrets are scrubbed."""
        raw_text = (
            "Contact me at student.alex@school.edu.sg or +65 9123 4567. "
            "Card number: 4111-2222-3333-4444. "
            "api_key = 'sk_live_9876543210abcdef'. "
            "Password: supersecretpass123!"
        )
        redacted = redact_text(raw_text)

        self.assertNotIn("student.alex@school.edu.sg", redacted)
        self.assertIn("[REDACTED_EMAIL]", redacted)

        self.assertNotIn("9123 4567", redacted)
        self.assertIn("[REDACTED_PHONE]", redacted)

        self.assertNotIn("4111-2222-3333-4444", redacted)
        self.assertIn("[REDACTED_CARD]", redacted)

        self.assertNotIn("sk_live_9876543210abcdef", redacted)
        self.assertNotIn("supersecretpass123!", redacted)
        self.assertIn("[REDACTED_SECRET]", redacted)

    def test_safe_preview_text_and_blurring_controls(self):
        """Preview snippet generation scrubs PII and supports toggleable blurring."""
        doc_path = os.path.join(self.root_path, "confidential_meeting.txt")
        with open(doc_path, "w") as f:
            f.write("Reach out to principal@domain.org for access tokens.")

        self.scanner.request_access(self.root_path)
        items = self.scanner.scan()
        item = items[0]

        # Get preview text
        preview = self.scanner.get_safe_preview_text(item.file_id)
        self.assertIn("[REDACTED_EMAIL]", preview)
        self.assertNotIn("principal@domain.org", preview)

        # Blurring preference
        self.assertTrue(self.scanner.is_preview_blurred(item.file_id))
        meta = self.scanner.get_preview_metadata(item.file_id)
        self.assertEqual(meta["blur_filter"], "blur(12px)")

        # Reveal preview
        self.scanner.set_preview_blurred(item.file_id, False)
        self.assertFalse(self.scanner.is_preview_blurred(item.file_id))
        meta_unblurred = self.scanner.get_preview_metadata(item.file_id)
        self.assertEqual(meta_unblurred["blur_filter"], "none")

    def test_confidential_file_blocks_preview(self):
        """Confidential files strictly forbid preview text inspection."""
        secret_file = os.path.join(self.root_path, "medical_record.txt")
        with open(secret_file, "w") as f:
            f.write("Sensitive clinical diagnosis")

        self.scanner.request_access(self.root_path)
        items = self.scanner.scan()
        item = items[0]
        self.scanner.mark_confidential(item.file_id, True)

        with self.assertRaises(ConfidentialFileError):
            self.scanner.get_safe_preview_text(item.file_id)

    # -------------------------------------------------------------------------
    # 7. Instant Revocation Protocol & Memory Wipe
    # -------------------------------------------------------------------------

    def test_instant_revocation_protocol(self):
        """Revocation immediately zeroes in-memory metadata and returns to BLIND state."""
        # Create 5 files
        for i in range(5):
            with open(os.path.join(self.root_path, f"item_{i}.dat"), "w") as f:
                f.write(f"data {i}")

        self.scanner.request_access(self.root_path)
        items = self.scanner.scan()
        self.assertEqual(len(items), 5)
        self.assertEqual(len(self.scanner.get_scanned_files()), 5)

        # Trigger instant revocation
        purged = self.scanner.revoke_access()
        self.assertEqual(purged, 5)

        # Assert memory wipe and state reset
        self.assertEqual(self.scanner.get_state(), ScanState.BLIND)
        self.assertFalse(self.scanner.is_access_granted())
        self.assertEqual(len(self.scanner.get_scanned_files()), 0)

        # Subsequent scan raises error until re-granted
        with self.assertRaises(PermissionRequiredError):
            self.scanner.scan()


if __name__ == "__main__":
    unittest.main()
