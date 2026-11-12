"""Runway and helicopter events at HWD from the pinned adsb.lol hours -> refs/cache/adsb/hwd_events.json (counts and rule
statistics only, default D1) + refs/cache/local/adsb/hwd_events_local.json (per-event rows with ICAO address and time,
gitignored, for Phase 2 development). New file (task G4); seeds the Phase 2 GA phase classifier (docs/PLAN.md section 4).

Input: refs/cache/local/adsb/hwd_tracks.pkl (extract.py). Heights, strips and corridors: derive.py.

Fixed-wing rules (every threshold is a named constant below; the output repeats them)
-------------------------------------------------------------------------------------
Per aircraft, fixes within R_FIELD of the ARP get a state:
  R  runway contact: on a runway strip, (ground flag or h <= H_CONTACT ft), and track within ALIGN_DEG of the runway axis
     (or gs < 5 kt / no track). Many GA ADS-B units have no weight-on-wheels input and report 'airborne' while rolling
     above some speed (observed: a C172 flagged airborne at 60 kt on the take-off roll and ground below ~30 kt on landing),
     so the ground flag alone cannot see touch-and-goes - h does.
  L  low on a runway corridor: airborne, |across| <= CORR_M, along in [-CORR_BEFORE, L + CORR_AFTER], h <= H_LOW, aligned.
  G  ground flag and not R (taxiing, parked, crossing a runway).
  A  any other airborne fix.
Runway episode = R fixes of one runway with gaps <= EP_GAP s and no G fix or A fix above H_BREAK ft in between.
Context of an episode (ctx): scanning away from it, skipping R fixes and airborne fixes at h <= H_BREAK ft (flare,
initial climb), the first G fix -> 'ground', the first airborne fix above H_BREAK -> 'air', within CTX_GAP s; only low
airborne fixes -> 'air' before the episode, 'air' after it if they climb >= 25 ft, else 'none'.
Ground = the ground flag, or 'ground by kinematics' (derive.py: airborne flag with h <= GK_H ft and gs < GK_GS kt).
  air  -> R -> air     touch_and_go; stop_and_go when the observed minimum gs < STOP_GS (obs) or the mean speed across
                        a polling hole inside the episode < STOP_HOLE_GS (inf: the stop itself was not observed).
                        touch_and_go is 'obs' with contact evidence (ground flag, ground by kinematics, >= 2 R fixes,
                        or min gs < DECEL_RATIO x the approach gs), 'inf' on a single R fix without it
  air  -> R -> ground  full_stop_landing (obs)
  ground -> R -> air   takeoff (obs)
  none -> R -> air     takeoff (inf: taxi-out unobserved)
  ground -> R -> none  takeoff (inf) when the last gs >= LIFT_GS, else runway_ground_move
  air  -> R -> none    full_stop_landing (inf) when the last gs < EXIT_GS, else landing_unresolved
  none -> R -> ground  full_stop_landing (inf) when the first gs >= LIFT_GS, else runway_ground_move
  ground -> R -> ground runway_ground_move (back-taxi, crossing at an angle within ALIGN_DEG, aborted take-off)
  none -> R -> none    unresolved
Hidden transitions (no R fix observed; the roll fell into a polling hole):
  G -> L/A within HID_GAP s, the G fix within HID_NEAR m of a runway axis, the air fix h <= HID_H ft and gs >= PASS_GS
  kt, no runway episode within CTX_GAP s: takeoff (inf); L/A -> G likewise: full_stop_landing (inf)
100-ft altitude transponders (derive.alt_quantum): R uses h <= H_CONTACT_COARSE, and a touch_and_go needs a ground flag,
ground by kinematics or the deceleration to be 'obs'.
Low passes: runs of L fixes (one runway, gaps <= EP_GAP s) with no R episode within PASS_ISO s and no hidden transition,
at least PASS_MIN_N fixes, minimum h <= H_PASS ft at gs >= PASS_GS kt, followed by a climb (a later fix >= 50 ft above
the minimum, or the next fix is A):
  low_approach_go_around (obs) when the aircraft is seen descending into its lowest point and climbing out of it within
  one polling burst (an earlier fix of that burst >= 25 ft higher and a later one >= 50 ft higher; h = 3-point median);
  otherwise the lowest point may lie in the polling hole before / after that burst:
  touch_and_go (inf) when the mean speed across that hole is < SLOW_RATIO x the slower of the speeds on either side (a
  straight pass averages at least the slower end speed: it slowed down where it could have touched) and the lowest
  observed h <= 100 ft;
  low_pass_unresolved otherwise (T&G or low approach cannot be told apart).
Runway end: from the direction of motion (circular mean track of the moving fixes; hwd_frame.rwy_axis headings 119.9 /
299.9 deg true). Event time: the first R fix (takeoff: the last), or the lowest L fix.

Helicopters (ICAO type in common.HELI_TYPES or emitter category A7): states G (ground flag), H (airborne, h <= HELI_H ft,
gs <= HELI_GS kt, within HELI_R m), A. lift_off = G -> H/A, touch_down = H/A -> G (gaps <= HID_GAP s), placed by the G
fix (OSM helipad / apron / runway / taxiway ... derive.Places); hover_taxi = runs of H fixes (gaps <= EP_GAP s) moving
>= HOVER_MIN_M; low_transit = a visit (fixes <= HELI_R m, separated by > 30 min from other visits) with H/A fixes below
HELI_H but no G fix.

After tower hours: event time outside 07:00-21:00 local (NASR ATC_BASE; PST = UTC-8 for the whole recording).
usage: python3 -I hwd3d/tools/adsb/events.py
"""
import json, math, os, sys
from collections import Counter, defaultdict
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C                                              # noqa: E402
import derive as DV                                             # noqa: E402

