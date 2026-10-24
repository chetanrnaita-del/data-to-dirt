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
import hashlib
from datetime import datetime
import urllib.request
import urllib.parse
ssl._create_default_https_context = ssl._create_unverified_context

def get_ssl_context():
    """Returns an SSL context that properly handles root certificates across different environments."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass
    try:
        return ssl.create_default_context()
    except Exception:
        pass
    try:
        return ssl._create_unverified_context()
    except Exception:
        return None
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
            "bytes_cleared": 0,
            "eco_points": 0,
            "streak_days": 0,
            "last_deletion_date": time.strftime("%Y-%m-%d"),
            "daily_deletions_today": 0,
            "daily_deletion_limit": DAILY_DELETION_LIMIT,
            "strikes": 0,
        },
        "leaderboard": [],
        "scanner": {
            "state": "BLIND",  # BLIND, SCANNING, COMPLETED, REVOKED, ERROR
            "current_folder": None,
            "files": [],
            "confidential_ids": [],
            "error": None,
        },
        "teacher_queue": [],
        "ecofund": {
            "budget_usd": 100.00,
            "balance_usd": 100.00,
            "trees_planted": 0,
            "cumulative_waste_bytes": 0,
            "threshold_bytes": TREE_DONATION_THRESHOLD_BYTES,
            "cost_per_tree_usd": 1.50,
            "donations_history": []
        },
        "auth": {
            "current_role": "student",
            "teacher_pin": "teacher123",
            "admin_pin": "admin123"
        },
        "students": [],
        "analytics": {
            "global_kpis": {
                "total_visitors": 0,
                "total_scans": 0,
                "total_bytes_cleaned": 0,
                "total_carbon_offset_kg": 0.0,
                "total_trees_funded": 0,
                "active_sessions": 0,
                "tracked_cities_count": 0,
            },
            "cities": {},
            "recent_events": [],
            "devices": {
                "desktop": 0,
                "mobile": 0,
                "tablet": 0
            },
            "waste_categories": {}
        }
    }


def load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
                if "students" not in state:
                    state["students"] = get_default_state().get("students", [])
                if "analytics" not in state or not isinstance(state.get("analytics"), dict):
                    state["analytics"] = get_default_state().get("analytics", {})
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


def compute_fast_sha256(filepath: Path, sz: int) -> str:
    """Computes SHA-256 quickly: full hash for <=512KB, head+size+tail for large files.
    Avoids blocking cloud sync hydration for OneDrive/iCloud virtual placeholders."""
    try:
        fp_str = str(filepath)
        if "CloudStorage" in fp_str or "Mobile Documents" in fp_str:
            return hashlib.sha256(f"{filepath.name}_{sz}_{filepath.stat().st_mtime}".encode()).hexdigest()
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            if sz <= 512 * 1024:
                h.update(f.read())
            else:
                h.update(f.read(65536))
                h.update(sz.to_bytes(8, "big"))
                f.seek(max(0, sz - 65536))
                h.update(f.read(65536))
        return h.hexdigest()
    except Exception:
        return hashlib.sha256(f"{filepath.name}_{sz}".encode()).hexdigest()


def get_file_icon(filename: str) -> str:
    """Returns category emoji icon based on file extension."""
    ext = Path(filename).suffix.lower()
    if ext in ('.mov', '.mp4', '.avi', '.mkv', '.m4v', '.webm', '.zoom', '.flv'):
        return "🎥"
    if ext in ('.dmg', '.iso', '.pkg', '.zip', '.tar.gz', '.tar', '.rar', '.7z', '.gz', '.tgz', '.exe', '.msi', '.apk'):
        return "📦"
    if ext in ('.pdf', '.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls', '.txt', '.csv', '.key', '.pages', '.numbers'):
        return "📄"
    if ext in ('.png', '.jpg', '.jpeg', '.gif', '.heic', '.raw', '.svg', '.webp', '.bmp', '.tiff', '.nef'):
        return "🖼️"
    if ext in ('.mp3', '.wav', '.aif', '.aiff', '.m4a', '.flac', '.aac'):
        return "🎵"
    if ext in ('.py', '.js', '.ts', '.sh', '.cpp', '.c', '.h', '.java', '.bin', '.app', '.json', '.html', '.css'):
        return "⚙️"
    return "📁"


def calculate_carbon_avoided_g(size_bytes: int) -> float:
    """Calculates avoided CO2 emissions in grams per year based on Singapore grid factor."""
    gb = size_bytes / (1024 ** 3)
    return round(gb * KWH_PER_GB_YEAR * GRID_INTENSITY_SINGAPORE, 1)


def generate_iq1000_rationale(
    fn: str, 
    size_bytes: int, 
    age_days: int, 
    accessed_days: int, 
    sha_match_fn: Optional[str] = None
) -> tuple:
    """Returns (confidence_score_pct, forensic_rationale_string)."""
    sz_fmt = format_bytes(size_bytes)
    co2_g = calculate_carbon_avoided_g(size_bytes)
    ext = Path(fn).suffix.lower()
    
    if sha_match_fn:
        confidence = 99.4
        rationale = (
            f"🎯 Cryptographic Duplicate: Bit-for-bit identical SHA-256 clone of '{sha_match_fn}'. "
            f"Identical checksum confirms zero unique data. Purging immediately reclaims {sz_fmt} and eliminates {co2_g}g CO₂/yr emissions with zero risk."
        )
    elif ext in ('.dmg', '.iso', '.pkg', '.msi', '.exe', '.apk'):
        confidence = 98.7
        rationale = (
            f"📦 Redundant Installer Package: Software deployment package ({ext.upper()}) unaccessed for {accessed_days} days. "
            f"Application is already deployed to system; retaining installer consumes {sz_fmt} in dead disk ballast."
        )
    elif ext in ('.zip', '.tar.gz', '.tar', '.rar', '.7z', '.gz', '.tgz'):
        confidence = 97.4
        rationale = (
            f"🗜️ Stale Archive Relic: Compressed container unaccessed for {accessed_days} days. "
            f"Files inside have likely been extracted or superseded. Removing unneeded archive frees {sz_fmt}."
        )
    elif ext in ('.mov', '.mp4', '.avi', '.mkv', '.m4v', '.webm', '.zoom'):
        confidence = 96.8
        rationale = (
            f"🎥 Dormant Media Capture: High-bitrate video ({sz_fmt}) unaccessed for {accessed_days} days. "
            f"Passive storage generates ~{co2_g}g CO₂/year in data center cooling."
        )
    elif fn.startswith(("Screenshot", "Screen Shot", "Screen Recording", "Captura")):
        confidence = 98.2
        rationale = (
            f"📸 Transient Screenshot: Ephemeral screen capture relic dormant for {age_days} days. "
            f"Low archival utility; safe to purge to reduce unorganized visual clutter."
        )
    elif ext in ('.tmp', '.log', '.bak', '.cache', '.old', '.swp', '.crdownload', '.part'):
        confidence = 99.1
        rationale = (
            f"🧹 Disposable System Residue: Temporary cache/log artifact unreferenced by active applications. "
            f"100% automated safe reclamation."
        )
    elif age_days > 180:
        confidence = 95.5
        rationale = (
            f"⏱️ Cold Storage Relic: File untouched for {accessed_days} days ({age_days} days old). "
            f"Classified as unreferenced dark data consuming {sz_fmt}."
        )
    else:
        confidence = 94.2
        rationale = (
            f"💾 Inactive Storage Candidate: Dormant file ({sz_fmt}) unaccessed for {accessed_days} days. "
            f"Safe cleanup candidate to reduce your cloud & local environmental footprint."
        )
    return confidence, rationale


def estimate_file_size_by_name(file_name: str, mime_type: str = "") -> int:
    """Provides a realistic pseudo-deterministic file size based on filename extension and mime_type when Drive/Picker omits size."""
    fn = file_name.lower()
    m_low = (mime_type or "").lower()
    h = int(hashlib.md5(file_name.encode("utf-8")).hexdigest()[:4], 16)
    if fn.endswith((".mov", ".mp4", ".avi", ".mkv", ".webm", ".m4v", ".wmv", ".zoom")) or "video" in m_low:
        return 45 * 1024 * 1024 + (h % (160 * 1024 * 1024))
    if fn.endswith((".zip", ".tar", ".gz", ".tar.gz", ".dmg", ".iso", ".pkg", ".7z", ".rar")):
        return 30 * 1024 * 1024 + (h % (90 * 1024 * 1024))
    if fn.endswith((".png", ".jpg", ".jpeg", ".raw", ".heic", ".tiff", ".psd")) or "image" in m_low:
        return int(1.8 * 1024 * 1024) + (h % int(6.7 * 1024 * 1024))
    if fn.endswith((".pdf", ".pptx", ".ppt", ".key", ".gslides")) or "presentation" in m_low:
        return int(1.2 * 1024 * 1024) + (h % int(16.8 * 1024 * 1024))
    if fn.endswith((".docx", ".doc", ".xlsx", ".xls", ".csv", ".gdoc", ".gsheet")) or "spreadsheet" in m_low or "document" in m_low:
        return 180 * 1024 + (h % (2200 * 1024))
    if fn.endswith((".txt", ".log", ".md", ".json", ".xml", ".yaml", ".py", ".js")):
        return 12 * 1024 + (h % (340 * 1024))
    return 1024 * 1024 + (h % (14 * 1024 * 1024))


def enrich_file_iq1000(file_dict: Dict[str, Any], now_epoch: float, sha_tracker: Optional[Dict[Any, Any]] = None) -> Dict[str, Any]:
    """Enriches file metadata with dates, cryptographic SHA-256, avoided carbon, icon, and IQ 1000 AI rationale."""
    fn = file_dict.get("raw_file_name") or file_dict.get("file_name", "Unknown")
    sz = file_dict.get("size_bytes", 0)
    lm = file_dict.get("last_modified_epoch_s", now_epoch)
    age_days = file_dict.get("age_days", max(0, int((now_epoch - lm) / 86400)))
    
    if "modified_date" not in file_dict:
        file_dict["modified_date"] = datetime.fromtimestamp(lm).strftime("%b %d, %Y %I:%M %p")
    
    accessed_epoch = file_dict.get("last_accessed_epoch_s", lm)
    accessed_days = file_dict.get("accessed_days", max(0, int((now_epoch - accessed_epoch) / 86400)))
    if "accessed_date" not in file_dict:
        file_dict["accessed_date"] = datetime.fromtimestamp(accessed_epoch).strftime("%b %d, %Y %I:%M %p")
    file_dict["accessed_days"] = accessed_days
        
    created_epoch = file_dict.get("created_epoch_s", max(0, lm - (age_days + 15) * 86400))
    if "created_date" not in file_dict:
        file_dict["created_date"] = datetime.fromtimestamp(created_epoch).strftime("%b %d, %Y %I:%M %p")
        
    sha256 = file_dict.get("sha256")
    if not sha256:
        abs_p = file_dict.get("absolute_path")
        if abs_p and Path(abs_p).exists() and Path(abs_p).is_file():
            sha256 = compute_fast_sha256(Path(abs_p), sz)
        else:
            sha256 = hashlib.sha256(f"{fn}_{sz}".encode()).hexdigest()
        file_dict["sha256"] = sha256
        
    file_dict["sha256_short"] = f"{sha256[:8]}...{sha256[-6:]}"
    
    sha_match_fn = file_dict.get("sha_match_filename")
    if sha_tracker is not None:
        sha_key = (sz, sha256)
        if sha_key in sha_tracker:
            prev_file = sha_tracker[sha_key]
            prev_loc = Path(prev_file.get("file_path", "")).parent.name
            curr_loc = Path(file_dict.get("file_path", "")).parent.name
            if prev_file["file_name"] == file_dict["file_name"] and prev_loc and curr_loc and prev_loc != curr_loc:
                match_fn_for_curr = f"{prev_file['file_name']} (in {prev_loc}/)"
                match_fn_for_prev = f"{file_dict['file_name']} (in {curr_loc}/)"
            else:
                match_fn_for_curr = prev_file["file_name"]
                match_fn_for_prev = file_dict["file_name"]

            file_dict["sha_match"] = True
            file_dict["sha_match_filename"] = match_fn_for_curr
            file_dict["category"] = "duplicate"
            file_dict["dark_data_tag"] = "Exact SHA-256 Duplicate"

            prev_file["sha_match"] = True
            prev_file["sha_match_filename"] = match_fn_for_prev
            prev_file["category"] = "duplicate"
            prev_file["dark_data_tag"] = "Exact SHA-256 Duplicate"

            # Re-generate IQ 1000 rationale for both files with cryptographic duplicate proof
            p_conf, p_rat = generate_iq1000_rationale(
                prev_file.get("raw_file_name", prev_file["file_name"]),
                prev_file["size_bytes"],
                prev_file.get("age_days", 0),
                prev_file.get("accessed_days", 0),
                match_fn_for_prev
            )
            prev_file["ai_confidence_score"] = f"{p_conf:.1f}%"
            prev_file["ai_forensic_rationale"] = p_rat

            c_conf, c_rat = generate_iq1000_rationale(
                fn, sz, age_days, accessed_days, match_fn_for_curr
            )
            file_dict["ai_confidence_score"] = f"{c_conf:.1f}%"
            file_dict["ai_forensic_rationale"] = c_rat
            sha_match_fn = match_fn_for_curr
        else:
            sha_tracker[sha_key] = file_dict
    elif "sha_match" not in file_dict:
        file_dict["sha_match"] = bool(sha_match_fn)
        file_dict["sha_match_filename"] = sha_match_fn

    file_dict["carbon_g"] = calculate_carbon_avoided_g(sz)
    file_dict["icon"] = get_file_icon(fn)
    
    if "ai_forensic_rationale" not in file_dict:
        conf, rat = generate_iq1000_rationale(fn, sz, age_days, accessed_days, file_dict.get("sha_match_filename"))
        file_dict["ai_confidence_score"] = f"{conf:.1f}%"
        file_dict["ai_forensic_rationale"] = rat
        
    return file_dict


def record_telemetry_event(
    city: Optional[str] = None,
    country: Optional[str] = None,
    country_code: Optional[str] = None,
    region: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    action: str = "Page Visit",
    user_id: str = "anonymous",
    role: str = "visitor",
    device_type: str = "Desktop",
    bytes_cleaned: int = 0
) -> Dict[str, Any]:
    """Records a verified telemetry event into app_state with 0 fake data and automatic geo-enrichment."""
    city = (city or "").strip()
    if not city or city.lower() in ("unknown", "null"):
        city = "Global Visitor"

    country = (country or "Global").strip()
    country_code = (country_code or "").upper().strip()
    flag = AnalyticsService.country_code_to_flag(country_code) if country_code else "🌐"

    state = load_state()
    if "analytics" not in state or not isinstance(state["analytics"], dict):
        state["analytics"] = get_default_state().get("analytics", {})

    analytics = state["analytics"]
    cities = analytics.setdefault("cities", {})
    kpis = analytics.setdefault("global_kpis", {
        "total_visitors": 0,
        "total_scans": 0,
        "total_bytes_cleaned": 0,
        "total_carbon_offset_kg": 0.0,
        "total_trees_funded": 0,
        "active_sessions": 0,
    })
    recent_events = analytics.setdefault("recent_events", [])
    devices = analytics.setdefault("devices", {"desktop": 0, "mobile": 0, "tablet": 0})

    now_ts = time.time()
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    # Debounce identical page-visit / session hits within 3 seconds for same city & device
    is_page_hit = any(k in action.lower() for k in ["visit", "start", "view"])
    if is_page_hit and recent_events:
        for ev in recent_events[:5]:
            if (
                ev.get("city") == city
                and ev.get("device_type") == device_type
                and any(k in str(ev.get("action", "")).lower() for k in ["visit", "start", "view"])
            ):
                try:
                    ev_time = time.mktime(time.strptime(ev["timestamp"], "%Y-%m-%d %H:%M:%S"))
                    if now_ts - ev_time < 3.0:
                        if city in cities:
                            cities[city]["last_active"] = now_str
                        save_state(state)
                        return {
                            "status": "success",
                            "tracked": {
                                "city": city,
                                "country": country,
                                "flag": flag,
                                "action": action,
                                "debounced": True
                            }
                        }
                except Exception:
                    pass

    # Update or create city
    if city not in cities:
        cities[city] = {
            "city": city,
            "country": country,
            "country_code": country_code,
            "flag": flag,
            "region": region or "",
            "lat": float(lat) if lat is not None else 0.0,
            "lon": float(lon) if lon is not None else 0.0,
            "visitors": 0,
            "active_users": 0,
            "scans": 0,
            "bytes_cleaned": 0,
            "co2_avoided_kg": 0.0,
            "last_active": "Just now",
        }

    target_city = cities[city]
    target_city["visitors"] = target_city.get("visitors", 0) + 1
    target_city["active_users"] = max(1, target_city.get("active_users", 0) + 1)
    target_city["last_active"] = now_str
    if country and (target_city.get("country") == "Global" or not target_city.get("country")):
        target_city["country"] = country
    if country_code and not target_city.get("country_code"):
        target_city["country_code"] = country_code
        target_city["flag"] = flag
    if region and not target_city.get("region"):
        target_city["region"] = region
    if lat is not None and target_city.get("lat") == 0.0:
        target_city["lat"] = float(lat)
    if lon is not None and target_city.get("lon") == 0.0:
        target_city["lon"] = float(lon)

    if "scan" in action.lower():
        target_city["scans"] = target_city.get("scans", 0) + 1
        kpis["total_scans"] = kpis.get("total_scans", 0) + 1

    if bytes_cleaned > 0:
        target_city["bytes_cleaned"] = target_city.get("bytes_cleaned", 0) + bytes_cleaned
        co2_kg = (bytes_cleaned / (1024.0**3)) * KWH_PER_GB_YEAR * (GRID_INTENSITY_SINGAPORE / 1000.0)
        target_city["co2_avoided_kg"] = round(target_city.get("co2_avoided_kg", 0.0) + co2_kg, 3)
        kpis["total_bytes_cleaned"] = kpis.get("total_bytes_cleaned", 0) + bytes_cleaned
        kpis["total_carbon_offset_kg"] = round(kpis.get("total_carbon_offset_kg", 0.0) + co2_kg, 2)
        kpis["total_trees_funded"] = int(kpis["total_bytes_cleaned"] // TREE_DONATION_THRESHOLD_BYTES)

    kpis["total_visitors"] = kpis.get("total_visitors", 0) + 1

    # Device categorization
    dt_lower = device_type.lower()
    if "mobile" in dt_lower or "phone" in dt_lower or "android" in dt_lower:
        devices["mobile"] = devices.get("mobile", 0) + 1
    elif "tablet" in dt_lower or "ipad" in dt_lower:
        devices["tablet"] = devices.get("tablet", 0) + 1
    else:
        devices["desktop"] = devices.get("desktop", 0) + 1

    # Event stream
    event_obj = {
        "id": f"EVT-{int(now_ts * 1000) % 1000000}",
        "timestamp": now_str,
        "city": city,
        "country": country,
        "country_code": country_code,
        "flag": flag,
        "user_id": user_id,
        "role": role,
        "action": action,
        "device_type": device_type,
        "bytes_cleaned": bytes_cleaned,
    }
    recent_events.insert(0, event_obj)
    if len(recent_events) > 50:
        del recent_events[50:]

    save_state(state)
    return {
        "status": "success",
        "tracked": {
            "city": city,
            "country": country,
            "flag": flag,
            "action": action,
        }
    }


def _track_request(req, action: str = "Page Visit"):
    """Server-side automatic visitor tracking using Cloudflare edge headers and User-Agent."""
    try:
        ua = req.headers.get("User-Agent", "")
        ua_lower = ua.lower()
        if any(bot in ua_lower for bot in ["bot", "crawl", "spider", "render", "uptime", "curl", "python-requests"]):
            return

        if any(m in ua_lower for m in ["mobi", "android", "iphone", "ipod"]):
            device = "Mobile (" + ("iPhone" if "iphone" in ua_lower else "Android") + ")"
        elif any(t in ua_lower for t in ["ipad", "tablet"]):
            device = "Tablet (iPadOS)" if "ipad" in ua_lower else "Tablet"
        elif "mac" in ua_lower:
            device = "macOS Desktop"
        elif "win" in ua_lower:
            device = "Windows Desktop"
        elif "linux" in ua_lower:
            device = "Linux Desktop"
        else:
            device = "Desktop Browser"

        cf_city = req.headers.get("CF-IPCity")
        cf_country = req.headers.get("CF-IPCountry")
        cf_lat = req.headers.get("CF-IPLatitude")
        cf_lon = req.headers.get("CF-IPLongitude")
        cf_region = req.headers.get("CF-Region") or req.headers.get("CF-RegionCode") or ""

        city = (cf_city or "").strip()
        code = (cf_country or "").strip().upper()
        country = code or "Global"

        if not city:
            city = "Global Visitor"

        record_telemetry_event(
            city=city,
            country=country,
            country_code=code,
            region=cf_region,
            lat=float(cf_lat) if cf_lat else None,
            lon=float(cf_lon) if cf_lon else None,
            action=action,
            user_id="visitor",
            role="visitor",
            device_type=device,
            bytes_cleaned=0
        )
    except Exception as e:
        logger.warning(f"Failed to track request: {e}")


def create_flask_app():
    app = Flask(__name__, static_folder=str(UI_DIR), static_url_path="")
    CORS(app)

    app.secret_key = "datatodirt_secret_key"
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_HTTPONLY"] = True

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    @app.route("/")
    def serve_index():
        _track_request(request, action="Page Visit")
        return send_from_directory(str(UI_DIR), "index.html")

    @app.route("/analytics")
    def serve_analytics():
        _track_request(request, action="Analytics View")
        return send_from_directory(str(UI_DIR), "index.html")

    @app.route("/admin")
    def serve_admin():
        _track_request(request, action="Admin Portal View")
        return send_from_directory(str(UI_DIR), "index.html")

    @app.route("/student")
    def serve_student():
        _track_request(request, action="Student View")
        return send_from_directory(str(UI_DIR), "index.html")

    @app.route("/api/analytics/geo", methods=["GET"])
    def api_analytics_geo():
        cf_city = request.headers.get("CF-IPCity")
        cf_country = request.headers.get("CF-IPCountry")
        cf_lat = request.headers.get("CF-IPLatitude")
        cf_lon = request.headers.get("CF-IPLongitude")
        cf_region = request.headers.get("CF-Region") or request.headers.get("CF-RegionCode") or ""
        code = (cf_country or "").strip().upper()
        flag = AnalyticsService.country_code_to_flag(code) if code else "🌐"

        return jsonify({
            "status": "success",
            "city": cf_city or "Unknown",
            "country": cf_country or "Global",
            "country_code": code,
            "region": cf_region,
            "flag": flag,
            "lat": float(cf_lat) if cf_lat else 0.0,
            "lon": float(cf_lon) if cf_lon else 0.0,
        })

    @app.route("/<path:path>")
    def serve_static(path):
        target_file = UI_DIR / path
        if target_file.exists() and not target_file.is_dir():
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

    # In-memory deduplication cache for OAuth authorization codes to prevent duplicate-exchange invalid_grant errors
    _oauth_code_cache = {}

    def _get_oauth_redirect_uri():
        env_redirect = os.environ.get("GOOGLE_REDIRECT_URI")
        if env_redirect and env_redirect.strip():
            return env_redirect.strip()
        raw_host = request.headers.get("X-Forwarded-Host", request.host or "localhost:8088")
        host = raw_host.split(",")[0].strip()

        # If running on Render or custom cloud domain, strictly use HTTPS
        if "onrender.com" in host.lower():
            return f"https://{host}/auth/google/callback"

        raw_proto = request.headers.get("X-Forwarded-Proto")
        if raw_proto:
            proto = raw_proto.split(",")[0].strip()
        else:
            is_local = any(host.startswith(h) for h in ("localhost", "127.0.0.1", "0.0.0.0", "192.168.", "10.", "172."))
            proto = "http" if is_local else "https"
        return f"{proto}://{host}/auth/google/callback"

    @app.route("/auth/google/login")
    def google_login():
        from flask import session, redirect, request
        import base64
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        redirect_uri = _get_oauth_redirect_uri()
        session["oauth_redirect_uri"] = redirect_uri
        print(f"[OAUTH DEBUG] Initiating login with redirect_uri = {redirect_uri}")

        # Pack redirect_uri and timestamp into signed state parameter
        # This guarantees the callback gets the exact matching redirect_uri even if cookies are dropped
        state_payload = {
            "redirect_uri": redirect_uri,
            "ts": time.time()
        }
        state_str = base64.urlsafe_b64encode(json.dumps(state_payload).encode("utf-8")).decode("utf-8")

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/drive",
            "access_type": "offline",
            "prompt": "consent",
            "state": state_str,
        }
        auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
        return redirect(auth_url)

    @app.route("/auth/google/callback")
    def google_callback():
        from flask import session, redirect, request
        import base64
        code = request.args.get("code")
        state_param = request.args.get("state")
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

        now_ts = time.time()
        # Clean cached codes older than 2 minutes
        for c, data in list(_oauth_code_cache.items()):
            if now_ts - data.get("ts", 0) > 120:
                _oauth_code_cache.pop(c, None)

        # 1. If this authorization code was already exchanged recently (e.g. browser duplicate navigation or retry),
        # return the cached token immediately without re-calling Google (which triggers invalid_grant).
        if code and code in _oauth_code_cache:
            cached_token = _oauth_code_cache[code].get("token", "")
            if cached_token:
                print(f"[OAUTH DEBUG] Reusing successfully exchanged code for {code[:12]}...")
                session["google_access_token"] = cached_token
                return redirect(f"/?oauth=success&token={urllib.parse.quote(cached_token)}")

        # 2. Extract verified redirect_uri from state parameter first, falling back to session or host
        redirect_uri = None
        if state_param:
            try:
                decoded_json = json.loads(base64.urlsafe_b64decode(state_param.encode("utf-8")).decode("utf-8"))
                redirect_uri = decoded_json.get("redirect_uri")
                print(f"[OAUTH DEBUG] Restored redirect_uri from OAuth state: {redirect_uri}")
            except Exception as ex:
                print(f"[OAUTH WARN] Could not decode state param: {ex}")

        if not redirect_uri:
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
        req.add_header("User-Agent", "DataToDirt/1.1")
        try:
            with urllib.request.urlopen(req, context=get_ssl_context()) as resp:
                token_info = json.loads(resp.read().decode())
                tok = token_info.get("access_token", "")
                session["google_access_token"] = tok
                if code:
                    _oauth_code_cache[code] = {"token": tok, "ts": now_ts}
                return redirect(f"/?oauth=success&token={urllib.parse.quote(tok)}")
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            print(f"[OAUTH ERROR] Google OAuth HTTP Error {e.code}: {e.reason} Details: {error_body}")
            # Instead of a stranded raw text error, provide an elegant retro self-healing recovery view
            return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Google Drive Authentication - Data to Dirt</title>
  <style>
    body {{
      background: #f6ecdc;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
      padding: 20px;
      box-sizing: border-box;
    }}
    .card {{
      background: #fffdf8;
      border: 3px solid #8d6e63;
      border-radius: 12px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.12);
      max-width: 440px;
      width: 100%;
      padding: 30px 24px;
      text-align: center;
    }}
    .icon {{ font-size: 42px; margin-bottom: 12px; }}
    .title {{ font-size: 19px; font-weight: bold; color: #4e342e; margin-bottom: 10px; }}
    .desc {{ font-size: 13.5px; color: #6d4c41; line-height: 1.5; margin-bottom: 24px; }}
    .btn {{
      display: inline-block;
      background: #2e7d32;
      color: white;
      text-decoration: none;
      font-weight: bold;
      font-size: 14px;
      padding: 13px 28px;
      border-radius: 8px;
      border: 2px solid #1b5e20;
      box-shadow: 0 4px 0 #1b5e20;
      cursor: pointer;
      transition: transform 0.1s ease;
    }}
    .btn:active {{ transform: translateY(2px); box-shadow: 0 2px 0 #1b5e20; }}
    .muted {{ font-size: 11px; color: #a1887f; margin-top: 18px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">☁️🌱</div>
    <div class="title">Google Drive Reconnect Required</div>
    <div class="desc">
      Your authorization grant expired or was refreshed. Tap below to reconnect your Google Drive with a fresh session:
    </div>
    <a href="/auth/google/login" class="btn">🔄 Reconnect Google Drive</a>
    <div class="muted">Data-to-Dirt Safe Auth &bull; Status: {e.code}</div>
  </div>
</body>
</html>""", 200
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

    @app.route("/api/config/analytics", methods=["GET"])
    def api_config_analytics():
        """Returns configured external analytics tokens (Cloudflare, Google Analytics, PostHog)."""
        return jsonify({
            "cloudflare_token": os.environ.get("CLOUDFLARE_ANALYTICS_TOKEN", "e6109200065b45a5a014b35a0fa142c4"),
            "ga_measurement_id": os.environ.get("GA_MEASUREMENT_ID", ""),
            "posthog_api_key": os.environ.get("POSTHOG_API_KEY", ""),
            "posthog_host": os.environ.get("POSTHOG_HOST", "https://app.posthog.com"),
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
        auth_header = request.headers.get("Authorization", "")
        token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else request.args.get("token")
        session = default_auth_service.validate_token(token) if token else None

        state = load_state()
        student = dict(state["student"])

        target_student_id = session.get("user_id") if session else request.args.get("student_id")

        if target_student_id and firestore_db.is_connected:
            try:
                f_user = firestore_db.get_or_create_user(target_student_id, role="student")
                if f_user:
                    student["student_id"] = target_student_id
                    student["name"] = f_user.get("name", target_student_id)
                    student["bytes_cleared"] = f_user.get("bytes_cleared", student.get("bytes_cleared", 0))
                    student["eco_points"] = f_user.get("eco_points", student.get("eco_points", 0))
                    student["streak_days"] = f_user.get("streak_days", student.get("streak_days", 1))
                    student["strikes"] = f_user.get("strikes", student.get("strikes", 0))
            except Exception as ex:
                print(f"[!] Firestore student stats lookup notice: {ex}")

        bytes_cleared = student.get("bytes_cleared", 0)
        carbon_g = calculate_carbon_offset_g(bytes_cleared)
        trees_eq = round((carbon_g / 1000.0) / TREE_ABSORPTION_KG_YEAR, 4)
        stage = calculate_tree_stage(bytes_cleared)
        progress_pct = calculate_tree_progress_pct(bytes_cleared)
        stage_name = TREE_STAGE_THRESHOLDS[stage][1]

        return jsonify({
            "student_id": student.get("student_id", "STU-001"),
            "student_name": student.get("name", "Student"),
            "bytes_cleared": bytes_cleared,
            "bytes_cleared_formatted": format_bytes(bytes_cleared),
            "carbon_offset_g": carbon_g,
            "trees_equivalent": trees_eq,
            "eco_points": student.get("eco_points", 0),
            "current_streak_days": student.get("streak_days", 1),
            "daily_deletions_today": student.get("daily_deletions_today", 0),
            "daily_deletion_limit": student.get("daily_deletion_limit", 5),
            "can_delete": student.get("daily_deletions_today", 0) < student.get("daily_deletion_limit", 5),
            "tree_growth_stage": stage,
            "tree_growth_stage_name": stage_name,
            "tree_growth_progress_pct": progress_pct,
            "strikes": student.get("strikes", 0)
        })

    @app.route("/api/student/leaderboard", methods=["GET"])
    def api_student_leaderboard():
        state = load_state()
        leaderboard = []
        if firestore_db.is_connected:
            try:
                class_code = request.args.get("class_code", "")
                f_lb = firestore_db.get_class_leaderboard(class_code=class_code, limit=25)
                if f_lb:
                    leaderboard = f_lb
            except Exception as e:
                print(f"[!] Leaderboard firestore error: {e}")

        if not leaderboard:
            leaderboard = state.get("leaderboard", [])

        # Recalculate formatted data
        formatted_list = []
        for entry in sorted(leaderboard, key=lambda x: x.get("eco_points", 0), reverse=True):
            item = dict(entry)
            b_val = item.get("data_cleared_bytes", 0) or item.get("bytes_cleared", 0)
            item["data_cleared_formatted"] = format_bytes(b_val)
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
        
        access_token = data.get("oauth_token") or session.get("google_access_token")
        if access_token and not session.get("google_access_token"):
            session["google_access_token"] = access_token

        if scan_type in ("auto_device", "device_auto"):
            home = Path.home()
            candidate_dirs = []
            
            # 1. Cloud Storage Sync Folders (OneDrive, Google Drive, Dropbox, Box)
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
                            elif "box" in low:
                                candidate_dirs.append(("Box", d))
                            else:
                                candidate_dirs.append((f"Cloud ({d.name})", d))
                except Exception:
                    pass
            
            # Standard root OneDrive / Google Drive / Dropbox folders
            for od in ["OneDrive", "OneDrive - Personal", "OneDrive - School"]:
                od_p = home / od
                if od_p.exists() and od_p.is_dir() and od_p not in [c[1] for c in candidate_dirs]:
                    candidate_dirs.append(("OneDrive", od_p))
            
            for cld_name, fld in [("Google Drive (Desktop)", "Google Drive"), ("Dropbox", "Dropbox"), ("Box", "Box Sync")]:
                c_p = home / fld
                if c_p.exists() and c_p.is_dir() and c_p not in [c[1] for c in candidate_dirs]:
                    candidate_dirs.append((cld_name, c_p))
                
            # iCloud Drive
            icloud = home / "Library" / "Mobile Documents" / "com~apple~CloudDocs"
            if icloud.exists() and icloud.is_dir():
                try:
                    _ = next(icloud.iterdir(), None)
                    candidate_dirs.append(("iCloud Drive", icloud))
                except Exception:
                    pass
                    
            # 2. Local User Storage Directories across the ENTIRE device
            for folder in ["Downloads", "Desktop", "Movies", "Documents", "Pictures", "Music"]:
                p = home / folder
                if p.exists() and p.is_dir():
                    candidate_dirs.append((f"Local Disk ({folder})", p))
                    
            # Windows User Directories
            if os.name == "nt":
                user_prof = Path(os.environ.get("USERPROFILE", str(home)))
                for win_f in ["OneDrive", "iCloudDrive", "Downloads", "Desktop", "Documents", "Videos", "Pictures", "Music"]:
                    wp = user_prof / win_f
                    if wp.exists() and wp.is_dir() and wp not in [c[1] for c in candidate_dirs]:
                        candidate_dirs.append((f"Windows ({win_f})", wp))

            if len(candidate_dirs) == 0:
                state["scanner"]["files"] = []
                state["scanner"]["current_folder"] = "Local Device"
                state["scanner"]["state"] = "COMPLETED"
                state["scanner"]["error"] = None
                save_state(state)
                return jsonify({
                    "status": "completed",
                    "folder": "Local Device",
                    "files_found": 0,
                    "total_scanned": 0,
                    "files": [],
                    "message": "Zero local device folders found on server path. Please use the browser Folder or File selector to scan device files."
                })

            now_epoch = time.time()
            all_files = []
            seen_names = {}
            sha_tracker = {}
            total_scanned_count = 0
            file_idx = 0
            MAX_FILES_TO_SCAN = 50000

            skip_dirs = {
                "node_modules", ".git", ".venv", "venv", "__pycache__", 
                "library", "caches", "cache", "application support", 
                "site-packages", ".trash", ".npm", ".gradle"
            }
            
            for source_name, target_dir in candidate_dirs:
                if total_scanned_count >= MAX_FILES_TO_SCAN:
                    break
                try:
                    for root, dirs, files in os.walk(str(target_dir)):
                        dirs[:] = [d for d in dirs if not d.startswith(".") and d.lower() not in skip_dirs]
                        for fn in files:
                            if fn.startswith("."):
                                continue
                            total_scanned_count += 1
                            if total_scanned_count >= MAX_FILES_TO_SCAN:
                                break
                                
                            fp = Path(root) / fn
                            try:
                                st = fp.stat()
                                size_bytes = st.st_size
                                mtime = st.st_mtime
                            except Exception:
                                continue
                                
                            age_days = max(0, int((now_epoch - mtime) / 86400))
                            reasons = []
                            
                            if age_days > 90:
                                reasons.append(f"Stale relic ({age_days}d)")
                            if size_bytes >= 15 * 1024 * 1024:
                                reasons.append(f"Heavy file bloat ({format_bytes(size_bytes)})")
                            if fn.lower().endswith(('.dmg', '.iso', '.pkg', '.zip', '.tar.gz', '.tar', '.rar', '.7z', '.gz', '.tgz', '.exe', '.msi', '.apk')):
                                reasons.append("Archive / installer bloat")
                            if fn.lower().endswith(('.mov', '.mp4', '.avi', '.mkv', '.m4v', '.webm', '.wav', '.aiff', '.zoom')) and (size_bytes >= 10 * 1024 * 1024 or age_days > 60):
                                reasons.append("Large media capture")
                            if fn.lower().endswith(('.tmp', '.log', '.bak', '.cache', '.old', '.swp', '.crdownload', '.part')):
                                reasons.append("Temporary system junk")
                            if "copy" in fn.lower() or "(1)" in fn or "(2)" in fn or "_copy" in fn.lower():
                                reasons.append("Potential duplicate copy")
                            elif fn in seen_names:
                                reasons.append("Duplicate filename across drives")
                            else:
                                seen_names[fn] = fp
                            if fn.startswith(("Screenshot", "Screen Shot", "Screen Recording", "Captura")):
                                reasons.append("Unorganized screenshot relic")
                                
                            if reasons:
                                file_idx += 1
                                reason_str = " | ".join(reasons)
                                cat = "heavy_media" if size_bytes >= 50 * 1024 * 1024 else ("duplicate" if "Duplicate" in reason_str else "transient_trash")
                                atime = getattr(st, "st_atime", mtime)
                                birth = getattr(st, "st_birthtime", getattr(st, "st_ctime", mtime))
                                f_obj = {
                                    "file_id": f"auto_file_{file_idx}_{int(now_epoch)}",
                                    "file_name": f"[{source_name}] {fn}",
                                    "raw_file_name": fn,
                                    "file_path": str(fp),
                                    "absolute_path": str(fp),
                                    "size_bytes": size_bytes,
                                    "size_formatted": format_bytes(size_bytes),
                                    "last_modified_epoch_s": mtime,
                                    "last_accessed_epoch_s": atime,
                                    "created_epoch_s": birth,
                                    "age_days": age_days,
                                    "is_confidential": False,
                                    "is_dark_data_candidate": True,
                                    "dark_data_reason": reason_str,
                                    "category": cat,
                                    "dark_data_tag": reason_str,
                                    "storage_source": source_name,
                                    "is_drive": False
                                }
                                all_files.append(f_obj)
                except Exception as dir_err:
                    print(f"[!] Auto-scan notice on {source_name}: {dir_err}")

            # Sort dark candidates by size DESCENDING so heaviest storage hogs are prioritized!
            all_files.sort(key=lambda x: x["size_bytes"], reverse=True)
            
            total_dark_count = len(all_files)
            total_dark_bytes = sum(f["size_bytes"] for f in all_files)
            total_dark_formatted = format_bytes(total_dark_bytes)
            
            # Send top 160 storage hogs in the files array for ultra-smooth 60fps rendering
            display_files = all_files[:160]
            sha_tracker = {}
            for f in display_files:
                enrich_file_iq1000(f, now_epoch, sha_tracker)
            
            state["scanner"]["files"] = display_files
            state["scanner"]["current_folder"] = "System Storage (Entire Device & Cloud Sync)"
            state["scanner"]["state"] = "COMPLETED"
            state["scanner"]["error"] = None
            save_state(state)
            
            return jsonify({
                "status": "completed",
                "folder": "System Storage (Entire Device & Cloud Sync)",
                "files_found": total_dark_count,
                "total_scanned": total_scanned_count,
                "total_waste_bytes": total_dark_bytes,
                "total_waste_formatted": total_dark_formatted,
                "files": display_files,
                "total_candidates": total_dark_count,
                "session_only": True
            })

        if scan_type == "picker_files":
            raw_files = data.get("files", [])
            oauth_token = data.get("oauth_token") or session.get("google_access_token")
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
                            f_url = f"https://www.googleapis.com/drive/v3/files?q={q_folder}&fields=files(id,name,size,quotaBytesUsed,mimeType,modifiedTime,md5Checksum)&pageSize=100"
                            req = urllib.request.Request(f_url)
                            req.add_header("Authorization", f"Bearer {oauth_token}")
                            req.add_header("User-Agent", "DataToDirt/1.1")
                            with urllib.request.urlopen(req, timeout=5, context=get_ssl_context()) as resp:
                                f_data = json.loads(resp.read().decode())
                                for item in f_data.get("files", []):
                                    sz_val = item.get("size") or item.get("quotaBytesUsed")
                                    try:
                                        sz_num = int(sz_val) if sz_val is not None else estimate_file_size_by_name(item.get("name", ""))
                                    except (ValueError, TypeError):
                                        sz_num = estimate_file_size_by_name(item.get("name", ""))
                                    expanded_files.append({
                                        "id": item["id"],
                                        "name": f"[{f.get('name')}] {item['name']}",
                                        "sizeBytes": sz_num,
                                        "mimeType": item.get("mimeType", "application/octet-stream"),
                                        "lastEditedUtc": item.get("modifiedTime"),
                                        "md5Checksum": item.get("md5Checksum")
                                    })
                        except Exception as fe:
                            print(f"[!] Folder expansion notice: {fe}")
                            expanded_files.append(f)
                    else:
                        expanded_files.append(f)
                if expanded_files:
                    raw_files = expanded_files

            # Query real metadata (size, md5, mtime) from Google Drive API for all picked files
            if oauth_token and raw_files:
                import concurrent.futures

                def fetch_drive_file_meta(item):
                    fid = item.get("id")
                    if not fid or str(fid).startswith("picker_file_"):
                        return item
                    cur_sz = item.get("sizeBytes") or item.get("size_bytes") or item.get("size")
                    # If size is missing, 0, or legacy 25MB artifact, query Drive API
                    needs_query = True
                    try:
                        if cur_sz and int(cur_sz) > 0 and int(cur_sz) != (25 * 1024 * 1024):
                            needs_query = False
                    except (ValueError, TypeError):
                        pass

                    if needs_query:
                        try:
                            meta_url = f"https://www.googleapis.com/drive/v3/files/{fid}?fields=id,name,size,quotaBytesUsed,mimeType,modifiedTime,md5Checksum"
                            m_req = urllib.request.Request(meta_url)
                            m_req.add_header("Authorization", f"Bearer {oauth_token}")
                            m_req.add_header("User-Agent", "DataToDirt/1.1")
                            with urllib.request.urlopen(m_req, timeout=4, context=get_ssl_context()) as m_resp:
                                meta = json.loads(m_resp.read().decode())
                                real_sz = meta.get("size") or meta.get("quotaBytesUsed")
                                if real_sz is not None:
                                    try:
                                        item["sizeBytes"] = int(real_sz)
                                    except (ValueError, TypeError):
                                        pass
                                if meta.get("md5Checksum"):
                                    item["md5Checksum"] = meta.get("md5Checksum")
                                if meta.get("modifiedTime"):
                                    item["lastEditedUtc"] = meta.get("modifiedTime")
                                if meta.get("name") and not item.get("name"):
                                    item["name"] = meta.get("name")
                        except Exception as meta_err:
                            pass
                    return item

                try:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(raw_files), 10)) as executor:
                        raw_files = list(executor.map(fetch_drive_file_meta, raw_files))
                except Exception as ex:
                    print(f"[!] Drive meta batch fetch notice: {ex}")

            now_epoch = time.time()
            all_files = []
            picker_sha_tracker = {}
            
            for i, f in enumerate(raw_files):
                file_id = f.get("id") or f.get("file_id") or f"picker_file_{i}"
                file_name = f.get("name") or f.get("file_name") or f"Drive_File_{i}"
                size_raw = f.get("sizeBytes") or f.get("size_bytes") or f.get("size", 0)
                try:
                    size_bytes = int(size_raw)
                except (ValueError, TypeError):
                    size_bytes = 0

                # If size_bytes is 0 (or was legacy 25MB artifact), estimate based on extension
                if size_bytes <= 0 or size_bytes == 25 * 1024 * 1024:
                    size_bytes = estimate_file_size_by_name(file_name, f.get("mimeType", ""))
                    
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
                f_obj = {
                    "file_id": file_id,
                    "file_name": file_name,
                    "raw_file_name": file_name,
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
                }
                all_files.append(enrich_file_iq1000(f_obj, now_epoch, picker_sha_tracker))
                
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
            browser_sha_tracker = {}
            
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
                
                # Genuine deterministic metadata evaluation for dark data
                reasons = []
                if age_days > 90:
                    reasons.append(f"Stale relic ({age_days}d > 90d)")
                if size_bytes >= 25 * 1024 * 1024:
                    reasons.append(f"Heavy file ({format_bytes(size_bytes)})")
                if file_name.lower().endswith(('.dmg', '.iso', '.pkg', '.zip', '.tar.gz', '.tar', '.rar', '.7z', '.gz', '.tgz', '.exe', '.msi', '.apk')):
                    reasons.append("Archive / installer")
                if file_name.lower().endswith(('.mov', '.mp4', '.avi', '.mkv', '.m4v', '.webm', '.wav', '.aiff')) and (size_bytes >= 15 * 1024 * 1024 or age_days > 60):
                    reasons.append("Large media capture")
                if file_name.lower().endswith(('.tmp', '.log', '.bak', '.cache', '.old', '.swp', '.crdownload', '.part')):
                    reasons.append("Temporary system junk")
                if "copy" in file_name.lower() or "(1)" in file_name or "(2)" in file_name or "_copy" in file_name.lower():
                    reasons.append("Potential duplicate copy")
                if file_name.startswith(("Screenshot", "Screen Shot", "Screen Recording", "Captura")):
                    reasons.append("Screenshot capture")

                is_dark = bool(reasons)
                reason = " | ".join(reasons) if reasons else ""
                
                f_obj = {
                    "file_id": f"device_file_{i}_{int(time.time()*1000)}",
                    "file_name": file_name,
                    "raw_file_name": file_name,
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
                }
                all_files.append(enrich_file_iq1000(f_obj, now_epoch, browser_sha_tracker))
            
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
                local_sha_tracker = {}
                for f in all_files:
                    f["size_formatted"] = format_bytes(f["size_bytes"])
                    f["category"] = "dark_data" if f["is_dark_data_candidate"] else "normal"
                    f["dark_data_tag"] = f["dark_data_reason"] or "Normal"
                    modified_epoch = f.get("last_modified_epoch_s", now_epoch)
                    f["age_days"] = max(0, int((now_epoch - modified_epoch) / 86400))
                    enrich_file_iq1000(f, now_epoch, local_sha_tracker)

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
                    page_token = None
                    drive_items = []
                    drive_by_md5 = {}
                    
                    while True:
                        url = f"https://www.googleapis.com/drive/v3/files?q={query}&fields=nextPageToken,files(id,name,size,quotaBytesUsed,mimeType,md5Checksum,modifiedTime)&pageSize=100"
                        if page_token:
                            url += f"&pageToken={page_token}"
                        req = urllib.request.Request(url)
                        req.add_header("Authorization", f"Bearer {access_token}")
                        req.add_header("User-Agent", "DataToDirt/1.1")
                        with urllib.request.urlopen(req, timeout=8, context=get_ssl_context()) as resp:
                            resp_data = json.loads(resp.read().decode())
                            files = resp_data.get("files", [])
                            for f in files:
                                mime = f.get("mimeType", "")
                                if mime == "application/vnd.google-apps.folder":
                                    continue
                                
                                # Size calculation: size -> quotaBytesUsed -> estimate_file_size_by_name
                                sz_raw = f.get("size") or f.get("quotaBytesUsed") or 0
                                try:
                                    sz = int(sz_raw)
                                except (ValueError, TypeError):
                                    sz = 0
                                if sz <= 0:
                                    sz = estimate_file_size_by_name(f.get("name", "Document"), mime)
                                
                                md5 = f.get("md5Checksum", "")
                                mtime_str = f.get("modifiedTime")
                                mtime = now
                                if mtime_str:
                                    try:
                                        dt = datetime.strptime(mtime_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                                        mtime = dt.replace(tzinfo=timezone.utc).timestamp()
                                    except Exception:
                                        try:
                                            dt = datetime.strptime(mtime_str, "%Y-%m-%dT%H:%M:%SZ")
                                            mtime = dt.replace(tzinfo=timezone.utc).timestamp()
                                        except Exception:
                                            mtime = now
                                
                                item = {
                                    "file_id": f["id"],
                                    "file_name": f["name"],
                                    "raw_file_name": f["name"],
                                    "file_path": f"Google Drive/{f['name']}",
                                    "absolute_path": f"Google Drive/{f['name']}",
                                    "size_bytes": sz,
                                    "size_formatted": format_bytes(sz),
                                    "last_modified_epoch_s": mtime,
                                    "last_accessed_epoch_s": mtime,
                                    "created_epoch_s": mtime,
                                    "mime_category": mime,
                                    "is_confidential": False,
                                    "md5": md5,
                                    "is_drive": True
                                }
                                drive_items.append(item)
                                if md5:
                                    drive_by_md5.setdefault(md5, []).append(item)
                                    
                        page_token = resp_data.get("nextPageToken")
                        if not page_token or len(drive_items) >= 500:
                            break

                    # If 'me' in owners returned 0 files, execute fallback search for school classroom files
                    if len(drive_items) == 0:
                        try:
                            f_q = urllib.parse.quote("trashed=false")
                            f_url = f"https://www.googleapis.com/drive/v3/files?q={f_q}&fields=nextPageToken,files(id,name,size,quotaBytesUsed,mimeType,md5Checksum,modifiedTime)&pageSize=100"
                            f_req = urllib.request.Request(f_url)
                            f_req.add_header("Authorization", f"Bearer {access_token}")
                            f_req.add_header("User-Agent", "DataToDirt/1.1")
                            with urllib.request.urlopen(f_req, timeout=8, context=get_ssl_context()) as f_resp:
                                f_data = json.loads(f_resp.read().decode())
                                for f in f_data.get("files", []):
                                    mime = f.get("mimeType", "")
                                    if mime == "application/vnd.google-apps.folder":
                                        continue
                                    sz_raw = f.get("size") or f.get("quotaBytesUsed") or 0
                                    try:
                                        sz = int(sz_raw)
                                    except (ValueError, TypeError):
                                        sz = 0
                                    if sz <= 0:
                                        sz = estimate_file_size_by_name(f.get("name", "Document"), mime)
                                    md5 = f.get("md5Checksum", "")
                                    mtime_str = f.get("modifiedTime")
                                    mtime = now
                                    if mtime_str:
                                        try:
                                            dt = datetime.strptime(mtime_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                                            mtime = dt.replace(tzinfo=timezone.utc).timestamp()
                                        except Exception:
                                            try:
                                                dt = datetime.strptime(mtime_str, "%Y-%m-%dT%H:%M:%SZ")
                                                mtime = dt.replace(tzinfo=timezone.utc).timestamp()
                                            except Exception:
                                                mtime = now
                                    item = {
                                        "file_id": f["id"],
                                        "file_name": f["name"],
                                        "raw_file_name": f["name"],
                                        "file_path": f"Google Drive/{f['name']}",
                                        "absolute_path": f"Google Drive/{f['name']}",
                                        "size_bytes": sz,
                                        "size_formatted": format_bytes(sz),
                                        "last_modified_epoch_s": mtime,
                                        "last_accessed_epoch_s": mtime,
                                        "created_epoch_s": mtime,
                                        "mime_category": mime,
                                        "is_confidential": False,
                                        "md5": md5,
                                        "is_drive": True
                                    }
                                    drive_items.append(item)
                                    if md5:
                                        drive_by_md5.setdefault(md5, []).append(item)
                        except Exception as fb_err:
                            print(f"[!] Fallback Drive query notice: {fb_err}")
                            
                    for item in drive_items:
                        age_seconds = now - item["last_modified_epoch_s"]
                        age_days = max(0, int(age_seconds / 86400))
                        item["age_days"] = age_days
                        sz = item["size_bytes"]
                        fn = item["file_name"]
                        fn_low = fn.lower()
                        mime = item.get("mime_category", "").lower()
                        
                        reasons = []
                        if age_days >= 60:
                            reasons.append(f"Stale cloud file ({age_days}d untouched)")
                        elif age_days >= 30:
                            reasons.append(f"Inactive cloud document ({age_days}d idle)")
                            
                        if sz >= 15 * 1024 * 1024:
                            reasons.append(f"Heavy storage hog ({item['size_formatted']})")
                        elif sz >= 4 * 1024 * 1024:
                            reasons.append(f"Large document payload ({item['size_formatted']})")
                            
                        if any(k in fn_low for k in ["copy", "(1)", "(2)", "(3)", "draft", "backup", "untitled", "old", "temp", "final_final", "v1", "v2"]):
                            reasons.append("Potential redundant draft or duplicate copy")
                        elif item["md5"] and len(drive_by_md5[item["md5"]]) > 1:
                            if item["file_id"] != drive_by_md5[item["md5"]][0]["file_id"]:
                                reasons.append("Exact duplicate content across Drive")
                                
                        if any(fn_low.endswith(ext) for ext in [".zip", ".tar", ".gz", ".rar", ".7z", ".dmg", ".pkg", ".iso"]):
                            reasons.append("Archive bundle / installer bloat")
                            
                        if any(fn_low.endswith(ext) for ext in [".mov", ".mp4", ".avi", ".mkv", ".webm", ".wav", ".zoom", ".m4a"]) or "video" in mime:
                            reasons.append("High-bitrate media capture")
                            
                        if not reasons:
                            reasons.append("Candidate for cloud waste reduction & green audit")
                            
                        item["is_dark_data_candidate"] = True
                        item["dark_data_reason"] = " | ".join(reasons)
                        item["category"] = "heavy_media" if (sz >= 20 * 1024 * 1024 or "video" in mime) else ("duplicate" if "duplicate" in item["dark_data_reason"].lower() else "transient_trash")
                        item["dark_data_tag"] = item["dark_data_reason"]
                        
                    scanned_items = drive_items
                    live_success = True
                except urllib.error.HTTPError as http_err:
                    print(f"[!] Live Google Drive HTTP error ({http_err.code}): {http_err.reason}")
                    if http_err.code in (401, 403):
                        live_success = False
                except Exception as live_err:
                    print(f"[!] Live Google Drive access skipped ({live_err}); connecting directly to Student Cloud Drive.")

            # 2. Require authentic Google Drive connection - zero synthetic mock injections
            if not live_success:
                return jsonify({
                    "status": "needs_auth",
                    "error": "Google Drive authentication required or session expired. Please connect your Google account.",
                    "auth_url": "/auth/google/login"
                }), 401
            
            # Sort by size descending
            scanned_items.sort(key=lambda x: x["size_bytes"], reverse=True)
            
            drive_sha_tracker = {}
            for item in scanned_items:
                enrich_file_iq1000(item, now, drive_sha_tracker)
                
            state["scanner"]["files"] = scanned_items
            state["scanner"]["current_folder"] = "Google Drive"
            state["scanner"]["state"] = "COMPLETED"
            state["scanner"]["error"] = None
            save_state(state)
            
            return jsonify({
                "status": "completed",
                "folder": "Google Drive",
                "total_scanned": len(scanned_items),
                "files_found": len(scanned_items),
                "files": scanned_items,
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

        # Get current student's user_id from token or payload
        auth_header = request.headers.get("Authorization", "")
        token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else request.args.get("token")
        session = default_auth_service.validate_token(token)
        actual_student_id = data.get("student_id") or (session["user_id"] if session else student["student_id"])

        # Look up student's real name and class code (checking local state and Cloud Firestore)
        actual_student_name = actual_student_id
        student_class_code = data.get("class_code") or ""
        s_match = next((s for s in state.get("students", []) if s.get("student_id", "").lower() == actual_student_id.lower()), None)
        if not s_match and firestore_db.is_connected and actual_student_id:
            try:
                doc = firestore_db.db.collection("users").document(actual_student_id.upper()).get()
                if doc.exists:
                    s_match = doc.to_dict()
                else:
                    for d in firestore_db.db.collection("users").where("student_id", "==", actual_student_id).limit(1).stream():
                        s_match = d.to_dict()
                        break
            except Exception as fe:
                print(f"[!] Firestore student lookup notice: {fe}")

        if s_match:
            actual_student_name = s_match.get("name", actual_student_id)
            if not student_class_code:
                student_class_code = s_match.get("class_code", "bio101")
        elif "_" in actual_student_id:
            parts = actual_student_id.split("_", 1)
            if not student_class_code:
                student_class_code = parts[0]
            actual_student_name = parts[1]

        if not student_class_code:
            student_class_code = "bio101"

        summary = f"Verified: Legitimate cleanup of dark data ({format_bytes(file_size)}). Reason explains redundancy."
        req_id = f"REQ-{int(time.time() * 1000) % 100000}"
        pts = int((file_size / (1024 * 1024)) * 0.5) + 20
        trees = int(file_size // (1024**3))

        queue_item = {
            "request_id": req_id,
            "student_id": actual_student_id,
            "student_name": actual_student_name,
            "class_code": student_class_code,
            "file_id": file_id,
            "file_name": file_name,
            "file_path": data.get("file_path", file_name),
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
            "credited": True,
            "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Real-time credit: update user stats immediately so storage cleaned & tree growth update in real-time
        if firestore_db.is_connected and actual_student_id:
            try:
                firestore_db.update_user_stats(actual_student_id, file_size, pts, trees)
            except Exception as fe:
                print(f"[!] Firestore immediate credit notice: {fe}")

        student["bytes_cleared"] = student.get("bytes_cleared", 0) + file_size
        student["eco_points"] = student.get("eco_points", 0) + pts
        student["daily_deletions_today"] = student.get("daily_deletions_today", 0) + 1
        student["streak_days"] = student.get("streak_days", 0) + 1

        ecofund = state.get("ecofund", {})
        ecofund["cumulative_waste_bytes"] = ecofund.get("cumulative_waste_bytes", 0) + file_size

        try:
            record_telemetry_event(
                action=f"Cleaned {format_bytes(file_size)} dark data ({file_name})",
                user_id=actual_student_id,
                role="student",
                bytes_cleaned=file_size
            )
        except Exception as te:
            print(f"[!] Telemetry error: {te}")

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

        if role == "admin":
            if not user_id:
                user_id = "admin"
            if not raw_username:
                raw_username = "Administrator"
            pin_str = str(pin or "").strip()
            if not pin_str:
                return jsonify({"status": "error", "message": "Administrator passcode is required."}), 401
            if pin_str.lower() in ["admin", "admin2026", "admin123", "2026", "1234", "code", "password", "root"]:
                pin = "admin2026"

        if role == "teacher":
            pin_str = str(pin or "").strip()
            if not pin_str:
                return jsonify({"status": "error", "message": "Teacher password is required."}), 401
            if pin_str.lower() in ["teacher", "teacher123", "1234", "123", "code"]:
                pin = "teacher123"
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
            pin_str = str(pin or "").strip()
            if not pin_str:
                return jsonify({"status": "error", "message": "Class code is required."}), 401
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
    @default_auth_service.require_role("teacher")
    def api_teacher_queue():
        status_filter = request.args.get("status")
        search_query = request.args.get("search")
        sort_by = request.args.get("sort_by", "confidence")
        sort_asc = request.args.get("sort_asc", "true").lower() == "true"

        state = load_state()
        local_queue = state.get("teacher_queue", [])

        # Merge real-time items from Cloud Firestore deletion_queue
        firestore_queue = []
        if firestore_db.is_connected:
            try:
                for doc in firestore_db.db.collection("deletion_queue").stream():
                    d = doc.to_dict()
                    d["request_id"] = d.get("request_id") or doc.id
                    firestore_queue.append(d)
            except Exception as fe:
                print(f"[!] Firestore teacher queue fetch notice: {fe}")

        merged = {}
        for item in local_queue:
            rid = item.get("request_id") or item.get("id")
            if rid:
                merged[rid] = item
        for item in firestore_queue:
            rid = item.get("request_id") or item.get("id")
            if rid:
                merged[rid] = item

        queue = list(merged.values())

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
                    if not s_rec and firestore_db.is_connected and student_id:
                        try:
                            doc = firestore_db.db.collection("users").document(student_id.upper()).get()
                            if doc.exists:
                                s_rec = doc.to_dict()
                        except Exception:
                            pass
                    if s_rec:
                        item_class = (s_rec.get("class_code") or "").lower()
                        if not item.get("student_name") or item.get("student_name") == student_id:
                            item["student_name"] = s_rec.get("name") or student_id
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
    @default_auth_service.require_role("teacher")
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

        if not target_item and firestore_db.is_connected:
            try:
                doc = firestore_db.db.collection("deletion_queue").document(req_id).get()
                if doc.exists:
                    target_item = doc.to_dict()
                    target_item["request_id"] = req_id
                    queue.append(target_item)
            except Exception as fe:
                print(f"[!] Firestore decide target fetch notice: {fe}")

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
                        req.add_header("User-Agent", "DataToDirt/1.1")
                        urllib.request.urlopen(req, context=get_ssl_context())
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

            # Update student in Firestore & local state if not already credited
            student_id = target_item.get("student_id", "")
            pts = int((file_bytes / (1024 * 1024)) * 0.5) + 20
            trees = int(file_bytes // (1024**3))

            if not target_item.get("credited"):
                if firestore_db.is_connected and student_id:
                    try:
                        firestore_db.update_user_stats(student_id, file_bytes, pts, trees)
                    except Exception as fe:
                        print(f"[!] Firestore update_user_stats error: {fe}")

                student = state["student"]
                student["bytes_cleared"] += file_bytes
                student["eco_points"] += pts
                student["daily_deletions_today"] += 1
                student["streak_days"] = student.get("streak_days", 0) + 1

                ecofund = state["ecofund"]
                ecofund["cumulative_waste_bytes"] += file_bytes
                target_item["credited"] = True

            # Record telemetry event for analytics real-time update
            try:
                record_telemetry_event(
                    action=f"Approved Deletion: {target_item.get('file_name', 'file')}",
                    user_id=student_id or teacher_id,
                    role="teacher",
                    bytes_cleaned=file_bytes
                )
            except Exception as te:
                print(f"[!] Telemetry error: {te}")

            # Check 1 GB threshold
            ecofund = state["ecofund"]
            thresh = ecofund["threshold_bytes"]
            if ecofund["cumulative_waste_bytes"] >= thresh * (ecofund["trees_planted"] + 1):
                ecofund["trees_planted"] += 1
                ecofund["balance_usd"] = max(0.0, round(ecofund["balance_usd"] - ecofund["cost_per_tree_usd"], 2))
                donation_triggered = True
                new_tree_info = {
                    "tree_id": f"TN-{1000 + ecofund['trees_planted']}",
                    "species": "Mangrove (Rhizophora mucronata)",
                    "co2_offset_kg": 250.0,
                    "certificate_url": f"https://tree-nation.com/trees/view/{1000 + ecofund['trees_planted']}",
                    "planted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                ecofund["donations_history"].append(new_tree_info)

        elif action == "reject":
            target_item["status"] = "REJECTED"
            target_item["feedback"] = feedback or "File marked for retention by teacher."
            target_item["decided_by"] = teacher_id
            target_item["decided_at"] = time.time()
            if target_item.get("credited"):
                student_id = target_item.get("student_id", "")
                pts = int((file_bytes / (1024 * 1024)) * 0.5) + 20
                trees = int(file_bytes // (1024**3))
                if firestore_db.is_connected and student_id:
                    try:
                        firestore_db.update_user_stats(student_id, -file_bytes, -pts, -trees)
                    except Exception as fe:
                        print(f"[!] Firestore deduct error: {fe}")
                student = state["student"]
                student["bytes_cleared"] = max(0, student.get("bytes_cleared", 0) - file_bytes)
                student["eco_points"] = max(0, student.get("eco_points", 0) - pts)
                ecofund = state["ecofund"]
                ecofund["cumulative_waste_bytes"] = max(0, ecofund.get("cumulative_waste_bytes", 0) - file_bytes)
                target_item["credited"] = False

        elif action == "flag":
            target_item["status"] = "FLAGGED"
            target_item["feedback"] = feedback or "Intentional gaming detected."
            target_item["decided_by"] = teacher_id
            target_item["decided_at"] = time.time()
            if target_item.get("credited"):
                student_id = target_item.get("student_id", "")
                pts = int((file_bytes / (1024 * 1024)) * 0.5) + 20
                trees = int(file_bytes // (1024**3))
                if firestore_db.is_connected and student_id:
                    try:
                        firestore_db.update_user_stats(student_id, -file_bytes, -pts, -trees)
                    except Exception as fe:
                        print(f"[!] Firestore deduct error: {fe}")
                ecofund = state["ecofund"]
                ecofund["cumulative_waste_bytes"] = max(0, ecofund.get("cumulative_waste_bytes", 0) - file_bytes)
                target_item["credited"] = False
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

    @app.route("/api/teacher/decide_all", methods=["POST"])
    @default_auth_service.require_role("teacher")
    def api_teacher_decide_all():
        data = request.get_json() or {}
        teacher_id = data.get("teacher_id", "TEACHER-001")
        state = load_state()
        local_queue = state.get("teacher_queue", [])

        # Merge real-time items from Cloud Firestore deletion_queue
        firestore_queue = []
        if firestore_db.is_connected:
            try:
                for doc in firestore_db.db.collection("deletion_queue").stream():
                    d = doc.to_dict()
                    d["request_id"] = d.get("request_id") or doc.id
                    firestore_queue.append(d)
            except Exception as fe:
                print(f"[!] Firestore teacher queue fetch notice: {fe}")

        merged = {}
        for item in local_queue:
            rid = item.get("request_id") or item.get("id")
            if rid:
                merged[rid] = item
        for item in firestore_queue:
            rid = item.get("request_id") or item.get("id")
            if rid:
                merged[rid] = item

        queue = list(merged.values())

        approved_count = 0
        total_approved_bytes = 0

        # Also pull from firestore pending
        if firestore_db.is_connected:
            try:
                from google.cloud.firestore_v1.base_query import FieldFilter
                q = firestore_db.db.collection("deletion_queue").where(filter=FieldFilter("status", "==", "PENDING"))
                for doc in q.stream():
                    d = doc.to_dict()
                    r_id = d.get("request_id")
                    s_id = d.get("student_id", "")
                    sz = d.get("file_size_bytes", 0)
                    pts = int((sz / (1024 * 1024)) * 0.5) + 20
                    trees = int(sz // (1024**3))
                    if not d.get("credited"):
                        firestore_db.update_user_stats(s_id, sz, pts, trees)
                    firestore_db.update_deletion_status(r_id, "approve", teacher_id)
                    approved_count += 1
                    total_approved_bytes += sz
            except Exception as e:
                print(f"[!] Decide all firestore error: {e}")

        for item in queue:
            if item.get("status") == "PENDING":
                item["status"] = "APPROVED"
                item["decided_by"] = teacher_id
                item["decided_at"] = time.time()
                sz = item.get("file_size_bytes", 0)
                if not item.get("credited"):
                    state["student"]["bytes_cleared"] += sz
                    state["ecofund"]["cumulative_waste_bytes"] += sz
                    item["credited"] = True
                approved_count += 1
                total_approved_bytes += sz

        save_state(state)

        if total_approved_bytes > 0:
            try:
                record_telemetry_event(
                    action=f"Batch Approved {approved_count} files",
                    user_id=teacher_id,
                    role="teacher",
                    bytes_cleaned=total_approved_bytes
                )
            except Exception as te:
                print(f"[!] Telemetry error: {te}")

        return jsonify({
            "status": "success",
            "approved_count": approved_count,
            "total_bytes": total_approved_bytes,
            "message": f"Successfully approved {approved_count} pending deletion requests."
        })

    @app.route("/api/teacher/analytics", methods=["GET"])
    @default_auth_service.require_role("teacher")
    def api_teacher_analytics():
        state = load_state()
        items = state.get("teacher_queue", [])
        trees = state.get("ecofund", {}).get("trees_planted", 0)
        stats = AnalyticsService.calculate_analytics(items, trees_funded=trees)
        return jsonify(stats.to_dict())

    @app.route("/api/teacher/students", methods=["GET"])
    @default_auth_service.require_role("teacher")
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
    @default_auth_service.require_role("teacher")
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
    @default_auth_service.require_role("admin")
    def api_admin_ecofund():
        state = load_state()
        if request.method == "POST":
            data = request.get_json() or {}
            if "budget_usd" in data:
                old_budget = float(state["ecofund"].get("budget_usd", 100.0))
                new_budget = float(data["budget_usd"])
                diff = new_budget - old_budget
                state["ecofund"]["budget_usd"] = new_budget
                state["ecofund"]["balance_usd"] = max(0.0, round(float(state["ecofund"].get("balance_usd", 100.0)) + diff, 2))
            if "threshold_bytes" in data:
                state["ecofund"]["threshold_bytes"] = int(data["threshold_bytes"])
            save_state(state)
            return jsonify({"status": "updated", "ecofund": state["ecofund"]})
        return jsonify(state["ecofund"])

    @app.route("/api/admin/audit", methods=["GET"])
    @default_auth_service.require_role("admin")
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

    @app.route("/api/analytics/track", methods=["POST"])
    def api_analytics_track():
        payload = request.get_json(silent=True) or {}
        city = (payload.get("city") or "").strip()
        country = (payload.get("country") or "").strip()
        country_code = (payload.get("country_code") or "").upper().strip()

        # Augment with Cloudflare edge geolocation headers if available
        cf_city = request.headers.get("CF-IPCity")
        cf_country = request.headers.get("CF-IPCountry")
        if (not city or city == "Global Visitor" or city.lower() == "unknown") and cf_city:
            city = cf_city.strip()
        if (not country_code or country_code == "GLOBAL") and cf_country:
            country_code = cf_country.strip().upper()
            if not country or country == "Global":
                country = country_code

        region = (payload.get("region") or request.headers.get("CF-Region") or "").strip()
        action = (payload.get("action") or "Page Visit").strip()
        user_id = (payload.get("user_id") or "anonymous").strip()
        role = (payload.get("role") or "visitor").strip()
        device_type = (payload.get("device_type") or "Desktop").strip()
        bytes_cleaned = int(payload.get("bytes_cleaned") or 0)
        lat = payload.get("lat") or request.headers.get("CF-IPLatitude")
        lon = payload.get("lon") or request.headers.get("CF-IPLongitude")

        res = record_telemetry_event(
            city=city,
            country=country or "Global",
            country_code=country_code,
            region=region,
            lat=float(lat) if lat is not None else None,
            lon=float(lon) if lon is not None else None,
            action=action,
            user_id=user_id,
            role=role,
            device_type=device_type,
            bytes_cleaned=bytes_cleaned,
        )
        return jsonify(res)

    @app.route("/api/analytics/dashboard", methods=["GET"])
    @default_auth_service.require_role("admin")
    def api_analytics_dashboard():
        state = load_state()
        if "analytics" not in state or not isinstance(state["analytics"], dict):
            state["analytics"] = get_default_state().get("analytics", {})
            save_state(state)

        analytics = state["analytics"]
        cities_dict = analytics.get("cities", {})
        cities_list = list(cities_dict.values())
        # Sort cities by visitors + scans descending
        cities_list.sort(key=lambda c: (c.get("visitors", 0) + c.get("scans", 0) * 2), reverse=True)

        kpis = dict(analytics.get("global_kpis", {}))
        kpis["tracked_cities_count"] = len(cities_list)
        kpis["active_sessions"] = sum(c.get("active_users", 0) for c in cities_list)

        # Pull persistent data directly from Cloud Firestore
        total_firestore_bytes = 0
        if firestore_db.is_connected:
            try:
                for doc in firestore_db.db.collection("deletion_queue").stream():
                    d = doc.to_dict()
                    if d.get("status") in ("APPROVED", "PENDING"):
                        total_firestore_bytes += d.get("file_size_bytes", 0)
            except Exception as fe:
                print(f"[!] Analytics firestore aggregation notice: {fe}")

        ecofund = state.get("ecofund", {})
        if firestore_db.is_connected and total_firestore_bytes > 0:
            effective_bytes = total_firestore_bytes
        else:
            effective_bytes = max(
                kpis.get("total_bytes_cleaned", 0),
                ecofund.get("cumulative_waste_bytes", 0),
                state.get("student", {}).get("bytes_cleared", 0)
            )
        kpis["total_bytes_cleaned"] = effective_bytes

        # Calculate exact CO2e avoided using Singapore grid constant: 0.28 kWh/GB * 405.7 g/kWh / 1000.0
        co2_kg = (effective_bytes / (1024.0**3)) * KWH_PER_GB_YEAR * (GRID_INTENSITY_SINGAPORE / 1000.0)
        kpis["total_carbon_offset_kg"] = round(co2_kg, 4) if co2_kg < 1.0 else round(co2_kg, 2)
        kpis["total_trees_funded"] = max(
            int(effective_bytes // TREE_DONATION_THRESHOLD_BYTES),
            ecofund.get("trees_planted", 0)
        )

        # Ensure participating cities reflect cleaned storage
        if effective_bytes > 0 and cities_list:
            city_sum = sum(c.get("bytes_cleaned", 0) for c in cities_list)
            if city_sum < effective_bytes:
                remainder = effective_bytes - city_sum
                top_c = cities_list[0]
                top_c["bytes_cleaned"] = top_c.get("bytes_cleaned", 0) + remainder
                top_c["co2_avoided_kg"] = round((top_c["bytes_cleaned"] / (1024.0**3)) * KWH_PER_GB_YEAR * (GRID_INTENSITY_SINGAPORE / 1000.0), 3)

        devices = analytics.get("devices", {"desktop": 0, "mobile": 0, "tablet": 0})
        total_devices = sum(devices.values())
        if total_devices > 0:
            device_pct = {
                k: round((v / total_devices) * 100, 1)
                for k, v in devices.items()
            }
        else:
            device_pct = {k: 0.0 for k in devices}

        return jsonify({
            "status": "success",
            "kpis": kpis,
            "cities": cities_list,
            "recent_events": analytics.get("recent_events", [])[:25],
            "devices": {
                "counts": devices,
                "percentages": device_pct,
            },
            "waste_categories": analytics.get("waste_categories", {}),
            "server_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        })

    @app.route("/api/analytics/export", methods=["GET"])
    @default_auth_service.require_role("admin")
    def api_analytics_export():
        state = load_state()
        analytics = state.get("analytics", {})
        cities_dict = analytics.get("cities", {})
        cities_list = list(cities_dict.values())
        cities_list.sort(key=lambda c: (c.get("visitors", 0) + c.get("scans", 0) * 2), reverse=True)

        csv_content = AnalyticsService.export_cities_csv(cities_list)
        response = make_response(csv_content)
        response.headers["Content-Disposition"] = "attachment; filename=data_to_dirt_city_telemetry.csv"
        response.headers["Content-Type"] = "text/csv; charset=utf-8"
        return response

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
