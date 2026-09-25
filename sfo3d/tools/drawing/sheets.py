"""Drawing sheets (SVG + PNG) of what the 3-D app places on the ground, drawn from the extracted scene
(out/draw/scene2d.json - the same parameters/geometry the 3-D uses), with title block, scale bar, north arrow, legend,
world (x/z) and airport-grid (s/t) grids, colour-coded layers, measured deviation call-outs (measure.py) and
clearance-audit conflict markers (audit.py).

Variants per sheet
  vector          no imagery - committable, written to docs/drawings/<id>.svg|png
  overlay-google  over the owner's Google screenshots - REFERENCE ONLY, written to out/draw/sheets/ (gitignored)
  overlay-naip    over NAIP (public domain) when refs/cache/naip/ holds imagery - out/draw/sheets/
Drawings are north-up (true north); plot coordinates are (x, -z).
Deviation dots / call-outs come from NAIP (public, independently georeferenced) on the vector and NAIP sheets, and from
the Google screenshots (re-registered to NAIP by imreg.py when available) on the Google overlays.
Title blocks carry the provenance: world frame id, git commit (+dirty), whether the scene is stale against the working
tree, and the imagery files (sha) and frames.
"""
import json, math, os, sys, time, collections, datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.patches import PathPatch, Rectangle, Polygon as MPoly, FancyArrow, Circle
from matplotlib.path import Path
import shapely
from shapely.geometry import Polygon, LineString, MultiPolygon, Point, box as sbox
from shapely.ops import unary_union
from shapely import affinity
from common import scene, OUT, DOCS, buildings, poly_rings, hull_poly, w2st, st2w, G, polys_of, mask_to_polys, ROOT, provenance
import background

PAPER = {'A3': (420, 297), 'A2': (594, 420), 'A1': (841, 594), 'A0': (1189, 841)}
SCALES = [500, 750, 1000, 1250, 1500, 2000, 2500, 3000, 4000, 5000, 7500, 10000, 12500, 15000, 20000, 25000]
BORDER = 10; STRIP = 78  # mm: frame border, right-hand strip (legend, title block)
DPI = 150
FONT = 'DejaVu Sans'
plt.rcParams.update({'font.family': FONT, 'svg.fonttype': 'none', 'path.simplify': True})

C = dict(pave='#e4e4e0', paveEdge='#7a8aa0', twy='#9a9a9a', rwy='#bdbdbd', rwyEdge='#555555', paint='#6fb36f', bldg='#8d949c', bldgEdge='#222222',
         walk='#b5bcc4', yellow='#d9a400', red='#c62828', white='#ffffff', stand='#006d77', env='#00a6b8', bridge='#6a1b9a', bridgeRest='#9c27b0',
         dock='#e91e63', gse='#ef6c00', ac='#1565c0', mast='#000000', sign='#c62828', vdgs='#37474f', blast='#f2c200', emas='#f7d774',
         gridW='#b0b0b0', gridST='#7fb3d5', dev0='#1a9850', dev1='#f4a300', dev2='#d73027', devNA='#bdbdbd', conflict='#d50000', pier='#4e342e', obstr='#aa00ff')


def P(g):
    """world (x, z) geometry -> plot (x, -z)"""
    return affinity.scale(g, 1, -1, origin=(0, 0))


def poly_path(g):
    verts, codes = [], []
    for p in polys_of(g):
        for ring in [p.exterior] + list(p.interiors):
            c = np.asarray(ring.coords)
            if len(c) < 3: continue
            verts.append(c); codes += [Path.MOVETO] + [Path.LINETO] * (len(c) - 2) + [Path.CLOSEPOLY]
    if not verts: return None
    return Path(np.concatenate(verts), codes)


def add_poly(ax, g, fc='none', ec='k', lw=0.4, alpha=1.0, z=1, ls='-', hatch=None, **kw):
    p = poly_path(g)
    if p is None: return
    ax.add_patch(PathPatch(p, fc=fc, ec=ec, lw=lw, alpha=alpha, zorder=z, ls=ls, hatch=hatch, **kw))


def add_lines(ax, lines, color, lw, z=2, ls='-', alpha=1.0):
    segs = [np.asarray(l) for l in lines if len(l) >= 2]
    if segs: ax.add_collection(LineCollection(segs, colors=color, linewidths=lw, zorder=z, linestyles=ls, alpha=alpha, capstyle='butt'))


