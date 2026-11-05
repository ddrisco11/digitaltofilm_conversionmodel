"""Fit independent writer and reader adapters with a frozen, gray-calibrated baseline."""
import argparse
import hashlib
import io
import json
import zipfile

import numpy as np
from PIL import Image, ImageCms, ImageOps
from digitalfilm import writer_adjust, reader_adjust
from negative_pipeline import HERE, develop, make_negative
from neutral import apply, calibrate

REFERENCE = HERE.parents[1] / "converter/digitalfilm-gold.json"
QUANTILES = [10, 25, 50, 75, 90]


def pixels(archive, names):
    swatches = []
    srgb = ImageCms.createProfile("sRGB")
    for name in names:
        with Image.open(io.BytesIO(archive.read(name))) as image:
            image.thumbnail((384, 384))
            rgb = ImageOps.exif_transpose(image).convert("RGB")
            profile = image.info.get("icc_profile")
            if profile:
                rgb = ImageCms.profileToProfile(rgb, ImageCms.ImageCmsProfile(io.BytesIO(profile)), srgb)
            w,h = rgb.size
            inner = rgb.crop((w*.08,h*.08,w*.92,h*.92))
            arr = np.asarray(inner).reshape(-1,3)
            seed = int.from_bytes(hashlib.sha256(name.encode()).digest()[:8],"big")
            swatches.append(arr[np.random.default_rng(seed).choice(len(arr),128,replace=True)])
    return np.concatenate(swatches).astype(np.float64) / 255


def stats(rgb):
    return np.percentile(rgb.reshape(-1,3), QUANTILES, axis=0)


def optimize(render, target):
    # Fixed budget for each adapter: three offsets, three gains, identical loss.
    def loss(p):
        residual = stats(render(p))-target
        return np.mean(residual**2) + .025*np.mean(p**2)
    best=np.zeros(6)
    for step in [.08,.04,.02,.01,.005]:
        for _ in range(3):
            moved=False
            for i in range(6):
                delta=np.eye(6)[i]*step
                choices=[best, np.clip(best+delta,-.30,.30),np.clip(best-delta,-.30,.30)]
                chosen=min(choices,key=loss)
                moved |= not np.array_equal(chosen,best)
                best=chosen
            if not moved:break
    return best


def run(archive_path):
    ref=json.loads(REFERENCE.read_text())
    with open(archive_path,'rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==ref['archive_sha256']
    report={}
    with zipfile.ZipFile(archive_path) as archive, np.load(HERE/'model.npz') as model:
        inputs={}; targets={}; held={}
        for role in ('digital','film'):
            train=ref['members'][role]
            candidates=[p for p in archive.namelist() if f'/{role}/' in p and p.lower().endswith(('.jpg','.jpeg','.png')) and p not in train]
            held[role]=sorted(candidates,key=lambda p:hashlib.sha256(p.encode()).digest())[:64]
            for split,names in [('fit',train),('holdout',held[role])]:
                swatch=pixels(archive,names)
                if role=='film': targets[split]=stats(swatch)
                else: inputs[split]=apply(make_negative(swatch[:,None,:],model), model,calibrate(model))
        base=inputs['fit']
        base_print=develop(base,model)
        writer=optimize(lambda p:develop(writer_adjust(base,model,p),model),targets['fit'])
        reader=optimize(lambda p:reader_adjust(base_print,p),targets['fit'])
        for split,neg in inputs.items():
            report[split]={}
            for branch in ('baseline','A','B','C'):
                n=writer_adjust(neg,model,writer) if branch in ('A','C') else neg
                out=develop(np.rint(n*65535)/65535,model)
                if branch in ('B','C'):out=reader_adjust(out,reader)
                report[split][branch]=round(float(np.mean(np.abs(stats(out)-targets[split]))*255),3)
    artifact=dict(writer=writer.tolist(),reader=reader.tolist(),held_out_members=held,
                  mean_absolute_rgb_quantile_gap_255=report)
    (HERE/'digitalfilm-adapters.json').write_text(json.dumps(artifact,indent=2)+'\n')
    print(report)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive')
    run(parser.parse_args().archive)
