"""Zone 'roof_details' of house 2: everything that sits ON the roofs.

Source: survey/roof.json (aerial p29 pixels) + survey/roof_3d.json (every roof plane z = a X + b Y + c).  An aerial
pixel becomes a world point by meeting its camera ray with the plane the survey names ('on'), lifted by the height of
the thing above the shingles -- so panels, vents and skylights land where the aerial shows them whatever the height.

  * solar arrays a1-a6 = 50 panels (6 + 10 + 19 + 5 + 7 + 3): real 0.798 x 1.559 m modules, square to their roof
    plane, in the survey's counts / rows / orientation and centred on the survey's rectangles; each a framed slab
    5 cm over its plane (test: every module corner has the house's roof 5 cm under it, except a2's east end -- see
    the note at ARRAYS);
  * 2 curb skylights, 23 roof vents by kind (box / pipe / dome / turbine / riser), the 2 PV conduits;
  * 2 stacked-stone chimneys with cream metal shrouds: an OPEN-topped box (drip band, sides leaning in to a thin rim)
    with the round flue cap inside, below the rim (p29 looks straight into them).  Rims = the aerial's top frames at
    the heights tools/epi.py gave in p28: north rim ~5.6 m (it stands from the ground at the north wing's wall and
    ends BELOW the two-storey eave), south ~9.1 m (through the east eave of the south block);
  * the satellite dish on the north porch roof beside the north chimney (p28 only: the chimney's shadow hides it in
    the aerial);
  * gutters on every eave edge (cream K-style box under the roof edge); downspouts [typical positions, no photograph
    resolves them] only where a house wall stands under the eave and no lower roof lies under the drop (walls from the
    house zone's footprints): none at the open porches / patios; shingle caps on ridges and hips (a shade lighter
    than the field), a pale metal flashing band round the flat deck.
"""
import json
import os

import numpy as np

from model import frame, plan
from shapely.geometry import Point, Polygon
from shapely.ops import nearest_points

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
    'ridge_cap': dict(color=(0.36, 0.37, 0.39), roughness=0.85),            # shingle caps, a shade lighter than the field
    'deck_flashing': dict(color=(0.62, 0.63, 0.64), roughness=0.45, metallic=0.5),
    'dish_white': dict(color=(0.80, 0.80, 0.78), roughness=0.5),
    'vent_metal': dict(color=(0.20, 0.20, 0.21), roughness=0.6, metallic=0.4),
    'vent_white': dict(color=(0.82, 0.82, 0.80), roughness=0.5),
    'chimney_shroud': dict(color=(0.66, 0.66, 0.62), roughness=0.5, metallic=0.4),
    'conduit': dict(color=(0.42, 0.43, 0.44), roughness=0.5, metallic=0.6),
}

PANEL_LIFT = 0.05          # panel underside above the shingles
PANEL_T = 0.04
MODULE = (0.798, 1.559)    # m: the SunPower 225 W module (the surveyed rectangles read ~10 % large: blooming)
MODULE_JOINT = 0.02        # m between neighbouring modules
ROW_JOINT = {'a1': 0.09, 'a2': 0.09}   # the two garage-side arrays stand apart on their rails (p29: pale strips)
# survey rectangles (p29 px: x0, y0, x1, y1) -> (n along image x, n along image y) modules: they give each block's
# centre, counts and orientation; the modules themselves are MODULE, square to the roof plane
# a2's east end (2 modules of the north row, 1 of the south row) runs in under the two-storey eave, as p29 / p28 show;
# the house zone's cw_n mesh stops at the aerial's visible edge there, 0.3-1.3 m short of these modules.
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
    # cap = the shroud's top RIM in p29 (the frame round the dark interior), which lies at z_top
    'chimney_n': dict(cap=(715, 291, 741, 320), z_stone=5.05, z_top=5.60),
    'chimney_s': dict(cap=(1037, 1274, 1080, 1306), z_stone=8.30, z_top=9.10),
}
# large skylight: its four outer corners re-read in p29 (the survey's first edge was 14 deg off the shingle courses)
SKYLIGHT_BCN = [(898.7, 1102.0), (918.7, 1086.0), (953.3, 1122.0), (934.7, 1140.7)]
# satellite dish: p28 only (the two-storey eave hides it in the aerial).  Its mount's foot, p28 px (1795, 1273), on
# its ray meets the north porch roof plane ncp_n (roof_3d.json runs it up to the NC wall at y 5.60) 0.45 m from the wall.
DISH = dict(plane='ncp_n', image='photos/p28_7ae0dd.jpg', px=(1795, 1273), mast=0.45, r=0.25, aim=(0.85, 0.15, 0.50))
# (aim: p28 from the NE looks almost square into the disc: a broad ellipse, ~0.47 m across)
WALL_MIN, WALL_MAX = 0.25, 1.00   # m: a downspout needs a wall this far behind the gutter line
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


