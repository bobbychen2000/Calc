"""Cross-check the parsed OSM features of KHWD (tools/osm/parse_osm.py -> refs/cache/osm/khwd_features.json) against the
FAA sources: NASR runway ends (tools/common/hwd_frame.py RWY_ENDS, cycle 2026-10-29) and the airport diagram AL-5015
(refs/cache/faa/05015ad_2611.pdf, cycle 2611).

New for hwd3d (no sfo3d counterpart; the runway part follows the idea of sfo3d/tools/xcheck/compare_runways.py @ a967f9b).

Checks
  1. Runways: each OSM runway way (ref a/b) against the NASR ends: end residual (dx east, dz south, along / across the
     NASR axis), max |across| of every node, OSM length vs NASR, bearing difference, tags (length / width / surface /
     ele) vs NASR. Done twice: OSM taken as WGS 84 (hwd_frame.wgs84_to_world, the frame's datum displacement applied)
     and, for comparison only, OSM taken as if it were NAD83 (ll_to_world, no displacement).
  2. Taxiway refs vs the AL-5015 list (A, A1, B, C, D, E, F, Z, Z1; PLAN.md section 1), per ref ways and length;
     taxiways tagged disused / abandoned.
  3. Hangar names, tower / FBO / fuel / fire station tagging (lists the matching records).
  4. AL-5015 'Closed Surface' marks: the TPP legend (d-TPP 2611 front matter, "LEGEND - AIRPORT DIAGRAM/AIRPORT
     SKETCH", legend 26302; refs/cache/faa/tpp_frntmatter_2611_p16.pdf) shows rows of x on grey pavement as "Closed
     Surface" (an outlined runway with x at its ends = "Closed Runway"); the FAA Chart Users' Guide (2026-07-09 edition,
     TPP - Terms, "Runway Construction"; refs/cache/faa/cug_20260709_p124.pdf) names the same symbol "Closed Pavement". The script finds the x glyphs on the
     diagram raster (small black X-shaped components standing on grey pavement), maps them into the world frame with an
     affine fit of the diagram to the 4 NASR runway ends (the bars of the runways are found on the raster), and lists the
     OSM ways near each row. The diagram is schematic: the TPP legend states "Positional accuracy within +-600 feet
     unless otherwise noted on the chart", and the fit residuals are printed - the match is topological, not a survey.
     Fix 2026-11-12 (Phase 1 cross-check, docs/phase1_crosscheck.md): the bar ends are now found by an axis walk
     (refine_bar_ends) instead of the extreme pieces of the opened bar mask. The HS 4 ring runs along the 10L/28R bar
     near 28R and cuts it into strips that the 9 x 9 px opening removes, so the old method stopped 92.6 px (76 m) short of
     the 28R end; the affine was sheared (scales 0.956 / 0.724 m/px, residuals 15-31 m). With the true end the 4 ends
     fit to < 1 m (the diagram's runways are drawn to scale).
Outputs: refs/cache/osm/khwd_osm_xcheck.json (numbers; ODbL-derived), out/phase1/g1/al5015_osm_overlay.png (+ crops;
working plots, gitignored).
Usage: python3 tools/osm/xcheck_osm_faa.py        (needs pdftoppm on PATH)
"""
import json, math, os, subprocess, sys
from collections import defaultdict

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as nd
from shapely.geometry import LineString, Point, Polygon

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'common'))
import hwd_frame as G                                               # noqa: E402

FEAT = os.path.join(ROOT, 'refs', 'cache', 'osm', 'khwd_features.json')
OUT = os.path.join(ROOT, 'refs', 'cache', 'osm', 'khwd_osm_xcheck.json')
PDF = os.path.join(ROOT, 'refs', 'cache', 'faa', '05015ad_2611.pdf')
FIG = os.path.join(ROOT, 'out', 'phase1', 'g1')
DPI = 400
FAA_TWYS = ['A', 'A1', 'B', 'C', 'D', 'E', 'F', 'Z', 'Z1']     # AL-5015 2611 taxiway labels (PLAN.md section 1)


def r(v, n=2): return None if v is None else round(float(v), n)


