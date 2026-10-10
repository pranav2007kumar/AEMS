# Round 2: Tech Stack and AI Usage

Open http://127.0.0.1:4173/tech-journey.html and click Start 3-minute tour. Read each checkpoint’s presenter notes or rehearse the script below. The HTML also works offline by opening the file directly.

## The problem — 15 seconds

Let us follow one fictional parent vehicle: TN 38 AB 1234. At our campus, visitors currently get out and write their details while security inspects the vehicle. Later, a warden signs a slip for exit. We digitize the record and approvals while keeping the inspection.

## Request — 20 seconds

Before travelling, the parent submits a request with their vehicle number and the student ID. A directory lookup fills the student, branch, hostel and warden. That lookup is ordinary software, not AI. The warden makes the approval decision. Our web interface and Python API share the record through SQLite.

## Capture — 15 seconds

At the main gate, a camera will capture the vehicle. OpenCV prepares the image for the recognition pipeline. In our current prototype, the camera reading is simulated. This lets us demonstrate approvals and correction handling before connecting the real camera and testing under actual lighting and traffic conditions.

## Recognize — 35 seconds

This is the main AI stage. A YOLO detector locates the plate, and PaddleOCR reads the characters inside that region. We normalize spaces and formatting to TN38AB1234. The real pipeline must return confidence and be evaluated for plate accuracy and latency. If glare, motion or a damaged plate causes a misread, the guard checks the visible plate and corrects it. Every correction triggers a fresh approval check. Recognition alone never proves who is inside the vehicle.

## Check — 25 seconds

The plate retrieves the active visit from the records. Software checks the date and the warden’s approval, and handles missing or duplicate requests. This decision uses clear rules, not an LLM. The guard still verifies the visitor and vehicle. Our target is a quick record lookup, but camera-to-decision timing must be measured after integration.

## Inspect — 25 seconds

An approved vehicle still undergoes physical inspection. Our prototype requires that confirmation before recording entry. ANPR does not inspect the boot or vehicle contents. To reduce waiting, the security head can compare queue length with inspection time and available lanes, then consider another staffed lane. This improves capacity; it does not claim to turn a two-minute inspection into five seconds.

## Visit & exit — 25 seconds

Inside campus, the app offers a Three.js campus preview and browser GPS controls to help visitors find their hostel. The parent and student then meet the warden for verification. The warden gives separate exit approval. At the exit gate, the plate retrieves the same visit, and security checks that approval before recording departure.

## Monitor — 20 seconds

The security head sees the full journey. Our Groq API adapter converts plain-language searches into visible filters and orders briefing facts; results come from records. Forecasts and anomaly flags currently use rules. A reported flag starts an assigned investigation, not automatic punishment. Our outcome is less paperwork, retained inspection and a traceable visit.

## Questions judges may ask

**Where is the AI?** Planned YOLO detection and PaddleOCR recognition handle plate images. The Groq adapter supports natural-language search and prioritizing verified briefing facts. Directory lookup, approval checks and current anomaly rules are ordinary software.

**Is Groq working now?** Yes. Groq-hosted GPT-OSS 20B was verified through the app for a live ANPR explanation, completed-visits-yesterday filters, and ordering briefing facts. The key stays in server memory and must be re-entered after restart. Do not describe the camera pipeline as connected yet.

**Does this reduce a two-to-three-minute inspection to five seconds?** No. It removes repeated registration and slip checking. Every vehicle is still physically inspected. Pre-registration and checks can run while guards inspect; additional staffed lanes increase throughput. Measure total waiting time in a pilot.

**What happens after a flag is reported?** It becomes an assigned incident visible to gate security or the warden. Staff acknowledge, investigate, record the outcome and resolve it. The full timeline is retained. A flag does not automatically blacklist a visitor or cancel permission.

**What if AI is wrong or offline?** Guards correct misread plates and recheck approval. Search and reports retain deterministic tools. AI never grants entry or exit.

**How is data connected?** The visitor, warden, security and head portals share revision-checked local SQLite records through the Python API. Production deployment needs authenticated roles and a campus-hosted server.

**What is sent to Groq?** Search question and date, or aggregate briefing facts. Full visitor records and images are not automatically uploaded. Avoid private identifiers in online questions. The API key is held only in server memory.
