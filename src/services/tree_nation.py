"""
Data-to-Dirt — Tree-Nation REST API Integration & Deterministic Offline Emulator
Connects to Tree-Nation (https://tree-nation.com/api) for automated reforestation micro-donations.
Provides a deterministic synthetic offline emulator when operating offline or without API keys.
"""

import os
import json
import time
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union


# Authoritative project fixtures for emulator
SYNTHETIC_PROJECTS = [
    {
        "id": 14,
        "name": "Eden Projects Madagascar",
        "location": "Mahajanga / Bombetoka Bay",
        "country": "Madagascar",
        "country_code": "MG",
        "latitude": -15.7167,
        "longitude": 46.3167,
        "description": "Restoration of coastal mangrove estuaries in northwest Madagascar.",
        "primary_species": "Mangrove",
        "scientific_name": "Rhizophora mucronata",
        "co2_capture_lifetime_kg": 250.0,
        "co2_capture_annual_kg": 20.0,
        "price_eur": 1.50,
        "price_usd": 1.50,
        "price_cents": 150,
    },
    {
        "id": 28,
        "name": "Usambara Biodiversity Conservation",
        "location": "Lushoto, Usambara Mountains",
        "country": "Tanzania",
        "country_code": "TZ",
        "latitude": -4.7898,
        "longitude": 38.2917,
        "description": "Montane cloud forest corridor protection and native acacia reforestation.",
        "primary_species": "Acacia",
        "scientific_name": "Acacia tortilis",
        "co2_capture_lifetime_kg": 200.0,
        "co2_capture_annual_kg": 18.0,
        "price_eur": 1.20,
        "price_usd": 1.35,
        "price_cents": 135,
    },
    {
        "id": 42,
        "name": "Great Rift Valley Forest Restoration",
        "location": "Kijabe, Great Rift Valley",
        "country": "Kenya",
        "country_code": "KE",
        "latitude": -0.9333,
        "longitude": 36.5833,
        "description": "Community-led agroforestry and indigenous baobab and cedar planting.",
        "primary_species": "Baobab",
        "scientific_name": "Adansonia digitata",
        "co2_capture_lifetime_kg": 350.0,
        "co2_capture_annual_kg": 25.0,
        "price_eur": 2.00,
        "price_usd": 2.20,
        "price_cents": 220,
    },
]

SPECIES_CATALOG = [
    {
        "id": 101,
        "common_name": "Mangrove",
        "scientific_name": "Rhizophora mucronata",
        "project_id": 14,
        "co2_capture_kg": 250.0,
        "habitat": "Coastal Estuaries",
    },
    {
        "id": 102,
        "common_name": "Acacia",
        "scientific_name": "Acacia tortilis",
        "project_id": 28,
        "co2_capture_kg": 200.0,
        "habitat": "Savanna & Montane Hills",
    },
    {
        "id": 103,
        "common_name": "Baobab",
        "scientific_name": "Adansonia digitata",
        "project_id": 42,
        "co2_capture_kg": 350.0,
        "habitat": "Arid Woodlands",
    },
]


class TreeNationError(Exception):
    """Base exception for Tree-Nation client operations."""
    pass


class TreeNationAPIError(TreeNationError):
    """Raised when the Tree-Nation API returns an error HTTP status."""
    def __init__(self, status_code: int, message: str):
        super().__init__(f"Tree-Nation API error (HTTP {status_code}): {message}")
        self.status_code = status_code
        self.message = message


