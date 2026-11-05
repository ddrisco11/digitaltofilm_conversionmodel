# Spectral darkroom

I implemented a relative-radiometry model of an LCD display, a Portra 400 negative, a filtered enlarger and a Portra Endura print. The input is a color-managed SDR photograph. The measured Apple Studio Display LCD primaries in Colour approximate the virtual display. I integrate from 405 to 695 nm in 5 nm increments, using a CIE 1931 observer. A fixed camera scale maps 18.4% linear neutral to the green film record’s reference exposure. The printer uses a 3200 K lamp, Durst dichroic profiles and a single midgray balance. Print reflection is evaluated under D50, Bradford-adapted and encoded as sRGB. The model covers mean color and tone. Spatial grain, halation, lens flare and chemical kinetics are outside this experiment.

The Python solver evaluates spectral transmission from dye amounts. It encodes the film negative at 1/16,384 coefficient units and saves the spatial index in an NPZ. The browser has fixed default exposure and settings and uses four precomputed 65³, red-fastest, display-encoded RGB stage tables with trilinear interpolation. Its JPEG exports of exposure and dye amounts are visualizations. Use Python for the physical intermediate.

From this folder, install requirements.txt in a Python 3.13 environment:

```sh
python render.py expose input.jpg negative.npz
python render.py print negative.npz print.jpg
python export_web.py
```

I used unmodified material profiles by **Andrea Volpato, spektrafilm**, licensed under CC BY-SA 4.0. My tables derive from those profiles and carry the same license. The stock/paper profiles model measured and fitted material characteristics. [Pinned source](https://github.com/andreavolpato/spektrafilm/tree/3bb2c2d2801ff68b92019cf1dbcbb133d60832bc) · [License](materials/SPEKTRAFILM_LICENSE.txt) · [Table creation notes](../../docs/physics/CHANGELOG.txt) · [Kodak Portra 400 technical bulletin](https://business.kodakmoments.com/sites/default/files/files/resources/portra400-techpub-e4050.pdf)
