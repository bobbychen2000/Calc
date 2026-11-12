"""Derived per-fix quantities shared by the HWD ADS-B tools: height above the runway, runway strip / corridor membership,
motion track, 'ground by kinematics', OSM location labels. New file (task G4).

Height above the runway surface (h, ft)
---------------------------------------
ADS-B alt_baro is pressure altitude (29.92 inHg), so near the ground it is off by the QNH (measured here: rolling aircraft
report -128 .. -240 ft on a runway whose surface is 28-52 ft MSL, varying with the weather). alt_geom (GNSS; for DO-260B
1090 ES the height above the WGS 84 ellipsoid [from memory, not re-read]; readsb derives it from alt_baro + the
geometric-minus-baro difference) does not depend on QNH. calibrate() measures both offsets from the data itself:
fixed-wing aircraft rolling on a runway = airborne-flag fixes on the paved strip, ground speed CAL_GS kt, within 60 s of
a ground-flag fix of the same aircraft; offset = median of (altitude - NASR runway surface elevation at that point,
hwd_frame.rwy_surface_y). GEOM_OFF is one constant (the ellipsoid-geoid separation plus quantisation; GEOID18 N at
HWD is about -32 m [from memory, not checked]); the baro offset is a running median over +-BARO_WIN_H hours.
h = alt_geom - GEOM_OFF - surface elevation, or (no alt_geom) alt_baro - baro offset(t) - surface elevation; the
surface elevation is the nearest runway's NASR profile at the clamped along-track position. GEOM_OFF is replaced by the
aircraft's own median when it has >= PER_AC_N calibration fixes (unit biases of tens of ft exist). Resolution: 25 ft, or
100 ft for transponders whose pressure altitude comes in 100-ft steps (alt_quantum: 56 of the 217 aircraft with >= 20
airborne fixes within 3 km, measured 2026-11-12) - for those h is only good to about +-50 ft.

Runway geometry (hwd_frame.py, FAA NASR ends): strip = |across| <= half width + STRIP_M, along in [-30, L + 30] m.
Corridor (approach / climb-out) = |across| <= CORR_M, along in [-CORR_BEFORE, L + CORR_AFTER]. 10L/28R lies 152.6 m
left of 10R/28L (both runway axes from NASR; measured with hwd_frame.rwy_along_across), so CORR_M = 75 m keeps them apart.
"""
import math, os, pickle, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C                                              # noqa: E402

F = C.F
CAL_GS = (20.0, 50.0)      # kt: rolling (a C172 lifts off at ~50-55 KIAS; Cessna POH, from memory) [inferred]
BARO_WIN_H = 3.0
STRIP_M = 12.0             # m beyond the paved edge: GNSS EPU (NACp 10 < 10 m) + antenna offset [inferred]
CORR_M = 75.0
CORR_BEFORE = 2000.0       # m before the runway end: ~1 NM final, ~300-400 ft on a 3-4 deg path
CORR_AFTER = 1000.0
ALIGN_DEG = 30.0
R_FIELD = 6000.0           # m from the ARP: events are looked for inside this radius
HOLE_S = 8.0               # s: a gap > HOLE_S between fixes = a polling hole (bursts ~1.3 s apart, holes ~46 s)
GK_H = 30.0                # ft: 'ground by kinematics' - an airborne-flag fix with h <= GK_H and gs < GK_GS kt is on the
GK_H_COARSE = 80.0         # ft: the same for 100-ft altitude transponders (alt_quantum) [inferred]
PER_AC_N = 5               # calibration fixes needed for a per-aircraft GEOM offset (25-ft units only)
GK_GS = 35.0               # ground (units without a weight-on-wheels input; observed taxiing at 12 kt and holding at
                           # 0.7 kt with the airborne flag). Not applied to helicopters (hover). [inferred]

RIDS = ['%s/%s' % p for p in F.RWY_PAIRS]
_AX = {rid: F.rwy_axis(rid.split('/')[0]) for rid in RIDS}


