"""Shared helpers for the 2-D drawing system (tools/drawing): paths, the extracted scene (out/draw/scene2d.json written
by jobs/extract2d.mjs from the running app), world <-> airport-grid frames, shapely helpers, aircraft planforms from the
real .sfom models / the procedural (TYPES) bodies, and small raster utilities.

World frame (js/geo.js): x east, z south, y up, metres from the ARP; ground at GROUND_Y = 3. Airport grid (s, t):
e = s*V0 + t*U0, n = s*V1 + t*U1, x = e, z = -n (V/U are stored in scene2d.json meta.stBasis).
Frame guard: scene2d.json records the app's world frame id (js/geo.js FRAME_ID). scene() refuses a scene whose frame
differs from tools/geo_frame.py (the Python twin every imagery transform goes through) or from js/geo.js now; a scene
extracted before frame ids existed is treated as the legacy 'equirect-v1' frame and refused too (re-extract).
Staleness: scene2d.json meta.inputs holds the hash of every file the app loaded; stale_inputs() lists those that differ
now in the directory the app was served from (report.py refuses to publish a stale scene unless ALLOW_STALE=1). That
directory is meta.appSource: run_all.sh serves a clean `git archive` of a commit (out/draw/app_snapshot, the default),
so the scene describes that commit exactly however the working tree changes during the run; worktree_changes() then
lists the loaded app files whose working-tree content differs (uncommitted or later work the scene does not cover).
The Python tools read app files (the .sfom models, js/geo.js) from the same directory (app_root()).
"""
import gzip, hashlib, json, math, os, re, struct, sys, functools
import numpy as np
import cv2
import shapely
from shapely.geometry import Polygon, MultiPolygon, Point, LineString, box as sbox
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.environ.get('DRAW_OUT', os.path.join(ROOT, 'out', 'draw'))
# committable outputs (vector sheets, vector conflict crops, report.md); DRAW_DOCS stages them elsewhere (e.g. while
# another run owns docs/drawings)
DOCS = os.environ.get('DRAW_DOCS', os.path.join(ROOT, 'docs', 'drawings'))
os.makedirs(OUT, exist_ok=True)
FT = 0.3048


sys.path.insert(0, os.path.join(ROOT, 'tools'))
import geo_frame as GF  # noqa: E402  (the Python twin of js/geo.js; tools/test_geo_frame.py)
LEGACY_FRAME = 'equirect-v1'


def app_root(S=None):
    """directory the scene's app was served from: the commit snapshot (meta.appSource.dir, relative to the repository)
    or the working tree (the repository itself)"""
    S = S or scene(); a = S['meta'].get('appSource') or {}
    return os.path.normpath(os.path.join(ROOT, a['dir'])) if a.get('kind') == 'git-archive' and a.get('dir') else ROOT


def js_frame_id(S=None):
    """FRAME_ID declared now in js/geo.js of the app the scene was extracted from (none: the legacy frame)"""
    m = re.search(r"FRAME_ID\s*=\s*'([^']+)'", open(os.path.join(app_root(S) if S is not None else ROOT, 'js', 'geo.js')).read())
    return m.group(1) if m else LEGACY_FRAME


class FrameMismatch(SystemExit):
    pass


def check_frame(S):
    """the scene's world frame must be the frame of tools/geo_frame.py (all imagery georeferencing) and of js/geo.js"""
    fid = S['meta'].get('frameId') or LEGACY_FRAME
    if os.environ.get('DRAW_FRAME_CHECK', '1') == '0': return fid
    bad = []
    if fid != GF.FRAME_ID: bad.append(f'tools/geo_frame.py FRAME_ID = {GF.FRAME_ID!r}')
    if fid != js_frame_id(S): bad.append(f'js/geo.js FRAME_ID = {js_frame_id(S)!r} ({os.path.relpath(app_root(S), ROOT)})')
    # the frame id is not enough on its own: the extracted runway ends must equal the Python twin's (1 cm)
    pr = S['meta'].get('probe')
    if pr and not bad:
        for k, e in (('end10L', '10L'), ('end28R', '28R')):
            w = GF.end_world(e); d = math.hypot(pr[k][0] - w[0], pr[k][2] - w[1])
            if d > 0.01: bad.append(f'runway end {e} extracted at ({pr[k][0]:.3f}, {pr[k][2]:.3f}) but geo_frame gives ({w[0]:.3f}, {w[1]:.3f}) ({d:.3f} m)')
    if bad:
        raise FrameMismatch(f'out/draw/scene2d.json was extracted in world frame {fid!r}, but ' + '; '.join(bad)
                            + ' - re-extract (tools/drawing/run_all.sh without SKIP_EXTRACT) before measuring or drawing')
    return fid


