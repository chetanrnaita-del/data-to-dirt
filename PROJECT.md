# PROJECT: Data-to-Dirt

**System Specification, Feature Inventory & Interface Contracts**  
**Version**: 1.0.0-M1  
**Target Environment**: macOS (Darwin arm64), Linux (x86_64/arm64), Windows (x86_64)  
**Primary Architectures**: Python 3.13 + Native C++ (clang++) + Retro HTML5 Canvas2D / CSS3 / Web Audio API Shell  

---

## 1. Executive Summary & Vision

**Data-to-Dirt** is a shippable, cross-platform desktop application that gamifies the elimination of digital "Dark Data" (abandoned downloads, redundant media takes, obsolete course files, stale build artifacts, unread notifications) by translating accumulated bytes into verifiable, real-world carbon footprint reductions and automated reforestation micro-donations.

The user interface delivers an authentic 16-bit retro-game visual style inspired by *Stardew Valley* and *Celeste*:
- Sprite-based wooden dialogue borders, parchment surfaces, and brass corner rivets.
- Procedural 5-stage growing pixel tree reflecting cumulative dark data eliminated.
- 60 FPS HTML5 Canvas2D particle system emitting binary data shards, eco-sparkles, and celebration confetti.
- Zero-dependency Web Audio API chiptune synthesizer delivering crisp procedural square, triangle, and noise waveforms.
- Complete on-device privacy guarantees with zero remote telemetry.
- On-device offline neural network accountability loop validating student deletion justifications.
- Role-based teacher confirmation queue with pre-allocated classroom Eco-Fund budgeting.

---

## 2. Complete Feature Inventory & Milestone Traceability (30 Features)

