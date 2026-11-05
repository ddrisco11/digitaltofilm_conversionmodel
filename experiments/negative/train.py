"""Fit on prepared real scan/print pairs; evaluate by held-out roll."""
import argparse,json
from pathlib import Path
import numpy as np
from negative_pipeline import HERE,as_density,features,develop
parser=argparse.ArgumentParser()
parser.add_argument('cache',type=Path)
args=parser.parse_args()
rows=json.loads((HERE/'manifest.json').read_text())['rows']
def load(r):
    with np.load(args.cache/('aligned-'+r['id']+'.npz')) as data:
        return [data[k] for k in ('negative','positive','mask')]
train=[r for r in rows if r['split']=='train']
bounds=[]; xs=[];ys=[]
rng=np.random.default_rng(193)
for r in train:
    n,p,mask=load(r);d=as_density(n)
    h,w=d.shape[:2]
    bounds.append(np.percentile(d[h//10:-h//10,w//10:-w//10],[2,98],axis=(0,1)))
    idx=rng.choice(mask.sum(),3000,replace=False)
    xs.append(d[mask][idx]);ys.append(p[mask][idx])
lo,hi=np.median(bounds,axis=0)
z=np.clip((np.vstack(xs)-lo)/(hi-lo),-.5,1.5);f=features(z);y=np.vstack(ys)
weights=np.linalg.solve(f.T@f+2*np.eye(f.shape[1]),f.T@y)
model=dict(lo=lo,hi=hi,weights=weights)
np.savez(HERE/'model.npz',**model)
report=[]
for r in rows:
    if r['split']!='test':continue
    n,p,mask=load(r);pred=develop(n,model)
    # Fixed density stretch; no positive target is used by either decoder.
    base=np.clip((as_density(n)-lo)/(hi-lo),0,1)
    row=dict(frame=r['id'])
    for name,result in [('stretch',base),('developer',pred)]:
        err=(result-p)[mask];row[name+'_mae_255']=float(np.mean(np.abs(err))*255)
        row[name+'_psnr_db']=float(-10*np.log10(np.mean(err**2)))
    report.append(row)
(HERE/'scores.json').write_text(json.dumps(report,indent=2)+'\n')
print(report)
