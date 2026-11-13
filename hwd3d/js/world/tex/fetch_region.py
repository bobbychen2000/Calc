#!/usr/bin/env python3
"""Regional ground backdrop beyond the HWD NAIP mosaic (hwd3d P2, Phase 2).

The committed 0.6 m mosaic (refs/cache/naip/naip_2024_hwd_rgb.jpg) covers only 3.8 x 3.3 km around the field; beyond it
the ground shader had a flat border colour. This script asks the USDA FPAC-BC GEO NAIP image service (the public-domain
source of that mosaic: tools/imagery/naip_fetch.py --source usda) for ONE resampled 2024 image of a 24 x 24 km square
centred on the HWD ARP, at 8 m per pixel (3000 x 3000 px, under the service's 4100 px limit), in UTM 10N (EPSG:26910),
restricted to the 2024 flights and the service overviews (mosaicRule where year_ts = 2024 OR year_ts IS NULL: at 8 m the service draws from its overview rasters, which carry no year; a first request with year_ts = 2024 alone returned an all-black image). One request; nothing is retried automatically.

Output: js/world/tex/naip2024_region_8m.jpg (JPEG q 82) + the 'region' entry of js/world/tex/naip2024.json (UTM origin =
outer north-west corner, pixel size, request URL and parameters, fetch date, sha256 of the raw download). The raw
response goes to its own new directory (untrusted download) and is never executed or imported.
Licence: NAIP is public domain (USDA; credit "USDA NAIP"), refs/cache/naip/SOURCES.json.

No-data: one 2024 quad over the open Bay has no imagery in the service (black square); those pixels are filled by a
push-pull pyramid interpolation of the surrounding (water) pixels, flagged in the metadata. A 16 m level (1500 px) is written
for the phone quality tier.

usage (from hwd3d/): python3 -I js/world/tex/fetch_region.py <empty download dir>
                     python3 -I js/world/tex/fetch_region.py --from-raw <region_raw.jpg>   (re-process, no request)
"""
import datetime, hashlib, io, json, os, sys, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
USDA = 'https://apps.geo.fpac.usda.gov/geo-imagery/rest/services/naip/conus_naip/ImageServer'
ARP_UTM = (577465.5, 4168336.6)     # tools/common/hwd_frame.py ll_to_utm10(ARP) (NASR ARP)
HALF = 12000.0                      # m
PX = 8.0                            # m per pixel


