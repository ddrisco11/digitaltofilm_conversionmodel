"""Develop three independent grain layers. Print a saved CMY negative in a separate invocation."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageOps

from simulate import expose_row, develop
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from emulsion.simulate import Emulsion, encode


def write_negative(stock, pixels):
    active = np.empty(pixels.shape, dtype=np.float32)
    for y, row in enumerate(pixels):
        exposure, _ = stock.write(row / 255.)
        for layer in range(3):
            _, hits, mass = expose_row(exposure[:, layer], 63 + layer, y)
            active[y,:,layer] = ((hits >= 4) * mass).sum(axis=1)
    dyes = np.empty_like(active)
    for layer in range(3):
        silver, _ = develop(active[:,:,layer].copy(), time=18, temperature=20, bath=1.)
        # Constant unit dye yield: summing incremental dye gives final reacted silver.
        # Complete bleach/fix leaves only the dyes as image-forming material.
        dyes[:,:,layer] = silver
    return active, dyes


def print_frame(stock, dyes, dest):
    neg, pos = (np.empty(dyes.shape, dtype=np.uint8) for _ in range(2))
    for start in range(0,len(dyes),12):
        rows = slice(start,start+12)
        light, _, result = stock.print_negative(dyes[rows])
        neg[rows], pos[rows] = encode(light), encode(result)
    for name, array in [('negative',neg),('print',pos)]:
        Image.fromarray(array).save(dest / (name+'.png'))


def probes(stock):
    values = {'red':[255,0,0],'green':[0,255,0],'blue':[0,0,255],
              'gray':[128,128,128],'canopy':[136,152,68]}
    report = {}
    for label, rgb in values.items():
        exposure, old_dyes = stock.write(np.array(rgb)/255)
        active, dyes = write_negative(stock,np.broadcast_to(rgb,(96,96,3)))
        _, paper, linear = stock.print_negative(dyes)
        result = encode(linear.mean(axis=(0,1)))
        report[label] = dict(input=rgb, exposure=exposure.tolist(),
                             latent_mass=active.mean(axis=(0,1),dtype=float).tolist(),
                             developed_dyes=dyes.mean(axis=(0,1),dtype=float).tolist(),
                             paper_exposure=paper.mean(axis=(0,1)).tolist(),
                             print_rgb=result.tolist(),
                             same_grains_instant_development=encode(
                                 stock.print_negative(active)[2].mean(axis=(0,1))).tolist(),
                             print_of_mean_dyes=encode(stock.print_negative(
                                 dyes.mean(axis=(0,1),dtype=float))[2]).tolist(),
                             control_mean_response=encode(stock.print_negative(old_dyes)[2]).tolist())
        if label in ('red','green','blue'):
            channel=int(np.argmax(rgb))
            assert channel==np.argmax(exposure)==np.argmax(report[label]['developed_dyes'])==np.argmin(report[label]['paper_exposure'])==np.argmax(result)
        if label=='gray':
            report[label]['neutral_spread_srgb8'] = int(np.ptp(result.astype(int)))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='operation', required=True)
    for name in ['write','print','probes']:
        cmd=sub.add_parser(name)
        if name!='probes':
            cmd.add_argument('source',type=Path)
        cmd.add_argument('dest',type=Path)
    args=parser.parse_args()
    stock=Emulsion()
    if args.operation=='probes':
        args.dest.write_text(json.dumps(probes(stock),indent=2))
    elif args.operation=='write':
        pixels=np.asarray(ImageOps.exif_transpose(Image.open(args.source)).convert('RGB'))
        _, dyes=write_negative(stock,pixels)
        np.save(args.dest,dyes,allow_pickle=False)
    else:
        args.dest.mkdir(parents=True,exist_ok=True)
        print_frame(stock,np.load(args.source,mmap_mode='r',allow_pickle=False),args.dest)
