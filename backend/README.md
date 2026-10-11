# Campus gate backend

The full-stack backend runs at **http://127.0.0.1:4174/** by default. Interactive API documentation: **http://127.0.0.1:4174/docs**.

## Start

From the repository root, run `pip install -r backend/requirements.txt`, then `PYTHONPATH=. python -u backend/run.py` (or `backend/start.ps1` on Windows). Port defaults to 4174.

Local accounts and generated passwords are in `data/backend-demo-accounts.txt`. They are not source controlled. This is a local demonstration; do not expose demo accounts publicly. Sessions use HttpOnly cookies, signed JWTs, server-side revocation and assigned roles. Passwords use salted scrypt hashes.

The loopback demo runner also accepts **1234 / 1234** in each staff portal. The selected portal determines the authenticated role; the warden sign-in lets you choose Menon or Devi. Original named accounts remain available. This shared demo login is rejected in production and for non-loopback requests; set `LOCAL_DEMO_LOGIN=0` to disable it locally. Visitor submissions do not require sign-in.

## Functional workflows

### Security-head and guard dashboard additions

The guard dashboard contains a prominent **Open registered vehicles** button. Both guards and head staff can search registrations by plate, owner, category or purpose, filter active/suspended/expired registrations, and export the filtered CSV. Approval and suspension remain head/admin actions.

The head dashboard includes **Campus occupancy**, **Recognition & review** and **System settings**, alongside existing incidents, visit/audit history and AI briefing. It shows occupancy versus capacity, current vehicles inside, registered-vehicle totals, the last 12 hours of recognition activity, recorded decision counts and a queue of uncertain/unknown reads. Recognition history preserves the original OCR text, capture/receipt timestamps, confidence, reason code and staff correction note. Recorded and current permission decisions are shown separately.

Head/admin can configure capacity, the recognition score threshold and normal/lockdown entry policy through `/api/v1/access-policy`. Entry confirmation for both registered and visitor vehicles rechecks these settings on the server. Lockdown does not disable departure. Policy versions serialize entry/capacity checks against concurrent policy changes. `/api/v1/monitoring/overview` is head/admin only; read review uses `/api/v1/anpr/detections/{id}/review`. A review never invents warden approval or confirms passage. Invalid-format/low-confidence readings become HOLD records instead of being silently corrected. The backend does not guess O/0 or I/1.

The backend connection banner pauses dashboard edits on network failure and provides Retry. There is no automatic switch to browser demo decisions. The supplied model still is not loaded or executed by this build.

| Function | Backend behavior |
|---|---|
| Visitor request | Validates details; looks up the student, hostel and assigned warden; issues a private tracking token |
| Warden | Can approve only assigned students; confirms the meeting before authorizing visitor exit |
| Guard | Checks approval, visible plate/visitor and inspection; records entry and exit atomically |
| Registered vehicle | Head/admin approves owner, category, purpose and expiry; guard performs an exact match and records inspected entry without a new warden request |
| Suspension / expiry | Blocks new registered entry; a vehicle already inside can still have departure recorded |
| Duplicate protection | Unique occupancy record prevents the same plate entering concurrently through registered and visitor workflows |
| Gate history | Separate passage records preserve each registered entry/exit and the authenticated guard; audit history records approval/suspension/actions |
| Incident follow-up | Head assigns visitor incidents; assigned role investigates and records the outcome; flags do not silently change passage permissions |
| Queue / analytics | Server computes queue estimates and historical counts, including registered passages; forecasting is a historical hourly baseline, not a trained ML model |
| AI chat / briefing | Head/admin only; backend supplies authorized aggregate facts and validates outputs; AI cannot grant permissions |
| Tailgating demonstration | Each entry creates a one-vehicle cycle; guard simulates a vehicle count; more than one raises an alert and prevents further entry recording until an investigation outcome is recorded |

**Inspection remains mandatory for every incoming vehicle.** Recognition and registration do not establish occupant identity. Real camera recognition, automatic vehicle counting, physical barrier control and verified campus GPS coordinates still require hardware/data integration. Tailgating currently uses explicitly labelled manual simulation; the backend does not physically hold or close a barrier.

Guards must enter `person_count` (1–100, including the driver) at entry and exit for visitors and registered vehicles. The database stores separate `entry_person_count` and `exit_person_count` per visit/passage. A mismatch returns HTTP 409 without recording departure or removing occupancy. Older records retain missing counts rather than invented values; missing entry counts block departure and require staff review. Guards must still physically verify the occupants; matching numbers alone do not confirm their identities.

## Live camera and optional model inference

The guard dashboard has Start camera, Stop camera and Recognize current frame controls. Browser camera access is requested only when the guard clicks Start camera; audio is disabled. Localhost or HTTPS is required. Leaving the page stops the camera tracks. Frames are sent to the local backend only when Recognize is clicked, and are processed in memory rather than saved as images.

`GET /api/v1/anpr/camera-status` reports configuration without loading any model. `POST /api/v1/anpr/frames` accepts a bounded JPEG/PNG frame from an authenticated guard, uses the supplied `backend/models/campus-anpr.pt` through an optional Ultralytics detector, reads cropped plates with local EasyOCR, and passes the result into the audited detection API. Multiple plates and unreadable frames require manual review. Recognition never records passage automatically.

