"""
Unit and Integration Tests for Tree-Nation Client and Offline Synthetic Emulator.
Verifies REST API structures, deterministic emulation, real project coordinates,
species cataloging, and certificate URL generation.
"""

import unittest
from src.services.tree_nation import (
    TreeNationClient,
    SYNTHETIC_PROJECTS,
    SPECIES_CATALOG,
    TreeNationError,
)


class TestTreeNationService(unittest.TestCase):
    """Test suite for Tree-Nation REST client and synthetic emulator."""

    def setUp(self):
        # Force offline emulator for deterministic testing
        self.client = TreeNationClient(offline=True)

    def test_client_defaults_to_offline_emulator_without_api_key(self):
        """Assert client activates offline emulator when no API key is supplied."""
        c = TreeNationClient(api_key="")
        self.assertFalse(c.is_live)
        self.assertTrue(c.offline)

    def test_client_forced_offline_mode(self):
        """Assert passing offline=True activates emulator even with mock key."""
        c = TreeNationClient(api_key="mock_secret_key_123", offline=True)
        self.assertFalse(c.is_live)
        self.assertTrue(c.offline)

    def test_list_projects_returns_authoritative_reforestation_sites(self):
        """Assert projects list contains real reforestation sites in Madagascar, Tanzania, Kenya."""
        projects = self.client.list_projects()
        self.assertGreaterEqual(len(projects), 3)

        countries = [p["country"] for p in projects]
        self.assertIn("Madagascar", countries)
        self.assertIn("Tanzania", countries)
        self.assertIn("Kenya", countries)

    def test_project_coordinates_accuracy(self):
        """Assert coordinates for projects are accurate real-world geographical coordinates."""
        projects = {p["id"]: p for p in self.client.list_projects()}

        # Madagascar (Eden Projects: Mahajanga / Bombetoka Bay)
        madagascar = projects[14]
        self.assertAlmostEqual(madagascar["latitude"], -15.7167, places=3)
        self.assertAlmostEqual(madagascar["longitude"], 46.3167, places=3)

        # Tanzania (Usambara Biodiversity Conservation)
        tanzania = projects[28]
        self.assertAlmostEqual(tanzania["latitude"], -4.7898, places=3)
        self.assertAlmostEqual(tanzania["longitude"], 38.2917, places=3)

        # Kenya (Great Rift Valley Forest Restoration)
        kenya = projects[42]
        self.assertAlmostEqual(kenya["latitude"], -0.9333, places=3)
        self.assertAlmostEqual(kenya["longitude"], 36.5833, places=3)

    def test_get_project_by_id(self):
        """Assert project lookup by ID returns correct project data."""
        p14 = self.client.get_project(14)
        self.assertEqual(p14["name"], "Eden Projects Madagascar")
        self.assertEqual(p14["primary_species"], "Mangrove")

        p28 = self.client.get_project(28)
        self.assertEqual(p28["name"], "Usambara Biodiversity Conservation")
        self.assertEqual(p28["primary_species"], "Acacia")

        p42 = self.client.get_project(42)
        self.assertEqual(p42["name"], "Great Rift Valley Forest Restoration")
        self.assertEqual(p42["primary_species"], "Baobab")

    def test_species_catalog_contains_expected_species(self):
        """Assert species catalog returns Mangrove, Acacia, and Baobab."""
        species = self.client.list_species()
        common_names = [s["common_name"] for s in species]
        self.assertIn("Mangrove", common_names)
        self.assertIn("Acacia", common_names)
        self.assertIn("Baobab", common_names)

    def test_filter_species_by_project_id(self):
        """Assert filtering species by project ID returns only species for that project."""
        madagascar_species = self.client.list_species(project_id=14)
        self.assertEqual(len(madagascar_species), 1)
        self.assertEqual(madagascar_species[0]["common_name"], "Mangrove")

        tanzania_species = self.client.list_species(project_id=28)
        self.assertEqual(len(tanzania_species), 1)
        self.assertEqual(tanzania_species[0]["common_name"], "Acacia")

    def test_emulator_plant_single_tree(self):
        """Assert synthetic tree planting returns valid tree record with coordinates and certificate."""
        res = self.client.plant_tree(
            count=1,
            project_id=14,
            recipient_name="Alex River",
            student_id="STU-001",
        )

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["mode"], "EMULATOR_OFFLINE")
        self.assertEqual(res["count"], 1)
        self.assertEqual(res["species"], "Mangrove")
        self.assertEqual(res["project_name"], "Eden Projects Madagascar")
        self.assertEqual(res["country"], "Madagascar")
        self.assertIn("latitude", res["coordinates"])
        self.assertIn("longitude", res["coordinates"])
        self.assertGreater(res["co2_offset_kg"], 0.0)

        # Certificate URL assertions
        self.assertTrue(res["certificate_url"].startswith("https://tree-nation.com/certificate/TN-"))
        self.assertTrue(res["app_certificate_url"].startswith("datatodirt://certificates/TN-"))
        self.assertIn("planted_at", res)

    def test_emulator_plant_multiple_trees_multiplies_co2_and_cost(self):
        """Assert batch planting multiplies CO2 offset and financial cost proportionally."""
        res_single = self.client.plant_tree(count=1, project_id=28)
        res_triple = self.client.plant_tree(count=3, project_id=28)

        self.assertEqual(res_triple["count"], 3)
        self.assertAlmostEqual(res_triple["co2_offset_kg"], res_single["co2_offset_kg"] * 3, places=2)
        self.assertAlmostEqual(res_triple["price_eur"], res_single["price_eur"] * 3, places=2)
        self.assertEqual(res_triple["amount_cents"], res_single["amount_cents"] * 3)

    def test_emulator_plant_species_selection_by_project(self):
        """Assert planting in different projects selects the appropriate indigenous species."""
        res_madagascar = self.client.plant_tree(project_id=14)
        self.assertEqual(res_madagascar["species"], "Mangrove")
        self.assertEqual(res_madagascar["country"], "Madagascar")

        res_tanzania = self.client.plant_tree(project_id=28)
        self.assertEqual(res_tanzania["species"], "Acacia")
        self.assertEqual(res_tanzania["country"], "Tanzania")

        res_kenya = self.client.plant_tree(project_id=42)
        self.assertEqual(res_kenya["species"], "Baobab")
        self.assertEqual(res_kenya["country"], "Kenya")

    def test_plant_tree_invalid_count_raises_value_error(self):
        """Assert zero or negative tree count raises ValueError."""
        with self.assertRaises(ValueError):
            self.client.plant_tree(count=0)
        with self.assertRaises(ValueError):
            self.client.plant_tree(count=-5)

    def test_realistic_co2_capture_figures(self):
        """Assert all synthetic projects provide realistic lifetime and annual CO2 figures."""
        for p in SYNTHETIC_PROJECTS:
            # Lifetime capture should be between 100 kg and 1,000 kg
            self.assertGreaterEqual(p["co2_capture_lifetime_kg"], 150.0)
            self.assertLessEqual(p["co2_capture_lifetime_kg"], 600.0)
            # Annual capture should be between 10 kg and 50 kg
            self.assertGreaterEqual(p["co2_capture_annual_kg"], 15.0)
            self.assertLessEqual(p["co2_capture_annual_kg"], 40.0)


if __name__ == "__main__":
    unittest.main()
