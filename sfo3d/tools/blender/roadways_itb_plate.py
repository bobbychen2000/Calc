"""ITB departures deck as one plate, measured on NAIP 2024 (integration review round 2, finding 1, critical): the roadway
deck in front of the International Terminal ran as two OSM ribbons (layer-2 ways 38853045 / 38853121, 8.4 m each) with a
3.5-m void between the ITB curb and the inner ribbon and a 7.4-m void between the ribbons. NAIP 2024 shows one deck from
the kerb across the inner roadway, island A and the bus roadway to island B (~34 m), and beyond it the light-concrete
outer roadway to the hedge line (~45 m out). This module measures them (numpy + OpenCV + shapely; no bpy) for
tools/blender/build_roadways.py, which builds the deck at the ITB L3 level as one surface and anchors the ways on it.

Frame: the ITB roof frame of manifest.json#itb.frame.roof_frame (u along heading 162.85, + towards Boarding Area A; v across,
+ ENE towards the hall). NAIP 2024 is resampled at 0.1-0.25 m with the frame-model relief of a point H_EDGE above grade
(tools/buildings/draw_data.lean_frame: nadir and flying height fitted on five FAA DOF poles, docs/research/buildings_itb.md
2.2 / V.2), H_EDGE = deck top + parapet: the deck edge and its barrier are then in their true plan position (the
reviewer's v -71 is the edge as imaged; relief-corrected it is ~4.5 m further out).

Measured [obs NAIP 2024, relief-corrected; +-0.5 m unless stated]:
  outer edge v_out(u)   per 1-m station: from the kerb outward, the last deck pixel before >= GAP_TOL of non-deck
                        (deck = smoothed brightness > DECK_L and not vegetation: G - (B+R)/2 < VEG_G): the hedge on the
                        straight, the dark gap where the outer roadway curves down at the ends; capped at the straight
                        section's median edge - 0.5 m (beyond it the ramps leave the plate: they stay OSM ribbons)
  straight section      the u range where v_out is within 1.5 m of that median (the full-width deck)
  bands (straight only) from the median cross-profile over the straight (crosswalk stations excluded): island A (bright
                        concrete plateau with a red kerb face, shelters), the red-painted kerb of island B and its
                        west gutter, the light-concrete outer roadway to the edge
Inferred: the deck is level at the ITB L3 deck top (11.35 m = spec_itb level3.floor 11.5 [inf] - 0.15 kerb) from the kerb
to the west edge of island B (the red-kerbed island); lane counts (OSM lanes as a minimum, the measured width / 3.6 m).
The outer light-concrete roadway beyond island B (OSM way 41015123, layer 1, 2 lanes) is a LOWER deck, not this one: in
OSM it runs under the anchored departures roadway's south leg (ways 38853121 / 38853045, layer 2) 20-30 m past the
straight - on this deck it would have to drop >= 5.8 m (deck + clearance) in that distance, a 19-25 % grade - and the
2.8-m band between island B's red kerb and its surface (dark 1-m line, bright line, dark line) reads as the step's barrier
and fascia seen at the 2024 lean (0.38 m per m to the east); NAIP 2020 / 2024 parallax could not separate the two levels
(the 2020 lean at this spot is not calibrated). The plate's measured outline (to the hedge line) is reported for it."""
import json, math, os, sys
import numpy as np
import shapely
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'buildings'))

DECK_L, VEG_G, DARK_L = 135.0, 5.0, 105.0   # smoothed NAIP brightness (mean BGR) / greenness G-(B+R)/2 [measured on the straight:
                                # deck 165-230; hedge 115-125 with greenness +10..+16; the shadowed gap where the outer roadway
                                # curves down at the south end < 100; cars, shelters, barrier shadows 50-150 but narrow across v]
GAP_L, GAP_W, GAP_LEN = 120.0, 1.6, 6.0    # structural gap: darker than GAP_L, >= GAP_W wide and >= GAP_LEN long [measured: the
                                # south-end gap 2-3 m wide, 30 m long, fragmented where it crosses the cap; island-B barrier
                                # shadow <= 1 m; dark cars <= 2 x 5 m]
