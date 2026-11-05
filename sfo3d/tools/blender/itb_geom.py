"""Geometry of the 3-D International Terminal (ITB) asset: main hall wing roof, its trusses, columns, west glass wall,
curb canopy, the ITB core block, Boarding Areas A and G with their roof pods and the BA-G pod-3 end box.

Pure numpy / shapely (no bpy): tools/blender/build_itb.py turns the parts into Blender objects; tools/blender/verify_itb.py
measures the exported glb against the same functions.

THE REFERENCE IS THE 2-D DRAWING CODE (sheets BI-01..04, docs/drawings/buildings/README.md), imported here, not copied:
  tools/buildings/draw_itb.py   roof frame F, roof_line(u) (wing eave profile + glazed centre arch), wing(u), depth(u)
                                (truss depth, BI-03), chord(u) (exposed bottom chord seen from the west, BI-02), lens_poly(k),
                                tip_bands(), the west wall WALL (band of the two canopy readings), WH (glass-wall head),
                                L3, CANOPY, CANOPY_D, HANGER_U, COL_U, BAY_HW / BAY_HEAD (clear central bay), LETTER_HW,
                                HALL_HL (705-ft hall), PODS (itb_pods.json)
  tools/buildings/draw_data.py  SFO Museum outlines (data/sfo_airport.json), the frame / relief models
  tools/buildings/spec_itb.json the verified spec (tags, sources) - the keys are carried into glTF extras
Model frame: Blender local coordinates X = x - OX (east), Y = OZ - z (north), Z = height above local grade (m), with
(OX, OZ) = the relief-corrected roof centre (draw_itb.F['c']); build_itb.py puts the root node at world (OX, GROUND_Y, OZ).

What is drawn where the sources are silent is tagged here ('inf' = derived / chosen from stated evidence, 'unk' = placeholder
with no source value) and listed in the manifest; nothing below changes a drawn [obs] / [pub] value.
"""
import json
import math
import os
import sys

import numpy as np
from shapely.geometry import Polygon, MultiPolygon, box as sbox, Point
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely import affinity
import shapely

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'buildings'))
import draw_data as D  # noqa: E402
import draw_itb as I  # noqa: E402

FT = 0.3048
F = I.F
OX, OZ = round(float(F['c'][0]), 3), round(float(F['c'][1]), 3)
HL, HW = float(I.HL), float(I.HW)
LINES_V = [float(v) for v in I.LINES_V]
L3, WH, CANOPY, CANOPY_D = float(I.L3), float(I.WH), float(I.CANOPY), float(I.CANOPY_D)
V_W = float(I.WALL['v'])                     # west glass wall (middle of the band of its two canopy readings) [inf]
HALL_HL = float(I.HALL_HL)
UN = float(I.UN)

# ------------------------------------------------------------------------------------------------ choices where the
# sheets give no number (all tagged; listed in the manifest)
ROOF_THK = 0.6           # roof deck + fascia: BI-02 draws the top chord line 0.6 m under the roof line; fascia depth [unk]
STRIP_W = 1.5            # glazed strip along each truss line (NAIP 2024: dark lines ~3 px at 0.5 m) [obs, rough]
TRUSS_HALF = 1.2         # half spacing of the two top chords (BI-03 cross section draws the trusses 2.4 m wide) [inf]
R_BOT, R_TOP, R_WEB = 0.50, 0.32, 0.20   # tube radii: bottom chord (photo i3: the big tube on the glass head), top chords,
                                         # webs [inf, photos i3 / i4]
CENTRE_HALF = 90 * FT    # 180-ft central (bowstring) section [pub snippet]: the wing trusses end at |u| 27.43
NODE_U = sorted({s * (10 + 20 * k) * FT for k in range(21) for s in (-1, 1)})   # truss panel nodes on the 20-ft grid offset
# 10 ft from the centre [inf]: it carries every column line (+-190 / +-270 ft), the centre-section ends (+-90 ft) and the
# canopy hangers (+-30, 90, 130 ... 330 ft) of the sheets; panel 6.1 m (BI-02 draws ~6 m schematic webs)
V_UP = LINES_V[0] + TRUSS_HALF + R_TOP + 0.35   # upper glazing behind the exposed west truss (photo i3: glass with a grid
                                                # behind the diagonals, above the glass-wall head) [inf]
V_E = HW - 1.0           # east clerestory line, 1 m inside the east eave ("clerestories" [pub SOM]; position [inf])
COL_R = 0.75             # column radius (BI-02 / BI-03 draw 1.5 m) [inf]
V_COL = V_W - 2.5        # west column line: in front of the glass (photos i3 / i4), 2.5 m as drawn [inf]
CURB_W = 7.0             # departures curb sidewalk under the canopy, from the wall [inf] (BI-02 draws the curb band at L3)
CURB_THK = 1.2           # BI-02: band L3 - 1.2 .. L3
CANOPY_THK = 0.6         # [inf]
H_CORE = 17.9            # ITB core block (east block, north / south bars): NO SOURCE [unk]; placeholder = the adjoining
                         # Boarding Area A main roof 17.9 m [obs] (the ITB has 5 levels [pub]: it may be taller)
PARAPET = 1.0            # pier / core parapet above the roof deck [inf]; the measured NAIP heights are the roof edges
PARAPET_T = 0.3
APRON_BAND = 5.2         # BA-A glazed gate-room bays ~5.2-17.2 m AGL (photo a2, +-1.5) [obs photo]; apron level below
GLAZE_TOP = 17.2
GATEROOM_W = 24.0        # glazed bay width, centred on each stand's bridge attach points (data/sfo_stands.json) [inf]
SWITCH_M = {0: 0.0, 1: 450.0, 2: 1600.0}   # LOD switch distances (camera to root), m [our choice]
# Centre-section lens skylights as raised vaults (review r1, 2026-11-05). draw_itb.roof_line(u) is the SILHOUETTE seen from
# the west (BI-02; the crown 40.1 is the topmost photo-i4 pixel, itb_photo_skyline.json). Photos i4 / i2 show that silhouette
# formed by dark lens glass rising above the white fascia: at the crown the dark cap is 10 px of i4 at 6.72 px/m = 1.5 m
# (+-0.3), tapering to nothing towards the notches; NAIP 2024 shades each lens like a vault (bright east half). So the deck and
# fascia of the centre section run CROWN_CAP below roof_line (crown_cap(u), a parabola over the lens row) and each lens vaults LENS_RISE above
# the deck: the i4 camera (~20 m up, ~430 m out, 2.7 deg up) loses 0.047 m per m behind the fascia, 0.40 m for lens 0 at
# 8.45 m, so 1.5 + 0.4 = 1.9 m puts the lens top on roof_line as seen from i4 (the orthographic west silhouette then sits
# <= 0.4 m above roof_line at the crown, inside the 0.5-m tolerance). Vault form: rise R (1 - x^2) (1 - (dv / hw)^2) on
# the pointed-lens planform (x = (u - uc) / a) [inf].
CROWN_CAP = 1.5          # [obs photo i4, low]
LENS_RISE = 1.9          # [inf: CROWN_CAP + the i4 line-of-sight drop to lens 0]
LENS_NV = 6              # lens strips across v (LOD0 / LOD1); LOD2: 2
# Boarding Area G apron facade, re-measured on photo a2 (review r1; a2 looks SSW over the BA-G NNE face - camera solved in
# render_itb.view_a2g). On a2 the bridge-head bump-outs of the outline (15.7 x 8.7 m) are low boxes: B1 (s -69.6..-53.8) top at
# 57 of the 148 px between the facade base and the 17.0 m roof edge -> 6.5 m; B2 / B3 the same by eye [obs, low]. The two-storey
# gate-room curtain walls fill the main-face segments BETWEEN the bump-outs under the pods (s 9.6..73.2 = 538 px for 63.6 m, and
# the west end of -133.1..-69.6), from 12.4 m to 2.3 m below the roof edge (8.6 px/m at the facade: 4.6..14.7 m); below them a
# light 1.6 m band and the dark recessed apron level (0..3.0 m); the panel segments between (s -53.8..-6.2, 88.9..120.8) carry only
# two isolated 2-lite windows (not modelled). The SSW face is not imaged: same rule [inf] -> six gate rooms = "six double-gated
# gate rooms" [pub tutor_bag].
BUMP_H_G = 6.5           # BA-G bridge-head bump-outs [obs photo a2, low]
APRON_TOP = 3.0          # dark recessed apron level [obs photo a2]
GLAZE_BOT, GLAZE_TOP2 = 4.6, 14.7   # gate-room curtain wall foot / head [obs photo a2 (BA-G); BA-A by analogy, inf]
GATE_POD_MIN = 35.0      # a main-face segment is a gate room where one pod overlaps it by >= 35 m [inf; selects 6 on BA-G]
GATE_TILE = (15.9, 10.1) # itb_c_curtain_gate tile (a quarter of the 63.6-m bay x the glazing height)

PODS = I.PODS
POD = I.POD
PIERS = PODS['piers']


def head(u):
    """west glass-wall head: WH, rising over the clear central bay to WH + BAY_HEAD between the notches (BI-02 V1)."""
    a = abs(u)
    if a >= I.BAY_HW: return WH
    if a <= UN: return WH + I.BAY_HEAD
    return WH + I.BAY_HEAD * (I.BAY_HW - a) / (I.BAY_HW - UN)


def crown_cap(u):
    """depth of the centre-section deck / fascia below the silhouette roof_line(u): CROWN_CAP at the lens row's middle,
    tapering with the lens vaults (mean lens centre / half-length of the five lenses: u -1.8 +- 23.98 m) to 0 at their ends,
    so the vault tops (LENS_RISE (1 - x^2)) carry the silhouette everywhere (first cut: tapered to the notches, which left
    the silhouette up to 0.55 m low where the lenses end, out of tolerance)."""
    uc = float(np.mean([L['uc'] for L in LENSES])); a = float(np.mean([L['a'] for L in LENSES]))
    x = (u - uc) / a
    return CROWN_CAP * (1.0 - x * x) if abs(x) < 1.0 else 0.0