# ------------------------------------------------------------------------------------------------ 1. runways
def runway_check(F):
    out = []
    for rw in F['features'].get('runway', []):
        ref = rw.get('ref', '')
        a, b = (ref.split('/') + ['', ''])[:2]
        if a not in G.RWY_ENDS or b not in G.RWY_ENDS:
            out.append({'osm_id': rw['osm']['id'], 'ref': ref, 'error': 'ref not matched to NASR ends'}); continue
        ll = rw['ll']; res = {'osm_id': rw['osm']['id'], 'version': rw['osm']['version'], 'timestamp': rw['osm']['timestamp'],
                              'ref': ref, 'n_nodes': len(ll), 'tags': rw['tags']}
        for mode, fn in (('wgs84', G.wgs84_to_world), ('as_nad83_no_shift', G.ll_to_world)):
            W = [fn(p[0], p[1]) for p in ll]
            # orient the OSM way from end a to end b
            if math.dist(W[0], G.end_world(a)) > math.dist(W[-1], G.end_world(a)): W = W[::-1]
            ends = {}
            for nm, P in ((a, W[0]), (b, W[-1])):
                E = G.end_world(nm); al, ac = G.rwy_along_across(a, *P); al0, _ = G.rwy_along_across(a, *E)
                # along: positive = OSM end lies beyond the NASR end (runway longer), from the runway's own direction
                along = (al - al0) * (-1 if nm == a else 1)
                ends[nm] = {'dx_east': r(P[0] - E[0]), 'dz_south': r(P[1] - E[1]), 'dist': r(math.dist(P, E)),
                            'along_beyond_end': r(along), 'across_right_of_%s' % a: r(ac)}
                if G.RWY_ENDS[nm]['thrLat'] is not None:      # NASR displaced threshold of this end
                    alt, _ = G.rwy_along_across(a, *G.thr_world(nm))
                    ends[nm]['along_beyond_displaced_thr'] = r((al - alt) * (-1 if nm == a else 1))
            acr = [G.rwy_along_across(a, *P)[1] for P in W]
            L = sum(math.dist(W[i], W[i + 1]) for i in range(len(W) - 1))
            h = G.vec_hdg(W[-1][0] - W[0][0], W[-1][1] - W[0][1])
            ax = G.rwy_axis(a)
            res[mode] = {'ends': ends, 'across_max_abs': r(max(abs(v) for v in acr)), 'across_mean': r(np.mean(acr)),
                         'osm_len_m': r(L), 'nasr_len_m': r(ax['length']), 'len_diff_m': r(L - ax['length']),
                         'hdg_osm': r(h, 3), 'hdg_nasr': r(ax['hdg'], 3), 'hdg_diff_deg': r(((h - ax['hdg'] + 180) % 360) - 180, 3)}
        D = G.RWY_DATA['%s/%s' % (a, b)]
        res['tags_vs_nasr'] = {'length_tag_m': rw['tags'].get('length'), 'nasr_len_ft': D['lenFt'], 'nasr_len_m': r(D['lenFt'] * G.FT),
                               'width_tag_m': rw['tags'].get('width'), 'nasr_width_ft': D['widthFt'], 'nasr_width_m': r(D['widthFt'] * G.FT),
                               'surface_tag': rw['tags'].get('surface'), 'nasr_surface': D['surface'],
                               'ele_tag': rw['tags'].get('ele'),
                               'nasr_end_elev_ft': [G.RWY_ENDS[a]['elev'], G.RWY_ENDS[b]['elev']]}
        out.append(res)
    return out


# ------------------------------------------------------------------------------------------------ 2.-3. inventory
def holds(fs):
    """each OSM holding position: nearest runway (by distance to the end-to-end segment), offset from its NASR centreline
    (m, ft; > 0 right of the low-numbered end's direction) and station along it from that end"""
    out = []
    for h in fs.get('holding_position', []):
        x, z = h['w'][0]; best = None
        for a, b in G.RWY_PAIRS:
            al, ac = G.rwy_along_across(a, x, z); L = G.rwy_axis(a)['length']
            d = math.hypot(max(0.0, -al, al - L), ac)                 # distance to the runway segment (end to end)
            if best is None or d < best[3]: best = ('%s/%s' % (a, b), al, ac, d)
        out.append({'id': h['osm']['id'], 'ref': h.get('ref'), 'runway': best[0], 'along_m': r(best[1], 1),
                    'across_m': r(best[2], 1), 'across_ft': r(best[2] / G.FT, 0), 'dist_to_runway_m': r(best[3], 1)})
    return sorted(out, key=lambda o: (o['runway'], o['along_m']))


