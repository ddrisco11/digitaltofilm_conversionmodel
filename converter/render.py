"""Render a full-resolution SDR image with a trained color lookup table."""
import argparse
import io
import json
from pathlib import Path
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageCms, ImageFilter, ImageOps

SRGB = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
MODEL = Path(__file__).with_name("filmset-classneg.npz")


def read_rgb(path):
    path = Path(path)
    if path.suffix.lower() in {".heic", ".heif"}:
        with tempfile.TemporaryDirectory() as temp:
            png = Path(temp) / "decoded.png"
            subprocess.run(["sips", "-s", "format", "png", str(path), "--out", str(png)],
                           stdout=subprocess.DEVNULL, check=True)
            return read_rgb(png)
    with Image.open(path) as source:
        return to_srgb(source)


def to_srgb(source):
    image = ImageOps.exif_transpose(source).convert("RGB")
    profile = source.info.get("icc_profile")
    if profile:
        original = ImageCms.ImageCmsProfile(io.BytesIO(profile))
        image = ImageCms.profileToProfile(image, original, SRGB, outputMode="RGB")
    image.info.clear()
    return image


def gold_adjustment(image, curves):
    values = np.arange(256)
    channels = [np.interp(values, anchors, outputs) for anchors, outputs in curves]
    return image.point(np.round(np.concatenate(channels)).clip(0, 255).astype(int).tolist())


def context(image):
    rgb = np.asarray(image.resize((64, 64), Image.Resampling.BOX), dtype=np.float32) / 255
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    return np.array([lum.mean(), lum.std(), (rgb[..., 0] - rgb[..., 2]).mean()])


def features(rgb):
    # Smooth, overlapping color neighborhoods plus an affine term.
    axis = np.linspace(0, 1, 4, dtype=np.float32)
    centers = np.stack(np.meshgrid(axis, axis, axis, indexing="ij"), axis=-1).reshape(-1, 3)
    distances = ((rgb[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
    return np.column_stack((np.ones(len(rgb), dtype=np.float32), rgb,
                            np.exp(-distances / (2 * 0.24 ** 2))))


def render(image, model, variant):
    table = model["fixed"]
    if variant == "adaptive":
        descriptor = (context(image) - model["mean"]) / model["scale"]
        table = model["adaptive_base"] + np.tensordot(np.clip(descriptor, -3, 3), model["adjustments"], axes=1)
    elif variant != "fixed":
        raise ValueError(f"Unknown variant: {variant}")
    lut = ImageFilter.Color3DLUT(int(model["size"]), np.clip(table, 0, 1).astype("float32"))
    return image.filter(lut)


def save_rgb(image, path):
    path = Path(path)
    options = {"icc_profile": SRGB.tobytes()}
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        options.update(quality=95, subsampling=0)
    image.save(path, **options)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--variant", choices=["fixed", "adaptive"], default="adaptive")
    parser.add_argument("--model", type=Path, default=MODEL)
    parser.add_argument("--gold", action="store_true",
                        help="Apply the experimental unpaired DigitalFilm color adjustment after the adaptive LUT")
    args = parser.parse_args()
    if args.gold and args.variant != "adaptive":
        parser.error("--gold requires --variant adaptive")
    if args.input.resolve() == args.output.resolve():
        parser.error("Choose a separate output path.")
    with np.load(args.model) as model:
        result = render(read_rgb(args.input), model, args.variant)
    if args.gold:
        calibration = json.loads(Path(__file__).with_name("digitalfilm-gold.json").read_text())
        result = gold_adjustment(result, calibration["curves"])
    save_rgb(result, args.output)