def roof_top(u):
    """top of the roof deck and fascia (the silhouette roof_line(u) less the lens cap over the centre section)."""
    u = max(-HL, min(HL, u))
    return float(I.roof_line(u)) - crown_cap(u)


def roof_us(u):
    return roof_top(u) - ROOF_THK


def bottom_chord_line(k, u):
    """bottom line (underside) of the bottom chord of truss line k (0 = west) [inf]:
    wings (|u| >= 27.43): BI-03 depth(u) (29 ft over the supports [pub], linear taper to 1.5 m at the inner and outer tips
    [inf]). The west line takes the higher of BI-02's chord(u) (level with the glass-wall head over the hall) and the BI-03
    taper: the two sheets differ only between the inner column line and the notch, where photos i3 / i4 show the west bottom
    chord sweeping up from the glass head towards the notch (~3.5-4 m above the head at |u| 30, i4) - so BI-03 is followed
    there and BI-02 elsewhere (listed in the manifest).
    Centre section (180 ft [pub snippet]): a sagging bowstring chord, meeting the deck at the notches and touching the clear
    bay's head (WH + 2) at u = 0 (photos i3 / i4 show a lens-shaped centre truss; BI-03 draws the form as unknown)."""
    a = abs(u)
    if a >= CENTRE_HALF:
        if k == 0:
            return max(float(I.chord(u)), head(u), roof_top(u) - float(I.depth(u)))
        return min(roof_top(u) - float(I.depth(u)), roof_us(u) - 2 * R_BOT - 0.3)
    z0 = WH + I.BAY_HEAD
    z1 = roof_us(CENTRE_HALF) - 2 * R_BOT - 0.2
    z = z0 + (z1 - z0) * (u / CENTRE_HALF) ** 2
    return max(z, head(u)) if k == 0 else z


def UVw(u, v):
    """roof frame (u, v) -> world (x, z)."""
    p = F['c'] + F['ax'] * u + F['v'] * v
    return float(p[0]), float(p[1])


def B(x, z, h):
    """world (x, z, height) -> Blender local (X east, Y north, Z up)."""
    return (x - OX, OZ - z, h)


def Buv(u, v, h):
    x, z = UVw(u, v)
    return B(x, z, h)


# ------------------------------------------------------------------------------------------------ mesh builder
class MB:
    """indexed polygon mesh in Blender local coordinates with per-face material, per-corner tiling UV (UV_detail, metres
    / tile) and a smooth flag. Vertices are de-duplicated within a named surface group only (sharp edges between groups)."""

    def __init__(self, name):
        self.name = name
        self.V, self.F, self.M, self.UV, self.S = [], [], [], [], []
        self._key = {}

    def v(self, p, grp=None):
        if grp is None:
            self.V.append(tuple(float(c) for c in p)); return len(self.V) - 1
        k = (grp, round(p[0], 4), round(p[1], 4), round(p[2], 4))
        i = self._key.get(k)
        if i is None:
            self.V.append(tuple(float(c) for c in p)); i = len(self.V) - 1; self._key[k] = i
        return i

    def face(self, pts, mat, uvs, smooth=False, grp=None):
        idx = [self.v(p, grp) for p in pts]
        # drop degenerate corners (repeated indices) - lens ends have zero width
        out, ouv = [], []
        for i, t in zip(idx, uvs):
            if out and out[-1] == i: continue
            out.append(i); ouv.append(t)
        if len(out) > 1 and out[0] == out[-1]: out.pop(); ouv.pop()
        if len(out) < 3: return
        P = np.array([self.V[i] for i in out])
        n = np.zeros(3)
        for a in range(len(P)):
            n += np.cross(P[a], P[(a + 1) % len(P)])
        if np.linalg.norm(n) < 1e-6: return
        self.F.append(out); self.M.append(mat); self.UV.append([tuple(map(float, t)) for t in ouv]); self.S.append(smooth)

    def quad_wall(self, a, b, z0a, z1a, z0b, z1b, mat, s0, tile, grp=None, smooth=False):
        """vertical quad from plan point a to b (Blender XY), bottom/top heights at a and b; outward normal = right of a->b.
        UV = (along / tile_u, z / tile_v) starting at s0 along."""
        L = math.hypot(b[0] - a[0], b[1] - a[1]); tu, tv = tile
        self.face([(a[0], a[1], z0a), (b[0], b[1], z0b), (b[0], b[1], z1b), (a[0], a[1], z1a)], mat,
                  [(s0 / tu, z0a / tv), ((s0 + L) / tu, z0b / tv), ((s0 + L) / tu, z1b / tv), (s0 / tu, z1a / tv)], smooth, grp)

    def merge(self, o):
        off = len(self.V)
        self.V += o.V
        self.F += [[i + off for i in f] for f in o.F]
        self.M += o.M; self.UV += o.UV; self.S += o.S

    def tris(self):
        return sum(len(f) - 2 for f in self.F)

    def bbox(self):
        P = np.array(self.V); return P.min(0), P.max(0)


def tube(mb, pts, r, sides, mat, tile=4.0, cap=False):
    """tube along a polyline (Blender coords), parallel-transport frames, smooth shading."""
    P = np.asarray(pts, float)
    if len(P) < 2: return
    T = np.diff(P, axis=0); Ls = np.linalg.norm(T, axis=1)
    keep = np.r_[True, Ls > 1e-6]; P = P[keep]
    if len(P) < 2: return
    T = np.diff(P, axis=0); T /= np.linalg.norm(T, axis=1)[:, None]
    tang = np.vstack([T[0], (T[:-1] + T[1:]), T[-1]]); tang /= np.linalg.norm(tang, axis=1)[:, None]
    ref = np.array([0, 0, 1.0]) if abs(tang[0][2]) < 0.9 else np.array([1.0, 0, 0])
    n = np.cross(tang[0], ref); n /= np.linalg.norm(n)
    frames = []
    for i in range(len(P)):
        t = tang[i]
        n = n - t * np.dot(n, t); n /= np.linalg.norm(n)
        frames.append((n, np.cross(t, n)))
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    ang = np.linspace(0, 2 * math.pi, sides + 1)
    rings = []
    for i in range(len(P)):
        n_, b_ = frames[i]
        # mitre: scale the ring in the bend plane so joints keep the radius
        rings.append([P[i] + r * (math.cos(a) * n_ + math.sin(a) * b_) for a in ang[:-1]])
    g = ('tube', id(rings))
    for i in range(len(P) - 1):
        for j in range(sides):
            j2 = (j + 1) % sides
            a0, a1 = ang[j] / (2 * math.pi), ang[j + 1] / (2 * math.pi)
            mb.face([rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]], mat,
                    [(s[i] / tile, a0), (s[i] / tile, a1), (s[i + 1] / tile, a1), (s[i + 1] / tile, a0)], True, g)
    if cap:
        for i, sg in ((0, -1), (len(P) - 1, 1)):
            ring = rings[i] if sg > 0 else rings[i][::-1]
            mb.face(ring, mat, [(0.5 + 0.5 * math.cos(a), 0.5 + 0.5 * math.sin(a)) for a in (ang[:-1] if sg > 0 else ang[:-1][::-1])])


def boxm(mb, c, d, w, h, z0, mat, tile=(3.0, 3.0), top=True, bottom=False):
    """oriented box: centre line from plan point c (Blender XY) along unit d, length w (along d), width h (across),
    from z0 to z0 + height given as tuple (z0, z1)."""
    d = np.asarray(d, float); d /= np.linalg.norm(d); n = np.array([d[1], -d[0]])
    c = np.asarray(c, float); za, zb = z0
    pts = [c - d * w / 2 - n * h / 2, c + d * w / 2 - n * h / 2, c + d * w / 2 + n * h / 2, c - d * w / 2 + n * h / 2]
    pts = [tuple(p) for p in pts]
    A = sum(pts[i][0] * pts[(i + 1) % 4][1] - pts[(i + 1) % 4][0] * pts[i][1] for i in range(4))
    ring = pts if A > 0 else pts[::-1]
    s = 0.0
    for i in range(4):
        a, b = ring[i], ring[(i + 1) % 4]
        mb.quad_wall(a, b, za, zb, za, zb, mat, s, tile)
        s += math.hypot(b[0] - a[0], b[1] - a[1])
    if top: mb.face([(p[0], p[1], zb) for p in ring], mat, [(p[0] / tile[0], p[1] / tile[1]) for p in ring])
    if bottom: mb.face([(p[0], p[1], za) for p in ring[::-1]], mat, [(p[0] / tile[0], p[1] / tile[1]) for p in ring[::-1]])


def tri_poly(poly):
    """constrained Delaunay triangulation of a shapely polygon (holes allowed) -> list of CCW triangles."""
    out = []
    for t in shapely.constrained_delaunay_triangles(poly).geoms:
        c = list(t.exterior.coords)[:3]
        A = (c[1][0] - c[0][0]) * (c[2][1] - c[0][1]) - (c[2][0] - c[0][0]) * (c[1][1] - c[0][1])
        if abs(A) < 1e-8: continue
        out.append(c if A > 0 else c[::-1])
    return out


def cap(mb, poly, z, mat, tile, down=False, grp=None):
    for t in tri_poly(poly):
        pts = t[::-1] if down else t
        mb.face([(p[0], p[1], z) for p in pts], mat, [(p[0] / tile, p[1] / tile) for p in pts], False, grp)


def to_blender_poly(P):
    """shapely polygon in world (x, z) -> Blender XY, CCW exterior."""
    g = affinity.affine_transform(P, [1, 0, 0, -1, -OX, OZ])
    return orient(g, 1.0) if isinstance(g, Polygon) else MultiPolygon([orient(p, 1.0) for p in g.geoms])


def rings_of(poly):
    return [list(poly.exterior.coords)[:-1]] + [list(r.coords)[:-1] for r in poly.interiors]


