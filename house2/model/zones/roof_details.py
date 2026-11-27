"""Zone 'roof_details' of house 2: everything that sits ON the roofs.

Source: survey/roof.json (aerial p29 pixels) + survey/roof_3d.json (every roof plane z = a X + b Y + c).  An aerial
pixel becomes a world point by meeting its camera ray with the plane the survey names ('on'), lifted by the height of
the thing above the shingles -- so panels, vents and skylights land where the aerial shows them whatever the height.

  * solar arrays a1-a6 = 50 panels (6 + 10 + 19 + 5 + 7 + 3): the survey's panel rectangles split into single modules,
    each a framed slab 5 cm over its plane;
  * 2 curb skylights, 23 roof vents by kind (box / pipe / dome / turbine / riser), the 2 PV conduits;
  * 2 stacked-stone chimneys with cream metal shrouds and round spark arrestors.  Tops by tools/epi.py (cap centre's
    aerial ray drawn into p28): north shroud top ~5.6 m (it stands from the ground at the north wing's wall and ends
    BELOW the two-storey eave), south ~9.1 m (through the east eave of the south block, 2.7 m above it);
  * gutters on every eave edge (cream K-style box under the roof edge), downspouts at the ends of the main runs
    [typical positions: the photographs resolve only a few], light metal caps on ridges and hips (they read pale grey in
    p29 / p28, not dark), a flashing band round the flat deck.
"""
import json
import os

import numpy as np

from model import frame, plan
from model.kit import Geo, Part
from tools import cams as CAMS

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SURVEY = {e['id']: e for e in json.load(open(os.path.join(HERE, 'survey', 'roof.json')))['elements']}
ROOF = json.load(open(os.path.join(HERE, 'survey', 'roof_3d.json')))
PLANES = {p['id']: p for p in ROOF['planes']}
AERIAL = 'photos/p29_ddf5dc.jpg'
UP = np.array([0.0, 0.0, 1.0])

MATERIALS = {
    'solar_frame': dict(color=(0.55, 0.56, 0.58), roughness=0.4, metallic=0.8),
    'gutter_cream': dict(color=(0.86, 0.84, 0.78), roughness=0.55),
    'ridge_cap': dict(color=(0.50, 0.51, 0.53), roughness=0.45, metallic=0.5),
    'vent_metal': dict(color=(0.20, 0.20, 0.21), roughness=0.6, metallic=0.4),
    'vent_white': dict(color=(0.82, 0.82, 0.80), roughness=0.5),
    'chimney_shroud': dict(color=(0.66, 0.66, 0.62), roughness=0.5, metallic=0.4),
    'conduit': dict(color=(0.42, 0.43, 0.44), roughness=0.5, metallic=0.6),
}

PANEL_LIFT = 0.05          # panel underside above the shingles
PANEL_T = 0.04
PANEL_GAP = 0.012          # half the joint between neighbouring modules
# survey rectangles (p29 px: x0, y0, x1, y1) -> (n along image x, n along image y) modules
ARRAYS = {
    'a1': ('g_n', [((348, 304, 507, 355), 5, 1), ((390, 357, 453, 384), 1, 1)]),
    'a2': ('cw_n', [((523, 368, 681, 418), 5, 1), ((485, 420, 642, 472), 5, 1)]),
    'a3': ('cc_w', [((643, 517, 693, 744), 1, 7), ((695, 512, 749, 775), 1, 8), ((751, 548, 782, 804), 1, 4)]),
    'a4': ('bg_n', [((943, 568, 1073, 621), 4, 1), ((1012, 540, 1076, 567), 1, 1)]),
    'a5': ('e', [((848, 715, 912, 845), 1, 4), ((915, 750, 977, 845), 1, 3)]),
}
A6 = ('ne', [(952, 899), (995, 857), (1063, 923), (1019, 965)], 3)       # quad, 3 modules along its long side

# chimneys: aerial cap centre + cap box, heights from tools/epi.py into p28 (stone top, shroud top)
CHIMNEYS = {
    'chimney_n': dict(cap=(715, 291, 741, 320), z_stone=5.05, z_top=5.60),
    'chimney_s': dict(cap=(1036, 1255, 1080, 1290), z_stone=8.30, z_top=9.10),
}
GUTTER_KINDS = ('eave', 'eave_over_lower_roof', 'eave_end')
GUTTER = [(0.0, -0.035), (0.0, -0.145), (0.075, -0.145), (0.115, -0.10), (0.115, -0.06), (0.13, -0.035)]
DOWNSPOUT_MIN_RUN = 4.0    # m: a gutter run this long gets a downspout at its lower-X / lower-Y end