| Feature ID | Category | Feature Name | Description | Target Milestone | Acceptance Criteria |
|---|---|---|---|:---:|---|
| **F-UI-01** | Retro UI | Stardew/Celeste Retro Shell | Pixelated styling, wooden frames, parchment cards, brass rivets, custom pixel fonts | **M1** | Renders crisp pixelated retro desktop frame with authentic earthen palette. |
| **F-UI-02** | Retro UI | 5-Stage Growing Tree Loop | Procedural canvas visual feedback: Soil -> Sprout -> Sapling -> Young Oak -> Ancient -> Golden | **M1** | Tree visually advances through stages according to cumulative dark data deleted. |
| **F-UI-03** | Retro UI | 60 FPS Particle Engine | Object-pooled particle emitters for binary shards, eco-sparkles, confetti | **M1** | 60 FPS rendering on canvas without GC hitches or memory leaks. |
| **F-UI-04** | Retro UI | Chiptune Sound Synthesizer | Procedural Web Audio API sound generator (UI_BLIP, COIN_DING, DELETION_POOF, FANFARE, BUZZER) | **M1** | Triggers distinct retro audio waveforms with zero external audio asset dependencies. |
| **F-UI-05** | Retro UI | Screen Shake & Impact Feedback | Decaying harmonic screen shake on significant file deletions | **M1** | Triggers viewport shake on deleting large files (>100 MB). |
| **F-UI-06** | Retro UI | Floating Eco-Numbers | Animated floating popups (+g CO2 offset, +EXP) drifting and fading upward | **M1** | Numbers float and fade smoothly upon carbon deletion events. |
| **F-UI-07** | Retro UI | Retro Dialogue & Confirmation Modals | Authentic RPG dialogue boxes for confirmation and deletion rationale input | **M1** | Modals render with pixel borders, input boxes, and cancel/confirm buttons. |
| **F-UI-08** | Retro UI | Responsive Desktop Container | 1200x800 framing, scanline overlay toggle, dedicated window mode | **M1** | Launches in dedicated Chrome `--app` mode, native WebKit, or clean browser window. |
| **F-UI-09** | Retro UI | Audio State & SFX Controls | Master volume slider, mute toggle, and audio preview buttons | **M1** | Mute and volume controls modify audio output gain instantaneously. |
| **F-R2-01** | Privacy | Blind Initial State Machine | Zero filesystem access or knowledge until explicit user selection | **M2** | Application starts with zero scanned files, zero path history in memory. |
| **F-R2-02** | Privacy | Explicit Permission Dialog | UI dialog for folder selection and permission lifetime (session vs persistent) | **M2** | Traversal only begins after user confirms path and terms. |
| **F-R2-03** | Privacy | Instant Revocation Protocol | User can revoke folder access at any moment, purging memory structures | **M2** | Revocation immediately clears file lists and closes file handles. |
| **F-R2-04** | Privacy | Recursive Metadata Traversal | High-performance filesystem walker capturing name, size, type, timestamps | **M2** | Accurately enumerates file metadata without reading file content into RAM. |
| **F-R2-05** | Privacy | Symlink & Cycle Protection | Prevents infinite recursion across filesystem symlinks and loops | **M2** | Detects symlinks and skips permission-denied directories gracefully. |
| **F-R2-06** | Privacy | Dark Data Heuristic Classifier | Tags files as stale relics (>180d), heavy media (>500MB), duplicates, or temp cache | **M2** | Correctly assigns dark data categories based on size and timestamp rules. |
| **F-R2-07** | Privacy | Confidential File Manual Tagging | User marks file confidential; file is excluded from all deletion operations | **M2** | Marked confidential file cannot be queued for deletion or accessed by AI. |
| **F-R2-08** | Privacy | Confidential Pattern Auto-Skip | Automatic pattern filter for `.env`, `*id_rsa*`, `*password*`, hidden system files | **M2** | Files matching sensitive patterns are excluded automatically. |
| **F-R2-09** | Privacy | PII Text Redaction Scrubber | Regex engine scrubbing emails, phone numbers, and keys from preview snippets | **M2** | File text preview displays `[REDACTED_EMAIL]`, `[REDACTED_PHONE]`. |
| **F-R2-10** | Privacy | Thumbnail Pixelation Filter | Image thumbnails rendered with 16x16 pixelation filter and manual reveal toggle | **M2** | Images blurred by default until intentional "Reveal Preview" click. |
| **F-R2-11** | Carbon Model | Scientific Carbon Calculation | Computes kWh and g CO2e using storage power and regional grid intensity | **M3** | Formula matches $E_{\text{storage}} \times CI$ (Singapore 405.7 gCO2/kWh default). |
| **F-R3-01** | AI Engine | MMCR Transformer Architecture | Multi-Modal Context-Reason Transformer fusing text tokens and tabular metadata | **M4** | Evaluates stated deletion reason against file context 100% offline. |
| **F-R3-02** | AI Engine | Subword Tokenizer & Vocabulary | 1024-token vocabulary handling domain terms and gaming patterns | **M4** | Tokenizes filenames and deletion reasons in <0.5ms. |
| **F-R3-03** | AI Engine | Pure NumPy Forward Pass | Zero-dependency offline matrix inference engine | **M4** | Forward pass completes in <5ms on CPU with zero network calls. |
| **F-R3-04** | AI Engine | Balanced Synthetic Dataset | 4,000 contextual sample pairs covering plausible and gaming cases | **M4** | Generates reproducible dataset offline via seed. |
| **F-R3-05** | AI Engine | Reproducible Training Script | CPU trainer generating weights file from scratch | **M4** | Trains model in <30 seconds, achieving >90% test accuracy. |
| **F-R3-06** | AI Engine | Calibrated Confidence Scorer | Probability score $S \in [0.0, 1.0]$ with 4-tier calibration | **M4** | Plausible reason scores $\ge 0.50$; nonsensical reason scores $< 0.50$. |
| **F-R3-07** | AI Engine | Evaluation Summary Synthesizer | Generates human-readable summary explaining confidence score | **M4** | Produces clear evaluation justification for teacher review queue. |
| **F-R3-08** | AI Engine | Anti-Gaming Escalation Loop | 3-strike penalty system: streak freeze, point loss, teacher incident flag | **M4** | Penalizes repeated gaming attempts and resets streak on severe infractions. |
| **F-R4-01** | Teacher/Admin | Role-Based Access Control | Secure PIN/credential modal switching between Student and Teacher/Admin views | **M5** | PIN `teacher123` unlocks Teacher confirmation panel and Admin settings. |
| **F-R4-02** | Teacher/Admin | Confirmation Review Queue | Real-time queue displaying pending student deletion requests with AI summaries | **M5** | Displays file details, student rationale, confidence badge, carbon impact. |
| **F-R4-03** | Teacher/Admin | Multi-Action Decision Workflow | Approve (commits deletion & points), Reject (feedback note), Flag (penalty) | **M5** | Action updates file status, student profile, and triggers downstream events. |
| **F-R4-04** | Teacher/Admin | Admin Eco-Fund Budget Controller | Pre-allocates cloud savings budget and monitors remaining balance | **M5** | Allows setting budget ($), tracking disbursements, and warns on low balance. |
| **F-R4-05** | Teacher/Admin | Aggregate Class Analytics | Classroom statistics: total data cleared, CO2 offset, top student leaderboard | **M5** | Renders aggregate class impact charts and exports audit report. |
| **F-R5-01** | Eco-Fund | Cumulative Waste Accumulator | Tracks verified teacher-approved bytes toward configurable threshold | **M6** | Accumulates waste across sessions until reaching threshold (default 1 GB). |
| **F-R5-02** | Eco-Fund | 1.0 GB Threshold Trigger | Automatic trigger executing micro-donation when threshold is crossed | **M6** | Automatically plants tree and logs transaction when cumulative waste $\ge 1\text{ GB}$. |
| **F-R5-03** | Eco-Fund | Tamper-Evident Ledger | SHA-256 hash-chained JSON ledger recording all financial/tree transactions | **M6** | Cryptographically verifies transaction integrity and detects tampering. |
| **F-R5-04** | Eco-Fund | Live Tree-Nation REST Client | Sends `POST /api/plant` requests to Tree-Nation API with bearer auth | **M6** | Dispatches real tree planting request and parses certificate URL. |
| **F-R5-05** | Eco-Fund | Offline Synthetic Tree Emulator | Fallback emulator generating synthetic tree records and offline certificates | **M6** | Operates cleanly without internet connection or missing API keys. |
| **F-R5-06** | Eco-Fund | Retro Certificate Viewer | Pixel-art modal displaying verified tree certificate and CO2 offset stats | **M6** | Clicking certificate URL displays authentic 8-bit diploma. |