def inventory(F):
    fs = F['features']
    tw = fs.get('taxiway', [])
    by = defaultdict(lambda: {'ways': 0, 'len_m': 0.0, 'ids': []})
    for t in tw:
        k = t.get('ref') or '(no ref)'
        by[k]['ways'] += 1; by[k]['len_m'] += t.get('len_m', 0.0); by[k]['ids'].append(t['osm']['id'])
    refs = sorted(k for k in by if k != '(no ref)')
    inv = {'taxiway_refs_osm': refs, 'taxiway_refs_faa': FAA_TWYS,
           'faa_not_in_osm': [k for k in FAA_TWYS if k not in refs], 'osm_not_in_faa': [k for k in refs if k not in FAA_TWYS],
           'taxiway_by_ref': {k: {'ways': v['ways'], 'len_m': r(v['len_m'], 1), 'ids': v['ids']} for k, v in sorted(by.items())},
           'taxiway_status': {t['osm']['id']: t['status'] for t in tw if t.get('status') != 'open'},
           'taxilane_named': [{'id': t['osm']['id'], 'ref': t.get('ref'), 'name': t.get('name')} for t in fs.get('taxilane', []) if t.get('ref') or t.get('name')],
           'holding_position_refs': sorted({h.get('ref') or '(none)' for h in fs.get('holding_position', [])}),
           'holding_positions': holds(fs),
           'aprons': [{'id': a['osm']['id'], 'ref': a.get('ref'), 'name': a.get('name'), 'area_m2': a.get('area_m2')} for a in fs.get('apron', [])],
           'hangars': sorted([{'id': h['osm']['id'], 'name': h.get('name'), 'area_m2': h.get('area_m2'),
                               'addr': ' '.join(filter(None, [h['tags'].get('addr:housenumber'), h['tags'].get('addr:street')])) or None}
                              for h in fs.get('hangar', [])], key=lambda h: (h['name'] is None, str(h['name']))),
           'helipads': [{'id': h['osm']['id'], 'tags': h['tags'], 'area_m2': h.get('area_m2'), 'c_w': h['c_w']} for h in fs.get('helipad', [])]}
    def lst(kind):
        return [{'type': x['osm']['type'], 'id': x['osm']['id'], 'name': x.get('name'), 'tags': x['tags'], 'c_w': x['c_w'],
                 'in_aerodrome': x['in_aerodrome']} for x in fs.get(kind, [])]
    inv['control_tower'] = lst('control_tower'); inv['fuel'] = lst('fuel'); inv['fire_station'] = lst('fire_station')
    inv['windsock'] = lst('windsock'); inv['navaid'] = lst('navaid'); inv['mast_beacon'] = lst('mast_beacon')
    inv['lifecycle_aeroway'] = lst('lifecycle_aeroway')
    fbo_words = ('jet center', 'signature', 'meridian', 'fbo', 'aviation', 'aero', 'flight', 'air')
    named = []
    for k, L in fs.items():
        for x in L:
            n = (x.get('name') or '').lower()
            if any(w in n for w in fbo_words):
                named.append({'kind': k, 'type': x['osm']['type'], 'id': x['osm']['id'], 'name': x.get('name'),
                              'tags': {t: v for t, v in x['tags'].items() if not t.startswith('addr:')}})
    inv['aviation_named'] = named
    inv['buildings_by_type'] = dict(sorted(((t, sum(1 for b in fs.get('building', []) if b.get('type') == t))
                                            for t in {b.get('type') for b in fs.get('building', [])}), key=lambda kv: -kv[1]))
    inv['buildings_named'] = [{'id': b['osm']['id'], 'name': b.get('name'), 'type': b.get('type')} for b in fs.get('building', []) if b.get('name')]
    return inv


# ------------------------------------------------------------------------------------------------ 4. AL-5015 overlay
def raster():
    png = os.path.join(FIG, 'al5015_%d-1.png' % DPI)
    if not os.path.exists(png):
        os.makedirs(FIG, exist_ok=True)
        subprocess.run(['pdftoppm', '-r', str(DPI), '-png', PDF, os.path.join(FIG, 'al5015_%d' % DPI)], check=True)
    return png