def _block(pid, O, ex, ey, px, n_img, joint=MODULE_JOINT):
    """A survey rectangle (aerial px corners) as a block of whole modules in the plane frame (s along the eave, t up
    the slope): its surveyed centre and extent, the module counts along s / t and the size it has with real modules."""
    q = on_plane(pid, px, 0.0)
    st = np.c_[(q - O) @ ex, (q - O) @ ey]
    lo, hi = st.min(0), st.max(0)
    u = q[1] - q[0]
    cnt = np.array(n_img if abs(u @ ex) >= abs(u @ ey) else n_img[::-1])
    pitch = (hi - lo) / cnt
    mod = np.array(MODULE if pitch[0] <= pitch[1] else MODULE[::-1])
    return dict(c=(lo + hi) / 2, ext=hi - lo, cnt=cnt, mod=mod, joint=joint, size=cnt * mod + (cnt - 1) * joint)


def _layout(blocks):
    """New centres of an array's blocks: real module sizes, neighbours that abut in the survey abut again (one joint
    apart; edges that were flush stay flush), the whole array centred on the surveyed array."""
    C = [b['c'].copy() for b in blocks]
    for i, bi in enumerate(blocks[1:], 1):
        for j in range(i):
            bj = blocks[j]
            d = bi['c'] - bj['c']
            gap = np.abs(d) - (bi['ext'] + bj['ext']) / 2
            k = int(np.argmax(gap))                              # the axis they are stacked along
            o = 1 - k
            if gap[k] > 0.30 or gap[o] > -0.20:
                continue
            C[i][k] = C[j][k] + np.sign(d[k]) * ((bi['size'][k] + bj['size'][k]) / 2 + MODULE_JOINT)
            lo_i, lo_j = bi['c'][o] - bi['ext'][o] / 2, bj['c'][o] - bj['ext'][o] / 2
            hi_i, hi_j = bi['c'][o] + bi['ext'][o] / 2, bj['c'][o] + bj['ext'][o] / 2
            if abs(lo_i - lo_j) < 0.15:
                C[i][o] = C[j][o] - bj['size'][o] / 2 + bi['size'][o] / 2
            elif abs(hi_i - hi_j) < 0.15:
                C[i][o] = C[j][o] + bj['size'][o] / 2 - bi['size'][o] / 2
            else:
                C[i][o] = C[j][o] + d[o] * (bi['size'][o] + bj['size'][o]) / (bi['ext'][o] + bj['ext'][o])
            break
    box = lambda cs, key: (np.min([c - b[key] / 2 for c, b in zip(cs, blocks)], 0) +          # noqa: E731
                           np.max([c + b[key] / 2 for c, b in zip(cs, blocks)], 0)) / 2
    shift = box([b['c'] for b in blocks], 'ext') - box(C, 'size')
    return [c + shift for c in C]


def solar_modules():
    """Every module: (array id, plane id, its 4 corners on the plane surface, counter-clockwise from above)."""
    out, rails = [], []
    arrays = [(aid, pid, [([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], (nu, nv)) for (x0, y0, x1, y1), nu, nv in rects])
              for aid, (pid, rects) in ARRAYS.items()]
    pid, poly, k = A6
    arrays.append(('a6', pid, [([poly[1], poly[2], poly[3], poly[0]], (k, 1))]))
    for aid, pid, rects in arrays:
        n, ex, ey = plane_frame(pid)
        O = on_plane(pid, rects[0][0][0], 0.0)[0]
        blocks = [_block(pid, O, ex, ey, px, cnt, ROW_JOINT.get(aid, MODULE_JOINT)) for px, cnt in rects]
        for b, c in zip(blocks, _layout(blocks)):
            lo = c - b['size'] / 2
            P = lambda s, t: O + ex * s + ey * t                                               # noqa: E731
            for i in range(b['cnt'][0]):
                for j in range(b['cnt'][1]):
                    s0 = lo[0] + i * (b['mod'][0] + b['joint'])
                    t0 = lo[1] + j * (b['mod'][1] + b['joint'])
                    s1, t1 = s0 + b['mod'][0], t0 + b['mod'][1]
                    out.append((aid, pid, np.array([P(s0, t0), P(s1, t0), P(s1, t1), P(s0, t1)])))
            k = int(np.argmax(b['size']))                         # two rails under each block, along its longer side
            for f in (0.25, 0.75):
                e = [lo.copy(), lo.copy()]
                e[0][1 - k] = e[1][1 - k] = lo[1 - k] + b['size'][1 - k] * f
                e[1][k] += b['size'][k]
                rails.append((pid, P(*e[0]), P(*e[1])))
    return out, rails


