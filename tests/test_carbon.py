"""Comprehensive Unit Tests for Carbon Footprint Calculation Engine.

Validates:
- Storage electrical energy model (0.28 kWh/GB/year).
- Singapore EMA grid carbon intensity model (405.7 g CO2e/kWh).
- Permanently avoided offset calculation (kg CO2e).
- Tree planting sequestration equivalence (20.0 kg CO2/tree/year).
- Preset and custom regional carbon profiles.
- Secondary real-world equivalencies (smartphones, car km, LED hours).
- Edge cases (zero bytes, massive volumes, invalid inputs).
"""

import unittest
from src.services.carbon_calculator import (
    CarbonCalculator,
    CarbonProfile,
    PRESET_PROFILES,
    BYTES_PER_GB,
    calculate_energy_kwh,
    calculate_carbon_grams,
    calculate_avoided_offset_kg,
    calculate_tree_equivalent,
)


class TestCarbonCalculator(unittest.TestCase):
    """Test suite verifying scientific accuracy of digital carbon formulations."""

    def setUp(self):
        self.calc = CarbonCalculator()

    # -------------------------------------------------------------------------
    # Baseline Physics & Benchmark Assertions
    # -------------------------------------------------------------------------

    def test_baseline_constants(self):
        """Verify default parameters match project and Singapore EMA specifications."""
        profile = self.calc.profile
        self.assertEqual(profile.kwh_per_gb_year, 0.28)
        self.assertEqual(profile.grid_intensity_gco2_kwh, 405.7)
        self.assertEqual(profile.projection_years, 1.0)
        self.assertEqual(profile.kg_co2_per_tree_year, 20.0)

    def test_one_gigabyte_energy_consumption(self):
        """1 GiB stored for 1 year must consume exactly 0.28 kWh."""
        one_gb = int(BYTES_PER_GB)
        energy_kwh = self.calc.calculate_energy_kwh(one_gb)
        self.assertAlmostEqual(energy_kwh, 0.28, places=6)

    def test_ten_gigabytes_carbon_footprint(self):
        """10 GiB stored for 1 year under Singapore grid must generate 1,135.96 g CO2e."""
        ten_gb = int(10 * BYTES_PER_GB)
        # 10 * 0.28 = 2.8 kWh
        # 2.8 * 405.7 = 1135.96 g CO2e
        carbon_g = self.calc.calculate_carbon_grams(ten_gb)
        self.assertAlmostEqual(carbon_g, 1135.96, places=4)

    def test_ten_gigabytes_avoided_offset_kg(self):
        """10 GiB dark data deleted must avoid 1.13596 kg CO2e."""
        ten_gb = int(10 * BYTES_PER_GB)
        offset_kg = self.calc.calculate_avoided_offset_kg(ten_gb)
        self.assertAlmostEqual(offset_kg, 1.13596, places=6)

    def test_ten_gigabytes_tree_equivalent(self):
        """10 GiB dark data deleted equals 1.13596 / 20.0 = 0.056798 trees."""
        ten_gb = int(10 * BYTES_PER_GB)
        trees = self.calc.calculate_tree_equivalent(ten_gb)
        expected = 1.13596 / 20.0
        self.assertAlmostEqual(trees, expected, places=6)

    # -------------------------------------------------------------------------
    # Top-Level Module Convenience Functions
    # -------------------------------------------------------------------------

    def test_top_level_convenience_functions(self):
        """Verify module-level functions mirror calculator instance results."""
        five_gb = int(5 * BYTES_PER_GB)
        self.assertAlmostEqual(
            calculate_energy_kwh(five_gb),
            self.calc.calculate_energy_kwh(five_gb),
            places=6,
        )
        self.assertAlmostEqual(
            calculate_carbon_grams(five_gb),
            self.calc.calculate_carbon_grams(five_gb),
            places=6,
        )
        self.assertAlmostEqual(
            calculate_avoided_offset_kg(five_gb),
            self.calc.calculate_avoided_offset_kg(five_gb),
            places=6,
        )
        self.assertAlmostEqual(
            calculate_tree_equivalent(five_gb),
            self.calc.calculate_tree_equivalent(five_gb),
            places=6,
        )

    # -------------------------------------------------------------------------
    # Edge Cases & Boundary Values
    # -------------------------------------------------------------------------

    def test_zero_bytes_produces_zero_emissions(self):
        """Zero bytes must produce exactly 0.0 across all calculations."""
        self.assertEqual(self.calc.calculate_energy_kwh(0), 0.0)
        self.assertEqual(self.calc.calculate_carbon_grams(0), 0.0)
        self.assertEqual(self.calc.calculate_avoided_offset_kg(0), 0.0)
        self.assertEqual(self.calc.calculate_tree_equivalent(0), 0.0)

    def test_negative_bytes_raises_value_error(self):
        """Negative byte inputs must raise ValueError."""
        with self.assertRaises(ValueError):
            self.calc.calculate_energy_kwh(-1024)
        with self.assertRaises(ValueError):
            self.calc.calculate_carbon_grams(-1)
        with self.assertRaises(ValueError):
            self.calc.calculate_avoided_offset_kg(-500)
        with self.assertRaises(ValueError):
            self.calc.calculate_tree_equivalent(-500)

    def test_invalid_tree_factor_raises_value_error(self):
        """Zero or negative tree sequestration factor must raise ValueError."""
        with self.assertRaises(ValueError):
            self.calc.calculate_tree_equivalent(1073741824, factor=0.0)
        with self.assertRaises(ValueError):
            self.calc.calculate_tree_equivalent(1073741824, factor=-10.0)

    def test_massive_dataset_scaling(self):
        """Verify calculations scale linearly without precision or overflow issues."""
        one_petabyte = 1024 * 1024 * int(BYTES_PER_GB)
        energy = self.calc.calculate_energy_kwh(one_petabyte)
        expected_energy = (1024 * 1024) * 0.28
        self.assertAlmostEqual(energy, expected_energy, places=2)

    # -------------------------------------------------------------------------
    # Presets & Multi-Region Carbon Profiles
    # -------------------------------------------------------------------------

    def test_hyperscale_efficient_profile(self):
        """Hyperscale profile (0.12 kWh/GB/yr) produces lower energy output."""
        calc_hyper = CarbonCalculator(PRESET_PROFILES["hyperscale_efficient"])
        one_gb = int(BYTES_PER_GB)
        self.assertAlmostEqual(calc_hyper.calculate_energy_kwh(one_gb), 0.12, places=6)
        self.assertAlmostEqual(
            calc_hyper.calculate_carbon_grams(one_gb), 0.12 * 405.7, places=4
        )

    def test_global_and_european_grid_profiles(self):
        """European grid (220 g/kWh) emissions are lower than global average (475 g/kWh)."""
        calc_eu = CarbonCalculator(PRESET_PROFILES["eu_average"])
        calc_global = CarbonCalculator(PRESET_PROFILES["global_average"])
        one_gb = int(BYTES_PER_GB)

        emissions_eu = calc_eu.calculate_carbon_grams(one_gb)
        emissions_global = calc_global.calculate_carbon_grams(one_gb)

        self.assertAlmostEqual(emissions_eu, 0.28 * 220.0, places=4)
        self.assertAlmostEqual(emissions_global, 0.28 * 475.0, places=4)
        self.assertLess(emissions_eu, emissions_global)

    def test_custom_projection_horizon(self):
        """3-year lifetime horizon triples projected energy and emissions."""
        custom_prof = CarbonProfile(projection_years=3.0)
        calc_3yr = CarbonCalculator(custom_prof)
        one_gb = int(BYTES_PER_GB)

        self.assertAlmostEqual(calc_3yr.calculate_energy_kwh(one_gb), 0.28 * 3.0, places=6)
        self.assertAlmostEqual(
            calc_3yr.calculate_carbon_grams(one_gb), 0.28 * 405.7 * 3.0, places=4
        )

    # -------------------------------------------------------------------------
    # Secondary Equivalencies & Summary Dictionaries
    # -------------------------------------------------------------------------

    def test_secondary_equivalencies(self):
        """Verify smartphone charges, car km, and LED hour conversion factors."""
        ten_gb = int(10 * BYTES_PER_GB)
        sec = self.calc.calculate_secondary_equivalencies(ten_gb)
        carbon_g = 1135.96

        self.assertEqual(sec["smartphones_charged"], round(carbon_g / 8.22, 2))
        self.assertEqual(sec["car_km_avoided"], round(carbon_g / 170.0, 4))
        self.assertEqual(sec["led_hours_saved"], round(carbon_g / 4.06, 2))

    def test_summarize_impact_structure(self):
        """Verify summary dictionary payload matches dashboard UI expectations."""
        one_gb = int(BYTES_PER_GB)
        summary = self.calc.summarize_impact(one_gb)

        self.assertIn("deleted_bytes", summary)
        self.assertIn("deleted_gb", summary)
        self.assertIn("energy_kwh", summary)
        self.assertIn("carbon_g", summary)
        self.assertIn("offset_kg", summary)
        self.assertIn("tree_equivalent", summary)
        self.assertIn("millitrees", summary)
        self.assertIn("secondary", summary)
        self.assertIn("profile", summary)

        self.assertEqual(summary["deleted_bytes"], one_gb)
        self.assertEqual(summary["deleted_gb"], 1.0)
        self.assertEqual(summary["millitrees"], round(summary["tree_equivalent"] * 1000.0, 1))


if __name__ == "__main__":
    unittest.main()
