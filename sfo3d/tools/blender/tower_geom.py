"""Procedural geometry of the SFO air traffic control tower (2016) and its base building (IBF), for the 3-D asset
data/buildings3d/tower.glb (tools/blender/build_tower.py). Pure numpy: no bpy here, so the same geometry can be checked
against the 2-D sheets without Blender (tools/blender/tower3d_verify.py).

Every dimension comes from the drawn geometry of the approved 2-D sheets BT-01..03 (tools/buildings/draw_tower.py,
which reads tools/buildings/spec_tower.json and data/sfo_airport.json). Nothing is re-measured here except the roof
garden outline (NAIP 2024, see GARDEN below), and nothing is typed in twice: the stations, radii, slot / mast bearings,
ribbon, blades, plinth and the base-building faces are taken from draw_tower's constants and functions.

Frame (local, metres): origin = the inferred shaft axis (draw_tower.AXIS, world (-740.5, 324.5)) at grade; X = east,
Y = north, Z = up (Blender's frame; the glTF exporter turns it into the app's x east / y up / z south, and the root node
is placed at world (AXIS.x, GROUND_Y, AXIS.z) by build_tower.py). Bearings are clockwise from north: bvec(b) = (sin b, cos b).

Two height families (buildings_tower.md 12.3, README "Two height sets"): F1 (D 15.2, rim 67.36 = 221 ft) and F2 (D 14.5,
rim 64.0, 221 ft at the mast tips). The sheets draw both and prefer neither; build() takes the family, the builder
writes tower.glb (F1) and tower_f2.glb (F2) and the manifest says that the choice is open.

Level of detail (one geometry generator, three tessellations; LOD0 is the close-up asset):
  LOD0  272 helical columns (4 per cladding joint), half-panel rows, recessed slots with glazed panes, dark seam joints,
        24 frameless cab panes with light joints, ribbon mullions, roof masts / poles / obstruction light, base-building
        mullions, parapet coping, railings, rooftop unit, sunken roof garden;
  LOD1  136 columns, panel rows, flat slots, dark seam joints, 24-facet cab, 15 whips, red light, plain base building;
  LOD2  68 columns, every second panel row, flat slots, 12-facet cab, 15 whips (3-sided), red light, base building as a
        box (phone / far).
Cladding joints (helical and row) are a base-colour + normal tile on UV0 (tools/blender/tower_tex.py), 4 x 2 panels per
tile: UV0 u = joint index / CLAD_TU, v = panel row / CLAD_TV.
"""
import math
import os
import sys

import numpy as np
from scipy.interpolate import PchipInterpolator

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
for _p in (os.path.join(ROOT, 'tools', 'buildings'), os.path.join(ROOT, 'tools')):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import draw_tower as DT  # noqa: E402  (the 2-D sheets' geometry: the reference for this model)

T = DT.T
AXIS = np.asarray(DT.AXIS, float)                     # world (x, z) of the shaft axis [inf]
CAB_W = np.asarray(DT.CAB, float)                     # world (x, z) of the cab-roof centre [inf]
CAB = np.array([CAB_W[0] - AXIS[0], -(CAB_W[1] - AXIS[1])])   # local ENU: (1.5 E, 1.0 N) [inf]
RIGHT_A = DT.hdg_vec(27.7)                            # BT-02 view A (from the ESE, looking WNW): right-hand world vector
RIGHT_B = DT.hdg_vec(207.7)                           # BT-02 view B (from the WNW, looking ESE)
LONG_FOOT_SPEC = T['h_lower_slot']['value'][0]        # 24.7 spec m: the reference station of the helical twist (draw_tower)
RIB_H = T['ribbon_height']['value_m']                 # 147 ft = 44.81 m [pub]
RIB_W0, RIB_W1 = T['ribbon_width']['value']           # 3.2 -> 6.8 m [obs, low]
RIB_ROWS = 25                                         # ribbon rows [obs photos t3 / t4: ~25] (draw_blades)
RIB_INSET = 1.0                                       # ribbon face 1 m inside the round-body radius (draw_tower.rib_shift)
SLOT_DEPTH = 0.25                                     # slot recess depth [inf: photos show dark recessed slots; depth unknown]
PARAPET = DT.PARAPET                                  # 0.7 m: base-building parapet above its roof (spec photo_constraint, assumed)
PARAPET_T = 0.30                                      # parapet / coping thickness [inf]
CAB_PANES = 24                                        # cab glass panes [pub ENR: 24 panels 6 ft x 11 ft]; ring 360 deg [inf]
ROOF_DROP = 0.30                                      # cab roof deck below the rim coping [inf]
COPING_W = 0.15                                       # cab-roof rim coping width [inf: photos show a thin top rim]
CURB_R, CURB_H = 4.75, 0.30                           # cab-roof inner curb ring [inf from NAIP / Google top-view rims r 4.5-5 obs]
RAIL_H = 1.07                                         # guard rails, 42 in [inf: OSHA 1910.29 top-rail height]
RED_LIGHT_BRG = 225.0                                 # red obstruction light on the cab-roof rim, SW side [obs photo t5 (Varnum
                                                      # 0463, dusk); bearing inf]; DOF lighting code R [pub]
GARDEN_DROP = 1.7                                     # roof garden ~1.7 m below the IBF roof [inf: NAIP lean ratio 0.18 vs 0.21]
# Roof garden outline [obs NAIP 2024-05-20, vegetated pixels on the IBF roof, moved back by the frame-model relief of a 12.4 m
# terrace (6.7 m E); +-1 m]: footprint frame s (m from the N corner along the NW face, towards W) 37.0 .. SW parapet,
# t (m from the N corner along the NE face, towards E) 8.5 .. SE parapet; 2,000 sq ft published (Mead & Hunt) [pub].
GARDEN = (37.0, 8.5)
# Rooftop unit next to the shaft foot [obs photo t4 (Famartin 2025-08-12 09:10, bearing 338, 81 m): a white louvred box ~3.1 m
# wide, ~1.8 m tall, 1.1 m right of the shaft silhouette; position inf: on the t4 ray at the axis depth, +-5 m along 158/338]
AHU = dict(s=22.0, t=5.5, L=3.1, W=2.0, H=1.8)
IBF_PANEL = (3.0, 1.2)                                # base-building metal panel module (w, h) [inf: t4 / t2 rough]
GLAZING_MULLION = 1.5                                 # airside glazing band mullion pitch [inf]
CLAD_TU, CLAD_TV = 4, 2                               # cladding tile = 4 joints x 2 panel rows (tower_tex.clad_*: per-panel tone)
SEAM_W = 0.10                                         # the two circumferential seams: a dark recessed joint band, flush in the
                                                      # shell (its own rows) [obs photos t2 / t4: darker than the row joints, a
                                                      # thin light lip above; width ~2-3 px at 0.032 m/px (t2) -> ~0.1 m inf]


def bvec(b):
    r = math.radians(b)
    return np.array([math.sin(r), math.cos(r)])


def world_to_local(p):
    return np.array([p[0] - AXIS[0], -(p[1] - AXIS[1])])


# ------------------------------------------------------------------------------------------------ mesh accumulator
class Part:
    """one glTF node: vertices (local ENU), faces with a material key each, per-vertex UV0 (detail tiling) and the
    node's provenance (extras)."""

    def __init__(self, name, extras, smooth=False, ao=True):
        self.name = name; self.extras = extras; self.smooth = smooth; self.ao = ao
        self.V = []; self.UV = []; self.F = []; self.M = []

    def v(self, p, uv=(0.0, 0.0)):
        self.V.append((float(p[0]), float(p[1]), float(p[2]))); self.UV.append((float(uv[0]), float(uv[1])))
        return len(self.V) - 1

    def f(self, idx, mat):
        self.F.append(tuple(int(i) for i in idx)); self.M.append(mat)

    def tris(self):
        return sum(len(f) - 2 for f in self.F)

    def merge(self, other):
        o = len(self.V)
        self.V += other.V; self.UV += other.UV
        self.F += [tuple(i + o for i in f) for f in other.F]; self.M += other.M


def orient(part, idx, mat, outside_dir=None, inside_pt=None):
    """add face idx with its winding chosen so that the normal points along outside_dir or away from inside_pt."""
    P = np.array([part.V[i] for i in idx])
    n = np.zeros(3)
    for k in range(len(P)):
        n += np.cross(P[k], P[(k + 1) % len(P)])
    ref = outside_dir if outside_dir is not None else P.mean(0) - np.asarray(inside_pt, float)
    if np.dot(n, ref) < 0:
        idx = idx[::-1]
    part.f(idx, mat)


