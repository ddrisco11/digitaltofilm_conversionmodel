"""Build an offline blind comparison of the local pairs, one entry per recorded scene group."""
import argparse
import base64
import csv
from html import escape
import io
import json
from pathlib import Path
import random
import subprocess
import tempfile

import numpy as np
from PIL import Image
from render import MODEL, gold_adjustment, read_rgb, render

ROOT = Path(__file__).resolve().parent.parent


def preview(image, label):
    image = image.copy()
    image.thumbnail((420, 315), Image.Resampling.LANCZOS)
    stream = io.BytesIO()
    image.save(stream, "JPEG", quality=87)
    data = base64.b64encode(stream.getvalue()).decode()
    return f'<figure><figcaption>{escape(label)}</figcaption><img alt="{escape(label)}" src="data:image/jpeg;base64,{data}"></figure>'


def read_digital(path):
    if path.suffix.lower() != ".arw":
        return read_rgb(path)
    with tempfile.TemporaryDirectory() as temp:
        png = Path(temp) / "camera-preview.png"
        subprocess.run(["sips", "-s", "format", "png", str(path), "--out", str(png)],
                       check=True, stdout=subprocess.DEVNULL)
        return read_rgb(png)


def build(output):
    rng = random.Random(2605)
    seen = set()
    sections = []
    curves = json.loads(MODEL.with_name("digitalfilm-gold.json").read_text())["curves"]
    with (ROOT / "pairs.csv").open() as stream, np.load(MODEL) as model:
        for row in csv.DictReader(stream):
            group = row["scene_group"]
            if group in seen:
                continue
            seen.add(group)
            source = read_digital(ROOT / row["digital_path"])
            analog = read_rgb(ROOT / row["analog_path"])
            # Render each scene through the same entry points as full-size export.
            adaptive = render(source, model, "adaptive")
            candidates = [("Fixed Classic Negative", render(source, model, "fixed")),
                          ("Adaptive Classic Negative", adaptive),
                          ("Experimental Gold", gold_adjustment(adaptive, curves))]
            rng.shuffle(candidates)
            cells = preview(analog, "Film reference")
            key = []
            for label, (name, image) in zip("ABC", candidates):
                cells += preview(image, label)
                key.append(f"{label} = {name}")
            credit = " / ".join(dict.fromkeys([row["analog_creator"], row["digital_creator"]]))
            links = " · ".join(f'<a href="{escape(row[role+"_source_url"], quote=True)}">{role.title()} source</a>'
                               for role in ("analog", "digital"))
            sections.append(f'<section><h2>{escape(row["subject"])}</h2><p>{escape(row["pair_id"])} · {escape(credit)} · {links}</p>'
                            f'<div class="photos">{cells}</div><details><summary>Reveal methods</summary>{", ".join(key)}</details></section>')
    output.write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Blind film comparison</title><style>
body{max-width:1600px;margin:2rem auto;padding:0 1.1rem;font:16px/1.45 system-ui;color:#242424;background:#faf9f6}
section{border-top:1px solid #bbb;margin:2rem 0}h2{margin-bottom:0}p{margin-top:.4rem}.photos{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.6rem}
figure{margin:0}figcaption{margin-bottom:.3rem;font-weight:600}img{width:100%;height:clamp(130px,18vw,315px);object-fit:contain;background:#eee}
summary{cursor:pointer}details{margin-top:.8rem}@media(max-width:700px){.photos{grid-template-columns:1fr 1fr}img{height:180px}}</style>
<h1>Blind film comparison</h1><p>Choose A, B or C for the closest color and tone to the film reference. Record the pair ID and your choice before revealing the methods.
Each row uses one representative per scene group. Camera viewpoints, processing and film stocks vary.</p>''' + "\n".join(sections) + "</html>")
    print(f"Wrote {len(sections)} scene groups to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    build(parser.parse_args().output)
