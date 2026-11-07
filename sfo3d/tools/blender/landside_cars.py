"""Parked cars on the landside parking decks (data/buildings3d/landside.glb): placement on the stall grid of each deck at the
NAIP-measured density and orientation (tools/buildings/landside_naip_measurements.json roof_cars; the central garage uses
the visual estimate of spec cg_roof_cars), and two low-poly car shapes. Pure numpy / shapely; build_landside.py exports each
(deck, shape, colour) group as one glTF node with EXT_mesh_gpu_instancing.

Orientation: the measured 'car_row_axis_heading_deg' is the long axis of the detected car blobs (0.5-m blur: single cars
dominate, see landside_naip_measure.py) -> the car axis. 90-degree stalls on 18.6-m modules (landside_geom.car_layout)
except the Rental Car Center (nose-to-tail ready-return lanes [obs NAIP]). Which stalls are taken is random (seeded):
NAIP gives counts and axes, not positions [inf] - except the central garage (round 1): its dark / coloured cars stand at their
NAIP 2024 blob positions (landside_r1_obs.json cg_roof.cars [obs]; blob colours un-mixed against the deck, deck['unmix']), white / silver ones are added next to them by fleet share. Colours: US fleet shares, white 25 / black 22 / grey 19 / silver 12 /
blue 10 / red 9 / other 3 % (industry surveys) [inf]; shapes 45 % sedan / 40 % SUV / 15 % pickup [inf] (close-out r3, buildings-9:
a third shape, the pickup with its open bed; and at LOD0 four wheels under the dark skirt - review r1 finding 4: 'boxes without
wheels, two shapes').
"""
import math

import numpy as np
import shapely
from shapely.geometry import Point
from shapely.ops import unary_union

from landside_mesh import MB

COLOURS = [('white', (226, 228, 228), 0.25), ('black', (22, 23, 25), 0.22), ('grey', (96, 99, 103), 0.19),
           ('silver', (168, 172, 176), 0.12), ('blue', (34, 58, 104), 0.10), ('red', (132, 22, 24), 0.09), ('beige', (156, 140, 112), 0.03)]
SHAPES = [('sedan', 4.75, 1.84, 1.45, 0.45), ('suv', 4.85, 1.95, 1.75, 0.40), ('pickup', 5.50, 1.95, 1.85, 0.15)]   # name, length,
#   width, height, share [inf]; widths <= 1.95 m (verify_landside: stall spacing 2.1 m); pickup = a mid / full-size crew cab average
WHEEL = {'sedan': (0.33, 0.95), 'suv': (0.37, 0.98), 'pickup': (0.40, 1.05)}   # tyre radius, axle inset from the bumper [inf]
WHEEL_W = 0.24                                                                  # tyre width [inf]


