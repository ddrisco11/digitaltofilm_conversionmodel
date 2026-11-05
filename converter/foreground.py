"""Detect salient foreground on the original image, including non-human subjects."""
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image


@lru_cache(maxsize=1)
def session():
    import onnxruntime as ort
    model = Path(__file__).resolve().parents[1] / "docs/vendor/foreground/u2netp.onnx"
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    return ort.InferenceSession(str(model), options, providers=["CPUExecutionProvider"])


def foreground_mask(image):
    rgb = np.asarray(image.resize((320, 320), Image.Resampling.BILINEAR), dtype=np.float32)
    rgb /= max(float(rgb.max()), 1)
    rgb -= np.array([0.485, 0.456, 0.406], dtype=np.float32)
    rgb /= np.array([0.229, 0.224, 0.225], dtype=np.float32)
    engine = session()
    inputs = {engine.get_inputs()[0].name: rgb.transpose(2, 0, 1)[None]}
    scores = engine.run([engine.get_outputs()[0].name], inputs)[0][0, 0]
    mask = Image.fromarray(np.rint(scores.clip(0, 1) * 255).astype(np.uint8))
    return mask.resize(image.size, Image.Resampling.BILINEAR)
