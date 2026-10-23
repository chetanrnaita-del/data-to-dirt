"""
Unit & Integration Tests for Data-to-Dirt City Telemetry & Analytics Console
Validates /api/analytics/track, /api/analytics/dashboard, /api/analytics/export,
country code to flag conversions, city state persistence, and device breakdowns.
"""

import unittest
import json
from src.app.server import create_flask_app, get_default_state
from src.services.analytics import AnalyticsService


class TestCityAnalytics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_flask_app()
        cls.client = cls.app.test_client()

    def test_country_code_to_flag(self):
        """Validates conversion of ISO country codes to Unicode flag emojis."""
        self.assertEqual(AnalyticsService.country_code_to_flag("IN"), "🇮🇳")
        self.assertEqual(AnalyticsService.country_code_to_flag("SG"), "🇸🇬")
        self.assertEqual(AnalyticsService.country_code_to_flag("US"), "🇺🇸")
        self.assertEqual(AnalyticsService.country_code_to_flag("GB"), "🇬🇧")
        self.assertEqual(AnalyticsService.country_code_to_flag("JP"), "🇯🇵")
        self.assertEqual(AnalyticsService.country_code_to_flag(""), "🌐")
        self.assertEqual(AnalyticsService.country_code_to_flag("INVALID"), "🌐")

    def test_api_analytics_dashboard_retrieval(self):
        """GET /api/analytics/dashboard returns genuine KPIs, cities list, and device stats."""
        res = self.client.get("/api/analytics/dashboard")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("kpis", data)
        self.assertIn("cities", data)
        self.assertIn("recent_events", data)
        self.assertIn("devices", data)
        self.assertIn("waste_categories", data)

        # Assert cities list is a valid list
        cities = data["cities"]
        self.assertIsInstance(cities, list)

        # Assert KPIs structure
        kpis = data["kpis"]
        self.assertIn("total_visitors", kpis)
        self.assertIn("total_scans", kpis)
        self.assertIn("total_bytes_cleaned", kpis)
        self.assertIn("tracked_cities_count", kpis)
        self.assertIn("active_sessions", kpis)

    def test_api_analytics_track_new_city(self):
        """POST /api/analytics/track registers a new participant city and updates global KPIs."""
        payload = {
            "city": "Paris",
            "country": "France",
            "country_code": "FR",
            "region": "Île-de-France",
            "lat": 48.8566,
            "lon": 2.3522,
            "action": "Device Scan (42 items indexed)",
            "user_id": "TEST-USER-PARIS",
            "role": "student",
            "device_type": "macOS Desktop",
            "bytes_cleaned": 524288000,  # 500 MB
        }
        res = self.client.post("/api/analytics/track", json=payload)
        self.assertEqual(res.status_code, 200)
        resp_data = res.get_json()
        self.assertEqual(resp_data["status"], "success")
        self.assertEqual(resp_data["tracked"]["city"], "Paris")
        self.assertEqual(resp_data["tracked"]["country"], "France")
        self.assertEqual(resp_data["tracked"]["flag"], "🇫🇷")

        # Now verify it appears in dashboard
        dash_res = self.client.get("/api/analytics/dashboard")
        dash_data = dash_res.get_json()
        paris_match = [c for c in dash_data["cities"] if c["city"] == "Paris"]
        self.assertEqual(len(paris_match), 1)
        paris = paris_match[0]
        self.assertEqual(paris["country_code"], "FR")
        self.assertEqual(paris["flag"], "🇫🇷")
        self.assertGreaterEqual(paris["scans"], 1)
        self.assertGreaterEqual(paris["bytes_cleaned"], 524288000)

        # Verify recent_events contains this event at the top
        events = dash_data["recent_events"]
        self.assertTrue(any(e["user_id"] == "TEST-USER-PARIS" for e in events))

    def test_api_analytics_track_unknown_fallback(self):
        """POST /api/analytics/track handles empty/missing fields gracefully with Global fallback."""
        payload = {
            "action": "Anonymous Page View"
        }
        res = self.client.post("/api/analytics/track", json=payload)
        self.assertEqual(res.status_code, 200)
        resp_data = res.get_json()
        self.assertEqual(resp_data["status"], "success")
        self.assertEqual(resp_data["tracked"]["city"], "Global Visitor")

    def test_api_analytics_export_csv(self):
        """GET /api/analytics/export returns a downloadable CSV with city telemetry."""
        # Ensure a city is tracked
        self.client.post("/api/analytics/track", json={
            "city": "Singapore",
            "country": "Singapore",
            "country_code": "SG",
            "action": "Page Visit"
        })
        res = self.client.get("/api/analytics/export")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res.headers.get("Content-Type", ""))
        self.assertIn("attachment; filename=data_to_dirt_city_telemetry.csv", res.headers.get("Content-Disposition", ""))
        content = res.get_data(as_text=True)
        self.assertIn("Rank,City,Country,Code,Visitors,Active_Sessions,Total_Scans,Data_Cleaned_GB,CO2_Avoided_kg,Last_Active", content)
        self.assertIn("Singapore", content)

    def test_api_config_analytics(self):
        """GET /api/config/analytics returns external analytics configuration keys."""
        res = self.client.get("/api/config/analytics")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("cloudflare_token", data)
        self.assertIn("ga_measurement_id", data)


if __name__ == "__main__":
    unittest.main()