def car_mesh(shape, lod=0):
    """low-poly car centred on its footprint, +X forward, ground at z = 0. Materials: 'paint', 'car_glass', 'car_dark'."""
    nm, L, W, H, _ = shape
    mb = MB(nm)
    # body bottom (LOD0: the dark skirt + wheels below it), shoulder line. LOD1 has no skirt / wheels: its body starts at the deck
    # (close-out r3 fix 2, verifier v3: the LOD1 cars floated 0.3 m above the deck at 450-1,500 m) [inf]
    zb, zs = (0.30 if lod == 0 else 0.0), 0.55 * H + 0.15
    hl, hw = L / 2, W / 2
    # lower body: an 8-sided prism in plan (chamfered corners), from zb to zs
    ch = 0.35
    plan = [(hl, -hw + ch), (hl, hw - ch), (hl - ch, hw), (-hl + ch, hw), (-hl, hw - ch), (-hl, -hw + ch), (-hl + ch, -hw), (hl - ch, -hw)]
    plan = plan[::-1] if _area(plan) < 0 else plan
    n = len(plan)
    for i in range(n):
        a, b = plan[i], plan[(i + 1) % n]
        mb.quad_wall(a, b, zb, zs, zb, zs, 'paint', 0, (1, 1))
        if lod == 0:
            mb.quad_wall((a[0] * 0.97, a[1] * 0.97), (b[0] * 0.97, b[1] * 0.97), 0.0, zb, 0.0, zb, 'car_dark', 0, (1, 1))
    # cabin (glass house): a frustum from the shoulder to the roof, roof shorter and narrower; bonnet / boot caps
    fx0, fx1 = {'sedan': (-1.25, 1.05), 'suv': (-2.0, 1.25), 'pickup': (-0.75, 1.20)}[nm]   # cabin footprint along x at the shoulder
    rx0, rx1 = (fx0 + 0.45, fx1 - 0.65) if nm == 'sedan' else (fx0 + 0.15, fx1 - 0.45)
    sw, rw = hw - 0.08, hw - 0.22
    lo = [(fx1, -sw), (fx1, sw), (fx0, sw), (fx0, -sw)]
    hi = [(rx1, -rw), (rx1, rw), (rx0, rw), (rx0, -rw)]
    for i in range(4):
        a0, b0 = lo[i], lo[(i + 1) % 4]; a1, b1 = hi[i], hi[(i + 1) % 4]
        mb.face([(a0[0], a0[1], zs), (b0[0], b0[1], zs), (b1[0], b1[1], H), (a1[0], a1[1], H)][::-1], 'car_glass', [(0, 0), (1, 0), (1, 1), (0, 1)])
    mb.face([(p[0], p[1], H) for p in hi[::-1]], 'paint', [(0, 0), (1, 0), (1, 1), (0, 1)])
    # top of the lower body outside the cabin (bonnet + boot): fan from the plan ring minus the cabin
    import shapely.geometry as sg
    from landside_mesh import cap
    deck = sg.Polygon(plan).difference(sg.Polygon(lo).buffer(0.0))
    if nm == 'pickup':
        # the open bed behind the cab: a dark bed liner 0.45 m below the rails (rails = the shoulder line), bonnet in paint
        bed = deck.intersection(sg.box(-hl - 1, -hw - 1, fx0 - 0.08, hw + 1)).buffer(-0.12, join_style=2)
        cap(mb, deck.difference(bed), zs, 'paint', 1.0)
        if not bed.is_empty:
            cap(mb, bed, zs - 0.45, 'car_dark', 1.0)
            br = list(bed.exterior.coords)[:-1]
            if _area(br) < 0: br = br[::-1]
            for i in range(len(br)):                        # bed walls, facing into the bed (inward of the ring)
                a, b = br[i], br[(i + 1) % len(br)]
                mb.quad_wall(b, a, zs - 0.45, zs, zs - 0.45, zs, 'paint', 0, (1, 1))
    else:
        cap(mb, deck, zs, 'paint', 1.0)
    # the car is convex in section: every face must point away from the body centre (single-sided materials)
    c = np.array([0.0, 0.0, 0.5 * H])
    for i, f in enumerate(mb.F):
        P = np.array([mb.V[k] for k in f])
        n = np.zeros(3)
        for a in range(len(P)):
            n += np.cross(P[a], P[(a + 1) % len(P)])
        inner_bed = nm == 'pickup' and P[:, 2].min() >= zs - 0.46 and P[:, 2].max() <= zs + 1e-6 and P[:, 0].max() < fx0 + 1e-6
        if inner_bed: continue                              # the bed walls / liner face into the bed (built that way)
        if float(n @ (P.mean(0) - c)) < 0:
            mb.F[i] = f[::-1]; mb.UV[i] = mb.UV[i][::-1]
    if lod == 0:
        # close-out r3 (buildings-9): the wheels - one 6-sided axle prism per axle spanning the track (ends 0.03 m inside the body
        # side), so only the tyres show: their faces outside the skirt (inset 3 %) and below the body bottom; 40 triangles per car
        # (1,737 instances: ~70k instanced triangles at LOD0, none at LOD1 / LOD2); built after the convex fix-up, wound outwards
        r, inset = WHEEL[nm]
        for ax in (hl - inset, -hl + inset):
            _wheel(mb, ax, 0.0, r, 2.0 * (hw - 0.03), n=6)
    return mb


