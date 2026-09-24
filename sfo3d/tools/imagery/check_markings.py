"""Check the airfield markings in data/sfo_details.json against the paint on USDA NAIP 2024 (public domain; 0.5 m world
raster, tools/imagery/paintline.py), independently of how they were built:

  centrelines  every 10 m: strongest yellow ridge within +-10 m across the line (averaged over 4 m along); reports the
               distribution of |offset| where a clear ridge exists (the review round 1 method).
  holds        the 7 ft yellow band across each hold bar, measured at +-0.2 and +-0.35 of its length from the centre, along
               the bar normal ('dir'), +-3.5 m (the red sign panels beside the bar are also 'yellowish'): offset of the band centre from the model bar.
  chevrons     blast-pad (10/28) and EMAS (1/19) chevron apexes on the runway axis beyond each end (yellow peaks on a 3 m
               wide strip): input for js/shaders/ground.js (blast pads, not owned here; docs/requests/static_geometry_round2.md)
               and js/live/airport.js END_ZONES chev0 (EMAS).
Exit status 1 if more than 5 % of the centreline samples are off by > 1.5 m or any hold bar is off by > 1.0 m.
Usage: python3 tools/imagery/check_markings.py
"""
import json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, 'tools'))
from paintline import Yellow, along_profile, _box, BAR_DEPTH
import geo_frame as GF


def main():
    Y = Yellow(); D = json.load(open(os.path.join(ROOT, 'data', 'sfo_details.json')))
    offs = []; n = 0
    for pl in D['centerlines']:
        P = np.array(pl)
        for i in range(len(P) - 1):
            a, b = P[i], P[i + 1]; L = np.linalg.norm(b - a)
            if L < 1: continue
            t = (b - a) / L
            for s in np.arange(5, L, 10):
                n += 1; r = Y.cross_peak(a + t * s, t, half=10, avg=4)
                if r and r[1] > 12 and r[2] < 0.6 * r[1]: offs.append(abs(r[0]))
    o = np.array(offs)
    print('centrelines: %d samples, %d with a clear ridge: |offset| median %.2f m, > 1.5 m %.1f %%, > 3 m %.1f %%, > 5 m %.1f %%' % (
        n, len(o), np.median(o), 100 * (o > 1.5).mean(), 100 * (o > 3).mean(), 100 * (o > 5).mean()))
    bad_h = []; hres = []
    for i, h in enumerate(D['holds']):
        u = np.array(h['dir']); bar = np.array([-u[1], u[0]]); a, b = np.array(h['a']), np.array(h['b']); c = (a + b) / 2
        ho = []
        for f in (-0.35, -0.2, 0.2, 0.35):          # not at the centre: the taxiway centreline crosses there
            q = c + (b - a) * f; sg = np.arange(-3.5, 3.51, 0.1)
            v = along_profile(Y, q[None] + u[None] * sg[:, None], np.repeat(bar[None], len(sg), 0), np.array([-0.5, 0.0, 0.5]))
            fb = _box(v, int(round(BAR_DEPTH / 0.1))); k = int(np.argmax(fb))
            if fb[k] - np.percentile(fb, 20) > 8 and 3 < k < len(sg) - 4: ho.append(sg[k])
        if ho:
            m = float(np.median(ho)); hres.append(abs(m))
            if abs(m) > 1.0: bad_h.append((i, h['twy'], h['text'], round(m, 2)))
    hr = np.array(hres)
    print('holds: %d, measured %d: |offset| median %.2f m, max %.2f m; > 1.0 m: %s' % (len(D['holds']), len(hr), np.median(hr), hr.max(), bad_h or 'none'))
    # blast-pad chevrons
    for a_, b_ in (('10L', '28R'), ('10R', '28L'), ('28R', '10L'), ('28L', '10R'), ('1L', '19R'), ('19R', '1L'), ('1R', '19L'), ('19L', '1R')):
        pa = np.array(GF.end_world(a_)); pb = np.array(GF.end_world(b_)); d = (pa - pb) / np.linalg.norm(pa - pb)
        s = np.arange(2, 280, 0.1); P = pa[None] + d[None] * s[:, None]
        v = along_profile(Y, P, np.repeat(d[None], len(s), 0), np.array([-1.0, -0.5, 0.0, 0.5, 1.0]))
        f = _box(v, 5); pk = []
        for k in range(10, len(f) - 10):
            if f[k] == f[k - 10:k + 11].max() and f[k] - np.median(f) > 15: pk.append(round(float(s[k]), 1))
        pk = [p for j, p in enumerate(pk) if j == 0 or p - pk[j - 1] > 5]
        print(('EMAS ' if a_[0] in '1' and len(a_) <= 3 and a_[:2] in ('1L', '1R', '19') else 'blast pad ') + 'chevron apexes beyond %s (m from the end): %s; spacing %s' % (a_, pk[:9], [round(pk[j + 1] - pk[j], 1) for j in range(min(8, len(pk) - 1))]))
    fail = (o > 1.5).mean() > 0.05 or bool(bad_h)
    print('RESULT:', 'FAIL' if fail else 'OK')
    return fail


if __name__ == '__main__':
    sys.exit(1 if main() else 0)