F = C.F
# Basis of the thresholds (Phase 1 review, 2026-11-12): none comes from a standard. All are chosen by me for HWD from
# typical GA speeds / heights and the recorder's ~46 s polling hole (common.py), and checked only by the consistency
# counts in the output (quality: TT / LL pairs ~0, circuit intervals); sensitivity not tested. One line each:
H_CONTACT = 30.0          # ft AGL: chosen; above the +-25 ft altitude quantum of 25-ft transponders, below a flare
H_CONTACT_COARSE = 80.0   # ft: 100-ft altitude transponders (derive.alt_quantum); chosen, below one quantum + noise
H_LOW = 400.0             # ft AGL: chosen; below circuit height (TPA 600 / 800 ft AGL, NASR) on final / climb-out
H_BREAK = 150.0           # ft AGL: chosen; flare / initial climb band that does not end a runway episode
H_PASS = 300.0            # ft AGL: chosen; a low approach / go-around goes lower than this
EP_GAP = 100.0            # s: chosen; about two polling holes
CTX_GAP = 150.0           # s: chosen; about three polling holes
STOP_GS = 15.0            # kt: chosen; slower than a touch-and-go roll, i.e. the aircraft stopped or nearly
STOP_HOLE_GS = 25.0       # kt: chosen; mean speed across a hole that a continuous roll would not go below
LIFT_GS = 40.0            # kt: chosen; about a C172 rotation speed (POH Vr ~55 KIAS, from memory, not re-read)
EXIT_GS = 30.0            # kt: chosen; a landing roll slower than this is exiting
HID_GAP = 100.0           # s: chosen; about two polling holes
HID_NEAR = 150.0          # m: chosen; within the runway strip and its connectors
HID_H = 800.0             # ft AGL: chosen; below the 10L/28R pattern altitude (800 ft AGL, NASR)
PASS_ISO = 60.0           # s: chosen; about one polling hole
SLOW_RATIO = 0.9          # chosen; 10 % below the slower end speed
PASS_MIN_N = 3            # fixes: chosen; minimum to see a descent and a climb
DECEL_RATIO = 0.85        # chosen; a 15 % deceleration = wheels on the ground
PASS_GS = 35.0            # kt: chosen; below this an aircraft over the runway is not flying a pass
HOLE_S = DV.HOLE_S
HELI_H = 150.0            # ft AGL: chosen; hover-taxi / air-taxi height band
HELI_GS = 40.0            # kt: chosen; hover-taxi / air-taxi speed band
HELI_R = 2000.0           # m: chosen; about the aerodrome plus the helicopter approach paths
HOVER_MIN_M = 30.0        # m: chosen; longer than the fix noise of a hovering helicopter
KT = 1852 / 3600.0

RULES = {k: v for k, v in dict(globals()).items() if k.isupper() and isinstance(v, (int, float)) and k not in ('KT',)}
RULES.update(STRIP_M=DV.STRIP_M, CORR_M=DV.CORR_M, CORR_BEFORE=DV.CORR_BEFORE, CORR_AFTER=DV.CORR_AFTER,
             ALIGN_DEG=DV.ALIGN_DEG, R_FIELD=DV.R_FIELD, GK_H=DV.GK_H, GK_GS=DV.GK_GS)


