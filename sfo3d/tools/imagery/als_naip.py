"""Approach-light structures of 28L and 28R over the Bay, measured on USDA NAIP 2024 (public domain; 0.5 m world
raster, refs/cache/naip/) - review round 3 (the model had FAA-standard piers every 200 ft at 28L and +-2.6 m crossbars
at 28R; the imagery shows a continuous catwalk, stations every 100 ft and +-12..17 m crossbars).

Method: an oriented strip along each extended runway centreline (NASR threshold = runway end + displacement, js/geo.js
RWY_ENDS; outward = away from the runway), 0.2 m pixels, 0..2550 ft from the threshold, +-30 m across.
  stations  dark station platforms / light-bar shadows on the axis (lateral -1.6..+1.2 m): peaks of darkness >= 25 grey
            levels below the water, >= 15 m apart
  catwalk   the bright deck ridge beside the axis: lateral position = median profile peak over 700-2400 ft
  crossbars at each station the dark bar across the axis, contrast against the same columns 3-6 m before / after the
            station (removes water texture); half-length = where the contrast stays >= 12 grey levels (gaps < 1.5 m)
Relief: NAIP leans elevated objects EAST by ~0.54 m per m of height (tools/stands/naip_relief.py); the outward heading
here is 117.8 deg, so an east shift moves the image 0.47 x shift to the LEFT of the outward axis and 0.88 x shift
outward. The deck is a few metres above the water (height not measured): positions are reported as imaged; geo.js
applies a +0.75 m lateral / -1.3 m along correction for an assumed 3 m deck height (inferred, +-1 m).
Output: refs/cache/als/als_naip.json and a printed table (no NAIP pixels in the repository).
Usage: python3 tools/imagery/als_naip.py
"""
import json, math, os, sys
import numpy as np
from scipy.signal import find_peaks
from scipy.ndimage import uniform_filter1d

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, os.path.join(ROOT, 'tools', 'stands'))
import geo_frame as GF  # noqa: E402
from common import Naip  # noqa: E402

FT = 0.3048; RES = 0.2; LEN_FT = 2550; HALF = 30.0
OPP = {'28L': '10R', '28R': '10L'}


def strip(N, end):
    a = np.array(GF.end_world(end)); b = np.array(GF.end_world(OPP[end])); d = (b - a) / np.linalg.norm(b - a)
    thr = a + d * GF.RWY_ENDS[end]['disp'] * FT; out = -d
    L = LEN_FT * FT; c = thr + out * L / 2
    hdg = math.degrees(math.atan2(out[0], -out[1])) % 360
    img, U, V = N.patch(c[0], c[1], hdg, L, 2 * HALF, RES)
    return img.astype(np.float32).mean(axis=2), U[:, 0] + L / 2, V[0], thr, hdg


def measure(N, end):
    lum, dist, lat, thr, hdg = strip(N, end)
    water = (dist > 700 * FT)
    bg = float(np.median(lum[water]))
    # seawall: last row (from the threshold outward) where the side band is still pavement-bright
    side = uniform_filter1d(lum[:, (lat < -8) & (lat > -25)].mean(axis=1), 11)
    # seawall: the outer edge of the white perimeter road at the end of the blast pad = the farthest row within
    # 500-800 ft whose band -10..+10 m is road-bright (> water + 30 grey levels); water begins there
    road = uniform_filter1d(lum[:, (lat > -10) & (lat < 10)].mean(axis=1), 3) > bg + 30
    cand = np.nonzero(road & (dist > 500 * FT) & (dist < 800 * FT))[0]
    sea = float(dist[cand].max()) if len(cand) else None
    # catwalk ridge
    prof = np.median(lum[(dist > 700 * FT) & (dist < 2400 * FT)], axis=0)
    j = np.argmax(np.where((lat > -5) & (lat < 6), prof, -1)); cw = float(lat[j])
    # stations
    band = (lat > -1.6) & (lat < 1.2)
    dk = uniform_filter1d(bg - lum[:, band].min(axis=1), 5)
    pk, _ = find_peaks(dk, height=25, distance=int(15 / RES))
    st = sorted(float(dist[k]) for k in pk if sea is None or dist[k] > sea)
    rows = []
    for s in st:
        i = int(np.argmin(np.abs(dist - s)))
        on = lum[max(0, i - 3):i + 4].min(axis=0)
        off = np.median(np.vstack([lum[max(0, i - 30):max(0, i - 15)], lum[i + 15:i + 30]]), axis=0)
        c = uniform_filter1d(off - on, 3)
        def ext(sign, start):
            k = int(np.argmin(np.abs(lat - start))); last = None; gap = 0.0
            while 0 <= k < len(lat):
                if c[k] >= 12: last = float(lat[k]); gap = 0.0
                else:
                    gap += RES
                    if gap > 1.5: break
                k += sign
            return last
        l_, r_ = ext(-1, -1.0), ext(1, cw + 1.6)
        # a crossbar is a dark bar on BOTH sides (>= 5 m each); one-sided hits are water texture / shadows
        xb = l_ is not None and r_ is not None and l_ <= -5 and r_ >= 5
        rows.append({'m': round(s, 1), 'ft': round(s / FT), 'crossbar': [round(l_, 1), round(r_, 1)] if xb else None})
    return {'end': end, 'thr': [round(v, 2) for v in thr], 'hdg_out': round(hdg, 2), 'water_bg': round(bg, 1),
            'seawall_m': round(sea, 1) if sea else None, 'catwalk_lat_img': round(cw, 2), 'stations': rows}


def main():
    N = Naip(); res = {}
    for end in ('28L', '28R'):
        r = measure(N, end); res[end] = r
        print(end, 'seawall %.1f m (%.0f ft), catwalk %.2f m right of the axis (imaged)' % (r['seawall_m'], r['seawall_m'] / FT, r['catwalk_lat_img']))
        for s in r['stations']:
            print('   %6.1f m %5d ft  %s' % (s['m'], s['ft'], 'crossbar %.1f .. %.1f m' % tuple(s['crossbar']) if s['crossbar'] else ''))
    os.makedirs(os.path.join(ROOT, 'refs', 'cache', 'als'), exist_ok=True)
    json.dump(res, open(os.path.join(ROOT, 'refs', 'cache', 'als', 'als_naip.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
