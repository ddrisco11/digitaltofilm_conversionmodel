"""DigitalFilm adapters. The reader adapter only receives a developed print."""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def parameters():
    return json.loads((HERE / "digitalfilm-adapters.json").read_text())


def writer_adjust(negative, model, params):
    from neutral import apply
    return apply(negative, model, np.asarray(params))


def reader_adjust(positive, params):
    bias, gain = np.asarray(params).reshape(2, 3)
    return np.clip((positive - 0.5) * (1 + gain) + 0.5 + bias, 0, 1)