def _sha(path):
    try:
        st = os.stat(path); return _sha_cached(os.path.abspath(path), st.st_mtime_ns, st.st_size)
    except OSError: return None


@functools.lru_cache(None)
def _sha_cached(path, mtime_ns, size):
    try:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
        return h.hexdigest()[:16]
    except OSError: return None


def stale_inputs(S=None):
    """files the app loaded at extraction whose content differs now in the directory it was served from ([] = the
    scene describes that app - the commit snapshot or the working tree - exactly); None when the scene predates input
    hashing. A commit snapshot must still be that commit (out/draw/app_snapshot/.rev)"""
    S = S or scene(); inp = S['meta'].get('inputs')
    if not inp: return None
    a = S['meta'].get('appSource') or {}; root = app_root(S)
    if a.get('kind') == 'git-archive':
        try: rev = open(os.path.join(root, '.rev')).read().strip()
        except OSError: rev = None
        if rev != a.get('rev'): return sorted(inp)
    return sorted(p for p, h in inp.items() if _sha(os.path.join(root, p)) != h)


def worktree_changes(S=None):
    """for a scene extracted from a commit snapshot: the loaded app files whose working-tree content differs from the
    scene's (uncommitted edits or later commits the scene does not cover); [] for a working-tree scene"""
    S = S or scene(); inp = S['meta'].get('inputs') or {}
    if (S['meta'].get('appSource') or {}).get('kind') != 'git-archive': return []
    return sorted(p for p, h in inp.items() if _sha(os.path.join(ROOT, p)) != h)


def git_head():
    try:
        import subprocess
        return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT, text=True).strip()
    except Exception: return None


def provenance(S=None):
    """one-line provenance for title blocks and the report: frame, git, extraction time, staleness"""
    S = S or scene(); m = S['meta']; st = stale_inputs(S); a = m.get('appSource') or {'kind': 'worktree'}
    return dict(frame=m.get('frameId') or LEGACY_FRAME, git=m.get('git'), gitHead=m.get('gitHead'), generated=m['generated'], inputsHash=m.get('inputsHash'),
                nInputs=len(m.get('inputs') or {}), stale=st, typesHash=m.get('typesHash'), changedDuring=m.get('inputsChangedDuringExtraction') or [],
                appSource=a.get('kind'), appRev=a.get('rev'), headNow=git_head(), worktreeChanged=worktree_changes(S))


# ------------------------------------------------------------------------------------------------ scene
@functools.lru_cache(None)
def scene():
    S = json.load(open(os.path.join(OUT, 'scene2d.json')))
    check_frame(S)
    S['_bin'] = np.fromfile(os.path.join(OUT, S.get('meshBin', 'meshes.bin')), np.uint8)
    return S


def mesh(entry):
    """(pos (n,3) float32, idx (m,3) uint32) of a mesh packed by extract2d.mjs"""
    B = scene()['_bin']; o = entry['off']; nv, ni = entry['nv'], entry['ni']
    pos = B[o:o + nv * 12].view(np.float32).reshape(-1, 3)
    idx = B[o + nv * 12:o + nv * 12 + ni * 4].view(np.uint32).reshape(-1, 3)
    return pos, idx


def G():
    return scene()['meta']['groundY']


# ------------------------------------------------------------------------------------------------ frames
def _VU():
    b = scene()['meta']['stBasis']; return np.array(b['V']), np.array(b['U'])


def w2st(x, z):
    V, U = _VU(); x = np.asarray(x, float); z = np.asarray(z, float); e, n = x, -z
    return e * V[0] + n * V[1], e * U[0] + n * U[1]