def solar(geo):
    count = {}
    mods, rails = solar_modules()
    for aid, pid, q in mods:
        n = plane_frame(pid)[0]
        _slab(geo, q + n * PANEL_LIFT, n, PANEL_T, 'solar_frame', 'solar', inset=0.02)
        count[aid] = count.get(aid, 0) + 1
    for pid, a0, a1 in rails:
        n = plane_frame(pid)[0]
        geo.prism('solar_frame', [(-0.02, -0.025), (0.02, -0.025), (0.02, 0.025), (-0.02, 0.025)],
                  a0 + n * PANEL_LIFT * 0.5, a1 + n * PANEL_LIFT * 0.5, up=n, cap=False)
    return count


def skylights(geo):
    x0, y0, x1, y1 = SURVEY['roof.skylight_bce']['bbox']
    for pid, px in (('bc_n', SKYLIGHT_BCN), ('bc_e', [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])):
        n, ex, ey = plane_frame(pid)
        q = on_plane(pid, px, 0.0)
        # a rectangle square to the plane (along the courses / up the slope) about the surveyed centre, its long and
        # short sides the surveyed quad's mean edge lengths
        c = q.mean(0)
        l1 = 0.5 * (np.linalg.norm(q[1] - q[0]) + np.linalg.norm(q[2] - q[3]))
        l2 = 0.5 * (np.linalg.norm(q[2] - q[1]) + np.linalg.norm(q[3] - q[0]))
        d_long = (q[1] - q[0]) if l1 >= l2 else (q[2] - q[1])
        e_u, e_v = (ex, ey) if abs(d_long @ ex) >= abs(d_long @ ey) else (ey, ex)
        hu, hv = 0.5 * max(l1, l2), 0.5 * min(l1, l2)
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
            geo.obox('vent_metal', p, ex, ey, n, (-0.15, -0.15, -0.01), (0.15, 0.15, 0.02))       # ~0.30 m square in p29
            geo.obox('vent_metal', p, ex, ey, n, (-0.11, -0.10, 0.02), (0.11, 0.11, 0.12))
        elif k == 'tall':                                        # the capped flue beside the ridge (p28: ~0.9 m mast)
            geo.obox('vent_metal', p, ex, ey, n, (-0.20, -0.20, -0.01), (0.20, 0.20, 0.015))
            geo.cylinder('vent_metal', p - UP * 0.05, p + UP * 0.80, 0.075, n=10)
            geo.cylinder('vent_metal', p + UP * 0.80, p + UP * 0.84, 0.11, n=10)
            geo.cylinder('vent_metal', p + UP * 0.84, p + UP * 0.93, 0.095, n=10)
            geo.cylinder('vent_metal', p + UP * 0.93, p + UP * 0.96, 0.13, n=10)
        elif k in ('pipe', 'pipe_white'):
            L = 0.36
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


def _ring(cx, cy, hx, hy, z):
    return [np.array([cx - hx, cy - hy, z]), np.array([cx + hx, cy - hy, z]), np.array([cx + hx, cy + hy, z]),
            np.array([cx - hx, cy + hy, z])]


