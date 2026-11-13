#!/usr/bin/env python3
"""Airside pavement seen on NAIP but missing from the OSM pavement -> hwd3d/js/aircraft/pave_naip.js (hwd3d Phase 2, P3).

Why: the site model's pavement (js/world/site.js paved: runways + OSM taxi ribbons at default widths + OSM aprons +
helipads) misses real airside asphalt - the wide entries of the run-up pads, apron edges short of hangar fronts, the
paved helicopter area south of 10R/28L (data/hwd_airport.json not_placed). Aircraft are observed standing and taxiing
there (ADS-B), the NAIP-textured ground shows asphalt, but the solid-body physics would push them onto the nearest OSM
ribbon. This mask adds that asphalt by the Phase 1 grey test, under the same airside rules P1 used for the taxi-graph
connectors (tools/live/build_taxigraph.py): inside the OSM aerodrome boundary, never in an OSM car park, never inside a
building / hangar footprint (dilated 1 m), never across a fence, and only where it is CONNECTED to the OSM pavement and
within MAX_FROM_OSM_M of it (an isolated grey roof or a landside road does not count) [inf rules].
Grey test (Phase 1 tools/build_airport.py on_pavement, reused by P1): median HSV saturation and median excess green in a
2-m disc, with the thresholds re-calibrated below (SAT_MAX 0.20, EG_MAX 6.5 instead of 0.16 / 8).
Inputs (read only): data/hwd_airport.json, refs/cache/osm/overpass_khwd_at_20261112T000000Z.json (through P1's
build_taxigraph.landside), refs/cache/naip/naip_2024_hwd_rgb.jpg (USDA NAIP 2024, public domain; tools/imagery Naip).
Output: js/aircraft/pave_naip.js = {x0, z0, res 1 m, nx, nz, rows: run-length [start, length, ...] per row of the ADDED
cells (OSM pavement itself is not repeated), stats}; out/traffic/pave_mask.png (overview for checking).
usage: python3 -I hwd3d/tools/traffic/build_pave_mask.py [--plot]
"""
import argparse, hashlib, json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); HWD = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(HWD, 'tools', 'live')); sys.path.insert(0, os.path.join(HWD, 'tools', 'imagery')); sys.path.insert(0, os.path.join(HWD, 'tools', 'common'))
import build_taxigraph as BT  # noqa: E402  (P1: landside(), SAT_MAX, EG_MAX, NAIP_DISC_M; read only)
from paintline import Naip  # noqa: E402
import hwd_frame as F  # noqa: E402

RES = 1.0
MAX_FROM_OSM_M = 30.0     # added asphalt must lie within this of OSM pavement [inf]
# grey test thresholds: Phase 1 / P1 use saturation < 0.16 and excess green < 8; the old beige asphalt of the run-up pads
# and taxiway shoulders measures 0.17-0.19 (e.g. world (358, 36), (387, 38) beside the 28R run-up pad). Calibrated here on a
# random 6,000-cell sample each: OSM apron cells pass 92.7 % at 0.20 / 6.5 (95.4 % at 0.16 / 8); aerodrome cells > 30 m
# from OSM pavement - grass, but also unmapped asphalt, roads and roofs, so an upper bound of false positives - pass
# 27.3 % (25.2 %). The connectivity and distance rules carry the rest [inf].
SAT_MAX, EG_MAX = 0.20, 6.5
OUT = os.path.join(HWD, 'js', 'aircraft', 'pave_naip.js')


