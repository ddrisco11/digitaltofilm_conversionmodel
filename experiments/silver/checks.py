"""Controlled exposure, bath, diffusion and conservation checks."""
import json
import numpy as np
from simulate import expose_row, develop

def flat_patch(ev=0, **bath):
    _, hits, mass = expose_row(np.full(8192,.18*2**ev),22,0)
    active = ((hits>=4)*mass).sum(axis=1).reshape(64,128)
    params = dict(time=18,temperature=20,bath=1.)
    params.update(bath)
    silver,c = develop(active,**params)
    assert np.all((silver>=0)&(silver<=active)) and c.min()>=0
    return round(float(silver.mean()),6)

if __name__=='__main__':
    base=flat_patch()
    exposure=[flat_patch(ev) for ev in (-1,0,1)]
    times=[flat_patch(time=t) for t in (0,9,18,36)]
    assert np.all(np.diff(exposure)>0) and np.all(np.diff(times)>0)
    cold,warm=flat_patch(temperature=10),flat_patch(temperature=30)
    dilute=flat_patch(bath=.5)
    assert cold<base<warm and 0==flat_patch(bath=0)<dilute<base
    edge=np.zeros((32,64))
    edge[:,32:]=1
    transport,_=develop(edge,18,20,1)
    isolated,_=develop(edge,18,20,1,diffusion=0)
    gain=float((transport-isolated)[16,32])
    assert gain>0 and np.all(transport[edge==0]==0)
    print(json.dumps(dict(silver_at_minus1_zero_plus1_EV=exposure,
                          silver_at_0_9_18_36_time_units=times,
                          silver_at_10_20_30_C=[cold,base,warm],
                          silver_in_half_strength_bath=dilute,
                          diffusion_edge_silver_gain=gain),indent=2))
