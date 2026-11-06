"""Separate enlarger exposure from coating scatter using identical synthetic negatives."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.special import gammainc
from wet_print import film,paper,reflection,process,encode,STOCK

def rgb(dyes,scatter):
    linear=reflection(dyes,scatter=scatter)@STOCK.viewer
    return encode(linear.mean(axis=(0,1))).tolist()

def diagnose():
    report={'paper_exposure':.35,'coating_scatter':.01,'neutral_patches':{},'direct_paper_wedge':[]}
    for code in (0,32,64,96,128,160,192,224,255):
        negative=film(np.full((64,64,3),code,np.uint8))
        previous=paper(negative,exposure=1)
        corrected=paper(negative,exposure=.35)
        report['neutral_patches'][str(code)] = {
            'previous':rgb(previous,.35),
            'exposure_only':rgb(corrected,.35),
            'scatter_only':rgb(previous,.01),
            'corrected':rgb(corrected,.01)}
    # Isolated uniform emulsion fields omit sampling variance for a smooth wedge.
    for h in np.geomspace(.0001,4,49):
        p=sum(gammainc(4,h*s) for s in (12,30,75))/3
        amount=process(np.full((4,4),p),55,.14)
        dyes=np.repeat(amount[:,:,None],3,axis=2)
        report['direct_paper_wedge'].append(
            {'relative_exposure':float(h),'dye':float(amount.mean()),
             'previous_scatter':rgb(dyes,.35),'corrected_scatter':rgb(dyes,.01)})
    corrected=np.array([v['corrected'] for v in report['neutral_patches'].values()])
    assert np.all(np.diff(corrected,axis=0)>0)
    assert corrected[0].max()<35 and corrected[-1].min()>215
    assert np.max(np.ptp(corrected,axis=1))<=3
    assert 115<=corrected[4].mean()<=135
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('output',type=Path)
    args=p.parse_args()
    args.output.write_text(json.dumps(diagnose(),indent=2))
