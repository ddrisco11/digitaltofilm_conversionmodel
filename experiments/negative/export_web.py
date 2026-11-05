"""Export the exact 8-bit input → 16-bit transmission curves and print-reader weights."""
import json
from negative_pipeline import HERE, make_negative, np
from neutral import apply, calibrate

with np.load(HERE / "model.npz") as model:
    ramp = np.arange(256, dtype=np.float32) / 255
    rgb = np.repeat(ramp[:, None, None], 3, axis=2)
    raw = make_negative(rgb, model)
    balanced = apply(raw, model, calibrate(model))
    data = {key: model[key].tolist() for key in ("lo", "hi", "weights")}
    for name, curve in [("raw", raw), ("balanced", balanced)]:
        data[name] = np.rint(curve[:, 0, :] * 65535).astype(int).T.tolist()
    (HERE.parents[1] / "docs/negative-model.json").write_text(json.dumps(data) + "\n")
