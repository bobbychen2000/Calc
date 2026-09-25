"""Airport shoreline (land / Bay water) from USDA NAIP 2024 near-infrared -> data/sfo_shore.json / .js.

Why (review round 3): the terrain used only the hand-drawn 16-vertex AIRPORT_LAND_ST polygon (js/geo.js) as the
airport landfill. On NAIP it is off by tens of metres: its east edge lies 44 m out in the Bay beyond the 28L / 28R
seawall (the NAIP-measured approach-light catwalks then started on rendered land), and it made the whole north basin
(open water between the maintenance base and the 19L/19R ends) land. js/geo.js keeps that polygon for the shaders
(a fixed 16-vertex uniform = the airport *area* mask); the land / water decision of js/world/terrain.js now uses
this file.

Method: NAIP 2024 bands R, G and NIR (EPSG:26910 GeoTIFF, refs/cache/naip/, public domain) sampled on a 2 m world grid
(exact per-point mapping, tools/imagery/common.py NaipSampler). Water = NDWI = (G - NIR) / (G + NIR) > 0.25 and
(NIR < 90 or NIR < 0.65 R: sun glint), on bands box-filtered over 10 m (glint speckle)
(measured: Bay 0.42-0.89 with NIR 7-59 incl. sun glint; asphalt / concrete 0.07-0.20 with NIR >= 114; grass / sand
< 0). Cleaned with a 3 px opening / closing; water bodies < 5000 m2 (puddles, dark roofs, shadows) are land. Land = the
connected non-water component containing the ARP (the airport and the mainland it joins, over the whole NAIP coverage),
after cutting connections thinner than ~12 m (catwalks, glint patches beyond the 28 seawalls) and regrowing 12 m inside
the classified land. Holes are filled. Contours simplified to 1.0 m; `nodata` = where NAIP has no pixels (unknown).
Observed (NAIP 2024, 2024-05-20); the Bay's tide level on that day sets the water line on the natural shores; the
airport's seawalls are vertical, so the line there is the seawall crest to ~1-2 m (2 m grid).
Usage: python3 tools/imagery/shore_naip.py
"""
import json, os, sys, subprocess
import numpy as np, cv2
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, 'tools'))
from common import NaipSampler  # noqa: E402
import geo_frame as GF  # noqa: E402

RES = 2.0
X0, Z0, X1, Z1 = -2600.0, -2350.0, 2240.0, 2640.0


def land_st_world():
    out = subprocess.run(['node', '--input-type=module', '-e', "import {stToWorld, AIRPORT_LAND_ST} from './js/geo.js'; "
                          "console.log(JSON.stringify(AIRPORT_LAND_ST.map(([s,t])=>{const w=stToWorld(s,t,0); return [w[0],w[2]];})))"],
                         capture_output=True, text=True, cwd=ROOT, check=True).stdout.strip().splitlines()[-1]
    return json.loads(out)


