#!/usr/bin/env python3
"""
Master E2E Test Suite Runner for Data-to-Dirt
Executes all 4 tiers of tests (345+ test cases) across all 30 features (F-01 through F-30).

Usage:
    python3 tests/e2e/run_all_e2e.py
    python3 tests/e2e/run_all_e2e.py --tier 1
    python3 tests/e2e/run_all_e2e.py --json
    python3 tests/e2e/run_all_e2e.py --verbose

Exit Codes:
    0 = All executed tests passed.
    1 = One or more tests failed or encountered errors.
"""

import unittest
import sys
import os
import time
import json
import argparse
from typing import Dict, List, Any

# Ensure project root is in path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.e2e.test_tier1_features import TestTier1FeatureCoverage
from tests.e2e.test_tier2_boundaries import TestTier2Boundaries
from tests.e2e.test_tier3_pairwise import TestTier3PairwiseInteractions
from tests.e2e.test_tier4_scenarios import TestTier4Scenarios


class StructuredTestResult(unittest.TestResult):
    def __init__(self, stream=None, descriptions=None, verbosity=1):
        super().__init__(stream, descriptions, verbosity)
        self.successes: List[Any] = []
        self.test_records: List[Dict[str, Any]] = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.successes.append(test)
        self.test_records.append({
            "test_id": test.id(),
            "name": test._testMethodName,
            "doc": test.shortDescription() or "",
            "status": "PASSED",
            "error": None
        })

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.test_records.append({
            "test_id": test.id(),
            "name": test._testMethodName,
            "doc": test.shortDescription() or "",
            "status": "FAILED",
            "error": self._exc_info_to_string(err, test)
        })

    def addError(self, test, err):
        super().addError(test, err)
        self.test_records.append({
            "test_id": test.id(),
            "name": test._testMethodName,
            "doc": test.shortDescription() or "",
            "status": "ERROR",
            "error": self._exc_info_to_string(err, test)
        })

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.test_records.append({
            "test_id": test.id(),
            "name": test._testMethodName,
            "doc": test.shortDescription() or "",
            "status": "SKIPPED",
            "error": reason
        })


def run_tier(suite_class, tier_name: str, verbose: bool = False) -> Dict[str, Any]:
    suite = unittest.TestLoader().loadTestsFromTestCase(suite_class)
    result = StructuredTestResult()
    start_time = time.time()
    suite.run(result)
    elapsed = time.time() - start_time

    return {
        "tier_name": tier_name,
        "total": suite.countTestCases(),
        "passed": len(result.successes),
        "failed": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "elapsed_seconds": round(elapsed, 3),
        "records": result.test_records
    }


def main():
    parser = argparse.ArgumentParser(description="Data-to-Dirt Master E2E Test Suite Runner")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4], help="Run only specified tier")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--verbose", action="store_true", help="Verbose test execution logs")
    args = parser.parse_args()

    tiers_to_run = []
    if args.tier is None or args.tier == 1:
        tiers_to_run.append((TestTier1FeatureCoverage, "Tier 1: Feature Coverage (F-01..F-30)"))
    if args.tier is None or args.tier == 2:
        tiers_to_run.append((TestTier2Boundaries, "Tier 2: Boundary & Corner Cases (F-01..F-30)"))
    if args.tier is None or args.tier == 3:
        tiers_to_run.append((TestTier3PairwiseInteractions, "Tier 3: Cross-Feature Interactions"))
    if args.tier is None or args.tier == 4:
        tiers_to_run.append((TestTier4Scenarios, "Tier 4: Real-World End-to-End Scenarios"))

    if not args.json:
        print("======================================================================")
        print("             DATA-TO-DIRT — MASTER E2E TEST SUITE RUNNER              ")
        print("======================================================================")
        print(f"Project Directory : {PROJECT_ROOT}")
        print(f"Test Directory    : {os.path.dirname(__file__)}")
        print(f"Execution Target  : All Active Tiers (150 T1 + 150 T2 + 30 T3 + 15 T4 = 345 Tests)")
        print("======================================================================\n")

    overall_start = time.time()
    tier_results = []
    all_passed = True

    for suite_class, tier_name in tiers_to_run:
        if not args.json:
            print(f"[*] Running {tier_name} ...", end="", flush=True)
        res = run_tier(suite_class, tier_name, args.verbose)
        tier_results.append(res)
        if res["failed"] > 0 or res["errors"] > 0:
            all_passed = False
        if not args.json:
            status_str = "PASS" if (res["failed"] == 0 and res["errors"] == 0) else "FAIL"
            print(f" [{status_str}] ({res['passed']}/{res['total']} passed in {res['elapsed_seconds']}s)")

    overall_elapsed = time.time() - overall_start

    total_tests = sum(r["total"] for r in tier_results)
    total_passed = sum(r["passed"] for r in tier_results)
    total_failed = sum(r["failed"] for r in tier_results)
    total_errors = sum(r["errors"] for r in tier_results)
    total_skipped = sum(r["skipped"] for r in tier_results)

    summary_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_tests": total_tests,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "total_errors": total_errors,
        "total_skipped": total_skipped,
        "overall_status": "PASSED" if all_passed else "FAILED",
        "duration_seconds": round(overall_elapsed, 3),
        "tiers": tier_results
    }

    # Write test_results.json artifact
    results_path = os.path.join(os.path.dirname(__file__), "test_results.json")
    with open(results_path, "w") as f:
        json.dump(summary_data, f, indent=2)

    if args.json:
        print(json.dumps(summary_data, indent=2))
    else:
        print("\n======================================================================")
        print("                         TEST EXECUTION SUMMARY                       ")
        print("======================================================================")
        print(f"{'Tier Name':<45} | {'Total':<6} | {'Pass':<6} | {'Fail':<6} | {'Time'}")
        print("-" * 72)
        for r in tier_results:
            print(f"{r['tier_name']:<45} | {r['total']:<6} | {r['passed']:<6} | {r['failed']:<6} | {r['elapsed_seconds']}s")
        print("-" * 72)
        print(f"{'TOTALS':<45} | {total_tests:<6} | {total_passed:<6} | {total_failed:<6} | {round(overall_elapsed, 2)}s")
        print("======================================================================")
        if all_passed:
            print(f"[✓] SUCCESS: All {total_tests} E2E tests across 4 tiers PASSED cleanly (Exit code 0).")
        else:
            print(f"[✗] FAILURE: {total_failed + total_errors} tests failed out of {total_tests}.")
        print(f"Detailed JSON Report: {results_path}\n")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
