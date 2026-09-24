"""Audit of the Google-screenshot registrations (tools/sat/work/reg.json) against NAIP (task (c)).

NAIP 2024 is the reference: naip_faa_check.py shows it agrees with the FAA runway-end coordinates to 0.3 m
(2-D, runway side stripes) and <= 0.9 m along-track (threshold bars), in the geo.js world frame.

Control points
  * named FAA points: the 8 runway ends, the 4 displaced thresholds (FAA end + published displacement,
    js/geo.js RWY_ENDS.disp) and the 4 runway-centreline intersections, placed at FAA + the measured NAIP-FAA shift;
  * automatic points: in every 250 m cell of the paved airside area (SFO Museum runway/taxiway polygons, the
    inferred apron of data/sfo_details.json and data/sfo_pavement.json; >= 75 % of the 48 m template paved;
    buildings + 10 m excluded), the NAIP location whose 48 m neighbourhood has the strongest 2-D gradient
    structure (min. eigenvalue of the structure tensor; aircraft-sized bright blobs removed first) - i.e. ground
    markings with corners (taxiway centreline junctions, hold bars, lead-in lines, pad edges).  Labelled with the
    SFO Museum feature that contains them.
Measurement: match.py (48 m templates, 32 m on close-ups >= 3 px/m; masked NCC of gradient images, screenshot resampled through its registration; building
footprints +10 m and aircraft-sized bright blobs masked).  A match is accepted when NCC >= 0.40, NCC minus the best
NCC > max(3 m, 2.5 px) away >= 0.08, the peak is not on the search border, and the grey-level NCC agrees within
max(2 m, 1.5 px).  Residual r = position given by the registration - NAIP position (x east, z south, metres).
Per image: all accepted control points (named + a dense grid at 1.5 x template spacing), robust statistics, and a
robust similarity fit r(w) = a + B (w - w_c) whose inverse gives a NAIP-corrected registration (reg_naip.json -
suggested only; tools/sat/work/reg.json is NOT modified).
Also: the expected error of each surveyed stand (data/sfo_stands.json) from the residual field of the image it was
measured on (tools/sat/stand_defs.py 'img', including the manual shifts applied there).

Outputs refs/cache/naip/{control_points.json, reg_audit.json, reg_naip.json, reg_audit_qa_<img>.jpg}
usage: python3 tools/imagery/reg_audit.py [--year 2024] [--only name,name]
"""
import argparse, json, math, os, sys, time, importlib.util
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from screens import REG, load, sim_of, rectify, Sim, SAT
from match import match_point, building_mask, sample_bmask, bright_blobs

FT = 0.3048
DISP_FT = {'28R': 300, '28L': 300, '1L': 640, '1R': 560}    # js/geo.js RWY_ENDS.disp (FAA/AirNav, not re-verified here)


def st_dirs():
    h1, h2 = math.radians(117.83), math.radians(27.83)     # js/geo.js airport grid headings (CLAUDE.md)
    return np.array([math.sin(h1), -math.cos(h1)]), np.array([math.sin(h2), -math.cos(h2)])


def faa_points(shift):
    P = {}
    ends = {k: np.array(world_geojs(*v), float) for k, v in RWY_ENDS.items()}
    other = {a: b for p in RWY_PAIRS for a, b in (p, p[::-1])}
    for k, w in ends.items():
        P[f'RWY {k} end'] = dict(faa=w.tolist(), kind='runway end (threshold bar / EMAS edge)')
    for k, d in DISP_FT.items():
        v = ends[other[k]] - ends[k]; v /= np.linalg.norm(v)
        P[f'RWY {k} displaced thr'] = dict(faa=(ends[k] + v * d * FT).tolist(), kind=f'displaced threshold bar ({d} ft)')
    def inter(a1, a2, b1, b2):
        p, r = ends[a1], ends[a2] - ends[a1]; q, s = ends[b1], ends[b2] - ends[b1]
        t = np.cross(q - p, s) / np.cross(r, s); return p + r * t
    for a, b in [(('1L', '19R'), ('10L', '28R')), (('1L', '19R'), ('10R', '28L')), (('1R', '19L'), ('10L', '28R')), (('1R', '19L'), ('10R', '28L'))]:
        P[f'X {a[0]}/{b[0]}'] = dict(faa=inter(*a, *b).tolist(), kind='runway centreline intersection')
    for k, v in P.items(): v['naip'] = (np.array(v['faa']) + shift).tolist()
    return P