def _wheel(mb, x0, y0, r, w, n=8):
    """tyre: an n-sided prism around the y axis at (x0, y0, r): tread quads + two side caps, all facing outwards."""
    ang = [2 * math.pi * (k + 0.5) / n for k in range(n)]
    ring = [(x0 + r * math.cos(a), r + r * math.sin(a)) for a in ang]       # (x, z) around the axle
    ya, yb = y0 - w / 2, y0 + w / 2
    c = np.array([x0, y0, r])
    def add(pts, uv):
        P = np.array(pts); nn = np.zeros(3)
        for a in range(len(P)): nn += np.cross(P[a], P[(a + 1) % len(P)])
        if float(nn @ (P.mean(0) - c)) < 0: pts = pts[::-1]; uv = uv[::-1]
        mb.face(pts, 'car_dark', uv)
    for k in range(n):
        (xa, za), (xb, zb) = ring[k], ring[(k + 1) % n]
        add([(xa, ya, za), (xb, ya, zb), (xb, yb, zb), (xa, yb, za)], [(0, 0), (1, 0), (1, 1), (0, 1)])
    for yy in (ya, yb):
        add([(x, yy, z) for x, z in ring], [(0.5 + 0.5 * math.cos(a), 0.5 + 0.5 * math.sin(a)) for a in ang])


def _area(r):
    return 0.5 * sum(r[i][0] * r[(i + 1) % len(r)][1] - r[(i + 1) % len(r)][0] * r[i][1] for i in range(len(r)))


def nearest_colour(rgb):
    """index of the fleet colour nearest to a NAIP blob colour (sRGB)."""
    c = np.asarray(rgb, float)
    return int(np.argmin([np.sum((np.asarray(col, float) - c) ** 2) for _, col, _ in COLOURS]))


def place_positions(deck, F, layout_fn, seed=0):
    """cars at observed positions (deck['positions']: local (x, y, yaw, rgb) from NAIP) + extra_share x n cars (colours not
    separable on the light deck: white / silver) on free stall slots within 8 m of the observed ones [inf]."""
    P = deck['poly']; inner = P.buffer(-0.4)
    excl = unary_union(deck.get('exclude') or []) if deck.get('exclude') else None
    rng = np.random.default_rng(seed)
    sw = np.array([s[4] for s in SHAPES]); sw = sw / sw.sum()
    cars, pts = [], []

    def free(x, y, r=2.35):
        return all((x - qx) ** 2 + (y - qy) ** 2 >= r * r for qx, qy in pts)
    dropped = 0
    um = None
    if deck.get('unmix'):
        # un-mix each blob against the deck (car share alpha), then remove the common blue cast of dark roofs / glass under the
        # sky (median blue excess over all blobs) before choosing the nearest fleet colour [inf]
        dk, al = np.asarray(deck['unmix'][0], float), deck['unmix'][1]
        um = np.clip(dk + (np.array([p_[3] for p_ in deck['positions']], float) - dk) / al, 0, 255)
        um[:, 2] = np.clip(um[:, 2] - float(np.median(np.maximum(um[:, 2] - um[:, :2].max(1), 0.0))), 0, 255)
    # review r2 (finding 4): snap each observed car to the nearest free stall of the deck layout (position and orientation of
    # the stall; the per-blob NAIP heading is noise at 0.5 m/px) within deck['snap'] m; the NAIP position / colour are kept as the
    # choice of stall / paint [obs]; a car with no stall within reach keeps its position with the yaw snapped to the stall axis
    snap = deck.get('snap')
    slots0 = layout_fn(P, deck['axis'], np.array(F.L(*deck['origin'])), False) if snap else []
    S0 = np.array([[s_[0], s_[1]] for s_ in slots0]) if slots0 else np.zeros((0, 2))
    used = set(); n_snapped = 0
    ax_yaw = math.atan2(*(np.array([math.sin(math.radians(deck['axis'])), math.cos(math.radians(deck['axis']))]))[::-1]) if snap else 0.0
    for ip, (x, y, yaw, rgb) in enumerate(deck['positions']):
        if snap and len(S0):
            dd = np.hypot(S0[:, 0] - x, S0[:, 1] - y)
            hit = False
            for j in np.argsort(dd)[:8]:
                if dd[j] > snap: break
                if j in used: continue
                sx, sy = float(S0[j, 0]), float(S0[j, 1])
                if not free(sx, sy) or (excl is not None and excl.intersects(Point(sx, sy).buffer(1.2))): continue
                x, y, yaw = sx, sy, slots0[j][2] + (math.pi if rng.random() < 0.15 else 0.0)    # ~15 % backed in [inf]
                used.add(int(j)); n_snapped += 1; hit = True
                break
            if not hit:
                yaw = ax_yaw + round((yaw - ax_yaw) / (math.pi / 2)) * (math.pi / 2)
        ok = inner.contains(Point(x, y)) and (excl is None or not excl.intersects(Point(x, y).buffer(1.2))) and free(x, y)
        if not ok:
            dropped += 1; continue
        pts.append((x, y))
        if um is not None:
            rgb = um[ip]
        cars.append((x, y, deck['z'] + 0.01, yaw, int(rng.choice(len(SHAPES), p=sw)), nearest_colour(rgb)))
    n_obs = len(cars)
    n_extra = int(round(deck.get('extra_share', 0.0) * n_obs))
    slots = layout_fn(P, deck['axis'], np.array(F.L(*deck['origin'])), False)
    if slots and n_extra:
        S = np.array([[s_[0], s_[1]] for s_ in slots]); O = np.array(pts) if pts else np.zeros((0, 2))
        from scipy.spatial import cKDTree
        dmin = cKDTree(O).query(S)[0] if len(O) else np.full(len(S), 1e9)
        cand = [i for i in np.argsort(dmin) if 2.4 < dmin[i] < 8.0]
        rng.shuffle(cand)
        wi = [i for i, c in enumerate(COLOURS) if c[0] in ('white', 'silver')]
        ww = np.array([COLOURS[i][2] for i in wi]); ww /= ww.sum()
        for i in cand:
            if n_extra <= 0: break
            x, y, yaw = slots[i][0], slots[i][1], slots[i][2]
            if excl is not None and excl.intersects(Point(x, y).buffer(1.2)): continue
            if not free(x, y): continue
            pts.append((x, y)); n_extra -= 1
            cars.append((x, y, deck['z'] + 0.01, yaw + math.radians(rng.normal(0, 1.5)), int(rng.choice(len(SHAPES), p=sw)), int(wi[rng.choice(len(wi), p=ww)])))
    area = P.area
    info = dict(deck_area_m2=round(area, 1), slots=len(slots), cars=len(cars), observed=n_obs, observed_dropped=dropped, added_light=len(cars) - n_obs,
                snapped=n_snapped, snap_m=snap,
                density_per_1000m2=round(1000 * len(cars) / area, 2) if area else 0, axis_deg=deck['axis'], lanes=False,
                count_src=deck.get('count_src'), axis_src=deck.get('axis_src'))
    return cars, info


