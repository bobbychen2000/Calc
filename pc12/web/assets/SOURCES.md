# Viewer assets

| file | source | licence |
|---|---|---|
| `studio_small_09_1k.hdr` | Poly Haven, "Studio Small 09" by Sergej Majboroda, 1k Radiance HDR: https://polyhaven.com/a/studio_small_09 (download: https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/1k/studio_small_09_1k.hdr) | CC0 1.0 (https://polyhaven.com/license) |
| `studio_small_09_512.hdr` | the same HDRI, 512 x 256: a 2 x 2 box filter of `studio_small_09_1k.hdr` in linear light, written as run-length encoded RGBE | CC0 1.0 |

`studio_small_09` is the environment the Blender hero render uses (`render/beauty.py`, 2k there); the viewer
loads the 1k file (the 512 px one on phones, `QUALITY.low`: a quarter of the download, the same look at phone
sizes) with `RGBELoader` and prefilters it with `PMREMGenerator` for reflections and ambient light, after the
per-theme grade in `viewer/studio.js` (the light theme adds rows of ceiling LED strips there). It is never shown as
the background.
