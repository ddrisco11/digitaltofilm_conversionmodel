# Film and digital photo pairs

The [iPhone film converter](converter/README.md) includes trained color models, a full-resolution HEIC/JPEG command, held-out FilmSet scores and a blind review tool.

The [pair index](pairs.csv) lists 39 film/digital comparisons and points to all 78 local image files. Each row gives the photographer or project credits, the source for each side, and the pairing evidence. Framing, poses, timing and processing vary. For a scene-level train/test split, keep repeated views and sessions together using `scene_group`.

| Collection | Pairs | Local files |
| --- | ---: | --- |
| Flickr group | 17 | Display JPEGs |
| Sillystill | 13 | Camera files and published research figures |
| Cameron Eng | 7 | Film and digital crops of published comparisons |
| Julia Trotti | 2 | Published WebP portraits |

## Photographer comparisons

Cameron Eng photographed the landscapes on Kodak Portra 400 at 35 mm and digitally at 28 mm. His article identifies the digital frame as the left or upper panel. Each crop is saved as a PNG. Both sides link to the published diptych, and the index records the crop bounds as left, top, right, bottom in source pixels, with right and bottom exclusive. [Original comparison by Cameron Eng](https://www.cameroneng.ca/journal/35mm-portra-400-vs-digital-comparison)

Julia Trotti compared a Yashica 635 loaded with Kodak Portra 160 with a Sony A7III in the same portrait session. The two selected comparisons are labeled by the photographer. She color-corrected and retouched the film scans and edited the digital photographs with a preset. The index links to each published image and to the article for context. [Original comparison by Julia Trotti](https://juliatrotti.com/blogs/photography/film-vs-digital-portrait-photography)

For both galleries the repository provides attribution and source links. Their image files are local-only because an explicit redistribution license was unavailable.

## CineStill 800T paper examples

The 13 Sillystill entries include one original camera-file pair (Sony ARW and film-scan JPEG) and twelve pairs of figure assets at their published sizes. Three entries show the same scooter scene in different representations. They share a `scene_group` so they can be kept together when splitting the data. Result figures can show crops.

Pierre Mackenzie, Mika Senghaas and Raphaël Achddou report collecting 41 raw pairs and retaining 38 after preprocessing. Their project README lists the full dataset download as pending. This collection includes the examples recoverable from the authors’ repository. [Paper](https://arxiv.org/html/2411.15967v1) · [Authors’ repository and download status](https://github.com/mikasenghaas/sillystill)

The figure files are credited to the authors above under the paper’s [CC BY 4.0 license](https://creativecommons.org/licenses/by/4.0/). The files were copied without edits from the authors’ report sources and verified against their Git blob hashes. The original café files are local-only because their separate redistribution terms were unclear. Each Sillystill row links to the exact revision of both source files. [Original café files](https://github.com/mikasenghaas/sillystill/tree/b1ebdb971207b403b7126b759c1d30d30954a722/imgs) · [Report figures](https://github.com/mikasenghaas/sillystill/tree/b1ebdb971207b403b7126b759c1d30d30954a722/report/figures)

## Flickr sources

The 17 Flickr pairs were selected by matching subjects and creators and checking the available medium evidence. The `digital_label_basis` column identifies inferred digital labels. All 34 photos are marked All Rights Reserved and their files are stored locally. [Original group pool](https://www.flickr.com/groups/lomoplusdigital/pool/)

[sources.csv](sources.csv) preserves the original titles, creator profiles, Flickr pages and license information for the 34 retained photos. [Excluded Flickr sources](excluded-flickr-sources.csv) preserves the attribution history for the 102 removed photos. Paths in that historical file refer to their former locations.

## GitHub copy

GitHub includes the pair index, source records and 24 Sillystill figure images. Paths beginning with `local-only/` are available on the collecting computer. The index provides original source links for those images.