def chimneys(geo):
    info = {}
    for name, c in CHIMNEYS.items():
        x0, y0, x1, y1 = c['cap']
        zt, zs = c['z_top'], c['z_stone']
        ring = plan.aerial_ring([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], zt)       # the rim, at its own height
        cx, cy = ring.mean(0)
        hx = float(np.abs(ring[:, 0] - cx).mean())
        hy = float(np.abs(ring[:, 1] - cy).mean())
        sx, sy = hx + 0.02, hy + 0.02                              # stone shaft: about the rim's size (p28)
        zg = float(plan.ground_z(cx, cy)) - 0.3
        geo.box('stone_veneer', (cx - sx, cy - sy, zg), (cx + sx, cy + sy, zs))
        # shroud: a drip band wider than the stone, sides leaning in to a thin rim, OPEN on top: a recessed deck with
        # the round flue cap inside, its top below the rim
        bx, by = sx + 0.07, sy + 0.07
        z1 = zs + 0.12
        geo.box('chimney_shroud', (cx - bx, cy - by, zs - 0.07), (cx + bx, cy + by, z1), faces='xXyYz')
        lo, hi = _ring(cx, cy, bx, by, z1), _ring(cx, cy, hx, hy, zt)
        t = 0.03
        zd = zs + 0.20
        inn, deck = _ring(cx, cy, hx - t, hy - t, zt), _ring(cx, cy, hx - t, hy - t, zd)
        for i in range(4):
            j = (i + 1) % 4
            geo.poly('chimney_shroud', [lo[i], lo[j], hi[j], hi[i]])                 # outer wall
            geo.poly('chimney_shroud', [hi[i], hi[j], inn[j], inn[i]])               # rim
            geo.poly('chimney_shroud', [inn[i], inn[j], deck[j], deck[i]])           # inner wall
        geo.poly('chimney_cap', deck)
        r = min(hx, hy) * 0.50
        geo.cylinder('vent_metal', (cx, cy, zd), (cx, cy, zt - 0.22), r * 0.7, n=12)
        geo.cylinder('vent_white', (cx, cy, zt - 0.22), (cx, cy, zt - 0.10), r, n=14)
        info[name] = dict(xy=(round(float(cx), 2), round(float(cy), 2)), size=(round(2 * sx, 2), round(2 * sy, 2)),
                          z_top=zt)
    info['dish'] = dish(geo)
    return info