# ------------------------------------------------------------------------------------------------ parts
class Part:
    """one glTF node: mesh + tags. kind 'shell' = gets the baked AO atlas (UV_ao); 'detail' = thin members, no AO."""

    def __init__(self, name, mb, kind, src, feature, spec=(), dims=None, note=''):
        self.name, self.mb, self.kind, self.src, self.feature = name, mb, kind, src, feature
        self.spec, self.dims, self.note = list(spec), dims or {}, note

    def extras(self, lod):
        e = dict(src=self.src, feature=self.feature, spec=self.spec, lod=lod)
        if self.dims: e['dims'] = self.dims
        if self.note: e['note'] = self.note
        return e


def dim(value, tag, source):
    return dict(v=value if not isinstance(value, float) else round(value, 3), tag=tag, source=source)


# ---------------------------------------------------------------------------- hall roof deck
def lens_params():
    out = []
    for k in range(5):
        _, Lk, Wk, uc = I.lens_poly(k)
        out.append(dict(k=k, uc=float(uc), a=float(Lk) / 2, b=float(Wk) / 2, vc=LINES_V[k]))
    return out


LENSES = lens_params()
(N0, N1), (S0, S1) = I.tip_bands()


def lens_hw(L, u):
    x = (u - L['uc']) / L['a']
    return max(0.0, L['b'] * (1 - x * x)) if abs(x) < 1 else 0.0


def lens_rise(L, u, v):
    """height of lens L's vaulted glass above the deck at (u, v) [inf form, see LENS_RISE]."""
    hw = lens_hw(L, u)
    if hw <= 0: return 0.0
    x = (u - L['uc']) / L['a']; d = (v - L['vc']) / hw
    return LENS_RISE * (1 - x * x) * max(0.0, 1 - d * d)


def roof_stations(step, lens_n=13):
    st = set(np.arange(-HL, HL + 1e-6, step).round(4).tolist())
    st |= {-HL, HL, N0, N1, S0, S1, -UN, UN, -CENTRE_HALF, CENTRE_HALF}
    for L in LENSES:
        st |= {L['uc'] - L['a'], L['uc'] + L['a']}
        if L['b'] > STRIP_W / 2:
            dx = L['a'] * math.sqrt(1 - (STRIP_W / 2) / L['b'])
            st |= {L['uc'] - dx, L['uc'] + dx}
        for f in np.linspace(-1, 1, lens_n):    # refine the lens edges (parabolic) and the vault
            st.add(L['uc'] + f * L['a'])
    st = sorted(x for x in st if -HL - 1e-6 <= x <= HL + 1e-6)
    out = [st[0]]
    for x in st[1:]:
        if x - out[-1] > 0.05: out.append(x)
    out[-1] = HL; out[0] = -HL
    return out


def roof_intervals(um, detail=True):
    """material intervals across v at u = um: list of (lo(u), hi(u), material, lens or None) with callables; the lens is
    given where the interval carries (part of) a vaulted lens skylight (lens_rise > 0). detail=False (LOD2): tip bands and
    the lenses only (no truss-line strips)."""
    cst = lambda c: (lambda u: c)  # noqa: E731
    if (N0 <= um <= N1) or (S0 <= um <= S1):
        return [(cst(-HW), cst(HW), 'glass_roof', None)]
    glass = []
    for L in LENSES:
        k = L['k']; vc = L['vc']; hw = lens_hw(L, um)
        if hw > STRIP_W / 2 or not (N1 <= um <= S0) or not detail:
            if hw > 0:
                glass.append(((lambda u, L=L: L['vc'] - lens_hw(L, u)), (lambda u, L=L: L['vc'] + lens_hw(L, u)), L))
        else:
            glass.append((cst(vc - STRIP_W / 2), cst(vc + STRIP_W / 2), L if hw > 0 else None))
    glass.sort(key=lambda g: g[0](um))
    out, cur = [], cst(-HW)
    for lo, hi, L in glass:
        out.append((cur, lo, 'roof_membrane', None)); out.append((lo, hi, 'glass_roof', L)); cur = hi
    out.append((cur, cst(HW), 'roof_membrane', None))
    return out


def hall_roof(step=2.0, detail=True):
    """the wing roof as a slab: top = roof_line(u) [obs profile, BI-02], flat across v (cross camber unknown, as drawn
    [unk]); 5 glazed truss-line strips, 5 lens skylights (pointed-lens planform as drawn, [inf]), glazed tip bands [obs];
    underside ROOF_THK lower (soffit, dark grey panels: photo i3), fascia all round."""
    mb = MB('hall_roof')
    st = roof_stations(step, 13 if detail else 5)
    soff = {'roof_membrane': 'soffit', 'glass_roof': 'glass_roof_under'}
    nv = LENS_NV if detail else 2
    for u0, u1 in zip(st[:-1], st[1:]):
        um = 0.5 * (u0 + u1)
        iv = roof_intervals(um, detail)
        t0, t1 = roof_top(u0), roof_top(u1)
        for lo, hi, mat, L in iv:
            a0, a1, b0, b1 = lo(u0), lo(u1), hi(u0), hi(u1)
            if max(b0 - a0, b1 - a1) < 1e-4: continue
            tl = 12.0 if mat == 'roof_membrane' else 3.0
            if L is not None:
                # vaulted lens: nv strips across, vertices raised by lens_rise (0 on the lens edge -> watertight with the deck)
                for j in range(nv):
                    f0, f1 = j / nv, (j + 1) / nv
                    vv = [a0 + (b0 - a0) * f0, a1 + (b1 - a1) * f0, a1 + (b1 - a1) * f1, a0 + (b0 - a0) * f1]
                    uu = [u0, u1, u1, u0]; tt = [t0, t1, t1, t0]
                    P = [Buv(x, y, z + lens_rise(L, x, y)) for x, y, z in zip(uu, vv, tt)]
                    mb.face(P, mat, [(x / tl, y / tl) for x, y in zip(uu, vv)], True, 'top')
            else:
                P = [Buv(u0, a0, t0), Buv(u1, a1, t1), Buv(u1, b1, t1), Buv(u0, b0, t0)]
                UVs = [(u0 / tl, a0 / tl), (u1 / tl, a1 / tl), (u1 / tl, b1 / tl), (u0 / tl, b0 / tl)]
                mb.face(P, mat, UVs, True, 'top')
            P2 = [Buv(u0, a0, t0 - ROOF_THK), Buv(u0, b0, t0 - ROOF_THK), Buv(u1, b1, t1 - ROOF_THK), Buv(u1, a1, t1 - ROOF_THK)]
            mb.face(P2, soff[mat], [(u0 / 6.096, a0 / 6.096), (u0 / 6.096, b0 / 6.096), (u1 / 6.096, b1 / 6.096), (u1 / 6.096, a1 / 6.096)], True, 'bot')
        for v, sg in ((-HW, -1), (HW, 1)):     # fascia: west (normal -v) / east (normal +v)
            pa, pb = (Buv(u0, v, 0), Buv(u1, v, 0)) if sg < 0 else (Buv(u1, v, 0), Buv(u0, v, 0))
            za, zb = (t0, t1) if sg < 0 else (t1, t0)
            mb.quad_wall(pa, pb, za - ROOF_THK, za, zb - ROOF_THK, zb, 'fascia', u0 if sg < 0 else -u1, (3.0, 3.0), grp='fas%d' % sg)
    for u, sg in ((-HL, -1), (HL, 1)):        # tip fascia
        t = roof_top(u)
        a, b = (Buv(u, HW, 0), Buv(u, -HW, 0)) if sg < 0 else (Buv(u, -HW, 0), Buv(u, HW, 0))
        mb.quad_wall(a, b, t - ROOF_THK, t, t - ROOF_THK, t, 'fascia', 0, (3.0, 3.0))
    return mb


# ---------------------------------------------------------------------------- trusses, outriggers, columns
def truss_nodes():
    return [u for u in NODE_U if abs(u) < HL - 0.8] + [-HL + 0.6, HL - 0.6]


def hall_trusses(lod=0):
    """5 three-chord 'football' trusses on the truss lines [pub form, obs lines]: two top chords under the deck, one bottom
    chord (bottom_chord_line), webs on the 20-ft node grid: in each side plane a diagonal per panel (alternating) and at
    every node a V of two posts in the cross-section [inf, photos i3 / i4]. LOD1: bottom chord + one top chord + the
    diagonals in the truss's mid plane."""
    mb = MB('hall_trusses')
    U = sorted(truss_nodes())
    sides = 8 if lod == 0 else 4
    ws = 6 if lod == 0 else 4
    for k, vk in enumerate(LINES_V):
        def zb(u, k=k):
            return bottom_chord_line(k, u) + R_BOT

        def zt(u):
            return roof_us(u) - R_TOP - 0.05

        # wings and centre section are separate trusses (inner cantilever tips at +-90 ft)
        segs = [[u for u in U if u <= -CENTRE_HALF + 1e-6], [u for u in U if -CENTRE_HALF - 1e-6 <= u <= CENTRE_HALF + 1e-6],
                [u for u in U if u >= CENTRE_HALF - 1e-6]]
        for seg in segs:
            if len(seg) < 2: continue
            fine = []
            for a, b in zip(seg[:-1], seg[1:]):
                for f in np.linspace(0, 1, 4)[:-1]: fine.append(a + (b - a) * f)
            fine.append(seg[-1])
            tube(mb, [Buv(u, vk, zb(u)) for u in fine], R_BOT, sides, 'steel_white', cap=True)   # capped: open chord ends
            tops = (vk - TRUSS_HALF, vk + TRUSS_HALF) if lod == 0 else (vk,)                 # would show back faces
            for vt in tops:
                tube(mb, [Buv(u, vt, zt(u)) for u in fine], R_TOP, max(4, sides - 2), 'steel_white', cap=True)
            for i, u in enumerate(seg):
                if lod == 0:
                    for vt in tops:   # node posts (V in the cross section)
                        tube(mb, [Buv(u, vk, zb(u) + R_BOT * 0.6), Buv(u, vt, zt(u) - R_TOP * 0.6)], R_WEB, ws, 'steel_white')
                if i + 1 < len(seg):
                    u2 = seg[i + 1]
                    a, b = (u, u2) if i % 2 == 0 else (u2, u)
                    for vt in tops:   # diagonal: bottom node a -> top node b
                        tube(mb, [Buv(a, vk, zb(a) + R_BOT * 0.6), Buv(b, vt, zt(b) - R_TOP * 0.6)], R_WEB, ws, 'steel_white')
    return mb


