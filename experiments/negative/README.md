# Synthetic negative → print rendering

I separated the color pipeline into two executable stages. The first writes a lossless 16-bit RGB PNG in the transmission convention of the scan thumbnails. The second reads that PNG and its fitted weights. The print reader receives only the negative and its fitted weights. The two stages run as separate processes. The browser demo implements the same two stages in a worker, passing 16-bit transmission values between stages in strips. Run export_web.py after fitting to refresh the browser parameters.

## Data and sources

**Copyrighted by Tien-Tsin Wong**. This is the required image credit for the BlueNeg material. Hanyuan Liu, Chengze Li, Minshan Xie, Zhenni Wang, Jiawen Liang, Chi-Sing Leung and Tien-Tsin Wong, *BlueNeg: A 35mm Negative Film Dataset for Restoring Channel-Heterogeneous Deterioration*, ICCV 2025. See [paper](https://openaccess.thecvf.com/content/ICCV2025/html/Liu_BlueNeg_A_35mm_Negative_Film_Dataset_for_Restoring_Channel-Heterogeneous_Deterioration_ICCV_2025_paper.html), [dataset and metadata](https://huggingface.co/datasets/ttgroup/blueneg-release) and [dataset terms](BlueNeg-LICENSE.txt). The manifest pins the data revision, individual scan/print paths, rolls and split. Only the specially prepared BlueNeg sample in the optional reproduction cache contains the researchers’ photographs. The demonstration photograph is the park portrait I supplied to Digital to Film.

**Film response.** I approximated RGB densities from section 20 of Fujifilm bulletin AF3-121E using a small set of visually read points. This is a later bulletin than the archived 1996 rolls. Status M density and scanner RGB differ. I approximate that difference by using training negatives to set the density range of each scanner channel. I treat the input as an already rendered sRGB image and invert its transfer function. Phone tone mapping and original spectral information remain unknown. The simulation currently covers color, film-base attenuation and nonlinear response. It omits physical grain, halation, and spectral cross-talk at exposure. [Manufacturer’s graph, archived by FilmColors](https://filmcolors.org/wp-content/uploads/2025/12/Fujicolor-Portrait-Film-NPH-400-Professional-_AF3-121E.pdf). I explore wavelength-dependent exposure in my [color emulsion lab](../emulsion/README.md).

**Real targets.** I selected intact NPH400 negatives with matching physical prints. I read the embedded 16-bit RGB negative thumbnail from each original DNG using byte ranges, and confirmed its negative polarity. The public 8-bit negative-preview PNG is already negated. For the pilot I resized the corresponding TIFF print, decoded it to 8-bit RGB and saved a JPEG training proxy. I registered the proxy to the thumbnail with SIFT and a RANSAC homography, excluding the border. Precision and potential profile differences in that print conversion limit the results. All nine registrations had at least 130 inlier matches. No synthetic positives or input park photographs were used to train the negative reader.

## Experiments

The fitted reader uses a regularized quadratic mapping from three normalized log-density channels to print RGB. Seven frames from three rolls contributed 3,000 matched pixels each. Two frames from a fourth roll were reserved for a pilot test. This split is independent of the authors’ official challenge split. The baseline is a fixed, per-channel density stretch estimated on training scans. The test reports 8-bit RGB error after registration. The two test frames come from the same event, so uncertainty is high. See scores.json. This measures negative-to-print rendering only.

For the gray-calibrated variant I passed a synthetic grayscale ramp through the frozen reader and fit six bounded exposure/balance parameters for the negative writer. Both park outputs use identical reader weights. This gray ramp is a modeling assumption, not a measured scanner calibration. The current production converter applies selective second passes, while this experimental scanner renders each negative once. The comparison is an inspection of those systems as used, not a controlled architecture ablation.

## Run

Use a fresh Python environment with the packages in requirements.txt. Supply an ordinary sRGB RGB JPEG or PNG. For HEIC or Display P3, first use the original converter’s color-managed read_rgb helper and save_rgb to export an oriented sRGB image without grading it.

    python negative_pipeline.py expose input.jpg negative.png
    python negative_pipeline.py develop negative.png result.jpg
    python negative_pipeline.py expose input.jpg balanced-negative.png --gray-calibration
    python negative_pipeline.py develop balanced-negative.png balanced-result.jpg

To reproduce the model, create a scratch folder and run fetch.py and register.py from that folder using their absolute paths. They use manifest.json from this experiment and write image pairs into the current folder. Then run train.py with the scratch folder as its argument. Download requires curl. Retain the BlueNeg image credit and license with any reproduced data. Never train on the held-out rolls when reporting these pilot scores.

## Next decisive test

Capture the same static scenes on iPhone ProRAW and on one fresh negative stock. Include a gray card and a color chart under daylight and artificial light. Keep the negative scan uninverted with fixed scanning settings, record the film base, and obtain a fixed-process positive of that frame. Fit stage one against the negative and stage two against the positive. Hold out complete rolls and lighting sessions. Compare the two-stage model with a direct model trained on the identical triples (digital → positive), a simple invert-then-learn control, and the existing converter. Score neutral patches, skin and foliage color, highlight roll-off, and blinded preferences. Use registered regions for pixel metrics. The physical negative is essential for diagnosing which stage causes each error.

## DigitalFilm stage-placement experiment

I used the Gold 200 archive and exact 256 digital + 256 film member lists recorded in the [existing manifest](../../converter/digitalfilm-gold.json). I reserved 64 additional filenames from each domain for evaluation. [DigitalFilm source and credits](https://huggingface.co/datasets/Richards-Sheehy-sudo/DigitalFilm_dataset) · [Fitted parameters, holdout IDs and scores](digitalfilm-adapters.json).

A fits three gains and three offsets in scanner density, evaluated through the frozen print reader. B freezes the negative writer and fits three gains and three offsets on the reader’s print output. Each fit minimizes a regularized squared difference at five marginal quantiles per RGB channel. I sample the same number of interior pixels from every photo. The weak supervision comes from aggregate film color statistics; DigitalFilm supplies no corresponding physical negatives. C combines A’s writer and B’s reader without refitting. This tests whether their separately fitted changes stack. A jointly optimized two-stage model would answer a different question.

Run `python fit_digitalfilm.py /path/to/Kodak_gold_200.zip` to refit and `python export_web.py` to export browser parameters. For a full-resolution local run, pass the same `--branch A`, `--branch B`, or `--branch C` to both the expose and develop commands above. Each branch uses the baseline gray calibration. On the same input, B has exactly the baseline negative and C has exactly A’s negative. The reader still consumes only the saved transmission image at inference.
