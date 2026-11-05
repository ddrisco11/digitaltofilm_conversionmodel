"""A two-process experiment. A 16-bit PNG is the only image passed between stages."""
import argparse
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
HERE = Path(__file__).resolve().parent
# Approximate readings of Fujifilm NPH 400, bulletin AF3-121E, section 20.
LOG_H = [-3.5, -3, -2.5, -2, -1.5, -1, -.5, 0, .5, .65]
CURVES = [[.16,.16,.21,.40,.67,.98,1.28,1.58,1.86,1.94],
          [.68,.68,.73,.90,1.20,1.50,1.78,2.04,2.29,2.36],
          [.95,.95,1.00,1.22,1.49,1.76,2.01,2.26,2.51,2.59]]


def as_density(negative):
    return -np.log10(np.maximum(negative, 1/65535))


def features(z):
    r,g,b=z.T
    return np.column_stack((np.ones(len(z)),r,g,b,r*r,g*g,b*b,r*g,g*b,b*r))


def make_negative(rgb, model):
    linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
    h=np.log10(np.maximum(linear,.00001))-.65
    stock=np.stack([np.interp(h[...,c],LOG_H,CURVES[c]) for c in range(3)],axis=-1)
    # Relative calibration: assume sRGB levels 0.06 and 0.94 approximately span
    # the median within-frame 2nd and 98th density percentiles in training scans.
    endpoint=np.asarray([.06,.94])
    anchor_h=np.log10(((endpoint+.055)/1.055)**2.4)-.65
    anchor=np.array([np.interp(anchor_h,LOG_H,c) for c in CURVES]).T
    z=(stock-anchor[0])/(anchor[1]-anchor[0])
    scanner_density=model['lo']+z*(model['hi']-model['lo'])
    return np.clip(10**(-scanner_density),0,1)


def develop(negative, model):
    z=np.clip((as_density(negative)-model['lo'])/(model['hi']-model['lo']),-.5,1.5)
    out=np.empty_like(negative)
    for start in range(0,z.shape[0],64):
        block=z[start:start+64]
        out[start:start+64]=(features(block.reshape(-1,3))@model['weights']).reshape(block.shape)
    return out.clip(0,1)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['expose','develop'])
    parser.add_argument('input',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--gray-calibration',action='store_true',help='Calibrate synthetic scan exposure and channel balance on a virtual gray ramp (expose only).')
    parser.add_argument('--branch', choices=['baseline','A','B','C'], default='baseline',
                        help='DigitalFilm adapter placement: A writer, B reader, C both. All three use gray calibration.')
    args=parser.parse_args()
    if args.gray_calibration and args.stage!='expose':parser.error('Gray calibration belongs to expose.')
    with np.load(HERE/'model.npz') as model:
        if args.stage=='expose':
            if args.output.suffix.lower()!='.png':parser.error('Use PNG for the 16-bit intermediate.')
            rgb=np.asarray(Image.open(args.input).convert('RGB'),dtype=np.float32)/255
            negative=make_negative(rgb,model)
            if args.gray_calibration or args.branch!='baseline':
                from neutral import calibrate,apply
                negative=apply(negative,model,calibrate(model))
            if args.branch in ('A','C'):
                from digitalfilm import parameters,writer_adjust
                negative=writer_adjust(negative,model,parameters()['writer'])
            assert cv2.imwrite(str(args.output),np.round(negative[:,:,::-1]*65535).astype('uint16'))
        else:
            raw=cv2.imread(str(args.input),cv2.IMREAD_UNCHANGED)
            if raw is None or raw.dtype!=np.uint16 or raw.ndim!=3 or raw.shape[2]!=3:
                parser.error('Developer input must be a 16-bit three-channel negative.')
            rgb=develop(raw[:,:,::-1].astype('float32')/65535,model)
            if args.branch in ('B','C'):
                from digitalfilm import parameters,reader_adjust
                rgb=reader_adjust(rgb,parameters()['reader'])
            Image.fromarray(np.round(rgb*255).astype('uint8')).save(args.output,quality=95)