def states(a):
    """per-fix state (see the header); ground = derive 'gk' (ground flag, or airborne flag but h <= GK_H and gs < GK_GS)."""
    n = len(a['t']); st = np.full(n, 'A', dtype=object); rid = np.full(n, '', dtype=object)
    hc = H_CONTACT if a['q'] == 25 else H_CONTACT_COARSE
    for i in range(n):
        if a['r'][i] > DV.R_FIELD: st[i] = '-'; continue
        s = a['strip'][i]; tr = a['mtrk'][i]; gs = a['gs'][i]
        if s and (a['gk'][i] or (not np.isnan(a['h'][i]) and a['h'][i] <= hc)):
            if (not np.isnan(gs) and gs < 5) or np.isnan(tr) or DV.aligned(tr, s):
                st[i] = 'R'; rid[i] = s; continue
        if a['gk'][i]: st[i] = 'G'; continue
        c = a['corr'][i]
        if c and not np.isnan(a['h'][i]) and a['h'][i] <= H_LOW and not np.isnan(tr) and DV.aligned(tr, c):
            st[i] = 'L'; rid[i] = c
    return st, rid


def direction(a, idx, rid):
    m = [i for i in idx if not np.isnan(a['mtrk'][i]) and (np.isnan(a['gs'][i]) or a['gs'][i] >= 5)]
    if m:
        h, _ = C.circ_mean([a['mtrk'][i] for i in m], [max(a['gs'][i] if not np.isnan(a['gs'][i]) else 10, 1) for i in m])
        return DV.end_of(rid, h)
    if len(idx) >= 2:
        i0, i1 = idx[0], idx[-1]; dx = a['x'][i1] - a['x'][i0]; dz = a['z'][i1] - a['z'][i0]
        if math.hypot(dx, dz) > 20: return DV.end_of(rid, F.vec_hdg(dx, dz))
    return None


def hole_speeds(a, idx):
    """[(i, j, mean speed kt)] across polling holes between consecutive fixes of idx."""
    out = []
    for i, j in zip(idx, idx[1:]):
        dt_ = a['t'][j] - a['t'][i]
        if dt_ > HOLE_S:
            out.append((i, j, math.hypot(a['x'][j] - a['x'][i], a['z'][j] - a['z'][i]) / dt_ / KT))
    return out


def ctx(a, st, i, step):
    """context of an episode boundary i: scan away from it (step -1 / +1), skipping R fixes and low airborne fixes
    (h <= H_BREAK: flare, initial climb), to the first decisive fix within CTX_GAP s: G -> 'ground', an airborne fix above
    H_BREAK -> 'air'. When only low airborne fixes are found: before the episode -> 'air' (on final); after it -> 'air'
    when they climb (h rises >= 25 ft), else 'none'. -> (context, index of the deciding fix or None)."""
    n = len(st); j = i + step; low = []
    while 0 <= j < n and st[j] != '-' and abs(a['t'][j] - a['t'][i]) <= CTX_GAP:
        if st[j] == 'G': return 'ground', j
        if st[j] in ('A', 'L'):
            if np.isnan(a['h'][j]) or a['h'][j] > H_BREAK: return 'air', j
            low.append(j)
        j += step
    if low:
        if step < 0: return 'air', low[0]
        hh = [a['h'][k] for k in low]
        if max(hh) >= hh[0] + 25: return 'air', low[-1]
    return 'none', None


