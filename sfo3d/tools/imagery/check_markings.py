"""Check the airfield markings in data/sfo_details.json against the paint on USDA NAIP 2024 (public domain; 0.5 m world
raster, tools/imagery/paintline.py), independently of how they were built:

  centrelines  every 10 m: strongest yellow ridge within +-10 m across the line (averaged over 4 m along); reports the
               distribution of |offset| where a clear ridge exists (the review round 1 method).
  holds        the 7 ft yellow band across each hold bar, measured at +-0.2 and +-0.35 of its length from the centre, along
               the bar normal ('dir'), +-3.5 m (the red sign panels beside the bar are also 'yellowish'): offset of the band centre from the model bar.
  chevrons     blast-pad (10/28) and EMAS (1/19) chevron apexes on the runway axis beyond each end (yellow peaks on a 3 m
               wide strip): input for js/shaders/ground.js (blast pads, not owned here; docs/requests/static_geometry_round2.md)
               and js/live/airport.js END_ZONES chev0 (EMAS).
  independent  (static close-out 2026-11-04) the same lines against a CIE Lab b* ridge - NOT the builder's min(R, G) - B
               index, which also responds to white paint - plus geometry: taxiway edges on runway side stripes (28.4-31.6 m
               from a runway centreline), reversals > 150 deg with legs > 3 m, self-intersections (drawn centrelines only).
Exit status 1 if more than 5 % of the centreline samples are off by > 1.5 m, any hold bar is off by > 1.0 m, more than
50 m of edges lie on runway side stripes, or any edge / drawn centreline reverses or any edge self-intersects.
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
    # ---- static close-out (2026-11-04): an INDEPENDENT detector (CIE Lab b*, not the builder's min(R, G) - B index, which
    # also lights up white paint) and geometry checks the review found missing
    ind = independent(D)
    fail = (o > 1.5).mean() > 0.05 or bool(bad_h) or ind['fail']
    print('RESULT:', 'FAIL' if fail else 'OK')
    return fail


def _bstar_profile(IM, meta, p, t, half, avg=3.0, step=0.1):
    from scipy.ndimage import map_coordinates
    res, x0, z0 = meta['res'], meta['x0'], meta['z0']
    t = np.asarray(t, float) / np.linalg.norm(t); n = np.array([-t[1], t[0]])
    o = np.arange(-half, half + 1e-9, step); a = np.linspace(-avg / 2, avg / 2, 7)
    O, A = np.meshgrid(o, a); X = p[0] + O * n[0] + A * t[0]; Z = p[1] + O * n[1] + A * t[1]
    r = (Z - z0) / res - 0.5; c = (X - x0) / res - 0.5
    r0, c0 = int(np.floor(r.min())) - 1, int(np.floor(c.min())) - 1
    sub = np.asarray(IM[r0:int(np.ceil(r.max())) + 2, c0:int(np.ceil(c.max())) + 2], np.float32) / 255.0
    rgb = np.stack([map_coordinates(sub[..., k], [r - r0, c - c0], order=1, mode='nearest') for k in (2, 1, 0)], -1)
    v = np.where(rgb > 0.04045, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)
    xyz = v @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return o, (200 * (f[..., 1] - f[..., 2])).mean(0), (116 * f[..., 1] - 16).mean(0)


def independent(D):
    """(1) b* ridge (CIE Lab, sRGB D65) within +-half of the line every 10 m: |offset| where the ridge rises >= 4 over the
    local median; (2) taxiway edges on a runway: length within 28.4-31.6 m of a runway centreline inside its length
    (the white side stripe); (3) vertices turning > 150 deg with both legs > 3 m; (4) self-intersecting polylines"""
    from shapely.geometry import LineString
    meta = json.load(open(os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_world_0.5m.json')))
    IM = np.load(os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_world_0.5m_bgr.npy'), mmap_mode='r')
    RW = []
    for a_, b_ in GF.RWY_PAIRS:
        pa = np.array(GF.end_world(a_)); pb = np.array(GF.end_world(b_)); L = np.linalg.norm(pb - pa); RW.append((pa, (pb - pa) / L, L))
    def rw_side(p):
        for pa, d, L in RW:
            v = p - pa; al = v @ d; cr = abs(-v[0] * d[1] + v[1] * d[0])
            if 0 < al < L and 28.4 <= cr <= 31.6: return True
        return False
    out = {}
    meta_cl = D.get('centerlineMeta') or []
    for name, lines, half, drawn in (('centrelines', D['centerlines'], 6.0, [m.get('drawn', True) for m in meta_cl] or None), ('edges', D.get('edges', []), 3.5, None)):
        offs, n_s, side_m, rev, selfx = [], 0, 0.0, 0, 0
        for k, pl in enumerate(lines):
            if drawn is not None and k < len(drawn) and not drawn[k]: continue
            P = np.array(pl, float)
            for i in range(1, len(P) - 1):
                u, v = P[i] - P[i - 1], P[i + 1] - P[i]; lu, lv = np.linalg.norm(u), np.linalg.norm(v)
                if lu > 3 and lv > 3 and math.degrees(math.acos(max(-1, min(1, u @ v / (lu * lv))))) > 150: rev += 1
            if len(P) >= 3 and not LineString(P).is_simple: selfx += 1
            for i in range(len(P) - 1):
                a, b = P[i], P[i + 1]; L = np.linalg.norm(b - a)
                if L < 1: continue
                t = (b - a) / L
                for s_ in np.arange(1.0, L, 2.0):
                    if rw_side(a + t * s_): side_m += 2.0
                for s_ in np.arange(5, L, 10):
                    n_s += 1; o_, bs, _ = _bstar_profile(IM, meta, a + t * s_, t, half)
                    k_ = int(np.argmax(bs))
                    if bs[k_] - np.median(bs) >= 4: offs.append(abs(o_[k_]))
        o = np.array(offs) if offs else np.zeros(1)
        out[name] = {'samples': n_s, 'ridges': len(offs), 'median': round(float(np.median(o)), 2), 'gt1.5_pct': round(100 * float((o > 1.5).mean()), 1),
                     'gt3_pct': round(100 * float((o > 3).mean()), 1), 'on_runway_side_stripe_m': round(side_m), 'reversals_gt150': rev, 'self_intersecting': selfx}
        print('independent (Lab b*) %s: %s' % (name, out[name]))
    out['fail'] = out['edges']['on_runway_side_stripe_m'] > 50 or out['edges']['reversals_gt150'] > 0 or out['edges']['self_intersecting'] > 0 \
        or out['centrelines']['reversals_gt150'] > 0
    return out


if __name__ == '__main__':
    sys.exit(1 if main() else 0)