def load():
    return pickle.load(open(C.TRACKS, 'rb'))


def rwy_frame(x, z):
    """-> dict rid -> (along, across) arrays (along from the 10x end)."""
    out = {}
    for rid in RIDS:
        A = _AX[rid]; px = x - A['origin'][0]; pz = z - A['origin'][1]
        out[rid] = (px * A['dir'][0] + pz * A['dir'][1], px * A['right'][0] + pz * A['right'][1])
    return out


def surface_ft(rid, along):
    a = rid.split('/')[0]; L = _AX[rid]['length']
    return np.array([F.rwy_surface_y(a, float(min(max(v, 0.0), L))) / F.FT for v in np.atleast_1d(along)])


def motion_track(a):
    """track (deg) per fix: the direction of the displacement to the neighbouring fixes (<= 15 s apart, >= 4 m moved),
    else the reported track (airborne) / true_heading (ground flag), else NaN. Displacement first: on the surface the
    reported 'track' can be stale (observed: a BE20 take-off roll at 46-91 kt reporting track 55.0 while true_heading and
    the displacement gave 300.9)."""
    t = a['t']; x = a['x']; z = a['z']; n = len(t)
    trk = np.where(a['g'] & ~np.isnan(a['hdg']), a['hdg'], a['trk']).astype(float)
    for i in range(n):
        for j0, j1 in ((i - 1, i + 1), (i - 1, i), (i, i + 1)):
            if 0 <= j0 < n and 0 <= j1 < n and j0 != j1 and t[j1] - t[j0] <= 15:
                dx = x[j1] - x[j0]; dz = z[j1] - z[j0]
                if math.hypot(dx, dz) >= 4: trk[i] = F.vec_hdg(dx, dz); break
    return trk


def alt_quantum(a):
    """25 or 100 ft: the pressure-altitude resolution of this transponder (100 when every airborne alt_baro within 3 km
    is a multiple of 100 ft - Gillham / 100-ft encoding; then alt_geom = alt_baro + GNSS delta is as coarse)."""
    al = a['alt'][~np.isnan(a['alt']) & (np.hypot(a['x'], a['z']) < 3000)]
    return 100 if len(al) >= 10 and np.all(np.mod(al, 100) == 0) else 25


def calibrate(T):
    rows = []
    for hx, a in T.items():
        if a['cls'] == 'helicopter' or not a['g'].any(): continue
        gt = a['t'][a['g']]
        R = rwy_frame(a['x'], a['z'])
        for i in np.where(~a['g'])[0]:
            gs = a['gs'][i]
            if np.isnan(a['alt'][i]) or np.isnan(gs) or not (CAL_GS[0] <= gs <= CAL_GS[1]): continue
            rid = None
            for r in RIDS:
                al, ac = R[r][0][i], R[r][1][i]
                if 0 <= al <= _AX[r]['length'] and abs(ac) <= C.RWY_HALF_W[r] + 10: rid = r
            if not rid: continue
            k = np.searchsorted(gt, a['t'][i]); near = min(abs(gt[j] - a['t'][i]) for j in (k - 1, k) if 0 <= j < len(gt))
            if near > 60: continue
            e = surface_ft(rid, R[rid][0][i])[0]
            rows.append((a['t'][i], a['alt'][i] - e, a['altg'][i] - e, hx))
    per = {}
    for hx in set(r[3] for r in rows):
        g = [r[2] for r in rows if r[3] == hx and not np.isnan(r[2])]
        if len(g) >= PER_AC_N and alt_quantum(T[hx]) == 25: per[hx] = float(np.median(g))
    R = np.array([r[:3] for r in rows], float)
    geom = R[~np.isnan(R[:, 2]), 2]
    cal = dict(n=int(len(R)), n_geom=int(len(geom)), gs_window_kt=list(CAL_GS),
               GEOM_OFF=float(np.median(geom)), geom_iqr=[float(np.percentile(geom, 25)), float(np.percentile(geom, 75))],
               baro_global=float(np.median(R[:, 1])), baro_iqr=[float(np.percentile(R[:, 1], 25)), float(np.percentile(R[:, 1], 75))],
               baro_t=R[:, 0].tolist(), baro_v=R[:, 1].tolist(), per_ac=per)
    po = np.array(list(per.values()))
    if len(po):
        cal['per_ac_n'] = len(po); cal['per_ac_minus_global_ft_pct'] = {p: round(float(np.percentile(po - cal['GEOM_OFF'], p)), 1) for p in (5, 25, 50, 75, 95)}
    return cal