def fixed_wing_events(hx, a):
    st, rid = states(a); n = len(st); ev = []; used_R = set()
    # ---- runway episodes
    R_idx = [i for i in range(n) if st[i] == 'R']
    eps = []; cur = []
    for i in R_idx:
        if cur:
            p = cur[-1]; br = rid[i] != rid[p] or a['t'][i] - a['t'][p] > EP_GAP
            if not br:
                for k in range(p + 1, i):
                    if st[k] == 'G' or (st[k] in ('A', '-') and (np.isnan(a['h'][k]) or a['h'][k] > H_BREAK)): br = True; break
            if br: eps.append(cur); cur = []
        cur.append(i)
    if cur: eps.append(cur)
    for e in eps:
        r = rid[e[0]]
        pv, ip = ctx(a, st, e[0], -1); nx, inx = ctx(a, st, e[-1], +1)
        gs = [a['gs'][i] for i in e if not np.isnan(a['gs'][i])]
        gmin = min(gs) if gs else None; g0 = gs[0] if gs else None; g1 = gs[-1] if gs else None
        hs = hole_speeds(a, e); hmin = min([h[2] for h in hs]) if hs else None
        typ = None; src = 'obs'; ev_ = []
        # contact evidence: ground flag / ground by kinematics / several fixes at h <= H_CONTACT / deceleration
        n_g = sum(1 for i in e if a['g'][i]); n_k = sum(1 for i in e if a['gk'][i] and not a['g'][i])
        g_app = a['gs'][ip] if ip is not None and not np.isnan(a['gs'][ip]) else None
        decel = gmin is not None and g_app is not None and pv == 'air' and gmin < DECEL_RATIO * g_app
        contact = ['ground flag'] if n_g else []
        if n_k: contact.append('ground by kinematics')
        if len(e) >= 2 and a['q'] == 25: contact.append('%d fixes at h <= %.0f ft' % (len(e), H_CONTACT))
        if decel: contact.append('gs %.0f -> %.0f kt' % (g_app, gmin))
        if pv == 'air' and nx == 'air':
            if gmin is not None and gmin < STOP_GS: typ = 'stop_and_go'; ev_.append('min gs %.0f kt observed' % gmin)
            elif hmin is not None and hmin < STOP_HOLE_GS: typ = 'stop_and_go'; src = 'inf'; ev_.append('mean %.0f kt across a hole' % hmin)
            else:
                typ = 'touch_and_go'
                if not contact:
                    src = 'inf'; ev_.append('single fix at h <= %.0f ft' % H_CONTACT if a['q'] == 25 else
                                            '100-ft altitude unit, no ground flag or deceleration')
        elif pv == 'air' and nx == 'ground': typ = 'full_stop_landing'
        elif pv == 'ground' and nx == 'air': typ = 'takeoff'
        elif pv == 'none' and nx == 'air': typ = 'takeoff'; src = 'inf'; ev_.append('taxi-out unobserved')
        elif pv == 'ground' and nx == 'none':
            if g1 is not None and g1 >= LIFT_GS: typ = 'takeoff'; src = 'inf'; ev_.append('lift-off unobserved')
            else: typ = 'runway_ground_move'
        elif pv == 'air' and nx == 'none':
            if g1 is not None and g1 < EXIT_GS: typ = 'full_stop_landing'; src = 'inf'; ev_.append('exit unobserved')
            else: typ = 'landing_unresolved'
        elif pv == 'none' and nx == 'ground':
            if g0 is not None and g0 >= LIFT_GS: typ = 'full_stop_landing'; src = 'inf'; ev_.append('approach unobserved')
            else: typ = 'runway_ground_move'
        elif pv == 'ground' and nx == 'ground': typ = 'runway_ground_move'
        else: typ = 'unresolved'
        ctx_idx = [k for k in (ip, inx) if k is not None]
        d = direction(a, e, r)
        if d is None:   # stationary episode: use the context fix that moves
            for k in ctx_idx:
                if not np.isnan(a['mtrk'][k]): d = DV.end_of(r, a['mtrk'][k]); break
        t_ev = a['t'][e[-1]] if typ == 'takeoff' else a['t'][e[0]]
        ev.append(dict(hex=hx, type=typ, src=src, evidence=ev_, contact=contact, rwy=r, end=d, t=float(t_ev), t0=float(a['t'][e[0]]),
                       t1=float(a['t'][e[-1]]), n=len(e), gs_min=gmin, gs_first=g0, gs_last=g1, hole_min_kt=hmin,
                       ctx=[pv, nx], ctx_gap=[None if ip is None else float(a['t'][e[0]] - a['t'][ip]),
                                              None if inx is None else float(a['t'][inx] - a['t'][e[-1]])],
                       x=float(a['x'][e[0]]), z=float(a['z'][e[0]]), via='runway_episode'))
        used_R.update(e)
        if ip is not None: used_R.add(ip)
        if inx is not None: used_R.add(inx)
    # ---- hidden transitions G <-> air with no R in between
    tR = [(a['t'][e[0]], a['t'][e[-1]]) for e in eps]
    hid = set()
    for i in range(n - 1):
        j = i + 1
        if st[i] == '-' or st[j] == '-' or a['t'][j] - a['t'][i] > HID_GAP: continue
        if st[i] == 'G' and st[j] in ('L', 'A') and not np.isnan(a['h'][j]) and a['h'][j] <= HID_H:
            g = i; air = j; typ = 'takeoff'
        elif st[i] in ('L', 'A') and st[j] == 'G' and not np.isnan(a['h'][i]) and a['h'][i] <= HID_H:
            g = j; air = i; typ = 'full_stop_landing'
        else: continue
        if abs(a['ac_near'][g]) > HID_NEAR: continue
        if np.isnan(a['gs'][air]) or a['gs'][air] < PASS_GS: continue          # flying speed (ground-flag flicker)
        if any(s_ - CTX_GAP <= a['t'][j] and a['t'][i] <= e_ + CTX_GAP for s_, e_ in tR): continue   # an episode's context
        r = rid[air] if st[air] == 'L' else a['near'][g]
        d = DV.end_of(r, a['mtrk'][air]) if not np.isnan(a['mtrk'][air]) else None
        ev.append(dict(hex=hx, type=typ, src='inf', evidence=['roll unobserved: G->air in %.0f s' % (a['t'][j] - a['t'][i])],
                       rwy=r, end=d, t=float(a['t'][air]), t0=float(a['t'][i]), t1=float(a['t'][j]), n=0,
                       gs_min=None, gs_first=None, gs_last=None, hole_min_kt=None, ctx=[st[i], st[j]], ctx_gap=None,
                       x=float(a['x'][g]), z=float(a['z'][g]), via='hidden_transition', h_air=float(a['h'][air])))
        hid.update((i, j))
    # ---- low passes
    L_idx = [i for i in range(n) if st[i] == 'L']
    runs = []; cur = []
    for i in L_idx:
        if cur:
            p = cur[-1]; br = rid[i] != rid[p] or a['t'][i] - a['t'][p] > EP_GAP or any(st[k] in ('G', 'R', '-') for k in range(p + 1, i))
            if br: runs.append(cur); cur = []
        cur.append(i)
    if cur: runs.append(cur)
    for rn in runs:
        t0, t1 = a['t'][rn[0]], a['t'][rn[-1]]
        if any(s - PASS_ISO <= t1 and t0 <= e_ + PASS_ISO for s, e_ in tR): continue
        if any(k in hid for k in rn) or (rn[0] - 1 in hid) or (rn[-1] + 1 in hid): continue
        hh = np.array([a['h'][i] for i in rn]); k = int(np.argmin(hh)); imin = rn[k]
        if hh[k] > H_PASS or len(rn) < PASS_MIN_N: continue
        if np.isnan(a['gs'][imin]) or a['gs'][imin] < PASS_GS: continue
        later = hh[k + 1:]
        nxt = rn[-1] + 1
        climbs = (len(later) and later.max() >= hh[k] + 50) or (nxt < n and st[nxt] == 'A' and a['t'][nxt] - t1 <= CTX_GAP)
        if not climbs: continue
        r = rid[imin]; d = direction(a, rn, r)
        # burst of the lowest fix: observed descending into it and climbing out of it?
        b0 = k
        while b0 > 0 and a['t'][rn[b0]] - a['t'][rn[b0 - 1]] <= HOLE_S: b0 -= 1
        b1 = k
        while b1 + 1 < len(rn) and a['t'][rn[b1 + 1]] - a['t'][rn[b1]] <= HOLE_S: b1 += 1
        seen_down = any(hh[q] >= hh[k] + 25 for q in range(b0, k))
        seen_up = any(hh[q] >= hh[k] + 50 for q in range(k + 1, b1 + 1))
        typ = 'low_approach_go_around'; src = 'obs'; evd = []; slow = None
        if not (seen_down and seen_up):
            src = 'inf'; typ = 'low_pass_unresolved'
            nb = []   # the hole(s) the lowest point may hide: before the burst (not seen descending) / after it
            if not seen_down:
                ib = rn[b0] - 1
                if ib >= 0 and st[ib] != '-': nb.append((ib, rn[b0]))
            if not seen_up:
                ia = rn[b1] + 1
                if ia < n and st[ia] != '-': nb.append((rn[b1], ia))
            for i, j in nb:
                dt_ = a['t'][j] - a['t'][i]
                if dt_ <= HOLE_S or dt_ > EP_GAP: continue
                v = math.hypot(a['x'][j] - a['x'][i], a['z'][j] - a['z'][i]) / dt_ / KT
                gi, gj = a['gs'][i], a['gs'][j]
                ref = np.nanmin([gi, gj]) if not (np.isnan(gi) and np.isnan(gj)) else np.nan
                r_ = v / ref if ref and not np.isnan(ref) else None
                evd.append('hole of %.0f s next to the lowest observed fix' % dt_)
                if r_ is not None and (slow is None or r_ < slow): slow = r_
            if slow is not None and slow < SLOW_RATIO and hh[k] <= 100:
                typ = 'touch_and_go'; evd.append('mean speed across the hole %.0f%% of the slower side' % (100 * slow))
            if not evd: evd.append('lowest point at the end of the observed track')
        al_dir = None
        if d:
            al, _ = F.rwy_along_across(d, a['x'][imin], a['z'][imin]); al_dir = float(al - F.thr_disp_m(d))
        ev.append(dict(hex=hx, type=typ, src=src, evidence=evd, rwy=r, end=d, t=float(a['t'][imin]), t0=float(t0), t1=float(t1),
                       n=len(rn), h_min=float(hh[k]), h_src=str(a['h_src'][imin]), al_thr_m=al_dir, slow_ratio=slow,
                       gs_at_min=None if np.isnan(a['gs'][imin]) else float(a['gs'][imin]),
                       x=float(a['x'][imin]), z=float(a['z'][imin]), via='low_pass'))
    return ev