---

## 3. System Architecture & Self-Contained Design

```
+-----------------------------------------------------------------------------+
|                          Data-to-Dirt Application                           |
+-----------------------------------------------------------------------------+
|  [Desktop Shell Container: Chrome --app / WebKit Native / Browser Fallback] |
|                                                                             |
|  +-----------------------------------------------------------------------+  |
|  |                Retro Web Frontend (HTML5 / CSS3 / JS)                 |  |
|  |  - Stardew Valley & Celeste Aesthetic (Pixel Borders, Parchment)      |  |
|  |  - 60 FPS Canvas2D Particle Emitters (Shards, Sparkles, Confetti)     |  |
|  |  - Procedural Growing Tree Visual Feedback Loop (5 Growth Stages)     |  |
|  |  - Web Audio API Chiptune Synth (Procedural Waveforms, Zero Audio)    |  |
|  |  - Views: Student Dashboard, Teacher Queue, Admin Eco-Fund Budget     |  |
|  +-----------------------------------+-----------------------------------+  |
|                                      | REST / JSON (Localhost)              |
|                                      v                                      |
|  +-----------------------------------------------------------------------+  |
|  |                    Python 3.13 Core Backend Server                     |  |
|  |  - REST Microservice (Flask / http.server on 127.0.0.1:Port)          |  |
|  |  - Scanner Service (Privacy-First Metadata Traversal, PII Scrubber)   |  |
|  |  - Carbon Footprint Engine (kWh/GB/yr * Regional Grid Factor)         |  |
|  |  - Gamification Service (Streaks, Daily Limits, EXP, Leaderboard)     |  |
|  |  - On-Device Neural Network (Pure NumPy MMCR-Transformer Forward)     |  |
|  |  - Teacher & Admin Service (RBAC, Approval Queue, Budget Ledger)      |  |
|  |  - Tree-Nation Client & Offline Emulator (1 GB Threshold Trigger)     |  |
|  |  - Safe Recycler (Send2Trash integration for non-destructive removal)  |  |
|  +-----------------------------------+-----------------------------------+  |
|                                      | Native C++ Bindings (Optional)       |
|                                      v                                      |
|  +-----------------------------------------------------------------------+  |
|  |                     Native C++ Acceleration Engine                    |  |
|  |  - C++17 Directory Scanner (skip_permission_denied, symlink safety)   |  |
|  |  - Native Matrix Forward Pass / Vector Operations (Clang++ compiled)  |  |
|  +-----------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------+
```

