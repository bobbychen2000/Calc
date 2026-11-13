#!/usr/bin/env python3
"""Ground backdrop textures from the committed NAIP 2024 mosaic (hwd3d P2, Phase 2).

Input : refs/cache/naip/naip_2024_hwd_rgb.jpg (+ .json): USDA NAIP 2024, 0.6 m, EPSG:26910, public domain
        (USDA FPAC-BC Geospatial Enterprise Operations; refs/cache/naip/SOURCES.json).
Output: js/world/tex/naip2024_<res>.jpg - the same UTM-aligned area, box-downsampled to 1.2 m and 2.4 m per pixel -
        and js/world/tex/naip2024.json: size, pixel size, the UTM origin, and the border colour (median of the outer
        200 m band, linear RGB) that the ground shader fades to beyond the imagery.
The world -> texture mapping is NOT computed here: js/live/airport.js fits it in the browser from js/geo.js
(worldToUtm10), the same frame code as everything else (max residual of the affine fit 6 mm over the area).
Deterministic: run `python3 js/world/tex/make_naip_tex.py` from hwd3d/.
"""
import json, os, sys
from PIL import Image
import numpy as np

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
SRC = os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_hwd_rgb.jpg')
META = json.load(open(os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_hwd_rgb.json')))


def main():
    im = Image.open(SRC).convert('RGB')
    W, H = im.size
    assert (W, H) == (META['width'], META['height']), (W, H)
    px = META['pixel_size_m']
    out = {'source': 'refs/cache/naip/naip_2024_hwd_rgb.jpg (USDA NAIP 2024, public domain)', 'crs': META['crs'],
           'origin_E': META['origin_E'], 'origin_N': META['origin_N'], 'origin_is': META['origin_is'],
           'flight_date': [t['flight_date'] for t in META['tiles']], 'credit': META['credit'],
           'made_by': 'hwd3d/js/world/tex/make_naip_tex.py', 'levels': {}}
    a = np.asarray(im).astype(np.float64) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    band = int(round(200 / px))
    mask = np.zeros((H, W), bool); mask[:band, :] = mask[-band:, :] = True; mask[:, :band] = mask[:, -band:] = True
    out['border_linear_rgb'] = [round(float(np.median(lin[..., k][mask])), 4) for k in range(3)]
    out['mean_linear_rgb'] = [round(float(lin[..., k].mean()), 4) for k in range(3)]
    for f, name in ((2, '1m2'), (4, '2m4')):
        w, h = W // f, H // f
        small = im.crop((0, 0, w * f, h * f)).resize((w, h), Image.BOX)
        fn = f'naip2024_{name}.jpg'
        small.save(os.path.join(HERE, fn), quality=85, optimize=True, progressive=False, subsampling=0)
        out['levels'][name] = {'file': fn, 'width': w, 'height': h, 'pixel_size_m': px * f, 'covers_m': [w * f * px, h * f * px],
                               'bytes': os.path.getsize(os.path.join(HERE, fn))}
    json.dump(out, open(os.path.join(HERE, 'naip2024.json'), 'w'), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
