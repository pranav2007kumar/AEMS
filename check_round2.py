from pathlib import Path
import re
root=Path(__file__).parent
page=(root/'dist/tech-journey.html').read_text(encoding='utf-8')
assert sum(map(int,re.findall(r'seconds:(\d+)',page)))==180
assert not re.search(r'https?://|fetch\(|<script[^>]+src=|@import',page)
assert 'Groq API adapter' in page
p=root/'Round_2_Preparation.md'
s=p.read_text(encoding='utf-8').replace('Groq GPT-OSS 20B was verified','Groq-hosted GPT-OSS 20B was verified')
p.write_text(s,encoding='utf-8')
print('Round 2: 8 checkpoints, 180 seconds, offline HTML and Groq preparation notes verified.')