# ---------------------------------------------------------------------------------------------------------------
def _cam():
    return frame.world_cams()[AERIAL]


def on_plane(pid, uv, lift=0.0):
    """World points where the aerial rays of pixels uv meet plane pid lifted by `lift` along its normal."""
    a, b, c = PLANES[pid]['plane']
    c = c + lift * np.sqrt(1 + a * a + b * b)
    uv = np.atleast_2d(np.asarray(uv, float))
    o, d = CAMS.ray(_cam(), uv)
    t = (a * o[0] + b * o[1] + c - o[2]) / (d[:, 2] - a * d[:, 0] - b * d[:, 1])
    return o + t[:, None] * d


def plane_frame(pid):
    """(normal, along-eave unit, up-slope unit) of a plane."""
    a, b, _ = PLANES[pid]['plane']
    n = np.array([-a, -b, 1.0])
    n /= np.linalg.norm(n)
    g = np.array([a, b, 0.0])
    if np.linalg.norm(g) < 1e-6:
        return n, np.array([1.0, 0, 0]), np.array([0, 1.0, 0])
    ex = np.cross(n, g)
    ex /= np.linalg.norm(ex)
    ey = np.cross(n, ex)
    return n, ex, ey if ey[2] > 0 else -ey


def _slab(geo, corners, n, t, mat, mat_top=None, inset=0.0):
    """A thin slab over a planar quad (corners counter-clockwise seen from above), thickness t along n."""
    q = np.asarray(corners, float)
    if np.dot(np.cross(q[1] - q[0], q[2] - q[0]), n) < 0:
        q = q[::-1]
    top = q + n * t
    for i in range(4):
        j = (i + 1) % 4
        geo.poly(mat, [q[i], q[j], top[j], top[i]])
    if mat_top and inset:
        c = top.mean(0)
        inn = np.array([p + (c - p) / np.linalg.norm(c - p) * inset * 1.414 for p in top])
        geo.poly(mat, top, holes=[inn])                          # the frame is a ring: nothing lies under the glass
        geo.poly(mat_top, inn)
    else:
        geo.poly(mat_top or mat, top)


def _split(q, nu, nv, gap):
    """Split quad q (p00, p10, p11, p01) into nu x nv cells, each shrunk by `gap` on every side."""
    q = np.asarray(q, float)
    f = lambda u, v: (q[0] * (1 - u) * (1 - v) + q[1] * u * (1 - v) + q[2] * u * v + q[3] * (1 - u) * v)  # noqa: E731
    out = []
    lu = np.linalg.norm(q[1] - q[0]) / nu
    lv = np.linalg.norm(q[3] - q[0]) / nv
    gu, gv = gap / lu, gap / lv
    for i in range(nu):
        for j in range(nv):
            u0, u1, v0, v1 = (i + gu) / nu, (i + 1 - gu) / nu, (j + gv) / nv, (j + 1 - gv) / nv
            out.append([f(u0, v0), f(u1, v0), f(u1, v1), f(u0, v1)])
    return out


def solar(geo):
    count = {}
    quads = []
    for aid, (pid, rects) in ARRAYS.items():
        for (x0, y0, x1, y1), nu, nv in rects:
            q = on_plane(pid, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], PANEL_LIFT)
            quads.append((aid, pid, q, nu, nv))
    pid, poly, k = A6
    quads.append(('a6', pid, on_plane(pid, [poly[1], poly[2], poly[3], poly[0]], PANEL_LIFT), k, 1))
    for aid, pid, q, nu, nv in quads:
        n = plane_frame(pid)[0]
        for cell in _split(q, nu, nv, PANEL_GAP):
            _slab(geo, cell, n, PANEL_T, 'solar_frame', 'solar', inset=0.02)
            count[aid] = count.get(aid, 0) + 1
        # two mounting rails under each block, along its longer side
        e_u, e_v = q[1] - q[0], q[3] - q[0]
        along, across = (e_u, e_v) if np.linalg.norm(e_u) > np.linalg.norm(e_v) else (e_v, e_u)
        for f in (0.25, 0.75):
            a0 = q[0] + across * f - n * PANEL_LIFT * 0.5
            geo.prism('solar_frame', [(-0.02, -0.025), (0.02, -0.025), (0.02, 0.025), (-0.02, 0.025)], a0, a0 + along,
                      up=n, cap=False)
    return count


