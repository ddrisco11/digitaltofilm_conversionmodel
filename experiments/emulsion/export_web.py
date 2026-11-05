"""Build red-fastest RGB tables and inverse-binomial tables for the browser worker."""
from pathlib import Path

import numpy as np
from scipy.stats import binom
from scipy.special import gammainc
from simulate import Emulsion, encode

out = Path(__file__).resolve().parents[2] / 'docs/emulsion'
stock = Emulsion()
axis = np.linspace(0, 1, 65)
blue, green, red = np.meshgrid(axis, axis, axis, indexing='ij')
grid = np.column_stack((red.ravel(), green.ravel(), blue.ravel()))
tables = {name: [] for name in ('exposure', 'negative', 'print')}
for start in range(0, len(grid), 4096):
    points = grid[start:start+4096]
    exposure, _ = stock.write(points)
    # Square-root coding gives more exposure resolution in dark areas.
    assert np.min(exposure) >= 0 and np.max(exposure) <= 2
    tables['exposure'].append(np.rint(255*np.sqrt(exposure/2)).astype('uint8'))
    negative, _, positive = stock.print_negative(points)
    tables['negative'].append(encode(negative))
    tables['print'].append(encode(positive))
for name, chunks in tables.items():
    np.concatenate(chunks).tofile(out / (name + '.bin'))

exposures = 2*(np.arange(256)/255)**2
quantiles = (np.arange(256)+0.5)/256
counts = [binom.ppf(quantiles, 128, gammainc(4, speed*exposures[:,None]))
          for speed in (2, 10, 50)]
np.asarray(counts, dtype='uint8').tofile(out/'grains.bin')
