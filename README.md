# Amrita University Entry Monitoring System

Static hackathon prototype styled after the supplied Amrita student portal reference.

Run `python monitor_server.py` from this directory and open http://127.0.0.1:4173/. This serves the static prototype and optional local AI adapter, bound to loopback only.

Four interfaces: Security Head monitoring at `/#head`, plus visitor requests and status tracking; warden entry and exit approvals; security plate correction, approval lookup, entry/exit records and audit history.

Student lookup: enter `CB.CSE.DEMO01`, `CB.ECE.DEMO02`, or `CB.AI.DEMO03` (or select a sample button). Name, branch, hostel, and warden fill automatically. Unknown IDs cannot submit; assignments come from the sample directory rather than parent selection. ID-card image upload/OCR is not included.

Hostel directions: track approved sample request `AMV-DEMO01` and select Directions. The Three.js 3D scene includes detailed buildings, trees, shadows, road markings, and a highlighted route. Drag to rotate, scroll/pinch to zoom, select a route step, or play the vehicle tour. Reset, top view, and fullscreen controls are available. Three.js 0.180.0 is served locally from `dist/vendor`.

The active renderer is `dist/campus-real.js`, using 99 OSM building footprints and 61 mapped roads/paths. Real hostel names and official contact information are shown. Building heights, facade detail and trees are illustrative. Routes are public-map approach previews, not approved visitor driving directions. See `CAMPUS_SOURCES.md` for all source links and limitations.

Enable GPS requests browser location permission and uses `watchPosition` for live coordinates and accuracy. GPS coordinates stay on the device; the watch stops when leaving the directions page. The model is georeferenced to the OSM main gate. A location fix inside the mapped campus boundary enables the blue position marker, accuracy circle and Follow GPS. Outside-campus fixes display that status. Desktop GPS may be imprecise. Real-device GPS tracking and approved visitor routes require an on-campus check.

Sample flow: scan TN38AB1234 in Security, verify and record entry, approve its exit in Warden after checking the verification box, then scan at the exit gate and record departure. KL07CD5678 starts with entry approval pending.

Data lives in localStorage in the same browser/origin. Student/visitor names and warden assignments are fictional demo records; campus building names and geometry come from public sources. This prototype does not include real ANPR, role authentication, a shared backend, university student records, camera snapshots, or physical gate control. Production use needs these integrations and verified institutional approval rules. Never use real visitor personal data in this demo.


## Security Head monitoring

`/#head` includes inspection queue inputs and lane suggestions; hourly-average traffic forecasts; full visit and audit history with CSV/JSON export; visit timelines; configurable outside-hours and dwell-time flags with persistent review notes; plain-language filtering and downloadable dated security briefings. Browser records and generated 15-day sample history are separate sources. Sample history is never inserted into visit/audit storage. Review notes and queue settings are browser-local.

Queue counting currently uses manual observations, not camera detection. The queue estimate assumes a uniform service duration, idle lanes, and no new arrivals; it does not reduce the physical inspection required for every vehicle. Entry confirmation now requires a guard's physical-inspection confirmation in addition to plate/visitor verification. `lookupToPassageSeconds` is elapsed time since the last approval lookup, not measured inspection duration.

Forecasts use mean hourly counts across recorded dates within the previous 14 complete calendar days, require at least 3 recorded dates, and exclude today's incomplete traffic. Missing dates are not counted as zero-traffic dates. Anomalies are rule-based review flags, not a trained ML classifier or evidence of misconduct.

Plain-language search falls back to a deterministic parser: dates, last weekday, time-of-day, vehicle type, status and vehicle plates. Unknown words trigger clarification. Night means 18:00–05:59 on the selected calendar date, not a period spanning two date filters. Historic records lacking vehicle type do not match type filters. Results are always retrieved from existing selected records.

Optional LLM: install/run Ollama separately with an installed local model. Under Search & daily briefing → Local LLM connection, check the connection, select a model and explicitly enable Use local LLM. The adapter uses Ollama structured JSON outputs (`https://ollama.com/blog/structured-outputs`), validates returned filters, and never asks the model to invent record results. Daily briefings let the model order verified aggregate fact IDs; report text is assembled from those facts. Missing/offline models leave deterministic tools available. No model is bundled or downloaded automatically. Server-side guards restrict adapter calls to the local preview origin; this is not production authentication.

Run `node test_head.cjs` and `node check_lookup.cjs` for analytics and existing student/directions checks. `node test_inspection.cjs` verifies mandatory inspection plus approval/exit safeguards in isolated storage. `python -m unittest test_monitor_server.py` verifies adapter validation without a running LLM.


## Connected local prototype

All four portals now share a revision-checked SQLite snapshot at `data/gate-state.sqlite3` through `/api/state`. Existing browser data is imported when the database is empty; subsequent sessions load server records. Browser snapshots are kept as backups. Conflicting saves are rejected and the latest state is loaded, with the rejected snapshot kept in `amrita-conflict-backup`; staff must review and repeat the action. Polling occurs every five seconds. This loopback-only preview shares across browsers on this computer, not across campus devices; authentication and deployment are still required.

Reported flags create assigned incidents. Gate security or the warden acknowledges the incident, records an investigation note, and resolves it with an outcome. The head sees the incident timeline. No automatic blacklist, permission cancellation, barrier operation, SMS or email is triggered. Sample incidents stay labelled and do not alter real visit permission. Briefing facts include inspections and incident counts.

The free local Ollama API runs at 127.0.0.1:11434, cloud disabled, with CPU runtime and models stored under `runtime/`. The security-head page discovers installed models. Search and summary responses include real model name, elapsed inference time and token count. Under Local LLM connection, Test AI live calls `/api/ai/test` and shows an actual generated response.

Standalone presentation: `dist/tech-journey.html`. One self-contained file, no network requests or libraries, with an exact 180-second tour, manual checkpoints, speaker script, keyboard controls and print layout. Open it directly from disk for an offline review.

## Mistral online connection and Round 2

Security head → Search & daily briefing → Mistral online API + local backup supports Mistral chat completions through the Python server. Use a Mistral Studio account in Free mode. The app cannot inspect the account's billing plan; do not enable paid billing. There is no automatic paid fallback or retry. The default online model is `ministral-3b-latest`; `mistral-small-latest` is also selectable but returned a quota limit during verification. Search questions and date context, or aggregate briefing facts, are sent to Mistral; complete visit records and images are not uploaded automatically. Avoid private details in online search questions.

The provided key is held only in server memory, not files, browser storage or SQLite. Re-enter it after a server restart. The live test, completed-visits-yesterday filter extraction, and fact-ID prioritization were verified against Mistral on 11 October 2026. The browser retrieves matching records locally and appends all remaining verified briefing facts, so an incomplete model ordering cannot remove facts. Physical inspection and human approval remain mandatory.

Groq is now the selected online provider. `openai/gpt-oss-20b` was verified through `/api/ai/test`, `/api/ai/search`, and `/api/ai/summary`: 0.75 s generic test, 1.00 s structured date/status search, and 0.59 s verified fact ordering in this run. These are individual observations, not latency guarantees. The key stays in server memory. The UI provides Groq and Mistral setup fields; use the provider's Free plan and do not upgrade billing. Provider quota errors do not trigger paid fallback. The adapter sends a descriptive app User-Agent required by the Groq gateway.

`Round_2_Preparation.md` contains the timed speaking script and likely judge questions. The presentation distinguishes implemented workflows and Mistral assistance from the planned camera/YOLO/PaddleOCR integration.