def baro_off(cal, t):
    bt = np.asarray(cal['baro_t']); bv = np.asarray(cal['baro_v']); w = BARO_WIN_H * 3600
    out = np.empty(len(t))
    order = np.argsort(bt); bt = bt[order]; bv = bv[order]
    for k, tt in enumerate(t):
        i0 = np.searchsorted(bt, tt - w); i1 = np.searchsorted(bt, tt + w)
        out[k] = np.median(bv[i0:i1]) if i1 - i0 >= 5 else cal['baro_global']
    return out


def median3(t, h, g):
    """3-point running median of h within a polling burst (fixes <= HOLE_S apart), airborne fixes only: removes
    single-fix altitude glitches (observed: one alt_geom fix 75-100 ft off its neighbours 1 s apart)."""
    out = h.copy(); n = len(h)
    for i in range(n):
        if g[i] or np.isnan(h[i]): continue
        w = [h[i]]
        if i > 0 and not g[i - 1] and t[i] - t[i - 1] <= HOLE_S and not np.isnan(h[i - 1]): w.append(h[i - 1])
        if i + 1 < n and not g[i + 1] and t[i + 1] - t[i] <= HOLE_S and not np.isnan(h[i + 1]): w.append(h[i + 1])
        out[i] = float(np.median(w))
    return out


def derive(a, cal):
    """adds to track dict a: r, R (rwy frame), near (closest runway id by |across|), h (ft above the runway surface,
    0 on the ground flag; 3-point median within a burst, h_raw unfiltered), gk (ground flag or ground by kinematics), mtrk (motion track), strip (rid or ''), corr (rid or '')."""
    x, z = a['x'], a['z']
    a['r'] = np.hypot(x, z)
    R = rwy_frame(x, z); a['R'] = R
    acs = np.vstack([np.abs(R[rid][1]) for rid in RIDS])
    near_i = np.argmin(acs, axis=0)
    a['near'] = np.array(RIDS)[near_i]
    al_near = np.array([R[RIDS[k]][0][i] for i, k in enumerate(near_i)])
    ac_near = np.array([R[RIDS[k]][1][i] for i, k in enumerate(near_i)])
    a['al_near'] = al_near; a['ac_near'] = ac_near
    elev = np.array([surface_ft(RIDS[k], al_near[i])[0] for i, k in enumerate(near_i)])
    a['q'] = alt_quantum(a)
    hg = a['altg'] - cal['per_ac'].get(a.get('hex'), cal['GEOM_OFF']) - elev
    need = np.isnan(hg) & ~np.isnan(a['alt'])
    hb = np.full(len(x), np.nan)
    if need.any(): hb[need] = a['alt'][need] - baro_off(cal, a['t'][need]) - elev[need]
    h = np.where(np.isnan(hg), hb, hg); h[a['g']] = 0.0
    gk = a['g'].copy()
    if a['cls'] != 'helicopter':
        with np.errstate(invalid='ignore'):
            gk |= (~a['g']) & (h <= (GK_H if a['q'] == 25 else GK_H_COARSE)) & (a['gs'] < GK_GS)
    a['gk'] = gk
    a['h_raw'] = h.copy()
    h = median3(a['t'], h, a['g'])
    a['h'] = h; a['h_src'] = np.where(a['g'], 'gnd', np.where(~np.isnan(hg), 'geom', np.where(~np.isnan(hb), 'baro', '')))
    a['mtrk'] = motion_track(a)
    strip = np.full(len(x), '', dtype=object); corr = np.full(len(x), '', dtype=object)
    for rid in RIDS:
        al, ac = R[rid]; L = _AX[rid]['length']
        s = (al >= -30) & (al <= L + 30) & (np.abs(ac) <= C.RWY_HALF_W[rid] + STRIP_M)
        strip[s & (strip == '')] = rid
        c = (al >= -CORR_BEFORE) & (al <= L + CORR_AFTER) & (np.abs(ac) <= CORR_M)
        corr[c & (corr == '')] = rid
    a['strip'] = strip; a['corr'] = corr
    return a