def heli_events(hx, a, places):
    n = len(a['t']); st = np.full(n, 'A', dtype=object)
    for i in range(n):
        if a['r'][i] > HELI_R: st[i] = '-'
        elif a['g'][i]: st[i] = 'G'
        elif not np.isnan(a['h'][i]) and a['h'][i] <= HELI_H and not np.isnan(a['gs'][i]) and a['gs'][i] <= HELI_GS: st[i] = 'H'
    ev = []
    for i in range(n - 1):
        j = i + 1
        if '-' in (st[i], st[j]) or a['t'][j] - a['t'][i] > HID_GAP: continue
        if st[i] == 'G' and st[j] in ('H', 'A'): typ, g = 'lift_off', i
        elif st[i] in ('H', 'A') and st[j] == 'G': typ, g = 'touch_down', j
        else: continue
        lab, det = places.label(a['x'][g], a['z'][g])
        ev.append(dict(hex=hx, type=typ, src='obs' if a['t'][j] - a['t'][i] <= HOLE_S else 'inf', place=lab, place_id=det,
                       t=float(a['t'][g]), x=float(a['x'][g]), z=float(a['z'][g]), cls='helicopter'))
    # hover-taxi runs
    cur = []
    def flush(cur):
        if len(cur) < 2: return
        d = math.hypot(a['x'][cur[-1]] - a['x'][cur[0]], a['z'][cur[-1]] - a['z'][cur[0]])
        path = sum(math.hypot(a['x'][q] - a['x'][p], a['z'][q] - a['z'][p]) for p, q in zip(cur, cur[1:]))
        if path < HOVER_MIN_M: return
        l0 = places.label(a['x'][cur[0]], a['z'][cur[0]]); l1 = places.label(a['x'][cur[-1]], a['z'][cur[-1]])
        ev.append(dict(hex=hx, type='hover_taxi', src='obs', t=float(a['t'][cur[0]]), dur_s=float(a['t'][cur[-1]] - a['t'][cur[0]]),
                       path_m=round(path, 1), disp_m=round(d, 1), gs_med=float(np.nanmedian([a['gs'][q] for q in cur])),
                       h_med=float(np.nanmedian([a['h'][q] for q in cur])), place=l0[0], place_end=l1[0],
                       x=float(a['x'][cur[0]]), z=float(a['z'][cur[0]]), cls='helicopter'))
    for i in range(n):
        if st[i] == 'H' and (not cur or a['t'][i] - a['t'][cur[-1]] <= EP_GAP): cur.append(i)
        else:
            flush(cur); cur = [i] if st[i] == 'H' else []
    flush(cur)
    # visits without ground contact
    near = [i for i in range(n) if st[i] != '-']
    vis = []; cur = []
    for i in near:
        if cur and a['t'][i] - a['t'][cur[-1]] > 1800: vis.append(cur); cur = []
        cur.append(i)
    if cur: vis.append(cur)
    for v in vis:
        if any(st[i] == 'G' for i in v): continue
        hh = [a['h'][i] for i in v if not np.isnan(a['h'][i])]
        if hh and min(hh) <= HELI_H:
            k = v[int(np.nanargmin([a['h'][i] if not np.isnan(a['h'][i]) else 1e9 for i in v]))]
            ev.append(dict(hex=hx, type='low_transit', src='obs', t=float(a['t'][k]), h_min=float(min(hh)),
                           x=float(a['x'][k]), z=float(a['z'][k]), cls='helicopter'))
    return ev


