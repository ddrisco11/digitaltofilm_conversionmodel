"""Test the two materials on uniform patches, without resetting their balance."""
import json
import sys
from pathlib import Path
import numpy as np
from wet_print import STOCK, film, paper, process, reflection, transmission, encode

def mean(values):
    return np.round(values.mean(axis=(0,1)),5).tolist()

def checks():
    zero=np.zeros((16,16),np.float32)
    assert not np.any(process(zero,45,.11))
    assert not np.any(process(zero+1,0,.11))
    active=zero.copy()
    active[7,7]=1
    dye=process(active,45,.11)
    assert 0<dye.sum()<=1 and dye[7,8]>0
    assert np.all(reflection(np.zeros(3))>reflection(np.ones(3)))
    assert np.all(reflection(np.ones(3),.2)<=reflection(np.ones(3),.94))
    results={}
    for name,rgb in [('black',[0]*3),('gray',[128]*3),('white',[255]*3),
                     ('red',[255,0,0]),('green',[0,255,0]),('blue',[0,0,255]),
                     ('leaf',[136,152,68])]:
        f=film(np.broadcast_to(rgb,(64,64,3)))
        p=paper(f)
        output=reflection(p)@STOCK.viewer
        result=encode(output.mean(axis=(0,1)))
        results[name]=dict(input=rgb,film_cmy=mean(f),paper_cmy=mean(p),print_rgb=result.tolist())
        if name in ('red','green','blue'):
            c=np.argmax(rgb)
            assert c==np.argmax(mean(f))==np.argmin(mean(p))==np.argmax(result)
    assert np.all(np.diff([results[key]['print_rgb'] for key in ('black','gray','white')],axis=0)>0)
    return results

if __name__=='__main__':
    Path(sys.argv[1]).write_text(json.dumps(checks(),indent=2))