def runway_bars(im):
    """the black runway bars: opening by a 9x9 square removes text and thin lines; the bars of a runway may be cut into
    pieces (hot-spot rings, hold marks): pieces are grouped by their direction and line offset"""
    blk = im.max(2) < 90
    op = nd.binary_opening(blk, structure=np.ones((9, 9), bool))
    lab, n = nd.label(op)
    sizes = nd.sum(op, lab, range(1, n + 1))
    pieces = []
    for i in np.argsort(-sizes):
        if sizes[i] < 5000: break
        ys, xs = np.nonzero(lab == i + 1)
        P = np.stack([xs, ys], 1).astype(float); m = P.mean(0)
        _, _, Vt = np.linalg.svd(P - m, full_matrices=False)
        pr = (P - m) @ Vt[0]; pc = (P - m) @ Vt[1]
        L = pr.max() - pr.min(); Wd = pc.max() - pc.min()
        if L < 4 * Wd: continue                                   # not a bar
        d = Vt[0] if Vt[0][1] > 0 else -Vt[0]                     # point down the page
        pieces.append({'m': m, 'd': d, 'a0': m + d * min(pr * np.sign(Vt[0] @ d)), 'a1': m + d * max(pr * np.sign(Vt[0] @ d)),
                       'len': L, 'wid': Wd})
    return pieces


def refine_bar_ends(im, bar):
    """true ends of a runway bar (fix 2026-11-12, see the header): walk along the bar axis from its middle; a
    cross-section is bar when >= 90 % of 21 samples across +-0.4 bar widths are black (max channel < 90) or hot-spot
    brown (the al5015.py colour test), so the overprinted hot-spot rings do not end the bar; gaps up to 16 px are
    bridged (the white dot near the 28L end is about 12 px across at 400 dpi). Text beyond the ends never fills 90 %."""
    blk = im.max(2) < 90
    brown = (im[..., 0] - im[..., 2] > 60) & (im[..., 0] > im[..., 1] + 25) & (im[..., 1] > im[..., 2] + 20)
    ink = blk | brown
    a, b = np.asarray(bar['top'], float), np.asarray(bar['bottom'], float)
    m = (a + b) / 2; d = (b - a) / np.hypot(*(b - a)); nr = np.array([-d[1], d[0]])
    ss = np.linspace(-0.4 * bar['wid'], 0.4 * bar['wid'], 21); ext = {}
    for sgn in (-1, 1):
        t = 0.0; last = 0.0
        while t - last <= 16.0:
            t += 0.5; c = m + sgn * d * t; Q = c[None] + ss[:, None] * nr[None]
            xi = np.round(Q[:, 0]).astype(int); yi = np.round(Q[:, 1]).astype(int)
            if xi.min() < 0 or yi.min() < 0 or xi.max() >= im.shape[1] or yi.max() >= im.shape[0]: break
            if ink[yi, xi].mean() >= 0.9: last = t
        ext[sgn] = m + sgn * d * last
    return ext[-1], ext[1]


def x_glyphs(im):
    """x marks of the 'Closed Surface' symbol: black components 14-45 px, pixels on the two diagonals, sparse, standing on
    grey pavement (letters of the labels stand on white)"""
    blk = im.max(2) < 110
    gray = (np.abs(im[..., 0] - im[..., 2]) < 12) & (im.mean(2) > 170) & (im.mean(2) < 235)
    lab, n = nd.label(blk)
    out = []
    for i, sl in enumerate(nd.find_objects(lab)):
        h = sl[0].stop - sl[0].start; w = sl[1].stop - sl[1].start
        if not (14 <= h <= 45 and 14 <= w <= 45): continue
        msk = lab[sl] == i + 1
        yy, xx = np.nonzero(msk); u = xx / w - yy / h; v = xx / w + yy / h - 1
        diag = np.mean((np.abs(u) < 0.2) | (np.abs(v) < 0.2)); fill = msk.mean()
        y0, y1, x0, x1 = sl[0].start - 6, sl[0].stop + 6, sl[1].start - 6, sl[1].stop + 6
        ring = gray[y0:y1, x0:x1].copy(); ring[6:-6, 6:-6] = False
        gshare = ring.sum() / max(1, (y1 - y0) * (x1 - x0) - h * w)
        if diag > 0.8 and fill < 0.4 and gshare > 0.25 and 0.5 < w / h < 2.0 and 18 <= max(w, h) <= 32:
            out.append(((sl[1].start + sl[1].stop) / 2, (sl[0].start + sl[0].stop) / 2))
    return out