def hall_outriggers(lod=0):
    """outrigger beams under the eave soffit from the outer truss lines to the eaves, one per truss node (photo i3: dark
    I-beams at regular spacing under the soffit) [inf: spacing / depth]; east side stops at the clerestory."""
    mb = MB('hall_outriggers')
    for u in truss_nodes():
        for v0, v1 in ((LINES_V[0] - TRUSS_HALF, -HW + 0.3), (LINES_V[-1] + TRUSS_HALF, V_E - 0.3)):
            us = roof_us(u)
            d = np.array(Buv(u, v1, 0)[:2]) - np.array(Buv(u, v0, 0)[:2]); L = float(np.linalg.norm(d)); d /= L
            c = (np.array(Buv(u, v0, 0)[:2]) + np.array(Buv(u, v1, 0)[:2])) / 2
            boxm(mb, c, d, L, 0.3, (us - 0.6, us), 'steel_grey', top=False, bottom=True)
    return mb


def column_points():
    pts = []
    for cu in I.COL_U:
        for s in (-1, 1):
            pts.append((s * cu, V_COL, 'west'))
            for v in LINES_V[1:]:
                pts.append((s * cu, v, 'inner'))
    return pts


def hall_columns(lod=0):
    """20 columns (5 truss lines x 4 at +-190 / +-270 ft) [pub count, inf positions]; the west line stands in front of the
    glass (photos i3 / i4) and branches at the glass head into 5 members: a post to the roof, two to the west truss and
    two to the eave soffit (BI-02 V1: post + 2 per side at +-5 / +-10 m) [obs count, inf geometry]. Inner lines: columns
    from level 3 to the bottom chords (spherical bearings [pub msc2000], drawn as a cap)."""
    mb = MB('hall_columns')
    sides = 16 if lod == 0 else 8
    for u, v, kind in column_points():
        if kind == 'west':
            tube(mb, [Buv(u, v, L3), Buv(u, v, WH)], COL_R, sides, 'steel_white', cap=True)
            for du in (-10.0, -5.0, 0.0, 5.0, 10.0):
                if du == 0:
                    tgt = Buv(u, v, roof_us(u) - 0.02)
                elif abs(du) < 7:
                    tgt = Buv(u + du, LINES_V[0], bottom_chord_line(0, u + du) + R_BOT)
                else:
                    tgt = Buv(u + du, -HW + 1.5, roof_us(u + du) - 0.02)
                tube(mb, [Buv(u, v, WH - 0.3), tgt], 0.28 if du else 0.32, 8 if lod == 0 else 4, 'steel_white')
        else:
            # inner lines at LOD0 and LOD1 (review r1: LOD1 kept only the west line; inside the opaque envelope they are not
            # seen from outside, but the LOD sets now match)
            top = bottom_chord_line(LINES_V.index(v), u)
            tube(mb, [Buv(u, v, L3), Buv(u, v, top - 0.4)], COL_R, sides, 'steel_white', cap=True)
    return mb


# ---------------------------------------------------------------------------- west wall, canopy, curb, podium, walls
def wall_u_breaks(extra=()):
    br = {-HALL_HL, HALL_HL, -I.BAY_HW, I.BAY_HW, -UN, UN}
    br |= {u for u in NODE_U if abs(u) < HALL_HL}
    br |= set(extra)
    return sorted(br)


def hall_west_wall():
    """west glass wall at v = V_W over the 705-ft hall [pub length, centred inf]: clear entrance glazing under the canopy,
    side bays fritted above a 1.5 m dark clear strip, clear central bay (+-40 m) whose head rises to WH + 2 (BI-02 V1)
    [obs photos i1 / i4]; head closure and the upper glazing behind the exposed west truss (photo i3) [inf]."""
    mb = MB('hall_west_wall')
    U = wall_u_breaks()
    for u0, u1 in zip(U[:-1], U[1:]):
        um = 0.5 * (u0 + u1); side = abs(um) > I.BAY_HW
        a, b = Buv(u0, V_W, 0), Buv(u1, V_W, 0)
        h0, h1 = head(u0), head(u1)
        # (z ranges, material); UV tiles: glass panes 6.096 x 4.4 m
        bands = [(L3, CANOPY, L3, CANOPY, 'glass_entrance')]
        if side:
            bands += [(CANOPY, CANOPY + 1.5, CANOPY, CANOPY + 1.5, 'glass_clear'), (CANOPY + 1.5, h0, CANOPY + 1.5, h1, 'glass_frit')]
        else:
            bands += [(CANOPY, h0, CANOPY, h1, 'glass_hall')]
        for z0a, z1a, z0b, z1b, mat in bands:
            mb.quad_wall(a, b, z0a, z1a, z0b, z1b, mat, u0, (6.096, 4.4) if mat != 'glass_frit' else (3.6, 3.6), grp='w')
    # head closure (alu): from V_W to V_UP at the head, 0.4 m deep. (u, v) is counter-clockwise in Blender XY, so the top
    # runs u0 -> u1 at V_W first (normal up) and the underside the other way (normal down); round 0 had both inverted - seen
    # as 2-4 back-face pixels under the north roof tip from the NNE (bag view, review r1)
    for u0, u1 in zip(U[:-1], U[1:]):
        h0, h1 = head(u0), head(u1)
        P = [Buv(u0, V_W, h0), Buv(u1, V_W, h1), Buv(u1, V_UP, h1), Buv(u0, V_UP, h0)]
        mb.face(P, 'mullion', [(0, 0), (1, 0), (1, 1), (0, 1)], False, 'ct')
        P = [Buv(u0, V_W, h0 - 0.4), Buv(u0, V_UP, h0 - 0.4), Buv(u1, V_UP, h1 - 0.4), Buv(u1, V_W, h1 - 0.4)]
        mb.face(P, 'mullion', [(0, 0), (1, 0), (1, 1), (0, 1)], False, 'cb')
    # upper glazing behind the exposed west truss, from the head to the roof underside
    U2 = sorted(set(U) | set(np.arange(-HALL_HL, HALL_HL, 3.0).round(3).tolist()))
    for u0, u1 in zip(U2[:-1], U2[1:]):
        a, b = Buv(u0, V_UP, 0), Buv(u1, V_UP, 0)
        mb.quad_wall(a, b, head(u0), roof_us(u0) + TUCK, head(u1), roof_us(u1) + TUCK, 'glass_hall', u0, (6.096, 4.4), grp='up')
    return mb


def hall_mullions():
    """LOD0 mullions on the west wall: verticals on the 20-ft grid (offset 10 ft, the column grid) [obs photo i4 ~6.1 m,
    low], transoms every 2.2 m over the clear central bay [obs photo i4, low], the door-head transom at L3 + 3 m and the
    canopy line [inf]."""
    mb = MB('hall_mullions')
    d = np.array(Buv(1, V_W, 0)[:2]) - np.array(Buv(0, V_W, 0)[:2]); d /= np.linalg.norm(d)
    nW = np.array(Buv(0, V_W - 1, 0)[:2]) - np.array(Buv(0, V_W, 0)[:2])
    for u in [u for u in NODE_U if abs(u) < HALL_HL] + [-HALL_HL + 0.15, HALL_HL - 0.15]:
        c = np.array(Buv(u, V_W, 0)[:2]) + nW * 0.2
        boxm(mb, c, nW, 0.4, 0.25, (L3, head(u)), 'mullion')
    for z in (L3 + 3.0,):
        c = np.array(Buv(0, V_W, 0)[:2]) + nW * 0.15
        boxm(mb, c, d, 2 * HALL_HL, 0.3, (z - 0.15, z + 0.15), 'mullion', bottom=True)
    zz = CANOPY + 2.2
    while zz < WH + I.BAY_HEAD - 0.3:
        ua = I.BAY_HW if zz <= WH else (I.BAY_HW - (zz - WH) / I.BAY_HEAD * (I.BAY_HW - UN))
        c = np.array(Buv(0, V_W, 0)[:2]) + nW * 0.15
        boxm(mb, c, d, 2 * ua, 0.25, (zz - 0.1, zz + 0.1), 'mullion', bottom=True)
        zz += 2.2
    # head beam along the glass head (alu cap)
    U = wall_u_breaks()
    for u0, u1 in zip(U[:-1], U[1:]):
        a = np.array(Buv(u0, V_W, 0)[:2]) + nW * 0.3; b = np.array(Buv(u1, V_W, 0)[:2]) + nW * 0.3
        mb.quad_wall(tuple(a), tuple(b), head(u0) - 0.5, head(u0), head(u1) - 0.5, head(u1), 'mullion', 0, (3, 3))
    return mb


def hall_canopy():
    """curb canopy ('entrance canopy' [pub SEAONC]): top at CANOPY = L3 + 5 m, CANOPY_D = 5 m deep [inf photos i3 / i4],
    over the hall length; slab CANOPY_THK."""
    mb = MB('hall_canopy')
    v0, v1 = V_W - CANOPY_D, V_W
    U = wall_u_breaks()
    for u0, u1 in zip(U[:-1], U[1:]):
        mb.face([Buv(u0, v0, CANOPY), Buv(u1, v0, CANOPY), Buv(u1, v1, CANOPY), Buv(u0, v1, CANOPY)], 'canopy_top',
                [(u0 / 6, v0 / 6), (u1 / 6, v0 / 6), (u1 / 6, v1 / 6), (u0 / 6, v1 / 6)], False, 't')
        mb.face([Buv(u0, v0, CANOPY - CANOPY_THK), Buv(u1, v0, CANOPY - CANOPY_THK), Buv(u1, v1, CANOPY - CANOPY_THK), Buv(u0, v1, CANOPY - CANOPY_THK)][::-1],
                'soffit', [(u0 / 6.096, v0 / 6.096), (u1 / 6.096, v0 / 6.096), (u1 / 6.096, v1 / 6.096), (u0 / 6.096, v1 / 6.096)][::-1], False, 'b')
        mb.quad_wall(Buv(u0, v0, 0), Buv(u1, v0, 0), CANOPY - CANOPY_THK, CANOPY, CANOPY - CANOPY_THK, CANOPY, 'steel_grey', u0, (3, 3), grp='e')
    for u, sg in ((-HALL_HL, -1), (HALL_HL, 1)):
        a, b = (Buv(u, v1, 0), Buv(u, v0, 0)) if sg < 0 else (Buv(u, v0, 0), Buv(u, v1, 0))
        mb.quad_wall(a, b, CANOPY - CANOPY_THK, CANOPY, CANOPY - CANOPY_THK, CANOPY, 'steel_grey', 0, (3, 3))
    return mb