def run(D=None):
    D = D or DV.load(); T = D['tracks']
    cal = DV.calibrate(T)
    places = DV.Places()
    evs = []
    for hx, a in T.items():
        if np.hypot(a['x'], a['z']).min() > DV.R_FIELD: continue
        a['hex'] = hx
        DV.derive(a, cal)
        E = heli_events(hx, a, places) if C.is_heli(a) else fixed_wing_events(hx, a)
        for e in E:
            e.setdefault('cls', a['cls']); e.setdefault('type_icao', a['type']); e.setdefault('cat', a['cat'])
        evs += E
    for e in evs:
        e['tower'] = 'open' if C.tower_open(e['t']) else 'closed'
        e['local_h'] = C.local_dt(e['t']).hour
    return evs, cal, D, places


def hist(v, edges):
    v = [x for x in v if x is not None and not (isinstance(x, float) and math.isnan(x))]
    h, _ = np.histogram(v, bins=edges)
    return {'edges': list(edges), 'counts': h.tolist(), 'n': len(v),
            'median': None if not v else round(float(np.median(v)), 1)}


def summarise(evs, cal, D):
    FW = ('takeoff', 'full_stop_landing', 'touch_and_go', 'stop_and_go', 'low_approach_go_around')
    out = {}
    for typ in sorted(set(e['type'] for e in evs)):
        E = [e for e in evs if e['type'] == typ]
        rec = {'total': len(E), 'by_src': dict(Counter(e['src'] for e in E)),
               'by_runway_end': dict(sorted(Counter(e.get('end') or '?' for e in E).items())) if typ in FW or typ in (
                   'landing_unresolved', 'runway_ground_move', 'unresolved', 'low_pass_unresolved') else None,
               'tower_closed': sum(e['tower'] == 'closed' for e in E),
               'tower_closed_by_runway_end': dict(Counter(e.get('end') or e.get('place') or '?' for e in E if e['tower'] == 'closed')),
               'by_class': dict(Counter(e['cls'] for e in E).most_common()),
               'by_local_hour': [sum(e['local_h'] == h for e in E) for h in range(24)],
               'aircraft': len(set(e['hex'] for e in E)),
               'via': dict(Counter(e.get('via', 'heli') for e in E))}
        if typ in ('lift_off', 'touch_down', 'hover_taxi'):
            rec['by_place'] = dict(Counter(str(e.get('place')) for e in E).most_common())
        if typ in ('lift_off', 'touch_down'):
            rec['by_place_detail'] = dict(Counter('%s %s' % (e.get('place'), e.get('place_id')) for e in E
                                                  if e.get('place') in ('apron', 'hangar', 'helipad')).most_common())
        if typ in ('lift_off', 'touch_down'):
            rec['by_helipad_osm_id'] = dict(Counter(str(e.get('place_id')) for e in E if e.get('place') == 'helipad').most_common())
        out[typ] = rec
    # rule statistics (seed the Phase 2 thresholds)
    stats = {}
    for typ in ('touch_and_go', 'stop_and_go', 'full_stop_landing', 'takeoff'):
        E = [e for e in evs if e['type'] == typ and e.get('via') == 'runway_episode']
        stats[typ] = {'gs_min_kt': hist([e['gs_min'] for e in E], [0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 80, 200]),
                      'gs_last_kt': hist([e['gs_last'] for e in E], [0, 5, 10, 20, 30, 40, 50, 60, 80, 200]),
                      'episode_s': hist([e['t1'] - e['t0'] for e in E], [0, 1, 5, 10, 20, 30, 60, 120, 300, 900, 3600])}
    E = [e for e in evs if e.get('via') == 'low_pass']
    stats['low_pass'] = {'h_min_ft': hist([e['h_min'] for e in E], [-100, 0, 25, 50, 75, 100, 150, 200, 250, 300]),
                         'al_thr_m': hist([e['al_thr_m'] for e in E], [-2000, -1000, -500, -250, 0, 250, 500, 1000, 1500, 2000, 3000]),
                         'slow_ratio': hist([e.get('slow_ratio') for e in E], [0, 0.4, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 2.0])}
    E = [e for e in evs if e.get('via') == 'hidden_transition']
    stats['hidden_transition'] = {'h_air_ft': hist([e.get('h_air') for e in E], [-100, 0, 50, 100, 200, 300, 400, 600, 800])}
    E = [e for e in evs if e['type'] == 'hover_taxi']
    stats['hover_taxi'] = {'dur_s': hist([e['dur_s'] for e in E], [0, 5, 10, 20, 40, 60, 120, 300, 900]),
                           'gs_med_kt': hist([e['gs_med'] for e in E], [0, 2, 5, 10, 15, 20, 30, 40]),
                           'path_m': hist([e['path_m'] for e in E], [0, 30, 60, 100, 200, 400, 800, 2000])}
    # daily movements per tower status (takeoff + landing-type events)
    mv = ('takeoff', 'full_stop_landing', 'touch_and_go', 'stop_and_go', 'low_approach_go_around')
    days = defaultdict(Counter)
    for e in evs:
        if e['type'] in mv: days[C.local_dt(e['t']).strftime('%Y-%m-%d')][e['type']] += 1
    # consistency of each aircraft's event sequence (quality check of the rules, not an input to them)
    code = {'takeoff': 'T', 'full_stop_landing': 'L', 'touch_and_go': 'G', 'stop_and_go': 'S', 'low_approach_go_around': 'P',
            'low_pass_unresolved': 'U', 'landing_unresolved': 'l'}
    by = defaultdict(list)
    for e in evs:
        if e['type'] in code: by[e['hex']].append(e)
    pairs = Counter(); iv = []
    for E in by.values():
        E.sort(key=lambda e: e['t'])
        for p, q in zip(E, E[1:]):
            if q['t'] - p['t'] < 3600: pairs[code[p['type']] + code[q['type']]] += 1
            if code[p['type']] in 'TGSPU' and code[q['type']] in 'GSPUL' and q['t'] - p['t'] < 1800: iv.append(q['t'] - p['t'])
    quality = {'codes': code, 'consecutive_pairs_within_1h': dict(pairs.most_common()),
               'note': 'TT = two take-offs with no arrival event between (a missed landing), LL = two full-stop landings with '
                       'no take-off between (a missed take-off); both should be ~0',
               'circuit_interval_s': hist(iv, [0, 60, 120, 180, 240, 300, 360, 420, 480, 600, 900, 1800]),
               'takeoffs_minus_full_stop_landings': sum(e['type'] == 'takeoff' for e in evs) - sum(e['type'] == 'full_stop_landing' for e in evs)}
    return out, stats, {k: dict(v) for k, v in sorted(days.items())}, quality


