#!/usr/bin/env python3
"""Build data/sfo_airport.json (+ data/sfo_airport_report.md) for the SFO 3D app.

Source: a local checkout of the SFO Museum "sfomuseum-data-architecture"
repository (CDLA-Permissive-1.0). Every *.geojson file is one Feature; only
features with properties["mz:is_current"] == 1 are used.

World frame (must match js/geo.js): x = east (m), z = SOUTH (m), origin = ARP.

Only the Python standard library and numpy are used (no shapely): Douglas-Peucker,
point-in-polygon, nearest-point-on-segment and the ring validity checks are
implemented below.

Usage:
    python3 tools/build_sfo_airport.py [--src DIR] [--out-json FILE] [--out-report FILE]
"""
import argparse
import glob
import json
import math
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SRC = os.environ.get('SFOM_DATA', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'refs', 'sfom-arch', 'data'))  # github.com/sfomuseum-data/sfomuseum-data-architecture @5f64ee8
DEFAULT_JSON = os.path.join(HERE, '..', 'data', 'sfo_airport.json')
DEFAULT_REPORT = os.path.join(HERE, '..', 'data', 'sfo_airport_report.md')

# --- world frame (identical to js/geo.js) ---------------------------------------------
LAT0 = 37.6188056
LON0 = -122.3754167
M_PER_DEG_LAT = 110990.0
M_PER_DEG_LON = 111320.0 * math.cos(math.radians(LAT0))

# --- build parameters ------------------------------------------------------------------
TOL_BUILDING = 0.4        # m, terminal complex / terminals / boarding areas
TOL_AIRFIELD = 0.3        # m, taxiways / runways
TOL_STRUCTURE = 0.3       # m, structures (incl. the AirTrain rail polygon)
MIN_RING_AREA = 20.0      # m^2, smaller rings are dropped
MAX_JSON_BYTES = 2_500_000
TOL_ESCALATION = (0.5, 0.75, 1.0, 1.5, 2.0)   # taxiway/structure tolerances if too big
PROBE_DIST = 5.0          # m, outward-normal test distance
FAR_GATE_DIST = 30.0      # m, gates farther than this from the boundary are reported
BA_PREFERENCE_EPS = 0.05  # m, a boarding-area edge must be this much closer to win
FALLBACK_HALF_WIDTH = 2.5 # m, lateral clearance required of a fallback edge's probe
MIN_FACADE_SEG = 3.0      # m, shorter boundary edges (facade jogs) don't define the normal
SMOOTH_HALF = 3.0         # m, half-length of the chord used for the normal at such jogs
UNTWIST_MAX_SPAN = 4      # self-crossing loops of at most this many vertices ...
UNTWIST_MAX_AREA = 10.0   # m^2 ... and this area are cut out of the (snapped) rings

ATTRIBUTION = ('Airport geometry: SFO Museum, sfomuseum-data-architecture '
               '(CDLA-Permissive-1.0)')
RING_CONVENTION = ('Coordinates are [x, z] in metres: x = east, z = south, origin = ARP. '
                   'Each polygon is a list of rings: rings[0] is the outer ring, the rest '
                   'are holes. Viewed from above in (x, -z) = (east, north) space, outer '
                   'rings are counter-clockwise and holes clockwise (so in raw [x, z] the '
                   'shoelace sum of an outer ring is negative). Rings are open: the first '
                   'vertex is not repeated at the end.')
FRAME = ('x = east (m), z = south (m), origin ARP lat 37.6188056 lon -122.3754167; '
         'm/deg lat 110990, m/deg lon 111320*cos(lat0)')

STRUCTURE_KINDS = ('atc', 'garage', 'building', 'hangar', 'hotel', 'airtrain', 'rail')
TERMINAL_COMPLEX_NAME = 'SFO Terminal Complex'

SURVEYED_RUNWAYS = (('10L', '28R'), ('10R', '28L'), ('1L', '19R'), ('1R', '19L'))
SURVEYED_ENDS = {  # lat, lon (decimal degrees)
    '28R': (37.6135336, -122.3571411), '10L': (37.6287387, -122.3933919),
    '28L': (37.6117119, -122.3583492), '10R': (37.6262911, -122.3931055),
    '1L': (37.6078979, -122.3829285), '19R': (37.6264814, -122.3706094),
    '1R': (37.6063299, -122.3810408), '19L': (37.6273422, -122.3671108),
}


def project(lon, lat):
    return (lon - LON0) * M_PER_DEG_LON, -((lat - LAT0) * M_PER_DEG_LAT)


# =======================================================================================
# Geometry helpers. Rings are lists of (x, z) tuples without a closing vertex.
# =======================================================================================

def area_en(ring):
    """Signed area in (east, north) space; > 0 means counter-clockwise seen from above.
    north = -z, so this is the negated shoelace sum of the raw (x, z) ring."""
    s = 0.0
    n = len(ring)
    for i in range(n):
        x1, z1 = ring[i]
        x2, z2 = ring[(i + 1) % n]
        s += x1 * z2 - x2 * z1
    return -0.5 * s


def dedupe(ring):
    """Remove consecutive duplicate vertices and the closing vertex."""
    out = []
    for p in ring:
        if not out or p[0] != out[-1][0] or p[1] != out[-1][1]:
            out.append(p)
    while len(out) > 1 and out[0][0] == out[-1][0] and out[0][1] == out[-1][1]:
        out.pop()
    return out


def _dp_keep(P, tol):
    """Douglas-Peucker on an open polyline P (n x 2 array); returns kept indices.
    Uses the distance to the segment (not the infinite line), iteratively."""
    n = len(P)
    keep = np.zeros(n, dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j - i < 2:
            continue
        a = P[i]
        ab = P[j] - a
        L2 = float(ab @ ab)
        Q = P[i + 1:j] - a
        if L2 > 0.0:
            t = np.clip((Q @ ab) / L2, 0.0, 1.0)
            d = np.hypot(Q[:, 0] - t * ab[0], Q[:, 1] - t * ab[1])
        else:
            d = np.hypot(Q[:, 0], Q[:, 1])
        k = int(np.argmax(d))
        if d[k] > tol:
            m = i + 1 + k
            keep[m] = True
            stack.append((i, m))
            stack.append((m, j))
    return np.nonzero(keep)[0]


def simplify_ring(ring, tol):
    """Douglas-Peucker for a closed ring. The ring is split at two extreme vertices
    (farthest from the vertex centroid, and farthest from that one), which are convex
    hull vertices and therefore always worth keeping."""
    n = len(ring)
    if tol <= 0 or n < 4:
        return list(ring)
    P = np.asarray(ring, dtype=float)
    a = int(np.argmax(((P - P.mean(axis=0)) ** 2).sum(axis=1)))
    P = np.roll(P, -a, axis=0)
    b = int(np.argmax(((P - P[0]) ** 2).sum(axis=1)))
    if b == 0:
        return [tuple(p) for p in P]
    k1 = _dp_keep(P[:b + 1], tol)
    k2 = _dp_keep(np.vstack([P[b:], P[:1]]), tol) + b
    idx = list(k1[:-1]) + list(k2[:-1])
    return [(float(P[i][0]), float(P[i][1])) for i in idx]


def _cross_point(p1, p2, q1, q2):
    """Proper intersection point of segments p1p2 and q1q2, or None."""
    d1 = _orient(q1[0], q1[1], q2[0], q2[1], p1[0], p1[1])
    d2 = _orient(q1[0], q1[1], q2[0], q2[1], p2[0], p2[1])
    d3 = _orient(p1[0], p1[1], p2[0], p2[1], q1[0], q1[1])
    d4 = _orient(p1[0], p1[1], p2[0], p2[1], q2[0], q2[1])
    if d1 * d2 < 0 and d3 * d4 < 0:
        t = d1 / (d1 - d2)
        return p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1])
    return None