def hall_hangers(lod=0):
    """canopy hangers on the 40-ft grid and at +-30 / +-90 ft (BI-02 HANGER_U) [obs photo i4]: an inclined pair from the
    glass wall (apex HANGER_H above the canopy) to the canopy edge, short leg -0.4 m, long leg +2.9 m along u; a post under
    the canopy at each [obs photo i4; form inf]."""
    mb = MB('hall_hangers')
    for uh in I.HANGER_U:
        if abs(uh) > HALL_HL: continue
        apex = Buv(uh, V_W - 0.25, CANOPY + I.HANGER_H)
        for du in (-0.4, I.HANGER_L):
            tube(mb, [apex, Buv(uh + du, V_W - CANOPY_D + 0.3, CANOPY)], 0.1, 6 if lod == 0 else 4, 'steel_grey')
        tube(mb, [Buv(uh, V_W - CANOPY_D + 0.5, L3), Buv(uh, V_W - CANOPY_D + 0.5, CANOPY - CANOPY_THK)], 0.18, 8 if lod == 0 else 4, 'steel_white')
    return mb


def hall_curb():
    """departures curb sidewalk at level 3 in front of the wall (BI-02: band L3 - 1.2 .. L3) [inf width]."""
    mb = MB('hall_curb')
    v0, v1 = V_W - CURB_W, V_W
    U = wall_u_breaks()
    z0, z1 = L3 - CURB_THK, L3
    for u0, u1 in zip(U[:-1], U[1:]):
        mb.face([Buv(u0, v0, z1), Buv(u1, v0, z1), Buv(u1, v1, z1), Buv(u0, v1, z1)], 'concrete',
                [(u0 / 4, v0 / 4), (u1 / 4, v0 / 4), (u1 / 4, v1 / 4), (u0 / 4, v1 / 4)], False, 't')
        mb.face([Buv(u0, v0, z0), Buv(u1, v0, z0), Buv(u1, v1, z0), Buv(u0, v1, z0)][::-1], 'concrete',
                [(u0 / 4, v0 / 4), (u1 / 4, v0 / 4), (u1 / 4, v1 / 4), (u0 / 4, v1 / 4)][::-1], False, 'b')
        mb.quad_wall(Buv(u0, v0, 0), Buv(u1, v0, 0), z0, z1 + 1.1, z0, z1 + 1.1, 'concrete', u0, (4, 4), grp='e')
        # 1.1 m upstand (parapet / railing base) along the curb edge [inf]: inner face and cap
        mb.quad_wall(Buv(u1, v0 + 0.3, 0), Buv(u0, v0 + 0.3, 0), z1, z1 + 1.1, z1, z1 + 1.1, 'concrete', -u1, (4, 4), grp='r')
        mb.face([Buv(u0, v0, z1 + 1.1), Buv(u1, v0, z1 + 1.1), Buv(u1, v0 + 0.3, z1 + 1.1), Buv(u0, v0 + 0.3, z1 + 1.1)], 'concrete',
                [(0, 0), (1, 0), (1, 1), (0, 1)], False, 'rc')
    for u, sg in ((-HALL_HL, -1), (HALL_HL, 1)):
        a, b = (Buv(u, v1, 0), Buv(u, v0, 0)) if sg < 0 else (Buv(u, v0, 0), Buv(u, v1, 0))
        mb.quad_wall(a, b, z0, z1, z0, z1, 'concrete', 0, (4, 4))
    return mb


def hall_podium():
    """levels 1-2 under the hall (services, arrivals [pub]): faces only, heights / openings not dimensioned [unk]:
    concrete with a dark arrivals glazing band 3.5-8.5 m [unk] on the west face, set at the wall line."""
    mb = MB('hall_podium')
    U = wall_u_breaks()
    for u0, u1 in zip(U[:-1], U[1:]):
        a, b = Buv(u0, V_W, 0), Buv(u1, V_W, 0)
        for z0, z1, mat in ((0, 3.5, 'concrete'), (3.5, 8.5, 'glass_dark'), (8.5, L3 - CURB_THK, 'concrete')):
            mb.quad_wall(a, b, z0, z1, z0, z1, mat, u0, (6.096, 4.4) if 'glass' in mat else (4, 4), grp='p')
    for u, sg in ((-HALL_HL, -1), (HALL_HL, 1)):
        a, b = (Buv(u, V_E, 0), Buv(u, V_W, 0)) if sg < 0 else (Buv(u, V_W, 0), Buv(u, V_E, 0))
        mb.quad_wall(a, b, 0, L3, 0, L3, 'concrete', 0, (4, 4))
    return mb


TUCK = 0.1    # walls that meet the soffit end 0.1 m INSIDE the 0.6-m deck: the soffit is piecewise linear between the roof
              # stations, so a wall top exactly on roof_us(u) at other stations leaves mm slits (back-face QA, view bag, r1)


def end_wall_poly(u):
    top = roof_us(u) + TUCK    # up into the deck slab (no slit under the soffit)
    return [(V_W, L3), (V_E, L3), (V_E, top), (V_UP, top), (V_UP, head(u)), (V_W, head(u))]


def hall_end_walls():
    """end curtain walls under the roof at u = +-HALL_HL ('custom unitized curtain walls spanning over 60 ft' [pub
    Enclos]; outline and mullions not published [unk]): from level 3 to the roof underside, the trusses pass through."""
    mb = MB('hall_end_walls')
    for u, sg in ((-HALL_HL, -1), (HALL_HL, 1)):
        ring = end_wall_poly(u)
        P = Polygon(ring)
        for t in tri_poly(P):
            # t is CCW in (v, z); the (u, v, z) frame is right-handed: a CCW (v, z) polygon faces +u
            pts = t if sg > 0 else t[::-1]
            mb.face([Buv(u, v, z) for v, z in pts], 'glass_tinted', [(v / 6.096, z / 4.4) for v, z in pts], False, 'e%d' % sg)
    return mb


def hall_end_mullions():
    mb = MB('hall_end_mullions')
    for u, sg in ((-HALL_HL, -1), (HALL_HL, 1)):
        nU = np.array(Buv(u + sg, 0, 0)[:2]) - np.array(Buv(u, 0, 0)[:2])
        dV = np.array(Buv(u, 1, 0)[:2]) - np.array(Buv(u, 0, 0)[:2])
        top = roof_us(u) - 0.05
        for v in np.arange(V_W + 3.048, V_E - 1.0, 6.096):
            z1 = top if v > V_UP else head(u)
            c = np.array(Buv(u, v, 0)[:2]) + nU * 0.2
            boxm(mb, c, nU, 0.4, 0.25, (L3, z1), 'mullion')
        for z in np.arange(L3 + 4.4, top - 0.5, 4.4):
            v0 = V_W if z < head(u) else V_UP
            c = np.array(Buv(u, (v0 + V_E) / 2, 0)[:2]) + nU * 0.15
            boxm(mb, c, dV, V_E - v0, 0.3, (z - 0.12, z + 0.12), 'mullion', bottom=True)
    return mb


def hall_east_clerestory():
    """east side of the hall above the core block: glazed clerestory at V_E from H_CORE to the roof underside
    ("elongated skylights and clerestories" [pub SOM]; position and glazing [inf])."""
    mb = MB('hall_east_clerestory')
    U = sorted(set(wall_u_breaks()) | set(np.arange(-HALL_HL, HALL_HL, 3.0).round(3).tolist()))
    for u0, u1 in zip(U[:-1], U[1:]):
        a, b = Buv(u0, V_E, 0), Buv(u1, V_E, 0)
        mb.quad_wall(b, a, H_CORE, roof_us(u1) + TUCK, H_CORE, roof_us(u0) + TUCK, 'glass_tinted', -u1, (6.096, 4.4), grp='c')
    return mb


# ---------------------------------------------------------------------------- core block, piers, pods, box
def largest(g):
    if isinstance(g, Polygon): return g
    return max((q for q in g.geoms if isinstance(q, Polygon)), key=lambda q: q.area)


def sfom_poly(name, key):
    return unary_union([Polygon(p[0], p[1:]).buffer(0) for p in D.sfom(name, key)])


PIER_A = sfom_poly('Boarding Area A', 'boardingAreas')
PIER_G = sfom_poly('Boarding Area G', 'boardingAreas')
ITB_ALL = sfom_poly('International Terminal', 'terminals')
# the outlines tools/stands/check_stands.py tests aircraft and bridges against (terminalComplex + boarding areas): every
# airside part of this asset stays inside them, so the stand / bridge checks carry over unchanged
AIRSIDE = unary_union([Polygon(p[0], p[1:]).buffer(0) for p in list(D.AIR['terminalComplex']) +
                       [q for b in D.AIR['boardingAreas'] for q in b['polys']]])


def hall_rect_world(v_west=-HW - 40.0):
    pts = [UVw(-HALL_HL, v_west), UVw(HALL_HL, v_west), UVw(HALL_HL, V_E), UVw(-HALL_HL, V_E)]
    return Polygon(pts)


def core_polys():
    """ITB core = the SFO Museum 'International Terminal' outline minus Boarding Areas A / G (both inside it) minus the hall
    (under the roof, west of the clerestory line); slivers < 150 m2 dropped."""
    g = ITB_ALL.intersection(AIRSIDE).difference(PIER_A).difference(PIER_G).difference(hall_rect_world())
    parts = [p for p in (g.geoms if hasattr(g, 'geoms') else [g]) if isinstance(p, Polygon) and p.area > 150]
    out = []
    for p in parts:
        p = p.buffer(0.01).buffer(-0.01).simplify(0.05).intersection(p)
        out.extend([q for q in (p.geoms if hasattr(p, 'geoms') else [p]) if isinstance(q, Polygon) and q.area > 150])
    return out