def skylights(geo):
    e = SURVEY['roof.skylight_bcn']
    x0, y0, x1, y1 = SURVEY['roof.skylight_bce']['bbox']
    for pid, px in (('bc_n', e['poly']), ('bc_e', [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])):
        n = plane_frame(pid)[0]
        q = on_plane(pid, px, 0.0)
        # square the surveyed quad up: a rectangle about its centre along its own longest edge
        c = q.mean(0)
        e_u = q[1] - q[0]
        e_u /= np.linalg.norm(e_u)
        e_v = np.cross(n, e_u)
        hu = 0.5 * np.mean([abs((q[1] - q[0]) @ e_u), abs((q[2] - q[3]) @ e_u)])
        hv = 0.5 * np.mean([abs((q[3] - q[0]) @ e_v), abs((q[2] - q[1]) @ e_v)])
        r = [c - e_u * hu - e_v * hv, c + e_u * hu - e_v * hv, c + e_u * hu + e_v * hv, c - e_u * hu + e_v * hv]
        _slab(geo, [p - n * 0.02 for p in r], n, 0.16, 'trim_white', 'skylight_glass', inset=0.05)


def _vent_kind(desc):
    d = desc.lower()
    if 'conduit' in d:
        return 'riser'
    if 'turbine' in d or 'white dome' in d:
        return 'turbine'
    if 'dome' in d or 'round' in d:
        return 'dome'
    if 'tall pipe' in d:
        return 'tall'
    if 'pipe' in d:
        return 'pipe_white' if 'white cap' in d else 'pipe'
    return 'box'


def vents(geo):
    kinds = {}
    for eid, e in SURVEY.items():
        if e['type'] != 'roof_vent':
            continue
        pid = e['attrs']['on'].split('/')[0].strip().replace('roof.', '')
        k = _vent_kind(e['desc'])
        kinds[k] = kinds.get(k, 0) + 1
        n, ex, ey = plane_frame(pid)
        h = {'box': 0.07, 'dome': 0.08, 'turbine': 0.15, 'tall': 0.45, 'riser': 0.12}.get(k, 0.18)
        p = on_plane(pid, e['point'], h)[0] - n * h              # the foot of something whose middle the pixel shows
        if k == 'box':                                           # low slant-back box vent
            geo.obox('vent_metal', p, ex, ey, n, (-0.20, -0.20, -0.01), (0.20, 0.20, 0.03))
            geo.obox('vent_metal', p, ex, ey, n, (-0.15, -0.13, 0.03), (0.15, 0.15, 0.14))
        elif k in ('pipe', 'pipe_white', 'tall'):
            L = 0.90 if k == 'tall' else 0.36
            geo.obox('vent_metal', p, ex, ey, n, (-0.14, -0.14, -0.01), (0.14, 0.14, 0.015))       # flashing
            geo.cylinder('vent_metal', p - UP * 0.03, p + UP * L, 0.04, n=8)
            if k == 'pipe_white':
                geo.cylinder('vent_white', p + UP * L, p + UP * (L + 0.07), 0.065, n=8)
        elif k == 'dome':
            geo.cylinder('vent_metal', p - UP * 0.05, p + UP * 0.13, 0.09, n=10)
            geo.cylinder('vent_metal', p + UP * 0.13, p + UP * 0.17, 0.17, n=12)
        elif k == 'turbine':
            geo.cylinder('vent_white', p - UP * 0.05, p + UP * 0.12, 0.11, n=10)
            geo.cylinder('vent_white', p + UP * 0.12, p + UP * 0.30, 0.17, n=12)
            geo.cylinder('vent_white', p + UP * 0.30, p + UP * 0.34, 0.10, n=10)
        else:                                                    # conduit riser / junction box
            geo.obox('conduit', p, ex, ey, n, (-0.08, -0.08, 0.0), (0.08, 0.08, 0.24))
    return kinds


def _in_poly(poly, x, y):
    poly = np.asarray(poly, float)
    q = np.roll(poly, -1, 0)
    c = ((poly[:, 1] > y) != (q[:, 1] > y)) & (x < (q[:, 0] - poly[:, 0]) * (y - poly[:, 1]) /
                                               (q[:, 1] - poly[:, 1] + 1e-12) + poly[:, 0])
    return bool(c.sum() % 2)


