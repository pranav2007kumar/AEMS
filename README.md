# 🚗 AEMS — Amrita Entry Monitoring System

### Paper registers and signed slips at the gate, replaced by one verified digital trail — from the parent's request to the car leaving campus.

> A parent fills the visit form before arriving. The warden approves it. The gate camera reads the number plate and the guard checks it against the approved request. On the way out, the warden's verification and the head-count are checked again. The Security Head watches everything, with an AI assistant on top of the database.

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=flat)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat&logo=sqlite&logoColor=white)
![YOLO](https://img.shields.io/badge/YOLO11-Ultralytics-111F68?style=flat)
![EasyOCR](https://img.shields.io/badge/EasyOCR-ANPR-orange?style=flat)
![Three.js](https://img.shields.io/badge/Three.js-000000?style=flat&logo=threedotjs&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-LLM%20assistant-f55036?style=flat)

---

## 🛑 The Problem (how a parent visit works today)

When a parent or guardian arrives at the Amrita gate, this is what happens:

1. The parent **gets out of the vehicle** and writes the **vehicle number, the student's details and the hostel details** in a **paper register**.
2. The security guard hands over a **paper slip** naming the person being visited.
3. The parent and the student walk to the **warden**, who **signs the slip**.
4. When the parent leaves, the guard **checks the slip** and lets the vehicle go.

| What goes wrong | Why it hurts |
|---|---|
| 📖 **Handwritten register** | Slow, hard to read, impossible to search. Nobody can say who was inside at 3 pm last Tuesday. |
| 🧾 **Paper slips** | Can be lost, copied or forged. The guard can't tell a genuine signature from a fake one. |
| 🚶 **Parent must leave the car at the gate** | Queues build up, and the parent walks around a campus they don't know. |
| 🗺️ **First-time visitors don't know the way** | Parents have no idea where the hostel is. |
| 🔢 **Plate numbers copied by hand** | Typos mean the number on the slip may not match the car that leaves. |
| 🚪 **No head-count** | Nobody records how many people entered or left in the vehicle. |
| 🔁 **Daily regulars treated like strangers** | Faculty, staff and daily vendors go through the same register every day. |
| 📉 **No visibility for the Security Head** | No idea how busy the gate is, when to put more guards on duty, or which vehicles stayed inside too long. |

---

## ✅ Our Solution

Everything the paper process did, but **before the car reaches the gate**, with the **number plate as the key**.

```
 PARENT / GUARDIAN        STUDENT           WARDEN               SECURITY GUARD            SECURITY HEAD
        │                    │                 │                        │                       │
 1. Fills the visit form     │                 │                        │                       │
    (vehicle no., student ID │                 │                        │                       │
    → hostel + warden are    │                 │                        │                       │
    filled in automatically) │                 │                        │                       │
        │──────────────────────────────────────▶ 2. Warden approves     │                       │
        │                    │                 │    the entry           │                       │
        │ 3D map shows the   │                 │                        │                       │
        │ route to the hostel│                 │                        │                       │
        │                                      │          4. Camera reads the plate (ANPR)      │
        │                                      │             Guard compares it with the form,   │
        │                                      │             inspects, counts people, ALLOWS    │
        │                    5. Visit with the student                  │                       │
        │──────────────────────────────────────▶ 6. Warden verifies     │                       │
        │                                      │    the visit, clears   │                       │
        │                                      │    the exit            │                       │
        │                                      │          7. Guard counts people again,        │
        │                                      │             records departure ───────────────▶│
        │                                      │                                  Monitors, charts, AI assistant
```

### What changed for each person

| Before (paper) | Now (AEMS) |
|---|---|
| Parent writes in a register at the gate | Parent fills the form in advance; typing the **student ID auto-fills branch, hostel and the assigned warden** |
| Guard issues a paper slip | No slip. The approval lives in the database |
| Parent asks for directions | **3D campus map** with a route to the correct hostel |
| Guard reads the plate by eye | **Camera + YOLO + OCR read the plate**; the guard just confirms it matches the approved form |
| Warden signs a slip | Warden approves the entry and later **verifies the visit before exit** |
| Nobody counts people | Guard records the head-count **in and out**; a mismatch blocks departure |
| Guard checks the slip on exit | Exit is only possible once the warden has cleared it |
| Head has no overview | Live dashboard, AI chat, anomaly alerts, staffing insight |

---

## 🧩 The Four Portals

### 1. 🙋 Visitor (Parent / Guardian)
- Fill the request: visitor details, vehicle number, student ID, purpose, date.
- **Student ID → auto-mapped** to the student's name, branch, hostel and assigned warden. Unknown IDs can't be submitted.
- **3D campus navigation** (Three.js, built from OpenStreetMap footprints: 99 buildings, 61 roads/paths) to guide first-time visitors to the right hostel.
- Private **request ID + tracking token** to follow entry and exit approval.

### 2. 🧑‍⚖️ Warden
- Sees only visits for students **assigned to their own account**.
- Approves or rejects entry (the student asks their warden, exactly as with an outpass).
- Authorises exit **only after confirming the meeting actually happened**.

### 3. 🛂 Security Guard
- **Camera number-plate recognition**: start the camera, click *Recognize current frame*. YOLO11 finds the plate, our trained CRNN reads it (EasyOCR is only a fallback).
- The guard compares the **detected plate** with the **plate on the parent's form**, looks at the **confidence score** and decides.
- Mandatory **vehicle inspection** and **people count** at entry **and** exit; the two counts must match.
- Confirming records entry; departure is recorded only after warden clearance.
- Tailgating simulation: one approval covers one vehicle; a higher count raises an alert.

### 4. 🧑‍💼 Security Head
Sidebar sections, all on one page:

| Section | What it gives the head |
|---|---|
| **Overview** | Campus capacity, recognition decisions, hourly activity chart, review queue |
| **Vehicles inside** | Who is on campus right now; **vehicles that stayed too long** |
| **Plate review** | Uncertain plate reads waiting for a human; searchable history; CSV export |
| **Registered vehicles** | Approve students'/faculty/staff/vendor vehicles **once at the start of the year**; they then enter daily without a new request. Suspend or expire any time |
| **Incidents** | Report → acknowledge → investigate → outcome → resolve |
| **History** | All old visits and the audit trail |
| **AI assistant** | An **LLM that queries the database**: *"how many cars arrived between 10:00 and 10:30?"*, daily briefing, unusual-activity notes |
| **Settings** | Capacity, minimum recognition score, normal / lockdown entry policy, queue settings |

Plus **queue estimates** (how long the queue will take to clear) and **historical arrival frequency** (busiest hours of the last 10–15 hours) so the head can plan guard staffing.

---

## 🔒 Rules the Backend Enforces

| Rule | How |
|---|---|
| Recognition is never permission | A plate read never records passage; a guard confirms every entry |
| No guessing | Low-confidence or invalid plates become `HOLD` reads; O/0 and I/1 are never auto-corrected |
| Entry needs warden approval | Visitors can't enter without an approved request for **that** plate and date |
| Exit needs warden verification | The visit must be verified by the warden before exit is allowed |
| Head-count must match | Exit count has to equal the entry count (HTTP 409 otherwise) |
| One plate, one place | The same plate can't be inside twice |
| Inspection is mandatory | Every entry needs a recorded inspection |
| Capacity / lockdown | Re-checked on the server at entry; exits are never blocked |
| The AI can't grant anything | LLM only sees authorised aggregate facts and can't approve or change records |
| Safe auth | HttpOnly cookies, signed JWT, server-side revocation, scrypt password hashes |
| Concurrency safe | Versioned records, so two staff can't overwrite each other |
| Audit trail | Every approval, suspension, policy change and review is recorded with the staff account |

---

## 🏛️ Architecture

```
┌────────────────────────── Browser (vanilla JS) ──────────────────────────┐
│ Visitor · Warden · Guard · Security Head   Three.js 3D campus            │
│ dist/            static pages, 3D map, hostel directory                  │
│ backend/frontend/ API-connected layers (portals, head sidebar, camera)   │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │ REST /api/v1/…  (cookie + JWT)
┌───────────────────────────────▼──────────────────────────────────────────┐
│ FastAPI backend (backend/)                                               │
│  main.py        auth, visits, approvals, incidents, queue, analytics     │
│  registry.py    registered vehicles                                      │
│  monitoring.py  head overview, occupancy, recognition summary            │
│  tailgating.py  one-approval-one-vehicle cycles + alerts                 │
│  anpr.py        audited plate-detection records + human review           │
│  camera.py      frame → YOLO11 plate detector → crop → CRNN reader      │
│  ai.py          LLM assistant (Groq) over database facts                 │
│  security.py    scrypt, JWT, sessions, role guards                       │
└───────────────┬──────────────────────────────────────────────────────────┘
                ▼  SQLAlchemy 2 + Alembic (migrations 0001–0007)
          SQLite  (created automatically in data/)
```

---

## 💻 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vanilla JS + CSS (no build step) |
| 3D navigation | Three.js 0.180 + OpenStreetMap data |
| Backend | FastAPI + Uvicorn |
| Database | SQLite, SQLAlchemy 2, Alembic |
| Auth | PyJWT + scrypt |
| Plate detection | Ultralytics YOLO11s (`plate-detector.pt`) |
| Plate reading | Our CRNN: MobileNetV3-Large → BiLSTM → CTC (`campus-anpr.pt`); EasyOCR English as fallback |
| LLM assistant | Groq API (optional) |
| Tests | pytest (13 tests) |

---

## 📁 Repository Contents

```
AEMS/
├── README.md
├── backend/
│   ├── main.py, registry.py, monitoring.py, tailgating.py   ← API
│   ├── anpr.py, camera.py, anpr_adapter.py, plate_reader.py ← plate recognition
│   ├── ai.py                                                ← LLM assistant
│   ├── models.py, schemas.py, services.py, security.py      ← data + auth
│   ├── bootstrap.py                                         ← seeds demo students/wardens/accounts
│   ├── migrations/                                          ← Alembic 0001–0007
│   ├── frontend/                                            ← backend-ui.js, head-monitor.js, live-camera.js
│   ├── models/
│   │   ├── plate-detector.pt   (YOLO11s number-plate detector, trained by us)
│   │   ├── ocr/english_g2.pth  (EasyOCR English recognizer — fallback only)
│   │   └── campus-anpr.pt      (CRNN plate-text reader, trained by us — primary OCR)
│   ├── tests/test_backend.py
│   ├── requirements.txt, requirements-anpr.txt
│   └── run.py, start.ps1
├── dist/              ← web UI, 3D campus (Three.js vendored), hostel directory
└── tools/             ← optional: regenerate the 3D map data from OpenStreetMap
    ├── campus-osm.xml, build_campus_data.py, build_real_view.py
```

---

## ⚙️ Setup — Replicate the Project

### Prerequisites
| Item | Requirement |
|---|---|
| Python | 3.10+ with `pip` |
| Browser | Chrome / Edge (camera access needs `localhost` or HTTPS) |
| Webcam | Only for live plate recognition |
| Groq API key | Only for the LLM assistant (optional) |

### 1. Clone
```bash
git clone https://github.com/pranav2007kumar/AEMS.git
cd AEMS
```

### 2. Install the web backend
```bash
pip install -r backend/requirements.txt
```

### 3. Run
```bash
# macOS / Linux
PYTHONPATH=. PORT=4174 LOCAL_DEMO_LOGIN=1 python -u backend/run.py
```
```powershell
# Windows PowerShell
$env:PYTHONPATH="."; $env:PORT="4174"; $env:LOCAL_DEMO_LOGIN="1"
python -u backend/run.py
```
Open **http://127.0.0.1:4174/** (API docs at `/docs`). The database, demo students, wardens and guards are created automatically on first start.

### 4. Try the full flow
Sign-in for the staff portals (**local demo only**): username `1234`, password `1234`. In the Warden portal pick Menon or Devi.

1. **Visitor portal**: enter student ID `CB.CSE.DEMO01` (also `CB.ECE.DEMO02`, `CB.AI.DEMO03`). Hostel and warden fill in automatically. Add a vehicle number, e.g. `TN38AB1234`, and submit. **Save the request ID and tracking token.**
2. **Warden portal**: approve the entry.
3. **Security portal**: look up `TN38AB1234`, tick the verification and inspection boxes, enter the people count and confirm passage (the **Allow** step).
4. **Warden portal**: verify the visit and clear the exit.
5. **Security portal**: switch to *exit*, enter the same people count, record departure.
6. **Security head**: view occupancy, history, registered vehicles, incidents and settings.

### 5. Optional: live camera plate recognition
```bash
pip install -r backend/requirements-anpr.txt     # use CPU torch wheels if you have no GPU
```
Then start the server with `ANPR_ENABLE_INFERENCE=1`. The weights are already in `backend/models/`. In the guard portal click **Start camera → Recognize current frame**.

### 6. Optional: LLM assistant
```bash
export GROQ_API_KEY=your_key      # PowerShell: $env:GROQ_API_KEY="your_key"
```
Set it before starting the server. The Security Head → *AI assistant* then answers questions from the database.

### 7. Run the tests
```bash
PYTHONPATH=. python -m pytest backend/tests -q
```

### Environment variables
| Variable | Purpose |
|---|---|
| `PORT` | Server port (default `4174`) |
| `LOCAL_DEMO_LOGIN` | `1` allows the `1234/1234` shortcut on loopback only |
| `ANPR_ENABLE_INFERENCE` | `1` loads the detector + OCR models for live recognition |
| `GROQ_API_KEY` | Enables the LLM assistant |
| `APP_ENV` / `JWT_SECRET` | `production` disables demo login and **requires** `JWT_SECRET` |
| `DATABASE_URL` | Override the default SQLite file |
| `TEST_PASSWORD` | Fixed password for seeded accounts (testing) |

---

## 🧠 Plate Recognition Pipeline

```
 Camera frame (in memory, never stored)
        │
        ▼
 YOLO11s plate detector ──▶ crop the plate ──▶ CRNN reader (votes over a few crop views)
        │                                          │
        └──────────────── plate text + confidence ◀┘
                              │
                              ▼
        audited ANPR record  ──▶  guard compares with the approved form
```

- Overlapping boxes on one plate are merged; several *different* plates in a frame, or an unreadable frame, go to manual review.
- Reported confidence is the OCR text confidence. A read must be a valid Indian plate format with confidence ≥ 0.5; the entry policy (default 0.90) decides what is held for review.
- The detector, OCR and form comparison are advisory. **The guard decides.**
- Details of the supplied checkpoints are in [backend/models/README.md](backend/models/README.md).

---

## ⚠️ Honest Limitations

- Plate-recognition accuracy has been smoke-tested, **not benchmarked** on a real gate dataset.
- Vehicle counting and the barrier are **simulated**; no physical sensors or gate hardware are connected.
- `1234 / 1234` is a local demo shortcut and is rejected in production and for non-loopback requests.
- The student/warden/hostel directory is **sample data** seeded for the demo.
- Queue forecasting is a historical hourly baseline, not a trained ML model.
- Building heights, facades and trees in the 3D map are illustrative; routes are approach previews.

---

## 🗺️ Map Data Credit

Campus geometry © OpenStreetMap contributors (ODbL), stored in `tools/campus-osm.xml` and compiled into `dist/campus-data.json`. Three.js is MIT-licensed (`dist/vendor/THREE-LICENSE.txt`).

---

*Entry with permission. Exit with verification.*