def rows_of(pts, gap=110):
    """group x glyphs into rows (single-link, gap in px)"""
    pts = list(pts); rows = []
    while pts:
        row = [pts.pop(0)]; grew = True
        while grew:
            grew = False
            for p in pts[:]:
                if min(math.dist(p, q) for q in row) < gap: row.append(p); pts.remove(p); grew = True
        rows.append(sorted(row))
    return rows


def diagram_check(F, inv):
    im = np.asarray(Image.open(raster()).convert('RGB')).astype(int)
    pieces = runway_bars(im)
    # group pieces into runways: same direction (< 1 deg) and same line (offset < 15 px)
    groups = []
    for p in pieces:
        for g in groups:
            q = g[0]; nrm = np.array([-q['d'][1], q['d'][0]])
            if abs(np.degrees(np.arccos(min(1, abs(p['d'] @ q['d']))))) < 1.0 and abs((p['m'] - q['m']) @ nrm) < 15:
                g.append(p); break
        else:
            groups.append([p])
    groups.sort(key=lambda g: -sum(p['len'] for p in g))
    bars = []
    for g in groups[:2]:
        d = g[0]['d']; m = g[0]['m']
        ts = [(p['a0'] - m) @ d for p in g] + [(p['a1'] - m) @ d for p in g]
        bars.append({'top': m + d * min(ts), 'bottom': m + d * max(ts), 'len': max(ts) - min(ts), 'pieces': len(g),
                     'wid': float(np.mean([p['wid'] for p in g]))})
    # the long wide bar is 10R/28L, the other 10L/28R; on the page east is up (28 ends at the top)
    bars.sort(key=lambda b: -b['len'])
    old = {'28L': bars[0]['top'], '10R': bars[0]['bottom'], '28R': bars[1]['top'], '10L': bars[1]['bottom']}
    for b in bars:                                             # fix 2026-11-12: true ends (refine_bar_ends)
        b['top'], b['bottom'] = refine_bar_ends(im, b); b['len'] = float(np.hypot(*(b['bottom'] - b['top'])))
    px = {'28L': bars[0]['top'], '10R': bars[0]['bottom'], '28R': bars[1]['top'], '10L': bars[1]['bottom']}
    end_shift = {k: r(np.hypot(*(np.asarray(px[k]) - np.asarray(old[k]))), 1) for k in px}
    names = list(px)
    P = np.array([px[k] for k in names]); Q = np.array([G.end_world(k) for k in names])
    A = np.c_[P, np.ones(len(P))]; M, *_ = np.linalg.lstsq(A, Q, rcond=None)
    resid = np.hypot(*(Q - A @ M).T)
    Minv = np.linalg.inv(np.r_[M.T, [[0, 0, 1]]])
    to_px = lambda xz: (Minv @ np.r_[xz, 1])[:2]
    to_w = lambda p: np.r_[p, 1] @ M
    scale = math.sqrt(abs(np.linalg.det(M[:2])))
    # x glyph rows -> world
    xs = x_glyphs(im); allrows = rows_of(xs)
    rows = [rw for rw in allrows if len(rw) >= 3]           # the symbol is a row of x; single x-like glyphs are other marks
    singles = [rw[0] for rw in allrows if len(rw) < 3]
    fs = F['features']
    cand = [(k, x) for k in ('taxiway', 'taxilane', 'apron', 'service_road', 'lifecycle_aeroway') for x in fs.get(k, []) if x['geom'] in ('line', 'area')]
    rowres = []
    for row in rows:
        W = np.array([to_w(p) for p in row])
        line = LineString(W) if len(W) > 1 else Point(W[0])
        near = []
        for k, x in cand:
            g = LineString(x['w']) if x['geom'] == 'line' else Polygon(x['w'])
            d = g.distance(line)
            if d < 60:
                # how much of the x row runs along this feature: mean distance of the x marks to it
                md = float(np.mean([g.distance(Point(p)) for p in W]))
                near.append({'kind': k, 'id': x['osm']['id'], 'ref': x.get('ref'), 'name': x.get('name'),
                             'status': x.get('status'), 'tags': x['tags'], 'min_d_m': r(d, 1), 'mean_d_m': r(md, 1)})
        near.sort(key=lambda n: n['mean_d_m'])
        rowres.append({'n_x': len(row), 'px': [[r(a, 1), r(b, 1)] for a, b in row], 'w': np.round(W, 1).tolist(),
                       'len_m': r(line.length if len(W) > 1 else 0, 1), 'near_osm': near[:8]})
    draw_overlay(im, fs, to_px, rows, px)
    return {'raster_dpi': DPI, 'runway_bars_px': {k: [r(v[0], 1), r(v[1], 1)] for k, v in px.items()},
            'bar_end_method': 'refine_bar_ends (axis walk; fix 2026-11-12): ends moved from the extreme opened pieces by %s px' % end_shift,
            'bar_pieces': [b['pieces'] for b in bars], 'affine_px_to_world': np.round(M, 6).tolist(),
            'affine_singular_values_m_per_px': [r(v, 4) for v in np.linalg.svd(M[:2], compute_uv=False)],
            'scale_m_per_px': r(scale, 4), 'fit_resid_m': {k: r(v, 1) for k, v in zip(names, resid)},
            'x_glyphs': len(xs), 'x_like_single_glyphs_ignored_px': [[r(a, 1), r(b, 1)] for a, b in singles],
            'closed_surface_rows': rowres,
            'legend_source': 'FAA d-TPP 2611 front matter (https://aeronav.faa.gov/d-tpp/2611/frntmatter.pdf), p. 16 '
                             '"LEGEND - INSTRUMENT APPROACH PROCEDURES (CHARTS) - AIRPORT DIAGRAM/AIRPORT SKETCH" (26302): '
                             'symbol "Closed Surface" = grey pavement with rows of x; "Closed Runway" = runway bar with x; '
                             '"Positional accuracy within +-600 feet unless otherwise noted on the chart."'}


