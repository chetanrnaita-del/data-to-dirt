"""
Unit and Integration Tests for Eco-Fund Accumulator and Tamper-Evident Ledger.
Tests cumulative byte threshold crossings, carryover surplus, budget safety caps,
Tree-Nation micro-donations, double-entry ledger chaining, and cryptographic tamper detection.
"""

import os
import tempfile
import unittest
from pathlib import Path

from src.services.ledger import AuditLedger, LedgerBlock
from src.services.tree_nation import TreeNationClient
from src.services.eco_fund import (
    EcoFundManager,
    DEFAULT_THRESHOLD_BYTES,
    DEFAULT_COST_PER_TREE_CENTS,
)


class TestEcoFundAndLedger(unittest.TestCase):
    """Test suite for EcoFundManager and AuditLedger."""

    def setUp(self):
        # Dedicated temporary directory for test storage
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_dir = Path(self.temp_dir.name)
        self.tree_client = TreeNationClient(offline=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    # =========================================================================
    # 1. Cumulative Waste Accumulator & Threshold Trigger Tests
    # =========================================================================

    def test_accumulation_under_threshold_remains_accumulating(self):
        """Assert adding bytes below 1.0 GB updates surplus without triggering donation."""
        eco = EcoFundManager(initial_budget_usd=50.0, tree_client=self.tree_client)
        half_gb = 500 * 1024 * 1024  # 500 MB

        res = eco.accumulate_waste(half_gb, student_id="STU-001")
        self.assertEqual(res["status"], "ACCUMULATING")
        self.assertEqual(res["trees_triggered"], 0)
        self.assertEqual(res["surplus_bytes"], half_gb)
        self.assertEqual(eco.cumulative_waste_bytes, half_gb)
        self.assertEqual(eco.lifetime_trees, 0)
        self.assertEqual(eco.budget_usd, 50.0)

    def test_threshold_crossing_500mb_plus_600mb(self):
        """
        Assert 500MB + 600MB = 1.1GB triggers 1 tree donation,
        deducts $1.50 from budget, carries over remaining ~76MB surplus,
        and provides certificate and celebration event payload.
        """
        eco = EcoFundManager(initial_budget_usd=20.0, tree_client=self.tree_client)
        mb_500 = 500 * 1024 * 1024
        mb_600 = 600 * 1024 * 1024
        total_bytes = mb_500 + mb_600
        expected_surplus = total_bytes - DEFAULT_THRESHOLD_BYTES

        # Step 1: Accumulate 500 MB
        r1 = eco.accumulate_waste(mb_500, student_id="STU-001")
        self.assertEqual(r1["status"], "ACCUMULATING")
        self.assertEqual(r1["trees_triggered"], 0)

        # Step 2: Accumulate 600 MB (crosses 1.0 GB)
        r2 = eco.accumulate_waste(mb_600, student_id="STU-001", student_name="Alex River")
        self.assertEqual(r2["status"], "DONATION_EXECUTED")
        self.assertEqual(r2["trees_triggered"], 1)
        self.assertEqual(eco.lifetime_trees, 1)
        self.assertEqual(r2["surplus_bytes"], expected_surplus)
        self.assertEqual(eco.surplus_bytes, expected_surplus)

        # Cost deduction
        self.assertEqual(eco.budget_usd, 20.0 - 1.50)

        # Celebration event payload
        event = r2["celebration_event"]
        self.assertIsNotNone(event)
        self.assertEqual(event["type"], "TREE_PLANTED")
        self.assertEqual(event["trees_count"], 1)
        self.assertEqual(event["sound_cue"], "FANFARE")
        self.assertIn("certificate_url", event)
        self.assertTrue(event["certificate_url"].startswith("https://tree-nation.com/certificate/TN-"))

    def test_multi_gb_batch_accumulation(self):
        """
        Assert a single 3.5 GB accumulation triggers 3 trees,
        deducts 3 * $1.50 = $4.50, and retains 0.5 GB surplus carryover.
        """
        eco = EcoFundManager(initial_budget_usd=100.0, tree_client=self.tree_client)
        batch_bytes = int(3.5 * DEFAULT_THRESHOLD_BYTES)
        expected_surplus = int(0.5 * DEFAULT_THRESHOLD_BYTES)

        res = eco.accumulate_waste(batch_bytes, student_id="STU-002")
        self.assertEqual(res["status"], "DONATION_EXECUTED")
        self.assertEqual(res["trees_triggered"], 3)
        self.assertEqual(eco.lifetime_trees, 3)
        self.assertEqual(res["surplus_bytes"], expected_surplus)
        self.assertEqual(eco.surplus_bytes, expected_surplus)
        self.assertAlmostEqual(eco.budget_usd, 100.0 - 4.50, places=2)

    def test_carryover_triggers_subsequent_tree(self):
        """
        Assert carryover surplus combines with subsequent deletions to trigger subsequent trees.
        1.4 GB -> 1 tree, 0.4 GB carryover.
        + 0.7 GB -> 0.4 + 0.7 = 1.1 GB -> 2nd tree, 0.1 GB carryover.
        """
        eco = EcoFundManager(initial_budget_usd=50.0, tree_client=self.tree_client)
        b1 = int(1.4 * DEFAULT_THRESHOLD_BYTES)
        r1 = eco.accumulate_waste(b1)
        self.assertEqual(r1["trees_triggered"], 1)
        self.assertEqual(eco.lifetime_trees, 1)

        b2 = int(0.7 * DEFAULT_THRESHOLD_BYTES)
        r2 = eco.accumulate_waste(b2)
        self.assertEqual(r2["trees_triggered"], 1)
        self.assertEqual(eco.lifetime_trees, 2)
        expected_surplus = (b1 + b2) - (2 * DEFAULT_THRESHOLD_BYTES)
        self.assertEqual(r2["surplus_bytes"], expected_surplus)

    def test_custom_threshold_and_custom_cost(self):
        """Assert configurable threshold (e.g. 500 MB) and custom cost ($0.50/tree)."""
        thresh_500mb = 500 * 1024 * 1024
        eco = EcoFundManager(
            initial_budget_usd=10.0,
            threshold_bytes=thresh_500mb,
            cost_per_tree_cents=50,  # $0.50 per tree
            tree_client=self.tree_client,
        )

        res = eco.accumulate_waste(600 * 1024 * 1024)  # 600 MB >= 500 MB
        self.assertEqual(res["status"], "DONATION_EXECUTED")
        self.assertEqual(res["trees_triggered"], 1)
        self.assertEqual(eco.budget_usd, 10.0 - 0.50)

    # =========================================================================
    # 2. Budget Safety Caps & Exhaustion Handling
    # =========================================================================

    def test_zero_budget_enters_pending_funds_state(self):
        """Assert crossing 1 GB with $0.00 budget enters PENDING_FUNDS and does not drop bytes."""
        eco = EcoFundManager(initial_budget_usd=0.0, tree_client=self.tree_client)
        res = eco.accumulate_waste(DEFAULT_THRESHOLD_BYTES)

        self.assertEqual(res["status"], "PENDING_FUNDS")
        self.assertEqual(res["trees_triggered"], 0)
        self.assertEqual(eco.lifetime_trees, 0)
        self.assertEqual(eco.budget_usd, 0.0)
        self.assertEqual(eco.surplus_bytes, DEFAULT_THRESHOLD_BYTES)
        self.assertIsNotNone(res["alert"])
        self.assertEqual(res["alert"]["warning"], "INSUFFICIENT_ECO_FUND_BUDGET")

    def test_partial_funds_insufficient_enters_pending_funds(self):
        """Assert having $1.00 when $1.50 is required enters PENDING_FUNDS."""
        eco = EcoFundManager(initial_budget_usd=1.00, tree_client=self.tree_client)
        res = eco.accumulate_waste(DEFAULT_THRESHOLD_BYTES)

        self.assertEqual(res["status"], "PENDING_FUNDS")
        self.assertEqual(eco.budget_usd, 1.00)
        self.assertEqual(eco.lifetime_trees, 0)

    def test_budget_topup_resolves_pending_donations(self):
        """Assert adding budget after entering PENDING_FUNDS disburses pending trees."""
        eco = EcoFundManager(initial_budget_usd=0.0, tree_client=self.tree_client)
        eco.accumulate_waste(DEFAULT_THRESHOLD_BYTES)
        self.assertEqual(eco.lifetime_trees, 0)

        # Admin tops up budget by $25.00
        topup_res = eco.topup_budget(2500, admin_id="TEACHER_1")
        self.assertEqual(topup_res["status"], "success")
        self.assertEqual(eco.lifetime_trees, 1)
        self.assertAlmostEqual(eco.budget_usd, 25.0 - 1.50, places=2)

    def test_large_budget_precision_no_float_drift(self):
        """Assert $1,000,000.00 budget operates without precision degradation."""
        eco = EcoFundManager(initial_budget_usd=1000000.0, tree_client=self.tree_client)
        res = eco.accumulate_waste(DEFAULT_THRESHOLD_BYTES)
        self.assertEqual(res["status"], "DONATION_EXECUTED")
        self.assertAlmostEqual(eco.budget_usd, 1000000.0 - 1.50, places=2)

    # =========================================================================
    # 3. Ledger SHA-256 Block Creation & Cryptographic Tamper Detection
    # =========================================================================

    def test_ledger_initial_block_is_budget_topup(self):
        """Assert initial non-zero budget creates a verified BUDGET_TOPUP genesis block."""
        eco = EcoFundManager(initial_budget_usd=100.0, tree_client=self.tree_client)
        blocks = eco.ledger.blocks
        self.assertGreaterEqual(len(blocks), 1)

        first = blocks[0]
        self.assertEqual(first.block_id, 0)
        self.assertEqual(first.transaction_type, "BUDGET_TOPUP")
        self.assertEqual(first.amount_cents, 10000)
        self.assertEqual(first.previous_hash, "0" * 64)
        self.assertEqual(first.hash, first.compute_hash())

    def test_ledger_sha256_hash_chain_validity(self):
        """Assert all transactions are linked via valid SHA-256 hashes."""
        eco = EcoFundManager(initial_budget_usd=50.0, tree_client=self.tree_client)
        eco.accumulate_waste(DEFAULT_THRESHOLD_BYTES, student_id="STU-001")
        eco.accumulate_waste(DEFAULT_THRESHOLD_BYTES, student_id="STU-002")

        valid, msg = eco.verify_chain()
        self.assertTrue(valid, msg)
        self.assertTrue(eco.verify_ledger_integrity())

    def test_tamper_detection_on_mutated_data_bytes(self):
        """Assert modifying data_bytes in an existing block causes verify_chain to fail."""
        eco = EcoFundManager(initial_budget_usd=50.0, tree_client=self.tree_client)
        eco.accumulate_waste(DEFAULT_THRESHOLD_BYTES)
        self.assertTrue(eco.verify_ledger_integrity())

        # Deliberately mutate data_bytes in block 1
        eco.ledger.blocks[1].data_bytes = 999999
        valid, msg = eco.verify_chain()
        self.assertFalse(valid)
        self.assertIn("Tamper detected at block 1", msg)

    def test_tamper_detection_on_mutated_amount_cents(self):
        """Assert modifying amount_cents in an existing block causes verify_chain to fail."""
        eco = EcoFundManager(initial_budget_usd=50.0, tree_client=self.tree_client)
        eco.accumulate_waste(DEFAULT_THRESHOLD_BYTES)
        self.assertTrue(eco.verify_ledger_integrity())

        # Deliberately mutate amount_cents in block 0
        eco.ledger.blocks[0].amount_cents = 99999999
        valid, msg = eco.verify_chain()
        self.assertFalse(valid)
        self.assertIn("Tamper detected at block 0", msg)

    def test_tamper_detection_on_corrupted_hash(self):
        """Assert modifying a block's hash string causes verify_chain to fail."""
        eco = EcoFundManager(initial_budget_usd=50.0, tree_client=self.tree_client)
        eco.accumulate_waste(DEFAULT_THRESHOLD_BYTES)
        self.assertTrue(eco.verify_ledger_integrity())

        # Mutate hash
        eco.ledger.blocks[-1].hash = "a" * 64
        valid, msg = eco.verify_chain()
        self.assertFalse(valid)

    def test_tamper_detection_on_broken_previous_hash_link(self):
        """Assert breaking previous_hash link between blocks causes verify_chain to fail."""
        eco = EcoFundManager(initial_budget_usd=50.0, tree_client=self.tree_client)
        eco.accumulate_waste(DEFAULT_THRESHOLD_BYTES)

        # Mutate previous_hash of block 1
        eco.ledger.blocks[1].previous_hash = "f" * 64
        valid, msg = eco.verify_chain()
        self.assertFalse(valid)
        self.assertIn("Previous hash broken", msg)

    # =========================================================================
    # 4. Persistence Tests (JSON & SQLite)
    # =========================================================================

    def test_json_ledger_persistence_roundtrip(self):
        """Assert ledger saves to JSON and reloads with 100% cryptographic integrity."""
        json_path = self.storage_dir / "test_ledger.json"
        ledger1 = AuditLedger(storage_path=json_path, initial_balance_cents=10000)
        ledger1.append_block(
            transaction_type="MICRO_DONATION",
            student_id="STU-001",
            data_bytes=DEFAULT_THRESHOLD_BYTES,
            amount_cents=150,
            description="Planted Mangrove",
        )
        self.assertTrue(ledger1.verify_ledger_integrity())

        # Reload in new instance from same JSON
        ledger2 = AuditLedger(storage_path=json_path)
        self.assertEqual(len(ledger2.blocks), len(ledger1.blocks))
        self.assertEqual(ledger2.get_last_hash(), ledger1.get_last_hash())
        self.assertTrue(ledger2.verify_ledger_integrity())

    def test_sqlite_ledger_persistence_roundtrip(self):
        """Assert ledger saves to SQLite and reloads with 100% cryptographic integrity."""
        db_path = self.storage_dir / "test_ledger.db"
        ledger1 = AuditLedger(storage_path=db_path, initial_balance_cents=25000)
        ledger1.append_block(
            transaction_type="MICRO_DONATION",
            student_id="STU-002",
            data_bytes=DEFAULT_THRESHOLD_BYTES,
            amount_cents=150,
            description="Planted Acacia",
        )
        self.assertTrue(ledger1.verify_ledger_integrity())

        # Reload in new instance from same SQLite DB
        ledger2 = AuditLedger(storage_path=db_path)
        self.assertEqual(len(ledger2.blocks), len(ledger1.blocks))
        self.assertEqual(ledger2.get_last_hash(), ledger1.get_last_hash())
        self.assertTrue(ledger2.verify_ledger_integrity())

    # =========================================================================
    # 5. Boundary & Edge Cases
    # =========================================================================

    def test_zero_byte_accumulation_no_change(self):
        """Assert accumulating 0 bytes does not change cumulative waste or plant trees."""
        eco = EcoFundManager(initial_budget_usd=50.0, tree_client=self.tree_client)
        res = eco.accumulate_waste(0)
        self.assertEqual(eco.cumulative_waste_bytes, 0)
        self.assertEqual(res["trees_triggered"], 0)

    def test_negative_byte_accumulation_raises_value_error(self):
        """Assert negative byte count raises ValueError."""
        eco = EcoFundManager(initial_budget_usd=50.0, tree_client=self.tree_client)
        with self.assertRaises(ValueError):
            eco.accumulate_waste(-1024)

    def test_exact_threshold_minus_one_byte_does_not_trigger(self):
        """Assert accumulating exactly 1 GB - 1 byte triggers 0 trees."""
        eco = EcoFundManager(initial_budget_usd=50.0, tree_client=self.tree_client)
        res = eco.accumulate_waste(DEFAULT_THRESHOLD_BYTES - 1)
        self.assertEqual(res["status"], "ACCUMULATING")
        self.assertEqual(res["trees_triggered"], 0)


if __name__ == "__main__":
    unittest.main()
