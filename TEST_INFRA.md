# Data-to-Dirt — Test Infrastructure & E2E Testing Architecture (TEST_INFRA.md)

**Document Reference**: `D2D-TEST-INFRA-V1`  
**Identity**: `teamwork_preview_test_writer` (E2E Testing Track Lead)  
**Authoritative Request**: `/Users/narayan/Desktop/Singapore Comp/ORIGINAL_REQUEST.md`  
**Project Directory**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt`  
**Date**: 2026-09-05  
**Version**: 1.0.0 — Production Specification  

---

## 1. Test Philosophy & Guiding Principles

The Data-to-Dirt End-to-End (E2E) Test Suite validates that the desktop application satisfies all functional, ecological, gamification, and security requirements laid out in the authoritative specification (`ORIGINAL_REQUEST.md`).

### 1.1 Core Principles
1. **Opaque-Box & Requirement-Driven**: Tests are derived strictly from specifications and interface contracts, treating components as opaque entities. Tests evaluate inputs, outputs, side effects (disk modifications, ledger transactions), and state transitions rather than private internal implementation details.
2. **Zero Facade & Anti-Cheating Invariant**: No test shall be constructed to unconditionally pass or bypass actual evaluation logic. All assertions verify real mathematical formulations, cryptographic hash chains, filesystem operations, neural network outputs, and data persistence.
3. **Airgap & Zero-Download Guarantee**: The test suite executes 100% offline without external network ingress or egress. Tests run seamlessly in corporate or airgapped environments without calling external package registries or remote APIs.
4. **Isolated & Idempotent Sandboxing**: Every test creates its own isolated sandbox environment (`tempfile.TemporaryDirectory`) for local filesystem scanning, deletions, and ledger writes. Tests never pollute the developer's home directory or persistent project files, and execute deterministically regardless of run order.
5. **Progressive Testability**: During milestone-based development, the test runner gracefully detects module availability, verifying implemented milestone targets while reporting pending components cleanly in baseline reports.

---

## 2. Feature Inventory Matrix (30 Features Across R1–R5)

The application architecture comprises 30 primary features organized across Requirements R1 through R5:

| Feature ID | Category | Feature Name | Core Requirement & Authoritative Contract | Target Service / Module | Tier 1 Tests | Tier 2 Tests |
|---|---|---|---|---|---|---|
| **F-01** | R1: Dashboard | Stored Carbon Calculation | $E = \text{GB} \times 0.28\,\text{kWh/GB/yr}$; $\text{CO}_2\text{e} = E \times 405.7\,\text{g/kWh}$. Avoided carbon for deleted bytes. | `services.carbon_calculator` | T1-F01-01..05 | T2-F01-01..05 |
| **F-02** | R1: Dashboard | Real-Time Footprint Counter | Dynamic footprint state updates upon scanning, staging, and deleting files. | `services.carbon_calculator`, `app.server` | T1-F02-01..05 | T2-F02-01..05 |
| **F-03** | R1: Dashboard | Student Leaderboard | Ranked entries by eco-score; tie-breaking by streak; minimum 3 test entries. | `services.gamification` | T1-F03-01..05 | T2-F03-01..05 |
| **F-04** | R1: Dashboard | Daily Deletion Streak Counter | Increments on consecutive UTC daily deletions; freezes/resets on missed days. | `services.gamification` | T1-F04-01..05 | T2-F04-01..05 |
| **F-05** | R1: Dashboard | Daily Deletion Limit | Enforces configurable maximum daily deletion count/size per student. | `services.gamification` | T1-F05-01..05 | T2-F05-01..05 |
| **F-06** | R1: Dashboard | Retro Growing Tree Visual State | 5 discrete growth stages (Soil, Sprout, Sapling, Young Oak, Ancient/Golden Tree). | `services.gamification`, `ui/tree.js` | T1-F06-01..05 | T2-F06-01..05 |
| **F-07** | R1: Dashboard | 60fps Particle System Feedback | Emitter parameters for data shards, eco-sparkles, and celebration confetti. | `ui/particles.js`, `app.server` | T1-F07-01..05 | T2-F07-01..05 |
| **F-08** | R1: Dashboard | Chiptune Sound Synthesizer | Web Audio procedural audio cues (`BLIP`, `DING`, `POOF`, `FANFARE`, `BUZZER`). | `ui/audio.js`, `app.server` | T1-F08-01..05 | T2-F08-01..05 |
| **F-09** | R1: Dashboard | Dark Data Review Carousel | Random sampling and prioritized presentation of stale/heavy files. | `services.scanner`, `services.gamification` | T1-F09-01..05 | T2-F09-01..05 |
| **F-10** | R2: Privacy | Blind Initial State Machine | Zero filesystem handles or cached paths on boot prior to explicit user grant. | `services.scanner` | T1-F10-01..05 | T2-F10-01..05 |
| **F-11** | R2: Privacy | Explicit Permission Modal | Temporary revocable access modal (Session-only vs persistent grant). | `services.scanner`, `app.server` | T1-F11-01..05 | T2-F11-01..05 |
| **F-12** | R2: Privacy | Instant Revocation & Memory Purge | Revoking access immediately closes descriptors, clears memory vectors, resets UI. | `services.scanner` | T1-F12-01..05 | T2-F12-01..05 |
| **F-13** | R2: Privacy | Recursive Metadata Traversal | Extracts file name, size, extension, modified/accessed timestamps via `stat`. | `services.scanner` | T1-F13-01..05 | T2-F13-01..05 |
| **F-14** | R2: Privacy | Dark Data Heuristic Indexer | Flags stale (>180d), large media (>500MB), duplicates, and temporary trash. | `services.scanner` | T1-F14-01..05 | T2-F14-01..05 |
| **F-15** | R2: Privacy | Manual Confidential File Marking | Marked files tagged `is_confidential=True`, completely excluded from deletion pool. | `services.scanner` | T1-F15-01..05 | T2-F15-01..05 |
| **F-16** | R2: Privacy | Confidential Pattern Auto-Skip | Skips `.env`, `*id_rsa*`, `*password*`, `.data_to_dirt_ignore` automatically. | `services.scanner` | T1-F16-01..05 | T2-F16-01..05 |
| **F-17** | R2: Privacy | PII Text Preview Redaction | Deterministic regex scrubber for emails, phone numbers, cards, and API keys. | `services.scanner` | T1-F17-01..05 | T2-F17-01..05 |
| **F-18** | R2: Privacy | Image Thumbnail Pixelation | Visual assets downsampled to $16\times16$ blocks with manual reveal trigger. | `services.scanner`, `ui/views` | T1-F18-01..05 | T2-F18-01..05 |
| **F-19** | R2: Privacy | Cloud Storage Provider Interface | Common abstraction `ICloudStorageProvider` for Drive, OneDrive, Dropbox, Mock. | `services.cloud_storage` | T1-F19-01..05 | T2-F19-01..05 |
| **F-20** | R2: Privacy | High-Fidelity Mock Cloud Sandbox | Deterministic offline cloud drive with realistic hierarchy, quota, soft trash. | `services.cloud_storage` | T1-F20-01..05 | T2-F20-01..05 |
| **F-21** | R3: AI Accountability | Custom Offline Neural Network | Pure NumPy/C++ forward pass, sub-5ms CPU latency, zero external API calls. | `ai.model`, `ai.nn_engine` | T1-F21-01..05 | T2-F21-01..05 |
| **F-22** | R3: AI Accountability | Lightweight Subword Tokenizer | 1024-token vocabulary, deterministic tokenization of reason and filename. | `ai.tokenizer` | T1-F22-01..05 | T2-F22-01..05 |
| **F-23** | R3: AI Accountability | Confidence Scoring Engine | Calibrated probability $S$: Plausible reasons $\ge 0.5$, gaming reasons $< 0.5$. | `ai.model` | T1-F23-01..05 | T2-F23-01..05 |
| **F-24** | R3: AI Accountability | AI Evaluation Summary Generator | Generates concise human-readable summaries combining score and file metadata. | `ai.model` | T1-F24-01..05 | T2-F24-01..05 |
| **F-25** | R3: AI Accountability | Anti-Gaming 3-Strike Penalty Loop | Progressive penalty enforcement: Warning -> Streak Freeze -> Reset & Flags. | `services.gamification`, `ai.model` | T1-F25-01..05 | T2-F25-01..05 |
| **F-26** | R4: Teacher View | Role-Based Access Control (RBAC) | Secure role switching between Student and Teacher/Admin views via PIN. | `services.auth` | T1-F26-01..05 | T2-F26-01..05 |
| **F-27** | R4: Teacher View | Teacher Confirmation Queue | Central queue showing pending deletions with AI confidence badges & summaries. | `services.teacher_queue` | T1-F27-01..05 | T2-F27-01..05 |
| **F-28** | R4: Teacher View | Tri-State Deletion Decisioning | Actions: Approve (delete & credit), Reject (preserve & note), Flag (discipline). | `services.teacher_queue` | T1-F28-01..05 | T2-F28-01..05 |
| **F-29** | R4: Teacher View | Admin Eco-Fund Budget Controller | Pre-allocates fund, tracks storage savings ROI, enforces available balance. | `services.eco_fund` | T1-F29-01..05 | T2-F29-01..05 |
| **F-30** | R5: Eco-Fund | Cumulative Waste Accumulator & Threshold | Tracks approved bytes toward 1 GB ($1,073,741,824$ bytes) donation trigger. | `services.tree_nation`, `services.eco_fund` | T1-F30-01..05 | T2-F30-01..05 |

---

## 3. Four-Tier Test Suite Architecture

```
                                  +-------------------------------------------------------------+
                                  |              Tier 4: Real-World Scenarios                   |
                                  |        (15 End-to-End Complete User Workflows)              |
                                  +------------------------------+------------------------------+
                                                                 |
                                  +------------------------------v------------------------------+
                                  |         Tier 3: Cross-Feature Interactions                  |
                                  |       (30 Multi-Module Pairwise Integration Tests)          |
                                  +------------------------------+------------------------------+
                                                                 |
                                  +------------------------------v------------------------------+
                                  |          Tier 2: Boundary & Corner Cases                    |
                                  |  (150 Edge, Limit, Stress, Corruption & Exception Tests)   |
                                  +------------------------------+------------------------------+
                                                                 |
                                  +------------------------------v------------------------------+
                                  |             Tier 1: Feature Coverage                        |
                                  |   (150 Independent Unit & Integration Feature Tests)        |
                                  +-------------------------------------------------------------+