### Self-Contained Zero-Dependency Guarantee
- No `npm install`, no `pip install` during build or runtime.
- Built-in Python 3.13 packages utilized: `flask`, `numpy`, `scikit-learn`, `send2trash`, `sqlite3`, `hashlib`, `json`.
- System tools utilized: `clang++` (Apple Clang 21.0), `make` (GNU Make 3.81).

---

## 4. Code Layout & Directory Structure

```
data-to-dirt/
├── Makefile                     # Master build, run, test targets
├── run.sh                       # Single-command executable launcher
├── PROJECT.md                   # System specifications and contracts
├── README.md                    # Quickstart and usage guide
├── src/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py            # Ports, paths, carbon coefficients, thresholds
│   │   ├── server.py            # Local HTTP API & static file service
│   │   └── desktop_shell.py     # Desktop window container launcher
│   ├── services/
│   │   ├── __init__.py
│   │   ├── carbon_calculator.py # Energy & CO2 computation
│   │   ├── gamification.py      # Streaks, leaderboard, tree stage calculation
│   │   ├── scanner.py           # Privacy-first file traversal & PII redaction
│   │   ├── cloud_storage.py     # Cloud storage providers & offline sandbox
│   │   ├── auth.py              # Role-based access control (Student / Teacher / Admin)
│   │   ├── teacher_queue.py     # Deletion request queue management
│   │   ├── eco_fund.py          # Budget ledger & tamper-evident SHA-256 chain
│   │   └── tree_nation.py       # Tree-Nation API client & offline emulator
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── tokenizer.py         # Subword tokenizer with vocab.json
│   │   ├── model.py             # Pure NumPy MMCR-Transformer forward pass
│   │   ├── train.py             # CPU reproducible training script
│   │   ├── dataset_generator.py # Synthetic sample pair generator
│   │   ├── vocab.json           # 1024-token vocabulary
│   │   └── weights.npz          # Pre-trained weights archive
│   ├── engine/                  # Optional native C++ acceleration
│   │   ├── Makefile             # C++ compilation target
│   │   ├── scanner_native.cpp   # Fast C++17 filesystem traversal
│   │   └── nn_native.cpp        # Fast SIMD/matrix forward pass
│   └── ui/                      # Retro Pixel-Art Web Application
│       ├── index.html           # Main retro desktop container HTML
│       ├── css/
│       │   ├── retro_base.css   # Pixel fonts, earthen color palette, scanlines
│       │   ├── stardew.css      # Wooden borders, parchment cards, brass rivets
│       │   └── animations.css   # Screen shake, floating numbers, tree bounce
│       ├── js/
│       │   ├── app.js           # Core state controller, event bus, API client
│       │   ├── audio.js         # Web Audio API chiptune synthesizer
│       │   ├── particles.js     # 60 FPS Canvas2D particle system
│       │   ├── tree.js          # Procedural 5-stage growing tree renderer
│       │   └── views/
│       │       ├── student.js   # Student dashboard, scanner UI, leaderboard
│       │       ├── teacher.js   # Teacher confirmation queue, approve/reject/flag
│       │       └── admin.js     # Eco-Fund budget manager & class analytics
│       └── assets/              # Pixel art SVGs, icons, and sprite definitions
└── tests/
    ├── __init__.py
    ├── test_ui_and_build.py     # Build verification, server endpoints, static files
    ├── test_carbon.py           # Carbon calculation verification
    ├── test_scanner.py          # Privacy & confidential file exclusion
    ├── test_neural_net.py       # AI confidence & gaming detection tests
    ├── test_gamification.py     # Streak increment/reset & daily limit tests
    ├── test_teacher_queue.py    # Approval workflow tests
    └── test_tree_nation.py      # Donation threshold & mock tests
```

---

## 5. Interface Contracts & API Specifications

### 5.1 REST API Specification (Backend `server.py`)

#### `GET /api/health`
- **Response**: `{"status": "ok", "app": "Data-to-Dirt", "version": "1.0.0"}`

