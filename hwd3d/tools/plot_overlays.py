"""Phase 1 cross-check renders of data/hwd_airport.json: 2-D data-check plots for the owner, plus the measurements the
cross-check report (docs/phase1_crosscheck.md) quotes.

New for hwd3d (Phase 1 cross-check task). No sfo3d counterpart is forked; it reuses hwd3d modules only:
tools/common/hwd_frame.py (world frame, UTM 10N), tools/imagery/common.py (NAIP loader), tools/airport/al5015.py
(AL-5015 text layer and hot-spot rings). Colours: the dark-surface categorical slots and the status colours of the
dataviz reference palette (validated with its validate_palette.js on the dark surface: taxiway set passes all checks).

Outputs (out/ is gitignored; docs/phase1/ is for commit):
  out/phase1/overlay_naip.png               the data over NAIP 2024, whole airfield, 0.6 m/px
  out/phase1/overlay_naip_<area>.png        zoom crops at 0.3 m/px (AREAS below)
  out/phase1/overlay_al5015.png             the data in the frame of AL-5015 (rasterised at 400 dpi, similarity fit)
  out/phase1/overlay_al5015_<area>.png      two crops of that overlay
  out/phase1/crosscheck_metrics.json        every number the report quotes
  docs/phase1/*.jpg                         the same images, <= 2 MB each, with the credit line   (--docs)
  docs/phase1/crosscheck_metrics.json       a committed copy of the metrics with the ODbL notice     (--docs; Phase 1 review)

Inputs (committed): data/hwd_airport.json; refs/cache/naip/naip_2024_hwd_rgb.jpg + .json (or the lossless local
GeoTIFF refs/cache/local/naip/naip_2024_hwd_utm10n.tif when present - same pixels before JPEG coding);
refs/cache/faa/05015ad_2611.pdf (pdftoppm / pdftotext of poppler); refs/cache/osm/khwd_osm_xcheck.json (the
diagram registration G1's xcheck_osm_faa.py stored, compared here with an independent one).

Measurements (all written to crosscheck_metrics.json):
  1. AL-5015 registration: the four runway-bar ends found on the 400 dpi raster by an axis walk (a cross-section is
     'bar' when >= 90 % of 21 samples across +-0.4 bar widths are black or hot-spot brown, i.e. the overprinted rings
     do not cut the bar; gaps <= 16 px are bridged), a similarity transform (complex least squares, 4 parameters, no
     shear) fitted to the NASR runway ends; residuals per end, along / across the runway; the 6-parameter affine for
     comparison; drawn bar widths vs NASR widths; bar ends vs the ones stored in khwd_osm_xcheck.json.
  2. AL-5015 vs the data (through the similarity): distance of every taxiway centreline sample (every 5 m) to the
     nearest diagram pavement pixel (grey 195-215 or runway bar, closed by 5 px over text); diagram pavement more than
     25 m from any of our paved features (areas > 400 m2); OSM hangars vs the diagram's black building blocks;
     hot-spot centres (al5015.hotspots ring centres through the similarity vs the data); the HS 5 hold symbols.
  3. NAIP 2024 vs the data: (a) taxiway centreline vs pavement centre - cross profiles every 6 m, pavement = the
     build's grey test (saturation < 0.16, excess green < 8: build_airport.SAT_MAX / EG_MAX, read on this mosaic),
     gaps < 1.5 m filled (paint), run width 6-35 m, stations within 40 m of a runway or inside an apron skipped;
     (b) hangar and building footprints vs roof edges - shift (+-8.1 m since the Phase 1 review, was +-3.9 m; 0.3 m step)
     that maximises the mean NAIP gradient magnitude along the outline, in NAIP 2024 and 2022; a shift >= 2 m that is
     the same in both years (within 1 m) is flagged as an outline offset candidate (roof lean changes with the flight); (c) the painted displaced-threshold bars of 10R and 28L along the runway
     axis vs the NASR surveyed displaced thresholds.

usage: python3 hwd3d/tools/plot_overlays.py [--no-naip] [--no-al] [--no-render (NAIP numbers only)]
                                           [--no-measure (NAIP images only; keeps the stored numbers)] [--docs]
"""
import json, math, os, subprocess, sys, tempfile

import numpy as np
from scipy import ndimage as nd
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.prepared import prep

HERE = os.path.dirname(os.path.abspath(__file__))
HWD = os.path.abspath(os.path.join(HERE, '..'))
for p in ('common', 'imagery', 'airport'):
    sys.path.insert(0, os.path.join(HERE, p))
import hwd_frame as F                                                     # noqa: E402
import common as IC                                                       # noqa: E402  (tools/imagery/common.py)
import al5015                                                             # noqa: E402

import matplotlib                                                         # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt                                           # noqa: E402
import matplotlib.patheffects as pe                                       # noqa: E402
from matplotlib.lines import Line2D                                       # noqa: E402

DATA = os.path.join(HWD, 'data', 'hwd_airport.json')
XCHECK = os.path.join(HWD, 'refs', 'cache', 'osm', 'khwd_osm_xcheck.json')
OUT = os.path.join(HWD, 'out', 'phase1')
DOCS = os.path.join(HWD, 'docs', 'phase1')
FT = 0.3048

# ------------------------------------------------------------------------------------------------ style (sourced)
# taxiway ref -> colour: dataviz reference palette, dark-surface categorical slots 1-5, 7, 8 in fixed order (slot 6
# green is skipped so that it never meets the status-green of observed parking spots); A1 / Z1 share the hue of A / Z
# and are dashed (composite encoding: 7 hues for 9 refs). validate_palette.js --mode dark: all checks pass.
TWY_COL = {'A': '#3987e5', 'B': '#d95926', 'C': '#199e70', 'D': '#c98500', 'E': '#d55181', 'F': '#9085e9', 'Z': '#e66767'}
TWY_COL['A1'] = TWY_COL['A']; TWY_COL['Z1'] = TWY_COL['Z']
OBS_COL, INF_COL = '#0ca30c', '#fab219'          # status palette good / warning: obs filled, inf hollow (+ legend)
INK, INK2, INK3 = '#f0efec', '#c3c2b7', '#8f8e88'  # text / secondary / muted (dark-surface text tokens)
HS_COL = '#b5651d'                                 # hot spots: brown, the colour AL-5015 itself uses (RGB 149, 81, 1)
HALO = [pe.withStroke(linewidth=2.6, foreground='#111111')]
KIND_MARK = {'tiedown': '^', 'ramp': 'o', 'hangar_apron': 's', 'helipad': 'D'}

CREDIT_NAIP = ('Imagery: USDA NAIP 2024 (USDA FPAC-BC Geospatial Enterprise Operations), public domain.  '
               'Data: © OpenStreetMap contributors (ODbL 1.0); contains information from ADSB.lol (ODbL 1.0); '
               'FAA NASR / AL-5015 (public domain).  hwd3d data/hwd_airport.json')
CREDIT_AL = ('Base: FAA airport diagram AL-5015, d-TPP cycle 2611 (29 Oct - 26 Nov 2026), public domain - not to be used '
             'for navigation.  Overlay: © OpenStreetMap contributors (ODbL 1.0); contains information from ADSB.lol '
             '(ODbL 1.0); FAA NASR (public domain).  hwd3d data/hwd_airport.json')

# zoom crops: name -> (x0, x1, z0, z1) in world metres (x east, z south), title
AREAS = {
    'west_hangars': ((-520, 70, -790, -370), 'West Hangars, west tie-down apron (AL-5015 prints "FBO RAMP" there), 10L run-up, HS 3'),
    'east_hangars_runup': ((470, 790, 40, 370), 'East Hangars (rows A-E), 28L run-up, HS 2'),
    'green_ramp_tower': ((-190, 200, -600, -220), 'Green Ramp tie-downs (AL-5015 "GA TRANSIENT RAMP" text), tower, terminal / administration'),
    'fbo_ne': ((30, 560, -390, 90), 'FBO Ramp (north-east): FBO hangars, transient ramp spots, helipads, 28R run-up'),
    'fbo_south_heli': ((-120, 300, 140, 450), 'FBO Ramp (south), Signature Aviation, unmapped helicopter pads'),
    'tower_helipads': ((-250, 90, -500, -320), 'Tower (ATCT), Helicopter Ramp helipads, Green Ramp north edge'),
    'rwy_10R_10L': ((-760, -380, -420, -170), 'Runway ends 10R (displaced threshold 826 ft) and 10L, two wind cones'),
    'rwy_28L': ((500, 850, 360, 590), 'Runway end 28L (displaced threshold 676 ft), HS 5, wind cone'),
    'rwy_28R': ((200, 430, -10, 160), 'Runway end 28R, 28R run-up, HS 4, wind cone'),
}
# cross-check annotations: features seen on AL-5015 and / or NAIP 2024 that the data set lacks (drawn as a dashed white
# ring, text in the crops); positions read by eye on 0.1 m NAIP 2024 resamplings (docs/phase1_crosscheck.md section 3)
ANNOT = [
    ((-410.5, -399.0), 'wind cone? (AL-5015 unlit wind cone + NAIP object; not in data)'),
    ((-412.0, -253.7), 'wind cone? (AL-5015 + NAIP; not in data)'),
    ((268.5, 95.2), 'wind cone? (AL-5015 + NAIP; not in data)'),
    ((537.5, 440.0), 'wind cone? (AL-5015 + NAIP; not in data)'),
    ((258.5, 280.5), 'wind cone? (AL-5015 + NAIP; not in data)'),
    ((-79.0, -412.0), 'painted H circle (NAIP; not in data)'),
]
OVERVIEW = (-1000, 1000, -850, 750)