def car_footprint(x, y, yaw, si, pad=0.0):
    """plan footprint (local XY) of a car instance: its shape's length x width box (the LOD0 mesh's chamfered plan and wheels
    lie inside it), rotated by yaw about the up axis (build_landside: rotation_euler z = yaw, +X forward), grown by pad."""
    from shapely.geometry import Polygon
    _, L, W, _, _ = SHAPES[si]
    c, s = math.cos(yaw), math.sin(yaw); hl, hw = L / 2 + pad, W / 2 + pad
    return Polygon([(x + c * u - s * v, y + s * u + c * v) for u, v in ((-hl, -hw), (hl, -hw), (hl, hw), (-hl, hw))])


SHORTER = {2: (1, 0), 1: (0,), 0: ()}      # pickup -> SUV -> sedan; SUV -> sedan (shape indices of SHAPES, by length)


def resolve_overlaps(cars, prior=(), gap=0.05, dz=1.5):
    """close-out r3 fix 2 (verifier v3: 16 overlapping pairs, worst 2.44 m2; the placement only kept centres >= 2.35 m apart, so
    cars could overlap end to end or at an angle, and a 5.5-m pickup did not fit a stall shorter than 5.5 m head to head): every
    car's oriented footprint (car_footprint, + gap / 2 each side) is tested against the cars accepted before it (in order: the
    NAIP-observed cars first, as placed) and against `prior` (other decks of the building) at the same level (+- dz); a car that
    overlaps takes the next shorter shape that fits (pickup -> SUV -> sedan), else it is dropped [inf: which car gives way].
    -> (cars, dict(dropped, reshaped))."""
    from shapely.strtree import STRtree
    acc_fp, acc_z = [], []
    for c in prior:
        acc_fp.append(car_footprint(c[0], c[1], c[3], c[4], gap / 2)); acc_z.append(c[2])
    out, dropped, reshaped = [], 0, 0
    for c in cars:
        x, y, z, yaw, si, ci = c
        tree = STRtree(acc_fp) if acc_fp else None
        ok_si = None
        for cand in (si,) + SHORTER[si]:
            g = car_footprint(x, y, yaw, cand, gap / 2)
            hit = False
            if tree is not None:
                for k in tree.query(g):
                    if abs(acc_z[int(k)] - z) < dz and acc_fp[int(k)].intersects(g) and acc_fp[int(k)].intersection(g).area > 1e-6:
                        hit = True; break
            if not hit: ok_si = cand; break
        if ok_si is None:
            dropped += 1; continue
        if ok_si != si: reshaped += 1
        out.append((x, y, z, yaw, ok_si, ci))
        acc_fp.append(car_footprint(x, y, yaw, ok_si, gap / 2)); acc_z.append(z)
    return out, dict(dropped=dropped, reshaped=reshaped)


