"""Measure acceleration and bound its effect on the rendered pixel codes."""
import json
import sys
import time
from pathlib import Path
import numpy as np
import native
from wet_print import _process_field,reflection,STOCK,encode

rng=np.random.default_rng(6)
active=rng.random((1000,1000),dtype=np.float32)
native.develop(active[:2,:2].copy(),1,.14)
times={}
fields={}
for name,fn in [('reference',_process_field),('native',native.develop)]:
 start=time.perf_counter()
 fields[name]=fn(active,55,.14)
 times[name]=time.perf_counter()-start
error=float(np.max(abs(fields['reference']-fields['native'])))
# Colored dye fields stress the nonlinear spectral-to-display transformation.
base=fields['reference'][::20,::20]
a=np.stack([base,np.roll(base,3,axis=0),np.roll(base,4,axis=1)],axis=-1)
base=fields['native'][::20,::20]
b=np.stack([base,np.roll(base,3,axis=0),np.roll(base,4,axis=1)],axis=-1)
ca=encode(reflection(a)@STOCK.viewer)
cb=encode(reflection(b)@STOCK.viewer)
delta=abs(ca.astype(int)-cb.astype(int))
assert error<2e-6 and delta.max()<=1
report=dict(seconds=times,speedup=times['reference']/times['native'],max_dye_error=error,
            max_srgb8_error=int(delta.max()),changed_channel_fraction=float(np.mean(delta!=0)),
            note='Same equations and float32 state. Compilation excluded. Floating-point results can differ by rounding.')
Path(sys.argv[1]).write_text(json.dumps(report,indent=2))
print(report)