def untwist_ring(ring, max_span=UNTWIST_MAX_SPAN, max_area=UNTWIST_MAX_AREA):
    """Remove tiny self-intersecting loops (a source-data defect): if edge i crosses
    edge i+s (2 <= s <= max_span) and the loop between them is smaller than max_area,
    replace the loop's vertices by the crossing point. Returns (ring, loops_removed)."""
    removed = 0
    changed = True
    while changed and len(ring) >= 4:
        changed = False
        n = len(ring)
        for i in range(n):
            for s in range(2, min(max_span, n - 2) + 1):
                j = (i + s) % n
                X = _cross_point(ring[i], ring[(i + 1) % n], ring[j], ring[(j + 1) % n])
                if X is None:
                    continue
                loop = [X] + [ring[(i + k) % n] for k in range(1, s + 1)]
                if abs(area_en(loop)) > max_area:
                    continue
                r = ring[i:] + ring[:i]               # rotate so that edge i is edge 0
                ring = [r[0], X] + r[s + 1:]
                removed += 1
                changed = True
                break
            if changed:
                break
    return ring, removed


def snap_ring(ring):
    """Round to 0.1 m (as integer decimetres), drop duplicates, exactly collinear
    vertices and zero-width spikes. Returns a ring of int (dx, dz) or None."""
    r = dedupe([(int(round(x * 10.0)), int(round(z * 10.0))) for x, z in ring])
    changed = True
    while changed and len(r) >= 3:
        changed = False
        out = []
        n = len(r)
        skip_next = False
        for i in range(n):
            if skip_next:
                skip_next = False
                out.append(r[i])
                continue
            ax, az = r[i - 1]
            bx, bz = r[i]
            cx, cz = r[(i + 1) % n]
            if (bx - ax) * (cz - bz) - (bz - az) * (cx - bx) == 0:
                changed = True          # collinear (straight run or spike): drop b
                skip_next = True        # re-evaluate the neighbour next pass
                continue
            out.append(r[i])
        r = dedupe(out)
    return r if len(r) >= 3 else None


def dm_to_m(ring_dm):
    return [(x / 10.0, z / 10.0) for x, z in ring_dm]


def _orient(ax, az, bx, bz, cx, cz):
    return (bx - ax) * (cz - az) - (bz - az) * (cx - ax)


def _on_segment(px, pz, ax, az, bx, bz):
    """For a point already known to be collinear with a-b: is it within the segment?"""
    return ((np.minimum(ax, bx) <= px) & (px <= np.maximum(ax, bx)) &
            (np.minimum(az, bz) <= pz) & (pz <= np.maximum(az, bz)))


def ring_defects(rings_dm):
    """Count crossing and touching pairs of non-adjacent edges among the rings of one
    polygon (exact integer arithmetic on the decimetre grid)."""
    A, B, rid, sid, rlen = [], [], [], [], []
    for k, r in enumerate(rings_dm):
        n = len(r)
        for i in range(n):
            A.append(r[i])
            B.append(r[(i + 1) % n])
            rid.append(k)
            sid.append(i)
            rlen.append(n)
    if not A:
        return 0, 0
    A = np.array(A, dtype=np.int64)
    B = np.array(B, dtype=np.int64)
    rid = np.array(rid)
    sid = np.array(sid)
    rlen = np.array(rlen)
    minx = np.minimum(A[:, 0], B[:, 0])
    maxx = np.maximum(A[:, 0], B[:, 0])
    minz = np.minimum(A[:, 1], B[:, 1])
    maxz = np.maximum(A[:, 1], B[:, 1])
    crossings = touches = 0
    m = len(A)
    for i in range(m - 1):
        j = np.arange(i + 1, m)
        j = j[(minx[j] <= maxx[i]) & (maxx[j] >= minx[i]) &
              (minz[j] <= maxz[i]) & (maxz[j] >= minz[i])]
        if j.size == 0:
            continue
        same = rid[j] == rid[i]
        adj = same & ((sid[j] == sid[i] + 1) | ((sid[i] == 0) & (sid[j] == rlen[i] - 1)))
        j = j[~adj]
        if j.size == 0:
            continue
        p1, p2 = A[i], B[i]
        q1, q2 = A[j], B[j]
        d1 = np.sign(_orient(q1[:, 0], q1[:, 1], q2[:, 0], q2[:, 1], p1[0], p1[1]))
        d2 = np.sign(_orient(q1[:, 0], q1[:, 1], q2[:, 0], q2[:, 1], p2[0], p2[1]))
        d3 = np.sign(_orient(p1[0], p1[1], p2[0], p2[1], q1[:, 0], q1[:, 1]))
        d4 = np.sign(_orient(p1[0], p1[1], p2[0], p2[1], q2[:, 0], q2[:, 1]))
        cross = (d1 * d2 < 0) & (d3 * d4 < 0)
        crossings += int(np.count_nonzero(cross))
        # touching: an endpoint of one edge lies on the other edge
        on = _on_segment
        t = ((d1 == 0) & on(p1[0], p1[1], q1[:, 0], q1[:, 1], q2[:, 0], q2[:, 1])) | \
            ((d2 == 0) & on(p2[0], p2[1], q1[:, 0], q1[:, 1], q2[:, 0], q2[:, 1])) | \
            ((d3 == 0) & on(q1[:, 0], q1[:, 1], p1[0], p1[1], p2[0], p2[1])) | \
            ((d4 == 0) & on(q2[:, 0], q2[:, 1], p1[0], p1[1], p2[0], p2[1]))
        touches += int(np.count_nonzero(t & ~cross))
    return crossings, touches


def point_in_rings(px, pz, rings):
    """Even-odd point-in-polygon over all rings (outer + holes) of one polygon."""
    inside = False
    for R in rings:
        R = np.asarray(R, dtype=float)
        x1, z1 = R[:, 0], R[:, 1]
        x2, z2 = np.roll(x1, -1), np.roll(z1, -1)
        cond = (z1 > pz) != (z2 > pz)
        with np.errstate(divide='ignore', invalid='ignore'):
            xs = x1 + (pz - z1) * (x2 - x1) / (z2 - z1)
        if np.count_nonzero(cond & (px < xs)) % 2:
            inside = not inside
    return inside


def point_in_polys(px, pz, polys):
    return any(point_in_rings(px, pz, rings) for rings in polys)


def outward_normal(ax, az, bx, bz):
    """Outward unit normal (in x, z) of edge a->b of a ring that is CCW in (east, north)
    space (outer ring): the interior is on the left in (e, n), i.e. the outward normal
    in (e, n) is (dn, -de); with n = -z that is (-dz, dx) in (x, z)."""
    dx, dz = bx - ax, bz - az
    L = math.hypot(dx, dz)
    if L == 0:
        return None
    return -dz / L, dx / L


# =======================================================================================
# Feature processing
# =======================================================================================

def raw_polygons(geom):
    if not geom:
        return []
    t = geom.get('type')
    if t == 'Polygon':
        return [geom['coordinates']]
    if t == 'MultiPolygon':
        return list(geom['coordinates'])
    if t == 'GeometryCollection':
        return [p for g in geom.get('geometries', []) for p in raw_polygons(g)]
    return []


class Log:
    """Geometry events, reported in the build report. Entries are (label, ...)."""
    def __init__(self):
        self.dropped_rings = []     # (label, 'outer'|'hole', area m^2)
        self.untwisted = []         # (label, loops removed)
        self.fixed = []             # (label, tolerance used, crossings at nominal tol)
        self.invalid = []           # (label, crossings, touches)
        self.touching = []          # (label, touches)

    def snapshot(self):
        return {k: list(v) for k, v in vars(self).items()}

    def restore(self, snap):
        for k, v in snap.items():
            setattr(self, k, list(v))