#### `GET /api/student/stats`
- **Response**:
  ```json
  {
    "student_id": "STU-001",
    "student_name": "Alex River",
    "bytes_cleared": 1420584960,
    "carbon_offset_g": 188.94,
    "trees_equivalent": 0.0094,
    "eco_points": 350,
    "current_streak_days": 5,
    "daily_deletions_today": 2,
    "daily_deletion_limit": 5,
    "tree_growth_stage": 3,
    "tree_growth_progress_pct": 64.2
  }
  ```

#### `GET /api/student/leaderboard`
- **Response**:
  ```json
  {
    "leaderboard": [
      {"rank": 1, "name": "Sarah Chen", "eco_points": 420, "data_cleared_formatted": "3.8 GB", "streak_days": 8, "trees": 3},
      {"rank": 2, "name": "Alex River (You)", "eco_points": 350, "data_cleared_formatted": "1.4 GB", "streak_days": 5, "trees": 1},
      {"rank": 3, "name": "Marcus Vance", "eco_points": 290, "data_cleared_formatted": "980 MB", "streak_days": 4, "trees": 0},
      {"rank": 4, "name": "Emily Rodriguez", "eco_points": 210, "data_cleared_formatted": "650 MB", "streak_days": 3, "trees": 0}
    ]
  }
  ```

#### `POST /api/scan/request`
- **Body**: `{"folder_path": "/path/to/folder", "session_only": true}`
- **Response**: `{"status": "scanning", "job_id": "scan_123"}`

#### `POST /api/scan/revoke`
- **Response**: `{"status": "revoked", "files_purged": 142}`

#### `POST /api/deletion/submit`
- **Body**: `{"file_id": "f_01", "file_name": "old_take.mov", "file_size": 524288000, "reason": "duplicate take already edited"}`
- **Response**:
  ```json
  {
    "status": "queued_for_teacher",
    "request_id": "REQ-1001",
    "ai_evaluation": {
      "confidence_score": 0.86,
      "tier": "HIGH_CONFIDENCE",
      "summary": "Verified: High-waste redundant video asset (500 MB .mov). Reason matches file profile.",
      "is_gaming": false
    }
  }
  ```

#### `POST /api/auth/login`
- **Body**: `{"role": "teacher", "pin": "teacher123"}`
- **Response**: `{"status": "authenticated", "role": "teacher", "token": "session_tok_..."}`

#### `GET /api/teacher/queue`
- **Response**: `{"queue": [...]}`

#### `POST /api/teacher/decide`
- **Body**: `{"request_id": "REQ-1001", "action": "approve" | "reject" | "flag", "feedback": "..."}`
- **Response**: `{"status": "completed", "action_taken": "approve", "cumulative_waste_bytes": 1073741824, "donation_triggered": true}`

#### `GET /api/admin/ecofund`
- **Response**: `{"budget_usd": 100.0, "balance_usd": 85.0, "trees_planted": 10, "threshold_gb": 1.0}`

---

## 6. Mathematical & Ecological Specifications

### 6.1 Storage Energy Model
$$E_{\text{storage}} = \text{Data (GB)} \times 0.28\,\frac{\text{kWh}}{\text{GB}\cdot\text{year}}$$

### 6.2 Carbon Emission Model
$$\text{CO}_2\text{e (grams)} = E_{\text{storage}} \times CI$$
where $CI = 405.7\,\frac{\text{g CO}_2\text{e}}{\text{kWh}}$ (Singapore Grid Emission Factor).

### 6.3 Tree Sequestration Equivalence
$$\text{Trees Equivalency} = \frac{\text{Avoided CO}_2\text{e (kg)}}{20.0\,\text{kg CO}_2/\text{tree}\cdot\text{year}}$$

---

## 7. Single-Command Build, Launch & Test Guarantee

1. **Clean Build**:
   ```bash
   make
   ```
   Verifies Python 3.13 environment, compiles C++ acceleration engine (if present), checks required libraries without internet downloads.

2. **Single-Command Launch**:
   ```bash
   make run
   # or
   ./run.sh
   ```
   Launches server on a free port, opens dedicated retro application desktop window.

3. **Comprehensive Verification**:
   ```bash
   make test
   ```
   Executes unit tests verifying UI assets, server API endpoints, carbon formulas, and system contracts.