def attach_groups(letter):
    """bridge attach points of the stands at one pier (data/sfo_stands.json; OSM / NAIP survey), L1 / L2 / upper of a
    stand merged: gate-room glazing is centred on them [inf]."""
    d = json.load(open(os.path.join(ROOT, 'data', 'sfo_stands.json')))
    out = []
    for s in d['stands']:
        if s['letter'] != letter: continue
        pts = [b['attach'] for b in s['bridges'] + s.get('bridges_upper', [])]
        if pts: out.append((s['name'], np.mean(np.asarray(pts, float), axis=0)))
    return out


def extruded_block(name, poly_world, h, wall_bands, roof_mat='roof_membrane_pier', glaze=None, parapet=True, grp_tile=(6.096, 6.096)):
    """extrude a world polygon: walls 0..h in bands [(z0, z1, mat)], optional glazed intervals [(edge test fn)] replacing
    the material in bands flagged 'gl'; parapet (outer wall to h, inner face, cap) and the roof deck at h - PARAPET."""
    mb = MB(name)
    P = to_blender_poly(poly_world)
    Ps = P.geoms if hasattr(P, 'geoms') else [P]
    for Pi in Ps:
        for ring in rings_of(Pi):
            # rings_of: exterior CCW, interiors CW (shapely orient) -> outward walls for both with a->b, normal right
            s = 0.0
            for i in range(len(ring)):
                a, b = ring[i], ring[(i + 1) % len(ring)]
                L = math.hypot(b[0] - a[0], b[1] - a[1])
                if L < 1e-3: continue
                cuts = [(0.0, L, False)]
                if glaze:
                    cuts = glaze(a, b, L)
                for t0, t1, gl in cuts:
                    if t1 - t0 < 1e-3: continue
                    pa = (a[0] + (b[0] - a[0]) * t0 / L, a[1] + (b[1] - a[1]) * t0 / L)
                    pb = (a[0] + (b[0] - a[0]) * t1 / L, a[1] + (b[1] - a[1]) * t1 / L)
                    for z0, z1, mat, glmat in wall_bands:
                        m = glmat if (gl and glmat) else mat
                        if m == 'glass_gate':
                            # gate-room curtain wall: tile origin at the bay start and the glazing foot (itb_c_curtain_gate)
                            tu, tv = GATE_TILE; Lq = t1 - t0
                            mb.face([(pa[0], pa[1], z0), (pb[0], pb[1], z0), (pb[0], pb[1], z1), (pa[0], pa[1], z1)], m,
                                    [(0.0, 0.0), (Lq / tu, 0.0), (Lq / tu, (z1 - z0) / tv), (0.0, (z1 - z0) / tv)])
                            continue
                        mb.quad_wall(pa, pb, z0, z1, z0, z1, m, s + t0, grp_tile if 'glass' not in m else (6.096, 4.4))
                s += L
        if parapet:
            inner = Pi.buffer(-PARAPET_T, join_style=2)
            ins = inner.geoms if hasattr(inner, 'geoms') else [inner]
            ring_poly = Pi.difference(inner)
            cap(mb, ring_poly, h, 'coping', 1.0)
            for q in ins:
                q = orient(q, 1.0)
                for ring in rings_of(q):
                    for i in range(len(ring)):
                        a, b = ring[i], ring[(i + 1) % len(ring)]
                        mb.quad_wall(b, a, h - PARAPET, h, h - PARAPET, h, 'coping', 0, (3, 3))
                cap(mb, q, h - PARAPET, roof_mat, 12.0)
        else:
            cap(mb, Pi, h, roof_mat, 12.0)
    return mb


def glaze_fn(groups, width=GATEROOM_W, tol=2.5):
    """edge splitter: intervals of an outline edge (Blender XY a->b) within tol of an attach point get the glazing."""
    G = [B(p[0], p[1], 0)[:2] for _, p in groups]

    def f(a, b, L):
        d = np.array([(b[0] - a[0]) / L, (b[1] - a[1]) / L]); a_ = np.array(a)
        iv = []
        for g in G:
            r = np.array(g) - a_; t = float(r @ d); off = abs(float(r[0] * d[1] - r[1] * d[0]))
            if -width / 2 < t < L + width / 2 and off < tol:
                iv.append((max(0.0, t - width / 2), min(L, t + width / 2)))
        iv.sort()
        merged = []
        for x in iv:
            if merged and x[0] <= merged[-1][1]: merged[-1] = (merged[-1][0], max(merged[-1][1], x[1]))
            else: merged.append(x)
        out, cur = [], 0.0
        for t0, t1 in merged:
            if t0 > cur: out.append((cur, t0, False))
            out.append((t0, t1, True)); cur = t1
        if cur < L: out.append((cur, L, False))
        return out
    return f


def pier_st(key, x, z):
    """world (x, z) -> pier frame (s along the pier, t across) of itb_pods.json piers[key]."""
    P = PIERS[key]; c = np.asarray(P['centre_xz'], float)
    d = np.array([x, z], float) - c
    return float(d @ np.asarray(P['s_axis'], float)), float(d @ np.asarray(P['t_axis'], float))


def pier_faces(key):
    """the two main faces of a pier as lines t = t0 + k s fitted to the outline vertices that lie on them (BA-G: t ~ -0.8 /
    37.5; BA-A: -17.4 / 21.4), the vertices outside the root connector and the tip."""
    poly = PIER_A if key == 'A' else PIER_G
    R = np.asarray(largest(poly).exterior.coords)
    st = np.array([pier_st(key, *p) for p in R])
    # edges running along the pier (|dt| < 0.5, > 3 m), binned by t: the main faces carry the most edge length (BA-G NNE:
    # ~270 m against ~79 m of bump-out fronts)
    lev = {}
    for p, q in zip(st[:-1], st[1:]):
        if abs(q[1] - p[1]) < 0.5 and abs(q[0] - p[0]) > 3.0:
            b = int(round((p[1] + q[1]) / 2))
            lev[b] = lev.get(b, 0.0) + abs(q[0] - p[0])
    tmid = np.median(st[:, 1])
    out = []
    for side in (-1, 1):
        cand = {b: L for b, L in lev.items() if (b - tmid) * side > 0}
        b = max(cand, key=cand.get)
        sel = st[np.abs(st[:, 1] - b) < 1.5]
        k, t0 = np.polyfit(sel[:, 0], sel[:, 1], 1)
        out.append((float(t0), float(k), float(sel[:, 0].min()), float(sel[:, 0].max())))
    return out    # [(t0, k, s_min, s_max)] for the -t face and the +t face


def bumpouts(key):
    """bridge-head bump-outs of a pier outline: the pieces of the outline outside the band between the two main-face lines,
    10-22 m along the face and 6-14 m deep (BA-G: 10 incl. the root and tip ones, BA-A: 8), as [(face 0/1, s0, s1, polygon
    world)]."""
    poly = largest(PIER_A if key == 'A' else PIER_G)
    P = PIERS[key]; c = np.asarray(P['centre_xz'], float); sa = np.asarray(P['s_axis'], float); ta = np.asarray(P['t_axis'], float)
    (ta0, ka, sa_min, sa_max), (tb0, kb, sb_min, sb_max) = pier_faces(key)
    W = lambda s, t: tuple(c + sa * s + ta * t)  # noqa: E731
    out = []
    for face, (t0, k, smin, smax), sg in ((0, (ta0, ka, sa_min, sa_max), -1), (1, (tb0, kb, sb_min, sb_max), 1)):
        S0, S1 = smin - 2.0, smax + 2.0
        # cut 0.5 m outside the fitted face line (the face vertices scatter +-0.2 m), then rebuild each piece over its s-range
        # from the face line itself, so the body / bump-out boundary is the straight face line
        off = sg * 0.5
        half = Polygon([W(S0, t0 + k * S0 + off), W(S1, t0 + k * S1 + off), W(S1, t0 + k * S1 + sg * 20), W(S0, t0 + k * S0 + sg * 20)])
        g = poly.intersection(half)
        for q in (g.geoms if hasattr(g, 'geoms') else [g]):
            if not isinstance(q, Polygon) or q.area < 50: continue
            st = np.array([pier_st(key, *p) for p in np.asarray(q.exterior.coords)])
            s0, s1 = st[:, 0].min(), st[:, 0].max()
            w = s1 - s0; dpt = np.abs(st[:, 1] - (t0 + k * st[:, 0])).max()
            if 10.0 <= w <= 22.0 and 6.0 <= dpt <= 14.0 and q.area < 300:
                rect = Polygon([W(s0, t0 + k * s0), W(s1, t0 + k * s1), W(s1, t0 + k * s1 + sg * 20), W(s0, t0 + k * s0 + sg * 20)])
                full = largest(poly.intersection(rect))
                out.append((face, float(s0), float(s1), full))
    return sorted(out, key=lambda b: (b[0], b[1]))


def gate_rooms(key):
    """main-face segments between consecutive bump-outs that one roof pod overlaps by >= GATE_POD_MIN (BA-G: 3 per face = the
    six double-gated gate rooms [pub]): [(face, s0, s1, pod id, overlap m)]."""
    pods = []
    for p, g in pod_polys(key):
        st = np.array([pier_st(key, *q) for q in np.asarray(g.exterior.coords)])
        pods.append((p['id'], st[:, 0].min(), st[:, 0].max()))
    out = []
    bo = bumpouts(key); faces = pier_faces(key)
    for face in (0, 1):
        # segment ends: the bump-outs and the two ends of the face line (root connector, tip)
        b = [(None, None, faces[face][2], None)] + [x for x in bo if x[0] == face] + [(None, faces[face][3], None, None)]
        for (_, _, e0, _), (_, s1, _, _) in zip(b[:-1], b[1:]):
            if s1 - e0 < 10: continue
            best = max(((pid, min(e0b, s1) - max(e0, s0b)) for pid, s0b, e0b in pods), key=lambda x: x[1])
            if best[1] >= GATE_POD_MIN:
                out.append((face, e0, s1, best[0], round(float(best[1]), 1)))
    return out


