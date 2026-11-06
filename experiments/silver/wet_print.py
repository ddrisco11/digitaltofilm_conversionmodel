"""Film/print bench. All distances, concentrations and times use relative units."""
import argparse
import json
from pathlib import Path

import colour
import numpy as np
from PIL import Image
from scipy.ndimage import laplace, gaussian_filter
from scipy.special import gammainc
from color import Emulsion, encode, expose_row
from emulsion.simulate import WAVE, SHAPE, bands

# Effective CMY absorption strengths are design assumptions. Keep the same film
# absorption spectra as the previous writer for a controlled paper comparison.
STOCK = Emulsion()
FILM_ABS = STOCK.dyes
PAPER_ABS = bands([635,545,451], [44,34,32]).T
PAPER_ABS /= PAPER_ABS.sum(axis=0)
LAMP = colour.SDS_ILLUMINANTS['D50'].copy().align(SHAPE).values
# Light enters from the blue-sensitive face, then reaches green and red records.
PAPER_CAPTURE = np.empty((len(WAVE),3))
remaining = np.ones_like(WAVE,dtype=float)
for j, coeff in reversed(list(enumerate(bands([622,541,450],[27,24,23]).T))):
    absorbed = -np.expm1(-.68*coeff)
    PAPER_CAPTURE[:,j] = remaining * absorbed
    remaining *= 1-absorbed
assert np.allclose(PAPER_CAPTURE.sum(axis=1)+remaining,1)
response = LAMP[:,None]*WAVE[:,None]*PAPER_CAPTURE
# Set relative record speeds against an open lamp once, without photo fitting.
response /= response.sum(axis=0)

# Fixed virtual enlarger setting and low-scattering dye coating over white backing.
# These are explicit material assumptions, evaluated on synthetic neutral patches.
PRINT_EXPOSURE = .35
COATING_SCATTER = .01


def _process_field(active, steps, replenishment):
    developer=np.ones_like(active)
    silver=np.zeros_like(active)
    oxidized=np.zeros_like(active)
    coupler=np.ones_like(active)
    dye=np.zeros_like(active)
    for _ in range(steps):
        developer += .4*(.15*laplace(developer,mode='nearest')+replenishment*(1-developer))
        silver_step=(active-silver)*(-np.expm1(-.13*.4*developer))
        silver_step=np.minimum(silver_step,developer)
        developer-=silver_step
        silver+=silver_step
        oxidized+=silver_step
        oxidized+=.4*.18*laplace(oxidized,mode='nearest')
        coupled=np.minimum(coupler,oxidized*(-np.expm1(-.7*.4*coupler)))
        oxidized-=coupled
        oxidized*=np.exp(-.03*.4)
        dye+=coupled
        coupler-=coupled
    assert np.all(dye>=0) and np.all(dye<=1.00001)
    return dye


def process(active, steps, replenishment):
    import native
    if native.available():
        return native.develop(active, steps, replenishment)
    # Two stencil updates per step bound the influence radius. Halo cropping
    # gives the same finite-difference result while keeping large frames in cache.
    if max(active.shape) <= 640:
        return _process_field(active, steps, replenishment)
    result = np.empty_like(active)
    halo = 2 * steps
    for y in range(0, active.shape[0], 512):
        for x in range(0, active.shape[1], 512):
            y1, x1 = min(y+512, active.shape[0]), min(x+512, active.shape[1])
            top, left = max(0, y-halo), max(0, x-halo)
            bottom = min(active.shape[0], y1+halo)
            right = min(active.shape[1], x1+halo)
            tile = _process_field(active[top:bottom,left:right].copy(),steps,replenishment)
            result[y:y1,x:x1] = tile[y-top:y1-top,x-left:x1-left]
    return result


def film(pixels, grain_variation=0.015):
    rng = np.random.default_rng(90210)
    coating = gaussian_filter(rng.standard_normal(pixels.shape[:2],dtype=np.float32),8,mode='reflect')
    coating = 1 + grain_variation*np.tanh(coating*np.sqrt(4*np.pi*8**2))
    active=np.empty(pixels.shape,np.float32)
    for y,row in enumerate(pixels):
        exposure,_=STOCK.write(row/255)
        exposure *= coating[y,:,None]
        for j in range(3):
            _,hits,mass=expose_row(exposure[:,j],63+j,y)
            active[y,:,j]=((hits>=4)*mass).sum(axis=1)
    for j in range(3):
        active[:,:,j]=process(active[:,:,j].copy(),45,.11)
    return active


def transmission(dyes):
    return 10**(-.10-2*(dyes@FILM_ABS))


def paper(exposed_negative, exposure=PRINT_EXPOSURE):
    active=np.empty(exposed_negative.shape,np.float32)
    rng=np.random.default_rng(1103)
    for y in range(0,len(active),12):
        rows=slice(y,y+12)
        h=(transmission(exposed_negative[rows])@response)*exposure
        count=np.zeros_like(h)
        for speed in (12,30,75):
            count+=rng.binomial(128,gammainc(4,h*speed))
        active[rows]=count/384
    for j in range(3):
        active[:,:,j]=process(active[:,:,j].copy(),55,.14)
    return active


def reflection(dyes,backing=.94,scatter=COATING_SCATTER):
    # Homogeneous finite KM slab over a diffuse backing (thickness = 1).
    k=.008+3.7*(dyes@PAPER_ABS)
    s=scatter
    g=np.sqrt(k*(k+2*s))
    u=np.sinh(g)/g
    denominator=np.cosh(g)+(k+s)*u
    r=s*u/denominator
    t=1/denominator
    result=r+t*t*backing/(1-r*backing)
    assert np.all((result>=0)&(result<=1))
    return result


def view(dyes,fn):
    result=np.empty(dyes.shape,np.uint8)
    for y in range(0,len(dyes),12):
        rows=slice(y,y+12)
        result[rows]=encode(fn(dyes[rows])@STOCK.viewer)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('film','paper'))
    parser.add_argument('input',type=Path)
    parser.add_argument('out',type=Path)
    args=parser.parse_args()
    args.out.mkdir(exist_ok=True,parents=True)
    if args.stage=='film':
        dyes=film(np.asarray(Image.open(args.input).convert('RGB')))
        np.save(args.out/'film-cmy.npy',dyes)
        Image.fromarray(view(dyes,transmission)).save(args.out/'negative.png')
    else:
        dyes=paper(np.load(args.input,mmap_mode='r',allow_pickle=False))
        np.save(args.out/'paper-cmy.npy',dyes)
        Image.fromarray(view(dyes,reflection)).save(args.out/'print.png')