# ------------------------------------------------------------------------------------------------ layers (plot coords)
class Layers:
    def __init__(self):
        S = scene(); self.S = S; g = G(); t0 = time.time()
        # paved raster the app uses (physics + ground shading), vectorised in the s/t grid then mapped to world
        import cv2
        r = S['rasters']['pave_1.00']; A = S['meta']['aptRect']; im = cv2.imread(os.path.join(OUT, r['file']))
        pave_st = mask_to_polys(im[:, :, 2] > 127, r['res'], 0, 0, simplify=0.6)
        # raster pixel (i=col, j=row) -> s = s0 + (i+.5) res, t = t0 + h - (j+.5) res ; mask_to_polys gave (col*res, row*res)
        V, U = np.array(S['meta']['stBasis']['V']), np.array(S['meta']['stBasis']['U'])
        def st_to_plot(geom):
            # (a, b) = (col*res, row*res) -> s = s0 + a, t = t0 + h - b -> e = s V0 + t U0 ; n = s V1 + t U1 ; plot = (e, n)
            s0, tt = A['s0'], A['t0'] + A['h']
            M = [V[0], -U[0], V[1], -U[1], s0 * V[0] + tt * U[0], s0 * V[1] + tt * U[1]]
            return affinity.affine_transform(geom, M)
        self.pave = st_to_plot(pave_st)
        self.twy = P(unary_union([poly_rings(p) for t in S['pave']['taxiways'] for p in t['polys']]))
        self.paint = P(unary_union([poly_rings(p) for p in S['pave']['paint']]))
        self.extra = P(unary_union([poly_rings(p) for p in S['pave']['extra']]))
        # runways
        self.rwy = []
        for rw in S['runways']:
            c = rw['corners']; body = P(Polygon(c)); d = np.array(rw['dir']); nrm = np.array([-d[1], d[0]])
            c0, c1 = np.array(rw['centre'][0]), np.array(rw['centre'][1]); L = np.linalg.norm(c1 - c0); pt = rw['paint']
            def R(u0, u1, v0, v1):  # rectangle in runway (along from end A, lateral) coords -> plot polygon
                q = [c0 + d * u0 + nrm * v0, c0 + d * u1 + nrm * v0, c0 + d * u1 + nrm * v1, c0 + d * u0 + nrm * v1]
                return P(Polygon(q))
            stripes = []
            for sg in (-1, 1): stripes.append(R(0, L, sg * pt['edgeStripe'][0], sg * pt['edgeStripe'][1]))
            for ei, e in enumerate(rw['ends']):
                disp = e['disp']; ts = pt['thrStripes']
                for k in range(ts['n']):
                    for sg in (-1, 1):
                        y0 = sg * (ts['lat0'] + ts['pitch'] * k); y1 = sg * (ts['lat0'] + ts['pitch'] * k + ts['width'])
                        u0, u1 = disp + ts['x0'], disp + ts['x1']
                        stripes.append(R(u0, u1, y0, y1) if ei == 0 else R(L - u1, L - u0, -y1, -y0))
                if disp > 1:
                    b0, b1 = disp + pt['dispBar'][0], disp + pt['dispBar'][1]
                    stripes.append(R(b0, b1, -30, 30) if ei == 0 else R(L - b1, L - b0, -30, 30))
                a0, a1 = disp + pt['aiming']['x0'], disp + pt['aiming']['x1']
                for sg in (-1, 1):
                    y0, y1 = sorted((sg * pt['aiming']['y0'], sg * pt['aiming']['y1']))
                    stripes.append(R(a0, a1, y0, y1) if ei == 0 else R(L - a1, L - a0, y0, y1))
            cl = pt['centreline']; u = rw['ends'][0]['disp'] + cl['start']
            while u + cl['dash'] < L - rw['ends'][1]['disp'] - cl['start']:
                stripes.append(R(u, u + cl['dash'], -cl['hw'], cl['hw'])); u += cl['period']
            thr = [P(LineString([np.array(e['thr']) + nrm * 30.48, np.array(e['thr']) - nrm * 30.48])) for e in rw['ends']]
            self.rwy.append(dict(name=rw['name'], body=body, stripes=unary_union(stripes), shoulder=P(Polygon(rw['shoulderPaved']['poly'])), thr=thr, ends=rw['ends'], dir=d))
        self.rwyPolys = P(unary_union([poly_rings(p) for r in S['pave']['runwayPolys'] for p in r['polys']]))
        self.endZones = [dict(kind=z['kind'], end=z['end'], poly=P(Polygon(z['rectW']))) for z in S['endZones']]
        self.emas = [P(hull_poly(b['hull'])) for b in S['emasBeds']]
        # markings
        M = collections.defaultdict(list)
        for rb in S['markings']['ribbons']:
            pts = np.asarray(rb['pts'], float)
            if len(pts) < 2: continue
            if abs(rb['offset']) > 1e-6:
                d = np.gradient(pts, axis=0); d /= np.maximum(np.linalg.norm(d, axis=1), 1e-9)[:, None]; pts = pts + np.c_[-d[:, 1], d[:, 0]] * rb['offset']
            M[rb['kind']].append(np.c_[pts[:, 0], -pts[:, 1]])
        self.marks = M
        # buildings
        self.bldg = []
        for b in buildings():
            if b.get('notBuilt'): continue
            p = poly_rings(b['rings'])
            if p.is_empty: continue
            self.bldg.append(dict(kind=b['kind'], name=b['name'], h=b['y1'] - g, y0=b['y0'] - g, poly=P(p)))
        self.itbRoof = P(hull_poly(S['itbRoof']['hull'])) if S.get('itbRoof') else None
        self.tower = [P(hull_poly(p['hull'])) for p in S['tower']['prims']] if S.get('tower') else []
        self.masts = S['masts']; self.signs = []
        for s in S['signs']:
            c = np.array(s['c']); u = np.array(s['u']); n = np.array([-u[1], u[0]]); hw, hd = s['w'] / 2, s['d'] / 2
            self.signs.append(P(Polygon([c - u * hw - n * hd, c + u * hw - n * hd, c + u * hw + n * hd, c - u * hw + n * hd])))
        # approach-light structures / posts (recorded boxes), light sprites, PAPI units
        self.piers = []
        for pr in S.get('piers') or []:
            ps = [P(hull_poly(p['hull'])) for p in pr['prims'] if len(p['hull']) >= 3]
            if ps: self.piers.append(dict(pr=pr, poly=unary_union(ps), pt=(pr['base'][0], -pr['base'][1])))
        LT = S.get('lights') or {}
        self.lights = np.array([[q[0], -q[2]] for q in LT.get('points', [])]) if LT.get('points') else np.zeros((0, 2))
        self.lightCol = [q[3] for q in LT.get('points', [])]
        self.papis = [(q['p'][0], -q['p'][2]) for q in LT.get('papis', [])]
        # stands, bridges, gse, aircraft
        self.stands = S['stands']; self.bridges = S['bridges']
        self.gse = [(v['kind'], P(hull_poly(v['hull']))) for v in S['gse'] if len(v['hull']) >= 3]
        from common import ac_instance_geom, plan_world
        self.ac = []
        for a in S['aircraft']:
            if not a['valid'] or not a['ground']: continue
            geom, W = ac_instance_geom(a)
            if geom is None: self.ac.append(dict(a=a, poly=None, pt=(a['pos'][0], -a['pos'][2]))); continue
            self.ac.append(dict(a=a, poly=P(plan_world(geom, W)), pt=(a['pos'][0], -a['pos'][2])))
        # class envelopes (from the audit) and deviation samples / conflicts
        self.env = {}
        af = os.path.join(OUT, 'audit.json')
        self.audit = json.load(open(af)) if os.path.exists(af) else None
        if self.audit and self.audit.get('envelopes'):
            for n, gj in self.audit['envelopes'].items(): self.env[n] = P(shapely.from_geojson(gj))
        self.dev = {}; self.devSummary = {}
        dj = os.path.join(OUT, 'deviations.json')
        if os.path.exists(dj):
            D = json.load(open(dj))
            for src, R in D.items():
                self.devSummary[src] = {f['id']: f for f in R['features']}
                sf = os.path.join(OUT, f'dev_samples_{src}.json')
                if os.path.exists(sf): self.dev[src] = json.load(open(sf))['samples']
        self.prov = provenance(S); self.imgprov = {'vector': 'none on this sheet; deviation dots from NAIP' if 'naip' in self.dev else 'none'}
        dvj = os.path.join(OUT, 'deviations.json')
        if os.path.exists(dvj):
            for src, R in json.load(open(dvj)).items():
                pv = R.get('provenance') or {}
                if src == 'naip': self.imgprov['overlay-naip'] = '; '.join(f'{p.get("file", "?").split("/")[-1]} sha {p.get("sha")} ({p.get("frame")})' for p in pv.get('parts', []))
                if src == 'google': self.imgprov['overlay-google'] = f'{pv.get("images")} screenshots, reg.json sha {pv.get("reg_sha")} ({",".join(pv.get("reg_frames", []))} -> {pv.get("frame")}); NAIP residual {pv.get("naip_correction", "?")}'
        print(f'  layers ready ({time.time() - t0:.0f} s)')