def st2w(s, t):
    V, U = _VU(); s = np.asarray(s, float); t = np.asarray(t, float)
    e = s * V[0] + t * U[0]; n = s * V[1] + t * U[1]
    return e, -n


def st_dir_world():
    """unit world (x,z) vectors of +s and +t"""
    V, U = _VU(); return np.array([V[0], -V[1]]), np.array([U[0], -U[1]])


# ------------------------------------------------------------------------------------------------ shapely helpers
def poly_rings(rings):
    """polygon from [outer, hole, ...] rings ([[x,z],...]); invalid input is repaired"""
    rings = [r for r in rings if len(r) >= 3]
    if not rings: return Polygon()
    P = Polygon(rings[0], rings[1:])
    if not P.is_valid: P = shapely.make_valid(P)
    return P


def only_polys(g):
    if g.is_empty: return Polygon()
    if isinstance(g, (Polygon, MultiPolygon)): return g
    parts = [p for p in getattr(g, 'geoms', []) if isinstance(p, (Polygon, MultiPolygon))]
    return unary_union(parts) if parts else Polygon()


def polys_of(g):
    g = only_polys(g)
    if isinstance(g, Polygon): return [] if g.is_empty else [g]
    return list(g.geoms)


def hull_poly(h):
    if len(h) < 3: return Point(h[0]).buffer(0.05) if h else Polygon()
    return Polygon(h).buffer(0)


