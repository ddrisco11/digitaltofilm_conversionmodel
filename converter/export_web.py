"""Export the trained scene-conditioned LUTs and Gold curves for the browser."""
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent


def export():
    target = ROOT.parent / "docs"
    with np.load(ROOT / "filmset-classneg.npz") as model:
        tables = np.vstack([model["adaptive_base"], model["adjustments"]])
        tables.astype("<f4").tofile(target / "lut.bin")
        meta = {key: model[key].tolist() for key in ("size", "mean", "scale")}
    meta["curves"] = json.loads((ROOT / "digitalfilm-gold.json").read_text())["curves"]
    (target / "model.json").write_text(json.dumps(meta, indent=2) + "\n")


if __name__ == "__main__":
    export()
