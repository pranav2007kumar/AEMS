from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib,json,urllib.request,math
base=Path(__file__).resolve().parent/'runtime'
manifest=json.loads((base/'qwen3-manifest.json').read_text())
layer=next(x for x in manifest['layers'] if x['mediaType']=='application/vnd.ollama.image.model')
digest=layer['digest'];size=layer['size'];blob=base/'models'/'blobs'/digest.replace(':','-')
partial=Path(str(blob)+'-partial');output=base/'qwen3-verified.gguf'
records=[json.loads(p.read_text()) for p in partial.parent.glob(partial.name+'-*')]
if sum(r['Size'] for r in records)!=size:raise ValueError('Incomplete partition metadata')
gaps=[]
with output.open('wb') as dest,partial.open('rb') as source:
    dest.truncate(size)
    for r in records:
        source.seek(r['Offset']);dest.seek(r['Offset']);left=r['Completed']
        while left:
            chunk=source.read(min(left,1024*1024));dest.write(chunk);left-=len(chunk)
        start=r['Offset']+r['Completed'];end=r['Offset']+r['Size']-1
        if start<=end:gaps.append((start,end))
remaining=sum(b-a+1 for a,b in gaps);chunk_size=math.ceil(remaining/8);ranges=[]
for a,b in gaps:
    while a<=b:
        end=min(b,a+chunk_size-1);ranges.append((a,end));a=end+1
print('Reusing verified-transfer segments; remaining bytes:',remaining,flush=True)
url='https://registry.ollama.ai/v2/library/qwen3/blobs/'+digest
with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=30) as response:resolved=response.url
def fetch(item):
    i,(a,b)=item
    with urllib.request.urlopen(urllib.request.Request(resolved,headers={'Range':f'bytes={a}-{b}'}),timeout=120) as response:
        if response.status!=206 or not response.headers.get('Content-Range','').startswith(f'bytes {a}-{b}/'):raise ValueError('Range mismatch')
        with output.open('r+b') as dest:
            dest.seek(a);total=0
            while chunk:=response.read(256*1024):dest.write(chunk);total+=len(chunk)
            if total!=b-a+1:raise ValueError('Incomplete range')
    return i
with ThreadPoolExecutor(max_workers=8) as pool:
    for future in as_completed([pool.submit(fetch,item) for item in enumerate(ranges)]):print('Finished range',future.result()+1,'/',len(ranges),flush=True)
h=hashlib.sha256()
with output.open('rb') as source:
    while chunk:=source.read(1024*1024):h.update(chunk)
if h.hexdigest()!=digest.split(':')[1]:raise ValueError('Checksum mismatch')
print('Qwen model SHA-256 verified.',flush=True)