def r(v, n=2): return None if v is None else round(float(v), n)


def load():
    return json.load(open(DATA))


# ============================================================================================ NAIP world raster
class NaipGrid:
    """NAIP 2024 resampled (bilinear) onto a north-up world grid; world -> pixel by a cubic polynomial fitted to the
    exact hwd_frame transform over the requested window (error asserted < 5 mm)."""
    def __init__(self, year='2024'):
        self.img, self.geo, self.src = IC.load_rgb(year, prefer='tif')
        self.year = year
        self._poly = {}            # per instance: the polynomial depends on the year's raster georeference

    def _px(self, X, Z, win):
        key = tuple(float(v) for v in win)
        if key not in self._poly: self._poly[key] = self._fit(win)
        terms, pc, pr = self._poly[key]
        Af = terms(X, Z)
        return (Af @ pc).reshape(np.shape(X)), (Af @ pr).reshape(np.shape(X))

    def _fit(self, win):
        x0, x1, z0, z1 = win
        gx, gz = np.meshgrid(np.linspace(x0, x1, 31), np.linspace(z0, z1, 31))
        E, N = F.world_to_utm10_np(gx, gz)
        g = self.geo['g']; C = (E - self.geo['e0']) / g - 0.5; R = (self.geo['n1'] - N) / g - 0.5
        cx, cz, sx, sz = (x0 + x1) / 2, (z0 + z1) / 2, (x1 - x0) / 2, (z1 - z0) / 2
        def terms(x, z):
            u = (np.ravel(x) - cx) / sx; v = (np.ravel(z) - cz) / sz
            return np.stack([u ** i * v ** j for i in range(4) for j in range(4 - i)], 1)
        A = terms(gx, gz); pc = np.linalg.lstsq(A, C.ravel(), rcond=None)[0]; pr = np.linalg.lstsq(A, R.ravel(), rcond=None)[0]
        t = np.linspace(0, 1, 97); tx = x0 + (x1 - x0) * t; tz = z0 + (z1 - z0) * t[::-1]
        Et, Nt = F.world_to_utm10_np(tx, tz); ce = (Et - self.geo['e0']) / g - 0.5; re = (self.geo['n1'] - Nt) / g - 0.5
        At = terms(tx, tz); err = float(np.max(np.hypot(At @ pc - ce, At @ pr - re))) * g
        assert err < 0.005, 'world->pixel polynomial error %.4f m' % err
        return terms, pc, pr

    def window(self, win, res):
        x0, x1, z0, z1 = win
        xs = np.arange(x0 + res / 2, x1, res); zs = np.arange(z0 + res / 2, z1, res)
        X, Z = np.meshgrid(xs, zs)
        c, rr = self._px(X, Z, win)
        out = np.stack([nd.map_coordinates(self.img[..., k], [rr, c], order=1, mode='constant', cval=0) for k in range(3)], -1)
        return out

    def sample(self, X, Z, win):
        """float RGB at world points (bilinear)"""
        c, rr = self._px(X, Z, win)
        return np.stack([nd.map_coordinates(self.img[..., k].astype(np.float32), [np.ravel(rr), np.ravel(c)], order=1, mode='nearest').reshape(np.shape(X)) for k in range(3)], -1)


# ============================================================================================ drawing
def _poly_xy(T, ring, close=True):
    P = T(np.asarray(ring, float))
    if close: P = np.vstack([P, P[:1]])
    return P[:, 0], P[:, 1]


def _disp_angle(T, x, z, hdg):
    """display rotation (deg, ccw) of a marker pointing along heading hdg at world (x, z): plot y grows downward"""
    v = np.array([math.sin(math.radians(hdg)), -math.cos(math.radians(hdg))])
    a = T(np.array([[x, z], [x + v[0], z + v[1]]])); d = a[1] - a[0]
    return math.degrees(math.atan2(-d[1], d[0]))