def gate_glaze_fn(key):
    """edge splitter for the main body: the parts of a main-face edge (Blender XY a->b) inside a gate-room segment."""
    faces = pier_faces(key); rooms = gate_rooms(key)

    def f(a, b, L):
        xa, za = a[0] + OX, OZ - a[1]; xb, zb = b[0] + OX, OZ - b[1]
        sa_, ta_ = pier_st(key, xa, za); sb_, tb_ = pier_st(key, xb, zb)
        if abs(sb_ - sa_) < 0.5: return [(0.0, L, False)]
        for face, (t0, k, _, _) in enumerate(faces):
            if abs(ta_ - (t0 + k * sa_)) < 0.3 and abs(tb_ - (t0 + k * sb_)) < 0.3:
                break
        else:
            return [(0.0, L, False)]
        iv = []
        for fc, s0, s1, _, _ in rooms:
            if fc != face: continue
            lo, hi = sorted(((s0 - sa_) / (sb_ - sa_) * L, (s1 - sa_) / (sb_ - sa_) * L))
            lo, hi = max(0.0, lo), min(L, hi)
            if hi - lo > 0.5: iv.append((lo, hi))
        out, cur = [], 0.0
        for t0_, t1_ in sorted(iv):
            if t0_ > cur: out.append((cur, t0_, False))
            out.append((t0_, t1_, True)); cur = t1_
        if cur < L: out.append((cur, L, False))
        return out
    return f


def pier_body(key, lod=0):
    """pier body extruded from the SFO Museum outline [obs]. Facade bands (review r1, photo a2 = the BA-G NNE face): dark
    apron level 0..APRON_TOP, light band, gate-room curtain walls GLAZE_BOT..GLAZE_TOP2 (glass_gate), metal panels above.
    BA-G: the bridge-head bump-outs are low boxes (BUMP_H_G) [obs a2] and the curtain walls fill the gate-room segments
    between them (gate_rooms) [obs a2 NNE face, inf SSW face]. BA-A: no reference photo of its facades (a2 shows BA-G):
    bump-outs kept at the full outline height and the round-0 bays (24 m centred on the bridge attach points) kept [unk],
    with the BA-G band heights [inf, analogy]."""
    P = PIERS[key]; h = float(P['h_main_roof'])
    poly = PIER_A if key == 'A' else PIER_G
    if lod == 2:
        poly = largest(poly.simplify(1.0).intersection(poly))
        if key == 'G':
            bo = unary_union([b[3] for b in bumpouts('G')]).buffer(0.01)
            body = largest(poly.difference(bo))
            mb = extruded_block('ba_g_body', body, h, [(0, h, 'alu_panel', None)], parapet=False)
            for b in bumpouts('G'):
                mb.merge(extruded_block('bump', b[3].intersection(poly).buffer(-0.02, join_style=2), BUMP_H_G, [(0, BUMP_H_G, 'alu_panel', None)], parapet=False))
            return mb
        return extruded_block('ba_%s_body' % key.lower(), poly, h, [(0, h, 'alu_panel', None)], parapet=False)
    bands = [(0, APRON_TOP, 'service_dark', None), (APRON_TOP, GLAZE_BOT, 'alu_panel', None),
             (GLAZE_BOT, GLAZE_TOP2, 'alu_panel', 'glass_gate'), (GLAZE_TOP2, h, 'alu_panel', None)]
    if key == 'A':
        return extruded_block('ba_a_body', poly, h, bands, glaze=glaze_fn(attach_groups('A')))
    bo = bumpouts('G')
    body = largest(poly.difference(unary_union([b[3] for b in bo]).buffer(0.01)))
    body = body.buffer(0.01, join_style=2).buffer(-0.01, join_style=2).intersection(poly)
    mb = extruded_block('ba_g_body', largest(body), h, bands, glaze=gate_glaze_fn('G'))
    for b in bo:
        mb.merge(extruded_block('bump', b[3], BUMP_H_G, [(0, APRON_TOP, 'service_dark', None), (APRON_TOP, BUMP_H_G, 'alu_panel', None)],
                                parapet=False, roof_mat='roof_membrane_pier'))
    return mb


def pod_polys(key):
    body = (PIER_A if key == 'A' else PIER_G).buffer(-0.5)
    out = []
    for p in PODS['pods']:
        if p['pier'] != key or p['id'].endswith('box'): continue
        g = Polygon(p['ring_true_xz']).buffer(0).intersection(body)
        out.append((p, g))
    return out


def pier_pods(key, lod=0):
    """raised roof pods traced on NAIP 2024 (itb_pods.json, relief-corrected) [obs], from the roof deck to their band
    tops [obs, low]; vertical walls of metal panels and a flat roof (photo a2) [inf]."""
    mb = MB('ba_%s_pods' % key.lower())
    h = float(PIERS[key]['h_main_roof'])
    for p, g in pod_polys(key):
        top = float(p['top_m'])
        g = g.simplify(0.15 if lod < 2 else 0.8)
        sub = extruded_block('pod', g, top, [(h - PARAPET, top - 0.6, 'alu_panel_pod', None), (top - 0.6, top, 'coping', None)],
                             parapet=False)
        mb.merge(sub)
    return mb


def g3_box(lod=0):
    """BA-G pod-3 end box (itb_pods.json G3-box: ~8 x 9 m, top 32.0 m (30.5-33.4) [obs, low]); a dark window band
    top - 2.6 .. top - 1.2 (photo d2, schematic) [inf]; function ramp-control cab [inf, unconfirmed]."""
    bx = POD['G3-box']; base = float(POD['G3']['top_m']); top = float(bx['top_m'])
    g = Polygon(bx['ring_true_xz'])
    bands = [(base, top - 2.6, 'alu_panel_pod', None), (top - 2.6, top - 1.2, 'glass_dark', None), (top - 1.2, top, 'alu_panel_pod', None)]
    if lod == 2: bands = [(base, top, 'alu_panel_pod', None)]
    mb = extruded_block('ba_g_box', g, top, bands, parapet=False, roof_mat='roof_membrane_pier')
    return mb


def g3_box_antennas():
    """antennas on the box (photo d2: several whips) - count / positions schematic [inf]."""
    mb = MB('ba_g_box_antennas')
    bx = POD['G3-box']; top = float(bx['top_m'])
    R = np.asarray(bx['ring_true_xz'], float); c = R.mean(0)
    for f in (-0.3, 0.0, 0.3):
        p = c + (R[1] - R[0]) * f
        x, y, _ = B(p[0], p[1], 0)
        tube(mb, [(x, y, top), (x, y, top + 5.0)], 0.06, 6, 'steel_grey')
    return mb


def core_block(lod=0):
    """ITB core outside the hall (east block, north / south bars): extruded to H_CORE [unk]; metal panels with a window
    band at the departures level [unk]."""
    mb = MB('itb_core')
    for g in core_polys():
        if lod == 2:
            g = largest(g.simplify(1.0).intersection(g))
            sub = extruded_block('c', g, H_CORE, [(0, H_CORE, 'alu_panel', None)], parapet=False)
        else:
            sub = extruded_block('c', g, H_CORE, [(0, L3 - 0.5, 'alu_panel', None), (L3 - 0.5, L3 + 3.5, 'glass_dark', None),
                                                  (L3 + 3.5, H_CORE, 'alu_panel', None)])
        mb.merge(sub)
    return mb


# ------------------------------------------------------------------------------------------------ assembly
SPEC_ROOF = ['roof.corners_obs', 'roof.length_obs', 'roof.width_obs', 'roof.axis_obs', 'roof.profile', 'roof.truss_lines_obs',
             'roof.truss_spacing_obs', 'roof.lenses_obs', 'roof.glazed_tips_obs', 'roof.dof_06-035315', 'roof.dof_06-035316']