def circle(c, r, n=32):
    return Point(c).buffer(r, quad_segs=max(4, n // 4))


# ------------------------------------------------------------------------------------------------ raster helpers
def raster_tris(tri_xz, res, x0, z0, W, H, values=None, img=None, dtype=np.uint8, order=None):
    """draw triangles (m,3,2 world x,z) into a (H,W) grid with pixel (i,j) <-> (x0 + (j+.5) res, z0 + (i+.5) res).
    values: per-triangle value (drawn in `order`, last wins); default 1"""
    if img is None: img = np.zeros((H, W), dtype)
    P = np.round(((tri_xz - [x0, z0]) / res - 0.5) * 16).astype(np.int32)
    idx = order if order is not None else range(len(P))
    if values is None:
        for k in idx: cv2.fillConvexPoly(img, P[k], 1, cv2.LINE_8, 4)
    else:
        for k in idx: cv2.fillConvexPoly(img, P[k], float(values[k]), cv2.LINE_8, 4)
    return img


def mask_to_polys(mask, res, x0, z0, simplify=None):
    """binary mask -> shapely (Multi)Polygon in world coords (pixel centres)"""
    m = (mask > 0).astype(np.uint8)
    cs, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hier is None: return Polygon()
    hier = hier[0]; out = []
    def tw(c): c = c.reshape(-1, 2).astype(float); return np.c_[x0 + (c[:, 0] + 0.5) * res, z0 + (c[:, 1] + 0.5) * res]
    for i, c in enumerate(cs):
        if hier[i][3] != -1 or len(c) < 3: continue
        holes = []; ch = hier[i][2]
        while ch != -1:
            if len(cs[ch]) >= 3: holes.append(tw(cs[ch]))
            ch = hier[ch][0]
        p = Polygon(tw(c), holes).buffer(0)
        if not p.is_empty: out.append(p)
    g = unary_union(out) if out else Polygon()
    # contours run through pixel centres: grow by half a pixel so the outline sits on the pixel edges
    g = g.buffer(res * 0.5, join_style=2)
    if simplify: g = g.simplify(simplify)
    return g


# ------------------------------------------------------------------------------------------------ aircraft geometry
def read_sfom(key):
    raw = open(os.path.join(app_root(), 'data', 'models', key + '.sfom'), 'rb').read()   # the app the scene came from
    if raw[:2] == b'\x1f\x8b': raw = gzip.decompress(raw)
    assert raw[:4] == b'SFOM'
    hl = struct.unpack('<I', raw[8:12])[0]; head = json.loads(raw[12:12 + hl]); B = 12 + hl
    nv, ni, q, o = head['nv'], head['ni'], head['quant'], head['offsets']
    pq = np.frombuffer(raw, np.uint16, nv * 3, B + o['pos']).reshape(-1, 3).astype(np.float64)
    # float32 like the page (models.js decodeModel: Float32Array)
    pos = (np.array(q['pmin']) + pq * np.array(q['pscale'])).astype(np.float32).astype(np.float64)
    idx = np.frombuffer(raw, np.uint16 if head['idxType'] == 'u16' else np.uint32, ni, B + o['idx']).astype(np.int64).reshape(-1, 3)
    zone = np.frombuffer(raw, np.uint8, nv, B + o['zone']).copy() if 'zone' in o else None
    head['_zone'] = zone
    return head, pos, idx


def m4(a):
    """column-major 16 floats (JS Float32Array) -> 4x4 numpy (acting on column vectors)"""
    return np.array(a, float).reshape(4, 4).T


def xform(M, P):
    return P @ M[:3, :3].T + M[:3, 3]


class AcGeom:
    """one aircraft's rendered geometry in the aircraft-local frame (x forward, y up, z right; origin = main gear on
    the ground). plan: shapely polygon (local x,z); ymin/ymax rasters for vertical checks."""
    RES = 0.1

    def __init__(self, pos, idx, source):
        self.source = source
        tri = pos[idx]  # (m,3,3)
        self.tri = tri
        xz = tri[:, :, [0, 2]]
        lo = xz.reshape(-1, 2).min(0) - 1; hi = xz.reshape(-1, 2).max(0) + 1
        r = self.RES; self.x0, self.z0 = lo; self.W, self.H = int((hi[0] - lo[0]) / r) + 1, int((hi[1] - lo[1]) / r) + 1
        yhi = tri[:, :, 1].max(1); ylo = tri[:, :, 1].min(1)
        m = raster_tris(xz, r, self.x0, self.z0, self.W, self.H)
        self.ymax = raster_tris(xz, r, self.x0, self.z0, self.W, self.H, values=yhi, img=np.full((self.H, self.W), -1e3, np.float32), order=np.argsort(yhi))
        self.ymin = raster_tris(xz, r, self.x0, self.z0, self.W, self.H, values=ylo, img=np.full((self.H, self.W), 1e3, np.float32), order=np.argsort(-ylo))
        self.mask = m > 0
        self.plan = mask_to_polys(m, r, self.x0, self.z0, simplify=0.05)
        self.ytop = float(yhi.max()); self.ybot = float(ylo.min())
        b = self.plan.bounds; self.length = b[2] - b[0]; self.span = b[3] - b[1]

    def heights_at(self, lx, lz):
        """(ymin, ymax) at local points (nan where empty)"""
        j = np.floor((np.asarray(lx) - self.x0) / self.RES).astype(int); i = np.floor((np.asarray(lz) - self.z0) / self.RES).astype(int)
        ok = (i >= 0) & (j >= 0) & (i < self.H) & (j < self.W)
        lo = np.full(len(j), np.nan); hi = np.full(len(j), np.nan)
        ii, jj = i[ok], j[ok]; occ = self.mask[ii, jj]
        lo[np.where(ok)[0][occ]] = self.ymin[ii[occ], jj[occ]]; hi[np.where(ok)[0][occ]] = self.ymax[ii[occ], jj[occ]]
        return lo, hi


ZONE_NOFIN = {2, 3, 7}  # engine, gear, pylon (tools/convert_models.py ZONE; js/live/models.js ZONE_NOFIN)


def _stretch(pos, st, zone=None, dims=None):
    """js/live/models.js applyStretch(), same order: wing span fit, fin height fit, fuselage plugs (fit.js plugShift,
    including negative plugs with the aft blend bl2); dims updated"""
    if not st: return pos
    pos = pos.copy(); dims = dims if dims is not None else {}
    W = st.get('wing'); Fn = st.get('fin')
    if W:
        z0, z1, dz, xMin = W['z0'], W['z1'], W['dz'], W['xMin']; sc = dz / (z1 - z0)
        x = pos[:, 0]; z = pos[:, 2]; az = np.abs(z)
        m = (x >= xMin) & (az > z0)
        pos[m, 2] = z[m] + np.sign(z[m]) * np.where(az[m] >= z1, dz, (az[m] - z0) * sc)
        if 'span' in dims: dims['span'] += 2 * dz
    if Fn:
        yF, xF, k = Fn['yF'], Fn['xF'], Fn['k']
        x = pos[:, 0]; y = pos[:, 1]
        m = (x < xF) & (y > yF)
        if zone is not None: m &= ~np.isin(zone, list(ZONE_NOFIN))
        pos[m, 1] = yF + (y[m] - yF) * k
        dims['H'] = float(pos[:, 1].max())
    if st.get('cut1') is not None:
        x = pos[:, 0].copy()
        pos[:, 0] = x + plug_shift(x, st['cut1'], st['d1']) + plug_shift(x, st['cut2'], st['d2'], st.get('bl2') or 0.0)
        if 'L' in dims: dims['L'] += st['d1'] + st['d2']
    return pos


def plug_shift(x, c, d, bl=0.0):
    """js/aircraft/fit.js plugShift (vectorised): x shift of model vertices at x by the fuselage plug at station c of
    length d - a plug (d >= 0) moves everything aft of c (x < c) aft by d; a negative plug removes [c + d, c), the
    section plus a blend bl compressed linearly onto bl, and everything aft of it moves forward by |d|"""
    x = np.asarray(x, float)
    if d >= 0: return np.where(x < c, -d, 0.0)
    D = -d; t = (c - x) / (D + bl) if D + bl > 0 else np.zeros_like(x)
    return np.where(x >= c, 0.0, np.where(x <= c - D - bl, D, (c - t * bl) - x))


@functools.lru_cache(None)
def model_geom(model_key, stretch_json, placement_json):
    """real model (.sfom) in aircraft-local frame: placement * stretched model (exactly as js/live/models.js)"""
    head, pos, idx = read_sfom(model_key)
    st = json.loads(stretch_json) if stretch_json else None
    dims = dict(head.get('dims') or {})
    pos = _stretch(pos, st, head.get('_zone'), dims)
    M = m4(json.loads(placement_json))
    g = AcGeom(xform(M, pos), idx, 'model:' + model_key); g.model_dims = dims
    return g


@functools.lru_cache(None)
def body_geom(type_key):
    """procedural (TYPES-derived) airframe from js/aircraft/model.js buildAircraft(type, 0)"""
    e = scene()['bodies'][type_key]
    pos, idx = mesh(e)
    return AcGeom(pos.astype(np.float64), idx.astype(np.int64), 'procedural:' + type_key)


def ac_instance_geom(a):
    """(AcGeom, W 4x4) for an extracted aircraft record, or (None, None) for markers"""
    if not a.get('W'): return None, None
    W = m4(a['W'])
    if a.get('placement') and a.get('modelKeyUsed'):
        g = model_geom(a['modelKeyUsed'], json.dumps(a['stretch'], sort_keys=True) if a.get('stretch') else '', json.dumps(a['placement']))
    else:
        tk = a['typeKey'] if a.get('typeKey') in scene()['bodies'] else None
        if not tk: return None, None
        g = body_geom(tk)
    return g, W


def plan_world(geom, W):
    """aircraft plan polygon in world x,z (rigid map of local x,z by W; W is ~level on the ground)"""
    A = W[[0, 2]][:, [0, 2]]; t = W[[0, 2], 3]
    return shapely.affinity.affine_transform(geom.plan, [A[0, 0], A[0, 1], A[1, 0], A[1, 1], t[0], t[1]])


def stand_W(nose_xz, dir_xz, T):
    """aircraft-local -> world matrix for an aircraft of type T parked nose at `nose_xz`, heading unit `dir_xz`
    (local origin = main gear = nose - dir * xMain; ground at GROUND_Y)"""
    f = np.array([dir_xz[0], 0, dir_xz[1]]); up = np.array([0, 1.0, 0]); r = np.cross(f, up); r /= np.linalg.norm(r)
    p = np.array([nose_xz[0], G(), nose_xz[1]]) - f * T['xMain']
    M = np.eye(4); M[:3, 0] = f; M[:3, 1] = up; M[:3, 2] = r; M[:3, 3] = p
    return M


def gear_points_world(T, W):
    """nose gear + main gear contact points (world x,z) from TYPES (the gear the app renders under every airframe)"""
    pts = [(T['xMain'] - T['gear']['nose']['x'], 0.0, 'nose')]
    for g in T['gear']['main']:
        for sg in (-1, 1): pts.append((T['xMain'] - g['x'], sg * g['z'], 'main'))
    P = np.array([[p[0], 0, p[1]] for p in pts]); Wp = xform(W, P)
    return [(float(Wp[i, 0]), float(Wp[i, 2]), pts[i][2]) for i in range(len(pts))]


def fmt(v, k=1):
    return f'{v:.{k}f}' if v is not None and not (isinstance(v, float) and math.isnan(v)) else '–'


def ring_area(r):
    P = np.asarray(r, float); return 0.5 * float(np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1]))