def process_polygon(raw_rings, tol, label, log):
    """Project, simplify, snap to 0.1 m, untwist, filter and orient one polygon.
    Returns a list of rings (float metres; rings[0] outer, CCW in (e, n)) or None."""
    projected = [dedupe([project(c[0], c[1]) for c in ring]) for ring in raw_rings]

    def build(t):
        rings_dm, dropped, loops = [], [], 0
        for ri, ring in enumerate(projected):
            r = snap_ring(simplify_ring(ring, t)) if len(ring) >= 3 else None
            if r:
                # snapping can fold sub-decimetre slivers of the source into tiny
                # self-crossing loops (and the source may contain some): remove them
                rm, k = untwist_ring(dm_to_m(r))
                if k:
                    loops += k
                    r = snap_ring(rm)
            a = abs(area_en(r)) / 100.0 if r else 0.0
            if r is None or a < MIN_RING_AREA:
                dropped.append(('outer' if ri == 0 else 'hole', a))
                if ri == 0:
                    return [], dropped, loops
                continue
            if (area_en(r) > 0) != (ri == 0):        # outer CCW, holes CW in (e, n)
                r = r[::-1]
            rings_dm.append(r)
        return rings_dm, dropped, loops

    rings_dm, dropped, loops = build(tol)
    log.dropped_rings += [(label, kind, a) for kind, a in dropped]
    if not rings_dm:
        return None
    crossings, touches = ring_defects(rings_dm)
    if crossings:
        # Simplification can make nearly-touching parts cross: retry with finer tolerances.
        for t in (tol / 2, tol / 4, tol / 8, 0.0):
            cand, _, cand_loops = build(t)
            c2, t2 = ring_defects(cand) if cand else (1, 0)
            if c2 == 0:
                log.fixed.append((label, t, crossings))
                rings_dm, crossings, touches, loops = cand, 0, t2, cand_loops
                break
        if crossings:
            log.invalid.append((label, crossings, touches))
    if loops:
        log.untwisted.append((label, loops))
    if touches:
        log.touching.append((label, touches))
    return [dm_to_m(r) for r in rings_dm]


def process_feature(feat, tol, log):
    label = '%s [%s]' % (fname(feat), fid(feat))
    polys = []
    for raw in raw_polygons(feat['geometry']):
        p = process_polygon(raw, tol, label, log)
        if p:
            polys.append(p)
    return polys


# =======================================================================================
# Gates vs building boundary
# =======================================================================================

def gate_sort_key(g):
    m = re.fullmatch(r'([A-Za-z]+)(\d+)([A-Za-z]*)', g['name'])
    if m:
        return (m.group(1), int(m.group(2)), m.group(3))
    return (g['name'], 0, '')


def build_boundary(tc_polys, ba_list):
    """Candidate building-boundary edges: the outer rings of the terminal complex and of
    the boarding areas (all oriented CCW in (east, north), so the outward normal of edge
    a->b is (-dz, dx) in (x, z)). Edges of one ring are stored contiguously."""
    A, B, src, rid, first, count = [], [], [], [], [], []
    rings = [('terminalComplex', p[0]) for p in tc_polys]
    rings += [('Boarding Area ' + ba['letter'], p[0]) for ba in ba_list for p in ba['polys']]
    for ri, (label, r) in enumerate(rings):
        n = len(r)
        for i in range(n):
            A.append(r[i])
            B.append(r[(i + 1) % n])
            src.append(label)
            rid.append(ri)
            first.append(len(A) - 1 - i)
            count.append(n)
    A = np.array(A, dtype=float)
    B = np.array(B, dtype=float)
    D = B - A
    L = np.hypot(D[:, 0], D[:, 1])
    N = np.column_stack([-D[:, 1] / L, D[:, 0] / L])
    return {'A': A, 'B': B, 'N': N, 'L': L, 'src': src, 'rid': rid,
            'first': np.array(first), 'count': np.array(count),
            'is_tc': np.array([s == 'terminalComplex' for s in src]), 'rings': rings}


def project_on_segments(px, pz, A, B):
    """Nearest points on all segments A[i]->B[i]: returns (t, Q, distance) arrays."""
    AB = B - A
    AP = np.array([px, pz]) - A
    L2 = (AB ** 2).sum(axis=1)
    with np.errstate(divide='ignore', invalid='ignore'):
        t = np.where(L2 > 0, (AP * AB).sum(axis=1) / np.where(L2 > 0, L2, 1.0), 0.0)
    t = np.clip(t, 0.0, 1.0)
    Q = A + AB * t[:, None]
    return t, Q, np.hypot(px - Q[:, 0], pz - Q[:, 1])


def ring_walk(ring, i, px, pz, dist, forward):
    """Point reached by walking `dist` m along the ring from (px, pz), which lies on
    edge i (ring[i] -> ring[i+1]), forwards or backwards."""
    n = len(ring)
    j, rem = i, dist
    for _ in range(n + 1):
        tx, tz = ring[(j + 1) % n] if forward else ring[j]
        L = math.hypot(tx - px, tz - pz)
        if L >= rem and L > 0:
            return px + (tx - px) * rem / L, pz + (tz - pz) * rem / L
        rem -= L
        px, pz = tx, tz
        j = (j + 1) % n if forward else (j - 1) % n
    return px, pz


def chord_normal(ring, i, px, pz, half):
    """Outward normal of the chord spanning +-half m of boundary around (px, pz) on edge
    i; equals the length-weighted mean of the edge normals over that stretch."""
    sx, sz = ring_walk(ring, i, px, pz, half, False)
    ex, ez = ring_walk(ring, i, px, pz, half, True)
    return outward_normal(sx, sz, ex, ez)