def _plane_at(uv, prefer):
    """The roof plane an aerial pixel lies on (survey polygons); `prefer` breaks ties / is the fallback."""
    hits = [p for p in PLANES if 'roof.' + p in SURVEY and 'poly' in SURVEY['roof.' + p]
            and _in_poly(SURVEY['roof.' + p]['poly'], uv[0], uv[1])]
    for p in prefer:
        if p in hits:
            return p
    if hits:                                                     # the one on top
        return max(hits, key=lambda p: on_plane(p, uv)[0][2])
    return prefer[0]


def conduits(geo):
    n_seg = 0
    for eid in ('roof.conduit_1', 'roof.conduit_2'):
        e = SURVEY[eid]
        prefer = [p.replace('roof.', '') for p in e['attrs']['on']]
        for line in [e['polyline']] + e['attrs'].get('branches', []):
            line = np.asarray(line, float)
            pts = []
            for a, b in zip(line[:-1], line[1:]):
                k = max(1, int(np.ceil(np.linalg.norm(b - a) / 12.0)))
                pts += [a + (b - a) * t for t in np.arange(k) / k]
            pts.append(line[-1])
            W = [on_plane(_plane_at(uv, prefer), uv, 0.045)[0] for uv in pts]
            for a, b in zip(W[:-1], W[1:]):
                if 0.02 < np.linalg.norm(b - a) < 3.0:
                    geo.cylinder('conduit', a, b, 0.016, n=5, cap=False)
                    n_seg += 1
    return n_seg


def chimneys(geo):
    info = {}
    for name, c in CHIMNEYS.items():
        x0, y0, x1, y1 = c['cap']
        zt, zs = c['z_top'], c['z_stone']
        ring = plan.aerial_ring([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], zs + 0.1)
        cx, cy = ring.mean(0)
        hx = 0.5 * (np.abs(ring[:, 0] - cx).mean() * 2)
        hy = 0.5 * (np.abs(ring[:, 1] - cy).mean() * 2)
        sx, sy = hx - 0.09, hy - 0.09                             # the stone shaft inside the shroud's drip edge
        zg = float(plan.ground_z(cx, cy)) - 0.3
        geo.box('stone_veneer', (cx - sx, cy - sy, zg), (cx + sx, cy + sy, zs))
        # shroud: a drip band, then a hipped lid with a flat top, the round spark arrestor on it
        geo.box('chimney_shroud', (cx - hx, cy - hy, zs - 0.06), (cx + hx, cy + hy, zs + 0.14))
        z1, z2 = zs + 0.14, zt - 0.22
        k = 0.45
        lo = [(cx - hx, cy - hy), (cx + hx, cy - hy), (cx + hx, cy + hy), (cx - hx, cy + hy)]
        hi = [(cx - hx * k, cy - hy * k), (cx + hx * k, cy - hy * k), (cx + hx * k, cy + hy * k), (cx - hx * k, cy + hy * k)]
        for i in range(4):
            j = (i + 1) % 4
            geo.poly('chimney_shroud', [(*lo[i], z1), (*lo[j], z1), (*hi[j], z2), (*hi[i], z2)])
        geo.poly('chimney_shroud', [(*p, z2) for p in hi])
        r = min(hx, hy) * 0.36
        geo.cylinder('chimney_cap', (cx, cy, z2), (cx, cy, zt - 0.03), r, n=12)
        geo.cylinder('chimney_shroud', (cx, cy, zt - 0.03), (cx, cy, zt), r * 1.25, n=12)
        info[name] = dict(xy=(round(float(cx), 2), round(float(cy), 2)), size=(round(2 * sx, 2), round(2 * sy, 2)),
                          z_top=zt)
    return info


def _edges(kinds):
    """All plane edges of the given kinds: (plane, a, b) with the plane's interior on the LEFT of a -> b."""
    out = []
    for p in ROOF['planes']:
        P = np.asarray(p['poly'], float)
        n = len(P)
        q = np.roll(P, -1, 0)
        ccw = ((P[:, 0] * q[:, 1] - q[:, 0] * P[:, 1]).sum()) > 0
        for i, k in enumerate(p['edges']):
            if k in kinds:
                a, b = P[i], P[(i + 1) % n]
                out.append((p, a, b) if ccw else (p, b, a))
    return out