# ------------------------------------------------------------------------------------------------ sheet definitions
def sheet_defs(L):
    S = L.S; out = []
    allb = unary_union([b['poly'] for b in L.bldg] + [r['body'] for r in L.rwy])
    x0, y0, x1, y1 = allb.bounds
    out.append(dict(id='00-overview', title='Overview - SFO as built by the 3-D app', box=(x0 - 150, y0 - 150, x1 + 150, y1 + 150), paper='A1', detail=0))
    # boarding areas: pier + its stands' envelopes and bridges
    for letter in 'ABCDEFG':
        geo = [b['poly'] for b in L.bldg if b['name'] == f'Boarding Area {letter}']
        for st in L.stands:
            if st['letter'] != letter: continue
            geo.append(Point(st['nose'][0], -st['nose'][1]).buffer(8))
            if st['name'] in L.env: geo.append(L.env[st['name']])
        if not geo: continue
        b = unary_union(geo).bounds
        out.append(dict(id=f'10-ba-{letter}', title=f'Boarding Area {letter} - stands, jet bridges, markings', box=(b[0] - 15, b[1] - 15, b[2] + 15, b[3] + 15), scale=1500, detail=2))
    itb = [b['poly'] for b in L.bldg if 'International' in b['name'] and b['kind'] == 'hall'] + [p for p in L.tower]
    b = unary_union(itb).bounds
    out.append(dict(id='20-itb-tower', title='International Terminal (ITB) and control tower', box=(b[0] - 60, b[1] - 60, b[2] + 60, b[3] + 60), scale=1500, detail=2))
    for rw in L.rwy:
        for e in rw['ends']:
            end = np.array(e['end']); inw = np.array(e['inward']); lat = np.array([-inw[1], inw[0]])
            # outward: the end zone and the approach-light piers of this end (up to 900 m), at least 220 m
            outw = [220.0] + [float(-(np.array([p['pt'][0], -p['pt'][1]]) - end) @ inw) + 40 for p in L.piers if p['pr'].get('end') == e['name']]
            outw += [float(max(-(np.array([c[0], -c[1]]) - end) @ inw for c in np.asarray(z['poly'].exterior.coords))) + 40 for z in L.endZones if z['end'] == e['name']]
            ob = min(900.0, max(outw))
            q = [end - inw * ob + lat * 170, end - inw * ob - lat * 170, end + inw * (e['disp'] + 380) + lat * 170, end + inw * (e['disp'] + 380) - lat * 170]
            q = np.array(q); bx = (q[:, 0].min(), -q[:, 1].max(), q[:, 0].max(), -q[:, 1].min())
            out.append(dict(id=f'30-rwy-{e["name"]}', title=f'Runway {e["name"]} end - threshold, markings, end zone', box=bx, scale=2000, detail=1))
    # cargo / maintenance / remote: clusters of the extra paved areas away from the terminal and runways
    ex = [p for p in polys_of(L.extra) if p.area > 15000]
    cl = []
    for p in sorted(ex, key=lambda p: -p.area):
        for c in cl:
            if c['g'].distance(p) < 120: c['g'] = unary_union([c['g'], p]); break
        else: cl.append(dict(g=p))
    term = unary_union([b['poly'] for b in L.bldg if b['kind'] in ('pier', 'hall', 'apron-level')]).buffer(150)
    k = 0
    for c in sorted(cl, key=lambda c: -c['g'].area)[:4]:
        g = c['g']
        if g.difference(term).area < 0.5 * g.area: continue
        b = g.bounds; cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        name = ('north' if cy > 400 else 'south' if cy < -600 else 'central') + '-' + ('west' if cx < -900 else 'east' if cx > 300 else 'middle')
        k += 1
        out.append(dict(id=f'40-apron-{k}-{name}', title=f'Cargo / maintenance / remote apron ({name.replace("-", " ")})', box=(b[0] - 40, b[1] - 40, b[2] + 40, b[3] + 40), scale=2000, detail=1))
    return out


def fit_sheet(sd):
    x0, y0, x1, y1 = sd['box']; w, h = x1 - x0, y1 - y0
    papers = [sd['paper']] if sd.get('paper') else ['A3', 'A2', 'A1']
    want = sd.get('scale')
    for sc in ([want] + [s for s in SCALES if s > want] if want else SCALES):
        for pp in papers:
            pw, ph = PAPER[pp]; vw, vh = pw - 2 * BORDER - STRIP, ph - 2 * BORDER
            if w * 1000 / sc <= vw and h * 1000 / sc <= vh:
                # expand the box to the full viewport at this scale
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; W, H = vw * sc / 1000, vh * sc / 1000
                return dict(paper=pp, scale=sc, box=(cx - W / 2, cy - H / 2, cx + W / 2, cy + H / 2))
    raise ValueError('sheet too large: ' + sd['id'])


# ------------------------------------------------------------------------------------------------ drawing
def nice_step(span_m):
    for s in (10, 20, 25, 50, 100, 200, 250, 500, 1000):
        if span_m / s <= 12: return s
    return 2000


def draw_grid(ax, box, sc):
    x0, y0, x1, y1 = box; step = nice_step(max(x1 - x0, y1 - y0))
    fs = 4.5
    for x in np.arange(math.ceil(x0 / step) * step, x1, step):
        ax.plot([x, x], [y0, y1], color=C['gridW'], lw=0.25, zorder=0.5)
        ax.text(x, y1, f'x {x:.0f}', fontsize=fs, color='#606060', ha='center', va='bottom', zorder=20, clip_on=False)
        ax.text(x, y0, f'x {x:.0f}', fontsize=fs, color='#606060', ha='center', va='top', zorder=20, clip_on=False)
    for y in np.arange(math.ceil(y0 / step) * step, y1, step):
        ax.plot([x0, x1], [y, y], color=C['gridW'], lw=0.25, zorder=0.5)
        ax.text(x0, y, f'z {-y:.0f}', fontsize=fs, color='#606060', ha='right', va='center', zorder=20, clip_on=False, rotation=90)
    # airport grid s/t (dashed blue), labelled where the lines leave the frame
    cs = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]); s, t = w2st(cs[:, 0], -cs[:, 1])
    fr = sbox(x0, y0, x1, y1)
    for kind, lo, hi in (('s', s.min(), s.max()), ('t', t.min(), t.max())):
        for v in np.arange(math.ceil(lo / step) * step, hi, step):
            if kind == 's': a = st2w(np.array([v, v]), np.array([t.min() - 10, t.max() + 10]))
            else: a = st2w(np.array([s.min() - 10, s.max() + 10]), np.array([v, v]))
            ln = LineString([(a[0][0], -a[1][0]), (a[0][1], -a[1][1])]).intersection(fr)
            if ln.is_empty: continue
            c = np.asarray(ln.coords); ax.plot(c[:, 0], c[:, 1], color=C['gridST'], lw=0.3, ls=(0, (4, 3)), zorder=0.6)
            e = c[np.argmax(c[:, 1])] if kind == 's' else c[np.argmin(c[:, 0])]
            ax.text(e[0], e[1], f' {kind} {v:.0f}', fontsize=fs, color='#2e86c1', ha='left', va='top', zorder=20, rotation=0)