def auto_points(S, cell=250.0, half=24.0):
    D = json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))
    res = 1.0
    x0, z0, x1, z1 = -2600.0, -2350.0, 2200.0, 1700.0
    W, H = int((x1 - x0) / res), int((z1 - z0) / res)
    air = np.zeros((H, W), np.uint8); lab = np.zeros((H, W), np.int32); names = ['']
    fill = lambda M, ring, v: cv2.fillPoly(M, [np.round((np.array(ring) - [x0, z0]) / res).astype(np.int32)], v)
    for cat in ('runways', 'taxiways'):
        for f in D[cat]:
            names.append(f['name'])
            for poly in f['polys']:
                fill(air, poly[0], 1); fill(lab, poly[0], len(names) - 1)
    DD = json.load(open(os.path.join(ROOT, 'data', 'sfo_details.json')))
    PV = json.load(open(os.path.join(ROOT, 'data', 'sfo_pavement.json')))
    for poly in DD['apron'] + PV['polys']:
        fill(air, poly[0], 1)
        for hole in poly[1:]: fill(air, hole, 0)
    # pavement only: the whole 48 m template should be mostly pavement (no grass/soil - it changes with season)
    air = (cv2.boxFilter(air.astype(np.float32), -1, (int(2 * half / res),) * 2) > 0.75) & (air > 0)
    xc = x0 + (np.arange(W) + 0.5) * res; zc = z0 + (np.arange(H) + 0.5) * res
    X, Z = np.meshgrid(xc, zc)
    G = S(X, Z)
    bm = sample_bmask(X, Z); blobs = bright_blobs(G, res)
    gx = cv2.Sobel(G, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(G, cv2.CV_32F, 0, 1, ksize=3)
    kill = bm | blobs | (G == 0)
    gx[kill] = 0; gy[kill] = 0
    k = int(2 * half / res)
    Sxx = cv2.boxFilter(gx * gx, -1, (k, k)); Syy = cv2.boxFilter(gy * gy, -1, (k, k)); Sxy = cv2.boxFilter(gx * gy, -1, (k, k))
    lam = 0.5 * (Sxx + Syy - np.sqrt((Sxx - Syy) ** 2 + 4 * Sxy ** 2))
    valid = (air > 0) & ~cv2.dilate(kill.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    valid &= cv2.boxFilter((~kill).astype(np.float32), -1, (k, k)) > 0.8
    lam[~valid] = 0
    thr = np.percentile(lam[valid], 60)
    pts = []
    bas = [(b['name'], np.mean(np.array(b['polys'][0][0]), 0)) for b in D['boardingAreas']]
    for cz in np.arange(z0, z1, cell):
        for cx in np.arange(x0, x1, cell):
            c0, r0 = int((cx - x0) / res), int((cz - z0) / res)
            sub = lam[r0:r0 + int(cell / res), c0:c0 + int(cell / res)]
            if sub.size == 0 or sub.max() < thr: continue
            i, j = np.unravel_index(np.argmax(sub), sub.shape)
            px, pz = float(xc[c0 + j]), float(zc[r0 + i])
            li = lab[r0 + i, c0 + j]
            if li: label = names[li]
            else:
                bn, bc = min(bas, key=lambda b: np.hypot(b[1][0] - px, b[1][1] - pz))
                label = 'apron near ' + bn if np.hypot(bc[0] - px, bc[1] - pz) < 450 else 'paved area (apron/service, not an SFO Museum taxiway)'
            pts.append(dict(naip=[px, pz], kind='auto: 2-D marking texture', label=label, lam=float(sub.max())))
    return pts


def accept(rg, rr):
    if rg is None: return False, 'no match'
    tol = max(2.0, 1.5 * rg['res'])
    if rg['edge']: return False, 'peak on border'
    if rg['ncc'] < 0.40: return False, f"ncc {rg['ncc']:.2f}"
    if rg['ncc'] - rg['second'] < 0.08: return False, f"ambiguous ({rg['ncc']:.2f}/{rg['second']:.2f})"
    if rr is not None and np.hypot(*(np.array(rg['resid']) - rr['resid'])) > tol: return False, 'grad/grey disagree'
    return True, 'ok'


def template_half(sim):
    # close-ups (>= 3 px/m, views ~200-360 m wide) are mostly roofs/aircraft: smaller 32 m templates find more ground
    return 16.0 if sim.s >= 3.0 else max(24.0, 30.0 / sim.s)


def measure(S, img, mask, sim, P):
    half = template_half(sim); search = 15.0 if sim.s > 0.5 else 30.0
    mu = 0.4 if half < 20 else 0.5
    rg = match_point(S, img, mask, sim, P, half=half, search=search, mode='grad', min_used=mu)
    rr = match_point(S, img, mask, sim, P, half=half, search=search, mode='gray', min_used=mu) if rg else None
    ok, why = accept(rg, rr)
    return rg, ok, why


def robust_fit(Wp, Rr, wc):
    """r = a + B (w - wc), B = [[k, -t], [t, k]]; IRLS with a hard 3-sigma(MAD) cut. Returns a, k, t, inliers."""
    a = np.median(Rr, 0); k = t = 0.0; inl = np.ones(len(Rr), bool)
    for _ in range(8):
        d = Wp - wc
        pred = a + np.c_[k * d[:, 0] - t * d[:, 1], t * d[:, 0] + k * d[:, 1]]
        e = np.hypot(*(Rr - pred).T)
        sig = max(0.5, 1.4826 * np.median(e))
        inl = e < max(1.5, 3 * sig)
        if inl.sum() < 3: break
        if inl.sum() >= 6 and np.ptp(d[inl], 0).max() > 60:
            M = np.zeros((2 * inl.sum(), 4)); y = np.zeros(2 * inl.sum())
            di = d[inl]; ri = Rr[inl]
            M[0::2] = np.c_[np.ones(len(di)), np.zeros(len(di)), di[:, 0], -di[:, 1]]
            M[1::2] = np.c_[np.zeros(len(di)), np.ones(len(di)), di[:, 1], di[:, 0]]
            y[0::2] = ri[:, 0]; y[1::2] = ri[:, 1]
            sol, *_ = np.linalg.lstsq(M, y, rcond=None); a = sol[:2]; k, t = sol[2], sol[3]
        else:
            a = np.median(Rr[inl], 0); k = t = 0.0
    d = Wp - wc
    pred = a + np.c_[k * d[:, 0] - t * d[:, 1], t * d[:, 0] + k * d[:, 1]]
    return a, k, t, inl, np.hypot(*(Rr - pred).T)


def corrected_sim(sim, a, k, t, wc):
    """reg maps world->px: q = A w + c.  True position w_true = w_reg - r(w_reg), r = a + B (w - wc)."""
    B = np.array([[k, -t], [t, k]])
    a0 = a - B @ wc                      # r = a0 + B w
    Ap = sim.A @ np.linalg.inv(np.eye(2) - B)
    tp = sim.t + Ap @ a0
    s = math.sqrt(abs(np.linalg.det(Ap))); th = math.degrees(math.atan2(Ap[1, 0], Ap[0, 0]))
    return dict(s=s, th=th, tx=float(tp[0]), ty=float(tp[1]))


def stands_by_image():
    spec = importlib.util.spec_from_file_location('stand_defs_ro', os.path.join(SAT, 'stand_defs.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    img = {}
    for s_ in m.STANDS:
        nm = s_['name'] if isinstance(s_['name'], str) else s_['name'][0]
        img[nm] = s_.get('img')
    return img


def qa_sheet(S, name, img, mask, sim, rows, path, n=8):
    """side-by-side NAIP | screenshot (as registered) | screenshot corrected by the measured residual."""
    tiles = []
    for r in rows[:n]:
        P = np.array(r['naip']); res = 0.25 if sim.s > 2 else 0.5; hw = 30.0
        c = np.arange(-hw, hw, res) + res / 2; X, Z = np.meshgrid(P[0] + c, P[1] + c)
        N = S(X, Z); T0, _ = rectify(img, mask, sim, X, Z)
        T1, _ = rectify(img, mask, sim, X + r['resid'][0], Z + r['resid'][1])
        row = np.hstack([N, T0, T1]).clip(0, 255).astype(np.uint8)
        row = cv2.cvtColor(row, cv2.COLOR_GRAY2BGR); w = N.shape[1]
        for q in range(3): cv2.drawMarker(row, (q * w + w // 2, w // 2), (0, 0, 255), cv2.MARKER_CROSS, 16, 1)
        cv2.putText(row, f"{r['id']} r=({r['resid'][0]:+.1f},{r['resid'][1]:+.1f}) ncc {r['ncc']:.2f}", (4, 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        tiles.append(cv2.resize(row, (720, 240)))
    if tiles: cv2.imwrite(path, np.vstack(tiles), [cv2.IMWRITE_JPEG_QUALITY, 85])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--year', default='2024'); ap.add_argument('--only', default='')
    a = ap.parse_args()
    S = NaipSampler(a.year)
    fc = json.load(open(os.path.join(CACHE, f'naip_faa_check_{a.year}.json')))
    sh = np.array([fc['shift_naip_minus_faa_world']['dx_east_m'], fc['shift_naip_minus_faa_world']['dz_south_m']])
    named = faa_points(sh)
    auto = auto_points(S)
    cps = [dict(id=k, **v) for k, v in named.items()] + [dict(id=f'A{i:02d}', **p) for i, p in enumerate(auto)]
    json.dump(cps, open(os.path.join(CACHE, 'control_points.json'), 'w'), indent=1)
    print(f'{len(named)} FAA-derived + {len(auto)} automatic control points')
    names = [n for n in REG if (not a.only or n in a.only.split(','))]
    out = dict(year=a.year, naip_minus_faa=sh.tolist(), images={})
    corr = {}
    for name in names:
        t0 = time.time()
        img, mask = load(name); sim = sim_of(name)
        ys, xs = np.nonzero(mask[::10, ::10]); Wv = sim.inv(np.stack([xs * 10, ys * 10], 1).astype(float))
        wc = Wv.mean(0)
        half = template_half(sim)
        # control points in view
        cp_rows = []
        for cp in cps:
            P = np.array(cp['naip'])
            q = sim.fwd(P[None])[0]
            if not (0 <= q[0] < 1290 and 0 <= q[1] < 2796) or mask[int(q[1]), int(q[0])] == 0: continue
            rg, ok, why = measure(S, img, mask, sim, P)
            row = dict(id=cp['id'], kind=cp['kind'], label=cp.get('label', cp['id']), naip=cp['naip'], ok=ok, why=why)
            if rg: row.update(resid=rg['resid'], ncc=rg['ncc'], second=rg['second'], res=rg['res'])
            if 'faa' in cp and rg: row['resid_vs_faa'] = (np.array(rg['resid']) + (np.array(cp['naip']) - np.array(cp['faa']))).tolist()
            cp_rows.append(row)
        # dense grid
        step = 1.5 * half
        gx = np.arange(Wv[:, 0].min(), Wv[:, 0].max(), step); gz = np.arange(Wv[:, 1].min(), Wv[:, 1].max(), step)
        dense = []
        for x in gx:
            for z in gz:
                rg, ok, why = measure(S, img, mask, sim, (x, z))
                if ok: dense.append(dict(w=[float(x), float(z)], resid=rg['resid'], ncc=rg['ncc']))
        allp = [(r['naip'], r['resid']) for r in cp_rows if r['ok']] + [(d['w'], d['resid']) for d in dense]
        res_img = dict(s=sim.s, m_per_px=1 / sim.s, th=sim.th, view_centre=wc.tolist(), control_points=cp_rows,
                       n_cp_in_view=len(cp_rows), n_cp_ok=sum(r['ok'] for r in cp_rows), n_dense_ok=len(dense), dense=dense)
        if len(allp) >= 3:
            Wp = np.array([p for p, _ in allp]); Rr = np.array([r for _, r in allp])
            mag = np.hypot(*Rr.T)
            av, k, t, inl, e = robust_fit(Wp, Rr, wc)
            res_img.update(n=len(allp), median=np.median(Rr, 0).tolist(), mean=Rr.mean(0).tolist(),
                           rms=float(np.sqrt((mag ** 2).mean())), median_abs=float(np.median(mag)), p90=float(np.percentile(mag, 90)),
                           max=float(mag.max()),
                           fit=dict(a=av.tolist(), scale_ppm=k * 1e6, rot_deg=math.degrees(t), n_inliers=int(inl.sum()),
                                    rms_after=float(np.sqrt((e[inl] ** 2).mean())), p90_after=float(np.percentile(e[inl], 90))))
            corr[name] = dict(**corrected_sim(sim, av, k, t, wc), note=f'NAIP {a.year}-corrected (reg_audit.py): '
                              f'translation {av.round(2).tolist()} m at view centre, scale {k * 1e6:+.0f} ppm, rotation {math.degrees(t):+.3f} deg')
            print(f"{name} {1 / sim.s:.2f} m/px: cps {res_img['n_cp_ok']}/{len(cp_rows)}, dense {len(dense)}; residual median "
                  f"({res_img['median'][0]:+.2f},{res_img['median'][1]:+.2f}) m, |r| median {res_img['median_abs']:.2f} p90 {res_img['p90']:.2f}; "
                  f"fit: a=({av[0]:+.2f},{av[1]:+.2f}) scale {k * 1e6:+.0f} ppm rot {math.degrees(t):+.3f} deg, rms after {res_img['fit']['rms_after']:.2f} m "
                  f"[{time.time() - t0:.0f} s]")
            qa_sheet(S, name, img, mask, sim, [r for r in cp_rows if r['ok']] + [dict(id='g', naip=d['w'], **d) for d in dense][:4],
                     os.path.join(CACHE, f'reg_audit_qa_{name}.jpg'))
        else:
            print(f'{name}: too few matches ({len(allp)})')
        out['images'][name] = res_img
    # stand error estimates
    simg = stands_by_image(); ds_, dt_ = st_dirs()
    manual = {'c235f3b8': 0.6 * ds_ + 2.3 * dt_}     # tools/sat/stand_defs.py: E-pier stands shifted (+0.6 s, +2.3 t)
    stands = json.load(open(os.path.join(ROOT, 'data', 'sfo_stands.json')))['stands']
    se = []
    for s_ in stands:
        im = simg.get(s_['name']); R = out['images'].get(im)
        if not R or 'fit' not in R: continue
        f = R['fit']; w = np.array(s_['nose']); d = w - np.array(R['view_centre'])
        k, t = f['scale_ppm'] * 1e-6, math.radians(f['rot_deg'])
        r = np.array(f['a']) + np.array([k * d[0] - t * d[1], t * d[0] + k * d[1]]) + manual.get(im, 0)
        se.append(dict(stand=s_['name'], img=im, src=s_.get('src'), err=r.tolist(), err_m=float(np.hypot(*r))))
    out['stand_error_estimates'] = se
    json.dump(out, open(os.path.join(CACHE, 'reg_audit.json'), 'w'), indent=1)
    json.dump(corr, open(os.path.join(CACHE, 'reg_naip.json'), 'w'), indent=1)
    if se:
        e = np.array([s['err_m'] for s in se])
        print(f'stands: {len(se)} with an estimate; |err| median {np.median(e):.2f} m, p90 {np.percentile(e, 90):.2f} m, max {e.max():.2f} m')


if __name__ == '__main__':
    main()
