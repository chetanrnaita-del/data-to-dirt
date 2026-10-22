# Project: Data-to-Dirt Bug Fix: Directory Scanning & Error Surfacing

## Architecture
- **Backend Service**: `src/services/scanner.py` (`FileScanner`) manages scan access scoping, directory traversal, state tracking, and heuristic flagging.
- **Analysis Engine**: `src/analyzer/engine.py` (`AnalysisEngine`) and `src/analyzer/sanitizer.py` provide security sanitization, dark data classification, and path validation.
- **HTTP Server**: `src/app/server.py` exposes REST endpoints (`POST /api/scan/request`, `/api/scan/revoke`, `/api/state`) and coordinates scanner state.
- **Frontend UI**: `src/ui/js/views/student.js` issues scan requests, handles UI states (success, error, progress), renders file list, and triggers audio chimes.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---|---|---|---|
| 1 | Directory Readability Validation | Test directory readability with `os.scandir()` in `FileScanner.request_access` before scoping | M1 | Survey (Obs 1.3) |
| 2 | Traversal Error Detection | Catch root and child permission errors in `os.walk` via `onerror` handler in `FileScanner.scan` | M1 | Survey (Obs 1.2) |
| 3 | TCC & Path Handling | Expand `~` paths and handle macOS TCC EPERM with clear guidance/fallbacks | M1 | Survey (Obs 1.5, R1) |
| 4 | API Error Surfacing | Return HTTP 400 with `status: "error"` and informative error string when scan fails in `server.py` | M1 | Survey (Obs 1.1, R2) |
| 5 | UI Error Banner & Feedback | Check response status in `student.js`, display red error banner with error message, error card, and audio buzzer | M1 | Survey (Obs 1.4, R2) |
| 6 | Regression & Error Test Suite | Preserve 503 passing tests in `make test` and add tests for invalid/restricted folder error surfacing | M1 | Survey (Obs 1.7, AC2, AC3) |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| 1 | Directory Scanning & Error Surfacing Fix | Fix `scanner.py`, `engine.py`, `sanitizer.py`, `server.py`, `student.js`, and add tests in `test_scanner.py` and `test_ui_and_build.py` | none | DONE |

## Code Layout
- `src/services/scanner.py`: Owned by Worker for scanning logic and error propagation
- `src/analyzer/engine.py` & `src/analyzer/sanitizer.py`: Owned by Worker for directory validation
- `src/app/server.py`: Owned by Worker for API endpoint error response
- `src/ui/js/views/student.js`: Owned by Worker for UI error rendering
- `tests/test_scanner.py` & `tests/test_ui_and_build.py`: Owned by Worker for verification test cases

## Interface Contracts
### `POST /api/scan/request`
- **Request**: `{"folder_path": "<string>", "session_only": <bool>}`
- **Success Response (HTTP 200)**:
  ```json
  {
    "status": "completed",
    "folder": "<resolved_path>",
    "files_found": <int>,
    "files": [...],
    "session_only": <bool>
  }
  ```
- **Error Response (HTTP 400)**:
  ```json
  {
    "status": "error",
    "error": "<descriptive_error_message>",
    "folder": "<target_path>",
    "files_found": 0,
    "files": []
  }
  ```
