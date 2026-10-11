# 🚗 AEMS — Amrita Entry Monitoring System

### The campus gate, with every visit accounted for — from visitor request to verified departure.

> Visitors request permission, wardens approve, guards verify the vehicle, and the Security Head watches the whole gate — all on one shared, audited record.

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=flat)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat&logo=sqlite&logoColor=white)
![YOLO](https://img.shields.io/badge/YOLO11-Ultralytics-111F68?style=flat)
![EasyOCR](https://img.shields.io/badge/EasyOCR-ANPR-orange?style=flat)
![Three.js](https://img.shields.io/badge/Three.js-000000?style=flat&logo=threedotjs&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-AI%20briefing-f55036?style=flat)

---

## 🛑 The Problem

University gates still run on paper registers and phone calls:

| Problem | Reality |
|---|---|
| 📞 **Approval by phone** | A guard rings a warden, who rings the student. Nothing is recorded, nothing can be audited. |
| 🔢 **Plate typos** | Vehicle numbers are copied by hand, so the same car is written three different ways. |
| 🚪 **Tailgating** | One approval is supposed to cover one vehicle, but nobody counts what actually drives through. |
| 👥 **Unknown head-count** | The number of people who entered is never compared with the number who left. |
| 🧾 **Regulars are treated like strangers** | Faculty, staff and daily vendors need a fresh request on every visit. |
| 📉 **No big picture** | The Security Head can't see who is inside right now, how busy the gate is, or which visits need attention. |

---

## ✅ What AEMS Does

```
 Visitor              Warden                Guard (gate)            Security Head
   │                    │                      │                        │
   │ 1. Request visit   │                      │                        │
   ├───────────────────▶│                      │                        │
   │                    │ 2. Approve entry     │                        │
   │                    ├─────────────────────▶│                        │
   │                    │                      │ 3. Read plate (ANPR),  │
   │                    │                      │    inspect, count      │
   │                    │                      │    people, record      │
   │                    │                      │    entry               │
   │                    │ 4. Verify the visit, │                        │
   │                    │    authorise exit    │                        │
   │                    ├─────────────────────▶│ 5. Count people again, │
   │                    │                      │    record departure    │
   │                    │                      ├───────────────────────▶│
   │                    │                      │   everything audited   │
```

Four portals, one backend, one database. Whatever one portal changes, the others see.

---

## 🧩 Feature Breakdown

### 1. 🙋 Visitor Portal
- Request permission to meet a student; the student, hostel and **assigned warden** are looked up from the directory (not picked by the visitor).
- Every request gets a request ID and a **private tracking token**, so only the visitor can track entry and exit approval.
- Hostel directions on a **3D campus map** (Three.js) built from OpenStreetMap footprints.

### 2. 🧑‍⚖️ Warden Dashboard
- Sees only the visits assigned to their own account.
- Approves or rejects entry, and **authorises exit only after confirming the meeting actually happened**.

### 3. 🛂 Security (Guard) Dashboard
- Look up a plate and see the approval status in one step.
- **Live camera ANPR** — YOLO11 plate detector + EasyOCR reader. Frames are processed in memory and never saved; recognition never records passage on its own.
- Mandatory **vehicle inspection** and **people count** (entry and exit counts must match, otherwise the departure is blocked with HTTP 409).
- **Tailgating simulation** — one approval covers one vehicle; a count above one raises an alert and blocks further entries until a guard records an outcome.

### 4. 🧑‍💼 Security Head Dashboard
A sidebar of everything the head needs, all inside one page:

| Section | What it shows |
|---|---|
| **Overview** | Capacity bar, recognition decisions, last-12-hours activity, guard review queue |
| **Vehicles inside** | Who is on campus right now and their exit-permission state |
| **Plate review** | Uncertain / unknown plate reads waiting for a human decision, plus searchable recognition history (CSV export) |
| **Registered vehicles** | Approve, suspend and search regular vehicles (faculty, staff, daily visitors, vendors) |
| **Incidents** | Report → acknowledge → investigate → outcome → resolve |
| **History** | Past visits and the audit trail |
| **AI assistant** | Daily briefing and Q&A over authorised aggregate facts only |
| **Settings** | Vehicle capacity, minimum recognition score, normal / lockdown entry policy |

### 5. 🪪 Registered Vehicles
- Faculty, staff, approved daily visitors and vendors get an expiring registration instead of a new warden request every time.
- An exact plate match gives entry permission — **inspection is still mandatory**.
- Suspension or expiry blocks new entry, but a vehicle already inside can still leave.

### 6. 🤖 AI Briefing (optional)
- Head/admin only. The backend supplies authorised aggregate facts and validates the output; **the AI can never grant a permission**.

---

## 🔒 Safety Rules Built Into the Backend

| Rule | How it's enforced |
|---|---|
| Recognition ≠ permission | A plate read never records passage; a human guard always confirms |
| No guessing | Low-confidence / invalid plates become `HOLD` reads — O/0 and I/1 are never auto-corrected |
| One plate, one place | A unique occupancy record stops the same plate entering twice at once |
| Head-count matching | Exit count must equal the saved entry count |
| Capacity & lockdown | Re-checked on the server at the moment of entry; exits are never blocked |
| Role-based access | HttpOnly cookie + signed JWT, server-side revocation, salted **scrypt** password hashes |
| Optimistic locking | Every approval carries a `version`, so two staff members can't overwrite each other |
| Full audit trail | Approvals, suspensions, policy changes and reviews record the responsible staff account |

---

## 🏛️ System Architecture

```
┌──────────────────────── Browser (single-page UI) ────────────────────────┐
│  Visitor · Warden · Guard · Security Head  (vanilla JS, Three.js 3D map)  │
│  dist/*.js  +  backend/frontend/{backend-ui, head-monitor, live-camera}   │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │  REST  /api/v1/…   (cookie + JWT)
┌───────────────────────────────▼──────────────────────────────────────────┐
│                         FastAPI backend (backend/)                        │
│  main.py        auth, visits, approvals, incidents, queue, analytics      │
│  registry.py    registered-vehicle approval, lookup, entry                │
│  monitoring.py  head overview, occupancy, recognition summary             │
│  tailgating.py  one-approval-one-vehicle cycles + alerts                  │
│  anpr.py        audited plate-detection records and human review          │
│  camera.py      frame → YOLO11 detector → plate crop → EasyOCR            │
│  ai.py          Groq / local-relay briefing (facts only)                  │
│  security.py    scrypt, JWT, sessions, role guards                        │
└───────────────┬──────────────────────────────────────────────────────────┘
                │  SQLAlchemy 2 + Alembic migrations (0001 … 0007)
                ▼
          SQLite database  (data/, never committed)
```

---

## 💻 Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | Vanilla JS + CSS | Four role-based portals, no build step |
| 3D map | Three.js 0.180 + OSM data | Hostel directions and route preview |
| Backend | FastAPI + Uvicorn | REST API, interactive docs at `/docs` |
| Database | SQLite + SQLAlchemy 2 + Alembic | Normalised records with versioned migrations |
| Auth | PyJWT + scrypt | Role-based sessions |
| Plate detection | Ultralytics YOLO11s | Finds the number plate in a frame |
| Plate reading | EasyOCR (English) | Reads the cropped plate locally |
| AI briefing | Groq API *(optional)* | Head-only daily summary / Q&A |
| Tests | pytest | API, registry, occupancy, tailgating, head-count rules |

---

## 📁 Repository Structure

```
AEMS/
├── README.md                    ← You are here
├── backend/                     ← FastAPI service
│   ├── main.py                  ← App, auth, visits, approvals, incidents
│   ├── registry.py              ← Registered vehicles
│   ├── monitoring.py            ← Security-head overview
│   ├── tailgating.py            ← Passage count + alerts
│   ├── anpr.py / camera.py      ← Plate recognition pipeline
│   ├── ai.py                    ← Optional AI briefing
│   ├── models.py, schemas.py    ← Database + API models
│   ├── migrations/              ← Alembic versions 0001–0007
│   ├── frontend/                ← Backend-connected UI layers
│   │   ├── backend-ui.js        ← Portals wired to the API
│   │   ├── head-monitor.js      ← Security-head sidebar + views
│   │   └── live-camera.js       ← Browser camera + recognise-frame
│   ├── models/README.md         ← ANPR weight notes (weights not committed)
│   └── tests/test_backend.py
├── dist/                        ← Static UI, 3D campus, vendor Three.js
├── worker/, scripts/, drizzle/  ← Hosted demo variant
├── monitor_server.py            ← Lightweight static demo server (port 4173)
├── campus-osm.xml, campus-roads-2025.pdf, CAMPUS_SOURCES.md  ← Map sources
└── Round_2_Preparation.md
```

---

## ⚙️ Quick Start

### Prerequisites

| Item | Requirement |
|---|---|
| OS | Windows / macOS / Linux |
| Python | 3.x with `pip` |
| Camera ANPR *(optional)* | `backend/requirements-anpr.txt` + model weights |

### 1. Clone

```bash
git clone https://github.com/pranav2007kumar/AEMS.git
cd AEMS
```

### 2. Install

```bash
pip install -r backend/requirements.txt
```

### 3. Run

```powershell
# Windows PowerShell
$env:PORT = "4174"; $env:IMPORT_LEGACY = "1"; $env:LOCAL_DEMO_LOGIN = "1"
python -u backend/run.py
```

```bash
# macOS / Linux
PORT=4174 IMPORT_LEGACY=1 LOCAL_DEMO_LOGIN=1 python -u backend/run.py
```

Open **http://127.0.0.1:4174/** — API docs at **http://127.0.0.1:4174/docs**.

### 4. Sign in (local demo only)

With `LOCAL_DEMO_LOGIN=1` the staff portals accept **`1234` / `1234`** on loopback. This shortcut is rejected in production and for non-loopback requests. Real accounts get generated passwords written to `data/backend-demo-accounts.txt`, which is never committed. Visitors don't need to sign in.

Student IDs to try in the visitor form: `CB.CSE.DEMO01`, `CB.ECE.DEMO02`, `CB.AI.DEMO03`.

### 5. Run the tests

```bash
python -m pytest backend/tests
```

### Environment variables

| Variable | Purpose |
|---|---|
| `PORT` | Server port (default `4174`) |
| `DATABASE_URL` | Database location (defaults to local SQLite) |
| `APP_ENV` | Set `production` to disable demo login and require `JWT_SECRET` |
| `JWT_SECRET` | Session signing secret (**required in production**) |
| `GROQ_API_KEY` | Enables the AI briefing (optional) |
| `ANPR_ENABLE_INFERENCE` | `1` to load the plate detector + OCR |
| `TEST_PASSWORD` | Fixed password for seeded accounts (testing only) |

---

## 📷 Camera Plate Recognition (optional)

```
Browser camera ─▶ "Recognize current frame" ─▶ YOLO11s plate detector
                                                     │
                                         cropped plate ▼
                                              EasyOCR (English)
                                                     │
                                                     ▼
                              audited ANPR record  ─▶  guard confirms
```

- Camera starts only when the guard clicks **Start camera**; audio is off; leaving the page releases the tracks.
- Model weights are **not** in this repo — see [backend/models/README.md](backend/models/README.md). Install `backend/requirements-anpr.txt` and set `ANPR_ENABLE_INFERENCE=1`.
- Multiple plates or unreadable frames always go to manual review.

---

## ⚠️ Honest Limitations

This is a hackathon prototype, and we'd rather say so than overstate it:

- Plate-recognition accuracy has been smoke-tested, **not benchmarked**.
- Vehicle counting and the gate barrier are **simulated** — no physical sensors or barrier are connected.
- The demo `1234` login is for local use only.
- Queue forecasting is a historical hourly baseline, not a trained ML model.
- Campus map building heights, facades and trees are illustrative; routes are approach previews.

---

## 🤝 Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feat/your-feature`
3. Add or change an endpoint in `backend/`, with a test in `backend/tests/`
4. Open a PR describing what changed and why

---

## 📄 License

Not yet specified — add a `LICENSE` file before reusing this code.

---

*Built with ❤️ for a hackathon — every visit, accounted for.*