```

### 3.1 Tier 1: Feature Coverage (>= 150 Tests)
- **Objective**: 5 dedicated test cases for each of the 30 features ($30 \times 5 = 150$ tests).
- **Scope**: Exercises the primary happy-path behavior, standard state mutations, and contract compliance for every feature in isolation.
- **Test File**: `tests/e2e/test_tier1_features.py`

### 3.2 Tier 2: Boundary & Corner Cases (>= 150 Tests)
- **Objective**: 5 dedicated edge/stress/boundary test cases for each of the 30 features ($30 \times 5 = 150$ tests).
- **Scope**:
  - Empty directories, deeply nested paths (15+ levels), zero-byte files, massive 100 GB sparse files.
  - Non-ASCII/Unicode paths, path traversal attempts (`../../etc/passwd`), unreadable permissions (`000`).
  - Symlink loop recursion prevention.
  - Streak edge transitions across midnight UTC, leap years, daylight saving time shifts.
  - Zero-balance and negative-balance Eco-Fund handling.
  - Tokenizer boundary inputs: 10,000 character strings, special format meta-characters, pure whitespace.
  - Extreme neural network inputs (0-byte file, 10-year age, unknown extensions).
- **Test File**: `tests/e2e/test_tier2_boundaries.py`

### 3.3 Tier 3: Cross-Feature Interactions (>= 30 Tests)
- **Objective**: 30 pairwise and multi-module interaction test cases ($30$ tests).
- **Scope**:
  - Scanning + Confidentiality Tagging + Deletion Queue filtering.
  - AI Confidence Evaluation + Anti-Gaming Strike Accrual + Leaderboard Deduction.
  - Teacher Queue Approval + Cumulative Waste Accumulator + 1 GB Threshold Trigger.
  - Threshold Trigger + Reforestation API Call + Eco-Fund Ledger SHA-256 Chaining.
  - Teacher Rejection + Student Feedback Notification + File Disk Preservation.
  - Cloud Storage Mock Deletion + Local Tree Growth Animation Event Dispatch.
- **Test File**: `tests/e2e/test_tier3_pairwise.py`

### 3.4 Tier 4: Real-World Application Scenarios (>= 15 Tests)
- **Objective**: 15 complete, end-to-end multi-step realistic user stories ($15$ tests).
- **Scope**:
  1. *Scenario 1*: Student semester-end cleanup (scans folder, marks confidential files, verifies 3 candidates with AI, queues for teacher).
  2. *Scenario 2*: Teacher morning review workflow (reviews 5 requests, approves 3, rejects 1 with feedback, flags 1 gaming attempt).
  3. *Scenario 3*: Threshold crossing & Tree-Nation micro-donation (cumulative waste crosses 1 GB, triggers tree planting, verifies synthetic certificate and ledger).
  4. *Scenario 4*: Gaming attack escalation (student submits repeated low-effort justifications, triggers strikes 1, 2, 3, streak resets to 0, teacher alerted).
  5. *Scenario 5*: Eco-Fund budget depletion & recovery (fund drops to $0, enters pledge mode, admin injects $50 savings, pending trees disburse).
  6. *Scenario 6*: Cloud storage Google Drive synchronization & soft-trash recycling.
  7. *Scenario 7*: Confidential file defense (user marks sensitive tax file confidential, attempts API deletion, assert hard rejection).
  8. *Scenario 8*: PII scrubbing on mixed documentation (emails, phone numbers, and API tokens scrubbed from student preview).
  9. *Scenario 9*: Daily deletion rate limiting (student deletes up to daily cap, 6th attempt blocked until tomorrow).
  10. *Scenario 10*: Classroom leaderboard competition (multiple students delete files, ranks recompute, tie-breaking applied).
  11. *Scenario 11*: Pixel Tree 5-stage visual growth cycle (tracks progression from Soil through Legendary Golden Tree).
  12. *Scenario 12*: Role-based security boundary (student attempts unauthorized admin endpoint, blocked by PIN challenge).
  13. *Scenario 13*: Multi-GB batch waste accumulation (single 3.5 GB file approved -> plants 3 trees immediately, retains 0.5 GB carryover).
  14. *Scenario 14*: Tamper-evident ledger audit (detects manual modification of ledger transaction hash, fails verification).
  15. *Scenario 15*: Full lifecycle roundtrip (Scan -> Heuristic Tag -> AI Verify -> Queue -> Teacher Approve -> Disk Recycle -> Accumulate -> Donate -> Ledger Chain -> Tree Level Up).
- **Test File**: `tests/e2e/test_tier4_scenarios.py`

---

## 4. Master Test Runner Specification (`run_all_e2e.py`)

The master test runner provides:
- Single-command execution: `python3 tests/e2e/run_all_e2e.py`
- Structured console output with color-coded tier progress bars.
- JSON output artifact generation (`tests/e2e/test_results.json`) for automated CI/CD and audit logging.
- Clean exit codes:
  - Exit code `0`: All tests passed.
  - Exit code `1`: One or more tests failed.
- CLI flags:
  - `--tier [1|2|3|4]`: Run only a specific tier.
  - `--feature [F-01..F-30]`: Filter tests by feature ID.
  - `--verbose`: Detailed stack traces and per-test timing.
  - `--json`: Output raw JSON report to stdout.

---

## 5. Verification Commands & Execution Instructions

```bash
# Run all 345+ E2E tests across all 4 tiers
python3 tests/e2e/run_all_e2e.py

# Run individual tiers
python3 -m unittest tests/e2e/test_tier1_features.py
python3 -m unittest tests/e2e/test_tier2_boundaries.py
python3 -m unittest tests/e2e/test_tier3_pairwise.py
python3 -m unittest tests/e2e/test_tier4_scenarios.py

# Run via project Makefile
make test-e2e
```
