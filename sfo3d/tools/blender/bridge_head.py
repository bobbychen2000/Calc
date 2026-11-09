"""Bridge-head vestibule extents (close-out round 4, buildings): shared by tools/blender/itb_geom.py (A / G) and
tools/blender/dom_geom.py (B-F).

The app's fixed jet-bridge walkway starts at walk[0] (js/live/gates.js, read through tools/blender/app_bridges.json) with its
end face across the walkway there. The 3-D asset must close that end over the walkway's full width (2.6 m, gates.js WALK_W):
the round-3 verifier found walkway ends 0.2-0.96 m in front of the 3-D facade (a strip of daylight), ends on oblique facades
open on one side, and ends whose edge passes a bump-out corner. The extent of the closing box is measured here in the
walkway frame (u = along the walkway away from the building, 0 at the end face; v across):

  depth(o) = distance along -u from the end-face point at v = o to the first facade point of the host solids (negative: the
             facade lies on the walkway side - the end is inside the building there; None: no facade within reach - past a
             corner), sampled every 0.1 m over the vestibule width.
  kind 'vestibule': some point of the walkway end (|o| <= 1.3 + 0.05) lies more than VEST_MIN in front of the facade -> box
             u in [-back, 0] (back = the deepest facade point within VEST_BACK_CAP of the nearest one, over the vestibule
             width, + VEST_IN into the facade); where the end passes a corner the box's back stands free (a closed box).
  kind 'nub':  the walkway end lies inside the facade but its edge passes the facade's corner (open side strip) -> box
             u in [-VEST_IN, front] with front NUB_RECESS behind the facade plane (no coplanar faces): the strip of the walkway
             end outside the corner is enclosed, the rest of the box is inside the building.
  None:        the walkway end lies inside (or within VEST_MIN of) the facade across its width.
The box width is VEST_W (the walkway + 0.3 m each side). Callers clip it clear of the other bridges' fixed solids
(other_solids_cut) and of the drums. Every value here is a modelling choice [inf]; the walkway ends are the data's.
"""
import math

import numpy as np
import shapely
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

VEST_W = 3.2                 # gates.js WALK_W 2.6 + 0.3 each side (dom_geom VEST['w'] since review r1)
WALK_HW = 1.3                # gates.js WALK_W / 2
VEST_IN = 0.15               # into the facade
VEST_BACK_CAP = 1.0          # depth samples more than this behind the nearest facade point: past a corner
VEST_MIN = 0.02              # a walkway end in front of the facade by more than this is closed by a vestibule
NUB_RECESS = 0.03            # nub front behind the facade plane (no coplanar faces with the host wall)
VEST_CLEAR = 0.05            # to the other bridges' fixed walkway solids / drums (static app solids; gates.js solidsQ)
REACH_BACK = 12.0            # facade search behind the end face
STEP = 0.1


def frame(b):
    """(E, u, v) of an app_bridges.json record: walkway start and unit vectors (world x, z)."""
    w = b['walk']
    E = np.array([w[0][0], w[0][2]], float); N = np.array([w[1][0], w[1][2]], float)
    u = (N - E) / np.linalg.norm(N - E)
    return E, u, np.array([-u[1], u[0]])


def depths(U, E, u, v, half=VEST_W / 2):
    """[(o, depth or None)] over the vestibule width against the host polygon U (same plan frame as E)."""
    out = []
    for o in np.arange(-half, half + 1e-6, STEP):
        q = E + v * o
        x = shapely.LineString([tuple(q + u * 3.0), tuple(q - u * REACH_BACK)]).intersection(U)
        ts = [float((q - c) @ u) for g in (x.geoms if hasattr(x, 'geoms') else [x]) if not g.is_empty for c in np.asarray(g.coords)]
        out.append((round(float(o), 3), min(ts) if ts else None))
    return out


def head_box(dep):
    """the closing box of a walkway end from its depth samples: dict(kind, a0, a1 (u range), gap_max, dmin, overhang) or
    dict(kind=None, ...) - see the module comment."""
    ok = [d for _, d in dep if d is not None]
    if not ok: return dict(kind=None, why='no facade within reach', dmin=None, gap_max=None, overhang=None)
    dmin = min(ok)
    inner = [(o, d) for o, d in dep if abs(o) <= WALK_HW + 0.05]
    valid_in = [d for _, d in inner if d is not None and d <= dmin + VEST_BACK_CAP]
    overhang = len(valid_in) < len(inner)
    gap_max = max(valid_in) if valid_in else dmin
    if gap_max > VEST_MIN:
        back = max(d for _, d in dep if d is not None and d <= dmin + VEST_BACK_CAP) + VEST_IN
        return dict(kind='vestibule', a0=-max(VEST_IN, back), a1=0.0, gap_max=round(gap_max, 3), dmin=round(dmin, 3), overhang=overhang)
    if overhang:
        front = min(-d for d in valid_in) - NUB_RECESS
        if front <= -VEST_IN + 0.05: front = 0.0
        return dict(kind='nub', a0=-VEST_IN, a1=max(0.0, front), gap_max=round(gap_max, 3), dmin=round(dmin, 3), overhang=True)
    return dict(kind=None, why='walkway end inside the facade', dmin=round(dmin, 3), gap_max=round(gap_max, 3), overhang=False)


def rect(c, u, a0, a1, hw):
    """plan rectangle along unit u from c + u a0 to c + u a1, half width hw."""
    v = np.array([-u[1], u[0]])
    return Polygon([tuple(c + u * a0 - v * hw), tuple(c + u * a1 - v * hw), tuple(c + u * a1 + v * hw), tuple(c + u * a0 + v * hw)])