COL = {'A': (220, 30, 30), 'A1': (240, 120, 0), 'B': (30, 130, 30), 'C': (0, 90, 220), 'D': (160, 0, 200),
       'E': (0, 170, 170), 'F': (180, 140, 0), 'Z': (230, 0, 130), 'Z1': (120, 60, 0)}


def draw_overlay(im, fs, to_px, rows, px):
    base = Image.fromarray(im.astype(np.uint8)).convert('RGB')
    img = Image.blend(base, Image.new('RGB', base.size, (255, 255, 255)), 0.35)
    dr = ImageDraw.Draw(img)
    try: font = ImageFont.truetype('DejaVuSans-Bold.ttf', 26)
    except OSError: font = ImageFont.load_default()
    def poly(x): return [tuple(to_px(p)) for p in x['w']]
    for x in fs.get('apron', []): dr.line(poly(x), fill=(90, 90, 90), width=3)
    for x in fs.get('hangar', []): dr.line(poly(x), fill=(120, 80, 40), width=3)
    for x in fs.get('helipad', []): dr.line(poly(x), fill=(0, 150, 0), width=3)
    for x in fs.get('taxilane', []): dr.line(poly(x), fill=(140, 140, 255), width=3)
    for x in fs.get('service_road', []):
        if x.get('inside_frac', 0) > 0.5: dr.line(poly(x), fill=(255, 190, 0), width=2)
    for x in fs.get('runway', []): dr.line(poly(x), fill=(255, 255, 0), width=5)
    for x in fs.get('taxiway', []):
        c = COL.get(x.get('ref'), (60, 60, 60))
        if x.get('status') != 'open': c = (255, 0, 0)
        pts = poly(x); dr.line(pts, fill=c, width=7 if x.get('status') != 'open' else 5)
        if x.get('ref') and len(pts) >= 2:
            m = pts[len(pts) // 2]; dr.text((m[0] + 6, m[1] - 14), x['ref'], fill=c, font=font)
        if x.get('status') != 'open':
            m = pts[len(pts) // 2]; dr.text((m[0] + 6, m[1] + 8), '%s %d' % (x['status'], x['osm']['id']), fill=(255, 0, 0), font=font)
    for x in fs.get('lifecycle_aeroway', []):
        if x['geom'] != 'point': dr.line(poly(x), fill=(255, 0, 255), width=7)
    for x in fs.get('holding_position', []):
        p = to_px(x['w'][0]); dr.ellipse([p[0] - 7, p[1] - 7, p[0] + 7, p[1] + 7], outline=(255, 0, 0), width=3)
    for kind, col, lbl in (('control_tower', (0, 0, 200), 'OSM tower'), ('fire_station', (200, 0, 0), 'OSM fire stn'),
                           ('windsock', (0, 120, 0), 'OSM windsock'), ('fuel', (150, 0, 150), 'OSM fuel')):
        for x in fs.get(kind, []):
            p = to_px(x['c_w'])
            if not (0 <= p[0] < img.size[0] and 0 <= p[1] < img.size[1]): continue
            dr.ellipse([p[0] - 14, p[1] - 14, p[0] + 14, p[1] + 14], outline=col, width=5)
            dr.text((p[0] + 16, p[1] - 12), lbl, fill=col, font=font)
    for x in fs.get('fence', []): dr.line(poly(x), fill=(0, 0, 0), width=2)
    for x in fs.get('gate', []):
        p = to_px(x['c_w']); dr.rectangle([p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6], fill=(0, 0, 0))
    for row in rows:
        for p in row: dr.rectangle([p[0] - 18, p[1] - 18, p[0] + 18, p[1] + 18], outline=(0, 200, 255), width=3)
    for k, p in px.items(): dr.ellipse([p[0] - 12, p[1] - 12, p[0] + 12, p[1] + 12], outline=(0, 0, 255), width=4)
    dr.text((60, 60), 'AL-5015 (2611) + OSM %s (affine fit to NASR runway ends); red = taxiway tagged disused/abandoned; '
            'magenta = prefixed aeroway; cyan boxes = Closed Surface x marks' % 'khwd', fill=(0, 0, 0), font=font)
    out = os.path.join(FIG, 'al5015_osm_overlay.png'); img.save(out)
    for f in os.listdir(FIG):                                    # crops of an earlier run
        if f.startswith('al5015_osm_xrow'): os.remove(os.path.join(FIG, f))
    for i, row in enumerate(rows):
        a = np.array(row); x0, y0 = a.min(0) - 260; x1, y1 = a.max(0) + 260
        img.crop((int(max(0, x0)), int(max(0, y0)), int(x1), int(y1))).save(os.path.join(FIG, 'al5015_osm_xrow%d.png' % i))
    print('wrote', os.path.relpath(out, ROOT))


def main():
    F = json.load(open(FEAT))
    res = {'source': os.path.relpath(FEAT, ROOT), 'osm_base': F['osm_base'], 'source_sha256': F['source_sha256'],
           'licence': 'ODbL 1.0 (https://opendatacommons.org/licenses/odbl/1-0/) for the OSM-derived numbers; FAA sources public domain',
           'attribution': '(c) OpenStreetMap contributors - https://www.openstreetmap.org/copyright',
           'counts': F['counts'], 'outside_counts': F['outside_counts']}
    res['runways'] = runway_check(F)
    res['inventory'] = inventory(F)
    res['al5015'] = diagram_check(F, res['inventory'])
    json.dump(res, open(OUT, 'w'), indent=1)
    print('wrote', os.path.relpath(OUT, ROOT))
    for rw in res['runways']:
        print('runway', rw['ref'], 'osm way', rw['osm_id'])
        for mode in ('wgs84', 'as_nad83_no_shift'):
            m = rw[mode]
            print('  %-18s' % mode, {k: (v['dist'], v['along_beyond_end'], list(v.values())[4], v.get('along_beyond_displaced_thr')) for k, v in m['ends'].items()},
                  'across max', m['across_max_abs'], 'mean', m['across_mean'], 'len diff', m['len_diff_m'], 'hdg diff', m['hdg_diff_deg'])
        print('  tags', rw['tags_vs_nasr'])
    inv = res['inventory']
    print('taxiway refs OSM', inv['taxiway_refs_osm'], 'FAA not in OSM', inv['faa_not_in_osm'], 'OSM not in FAA', inv['osm_not_in_faa'])
    print('fit resid m', res['al5015']['fit_resid_m'], 'scale m/px', res['al5015']['scale_m_per_px'])
    for row in res['al5015']['closed_surface_rows']:
        print('x row', row['n_x'], 'len', row['len_m'], [(n['kind'], n['id'], n['ref'], n['status'], n['mean_d_m']) for n in row['near_osm'][:5]])


if __name__ == '__main__':
    main()