VEG_RUN, DARK_RUN, GAP_TOL = 1.0, 2.0, 6.0  # m: the walk outward stops at this much vegetation, very dark (< DARK_L) or any
                                # non-deck in a row (a shelter or a bus across v is <= 4 m; the hedge >= 3 m)
RES = 0.25                      # m, resampling of the outline
PARAPET_H = 0.85                # build_roadways.PARAPET_H


def frame():
    man = json.load(open(os.path.join(ROOT, 'data', 'buildings3d', 'manifest.json')))
    rf = man['itb']['frame']['roof_frame']
    C = np.array(rf['centre_xz'], float); du = np.array(rf['u_axis_xz'], float); du /= np.linalg.norm(du)
    dv = np.array([du[1], -du[0]])      # + ENE (x east, z south)
    return C, du, dv


def naip():
    m = json.load(open(os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_world_0.5m.json')))
    im = np.load(os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_world_0.5m_bgr.npy'), mmap_mode='r')
    return m, im


def sample(U, V, h, C, du, dv, N=None, im=None):
    """NAIP 2024 (BGR float) at roof-frame points (U, V), relief-corrected for a point h above grade"""
    import cv2
    import draw_data as DD
    if N is None: N, im = naip()
    P = C[None, None] + U[..., None] * du + V[..., None] * dv
    if h: P = P + DD.lean_frame(P.reshape(-1, 2), h).reshape(P.shape)
    cx = ((P[..., 0] - N['x0']) / N['res'] - 0.5).astype(np.float32); cz = ((P[..., 1] - N['z0']) / N['res'] - 0.5).astype(np.float32)
    x0, z0 = int(cx.min()) - 2, int(cz.min()) - 2; x1, z1 = int(cx.max()) + 3, int(cz.max()) + 3
    sub = np.ascontiguousarray(im[z0:z1, x0:x1]).astype(np.float32)
    return cv2.remap(sub, cx - x0, cz - z0, cv2.INTER_LINEAR)


def uv_of(xz, C, du, dv):
    q = np.asarray(xz, float) - C
    return np.c_[q @ du, q @ dv]


def xz_of(uv, C, du, dv):
    uv = np.asarray(uv, float)
    return C[None] + uv[:, :1] * du[None] + uv[:, 1:2] * dv[None]


def kerb_from_asset(T_itb, curb_h, C, du, dv, G=3.0):
    """the curb sidewalk top of the ITB asset (LOD0 hall triangles facing up at the curb level): per 1-m u station the
    kerb face v (its smallest v) and the u range of the curb [asset geometry: itb_geom.hall_curb, KERB_V obs NAIP]"""
    T = T_itb
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    sel = (n[:, 1] > 0.95) & (np.abs(T[:, :, 1] - (G + curb_h)).max(1) < 0.06)
    if not sel.any(): return None
    P = T[sel][:, :, [0, 2]].reshape(-1, 2); uv = uv_of(P, C, du, dv)
    near = uv[:, 1] < -15.0   # the west curb (the hall is v > -26)
    uv = uv[near]
    if not len(uv): return None
    u0, u1 = float(uv[:, 0].min()), float(uv[:, 0].max())
    us = np.arange(math.ceil(u0), math.floor(u1) + 1)
    kv = np.array([uv[np.abs(uv[:, 0] - u) < 3.0, 1].min() if (np.abs(uv[:, 0] - u) < 3.0).any() else np.nan for u in us])
    return dict(u0=u0, u1=u1, us=us, kv=kv, v_kerb=float(np.nanmedian(kv)))


def measure(h_deck, kerb, log=print, crosswalk_u=(-52.8, -15.8, -4.7, 2.5, 14.0, 49.5)):
    """the plate outline (world polygon), the straight section and the bands; kerb = kerb_from_asset(...)"""
    import cv2
    C, du, dv = frame(); N, im = naip()
    h_edge = h_deck + PARAPET_H
    vk = kerb['v_kerb']
    U0, U1 = kerb['u0'] - 4.0, kerb['u1'] + 4.0; V0, V1 = vk - 70.0, vk + 3.0
    us = np.arange(U0, U1, RES); vs = np.arange(V0, V1, RES)
    VV, UU = np.meshgrid(vs, us)
    img = sample(UU, VV, h_edge, C, du, dv, N, im)          # rows u, cols v
    L = cv2.GaussianBlur(img.mean(2), (0, 0), 0.5 / RES); g = cv2.GaussianBlur(img[..., 1] - (img[..., 0] + img[..., 2]) / 2, (0, 0), 0.5 / RES)
    veg = (g > VEG_G) & (L < 170.0); dark = (L < DARK_L) & ~veg; deck = (L > DECK_L) & ~veg
    # structural gaps: dark bands >= GAP_W wide (an opening removes barrier shadows and lane gutters) and >= GAP_LEN long
    # (removes cars, shelters, buses): the shadowed gap where the outer roadway curves down off the deck at the ends
    dk = ((L < GAP_L) & ~veg).astype(np.uint8)
    rk = max(1, int(round(GAP_W / 2 / RES)))
    dk = cv2.morphologyEx(dk, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))   # joins fragments (1.25 m)
    dk = cv2.morphologyEx(dk, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rk + 1, 2 * rk + 1)))
    nlab, lab, sts, _ = cv2.connectedComponentsWithStats(dk, 8)
    gaps = np.zeros_like(dk, bool); ngap = []
    for c in range(1, nlab):
        ys, xs = np.nonzero(lab == c)
        ext = math.hypot((ys.max() - ys.min()) * RES, (xs.max() - xs.min()) * RES)
        if ext >= GAP_LEN: gaps |= lab == c; ngap.append(dict(u=round(float(us[ys].mean()), 1), v=round(float(vs[xs].mean()), 1), len_m=round(ext, 1), area_m2=round(len(ys) * RES * RES, 1)))
    dark |= gaps; deck &= ~gaps
    # per u station: walk outward (decreasing v) from the kerb; the edge is the last deck pixel before VEG_RUN of
    # vegetation, DARK_RUN of very dark or GAP_TOL of any non-deck
    nv, nd, ng = (int(round(x / RES)) for x in (VEG_RUN, DARK_RUN, GAP_TOL)); st = np.arange(math.ceil(kerb['u0']), math.floor(kerb['u1']) + 1, 1.0)
    vout = np.full(len(st), np.nan); bygap = np.zeros(len(st), bool)
    for k, u in enumerate(st):
        r = np.abs(us - u) < 0.6                             # rows within +-0.6 m of the station
        cd, cv, ck, cg = deck[r].mean(0) > 0.5, veg[r].mean(0) > 0.5, dark[r].mean(0) > 0.5, gaps[r].mean(0) > 0.3
        c = int(np.searchsorted(vs, vk - 0.5)); rv = rk = rg = 0; last = c
        while c > 0:
            c -= 1
            if cd[c]: rv = rk = rg = 0; last = c; continue
            rg += 1; rv = rv + 1 if cv[c] else 0; rk = rk + 1 if ck[c] else 0
            if cg[c]: bygap[k] = True; break
            if rv >= nv or rk >= nd or rg >= ng: break
        vout[k] = vs[last]
    # the straight section: where the edge is within 1.5 m of the median of the central half of the curb
    cen = (st > np.percentile(st, 25)) & (st < np.percentile(st, 75))
    vmed = float(np.nanmedian(vout[cen])); vcap = vmed - 0.5
    full = np.abs(vout - vmed) < 1.5
    # longest run of `full` stations containing the centre
    best = (0, 0); k = 0
    while k < len(st):
        if not full[k]: k += 1; continue
        j = k
        while j < len(st) and full[j]: j += 1
        if j - k > best[1] - best[0]: best = (k, j)
        k = j
    s0, s1 = float(st[best[0]]) + 3.0, float(st[best[1] - 1]) - 3.0
    vout_c = np.maximum(vout, vcap)
    # median filter (9 stations) against picks on a bus or a dark car at the edge; a station stopped by a structural gap
    # keeps its pick (the plate ends at the gap)
    vf = np.array([np.nanmedian(vout_c[max(0, i - 4):i + 5]) for i in range(len(vout_c))])
    vf[bygap] = np.maximum(vf[bygap], vout_c[bygap])
    # plate outline in (u, v): kerb side 1.0 m inside the curb (the trimming against the ITB asset cuts it at the kerb face)
    top = [(float(u), float(vk + 1.0)) for u in (st[0], st[-1])]
    ring = [(float(st[0]), float(vk + 1.0))] + [(float(u), float(v)) for u, v in zip(st, vf)] + [(float(st[-1]), float(vk + 1.0))]
    puv = Polygon(ring).buffer(0)
    # profile over the straight section (crosswalks excluded) at 0.1 m: bands
    ub = np.array([u for u in np.arange(s0, s1, 0.5) if all(abs(u - c) > 4.0 for c in crosswalk_u)])
    vb = np.arange(vmed - 2.0, vk + 1.0, 0.1); VB, UB = np.meshgrid(vb, ub)
    pi = sample(UB, VB, h_edge, C, du, dv, N, im)
    pL = np.median(pi.mean(2), 0); pR = np.median(pi[..., 2] - pi[..., 1], 0)
    def at(v): return int(np.clip(np.searchsorted(vb, v), 0, len(vb) - 1))
    # island B: the red-painted kerb (R - G peak) between v -68 and -56 (v relative to the kerb ~ -32 .. -26 m out)
    lo, hi = at(vk - 38.0), at(vk - 26.0)
    kr = lo + int(np.argmax(pR[lo:hi])); v_red = float(vb[kr])
    # its west gutter: the darkest point within 4 m west of the red kerb
    lo2 = at(v_red - 4.0); kd = lo2 + int(np.argmin(pL[lo2:kr - 5])) if kr - 5 > lo2 else lo2; v_gut = float(vb[kd])
    # island A: the bright plateau 12-20 m out from the kerb (shelters, crosswalk refuges): its extent where the profile is
    # above the mid-level between the plateau peak and the roadway median on each side
    lo3, hi3 = at(vk - 20.0), at(vk - 11.0)
    seg = pL[lo3:hi3]; kp = lo3 + int(np.argmax(seg)); rd = float(np.median(pL[at(vk - 10.0):at(vk - 3.0)]))
    thr = rd + 0.6 * (pL[kp] - rd); a = kp    # 60 % of the way from the roadway level to the plateau peak
    while a > lo3 and pL[a] > thr: a -= 1
    b = kp
    while b < hi3 and pL[b] > thr: b += 1
    islA = (float(vb[a]), float(vb[b]))
    islB = (v_gut, v_red + 0.3)
    bands = [dict(name='inner', v=(islA[1], vk), kind='road'), dict(name='islandA', v=islA, kind='island'),
             dict(name='middle', v=(islB[1], islA[0]), kind='road'), dict(name='islandB', v=islB, kind='island')]
    # the outer light-concrete roadway (v_gut .. the edge) is NOT on this deck: build_roadways keeps it as the lower OSM
    # layer-1 deck (see the module header) and widens it to the imaged edges; its band is reported here
    outer = dict(name='outer (lower deck)', v=(vmed, islB[0]), kind='road_light')
    poly = Polygon(xz_of(np.array(puv.exterior.coords), C, du, dv)).buffer(0)
    out = dict(frame=dict(centre=C.tolist(), du=du.tolist(), dv=dv.tolist()), h_edge=h_edge, v_kerb=vk, v_edge_median=round(vmed, 2), v_cap=round(vcap, 2),
               straight=(round(s0, 1), round(s1, 1)), stations=st.tolist(), v_out=[round(float(v), 2) for v in vf], bands=bands,
               red_kerb_v=round(v_red, 2), gutter_v=round(v_gut, 2), gaps=ngap, outer=outer, islandA=[round(x, 2) for x in islA], poly_uv=puv, poly=poly,
               profile=dict(v=vb.tolist(), L=pL.tolist(), RG=pR.tolist()), img=dict(us=(U0, U1), vs=(V0, V1), res=RES))
    log('ITB departures deck (NAIP 2024, relief at %.2f m): kerb v %.2f (asset), imaged outer edge v %.2f median (cap %.2f), straight u %.1f..%.1f, '
        'island A v %.2f..%.2f, red kerb v %.2f, island B west edge v %.2f; measured outline %.0f m2'
        % (h_edge, vk, vmed, vcap, s0, s1, islA[0], islA[1], v_red, v_gut, poly.area))
    return out, img


