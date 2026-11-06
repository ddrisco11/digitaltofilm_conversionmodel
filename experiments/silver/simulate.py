"""A discrete-grain monochrome negative with a developer bath shared by neighboring pixels."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from scipy.ndimage import gaussian_filter, laplace

GRAINS = 24
BASE_DENSITY = 0.08
SILVER_DENSITY = 2.2


def expose_row(light, seed, row):
    # Independent reproducible row streams make any single grain inspectable.
    rng = np.random.default_rng([seed, row])
    radius = rng.choice([0.75, 1.0, 1.35], size=(light.size, GRAINS), p=[.4, .4, .2])
    efficiency = rng.choice([2., 10., 50.], radius.shape)
    hits = rng.poisson(light[:, None] * efficiency * radius**2)
    mass = radius**3
    mass /= mass.sum(axis=1, keepdims=True)
    return radius, hits, mass


def develop(active_mass, time, temperature, bath, diffusion=.15):
    # No-flux lateral boundaries; each column exchanges developer with a bulk bath.
    c = np.full_like(active_mass, bath)
    silver = np.zeros_like(active_mass)
    rate = .13 * 2 ** ((temperature - 20) / 10)
    steps = max(1, int(np.ceil(time / .4)))
    dt = time / steps
    for _ in range(steps):
        c += dt * (diffusion * laplace(c, mode='nearest') + .11 * (bath - c))
        reaction = (active_mass - silver) * (-np.expm1(-rate * c * dt))
        reaction = np.minimum(reaction, c / .85)
        c -= .85 * reaction
        silver += reaction
    return silver, c


def encode(linear):
    linear = np.clip(linear, 0, 1)
    code = np.where(linear <= .0031308, 12.92*linear, 1.055*linear**(1/2.4)-.055)
    return np.uint8(np.rint(255*code))


def simulate(args):
    photo = ImageOps.exif_transpose(Image.open(args.image)).convert('RGB')
    code = np.asarray(photo, dtype=np.float32)/255
    linear = np.where(code <= .04045, code/12.92, ((code+.055)/1.055)**2.4)
    light = gaussian_filter(linear @ np.array([.2126,.7152,.0722],np.float32), .65) * 2**args.ev
    active = np.empty_like(light)
    for y, row in enumerate(light):
        _, hits, mass = expose_row(row, args.seed, y)
        active[y] = ((hits >= 4) * mass).sum(axis=1)
    silver, concentration = develop(active,args.time,args.temperature,args.bath)
    transmission = 10**(-BASE_DENSITY - SILVER_DENSITY*silver)
    # Scan the transmitted negative using a fixed base and density range.
    positive = (-np.log10(transmission) - BASE_DENSITY)/SILVER_DENSITY
    args.out.mkdir(parents=True, exist_ok=True)
    for name, array in [('negative',transmission), ('positive',positive)]:
        Image.fromarray(encode(array)).save(args.out/(name+'.png'))
    x,y = args.inspect or (photo.width//2,photo.height//2)
    radius,hits,mass = expose_row(light[y], args.seed,y)
    fraction = float(silver[y,x]/active[y,x]) if active[y,x] else 0.
    grains = []
    for i in range(GRAINS):
        initial = float(mass[x,i])
        developed = initial*fraction if hits[x,i]>=4 else 0.
        grains.append(dict(index=i,relative_radius=float(radius[x,i]),effective_events=int(hits[x,i]),
                           latent=bool(hits[x,i]>=4),initial_silver_equivalent=initial,
                           retained_metallic_silver=developed,removed_by_complete_fix=initial-developed))
    assert abs(sum(g['retained_metallic_silver'] for g in grains)-silver[y,x]) < 1e-6
    report = dict(x=x,y=y,seed=args.seed,exposure_ev=args.ev,temperature_C=args.temperature,
                  relative_bath_strength=args.bath,development_time_units=args.time,
                  final_local_developer=float(concentration[y,x]),grains=grains)
    (args.out/'grain-trace.json').write_text(json.dumps(report,indent=2))
    return photo


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image',help='SDR sRGB input')
    parser.add_argument('out',type=Path)
    parser.add_argument('--ev',type=float,default=0)
    parser.add_argument('--time',type=float,default=18)
    parser.add_argument('--temperature',type=float,default=20)
    parser.add_argument('--bath',type=float,default=1)
    parser.add_argument('--seed',type=int,default=63)
    parser.add_argument('--inspect',nargs=2,type=int,metavar=('X','Y'))
    args = parser.parse_args()
    if not (-12<=args.ev<=12 and 0<=args.time<=300 and 0<=args.temperature<=50 and 0<=args.bath<=4 and args.seed>=0):
        parser.error('Use EV ±12, time 0–300, temperature 0–50, bath 0–4 and a nonnegative seed.')
    if args.inspect:
        with Image.open(args.image) as source:
            w,h=ImageOps.exif_transpose(source).size
        if not (0<=args.inspect[0]<w and 0<=args.inspect[1]<h):
            parser.error('Inspection coordinates must fall inside the oriented image.')
    simulate(args)