class TreeNationClient:
    """
    Client for Tree-Nation REST API with high-fidelity deterministic offline emulator.
    Switches to offline emulator when API key is missing or set to 'MOCK'.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://tree-nation.com/api",
        offline: Optional[bool] = None,
        default_project_id: int = 14,
    ):
        self.api_key = api_key if api_key is not None else os.getenv("TREE_NATION_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.default_project_id = default_project_id

        # Determine if offline
        if offline is not None:
            self.offline = offline
        else:
            self.offline = not bool(self.api_key) or self.api_key.upper() in ("MOCK", "OFFLINE", "NONE", "")

        # Internal counter for deterministic emulator IDs
        self._tree_counter = 1000

    @property
    def is_live(self) -> bool:
        """Returns True if client is operating in live authenticated REST mode."""
        return not self.offline and bool(self.api_key)

    def list_projects(self) -> List[Dict[str, Any]]:
        """
        Lists available reforestation projects.
        GET /api/projects
        """
        if self.is_live:
            return self._request_json("GET", "/projects")
        # Offline synthetic emulator
        return [dict(p) for p in SYNTHETIC_PROJECTS]

    def get_project(self, project_id: int) -> Dict[str, Any]:
        """
        Retrieves details for a specific project.
        GET /api/projects/{project_id}
        """
        if self.is_live:
            return self._request_json("GET", f"/projects/{project_id}")

        for p in SYNTHETIC_PROJECTS:
            if p["id"] == project_id:
                return dict(p)
        # Default fallback
        return dict(SYNTHETIC_PROJECTS[0])

    def list_species(self, project_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Lists tree species available in the catalog, optionally filtered by project.
        GET /api/projects/{id}/species or catalog
        """
        if self.is_live:
            endpoint = f"/projects/{project_id}/species" if project_id else "/species"
            return self._request_json("GET", endpoint)

        if project_id is not None:
            return [dict(s) for s in SPECIES_CATALOG if s["project_id"] == project_id]
        return [dict(s) for s in SPECIES_CATALOG]

    def plant_tree(
        self,
        count: int = 1,
        project_id: Optional[int] = None,
        species_id: Optional[int] = None,
        recipient_name: str = "Data-to-Dirt Student",
        recipient_email: str = "student@datatodirt.org",
        student_id: Optional[str] = None,
        message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Plants one or more trees via Tree-Nation API or deterministic synthetic emulator.
        POST /api/plant or /api/projects/{id}/plant
        """
        if count <= 0:
            raise ValueError(f"Tree count must be >= 1, got {count}")

        pid = project_id or self.default_project_id
        msg = message or f"Data-to-Dirt automated micro-donation: {count} tree(s) planted for dark data eliminated!"

        if self.is_live:
            payload = {
                "count": count,
                "project_id": pid,
                "species_id": species_id,
                "email": recipient_email,
                "name": recipient_name,
                "message": msg,
                "lang": "en",
            }
            res = self._request_json("POST", "/plant", payload=payload)
            return res

        # Deterministic Synthetic Offline Emulator
        return self._emulate_plant_tree(
            count=count,
            project_id=pid,
            species_id=species_id,
            recipient_name=recipient_name,
            recipient_email=recipient_email,
            student_id=student_id,
            message=msg,
        )

    def _emulate_plant_tree(
        self,
        count: int,
        project_id: int,
        species_id: Optional[int],
        recipient_name: str,
        recipient_email: str,
        student_id: Optional[str],
        message: str,
    ) -> Dict[str, Any]:
        """Generates deterministic synthetic tree planting records."""
        # Select project
        project = None
        for p in SYNTHETIC_PROJECTS:
            if p["id"] == project_id:
                project = p
                break
        if not project:
            project = SYNTHETIC_PROJECTS[0]

        # Select species
        species = project["primary_species"]
        scientific = project["scientific_name"]
        co2_offset = project["co2_capture_lifetime_kg"] * count

        self._tree_counter += 1
        # Deterministic tree identifier
        seed_str = f"{student_id or recipient_name}:{project['id']}:{self._tree_counter}"
        hex_suffix = hashlib.sha256(seed_str.encode("utf-8")).hexdigest()[:6]
        tree_id = f"TN-{self._tree_counter}-{hex_suffix}"

        now_iso = datetime.now(timezone.utc).isoformat()
        cert_url = f"https://tree-nation.com/certificate/{tree_id}"
        collect_url = f"https://tree-nation.com/trees/view/{tree_id}"
        app_cert_url = f"datatodirt://certificates/{tree_id}"

        response = {
            "status": "success",
            "mode": "EMULATOR_OFFLINE",
            "tree_id": tree_id,
            "count": count,
            "species": species,
            "scientific_name": scientific,
            "project_id": project["id"],
            "project_name": project["name"],
            "country": project["country"],
            "coordinates": {
                "latitude": project["latitude"],
                "longitude": project["longitude"],
            },
            "co2_offset_kg": round(co2_offset, 2),
            "annual_co2_kg": round(project["co2_capture_annual_kg"] * count, 2),
            "price_eur": round(project["price_eur"] * count, 2),
            "price_usd": round(project["price_usd"] * count, 2),
            "amount_cents": int(project["price_cents"] * count),
            "currency": "EUR",
            "recipient_name": recipient_name,
            "recipient_email": recipient_email,
            "student_id": student_id or "STU-GENERAL",
            "message": message,
            "certificate_url": cert_url,
            "collect_url": collect_url,
            "app_certificate_url": app_cert_url,
            "planted_at": now_iso,
        }
        return response

    def _request_json(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        timeout: float = 10.0,
    ) -> Dict[str, Any]:
        """Performs authenticated HTTP request to Tree-Nation API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Data-to-Dirt-Client/1.0",
        }

        data_bytes = None
        if payload is not None:
            data_bytes = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method.upper())

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8") if e.fp else ""
            raise TreeNationAPIError(e.code, f"{e.reason}: {err_body}")
        except urllib.error.URLError as e:
            raise TreeNationError(f"Network connection failed: {e.reason}")
        except Exception as e:
            raise TreeNationError(f"Tree-Nation request failed: {e}")
