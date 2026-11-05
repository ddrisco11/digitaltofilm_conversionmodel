import json,subprocess,concurrent.futures,io,urllib.parse
from pathlib import Path
from PIL import Image
import numpy as np
m=json.loads(Path(__file__).with_name('manifest.json').read_text())
def get(url,byte_range=None):
 args=['curl','-fsSL','--retry','3','--max-time','100']
 if byte_range:args+=['-r',byte_range];url+='?span='+byte_range
 return subprocess.check_output(args+[url])
def fetch(r):
 root='https://huggingface.co/datasets/ttgroup/blueneg-release/resolve/'+m['rev']+'/'
 url=root+urllib.parse.quote(r['negative']);header=get(url,'0-65535');im=Image.open(io.BytesIO(header));tags=im.tag_v2
 offsets,counts=tags[273],tags[279];assert tags[259]==1 and tags[258]==(16,16,16)
 start=min(offsets);end=max(a+b for a,b in zip(offsets,counts))
 blob=get(url,f'{start}-{end-1}');assert len(blob)==end-start
 strips=b''.join(blob[a-start:a-start+b] for a,b in zip(offsets,counts))
 arr=np.frombuffer(strips,dtype='<u2' if header[:2]==b'II' else '>u2').reshape(im.height,im.width,3)
 np.save(r['id']+'.npy',arr)
 pos=Image.open(io.BytesIO(get(root+urllib.parse.quote(r['positive']))))
 pos.thumbnail((800,800));pos.convert('RGB').save(r['id']+'.jpg',quality=96)
 print(r['id'],im.size,np.mean(arr,axis=(0,1)),flush=True)
with concurrent.futures.ThreadPoolExecutor(3) as pool:list(pool.map(fetch,m['rows']))
