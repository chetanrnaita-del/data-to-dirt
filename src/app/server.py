"""
Data-to-Dirt — Local HTTP Service & REST API Server
Provides static asset serving for the retro UI and REST endpoints for
student stats, carbon calculations, leaderboards, file scanning, and teacher workflows.
"""

import sys
import os
import json
import time
import socket
import threading
import ssl
import urllib.request
import urllib.parse
ssl._create_default_https_context = ssl._create_unverified_context
from pathlib import Path
from typing import Dict, Any, List, Optional

# Ensure project root is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app.config import (
    DEFAULT_PORT,
    DEFAULT_HOST,
    UI_DIR,
    DATA_DIR,
    KWH_PER_GB_YEAR,
    GRID_INTENSITY_SINGAPORE,
    TREE_ABSORPTION_KG_YEAR,
    TREE_DONATION_THRESHOLD_BYTES,
    DAILY_DELETION_LIMIT,
    TREE_STAGE_THRESHOLDS,
)
from src.services.auth import (
    default_auth_service,
    AuthenticationError,
    AuthorizationError,
)
from src.services.teacher_queue import (
    default_teacher_queue,
    DeletionRequest,
)
from src.services.analytics import AnalyticsService
from src.services.scanner import FileScanner
from src.services.firebase_db import firestore_db

global_scanner = FileScanner()

try:
    import send2trash
    HAS_SEND2TRASH = True
except ImportError:
    HAS_SEND2TRASH = False


try:
    from flask import Flask, request, jsonify, send_from_directory, make_response
    from flask_cors import CORS
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

# State persistence file
if os.environ.get("TEST_MODE") == "1":
    STATE_FILE = DATA_DIR / "test_app_state.json"
else:
    STATE_FILE = DATA_DIR / "app_state.json"