Inference remains disabled unless `ANPR_ENABLE_INFERENCE=1` is explicitly set before starting the server. Install `backend/requirements-anpr.txt` into the backend runtime and provision EasyOCR English recognition and detection weights in `backend/models/ocr/` before enabling it. The runtime disables automatic OCR downloads. The supplied model's format/classes and real recognition accuracy remain unverified until loading/running is authorized. No model is imported or executed by startup, camera-status checks, or the integration tests (which mock recognition).

## Database tables

`data/campus-gate.sqlite3` stores normalized relational tables: users, login_sessions, students, hostels, gates, visits, approvals, inspections, gate_events, incidents, incident_actions, audit_logs, settings, registered_vehicles, registered_passages, vehicle_occupancy, barrier_cycles and plate_detections. Foreign keys, unique indexes, optimistic versions and atomic commits enforce workflow rules. Alembic migrations run on startup. SQLite WAL is enabled.

Original demo data remains in `data/gate-state.sqlite3`; a backup and migration report are in `data/backups` and `data/legacy-migration-report.json`. Sample student records remain labelled sample. PostgreSQL deployment is not tested.

## API endpoints

| Method | Path | Access / purpose |
|---|---|---|
| POST / GET / POST | `/api/v1/auth/login`, `/auth/me`, `/auth/logout` | Staff session |
| GET | `/api/v1/students/{id}` | Sample directory lookup; non-sample directory protected |
| POST | `/api/v1/visits` | Visitor request creation |
| GET | `/api/v1/public/visits/{id}` | Requires private `X-Visit-Token` |
| GET | `/api/v1/visits`, `/visits/{id}` | Authorized staff; paginated list |
| POST | `/api/v1/visits/{id}/entry-approval`, `/exit-approval` | Assigned warden |
| POST | `/api/v1/visits/{id}/inspection`, `/entry`, `/exit` | Guard; version and workflow checks |
| GET / POST | `/api/v1/registered-vehicles` | Guard/head/admin read; head/admin approve |
| PATCH | `/api/v1/registered-vehicles/{id}` | Head/admin activate or suspend |
| GET | `/api/v1/registered-vehicles/lookup/{plate}` | Exact normalized plate, expiry/active check and active passage |
| POST | `/api/v1/registered-vehicles/{id}/entry` | Guard; mandatory inspection and occupant verification |
| POST | `/api/v1/registered-passages/{id}/exit` | Guard; records actual departure |
| GET | `/api/v1/barrier-cycles` | Guard/head/admin history and alerts |
| POST | `/api/v1/barrier-cycles/{id}/count` | Guard; manual detector simulation |
| POST | `/api/v1/barrier-cycles/{id}/resolve` | Guard/head/admin investigation outcome |
| GET / POST | `/api/v1/incidents` | Authorized follow-up / head creates |
| POST | `/api/v1/incidents/{id}/actions` | Assigned role / head |
| GET / PATCH | `/api/v1/settings` | Staff read / head or admin updates |
| GET | `/api/v1/audit-logs`, `/analytics/summary`, `/state` | Authorized data projections |
| POST | `/api/v1/ai/chat`, `/ai/summary` | Head/admin inference |
| GET | `/api/v1/ai/status`, `/health` | AI configuration / health |

Mutable visit, registration, incident and count requests require the current record version; stale changes return 409. The interactive OpenAPI documentation gives exact request schemas. The legacy shared-snapshot write API returns 410.

## AI configuration

## Supplied ANPR model: output connection only

`backend/models/campus-anpr.pt` is a byte-for-byte copy of `C:\Users\prana\Downloads\model.pt.zip`. The file is already a ZIP-based model serialization archive containing `model/data.pkl` and tensor storage; it is not an outer ZIP containing a second `.pt` file. Only the ZIP directory and file hashes were inspected. **No model deserialization, Torch import or inference was performed.**

`backend/anpr_adapter.py` exposes `MODEL_PATH` and `publish_recognition(plate_text, confidence, session_cookie=...)` for an independently operated model/OCR process to call when ready. It posts already-computed output to **POST `/api/v1/anpr/detections`**, requiring a guard session. The backend validates, normalizes and stores the plate, confidence, gate, direction, capture/receipt timestamps and submitting guard. **GET `/api/v1/anpr/detections`** exposes the latest results to authorized staff; the guard can select a result and check its permission. Receiving a prediction never approves passage. Duplicate detection IDs return 409.

The supplied model's architecture/classes and whether it outputs plate text or bounding boxes have not been verified. A plate detector producing only boxes needs an OCR stage before `publish_recognition`. There is no camera/inference startup anywhere in this adapter.

## Provider setup

Set `GROQ_API_KEY` in the backend process environment for direct provider access. No key belongs in browser code or source control. The assistant is optional; without a key the AI endpoints report that it is not configured. Provider keys and responses are not stored in the database. No billing subscription is purchased by this code; free-tier availability depends on the provider account and limits.

## Validation and deployment limits

Run `python -m pytest backend/tests -q` with the dependency path configured. Tests use an isolated database. They cover authorization, private tracking, assigned wardens, failed inspection, stale changes, duplicate passage, incidents, AI context, registered access and tailgating alerts.

This prototype is not a completed production campus deployment. It needs HTTPS hosting, actual staff/student provisioning, account administration, independent security review, backups, durable multi-instance rate limiting, live ANPR/sensor integration and barrier safety interlocks before production use. In-memory rate limiting applies to a single server process. The static Site deployment does not run this Python API.