def gutters(geo):
    """A cream box gutter under every eave edge; downspouts at the ends of the longer runs that reach the ground."""
    runs, spouts = 0, 0
    for p, a, b in _edges(GUTTER_KINDS):
        L = np.linalg.norm((b - a)[:2])
        if L < 0.35:
            continue
        d = (b - a) / np.linalg.norm(b - a)
        a2, b2 = a - d * 0.07, b + d * 0.07                        # close the corners
        geo.prism('gutter_cream', GUTTER, a2, b2)
        runs += 1
    # downspouts: at outer corners where two ground-reaching eaves of one storey meet (one per corner), every other one
    corners = []
    for p, a, b in _edges(('eave',)):
        if np.linalg.norm((b - a)[:2]) < DOWNSPOUT_MIN_RUN:
            continue
        for q, other in ((a, b), (b, a)):
            if all(np.linalg.norm(q - c[0]) > 0.6 for c in corners):
                corners.append((q, other, p['storey']))
    for q, other, storey in corners:
        d = (other - q)[:2]
        d /= np.linalg.norm(d)
        inw = np.array([-d[1], d[0]])
        # the wall stands back from the eave by the overhang: find the inward side by testing the plane's centroid
        cen = np.asarray(PLANES_BY_POINT(q), float)
        if (cen - q[:2]) @ inw < 0:
            inw = -inw
        over = 0.50 if storey == 1 else 0.60
        top = np.array([*(q[:2] + d * 0.45 - inw * 0.06), q[2] - 0.15])
        wall = np.array([*(q[:2] + d * 0.45 + inw * (over - 0.05)), q[2] - 0.15 - over * 0.8])
        zg = float(plan.ground_z(wall[0], wall[1]))
        if wall[2] - zg < 1.0:
            continue
        sec = [(-0.04, -0.03), (0.04, -0.03), (0.04, 0.03), (-0.04, 0.03)]
        geo.prism('gutter_cream', sec, top, wall, up=np.array([inw[0], inw[1], 0.0]) + UP * 0.01)
        geo.box('gutter_cream', (wall[0] - 0.04, wall[1] - 0.04, zg + 0.05), (wall[0] + 0.04, wall[1] + 0.04, wall[2] + 0.03))
        spouts += 1
    return runs, spouts


def PLANES_BY_POINT(q):
    """Plan centroid of the eave-carrying plane with a vertex at q (to tell inward from outward)."""
    best, bd = None, 1e9
    for p in ROOF['planes']:
        P = np.asarray(p['poly'], float)
        d = np.linalg.norm(P - q, axis=1).min()
        if d < bd:
            best, bd = P[:, :2].mean(0), d
    return best


def caps(geo):
    """Ridge and hip caps (one per shared edge) and the flashing band round the flat deck."""
    seen = []
    n = 0
    sec = [(-0.13, -0.035), (0.13, -0.035), (0.045, 0.045), (-0.045, 0.045)]
    for p, a, b in _edges(('ridge', 'hip')):
        if np.linalg.norm(b - a) < 0.3:
            continue
        dup = False
        for s, t in seen:
            if (np.linalg.norm(a - s) < 0.2 and np.linalg.norm(b - t) < 0.2) or \
               (np.linalg.norm(a - t) < 0.2 and np.linalg.norm(b - s) < 0.2):
                dup = True
                break
        if dup:
            continue
        seen.append((a, b))
        geo.prism('ridge_cap', sec, a, b)
        n += 1
    deck = PLANES['deck']
    P = np.asarray(deck['poly'], float)
    band = [(-0.10, -0.03), (0.10, -0.03), (0.10, 0.05), (-0.10, 0.05)]
    for i in range(len(P)):
        a, b = P[i], P[(i + 1) % len(P)]
        if np.linalg.norm(b - a) > 0.2:
            d = (b - a) / np.linalg.norm(b - a)
            geo.prism('ridge_cap', band, a - d * 0.1, b + d * 0.1)
    return n


def build():
    parts, rep = [], {}
    for name, fn in (('solar', solar), ('skylights', skylights), ('roof_vents', vents), ('conduits', conduits),
                     ('chimneys', chimneys), ('gutters', gutters), ('roof_caps', caps)):
        g = Geo()
        rep[name] = fn(g)
        parts.append(Part(name, g, group='house', extras={'zone': 'roof_details'}))
    build.report = rep
    return parts


if __name__ == '__main__':
    ps = build()
    for p in ps:
        print('%-12s %6d tris  %s' % (p.name, p.ntri, build.report[p.name]))
    print('total', sum(p.ntri for p in ps))