@functools.lru_cache(None)
def _buildings():
    """building footprints as built: the terminal complex ramp-level rings (terminals.js buildTerminals: rings whose
    orientation differs from the largest ring are courtyards/holes) merged into polygons with holes; duplicate
    AirTrain station footprints the app skips are dropped"""
    S = scene(); out = []; cx = [b for b in S['buildings'] if b['kind'] == 'apron-level']
    if cx and all(len(b['rings']) == 1 for b in cx):
        rings = [b['rings'][0] for b in cx]; big = max(rings, key=lambda r: abs(ring_area(r))); sg = np.sign(ring_area(big))
        outers = [r for r in rings if np.sign(ring_area(r)) == sg]; holes = [r for r in rings if np.sign(ring_area(r)) != sg]
        for i, o in enumerate(outers):
            po = Polygon(o); hs = [h for h in holes if po.contains(Polygon(h).representative_point())]
            out.append(dict(cx[0], id=f'complex{i}', rings=[o] + hs))
    else: out += cx
    out += [b for b in S['buildings'] if b['kind'] != 'apron-level' and not b.get('notBuilt')]
    return out


def buildings():
    return _buildings()


# ------------------------------------------------------------------------------------------------ physics pavement
class NetPaved:
    """traffic.js TaxiNet.paved(x, z) (GroundPhysics adds it to the raster: ground.js pavedUnion, which tests the net
    at Math.round(x), Math.round(z)): distance to an OSM taxi-net edge < hw (runway edges: 30.5 m), or inside an apron
    ring. Re-implemented with shapely from scene2d.json `net`; verified against the page's own answers
    (scene2d.json physics.samples) by check()."""
    def __init__(self):
        S = scene(); N = S.get('net')
        self.ok = bool(N)
        if not self.ok: return
        from shapely.geometry import LineString as LS
        E = np.array(N['edges'], float)
        segs = [LS([(e[0], e[1]), (e[2], e[3])]).buffer(N['rwHw'] if e[4] else N['hw'], quad_segs=16) for e in E if (e[0], e[1]) != (e[2], e[3])]
        rings = [Polygon(r).buffer(0) for r in N['aprons'] if len(r) >= 3]
        self.geom = unary_union(segs + rings); shapely.prepare(self.geom)

    def __call__(self, x, z):
        x = np.round(np.asarray(x, float)); z = np.round(np.asarray(z, float))
        if not self.ok: return np.zeros(np.shape(x), bool)
        return shapely.contains_xy(self.geom, x, z)

    def check(self):
        smp = scene()['physics'].get('samples')
        if not smp or not self.ok: return None
        A = np.array(smp, float); mine = self(A[:, 0], A[:, 1])
        return dict(n=len(A), agree=float((mine == (A[:, 3] > 0)).mean()))


def phys_gear_points(T, W):
    """GroundPhysics gear points (js/live/ground.js samples(): nose gear xNose (default 3 m) behind the nose, main gear
    at xMain +- track/2 (default 6 m)) in world x, z for an aircraft-local -> world matrix W (x forward, origin = main
    gear); replicated (meta.replicated lists it)"""
    xn = T.get('xNose') if T.get('xNose') is not None else 3.0; tr = (T.get('track') or 6) / 2
    P = np.array([[T['xMain'] - xn, 0, 0], [0, 0, tr], [0, 0, -tr]], float); Q = P @ W[:3, :3].T + W[:3, 3]
    return Q[:, 0], Q[:, 2], ['nose', 'main', 'main']
