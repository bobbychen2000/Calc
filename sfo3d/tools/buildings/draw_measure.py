"""Measured deviations of the drawn footprints / roof outlines against NAIP 2024 (for the overlay sheets and
docs/drawings/buildings/deviations.json, numbers only).

Why not a plain overlay: NAIP is orthorectified to a bare-earth DEM, so every roof is imaged displaced away from the
camera nadir by h x (P - N) / (H - h) (relief displacement; several metres at SFO). A drawn roof edge is therefore
compared with NAIP at its PREDICTED IMAGED position, and a footprint (ground-contact) edge only where it can be seen:

  kind 'roof'  roof edge of known height h on a face that does NOT face the nadir (or runs along the lean):
               predicted imaged edge = drawn edge + lean(P) * h; NAIP searched +-6 m across it.
  kind 'base'  facade base on a face that FACES the nadir (the facade is seen between base and roof edge): drawn edge
               at h = 0, searched within +-min(4, max(1.5, 0.45 |lean| h)) m so the roof edge (displaced inward by
               |lean| h) stays outside the window.
  kind 'line'  a lean-free roof-edge LINE measured by the research (domestic piers): checked at its predicted imaged
               position; NOT independent (derived from the same imagery) - a consistency check of the lean model.

Lean (relief per metre of height, world x, z) per building, with its source:
  frame    NAIP 2024 frame model on the five FAA DOF poles (draw_data.lean_frame; ITB research V.2): ITB hall and its
           west facade base, BA-A, the tower and its base building (BA-G: reported for comparison only);
  dom      the domestic two-epoch 2024 lean per pier (draw_data.dom_lean; east assumed for the along-face part);
  north    0.30-0.33 m/m east measured at the CAC and LTP Garage 1 by shadow (spec_landside cac_height, ltp1_scan);
  kmodel   the ITB k(x) east model inside its calibrated range (BA-G, as its spec height; Garages A / G) or
           extrapolated (central garage) [inf];
  fitted   the Superbay's 2-D roof shift (-7.0, -7.5) m over the DOF 135 ft - fitted to this imagery, so its roof
           offsets are circular (reported, not a check).
Offsets o are signed along the edge's OUTWARD normal: + = NAIP edge outside the predicted / drawn edge.
Edge method: draw_lib.measure_edge (median gradient profile; 'weak' when the peak is < 1.25 x the next one > 2 m away).
"""
import json
import math
import os

import numpy as np

import draw_data as D
from draw_lib import measure_edge, outward_normals, unit, DOCS, ring_area

MIN_LEN = 12.0
CHUNK = 40.0


def _chunks(p, q):
    p, q = np.asarray(p, float), np.asarray(q, float); L = float(np.hypot(*(q - p)))
    n = max(1, int(math.ceil(L / CHUNK)))
    return [(p + (q - p) * i / n, p + (q - p) * (i + 1) / n) for i in range(n)]


def measure_ring(name, ring, h, lean, lean_src, h_src, kinds=('roof', 'base'), hfun=None):
    """lean: per-metre relief vector (x, z) or a function P -> per-metre vector."""
    ring = np.asarray(ring, float); out = []
    nrm = outward_normals(ring)
    for i in range(len(ring)):
        p, q = ring[i], ring[(i + 1) % len(ring)]
        if np.hypot(*(q - p)) < MIN_LEN: continue
        n = nrm[i]
        for a, b in _chunks(p, q):
            mid = (a + b) / 2
            lv = lean(mid) if callable(lean) else np.asarray(lean, float)
            hh = hfun(a, b) if hfun else h
            ld = unit(lv) if np.hypot(*lv) > 0 else np.array([1.0, 0.0])
            facing = float(np.dot(n, ld))
            if facing < -0.2 and 'base' in kinds:
                half = min(4.0, max(1.5, 0.45 * float(np.hypot(*lv)) * (hh or 10.0)))
                r = measure_edge(a, b, n, (0, 0), half=half); kind, shift = 'base', np.zeros(2)
            elif hh is not None and 'roof' in kinds and facing >= -0.2:
                shift = lv * hh; r = measure_edge(a, b, n, shift, half=6.0); kind = 'roof'
            else:
                continue
            if r is None: continue
            out.append(dict(building=name, kind=kind, p0=[round(float(x), 2) for x in a], p1=[round(float(x), 2) for x in b],
                            n=[round(float(x), 3) for x in n], h=None if kind == 'base' else (round(float(hh), 2) if hh is not None else None),
                            shift=[round(float(x), 2) for x in shift], lean=lean_src, h_src=h_src, **r,
                            ok=bool(r['ratio'] >= 1.25 and r['strength'] >= 3.0)))
    return out