def box(part, c, ax, ay, az, mat, uvs=1.0, skip=()):
    """oriented box: centre c, half-axes ax / ay / az (3-vectors); faces named +x,-x,+y,-y,+z,-z can be skipped."""
    c = np.asarray(c, float); A = [np.asarray(a, float) for a in (ax, ay, az)]
    for k, sgn, nm in ((0, 1, '+x'), (0, -1, '-x'), (1, 1, '+y'), (1, -1, '-y'), (2, 1, '+z'), (2, -1, '-z')):
        if nm in skip: continue
        o = c + sgn * A[k]; u = A[(k + 1) % 3]; w = A[(k + 2) % 3]
        pts = [o - u - w, o + u - w, o + u + w, o - u + w]
        lu, lw = 2 * np.linalg.norm(u) / uvs, 2 * np.linalg.norm(w) / uvs
        ids = [part.v(p, uv) for p, uv in zip(pts, ((0, 0), (lu, 0), (lu, lw), (0, lw)))]
        orient(part, ids, mat, outside_dir=sgn * A[k])


def tube(part, pts, r, n, mat, r_top=None, cap=True):
    """polyline tube (masts, rails, posts): radius r (-> r_top), n sides."""
    pts = [np.asarray(p, float) for p in pts]
    rings = []
    L = [0.0]
    for i in range(1, len(pts)):
        L.append(L[-1] + np.linalg.norm(pts[i] - pts[i - 1]))
    for i, p in enumerate(pts):
        d = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]; d /= np.linalg.norm(d)
        a = np.cross(d, [0, 0, 1.0]) if abs(d[2]) < 0.9 else np.cross(d, [1.0, 0, 0])
        a /= np.linalg.norm(a); b = np.cross(d, a)
        rr = r if r_top is None else r + (r_top - r) * L[i] / max(L[-1], 1e-9)
        rings.append([part.v(p + rr * (math.cos(2 * math.pi * k / n) * a + math.sin(2 * math.pi * k / n) * b),
                             (k / n, L[i])) for k in range(n)])
    for i in range(len(rings) - 1):
        for k in range(n):
            ids = [rings[i][k], rings[i][(k + 1) % n], rings[i + 1][(k + 1) % n], rings[i + 1][k]]
            c = (pts[i] + pts[i + 1]) / 2
            orient(part, ids, mat, inside_pt=c)
    if cap and n >= 3:
        for ring, p, s in ((rings[0], pts[0], -1), (rings[-1], pts[-1], 1)):
            d = pts[-1] - pts[0]; d /= np.linalg.norm(d)
            if n == 3:
                orient(part, list(ring), mat, outside_dir=s * d)
            else:
                cid = part.v(p)
                for k in range(n):
                    orient(part, [ring[k], ring[(k + 1) % n], cid], mat, outside_dir=s * d)


