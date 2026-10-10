from pathlib import Path
root=Path(__file__).parent
p=root/'dist/security-head.js'
s=p.read_text(encoding='utf-8')
s=s.replace('Mistral online API + local backup','Groq / Mistral online API + local backup')
s=s.replace('Mistral needs your own Free-mode key.','Groq or Mistral needs your own Free-mode key.')
s=s.replace('<form id="head-mistral-config"><label','<form id="head-mistral-config"><label class="field">Online provider<select id="head-provider"><option value="groq">Groq</option><option value="mistral">Mistral</option></select></label><label')
s=s.replace('Mistral API key<input','Online API key<input').replace('I confirm my Mistral account','I confirm my selected provider account').replace('Connect Mistral','Connect online AI').replace('Disconnect Mistral','Disconnect selected provider')
s=s.replace('Create a free key</a>','Mistral key</a><a href="https://console.groq.com/keys" target="_blank" rel="noopener">Groq key</a>')
s=s.replace("key:input.value.trim(),freeMode:","provider:document.querySelector('#head-provider').value,key:input.value.trim(),freeMode:")
s=s.replace("headProof='Mistral key configured.","headProof='Online key configured.")
s=s.replace("JSON.stringify({key:''})","JSON.stringify({provider:document.querySelector('#head-provider').value,key:''})")
s=s.replace("headProof='Mistral disconnected.'","headProof='Selected provider disconnected.'").replace('Enter a Mistral key or start','Enter an online API key or start')
p.write_text(s,encoding='utf-8')
p=root/'dist/tech-journey.html'
s=p.read_text(encoding='utf-8').replace('Mistral API adapter + local backup','Groq API adapter + optional backups').replace('Mistral API adapter','Groq API adapter').replace('Mistral use requires a Free-mode API key and a successful live test.','Groq online inference is connected; search and briefing return validated outputs. Camera integration is still planned.')
p.write_text(s,encoding='utf-8')
p=root/'Round_2_Preparation.md'
s=p.read_text(encoding='utf-8').replace('Mistral','Groq').replace('Ministral 3B','GPT-OSS 20B').replace('Free-mode','Free-plan')
p.write_text(s,encoding='utf-8')