def build(lod):
    """parts of one LOD: {name: Part}."""
    P = {}
    det = lod < 2
    tl = dict(
        hall_roof=dim([round(F['L'], 2), round(F['W'], 2)], 'obs', 'spec roof.corners_obs (NAIP 2024 frame-model relief correction)'),
        profile=dim('roof_line(u): notch 35.7, humps 40.08, crown 40.1, tip 34.4', 'obs', 'BI-02 / spec roof.profile (NAIP eave relief, DOF-anchored [inf])'),
        thickness=dim(ROOF_THK, 'inf', 'BI-02 top-chord line 0.6 m below the roof line; fascia depth unknown'),
        camber=dim('flat across v', 'unk', 'cross camber unknown (BI-02 V2, BI-03 V2 draw it flat)'),
        strips=dim(STRIP_W, 'obs', 'glazed truss-line strips, NAIP 2024 (rough width)'),
        lenses=dim([[round(2 * L['a'], 2), round(2 * L['b'], 2)] for L in LENSES], 'obs', 'spec roof.lenses_obs (planform: pointed lens [inf])'),
        tip_bands=dim([I.TN, I.TS], 'obs', 'spec roof.glazed_tips_obs, ending 1.6 / 3.6 m inside the fascia'))
    P['hall_roof'] = Part('hall_roof', hall_roof(2.0 if lod < 2 else 8.0, detail=det), 'shell', 'obs', 'main hall wing roof (deck, glazing, fascia, soffit)',
                          SPEC_ROOF, tl)
    if lod < 2:
        P['hall_trusses'] = Part('hall_trusses', hall_trusses(lod), 'detail', 'inf', '5 three-chord football trusses',
                                 ['roof.form', 'roof.truss_depth', 'roof.truss_lines_obs', 'roof.centre_section', 'roof.cantilever_end'],
                                 dict(lines=dim(LINES_V, 'obs', 'spec roof.truss_spacing_obs 12.12 m'),
                                      depth=dim(29 * FT, 'pub', 'SEAONC: up to 29 ft over the supports; taper [inf] (BI-03 depth(u))'),
                                      west_bottom_chord=dim('max(BI-02 chord(u), BI-03 roof_line - depth(u))', 'inf', 'BI-02 V1 / BI-03 V1; photos i3 / i4 (sweep up to the notch)'),
                                      centre_chord=dim('sagging bowstring: deck at the notches -> WH + 2 at u = 0', 'inf', 'photos i3 / i4 (form); BI-03: unknown'),
                                      centre_section=dim(180, 'pub', 'ft, snippet; bowstring chord form [unk] (BI-03)'),
                                      panel=dim(20 * FT, 'inf', '20-ft node grid offset 10 ft (columns, hangers on it)'),
                                      tube_radii=dim([R_BOT, R_TOP, R_WEB], 'inf', 'photos i3 / i4')))
        P['hall_outriggers'] = Part('hall_outriggers', hall_outriggers(lod), 'detail', 'inf', 'eave outriggers under the soffit',
                                    ['roof.form'], dict(spacing=dim(20 * FT, 'inf', 'photo i3 (regular spacing)')))
        P['hall_columns'] = Part('hall_columns', hall_columns(lod), 'detail', 'inf', '20 columns, west line branching into 5 members',
                                 ['roof.columns', 'roof.col_positions_inf', 'roof.rhythm_inf'],
                                 dict(count=dim(20, 'pub', 'SEAONC'), u=dim([57.9, 82.3], 'inf', '+-190 / +-270 ft (spec roof.col_positions_inf)'),
                                      west_v=dim(V_COL, 'inf', 'BI-01 / BI-03: 2.5 m in front of the wall'),
                                      fan=dim(5, 'obs', 'photos i3 / i4 (post + 2 per side); geometry inf')))
    P['hall_west_wall'] = Part('hall_west_wall', hall_west_wall(), 'shell', 'inf', 'west glass wall, head closure, upper glazing',
                               ['facade.west', 'level3.floor'],
                               dict(v=dim(V_W, 'inf', 'BI-01: middle of the band v %.1f..%.1f (NAIP line [obs] = canopy edge / wall above)' % tuple(I.WALL['band'])),
                                    length=dim(2 * HALL_HL, 'pub', '705 ft great hall (SEAONC), centred [inf]'),
                                    L3=dim(L3, 'inf', 'level3.floor 11.5 (9.6-14.8)'),
                                    head=dim(WH, 'obs', 'photo i4: 9.3 m below the wing crest (+-1.5)'),
                                    central_bay=dim([2 * I.BAY_HW, I.BAY_HEAD], 'obs', 'photos i1 / i4 (+-39 / +-42 m; head +2 m tentative)'),
                                    upper_glazing_v=dim(V_UP, 'inf', 'photo i3: glazing behind the exposed truss')))
    P['hall_canopy'] = Part('hall_canopy', hall_canopy(), 'shell', 'inf', 'curb (entrance) canopy',
                            ['facade.west'], dict(top=dim(CANOPY, 'inf', 'L3 + 5 (photos i3 / i4)'), depth=dim(CANOPY_D, 'inf', 'photos'),
                                                  exists=dim(True, 'pub', 'SEAONC "entrance canopy"')))
    P['hall_curb'] = Part('hall_curb', hall_curb(), 'shell', 'inf', 'departures curb sidewalk (L3)', ['level3.floor'],
                          dict(width=dim(CURB_W, 'inf', 'under the canopy + 2 m'), level=dim(L3, 'inf', 'level3.floor')))
    P['hall_podium'] = Part('hall_podium', hall_podium(), 'shell', 'unk', 'levels 1-2 under the hall (faces only)', ['itb.levels'],
                            dict(levels=dim('L1 services, L2 arrivals', 'pub', 'sfgate2000'), facade=dim('concrete / glazing band', 'unk', 'not dimensioned')))
    P['hall_end_walls'] = Part('hall_end_walls', hall_end_walls(), 'shell', 'inf', 'end curtain walls (u = +-107.4)', ['facade.end_walls', 'hall.size_snippet'],
                               dict(u=dim(HALL_HL, 'inf', '705-ft hall centred in the roof'), outline=dim('L3 to the roof underside', 'unk', 'not published')))
    P['hall_east_clerestory'] = Part('hall_east_clerestory', hall_east_clerestory(), 'shell', 'inf', 'east clerestory above the core block',
                                     ['facade.west'], dict(v=dim(V_E, 'inf', '1 m inside the east eave'), base=dim(H_CORE, 'unk', 'core block top')))
    if lod == 0:
        P['hall_mullions'] = Part('hall_mullions', hall_mullions(), 'detail', 'obs', 'west wall mullions / transoms', ['facade.west'],
                                  dict(module=dim(20 * FT, 'obs', 'photo i4 ~6.1 m (low)'), transoms=dim(2.2, 'obs', 'photo i4 (low)')))
        P['hall_end_mullions'] = Part('hall_end_mullions', hall_end_mullions(), 'detail', 'unk', 'end wall mullions', ['facade.end_walls'],
                                      dict(module=dim([6.096, 4.4], 'unk', 'not published')))
    elif lod == 1:
        # review r1 (LOD pop at 450 m): the same mullions, west + end walls joined into one node (one draw call)
        mm = hall_mullions(); mm.merge(hall_end_mullions()); mm.name = 'hall_mullions'
        P['hall_mullions'] = Part('hall_mullions', mm, 'detail', 'obs', 'west wall + end wall mullions (joined)', ['facade.west', 'facade.end_walls'],
                                  dict(module=dim(20 * FT, 'obs', 'photo i4 ~6.1 m (low)'), transoms=dim(2.2, 'obs', 'photo i4 (low)'),
                                       end_module=dim([6.096, 4.4], 'unk', 'not published')))
    if lod < 2:
        P['hall_hangers'] = Part('hall_hangers', hall_hangers(lod), 'detail', 'obs', 'canopy hangers and posts', ['facade.west'],
                                 dict(u=dim([round(u, 2) for u in I.HANGER_U], 'obs', 'photo i4: 40-ft grid + +-30 / +-90 ft'),
                                      apex=dim(I.HANGER_H, 'obs', 'photo i4, rough'), form=dim('inclined pair + post', 'inf', 'schematic')))
    P['itb_core'] = Part('itb_core', core_block(lod), 'shell', 'unk', 'ITB core: east block and north / south bars',
                         ['itb.stories', 'itb.levels'], dict(outline=dim('SFO Museum International Terminal - piers - hall', 'obs', 'data/sfo_airport.json'),
                                                           height=dim(H_CORE, 'unk', 'no source; = BA-A main roof [obs] as placeholder')))
    for key in ('A', 'G'):
        Pk = PIERS[key]; k = key.lower()
        P['ba_%s_body' % k] = Part('ba_%s_body' % k, pier_body(key, lod), 'shell', 'obs', 'Boarding Area %s pier body' % key,
                                   ['ba_%s.height_roof' % k, 'ba_%s.footprint' % k] + (['ba_g.facade'] if key == 'G' else []),
                                   dict(outline=dim('SFO Museum %s' % Pk['name'], 'obs', 'data/sfo_airport.json'),
                                        h=dim(Pk['h_main_roof'], 'obs', 'NAIP relief / shadow band, range %s' % Pk['h_main_range']),
                                        parapet=dim(PARAPET, 'inf', 'roof deck 1 m below the measured roof edge'),
                                        glazing=dim([GLAZE_BOT, GLAZE_TOP2], 'obs' if key == 'G' else 'inf',
                                                    'photo a2 = the BA-G NNE face (camera solved, review r1)' if key == 'G' else
                                                    'no BA-A photo: the BA-G heights by analogy'),
                                        apron_level=dim([0.0, APRON_TOP], 'obs' if key == 'G' else 'inf', 'photo a2 (BA-G)'),
                                        bays=(dim('main-face segments between the bump-outs under a pod (>= %.0f m overlap): %d rooms' % (GATE_POD_MIN, len(gate_rooms('G'))),
                                                  'obs', 'photo a2 NNE face (s 9.6..73.2, -133.1..-69.6 imaged); SSW face and G3 inf') if key == 'G' else
                                              dim(GATEROOM_W, 'unk', 'round-0 placeholder: 24 m centred on the bridge attach points (no BA-A photo)')),
                                        **({'bumpouts': dim(BUMP_H_G, 'obs', 'photo a2: bridge-head boxes 6.5 m (B1 measured, low)')} if key == 'G' else {})))
        P['ba_%s_pods' % k] = Part('ba_%s_pods' % k, pier_pods(key, lod), 'shell', 'obs', 'Boarding Area %s roof pods' % key,
                                   ['ba_%s.pods' % k] + (['ba_a.dof_pod'] if key == 'A' else []),
                                   dict(outline=dim('itb_pods.json ring_true_xz', 'obs', 'NAIP 2024 trace, relief-corrected'),
                                        tops=dim([p['top_m'] for p, _ in pod_polys(key)], 'obs', 'NAIP WNW band (low)'),
                                        **({'dof_conflict': dim(85 * FT, 'pub', 'DOF 06-035352 pod-1 top 25.91 m: NAIP 22.1-25.0 (drawn 23.6)')} if key == 'A' else {})))
    P['ba_g_box'] = Part('ba_g_box', g3_box(lod), 'shell', 'obs', 'BA-G pod-3 end box (probable ramp-control cab)', ['ba_g.pod3_end_box'],
                         dict(top=dim(POD['G3-box']['top_m'], 'obs', 'NAIP band (30.5-33.4, low)'), function=dim('ramp-control cab', 'inf', 'photo d2 + LiveATC; unconfirmed'),
                              window_band=dim('top-2.6..top-1.2', 'inf', 'photo d2 schematic')))
    if lod == 0:
        P['ba_g_box_antennas'] = Part('ba_g_box_antennas', g3_box_antennas(), 'detail', 'inf', 'antennas on the end box (schematic)', ['ba_g.pod3_end_box'])
    return P


if __name__ == '__main__':
    import time
    for lod in (0, 1, 2):
        t = time.time(); P = build(lod)
        print('LOD', lod, 'parts', len(P), 'tris', sum(p.mb.tris() for p in P.values()), '%.1f s' % (time.time() - t))
        for n, p in P.items():
            print('   %-22s %-6s %6d tris  mats %s' % (n, p.kind, p.mb.tris(), sorted(set(p.mb.M))))
