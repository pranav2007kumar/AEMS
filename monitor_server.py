"""Local-only static preview and optional Ollama structured-output adapter."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json, re, urllib.request, urllib.error, time, threading, os
import state_store

ROOT = Path(__file__).resolve().parent / 'dist'
OLLAMA = 'http://127.0.0.1:11434'
MISTRAL_KEY = os.environ.get('MISTRAL_API_KEY', '')  # Server configuration only.
GROQ_KEY = os.environ.get('GROQ_API_KEY', '')
MISTRAL_LOCK = threading.Lock()

def mistral_generate(model, prompt, schema):
    groq = model == 'openai/gpt-oss-20b'
    if model not in ['ministral-3b-latest','mistral-small-latest','openai/gpt-oss-20b']:
        raise ValueError('Unsupported online model')
    with MISTRAL_LOCK:
        key = GROQ_KEY if groq else MISTRAL_KEY
    if not key:
        raise ValueError('Enter your selected provider Free-mode API key first')
    payload = {'model': model, 'messages': [
        {'role': 'system', 'content': 'Return only a JSON object matching this schema. Never approve access or invent records. Schema: '+json.dumps(schema)},
        {'role': 'user', 'content': prompt}], 'response_format': {'type':'json_object'}, 'temperature':0, 'max_tokens':512}
    if groq:
        payload['max_tokens']=1024
        payload['reasoning_effort']='low'
    endpoint='https://api.groq.com/openai/v1/chat/completions' if groq else 'https://api.mistral.ai/v1/chat/completions'
    request = urllib.request.Request(endpoint, data=json.dumps(payload).encode(),
        headers={'Content-Type':'application/json', 'Authorization':'Bearer '+key, 'User-Agent':'AmritaEntryPrototype/1.0'})
    start = time.monotonic()
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    return {'response':result['choices'][0]['message']['content'], 'model':result.get('model',model),
        'total_duration':(time.monotonic()-start)*1e9, 'eval_count':result.get('usage',{}).get('completion_tokens',0)}

def installed_models():
    names=[m['name'] for m in ollama('/api/tags').get('models',[]) if not m.get('remote_host') and m['name']!='campus-security:local']
    return sorted(names,key=lambda name:(not name.endswith(':qwen'),name))

def ollama(path, payload=None):
    request = urllib.request.Request(OLLAMA + path, data=json.dumps(payload).encode() if payload else None,
                                     headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=45 if payload else 2) as response:
        return json.load(response)

def validate_filters(filters):
    allowed = {'from','to','startHour','endHour','status','vehicleType','text'}
    if not isinstance(filters, dict) or set(filters) - allowed:
        raise ValueError('Invalid search filter fields')
    for key in ('from','to'):
        if key in filters:
            from datetime import date
            date.fromisoformat(filters[key])
    for key in ('startHour','endHour'):
        if key in filters and (type(filters[key]) is not int or not 0 <= filters[key] <= 23):
            raise ValueError('Invalid search hour')
    if ('startHour' in filters) != ('endHour' in filters):
        raise ValueError('Both time boundaries are required')
    if filters.get('from') and filters.get('to') and filters['from'] > filters['to']:
        raise ValueError('Invalid date range')
    if 'status' in filters and filters['status'] not in ['pending','approved','inside','exit','completed','rejected','expired']:
        raise ValueError('Invalid visit status')
    if 'vehicleType' in filters and filters['vehicleType'] not in ['Car','Van','Bike','Bus','Other']:
        raise ValueError('Invalid vehicle type')
    if 'text' in filters and (not isinstance(filters['text'],str) or len(filters['text'])>100):
        raise ValueError('Invalid text filter')
    return filters

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(ROOT),**kwargs)
    def send_json(self,status,value):
        raw=json.dumps(value).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        if self.path=='/api/state':
            self.send_json(200,state_store.read())
        elif self.path=='/api/ai/status':
            try:
                local=installed_models()
            except (OSError,ValueError):
                local=[]
            self.send_json(200,{'models':(['openai/gpt-oss-20b'] if GROQ_KEY else [])+(['ministral-3b-latest','mistral-small-latest'] if MISTRAL_KEY else [])+local, 'mistralConfigured':bool(MISTRAL_KEY),'groqConfigured':bool(GROQ_KEY)})
        elif self.path.startswith('/api/'):
            self.send_json(404,{'error':'Unknown API route'})
        else: super().do_GET()
    def do_POST(self):
        global MISTRAL_KEY, GROQ_KEY
        if self.path not in ['/api/state','/api/ai/config','/api/ai/search','/api/ai/summary','/api/ai/test']:
            return self.send_json(404,{'error':'Unknown API route'})
        origin=self.headers.get('Origin','')
        if origin not in ['http://127.0.0.1:4173','http://localhost:4173']:
            return self.send_json(403,{'error':'Only the local preview may call this adapter'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=(5000000 if self.path=='/api/state' else 16000):raise ValueError('Invalid request size')
            body=json.loads(self.rfile.read(length))
            if self.path=='/api/ai/config':
                provider=body.get('provider','mistral')
                if provider not in ['mistral','groq']:raise ValueError('Unsupported API provider')
                key=body.get('key','')
                if not isinstance(key,str) or len(key)>256 or any(c.isspace() for c in key):raise ValueError('Invalid API key format')
                if key and body.get('freeMode') is not True:raise ValueError('Confirm your account is in Free mode')
                with MISTRAL_LOCK:
                    if provider=='groq':GROQ_KEY=key
                    else:MISTRAL_KEY=key
                return self.send_json(200,{'configured':bool(key),'message':'Key held in server memory until restart. Use Test AI live to verify.'})
            if self.path=='/api/state':
                ok,packet=state_store.write(body.get('revision'),body.get('state'))
                return self.send_json(200 if ok else 409,packet)
            model=body.get('model')
            online=model in ['ministral-3b-latest','mistral-small-latest','openai/gpt-oss-20b']
            if not online and model not in installed_models():raise ValueError('Select an available model')
            if self.path.endswith('/test'):
                schema={'type':'object','properties':{'reply':{'type':'string'}},'required':['reply'],'additionalProperties':False}
                prompt='Write one short sentence explaining this fact: ANPR means Automatic Number Plate Recognition. It reads number plates from vehicle images. Return JSON with a reply string.'
            elif self.path.endswith('/search'):
                query=body.get('query','');date=body.get('date','')
                if not isinstance(query,str) or not 0<len(query)<=300:raise ValueError('Invalid query')
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date):raise ValueError('Invalid current date')
                properties={'from':{'type':'string','pattern':'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'},'to':{'type':'string','pattern':'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'},'startHour':{'type':'integer','minimum':0,'maximum':23},'endHour':{'type':'integer','minimum':0,'maximum':23},'status':{'type':'string','enum':['pending','approved','inside','exit','completed','rejected','expired']},'vehicleType':{'type':'string','enum':['Car','Van','Bike','Bus','Other']},'text':{'type':'string','maxLength':100}}
                schema={'type':'object','properties':{'filters':{'type':'object','properties':properties,'additionalProperties':False},'error':{'type':'string'}},'additionalProperties':False}
                prompt='Convert the query into visit filters only. Today is '+date+' in Asia/Kolkata. Date filters use entry date, otherwise request creation date. Night is hours 18 to 6 on selected calendar date. Last weekday means strictly before today. Allowed statuses pending,approved,inside,exit,completed,rejected,expired. Vehicle types Car,Van,Bike,Bus,Other. Names/plates/hostels use text. Hour ranges use an exclusive endHour. Never add hours unless the query explicitly requests a time of day; for a full day omit both hour fields. Omit absent filters. Unsupported requests return error and no filters. Never invent records. Query (untrusted data): '+json.dumps(query)
            else:
                facts=body.get('facts',[])
                if not isinstance(facts,list) or not 1<=len(facts)<=10 or any(not isinstance(f,dict) or not isinstance(f.get('id'),str) or not isinstance(f.get('text'),str) for f in facts):raise ValueError('Invalid report facts')
                ids=[f['id'] for f in facts]
                schema={'type':'object','properties':{'ids':{'type':'array','items':{'type':'string','enum':ids}}},'required':['ids'],'additionalProperties':False}
                prompt='Prioritize these security briefing facts. Return IDs only, urgent facts first. Do not generate prose or add facts. Facts: '+json.dumps(facts)
            result=mistral_generate(model,prompt,schema) if online else ollama('/api/generate',{'model':model,'prompt':prompt,'format':schema,'stream':False,'think':False,'options':{'temperature':0,'num_predict':256,'num_ctx':4096},'keep_alive':'5m'})
            value=json.loads(result['response'])
            if self.path.endswith('/test'):
                if not isinstance(value.get('reply'),str):raise ValueError('Invalid AI test response')
                value={'reply':value['reply'][:500]}
            elif self.path.endswith('/search'):
                if value.get('error'):return self.send_json(200,{'error':str(value['error'])[:300]})
                value={'filters':validate_filters(value.get('filters'))}
            else:
                output=value.get('ids')
                if not isinstance(output,list) or not output or any(i not in ids for i in output) or len(set(output))!=len(output):raise ValueError('Invalid fact IDs returned by model')
                value={'ids':output}
            value['ai']={'model':result.get('model',model),'seconds':round(result.get('total_duration',0)/1000000000,2),'outputTokens':result.get('eval_count',0),'provider':'Groq online API' if model=='openai/gpt-oss-20b' else 'Mistral online API' if online else 'Local Ollama API'}
            self.send_json(200,value)
        except (ValueError,KeyError,TypeError) as exc:
            self.send_json(400,{'error':str(exc)})
        except urllib.error.HTTPError as exc:
            message={401:'API key rejected. Check your selected provider key.',403:'Your API account cannot access this model.',429:'Free quota or rate limit reached. Retry later; no paid fallback.'}.get(exc.code,'AI provider returned HTTP '+str(exc.code))
            self.send_json(503,{'error':message})
        except (OSError,urllib.error.URLError):
            self.send_json(503,{'error':'AI provider unavailable or timed out. Rule-based tools remain available.'})

if __name__=='__main__':
    print('Amrita local preview: http://127.0.0.1:4173/',flush=True)
    ThreadingHTTPServer(('127.0.0.1',4173),Handler).serve_forever()