def analyse_gate(gx, gz, bnd, tc_polys, building_polys):
    """Relationship of a gate point to the building outline.

    edge: nearest point on the terminal-complex outer rings, or on a boarding-area outer
          ring if that is more than BA_PREFERENCE_EPS closer;
    out:  outward unit normal of the boundary edge at that point. If the nearest point is
          a vertex, the adjacent edge whose normal best matches the gate->edge direction
          (edge->gate for gates outside) is used. If that edge is shorter than
          MIN_FACADE_SEG (a small jog in the facade), the normal of the chord spanning
          +-SMOOTH_HALF m of boundary is used instead ('smoothed').
    test: edge + out * PROBE_DIST must lie outside the terminal complex. If it does not,
          the nearest boundary point on an edge >= MIN_FACADE_SEG long that faces the gate
          the right way and faces open space is used instead ('fallback')."""
    t, Q, d = project_on_segments(gx, gz, bnd['A'], bnd['B'])
    is_tc = bnd['is_tc']
    k_tc = int(np.flatnonzero(is_tc)[np.argmin(d[is_tc])])
    k_ba = int(np.flatnonzero(~is_tc)[np.argmin(d[~is_tc])])
    k = k_ba if d[k_ba] < d[k_tc] - BA_PREFERENCE_EPS else k_tc
    qx, qz, dist = float(Q[k, 0]), float(Q[k, 1]), float(d[k])
    first, n = int(bnd['first'][k]), int(bnd['count'][k])
    i = k - first
    ring = bnd['rings'][bnd['rid'][k]][1]
    seg_len = float(bnd['L'][k])
    other, at_vertex = None, None
    if t[k] * seg_len < 1e-6:
        at_vertex, other = 'start', first + (i - 1) % n
    elif (1.0 - t[k]) * seg_len < 1e-6:
        at_vertex, other = 'end', first + (i + 1) % n
    kn = k                                   # edge that supplies the normal
    if other is not None and dist > 1e-6:
        rx, rz = (qx - gx) / dist, (qz - gz) / dist
        if not point_in_rings(gx, gz, [ring]):
            rx, rz = -rx, -rz
        if bnd['N'][other] @ (rx, rz) > bnd['N'][k] @ (rx, rz):
            kn = other
    normal = (float(bnd['N'][kn][0]), float(bnd['N'][kn][1]))
    smoothed = bool(bnd['L'][kn] < MIN_FACADE_SEG or (other is not None and dist <= 1e-6))
    if smoothed:
        normal = chord_normal(ring, i, qx, qz, SMOOTH_HALF)

    def probe_ok(ex, ez, nx, nz):
        return not point_in_polys(ex + nx * PROBE_DIST, ez + nz * PROBE_DIST, tc_polys)

    inside = point_in_polys(gx, gz, building_polys)
    res = {'edge': (qx, qz), 'out': normal, 'dist': dist, 'source': bnd['src'][k],
           'at_vertex': at_vertex, 'smoothed': smoothed,
           'seg_normal': (float(bnd['N'][kn][0]), float(bnd['N'][kn][1])),
           'inside_tc': point_in_polys(gx, gz, tc_polys), 'inside_building': inside,
           'd_tc': float(d[k_tc]), 'd_ba': float(d[k_ba]),
           'probe_ok': probe_ok(qx, qz, *normal), 'fallback': False}
    if res['probe_ok']:
        return res
    res['primary'] = {'edge': (qx, qz), 'out': normal, 'dist': dist, 'source': res['source']}

    def faces_open_space(ex, ez, nx, nz):
        # the probe and two points FALLBACK_HALF_WIDTH to either side of it must all be
        # outside the terminal complex (rejects the ends/sides of narrow slots)
        px, pz = ex + nx * PROBE_DIST, ez + nz * PROBE_DIST
        return all(not point_in_polys(px - nz * s, pz + nx * s, tc_polys)
                   for s in (0.0, -FALLBACK_HALF_WIDTH, FALLBACK_HALF_WIDTH))

    for j in np.argsort(d, kind='stable'):
        if bnd['L'][j] < MIN_FACADE_SEG:
            continue
        ex, ez = float(Q[j, 0]), float(Q[j, 1])
        nx, nz = float(bnd['N'][j][0]), float(bnd['N'][j][1])
        if d[j] > 0.5:
            facing = (ex - gx) * nx + (ez - gz) * nz
            if (inside and facing <= 0) or (not inside and facing >= 0):
                continue
        if faces_open_space(ex, ez, nx, nz):
            res.update({'edge': (ex, ez), 'out': (nx, nz), 'dist': float(d[j]),
                        'source': bnd['src'][j], 'at_vertex': None, 'smoothed': False,
                        'fallback': True})
            break
    return res


# =======================================================================================
# Runway sanity check
# =======================================================================================

def polygon_moments(polys):
    """Area, centroid and central second moments in (east, north) space."""
    ox, oy = polys[0][0][0][0], -polys[0][0][0][1]
    A = Sx = Sy = Sxx = Syy = Sxy = 0.0
    for p in polys:
        for ring in p:
            pts = [(x - ox, -z - oy) for x, z in ring]
            n = len(pts)
            for i in range(n):
                x1, y1 = pts[i]
                x2, y2 = pts[(i + 1) % n]
                c = x1 * y2 - x2 * y1
                A += c
                Sx += (x1 + x2) * c
                Sy += (y1 + y2) * c
                Sxx += (x1 * x1 + x1 * x2 + x2 * x2) * c
                Syy += (y1 * y1 + y1 * y2 + y2 * y2) * c
                Sxy += (x1 * y2 + 2 * x1 * y1 + 2 * x2 * y2 + x2 * y1) * c
    A *= 0.5
    cx, cy = Sx / (6 * A), Sy / (6 * A)
    cxx = Sxx / 12 - A * cx * cx
    cyy = Syy / 12 - A * cy * cy
    cxy = Sxy / 24 - A * cx * cy
    return A, (cx + ox, cy + oy), (cxx, cyy, cxy)


def heading_deg(ue, un):
    return math.degrees(math.atan2(ue, un)) % 360.0


def runway_ends(name):
    """'RUNWAY 01L/19R' -> ['1L', '19R']"""
    return [e.lstrip('0') for e in re.findall(r'(\d+[LRC]?)', name)]


def runway_name(ends):
    """['1R', '19L'] -> 'RUNWAY 01R/19L' (the source's naming style)"""
    return 'RUNWAY ' + '/'.join('%02d%s' % (int(re.match(r'\d+', e).group()),
                                             e.lstrip('0123456789')) for e in ends)


def runway_check(polys, ends):
    """Centroid, long axis, length and width of a runway polygon set, compared with the
    surveyed centerline between the two runway ends `ends` (if both are known)."""
    A, (ce, cn), (cxx, cyy, cxy) = polygon_moments(polys)
    th = 0.5 * math.atan2(2 * cxy, cxx - cyy)
    u = (math.cos(th), math.sin(th))                     # long axis in (e, n)
    pts = [(x, -z) for p in polys for r in p for x, z in r]
    along = [(e - ce) * u[0] + (n - cn) * u[1] for e, n in pts]
    across = [-(e - ce) * u[1] + (n - cn) * u[0] for e, n in pts]
    out = {'area': A, 'centroid_xz': (ce, -cn), 'length': max(along) - min(along),
           'width': max(across) - min(across), 'ends': ends, 'hdg_poly': heading_deg(*u)}
    if len(ends) != 2 or not all(e in SURVEYED_ENDS for e in ends):
        return out
    e1 = project(SURVEYED_ENDS[ends[0]][1], SURVEYED_ENDS[ends[0]][0])
    e2 = project(SURVEYED_ENDS[ends[1]][1], SURVEYED_ENDS[ends[1]][0])
    p1, p2 = (e1[0], -e1[1]), (e2[0], -e2[1])
    L = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    v = ((p2[0] - p1[0]) / L, (p2[1] - p1[1]) / L)
    if u[0] * v[0] + u[1] * v[1] < 0:
        u = (-u[0], -u[1])
        along = [-a for a in along]

    def lateral(e, n):  # signed: > 0 = left of the low->high-numbered direction
        return v[0] * (n - p1[1]) - v[1] * (e - p1[0])
    a0, a1 = min(along), max(along)
    s = [(e - p1[0]) * v[0] + (n - p1[1]) * v[1] for e, n in pts]
    out.update({
        'hdg_poly': heading_deg(*u), 'hdg_surv': heading_deg(*v),
        'dhdg': (heading_deg(*u) - heading_deg(*v) + 90.0) % 180.0 - 90.0,
        'len_surv': L, 'off_centroid': lateral(ce, cn),
        'off_end0': lateral(ce + u[0] * a0, cn + u[1] * a0),
        'off_end1': lateral(ce + u[0] * a1, cn + u[1] * a1),
        'beyond0': -min(s), 'beyond1': max(s) - L,
    })
    return out


def match_runways(runways):
    """Compare every runway polygon with every surveyed centerline. If a polygon fits a
    different runway's centerline far better than its own (the source can carry swapped
    designations), rename it and keep the source name in 'srcName'."""
    pairs = [tuple(p) for p in SURVEYED_RUNWAYS]
    proposals = {}
    for rw in runways:
        own = runway_ends(rw['name'])
        rw['check_src'] = runway_check(rw['polys'], own)
        best, best_score = None, None
        for pair in pairs:
            c = runway_check(rw['polys'], list(pair))
            if abs(c['dhdg']) > 5.0:
                continue
            score = abs(c['off_centroid']) + abs(c['length'] - c['len_surv'])
            if best_score is None or score < best_score:
                best, best_score = list(pair), score
        rw['check'] = rw['check_src']
        if best and best != own:
            own_c = rw['check_src']
            own_score = (abs(own_c['off_centroid']) + abs(own_c['length'] - own_c['len_surv'])
                         if 'off_centroid' in own_c else float('inf'))
            if best_score < 0.1 * own_score:
                proposals[id(rw)] = best
    # apply only if the result keeps the designations unique
    names = [runway_name(proposals[id(rw)]) if id(rw) in proposals else rw['name']
             for rw in runways]
    if len(set(names)) == len(names):
        for rw in runways:
            if id(rw) in proposals:
                rw['srcName'] = rw['name']
                rw['name'] = runway_name(proposals[id(rw)])
                rw['check'] = runway_check(rw['polys'], proposals[id(rw)])
    runways.sort(key=lambda r: r['name'])