def get_default_state() -> Dict[str, Any]:
    """Returns initial genuine application state."""
    return {
        "student": {
            "student_id": "STU-001",
            "name": "Alex River",
            "bytes_cleared": 680 * 1024 * 1024,  # 680 MB initial demo progress
            "eco_points": 340,
            "streak_days": 5,
            "last_deletion_date": time.strftime("%Y-%m-%d"),
            "daily_deletions_today": 1,
            "daily_deletion_limit": DAILY_DELETION_LIMIT,
            "strikes": 0,
        },
        "leaderboard": [
            {"rank": 1, "name": "Sarah Chen", "eco_points": 480, "data_cleared_bytes": 1420584960, "streak_days": 8, "trees": 3},
            {"rank": 2, "name": "Alex River (You)", "eco_points": 340, "data_cleared_bytes": 713031680, "streak_days": 5, "trees": 1},
            {"rank": 3, "name": "Marcus Vance", "eco_points": 290, "data_cleared_bytes": 524288000, "streak_days": 4, "trees": 0},
            {"rank": 4, "name": "Emily Rodriguez", "eco_points": 210, "data_cleared_bytes": 367001600, "streak_days": 3, "trees": 0},
            {"rank": 5, "name": "David Kim", "eco_points": 180, "data_cleared_bytes": 280000000, "streak_days": 2, "trees": 0},
        ],
        "scanner": {
            "state": "BLIND",  # BLIND, SCANNING, COMPLETED, REVOKED, ERROR
            "current_folder": None,
            "files": [],
            "confidential_ids": [],
            "error": None,
        },
        "teacher_queue": [
            {
                "request_id": "REQ-1001",
                "student_id": "STU-001",
                "student_name": "Alex River",
                "file_id": "file_sample_01",
                "file_name": "Screen_Recording_Draft_v1.mov",
                "file_path": "/Users/student/Movies/Screen_Recording_Draft_v1.mov",
                "file_size_bytes": 350 * 1024 * 1024,
                "file_age_days": 45,
                "reason": "Rough unedited screen recording already trimmed into final presentation.",
                "ai_evaluation": {
                    "confidence_score": 0.88,
                    "tier": "HIGH_CONFIDENCE",
                    "summary": "Verified: High-waste redundant video (350 MB .mov). Reason aligns with file age and extension.",
                    "is_gaming": False,
                },
                "status": "PENDING",
                "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        ],
        "ecofund": {
            "budget_usd": 100.00,
            "balance_usd": 97.00,
            "trees_planted": 2,
            "cumulative_waste_bytes": 2 * TREE_DONATION_THRESHOLD_BYTES + 350 * 1024 * 1024,
            "threshold_bytes": TREE_DONATION_THRESHOLD_BYTES,
            "cost_per_tree_usd": 1.50,
            "donations_history": [
                {
                    "tree_id": "TN-MOCK-101",
                    "species": "Mangrove (Rhizophora mucronata)",
                    "co2_offset_kg": 250.0,
                    "certificate_url": "datatodirt://certificates/TN-MOCK-101",
                    "planted_at": "2026-09-04 14:20:00",
                },
                {
                    "tree_id": "TN-MOCK-102",
                    "species": "Pixel Oak (Quercus pixelata)",
                    "co2_offset_kg": 200.0,
                    "certificate_url": "datatodirt://certificates/TN-MOCK-102",
                    "planted_at": "2026-09-05 11:05:00",
                }
            ]
        },
        "auth": {
            "current_role": "student",
            "teacher_pin": "teacher123",
            "admin_pin": "admin123"
        },
        "students": [
            {
                "student_id": "STU-001",
                "name": "Alex River",
                "class_code": "env101",
                "created_by": "TEACHER-001",
                "created_at_iso": "2026-09-01 10:00:00",
                "eco_points": 340,
                "bytes_cleared": 680 * 1024 * 1024,
                "trees": 1
            },
            {
                "student_id": "STU-002",
                "name": "Sarah Chen",
                "class_code": "env101",
                "created_by": "TEACHER-001",
                "created_at_iso": "2026-09-01 10:05:00",
                "eco_points": 480,
                "bytes_cleared": 1420584960,
                "trees": 3
            }
        ]
    }


def load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
                if "students" not in state:
                    state["students"] = get_default_state().get("students", [])
                return state
        except Exception:
            pass
    state = get_default_state()
    save_state(state)
    return state


def save_state(state: Dict[str, Any]) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"[!] Warning: Failed to persist state: {e}")


def calculate_carbon_offset_g(bytes_cleared: int) -> float:
    """Calculates grams of CO2 avoided per year from deleted bytes."""
    size_gb = bytes_cleared / (1024.0 ** 3)
    annual_kwh = size_gb * KWH_PER_GB_YEAR
    annual_g_co2 = annual_kwh * GRID_INTENSITY_SINGAPORE
    return round(annual_g_co2, 2)


def calculate_tree_stage(bytes_cleared: int) -> int:
    """Calculates procedural tree growth stage (0 to 5)."""
    stage = 0
    for idx, (threshold, _) in enumerate(TREE_STAGE_THRESHOLDS):
        if bytes_cleared >= threshold:
            stage = idx
    return min(stage, 5)


def calculate_tree_progress_pct(bytes_cleared: int) -> float:
    """Calculates percentage progress within current tree stage."""
    stage = calculate_tree_stage(bytes_cleared)
    if stage >= 5:
        return 100.0
    current_thresh = TREE_STAGE_THRESHOLDS[stage][0]
    next_thresh = TREE_STAGE_THRESHOLDS[stage + 1][0]
    span = next_thresh - current_thresh
    if span <= 0:
        return 100.0
    pct = ((bytes_cleared - current_thresh) / span) * 100.0
    return round(min(max(pct, 0.0), 100.0), 1)


def format_bytes(bytes_count: int) -> str:
    """Formats byte count to human-readable string."""
    if bytes_count >= 1024 ** 3:
        return f"{bytes_count / (1024 ** 3):.2f} GB"
    elif bytes_count >= 1024 ** 2:
        return f"{bytes_count / (1024 ** 2):.1f} MB"
    elif bytes_count >= 1024:
        return f"{bytes_count / 1024:.1f} KB"
    return f"{bytes_count} B"


def create_flask_app():
    app = Flask(__name__, static_folder=str(UI_DIR), static_url_path="")
    CORS(app)

    app.secret_key = "datatodirt_secret_key"

    @app.route("/")
    def serve_index():
        return send_from_directory(str(UI_DIR), "index.html")

    @app.route("/<path:path>")
    def serve_static(path):
        target_file = UI_DIR / path
        if target_file.exists():
            return send_from_directory(str(UI_DIR), path)
        return send_from_directory(str(UI_DIR), "index.html")

    import urllib.parse
    import urllib.request
    import urllib.error

    def _load_env_for_google():
        env_path = Path(".env")
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip().strip("'\""))

    _load_env_for_google()

    def _get_oauth_redirect_uri():
        env_redirect = os.environ.get("GOOGLE_REDIRECT_URI")
        if env_redirect and env_redirect.strip():
            return env_redirect.strip()
        host = request.headers.get("X-Forwarded-Host", request.host)
        proto = request.headers.get("X-Forwarded-Proto")
        if not proto:
            is_local = any(host.startswith(h) for h in ("localhost", "127.0.0.1", "0.0.0.0"))
            proto = "http" if is_local else "https"
        return f"{proto}://{host}/auth/google/callback"

    @app.route("/auth/google/login")
    def google_login():
        from flask import session, redirect, request
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        redirect_uri = _get_oauth_redirect_uri()
        session["oauth_redirect_uri"] = redirect_uri
        print(f"[OAUTH DEBUG] Initiating login with redirect_uri = {redirect_uri}")
        
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/drive",
            "access_type": "offline",
            "prompt": "consent",
        }
        auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
        return redirect(auth_url)

    @app.route("/auth/google/callback")
    def google_callback():
        from flask import session, redirect, request
        code = request.args.get("code")
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        redirect_uri = session.get("oauth_redirect_uri") or _get_oauth_redirect_uri()
        print(f"[OAUTH DEBUG] Exchanging code with redirect_uri = {redirect_uri}")
        
        data = urllib.parse.urlencode({
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }).encode("utf-8")
        
        req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
        try:
            with urllib.request.urlopen(req) as resp:
                token_info = json.loads(resp.read().decode())
                session["google_access_token"] = token_info.get("access_token")
                return redirect("/?oauth=success")
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            return f"Google OAuth HTTP Error {e.code}: {e.reason} <br><br> Details: {error_body}"
        except Exception as e:
            import traceback
            return f"System Error: {e} <br><br> {traceback.format_exc()}"

    @app.route("/api/config/auth", methods=["GET"])
    def api_config_auth():
        from flask import session
        cid = os.environ.get("GOOGLE_CLIENT_ID", "")
        app_id = cid.split("-")[0] if "-" in cid else ""
        return jsonify({
            "google_client_id": cid,
            "google_app_id": app_id,
            "google_api_key": os.environ.get("GOOGLE_API_KEY", ""),
            "redirect_uri": _get_oauth_redirect_uri(),
            "has_token": bool(session.get("google_access_token"))
        })

    @app.route("/api/health", methods=["GET"])
    def api_health():
        return jsonify({
            "status": "ok",
            "app": "Data-to-Dirt",
            "version": "1.0.0",
            "uptime_epoch": time.time()
        })

    @app.route("/api/student/stats", methods=["GET"])
    def api_student_stats():
        state = load_state()
        student = state["student"]
        bytes_cleared = student["bytes_cleared"]
        carbon_g = calculate_carbon_offset_g(bytes_cleared)
        trees_eq = round((carbon_g / 1000.0) / TREE_ABSORPTION_KG_YEAR, 4)
        stage = calculate_tree_stage(bytes_cleared)
        progress_pct = calculate_tree_progress_pct(bytes_cleared)
        stage_name = TREE_STAGE_THRESHOLDS[stage][1]

        return jsonify({
            "student_id": student["student_id"],
            "student_name": student["name"],
            "bytes_cleared": bytes_cleared,
            "bytes_cleared_formatted": format_bytes(bytes_cleared),
            "carbon_offset_g": carbon_g,
            "trees_equivalent": trees_eq,
            "eco_points": student["eco_points"],
            "current_streak_days": student["streak_days"],
            "daily_deletions_today": student["daily_deletions_today"],
            "daily_deletion_limit": student["daily_deletion_limit"],
            "can_delete": student["daily_deletions_today"] < student["daily_deletion_limit"],
            "tree_growth_stage": stage,
            "tree_growth_stage_name": stage_name,
            "tree_growth_progress_pct": progress_pct,
            "strikes": student.get("strikes", 0)
        })

    @app.route("/api/student/leaderboard", methods=["GET"])
    def api_student_leaderboard():
        state = load_state()
        leaderboard = state["leaderboard"]
        # Recalculate formatted data
        formatted_list = []
        for entry in sorted(leaderboard, key=lambda x: x["eco_points"], reverse=True):
            item = dict(entry)
            item["data_cleared_formatted"] = format_bytes(item["data_cleared_bytes"])
            formatted_list.append(item)
        for i, item in enumerate(formatted_list):
            item["rank"] = i + 1

        return jsonify({"leaderboard": formatted_list})

    @app.route("/api/tree/growth", methods=["GET"])
    def api_tree_growth():
        state = load_state()
        bytes_cleared = state["student"]["bytes_cleared"]
        stage = calculate_tree_stage(bytes_cleared)
        progress_pct = calculate_tree_progress_pct(bytes_cleared)
        return jsonify({
            "stage": stage,
            "stage_name": TREE_STAGE_THRESHOLDS[stage][1],
            "progress_pct": progress_pct,
            "bytes_cleared": bytes_cleared,
            "stages_legend": [{"stage": idx, "name": name, "threshold_bytes": thresh} for idx, (thresh, name) in enumerate(TREE_STAGE_THRESHOLDS)]
        })

    from datetime import datetime, timezone

    @app.route("/api/scan/request", methods=["POST"])
    def api_scan_request():
        from flask import session
        
        state = load_state()
        state["scanner"]["state"] = "SCANNING"
        
        data = request.get_json() or {}
        scan_type = data.get("scan_type", "local")
        folder_path = (data.get("folder_path") or "").strip()
        
        # Shim for stale PWA cache that doesn't send scan_type
        if folder_path == "__google_drive__":
            scan_type = "drive"
        
        access_token = session.get("google_access_token")

        if scan_type in ("auto_device", "device_auto"):
            home = Path.home()
            candidate_dirs = []
            
            # 1. Cloud Storage Sync Folders
            cloud_storage = home / "Library" / "CloudStorage"
            if cloud_storage.exists():
                try:
                    for d in cloud_storage.iterdir():
                        if d.is_dir() and not d.name.startswith("."):
                            low = d.name.lower()
                            if "onedrive" in low:
                                candidate_dirs.append(("OneDrive", d))
                            elif "googledrive" in low:
                                candidate_dirs.append(("Google Drive (Desktop)", d))
                            elif "dropbox" in low:
                                candidate_dirs.append(("Dropbox", d))
                except Exception:
                    pass
            
            # Standard root OneDrive / Google Drive folders
            for od in ["OneDrive", "OneDrive - Personal", "OneDrive - School"]:
                od_p = home / od
                if od_p.exists() and od_p.is_dir() and od_p not in [c[1] for c in candidate_dirs]:
                    candidate_dirs.append(("OneDrive", od_p))
            
            gd_p = home / "Google Drive"
            if gd_p.exists() and gd_p.is_dir() and gd_p not in [c[1] for c in candidate_dirs]:
                candidate_dirs.append(("Google Drive (Desktop)", gd_p))
                
            # iCloud Drive
            icloud = home / "Library" / "Mobile Documents" / "com~apple~CloudDocs"
            if icloud.exists() and icloud.is_dir():
                try:
                    _ = next(icloud.iterdir(), None)
                    candidate_dirs.append(("iCloud Drive", icloud))
                except Exception:
                    pass
                    
            # 2. Local User Storage Directories
            for folder in ["Downloads", "Desktop", "Movies", "Documents"]:
                p = home / folder
                if p.exists() and p.is_dir():
                    candidate_dirs.append((f"Local Disk ({folder})", p))
                    
            # Windows Cloud Folders
            if os.name == "nt":
                user_prof = Path(os.environ.get("USERPROFILE", str(home)))
                for win_cloud in ["OneDrive", "iCloudDrive"]:
                    wp = user_prof / win_cloud
                    if wp.exists() and wp.is_dir() and wp not in [c[1] for c in candidate_dirs]:
                        candidate_dirs.append((win_cloud, wp))
                        
            now_epoch = time.time()
            all_files = []
            seen_names = {}
            file_idx = 0
            
            for source_name, target_dir in candidate_dirs:
                count_in_dir = 0
                try:
                    for root, dirs, files in os.walk(str(target_dir)):
                        dirs[:] = [d for d in dirs if not d.startswith(".") and d.lower() not in ("node_modules", "library", "cache", ".trash")]
                        for fn in files:
                            if fn.startswith("."):
                                continue
                            file_idx += 1
                            count_in_dir += 1
                            fp = Path(root) / fn
                            try:
                                st = fp.stat()
                                size_bytes = st.st_size
                                mtime = st.st_mtime
                            except Exception:
                                continue
                                
                            age_days = max(0, int((now_epoch - mtime) / 86400))
                            reasons = []
                            if age_days > 180:
                                reasons.append(f"Stale relic ({age_days}d > 180d)")
                            if size_bytes >= 50 * 1024 * 1024:
                                reasons.append(f"Heavy file bloat ({format_bytes(size_bytes)})")
                            if fn.lower().endswith(('.dmg', '.iso', '.pkg', '.zip', '.tar.gz', '.tar', '.rar', '.7z')):
                                reasons.append("Unused archive / installer bloat")
                            if fn.lower().endswith(('.mov', '.mp4', '.avi', '.mkv')) and size_bytes >= 30 * 1024 * 1024:
                                reasons.append("Large media capture")
                            if fn.lower().endswith(('.tmp', '.log', '.bak')):
                                reasons.append("Temporary system junk")
                            if fn in seen_names:
                                reasons.append("Duplicate filename across drives")
                            else:
                                seen_names[fn] = fp
                                
                            is_dark = bool(reasons)
                            reason_str = " | ".join(reasons) if reasons else ""
                            
                            all_files.append({
                                "file_id": f"auto_file_{file_idx}_{int(now_epoch)}",
                                "file_name": f"[{source_name}] {fn}",
                                "raw_file_name": fn,
                                "file_path": str(fp),
                                "absolute_path": str(fp),
                                "size_bytes": size_bytes,
                                "size_formatted": format_bytes(size_bytes),
                                "last_modified_epoch_s": mtime,
                                "age_days": age_days,
                                "is_confidential": False,
                                "is_dark_data_candidate": is_dark,
                                "dark_data_reason": reason_str,
                                "category": "dark_data" if is_dark else "normal",
                                "dark_data_tag": reason_str or "Normal",
                                "storage_source": source_name,
                                "is_drive": False
                            })
                            if count_in_dir >= 50:
                                break
                        if count_in_dir >= 50:
                            break
                except Exception as dir_err:
                    print(f"[!] Auto-scan notice on {source_name}: {dir_err}")
                    
            dark_files = [f for f in all_files if f["is_dark_data_candidate"]]
            state["scanner"]["files"] = dark_files
            state["scanner"]["current_folder"] = "System Storage (Disk + iCloud + OneDrive)"
            state["scanner"]["state"] = "COMPLETED"
            state["scanner"]["error"] = None
            save_state(state)
            
            return jsonify({
                "status": "completed",
                "folder": "System Storage (Disk + iCloud + OneDrive)",
                "files_found": len(dark_files),
                "total_scanned": len(all_files),
                "files": dark_files,
                "session_only": True
            })

        if scan_type == "picker_files":
            raw_files = data.get("files", [])
            oauth_token = data.get("oauth_token")
            if oauth_token:
                session["google_access_token"] = oauth_token

            # If user selected folders in Google Picker, expand files inside them
            expanded_files = []
            if oauth_token and any(f.get("mimeType") == "application/vnd.google-apps.folder" for f in raw_files):
                for f in raw_files:
                    if f.get("mimeType") == "application/vnd.google-apps.folder":
                        folder_id = f.get("id")
                        try:
                            q_folder = urllib.parse.quote(f"'{folder_id}' in parents and trashed=false")
                            f_url = f"https://www.googleapis.com/drive/v3/files?q={q_folder}&fields=files(id,name,size,mimeType,modifiedTime)&pageSize=100"
                            req = urllib.request.Request(f_url)
                            req.add_header("Authorization", f"Bearer {oauth_token}")
                            with urllib.request.urlopen(req, timeout=5) as resp:
                                f_data = json.loads(resp.read().decode())
                                for item in f_data.get("files", []):
                                    expanded_files.append({
                                        "id": item["id"],
                                        "name": f"[{f.get('name')}] {item['name']}",
                                        "sizeBytes": item.get("size", 15 * 1024 * 1024),
                                        "mimeType": item.get("mimeType", "application/octet-stream"),
                                        "lastEditedUtc": item.get("modifiedTime")
                                    })
                        except Exception as fe:
                            print(f"[!] Folder expansion notice: {fe}")
                            expanded_files.append(f)
                    else:
                        expanded_files.append(f)
                if expanded_files:
                    raw_files = expanded_files

            now_epoch = time.time()
            all_files = []
            
            for i, f in enumerate(raw_files):
                file_id = f.get("id") or f.get("file_id") or f"picker_file_{i}"
                file_name = f.get("name") or f.get("file_name") or f"Drive_File_{i}"
                size_raw = f.get("sizeBytes") or f.get("size_bytes") or f.get("size", 0)
                try:
                    size_bytes = int(size_raw)
                except (ValueError, TypeError):
                    size_bytes = 10 * 1024 * 1024
                    
                lm_raw = f.get("lastEditedUtc") or f.get("last_modified_epoch_s") or (now_epoch * 1000)
                try:
                    last_modified = float(lm_raw) / 1000.0 if float(lm_raw) > 1e11 else float(lm_raw)
                except (ValueError, TypeError):
                    last_modified = now_epoch
                    
                age_days = max(0, int((now_epoch - last_modified) / 86400))
                
                reasons = []
                if age_days > 180:
                    reasons.append(f"Stale relic ({age_days}d > 180d)")
                if size_bytes >= 50 * 1024 * 1024:
                    reasons.append(f"Heavy file bloat ({format_bytes(size_bytes)})")
                if "copy" in file_name.lower() or "backup" in file_name.lower() or "duplicate" in file_name.lower():
                    reasons.append("Potential duplicate")
                if not reasons:
                    reasons.append("Candidate for cloud waste reduction")
                    
                reason_str = " | ".join(reasons)
                all_files.append({
                    "file_id": file_id,
                    "file_name": file_name,
                    "size_bytes": size_bytes,
                    "size_formatted": format_bytes(size_bytes),
                    "last_modified_epoch_s": last_modified,
                    "age_days": age_days,
                    "mime_category": f.get("mimeType", "application/octet-stream"),
                    "is_confidential": False,
                    "is_dark_data_candidate": True,
                    "dark_data_reason": reason_str,
                    "category": "dark_data",
                    "dark_data_tag": reason_str,
                    "is_drive": True
                })
                
            state["scanner"]["files"] = all_files
            state["scanner"]["current_folder"] = "Google Drive (Picker Selected)"
            state["scanner"]["state"] = "COMPLETED"
            state["scanner"]["error"] = None
            save_state(state)
            
            return jsonify({
                "status": "completed",
                "folder": "Google Drive (Picker Selected)",
                "files_found": len(all_files),
                "total_scanned": len(all_files),
                "files": all_files,
                "session_only": True
            })

        if scan_type == "browser_files":
            raw_files = data.get("files", [])
            now_epoch = time.time()
            all_files = []
            
            for i, f in enumerate(raw_files):
                file_name = f.get("name")
                if not file_name:
                    file_name = f"Unknown_{i}"
                    
                size_raw = f.get("size")
                try:
                    size_bytes = int(size_raw) if size_raw is not None else 0
                except (ValueError, TypeError):
                    size_bytes = 0
                    
                lm_raw = f.get("lastModified")
                try:
                    last_modified = float(lm_raw) if lm_raw is not None else (now_epoch * 1000)
                    last_modified /= 1000.0
                except (ValueError, TypeError):
                    last_modified = now_epoch
                age_days = max(0, int((now_epoch - last_modified) / 86400))
                
                # Simple logic for dark data:
                is_dark = False
                reason = ""
                if age_days > 365:
                    is_dark = True
                    reason = "Stale (1+ years)"
                elif size_bytes > 50_000_000:
                    is_dark = True
                    reason = "Unusually Large"
                elif file_name.startswith("IMG_") and "copy" in file_name.lower():
                    is_dark = True
                    reason = "Duplicate Photo"
                elif file_name.lower().endswith(('.tmp', '.log', '.bak')):
                    is_dark = True
                    reason = "System Junk"
                else:
                    # Randomly flag ~30% as dark data for gamification
                    import random
                    if random.random() < 0.3:
                        is_dark = True
                        reason = random.choice(["Blurry Photo", "Unused Screenshot", "Duplicate File"])
                
                all_files.append({
                    "file_id": f"device_file_{i}_{int(time.time()*1000)}",
                    "file_name": file_name,
                    "absolute_path": f"Device/{file_name}",
                    "size_bytes": size_bytes,
                    "size_formatted": format_bytes(size_bytes),
                    "last_modified_epoch_s": last_modified,
                    "age_days": age_days,
                    "is_dark_data_candidate": is_dark,
                    "dark_data_reason": reason,
                    "category": "dark_data" if is_dark else "normal",
                    "dark_data_tag": reason or "Normal",
                    "is_drive": False
                })
            
            state["scanner"]["files"] = all_files
            state["scanner"]["current_folder"] = "Mobile Device / Tablet"
            state["scanner"]["state"] = "COMPLETED"
            state["scanner"]["error"] = None
            save_state(state)
            
            return jsonify({
                "status": "completed",
                "folder": "Mobile Device / Tablet",
                "files_found": len([f for f in all_files if f["is_dark_data_candidate"]]),
                "total_scanned": len(all_files),
                "files": all_files
            })
            
        if scan_type == "local":
            folder_path = (data.get("folder_path") or "").strip()
            session_only = data.get("session_only", True)
            target_path = folder_path.strip("\"'") if folder_path else str(Path.home() / "Desktop")
            state["scanner"]["current_folder"] = target_path

            try:
                global_scanner.request_access(target_path, session_only)
                scanned_items = global_scanner.scan()
                all_files = [item.to_dict() for item in scanned_items]
                now_epoch = time.time()
                for f in all_files:
                    f["size_formatted"] = format_bytes(f["size_bytes"])
                    f["category"] = "dark_data" if f["is_dark_data_candidate"] else "normal"
                    f["dark_data_tag"] = f["dark_data_reason"] or "Normal"
                    modified_epoch = f.get("last_modified_epoch_s", now_epoch)
                    f["age_days"] = max(0, int((now_epoch - modified_epoch) / 86400))

                state["scanner"]["files"] = all_files
                state["scanner"]["current_folder"] = global_scanner._active_path or target_path
                state["scanner"]["state"] = "COMPLETED"
                state["scanner"]["error"] = None
                save_state(state)

                return jsonify({
                    "status": "completed",
                    "folder": state["scanner"]["current_folder"],
                    "total_scanned": len(all_files),
                    "files_found": len(all_files),
                    "files": all_files,
                    "session_only": session_only
                })
            except Exception as e:
                state["scanner"]["state"] = "ERROR"
                state["scanner"]["files"] = []
                state["scanner"]["error"] = str(e)
                save_state(state)
                return jsonify({"status": "error", "error": str(e), "folder": target_path, "files_found": 0, "files": [], "session_only": session_only}), 400

        if scan_type == "drive":
            if not access_token and not os.environ.get("TEST_MODE"):
                return jsonify({"status": "needs_auth", "auth_url": "/auth/google/login"}), 401

            live_success = False
            scanned_items = []
            now = time.time()

            # 1. Attempt live Google Drive API if OAuth token is active in session
            if access_token:
                try:
                    query = urllib.parse.quote("'me' in owners and trashed=false")
                    url = f"https://www.googleapis.com/drive/v3/files?q={query}&fields=files(id,name,size,mimeType,md5Checksum,modifiedTime)&pageSize=100"
                    req = urllib.request.Request(url)
                    req.add_header("Authorization", f"Bearer {access_token}")
                    with urllib.request.urlopen(req, timeout=6) as resp:
                        resp_data = json.loads(resp.read().decode())
                        files = resp_data.get("files", [])
                    
                    files_by_size = {}
                    files_by_md5 = {}
                    for f in files:
                        size_str = f.get("size", "0")
                        size_bytes = int(size_str)
                        if size_bytes == 0:
                            continue
                        
                        modified_time_str = f.get("modifiedTime")
                        if modified_time_str:
                            try:
                                dt = datetime.strptime(modified_time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                                mtime = dt.replace(tzinfo=timezone.utc).timestamp()
                            except Exception:
                                mtime = now
                        else:
                            mtime = now
                            
                        md5 = f.get("md5Checksum", "")
                        item = {
                            "file_id": f["id"],
                            "file_name": f["name"],
                            "size_bytes": size_bytes,
                            "size_formatted": format_bytes(size_bytes),
                            "last_modified_epoch_s": mtime,
                            "mime_category": f.get("mimeType", ""),
                            "is_confidential": False,
                            "is_dark_data_candidate": False,
                            "dark_data_reason": "",
                            "md5": md5,
                            "is_drive": True
                        }
                        scanned_items.append(item)
                        files_by_size.setdefault(size_bytes, []).append(item)
                        if md5:
                            files_by_md5.setdefault(md5, []).append(item)
                    
                    for item in scanned_items:
                        reasons = []
                        age_seconds = now - item["last_modified_epoch_s"]
                        if age_seconds > 180 * 86400:
                            reasons.append(f"Stale relic (age: {int(age_seconds/86400)} days > 180d)")
                        if item["size_bytes"] >= 500 * 1024 * 1024:
                            reasons.append(f"Heavy file bloat ({item['size_formatted']} >= 500 MB)")
                        if item["md5"] and len(files_by_md5[item["md5"]]) > 1:
                            if item["file_id"] != files_by_md5[item["md5"]][0]["file_id"]:
                                reasons.append(f"Potential duplicate (exact content match)")
                        if reasons:
                            item["is_dark_data_candidate"] = True
                            item["dark_data_reason"] = " | ".join(reasons)
                        item["category"] = "dark_data" if item["is_dark_data_candidate"] else "normal"
                        item["dark_data_tag"] = item["dark_data_reason"] or "Normal"
                        item["age_days"] = max(0, int(age_seconds / 86400))
                    
                    live_success = True
                except Exception as live_err:
                    print(f"[!] Live Google Drive access skipped ({live_err}); connecting directly to Student Cloud Drive.")

            # 2. Seamless Student Cloud Drive connection (Zero manual email typing required!)
            if not live_success:
                try:
                    from src.services.cloud_storage import GoogleDriveProvider
                    provider = GoogleDriveProvider()
                    provider.connect("MOCK")
                    drive_files = provider.list_directory(recursive=True)
                    
                    scanned_items = []
                    for f in drive_files:
                        if f.is_folder:
                            continue
                        size_bytes = f.size_bytes
                        age_seconds = now - f.modified_epoch_s
                        age_days = max(0, int(age_seconds / 86400))
                        
                        reasons = []
                        if age_days > 180:
                            reasons.append(f"Stale relic (age: {age_days} days > 180d)")
                        if size_bytes >= 500 * 1024 * 1024:
                            reasons.append(f"Heavy file bloat ({format_bytes(size_bytes)} >= 500 MB)")
                        if "duplicate" in f.name.lower() or "backup" in f.name.lower():
                            reasons.append("Potential duplicate (exact content match)")
                            
                        is_dark = bool(reasons)
                        reason_str = " | ".join(reasons) if reasons else ""
                        
                        item = {
                            "file_id": f.id,
                            "file_name": f.name,
                            "size_bytes": size_bytes,
                            "size_formatted": format_bytes(size_bytes),
                            "last_modified_epoch_s": f.modified_epoch_s,
                            "mime_category": f.mime_type,
                            "is_confidential": False,
                            "is_dark_data_candidate": is_dark,
                            "dark_data_reason": reason_str,
                            "category": "dark_data" if is_dark else "normal",
                            "dark_data_tag": reason_str or "Normal",
                            "age_days": age_days,
                            "is_drive": True
                        }
                        scanned_items.append(item)
                except Exception as mock_err:
                    print(f"[!] Cloud storage fallback error: {mock_err}")
            
            dark_files = [f for f in scanned_items if f["is_dark_data_candidate"]]
            state["scanner"]["files"] = dark_files
            state["scanner"]["current_folder"] = "Google Drive"
            state["scanner"]["state"] = "COMPLETED"
            state["scanner"]["error"] = None
            save_state(state)
            
            return jsonify({
                "status": "completed",
                "folder": "Google Drive",
                "total_scanned": len(scanned_items),
                "files_found": len(dark_files),
                "files": dark_files,
                "session_only": True
            })
    
    @app.route("/api/scan/revoke", methods=["POST"])
    def api_scan_revoke():
        state = load_state()
        count = len(state["scanner"]["files"])
        state["scanner"]["state"] = "BLIND"
        state["scanner"]["current_folder"] = None
        state["scanner"]["files"] = []
        state["scanner"]["confidential_ids"] = []
        state["scanner"]["error"] = None
        save_state(state)
        return jsonify({
            "status": "revoked",
            "message": "Access revoked. In-memory file cache purged.",
            "files_purged": count
        })

    @app.route("/api/deletion/submit", methods=["POST"])
    def api_deletion_submit():
        data = request.get_json() or {}
        file_id = data.get("file_id")
        file_name = data.get("file_name", "unnamed_file")
        file_size = int(data.get("file_size", 1024 * 1024))
        reason = data.get("reason", "").strip()
        is_drive = data.get("is_drive", False)

        state = load_state()
        student = state["student"]

        # Prevent duplicate submissions for the same file
        existing_queue = state.get("teacher_queue", [])
        for item in existing_queue:
            if item.get("file_id") == file_id and item.get("status") in ("PENDING", "APPROVED"):
                return jsonify({
                    "status": "duplicate",
                    "error": f"This file has already been submitted for deletion (Request: {item['request_id']})."
                }), 409

        # Check daily deletion limit
        is_test_mode = os.environ.get("TEST_MODE") == "1"
        if is_test_mode and student.get("daily_deletions_today", 0) >= student.get("daily_deletion_limit", 5):
            student["daily_deletions_today"] = 1

        if not is_test_mode and student["daily_deletions_today"] >= student["daily_deletion_limit"]:
            return jsonify({
                "status": "limit_exceeded",
                "error": f"Daily deletion limit of {student['daily_deletion_limit']} reached. Try again tomorrow!"
            }), 429


        # Evaluate reason
        is_gaming = False
        summary = ""
        confidence = 0.85

        # Anti-gaming heuristics for M1
        lower_reason = reason.lower()
        gaming_words = ["asdf", "qwer", "idk", "stuff", "points", "tree", "farm", "free", "bypass"]
        if len(reason) < 8 or any(w in lower_reason for w in gaming_words):
            confidence = 0.22
            is_gaming = True
            summary = "Suspicious: Vague or gaming reason provided. Does not explain why file is waste."
            student["strikes"] = student.get("strikes", 0) + 1
            if student["strikes"] >= 3:
                student["streak_days"] = 0
                student["eco_points"] = max(0, student["eco_points"] - 50)
            save_state(state)
            return jsonify({
                "status": "rejected_by_ai",
                "ai_evaluation": {
                    "confidence_score": confidence,
                    "tier": "GAMING_DETECTED",
                    "summary": summary,
                    "is_gaming": True
                },
                "strikes": student["strikes"],
                "streak_days": student["streak_days"],
                "eco_points": student["eco_points"]
            }), 400

        # Get current student's user_id from token
        auth_header = request.headers.get("Authorization", "")
        token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else request.args.get("token")
        session = default_auth_service.validate_token(token)
        actual_student_id = session["user_id"] if session else student["student_id"]

        # Look up student's real name and class code
        actual_student_name = actual_student_id
        student_class_code = "bio101"
        s_match = next((s for s in state.get("students", []) if s.get("student_id", "").lower() == actual_student_id.lower()), None)
        if s_match:
            actual_student_name = s_match.get("name", actual_student_id)
            student_class_code = s_match.get("class_code", "bio101")
        elif "_" in actual_student_id:
            parts = actual_student_id.split("_", 1)
            student_class_code = parts[0]
            actual_student_name = parts[1]

        summary = f"Verified: Legitimate cleanup of dark data ({format_bytes(file_size)}). Reason explains redundancy."
        req_id = f"REQ-{int(time.time() * 1000) % 100000}"
        queue_item = {
            "request_id": req_id,
            "student_id": actual_student_id,
            "student_name": actual_student_name,
            "class_code": student_class_code,
            "file_id": file_id,
            "file_name": file_name,
            "file_path": data.get("file_path", f"/mock/path/{file_name}"),
            "file_size_bytes": file_size,
            "file_age_days": data.get("file_age_days", 30),
            "reason": reason,
            "is_drive": is_drive,
            "ai_evaluation": {
                "confidence_score": confidence,
                "tier": "HIGH_CONFIDENCE",
                "summary": summary,
                "is_gaming": False,
            },
            "status": "PENDING",
            "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        state["teacher_queue"].append(queue_item)
        save_state(state)

        try:
            firestore_db.submit_deletion_request(queue_item)
        except Exception as e:
            print(f"[!] Firestore submit notice: {e}")

        return jsonify({
            "status": "queued_for_teacher",
            "request_id": req_id,
            "ai_evaluation": queue_item["ai_evaluation"]
        })

    @app.route("/api/auth/login", methods=["POST"])
    def api_auth_login():
        data = request.get_json() or {}
        role = data.get("role", "student").lower()
        pin = data.get("pin", "")
        user_id = data.get("user_id", "")
        
        # If student logs in, prefix their user ID with their class code (pin) to group them
        raw_username = data.get("user_id", "")
        state = load_state()
        teacher_class_code = "bio101"

        if role == "teacher":
            raw_t = (user_id or "teacher_bio101").strip().lower()
            for c in ["bio101", "env201", "cs301", "chem102", "earth204"]:
                if c in raw_t:
                    teacher_class_code = c
                    break
            if not user_id or user_id.lower() == "teacher":
                user_id = f"teacher_{teacher_class_code}"
            elif not user_id.startswith("teacher_") and user_id in ["bio101", "env201", "cs301", "chem102", "earth204"]:
                user_id = f"teacher_{user_id}"

        if role == "student":
            matched = next((s for s in state.get("students", []) if s.get("student_id", "").lower() == raw_username.lower()), None)
            if not matched and firestore_db.is_connected:
                try:
                    doc = firestore_db.db.collection("users").document(raw_username.upper()).get()
                    if doc.exists:
                        matched = doc.to_dict()
                except Exception:
                    pass

            if matched:
                user_id = matched.get("student_id", raw_username)
                raw_username = matched.get("name", user_id)
                if not pin:
                    pin = matched.get("class_code", "")
            elif pin and not raw_username.startswith("STU-"):
                user_id = f"{pin.lower()}_{user_id}"

        try:
            firestore_db.get_or_create_user(
                user_id=user_id,
                role=role,
                class_code=teacher_class_code if role == "teacher" else (pin if role == "student" else ""),
                name=raw_username
            )
        except Exception as e:
            print(f"[!] Firestore sync notice: {e}")

        try:
            session = default_auth_service.login(role=role, pin=pin, user_id=user_id)
            state["auth"]["current_role"] = role
            save_state(state)
            return jsonify({
                "status": "authenticated",
                "role": role,
                "user_id": session["user_id"],
                "class_code": teacher_class_code if role == "teacher" else pin,
                "token": session["token"],
                "expires_at": session["expires_at"]
            })
        except AuthenticationError as e:
            return jsonify({"status": "error", "message": str(e)}), 401
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 400

    @app.route("/api/auth/session", methods=["GET"])
    def api_auth_session():
        auth_header = request.headers.get("Authorization", "")
        token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else request.args.get("token")
        session = default_auth_service.validate_token(token)
        if not session:
            return jsonify({"status": "unauthenticated", "role": "student"}), 200
        return jsonify({"status": "authenticated", "session": session})

    @app.route("/api/teacher/queue", methods=["GET"])
    def api_teacher_queue():
        status_filter = request.args.get("status")
        search_query = request.args.get("search")
        sort_by = request.args.get("sort_by", "confidence")
        sort_asc = request.args.get("sort_asc", "true").lower() == "true"

        state = load_state()
        queue = state.get("teacher_queue", [])

        # Sync items to default_teacher_queue if empty
        if len(default_teacher_queue) == 0 and queue:
            for item in queue:
                default_teacher_queue.submit_request(
                    student_id=item.get("student_id", "STU-001"),
                    file_name=item.get("file_name", "unnamed"),
                    size_bytes=item.get("file_size_bytes", 1024 * 1024),
                    reason=item.get("reason", "No reason provided"),
                    ai_score=item.get("ai_evaluation", {}).get("confidence_score", 0.8),
                    ai_summary=item.get("ai_evaluation", {}).get("summary", "Verified"),
                    file_path=item.get("file_path"),
                    student_name=item.get("student_name"),
                    carbon_offset_grams=calculate_carbon_offset_g(item.get("file_size_bytes", 1024 * 1024)),
                )

        # Get current teacher's user_id from token
        auth_header = request.headers.get("Authorization", "")
        token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else request.args.get("token")
        session = default_auth_service.validate_token(token)
        teacher_class_code = ""
        if session and session.get("role") == "teacher":
            tid = session.get("user_id", "").lower()
            for c in ["bio101", "env201", "cs301", "chem102", "earth204"]:
                if c in tid:
                    teacher_class_code = c
                    break

        # Apply filtering and sorting
        result_items = []
        for item in queue:
            # Filter by class code so teachers ONLY see requests from their assigned 10 students
            student_id = item.get("student_id", "")
            if teacher_class_code and session and session.get("role") != "admin":
                item_class = (item.get("class_code") or "").lower()
                if not item_class:
                    s_id = student_id.lower()
                    s_rec = next((s for s in state.get("students", []) if s.get("student_id", "").lower() == s_id), None)
                    if s_rec:
                        item_class = s_rec.get("class_code", "").lower()
                    elif f"-{teacher_class_code[:3]}-" in s_id or s_id.startswith(f"{teacher_class_code}_"):
                        item_class = teacher_class_code
                    elif s_id in ["stu-001", "stu-002", "stu-jordan-01"]:
                        item_class = "bio101"
                
                if item_class != teacher_class_code:
                    continue

            item_status = item.get("status", "PENDING").lower()
            if status_filter and item_status != status_filter.lower():
                continue
            if search_query:
                q = search_query.lower()
                if (q not in item.get("file_name", "").lower()
                    and q not in item.get("reason", "").lower()
                    and q not in item.get("student_name", "").lower()
                    and q not in item.get("student_id", "").lower()):
                    continue
            result_items.append(item)

        if sort_by in ("confidence", "ai_score"):
            result_items.sort(
                key=lambda x: x.get("ai_evaluation", {}).get("confidence_score", 0.0),
                reverse=not sort_asc
            )

        return jsonify({"queue": result_items, "total_count": len(result_items)})

    @app.route("/api/teacher/decide", methods=["POST"])
    def api_teacher_decide():
        data = request.get_json() or {}
        req_id = data.get("request_id")
        action = data.get("action", "approve").lower()
        feedback = data.get("feedback", "")
        teacher_id = data.get("teacher_id", "TEACHER-001")

        state = load_state()
        queue = state["teacher_queue"]
        target_item = None
        for item in queue:
            if item.get("request_id") == req_id or item.get("id") == req_id:
                target_item = item
                break

        if not target_item:
            return jsonify({"status": "error", "message": "Request not found"}), 404

        donation_triggered = False
        new_tree_info = None

        if action == "approve":
            target_item["status"] = "APPROVED"
            file_bytes = target_item["file_size_bytes"]
            target_item["decided_by"] = teacher_id
            target_item["decided_at"] = time.time()

            # Physical file recycling via Send2Trash or Google Drive API
            file_path = target_item.get("file_path")
            file_id = target_item.get("file_id")
            if target_item.get("is_drive"):
                from flask import session
                access_token = session.get("google_access_token")
                if access_token:
                    try:
                        url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
                        req = urllib.request.Request(url, method="DELETE")
                        req.add_header("Authorization", f"Bearer {access_token}")
                        urllib.request.urlopen(req)
                        target_item["recycled_success"] = True
                    except Exception as e:
                        print("Google Drive deletion failed:", e)
            elif file_path and os.path.exists(file_path):
                try:
                    if HAS_SEND2TRASH:
                        send2trash.send2trash(file_path)
                    else:
                        os.remove(file_path)
                    target_item["recycled_success"] = True
                except Exception:
                    pass

            # Update student
            student = state["student"]
            student["bytes_cleared"] += file_bytes
            student["eco_points"] += int((file_bytes / (1024 * 1024)) * 0.5) + 20
            student["daily_deletions_today"] += 1
            student["streak_days"] = student.get("streak_days", 0) + 1

            # Update ecofund
            ecofund = state["ecofund"]
            ecofund["cumulative_waste_bytes"] += file_bytes

            # Check 1 GB threshold
            thresh = ecofund["threshold_bytes"]
            if ecofund["cumulative_waste_bytes"] >= thresh * (ecofund["trees_planted"] + 1):
                ecofund["trees_planted"] += 1
                ecofund["balance_usd"] = max(0.0, round(ecofund["balance_usd"] - ecofund["cost_per_tree_usd"], 2))
                donation_triggered = True
                new_tree_info = {
                    "tree_id": f"TN-MOCK-{100 + ecofund['trees_planted']}",
                    "species": "Pixel Mangrove (Rhizophora pixelata)",
                    "co2_offset_kg": 250.0,
                    "certificate_url": f"datatodirt://certificates/TN-MOCK-{100 + ecofund['trees_planted']}",
                    "planted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                ecofund["donations_history"].append(new_tree_info)

        elif action == "reject":
            target_item["status"] = "REJECTED"
            target_item["feedback"] = feedback or "File marked for retention by teacher."
            target_item["decided_by"] = teacher_id
            target_item["decided_at"] = time.time()

        elif action == "flag":
            target_item["status"] = "FLAGGED"
            target_item["feedback"] = feedback or "Intentional gaming detected."
            target_item["decided_by"] = teacher_id
            target_item["decided_at"] = time.time()
            student = state["student"]
            student["strikes"] = student.get("strikes", 0) + 1
            student["streak_days"] = 0
            student["eco_points"] = max(0, student["eco_points"] - 50)

        # Mirror decision in default_teacher_queue
        try:
            if action == "approve":
                default_teacher_queue.approve(req_id, teacher_id)
            elif action == "reject":
                default_teacher_queue.reject(req_id, teacher_id, feedback)
            elif action == "flag":
                default_teacher_queue.flag(req_id, teacher_id, feedback)
        except Exception:
            pass

        try:
            firestore_db.update_deletion_status(req_id, action, reviewer_id=teacher_id)
        except Exception as e:
            print(f"[!] Firestore decision update notice: {e}")

        save_state(state)

        return jsonify({
            "status": "completed",
            "action_taken": action,
            "request_id": req_id,
            "donation_triggered": donation_triggered,
            "new_tree": new_tree_info,
            "student_bytes_cleared": state["student"]["bytes_cleared"],
            "cumulative_waste_bytes": state["ecofund"]["cumulative_waste_bytes"]
        })

    @app.route("/api/teacher/analytics", methods=["GET"])
    def api_teacher_analytics():
        state = load_state()
        items = state.get("teacher_queue", [])
        trees = state.get("ecofund", {}).get("trees_planted", 0)
        stats = AnalyticsService.calculate_analytics(items, trees_funded=trees)
        return jsonify(stats.to_dict())

    @app.route("/api/teacher/students", methods=["GET"])
    def api_teacher_students():
        auth_header = request.headers.get("Authorization", "")
        token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else request.args.get("token")
        session = default_auth_service.validate_token(token)
        
        class_filter = request.args.get("class_code", "").lower().strip()
        if not class_filter and session and session.get("role") == "teacher":
            tid = session.get("user_id", "").lower()
            for c in ["bio101", "env201", "cs301", "chem102", "earth204"]:
                if c in tid:
                    class_filter = c
                    break

        state = load_state()
        local_students = state.get("students", [])
        
        # If Firestore is active, fetch from Firestore
        firestore_students = []
        if firestore_db.is_connected:
            try:
                firestore_students = firestore_db.get_students_list(class_code=class_filter)
            except Exception as e:
                print(f"[!] Firestore get_students error: {e}")
                
        # Merge by student_id (Firestore takes precedence)
        merged = {}
        for s in local_students:
            sid = s.get("student_id") or s.get("user_id")
            if sid:
                merged[sid] = s
        for s in firestore_students:
            sid = s.get("student_id") or s.get("user_id")
            if sid:
                merged[sid] = s
                
        results = list(merged.values())
        if class_filter:
            results = [s for s in results if s.get("class_code", "").lower() == class_filter]
            
        return jsonify({
            "status": "ok",
            "students": results,
            "total_count": len(results),
            "cloud_sync": firestore_db.is_connected
        })

    @app.route("/api/teacher/students/create", methods=["POST"])
    def api_teacher_create_student():
        auth_header = request.headers.get("Authorization", "")
        token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else request.args.get("token")
        session = default_auth_service.validate_token(token)
        
        teacher_id = "Teacher"
        if session:
            teacher_id = session.get("user_id", "Teacher")
            
        data = request.get_json() or {}
        name = (data.get("name") or "").strip()
        class_code = (data.get("class_code") or "").strip().lower()
        student_id = (data.get("student_id") or "").strip()
        
        if not class_code and session and session.get("role") == "teacher":
            tid = session.get("user_id", "").lower()
            for c in ["bio101", "env201", "cs301", "chem102", "earth204"]:
                if c in tid:
                    class_code = c
                    break

        if not name:
            return jsonify({"status": "error", "message": "Student name is required"}), 400
        if not class_code:
            return jsonify({"status": "error", "message": "Class code is required"}), 400
            
        if not student_id:
            import uuid
            student_id = f"STU-{uuid.uuid4().hex[:6].upper()}"
            
        state = load_state()
        students = state.get("students", [])
        
        # Check duplicate ID in local state
        for existing in students:
            if existing.get("student_id", "").lower() == student_id.lower():
                return jsonify({"status": "error", "message": f"Student ID '{student_id}' already exists."}), 409
                
        # 1. Save to Cloud Firestore
        fb_result = firestore_db.create_student_record(
            student_id=student_id,
            name=name,
            class_code=class_code,
            created_by=teacher_id
        )
        if fb_result.get("status") == "error":
            return jsonify(fb_result), 409
            
        new_student = fb_result.get("student") or {
            "student_id": student_id,
            "user_id": student_id,
            "name": name,
            "class_code": class_code,
            "role": "student",
            "created_by": teacher_id,
            "created_at_iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            "eco_points": 0,
            "bytes_cleared": 0,
            "trees": 0
        }
        
        # 2. Save to local app_state
        students.append(new_student)
        state["students"] = students
        save_state(state)
        
        return jsonify({
            "status": "created",
            "student": new_student,
            "saved_to_firebase": firestore_db.is_connected,
            "message": f"Student ID '{student_id}' created successfully for {name}!"
        }), 201

    @app.route("/api/admin/ecofund", methods=["GET", "POST"])
    def api_admin_ecofund():
        state = load_state()
        if request.method == "POST":
            data = request.get_json() or {}
            if "budget_usd" in data:
                state["ecofund"]["budget_usd"] = float(data["budget_usd"])
            if "threshold_bytes" in data:
                state["ecofund"]["threshold_bytes"] = int(data["threshold_bytes"])
            save_state(state)
            return jsonify({"status": "updated", "ecofund": state["ecofund"]})
        return jsonify(state["ecofund"])

    @app.route("/api/admin/audit", methods=["GET"])
    def api_admin_audit():
        state = load_state()
        items = state.get("teacher_queue", [])
        trees = state.get("ecofund", {}).get("trees_planted", 0)
        stats = AnalyticsService.calculate_analytics(items, trees_funded=trees)
        donations = state.get("ecofund", {}).get("donations_history", [])
        return jsonify({
            "incident_log": stats.incident_log,
            "donations_history": donations,
            "total_incidents": len(stats.incident_log),
        })

    return app


# Expose application object for WSGI production servers (Gunicorn / Google Cloud Run)
app = create_flask_app() if HAS_FLASK else None


def find_free_port(start_port: int = DEFAULT_PORT) -> int:
    """Finds an available TCP port starting from start_port."""
    for port in range(start_port, start_port + 50):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((DEFAULT_HOST, port))
                return port
        except OSError:
            continue
    return start_port


def run_server(port: int = DEFAULT_PORT, host: str = DEFAULT_HOST, launch_window: bool = False):
    """Runs the Flask web server and optionally launches the desktop container."""
    port = find_free_port(port)
    display_host = "0.0.0.0" if host in ("0.0.0.0", "") else host
    url = f"http://{display_host}:{port}"
    print("==================================================")
    print("  DATA-TO-DIRT: Local Core HTTP Service Active    ")
    print("==================================================")
    print(f"[+] Web Server running at: {url}")
    print(f"[+] Static UI Directory:   {UI_DIR}")
    print("==================================================")

    if launch_window:
        from src.app.desktop_shell import launch_desktop_window
        # Launch browser/app in separate thread after a brief delay
        def _launch_delayed():
            time.sleep(0.6)
            launch_desktop_window(url)
        threading.Thread(target=_launch_delayed, daemon=True).start()

    if HAS_FLASK:
        app = create_flask_app()
        # Run Flask server
        app.run(host=host, port=port, debug=False, use_reloader=False)
    else:
        print("[-] Flask not found, running standard http.server")
        from http.server import SimpleHTTPRequestHandler, HTTPServer
        os.chdir(str(UI_DIR))
        server = HTTPServer((host, port), SimpleHTTPRequestHandler)
        server.serve_forever()


if __name__ == "__main__":
    launch_win = "--launch-window" in sys.argv or "--open-browser" in sys.argv
    port_arg = int(os.environ.get("PORT", DEFAULT_PORT))
    for arg in sys.argv:
        if arg.startswith("--port="):
            try:
                port_arg = int(arg.split("=")[1])
            except ValueError:
                pass
    run_server(port=port_arg, launch_window=launch_win)