def lathe(part, prof, centre, n, mat, uv_u=1.0, uv_v=1.0, a0=0.0, outward=True, closed_top=False):
    """surface of revolution about the vertical through centre (local x, y): prof = [(r, z), ...]."""
    centre = np.asarray(centre, float)
    rings = []
    s = [0.0]
    for i in range(1, len(prof)):
        s.append(s[-1] + math.hypot(prof[i][0] - prof[i - 1][0], prof[i][1] - prof[i - 1][1]))
    for i, (r, z) in enumerate(prof):
        ring = []
        for k in range(n + 1):
            b = a0 + 360.0 * k / n
            d = bvec(b)
            ring.append(part.v((centre[0] + r * d[0], centre[1] + r * d[1], z), (k / n * uv_u, s[i] / uv_v)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for k in range(n):
            ids = [rings[i][k], rings[i + 1][k], rings[i + 1][k + 1], rings[i][k + 1]]
            b = a0 + 360.0 * (k + 0.5) / n; d = bvec(b)
            r0, z0 = prof[i]; r1, z1 = prof[i + 1]
            # outward = away from the axis, rotated by the profile slope (normal of the generating segment)
            tr, tz = r1 - r0, z1 - z0
            nr, nz = tz, -tr
            od = np.array([nr * d[0], nr * d[1], nz])
            if not outward: od = -od
            if np.linalg.norm(od) < 1e-9: od = np.array([d[0], d[1], 0.0])
            orient(part, ids, mat, outside_dir=od)
    return rings


def disc(part, centre, r, z, n, mat, up=True, uvs=4.0):
    centre = np.asarray(centre, float)
    cid = part.v((centre[0], centre[1], z), (centre[0] / uvs, centre[1] / uvs))
    ring = []
    for k in range(n):
        d = bvec(360.0 * k / n); p = (centre[0] + r * d[0], centre[1] + r * d[1], z)
        ring.append(part.v(p, (p[0] / uvs, p[1] / uvs)))
    for k in range(n):
        orient(part, [ring[k], ring[(k + 1) % n], cid], mat, outside_dir=(0, 0, 1 if up else -1))


# ------------------------------------------------------------------------------------------------ the tower model
LODS = {
    0: dict(m_sub=4, rows='half', lobe_n=14, shoulder=(0, 0.01, 0.03, 0.05, 0.076, 0.12, 0.167, 0.3, 0.515, 0.75, 1.0),
            recess=True, seams=True, panes=True, cab_n=CAB_PANES, round_n=96, joints=True, masts=6, poles=True, mullions=True,
            ibf='full', switch_m=(0, 350)),
    1: dict(m_sub=2, rows='full', lobe_n=8, shoulder=(0, 0.03, 0.076, 0.167, 0.515, 1.0), recess=False, seams=True,
            panes=False, cab_n=CAB_PANES, round_n=48, joints=False, masts=3, poles=False, mullions=False, ibf='plain',
            switch_m=(350, 1200)),
    2: dict(m_sub=1, rows='half_density', lobe_n=5, shoulder=(0, 0.076, 0.515, 1.0), recess=False, seams=False,
            panes=False, cab_n=12, round_n=24, joints=False, masts=3, poles=False, mullions=False, ibf='box',
            switch_m=(1200, None)),
}


class Tower:
    """the tower of one height family (1 = F1, 2 = F2), with the drawn geometry of BT-01..03."""

    def __init__(self, fam=1):
        self.fam = fam; f = self.f = DT.FAM[fam]
        self.k = f['D'] / 15.2                       # F1-metre scale of the photo-read features (masts, post) (draw_tower)
        sh = DT.shaft_outline(f)
        h59 = DT.hf(59.4, f)
        body = [(r, h) for r, h in sh if h <= h59 + 1e-6]
        self.shoulder_pts = [(r, h) for r, h in sh if h > h59 + 1e-6]
        self.h_top = h59                              # flare, widest = top row of the shell
        self.r_top = body[-1][0]
        hs = np.array([h for r, h in body]); rs = np.array([r for r, h in body])
        self.R_ = PchipInterpolator(hs, rs, extrapolate=True)
        self.body_pts = body
        self.ibf = f['ibf']; self.par = self.ibf + PARAPET
        self.hb = self.ibf                            # ribbon foot = base-building roof [inf, drawing]
        self.ht = min(self.ibf + RIB_H, self.h_top)   # ribbon head: 147 ft [pub] from the roof; capped at the flare corner
        self.rib_capped = self.ibf + RIB_H > self.h_top + 0.05
        self.h_bot = self.ibf - 0.3                   # shell foot, buried 0.3 m below the base-building roof
        pr, p0, p1 = DT.plinth(f)
        self.plinth_r, self.deck_h, self.sill_h = pr, p0, p1
        c = DT.cab_outline(f)
        self.cab = c
        self.floor_h = DT.hf(61.0, f)                 # cab floor (sill band) station [inf]
        self.rim_h = c['roof_rim'][1]
        self.tip_h = self.ht + DT.NE_TIP              # NE blade top: flush with the flare corner / ribbon head (draw_blades,
                                                      # NE_TIP) [obs photos t3 / t4 / t5]
        self.slot_band = tuple(DT.hf(x, f) for x in T['h_upper_slots']['value'])
        self.long_band = tuple(DT.hf(x, f) for x in T['h_lower_slot']['value'])
        self.seams = [DT.hf(x, f) for x in T['h_seams']['value']]
        # SW wing outer line of the BT-02 B elevation (draw_blades): u_out(h) = x0 + (wt - x0) t^1.8 up to ht - 2.5
        self.wt = DT.surf_u(DT.WING_TIP[0], DT.WING_TIP[1] * f['s'] * DT.D_SPEC / 15.2, RIGHT_B)
        self.x0 = RIB_W0 / 2 + 1.4 + DT.rib_shift(self.hb, f, RIGHT_B)
        self.rho_tip_top = DT.WING_TIP[1] * f['s'] * DT.D_SPEC / 15.2
        self.h_w1 = self.ht - 2.5
        # slots (draw_slots): upper band positions every 360/13 deg from SLOT_PHASE, none in the landside sector
        n = int(round(360 / DT.SLOT_PITCH))
        self.upper = [(DT.SLOT_PHASE + k * 360.0 / n) % 360 for k in range(n)]
        self.upper = [b for b in self.upper if not (DT.SLOT_SKIP[0] <= b <= DT.SLOT_SKIP[1])]
        self.glazed = [b for b in self.upper if b >= DT.SLOT_GLAZED[0] or b <= DT.SLOT_GLAZED[1]]
        self.notes = []
        self.details = {}

    # ---------------------------------------------------------------- thin details: separate nodes without AO
    def _detail(self, name, extras):
        if name not in self.details:
            self.details[name] = Part(name, extras, smooth=False, ao=False)
        return self.details[name]

    # ---------------------------------------------------------------- profile helpers
    def R(self, h):
        return float(self.R_(min(max(h, self.ibf), self.h_top)))

    def hs(self, h):
        return DT.h2spec(h, self.f)

    def theta(self, psi, h):
        """bearing of the helical column psi at height h (draw_tower joints: b = psi - TWIST (h_spec - 24.7))."""
        return psi - DT.TWIST * (self.hs(h) - LONG_FOOT_SPEC)

    def psi(self, theta, h):
        return theta + DT.TWIST * (self.hs(h) - LONG_FOOT_SPEC)

    def uv_v(self, h):
        return (self.hs(h) - DT.ROW0) / DT.ROW_PITCH          # panel rows at integer v (spec pitch 2.467 m)

    def uv_clad(self, psi, h):
        """UV0 of the cladding tile at the helical coordinate psi (deg) and height h: joints at u = k / CLAD_TU, rows at
        v = k / CLAD_TV (one tile = 4 joints x 2 panel rows)."""
        return (psi / (360.0 / DT.N_JOINTS) / CLAD_TU, self.uv_v(h) / CLAD_TV)

    def in_seam(self, h0, h1):
        """True if the row band [h0, h1] lies inside one of the dark seam bands (SEAM_W)."""
        return any(hs - SEAM_W / 2 - 1e-4 <= h0 and h1 <= hs + SEAM_W / 2 + 1e-4 for hs in self.seams)

    # ---------------------------------------------------------------- landside insert at one height
    def insert(self, h, lobe_n):
        """plan contour of the landside sector at height h: lobe (SW wing) from its end on the round body to the channel,
        SW channel wall, ribbon face, NE channel wall, NE blade facet to its root on the round body.
        Returns segments of local (x, y) points in increasing bearing and the boundary bearings."""
        R = self.R(h)
        tr = min(max((h - self.hb) / (self.ht - self.hb), 0.0), 1.0)
        tw = min(max((h - self.hb) / (self.h_w1 - self.hb), 0.0), 1.0)
        w = RIB_W0 + (RIB_W1 - RIB_W0) * tr
        d = R - RIB_INSET
        e, nn = bvec(DT.RIB_BRG), bvec(DT.RIB_BRG + 90.0)
        P = lambda X, Y: X * e + Y * nn
        # NE blade: root on the round body w/2 + 1.0 (BT-02 B foot) -> 1.2 m (BT-01, flare level) NE of the ribbon edge; the
        # sharp tip 0.5 m NE of the ribbon edge, standing out 0.25 m (foot) -> 1.6 m (BT-01) beyond the round body [inf]
        yr = w / 2 + 1.0 + 0.2 * tr
        xr = math.sqrt(R * R - yr * yr)
        p_ne = 0.25 + 1.35 * tr ** 1.5
        tip = P(R + p_ne, w / 2 + 0.5)
        root = P(xr, yr)
        e_ne, e_sw, mid = P(d, w / 2), P(d, -w / 2), P(d, 0.0)
        # SW wing (lobe): BT-01 plan points at the flare level (bearings 285 / 266 / 254 (tip) / 246 / 240 at R + 0.9 / 1.7 /
        # 14.0 m / 0.9 / 0) as fractions q of the angle from the ribbon edge to the end; the tip follows the BT-02 B outer line
        # u_out(h) (draw_blades) at a radius R + 0.5 (foot) -> 14.0 m (top) [inf]
        phi_e = math.degrees(math.atan2(-w / 2, d))
        if tw >= 1.0:
            rho_t, b_tip = self.rho_tip_top, DT.WING_TIP[0]
        else:
            Rw1 = self.R(self.h_w1)
            rho_t = R + 0.5 + (self.rho_tip_top - Rw1 - 0.5) * tw ** 1.8
            u_out = self.x0 + (self.wt - self.x0) * tw ** 1.8
            b_tip = 207.7 + math.degrees(math.acos(min(1.0, u_out / rho_t)))
        q_tip = (254.0 - 310.0 - (-17.15)) / (240.0 - 310.0 - (-17.15))      # 0.735 at the flare level (BT-01)
        phi_tip = b_tip - DT.RIB_BRG
        phi_end = phi_e + (phi_tip - phi_e) / q_tip
        top_R = self.r_top
        Q = np.array([(285 - 292.85) / (240 - 292.85), (266 - 292.85) / (240 - 292.85), q_tip, (246 - 292.85) / (240 - 292.85), 1.0])
        Pq = np.array([0.9, 1.7, self.rho_tip_top - top_R, 0.9, 0.0]) / (self.rho_tip_top - top_R)
        prof = PchipInterpolator(Q, Pq)
        p_tip = rho_t - R
        qs = np.linspace(1.0, Q[0], lobe_n)
        if not np.any(np.isclose(qs, q_tip, atol=1e-3)):
            qs = np.sort(np.append(qs, q_tip))[::-1]
        lobe = []
        for q in qs:
            phi = phi_e + q * (phi_end - phi_e)
            rho = R + p_tip * float(prof(q))
            lobe.append(rho * bvec(DT.RIB_BRG + phi))
        return dict(R=R, w=w, d=d, tr=tr, tw=tw, lobe=lobe, e_sw=e_sw, mid=mid, e_ne=e_ne, tip=tip, root=root,
                    th_a=DT.RIB_BRG + phi_end, th_b=DT.RIB_BRG + math.degrees(math.atan2(yr, xr)),
                    b_tip=b_tip, rho_tip=rho_t, phi_e=phi_e)

    # ---------------------------------------------------------------- height stations
    def stations(self, lod):
        L = LODS[lod]
        rows = [DT.hf(DT.ROW0 + k * DT.ROW_PITCH, self.f) for k in range(-14, 14)]
        rows = [h for h in rows if self.ibf + 0.2 < h < self.h_top - 0.2]
        if L['rows'] == 'half':
            rows = rows + [(a + b) / 2 for a, b in zip(rows[:-1], rows[1:])]
            rows += [(self.ibf + min(rows)) / 2]
        elif L['rows'] == 'half_density':
            rows = rows[::2]
        key = [self.h_bot, self.ibf, self.ht, self.h_top] + list(self.slot_band) + list(self.long_band) + self.seams
        if L['seams']:
            key += [h + d for h in self.seams for d in (-SEAM_W / 2, SEAM_W / 2)]
        if L['panes']:
            for h0 in (self.slot_band[0],):
                key += [h0 + 0.25 * self.f['s'], DT.hf(DT.h2spec(h0, self.f) + DT.ROW_PITCH, self.f) - 0.25 * self.f['s']]
        if lod < 2:
            key += [h for r, h in self.body_pts]
            key += [self.h_top - 1.0, self.h_top - 0.45]          # curvature of the flare's widest part
        hs = sorted(set(round(h, 4) for h in key))
        for h in sorted(rows):
            if min(abs(h - k) for k in hs) > (0.35 if lod == 0 else 0.6):
                hs.append(round(h, 4))
        return sorted(set(hs))

    # ---------------------------------------------------------------- slots in (psi, h)
    def slot_list(self):
        """(name, psi_c(h), half-width deg(h), h0, h1, glazed) of every slot, from draw_tower.draw_slots."""
        a, b = self.slot_band
        out = []
        for bm in self.upper:
            def bc(h, bm=bm):
                t = (h - a) / (b - a)
                return bm + DT.SLOT_SWEEP / 2 - DT.SLOT_SWEEP * t
            out.append(dict(name=f'upper_{bm:.1f}', bm=bm, centre=bc, w=DT.SLOT_W, h0=a, h1=b, glazed=bm in self.glazed))
        a2, b2 = self.long_band

        def bl(h):
            t = (h - a2) / (b2 - a2)
            return DT.LONG_SLOT[0] + (DT.LONG_SLOT[1] - DT.LONG_SLOT[0]) * t
        out.append(dict(name='long', bm=sum(DT.LONG_SLOT) / 2, centre=bl, w=DT.LONG_W, h0=a2, h1=b2, glazed=False))
        return out

    # ---------------------------------------------------------------- round airside body with the slots
    def shell(self, H, ins, L):
        part = Part('shaft', dict(
            src='inf', feature='round airside body: radius r(h) = A380 width ratios / 1.015 x D, stations rim - k D; helical '
            'panel joints and panel rows (UV0 base-colour + normal tile, 4 x 2 panels); two dark seam joint bands (0.10 m, flush); '
            'upper slot band + long helical slot', spec=['shaft_profile_ratio_A380', 'd_flare_max',
            'd_shaft_waist', 'd_shaft_at_ibf_roof', 'h_flare_max', 'h_upper_slots', 'h_lower_slot', 'h_seams', 'cladding'],
            drawing='BT-02 A/B, BT-03 (shaft_outline, draw_slots, draw_cladding_grid)',
            tags=dict(radii='inf (photo ratios x D)', stations='inf', slots='inf from obs photos t1/t2 (count, phase inf)',
                      slot_glazing='obs photos t3/t4', joints='spacing obs t2; count / twist inf; phase unknown; dark joint lines '
                      'obs t2/t4 (width / contrast inf)', seams='dark joint bands obs t2/t4; width inf')),
            smooth=True)
        m = L['m_sub']; n = 68 * m; dpsi = 360.0 / n
        psi0 = DT.LONG_SLOT[0]
        cols = np.array([psi0 + j * dpsi for j in range(n)])
        slots = self.slot_list()
        # per row: column psi (helical), snapped to the slot edges inside each slot band (local redistribution)
        snap = {}
        for si, s in enumerate(slots):
            hm = (s['h0'] + s['h1']) / 2
            pc = self.psi(s['centre'](hm), hm); hw = math.degrees(s['w'] / 2 / self.R(hm))
            jl = int(round((pc - hw - psi0) / dpsi)); jr = int(round((pc + hw - psi0) / dpsi))
            if jr <= jl: jr = jl + 1
            s['jl'], s['jr'] = jl, jr
        rows_psi = []
        for k, h in enumerate(H):
            ps = cols.copy()
            for s in slots:
                if not (s['h0'] - 1e-3 <= h <= s['h1'] + 1e-3): continue
                pc = self.psi(s['centre'](h), h); hw = math.degrees(s['w'] / 2 / self.R(h))
                el, er = pc - hw, pc + hw
                # keep the slot clear of the NE blade root (the landside sector) by 0.3 m [the drawing lets the blade
                # cover the 345.5-deg slot's top corner; here it is clipped at the crease]
                thb = ins[k]['th_b']
                lim = self.psi(thb, h) + math.degrees(0.3 / self.R(h))
                lo = lim + 360.0 * math.floor((el - lim + 180.0) / 360.0)
                if lo > el - 1e-9 and lo < er:
                    el = min(lo, er - 0.2)
                    self.notes.append(f"slot {s['name']} clipped at the NE blade root at h {h:.2f} ({er - el:.2f} deg left)")
                jl, jr = s['jl'], s['jr']
                a0, a1 = jl - 2, jr + 2
                anchors = [(a0, cols[a0 % n] + 360 * (a0 // n)), (jl, el), (jr, er), (a1, cols[a1 % n] + 360 * (a1 // n))]
                for (ja, pa), (jb, pb) in zip(anchors[:-1], anchors[1:]):
                    for j in range(ja, jb + 1):
                        ps[j % n] = pa + (pb - pa) * (j - ja) / (jb - ja) - 360 * (j // n)
            rows_psi.append(ps)
        snap['rows'] = rows_psi
        # vertices per row: B (NE root), helical columns strictly inside the round arc, A (lobe end)
        lists = []
        for k, h in enumerate(H):
            R = self.R(h); c = self.psi(0.0, h)
            thb, tha = ins[k]['th_b'], ins[k]['th_a'] + 360.0
            pB = thb + c
            items = []
            idB = part.v((R * bvec(thb))[0:2].tolist() + [h], self.uv_clad(pB, h))
            items.append((pB, idB, 'B'))
            span = tha - thb
            margin = 0.35 * dpsi
            for j in range(n):
                pj = rows_psi[k][j]
                pu = pB + ((pj - pB) % 360.0)
                if pu - pB < margin or pu - pB > span - margin: continue
                th = pu - c
                p = R * bvec(th)
                vid = part.v((p[0], p[1], h), self.uv_clad(pu, h))
                items.append((pu, vid, j))
            pA = tha + c
            idA = part.v((R * bvec(tha)).tolist() + [h], self.uv_clad(pA, h))
            items.append((pA, idA, 'A'))
            items.sort(key=lambda x: x[0])
            lists.append(items)
        self.shell_lists = lists
        # slot cells: rows strictly inside a band and columns jl .. jr-1
        def in_slot(k, j):
            hm = (H[k] + H[k + 1]) / 2
            for s in slots:
                if s['h0'] - 1e-3 <= H[k] and H[k + 1] <= s['h1'] + 1e-3 and hm > s['h0']:
                    jj = (j - s['jl']) % n
                    if jj < (s['jr'] - s['jl']): return s
            return None
        holes = {}
        for k in range(len(H) - 1):
            A, B = lists[k], lists[k + 1]
            i = j = 0
            cm = 'seam' if (L['seams'] and self.in_seam(H[k], H[k + 1])) else 'clad'
            while i < len(A) - 1 or j < len(B) - 1:
                if (i < len(A) - 1 and j < len(B) - 1 and isinstance(A[i][2], int) and isinstance(A[i + 1][2], int)
                        and A[i][2] == B[j][2] and A[i + 1][2] == B[j + 1][2] and (A[i + 1][2] - A[i][2]) % n == 1):
                    s = in_slot(k, A[i][2])
                    ids = [A[i][1], B[j][1], B[j + 1][1], A[i + 1][1]]
                    if s is None:
                        part.f(ids, cm)
                    elif L['recess']:
                        holes.setdefault(s['name'], []).append((k, A[i][2], ids))
                    else:
                        part.f(ids, 'slot')
                    i += 1; j += 1; continue
                if j >= len(B) - 1 or (i < len(A) - 1 and A[i + 1][0] <= B[j + 1][0]):
                    part.f([A[i][1], B[j][1], A[i + 1][1]], cm); i += 1
                else:
                    part.f([A[i][1], B[j][1], B[j + 1][1]], cm); j += 1
        if L['recess']:
            self.slot_pockets(part, H, holes, slots, L)
        # the two seams (h_seams) are dark joint bands SEAM_W wide in the shell itself (material 'seam', LOD0 / LOD1); the
        # round-1 light band standing 0.03 m proud (seam_rings) is withdrawn: the photos show dark joints
        return part

    def slot_pockets(self, part, H, holes, slots, L):
        """recessed slot pockets (LOD0): floor = the slot cells moved SLOT_DEPTH inwards, walls around the opening;
        glazed pane in the lowest panel row of the NE-flank slots (draw_slots) [obs photos t3 / t4]."""
        byname = {s['name']: s for s in slots}
        for name, cells in holes.items():
            s = byname[name]
            vmap = {}

            def inner(vid):
                if vid not in vmap:
                    p = np.array(part.V[vid]); r = math.hypot(p[0], p[1])
                    q = p.copy(); q[0:2] *= (r - SLOT_DEPTH) / r
                    vmap[vid] = part.v(q, part.UV[vid])
                return vmap[vid]
            edges = {}
            for k, j, ids in cells:
                part.f([inner(i) for i in ids], 'slot')
                for a, b in zip(ids, ids[1:] + ids[:1]):
                    edges[(a, b)] = edges.get((a, b), 0) + 1
            # boundary edges = edges whose reverse is not in the set -> walls
            for (a, b) in list(edges):
                if (b, a) in edges: continue
                part.f([b, inner(b), inner(a), a], 'slot')       # faces into the pocket (audited: tower3d_verify.orientation)
            if s['glazed'] and L['panes']:
                self.slot_pane(part, s)

    def slot_pane(self, part, s):
        a = s['h0']
        g0 = a + 0.25 * self.f['s']
        g1 = DT.hf(DT.h2spec(a, self.f) + DT.ROW_PITCH, self.f) - 0.25 * self.f['s']
        n = 4
        L_, R_ = [], []
        for i in range(n + 1):
            h = g0 + (g1 - g0) * i / n
            r = self.R(h) - SLOT_DEPTH + 0.06
            hw = math.degrees(0.7 * s['w'] / 2 / self.R(h))
            bc = s['centre'](h)
            L_.append(part.v((r * bvec(bc - hw)).tolist() + [h], (0, i / n)))
            R_.append(part.v((r * bvec(bc + hw)).tolist() + [h], (1, i / n)))
        for i in range(n):
            ids = [L_[i], L_[i + 1], R_[i + 1], R_[i]]
            bc = s['centre']((g0 + g1) / 2)
            orient(part, ids, 'slot_glass', outside_dir=np.append(bvec(bc), 0.0))

    # ---------------------------------------------------------------- landside: blades, channel, ribbon
    def landside(self, H, ins, L):
        land = Part('landside', dict(
            src='inf', feature='landside sector: SW wing (horizontally louvred, broad, rounded outer edge; tip 254 deg / 14.0 m '
            'at the flare level), flat channel walls (both louvred), NE blade (narrow clad facet, sharp flat-topped tip 1.6 m proud '
            'at the flare level, flush with the flare corner)',
            spec=['shaft_plan_shape', 'ribbon_width'], drawing='BT-01 (plan at the flare level), BT-02 B (draw_blades)',
            tags=dict(form='obs photos t3/t4', plan='unknown beyond the wing-tip point (schematic, BT-01)',
                      wing_tip='inf (reproduces t3/t4)', blade_proportions='inf (oblique photos)')), smooth=False)
        rib = Part('ribbon', dict(
            src='pub', feature='glass ribbon, LED-backlit (emissive off by day; extras.led), 147 ft from the base-building roof, '
            '3.2 -> 6.8 m wide, 2 columns x 25 rows, facing bearing 310, 1 m inside the round-body radius',
            spec=['ribbon_height', 'ribbon_width', 'ribbon_facade'], drawing='BT-02 B (draw_blades), BT-01',
            tags=dict(height='pub 147 ft (start / end levels inf: from the IBF roof)', width='obs low', grid='obs photos',
                      bearing='inf (photo range 300-320)'), led=True), smooth=False, ao=True)
        # segments: lobe (smooth, louvre), SW wall (louvre), ribbon (glass), NE wall (clad), NE facet (clad)
        def seg_pts(I):
            return dict(lobe=I['lobe'], sw=[I['lobe'][-1], I['e_sw']], rib=[I['e_sw'], I['mid'], I['e_ne']],
                        ne=[I['e_ne'], I['tip']], fac=[I['tip'], I['root']])
        segs = [seg_pts(I) for I in ins]
        # the NE channel wall (ribbon NE edge -> blade tip) is horizontally louvred like the SW wing [obs photos t3 / t4: the narrow
        # strip beside the ribbon shows the same horizontal lines; draw_tower.NE_TIP note]; the blade's outer facet is clad
        for key, mat, smooth in (('lobe', 'louvre', True), ('sw', 'louvre', False), ('ne', 'louvre', False), ('fac', 'clad', False)):
            rows = []
            for k, h in enumerate(H):
                pts = segs[k][key]
                s = [0.0]
                for a in range(1, len(pts)): s.append(s[-1] + float(np.linalg.norm(pts[a] - pts[a - 1])))
                if mat == 'louvre':
                    rows.append([land.v((p[0], p[1], h), (s[a] / 1.5, h / 1.2)) for a, p in enumerate(pts)])
                else:                             # cladding tile: a joint every 0.9 m along the facet [inf], panel rows
                    rows.append([land.v((p[0], p[1], h), (s[a] / 0.9 / CLAD_TU, self.uv_v(h) / CLAD_TV)) for a, p in enumerate(pts)])
            self._strip(land, rows, mat, ins, H)
        # ribbon: glass between hb and ht, clad below (buried) and above (if capped)
        rows = []
        for k, h in enumerate(H):
            pts = segs[k]['rib']
            rows.append([rib.v((p[0], p[1], h), (a / 2.0, (h - self.hb) / (self.ht - self.hb) * RIB_ROWS)) for a, p in enumerate(pts)])
        for k in range(len(H) - 1):
            hm = (H[k] + H[k + 1]) / 2
            mat = 'ribbon_glass' if self.hb - 1e-6 <= hm <= self.ht + 1e-6 else 'clad'
            for a in range(len(rows[k]) - 1):
                ids = [rows[k][a], rows[k + 1][a], rows[k + 1][a + 1], rows[k][a + 1]]
                orient(rib, ids, mat, outside_dir=np.append(bvec(DT.RIB_BRG), 0.0))
        if L['mullions']:
            self.ribbon_mullions(self._detail('ribbon_mullions', dict(
                src='obs', feature='ribbon mullion grid: centre mullion, edge frames, 24 transoms + head / foot (2 columns x 25 rows)',
                spec=['ribbon_facade'], drawing='BT-02 B (draw_blades)', tags=dict(grid='obs photos t3/t4', profile='inf'))))
        return land, rib

    def _strip(self, part, rows, mat, ins, H):
        """loft a contour segment over the rows. The section contour runs clockwise seen from above (increasing bearing),
        so the winding (lower a, upper a, upper a+1, lower a+1) puts the normal on the left of travel = outside."""
        for k in range(len(rows) - 1):
            for a in range(len(rows[k]) - 1):
                part.f([rows[k][a], rows[k + 1][a], rows[k + 1][a + 1], rows[k][a + 1]], mat)

    def ribbon_mullions(self, rib):
        """2 columns x 25 rows: centre mullion, edge frames and 24 transoms + head / foot [obs photos], 0.10 m wide, 0.08 m
        proud of the glass [inf]."""
        hs = np.linspace(self.hb, self.ht, 25)
        e, nn = bvec(DT.RIB_BRG), bvec(DT.RIB_BRG + 90.0)
        out = np.append(e, 0.0)

        def at(h, y):
            I_R = self.R(h); tr = (h - self.hb) / (self.ht - self.hb); w = RIB_W0 + (RIB_W1 - RIB_W0) * tr
            d = I_R - RIB_INSET
            yy = y * w / 2
            p = d * e + yy * nn
            return np.array([p[0], p[1], h])
        for y in (-1.0, 0.0, 1.0):
            pts = [at(h, y) + out * 0.04 for h in hs]
            for a in range(len(pts) - 1):
                c = (pts[a] + pts[a + 1]) / 2; ax = (pts[a + 1] - pts[a]) / 2
                box(rib, c, ax, np.append(nn, 0.0) * 0.05, out * 0.04, 'mullion', skip=('-z',))
        for r in range(RIB_ROWS + 1):
            h = self.hb + (self.ht - self.hb) * r / RIB_ROWS
            p0, p1 = at(h, -1.0) + out * 0.04, at(h, 1.0) + out * 0.04
            box(rib, (p0 + p1) / 2, (p1 - p0) / 2, np.array([0, 0, 0.05]), out * 0.04, 'mullion', skip=('-z',))

    # ---------------------------------------------------------------- flare top (rounded shoulder), NE tip, wing post
    def deck(self, H, ins, L):
        part = Part('flare_deck', dict(
            src='inf', feature='flare top: rounded shoulder from the widest corner up to the plinth foot (t1 profile '
            'fractions of the spec rise); NE blade pointed tip; post with a stay on the SW wing top; railing around the plinth',
            spec=['h_flare_max', 'h_cab_floor', 'd_flare_max'], drawing='BT-02, BT-03 (SHOULDER, draw_blades)',
            tags=dict(shoulder='shape obs photo t1, stations inf; landside sector flat, then a linear ~14-deg rise (obs t3/t4: flat '
                      'blade tops, no deck visible above them from 30 deg below)', ne_tip='flush with the flare corner, obs photos t3/t4/t5',
                      post='obs photos t3/t4/t5, position inf',
                      railing='obs photo t3, dimensions inf')), smooth=True)
        k = len(H) - 1
        I = ins[k]
        sh = self.shell_lists[k]
        loop = []
        for pu, vid, j in sh:                                    # round arc (B .. A), increasing bearing
            loop.append(np.array(self._shellpart_v(vid)))
        # landside top contour from the lobe end (A) to the root (B), skipping the duplicated A / B
        land = list(I['lobe'][1:]) + [I['e_sw'], I['mid'], I['e_ne'], I['tip']]
        loop = loop + [np.array([p[0], p[1], self.h_top]) for p in land]
        npt = len(loop)
        # targets on the plinth foot circle (around the cab centre), bearings forced monotonic
        brg = []
        for p in loop:
            d = p[0:2] - CAB
            brg.append(math.degrees(math.atan2(d[0], d[1])))
        brg = np.unwrap(np.radians(brg)); brg = np.degrees(brg)
        for i in range(1, npt):
            brg[i] = max(brg[i], brg[i - 1] + 0.05)
        span = brg[-1] - brg[0]
        if span > 359.0:
            brg = brg[0] + (brg - brg[0]) * 359.0 / span
        tgt = [np.array([CAB[0] + self.plinth_r * bvec(b)[0], CAB[1] + self.plinth_r * bvec(b)[1], self.deck_h]) for b in brg]
        runs = np.array([a for a, b in DT.SHOULDER]); rises = np.array([b for a, b in DT.SHOULDER])
        rise_of = PchipInterpolator(runs, rises)
        # landside sector (SW wing, ribbon head, NE blade): flat tops [obs photos t3 / t4: the wing's "flat top", the NE blade
        # ends in a sharp flat corner; from t4 (81 m, ~30 deg below) no deck shows above the blade or the ribbon head, from t3
        # (263 m, ~12 deg below) a thin band does]: the deck stays at the flare corner over the part outside the round body
        # and at least LAND_FLAT of the run, then rises linearly (~14 deg) to the plinth foot, so it hides below a 30-deg
        # sight line and shows as a sliver at 12 deg. The round body keeps the t1 SHOULDER (rounded, ~37 deg at the edge).
        # Round 1 used the SHOULDER everywhere: a sunlit ~0.3-0.5 m facet stood above the NE blade in the t4 render.
        LAND_FLAT = 0.25
        a0 = []
        for i in range(npt):
            ex = max(0.0, math.hypot(loop[i][0], loop[i][1]) - self.r_top)
            run = max(1e-6, math.hypot(loop[i][0] - CAB[0], loop[i][1] - CAB[1]) - self.plinth_r)
            a0.append(min(0.6, max(LAND_FLAT, ex / run)) if i >= len(sh) else None)
        rings = []
        for a in L['shoulder']:
            ring = []
            for i in range(npt):
                p = loop[i] * (1 - a) + tgt[i] * a
                if a0[i] is None:
                    rz = float(rise_of(a))
                else:
                    rz = max(0.0, (a - a0[i]) / (1.0 - a0[i]))
                p[2] = self.h_top + (self.deck_h - self.h_top) * rz
                rr = math.hypot(p[0] - CAB[0], p[1] - CAB[1])
                ring.append(part.v(p, (i / 6.0, rr / 2.0)))
            rings.append(ring)
        for r in range(len(rings) - 1):
            for i in range(npt):
                ids = [rings[r][i], rings[r][(i + 1) % npt], rings[r + 1][(i + 1) % npt], rings[r + 1][i]]
                orient(part, ids, 'clad_deck', outside_dir=(0, 0, 1))
        # NE blade top: flush with the flare corner (DT.NE_TIP = 0) [obs photos t3 / t4 / t5]; a wedge only if the sheet
        # draws the tip above the corner
        if self.tip_h > self.h_top + 0.05:
            R0 = np.append(I['root'], self.h_top); T0 = np.append(I['tip'], self.h_top); E0 = np.append(I['e_ne'], self.h_top)
            T1 = T0.copy(); T1[2] = self.tip_h
            ids = [part.v(p) for p in (R0, T0, E0, T1)]
            cen = (R0 + T0 + E0) / 3; cen[2] = self.h_top + 0.2
            for tri in ((0, 1, 3), (1, 2, 3), (2, 0, 3)):
                orient(part, [ids[t] for t in tri], 'clad_deck', inside_pt=cen)
        if L['poles']:
            rp = self._detail('deck_rails', dict(src='obs', feature='post with a stay on the SW wing top; railing on the '
                              'flare deck around the plinth', spec=['roof_equipment'], drawing='BT-02 B (WING_POST)',
                              tags=dict(post='obs photos t3/t4/t5, position inf', railing='obs photo t3, dimensions inf')))
            # post with a diagonal stay on the SW wing top, 0.6 of the way from the ribbon edge to the tip, 0.6 m in [inf]
            lobe = I['lobe']
            tip_i = int(np.argmax([np.linalg.norm(p) for p in lobe]))
            pin = I['e_sw'] + 0.6 * (lobe[tip_i] - I['e_sw'])
            pin = pin * (np.linalg.norm(pin) - 0.6) / np.linalg.norm(pin)
            hpost = DT.WING_POST * self.k
            base = np.array([pin[0], pin[1], self.h_top + 0.15])
            top = base + np.array([0, 0, hpost])
            tube(rp, [base, top], 0.06, 6, 'rail')
            to_rib = I['e_sw'] - pin; to_rib /= np.linalg.norm(to_rib)
            foot = base + np.append(to_rib * 1.6, 0.0)
            tube(rp, [top - np.array([0, 0, 0.2]), foot], 0.025, 4, 'rail')
            # railing on the deck around the plinth [obs photo t3; height / position inf]
            rr = self.plinth_r + 0.4
            nposts = int(2 * math.pi * rr / 2.0)
            hb_ = self.deck_h - 0.05
            for i in range(nposts):
                d = bvec(360.0 * i / nposts)
                p = np.array([CAB[0] + rr * d[0], CAB[1] + rr * d[1], hb_])
                tube(rp, [p, p + np.array([0, 0, RAIL_H])], 0.025, 4, 'rail', cap=False)
            for hh in (RAIL_H, RAIL_H / 2):
                ring = [np.array([CAB[0] + rr * bvec(a)[0], CAB[1] + rr * bvec(a)[1], hb_ + hh]) for a in np.linspace(0, 360, 49)]
                tube(rp, ring, 0.022, 4, 'rail', cap=False)
        return part

    def _shellpart_v(self, vid):
        return self._shell_part.V[vid]

    # ---------------------------------------------------------------- cab
    def cab_parts(self, L):
        part = Part('cab', dict(
            src='inf', feature='cab on its inferred centre (1.5 E, 1.0 N of the axis): dark plinth ring, floor, inverted-cone '
            'roof fascia, roof deck with rim coping and inner curb, ceiling (interior dark)',
            spec=['d_cab_roof', 'd_cab_glass_top', 'd_cab_glass_bottom', 'cab_roof_fascia_height', 'h_roof_top',
                  'h_cab_glass_top', 'h_cab_glass_bottom', 'h_cab_floor', 'position_cab_roof_centre', 'cab_offset'],
            drawing='BT-02, BT-03 (cab_outline, plinth)',
            tags=dict(diameters='inf (family D; measured 14.3 +-1.0 / EXIF 14.75 +-0.5 obs)', plinth='obs photo t1',
                      centre='inf', roof_curb='inf (NAIP rims obs)', interior='unknown (dark placeholder floor / ceiling)'),
            anchors=dict(cab_floor_h=self.floor_h, eye_h=self.floor_h + 1.6)), smooth=True)
        glass = Part('cab_glass', dict(
            src='inf', feature=f'cab glass: {L["cab_n"]} flat frameless panes leaning out, full ring; light butt joints (LOD0); '
            'tinted, see-through (alpha 0.5: the far-side panes and the sky show through, photos t1 / t2)',
            spec=['cab_glass_panels', 'cab_glass_slope', 'cab_glass_type', 'cab_view_angle'], drawing='BT-02, BT-03',
            tags=dict(panes='pub ENR 24 x 6 ft x 11 ft (slant 3.32 m here = 10.9 ft)', arc='inf: glass on both sides in photos '
                      't2/t3/t4; 220/235/270 deg published as view / column-free angles (conflict)', phase='unknown')),
            smooth=False, ao=False)
        gb, gt, rim = self.cab['glass_bottom'], self.cab['glass_top'], self.cab['roof_rim']
        n = L['round_n']
        # plinth ring: deck -> sill [obs photo t1]; top ledge to the glass sill
        lathe(part, [(self.plinth_r, self.deck_h - 0.05), (self.plinth_r, self.sill_h), (gb[0], self.sill_h), (gb[0], self.floor_h)],
              CAB, n, 'plinth', uv_u=n / 4, uv_v=1.0)        # outer face, sill ledge, inner face down to the cab floor
        disc(part, CAB, gb[0], self.floor_h, n, 'cab_interior', up=True)
        if L['ibf'] != 'box':
            # controller consoles: a dark ring 0.9 m high, 0.8 m deep inside the glass [unknown: placeholder only; 13 positions
            # (snippet, unverified); photos t1 / t2 show a dark lower band behind the glass]
            rc = gb[0] - 0.25
            lathe(part, [(rc, self.floor_h), (rc, self.floor_h + 0.9), (rc - 0.8, self.floor_h + 0.9), (rc - 0.8, self.floor_h)],
                  CAB, max(24, n // 2), 'cab_interior', uv_u=24, uv_v=1.0)
        disc(part, CAB, gt[0], gt[1] - 0.01, n, 'cab_interior', up=False)
        # roof fascia (inverted cone) glass head -> rim, coping, inner face, deck, curb
        rf = rim[0]
        # fascia: ~32 radial joints [obs t1/t2] = 8 cladding tiles around; v kept inside one panel row (no row joint seen)
        sl = math.hypot(rf - gt[0], rim[1] - gt[1])
        lathe(part, [(gt[0], gt[1]), (rf, rim[1])], CAB, n, 'clad', uv_u=32 / CLAD_TU, uv_v=sl / 0.46)
        lathe(part, [(rf, rim[1]), (rf - COPING_W, rim[1]), (rf - COPING_W, rim[1] - ROOF_DROP)], CAB, n, 'coping',
              uv_u=n / 4, uv_v=1.0, outward=True)
        disc(part, CAB, rf - COPING_W, rim[1] - ROOF_DROP, n, 'roof_deck', up=True)
        if L['ibf'] != 'box':
            lathe(part, [(CURB_R + 0.15, rim[1] - ROOF_DROP), (CURB_R + 0.15, rim[1] - ROOF_DROP + CURB_H),
                         (CURB_R, rim[1] - ROOF_DROP + CURB_H), (CURB_R, rim[1] - ROOF_DROP)], CAB, max(24, n // 2), 'coping',
                  uv_u=24, uv_v=1.0)
        # glass: flat panes, corners on the sill / head circles; joints = dark butt joints [obs: vertical joints only]
        npn = L['cab_n']
        gap = 0.012 if L['joints'] else 0.0
        for i in range(npn):
            b0, b1 = 360.0 * i / npn, 360.0 * (i + 1) / npn
            q = []
            for (r, h) in (gb, gt):
                for b in (b0, b1):
                    q.append(np.array([CAB[0] + r * bvec(b)[0], CAB[1] + r * bvec(b)[1], h]))
            p00, p01, p10, p11 = q          # bottom b0, bottom b1, top b0, top b1
            if gap:
                db = (p01 - p00); db /= np.linalg.norm(db); dt = (p11 - p10); dt /= np.linalg.norm(dt)
                p00 = p00 + db * gap / 2; p01 = p01 - db * gap / 2; p10 = p10 + dt * gap / 2; p11 = p11 - dt * gap / 2
            ids = [glass.v(p00, (0, 0)), glass.v(p10, (0, 1)), glass.v(p11, (1, 1)), glass.v(p01, (1, 0))]
            orient(glass, ids, 'cab_glass', outside_dir=np.append(bvec((b0 + b1) / 2), 0.0))
        if L['joints']:
            for i in range(npn):
                b = 360.0 * i / npn
                pb = np.array([CAB[0] + gb[0] * bvec(b)[0], CAB[1] + gb[0] * bvec(b)[1], gb[1]])
                pt = np.array([CAB[0] + gt[0] * bvec(b)[0], CAB[1] + gt[0] * bvec(b)[1], gt[1]])
                c = (pb + pt) / 2; ax = (pt - pb) / 2
                tang = np.array([math.cos(math.radians(b)), -math.sin(math.radians(b)), 0.0])
                rad = np.cross(ax / np.linalg.norm(ax), tang)
                if np.dot(rad[0:2], bvec(b)) < 0: rad = -rad
                box(glass, c + rad * 0.01, ax, tang * 0.03, rad * 0.015, 'cab_joint')
        return part, glass

    # ---------------------------------------------------------------- roof masts, poles, red light
    def masts(self, L):
        part = Part('roof_masts', dict(
            src='inf', feature=f'2025 roof masts: {len(DT.MASTS)} whips + {len(DT.POLES)} camera / lamp / bracket poles on a '
            f'ring {DT.MAST_K} x the rim radius; red obstruction light on the rim (SW)',
            spec=['roof_equipment', 'h_antenna_tips', 'obstruction_lighting'], drawing='BT-02 (draw_masts), BT-01',
            tags=dict(count='obs photos t2/t3', bearings_heights='inf (+-5 deg / +-0.3 m)', red_light='obs photo t5; bearing inf; '
                      'fixture type unknown (L-810 or L-864)'), obstruction_light=dict(colour='red', faa_dof_lighting='R')),
            smooth=False, ao=False)
        rim = self.cab['roof_rim']; rr = DT.MAST_K * rim[0]; base_h = rim[1] - ROOF_DROP
        for b, hm in DT.MASTS:
            d = bvec(b); p = np.array([CAB[0] + rr * d[0], CAB[1] + rr * d[1], base_h])
            top = np.array([p[0], p[1], rim[1] + hm * self.k])
            if L['masts']:
                tube(part, [p, top], 0.045, L['masts'], 'mast', r_top=0.015, cap=L['masts'] > 3)
                if L['poles']:
                    box(part, p + np.array([0, 0, 0.1]), np.array([0.12, 0, 0]), np.array([0, 0.12, 0]), np.array([0, 0, 0.1]), 'pole')
        if L['poles']:
            for i, (b, hm) in enumerate(DT.POLES):
                d = bvec(b); p = np.array([CAB[0] + rr * d[0], CAB[1] + rr * d[1], base_h])
                top = np.array([p[0], p[1], rim[1] + hm * self.k])
                tube(part, [p, top], 0.04, 6, 'pole')
                # head: dome camera / lamp / bracket (schematic) [inf]
                box(part, top + np.array([0, 0, 0.08]), np.array([0.13, 0, 0]), np.array([0, 0.13, 0]), np.array([0, 0, 0.08]), 'pole')
        # red obstruction light on the rim (FAA: required, DOF lighting R [pub]; one fixture seen, photo t5 [obs]) in EVERY LOD:
        # it is what is seen from afar at night (the app's beacon glow keys on the material); LOD1 / LOD2 coarser
        nl = 8 if L['poles'] else 4
        d = bvec(RED_LIGHT_BRG); rl = rim[0] - COPING_W / 2
        p = np.array([CAB[0] + rl * d[0], CAB[1] + rl * d[1], rim[1]])
        tube(part, [p, p + np.array([0, 0, 0.12])], 0.06, nl, 'pole')
        tube(part, [p + np.array([0, 0, 0.12]), p + np.array([0, 0, 0.30])], 0.09, nl, 'red_light', r_top=0.04)
        return part

    # ---------------------------------------------------------------- base building (IBF)
    def ibf_frame(self):
        ring = np.asarray(DT.D.sfom('Air Traffic Control Tower')[0][0], float)
        Nn, W, S, E = [world_to_local(p) for p in ring]
        return Nn, W, S, E

    def base_building(self, L):
        part = Part('ibf', dict(
            src='obs', feature='base building (IBF): SFO Museum footprint 44.95 x 27.20 m, 3 storeys; roof = rim - (3.46 D + 0.7) '
            '(family), parapet 0.7 m; airside parapet panel band + continuous dark glazing band (photo t2); landside curtain-wall '
            'bay (photo t4); sunken roof garden (NAIP outline)',
            spec=['ibf_footprint', 'h_ibf_roof', 'ibf_storeys', 'ibf_facade', 'ibf_roof_garden', 'h_roof_garden'],
            drawing='BT-01, BT-02 A/B (draw_ibf_faces), BT-03',
            tags=dict(footprint='obs SFO Museum (+-1.5-5 m)', roof='inf (photo span / NAIP ratio, family)', airside_band='obs photo t2 '
                      '(heights below the parapet; SW part hidden = unknown, drawn as panels)', curtain_wall='obs photo t4 (extent inf '
                      '+-5 m; foot unknown)', panel_module='inf', garden_outline='obs NAIP 2024 (lean-corrected, +-1 m)',
                      garden_level='inf', other_faces='unknown (grey metal panels per spec text)')), smooth=False)
        Nn, W, S, E = self.ibf_frame()
        cen = (Nn + W + S + E) / 4
        ibf, par = self.ibf, self.par
        top = par if L['ibf'] != 'box' else par
        faces = [('NW', Nn, W), ('SW', W, S), ('SE', S, E), ('NE', E, Nn)]
        pw, ph = IBF_PANEL
        u_rA = lambda p: float(np.dot(np.array([p[0], -p[1]]), RIGHT_A))  # local -> world offset from the axis . right_A
        for nm, A, B in faces:
            e = (B - A); Lf = float(np.linalg.norm(e)); e /= Lf
            out = np.array([e[1], -e[0]])
            if np.dot(out, (A + B) / 2 - cen) < 0: out = -out
            # (s0, s1, h0, h1, mat) rectangles of this face
            rects = []
            if nm == 'SE':
                gt_ = par - DT.IBF_AIR_BAND[0]; gb_ = gt_ - DT.IBF_AIR_BAND[1]
                ua, ub = u_rA(A), u_rA(B)
                s_obs = (DT.IBF_AIR_BAND[2] - ua) / (ub - ua) * Lf
                rects += [(0, Lf, 0, gb_, 'ibf_panel'), (0, s_obs, gb_, gt_, 'ibf_panel'), (s_obs, Lf, gb_, gt_, 'ibf_glass_dark'),
                          (0, Lf, gt_, top, 'ibf_panel')]
                self.se_band = dict(s_obs=s_obs, gb=gb_, gt=gt_, L=Lf)
            elif nm == 'NW':
                s0, s1, hv_, nb = DT.IBF_CW
                bot = ibf - hv_
                rects += [(0, s0, 0, top, 'ibf_panel'), (s1, Lf, 0, top, 'ibf_panel'), (s0, s1, 0, bot, 'ibf_panel'),
                          (s0, s1, bot, ibf, 'ibf_curtain'), (s0, s1, ibf, top, 'ibf_panel')]
                self.nw_cw = dict(s0=s0, s1=s1, bot=bot, top=ibf, bays=nb)
            else:
                rects += [(0, Lf, 0, top, 'ibf_panel')]
            for s0, s1, h0, h1, mat in rects:
                if s1 - s0 < 1e-3 or h1 - h0 < 1e-3: continue
                pts = [A + e * s0, A + e * s1]
                q = [np.array([pts[0][0], pts[0][1], h0]), np.array([pts[1][0], pts[1][1], h0]),
                     np.array([pts[1][0], pts[1][1], h1]), np.array([pts[0][0], pts[0][1], h1])]
                uv = [(s0 / pw, h0 / ph), (s1 / pw, h0 / ph), (s1 / pw, h1 / ph), (s0 / pw, h1 / ph)]
                ids = [part.v(p, t) for p, t in zip(q, uv)]
                orient(part, ids, mat, outside_dir=np.append(out, 0.0))
        # roof (and parapet) in the bilinear footprint frame
        def P(s, t):
            return Nn + (W - Nn) * s + (E - Nn) * t + (S - W - E + Nn) * s * t
        Ls = float(np.linalg.norm(W - Nn)); Lt = float(np.linalg.norm(E - Nn))
        if L['ibf'] == 'box':
            ids = [part.v(np.append(p, top), (p[0] / 4, p[1] / 4)) for p in (Nn, W, S, E)]
            orient(part, ids, 'roof_deck', outside_dir=(0, 0, 1))
            return part
        it = PARAPET_T
        si, ti = it / Ls, it / Lt
        gs, gtt = GARDEN[0] / Ls, GARDEN[1] / Lt
        sb = [si, gs, 1 - si]; tb = [ti, gtt, 1 - ti]
        for a in range(2):
            for b in range(2):
                garden = (a == 1 and b == 1)
                hz = ibf - GARDEN_DROP if garden else ibf
                q = [P(sb[a], tb[b]), P(sb[a + 1], tb[b]), P(sb[a + 1], tb[b + 1]), P(sb[a], tb[b + 1])]
                ids = [part.v(np.append(p, hz), (p[0] / 4, p[1] / 4)) for p in q]
                orient(part, ids, 'garden' if garden else 'roof_deck', outside_dir=(0, 0, 1))
        # garden pit walls: inner sides (s = gs, t = gtt) from the garden floor to the roof; outer sides up to the parapet top
        g0 = ibf - GARDEN_DROP
        cg = np.append(P((gs + 1 - si) / 2, (gtt + 1 - ti) / 2), g0 + 0.5)
        for (pa, pb) in ((P(gs, gtt), P(1 - si, gtt)), (P(gs, gtt), P(gs, 1 - ti)),
                         (P(1 - si, gtt), P(1 - si, 1 - ti)), (P(gs, 1 - ti), P(1 - si, 1 - ti))):
            q = [np.append(pa, g0), np.append(pb, g0), np.append(pb, ibf), np.append(pa, ibf)]
            ids = [part.v(p, (np.linalg.norm(p[0:2] - pa) / pw, p[2] / ph)) for p in q]
            orient(part, ids, 'ibf_panel', outside_dir=np.append(cg[0:2] - (pa + pb) / 2, 0.0))
        # parapet: inner faces (roof -> top) and coping (top), around the outside of the roof rectangle
        inner = [P(si, ti), P(1 - si, ti), P(1 - si, 1 - ti), P(si, 1 - ti)]
        outer = [Nn, W, S, E]
        for i in range(4):
            a, b = inner[i], inner[(i + 1) % 4]
            # the garden side of the parapet starts at the garden floor (walls added above); here: roof -> parapet top
            q = [np.append(a, ibf), np.append(b, ibf), np.append(b, par), np.append(a, par)]
            ids = [part.v(p, (np.linalg.norm(p[0:2] - a) / pw, p[2] / ph)) for p in q]
            orient(part, ids, 'ibf_panel', outside_dir=np.append(cen - (a + b) / 2, 0.0))
            oa, ob = outer[i], outer[(i + 1) % 4]
            q = [np.append(oa, par), np.append(ob, par), np.append(b, par), np.append(a, par)]
            ids = [part.v(p, (p[0] / 2, p[1] / 2)) for p in q]
            orient(part, ids, 'coping', outside_dir=(0, 0, 1))
        if L['ibf'] == 'full':
            self.ibf_mullions(self._detail('ibf_mullions', dict(
                src='obs', feature='mullions of the airside glazing band and of the landside curtain-wall bay', spec=['ibf_facade'],
                drawing='BT-02 A/B (draw_ibf_faces)', tags=dict(curtain_wall='obs photo t4 (5 bays, transoms 1.2 m)',
                                                                glazing_band='pitch 1.5 m inf'))), faces, cen)
        return part

    def ibf_mullions(self, part, faces, cen):
        """LOD0: mullions of the airside glazing band (every 1.5 m [inf]) and of the landside curtain-wall bay (5 bays, transoms
        ~1.2 m [obs photo t4]); 0.08 m wide, 0.12 m proud."""
        for nm, A, B in faces:
            e = (B - A); Lf = float(np.linalg.norm(e)); e /= Lf
            out = np.array([e[1], -e[0]])
            if np.dot(out, (A + B) / 2 - cen) < 0: out = -out
            o3 = np.append(out, 0.0); e3 = np.append(e, 0.0)
            if nm == 'SE':
                b = self.se_band
                for s in np.arange(b['s_obs'], b['L'] + 1e-6, GLAZING_MULLION):
                    p = np.append(A + e * s, (b['gb'] + b['gt']) / 2) + o3 * 0.06
                    box(part, p, np.array([0, 0, (b['gt'] - b['gb']) / 2]), e3 * 0.04, o3 * 0.06, 'mullion', skip=('-z',))
                for h in (b['gb'], b['gt']):
                    s0, s1 = b['s_obs'], b['L']
                    p = np.append(A + e * (s0 + s1) / 2, h) + o3 * 0.06
                    box(part, p, e3 * (s1 - s0) / 2, np.array([0, 0, 0.05]), o3 * 0.06, 'mullion', skip=('-z',))
            if nm == 'NW':
                c = self.nw_cw
                for i in range(c['bays'] + 1):
                    s = c['s0'] + (c['s1'] - c['s0']) * i / c['bays']
                    p = np.append(A + e * s, (c['bot'] + c['top']) / 2) + o3 * 0.06
                    box(part, p, np.array([0, 0, (c['top'] - c['bot']) / 2]), e3 * 0.05, o3 * 0.06, 'mullion', skip=('-z',))
                for h in np.arange(c['top'], c['bot'] - 1e-6, -1.2):
                    p = np.append(A + e * (c['s0'] + c['s1']) / 2, h) + o3 * 0.05
                    box(part, p, e3 * (c['s1'] - c['s0']) / 2, np.array([0, 0, 0.04]), o3 * 0.05, 'mullion', skip=('-z',))

    def ibf_equipment(self):
        part = Part('ibf_equipment', dict(
            src='inf', feature='rooftop unit beside the shaft foot (photo t4) and the guard rail along the airside parapet (photo t2)',
            spec=['ibf_facade'], drawing='not on the sheets (photo features, LOD0 only)',
            tags=dict(rooftop_unit='obs photo t4; position inf (+-5 m along the view ray)', rail='obs photo t2; height inf (42 in)')),
            smooth=False)
        Nn, W, S, E = self.ibf_frame()
        eL = (W - Nn) / np.linalg.norm(W - Nn); eT = (E - Nn) / np.linalg.norm(E - Nn)
        c = Nn + eL * AHU['s'] + eT * AHU['t']
        z = self.ibf + AHU['H'] / 2
        box(part, np.append(c, z), np.append(eL, 0) * AHU['L'] / 2, np.append(eT, 0) * AHU['W'] / 2, np.array([0, 0, AHU['H'] / 2]),
            'equipment', uvs=1.2, skip=('-z',))
        # guard rail on the airside (SE) parapet coping [obs photo t2]
        rp = self._detail('ibf_rails', dict(src='obs', feature='guard rail along the airside parapet (photo t2)',
                                            spec=['ibf_facade'], drawing='-', tags=dict(rail='obs photo t2; height inf (42 in)')))
        e = (E - S); Lf = float(np.linalg.norm(e)); e /= Lf
        inward = np.array([-e[1], e[0]])
        if np.dot(inward, (Nn + W + S + E) / 4 - (S + E) / 2) < 0: inward = -inward
        z0 = self.par
        for s in np.arange(0.5, Lf - 0.4, 2.0):
            p = np.append(S + e * s + inward * 0.15, z0)
            tube(rp, [p, p + np.array([0, 0, RAIL_H])], 0.025, 4, 'rail', cap=False)
        for hh in (RAIL_H, RAIL_H / 2):
            a = np.append(S + e * 0.5 + inward * 0.15, z0 + hh); b = np.append(S + e * (Lf - 0.5) + inward * 0.15, z0 + hh)
            tube(rp, [a, b], 0.022, 4, 'rail', cap=False)
        return part


def build(fam=1, lods=(0, 1, 2)):
    """{lod: {node name: Part}}, the Tower instance (for anchors / metadata)."""
    T_ = Tower(fam)
    out = {}
    for lod in lods:
        T_.notes = []
        T_.details = {}
        # the deck reads the shell vertices: keep a handle on the shell part while building
        L = LODS[lod]
        H = T_.stations(lod)
        ins = [T_.insert(h, L['lobe_n']) for h in H]
        parts = {}
        shell = T_.shell(H, ins, L)
        T_._shell_part = shell
        parts['shaft'] = shell
        land, rib = T_.landside(H, ins, L)
        parts['landside'] = land; parts['ribbon'] = rib
        parts['flare_deck'] = T_.deck(H, ins, L)
        cab, glass = T_.cab_parts(L)
        parts['cab'] = cab; parts['cab_glass'] = glass
        if L['masts'] or L['poles']:
            parts['roof_masts'] = T_.masts(L)
        parts['ibf'] = T_.base_building(L)
        if L['ibf'] == 'full':
            parts['ibf_equipment'] = T_.ibf_equipment()
        parts.update(T_.details)
        out[lod] = {k: v for k, v in parts.items() if v.F}
        out[lod]['_notes'] = list(dict.fromkeys(T_.notes))
        out[lod]['_stations'] = H
    return out, T_


if __name__ == '__main__':
    import time
    for fam in (1, 2):
        t = time.time()
        m, Tw = build(fam)
        for lod, parts in m.items():
            tot = sum(p.tris() for k, p in parts.items() if not k.startswith('_'))
            print(f'F{fam} LOD{lod}: {tot} tris', {k: p.tris() for k, p in parts.items() if not k.startswith('_')})
            for n_ in parts['_notes'][:3]: print('   note:', n_)
        print(f'  {time.time() - t:.1f} s; ibf {Tw.ibf:.2f} ht {Tw.ht:.2f} h_top {Tw.h_top:.2f} capped {Tw.rib_capped}')
