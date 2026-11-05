"""Expose an RGB image or print a saved dye negative. Each stage has a separate entry point."""
import argparse, io
from pathlib import Path
from PIL import Image, ImageCms, ImageOps
from simulation import *

ICC=ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
DENSITY_SCALE=16384.0   # unsigned 16-bit fixed-point, in dye coefficient units


def load_image(path):
    with Image.open(path) as src:
        image=ImageOps.exif_transpose(src).convert('RGB')
        icc=src.info.get('icc_profile')
        if icc:
            image=ImageCms.profileToProfile(image,ImageCms.ImageCmsProfile(io.BytesIO(icc)),ImageCms.createProfile('sRGB'))
        return np.asarray(image,dtype=np.uint8)


def write_negative(source, path, ev=0):
    sim=CameraAndPrinter()
    im=load_image(source);h,w=im.shape[:2]
    packed=im[...,0].astype('uint32')<<16 | im[...,1].astype('uint32')<<8 | im[...,2]
    keys,index=np.unique(packed,return_inverse=True)
    rgb=np.column_stack([(keys>>shift)&255 for shift in (16,8,0)])/255
    cmy=sim.negative_density(linear(rgb),ev)
    assert cmy.min()>=0 and cmy.max()*DENSITY_SCALE<65535
    np.savez_compressed(path, cmy=np.rint(cmy*DENSITY_SCALE).astype('uint16'), density_scale=DENSITY_SCALE,
                        pixels=index.reshape(h,w).astype('uint32'), film='kodak_portra_400', ev=ev)


def print_negative(path, destination):
    sim=CameraAndPrinter()
    with np.load(path) as f:
        assert str(f['film'])=='kodak_portra_400'
        palette=f['cmy'].astype(float)/f['density_scale'];index=f['pixels']
    out=np.empty((len(palette),3),dtype='uint8')
    for i in range(0,len(palette),8192):
        d=palette[i:i+8192]
        h=transmission(d,sim.film)@sim.print_matrix
        xyz=sim.reflect(develop(h,sim.paper))
        out[i:i+len(d)]=np.rint(255*srgb(xyz@sim.to_rgb)).astype('uint8')
    Image.fromarray(out[index]).save(destination,quality=96,subsampling=0,icc_profile=ICC)
    with Image.open(destination) as verify:
        verify.load();assert verify.size==index.shape[::-1]


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['expose','print']);p.add_argument('input',type=Path);p.add_argument('output',type=Path);p.add_argument('--ev',type=float,default=0)
    a=p.parse_args()
    if a.stage=='expose':write_negative(a.input,a.output,a.ev)
    else:print_negative(a.input,a.output)
