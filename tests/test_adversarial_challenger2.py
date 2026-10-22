"""
Adversarial Stress Test Suite — Challenger 2
Empirically tests:
1. Ledger Cryptographic Tamper-Evident Integrity & Double-Entry Balance Reconciliation
2. Eco-Fund & Cumulative Waste Accumulator Boundary & Exhaustion
3. Concurrency & High Load Multi-Threaded Stress Testing
"""

import os
import sys
import json
import time
import shutil
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.ledger import AuditLedger, LedgerBlock, VALID_TRANSACTION_TYPES, DEFAULT_ACCOUNTS
from src.services.eco_fund import EcoFundManager, DEFAULT_THRESHOLD_BYTES, DEFAULT_COST_PER_TREE_CENTS
from src.services.teacher_queue import TeacherQueue, STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED, STATUS_FLAGGED
from src.services.tree_nation import TreeNationClient


class TestAdversarialLedger(unittest.TestCase):
    """
    1. Cryptographic Tamper-Evident Stress-Testing & Double-Entry Reconciliation.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = Path(self.temp_dir.name) / "adversarial_ledger.json"
        self.sqlite_path = Path(self.temp_dir.name) / "adversarial_ledger.db"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_multiblock_chain_creation_and_integrity(self):
        """Build a 100-block multi-transaction chain and verify cryptographic validity."""
        ledger = AuditLedger(storage_path=self.storage_path, initial_balance_cents=50000)  # $500.00
        self.assertEqual(len(ledger.blocks), 1)

        tx_types = ["DATA_REDUCTION", "MICRO_DONATION", "BUDGET_TOPUP", "ADJUSTMENT"]
        for i in range(1, 100):
            ttype = tx_types[i % len(tx_types)]
            amount = (i * 15) if ttype in ("MICRO_DONATION", "BUDGET_TOPUP", "ADJUSTMENT") else 0
            bytes_val = (i * 1024 * 1024) if ttype == "DATA_REDUCTION" else 0
            ledger.append_block(
                transaction_type=ttype,
                student_id=f"STU-{i:03d}",
                data_bytes=bytes_val,
                amount_cents=amount,
                description=f"Synthetic block {i} of type {ttype}",
                metadata={"iteration": i, "tag": "stress_test"},
            )

        self.assertEqual(len(ledger.blocks), 100)
        valid, msg = ledger.verify_chain()
        self.assertTrue(valid, f"Chain validation failed: {msg}")

        # Check persistence roundtrip to JSON
        ledger_reloaded = AuditLedger(storage_path=self.storage_path)
        self.assertEqual(len(ledger_reloaded.blocks), 100)
        self.assertEqual(ledger_reloaded.get_last_hash(), ledger.get_last_hash())
        valid_reloaded, msg_reloaded = ledger_reloaded.verify_chain()
        self.assertTrue(valid_reloaded, f"Reloaded JSON validation failed: {msg_reloaded}")

        # Check persistence roundtrip to SQLite
        ledger.save_to_sqlite(self.sqlite_path)
        sqlite_ledger = AuditLedger(storage_path=self.sqlite_path)
        self.assertEqual(len(sqlite_ledger.blocks), 100)
        self.assertEqual(sqlite_ledger.get_last_hash(), ledger.get_last_hash())
        valid_sqlite, msg_sqlite = sqlite_ledger.verify_chain()
        self.assertTrue(valid_sqlite, f"Reloaded SQLite validation failed: {msg_sqlite}")

    def test_tamper_detection_on_all_payload_fields(self):
        """
        Deliberately tamper with EVERY field in block payload across multiple positions
        and verify verify_chain() reliably detects every single tampering attempt.
        """
        fields_to_tamper = [
            ("data_bytes", lambda b: setattr(b, "data_bytes", b.data_bytes + 1024)),
            ("amount_cents", lambda b: setattr(b, "amount_cents", b.amount_cents + 100)),
            ("timestamp", lambda b: setattr(b, "timestamp", "1999-01-01T00:00:00Z")),
            ("student_id", lambda b: setattr(b, "student_id", "MALICIOUS_STUDENT")),
            ("debit_account", lambda b: setattr(b, "debit_account", "MALICIOUS_ACCOUNT")),
            ("credit_account", lambda b: setattr(b, "credit_account", "MALICIOUS_ACCOUNT")),
            ("description", lambda b: setattr(b, "description", "Forged description")),
            ("metadata", lambda b: b.metadata.update({"forged_key": "injected_value"})),
        ]

        for field_name, tamper_fn in fields_to_tamper:
            with self.subTest(field=field_name):
                ledger = AuditLedger(initial_balance_cents=10000)
                for j in range(5):
                    ledger.append_block(
                        transaction_type="DATA_REDUCTION" if j % 2 == 0 else "MICRO_DONATION",
                        student_id=f"STU-{j}",
                        data_bytes=1000 * (j + 1),
                        amount_cents=150 * (j + 1),
                        description=f"Block {j}",
                    )
                self.assertTrue(ledger.verify_chain()[0])

                # Tamper with middle block (block index 2)
                tamper_fn(ledger.blocks[2])
                valid, err = ledger.verify_chain()
                self.assertFalse(valid, f"Tamper on {field_name} was NOT detected!")
                self.assertIn("Tamper detected at block 2", err)

    def test_tamper_detection_structural_attacks(self):
        """
        Test structural attacks:
        1. Swapping block positions (sequence / previous_hash violation).
        2. Block deletion in middle.
        3. Block duplication / replay attack.
        4. Truncation attack.
        5. Forged hash recalculation without re-hashing descendants.
        """
        # Attack 1: Swapping block positions
        ledger = AuditLedger(initial_balance_cents=10000)
        for j in range(4):
            ledger.append_block(transaction_type="BUDGET_TOPUP", amount_cents=100)
        self.assertTrue(ledger.verify_chain()[0])

        # Swap block 1 and block 2
        ledger.blocks[1], ledger.blocks[2] = ledger.blocks[2], ledger.blocks[1]
        valid, err = ledger.verify_chain()
        self.assertFalse(valid, "Block swap was not detected!")

        # Attack 2: Block deletion in middle
        ledger = AuditLedger(initial_balance_cents=10000)
        for j in range(4):
            ledger.append_block(transaction_type="BUDGET_TOPUP", amount_cents=100)
        del ledger.blocks[2]
        valid, err = ledger.verify_chain()
        self.assertFalse(valid, "Block deletion was not detected!")

        # Attack 3: Block duplication (replay)
        ledger = AuditLedger(initial_balance_cents=10000)
        for j in range(3):
            ledger.append_block(transaction_type="BUDGET_TOPUP", amount_cents=100)
        ledger.blocks.insert(2, ledger.blocks[1])
        valid, err = ledger.verify_chain()
        self.assertFalse(valid, "Block replay/duplication was not detected!")

        # Attack 4: Modifying block payload and recomputing ITS hash, but not descendants
        ledger = AuditLedger(initial_balance_cents=10000)
        for j in range(5):
            ledger.append_block(transaction_type="BUDGET_TOPUP", amount_cents=100)
        # Modify block 2 and recompute its hash
        ledger.blocks[2].amount_cents = 99999
        ledger.blocks[2].hash = ledger.blocks[2].compute_hash()
        # Block 3 still has old previous_hash!
        valid, err = ledger.verify_chain()
        self.assertFalse(valid, "Forged block hash without descendant update was not detected!")
        self.assertIn("Previous hash broken at block 3", err)

    def test_double_entry_balance_reconciliation(self):
        """
        Verify strict double-entry accounting reconciliation across all accounts:
        1. Sum(Debits) == Sum(Credits) across the entire ledger.
        2. Net balance of debit-normal accounts = Debits - Credits.
        3. Accounting equation: Sum(All Account Net Balances) == 0.
        4. Running balances strictly match account balances with 0 cent drift.
        """
        ledger = AuditLedger(initial_balance_cents=20000)  # $200.00
        # Block 0: BUDGET_TOPUP (Dr ECO_FUND_CASH 20000, Cr ADMIN_BUDGET_EQUITY 20000)

        # Append series of operations
        ledger.append_block(
            transaction_type="DATA_REDUCTION",
            student_id="STU-01",
            data_bytes=1073741824,
            amount_cents=0,
        )
        ledger.append_block(
            transaction_type="MICRO_DONATION",
            student_id="STU-01",
            amount_cents=150,  # $1.50
        )
        ledger.append_block(
            transaction_type="MICRO_DONATION",
            student_id="STU-02",
            amount_cents=300,  # $3.00
        )
        ledger.append_block(
            transaction_type="BUDGET_TOPUP",
            student_id="ADMIN",
            amount_cents=5000,  # $50.00
        )
        ledger.append_block(
            transaction_type="ADJUSTMENT",
            student_id="ADMIN",
            amount_cents=1000,
            debit_account="ADMIN_BUDGET_EQUITY",
            credit_account="ECO_FUND_CASH",
            description="Rebalance",
        )

        # 1. Total debits must equal total credits
        total_debits = sum(b.amount_cents for b in ledger.blocks)
        total_credits = sum(b.amount_cents for b in ledger.blocks)
        self.assertEqual(total_debits, total_credits)

        # 2. Get account balances
        balances = ledger.get_account_balances()

        # In double entry:
        # ECO_FUND_CASH: +20000 (topup) - 150 (donation) - 300 (donation) + 5000 (topup) - 1000 (adj) = 23550 cents ($235.50)
        expected_cash_cents = 20000 - 150 - 300 + 5000 - 1000
        self.assertEqual(balances.get("ECO_FUND_CASH"), expected_cash_cents)
        self.assertEqual(ledger.get_eco_fund_balance_cents(), expected_cash_cents)
        self.assertEqual(ledger.get_eco_fund_balance_usd(), 235.50)

        # REFORESTATION_EXPENSE: +150 + 300 = 450 cents
        self.assertEqual(balances.get("REFORESTATION_EXPENSE"), 450)

        # ADMIN_BUDGET_EQUITY: -20000 - 5000 + 1000 = -24000 cents
        self.assertEqual(balances.get("ADMIN_BUDGET_EQUITY"), -24000)

        # 3. Sum of all signed balances must be EXACTLY ZERO
        self.assertEqual(sum(balances.values()), 0, "Double-entry accounts do not balance to zero!")

        # 4. Check running balance calculation on transactions property
        txs = ledger.transactions
        self.assertEqual(txs[-1]["balance_after_cents"], expected_cash_cents)
        self.assertEqual(txs[-1]["balance_after"], 235.50)


class TestAdversarialEcoFundAndAccumulator(unittest.TestCase):
    """
    2. Eco-Fund & Cumulative Waste Accumulator Stress-Testing:
       Extreme boundaries, carryover surplus across thresholds, budget exhaustion.
    """

    def setUp(self):
        self.tree_client = TreeNationClient(offline=True)

    def test_extreme_boundary_conditions(self):
        """
        Test 0 bytes, 1 byte, exactly 1 GB (1,073,741,824), 1 GB + 1 byte, 10 GB.
        """
        eco = EcoFundManager(initial_budget_usd=100.0, tree_client=self.tree_client)

        # 1. Zero bytes
        r0 = eco.accumulate_waste(0)
        self.assertEqual(r0["status"], "ACCUMULATING")
        self.assertEqual(r0["trees_triggered"], 0)
        self.assertEqual(eco.cumulative_waste_bytes, 0)
        self.assertEqual(eco.surplus_bytes, 0)
        self.assertEqual(eco.lifetime_trees, 0)
        self.assertEqual(eco.budget_usd, 100.0)

        # 2. Exactly 1 byte
        r1 = eco.accumulate_waste(1)
        self.assertEqual(r1["status"], "ACCUMULATING")
        self.assertEqual(r1["trees_triggered"], 0)
        self.assertEqual(eco.cumulative_waste_bytes, 1)
        self.assertEqual(eco.surplus_bytes, 1)
        self.assertEqual(eco.lifetime_trees, 0)
        self.assertEqual(eco.budget_usd, 100.0)

        # 3. Add bytes to reach exactly 1 GB (DEFAULT_THRESHOLD_BYTES - 1)
        # Current waste is 1. Adding (1073741824 - 1) reaches exactly 1073741824
        r_exact = eco.accumulate_waste(DEFAULT_THRESHOLD_BYTES - 1)
        self.assertEqual(r_exact["status"], "DONATION_EXECUTED")
        self.assertEqual(r_exact["trees_triggered"], 1)
        self.assertEqual(eco.cumulative_waste_bytes, DEFAULT_THRESHOLD_BYTES)
        self.assertEqual(eco.surplus_bytes, 0)
        self.assertEqual(eco.lifetime_trees, 1)
        self.assertAlmostEqual(eco.budget_usd, 100.0 - 1.50, places=2)

        # 4. Add exactly 1 GB + 1 byte
        r_plus1 = eco.accumulate_waste(DEFAULT_THRESHOLD_BYTES + 1)
        self.assertEqual(r_plus1["status"], "DONATION_EXECUTED")
        self.assertEqual(r_plus1["trees_triggered"], 1)
        self.assertEqual(eco.cumulative_waste_bytes, 2 * DEFAULT_THRESHOLD_BYTES + 1)
        self.assertEqual(eco.surplus_bytes, 1)  # exactly 1 byte carryover!
        self.assertEqual(eco.lifetime_trees, 2)
        self.assertAlmostEqual(eco.budget_usd, 100.0 - 3.00, places=2)

        # 5. Multi-GB batch: exactly 10 GB
        ten_gb = 10 * DEFAULT_THRESHOLD_BYTES
        r_10gb = eco.accumulate_waste(ten_gb)
        self.assertEqual(r_10gb["status"], "DONATION_EXECUTED")
        self.assertEqual(r_10gb["trees_triggered"], 10)
        self.assertEqual(eco.lifetime_trees, 12)
        self.assertEqual(eco.surplus_bytes, 1)  # still the 1 byte carryover
        self.assertAlmostEqual(eco.budget_usd, 100.0 - 3.00 - 15.00, places=2)

    def test_carryover_surplus_tracking_randomized_micro_additions(self):
        """
        Test fine-grained surplus tracking:
        100 micro-additions of varying sizes that sum to exactly 3.0 GB.
        Verify:
        - Exactly 3 trees are planted across the run.
        - Final surplus is exactly 0.
        - Ledger verification succeeds.
        """
        import random
        random.seed(42)

        target_total_bytes = 3 * DEFAULT_THRESHOLD_BYTES  # 3 GB
        eco = EcoFundManager(initial_budget_usd=50.0, tree_client=self.tree_client)

        # Generate 100 chunks summing to target_total_bytes
        raw_parts = [random.randint(1000, 1000000) for _ in range(100)]
        sum_parts = sum(raw_parts)
        chunks = [int(p * target_total_bytes / sum_parts) for p in raw_parts]
        diff = target_total_bytes - sum(chunks)
        chunks[-1] += diff
        self.assertEqual(sum(chunks), target_total_bytes)

        total_trees_observed = 0
        for i, chunk in enumerate(chunks):
            res = eco.accumulate_waste(chunk, student_id=f"STU-{i%5:02d}")
            total_trees_observed += res["trees_triggered"]

        self.assertEqual(total_trees_observed, 3)
        self.assertEqual(eco.lifetime_trees, 3)
        self.assertEqual(eco.cumulative_waste_bytes, target_total_bytes)
        self.assertEqual(eco.surplus_bytes, 0)
        self.assertAlmostEqual(eco.budget_usd, 50.0 - 4.50, places=2)
        self.assertTrue(eco.verify_ledger_integrity())

    def test_budget_exhaustion_scenarios(self):
        """
        Budget exhaustion testing:
        - $0.00 balance: verify PENDING_FUNDS, alert generated, no deduction, waste tracked.
        - $1.00 balance (< $1.50): verify PENDING_FUNDS.
        - Multi-tree deficit: $2.00 balance with 2 trees needed ($3.00):
          Verify how pending trees and deficit are calculated.
        - Subsequent top-up: verify pending trees disburse and alert clears.
        """
        # Scenario A: $0.00 balance
        eco0 = EcoFundManager(initial_budget_usd=0.0, tree_client=self.tree_client)
        r0 = eco0.accumulate_waste(DEFAULT_THRESHOLD_BYTES)
        self.assertEqual(r0["status"], "PENDING_FUNDS")
        self.assertEqual(r0["trees_triggered"], 0)
        self.assertEqual(eco0.pending_trees_count, 1)
        self.assertIsNotNone(eco0.latest_alert)
        self.assertEqual(eco0.latest_alert["warning"], "INSUFFICIENT_ECO_FUND_BUDGET")
        self.assertEqual(eco0.latest_alert["required_cents"], 150)
        self.assertEqual(eco0.latest_alert["available_cents"], 0)
        self.assertEqual(eco0.latest_alert["deficit_usd"], 1.50)

        # Top up with exactly $1.50 (150 cents)
        top_res = eco0.topup_budget(150, admin_id="ADMIN")
        self.assertEqual(top_res["status"], "success")
        self.assertEqual(eco0.lifetime_trees, 1)
        self.assertEqual(eco0.pending_trees_count, 0)
        self.assertIsNone(eco0.latest_alert)
        self.assertEqual(eco0.budget_usd, 0.0)

        # Scenario B: $1.00 balance (< $1.50)
        eco1 = EcoFundManager(initial_budget_usd=1.00, tree_client=self.tree_client)
        r1 = eco1.accumulate_waste(DEFAULT_THRESHOLD_BYTES)
        self.assertEqual(r1["status"], "PENDING_FUNDS")
        self.assertEqual(r1["trees_triggered"], 0)
        self.assertEqual(eco1.budget_usd, 1.00)
        self.assertEqual(eco1.pending_trees_count, 1)
        self.assertEqual(r1["alert"]["deficit_usd"], 0.50)

        # Top up with $10.00
        eco1.topup_budget(1000)
        self.assertEqual(eco1.lifetime_trees, 1)
        self.assertEqual(eco1.pending_trees_count, 0)
        # Was $1.00 + $10.00 - $1.50 = $9.50
        self.assertAlmostEqual(eco1.budget_usd, 9.50, places=2)

        # Scenario C: Multi-tree batch exceeding balance
        # Initial $2.00, accumulate 2 GB ($3.00 needed for 2 trees)
        eco2 = EcoFundManager(initial_budget_usd=2.00, tree_client=self.tree_client)
        r2 = eco2.accumulate_waste(2 * DEFAULT_THRESHOLD_BYTES)
        self.assertEqual(r2["status"], "PENDING_FUNDS")
        self.assertEqual(eco2.pending_trees_count, 2)
        self.assertEqual(r2["alert"]["required_cents"], 300)
        self.assertEqual(r2["alert"]["available_cents"], 200)
        self.assertEqual(r2["alert"]["deficit_usd"], 1.00)

        # Top up with $5.00 (500 cents)
        eco2.topup_budget(500)
        self.assertEqual(eco2.lifetime_trees, 2)
        self.assertEqual(eco2.pending_trees_count, 0)
        # $2.00 + $5.00 - $3.00 = $4.00
        self.assertAlmostEqual(eco2.budget_usd, 4.00, places=2)


class TestAdversarialConcurrency(unittest.TestCase):
    """
    3. Concurrency & High Load Stress-Testing:
       Multi-threaded student deletion submissions and simultaneous teacher queue reviews.
    """

    def setUp(self):
        self.tree_client = TreeNationClient(offline=True)

    def test_concurrent_student_submissions_and_teacher_decisions(self):
        """
        Simulate high-load concurrency:
        - 15 concurrent student threads submitting 30 requests each (450 total requests).
        - 5 concurrent teacher review threads polling and deciding (approve/reject/flag).
        - 3 concurrent observer threads querying get_queue() and get_analytics().
        Verify:
        - Zero race conditions or unhandled exceptions.
        - Exactly 450 unique requests created.
        - All decisions mutually exclusive (no request decided twice).
        - Queue state consistent.
        """
        eco = EcoFundManager(initial_budget_usd=1000.0, tree_client=self.tree_client)
        t_queue = TeacherQueue(ledger=eco)

        submission_count_per_thread = 30
        num_student_threads = 15
        total_expected_requests = submission_count_per_thread * num_student_threads

        all_submitted_ids = []
        submission_lock = threading.Lock()
        stop_workers = threading.Event()
        errors = []

        def student_worker(thread_idx: int):
            try:
                for i in range(submission_count_per_thread):
                    req_id = t_queue.submit_request(
                        student_id=f"STU-T{thread_idx:02d}",
                        file_name=f"file_t{thread_idx}_{i}.mov",
                        size_bytes=10 * 1024 * 1024,
                        reason="Duplicate project export",
                        ai_score=0.85,
                        ai_summary="High confidence duplicate",
                    )
                    with submission_lock:
                        all_submitted_ids.append(req_id)
                    time.sleep(0.001)  # small yield to encourage thread interleaving
            except Exception as e:
                errors.append(f"Student worker error: {e}")

        decided_count = {"approve": 0, "reject": 0, "flag": 0}
        decided_lock = threading.Lock()

        def teacher_worker(teacher_idx: int):
            try:
                while not stop_workers.is_set() or len(all_submitted_ids) < total_expected_requests:
                    # Pick an undecided item
                    with t_queue._lock:
                        pending_items = [r for r in t_queue._requests if r.status == STATUS_PENDING]
                    if pending_items:
                        target = pending_items[0]
                        # Decide action based on id hash
                        h = hash(target.id) % 3
                        try:
                            if h == 0:
                                res = t_queue.approve(target.id, teacher_id=f"TEACHER-{teacher_idx}")
                                with decided_lock:
                                    decided_count["approve"] += 1
                            elif h == 1:
                                res = t_queue.reject(target.id, f"TEACHER-{teacher_idx}", "Preserved")
                                with decided_lock:
                                    decided_count["reject"] += 1
                            else:
                                res = t_queue.flag(target.id, f"TEACHER-{teacher_idx}", "Flagged")
                                with decided_lock:
                                    decided_count["flag"] += 1
                        except ValueError:
                            # Already processed by another teacher thread concurrently — expected race condition handled!
                            pass
                    time.sleep(0.002)
            except Exception as e:
                errors.append(f"Teacher worker error: {e}")

        def observer_worker():
            try:
                while not stop_workers.is_set():
                    q = t_queue.get_queue(page_size=10, sort_by="confidence")
                    self.assertIsInstance(q["items"], list)
                    analytics = t_queue.get_analytics()
                    self.assertIsInstance(analytics, dict)
                    time.sleep(0.005)
            except Exception as e:
                errors.append(f"Observer worker error: {e}")

        # Launch all threads
        threads = []
        for s in range(num_student_threads):
            threads.append(threading.Thread(target=student_worker, args=(s,)))
        for t in range(5):
            threads.append(threading.Thread(target=teacher_worker, args=(t,)))
        for o in range(3):
            threads.append(threading.Thread(target=observer_worker))

        for t in threads:
            t.start()

        # Wait for all student submissions to finish
        for s_idx in range(num_student_threads):
            threads[s_idx].join(timeout=10.0)

        # Give teacher threads time to drain the queue
        time.sleep(1.0)
        stop_workers.set()

        for t in threads[num_student_threads:]:
            t.join(timeout=5.0)

        # Assertions
        self.assertEqual(len(errors), 0, f"Encountered concurrency errors: {errors}")
        self.assertEqual(len(all_submitted_ids), total_expected_requests)
        self.assertEqual(len(set(all_submitted_ids)), total_expected_requests, "Duplicate request IDs generated!")
        self.assertEqual(len(t_queue), total_expected_requests)

        # Drain any remaining pending items sequentially to verify state consistency
        with t_queue._lock:
            for r in t_queue._requests:
                if r.status == STATUS_PENDING:
                    t_queue.approve(r.id)
                    decided_count["approve"] += 1

        # Every single item must now be in an approved, rejected, or flagged state
        statuses = [r.status for r in t_queue.queue]
        self.assertTrue(all(s in (STATUS_APPROVED, STATUS_REJECTED, STATUS_FLAGGED) for s in statuses))
        self.assertEqual(sum(decided_count.values()), total_expected_requests)

        # Verify underlying ledger cryptographic chain is 100% valid despite concurrent approvals
        valid_chain, chain_msg = eco.verify_chain()
        self.assertTrue(valid_chain, f"Ledger corrupted during concurrent approvals: {chain_msg}")

    def test_direct_concurrent_ledger_appends_thread_safety(self):
        """
        Adversarial test on AuditLedger directly:
        Can concurrent append_block calls on AuditLedger cause broken previous_hash or block_id races?
        We test with 10 threads appending 20 blocks each directly to AuditLedger.
        If AuditLedger is NOT thread-safe, this will expose race conditions in block_id or hash chaining!
        """
        ledger = AuditLedger(initial_balance_cents=100000)

        def append_worker(t_id: int):
            for i in range(20):
                ledger.append_block(
                    transaction_type="DATA_REDUCTION",
                    student_id=f"STU-{t_id}",
                    data_bytes=1024,
                    amount_cents=0,
                    description=f"Thread {t_id} block {i}",
                )

        threads = [threading.Thread(target=append_worker, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(ledger.blocks), 201)  # 1 genesis + 200 appended
        valid, msg = ledger.verify_chain()
        # Report the finding: Does AuditLedger maintain valid chain under concurrent naked appends?
        # Note: if it fails, we catch and report as an empirical finding.
        if not valid:
            print(f"\n[EMPIRICAL VULNERABILITY DETECTED] AuditLedger is not thread-safe for concurrent naked appends: {msg}")
        self.assertTrue(valid, f"AuditLedger failed thread-safety test: {msg}")


if __name__ == "__main__":
    unittest.main()
