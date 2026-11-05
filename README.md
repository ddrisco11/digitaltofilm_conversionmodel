# Analog + Digital (pairs)
 
The Flickr collection contains 136 photographs from both pages of the [Flickr group pool](https://www.flickr.com/groups/lomoplusdigital/pool/), collected November 5, 2026. It contains 17 same-scene film/digital pairs and 102 photos without an assigned pair.

## CineStill 800T paper examples

The combined [pair index](pairs.csv) has 30 entries. Filter `source_collection` to choose the 17 Flickr pairs or the 13 Sillystill entries. The latter include one original camera-file pair (Sony ARW and film-scan JPEG) and twelve pairs of figure assets at their published sizes. Three entries show the same scooter scene in different representations. They share a `scene_group` so they can be kept together when splitting the data. Result figures can show crops.

Pierre Mackenzie, Mika Senghaas and Raphaël Achddou report collecting 41 raw pairs and retaining 38 after preprocessing. Their project README lists the full dataset download as pending. This collection includes the examples recoverable from the authors’ repository. [Paper](https://arxiv.org/html/2411.15967v1) · [Authors’ repository and download status](https://github.com/mikasenghaas/sillystill)

The figure files are credited to the authors above under the paper’s [CC BY 4.0 license](https://creativecommons.org/licenses/by/4.0/). The files were copied without edits from the authors’ report sources and verified against their Git blob hashes. The original café files are local-only because their separate redistribution terms were unclear. Each Sillystill row links to the exact revision of both source files. [Original café files](https://github.com/mikasenghaas/sillystill/tree/b1ebdb971207b403b7126b759c1d30d30954a722/imgs) · [Report figures](https://github.com/mikasenghaas/sillystill/tree/b1ebdb971207b403b7126b759c1d30d30954a722/report/figures)

## Using the Flickr pairs

Each row in [pairs.csv](pairs.csv) identifies the film and digital images by relative file path, Flickr ID, creator and source page. Open the two paths on the same row to compare the photographs. Framing, viewpoint, exposure and timing can differ. Pixelwise comparisons require registration.

The pairs were selected by visual comparison of the same subject and scene, matching authorship, and film evidence in the titles or descriptions. The digital label is inferred where the uploader supplied no explicit camera or medium. The final column records this distinction. The remaining pool entries are catalogued individually.

## Attribution and files

[sources.csv](sources.csv) credits each Flickr photo by title, creator, creator profile, original Flickr page and license. It also gives the image dimensions and local filename. Files are Flickr-served JPEGs copied without edits.

The local collection includes every catalogued photo. The GitHub copy includes 77 photos by alcides OTA under [CC BY-NC 2.0](https://creativecommons.org/licenses/by-nc/2.0/). Reuse of these photos requires attribution and is limited to noncommercial purposes under that license.

The other 59 photos are marked All Rights Reserved. Their files are kept in the local-only folder on the collecting computer. All 17 Flickr pairs use photos from this folder. On GitHub, use the individual source links in pairs.csv to view both sides of a pair on Flickr.