def draw_data(ax, D, T, mpp, fs, zoom, view):
    """draw the data set. T: (n, 2) world xz -> plot coords (y down); mpp: metres per plot unit; fs: base font size (pt);
    zoom: True for crops (spans, helipad H, more labels); view (x0, x1, y0, y1) in plot coords, to place labels inside."""
    lw = 1.6 if zoom else 1.1
    def inside(p, m=0.0):
        return view[0] + m <= p[0] <= view[1] - m and view[2] + m <= p[1] <= view[3] - m
    def label(p, s, size=fs, col=INK, **kw):
        if inside(p): ax.text(p[0], p[1], s, fontsize=size, color=col, path_effects=HALO, ha=kw.pop('ha', 'center'), va=kw.pop('va', 'center'), zorder=kw.pop('zorder', 30), **kw)
    # aprons
    for a in D['aprons']:
        x, y = _poly_xy(T, a['ring']); ax.plot(x, y, color=INK2, lw=lw * 0.8, ls=(0, (1, 2)), zorder=3)
        if a['name']:
            c = Polygon(a['ring']).representative_point(); p = T(np.array([[c.x, c.y]]))[0]
            label(p, a['name'], size=fs * 0.95, col=INK2, style='italic', zorder=29)
    # buildings, hangars, helipads
    for b in D['buildings']:
        if b.get('ring'):
            x, y = _poly_xy(T, b['ring'])
            tower = b['kind'] == 'control_tower'
            ax.plot(x, y, color=INK if tower else INK3, lw=lw * (1.6 if tower else 0.7), zorder=4)
            if tower:
                c = Polygon(b['ring']).centroid; p = T(np.array([[c.x, c.y]]))[0]
                label(p + np.array([0, -18 / mpp]), 'ATCT (OSM)', size=fs, fontweight='bold')
        if b['kind'] == 'fire_station':
            p = T(np.array([[b['x'], b['z']]]))[0]
            ax.plot(*p, marker='P', ms=9 if zoom else 7, mfc=INK, mec='#111111', zorder=20)
            label(p + np.array([0, 14 / mpp]), 'fire station (OSM node)', size=fs * 0.9)
    for h in D['hangars']:
        x, y = _poly_xy(T, h['ring'])
        ax.plot(x, y, color=INK, lw=lw * 0.9, ls='-' if h['kind'] == 't_hangar_row' else (0, (4, 2)), zorder=5)
        name = h['letter'] or h['name']
        if name:
            c = Polygon(h['ring']).centroid; p = T(np.array([[c.x, c.y]]))[0]
            label(p, name, size=fs * (1.05 if h['letter'] else 0.85), fontweight='bold' if h['letter'] else 'normal')
    for hp in D['helipads']:
        x, y = _poly_xy(T, hp['ring']); ax.plot(x, y, color=INK, lw=lw * 0.8, zorder=6)
        if zoom: label(T(np.array([[hp['x'], hp['z']]]))[0], 'H', size=fs * 0.9, fontweight='bold')
    # runways
    for rw in D['runways']:
        x, y = _poly_xy(T, rw['outline']['ring']); ax.plot(x, y, color='white', lw=lw * 1.1, zorder=8)
        e0, e1 = rw['ends']; P = T(np.array([[e0['x'], e0['z']], [e1['x'], e1['z']]]))
        ax.plot(P[:, 0], P[:, 1], color='white', lw=lw * 0.6, ls=(0, (8, 6)), zorder=8)
        u = (P[1] - P[0]) / np.hypot(*(P[1] - P[0]))
        for e, sgn, p in ((e0, -1, P[0]), (e1, 1, P[1])):
            ax.plot(*p, marker='o', ms=6 if zoom else 4, mfc='white', mec='#111111', zorder=21)
            label(p + sgn * u * (16 / mpp), e['id'], size=fs * 1.15, fontweight='bold', zorder=31)
            dt = e['displaced_threshold']
            if dt:
                q = T(np.array([[dt['x'], dt['z']]]))[0]; n = np.array([-u[1], u[0]]) * (rw['width_m'] / 2 / mpp)
                ax.plot([q[0] - n[0], q[0] + n[0]], [q[1] - n[1], q[1] + n[1]], color='white', lw=lw * 2.2, solid_capstyle='butt', zorder=9)
                ax.plot([q[0] - n[0], q[0] + n[0]], [q[1] - n[1], q[1] + n[1]], color='#111111', lw=lw * 0.6, solid_capstyle='butt', zorder=9)
                label(q + n * 1.0 + np.array([0, 0]) + np.array([-u[1], u[0]]) * (14 / mpp), 'displaced thr %s (%d ft, NASR)' % (e['id'], dt['len_ft_nasr']), size=fs * 0.95, zorder=31)
    # taxilanes, taxiways
    for w in D['taxilanes']:
        P = T(np.array(w['pts'])); ax.plot(P[:, 0], P[:, 1], color=INK2, lw=lw * 0.7, zorder=10)
    placed = {}
    for w in sorted(D['taxiways'], key=lambda w: -w['len_m']):
        P = T(np.array(w['pts'])); ref = w['ref']
        if w['status'] != 'open':
            ax.plot(P[:, 0], P[:, 1], color=INK3, lw=lw * 1.0, ls=(0, (1, 1.5)), zorder=11)
            if zoom:
                m = P[len(P) // 2]; label(m, w['status'], size=fs * 0.8, col=INK3)
            continue
        col = TWY_COL.get(ref, INK2)
        ax.plot(P[:, 0], P[:, 1], color='#111111', lw=lw * 2.4 if ref else lw * 1.4, alpha=0.55, solid_capstyle='round', zorder=11)
        ax.plot(P[:, 0], P[:, 1], color=col, lw=lw * 1.6 if ref else lw * 0.8, ls=(0, (5, 2)) if ref in ('A1', 'Z1') else '-',
                solid_capstyle='round', zorder=12)
        if ref:
            L = LineString(w['pts']); m = L.interpolate(0.5, normalized=True); p = T(np.array([[m.x, m.y]]))[0]
            sep = (45 if zoom else 140) / mpp
            if all(np.hypot(*(p - q)) > sep for q in placed.get(ref, [])) and inside(p, 10):
                ax.text(p[0], p[1], ref, fontsize=fs * 1.1, color=INK, fontweight='bold', ha='center', va='center', zorder=32,
                        bbox=dict(boxstyle='round,pad=0.18', fc='#1a1a19', ec=col, lw=1.4, alpha=0.9))
                placed.setdefault(ref, []).append(p)
    # holds
    for h in D['holds']:
        if h['bar']:
            b = h['bar']; d = np.array(b['dir']); half = 6.0
            P = T(np.array([[b['x'] - d[0] * half, b['z'] - d[1] * half], [b['x'] + d[0] * half, b['z'] + d[1] * half]]))
            ax.plot(P[:, 0], P[:, 1], color='#111111', lw=lw * 3.4, solid_capstyle='butt', zorder=14)
            ax.plot(P[:, 0], P[:, 1], color='white', lw=lw * 2.0, solid_capstyle='butt', zorder=15)
        else:
            p = T(np.array([[h['x'], h['z']]]))[0]
            ax.plot(*p, marker='o', ms=7, mfc='none', mec='white', mew=1.6, zorder=15)
        if zoom:
            p = T(np.array([[h['x'], h['z']]]))[0]
            label(p + np.array([0, 9 / mpp]), '%d ft' % h['cl_dist_ft'], size=fs * 0.75, col=INK2)
    # hot spots
    for hs in D['hotspots']:
        if not hs['ring']: continue
        x, y = _poly_xy(T, hs['ring']); ax.plot(x, y, color=HS_COL, lw=lw * 1.4, ls=(0, (6, 3)), zorder=16)
        P = T(np.array(hs['ring'])); top = P[np.argmin(P[:, 1])]
        label(top + np.array([0, -10 / mpp * (1 if zoom else 2)]), hs['hs'], size=fs * 1.05, col='#f2b27a', fontweight='bold')
    # markers
    for m in D['markers']:
        p = T(np.array([[m['x'], m['z']]]))[0]
        if m['kind'] == 'windsock':
            ax.plot(*p, marker='*', ms=12 if zoom else 9, mfc=INK, mec='#111111', zorder=20)
        else:
            ax.add_patch(plt.Circle(p, m['diameter_m'] / 2 / mpp, fill=False, ec=INK, lw=lw, ls=(0, (3, 2)), zorder=19))
            label(p + np.array([0, (m['diameter_m'] / 2 + 9) / mpp]), 'segmented circle + windsock', size=fs * 0.85)
    # parking
    for s in D['parking']:
        p = T(np.array([[s['x'], s['z']]]))[0]
        if not inside(p): continue
        obs = s['src'] == 'obs'; col = OBS_COL if obs else INF_COL
        mk = KIND_MARK[s['kind']]; ms = (8 if zoom else 5) * (1.15 if mk == '^' else 1.0)
        if mk == '^' and s['heading'] is not None:
            mk = (3, 0, _disp_angle(T, s['x'], s['z'], s['heading']) - 90)
        ax.plot(*p, marker=mk, ms=ms, mfc=col if obs else 'none', mec=col if not obs else '#111111', mew=1.8 if not obs else 0.8, zorder=24)
        if zoom and s.get('size') and s['size'].get('max_span_m'):
            span = s['size']['max_span_m']
            if s['heading'] is not None:
                h = math.radians(s['heading']); v = np.array([math.cos(h), math.sin(h)]) * span / 2    # across the heading
                Q = T(np.array([[s['x'] - v[0], s['z'] - v[1]], [s['x'] + v[0], s['z'] + v[1]]]))
                ax.plot(Q[:, 0], Q[:, 1], color=col, lw=0.9, alpha=0.8, zorder=23)
            else:
                ax.add_patch(plt.Circle(p, span / 2 / mpp, fill=False, ec=col, lw=0.7, alpha=0.7, ls=(0, (2, 2)), zorder=23))
    # terminal / administration (kind from AL-5015, inf)
    for b in D['buildings']:
        if b['kind'] == 'terminal_admin':
            c = Polygon(b['ring']).centroid; p = T(np.array([[c.x, c.y]]))[0]
            label(p + np.array([0, 16 / mpp]), 'terminal / admin (AL-5015, inf)', size=fs * 0.85)
    # cross-check annotations: features missing from the data set
    for (ax_, az_), txt in ANNOT:
        p = T(np.array([[ax_, az_]]))[0]
        if not inside(p): continue
        ax.add_patch(plt.Circle(p, 6 / mpp, fill=False, ec='white', lw=1.4, ls=(0, (2, 1.5)), zorder=26))
        if zoom: label(p + np.array([0, -12 / mpp]), txt, size=fs * 0.8, style='italic')
    # not placed: the unmapped helicopter pads (not_placed[...] text gives x -60, z 200)
    for npl in D['not_placed']:
        if npl['what'].startswith('paved helicopter area'):
            p = T(np.array([[-60.0, 200.0]]))[0]
            label(p, 'unmapped helicopter pads\n(NAIP; not in OSM, not placed)', size=fs * 0.85, col=INF_COL)


def legend_handles(extra=()):
    H = [Line2D([], [], color=TWY_COL[k], lw=3, ls=(0, (5, 2)) if k in ('A1', 'Z1') else '-', label='taxiway %s' % k)
         for k in ('A', 'A1', 'B', 'C', 'D', 'E', 'F', 'Z', 'Z1')]
    H += [Line2D([], [], color=INK2, lw=1.2, label='taxiway (no ref) / taxilane'),
          Line2D([], [], color=INK3, lw=1.5, ls=(0, (1, 1.5)), label='taxiway abandoned / disused'),
          Line2D([], [], color='white', lw=1.5, label='runway (NASR rectangle), end'),
          Line2D([], [], color='white', lw=4, label='displaced threshold (NASR)'),
          Line2D([], [], color='white', lw=3, label='hold bar (NAIP); o = OSM node only'),
          Line2D([], [], color=HS_COL, lw=2, ls=(0, (6, 3)), label='hot spot (AL-5015, inferred)'),
          Line2D([], [], color=INK, lw=1.2, label='T-hangar row / box hangar (dashed)'),
          Line2D([], [], color=INK2, lw=1.2, ls=(0, (1, 2)), label='apron (OSM)'),
          Line2D([], [], color='none', marker='^', mfc=OBS_COL, mec='#111111', ms=9, label='parking obs: filled; ^ = tie-down'),
          Line2D([], [], color='none', marker='o', mfc='none', mec=INF_COL, mew=1.8, ms=9, label='parking inf: hollow'),
          Line2D([], [], color='none', marker='s', mfc='none', mec=INK2, mew=1.2, ms=8, label='o ramp, \u25a1 hangar apron, \u25c7 helipad'),
          Line2D([], [], color='none', marker='o', mfc='none', mec='white', mew=1.4, ms=11, ls='none', label='missing from the data (dashed ring)')]
    return H + list(extra)


def legend_layout(W, n):
    """legend below the map (never over the data): font size, columns, block height (px)"""
    fs = max(8.0, min(11.0, W / 170.0))
    col_w = 36 * 0.56 * fs * 100 / 72 + 52
    ncol = max(1, int(0.98 * W // col_w)); rows = -(-n // ncol)
    return fs, ncol, int(rows * fs * 100 / 72 * 1.55 + 16)


def legend_below(fig, foot, cred_h, handles, W):
    fs, ncol, h = legend_layout(W, len(handles))
    fig.legend(handles=handles, loc='upper left', bbox_to_anchor=(0.004, (foot - 4) / fig.bbox.height), ncol=ncol, fontsize=fs,
               frameon=False, labelcolor=INK, handlelength=2.6, columnspacing=1.6, borderaxespad=0.2)


def figure(W, H, foot):
    fig = plt.figure(figsize=(W / 100, (H + foot) / 100), dpi=100, facecolor='#1a1a19')
    ax = fig.add_axes([0, foot / (H + foot), 1, H / (H + foot)]); ax.set_axis_off()
    return fig, ax


def footer_layout(W, credit, extra):
    """credit + note wrapped to the image width at a font size that stays legible in the downscaled docs copies
    (>= 8.5 pt = 11.8 px at 100 dpi). Returns (credit lines, note lines, font size pt, footer height px)."""
    import textwrap
    fsz = max(8.5, W / 220.0)
    cpl = max(40, int(0.97 * W / (fsz * 100 / 72 * 0.56)))
    parts = [p_.strip() for p_ in credit.split('.  ')]
    lc = []
    for k, p_ in enumerate(parts):
        lc += textwrap.wrap(p_ + ('.' if k < len(parts) - 1 else ''), cpl)
    le = textwrap.wrap(extra, cpl) if extra else []
    return lc, le, fsz, int((len(lc) + len(le)) * fsz * 100 / 72 * 1.45 + 14)


def footer(fig, W, foot, layout):
    lc, le, fsz, _ = layout; step = fsz * 100 / 72 * 1.45
    for i, t in enumerate(lc + le):
        fig.text(0.006, (foot - 7 - step * (i + 0.5)) / fig.bbox.height, t, color=INK if i < len(lc) else INK2, fontsize=fsz, ha='left', va='center')


def scalebar(ax, view, mpp, fs, length_m):
    x0, x1, y0, y1 = view; L = length_m / mpp
    px = x1 - (x1 - x0) * 0.03 - L; py = y1 - (y1 - y0) * 0.035
    ax.plot([px, px + L], [py, py], color='white', lw=4, solid_capstyle='butt', zorder=40, path_effects=[pe.withStroke(linewidth=6, foreground='#111111')])
    ax.text(px + L / 2, py - (y1 - y0) * 0.012, '%d m' % length_m, color=INK, fontsize=fs, ha='center', va='bottom', path_effects=HALO, zorder=40)


def north(ax, view, fs, ang=90.0):
    """north arrow; ang = display direction (deg ccw from +x) of true north"""
    x0, x1, y0, y1 = view; L = min(x1 - x0, y1 - y0) * 0.03; cx = x1 - L * 2.2; cy = y0 + L * 2.2
    dx, dy = math.cos(math.radians(ang)) * L, -math.sin(math.radians(ang)) * L
    ax.annotate('', xy=(cx + dx, cy + dy), xytext=(cx - dx, cy - dy), arrowprops=dict(arrowstyle='-|>', color='white', lw=2), zorder=40)
    ax.text(cx + dx * 1.5, cy + dy * 1.5, 'N', color=INK, fontsize=fs * 1.1, ha='center', va='center', path_effects=HALO, zorder=40, fontweight='bold')


# ============================================================================================ NAIP overlays
def naip_overlays(D, N, M):
    paths = []
    jobs = [('overlay_naip', OVERVIEW, 0.6, 'HWD data set over USDA NAIP 2024 (0.6 m) - whole airfield', False)]
    jobs += [('overlay_naip_' + k, v[0], 0.3, v[1], True) for k, v in AREAS.items()]
    for name, win, res, title, zoom in jobs:
        img = N.window(win, res)
        img = (img.astype(np.float32) * (0.62 if not zoom else 0.72)).astype(np.uint8)       # recede the imagery
        Hh, Ww = img.shape[:2]
        lay = footer_layout(Ww, CREDIT_NAIP, 'NAIP pixels: %s (bilinear to a world-aligned grid; imagery darkened to 62-72 %%)' % os.path.relpath(N.src, HWD))
        hand = legend_handles(); foot = lay[3] + legend_layout(Ww, len(hand))[2]
        fig, ax = figure(Ww, Hh, foot)
        x0, x1, z0, z1 = win
        ax.imshow(img, extent=(x0, x1, z1, z0), interpolation='nearest' if zoom else 'antialiased', zorder=0)
        ax.set_xlim(x0, x1); ax.set_ylim(z1, z0)
        fs = max(8.0, Ww / 190.0) if zoom else max(8.0, Ww / 260.0)
        draw_data(ax, D, lambda P: np.asarray(P, float), 1.0, fs, zoom, (x0, x1, z0, z1))
        legend_below(fig, foot, lay[3], hand, Ww)
        ax.text(x0 + (x1 - x0) * 0.008, z0 + (z1 - z0) * 0.01, title + '\nnorth up; world frame x east / z south (m from the NASR ARP); %s m/px' % res,
                color=INK, fontsize=fs * 1.15, ha='left', va='top', zorder=45,
                bbox=dict(boxstyle='round,pad=0.4', fc='#1a1a19', ec=INK3, alpha=0.88))
        scalebar(ax, (x0, x1, z0, z1), 1.0, fs, 100 if (x1 - x0) > 400 else 50)
        north(ax, (x0, x1, z0, z1), fs)
        footer(fig, Ww, lay[3], lay)
        p = os.path.join(OUT, name + '.png'); fig.savefig(p, dpi=100, facecolor=fig.get_facecolor()); plt.close(fig)
        paths.append(p); print('wrote', os.path.relpath(p, HWD), '%dx%d' % (Ww, Hh + foot))
    return paths


# ============================================================================================ AL-5015
def al_raster(dpi=al5015.DPI):
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(['pdftoppm', '-r', str(dpi), '-png', al5015.PDF, os.path.join(td, 'al')], check=True)
        from PIL import Image
        return np.asarray(Image.open(os.path.join(td, 'al-1.png')).convert('RGB')).astype(int)


def bar_ends(im):
    """the two runway bars of AL-5015 and their ends (px). Bars: the two largest components of black (max channel < 90)
    after a 9x9 opening (removes text and thin lines; as G1's xcheck_osm_faa.runway_bars). Ends: walk along each bar's
    principal axis from its centre; a cross-section counts as bar when >= 90 % of 21 samples across +-0.4 bar width are
    black OR hot-spot brown (the overprinted rings do not end the bar); the walk stops after a 16 px gap (the white dot
    near the 28L end is about 12 px across at 400 dpi; text beyond the ends never fills 90 % of a cross-section)."""
    blk = im.max(2) < 90
    brown = (im[..., 0] - im[..., 2] > 60) & (im[..., 0] > im[..., 1] + 25) & (im[..., 1] > im[..., 2] + 20)   # al5015.py
    ink = blk | brown
    op = nd.binary_opening(blk, structure=np.ones((9, 9), bool))
    lab, n = nd.label(op); sizes = nd.sum(op, lab, range(1, n + 1))
    bars = []
    for i in np.argsort(-sizes)[:2]:
        ys, xs = np.nonzero(lab == i + 1); P = np.c_[xs, ys].astype(float); m = P.mean(0)
        _, _, Vt = np.linalg.svd(P - m, full_matrices=False); d = Vt[0] if Vt[0][1] > 0 else -Vt[0]; nr = np.array([-d[1], d[0]])
        wid = float(np.percentile((P - m) @ nr, 99) - np.percentile((P - m) @ nr, 1))
        ss = np.linspace(-0.4 * wid, 0.4 * wid, 21); ext = {}
        for sgn in (-1, 1):
            t = 0.0; last = 0.0
            while t - last <= 16.0:
                t += 0.5; c = m + sgn * d * t; Q = c[None] + ss[:, None] * nr[None]
                xi = np.round(Q[:, 0]).astype(int); yi = np.round(Q[:, 1]).astype(int)
                if xi.min() < 0 or yi.min() < 0 or xi.max() >= im.shape[1] or yi.max() >= im.shape[0]: break
                if ink[yi, xi].mean() >= 0.9: last = t
            ext[sgn] = m + sgn * d * last
        bars.append({'top': ext[-1], 'bottom': ext[1], 'len_px': float(np.hypot(*(ext[1] - ext[-1]))), 'wid_px': wid, 'axis': d})
    bars.sort(key=lambda b: -b['len_px'])          # long wide bar = 10R/28L; east is up on the page (28 ends at the top)
    px = {'28L': bars[0]['top'], '10R': bars[0]['bottom'], '28R': bars[1]['top'], '10L': bars[1]['bottom']}
    return px, bars


def similarity(px):
    names = ['28L', '10R', '28R', '10L']
    u = np.array([px[k][0] + 1j * px[k][1] for k in names]); w = np.array([complex(*F.end_world(k)) for k in names])
    A = np.c_[u, np.ones(4)]; c, *_ = np.linalg.lstsq(A, w, rcond=None)
    res = w - A @ c
    # affine for comparison
    P = np.array([px[k] for k in names]); Q = np.array([F.end_world(k) for k in names]); Aa = np.c_[P, np.ones(4)]
    Ma, *_ = np.linalg.lstsq(Aa, Q, rcond=None); ra = np.hypot(*(Q - Aa @ Ma).T)
    sv = np.linalg.svd(Ma[:2], compute_uv=False)
    out = {'names': names, 'a': c[0], 'b': c[1], 'scale_m_per_px': abs(c[0]), 'rot_deg': math.degrees(np.angle(c[0])),
           'resid_m': {k: abs(v) for k, v in zip(names, res)}}
    al = {}
    for rw in (('10L', '28R'), ('10R', '28L')):
        ax_ = np.array(F.end_world(rw[1])) - np.array(F.end_world(rw[0])); ax_ /= np.hypot(*ax_); nr = np.array([-ax_[1], ax_[0]])
        for k in rw:
            v = np.array([res[names.index(k)].real, res[names.index(k)].imag]); al[k] = {'along_m': float(v @ ax_), 'across_m': float(v @ nr)}
    out['resid_along_across'] = al
    out['affine'] = {'resid_m': {k: float(v) for k, v in zip(names, ra)}, 'singular_values_m_per_px': [float(s) for s in sv]}
    return out


def to_px_fn(S):
    a, b = S['a'], S['b']
    def T(P):
        P = np.asarray(P, float); u = ((P[:, 0] + 1j * P[:, 1]) - b) / a
        return np.c_[u.real, u.imag]
    return T


def to_world_fn(S):
    a, b = S['a'], S['b']
    def W(P):
        P = np.asarray(P, float); w = a * (P[:, 0] + 1j * P[:, 1]) + b
        return np.c_[w.real, w.imag]
    return W


def al_measure(D, im, S, bars_px):
    """diagram vs data numbers (section 2 of the header)"""
    T = to_px_fn(S); Wf = to_world_fn(S); mpp = S['scale_m_per_px']
    out = {}
    grey = (np.abs(im[..., 0] - im[..., 2]) < 6) & (im[..., 0] >= 195) & (im[..., 0] <= 215)
    blk = im.max(2) < 90
    bar = np.zeros(im.shape[:2], bool)
    for k0, k1 in (('28L', '10R'), ('28R', '10L')):
        a_, b_ = bars_px[k0], bars_px[k1]; d = (b_ - a_) / np.hypot(*(b_ - a_)); nr = np.array([-d[1], d[0]])
        yy, xx = np.mgrid[0:im.shape[0], 0:im.shape[1]]
        t = (xx - a_[0]) * d[0] + (yy - a_[1]) * d[1]; s = (xx - a_[0]) * nr[0] + (yy - a_[1]) * nr[1]
        L = np.hypot(*(b_ - a_)); wd = 34 if k0 == '28L' else 18
        bar |= (t >= -2) & (t <= L + 2) & (np.abs(s) <= wd)
    pave = nd.binary_closing(grey | (blk & bar), structure=np.ones((5, 5), bool))
    dist_px = nd.distance_transform_edt(~pave)
    # 2a: taxiway centrelines vs diagram pavement
    per = {}
    for w in D['taxiways']:
        if w['status'] != 'open': continue
        L = LineString(w['pts']); n = max(2, int(L.length / 5.0) + 1)
        Pw = np.array([L.interpolate(i / (n - 1), normalized=True).coords[0] for i in range(n)]); Pp = T(Pw)
        xi = np.clip(np.round(Pp[:, 0]).astype(int), 0, im.shape[1] - 1); yi = np.clip(np.round(Pp[:, 1]).astype(int), 0, im.shape[0] - 1)
        dm = dist_px[yi, xi] * mpp
        k = w['ref'] or '(no ref)'
        per.setdefault(k, {'d': [], 'worst': []})['d'].extend(dm.tolist())
        j = int(np.argmax(dm)); per[k]['worst'].append((float(dm[j]), w['id'], [r(Pw[j][0], 1), r(Pw[j][1], 1)]))
    out['taxiway_to_diagram_pavement_m'] = {k: {'n': len(v['d']), 'on_pavement_frac': r(np.mean(np.array(v['d']) < 0.5 * mpp + 1e-9), 3),
                                                 'p50': r(np.percentile(v['d'], 50), 1), 'p90': r(np.percentile(v['d'], 90), 1), 'max': r(max(v['d']), 1),
                                                 'worst': sorted(v['worst'], reverse=True)[:3]} for k, v in sorted(per.items())}
    # 2b: diagram pavement far from our paved features
    paved = [Polygon(a['ring']) for a in D['aprons']] + [Polygon(rw['outline']['ring']) for rw in D['runways']]
    paved += [LineString(w['pts']).buffer(12.0) for w in D['taxiways']] + [LineString(w['pts']).buffer(8.0) for w in D['taxilanes']]
    paved += [Polygon(h['ring']).buffer(3.0) for h in D['helipads']]
    U = prep(unary_union(paved).buffer(25.0))
    gy, gx = np.nonzero(grey[::4, ::4]); gy = gy * 4; gx = gx * 4
    Gw = Wf(np.c_[gx, gy]); far = np.array([not U.contains(Point(p)) for p in Gw])
    farmask = np.zeros(im.shape[:2], bool); farmask[gy[far], gx[far]] = True
    farmask = nd.binary_dilation(farmask, structure=np.ones((5, 5), bool)) & grey
    lab, n = nd.label(farmask, structure=np.ones((3, 3)))
    comps = []
    for i, sl in enumerate(nd.find_objects(lab)):
        m = lab[sl] == i + 1; area = float(m.sum()) * mpp * mpp
        if area < 400: continue
        yy, xx = np.nonzero(m); c = Wf(np.array([[xx.mean() + sl[1].start, yy.mean() + sl[0].start]]))[0]
        comps.append({'centre_world': [r(c[0], 0), r(c[1], 0)], 'centre_px': [r(xx.mean() + sl[1].start, 0), r(yy.mean() + sl[0].start, 0)], 'area_m2': r(area, 0)})
    out['diagram_pavement_not_in_data'] = sorted(comps, key=lambda c: -c['area_m2'])
    # 2c: hangars vs diagram building blocks (black, opened 7x7, not the runway bars)
    bld = nd.binary_opening(blk & ~nd.binary_dilation(bar, iterations=3), structure=np.ones((7, 7), bool))
    dist_b = nd.distance_transform_edt(~bld)
    hg = []
    for h in D['hangars'] + [b for b in D['buildings'] if b.get('ring')]:
        pg = Polygon(h['ring']); c = pg.centroid; pc = T(np.array([[c.x, c.y]]))[0]
        minx, miny, maxx, maxy = pg.bounds
        gxs, gzs = np.meshgrid(np.arange(minx, maxx, 2.0), np.arange(miny, maxy, 2.0))
        inn = [Point(a_, b_) for a_, b_ in zip(gxs.ravel(), gzs.ravel()) if pg.contains(Point(a_, b_))]
        Pin = T(np.array([[p.x, p.y] for p in inn])) if inn else np.zeros((0, 2))
        xi = np.clip(np.round(Pin[:, 0]).astype(int), 0, im.shape[1] - 1); yi = np.clip(np.round(Pin[:, 1]).astype(int), 0, im.shape[0] - 1)
        cov = float(bld[yi, xi].mean()) if len(Pin) else None
        dc = float(dist_b[int(round(pc[1])), int(round(pc[0]))]) * mpp if 0 <= pc[0] < im.shape[1] and 0 <= pc[1] < im.shape[0] else None
        hg.append({'id': h['id'], 'name': h.get('name') or h.get('letter'), 'kind': h['kind'], 'area_m2': r(pg.area, 0),
                   'covered_by_diagram_block': r(cov, 2), 'centroid_to_block_m': r(dc, 1)})
    out['osm_footprints_vs_diagram_blocks'] = hg
    lab, n = nd.label(bld)
    allfp = [Polygon(h['ring']) for h in D['hangars']] + [Polygon(b['ring']) for b in D['buildings'] if b.get('ring')]
    blocks = []
    for i, sl in enumerate(nd.find_objects(lab)):
        m = lab[sl] == i + 1; yy, xx = np.nonzero(m)
        c = Wf(np.array([[xx.mean() + sl[1].start, yy.mean() + sl[0].start]]))[0]
        d = min(fp.distance(Point(c)) for fp in allfp)
        blocks.append({'centre_world': [r(c[0], 0), r(c[1], 0)], 'area_m2': r(m.sum() * mpp * mpp, 0), 'dist_to_osm_footprint_m': r(d, 1)})
    core = unary_union(paved)
    near_field = [b for b in blocks if core.distance(Point(*b['centre_world'])) < 150 and b['area_m2'] >= 100]
    out['diagram_blocks'] = {'n': len(blocks), 'n_on_field_ge_100m2': len(near_field),
                             'note': 'black blocks of the diagram (opened 7x7, runway bars removed) within 150 m of our paved features and >= 100 m2 (the frame ticks and text are outside or smaller)',
                             'not_near_osm_15m': [b for b in near_field if b['dist_to_osm_footprint_m'] > 15]}
    # TWR beacon symbol (star with a white circle: the black component near the TWR label, outside the TWR word box,
    # whose filled area exceeds its ink by > 15 %) vs the OSM tower footprint
    twr = [l for l in D['al5015_labels'] if l['text'] == 'TWR'][0]; c0 = np.array(twr['pdf_pt']) * al5015.K
    tb = [np.array(w[1:]) * al5015.K for w in al5015.words() if w[0] == 'TWR'][0]          # the TWR word box (px)
    y0_, x0_ = int(c0[1] - 80), int(c0[0] - 80); win = im[y0_:y0_ + 160, x0_:x0_ + 160].max(2) < 110
    lab2, n2 = nd.label(win, structure=np.ones((3, 3))); star = None
    for i, sl in enumerate(nd.find_objects(lab2)):
        m = lab2[sl] == i + 1; h_, w_ = m.shape
        bx0, by0 = sl[1].start + x0_, sl[0].start + y0_
        in_word = bx0 + w_ > tb[0] and bx0 < tb[2] and by0 + h_ > tb[1] and by0 < tb[3]
        if 18 <= h_ <= 40 and 18 <= w_ <= 40 and not in_word and nd.binary_fill_holes(m).sum() > 1.15 * m.sum():
            yy, xx = np.nonzero(m); star = (xx.mean() + sl[1].start + x0_, yy.mean() + sl[0].start + y0_)
    if star is not None:
        sw = Wf(np.array([star]))[0]; tw = [b for b in D['buildings'] if b['kind'] == 'control_tower'][0]
        out['twr_beacon_symbol'] = {'px': [r(star[0], 1), r(star[1], 1)], 'world': [r(sw[0], 1), r(sw[1], 1)],
                                    'dist_to_osm_tower_m': r(Polygon(tw['ring']).distance(Point(*sw)), 1),
                                    'dist_to_osm_tower_centroid_m': r(Polygon(tw['ring']).centroid.distance(Point(*sw)), 1)}
    # 2d: hot spots: the diagram ring centres (al5015.hotspots) through the similarity vs the data. NOTE (Phase 1 review):
    #     the data's hot spots are the same ring centres through the affine, so this only measures the difference between
    #     the two transforms, not the hot-spot placement itself
    Wd = al5015.words(); Mx, _ = al5015.affine(); hs = al5015.hotspots(Wd, Mx)
    rows = []
    for g in hs:
        cw = Wf(np.array([g['centre_px']]))[0]
        dd = [x for x in D['hotspots'] if x['hs'] == g['hs']]
        best = min(dd, key=lambda x: math.hypot(x['centre'][0] - cw[0], x['centre'][1] - cw[1]))
        rows.append({'hs': g['hs'], 'centre_px': g['centre_px'], 'centre_similarity': [r(cw[0], 1), r(cw[1], 1)],
                     'centre_data': best['centre'], 'data_minus_similarity_m': r(math.hypot(best['centre'][0] - cw[0], best['centre'][1] - cw[1]), 1),
                     'axes_m_similarity': [r(a * mpp, 1) for a in g['axes_px']]})
    out['hotspots'] = {'note': 'the data hot spots are the same al5015.hotspots ring centres mapped by the 4-point affine; this compares the affine with the similarity fit (a transform consistency check, not an independent placement check)', 'rows': rows}
    # 2e: HS 5 hold symbols: black pixels inside each HS 5 ring, but not grey, = the holding-position symbol
    hs5 = []
    for g in [g for g in hs if g['hs'] == 'HS 5']:
        c = np.array(g['centre_px']); a0 = max(g['axes_px'])
        y0, y1, x0, x1 = int(c[1] - a0), int(c[1] + a0), int(c[0] - a0), int(c[0] + a0)
        sub = blk[y0:y1, x0:x1].copy(); yy, xx = np.mgrid[y0:y1, x0:x1]
        sub &= np.hypot(xx - c[0], yy - c[1]) < min(g['axes_px']) * 0.9
        yy, xx = np.nonzero(sub)
        if len(xx) < 20: continue
        cw = Wf(np.array([[xx.mean() + x0, yy.mean() + y0]]))[0]
        near = min(D['holds'], key=lambda h: math.hypot(h['x'] - cw[0], h['z'] - cw[1]))
        al, ac = F.rwy_along_across('10R', *cw); alh, ach = F.rwy_along_across('10R', near['x'], near['z'])
        hs5.append({'symbol_centre_world': [r(cw[0], 1), r(cw[1], 1)], 'symbol_cl_dist_ft': round(abs(ac) / FT), 'nearest_hold': near['id'],
                    'hold_twy': near.get('twy_ref'), 'hold_cl_dist_ft': near['cl_dist_ft'], 'dist_m': r(math.hypot(near['x'] - cw[0], near['z'] - cw[1]), 1),
                    'symbol_minus_hold_along_rwy_m': r(al - alh, 1), 'symbol_minus_hold_from_cl_m': r(abs(ac) - abs(ach), 1)})
    out['hs5_hold_symbols'] = hs5
    # 2f: the TWR beacon star / labels: our al5015_labels (affine) through the inverse similarity vs their pdf points
    lab_dev = []
    for l in D['al5015_labels']:
        p = T(np.array([[l['x'], l['z']]]))[0]; q = np.array(l['pdf_pt']) * al5015.K
        lab_dev.append({'text': l['text'], 'data_anchor_vs_text_m': r(np.hypot(*(p - q)) * mpp, 1)})
    out['al5015_label_anchors'] = lab_dev
    return out


def al_overlay(D, im, S, px, bars, M):
    T = to_px_fn(S); mpp = S['scale_m_per_px']
    Hh, Ww = im.shape[:2]
    lay = footer_layout(Ww, CREDIT_AL, 'Diagram faded and darkened; our data drawn through the inverse of the similarity transform.')
    hand = legend_handles([Line2D([], [], color='none', marker='+', mec='#00e0ff', ms=14, mew=2, label='AL-5015 bar end (registration)')])
    foot = lay[3] + legend_layout(Ww, len(hand))[2]
    fig, ax = figure(Ww, Hh, foot)
    base = (255 - (255 - im.astype(np.float32)) * 0.55)                           # fade the diagram ...
    base = (base * 0.38).astype(np.uint8)                                         # ... then recede it as a dark surface
    ax.imshow(base, extent=(0, Ww, Hh, 0), interpolation='antialiased', zorder=0)
    ax.set_xlim(0, Ww); ax.set_ylim(Hh, 0)
    fs = 13.0
    draw_data(ax, D, T, mpp, fs, False, (0, Ww, 0, Hh))
    for k, p in px.items():
        ax.plot(*p, marker='+', ms=26, mew=2.2, color='#00e0ff', zorder=33)
    # north: world north (0, -1) in px
    a = T(np.array([[0.0, 0.0], [0.0, -100.0]])); d = a[1] - a[0]
    north(ax, (0, Ww, 0, Hh), fs, math.degrees(math.atan2(-d[1], d[0])))
    scalebar(ax, (0, Ww, 0, Hh), mpp, fs, 200)
    rs = S['resid_along_across']
    txt = ('HWD data set in the frame of FAA AL-5015 (cycle 2611), rasterised at %d dpi\n'
           'similarity fit (4 parameters, no shear) of the 4 runway-bar ends (cyan +) to the NASR ends:\n'
           'scale %.4f m/px, rotation %.2f deg; residuals (along / across the runway, m):\n  %s\n'
           'the 6-parameter affine gives %s m (scales %.4f / %.4f m/px)\n'
           'chart legend: "Positional accuracy within +-600 feet unless otherwise noted"' % (
               al5015.DPI, mpp, S['rot_deg'],
               ',  '.join('%s %+.1f / %+.1f' % (k, rs[k]['along_m'], rs[k]['across_m']) for k in S['names']),
               ' '.join('%s %.1f' % (k, v) for k, v in S['affine']['resid_m'].items()), *S['affine']['singular_values_m_per_px']))
    ax.text(30, Hh - 30, txt, color=INK, fontsize=fs * 0.95, ha='left', va='bottom', zorder=45, family='DejaVu Sans',
            bbox=dict(boxstyle='round,pad=0.5', fc='#1a1a19', ec=INK3, alpha=0.9))
    legend_below(fig, foot, lay[3], hand, Ww)
    footer(fig, Ww, lay[3], lay)
    p = os.path.join(OUT, 'overlay_al5015.png'); fig.savefig(p, dpi=100, facecolor=fig.get_facecolor()); plt.close(fig)
    print('wrote', os.path.relpath(p, HWD), '%dx%d' % (Ww, Hh + foot))
    paths = [p]
    # crops of the overlay (west half, east half)
    from PIL import Image
    full = Image.open(p)
    for name, (wx0, wx1, wz0, wz1) in (('west', (-760, 120, -800, -150)), ('east', (150, 860, -400, 640))):
        C = T(np.array([[wx0, wz0], [wx1, wz0], [wx0, wz1], [wx1, wz1]]))
        x0, y0 = np.floor(C.min(0)).astype(int); x1, y1 = np.ceil(C.max(0)).astype(int)
        x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(Ww, x1), min(Hh, y1)
        crop = full.crop((x0, y0, x1, y1))
        out = pil_footer(crop, CREDIT_AL, 'Crop of overlay_al5015.png (diagram faded; our data through the inverse similarity); the legend is under overlay_al5015.')
        q = os.path.join(OUT, 'overlay_al5015_%s.png' % name); out.save(q); paths.append(q)
        print('wrote', os.path.relpath(q, HWD), out.size)
    return paths


def pil_footer(img, credit, extra, px=15):
    """append a footer with the credit (wrapped to the image width, DejaVu Sans px pixels) under a PIL image"""
    import textwrap
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype('DejaVuSans.ttf', px)
    cw = font.getlength('abcdefghijklmnopqrstuvwxyz ABCDEFGHIJ') / 37.0
    lines = []
    for part in [credit, extra]:
        lines += textwrap.wrap(part, max(30, int((img.width - 16) / cw)))
    h = 10 + len(lines) * (px + 5)
    out = Image.new('RGB', (img.width, img.height + h), '#1a1a19'); out.paste(img, (0, 0))
    d = ImageDraw.Draw(out)
    for i, t in enumerate(lines):
        d.text((8, img.height + 6 + i * (px + 5)), t, fill=INK if i < len(lines) - len(textwrap.wrap(extra, max(30, int((img.width - 16) / cw)))) else INK2, font=font)
    return out


# ============================================================================================ NAIP measurements
def naip_measure(D, N):
    out = {}
    win = OVERVIEW
    rwy = unary_union([Polygon(rw['outline']['ring']) for rw in D['runways']]).buffer(40.0); rwy_p = prep(rwy)
    apr = prep(unary_union([Polygon(a['ring']) for a in D['aprons']]))
    # (a) taxiway centreline vs pavement centre
    lat = np.arange(-30.0, 30.01, 0.3)
    rows = []
    for w in D['taxiways']:
        if w['status'] != 'open': continue
        L = LineString(w['pts']); n = int(L.length / 6.0)
        offs = []; wids = []; where = []
        for i in range(1, n):
            s = i * 6.0; p = np.array(L.interpolate(s).coords[0]); q = np.array(L.interpolate(min(L.length, s + 0.5)).coords[0]) - np.array(L.interpolate(max(0, s - 0.5)).coords[0])
            t = q / np.hypot(*q); nr = np.array([-t[1], t[0]])
            if rwy_p.contains(Point(p)) or apr.contains(Point(p)): continue
            X = p[0] + nr[0] * lat; Z = p[1] + nr[1] * lat
            rgb = N.sample(X, Z, win); mx = rgb.max(-1); mn = rgb.min(-1)
            sat = (mx - mn) / np.maximum(mx, 1); eg = rgb[:, 1] - (rgb[:, 0] + rgb[:, 2]) / 2
            pav = (sat < 0.16) & (eg < 8.0)
            pav = nd.binary_closing(np.r_[False, pav, False], structure=np.ones(6, bool))[1:-1]     # gaps < 1.5 m (paint)
            k0 = len(lat) // 2
            if not pav[k0]:
                cand = [k for k in range(k0 - 5, k0 + 6) if 0 <= k < len(lat) and pav[k]]
                if not cand: continue
                k0 = min(cand, key=lambda k: abs(k - len(lat) // 2))
            a = k0
            while a > 0 and pav[a - 1]: a -= 1
            b = k0
            while b < len(lat) - 1 and pav[b + 1]: b += 1
            if a == 0 or b == len(lat) - 1: continue
            lo, hi = lat[a] - 0.15, lat[b] + 0.15; wd = hi - lo
            if not (6.0 <= wd <= 35.0): continue
            offs.append((lo + hi) / 2); wids.append(wd); where.append(p)
        if len(offs) >= 5:
            o = np.array(offs); big = np.abs(o) > 2.0
            rows.append({'id': w['id'], 'ref': w['ref'], 'len_m': w['len_m'], 'n': len(o), 'median_offset_m': r(np.median(o), 2),
                         'iqr_m': r(np.subtract(*np.percentile(o, [75, 25])), 2), 'median_width_m': r(np.median(wids), 1),
                         'n_abs_gt_2m': int(big.sum()), 'where_mid': [r(where[len(where) // 2][0], 0), r(where[len(where) // 2][1], 0)]})
    allo = [x['median_offset_m'] for x in rows]
    out['taxiway_vs_pavement_centre'] = {'note': 'positive offset = pavement centre lies to the right of the way direction; widths are grey-test pavement widths (shoulders of the same grey are included)',
                                         'n_ways': len(rows), 'per_way_median_abs_p50_p90_max': [r(np.percentile(np.abs(allo), q), 2) for q in (50, 90, 100)] if rows else None,
                                         'ways': sorted(rows, key=lambda x: -abs(x['median_offset_m']))}
    # (b) footprint vs roof edges, NAIP 2024 and 2022 (Phase 1 review: search +-8.1 m instead of +-3.9 m; an outline whose
    #     shift is the same in both flights is more likely an outline offset than roof lean, which changes with the flight)
    feats = [(h['id'], h.get('name') or h.get('letter'), h['kind'], h['ring']) for h in D['hangars']]
    feats += [(b['id'], b.get('name'), b['kind'], b['ring']) for b in D['buildings'] if b.get('ring')]
    res = roof_shift(N, feats, win)
    try:
        N22 = NaipGrid('2022'); r22 = {x['id']: x for x in roof_shift(N22, feats, win)}
    except Exception as e:  # noqa: BLE001
        r22 = {}; print('NAIP 2022 roof shifts not measured:', e)
    for x in res:
        y = r22.get(x['id'])
        if not y: continue
        x['shift_2022_m'] = y['shift_m']; x['at_search_edge_2022'] = y['at_search_edge']; x['gain_2022'] = y['gain']
        dd = math.hypot(x['shift_m'][0] - y['shift_m'][0], x['shift_m'][1] - y['shift_m'][1]); x['shift_diff_2024_2022_m'] = r(dd, 1)
        x['stable_offset'] = bool(x['shift_abs_m'] >= SHIFT_FLAG_M and dd <= SHIFT_STABLE_M and not x['at_search_edge'] and not y['at_search_edge'])
    sa = [x['shift_abs_m'] for x in res if not x['at_search_edge']]
    dx = [x['shift_m'][0] for x in res if not x['at_search_edge']]; dz = [x['shift_m'][1] for x in res if not x['at_search_edge']]
    out['footprint_vs_roof_edges'] = {'note': 'shift (dx east, dz south, m) of the OSM outline that maximises the mean NAIP gradient magnitude along it, searched +-%.1f m in 0.3 m steps; gain = that mean / the mean at zero shift; stable_offset = shift >= %.1f m in 2024 and the 2022 shift within %.1f m of it (an outline offset rather than roof lean: candidates for a manual correction or an OSM note; roof lean is not excluded)' % (SHIFT_MAX, SHIFT_FLAG_M, SHIFT_STABLE_M),
                                      'search_m': SHIFT_MAX, 'n': len(res), 'n_at_search_edge': sum(x['at_search_edge'] for x in res),
                                      'shift_abs_p50_p90_max': [r(np.percentile(sa, q), 1) for q in (50, 90, 100)] if sa else None,
                                      'n_over_2m': sum(1 for v in sa if v > 2.0),
                                      'median_shift_dx_dz': [r(np.median(dx), 2), r(np.median(dz), 2)] if sa else None,
                                      'stable_offset': [{k: x[k] for k in ('id', 'name', 'shift_m', 'shift_2022_m', 'gain')} for x in res if x.get('stable_offset')],
                                      'items': sorted(res, key=lambda x: -x['shift_abs_m'])}
    return _bars(out, D, N, win)


SHIFT_MAX = 8.1          # m, roof-edge search half-window (the review found outlines 3-6 m off; 0.3 m steps)
SHIFT_FLAG_M = 2.0       # m, a shift at least this large is reported as an outline offset candidate
SHIFT_STABLE_M = 1.0     # m, ... when the 2022 shift agrees with the 2024 one within this


def roof_shift(N, feats, win):
    res = []
    sh = np.round(np.arange(-27, 28) * 0.3, 2)           # -8.1 .. 8.1 m, includes 0
    for fid, name, kind, ring in feats:
        pg = Polygon(ring); minx, miny, maxx, maxy = pg.bounds
        wv = (minx - 12, maxx + 12, miny - 12, maxy + 12)
        xs = np.arange(wv[0], wv[1], 0.3); zs = np.arange(wv[2], wv[3], 0.3); X, Z = np.meshgrid(xs, zs)
        g = N.sample(X, Z, win).mean(-1)
        gm = np.hypot(nd.sobel(g, 1), nd.sobel(g, 0))
        ext = LineString(list(ring) + [ring[0]]); n = max(8, int(ext.length / 0.3))
        P = np.array([ext.interpolate(i / n, normalized=True).coords[0] for i in range(n)])
        best = (-1, 0, 0); s0 = None
        for dx in sh:
            for dz in sh:
                c = (P[:, 0] + dx - wv[0]) / 0.3; rr = (P[:, 1] + dz - wv[2]) / 0.3
                v = float(nd.map_coordinates(gm, [rr, c], order=1).mean())
                if abs(dx) < 1e-9 and abs(dz) < 1e-9: s0 = v
                if v > best[0]: best = (v, dx, dz)
        edge = best[1] in (sh[0], sh[-1]) or best[2] in (sh[0], sh[-1])
        res.append({'id': fid, 'name': name, 'kind': kind, 'shift_m': [r(best[1], 1), r(best[2], 1)], 'shift_abs_m': r(math.hypot(best[1], best[2]), 1),
                    'gain': r(best[0] / max(s0, 1e-6), 2), 'at_search_edge': edge})
    return res


def _bars(out, D, N, win):
    # (c) displaced-threshold bars: along-axis profile of the grey level averaged over +-85 % of the half width, 0.1 m
    #     steps, +-25 m around the NASR surveyed displaced threshold; the bar = the 3 m box maximum, edges at half
    #     contrast. AC 150/5340-1M Chg 1 para 2.9.1.3 / 2.9.1.5 (p. 54 of the official PDF; not in the committed
    #     extract): the bar is 10 ft (3.1 m) wide, wholly on the landing portion, its outboard edge on the threshold.
    bars = {}
    for end in ('10R', '28L'):
        d = F.thr_disp_m(end); half = F.RWY_DATA['10R/28L']['widthFt'] * FT / 2
        al = np.arange(d - 25, d + 25, 0.1); ac = np.linspace(-0.85 * half, 0.85 * half, 61)
        A, C = np.meshgrid(al, ac)
        W = np.array([F.rwy_to_world(end, a, c) for a, c in zip(A.ravel(), C.ravel())])
        prof = N.sample(W[:, 0], W[:, 1], win).mean(-1).reshape(A.shape).mean(0); base = float(np.median(prof))
        k = int(np.argmax(np.convolve(prof, np.ones(30) / 30, mode='same'))); hm = (prof[k] + base) / 2
        lo = k
        while lo > 0 and prof[lo] > hm: lo -= 1
        hi = k
        while hi < len(prof) - 1 and prof[hi] > hm: hi += 1
        bars[end] = {'nasr_thr_from_end_m': r(d, 2), 'bar_outboard_edge_minus_nasr_m': r(al[lo] - d, 2), 'bar_inboard_edge_minus_nasr_m': r(al[hi] - d, 2),
                     'bar_width_m': r(al[hi] - al[lo], 2), 'contrast_dn': r(prof[k] - base, 1)}
    out['displaced_threshold_bars'] = bars
    return out


# ============================================================================================ docs copies
def docs_copy(paths, max_bytes=2_000_000):
    from PIL import Image
    os.makedirs(DOCS, exist_ok=True)
    rows = []
    for p in paths:
        im = Image.open(p).convert('RGB'); name = os.path.splitext(os.path.basename(p))[0] + '.jpg'; q = os.path.join(DOCS, name)
        scale = min(1.0, 2600 / max(im.size)); qual = 88
        while True:
            im2 = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS) if scale < 1 else im
            im2.save(q, 'JPEG', quality=qual, optimize=True, progressive=True)
            if os.path.getsize(q) <= max_bytes: break
            if qual > 72: qual -= 6
            else: scale *= 0.88
        rows.append((name, im2.size, os.path.getsize(q), qual)); print('docs', name, im2.size, os.path.getsize(q), 'q', qual)
    # SOURCES.json beside the committed images (owner's rule: url, licence, fetched, made_by / note per file)
    src = {}
    for name, size, nbytes, qual in rows:
        al = name.startswith('overlay_al5015')
        src[name] = {
            'url': ('https://aeronav.faa.gov/d-tpp/2611/05015ad.pdf (base: FAA AL-5015, cycle 2611)' if al else
                    'https://apps.geo.fpac.usda.gov/geo-imagery/rest/services/naip/conus_naip/ImageServer (base: USDA NAIP 2024, tiles m_3712223_se / m_3712224_sw, flown 2024-05-20)')
                   + '; overlay: hwd3d data/hwd_airport.json (OpenStreetMap https://www.openstreetmap.org/copyright, adsb.lol https://adsb.lol, FAA NASR)',
            'licence': ('base U.S. Government work, public domain' if al else 'base public domain (USDA NAIP; credit requested)')
                       + '; overlay content from OpenStreetMap and adsb.lol under ODbL 1.0 - Produced Work, the notice is in the image',
            'fetched': '2026-11-12 (inputs: AL-5015 and NAIP fetched 2026-11-12; OSM state 2026-11-12T00:00Z; adsb.lol 2026-11-04..11)',
            'made_by': 'hwd3d/tools/plot_overlays.py --docs (JPEG %dx%d, quality %d, %d bytes)' % (size[0], size[1], qual, nbytes),
            'note': 'cross-check render for docs/phase1_crosscheck.md; not for navigation'}
    json.dump(src, open(os.path.join(DOCS, 'SOURCES.json'), 'w'), indent=1, ensure_ascii=False)
    return rows


def main():
    D = load()
    os.makedirs(OUT, exist_ok=True)
    metrics = {'data_sha256': __import__('hashlib').sha256(open(DATA, 'rb').read()).hexdigest()}
    paths = []
    if '--no-al' not in sys.argv:
        im = al_raster()
        px, bars = bar_ends(im)
        S = similarity(px)
        X = json.load(open(XCHECK))['al5015']
        metrics['al5015_registration'] = {
            'dpi': al5015.DPI, 'bar_ends_px': {k: [r(v[0], 1), r(v[1], 1)] for k, v in px.items()},
            'bar_ends_px_in_khwd_osm_xcheck': X['runway_bars_px'],
            'bar_end_diff_vs_xcheck_px': {k: r(np.hypot(*(np.array(px[k]) - np.array(X['runway_bars_px'][k]))), 1) for k in px},
            'similarity': {'scale_m_per_px': r(S['scale_m_per_px'], 5), 'rot_deg': r(S['rot_deg'], 3),
                           'resid_m': {k: r(v, 2) for k, v in S['resid_m'].items()},
                           'resid_along_across_m': {k: {kk: r(vv, 2) for kk, vv in v.items()} for k, v in S['resid_along_across'].items()}},
            'affine': {'resid_m': {k: r(v, 2) for k, v in S['affine']['resid_m'].items()}, 'singular_values_m_per_px': [r(v, 5) for v in S['affine']['singular_values_m_per_px']]},
            'affine_in_khwd_osm_xcheck_resid_m': X['fit_resid_m'],
            'bars': [{'len_px': r(b['len_px'], 1), 'len_m': r(b['len_px'] * S['scale_m_per_px'], 1), 'width_px': r(b['wid_px'], 1),
                      'width_m_drawn': r(b['wid_px'] * S['scale_m_per_px'], 1)} for b in bars],
            'nasr': {'10R/28L': {'len_m': r(5694 * FT, 1), 'width_m': r(150 * FT, 2)}, '10L/28R': {'len_m': r(3108 * FT, 1), 'width_m': r(75 * FT, 2)}},
        }
        metrics['al5015_vs_data'] = al_measure(D, im, S, px)
        paths += al_overlay(D, im, S, px, bars, None)
    if '--no-naip' not in sys.argv:
        N = NaipGrid('2024')
        metrics['naip_source'] = os.path.relpath(N.src, HWD)
        if '--no-render' not in sys.argv: paths = naip_overlays(D, N, metrics) + paths
        if '--no-measure' not in sys.argv: metrics['naip_vs_data'] = naip_measure(D, N)
    mp = os.path.join(OUT, 'crosscheck_metrics.json')
    old = json.load(open(mp)) if os.path.exists(mp) else {}
    old.update(metrics); json.dump(old, open(mp, 'w'), indent=1)
    print('wrote', os.path.relpath(mp, HWD))
    if '--docs' in sys.argv:
        allp = sorted(os.path.join(OUT, f) for f in os.listdir(OUT) if f.startswith('overlay_') and f.endswith('.png'))
        metrics_docs = docs_copy(allp)
        print(json.dumps(metrics_docs))
        # the numbers the committed cross-check report quotes are committed beside it (Phase 1 review: the out/ copy is
        # gitignored, so the report's evidence was not reproducible from a clone)
        cm = dict(old, licence='ODbL 1.0 (https://opendatacommons.org/licenses/odbl/1-0/): numbers derived from data/hwd_airport.json (OpenStreetMap, (c) OpenStreetMap contributors; adsb.lol) and from public-domain FAA AL-5015 and USDA NAIP',
                  made_by='hwd3d/tools/plot_overlays.py --docs')
        json.dump(cm, open(os.path.join(DOCS, 'crosscheck_metrics.json'), 'w'), indent=1)
        sj = os.path.join(DOCS, 'SOURCES.json'); src = json.load(open(sj))
        src['crosscheck_metrics.json'] = {'url': None, 'licence': cm['licence'], 'fetched': '2026-11-12 (inputs as the images)',
                                          'made_by': 'hwd3d/tools/plot_overlays.py --docs (copy of out/phase1/crosscheck_metrics.json)',
                                          'note': 'every measured number of docs/phase1_crosscheck.md; NAIP numbers come from the local lossless GeoTIFF when present (naip_source), else from the committed JPEG'}
        json.dump(src, open(sj, 'w'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