def main():
    e0 = round((ARP_UTM[0] - HALF) / PX) * PX; n1 = round((ARP_UTM[1] + HALF) / PX) * PX
    n = int(2 * HALF / PX); e1 = e0 + n * PX; n0 = n1 - n * PX
    params = dict(bbox=f'{e0:.1f},{n0:.1f},{e1:.1f},{n1:.1f}', bboxSR=26910, imageSR=26910, size=f'{n},{n}', format='jpg',
                  compressionQuality=92, pixelType='U8', interpolation='RSP_BilinearInterpolation', bandIds='0,1,2',
                  mosaicRule=json.dumps({'mosaicMethod': 'esriMosaicNorthwest', 'where': 'year_ts = 2024 OR year_ts IS NULL'}), f='image')
    url = USDA + '/exportImage?' + urllib.parse.urlencode(params)
    if sys.argv[1] == '--from-raw':
        raw = open(sys.argv[2], 'rb').read(); fetched = None
    else:
        dl = sys.argv[1]; os.makedirs(dl, exist_ok=False)
        raw = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'hwd3d-naip-backdrop/1'}), timeout=300).read()
        open(os.path.join(dl, 'region_raw.jpg'), 'wb').write(raw); fetched = datetime.date.today().isoformat()
    import numpy as np
    from PIL import Image
    from scipy import ndimage as ndi
    im = Image.open(io.BytesIO(raw)).convert('RGB')
    assert im.size == (n, n), im.size
    a = np.asarray(im).astype(np.float32)
    nod = a.max(-1) < 12                                    # service no-data (black)
    lab, nl = ndi.label(nod); sizes = ndi.sum(nod, lab, range(1, nl + 1))
    nod = np.isin(lab, 1 + np.nonzero(sizes > 400)[0])      # only large holes (not dark roofs / shadows)
    nod = ndi.binary_dilation(nod, iterations=4)            # JPEG ringing at the square's edge
    filled = 0
    if nod.any():
        # pyramid (push-pull) fill: mask-weighted averages of the valid pixels at halving resolutions, then filled back
        # up from the coarsest level, so the hole takes a smooth interpolation of the surrounding water colours
        def push_pull(img, valid):
            if min(img.shape[:2]) <= 2: 
                m = valid.astype(np.float32); return np.where(valid[..., None], img, (img * m[..., None]).sum((0, 1)) / max(m.sum(), 1))
            h, w = img.shape[:2]; h2, w2 = (h + 1) // 2, (w + 1) // 2
            pi = np.zeros((h2 * 2, w2 * 2, 3), np.float32); pm = np.zeros((h2 * 2, w2 * 2), np.float32)
            pi[:h, :w] = img * valid[..., None]; pm[:h, :w] = valid
            si = pi.reshape(h2, 2, w2, 2, 3).sum((1, 3)); sm = pm.reshape(h2, 2, w2, 2).sum((1, 3))
            small = push_pull(np.where(sm[..., None] > 0, si / np.maximum(sm, 1e-6)[..., None], 0), sm > 0)
            up = np.repeat(np.repeat(small, 2, 0), 2, 1)[:h, :w]
            up = np.stack([ndi.gaussian_filter(up[..., k], 1.0) for k in range(3)], -1)
            return np.where(valid[..., None], img, up)
        a = push_pull(a, ~nod); filled = int(nod.sum())
    im = Image.fromarray(a.clip(0, 255).astype(np.uint8))
    out = os.path.join(HERE, 'naip2024_region_8m.jpg')
    im.save(out, quality=82, optimize=True, subsampling=0)
    out16 = os.path.join(HERE, 'naip2024_region_16m.jpg')
    im.resize((n // 2, n // 2), Image.BOX).save(out16, quality=82, optimize=True, subsampling=0)
    meta = json.load(open(os.path.join(HERE, 'naip2024.json')))
    prev = meta.get('region', {})
    lin = np.where(a / 255 <= 0.04045, a / 255 / 12.92, ((a / 255 + 0.055) / 1.055) ** 2.4)
    band = int(1000 / PX); m = np.zeros(a.shape[:2], bool); m[:band] = m[-band:] = True; m[:, :band] = m[:, -band:] = True
    border = [round(float(np.median(lin[..., k][m])), 4) for k in range(3)]
    meta['region'] = {'file': 'naip2024_region_8m.jpg', 'file_16m': 'naip2024_region_16m.jpg', 'width': n, 'height': n, 'pixel_size_m': PX, 'origin_E': e0, 'origin_N': n1,
                      'origin_is': 'outer north-west corner of pixel (col 0, row 0)', 'crs': 'EPSG:26910',
                      'covers_m': [n * PX, n * PX], 'bytes': os.path.getsize(out), 'bytes_16m': os.path.getsize(out16),
                      'nodata_filled_px': filled, 'border_linear_rgb': border,
                      'request': {'url': USDA + '/exportImage', 'params': params}, 'fetched': fetched or prev.get('fetched'),
                      'raw_sha256': hashlib.sha256(raw).hexdigest(),
                      'note': 'USDA image-service resampling (bilinear) of the 2024 NAIP flights (28 quads, all flown 2024-05-20 per the service query) and its overviews, Northwest mosaic; no-data square over the open Bay filled by push-pull interpolation of the surrounding water; JPEG q 82'}
    json.dump(meta, open(os.path.join(HERE, 'naip2024.json'), 'w'), indent=1)
    print(json.dumps(meta['region'], indent=1))


if __name__ == '__main__':
    main()