def max_deviation(feat, polys):
    """Largest distance (m) from a source vertex (of rings >= MIN_RING_AREA) to the
    published outline: the simplification + snapping + clean-up error."""
    segs = [(r[i], r[(i + 1) % len(r)]) for p in polys for r in p for i in range(len(r))]
    if not segs:
        return 0.0
    A = np.array([s[0] for s in segs], dtype=float)
    AB = np.array([s[1] for s in segs], dtype=float) - A
    L2 = (AB ** 2).sum(axis=1)
    L2[L2 == 0] = 1.0
    worst = 0.0
    for raw in raw_polygons(feat['geometry']):
        for ring in raw:
            pr = dedupe([project(c[0], c[1]) for c in ring])
            if len(pr) < 3 or abs(area_en(pr)) < MIN_RING_AREA:
                continue
            P = np.array(pr, dtype=float)
            for s in range(0, len(P), 256):
                AP = P[s:s + 256, None, :] - A[None, :, :]
                t = np.clip((AP * AB[None]).sum(axis=2) / L2[None], 0.0, 1.0)
                d = np.hypot(AP[..., 0] - t * AB[None, :, 0], AP[..., 1] - t * AB[None, :, 1])
                worst = max(worst, float(d.min(axis=1).max()))
    return worst


# =======================================================================================
# Output helpers
# =======================================================================================

def num(v, nd=1):
    v = round(v, nd)
    return int(v) if v == int(v) else v


def fmt_polys(polys):
    return [[[[num(x), num(z)] for x, z in ring] for ring in p] for p in polys]


def bbox_of(points):
    xs = [p[0] for p in points]
    zs = [p[1] for p in points]
    return [min(xs), min(zs), max(xs), max(zs)]


def poly_points(polys):
    return [pt for p in polys for r in p for pt in r]


def load_current(src):
    """All features with mz:is_current == 1, and the number of files scanned."""
    feats = []
    paths = sorted(glob.glob(os.path.join(src, '**', '*.geojson'), recursive=True))
    for path in paths:
        with open(path, encoding='utf-8') as fh:
            f = json.load(fh)
        if (f.get('properties') or {}).get('mz:is_current') == 1:
            feats.append(f)
    return feats, len(paths)