def draw_layers(ax, L, box, sc, variant, detail, highlight=None):
    fr = sbox(*box).buffer(5); tol = sc / 1000 * 0.1  # 0.1 mm on paper
    clip = lambda g: g.intersection(fr).simplify(tol) if g is not None and not g.is_empty and g.intersects(fr) else None
    lwk = max(0.4, 1500 / sc)  # line weight factor (thicker at larger scale)
    over = variant != 'vector'
    # pavement (app raster) + taxiway source polygons + extra pavement
    g = clip(L.pave)
    if g is not None:
        if over: add_poly(ax, g, fc='none', ec=C['paveEdge'], lw=0.35, z=1, ls=(0, (3, 2)))
        else: add_poly(ax, g, fc=C['pave'], ec='#b0b0a8', lw=0.2, z=1)
    g = clip(L.twy)
    if g is not None: add_poly(ax, g, fc='none' if over else '#d6d6d2', ec=C['twy'], lw=0.25, z=1.2)
    g = clip(L.paint)
    if g is not None: add_poly(ax, g, fc=C['paint'], ec='#2e7d32', lw=0.2, alpha=0.35 if over else 0.8, z=1.4)
    for rw in L.rwy:
        g = clip(rw['shoulder'])
        if g is not None and not over: add_poly(ax, g, fc='#cfcfcb', ec='none', z=1.5)
        g = clip(rw['body'])
        if g is None: continue
        add_poly(ax, g, fc='none' if over else C['rwy'], ec=C['rwyEdge'], lw=0.4, z=1.6)
        st = clip(rw['stripes'])
        if st is not None: add_poly(ax, st, fc='#ffffff' if not over else 'none', ec='#909090' if not over else '#ffffff', lw=0.15 if not over else 0.3, z=1.7)
        for t in rw['thr']:
            t = clip(t)
            if t is not None: c = np.asarray(t.coords); ax.plot(c[:, 0], c[:, 1], color='#00897b', lw=0.8, zorder=1.8)
    for z in L.endZones:
        g = clip(z['poly'])
        if g is not None: add_poly(ax, g, fc='none', ec=C['blast'] if z['kind'] == 'blastpad' else '#b8860b', lw=0.5, hatch='////' if z['kind'] == 'blastpad' else None, z=1.65)
    for e in L.emas:
        g = clip(e)
        if g is not None: add_poly(ax, g, fc=C['emas'], ec='#8d6e00', lw=0.4, alpha=0.5 if over else 0.9, hatch='xx', z=1.66)
    # markings
    mw = {'taxiway-centreline': 0.45, 'taxiway-edge': 0.25, 'enhanced-centreline': 0.3, 'hold-solid': 0.35, 'hold-dashed': 0.35, 'leadin': 0.4, 'stopbar': 0.6, 'redbox': 0.35, 'road-edge': 0.3, 'road-centre': 0.3}
    for kind, lines in L.marks.items():
        if detail == 0 and kind not in ('taxiway-centreline',): continue
        col = C['red'] if kind == 'redbox' else ('#ffffff' if kind.startswith('road') and over else '#777777' if kind.startswith('road') else C['yellow'])
        ls = (0, (3, 2)) if kind in ('enhanced-centreline', 'hold-dashed', 'road-centre') else '-'
        tol = sc / 1000 * 0.1  # 0.1 mm on paper
        sel = []
        for l in lines:
            g = LineString(l) if len(l) > 1 else None
            if g is None or not fr.intersects(g): continue
            sel.append(np.asarray(g.simplify(tol).coords))
        add_lines(ax, sel, col, mw.get(kind, 0.3) * (lwk if detail else 0.6), z=2 + (0.1 if kind == 'redbox' else 0), ls=ls)
    # buildings
    for b in L.bldg:
        g = clip(b['poly'])
        if g is None: continue
        if b['kind'] == 'walkway': add_poly(ax, g, fc='none' if over else C['walk'], ec='#37474f', lw=0.4, hatch='....', z=3.2)
        elif b['kind'] == 'rail': add_poly(ax, g, fc='none', ec='#607d8b', lw=0.3, ls=(0, (2, 2)), z=3.1)
        else: add_poly(ax, g, fc='none' if over else C['bldg'], ec=C['bldgEdge'] if not over else '#ff1744', lw=0.55 if not over else 0.7, alpha=1 if over else 0.9, z=3)
    if L.itbRoof is not None:
        g = clip(L.itbRoof)
        if g is not None: add_poly(ax, g, fc='none', ec='#455a64' if not over else '#ff1744', lw=0.5, ls=(0, (5, 3)), z=3.3)
    for t in L.tower:
        g = clip(t)
        if g is not None: add_poly(ax, g, fc='none', ec='#263238' if not over else '#ff1744', lw=0.3, z=3.4)
    if detail:
        for b in L.bldg:
            if b['kind'] in ('walkway', 'rail') or b['poly'].area < 400: continue
            g = clip(b['poly'])
            if g is None or g.area < 0.3 * b['poly'].area: continue
            c = g.representative_point()
            ax.text(c.x, c.y, f'{b["name"]}\nh {b["h"]:.1f} m', fontsize=4.5, ha='center', va='center', color='#111111' if not over else '#ffffff', zorder=9,
                    bbox=dict(boxstyle='round,pad=0.15', fc='white' if not over else 'black', ec='none', alpha=0.6))
    # masts, signs
    for m in L.masts:
        if not fr.contains(Point(m['x'], -m['z'])): continue
        if m['removed']: ax.plot(m['x'], -m['z'], marker='x', ms=2.5, color='#9e9e9e', mew=0.5, zorder=6)
        else: ax.add_patch(Circle((m['x'], -m['z']), max(m['r'], sc / 1500 * 1.2), fc='k', ec='k', lw=0.3, zorder=6)); ax.add_patch(Circle((m['x'], -m['z']), m['headHalf'], fc='none', ec='k', lw=0.25, zorder=6))
    if detail:
        sg = [s for s in L.signs if fr.intersects(s)]
        if sg: add_poly(ax, unary_union(sg), fc=C['sign'], ec=C['sign'], lw=0.3, z=6)
    # stands: class envelopes, nose, heading, name
    if detail:
        for st in L.stands:
            n = np.array([st['nose'][0], -st['nose'][1]])
            if not fr.contains(Point(n)): continue
            if st['name'] in L.env:
                g = clip(L.env[st['name']])
                if g is not None: add_poly(ax, g.simplify(0.4), fc='none', ec=C['env'], lw=0.3, ls=(0, (4, 2)), z=4, alpha=0.8)
            d = np.array([st['dir'][0], -st['dir'][1]])
            ax.plot([n[0], n[0] - d[0] * 8], [n[1], n[1] - d[1] * 8], color=C['stand'], lw=0.6, zorder=7)
            ax.plot(*n, marker='+', ms=4, color=C['stand'], mew=0.7, zorder=7)
            lbl = st['name'] + (f' ({",".join(st["alias"])})' if st['alias'] else '') + f'\n{st["cls"]} {st["src"] or ""}'
            q = n - d * 14
            ax.text(q[0], q[1], lbl, fontsize=4.2, ha='center', va='center', color=C['stand'] if not over else '#80deea', zorder=9, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.1', fc='white' if not over else 'black', ec='none', alpha=0.55))
            for p in st.get('vdgs') or []:
                if len(p['hull']) >= 3: add_poly(ax, P(hull_poly(p['hull'])), fc=C['vdgs'], ec=C['vdgs'], lw=0.2, z=6)
        # bridges: rest (thin outline), docked to the class max type (dashed), current (filled)
        for b in L.bridges:
            if not fr.contains(Point(b['rc'][0], -b['rc'][1])): continue
            for pose, sty in (('rest', dict(fc='none', ec=C['bridgeRest'], lw=0.3, z=5.1)), ('dockMax', dict(fc='none', ec=C['dock'], lw=0.3, ls=(0, (2, 1.5)), z=5.2)),
                              ('current', dict(fc=C['bridge'], ec='#311b92', lw=0.25, alpha=0.55 if over else 0.8, z=5.3))):
                Pz = b['poses'].get(pose)
                if not Pz: continue
                if pose == 'rest' and b['poses']['current']['k'] == 0: continue
                parts = [P(hull_poly(p['hull'])) for p in Pz['parts'] if len(p['hull']) >= 3 and p['part'] not in ('column',)]
                add_poly(ax, unary_union(parts), **sty)
            ax.text(b['rc'][0], -b['rc'][1], b['gate'], fontsize=3.4, ha='center', va='center', color='white', zorder=8)
    # approach-light structures (water: stations, crossbars, catwalk, huts; land: posts), light sprites, PAPI units
    for p in L.piers:
        if not fr.intersects(p['poly']): continue
        add_poly(ax, p['poly'], fc=C['pier'], ec=C['pier'], lw=0.25, z=5.5)
        if not p['pr']['water']: ax.plot(*p['pt'], marker='s', ms=1.8 if detail else 1.0, mfc='none', mec=C['pier'], mew=0.4, zorder=5.6)
    if detail and len(L.lights):
        inb = (L.lights[:, 0] > box[0]) & (L.lights[:, 0] < box[2]) & (L.lights[:, 1] > box[1]) & (L.lights[:, 1] < box[3])
        if inb.any():
            lc = {'white': '#9e9e9e', 'red': '#e53935', 'green': '#43a047', 'blue': '#1e88e5', 'yellow': '#fbc02d'}
            cols = [lc.get(L.lightCol[i], '#9e9e9e') for i in np.where(inb)[0]]
            ax.scatter(L.lights[inb, 0], L.lights[inb, 1], s=0.35, c=cols, linewidths=0, zorder=5.4, rasterized=over)
        for q in L.papis:
            if fr.contains(Point(q)): ax.add_patch(Rectangle((q[0] - 1.0, q[1] - 0.6), 2.0, 1.2, fc='#ff6f00', ec='k', lw=0.2, zorder=5.6))
    # GSE and aircraft
    for kind, g in L.gse:
        g = clip(g)
        if g is not None: add_poly(ax, g, fc=C['gse'], ec='#bf360c', lw=0.2, z=6.5)
    for a in L.ac:
        A = a['a']
        if a['poly'] is None:
            if fr.contains(Point(a['pt'])): ax.plot(*a['pt'], marker='D', ms=2.5, color=C['ac'], zorder=7)
            continue
        g = clip(a['poly'])
        if g is None: continue
        add_poly(ax, g, fc=C['ac'], ec='#0d47a1', lw=0.3, alpha=0.3 if not over else 0.35, z=6.8)
        if detail:
            c = a['poly'].centroid
            ax.text(c.x, c.y, f'{A["flight"] or A["hex"]}\n{A["icao"]}', fontsize=3.8, ha='center', va='center', color='#0d47a1' if not over else '#bbdefb', zorder=9)


def draw_deviations(ax, L, box, src, detail):
    if src not in L.dev: return 0, 0
    fr = sbox(*box); n = nflag = 0
    pts, cols = [], []
    labels = []
    for fid, s in L.dev[src].items():
        summ = L.devSummary[src].get(fid) or {}
        if fid.startswith('rotunda:'):
            p = np.array(s['pts'][0]); v = s.get('vec')
            if v and s['off'][0] is not None and fr.contains(Point(p[0], -p[1])):
                q = p + np.array(v); col = C['dev2'] if s['off'][0] > 1 else C['dev1'] if s['off'][0] > 0.5 else C['dev0']
                ax.annotate('', xy=(q[0], -q[1]), xytext=(p[0], -p[1]), arrowprops=dict(arrowstyle='->', color=col, lw=0.5), zorder=11)
                ax.add_patch(Circle((q[0], -q[1]), 2.45, fc='none', ec=col, lw=0.4, ls=(0, (1, 1)), zorder=11))
            continue
        P0 = np.array(s['pts']); N = np.array(s['nrm']); off = np.array([np.nan if o is None else o for o in s['off']], float)
        if not len(P0): continue
        inside = (P0[:, 0] > box[0]) & (P0[:, 0] < box[2]) & (-P0[:, 1] > box[1]) & (-P0[:, 1] < box[3])
        if not inside.any(): continue
        n += 1
        m = ~np.isnan(off)
        E = P0 + N * np.nan_to_num(off)[:, None]
        for k in np.where(inside)[0]:
            if m[k]:
                a = abs(off[k]); pts.append((E[k, 0], -E[k, 1])); cols.append(C['dev2'] if a > 1 else C['dev1'] if a > 0.5 else C['dev0'])
            elif detail: pts.append((P0[k, 0], -P0[k, 1])); cols.append(C['devNA'])
        if summ.get('flag'):
            nflag += 1
            k = np.where(inside & m)[0]
            if len(k):
                kk = k[np.argmax(np.abs(off[k]))]; labels.append((E[kk], summ))
    if pts:
        pts = np.array(pts); ax.scatter(pts[:, 0], pts[:, 1], s=0.6 if detail else 0.15, c=cols, linewidths=0, zorder=10, rasterized=True)
    # call-outs for flagged features (median offset > 1 m); on the overview only the dots
    for i, (e, summ) in enumerate(labels[:60] if detail else []):
        ang = (i * 137.5) % 360; r = 18 if detail else 60
        q = (e[0] + r * math.cos(math.radians(ang)), -e[1] + r * math.sin(math.radians(ang)))
        nm = summ['name'][:34]
        ax.annotate(f'{nm}\nmed {summ["median"]:.1f} / p90 {summ["p90"]:.1f} / max {summ["max"]:.1f} m', xy=(e[0], -e[1]), xytext=q, fontsize=3.6 if detail else 3.2, color=C['dev2'],
                    arrowprops=dict(arrowstyle='-', color=C['dev2'], lw=0.35), zorder=12, bbox=dict(boxstyle='round,pad=0.15', fc='white', ec=C['dev2'], lw=0.3, alpha=0.85))
    return n, nflag


def draw_conflicts(ax, L, box, detail):
    if not L.audit: return collections.Counter()
    fr = sbox(*box); cnt = collections.Counter()
    for c in L.audit['conflicts']:
        if not c.get('loc'): continue
        p = (c['loc'][0], -c['loc'][1])
        if not fr.contains(Point(p)): continue
        cnt[c['severity']] += 1
        if c['severity'] in ('COLLISION', 'OFF-PAVEMENT'):
            ax.plot(*p, marker='x', ms=4.5 if detail else 3, mew=0.9, color=C['conflict'], zorder=13)
            if detail or cnt[c['severity']] < 60: ax.text(p[0] + 1.5, p[1] + 1.5, f'#{c["n"]}', fontsize=3.8, color=C['conflict'], zorder=13, fontweight='bold')
        elif c['severity'] == 'OBSTRUCTION':
            ax.plot(*p, marker='^', ms=4 if detail else 2.5, mfc='none', mew=0.7, color=C['obstr'], zorder=13)
            if detail: ax.text(p[0] + 1.5, p[1] - 3.0, f'#{c["n"]}', fontsize=3.4, color=C['obstr'], zorder=13)
        elif c['severity'] == 'CLEARANCE':
            ax.plot(*p, marker='o', ms=2.2, mfc='none', mew=0.4, color='#ff6d00', zorder=12)
    return cnt


def legend(ax, x, y, over):
    items = [('pave', 'paved area (app raster: physics + ground)', dict(fc='none' if over else C['pave'], ec=C['paveEdge'] if over else '#b0b0a8')),
             ('rwy', 'runway (RWY table) + painted markings', dict(fc=C['rwy'], ec=C['rwyEdge'])), ('twy', 'taxiway polygon (SFO Museum)', dict(fc='#d6d6d2', ec=C['twy'])),
             ('paint', 'green no-taxi paint', dict(fc=C['paint'], ec='#2e7d32')), ('emas', 'EMAS bed / blast pad (hatched)', dict(fc=C['emas'], ec='#8d6e00')),
             ('bldg', 'building footprint (label: roof height)', dict(fc=C['bldg'], ec='k')), ('walk', 'elevated walkway', dict(fc=C['walk'], ec='#37474f')),
             ('br', 'jet bridge as displayed', dict(fc=C['bridge'], ec='#311b92')), ('brr', 'bridge parked (rest)', dict(fc='none', ec=C['bridgeRest'])),
             ('brd', 'bridge docked to class-max type', dict(fc='none', ec=C['dock'])), ('env', 'stand class envelope (union of types)', dict(fc='none', ec=C['env'])),
             ('ac', 'aircraft (rendered model planform)', dict(fc=C['ac'], ec='#0d47a1')), ('gse', 'ground service vehicle', dict(fc=C['gse'], ec='#bf360c'))]
    for i, (k, t, sty) in enumerate(items):
        yy = y - i * 4.2
        ax.add_patch(Rectangle((x, yy - 1.4), 6, 2.8, lw=0.4, **sty)); ax.text(x + 8, yy, t, fontsize=5.2, va='center')
    yy = y - len(items) * 4.2
    for col, t, ls in ((C['yellow'], 'taxiway centreline / edge / lead-in / hold', '-'), (C['red'], 'red equipment box', '-'), ('#00897b', 'runway threshold', '-')):
        ax.plot([x, x + 6], [yy, yy], color=col, lw=0.9, ls=ls); ax.text(x + 8, yy, t, fontsize=5.2, va='center'); yy -= 4.2
    for col, t in ((C['dev0'], 'imaged edge <= 0.5 m from model'), (C['dev1'], 'imaged edge 0.5 - 1.0 m'), (C['dev2'], 'imaged edge > 1.0 m (call-out: feature median > 1 m)')):
        ax.scatter([x + 3], [yy], s=6, c=col); ax.text(x + 8, yy, t, fontsize=5.2, va='center'); yy -= 4.2
    ax.plot([x + 3], [yy], marker='x', ms=5, mew=1, color=C['conflict']); ax.text(x + 8, yy, 'conflict #n (see report.md)', fontsize=5.2, va='center'); yy -= 4.2
    ax.plot([x + 3], [yy], marker='^', ms=4, mfc='none', mew=0.8, color=C['obstr']); ax.text(x + 8, yy, 'obstruction: pier / sign on a movement surface', fontsize=5.2, va='center'); yy -= 4.2
    ax.plot([x + 3], [yy], marker='o', ms=3, mfc='none', color='#ff6d00'); ax.text(x + 8, yy, 'below ICAO stand clearance', fontsize=5.2, va='center'); yy -= 4.2
    ax.add_patch(Rectangle((x, yy - 1.4), 6, 2.8, lw=0.4, fc=C['pier'], ec=C['pier'])); ax.text(x + 8, yy, 'approach-light structure (water) / post (land, square)', fontsize=5.2, va='center'); yy -= 4.2
    ax.scatter([x + 1.5, x + 3, x + 4.5], [yy, yy, yy], s=3, c=['#9e9e9e', '#e53935', '#43a047']); ax.text(x + 8, yy, 'light sprite (runway / approach / taxi edge); PAPI box orange', fontsize=5.2, va='center'); yy -= 4.2
    ax.plot([x, x + 6], [yy, yy], color=C['gridST'], lw=0.6, ls=(0, (4, 3))); ax.text(x + 8, yy, 'airport grid s / t (100 m)', fontsize=5.2, va='center')
    return yy


def render_sheet(L, sd, variant, src=None, outdir=None, stats=None):
    fs = fit_sheet(sd); pw, ph = PAPER[fs['paper']]; sc = fs['scale']; box = fs['box']
    fig = plt.figure(figsize=(pw / 25.4, ph / 25.4))
    vw, vh = pw - 2 * BORDER - STRIP, ph - 2 * BORDER
    ax = fig.add_axes([BORDER / pw, BORDER / ph, vw / pw, vh / ph])
    ax.set_xlim(box[0], box[2]); ax.set_ylim(box[1], box[3]); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_linewidth(0.8)
    img_note = 'none (vector)'
    if variant != 'vector' and src is not None:
        res = max(0.15, sc * 25.4 / DPI / 1000)
        img, valid, _ = src.raster(box[0], -box[3], box[2], -box[1], res)
        rgba = np.dstack([img[:, :, ::-1], (valid * 255).astype(np.uint8)])
        ax.imshow(rgba, extent=[box[0], box[2], box[1], box[3]], origin='upper', zorder=0, interpolation='bilinear')
        ax.set_facecolor('#202020'); img_note = src.name
    draw_grid(ax, box, sc)
    draw_layers(ax, L, box, sc, variant, sd.get('detail', 1))
    devsrc = 'naip' if 'naip' in L.dev else (next(iter(L.dev)) if L.dev else None)
    if variant == 'overlay-google' and 'google' in L.dev: devsrc = 'google'
    nf, nflag = draw_deviations(ax, L, box, devsrc, sd.get('detail', 1)) if devsrc else (0, 0)
    cc = draw_conflicts(ax, L, box, sd.get('detail', 1))
    # right-hand strip: north arrow, scale bar, legend, title block
    sx = fig.add_axes([(pw - BORDER - STRIP + 3) / pw, BORDER / ph, (STRIP - 3) / pw, vh / ph]); sx.set_xlim(0, STRIP - 3); sx.set_ylim(0, vh); sx.axis('off')
    top = vh - 4
    sx.add_patch(FancyArrow(12, top - 22, 0, 18, width=2.2, head_width=7, head_length=7, length_includes_head=True, fc='k', ec='k'))
    sx.text(12, top - 1, 'N', ha='center', va='bottom', fontsize=9, fontweight='bold'); sx.text(12, top - 27, 'true north', ha='center', fontsize=4.5)
    Vs, Us = np.array(scene()['meta']['stBasis']['V']), np.array(scene()['meta']['stBasis']['U'])
    for vec, nm in ((Vs, '+s (10->28)'), (Us, '+t (1->19)')):
        sx.annotate('', xy=(40 + vec[0] * 12, top - 13 + vec[1] * 12), xytext=(40, top - 13), arrowprops=dict(arrowstyle='->', color='#2e86c1', lw=0.7))
        sx.text(40 + vec[0] * 15, top - 13 + vec[1] * 15, nm, fontsize=4.2, color='#2e86c1', ha='center', va='center')
    # scale bar
    m_per_mm = sc / 1000; nice = [10, 20, 25, 50, 100, 200, 250, 500, 1000][np.searchsorted([10, 20, 25, 50, 100, 200, 250, 500, 1000], 45 * m_per_mm) - 1] if 45 * m_per_mm >= 10 else 10
    Lmm = nice / m_per_mm; y = top - 38
    for i in range(4):
        sx.add_patch(Rectangle((4 + i * Lmm / 4, y), Lmm / 4, 1.6, fc='k' if i % 2 == 0 else 'white', ec='k', lw=0.4))
    for i in (0, 2, 4): sx.text(4 + i * Lmm / 4, y - 1.2, f'{nice * i / 4:g}', ha='center', va='top', fontsize=4.5)
    sx.text(4 + Lmm + 2, y + 0.8, 'm', fontsize=4.5, va='center')
    sx.text(4, y + 3.5, f'Scale 1:{sc} on {fs["paper"]}', fontsize=6, fontweight='bold')
    yy = legend(sx, 4, y - 10, variant != 'vector')
    # title block
    S = scene(); tb_h = 70; y0 = 2; PV = L.prov
    sx.add_patch(Rectangle((1, y0), STRIP - 5, tb_h, fc='white', ec='k', lw=0.8))
    lines = [('SFO Live 3D - 2-D drawing set (drawn from the 3-D parameters)', 5.2, 'bold'), (sd['title'], 6.6, 'bold'),
             (f'Sheet {sd["id"]}  |  variant: {variant}  |  1:{sc} {fs["paper"]}', 5.0, 'normal'),
             (f'Imagery: {img_note}', 4.6, 'normal'),
             ('Deviation dots: ' + (f'measured on {L.S and devsrc} imagery' if devsrc else 'not measured'), 4.6, 'normal'),
             (f'Features on sheet: {nf} measured, {nflag} with median > 1.0 m', 4.8, 'normal'),
             (f'Conflicts on sheet: ' + ', '.join(f'{k} {v}' for k, v in sorted(cc.items())) if cc else 'Conflicts on sheet: none', 4.8, 'normal'),
             (f'Scene: git {PV["git"]}, extracted {PV["generated"][:16]}Z, inputs {PV["inputsHash"]}', 4.2, 'normal'),
             (f'World frame {PV["frame"]}  |  ' + (f'STALE: {len(PV["stale"])} input(s) changed since' if PV['stale'] else 'staleness unknown' if PV['stale'] is None
                                                     else (f'app = commit {PV["git"]} (git archive)' + (f'; working tree differs in {len(PV["worktreeChanged"])} app file(s)' if PV.get('worktreeChanged') else ''))
                                                     if PV.get('appSource') == 'git-archive' else 'matches the working tree'), 4.2, 'bold' if PV['stale'] or PV.get('worktreeChanged') else 'normal'),
             (('Imagery: ' + L.imgprov.get(variant, '')) [:110], 3.9, 'normal'),
             ('World grid: x east / z south (m from ARP)  |  s/t: airport grid (js/geo.js)', 4.2, 'normal'),
             ('Geometry: SFO Museum (CDLA-Permissive-1.0) + surveyed stands/paint/pavement', 4.2, 'normal'),
             (('Google imagery: reference only - do not redistribute' if variant == 'overlay-google' else 'No imagery pixels on this sheet' if variant == 'vector' else 'NAIP imagery: public domain (USDA)'), 4.4, 'bold'),
             (f'Generated {datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")}Z by tools/drawing/sheets.py', 4.2, 'normal')]
    ty = y0 + tb_h - 4
    for t, f, w in lines:
        sx.text(3, ty, t, fontsize=f, fontweight=w, va='top'); ty -= f * 0.62 + 1.2
    # border
    fig.add_artist(Rectangle((BORDER / 2 / pw, BORDER / 2 / ph), 1 - BORDER / pw, 1 - BORDER / ph, transform=fig.transFigure, fill=False, lw=1.0, ec='k'))
    os.makedirs(outdir, exist_ok=True)
    base = os.path.join(outdir, sd['id'] + ('' if variant == 'vector' else '_' + variant))
    fig.savefig(base + '.svg', dpi=DPI); fig.savefig(base + '.png', dpi=DPI)
    plt.close(fig)
    if variant == 'vector': compact(base)
    if stats is not None: stats[sd['id'] + ':' + variant] = dict(scale=sc, paper=fs['paper'], features=nf, flagged=nflag, conflicts=dict(cc), box=box, file=os.path.relpath(base, ROOT))
    return base


def compact(base):
    """committable sheets: 256-colour palette PNG, SVG numbers rounded to 0.01 pt (0.004 mm on paper)"""
    import re
    from PIL import Image
    im = Image.open(base + '.png').convert('RGB'); im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(base + '.png', optimize=True)
    t = open(base + '.svg').read(); t = re.sub(r'(\d+\.\d{2})\d+', r'\1', t); open(base + '.svg', 'w').write(t)


def crop(L, c, variant, src, outdir, size_m=None):
    """close-up of one conflict: all layers, the two objects outlined"""
    x, z = c['loc']; r = size_m or 32
    fig = plt.figure(figsize=(3.6, 3.6)); ax = fig.add_axes([0.02, 0.1, 0.96, 0.88])
    box = (x - r, -z - r, x + r, -z + r); ax.set_xlim(box[0], box[2]); ax.set_ylim(box[1], box[3]); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
    if variant != 'vector' and src is not None:
        img, valid, _ = src.raster(box[0], -box[3], box[2], -box[1], 0.12)
        ax.imshow(np.dstack([img[:, :, ::-1], (valid * 255).astype(np.uint8)]), extent=[box[0], box[2], box[1], box[3]], origin='upper', zorder=0)
    draw_layers(ax, L, box, 300, variant, 2)
    ax.plot(x, -z, marker='x', ms=10, mew=1.5, color=C['conflict'], zorder=20)
    for k, col in (('a', '#d50000'), ('b', '#ff9100')):
        for ring in c[k].get('geom') or []:
            r = np.asarray(ring); ax.plot(r[:, 0], -r[:, 1], color=col, lw=1.4, zorder=19)
    from audit import scen_label
    ax.set_title(f'#{c["n"]} {c["severity"]} [{scen_label(c)}] {c["kind"]}', fontsize=6, loc='left', pad=2)
    fig.text(0.02, 0.02, ('red: ' + c['a'].get('label', '') + '   orange: ' + c['b'].get('label', ''))[:130] + '\n' + (c.get('note') or '')[:130], fontsize=4.2, va='bottom')
    ax.plot([box[0] + 2, box[0] + 12], [box[1] + 2, box[1] + 2], color='k', lw=1.5, zorder=20); ax.text(box[0] + 7, box[1] + 3, '10 m', fontsize=5, ha='center', zorder=20)
    os.makedirs(outdir, exist_ok=True); f = os.path.join(outdir, f'conflict_{c["n"]:04d}' + ('' if variant == 'vector' else '_' + variant) + '.png')
    fig.savefig(f, dpi=200); plt.close(fig)
    if variant == 'vector':
        from PIL import Image
        Image.open(f).convert('RGB').quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(f, optimize=True)
    return f


def run(only=None, crops_docs=60, crops_out=250):
    L = Layers(); srcs = background.sources(); stats = {}
    defs = sheet_defs(L)
    if only: defs = [d for d in defs if any(o in d['id'] for o in only)]
    for sd in defs:
        t0 = time.time()
        render_sheet(L, sd, 'vector', None, DOCS, stats)
        if 'google' in srcs: render_sheet(L, sd, 'overlay-google', srcs['google'], os.path.join(OUT, 'sheets'), stats)
        if 'naip' in srcs: render_sheet(L, sd, 'overlay-naip', srcs['naip'], os.path.join(OUT, 'sheets'), stats)
        print(f'  sheet {sd["id"]} ({time.time() - t0:.0f} s)', flush=True)
    # conflict close-ups
    if L.audit and not only:
        cs = [c for c in L.audit['conflicts'] if c.get('loc') and c['scenario'] != 'KINEMATICS']
        imp = [c for c in cs if c['severity'] in ('COLLISION', 'OFF-PAVEMENT', 'OBSTRUCTION')]
        t0 = time.time()
        for c in imp[:crops_out]:
            if 'google' in srcs: crop(L, c, 'overlay-google', srcs['google'], os.path.join(OUT, 'crops'))
        for c in imp[:crops_docs]: crop(L, c, 'vector', None, os.path.join(DOCS, 'crops'))
        print(f'  {min(len(imp), crops_out)} overlay + {min(len(imp), crops_docs)} vector conflict crops ({time.time() - t0:.0f} s)')
    if not only:
        # sheets of an earlier sheet set (renamed / dropped ids) must not linger next to the current ones
        import re
        ids = {d['id'] for d in defs}
        for d, pat in ((DOCS, r'^(\d\d-[^_]+?)\.(svg|png)$'), (os.path.join(OUT, 'sheets'), r'^(\d\d-[^_]+?)_overlay-[a-z]+\.(svg|png)$')):
            for fn in (os.listdir(d) if os.path.isdir(d) else []):
                m = re.match(pat, fn)
                if m and m.group(1) not in ids: os.remove(os.path.join(d, fn)); print('  removed stale sheet', os.path.relpath(os.path.join(d, fn), ROOT))
    json.dump(stats, open(os.path.join(OUT, 'sheets.json'), 'w'), indent=1)
    return stats


if __name__ == '__main__':
    run(sys.argv[1:] or None)
