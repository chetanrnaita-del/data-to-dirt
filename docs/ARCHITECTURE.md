# Data-to-Dirt — Full Application Architecture

## 1. System Waterfall / Sequence Diagram

This sequence diagram shows the **end-to-end lifecycle** of a student interacting with the platform — from login to tree planting.

> 📥 **Rendered Image Formats:**
> - [View / Download High-Res PNG (1892x2537)](file:///Users/narayan/.gemini/antigravity/scratch/data-to-dirt/docs/diagrams/waterfall_sequence_diagram.png)
> - [View / Download High-Quality JPG (1892x2537)](file:///Users/narayan/.gemini/antigravity/scratch/data-to-dirt/docs/diagrams/waterfall_sequence_diagram.jpg)
> - [View / Download Vector SVG](file:///Users/narayan/.gemini/antigravity/scratch/data-to-dirt/docs/diagrams/waterfall_sequence_diagram.svg)

```mermaid
sequenceDiagram
    autonumber
    participant S as 🧑‍🎓 Student Browser
    participant SW as 📦 Service Worker
    participant F as 🖥️ Flask Server
    participant FS as 🔥 Cloud Firestore
    participant GD as ☁️ Google Drive API
    participant AI as 🤖 AI Evaluator
    participant T as 👨‍🏫 Teacher Browser
    participant TN as 🌳 Tree-Nation API

    rect rgb(240, 237, 255)
    Note over S,F: Phase 1 — Authentication
    S->>SW: GET / (cached PWA shell)
    SW-->>S: index.html + login.js
    S->>F: POST /api/auth/login {role, user_id, pin}
    F->>FS: Query users collection (live credential check)
    FS-->>F: User doc {student_id, name, class_code}
    F->>F: Verify PIN matches class_code (HMAC token)
    F-->>S: 200 {token, role, student_name, class_code}
    end

    rect rgb(232, 248, 245)
    Note over S,F: Phase 2 — Dashboard & Stats
    S->>F: GET /api/student/stats?token=...
    F->>FS: Read student document
    FS-->>F: {bytes_cleared, eco_points, streak_days, strikes}
    F-->>S: Stats JSON
    S->>F: GET /api/student/leaderboard
    F-->>S: Top-N students sorted by eco_points
    S->>F: GET /api/tree/growth
    F-->>S: Tree growth stage + SVG data
    end

    rect rgb(255, 245, 238)
    Note over S,GD: Phase 3 — File Scanning (Google Drive)
    S->>F: POST /api/scan/request {folder_id, token}
    F->>GD: OAuth2 → List files in folder
    GD-->>F: File metadata array
    F->>F: Scanner classifies dark data candidates
    F->>F: Carbon calculator estimates CO₂ per file
    F-->>S: {files[], dark_data_count, total_bytes}
    end

    rect rgb(255, 240, 240)
    Note over S,AI: Phase 4 — Deletion Request + AI Evaluation
    S->>F: POST /api/deletion/submit {file_id, reason, token}
    F->>AI: AI evaluates legitimacy (anti-gaming check)
    AI-->>F: {confidence_score, tier, is_gaming}
    F->>FS: Write deletion request to Firestore
    F-->>S: {request_id, status: "PENDING", ai_evaluation}
    end

    rect rgb(240, 248, 255)
    Note over T,FS: Phase 5 — Teacher Review
    T->>F: GET /api/teacher/queue?class_code=bio101
    F->>FS: Query pending deletion requests
    FS-->>F: Pending requests array
    F-->>T: Queue JSON with AI evaluations
    T->>F: POST /api/teacher/decide {request_id, decision}
    F->>FS: Update request status (APPROVED/REJECTED)
    F->>FS: Credit eco_points + bytes_cleared to student
    F-->>T: {status: "success", decision}
    end

    rect rgb(232, 255, 232)
    Note over F,TN: Phase 6 — Eco-Fund & Tree Planting
    F->>F: Check cumulative_waste_bytes ≥ 1 GB threshold
    F->>TN: Fund tree planting via Tree-Nation
    TN-->>F: {tree_id, species, location}
    F->>FS: Record donation in ecofund history
    F-->>S: 🎉 Tree planted notification
    end
```

---

## 2. Component / Class Diagram (UML)

> 📥 **Rendered Image Formats:**
> - [View / Download High-Res PNG (1904x842)](file:///Users/narayan/.gemini/antigravity/scratch/data-to-dirt/docs/diagrams/uml_class_diagram.png)
> - [View / Download High-Quality JPG (1904x842)](file:///Users/narayan/.gemini/antigravity/scratch/data-to-dirt/docs/diagrams/uml_class_diagram.jpg)
> - [View / Download Vector SVG](file:///Users/narayan/.gemini/antigravity/scratch/data-to-dirt/docs/diagrams/uml_class_diagram.svg)

```mermaid
classDiagram
    direction TB

    class FlaskServer {
        +create_app() Flask
        +api_auth_login()
        +api_student_stats()
        +api_student_leaderboard()
        +api_scan_request()
        +api_scan_revoke()
        +api_deletion_submit()
        +api_teacher_queue()
        +api_teacher_decide()
        +api_teacher_decide_all()
        +api_teacher_students()
        +api_teacher_create_student()
        +api_admin_ecofund()
        +api_admin_audit()
        +api_analytics_track()
        +api_analytics_dashboard()
        +api_analytics_export()
        +api_tree_growth()
        +api_health()
    }

    class AuthService {
        +admin_pin: str
        +teacher_passwords: dict
        +validate_token(token) bool
        +generate_token(user_id) str
    }

    class FirebaseDB {
        +db: firestore.Client
        +get_student(student_id) dict
        +save_student(data) void
        +query_users(class_code) list
        +save_deletion_request(req) void
        +get_pending_requests(class) list
    }

    class Scanner {
        +scan_folder(path) list
        +classify_dark_data(file) dict
        +calculate_ai_confidence(file) float
        +detect_confidential(file) bool
    }

    class CarbonCalculator {
        +estimate_co2(bytes) float
        +format_carbon(grams) str
    }

    class EcoFund {
        +budget_usd: float
        +balance_usd: float
        +trees_planted: int
        +check_threshold(bytes) bool
        +fund_tree() dict
    }

    class TeacherQueue {
        +get_pending(class_code) list
        +approve(request_id) dict
        +reject(request_id, reason) dict
        +bulk_decide(ids, decision) list
    }

    class TreeNation {
        +plant_tree(species) dict
        +get_forest_stats() dict
    }

    class CloudStorage {
        +list_files(folder_id) list
        +delete_file(file_id) bool
        +get_file_metadata(id) dict
    }

    class Analytics {
        +track_event(event) void
        +get_dashboard() dict
        +get_geo_data() dict
        +export_csv() bytes
    }

    class Ledger {
        +record_transaction(tx) void
        +get_audit_trail() list
    }

    FlaskServer --> AuthService : authenticates
    FlaskServer --> FirebaseDB : persists data
    FlaskServer --> Scanner : scans files
    FlaskServer --> CarbonCalculator : estimates CO₂
    FlaskServer --> EcoFund : manages fund
    FlaskServer --> TeacherQueue : manages approvals
    FlaskServer --> TreeNation : plants trees
    FlaskServer --> CloudStorage : Google Drive ops
    FlaskServer --> Analytics : tracks events
    FlaskServer --> Ledger : audit trail

    class LoginView {
        +selectedRole: string
        +render(container) void
        +bindEvents(container) void
    }

    class StudentView {
        +render(container) void
        +loadStats() void
        +submitDeletion(file) void
        +renderTree() void
    }

    class TeacherView {
        +render(container) void
        +loadQueue() void
        +decideDeletion(id, decision) void
        +createStudent(data) void
    }

    class AdminView {
        +render(container) void
        +loadEcoFund() void
        +loadAuditLog() void
    }

    class AnalyticsView {
        +render(container) void
        +loadDashboard() void
        +renderCharts() void
        +exportData() void
    }

    class AppController {
        +currentView: string
        +token: string
        +role: string
        +navigate(view) void
        +logout() void
    }

    AppController --> LoginView : mounts
    AppController --> StudentView : mounts
    AppController --> TeacherView : mounts
    AppController --> AdminView : mounts
    AppController --> AnalyticsView : mounts

    LoginView ..> FlaskServer : POST /api/auth/login
    StudentView ..> FlaskServer : GET /api/student/*
    StudentView ..> FlaskServer : POST /api/scan/*
    StudentView ..> FlaskServer : POST /api/deletion/*
    TeacherView ..> FlaskServer : GET/POST /api/teacher/*
    AdminView ..> FlaskServer : GET/POST /api/admin/*
    AnalyticsView ..> FlaskServer : GET /api/analytics/*
```

---

## 3. Deployment Architecture

> 📥 **Rendered Image Formats:**
> - [View / Download High-Res PNG (1070x693)](file:///Users/narayan/.gemini/antigravity/scratch/data-to-dirt/docs/diagrams/deployment_architecture_diagram.png)
> - [View / Download High-Quality JPG (1070x693)](file:///Users/narayan/.gemini/antigravity/scratch/data-to-dirt/docs/diagrams/deployment_architecture_diagram.jpg)
> - [View / Download Vector SVG](file:///Users/narayan/.gemini/antigravity/scratch/data-to-dirt/docs/diagrams/deployment_architecture_diagram.svg)

```mermaid
flowchart LR
    subgraph Client["🌐 Client (Browser / PWA)"]
        PWA["📱 PWA Shell<br/>Service Worker v57"]
        UI["🎮 Retro UI<br/>login · student · teacher<br/>admin · analytics"]
    end

    subgraph Render["☁️ Render (PaaS)"]
        Flask["🐍 Flask Server<br/>Gunicorn · Python 3.13"]
    end

    subgraph Google["🔷 Google Cloud"]
        Firestore["🔥 Firestore<br/>datatodirt"]
        Drive["📂 Google Drive API<br/>OAuth2 File Access"]
        GIS["🔐 Google Identity<br/>Services (OAuth)"]
    end

    subgraph External["🌍 External"]
        TN["🌳 Tree-Nation API"]
        CF["📊 Cloudflare<br/>Web Analytics"]
    end

    subgraph GitHub["🐙 GitHub"]
        Repo["📦 chetanrnaita-del/<br/>data-to-dirt"]
    end

    PWA --> Flask
    UI --> Flask
    Flask --> Firestore
    Flask --> Drive
    Flask --> GIS
    Flask --> TN
    Client --> CF
    Repo -->|"Auto-deploy on push"| Render
```

---

## 4. Data Flow Waterfall (Phase Summary)

| Phase | Actor | Action | Backend Service | Storage |
|-------|-------|--------|-----------------|---------|
| **1. Auth** | Student / Teacher / Admin | Login with credentials | `AuthService` | Firestore `users` |
| **2. Dashboard** | Student | View stats, leaderboard, tree | `FlaskServer` | Firestore + `app_state.json` |
| **3. Scan** | Student | Select Google Drive folder → scan | `Scanner` + `CloudStorage` | Google Drive API |
| **4. Submit** | Student | Request file deletion with reason | `AI Evaluator` + `TeacherQueue` | Firestore `deletion_requests` |
| **5. Review** | Teacher | Approve / reject deletion requests | `TeacherQueue` | Firestore |
| **6. Credit** | System | Award eco-points, update streak | `CarbonCalculator` + `Ledger` | Firestore `users` |
| **7. Eco-Fund** | System | Check threshold → fund tree | `EcoFund` + `TreeNation` | Firestore `ecofund` |
| **8. Analytics** | Admin | View global KPIs, geo heatmap | `Analytics` | Firestore `analytics` |
