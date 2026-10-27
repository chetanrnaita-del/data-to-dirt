"""Unit tests verifying that Google Drive scans strictly exclude shared files.

Files shared with students and teachers take 0 storage quota on their account,
so cleaning them up does not reclaim personal storage and risks altering documents
owned by someone else.
"""

import json
import os
import unittest
from unittest.mock import patch, MagicMock

# Ensure test mode environment
os.environ["TEST_MODE"] = "1"

from src.app.server import app


class TestDriveSharedFilesExclusion(unittest.TestCase):
    """Test suite validating that shared files are never ingested into dark data lists."""

    def setUp(self):
        self.client = app.test_client()

    def test_picker_files_shared_with_me_flag_excluded(self):
        """Files flagged with sharedWithMe=True or is_shared_with_me=True are excluded."""
        payload = {
            "scan_type": "picker_files",
            "session_only": True,
            "files": [
                {
                    "id": "owned_file_01",
                    "name": "My_Personal_Research_Project.docx",
                    "sizeBytes": 1024 * 1024,
                    "mimeType": "application/vnd.google-apps.document",
                    "sharedWithMe": False,
                    "owners": [{"me": True, "displayName": "Student Me"}]
                },
                {
                    "id": "shared_file_01",
                    "name": "Teacher_Syllabus_Fall2026.pdf",
                    "sizeBytes": 5 * 1024 * 1024,
                    "mimeType": "application/pdf",
                    "sharedWithMe": True,
                    "owners": [{"me": False, "displayName": "Mr. Smith"}]
                },
                {
                    "id": "shared_file_02",
                    "name": "Classmate_Group_Draft.gdoc",
                    "sizeBytes": 2 * 1024 * 1024,
                    "mimeType": "application/vnd.google-apps.document",
                    "is_shared_with_me": True
                }
            ]
        }

        res = self.client.post("/api/scan/request", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["files_found"], 1)
        self.assertEqual(data["excluded_shared_files"], 2)
        self.assertIn("Excluded 2 shared file(s)", data.get("note", ""))
        self.assertEqual(data["files"][0]["file_id"], "owned_file_01")
        self.assertEqual(data["files"][0]["file_name"], "My_Personal_Research_Project.docx")

    def test_picker_files_owners_me_false_excluded(self):
        """Files where owners list has no me=True are excluded."""
        payload = {
            "scan_type": "picker_files",
            "session_only": True,
            "files": [
                {
                    "id": "owned_file_02",
                    "name": "Chemistry_Lab_Notes.docx",
                    "sizeBytes": 512 * 1024,
                    "mimeType": "application/vnd.google-apps.document",
                    "owners": [{"me": True}]
                },
                {
                    "id": "external_file_01",
                    "name": "Department_Meeting_Deck.pptx",
                    "sizeBytes": 15 * 1024 * 1024,
                    "mimeType": "application/vnd.google-apps.presentation",
                    "owners": [{"me": False, "emailAddress": "dean@school.edu"}]
                }
            ]
        }

        res = self.client.post("/api/scan/request", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertEqual(data["files_found"], 1)
        self.assertEqual(data["excluded_shared_files"], 1)
        self.assertEqual(data["files"][0]["file_id"], "owned_file_02")

    def test_picker_files_is_owner_false_excluded(self):
        """Files with isOwner=False from Google Picker are excluded."""
        payload = {
            "scan_type": "picker_files",
            "session_only": True,
            "files": [
                {
                    "id": "owned_03",
                    "name": "Personal_Homework.pdf",
                    "sizeBytes": 200000,
                    "isOwner": True
                },
                {
                    "id": "shared_03",
                    "name": "Peer_Review_Sheet.pdf",
                    "sizeBytes": 400000,
                    "isOwner": False
                }
            ]
        }

        res = self.client.post("/api/scan/request", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertEqual(data["files_found"], 1)
        self.assertEqual(data["excluded_shared_files"], 1)
        self.assertEqual(data["files"][0]["file_id"], "owned_03")

    def test_all_picker_files_shared_returns_zero_candidates(self):
        """When all selected files in Google Drive are shared, zero candidates are queued."""
        payload = {
            "scan_type": "picker_files",
            "session_only": True,
            "files": [
                {
                    "id": "shared_only_01",
                    "name": "Shared_Lesson_Plan.pdf",
                    "sizeBytes": 10000000,
                    "sharedWithMe": True
                },
                {
                    "id": "shared_only_02",
                    "name": "Shared_Grading_Rubric.xlsx",
                    "sizeBytes": 5000000,
                    "owners": [{"me": False}]
                }
            ]
        }

        res = self.client.post("/api/scan/request", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertEqual(data["files_found"], 0)
        self.assertEqual(data["excluded_shared_files"], 2)
        self.assertEqual(data["files"], [])
        self.assertIn("Excluded 2 shared file(s)", data.get("note", ""))

    @patch("urllib.request.urlopen")
    def test_direct_drive_scan_excludes_shared_files(self, mock_urlopen):
        """Direct Drive API scan filters out files where sharedWithMe is true or me is not in owners."""
        fake_drive_response = {
            "files": [
                {
                    "id": "drive_owned_01",
                    "name": "My_Old_Project_Archive.zip",
                    "size": "35000000",
                    "quotaBytesUsed": "35000000",
                    "mimeType": "application/zip",
                    "modifiedTime": "2024-01-01T00:00:00.000Z",
                    "sharedWithMe": False,
                    "owners": [{"me": True, "displayName": "Me"}]
                },
                {
                    "id": "drive_shared_01",
                    "name": "School_Wide_Announcements.mp4",
                    "size": "150000000",
                    "quotaBytesUsed": "0",  # Shared files use 0 quota on recipient drive!
                    "mimeType": "video/mp4",
                    "modifiedTime": "2024-01-01T00:00:00.000Z",
                    "sharedWithMe": True,
                    "owners": [{"me": False, "displayName": "Principal"}]
                }
            ]
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(fake_drive_response).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        payload = {
            "scan_type": "drive",
            "oauth_token": "ya29.test_valid_oauth_token",
            "session_only": True
        }

        res = self.client.post("/api/scan/request", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["files_found"], 1)
        self.assertEqual(data["excluded_shared_files"], 1)
        self.assertEqual(data["files"][0]["file_id"], "drive_owned_01")
        self.assertEqual(data["files"][0]["file_name"], "My_Old_Project_Archive.zip")


if __name__ == "__main__":
    unittest.main()