def measure_line(name, line, h, lean, lean_src, h_src, n_hint):
    a, b = (np.asarray(x, float) for x in line)
    d = unit(b - a); n = np.array([d[1], -d[0]])
    if np.dot(n, n_hint) < 0: n = -n
    shift = np.asarray(lean, float) * h
    r = measure_edge(a, b, n, shift, half=6.0)
    if r is None: return []
    return [dict(building=name, kind='line', p0=[round(float(x), 2) for x in a], p1=[round(float(x), 2) for x in b],
                 n=[round(float(x), 3) for x in n], h=round(float(h), 2), shift=[round(float(x), 2) for x in shift],
                 lean=lean_src, h_src=h_src, **r, ok=bool(r['ratio'] >= 1.25 and r['strength'] >= 3.0))]


def per_m_frame(P, h):
    return D.lean_frame(P, h) / h


def run():
    E = []
    # ------------------------------------------------------------------ tower base building + cab disc
    atc = D.sfom('Air Traffic Control Tower')[0][0]
    h_ibf = D.TV['h_ibf_roof']['value']
    E += measure_ring('Tower base building (IBF)', atc, h_ibf, lambda P: per_m_frame(P, h_ibf), 'frame',
                      'h_ibf_roof 14.2 [inf] (12.7-16.5)')
    cab = np.array(D.TV['position_cab_roof_centre']['value'], float)
    imaged = np.array([-700.85, 322.40])  # spec position_cab_roof_centre note: NAIP 2024 disc centre (obs)
    cabchk = {}
    preds = []
    for fam, H in (('family 1 (rim 67.36 m)', 67.36), ('family 2 (rim 64.0 m)', 64.0)):
        pred = cab + D.lean_frame(cab, H); preds.append(pred)
        cabchk[fam] = dict(predicted_imaged=[round(float(x), 2) for x in pred], observed_imaged=imaged.tolist(),
                           delta=[round(float(x), 2) for x in imaged - pred])
    fm = D.IV['naip.k_model']['alt_frame_model']
    lean_m = float(np.hypot(*D.lean_frame(cab, 66.0)))
    cabchk['_reading'] = dict(
        prediction_difference_m=round(float(np.hypot(*(preds[0] - preds[1]))), 2),
        input_uncertainty=dict(cab_x_m=5.0, cab_x_tag='inf (OSM / Google traced on lean-affected imagery; spec: not independent)',
                               frame_lean_sd_m=round(lean_m * fm['H_minus_h_sd'] / fm['H_minus_h'], 1),
                               frame_note=f"H - h sd {fm['H_minus_h_sd']} m of {fm['H_minus_h']} m on the ~{lean_m:.0f} m lean"),
        verdict='INCONCLUSIVE: the two families predict imaged centres closer together than the input uncertainty; the k(x) model '
                'gives the same pair (-701.8 / -703.7), so a second relief model does not separate them.')
    # ------------------------------------------------------------------ ITB hall roof (eave height varies along u)
    F = D.itb_frame(); C = F['corners']
    ring = [C['NW'], C['NE'], C['SE'], C['SW']]

    def h_itb(a, b):
        m = (np.asarray(a) + np.asarray(b)) / 2 - F['c']; u = float(np.dot(m, F['ax']))
        return float(D.itb_eave_h(min(abs(u), 126.0)))
    E += measure_ring('ITB main hall roof', ring, None, lambda P: per_m_frame(P, 38.0), 'frame',
                      'roof.profile (eave, obs; DOF-anchored)', kinds=('roof',), hfun=h_itb)
    # ITB west facade (glass wall) base: the NAIP straight facade-base line (itb_naip_measurements eave_profile, imaged
    # v -43.5) is the wall base on the elevated departures curb (level 3, photos); drawn wall = that line moved back by the
    # relief of h = L3; checked at its predicted imaged position (same imagery: a consistency check of the placement)
    W = D.itb_west_wall()
    a, b = D.itb_uv(F, -100.0, W['v']), D.itb_uv(F, 100.0, W['v'])
    for p, q in _chunks(a, b):
        mid = (p + q) / 2; sh = D.lean_frame(mid, W['h_base']); n = -F['v']
        r = measure_edge(p, q, n, sh, half=3.0)
        if r is None: continue
        E.append(dict(building='ITB west facade (glass-wall base on L3)', kind='base', p0=[round(float(x), 2) for x in p],
                      p1=[round(float(x), 2) for x in q], n=[round(float(x), 3) for x in n], h=round(W['h_base'], 2),
                      shift=[round(float(x), 2) for x in sh], lean='frame', h_src=f"level3.floor {W['h_base']} [inf]", **r,
                      ok=bool(r['ratio'] >= 1.25 and r['strength'] >= 3.0)))
    # Boarding Areas A (frame model) and G (k(x) east-only, as the spec's verified height; the frame model is reported
    # for comparison only: under it G's roof would hide its own shadow - spec ba_g.height_roof verification)
    h = D.IV['ba_a.height_roof']['value']
    for r in D.outer_rings('Boarding Area A', 'boardingAreas'):
        E += measure_ring('Boarding Area A', r, h, lambda P, h=h: per_m_frame(P, h), 'frame', f'ba_a.height_roof {h} [obs]')
    h = D.IV['ba_g.height_roof']['value']
    for r in D.outer_rings('Boarding Area G', 'boardingAreas'):
        E += measure_ring('Boarding Area G', r, h, lambda P: np.array([D.k_x_model(float(P[0])), 0.0]),
                          'kmodel: east k(x) per edge (as spec ba_g.height_roof)', f'ba_g.height_roof {h} [obs]')
        E += measure_ring('Boarding Area G (frame model, comparison only)', r, h, lambda P, h=h: per_m_frame(P, h), 'frame',
                          f'ba_g.height_roof {h} [obs]')
    # ------------------------------------------------------------------ domestic piers and halls
    for L, nm in (('B', 'Boarding Area B'), ('C', 'Boarding Area C'), ('D', 'Boarding Area D'), ('E', 'Boarding Area E'),
                  ('F', 'Boarding Area F')):
        lv, h, src = D.dom_lean(L)
        for r in D.outer_rings(nm, 'boardingAreas'):
            E += measure_ring(nm, r, h, lv, 'dom: ' + src, f'{D.DOM_PIER[L][0]} {h} [obs]')
    for nm in ('Harvey Milk Terminal 1', 'Terminal 2', 'Terminal 3'):
        for r in D.outer_rings(nm, 'terminals'):
            E += measure_ring(nm, r, None, np.array([0.45, 0.0]), 'east (dom range 0.33-0.58) [inf]', 'no height', kinds=('base',))
    for sid, rid, L in (('bab.roof_edges', 'ba_b_south', 'B'), ('bad.roof_edges', 'ba_d_head', 'D'), ('baf.roof_edges', 'ba_f_ne_arm', 'F')):
        te = D.dom_true_edges(sid, rid); lv, h, src = D.dom_lean(L)
        R = D.dom_faces(rid)
        if not te: continue
        nh = D.hdg_vec(R.get('n_hdg', 117.8)) if 'n_hdg' in R else D.hdg_vec(117.8)
        E += measure_line(f'Boarding Area {L} (lean-free roof edge, ESE)', te['n'], h, lv, 'dom: ' + src, sid, nh)
        E += measure_line(f'Boarding Area {L} (lean-free roof edge, WNW)', te['m'], h, lv, 'dom: ' + src, sid, -nh)
    # ------------------------------------------------------------------ landside
    north = np.array([0.315, 0.0])
    LS = [('Central Parking Garage', 24.69, np.array([D.k_x_model(-938.2), 0.0]), 'kmodel extrapolated [inf]', 'cg_height 81 ft [pub, definition unknown]'),
          ('Garage A', None, np.array([D.k_x_model(-1421.7), 0.0]), 'kmodel [obs]', 'no roof-deck height (base only)'),
          ('Garage G', None, np.array([D.k_x_model(-1485.7), 0.0]), 'kmodel [obs]', 'no roof-deck height (base only)'),
          ('Grand Hyatt Hotel', None, np.array([D.k_x_model(-1639.3), 0.0]), 'kmodel extrapolated [inf]', 'height unknown (base only)'),
          ('Consolidated Administration Campus', 18.3, np.array([0.30, 0.0]), 'north: 0.30 m/m east (cac_height) [obs]', 'cac 4 x 15 ft [pub/inf]'),
          ('Long-Term Parking Garage 1', 16.5, np.array([0.33, 0.0]), 'north: 0.33 m/m east (ltp1_scan) [obs]', 'ltp1_parapet_obs 16.5 [obs]'),
          ('Long-Term Parking Garage 2', None, north, 'north: 0.30-0.33 east [inf]', 'roof 60 ft [inf] (base only)'),
          ('Rental Car Center', 16.46, north, 'north: 0.30-0.33 east [inf]', 'rcc_dof 54 ft parapet [pub]'),
          ('Super Bay Hangar Building', 41.15, np.array([-7.0, -7.5]) / 41.15, 'fitted (sb_roof_shift) - circular', 'sb_height_dof 135 ft [pub]')]
    for nm, h, lv, lsrc, hsrc in LS:
        for r in D.outer_rings(nm, 'structures'):
            E += measure_ring(nm, r, h, lv, lsrc, hsrc)
    # ------------------------------------------------------------------ summary
    summ = {}
    for e in E:
        k = (e['building'], e['kind'])
        summ.setdefault(k, []).append(e)
    S = []
    for (b, k), es in summ.items():
        ok = [e for e in es if e['ok']]
        o = np.array([e['o'] for e in ok]) if ok else np.array([])
        w = np.array([e['L'] for e in ok]) if ok else np.array([])
        S.append(dict(building=b, kind=k, edges=len(es), ok=len(ok), lean=es[0]['lean'], h_src=es[0]['h_src'],
                      median_o=round(float(np.median(o)), 2) if len(o) else None,
                      median_abs_o=round(float(np.median(np.abs(o))), 2) if len(o) else None,
                      within_1m=round(float(np.sum(w[np.abs(o) <= 1.0]) / np.sum(w)), 2) if len(o) else None,
                      within_2_5m=round(float(np.sum(w[np.abs(o) <= 2.5]) / np.sum(w)), 2) if len(o) else None))
    out = dict(generated_by='tools/buildings/draw_measure.py (via draw.py)', imagery='NAIP 2024 (2024-05-20), refs/cache/naip/naip_2024_world_0.5m',
               method=__doc__.strip(), frame_model=dict(nadir=D.NADIR.tolist(), H_fly_m=round(D.H_FLY, 1)),
               tower_cab_check=cabchk, summary=sorted(S, key=lambda s: (s['building'], s['kind'])), edges=E)
    os.makedirs(DOCS, exist_ok=True)
    json.dump(out, open(os.path.join(DOCS, 'deviations.json'), 'w'), indent=1)
    return out


if __name__ == '__main__':
    o = run()
    for s in o['summary']:
        print(f"{s['building'][:44]:44s} {s['kind']:5s} {s['ok']:3d}/{s['edges']:3d}  med {s['median_o']}  |med| {s['median_abs_o']}  <=1m {s['within_1m']}  <=2.5m {s['within_2_5m']}")
    print(json.dumps(o['tower_cab_check'], indent=1))
