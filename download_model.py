"""Fetch a verified official Ollama blob with bounded parallel HTTP ranges."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib,json,urllib.request
BASE=Path(__file__).resolve().parent/'runtime'
manifest=json.loads((BASE/'smollm-manifest.json').read_text())
layer=next(x for x in manifest['layers'] if x['mediaType']=='application/vnd.ollama.image.model')
digest=layer['digest'];size=layer['size']
url='https://registry.ollama.ai/v2/library/smollm2/blobs/'+digest
with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=30) as response:
    resolved=response.url
def part(index):
    start=size*index//8;end=size*(index+1)//8-1
    req=urllib.request.Request(resolved,headers={'Range':f'bytes={start}-{end}'})
    dest=BASE/f'small-model-part-{index}'
    with urllib.request.urlopen(req,timeout=90) as response:
        if response.status!=206 or not response.headers.get('Content-Range','').startswith(f'bytes {start}-{end}/'):
            raise ValueError('Server did not honor the requested range')
        with dest.open('wb') as output:
            while chunk:=response.read(1024*1024):output.write(chunk)
    if dest.stat().st_size!=end-start+1:raise ValueError('Incomplete range')
    return index
with ThreadPoolExecutor(max_workers=8) as pool:
    for future in as_completed([pool.submit(part,i) for i in range(8)]):print('Downloaded part',future.result()+1,'of 8',flush=True)
output=BASE/'smollm-model.gguf';checksum=hashlib.sha256()
with output.open('wb') as dest:
    for i in range(8):
        with (BASE/f'small-model-part-{i}').open('rb') as source:
            while chunk:=source.read(1024*1024):checksum.update(chunk);dest.write(chunk)
if checksum.hexdigest()!=digest.split(':')[1]:raise ValueError('Model checksum mismatch')
print('Verified official model SHA-256:',checksum.hexdigest(),flush=True)