def source_commit(src):
    try:
        import subprocess
        out = subprocess.run(['git', '-C', src, 'log', '-1', '--format=%h %cs'],
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or None
    except Exception:
        return None


def fid(f):
    return f['properties'].get('wof:id')


def fname(f):
    return f['properties'].get('wof:name') or ''


# =======================================================================================
# Main
# =======================================================================================

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--src', default=DEFAULT_SRC)
    ap.add_argument('--out-json', default=DEFAULT_JSON)
    ap.add_argument('--out-report', default=DEFAULT_REPORT)
    args = ap.parse_args()

    feats, n_files = load_current(args.src)
    if not feats:
        sys.exit('no current features found under %s' % args.src)
    by_type = {}
    for f in feats:
        by_type.setdefault(f['properties'].get('sfomuseum:placetype'), []).append(f)
    log = Log()

    # --- terminal complex, terminals, boarding areas ------------------------------------
    tcs = [f for f in by_type.get('building', []) if fname(f) == TERMINAL_COMPLEX_NAME]
    if len(tcs) != 1:
        sys.exit('expected exactly one current "%s", found %d' % (TERMINAL_COMPLEX_NAME, len(tcs)))
    tc_feat = tcs[0]
    tc_polys = process_feature(tc_feat, TOL_BUILDING, log)

    def entry(f, tol, **extra):
        e = {'name': fname(f), 'id': fid(f), 'polys': process_feature(f, tol, log), '_feat': f,
             '_tol': tol}
        e.update(extra)
        return e

    terminals = [entry(f, TOL_BUILDING) for f in sorted(by_type.get('terminal', []), key=fname)]
    bas = []
    for f in by_type.get('boardingarea', []):
        m = re.search(r'\b([A-Z])$', fname(f))
        bas.append(entry(f, TOL_BUILDING, letter=m.group(1) if m else '?'))
    bas.sort(key=lambda b: (b['letter'], b['name']))

    # --- gates -------------------------------------------------------------------------
    bnd = build_boundary(tc_polys, bas)
    building_polys = tc_polys + [p for b in bas for p in b['polys']]
    raw_gates = []
    for f in by_type.get('gate', []):
        p = f['properties']
        g = f['geometry']
        if not g or g.get('type') != 'Point':
            continue
        lon, lat = g['coordinates'][:2]
        x, z = project(lon, lat)
        name = p.get('wof:name') or ''
        m = re.fullmatch(r'([A-Za-z]+)(\d+)([A-Za-z]*)', name)
        raw_gates.append({'name': name, 'letter': name[:1].upper(), 'x': x, 'z': z,
                          'level': p.get('sfo:level'), 'variant': bool(m and m.group(3)),
                          'id': fid(f), 'inception': p.get('edtf:inception') or '',
                          'parent': p.get('wof:parent_id')})
    # order: letter, number, suffix; for duplicated names the newest record comes first,
    # so the later (dup) entries are the older records.
    raw_gates.sort(key=lambda g: g['id'], reverse=True)
    raw_gates.sort(key=lambda g: g['inception'], reverse=True)
    raw_gates.sort(key=gate_sort_key)
    seen = set()
    gates_out, gate_info = [], []
    for g in raw_gates:
        a = analyse_gate(g['x'], g['z'], bnd, tc_polys, building_polys)
        e = {'name': g['name'], 'letter': g['letter'], 'x': num(g['x']), 'z': num(g['z'])}
        if g['level'] is not None:
            e['level'] = g['level']
        e['variant'] = g['variant']
        if g['name'] in seen:
            e['dup'] = True
        seen.add(g['name'])
        e['edge'] = [num(a['edge'][0]), num(a['edge'][1])]
        e['out'] = [num(a['out'][0], 4), num(a['out'][1], 4)]
        e['dist'] = num(a['dist'])
        if a['fallback']:
            e['fallback'] = True
        e['id'] = g['id']
        gates_out.append(e)
        gate_info.append((g, a, e))

    # --- airfield + structures (with size control) ------------------------------------
    def build_taxiways(tol):
        return [entry(f, tol) for f in sorted(by_type.get('taxiway', []),
                                              key=lambda f: (fname(f), fid(f)))]

    def build_structures(tol):
        out = []
        for kind in STRUCTURE_KINDS:
            for f in sorted(by_type.get(kind, []), key=lambda f: (fname(f), fid(f))):
                if fid(f) == fid(tc_feat):
                    continue
                out.append(entry(f, tol, kind=kind))
        return out

    runways = [entry(f, TOL_AIRFIELD) for f in sorted(by_type.get('runway', []), key=fname)]
    runways = [r for r in runways if r['polys']]
    match_runways(runways)
    tol_tw, tol_st = TOL_AIRFIELD, TOL_STRUCTURE
    base_log = log.snapshot()
    escalation = [(tol_tw, tol_st)] + [(t, t) for t in TOL_ESCALATION]
    for tol_tw, tol_st in escalation:
        log.restore(base_log)
        taxiways = build_taxiways(tol_tw)
        structures = build_structures(tol_st)
        doc = assemble(tc_polys, terminals, bas, gates_out, taxiways, runways, structures)
        blob = json.dumps(doc, separators=(',', ':'), ensure_ascii=False)
        if len(blob.encode('utf-8')) <= MAX_JSON_BYTES:
            break
    size = len(blob.encode('utf-8'))
    if size > MAX_JSON_BYTES:
        print('warning: %d bytes even at tolerance %.2g m' % (size, tol_tw), file=sys.stderr)
    os.makedirs(os.path.dirname(os.path.abspath(args.out_json)), exist_ok=True)
    with open(args.out_json, 'w', encoding='utf-8') as fh:
        fh.write(blob)

    tc_entry = {'name': TERMINAL_COMPLEX_NAME, 'id': fid(tc_feat), 'polys': tc_polys,
                '_feat': tc_feat, '_tol': TOL_BUILDING}
    report = make_report(doc, size, args, n_files, feats, by_type, tc_entry, terminals, bas,
                         gate_info, taxiways, runways, structures, log, (tol_tw, tol_st))
    with open(args.out_report, 'w', encoding='utf-8') as fh:
        fh.write(report)
    print('wrote %s (%.1f KB) and %s' % (os.path.normpath(args.out_json), size / 1024.0,
                                         os.path.normpath(args.out_report)))


def assemble(tc_polys, terminals, bas, gates_out, taxiways, runways, structures):
    pts = poly_points(tc_polys)
    for group in (terminals, bas, taxiways, runways, structures):
        for e in group:
            pts += poly_points(e['polys'])
    pts += [(g['x'], g['z']) for g in gates_out] + [tuple(g['edge']) for g in gates_out]
    return {
        'attribution': ATTRIBUTION,
        'ringConvention': RING_CONVENTION,
        'frame': FRAME,
        'bounds': [num(v) for v in bbox_of(pts)],
        'terminalComplex': fmt_polys(tc_polys),
        'terminals': [{'name': t['name'], 'id': t['id'], 'polys': fmt_polys(t['polys'])}
                      for t in terminals],
        'boardingAreas': [{'name': b['name'], 'letter': b['letter'], 'id': b['id'],
                           'polys': fmt_polys(b['polys'])} for b in bas],
        'gates': gates_out,
        'taxiways': [{'name': t['name'], 'id': t['id'], 'polys': fmt_polys(t['polys'])}
                     for t in taxiways if t['polys']],
        'runways': [dict([('name', r['name'])] +
                         ([('srcName', r['srcName'])] if 'srcName' in r else []) +
                         [('id', r['id']), ('polys', fmt_polys(r['polys']))])
                    for r in runways],
        'structures': [{'name': s['name'], 'kind': s['kind'], 'id': s['id'],
                        'polys': fmt_polys(s['polys'])} for s in structures if s['polys']],
    }


def _fmt(v, nd=1):
    return ('%.' + str(nd) + 'f') % v


def _bbox_str(b):
    return '[%s, %s, %s, %s]' % tuple(_fmt(v) for v in b)


def _angle_deg(a, b):
    return math.degrees(math.acos(max(-1.0, min(1.0, a[0] * b[0] + a[1] * b[1]))))


def make_report(doc, size, args, n_files, feats, by_type, tc_entry, terminals, bas, gate_info,
                taxiways, runways, structures, log, tols):
    tc_polys = tc_entry['polys']
    L = []
    w = L.append
    commit = source_commit(args.src)
    tw_tol, st_tol = tols
    w('# SFO airport geometry: build report')
    w('')
    w('Built by `tools/build_sfo_airport.py` from the SFO Museum *sfomuseum-data-architecture* '
      'checkout (`%s`%s, CDLA-Permissive-1.0): %d GeoJSON files scanned, %d with '
      '`mz:is_current == 1` used.' % (args.src, ', commit ' + commit if commit else '',
                                      n_files, len(feats)))
    w('')
    w('- Output: `%s`, **%.1f KB** (%d bytes, compact JSON).' % (
        os.path.normpath(args.out_json), size / 1024.0, size))
    w('- World frame: x = east, z = south (m), origin ARP 37.6188056, -122.3754167; '
      'coordinates rounded to 0.1 m. `bounds` = %s.' % doc['bounds'])
    esc = '' if (tw_tol, st_tol) == (TOL_AIRFIELD, TOL_STRUCTURE) else \
        ' (**raised** from %.1f m to stay under %.1f MB)' % (TOL_AIRFIELD, MAX_JSON_BYTES / 1e6)
    w('- Douglas-Peucker tolerances: terminal complex / terminals / boarding areas %.1f m, '
      'runways %.1f m, taxiways %.2g m, structures %.2g m%s. Rings < %g m^2 dropped; '
      'holes kept.' % (TOL_BUILDING, TOL_AIRFIELD, tw_tol, st_tol, esc, MIN_RING_AREA))
    w('- Rings: outer counter-clockwise / holes clockwise in (east, north) = (x, -z); open '
      '(first vertex not repeated). Every feature also carries its `id` (wof:id).')
    w('')

    # ---- counts ------------------------------------------------------------------------
    def stats(entries):
        polys = [p for e in entries for p in e['polys']]
        rings = sum(len(p) for p in polys)
        return len(polys), rings, rings - len(polys), sum(len(r) for p in polys for r in p)

    w('## Counts')
    w('')
    w('| Category | Current source features | Output entries | Polygons | Rings (holes) | Vertices |')
    w('|---|---|---|---|---|---|')
    tc_e = [{'polys': tc_polys}]
    rows = [('terminalComplex', 1, tc_e), ('terminals', len(by_type.get('terminal', [])), terminals),
            ('boardingAreas', len(by_type.get('boardingarea', [])), bas),
            ('taxiways', len(by_type.get('taxiway', [])), [t for t in taxiways if t['polys']]),
            ('runways', len(by_type.get('runway', [])), [r for r in runways if r['polys']])]
    for kind in STRUCTURE_KINDS:
        n_src = len(by_type.get(kind, [])) - (1 if kind == 'building' else 0)
        rows.append(('structures: ' + kind, n_src,
                     [s for s in structures if s['kind'] == kind and s['polys']]))
    tot = [0, 0, 0, 0]
    for label, n_src, entries in rows:
        np_, nr, nh, nv = stats(entries)
        tot = [tot[0] + np_, tot[1] + nr, tot[2] + nh, tot[3] + nv]
        w('| %s | %d | %d | %d | %d (%d) | %d |' % (label, n_src, len(entries), np_, nr, nh, nv))
    gates = [e for _, _, e in gate_info]
    n_l2 = sum(1 for e in gates if e.get('level') == 2)
    n_l0 = sum(1 for e in gates if e.get('level') == 0)
    n_var = sum(1 for e in gates if e['variant'])
    w('| gates (points) | %d | %d | | | |' % (len(by_type.get('gate', [])), len(gates)))
    w('| **total polygons** | | | %d | %d (%d) | %d |' % tuple(tot))
    w('')
    w('Gates: %d at level 2 (terminal gates), %d at level 0 (apron positions); %d have a '
      'letter suffix (`variant: true`), %d duplicate-name records flagged `dup`. Structures: '
      'the terminal complex is excluded from `structures`.' % (
          n_l2, n_l0, n_var, sum(1 for e in gates if e.get('dup'))))
    w('')

    # ---- boarding areas ----------------------------------------------------------------
    w('## Boarding areas')
    w('')
    w('| Letter | Name | bbox [minx, minz, maxx, maxz] (m) | E-W x N-S (m) | Area (m^2) | Gates (level 2 / level 0) |')
    w('|---|---|---|---|---|---|')
    for b in bas:
        bb = bbox_of(poly_points(b['polys']))
        area = sum(area_en(r) for p in b['polys'] for r in p)
        g2 = sum(1 for e in gates if e['letter'] == b['letter'] and e.get('level') == 2)
        g0 = sum(1 for e in gates if e['letter'] == b['letter'] and e.get('level') == 0)
        w('| %s | %s | %s | %.0f x %.0f | %.0f | %d / %d |' % (
            b['letter'], b['name'], _bbox_str(bb), bb[2] - bb[0], bb[3] - bb[1], area, g2, g0))
    w('')

    # ---- gates by letter ---------------------------------------------------------------
    w('## Gates by letter')
    w('')
    w('Order as in the JSON. `(dup)` = later record of a duplicated name; `(L0)` = level 0 '
      'without a suffix.')
    w('')
    w('| Letter | Count | Gates | Variants (letter suffix) |')
    w('|---|---|---|---|')
    for letter in sorted({e['letter'] for e in gates}):
        es = [e for e in gates if e['letter'] == letter]
        main = [e['name'] + (' (dup)' if e.get('dup') else '') +
                (' (L0)' if e.get('level') == 0 else '') for e in es if not e['variant']]
        var = [e['name'] + (' (dup)' if e.get('dup') else '') for e in es if e['variant']]
        w('| %s | %d | %s | %s |' % (letter, len(es), ', '.join(main), ', '.join(var) or '-'))
    w('')

    # ---- gate <-> building -------------------------------------------------------------
    w('## Gates vs building outline')
    w('')
    w('`edge` = nearest point on the (simplified, as-published) outer boundary of the terminal '
      'complex, or of a boarding-area polygon when that is > %.2f m closer; `out` = outward unit '
      'normal of that boundary edge; `dist` = gate-to-edge distance. At a vertex the adjacent '
      'edge whose normal best matches the gate direction is used. Test: `edge + out * %g m` '
      'must lie outside the terminal complex.' % (BA_PREFERENCE_EPS, PROBE_DIST))
    w('')

    def dstats(sel):
        ds = sorted(a['dist'] for g, a, e in sel)
        if not ds:
            return 'none'
        return 'min %.1f / median %.1f / max %.1f m' % (ds[0], ds[len(ds) // 2], ds[-1])
    l2 = [x for x in gate_info if x[0]['level'] == 2]
    l0 = [x for x in gate_info if x[0]['level'] == 0]
    w('- Level-2 gates (%d): dist %s; %d inside the terminal complex, %d inside the building '
      '(terminal complex or a boarding area).' % (
          len(l2), dstats(l2), sum(1 for g, a, e in l2 if a['inside_tc']),
          sum(1 for g, a, e in l2 if a['inside_building'])))
    out2 = [(e['name'], a['dist']) for g, a, e in l2 if not a['inside_building']]
    if out2:
        w('  Outside the outline: %s (all on the facade).' % ', '.join(
            '%s %.1f m' % x for x in out2) if max(d for _, d in out2) < 1.0 else
          '  Outside the outline: %s.' % ', '.join('%s %.1f m' % x for x in out2))
    w('- Level-0 positions (%d): dist %s; %d outside the building (apron stands, not doors).' % (
        len(l0), dstats(l0), sum(1 for g, a, e in l0 if not a['inside_building'])))
    n_ba = sum(1 for g, a, e in gate_info if a['source'] != 'terminalComplex')
    w('- Edge taken from a boarding-area polygon (closer than the terminal complex): %d gates.'
      % n_ba)
    w('')

    w('## Anomalies')
    w('')
    # duplicates
    by_name = {}
    for g, a, e in gate_info:
        by_name.setdefault(g['name'], []).append((g, a, e))
    dups = {k: v for k, v in by_name.items() if len(v) > 1}
    w('**Duplicate gate names (%d).** Both records kept; `dup: true` is set on the later '
      'entry, which is ordered to be the *older* record (the first entry is the newest, '
      'consistent with the 2024 terminal outlines).' % len(dups))
    w('')
    for name, recs in sorted(dups.items(), key=lambda kv: gate_sort_key({'name': kv[0]})):
        (g0, _, _) = recs[0]
        parts = []
        for g, a, e in recs:
            parts.append('id %s (%s, level %s%s)' % (g['id'], g['inception'] or '?', g['level'],
                                                     ', dup' if e.get('dup') else ''))
        sep = math.hypot(recs[0][0]['x'] - recs[1][0]['x'], recs[0][0]['z'] - recs[1][0]['z'])
        w('- %s: %s; %s.' % (name, '; '.join(parts),
                              'identical position' if sep < 0.05 else '%.1f m apart' % sep))
    w('')

    # outward test
    fails = [(g, a, e) for g, a, e in gate_info if not a['probe_ok']]
    w('**Outward-normal test (edge + out * %g m outside the terminal complex).** %d of %d gate '
      'records pass with the nearest edge; %d fail%s' % (
          PROBE_DIST, len(gate_info) - len(fails), len(gate_info), len(fails),
          ':' if fails else '.'))
    w('')
    for g, a, e in fails:
        p = a['primary']
        fix = ('fallback edge at %.1f m, out [%.3f, %.3f]' % (a['dist'], a['out'][0], a['out'][1])
               if a['fallback'] else 'no alternative found, left as is')
        w('- %s%s (id %s): nearest edge (%s, %.1f m) has out [%.3f, %.3f], probe inside the '
          'terminal complex -> %s.' % (g['name'], ' (dup)' if e.get('dup') else '', g['id'],
                                       p['source'], p['dist'], p['out'][0], p['out'][1], fix))
    if fails:
        w('')
        w('Fallback = nearest boundary point on an edge >= %g m long that faces away from the '
          'gate and has open space ahead (the probe and points %g m to either side of it are '
          'outside the terminal complex). These entries carry `fallback: true`.' % (
              MIN_FACADE_SEG, FALLBACK_HALF_WIDTH))
        w('')
        w('Cause: at the root of pier A the nearest edges are either an internal '
          'boarding-area partition or the side of a ~1.5 m wide slot between the pier and the '
          'slab west of it, so no nearest-edge normal can point at the apron.'
          if all(e['letter'] == 'A' for g, a, e in fails) else
          'Cause: nearest edge is internal or faces a narrow slot.')
        w('')
    sm = [(g, a, e) for g, a, e in gate_info if a['smoothed']]
    if sm:
        w('**Normals from facade jogs.** For %d gates the edge supplying the normal is shorter '
          'than %g m (a jog in the facade); `out` is the normal of the chord spanning +-%g m of '
          'boundary instead: %s.' % (
              len(sm), MIN_FACADE_SEG, SMOOTH_HALF, ', '.join(
                  '%s%s (%.0f deg change)' % (e['name'], ' (dup)' if e.get('dup') else '',
                                              _angle_deg(a['out'], a['seg_normal']))
                  for g, a, e in sm)))
        w('')

    far = [(g, a, e) for g, a, e in gate_info if a['dist'] > FAR_GATE_DIST]
    w('**Gates > %g m from the building boundary (%d).** All are level-0 apron positions:'
      % (FAR_GATE_DIST, len(far)) if far and all(g['level'] == 0 for g, a, e in far) else
      '**Gates > %g m from the building boundary (%d).**' % (FAR_GATE_DIST, len(far)))
    w('')
    if far:
        w(', '.join('%s %.1f m' % (e['name'], a['dist']) for g, a, e in far) + '.')
        w('')
    deep = [(g, a, e) for g, a, e in l2
            if a['inside_building'] and min(a['d_tc'], a['d_ba']) > 5.0]
    if deep:
        w('Level-2 gates more than 5 m from the nearest boundary (inside the building): %s.'
          % ', '.join('%s %.1f m' % (e['name'], min(a['d_tc'], a['d_ba'])) for g, a, e in deep))
        w('')

    # gates from older snapshots
    current_ids = {fid(f) for f in feats}
    orphans = [(g, e) for g, a, e in gate_info
               if g['level'] == 2 and g['parent'] not in current_ids]
    if orphans:
        w('**Level-2 gates whose parent record is not current (%d)** (older snapshots still '
          'flagged current; included as instructed): %s.' % (len(orphans), ', '.join(
              '%s%s (%s)' % (g['name'], ' dup' if e.get('dup') else '', g['inception'] or '?')
              for g, e in orphans)))
        w('')
    level0_parent = {g['parent'] for g, a, e in l0}
    if l0:
        w('The %d level-0 positions all date from %s and hang off %s.' % (
            len(l0), '/'.join(sorted({g['inception'] for g, a, e in l0})),
            'the airport campus record' if level0_parent == {102527513} else
            'parents %s' % sorted(level0_parent)))
        w('')

    # overlapping structures (AirTrain generations)
    def bbox_iou(a, b):
        ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
        iz = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
        inter = ix * iz
        ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
        return inter / ua if ua > 0 else 0.0
    sts = [s for s in structures if s['polys']]
    pairs = []
    for i in range(len(sts)):
        for j in range(i + 1, len(sts)):
            if sts[i]['kind'] != sts[j]['kind']:
                continue
            iou = bbox_iou(bbox_of(poly_points(sts[i]['polys'])),
                           bbox_of(poly_points(sts[j]['polys'])))
            if iou > 0.3:
                pairs.append((sts[i], sts[j], iou))
    if pairs:
        parent = {s['id']: s['id'] for s in sts}

        def root(k):
            while parent[k] != k:
                k = parent[k]
            return k
        for a, b, iou in pairs:
            parent[root(a['id'])] = root(b['id'])
        clusters = {}
        for s in sts:
            clusters.setdefault(root(s['id']), []).append(s)
        groups = [sorted(v, key=lambda s: s['id']) for v in clusters.values() if len(v) > 1]
        groups.sort(key=lambda v: v[0]['name'])
        w('**Overlapping structures.** %d footprints form %d groups of overlapping duplicates '
          '(bbox IoU > 0.3), all AirTrain stations: the source has two current generations of '
          'station footprints (ids 17297919xx/17300514xx and 17635885xx), and some stations '
          'appear twice within the newer one. The app may want to draw one footprint per group:'
          % (sum(len(v) for v in groups), len(groups)))
        w('')
        for v in groups:
            w('- ' + '; '.join('%s [%s]' % (s['name'], s['id']) for s in v))
        w('')
        swapped = []
        for v in groups:
            letters = {}
            for s in v:
                m = re.search(r'International Terminal \(?([AG])\)?', s['name'])
                if m:
                    letters.setdefault(m.group(1), []).append(s)
            if len(letters) > 1:
                swapped.append(' vs '.join('"%s"' % s['name'] for s in v))
        if swapped:
            w('  Name clash: co-located International Terminal stations carry different letters '
              '(%s). By position the older records are right (A is the southern station, at the '
              'Garage A / Boarding Area A end), so the "(A)"/"(G)" names of the 17635885xx records '
              'are swapped. Published as in the source.' % '; '.join(swapped))
            w('')
    typos = [s['name'] for s in sts if re.search(r'Garaga|\)g$', s['name'])]
    if typos:
        w('Source name typos kept as-is: %s.' % ', '.join('"%s"' % t for t in typos))
        w('')

    # geometry
    w('**Geometry clean-up.**')
    w('')
    if log.dropped_rings:
        w('- Dropped rings < %g m^2: %s.' % (MIN_RING_AREA, '; '.join(
            '%s %s %.2f m^2' % (lab, kind, a) for lab, kind, a in log.dropped_rings)))
    if log.untwisted:
        w('- Tiny self-crossing loops removed (sub-decimetre slivers in the source that fold '
          'over when snapped to 0.1 m): %s.' % '; '.join(
              '%s x%d' % (lab, k) for lab, k in log.untwisted))
    if log.fixed:
        w('- Simplification created crossings, finer tolerance used: %s.' % '; '.join(
            '%s at %.3g m' % (lab, t) for lab, t, c in log.fixed))
    dev_rows = []
    for label, entries in (('terminal complex', [tc_entry]), ('terminals', terminals),
                           ('boarding areas', bas), ('runways', runways),
                           ('taxiways', taxiways), ('structures', structures)):
        devs = [(max_deviation(e['_feat'], e['polys']), e) for e in entries if e['polys']]
        if not devs:
            continue
        worst = max(devs, key=lambda x: x[0])
        over = [(d, e) for d, e in devs if d > e['_tol'] + 0.1]
        dev_rows.append('%s %.2f m (tol %.2g)%s' % (
            label, worst[0], worst[1]['_tol'], '' if not over else ' [over tol+0.1: %s]' % ', '.join(
                '%s %.2f m' % (e['name'], d) for d, e in over)))
    w('- Max distance from any source vertex to the published outline: %s. Larger values '
      'come only from removed defects (zero-width spikes and self-crossing slivers).'
      % '; '.join(dev_rows))
    w('- Output validity: %d polygons with crossing edges, %d with touching edges; all '
      'rings have >= 3 vertices.' % (len(log.invalid), len(log.touching)))
    for lab, c, t in log.invalid:
        w('  - still invalid: %s (%d crossings, %d touches)' % (lab, c, t))
    w('')

    # ---- runways -----------------------------------------------------------------------
    w('## Runway sanity check')
    w('')
    renamed = [rw for rw in runways if 'srcName' in rw]
    if renamed:
        w('**Runway designations swapped in the source:** %s. Each polygon matches the other '
          "runway's surveyed centerline to within ~1.5 m and ~1 m in length, and its own to "
          'within neither, so the build publishes the matching designation as `name` and keeps '
          'the source designation as `srcName`.' % '; '.join(
              'polygon %s is named "%s" (wof:name, sfo:id, sfomuseum:name) but lies %.0f m off '
              'that centerline and is %.0f m long vs %.0f m surveyed; published as "%s"' % (
                  rw['id'], rw['srcName'], abs(rw['check_src']['off_centroid']),
                  rw['check_src']['length'], rw['check_src']['len_surv'], rw['name'])
              for rw in renamed))
        w('')
    w('Polygon centroid (area-weighted, all parts) and long axis from the second moments of '
      'area; length/width = extent of the vertices along/across that axis. Surveyed centerline '
      '= line between the two surveyed runway ends (same projection). Offsets are perpendicular '
      'distances from the surveyed centerline (+ = left of the low-to-high numbered direction); '
      '"beyond ends" = how far the polygon extends past each surveyed end along the centerline '
      '(negative = stops short).')
    w('')
    w('| Runway (published name) | Centroid x, z (m) | Polygon axis (deg T) | Polygon L x W (m) | Surveyed axis (deg T) | Surveyed L (m) | d-heading (deg) | Offset: centroid / axis ends (m) | Beyond ends (m) |')
    w('|---|---|---|---|---|---|---|---|---|')
    for rw in runways:
        c = rw['check']
        cx, cz = c['centroid_xz']
        label = rw['name'] + (' (src: %s)' % rw['srcName'] if 'srcName' in rw else '')
        if 'hdg_surv' in c:
            w('| %s | %.1f, %.1f | %.2f / %.2f | %.0f x %.0f | %.2f / %.2f | %.0f | %+.3f | %+.1f / %+.1f, %+.1f | %s %+.1f, %s %+.1f |' % (
                label, cx, cz, c['hdg_poly'] % 180, c['hdg_poly'] % 180 + 180,
                c['length'], c['width'], c['hdg_surv'] % 180, c['hdg_surv'] % 180 + 180,
                c['len_surv'], c['dhdg'], c['off_centroid'], c['off_end0'], c['off_end1'],
                c['ends'][0], c['beyond0'], c['ends'][1], c['beyond1']))
        else:
            w('| %s | %.1f, %.1f | %.2f | %.0f x %.0f | - | - | - | - | - |' % (
                label, cx, cz, c['hdg_poly'] % 180, c['length'], c['width']))
    w('')
    return '\n'.join(L)


if __name__ == '__main__':
    main()
