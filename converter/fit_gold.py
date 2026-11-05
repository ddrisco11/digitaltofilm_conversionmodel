"""Fit a restrained correction to unpaired DigitalFilm reference color distributions."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
from PIL import Image
from render import MODEL, render, to_srgb

ARCHIVE_SHA256 = "5124d45f0d5c016cc2ae0202ffdb42492639dfbd17cb53d9e485949889c275d2"


def sample_stats(archive, members, model=None):
    brightness, stats = [], []
    for name in members:
        with Image.open(io.BytesIO(archive.read(name))) as src:
            src.thumbnail((384, 384))
            image = to_srgb(src)
        if model is not None:
            image = render(image, model, "adaptive")
        w, h = image.size
        # Ignore the outer 8% on each edge to reduce the influence of scan borders.
        rgb = np.asarray(image.crop((w*0.08, h*0.08, w*0.92, h*0.92))).reshape(-1, 3)
        brightness.append(rgb.mean())
        stats.append(np.percentile(rgb, [2, 10, 25, 50, 75, 90, 98], axis=0))
    # Equal weight for brightness quartiles and for individual photographs.
    buckets = np.array_split(np.argsort(brightness), 4)
    return np.mean([np.median(np.asarray(stats)[ids], axis=0) for ids in buckets], axis=0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    with args.archive.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != ARCHIVE_SHA256:
            raise ValueError("Unexpected DigitalFilm Gold archive checksum")
    members = {}
    with zipfile.ZipFile(args.archive) as archive, np.load(MODEL) as model:
        for role in ["digital", "film"]:
            candidates = [p for p in archive.namelist()
                          if f"/{role}/" in p and p.lower().endswith((".jpg", ".jpeg", ".png"))]
            members[role] = sorted(candidates, key=lambda p: hashlib.sha256(p.encode()).digest())[:256]
            if len(members[role]) != 256:
                raise ValueError(f"Expected 256 {role} images")
        digital = sample_stats(archive, members["digital"], model)
        film = sample_stats(archive, members["film"])
    curves = []
    for channel in range(3):
        x = digital[:, channel]
        # Shrink the estimated change because scene contents and lighting differ.
        y = x + 0.4 * np.clip(film[:, channel] - x, -24, 24)
        curves.append(([0, *x, 255], [0, *np.maximum.accumulate(y), 255]))
    artifact = {"archive_sha256": ARCHIVE_SHA256, "members_per_domain": 256,
                "method": "brightness-stratified unpaired channel quantiles, 40% strength",
                "curves": curves, "members": members}
    Path(__file__).with_name("digitalfilm-gold.json").write_text(json.dumps(artifact, indent=2) + "\n")
