"""Fit a fixed LUT and a scene-conditioned LUT from matched FilmSet v1 images."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from render import MODEL, context, features, read_rgb, render


def select_pairs(root, split, count, exclude=()):
    folder = root / split
    paths = sorted((p for p in (folder / "input").glob("*.png") if p.name not in exclude),
                   key=lambda p: hashlib.sha256(p.name.encode()).digest())
    selected = [(p, folder / "ClassNeg" / p.name) for p in paths[:count]]
    if len(selected) != count or any(not target.exists() for _, target in selected):
        raise ValueError(f"Expected {count} complete {split} pairs")
    return selected


def samples(pairs):
    descriptors, inputs, targets = [], [], []
    for src, target in pairs:
        image, reference = read_rgb(src), read_rgb(target)
        if image.size != reference.size:
            raise ValueError(f"Mismatched dimensions for {src.name}")
        descriptors.append(context(image))
        # Each training image contributes equally regardless of dimensions.
        seed = int.from_bytes(hashlib.sha256(src.name.encode()).digest()[:8], "big")
        pixels = np.random.default_rng(seed).choice(image.width * image.height, 1024, replace=False)
        inputs.append(np.asarray(image).reshape(-1, 3)[pixels] / np.float32(255))
        targets.append(np.asarray(reference).reshape(-1, 3)[pixels] / np.float32(255))
    return np.array(descriptors), inputs, targets


def fit(pairs):
    descriptors, inputs, targets = samples(pairs)
    mean, scale = descriptors.mean(axis=0), np.maximum(descriptors.std(axis=0), 0.02)
    moments, rhs = [], []
    for descriptor, x, y in zip(descriptors, inputs, targets):
        f = features(x).astype(np.float64)
        c = np.r_[1., np.clip((descriptor - mean) / scale, -3, 3)]
        moments.append(np.kron(np.outer(c, c), f.T @ f))
        rhs.append(np.vstack([v * (f.T @ (y - x)) for v in c]))
    a, b = np.sum(moments, axis=0), np.sum(rhs, axis=0)
    width = features(np.zeros((1, 3), dtype=np.float32)).shape[1]
    # Ridge penalties shrink sparse colors and scene-dependent corrections.
    fixed = np.linalg.solve(a[:width, :width] + 4 * np.eye(width), b[:width])
    adaptive = np.linalg.solve(a + np.diag(np.repeat([4, 35, 35, 35], width)), b)
    axis = np.linspace(0, 1, 33, dtype=np.float32)
    blue, green, red = np.meshgrid(axis, axis, axis, indexing="ij")
    grid = np.column_stack((red.ravel(), green.ravel(), blue.ravel()))
    f = features(grid)
    fixed_lut = grid + f @ fixed
    base, *slopes = [f @ weights for weights in np.split(adaptive, 4)]
    # Store adaptive intercept separately, so fixed remains the true independent baseline.
    return dict(fixed=fixed_lut.flatten().astype("float32"),
                adaptive_base=(grid + base).flatten().astype("float32"),
                adjustments=np.array(slopes, dtype=np.float32).reshape(3, -1),
                mean=mean, scale=scale, size=33)


def evaluate(model, pairs):
    scores = {name: [] for name in ("input", "fixed", "adaptive")}
    for src, target in pairs:
        image = read_rgb(src)
        y = np.asarray(read_rgb(target), dtype=np.float32) / 255
        for name in scores:
            output = image if name == "input" else render(image, model, name)
            error = np.asarray(output, dtype=np.float32) / 255 - y
            scores[name].append(float(-10 * np.log10(max((error ** 2).mean(), 1e-12))))
    return {k: round(float(np.mean(v)), 3) for k, v in scores.items()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="FilmSet directory containing train/ and test/")
    parser.add_argument("--output", type=Path, default=MODEL)
    args = parser.parse_args()
    test = select_pairs(args.root, "test", 48)
    train = select_pairs(args.root, "train", 160, {a.name for a, _ in test})
    assert {a.name for a, _ in train}.isdisjoint(a.name for a, _ in test)
    model = fit(train)
    np.savez_compressed(args.output, **model)
    metrics = evaluate(model, test)
    print(json.dumps(metrics, indent=2))
    args.output.with_suffix(".json").write_text(json.dumps(
        {"dataset": "xuhangc/filmset", "version": 1, "recipe": "ClassNeg",
         "train_pairs": len(train), "test_pairs": len(test), "mean_per_image_psnr_db_srgb": metrics},
        indent=2) + "\n")
    with args.output.with_suffix(".csv").open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["split", "input_member", "target_member"])
        for split, rows in [("train", train), ("test", test)]:
            for src, target in rows:
                writer.writerow([split, src.relative_to(args.root), target.relative_to(args.root)])