def aligned(trk, rid, tol=ALIGN_DEG):
    """track within tol of the runway axis, either direction."""
    hd = _AX[rid]['hdg']
    d = np.abs((np.asarray(trk) - hd + 90) % 180 - 90)
    return d <= tol


def end_of(rid, trk):
    return C.rwy_end_for(rid, trk)


# ---------------------------------------------------------------------------------------------- OSM location labels
class Places:
    """OSM (refs/cache/osm/khwd_features.json, ODbL) geometry for location labels. Widths: runways = NASR width;
    taxiways TWY_HALF, taxilanes TL_HALF either side of the mapped centreline (OSM has no width tags here) [inferred]."""
    TWY_HALF = 10.0
    TL_HALF = 8.0

    def __init__(self):
        from shapely.geometry import LineString, Polygon, Point
        from shapely.ops import unary_union
        from shapely.prepared import prep
        self.Point = Point
        o = C.load_osm()['features']
        self.o = o
        poly = lambda f: Polygon(f['w']).buffer(0)
        self.aerodrome = poly(o['aerodrome'][0])
        rw = []
        for rid in RIDS:
            a, b = rid.split('/'); A = F.end_world(a); B = F.end_world(b)
            rw.append(LineString([A, B]).buffer(C.RWY_HALF_W[rid], cap_style=2))
        self.runway = unary_union(rw)
        self.taxiway = unary_union([LineString(f['w']).buffer(self.TWY_HALF) for f in o['taxiway'] if len(f['w']) > 1])
        self.taxilane = unary_union([LineString(f['w']).buffer(self.TL_HALF) for f in o['taxilane'] if len(f['w']) > 1])
        self.aprons = [((f['tags'].get('name') or f['tags'].get('ref') or 'apron %d' % f['osm']['id']), poly(f)) for f in o['apron']]
        self.hangars = [((f['tags'].get('name') or 'hangar %d' % f['osm']['id']), poly(f)) for f in o['hangar']]
        self.helipads = [(f['osm']['id'], poly(f)) for f in o['helipad']]
        self.holds = [(f['osm']['id'], f['w'][0]) for f in o['holding_position']]
        self.paved = unary_union([self.runway, self.taxiway, self.taxilane] + [p for _, p in self.aprons] +
                                 [p for _, p in self.hangars] + [p for _, p in self.helipads])
        self.paved_p = prep(self.paved)

    def label(self, x, z):
        """-> (label, detail): runway / helipad / hangar / apron (name) / taxiway / taxilane / off_osm_pavement
        (with the distance to the nearest mapped pavement)."""
        P = self.Point(x, z)
        if self.runway.contains(P): return 'runway', None
        for i, p in self.helipads:
            if p.buffer(5).contains(P): return 'helipad', i
        for n, p in self.hangars:
            if p.contains(P): return 'hangar', n
        for n, p in self.aprons:
            if p.contains(P): return 'apron', n
        if self.taxiway.contains(P): return 'taxiway', None
        if self.taxilane.contains(P): return 'taxilane', None
        return 'off_osm_pavement', round(self.paved.distance(P), 1)

    def near_hold(self, x, z, r=25.0):
        best = None
        for i, w in self.holds:
            d = math.hypot(x - w[0], z - w[1])
            if d <= r and (best is None or d < best[1]): best = (i, d)
        return best