def drum_disc(c, r, segs=64):
    """plan disc of a drum keep-out (centre c, radius r = rotR + clearance). segs = shapely quad_segs; below the full 64 the
    polygon CIRCUMSCRIBES the circle (vertices at r / cos(pi / (4 segs))), so a coarse cut never reaches inside the clearance
    (close-out round 5: the LOD2 bridge heads use 8 - a 32-gon, at most r x 0.5 % beyond the circle)."""
    if segs >= 64: return Point(*c).buffer(r, 64)
    return Point(*c).buffer(r / math.cos(math.pi / (4 * segs)), segs)


def other_solids_cut(all_bridges, mine, E, z0, z1, reach=8.0, drums=True, segs=64):
    """union of the OTHER bridges' fixed solids (app_bridges rest walkway segments, + VEST_CLEAR; rotunda drums, rotR +
    VEST_CLEAR) whose height band meets [z0, z1] (above the apron) near E (world x, z), or None. segs: drum_disc."""
    cut = []
    for b in all_bridges:
        if (b['stand'], b['door'], b['upper']) in mine: continue
        for so in b['rest']:
            if so['lo'] > z1 or so['hi'] < z0: continue
            if so['part'] == 'rotunda' and not drums: continue
            c = np.array(so['c'], float)
            if np.hypot(*(c - E)) > so['hl'] + so['hw'] + reach: continue
            if so['part'] == 'rotunda':
                cut.append(drum_disc(c, float(so.get('round') or so['hl']) + VEST_CLEAR, segs))
            else:
                cut.append(rect(c, np.array(so['u'], float), -so['hl'], so['hl'], so['hw']).buffer(VEST_CLEAR, join_style=2))
    return unary_union(cut) if cut else None


def own_drum_cut(b, z0, z1, segs=64):
    """the bridge's own rotunda drum (rotR + VEST_CLEAR) if its band meets [z0, z1], or None (world x, z). segs: drum_disc."""
    lo, hi = b['Hr'] - 0.3, b['Hr'] + 3.3
    if lo > z1 or hi < z0: return None
    return drum_disc(b['rot'], float(b['rotR']) + VEST_CLEAR, segs)


def fixed_solids_near(all_bridges, E, reach=8.0):
    """every bridge's fixed rest solids near E (world x, z): [(key (stand, door, upper), seg or None, part, plan polygon,
    lo, hi)] - walkway segments as their rectangles, drums as full-resolution discs (no clearance added; heights above the
    apron, app_bridges.json)."""
    out = []
    for b in all_bridges:
        key = (b['stand'], b['door'], b['upper'])
        for so in b['rest']:
            c = np.array(so['c'], float)
            if np.hypot(*(c - E)) > so['hl'] + so['hw'] + reach: continue
            if so['part'] == 'rotunda':
                g = Point(*c).buffer(float(so.get('round') or so['hl']), 64)
            elif so['part'] == 'walkway':
                g = rect(c, np.array(so['u'], float), -so['hl'], so['hl'], so['hw'])
            else:
                continue
            out.append((key, so.get('seg'), so['part'], g, float(so['lo']), float(so['hi'])))
    return out


def clip_member(n_lo, n_hi, z0, z1, foot_fn, obstacles, keep_frac=0.5, min_h=0.1):
    """clip a door-surround member against the app's fixed solids (close-out round 5, verifier finding 'ITB door surrounds').
    The member spans n_lo..n_hi along the door line and z0..z1 (above the apron); foot_fn(a, b) is its REAL plan footprint
    between a and b along that line. obstacles: [(plan polygon, lo, hi)]. An obstacle closer than VEST_CLEAR in plan whose
    band starts > min_h above the member's foot caps the member's top VEST_CLEAR below it (stacked walkways: the lower
    door's head stops under the upper deck's walkway floor); any other one removes its stretch of the member (+ VEST_CLEAR).
    -> (n_lo, n_hi, z0, z1) of the piece kept (the stretch containing the member's middle, else the longest), or None when
    less than keep_frac of the length or less than min_h of the height is left."""
    ivs = [(n_lo, n_hi)]
    L0 = n_hi - n_lo
    for g, lo, hi in obstacles:
        if lo >= z1 + VEST_CLEAR or hi <= z0 - VEST_CLEAR: continue
        gb = g.buffer(VEST_CLEAR - 1e-3)
        x = foot_fn(n_lo, n_hi).intersection(gb)
        if x.is_empty or x.area < 1e-6: continue
        if lo > z0 + min_h:
            z1 = min(z1, lo - VEST_CLEAR); continue
        # the stretch along the member line that meets the obstacle (projected by bisection on sub-footprints, 1 cm)
        pts = np.arange(n_lo, n_hi + 1e-9, 0.01)
        hit = [foot_fn(a, min(a + 0.01, n_hi)).intersects(gb) for a in pts[:-1]]
        new = []
        for a, b_ in ivs:
            cur = None
            for k, h in enumerate(hit):
                s0, s1 = pts[k], pts[k + 1]
                if s1 <= a or s0 >= b_: continue
                if not h:
                    cur = [max(s0, a), min(s1, b_)] if cur is None else [cur[0], min(s1, b_)]
                elif cur is not None:
                    new.append(tuple(cur)); cur = None
            if cur is not None: new.append(tuple(cur))
        ivs = [iv for iv in new if iv[1] - iv[0] > 1e-6]
        if not ivs: return None
    if z1 - z0 < min_h: return None
    mid = 0.5 * (n_lo + n_hi)
    best = next((iv for iv in ivs if iv[0] <= mid <= iv[1]), max(ivs, key=lambda iv: iv[1] - iv[0]))
    if best[1] - best[0] < keep_frac * L0 - 1e-6: return None
    return best[0], best[1], z0, z1