def dish(geo):
    """The satellite dish on the north porch roof (p28): a mast, an arm, a shallow white disc aimed up to the south."""
    a, b, c = PLANES[DISH['plane']]['plane']
    o, d = CAMS.ray(frame.world_cams()[DISH['image']], [DISH['px']])
    d = d[0]
    foot = o + (a * o[0] + b * o[1] + c - o[2]) / (d[2] - a * d[0] - b * d[1]) * d
    top = foot + UP * DISH['mast']
    aim = np.asarray(DISH['aim'], float)
    aim /= np.linalg.norm(aim)
    geo.obox('vent_metal', foot, (1, 0, 0), (0, 1, 0), UP, (-0.10, -0.10, -0.02), (0.10, 0.10, 0.03))
    geo.cylinder('vent_metal', foot - UP * 0.05, top, 0.025, n=6)
    ctr = top + aim * 0.10
    geo.cylinder('dish_white', ctr - aim * 0.03, ctr + aim * 0.02, DISH['r'], n=16)
    arm = ctr + aim * 0.42 - UP * 0.22
    geo.cylinder('vent_metal', ctr - UP * DISH['r'] * 0.9, arm, 0.012, n=5, cap=False)
    geo.obox('dish_white', arm, (1, 0, 0), (0, 1, 0), UP, (-0.04, -0.04, -0.04), (0.04, 0.04, 0.06))
    return tuple(float(v) for v in np.round(foot, 2))


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
    for p, a, b in _edges(GUTTER_KINDS) + _entry_eaves():
        if p['id'] == 'swp':                                       # the house builds the entry gable over this leg
            continue
        if p['id'] == 'g_s':                                       # built without its notch: one straight eave
            P = np.asarray(p['poly'], float)
            e = (P[0] - P[2]) / np.linalg.norm(P[0] - P[2])
            a, b = P[2] + e * ((a - P[2]) @ e), P[2] + e * ((b - P[2]) @ e)
        L = np.linalg.norm((b - a)[:2])
        if L < 0.35:
            continue
        d = (b - a) / np.linalg.norm(b - a)
        a2, b2 = a - d * 0.07, b + d * 0.07                        # close the corners
        geo.prism('gutter_cream', GUTTER, a2, b2)
        runs += 1
    # downspouts: at the ends of ground-reaching eave runs, but only where a house wall stands under the eave and no
    # other roof lies under the drop
    walls = _walls()
    if walls is None:
        return runs, 0
    lower = [(Polygon(np.asarray(p['poly'])[:, :2]).buffer(0.9, join_style=2), p) for p in ROOF['planes']]
    corners = []
    for p, a, b in _edges(('eave',)):
        if np.linalg.norm((b - a)[:2]) < DOWNSPOUT_MIN_RUN:
            continue
        for q, other in ((a, b), (b, a)):
            if all(np.linalg.norm(q - c[0]) > 0.6 for c in corners):
                corners.append((q, other, p))
    sec = [(-0.04, -0.03), (0.04, -0.03), (0.04, 0.03), (-0.04, 0.03)]
    placed = []
    for q, other, p in corners:
        d = (other - q)[:2]
        d /= np.linalg.norm(d)
        W = walls[p['storey']]
        for s_along in (0.90, 1.5, 2.2, 3.0):                        # step along the run until a wall lies behind it
            g = q[:2] + d * s_along
            w = np.array(nearest_points(W.boundary, Point(g))[0].coords[0])
            dist = float(np.linalg.norm(w - g))
            if WALL_MIN < dist < WALL_MAX and not W.contains(Point(g)):
                inw = (w - g) / dist                               # ... and the wall runs on to both sides (no corner)
                if all(W.contains(Point(w + inw * 0.12 + d * k)) for k in (-0.25, 0.25)) and \
                        all(np.linalg.norm(w - o[:2]) > o[2] / 2 + 0.30 for o in walls['openings']):
                    break
        else:
            continue
        out = (g - w) / dist
        if abs(out @ d) > 0.5:                                     # the nearest wall is round a corner, not behind
            continue
        pipe = w + out * 0.05
        if any(np.linalg.norm(pipe - o) < 2.5 for o in placed):   # one per corner
            continue
        # the ground-floor wall must run on under an upper one, and no other roof may lie under the drop
        if p['storey'] == 2 and walls[1].boundary.distance(Point(w)) > 0.15:
            continue
        ztop = q[2] - 0.15 - dist * 0.8
        if any(pp is not p and poly.contains(Point(pipe))
               and pp['plane'][0] * pipe[0] + pp['plane'][1] * pipe[1] + pp['plane'][2] < ztop - 0.2 for poly, pp in lower):
            continue
        zg = float(plan.ground_z(pipe[0], pipe[1]))
        if ztop - zg < 1.0:
            continue
        top = np.array([g[0], g[1], q[2] - 0.15])
        geo.prism('gutter_cream', sec, top, np.array([pipe[0], pipe[1], ztop]), up=np.array([out[0], out[1], 0.0]) + UP * 0.01)
        geo.box('gutter_cream', (pipe[0] - 0.04, pipe[1] - 0.04, zg + 0.05), (pipe[0] + 0.04, pipe[1] + 0.04, ztop + 0.03))
        placed.append(pipe)
        spouts += 1
    gutters.spouts = placed
    return runs, spouts


def _entry_eaves():
    """The two eaves of the house zone's entry gable (it replaces plane swp), interior on the left of a -> b."""
    try:
        from model.zones import house
        M, t, n, half, eave = house.entry_frame()
    except Exception as e:
        print('roof_details: entry gable unavailable (%s)' % e)
        return []
    E = lambda q: np.array([q[0], q[1], eave])                      # noqa: E731
    out = []
    for sgn in (1, -1):
        a, b = E(M + t * sgn * half), E(M + n * 3.1 + t * sgn * half)
        out.append(({'id': 'entry_gable'}, a, b) if sgn > 0 else ({'id': 'entry_gable'}, b, a))
    return out


def _walls():
    """Closed wall outlines per storey (plan polygons) from the house zone's footprints: {1: ground, 2: upper},
    and its openings (a pipe never crosses a window or door)."""
    try:
        from model.zones import house
        fp = house.footprints(house._planes())
        ops = [np.array([o[2][0], o[2][1], o[4]]) for o in house.OPENINGS]       # (x, y, width) of every opening
        return {1: fp['G'], 2: fp['U'], 'openings': ops}
    except Exception as e:                                         # no walls known: no downspouts
        print('roof_details: house footprints unavailable (%s): no downspouts' % e)
        return None


def caps(geo):
    """Ridge and hip caps (one per shared edge) and the flashing band round the flat deck."""
    seen = []
    n = 0
    sec = [(-0.10, -0.03), (0.10, -0.03), (0.04, 0.03), (-0.04, 0.03)]
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
            geo.prism('deck_flashing', band, a - d * 0.1, b + d * 0.1)
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
