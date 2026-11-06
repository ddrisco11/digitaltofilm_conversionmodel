# Silver-grain bench

I start with a floating-point luminance image of a displayed sRGB photograph. A narrow Gaussian blur approximates optical spread. Exposure in stops scales the light incident on 24 discrete grain samples per image pixel. Each sample has a relative radius and efficiency. Projected area sets its mean number of effective light-induced events. A Poisson draw of at least four events makes a grain developable. Its share of the pixel's silver supply scales with its volume. Grain counts and material constants are prototype choices.

During development I evolve a two-dimensional concentration field. Developer diffuses between neighboring pixels, enters from a uniform bulk bath and is consumed when developable halide turns into metallic silver. The rate increases with concentration and uses an assumed doubling per 10 °C. Because every latent grain in a pixel shares the same reaction rate, I can integrate their combined mass exactly for a given concentration history and reconstruct each grain's individual share. The boundaries have zero lateral flux. Stopping terminates the reaction. An ideal complete fix removes remaining halide. Washing and drying are endpoint assumptions. The model covers monochrome negative film.

The negative transmits light as 10 raised to minus its optical density. I derive the positive from that transmission with a fixed scanner density range. Repeated runs with the same input, seed and parameters reproduce the grain states. Spatial diffusion operates across the whole frame.

Run with NumPy, SciPy and Pillow (the sibling emulsion experiment pins the working versions). From this directory:

    python simulate.py input-srgb.png results --inspect 1050 600
    python simulate.py input-srgb.png longer --time 36 --ev 1
    python checks.py

Each run saves a negative, a positive and the selected pixel's grain ledger. Time, silver mass, effective photon exposure and concentration use relative scales. Temperature is a model control pending physical calibration. Pixel pitch sets the simulated diffusion length and grain scale. The program expects a color-managed SDR sRGB export.

The supplied design brief motivates the causal sequence. The four-event threshold is a simplified interpretation of the Ag₄ result in [Ohzeki and Tani's study of development centers](https://library.imaging.org/jist/articles/50/4/art00010). This implementation uses NumPy randomness and SciPy finite differences. It does not consume commercial stock profiles or fit photographic examples.

## Three-layer color experiment

I use the color lab's display and layer exposure model, then apply the silver-grain process separately to its red, green and blue exposures. Each layer uses 24 grain samples per pixel. Each unit of silver reacted produces one relative unit of cyan, magenta or yellow dye. Complete bleaching and fixing remove silver and halide. Only the three dye amounts go to disk. The printer reads that array in a separate invocation and uses the existing color lab's fixed paper and D50 illumination.

    python color.py probes probes.json
    python color.py write input-srgb.png developed-cmy.npy
    python color.py print developed-cmy.npy output

I keep all baths at 20 °C, unit strength and 18 model time units. Developer diffuses laterally inside each layer. Grain size and bath rates are design assumptions. The probe report averages linear print RGB across each uniform patch before encoding. It also prints a uniform negative at the mean dye load and compares immediate complete development of the exact same activated grains.

## Two-material wet print

I replaced unit silver-to-dye yield with local oxidized-developer and finite coupler fields. I use the same reaction solver with different development times and bath replenishment on film and paper. The paper has its own stochastic latent image and a separate saved dye field. The optical output uses finite-layer Kubelka–Munk reflection over a backing. I treat paper scattering as wavelength-independent, approximate its developed coating as homogeneous, and assume ideal silver removal. The earlier writer supplies display exposures and film absorption spectra. Its print response is bypassed. [Chemistry reference](https://www.kodak.com/content/pdfs/Using-KODAK-Kit-Chemicals-in-Motion-Picture-Film-Laboratories.pdf) · [Finite-layer reflection reference](https://library.imaging.org/admin/apis/public/api/ist/website/downloadArticle/cic/29/1/art00022)

    python wet_print.py film input-srgb.png results
    python wet_print.py paper results/film-cmy.npy results
    python wet_checks.py results/checks.json

The patch checks verify color-record ordering, capture and escape, monotone neutral levels, neighbor coupling after a single localized exposure, dye mass bounded by that exposure in the isolated-grain test, and bounded reflectance. I selected the material parameters as hypotheses. The first print's neutral range of 67–134 exposed excessive paper exposure and a high coating-scatter floor. I corrected relative print exposure to 0.35 and coating scatter to 0.01. The current controlled ramp spans about 25–227, with middle gray at 123. These values are material design choices guided by synthetic neutral targets. The paper_diagnosis.py experiment separates their effects.


    python paper_diagnosis.py paper-diagnosis.json

I compute large-frame reaction fields in overlapping tiles with a halo of two stencil radii per time step. A comparison against the complete field on a 677 × 731 random exposure map at 55 steps produced exactly equal arrays, including tile seams.


## Preferred print with subtle grain variation

The active version uses the corrected wet-print model. I apply a bounded ±1.5% variation to local film sensitivity before activation. Python uses a correlated random coating field. The browser uses a smooth seeded field within the same amplitude bound. Film grain sampling remains stochastic, and each browser run gets a fresh seed recorded with the trace. These implementations share the material equations and have independent grain patterns.

    FILM_NATIVE=1 python wet_print.py film input-srgb.png results
    FILM_NATIVE=1 python wet_print.py paper results/film-cmy.npy results

The optional native kernel compiles native.c with clang into the system temporary directory on first use. It uses the reference reaction equations, float32 state and no fast-math compiler option. Remove FILM_NATIVE to use NumPy. The native implementation supports macOS with clang. The browser implementation is JavaScript and runs in a worker.

    python native_benchmark.py native-benchmark.json

The benchmark excludes compilation, compares a million-pixel reaction field, and checks the resulting color codes on colored dye samples. Tiny floating-point rounding differences are possible.

## Browser studio

Open docs/chemistry.html through an HTTP server. It accepts JPEG, PNG, WebP and HEIC, offers preview or original-resolution processing, and exports a PNG and the measured trace. A fresh seed produces another grain realization. The selected pixel is fixed for each run. Graphs record the currently developing color record and the final spectrum. All image processing happens on-device.

The reference four-event latent-image rule is sampled directly in Python. The browser samples the mathematically equivalent activation probability. Its paper counts use inverse-binomial sampling. Spatial development and spectral reflection run explicitly in both implementations.
