# Color emulsion lab

I simulate a display photographed on an invented three-layer film. The input is an orientation-corrected SDR sRGB image. I integrate a documented Apple Studio Display primary spectrum against three Gaussian layer sensitivities over 61 bands from 400 to 700 nm. I chose their centers (615, 540, 455 nm) and widths (28, 23, 22 nm), and balance the layer exposures on display white. [Display primary data](https://colour.readthedocs.io/en/v0.3.9/colour.characterisation.dataset.displays.lcd.rgb_primaries.html)

Each layer has three grain populations. I model surviving reduction events as Poisson counts and use four events as the development threshold. The threshold is inspired by an experimental result on silver bromide. The relative speeds (2, 10, 50), population sizes (128 each per pixel), and dye yield are design choices. I sample the developed count separately in each population. [Ohzeki and Tani, Characterization of Various Development Centers in Silver Halide Photography](https://library.imaging.org/jist/articles/50/4/art00010)

I give each developed layer a cyan, magenta or yellow absorption curve, combine the optical densities and use Beer–Lambert transmission. The paper model takes only the developed dye amounts. I expose it through the negative with D50 light, apply a saturating development curve, then integrate reflected light with the standard observer. The model uses a fixed geometry and relative exposures. Diffusion, spatial dye clouds and chemical reaction rates are open experiments.

## Reproduce the park experiment

From this directory, install the pinned dependencies and run on an sRGB export of a photo.

    python -m pip install -r requirements.txt
    python simulate.py input.png results/
    python export_web.py

The first script checks the mean neutral ramp and display primaries, then writes a full-resolution negative preview and print with seeded grain. The second generates the browser exposure and printing tables plus quantiles for the three grain populations. Browser stages share the same seeded grain realization. The browser quantizes layer exposures, dye amounts and binomial quantiles and uses a different random generator, so its grain pattern differs from Python's.

On the park probe, a grain-free input of (136, 152, 68) prints at (99, 93, 37). This measures a shift in leaf color relative to the input. A physical reference would be needed to assess fidelity to a specific film or paper.