def sheet(M, img, pieces_uv, cols_uv, path, title):
    """BR-02 check sheet: relief-corrected NAIP 2024 in the roof frame with the measured plate, bands, island lines and
    the built deck outline / columns over it, and the cross-profile with the band picks"""
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    (U0, U1), (V0, V1), res = M['img']['us'], M['img']['vs'], M['img']['res']
    rgb = np.clip(img[..., ::-1] / 255.0, 0, 1).transpose(1, 0, 2)[::-1]   # rows v (top = V1), cols u
    fig = plt.figure(figsize=(16.5, 11.0), dpi=100)
    ax = fig.add_axes([0.04, 0.38, 0.92, 0.56]); ax.imshow(rgb * 0.8 + 0.1, extent=[U0, U1, V0, V1], aspect='equal')
    x, y = M['poly_uv'].exterior.xy; ax.plot(x, y, '-', color='yellow', lw=1.2, label='measured deck outline (NAIP, relief at %.2f m)' % M['h_edge'])
    for g in pieces_uv:
        for p in (getattr(g, 'geoms', None) or [g]):
            if p.is_empty: continue
            x, y = p.exterior.xy; ax.plot(x, y, '-', color='magenta', lw=0.8)
    ax.plot([], [], '-', color='magenta', lw=0.8, label='built deck (after trimming at the ITB curb)')
    for b in M['bands']:
        for v in b['v']: ax.axhline(v, xmin=(M['straight'][0] - U0) / (U1 - U0), xmax=(M['straight'][1] - U0) / (U1 - U0), color='cyan', lw=0.6, ls='--')
    ax.axhline(M['v_kerb'], color='orange', lw=0.8, label='ITB kerb (asset)')
    if len(cols_uv): ax.plot(np.array(cols_uv)[:, 0], np.array(cols_uv)[:, 1], 'o', ms=3, mfc='w', mec='k', label='columns')
    ax.set_xlim(U0, U1); ax.set_ylim(V0, V1); ax.set_xlabel('u (m, ITB roof frame, + towards BA-A)'); ax.set_ylabel('v (m, + ENE)')
    ax.legend(loc='lower right', fontsize=8); ax.set_title(title, fontsize=9, loc='left')
    a2 = fig.add_axes([0.06, 0.06, 0.88, 0.25]); v = np.array(M['profile']['v'])
    a2.plot(v, M['profile']['L'], lw=1, label='median brightness (straight section, crosswalks excluded)'); a2.plot(v, np.array(M['profile']['RG']) + 100, lw=0.8, label='R - G (+100)')
    for b in M['bands']:
        a2.axvspan(*sorted(b['v']), alpha=0.12, color={'road': 'grey', 'island': 'orange', 'road_light': 'yellow'}[b['kind']])
        a2.text(np.mean(b['v']), 245, b['name'], ha='center', fontsize=7)
    a2.axvline(M['v_kerb'], color='orange'); a2.axvline(M['v_edge_median'], color='yellow')
    a2.set_xlabel('v (m)'); a2.grid(alpha=0.3); a2.legend(fontsize=7, loc='lower left'); a2.set_ylim(60, 260)
    fig.savefig(path); plt.close(fig)