def place(deck, F, layout_fn, seed=0, prior=()):
    """cars on one deck: deck = dict(poly (local), z, axis, origin (world), density | count | positions, lanes, exclude [local])
    -> (cars [(x, y, z, yaw, shape, colour)], info); oriented-footprint overlaps resolved against each other and `prior` (the
    building's other decks) by resolve_overlaps (close-out r3 fix 2)."""
    cars, info = _place(deck, F, layout_fn, seed)
    cars, ov = resolve_overlaps(cars, prior)
    info.update(cars=len(cars), overlap_dropped=ov['dropped'], overlap_reshaped=ov['reshaped'])
    return cars, info


def _place(deck, F, layout_fn, seed=0):
    if deck.get('positions'):
        return place_positions(deck, F, layout_fn, seed)
    P = deck['poly']
    excl = unary_union(deck.get('exclude') or []) if deck.get('exclude') else None
    o = np.array(F.L(*deck['origin']))
    lanes = bool(deck.get('lanes'))
    slots = layout_fn(P, deck['axis'], o, lanes)
    if excl is not None and not excl.is_empty and slots:
        keep = ~shapely.intersects(excl, shapely.buffer(shapely.points(np.array([[s[0], s[1]] for s in slots])), 2.4))
        slots = [s for s, k in zip(slots, keep) if k]
    area = P.area
    n = int(round(deck['count'])) if deck.get('count') else int(round(deck['density'] * area / 1000.0))
    n = min(n, len(slots))
    rng = np.random.default_rng(seed)
    if lanes:
        # rental lanes: whole lanes filled nose-to-tail (lane index j, position k)
        by = {}
        for s in slots: by.setdefault(s[3], []).append(s)
        order = rng.permutation(sorted(by))
        chosen = []
        for j in order:
            row = sorted(by[j], key=lambda s: s[4])
            take = row[:max(0, n - len(chosen))]
            chosen += take
            if len(chosen) >= n: break
    else:
        idx = rng.choice(len(slots), size=n, replace=False) if n else []
        chosen = [slots[i] for i in idx]
    cw = np.array([c[2] for c in COLOURS]); cw = cw / cw.sum()
    sw = np.array([s[4] for s in SHAPES]); sw = sw / sw.sum()
    cars = []
    for s in chosen:
        x, y, yaw = s[0], s[1], s[2]
        yaw += math.radians(rng.normal(0, 1.5))
        x += float(np.clip(rng.normal(0, 0.06), -0.12, 0.12)); y += float(np.clip(rng.normal(0, 0.06), -0.12, 0.12))
        cars.append((x, y, deck['z'] + 0.01, yaw, int(rng.choice(len(SHAPES), p=sw)), int(rng.choice(len(COLOURS), p=cw))))
    info = dict(deck_area_m2=round(area, 1), slots=len(slots), cars=len(cars), target=n,
                density_per_1000m2=round(1000 * len(cars) / area, 2) if area else 0, axis_deg=deck['axis'], lanes=lanes,
                count_src=deck.get('count_src'), axis_src=deck.get('axis_src'))
    return cars, info