def main():
    S = NaipSampler('2024', bands=(1, 2, 4))
    xs = X0 + (np.arange(int((X1 - X0) / RES)) + 0.5) * RES; zs = Z0 + (np.arange(int((Z1 - Z0) / RES)) + 0.5) * RES
    W, H = len(xs), len(zs)
    Rr = np.zeros((H, W), np.float32); G = np.zeros((H, W), np.float32); N = np.zeros((H, W), np.float32)
    for j0 in range(0, H, 256):
        Zg, Xg = np.meshgrid(zs[j0:j0 + 256], xs, indexing='ij')
        v = S(Xg, Zg, gray=False)
        Rr[j0:j0 + 256] = v[..., 0]; G[j0:j0 + 256] = v[..., 1]; N[j0:j0 + 256] = v[..., 2]
    valid = (G > 0) | (N > 0)
    # sparkle glint (sub-metre white specks) averages out over 10 m; a symmetric box filter keeps the 50 % crossing of a
    # straight seawall where it is
    Rr, G, N = (ndi.uniform_filter(a, size=5) for a in (Rr, G, N))
    ndwi = (G - N) / (G + N + 1.0)
    # sun glint lifts every band of the water (NIR up to ~85-100 east of the 28 ends) but keeps NIR well below red
    # (water NIR / R 0.40-0.58; concrete 0.94-1.06, grass / sand > 1); dark asphalt keeps NDWI <= 0.20
    water = (ndwi > 0.25) & ((N < 90) | (N < 0.65 * Rr)) & valid
    water = ndi.binary_opening(water, iterations=3); water = ndi.binary_closing(water, iterations=3)
    lab, n = ndi.label(water); sz = ndi.sum(water, lab, range(1, n + 1)) * RES * RES
    water = np.isin(lab, 1 + np.nonzero(sz >= 5000)[0])
    land0 = (~water) & valid
    # the approach-light catwalks, crossbars and sun-glint patches beyond the 28 seawalls classify as land in places and
    # hang on the airport through the thin catwalks: cut thin connections (opening by 12 m), keep the component with the
    # ARP (the airport and the mainland it joins), grow it back by 12 m inside the original land (restores the seawall
    # line), drop thin stubs (6 m opening)
    core = ndi.binary_opening(land0, iterations=6)
    lab, n = ndi.label(core)
    i0, j0 = int((0 - Z0) / RES), int((0 - X0) / RES)
    core = lab == lab[i0, j0]
    land = ndi.binary_dilation(core, iterations=6) & land0
    land = ndi.binary_opening(land, iterations=3) | core
    lab, n = ndi.label(land); land = lab == lab[i0, j0]
    land = ndi.binary_fill_holes(land)
    nodata = ndi.binary_dilation(~valid, iterations=3)
    def rings_of(mask, tol, min_area):
        cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        out = []
        for c in cs:
            if cv2.contourArea(c) * RES * RES < min_area: continue
            c = cv2.approxPolyDP(c.astype(np.float32), tol / RES, True)[:, 0, :]
            out.append([[round(float(X0 + (p[0] + 0.5) * RES), 1), round(float(Z0 + (p[1] + 0.5) * RES), 1)] for p in c])
        return out
    rings = rings_of(land, 1.0, 1e4); nodata_rings = rings_of(nodata, 2.0, 100.0)
    area_ha = float(land.sum()) * RES * RES / 1e4
    P = np.array(land_st_world())
    old = np.zeros((H, W), np.uint8); cv2.fillPoly(old, [np.round(((P - [X0, Z0]) / RES - 0.5) * 16).astype(np.int32)], 1, shift=4)
    wet_old = old.astype(bool) & water
    doc = {'frame': GF.FRAME_ID, 'source': 'USDA NAIP 2024 (2024-05-20, public domain) NIR / NDWI water classification, tools/imagery/shore_naip.py',
           'res_m': RES, 'rule': 'water = NDWI > 0.25 and (NIR < 90 or NIR < 0.65 R) on 10 m box-filtered bands; water bodies >= 5000 m2; '
                                 'land = the component with the ARP (airport + mainland), thin (< 12 m) connections cut',
           'land_ha': round(area_ha, 1), 'area_polygon_water_ha': round(float(wet_old.sum()) * RES * RES / 1e4, 1),
           'coverage': [X0, Z0, X1, Z1], 'rings': rings, 'nodata': nodata_rings,
           'note': 'inside `coverage`: land inside `rings`, no data inside `nodata`, Bay water elsewhere; outside it: unknown'}
    json.dump(doc, open(os.path.join(ROOT, 'data', 'sfo_shore.json'), 'w'), separators=(',', ':'))
    open(os.path.join(ROOT, 'data', 'sfo_shore.js'), 'w').write(
        '// generated by tools/imagery/shore_naip.py - shoreline measured on USDA NAIP 2024 (public domain; credit: USDA FPAC-BC GEO)\n'
        'export const SHORE = ' + json.dumps(doc, separators=(',', ':')) + ';\n')
    print('shore: %d land ring(s) (%s vertices), %d no-data ring(s); land %.0f ha; water inside AIRPORT_LAND_ST %.1f ha' % (
        len(rings), '+'.join(str(len(r)) for r in rings), len(nodata_rings), area_ha, doc['area_polygon_water_ha']))
    # debug overlay (NAIP pixels -> out/ only)
    os.makedirs(os.path.join(ROOT, 'out', 'shore'), exist_ok=True)
    img = np.dstack([(water * 180).astype(np.uint8), (land * 160).astype(np.uint8), (old * 90).astype(np.uint8)])
    for r in rings: cv2.polylines(img, [np.array([[(p[0] - X0) / RES, (p[1] - Z0) / RES] for p in r], np.int32)], True, (255, 255, 255), 1)
    cv2.imwrite(os.path.join(ROOT, 'out', 'shore', 'shore_mask.png'), img[::2, ::2])


if __name__ == '__main__':
    main()