def raster_polys(polys, x0, z0, nx, nz, dilate=0.0):
    from PIL import Image, ImageDraw
    im = Image.new('1', (nx, nz), 0); d = ImageDraw.Draw(im)
    for g in polys:
        if dilate: g = g.buffer(dilate)
        for p in getattr(g, 'geoms', [g]):
            if p.is_empty or p.geom_type != 'Polygon': continue
            d.polygon([((x - x0) / RES - 0.5, (z - z0) / RES - 0.5) for x, z in p.exterior.coords], fill=1)
            for h in p.interiors: d.polygon([((x - x0) / RES - 0.5, (z - z0) / RES - 0.5) for x, z in h.coords], fill=0)
    return np.asarray(im, dtype=bool)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--plot', action='store_true'); a = ap.parse_args()
    from shapely.geometry import Polygon, LineString
    from scipy import ndimage
    A = json.load(open(os.path.join(HWD, 'data', 'hwd_airport.json')))
    AERO, PARK, FENCE, _ids = BT.landside()
    bx0, bz0, bx1, bz1 = AERO.bounds
    x0 = math.floor(bx0 / 10) * 10 - 10; z0 = math.floor(bz0 / 10) * 10 - 10; nx = int(math.ceil((bx1 + 10 - x0) / RES)); nz = int(math.ceil((bz1 + 10 - z0) / RES))
    # OSM pavement as the site model draws it (site.js: runway rectangles, taxi ribbons at wayWidth, aprons, helipads)
    pav = [Polygon(r['outline']['ring']) for r in A['runways']] + [Polygon(x['ring']) for x in A['aprons']] + [Polygon(x['ring']) for x in A['helipads']]
    for k in ('taxiways', 'taxilanes'):
        for w in A[k]:
            W = w.get('width') or {}
            m = W.get('naip_grey_width_m') if W.get('naip_src') == 'obs' and W.get('naip_grey_width_m') else (W.get('default_m') or (7.62 if w['kind'] == 'taxilane' else 10.67))
            pav.append(LineString(w['pts']).buffer(m / 2))
    OSM = raster_polys(pav, x0, z0, nx, nz)
    AER = raster_polys([AERO], x0, z0, nx, nz)
    PK = raster_polys([PARK], x0, z0, nx, nz) if not PARK.is_empty else np.zeros_like(OSM)
    BLD = raster_polys([Polygon(o['ring']) for o in A['buildings'] + A['hangars'] if len(o.get('ring') or []) >= 3], x0, z0, nx, nz, dilate=1.0)
    FN = raster_polys([FENCE.buffer(0.8)], x0, z0, nx, nz) if not FENCE.is_empty else np.zeros_like(OSM)
    # NAIP grey test per cell (2-m disc, 9 samples, medians)
    naip = Naip('2024')
    dg = np.linspace(-BT.NAIP_DISC_M, BT.NAIP_DISC_M, 5); DX, DZ = np.meshgrid(dg, dg); msk = np.hypot(DX, DZ) <= BT.NAIP_DISC_M; DX, DZ = DX[msk], DZ[msk]
    GREY = np.zeros((nz, nx), bool)
    xs = x0 + (np.arange(nx) + 0.5) * RES
    for j in range(nz):
        z = z0 + (j + 0.5) * RES
        need = AER[j] & ~OSM[j]
        if not need.any(): continue
        X = xs[need][:, None] + DX[None, :]; Z = np.full_like(X, z) + DZ[None, :]
        R_, G_, B_ = (naip.sample(X, Z, k) for k in 'RGB')
        mx = np.maximum(np.maximum(R_, G_), B_); mn = np.minimum(np.minimum(R_, G_), B_)
        sat = np.median((mx - mn) / np.maximum(mx, 1.0), axis=1); eg = np.median(G_ - (R_ + B_) / 2.0, axis=1)
        row = np.zeros(nx, bool); row[need] = (sat < SAT_MAX) & (eg < EG_MAX); GREY[j] = row
    cand = GREY & AER & ~PK & ~BLD & ~FN & ~OSM
    cand = ndimage.binary_opening(cand, structure=np.ones((3, 3)))          # speckle (single grey pixels on grass)
    dist = ndimage.distance_transform_edt(~OSM) * RES
    cand &= dist <= MAX_FROM_OSM_M
    lab, n = ndimage.label(cand | OSM, structure=np.ones((3, 3)))
    keep = np.unique(lab[OSM]); keep = keep[keep > 0]
    ADD = cand & np.isin(lab, keep)
    # paint is not grey: hold bars, centrelines and tie-down tees punch 1-3 m holes into the grey test; a closing (5 x 5 m)
    # fills holes up to ~4 m across, then the airside rules are applied again
    full = ndimage.binary_closing(OSM | ADD, structure=np.ones((5, 5)))
    ADD = full & ~OSM & AER & ~PK & ~BLD & ~FN
    # one cell of overlap with the OSM pavement: the site model rasterises its ribbons on its own 0.5-m grid, so a seam of
    # unpaved slivers would otherwise remain between the two masks
    ADD = ndimage.binary_dilation(ADD, structure=np.ones((3, 3))) & AER & ~PK & ~BLD & ~FN
    rows = []
    for j in range(nz):
        r = ADD[j]; out = []
        if r.any():
            d = np.diff(np.r_[0, r.astype(np.int8), 0]); s = np.where(d == 1)[0]; e = np.where(d == -1)[0]
            for a_, b_ in zip(s, e): out += [int(a_), int(b_ - a_)]
        rows.append(out)
    stats = {'osm_pavement_m2': int(OSM.sum() * RES * RES), 'added_m2': int(ADD.sum() * RES * RES), 'grey_candidates_m2': int((GREY & ~OSM).sum()),
             'removed_car_park_m2': int((GREY & PK & ~OSM).sum()), 'removed_building_m2': int((GREY & BLD & ~OSM).sum()), 'max_from_osm_m': MAX_FROM_OSM_M}
    sha = hashlib.sha256(open(os.path.join(HWD, 'refs', 'cache', 'naip', 'naip_2024_hwd_rgb.jpg'), 'rb').read()).hexdigest()
    hdr = ('// generated by tools/traffic/build_pave_mask.py - do not edit. Airside asphalt that USDA NAIP 2024 (public domain; sha256 %s)\n'
           '// shows grey (Phase 1 grey test: saturation < %.2f, excess green < %.0f in a 2-m disc) inside the OSM aerodrome boundary, outside OSM car\n'
           '// parks / buildings / fences, connected to and within %.0f m of the OSM pavement of data/hwd_airport.json - added to the site pavement\n'
           '// for the ground physics (js/live/ground.js). Cells are 1 m; rows: [start, length, ...] of added cells. Derived in part from OSM\n'
           '// (c) OpenStreetMap contributors, ODbL 1.0 (https://opendatacommons.org/licenses/odbl/1-0/).\n' % (sha[:16], SAT_MAX, EG_MAX, MAX_FROM_OSM_M))
    body = json.dumps({'x0': x0, 'z0': z0, 'res': RES, 'nx': nx, 'nz': nz, 'stats': stats, 'rows': rows}, separators=(',', ':'))
    open(OUT, 'w').write(hdr + 'export const PAVE_NAIP = ' + body + ';\n')
    print('wrote', OUT, os.path.getsize(OUT), 'bytes', stats)
    if a.plot:
        from PIL import Image
        img = np.zeros((nz, nx, 3), np.uint8); img[AER] = (40, 50, 40); img[OSM] = (150, 150, 150); img[ADD] = (255, 140, 0); img[BLD] = (255, 255, 255); img[PK & ~OSM] = (90, 0, 120)
        Image.fromarray(img).save(os.path.join(HWD, 'out', 'traffic', 'pave_mask.png')); print('plot out/traffic/pave_mask.png')


if __name__ == '__main__':
    main()
