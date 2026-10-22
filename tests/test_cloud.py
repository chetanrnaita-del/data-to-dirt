"""Comprehensive Unit Tests for Cloud Storage Provider Integrations.

Validates:
- ICloudStorageProvider abstract interface contract.
- MockCloudProvider high-fidelity offline sandbox:
  - Realistic school drive hierarchy and metadata enumeration.
  - Quota calculation (total, active used, trash, dark data candidate bytes).
  - Safe non-destructive trash staging and restoration.
  - Sandbox reset idempotence.
- GoogleDriveProvider live client abstraction and transparent offline fallback.
"""

import unittest
from src.services.cloud_storage import (
    ICloudStorageProvider,
    MockCloudProvider,
    GoogleDriveProvider,
    CloudFileItem,
    CloudQuotaInfo,
    DEFAULT_TOTAL_QUOTA_BYTES,
    DEFAULT_INITIAL_TRASH_BYTES,
)


class TestCloudStorageProviders(unittest.TestCase):
    """Test suite for Cloud Storage Provider abstraction and offline sandbox."""

    def setUp(self):
        self.mock_provider = MockCloudProvider()

    # -------------------------------------------------------------------------
    # 1. Interface & Abstract Base Class Contract
    # -------------------------------------------------------------------------

    def test_icloud_storage_provider_cannot_be_instantiated(self):
        """ICloudStorageProvider is an ABC and cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            ICloudStorageProvider()

    # -------------------------------------------------------------------------
    # 2. MockCloudProvider Connection & Lifecycle
    # -------------------------------------------------------------------------

    def test_mock_provider_lifecycle(self):
        """Mock provider starts connected and respects disconnect / reconnect."""
        self.assertTrue(self.mock_provider.is_connected())

        self.mock_provider.disconnect()
        self.assertFalse(self.mock_provider.is_connected())

        # Operations fail when disconnected
        with self.assertRaises(ConnectionError):
            self.mock_provider.list_directory()

        self.mock_provider.connect("test_token")
        self.assertTrue(self.mock_provider.is_connected())
        files = self.mock_provider.list_directory()
        self.assertGreater(len(files), 0)

    # -------------------------------------------------------------------------
    # 3. School Drive Hierarchy Enumeration
    # -------------------------------------------------------------------------

    def test_root_directory_enumeration(self):
        """Root directory contains expected school project files and subfolders."""
        root_items = self.mock_provider.list_directory(folder_id="root", recursive=False)
        names = {item.name: item for item in root_items}

        self.assertIn("Science_Fair_Video_Final_Render_4K.mp4", names)
        self.assertIn("History_Presentation_Backup_2023.zip", names)
        self.assertIn("Math_Homework_Scan_Unused.pdf", names)
        self.assertIn("Scratch_Project_Assets_Duplicate.tar", names)
        self.assertIn("Class_Zoom_Recording_2023_09_14.mp4", names)
        self.assertIn("Archives_2023", names)

        folder_item = names["Archives_2023"]
        self.assertTrue(folder_item.is_folder)

    def test_recursive_directory_enumeration(self):
        """Recursive listing returns nested items inside subfolders."""
        all_items = self.mock_provider.list_directory(recursive=True)
        names = [item.name for item in all_items]

        # Old_Robotics_Code_v1.tar.gz is inside Archives_2023
        self.assertIn("Old_Robotics_Code_v1.tar.gz", names)

    def test_get_file_metadata(self):
        """Fetching specific metadata by file ID returns accurate item struct."""
        item = self.mock_provider.get_file_metadata("gdrive_001")
        self.assertEqual(item.id, "gdrive_001")
        self.assertEqual(item.name, "Science_Fair_Video_Final_Render_4K.mp4")
        self.assertEqual(item.size_bytes, 2847582208)
        self.assertEqual(item.mime_type, "video/mp4")
        self.assertFalse(item.is_trashed)
        self.assertFalse(item.is_folder)

        with self.assertRaises(KeyError):
            self.mock_provider.get_file_metadata("invalid_id_999")

    # -------------------------------------------------------------------------
    # 4. Quota Calculation & Dark Data Candidate Tracking
    # -------------------------------------------------------------------------

    def test_quota_metrics(self):
        """Quota metrics report total, used, trash, and free bytes correctly."""
        quota = self.mock_provider.get_quota()

        self.assertEqual(quota.total_bytes, DEFAULT_TOTAL_QUOTA_BYTES)
        self.assertGreater(quota.used_bytes, 0)
        self.assertEqual(quota.trash_bytes, DEFAULT_INITIAL_TRASH_BYTES)
        self.assertEqual(
            quota.free_bytes,
            quota.total_bytes - quota.used_bytes - quota.trash_bytes,
        )
        self.assertGreater(quota.dark_data_candidate_bytes, 0)

        # Dictionary serialization
        q_dict = quota.to_dict()
        self.assertIn("free_bytes", q_dict)
        self.assertEqual(q_dict["free_bytes"], quota.free_bytes)

    # -------------------------------------------------------------------------
    # 5. Safe Non-Destructive Trash Simulation & Quota Recalculation
    # -------------------------------------------------------------------------

    def test_stage_deletion_safe_trash_workflow(self):
        """Staging deletion moves file to trash, updates quota, and can be restored."""
        file_id = "gdrive_001"
        item = self.mock_provider.get_file_metadata(file_id)
        original_size = item.size_bytes

        initial_quota = self.mock_provider.get_quota()

        # 1. Stage deletion
        staged = self.mock_provider.stage_deletion(file_id)
        self.assertTrue(staged)
        self.assertTrue(item.is_trashed)

        # Staging already trashed file returns False
        self.assertFalse(self.mock_provider.stage_deletion(file_id))

        # File is excluded from active directory list
        active_items = self.mock_provider.list_directory("root")
        self.assertNotIn(file_id, [f.id for f in active_items])

        # File is listed in trashed items
        trashed_items = self.mock_provider.list_trashed()
        self.assertIn(file_id, [f.id for f in trashed_items])

        # Quota reflects shift from active used to trash
        new_quota = self.mock_provider.get_quota()
        self.assertEqual(new_quota.used_bytes, initial_quota.used_bytes - original_size)
        self.assertEqual(new_quota.trash_bytes, initial_quota.trash_bytes + original_size)

        # 2. Restore file
        restored = self.mock_provider.restore_file(file_id)
        self.assertTrue(restored)
        self.assertFalse(item.is_trashed)

        restored_quota = self.mock_provider.get_quota()
        self.assertEqual(restored_quota.used_bytes, initial_quota.used_bytes)
        self.assertEqual(restored_quota.trash_bytes, initial_quota.trash_bytes)

    def test_commit_deletion(self):
        """Commit deletion confirms file trash status."""
        self.mock_provider.stage_deletion("gdrive_002")
        committed = self.mock_provider.commit_deletion("gdrive_002")
        self.assertTrue(committed)
        self.assertTrue(self.mock_provider.get_file_metadata("gdrive_002").is_trashed)

    # -------------------------------------------------------------------------
    # 6. Sandbox Reset
    # -------------------------------------------------------------------------

    def test_reset_sandbox(self):
        """Calling reset_sandbox reverts all staged deletions and restored state."""
        self.mock_provider.stage_deletion("gdrive_001")
        self.mock_provider.stage_deletion("gdrive_002")
        self.assertTrue(self.mock_provider.get_file_metadata("gdrive_001").is_trashed)

        self.mock_provider.reset_sandbox()
        self.assertFalse(self.mock_provider.get_file_metadata("gdrive_001").is_trashed)
        self.assertFalse(self.mock_provider.get_file_metadata("gdrive_002").is_trashed)

    # -------------------------------------------------------------------------
    # 7. GoogleDriveProvider & Offline Fallback
    # -------------------------------------------------------------------------

    def test_google_drive_provider_offline_fallback(self):
        """GoogleDriveProvider seamlessly delegates to offline sandbox without token."""
        gdrive = GoogleDriveProvider(auth_token=None)
        self.assertFalse(gdrive.is_connected())

        gdrive.connect("OFFLINE")
        self.assertTrue(gdrive.is_connected())

        # Enumerate fallback directory
        items = gdrive.list_directory()
        self.assertGreater(len(items), 0)

        # Quota fallback
        quota = gdrive.get_quota()
        self.assertEqual(quota.total_bytes, DEFAULT_TOTAL_QUOTA_BYTES)

        # Staged deletion fallback
        staged = gdrive.stage_deletion("gdrive_003")
        self.assertTrue(staged)
        meta = gdrive.get_file_metadata("gdrive_003")
        self.assertTrue(meta.is_trashed)

        # Restore fallback
        restored = gdrive.restore_file("gdrive_003")
        self.assertTrue(restored)
        self.assertFalse(gdrive.get_file_metadata("gdrive_003").is_trashed)


if __name__ == "__main__":
    unittest.main()
