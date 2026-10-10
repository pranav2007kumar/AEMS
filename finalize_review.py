from pathlib import Path
import re
root=Path(__file__).parent
p=root/'dist/security-head.js'
s=p.read_text(encoding='utf-8')
for char in ['·','—','→','–','…','←']:
    s=s.replace(char.encode('utf-8').decode('cp1252',errors='replace'),char)
p.write_text(s,encoding='utf-8')
page=(root/'dist/tech-journey.html').read_text(encoding='utf-8')
scripts=re.findall(r"script:'(.*?)'\}",page)
names=re.findall(r"\{name:'(.*?)',seconds:(\d+)",page)
assert len(scripts)==len(names)==8
notes=['# Round 2: Tech Stack and AI Usage','', 'Open http://127.0.0.1:4173/tech-journey.html and click Start 3-minute tour. Read each checkpoint’s presenter notes or rehearse the script below. The HTML also works offline by opening the file directly.','']
for (name,duration),script in zip(names,scripts):
    notes += [f'## {name} — {duration} seconds','',script,'']
notes += ['## Questions judges may ask','',
'**Where is the AI?** Planned YOLO detection and PaddleOCR recognition handle plate images. The Mistral adapter supports natural-language search and prioritizing verified briefing facts. Directory lookup, approval checks and current anomaly rules are ordinary software.', '',
'**Is Mistral working now?** The adapter is implemented. Online inference is verified only after a Free-mode key is entered and Test AI live succeeds. Do not describe the camera pipeline as connected yet.', '',
'**Does this reduce a two-to-three-minute inspection to five seconds?** No. It removes repeated registration and slip checking. Every vehicle is still physically inspected. Pre-registration and checks can run while guards inspect; additional staffed lanes increase throughput. Measure total waiting time in a pilot.', '',
'**What happens after a flag is reported?** It becomes an assigned incident visible to gate security or the warden. Staff acknowledge, investigate, record the outcome and resolve it. The full timeline is retained. A flag does not automatically blacklist a visitor or cancel permission.', '',
'**What if AI is wrong or offline?** Guards correct misread plates and recheck approval. Search and reports retain deterministic tools. AI never grants entry or exit.', '',
'**How is data connected?** The visitor, warden, security and head portals share revision-checked local SQLite records through the Python API. Production deployment needs authenticated roles and a campus-hosted server.', '',
'**What is sent to Mistral?** Search question and date, or aggregate briefing facts. Full visitor records and images are not automatically uploaded. Avoid private identifiers in online questions. The API key is held only in server memory.', '']
(root/'Round_2_Preparation.md').write_text('\n'.join(notes),encoding='utf-8')
assert sum(int(t) for _,t in names)==180
assert not re.search(r'https?://|fetch\(|<script[^>]+src=|@import',page)
print('Presentation checked: 8 stages, 180 seconds, self-contained. Preparation notes saved.')