def main():
    evs, cal, D, places = run()
    counts, stats, days, quality = summarise(evs, cal, D)
    polls = D['polls']
    out = {
        'what': 'HWD runway and helicopter events classified from the pinned adsb.lol hours (tools/adsb/events.py): counts by '
                'event type, runway end, tower status, aircraft class and local hour, plus the distributions the rules cut '
                'on. Aggregates only (default D1): no ICAO address, registration, callsign or time stamp.',
        'licence': C.LICENCE, 'attribution': C.ATTRIBUTION,
        'source': 'sfo3d/refs/cache/rec_pack/adsblol_<hour>.jsonl.xz @ %s' % C.PACK_COMMIT, 'hours': C.HOURS,
        'frame': F.FRAME_ID,
        'sampling': D['pattern'] | {'hours_ok_polls': None},
        'local_time': 'PST = UTC-8 (whole recording after the 1 Nov 2026 DST end); tower 07:00-21:00 local (FAA NASR ATC_BASE)',
        'calibration': {k: v for k, v in cal.items() if k not in ('baro_t', 'baro_v', 'per_ac')} | {
            'what': 'h = alt_geom - GEOM_OFF - NASR runway surface (ft); baro fallback with a +-%.0f h running median offset' % DV.BARO_WIN_H},
        'rules': RULES, 'rules_text': __doc__.split('Fixed-wing rules')[1].split('usage:')[0].strip(),
        'counts': counts, 'rule_stats': stats, 'movements_by_local_day': days, 'quality': quality,
        'helipads_osm': {str(i): [round(p.centroid.x, 1), round(p.centroid.y, 1)] for i, p in places.helipads},
        'aircraft_considered': sum(1 for a in D['tracks'].values() if 'r' in a),
    }
    n = C.write_json(os.path.join(C.OUT_DIR, 'hwd_events.json'), out)
    loc = [dict(e, hex=e['hex']) for e in evs]
    C.write_json(os.path.join(C.LOCAL, 'hwd_events_local.json'), {'note': 'LOCAL ONLY (gitignored): holds ICAO addresses', 'events': loc}, compact=True)
    print('events', len(evs), '->', n, 'bytes')
    for k, v in counts.items():
        print('%-24s %4d  src %s  ends %s  closed %d  cls %s' % (k, v['total'], v['by_src'], v['by_runway_end'], v['tower_closed'], v['by_class']))
    print('calibration GEOM_OFF %.1f ft (n %d), baro global %.1f' % (cal['GEOM_OFF'], cal['n_geom'], cal['baro_global']))


if __name__ == '__main__':
    main()
