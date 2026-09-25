"""
Sheet L3 -- FUSELAGE OPENINGS: doors, cabin windows and the over-wing emergency exit, drawn from the opening
constants of model/fuselage_parts.py (WIN_*, FIXED_WINDOWS, AIRSTAIR, CARGO, EXIT, DOOR_WINDOWS,
DOOR_DETAILS) on the refitted OML of model/fuselage.py -- never from the mesh.

    python3 -m drawing.master L3          (or: python3 -m drawing.openings_sheet)

Views: port elevation (seen from port, 1:20) with station ordinates to every opening; plan (1:20) with the
openings projected through the OML (y = side_y(x, z); parts below the max-breadth WL hidden) -- the view the
starboard windows were read from; starboard elevation (seen from starboard, nose right, 1:20); detail A cabin
window (1:5), detail B emergency exit (1:10), section C-C with the door hinges and swings (1:30).  Tables:
openings (our stations; doors as clear opening + panel seam, DOOR_PANELS), deviations vs the registered Pilatus
drawing / the Pilatus tech-data side render (render_check(), measured at run time from the git-ignored cache
image) / photos / rev A, Stage-3 hand-over.  The overlay variant adds the Pilatus drawing in red, photo-derived
stations in blue and the render-derived stations in purple; refs/cache/overlays/L3_render_check.png shows our port
openings drawn onto the render.
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drawing import master as M  # noqa: E402
from drawing.canvas import text_width  # noqa: E402
from drawing.master import (INK, GRID, MUTED, ACCENT, BLUE, RED, W_OBJ, W_FINE, W_DIM, W_THIN, W_GRID,  # noqa: E402
                            CHAIN, PHANTOM, grid_lines, station_grid, table, view_title, scale_bar, side_view,
                            plan_view, aft_view, View)
from model import fuselage as F  # noqa: E402
from model import fuselage_parts as FP  # noqa: E402

SHEET = dict(id="L3", title="FUSELAGE OPENINGS", subtitle="FUSELAGE OPENINGS - DOORS, WINDOWS, EXIT", size="A1",
             scale="AS SHOWN", rev="A", order=30)

X0, X1, Z0, Z1 = 2.60, 10.00, 0.85, 2.95          # elevation / plan window (model m)
YP = 0.95                                          # plan half-width shown
K20 = 50.0                                         # sheet mm per m at 1:20
GRID_FRAMES = ("FR10", "FR12", "FR14", "FR16", "FR19", "FR21", "FR23", "FR25", "FR27", "FR29", "FR30", "FR31",
               "FR33", "FR36")
LIGHT = "#34434B"
GHOST = "#AEB8BF"                                  # rev A openings (before this refit)
EXIT_DETAIL_R = 0.44                               # detail circle B about the exit hatch (m)

# rev A (the model before this refit) for the change column
REV_A = dict(win=(0.310, 0.430, 2.010, "rrect r60"), port=[5.52, 6.32, 7.12, 7.92], stbd=[4.72, 6.32, 7.12, 7.92, 8.72],
             airstair=(4.715, 1.775, 0.305, 0.675, 0.09), cargo=(8.925, 1.780, 0.675, 0.660, 0.10),
             exit=(5.520, 1.905, 0.255, 0.455, 0.08), door_win=dict(door_airstair=4.715, door_cargo=8.72,
                                                                    exit_hatch=5.52))

# photo measurements (refs/photos.json ids; registration and pixel reads in the module notes of photo_check())
PHOTO = dict(
    kenia_stbd=dict(id="ngx_kenia_stbd_pilatus", px_tip=3107.5, px_per_m=166.7,
                    win_px=[2286.0, 2149.5, 2025.0, 1907.5, 1782.5], exit_px=(2111.0, 2192.5)),
    ownership_port=dict(id="ngx_ownership_port_pilatus", d1_px=(904.0, 1014.0), win_px=[1070.75, 1173.25, 1307.25],
                        d2_px=(1397.5, 1640.0)),
)


# ============================================================================================ model data
def openings():
    """Drawing records (sheet ids P1.., S1.., D1, D2, E1) built from the fuselage_parts constants."""
    R = []
    A, C, E = FP.AIRSTAIR, FP.CARGO, FP.EXIT
    R.append(dict(id="D1", name="AIRSTAIR DOOR", kind="door", o=A, side=-1))
    for i, cx in enumerate(FP.FIXED_WINDOWS[-1]):
        R.append(dict(id=f"P{i + 1}", name="CABIN WINDOW", kind="window", cx=cx, side=-1))
    R.append(dict(id="D2", name="CARGO DOOR", kind="door", o=C, side=-1))
    if FP.DOOR_WINDOWS.get("door_cargo") is not None:
        R.append(dict(id=f"P{len(FP.FIXED_WINDOWS[-1]) + 1}", name="WINDOW IN D2", kind="window",
                      cx=FP.DOOR_WINDOWS["door_cargo"], side=-1, host="D2"))
    if FP.DOOR_WINDOWS.get("door_airstair") is not None:
        R.append(dict(id="P0", name="WINDOW IN D1", kind="window", cx=FP.DOOR_WINDOWS["door_airstair"], side=-1,
                      host="D1"))
    R.append(dict(id="E1", name="EMERGENCY EXIT", kind="exit", o=E, side=+1))
    sw = [(cx, None) for cx in FP.FIXED_WINDOWS[+1]]
    if FP.DOOR_WINDOWS.get("exit_hatch") is not None:
        sw.append((FP.DOOR_WINDOWS["exit_hatch"], "E1"))
    for i, (cx, host) in enumerate(sorted(sw)):
        R.append(dict(id=f"S{i + 1}", name="CABIN WINDOW" if host is None else "WINDOW IN E1", kind="window", cx=cx,
                      side=+1, host=host))
    for r in R:
        if r["kind"] == "window":
            r.update(outline=FP.window_outline(r["cx"]), x0=r["cx"] - FP.WIN_HX, x1=r["cx"] + FP.WIN_HX,
                     z0=FP.WIN_CZ - FP.WIN_HZ, z1=FP.WIN_CZ + FP.WIN_HZ, cz=FP.WIN_CZ, w=FP.WIN_W, h=FP.WIN_H)
        else:
            o = r["o"]
            p = FP.door_panel(o)
            r.update(outline=FP.opening_outline(o), cx=o["cx"], cz=o["cz"], x0=o["cx"] - o["hx"],
                     x1=o["cx"] + o["hx"], z0=o["cz"] - o["hz"], z1=o["cz"] + o["hz"], w=2 * o["hx"], h=2 * o["hz"],
                     panel=p, poutline=FP.opening_outline(p), px0=p["cx"] - p["hx"], px1=p["cx"] + p["hx"],
                     pz0=p["cz"] - p["hz"], pz1=p["cz"] + p["hz"], pw=2 * p["hx"], ph=2 * p["hz"],
                     has_seam=p is not o)
    return R


RENDER_FILE = M.ROOT / "refs" / "cache" / "photos" / "cand" / "pil_techdata_side_5000.webp"
RENDER_URL = ("pilatus-aircraft.com/en/pc-12/technical-data (image PC-12G_techdata_exterior_side_desktop, 5000 px "
              "variant, 3500 x 1351)")


def render_check():
    """Pilatus PC-12 technical-data side render (port side, current production: single-pane cockpit side window,
    no window in the airstair door).  Measured at run time from the git-ignored cache image (no pixel data in git):
    cabin-window blobs (half-maximum edges), the four vertical door-panel seams (dark lines between the door tops
    and the window tops, refined row by row between the window rows), the airstair-door top seam.  The port
    opening pattern [D1 seams, P1-P4, D2 seams] is fitted to OUR stations with a scale + offset (perspective
    render; every feature lies on the fuselage side), giving residuals and render-derived stations.
    Returns None when the image is not cached."""
    if not RENDER_FILE.exists():
        return None
    from PIL import Image
    from scipy import ndimage as ndi
    from scipy.signal import find_peaks
    im = np.asarray(Image.open(RENDER_FILE).convert("L")).astype(float)
    # cabin windows: dark blobs in the window band
    y0, y1, x0, x1 = 400, 560, 1000, 2100
    m = ndi.binary_fill_holes(ndi.binary_opening(im[y0:y1, x0:x1] < 190, iterations=2))
    lab, n = ndi.label(m)
    wins = []
    for i in range(1, n + 1):
        yy, xx = np.nonzero(lab == i)
        if len(yy) < 800:
            continue
        cx, cy = 0.5 * (xx.min() + xx.max()) + x0, 0.5 * (yy.min() + yy.max()) + y0

        def half_max(p):
            hi, lo = np.median(np.r_[p[:5], p[-5:]]), np.percentile(p, 10)
            th = 0.5 * (hi + lo)
            idx = np.nonzero(p < th)[0]
            a, b = idx.min(), idx.max()
            return (b + (p[b] - th) / (p[b] - p[b + 1])) - (a - 1 + (p[a - 1] - th) / (p[a - 1] - p[a]))

        ic, jc = int(round(cy)), int(round(cx))
        w = np.median([half_max(im[r, jc - 45:jc + 46]) for r in range(ic - 14, ic + 15, 3)])
        h = np.median([half_max(im[ic - 60:ic + 61, c]) for c in range(jc - 10, jc + 11, 3)])
        wins.append((cx, cy, w, h, len(yy) / ((xx.max() - xx.min() + 1) * (yy.max() - yy.min() + 1))))
    wins.sort()
    # vertical seams: minima of the band between the door tops and the window tops, refined row by row
    band = im[398:440, 1030:2050].mean(0)
    base = np.convolve(band, np.ones(21) / 21, "same")
    pk, pr = find_peaks(-(band - base), prominence=5)
    cand = sorted(1030 + pk[np.argsort(pr["prominences"])[-4:]])
    seams = []
    for c in cand:
        v = []
        for r in range(430, 561, 10):
            p = im[r - 3:r + 4, c - 7:c + 8].mean(0)
            k = int(np.argmin(p))
            if 0 < k < len(p) - 1:
                a, b, cc = p[k - 1], p[k], p[k + 1]
                v.append(c - 7 + k + (0.5 * (a - cc) / (a - 2 * b + cc) if (a - 2 * b + cc) else 0.0))
        seams.append(float(np.median(v)))
    # airstair-door top seam (dark gutter line) over the door's middle
    p = im[370:410, int(seams[0]) + 30:int(seams[1]) - 30].mean(1)
    k = int(np.argmin(p))
    d1_top = 370 + k + 0.5 * (p[k - 1] - p[k + 1]) / (p[k - 1] - 2 * p[k] + p[k + 1])
    if len(wins) != 4 or len(seams) != 4:
        return dict(ok=False, note=f"render: found {len(wins)} windows / {len(seams)} seams (expected 4 / 4)")
    by = {r["id"]: r for r in openings()}
    names = ["D1 fwd seam", "D1 aft seam", "P1", "P2", "P3", "P4", "D2 fwd seam", "D2 aft seam"]
    px = np.array([seams[0], seams[1]] + [w[0] for w in wins] + [seams[2], seams[3]])
    ours = np.array([by["D1"]["px0"], by["D1"]["px1"]] + [by[f"P{i}"]["cx"] for i in range(1, 5)] +
                    [by["D2"]["px0"], by["D2"]["px1"]])
    A = np.c_[px, np.ones_like(px)]
    c, *_ = np.linalg.lstsq(A, ours, rcond=None)
    fit = A @ c
    s = 1.0 / c[0]                                             # px per m on the fuselage side
    ww, hh = np.median([w[2] for w in wins]), np.median([w[3] for w in wins])
    cy = np.median([w[1] for w in wins])
    return dict(ok=True, names=names, px=px, ours=ours, fit=fit, res=(fit - ours) * 1000, px_per_m=s,
                win_w=ww / s, win_h=hh / s, win_wh=ww / hh, d1_w=(seams[1] - seams[0]) / s,
                d2_w=(seams[3] - seams[2]) / s, d2_over_d1=(seams[3] - seams[2]) / (seams[1] - seams[0]),
                win_cl_below_d1_top=(cy - d1_top) / s, coef=c, d1_top_px=d1_top,
                win_fill=wins[0][4] if len(wins[0]) > 4 else None,
                note=f"{len(wins)} windows, 4 seams, {s:.1f} px/m, pattern residual max "
                     f"{np.max(np.abs((fit - ours) * 1000)):.1f} mm")


def rev_a_outlines(side):
    """Outlines (x, z) of the rev-A openings on one side (the model before this refit)."""
    from cad import sdf2d
    ra = REV_A
    w, h, cz = ra["win"][0] / 2, ra["win"][1] / 2, ra["win"][2]
    out = []
    wins = list(ra["port"] if side < 0 else ra["stbd"])
    wins += [ra["door_win"]["door_airstair"], ra["door_win"]["door_cargo"]] if side < 0 else \
        [ra["door_win"]["exit_hatch"]]
    for cx in wins:
        P = sdf2d.rrect_outline(cx, cz, w, h, 0.06, 8)
        out.append(np.vstack([P, P[:1]]))
    doors = [ra["airstair"], ra["cargo"]] if side < 0 else [ra["exit"]]
    for cx, czd, hx, hz, r in doors:
        P = sdf2d.rrect_outline(cx, czd, hx, hz, r, 8)
        out.append(np.vstack([P, P[:1]]))
    return out


def plan_projection(P, side):
    """Side-projection outline (x, z) on the OML -> plan (x, y) runs, flagged visible (above the max-breadth
    WL, facing up) or hidden."""
    x, z = P[:, 0], P[:, 1]
    y = side * F.side_y(x, z)
    vis = z >= F.z_mw(x)
    out = []
    start = 0
    for i in range(1, len(P) + 1):
        if i == len(P) or vis[i] != vis[start]:
            j0 = max(start - 1, 0)
            out.append((np.c_[x[j0:i], y[j0:i]], bool(vis[start])))
            start = i
    return out


def cockpit_window_outline():
    """Context: the cockpit side window and the PRO dark mask (model/cockpit_glazing.py, owned by the glazing
    sheet) in side projection; parts of the mask above the crown are dropped.  Returns [(pts, kind)]."""
    try:
        from model import cockpit_glazing as CG
        out = []
        if hasattr(CG, "side_outline"):
            P = np.asarray(CG.side_outline("sw"))
            out.append((np.vstack([P, P[:1]]), "sw"))
            P = np.asarray(CG.side_outline("mask"))
            P = np.vstack([P, P[:1]])
            seg = np.linalg.norm(np.diff(P, axis=0), axis=1)          # resample every ~5 mm so edges clip at the crown
            sa = np.r_[0.0, np.cumsum(seg)]
            su = np.linspace(0.0, sa[-1], max(int(sa[-1] / 0.005), 8) + 1)
            P = np.c_[np.interp(su, sa, P[:, 0]), np.interp(su, sa, P[:, 1])]
            ok = P[:, 1] <= F.z_top(P[:, 0]) + 0.002
            if ok.all():
                return out + [(P, "mask")]
            k = int(np.argmin(ok))                       # start the loop at a dropped point
            P, ok = np.roll(P[:-1], -k, 0), np.roll(ok[:-1], -k)
            P, ok = np.vstack([P, P[:1]]), np.r_[ok, ok[:1]]
            start = None
            for i in range(len(P) + 1):
                if i < len(P) and ok[i]:
                    start = i if start is None else start
                elif start is not None:
                    if i - start >= 2:
                        out.append((P[start:i], "mask"))
                    start = None
            return out
        import contourpy
        xs = np.linspace(3.0, 4.7, 341)
        zs = np.linspace(1.75, 2.85, 221)
        Xg, Zg = np.meshgrid(xs, zs)
        D = CG.sidewindow_sdf(Xg, np.full_like(Xg, 0.8), Zg)
        return [(np.asarray(L), "sw") for L in contourpy.contour_generator(xs, zs, D).lines(0.0) if len(L) > 5]
    except Exception:                                                     # noqa: BLE001
        return []


# ============================================================================================ reference
def reference():
    """Measurements of the registered Pilatus drawing (refs/mbp.py, git-ignored cache): the numbers the
    constants were fitted to.  Only DELTAS go onto the clean sheet."""
    d = M.mbp_data()
    O = d["openings"]["side"]
    bb = lambda P: (float(np.min(P[:, 0])), float(np.max(P[:, 0])), float(np.min(P[:, 1])), float(np.max(P[:, 1])))
    ref = {}
    for k in ("door_airstair", "door_cargo", "cabin_win_1", "cabin_win_2", "cabin_win_3", "door_cargo_win"):
        ref[k] = bb(np.asarray(O[k]))
    # cargo door: the side outline is open at the bottom (behind the wing fairing); its sill is the lowest
    # near-horizontal outline / hidden run inside the door's span
    x0, x1 = ref["door_cargo"][:2]
    lows = []
    for it in d["side"]:
        if it["kind"] not in ("outline", "hidden"):
            continue
        P = it["pts"]
        m = (P[:, 0] > x0 + 0.05) & (P[:, 0] < x1 - 0.05) & (P[:, 1] > 1.10) & (P[:, 1] < 1.24)
        if m.sum() >= 2 and np.ptp(P[m, 1]) < 0.02 and np.ptp(P[m, 0]) > 0.2:
            lows.append(float(np.median(P[m, 1])))
    if lows:
        c = ref["door_cargo"]
        ref["door_cargo"] = (c[0], c[1], max(lows), c[3])
    # plan view: closed windows (0.30 long, y 0.72-0.84) per side, exit hatch (0.48 long)
    pw = {1: [], -1: []}
    for it in d["plan"]:
        P = it["pts"]
        if it["kind"] != "outline" or len(P) < 20 or not np.allclose(P[0], P[-1]):
            continue
        w = np.ptp(P[:, 0])
        ym = float(np.mean(P[:, 1]))
        if abs(w - 0.30) < 0.01 and 0.70 < abs(ym) < 0.86:
            pw[1 if ym > 0 else -1].append(0.5 * (P[:, 0].min() + P[:, 0].max()))
        if abs(w - 0.482) < 0.01 and ym > 0:
            ref["plan_exit"] = (float(P[:, 0].min()), float(P[:, 0].max()), float(P[:, 1].min()), float(P[:, 1].max()))
    ref["plan_win"] = {s: sorted(v) for s, v in pw.items()}
    for it in d["detail_stbd"]:
        P = it["pts"]
        if it["kind"] == "outline" and abs(np.ptp(P[:, 0]) - 0.482) < 0.01 and abs(np.ptp(P[:, 1]) - 0.641) < 0.02:
            ref["detail_exit"] = bb(P)
    for it in d["detail_port_sheet2"]:
        P = it["pts"]
        if it["kind"] == "outline" and 0.55 < np.ptp(P[:, 0]) < 0.66 and np.ptp(P[:, 1]) > 1.3:
            ref["s2_airstair"] = bb(P)
    return ref


def photo_check():
    """Photo stations.  Kenia NGX starboard (5000 px, near broadside): spinner tip X 3107.5 px = STA 390, aft
    cowl joint X 2672.5 px = STA 3000 -> 166.7 px/m; window centres read at 2x zoom.  NGX 'Ownership' port
    (1920 px): door-opening edges and window centres.  Each pattern is also fitted to our stations with a
    scale + offset (perspective), giving the residuals."""
    out = {}
    k = PHOTO["kenia_stbd"]
    xs = np.array(k["win_px"])
    out["stbd_abs"] = list(0.39 + (k["px_tip"] - xs) / k["px_per_m"])
    e = np.array(k["exit_px"])
    out["exit_abs"] = list(0.39 + (k["px_tip"] - e[::-1]) / k["px_per_m"])
    ours = [r["cx"] for r in openings() if r["side"] > 0 and r["kind"] == "window"]
    A = np.c_[xs, np.ones_like(xs)]
    c, *_ = np.linalg.lstsq(A, np.array(ours), rcond=None)
    out["stbd_fit_res"] = list((A @ c - ours) * 1000)
    out["stbd_fit"] = list(A @ c)
    o = PHOTO["ownership_port"]
    px = np.array([np.mean(o["d1_px"])] + o["win_px"] + [np.mean(o["d2_px"])])
    ours_p = [FP.AIRSTAIR["cx"]] + list(FP.FIXED_WINDOWS[-1]) + [FP.CARGO["cx"]]
    A = np.c_[px, np.ones_like(px)]
    c, *_ = np.linalg.lstsq(A, np.array(ours_p), rcond=None)
    out["port_fit_res"] = list((A @ c - ours_p) * 1000)
    out["port_fit"] = list(A @ c)
    out["d2_over_d1"] = (o["d2_px"][1] - o["d2_px"][0]) / (o["d1_px"][1] - o["d1_px"][0])
    return out


# ============================================================================================ helpers
def _relax(vals, gap):
    """Spread sorted positions so neighbours are >= gap apart, staying close to the originals."""
    v = np.array(vals, float)
    order = np.argsort(v)
    s = v[order].copy()
    for _ in range(200):
        moved = False
        for i in range(1, len(s)):
            d = s[i] - s[i - 1]
            if d < gap - 1e-6:
                sh = 0.5 * (gap - d)
                s[i - 1] -= sh
                s[i] += sh
                moved = True
        if not moved:
            break
    out = np.empty_like(s)
    out[order] = s
    return out


def ordinates(ds, v, items, row_y, color=INK, size=2.4, gap=3.4):
    """Station ordinates above a view: items = [(x, z_feature, text)], extension lines from the features up to
    row_y (sheet mm) with a jog where labels had to be spread; text reads upward from row_y."""
    X = [v.pt(x, z)[0] for x, z, _ in items]
    Xt = _relax(X, gap)
    for (x, z, s), xa, xt in zip(items, X, Xt):
        _, yf = v.pt(x, z)
        yj = row_y + 5.0
        ds.cv.path([(xa, yf - 1.0), (xa, yj), (xt, row_y + 2.0), (xt, row_y + 0.8)], W_DIM, color=color)
        ds.text(xt, row_y, s, size, "mono", "start", rot=-90, vcenter=True, fill=color, tag="ordinate")


def wl_ticks(ds, v, entries, edge_x, size=2.2, gap=2.9, color=INK):
    """WL ordinates on the view's sheet-left edge: entries = [(z, text)]."""
    X, _ = v.pt(edge_x, 0.0)
    Y = [v.pt(edge_x, z)[1] for z, _ in entries]
    Yt = _relax(Y, gap)
    for (z, s), ya, yt in zip(entries, Y, Yt):
        ds.cv.path([(X, ya), (X - 3.0, ya), (X - 4.5, yt), (X - 5.5, yt)], W_DIM, color=color)
        ds.text(X - 6.2, yt, s, size, "mono", "end", vcenter=True, fill=color, tag="wl")


def break_line(ds, v, x, z0, z1, n=5, amp=0.035):
    zs = np.linspace(z0, z1, 2 * n + 1)
    xs = x + np.array([0 if i % 2 == 0 else (amp if (i // 2) % 2 == 0 else -amp) for i in range(len(zs))])
    ds.cv.path(v.pts(np.c_[xs, zs]), W_THIN, color=INK)


def centre_marks(ds, v, cx, cz, hx, hz, ext=0.03):
    ds.cv.line(v.pt(cx - hx - ext, cz), v.pt(cx + hx + ext, cz), W_GRID, CHAIN, color=MUTED)
    ds.cv.line(v.pt(cx, cz - hz - ext), v.pt(cx, cz + hz + ext), W_GRID, CHAIN, color=MUTED)


def stbd_view(name, origin, scale, model_origin, box=None):
    """Elevation seen from STARBOARD (nose right): (x, z) -> sheet."""
    k = 1000.0 / scale
    A = np.array([[-k, 0.0], [0.0, -k]])
    t = np.asarray(origin, float) - A @ np.asarray(model_origin, float)
    return View(name, "xz", A, t, float(scale), box, "seen from starboard, nose right")


# ============================================================================================ views
def draw_elevation(ds, v, side, R, row_y):
    cv = ds.cv
    xs = np.linspace(X0, X1, 600)
    # grids: WLs (labels on the sheet-right end), frames (labels below)
    wls = (1.0, 1.5, 2.0, 2.5)
    grid_lines(ds, v, "b", wls, X0, X1, labels=[f"WL {z * 1000:.0f}" for z in wls],
               where=("end",) if side < 0 else ("start",), size=2.1)
    fr = {n: F.FRAMES[n] for n in GRID_FRAMES}
    station_grid(ds, [v], fr, [(Z0, Z1)], label_at="lo", size=2.1)
    for name, xk in (("FIREWALL", F.STA["firewall"]), ("APB", F.STA["aft_pressure_bulkhead"])):
        p, q = v.pt(xk, Z0), v.pt(xk, Z1)
        ds.cv.line(p, q, W_GRID, (5.0, 1.0, 0.8, 1.0), color=MUTED)
        ds.text(p[0], p[1] + 10.0, f"{name} {xk * 1000:.0f}", 1.9, "label", "middle", fill=MUTED, tag="key")
    # OML silhouette (crown, keel), max-breadth line, break lines at the view ends
    cv.path(v.pts(np.c_[xs, F.z_top(xs)]), W_OBJ)
    cv.path(v.pts(np.c_[xs, F.z_bot(xs)]), W_OBJ)
    cv.path(v.pts(np.c_[xs, F.z_mw(xs)]), W_THIN, CHAIN, color=LIGHT)
    for x in (X0, X1):
        break_line(ds, v, x, float(F.z_bot(x)) - 0.03, float(F.z_top(x)) + 0.03)
    # label clear of its own (curved) chain line: baseline above the line's highest point under the label
    lab = "MAX-BREADTH WL"
    X, _ = v.pt(9.35, 0.0)
    hw = 0.5 * text_width(lab, 1.9) / abs(v.A[0, 0])
    xl = np.linspace(9.35 - hw - 0.05, 9.35 + hw + 0.05, 30)
    Y = min(v.pt(x_, float(F.z_mw(x_)))[1] for x_ in xl)
    ds.text(X, Y - 1.2, lab, 1.9, "label", "middle", fill=LIGHT, tag="lbl")
    # cabin floor / door sill line (reference)
    cv.line(v.pt(4.45, FP.DOOR_SILL_WL), v.pt(9.8, FP.DOOR_SILL_WL), W_THIN, (3.0, 1.2), color=MUTED)
    # cockpit side window (context)
    for L, kind in cockpit_window_outline():
        cv.path(v.pts(L), W_FINE, None if kind == "sw" else (1.2, 0.8), color=MUTED)
    X, Y = v.pt(3.62, 1.93)
    ds.text(X, Y, "COCKPIT SIDE WINDOW + PRO MASK (CONTEXT)", 1.9, "label", "middle", fill=MUTED, tag="lbl")
    # rev A openings (ghost, for the change review)
    for P in rev_a_outlines(side):
        cv.path(v.pts(P), W_THIN, (1.0, 0.8), closed=True, color=GHOST)
    # openings of this side
    mine = [r for r in R if r["side"] == side]
    for r in mine:
        if r["kind"] == "door":
            # door-panel seam (visible outline) + clear opening inside it (door frame, hidden: dashed)
            cv.path(v.pts(r["poutline"]), W_OBJ, closed=True)
            cv.path(v.pts(r["outline"]), W_FINE, (1.4, 0.8), closed=True, color=MUTED)
        else:
            cv.path(v.pts(r["outline"]), W_OBJ, closed=True)
        if r["kind"] == "window":
            centre_marks(ds, v, r["cx"], r["cz"], FP.WIN_HX, FP.WIN_HZ, 0.025)   # broken under the id (draw())
            X, Y = v.pt(r["cx"], r["z0"] + 0.06)
            ds.text(X, Y, r["id"], 2.3, "label", "middle", weight=600, tag="id")
        else:
            o = r["o"]
            h = FP.hinge_line(o)
            if h:
                cv.line(v.pt(h[0] + 0.02, h[2]), v.pt(h[1] - 0.02, h[2]), W_FINE, PHANTOM, color=ACCENT)
            _door_text(ds, v, r)
    for key, o in FP.DOOR_DETAILS.items():
        if o["side"] == side:
            cv.path(v.pts(FP.opening_outline(o, 8)), W_FINE, closed=True)
    # ordinates: door / exit edges, window centre lines
    items = []
    for r in mine:
        if r["kind"] == "window":
            items.append((r["cx"], r["z1"], f"{r['cx'] * 1000:.0f}"))
        else:
            items += [(r["px0"], r["pz1"], f"{r['px0'] * 1000:.0f}"), (r["px1"], r["pz1"], f"{r['px1'] * 1000:.0f}")]
    items.sort(key=lambda t: t[0])
    ordinates(ds, v, items, row_y)
    X, _ = v.pt(X0 if side < 0 else X1, 0)
    ds.text(X + (1 if side < 0 else -1) * 0.0, row_y - 15.5,
            "STATIONS (mm aft of datum): door-panel seams / exit hatch edges, window centre lines "
            "(clear openings: table)", 2.1, "label", "start" if side < 0 else "start", fill=MUTED, tag="lbl")
    # WL ordinates on the sheet-left edge
    ents = [(float(F.z_top(6.0)), f"{F.z_top(6.0) * 1000:.0f} CROWN"),
            (FP.WIN_CZ + FP.WIN_HZ, f"{(FP.WIN_CZ + FP.WIN_HZ) * 1000:.0f}"),
            (FP.WIN_CZ, f"{FP.WIN_CZ * 1000:.0f} WIN CL"),
            (FP.WIN_CZ - FP.WIN_HZ, f"{(FP.WIN_CZ - FP.WIN_HZ) * 1000:.0f}")]
    for r in mine:
        if r["kind"] == "door":
            ents += [(r["pz0"], f"{r['pz0'] * 1000:.0f} {r['id']} SEAM"), (r["pz1"], f"{r['pz1'] * 1000:.0f} {r['id']} SEAM")]
        elif r["kind"] == "exit":
            ents += [(r["z0"], f"{r['z0'] * 1000:.0f} {r['id']} SILL"), (r["z1"], f"{r['z1'] * 1000:.0f} {r['id']} TOP")]
    if side < 0:
        ents.append((FP.DOOR_SILL_WL, f"{FP.DOOR_SILL_WL * 1000:.0f} D1/D2 SILL"))
    groups = {}
    for z, s in ents:
        groups.setdefault(round(z, 4), []).append(s)
    ents2 = []
    for key in sorted(groups, reverse=True):
        ss = groups[key]
        if len(ss) == 1:
            ents2.append((key, ss[0]))
        else:
            ids = "/".join(t.split()[1] for t in ss)
            ents2.append((key, f"{ss[0].split()[0]} {ids} {ss[0].split()[-1]}"))
    wl_ticks(ds, v, ents2, X0 if side < 0 else X1)


def _door_text(ds, v, r):
    o = r["o"]
    w, h = 2 * o["hx"], 2 * o["hz"]
    hinge = {"bottom": "HINGED AT SILL - OPENS DOWN", "top": "HINGED AT TOP - OPENS UP",
             None: "PLUG TYPE - REMOVED INWARD"}[o.get("hinge")]
    if r["kind"] == "door":
        if r["id"] == "D1":
            X, Y = v.pt(o["cx"], o["cz"] + 0.34)
        else:                                   # D2: below the max-breadth chain line that crosses the panel
            xn = o["cx"] + 0.33
            X, Y = v.pt(xn, min(float(F.z_mw(x_)) for x_ in np.linspace(xn - 0.25, xn + 0.25, 11)) - 0.10)
        lines = [f"{r['id']}  {r['name']}", f"CLEAR {w * 1000:.0f} x {h * 1000:.0f}",
                 f"PANEL {r['pw'] * 1000:.0f} x {r['ph'] * 1000:.0f}", hinge.split(" - ")[0],
                 hinge.split(" - ")[1] + (f" {o['open_deg']:.0f} DEG" if o.get("open_deg") else "")]
        for i, s in enumerate(lines):
            ds.text(X, Y + 3.0 * i, s, 2.1 if i else 2.3, "label" if i not in (1, 2) else "mono", "middle",
                    weight=600 if i == 0 else 400, tag="door")
        # hinge label
        hl = FP.hinge_line(o)                   # label outside the panel seam, next to the hinge line's end
        X, Y = v.pt(hl[0] + 0.03, hl[2])
        _, Ys = v.pt(hl[0], r["pz1"] if o["hinge"] == "top" else r["pz0"])
        ds.text(X + (1.0 if v.A[0, 0] > 0 else -1.0), Ys - 1.1 if o["hinge"] == "top" else Ys + 2.4, "HINGE", 1.8,
                "label", "start" if v.A[0, 0] > 0 else "end", fill=ACCENT, tag="hinge")
    else:                                       # below detail circle B (radius EXIT_DETAIL_R about the hatch)
        X, Y = v.pt(o["cx"], o["cz"] - EXIT_DETAIL_R)
        ds.text(X, Y + 3.4, f"{r['id']}  EMERGENCY EXIT  {w * 1000:.0f} x {h * 1000:.0f}", 2.1, "label", "middle",
                weight=600, tag="door")


def draw_plan(ds, v, R):
    cv = ds.cv
    xs = np.linspace(X0, X1, 600)
    bls = (-0.8, -0.5, 0.5, 0.8)
    grid_lines(ds, v, "b", bls, X0, X1, labels=[f"BL {abs(y) * 1000:.0f} {'S' if y > 0 else 'P'}" for y in bls],
               where=("end",), size=2.0)
    fr = {n: F.FRAMES[n] for n in GRID_FRAMES}
    for n, x in fr.items():
        cv.line(v.pt(x, -YP), v.pt(x, YP), W_GRID, color=GRID)
    cv.line(v.pt(X0 - 0.1, 0), v.pt(X1 + 0.1, 0), W_FINE, CHAIN)
    X, Y = v.pt(X0 - 0.1, 0)
    ds.text(X - 1.2, Y, "CL", 2.3, "label", "end", vcenter=True, weight=600, tag="cl")
    for s in (1, -1):
        cv.path(v.pts(np.c_[xs, s * F.half_w(xs)]), W_OBJ)
    for x in (X0, X1):
        for s in (1, -1):
            yy = float(F.half_w(x))
            P = np.c_[x + np.array([0, 0.03, -0.03, 0.0]), s * np.array([yy + 0.03, yy * 0.66, yy * 0.33, 0.0])]
            cv.path(v.pts(P), W_THIN)
    for r in R:
        for P, vis in plan_projection(r["poutline"] if r["kind"] == "door" else r["outline"], r["side"]):
            cv.path(v.pts(P), W_FINE if r["kind"] == "window" else W_OBJ, None if vis else (1.4, 0.8),
                    color=INK if vis else MUTED)
    for key, o in FP.DOOR_DETAILS.items():
        for P, vis in plan_projection(FP.opening_outline(o, 8), o["side"]):
            if vis:
                cv.path(v.pts(P), W_THIN)
    # side labels + ids
    X, Y = v.pt(X0 + 0.05, 0.60)
    ds.text(X, Y, "STARBOARD", 2.4, "label", "start", weight=600, tag="lbl")
    X, Y = v.pt(X0 + 0.05, -0.60)
    ds.text(X, Y + 1.5, "PORT", 2.4, "label", "start", weight=600, tag="lbl")
    for r in R:
        yy = r["side"] * float(F.side_y(r["cx"], r["z1"]))
        X, Y = v.pt(r["cx"], yy)
        if r["id"] == "E1":                     # inside the hatch outline, aft of the handle
            ds.text(X + 0.075 * K20, Y - 1.2, r["id"], 2.0, "label", "start", weight=600, tag="id")
            continue
        ds.text(X, Y + (-1.2 if r["side"] > 0 else 3.0), r["id"], 2.0, "label", "middle", weight=600, tag="id")
    X, Y = v.pt(0.5 * (X0 + X1), -0.30)
    ds.text(X, Y, "OPENINGS PROJECTED THROUGH THE OML: y = side_y(x, z) - DASHED BELOW THE MAX-BREADTH WL (HIDDEN)",
            2.0, "label", "middle", fill=MUTED, tag="lbl")


D1_COL, D2_COL = ACCENT, "#A0522D"                   # door colours in section C-C


def draw_section(ds, v, R):
    """Section C-C: constant cabin section (STA 4600-8200) through P2 / E1 (STA 6200) looking forward (seen from
    aft, starboard right); door arcs taken at their own centre stations (D1 4970, D2 8240), drawn just outside
    the skin line; hinge lines and open positions / swings of the free edges (build_door angles)."""
    cv = ds.cv
    x = FP.EXIT["cx"]
    t = np.linspace(0, 1, 721)
    S = F.section(np.full_like(t, x), t)
    cv.path(v.pts(S[:, 1:]), W_OBJ, closed=True)
    cv.line(v.pt(0, 0.80), v.pt(0, 2.90), W_FINE, CHAIN)
    cv.line(v.pt(-2.20, 0.0), v.pt(1.0, 0.0), W_FINE)
    X, Y = v.pt(1.0, 0.0)
    ds.text(X, Y + 3.0, "GROUND WL 0", 1.9, "label", "end", fill=MUTED, tag="lbl")
    cv.line(v.pt(-0.80, FP.DOOR_SILL_WL), v.pt(0.80, FP.DOOR_SILL_WL), W_THIN, (3.0, 1.2), color=MUTED)
    X, Y = v.pt(0.08, FP.DOOR_SILL_WL)
    ds.text(X, Y - 0.9, f"DOOR SILLS WL {FP.DOOR_SILL_WL * 1000:.0f}", 1.8, "label", "middle", fill=MUTED, tag="lbl")

    def arc(xs, za, zb, side, n=80, off=0.0):
        z = np.linspace(za, zb, n)
        return np.c_[side * (F.side_y(np.full_like(z, xs), z) + off), z]

    # windows (both sides: P2 / S2 at this station) and the exit plug
    for side in (1, -1):
        cv.path(v.pts(arc(x, FP.WIN_CZ - FP.WIN_HZ, FP.WIN_CZ + FP.WIN_HZ, side)), 1.1, color=INK)
    E = FP.EXIT
    cv.path(v.pts(arc(E["cx"], E["cz"] - E["hz"], E["cz"] + E["hz"], 1, off=0.022)), W_OBJ, color=INK)
    X, Y = v.pt(float(F.side_y(x, FP.WIN_CZ)), FP.WIN_CZ)
    ds.text(X - 2.0, Y + 0.7, "S2", 2.0, "label", "end", weight=600, tag="lbl")
    X, Y = v.pt(float(F.side_y(E["cx"], E["cz"] + E["hz"])), E["cz"] + E["hz"])
    ds.text(X - 1.5, Y + 1.0, "E1 (PLUG)", 1.9, "label", "end", tag="lbl")
    X, Y = v.pt(-float(F.side_y(x, FP.WIN_CZ)), FP.WIN_CZ)
    ds.text(X + 2.0, Y + 0.7, "P2", 2.0, "label", "start", weight=600, tag="lbl")
    # doors: closed panel arc, hinge, open position (open_deg of the constants), swing of the free edge
    for o, sgn, lab, col, off in ((FP.AIRSTAIR, 1.0, "D1", D1_COL, 0.020), (FP.CARGO, -1.0, "D2", D2_COL, 0.045)):
        ang = sgn * float(o.get("open_deg") or 0.0)
        pn = FP.door_panel(o)
        z0, z1 = pn["cz"] - pn["hz"], pn["cz"] + pn["hz"]
        A = arc(o["cx"], z0, z1, -1)
        hl = FP.hinge_line(o)
        zh = hl[2]
        yh = -float(F.side_y(o["cx"], zh))
        H = np.array([yh, zh])
        a = math.radians(ang)
        Rm = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
        Op = (A - H) @ Rm.T + H
        cv.path(v.pts(arc(o["cx"], z0, z1, -1, off=off)), W_OBJ, color=col)
        cv.path(v.pts(Op), W_FINE, PHANTOM, color=col)
        free = A[-1] if o["hinge"] == "bottom" else A[0]
        rr = np.linalg.norm(free - H)
        a0 = math.atan2(free[1] - H[1], free[0] - H[0])
        ts = np.linspace(a0, a0 + a, 40)
        cv.path(v.pts(np.c_[H[0] + rr * np.cos(ts), H[1] + rr * np.sin(ts)]), W_THIN, (1.2, 0.8), color=col)
        X, Y = v.pt(*H)
        cv.circle(X, Y, 0.9, w=W_FINE, fill=M.PAPER)
        if lab == "D1":
            ds.text(X + 1.8, Y + 3.4, f"D1 HINGE WL {zh * 1000:.0f}", 1.9, "label", "start", fill=col, tag="hinge")
        else:
            ds.text(X + 1.6, Y + 3.2, f"D2 HINGE WL {zh * 1000:.0f}", 1.9, "label", "start", fill=col, tag="hinge")
        e = Op[-1] if o["hinge"] == "bottom" else Op[0]
        X, Y = v.pt(*e)
        sta = f"STA {o['cx'] * 1000:.0f}"
        if lab == "D1":
            X, Y = v.pt(-0.84, 0.66)                    # clear area between the open door and the keel
            ds.text(X, Y, f"D1 AIRSTAIR ({sta})", 1.9, "label", "start", fill=col, tag="swing")
            ds.text(X, Y + 2.6, f"OPEN {abs(ang):.0f} DEG, FREE EDGE", 1.9, "label", "start", fill=col, tag="swing")
            ds.text(X, Y + 5.2, f"{float(Op[:, 1].min()) * 1000:.0f} ABOVE GROUND", 1.9, "label", "start", fill=col,
                    tag="swing")
        else:
            ds.text(X, Y - 1.6, f"D2 CARGO ({sta}) OPEN {abs(ang):.0f} DEG", 1.9, "label", "start", fill=col,
                    tag="swing")
    X, Y = v.pt(-0.40, 3.02)
    ds.text(X, Y, "PORT", 2.2, "label", "end", weight=600, tag="lbl")
    X, Y = v.pt(0.40, 3.02)
    ds.text(X, Y, "STBD", 2.2, "label", "start", weight=600, tag="lbl")


def draw_detail_window(ds, v, cx):
    cv = ds.cv
    P = FP.window_outline(cx, 360)
    cv.path(v.pts(P), W_OBJ, closed=True)
    # equivalent round-cornered rectangle (reference)
    Q = FP.opening_outline(dict(cx=cx, cz=FP.WIN_CZ, hx=FP.WIN_HX, hz=FP.WIN_HZ, r=FP.WIN_R), 16)
    cv.path(v.pts(Q), W_THIN, (1.2, 0.8), color=MUTED)
    centre_marks(ds, v, cx, FP.WIN_CZ, FP.WIN_HX, FP.WIN_HZ, 0.03)
    sh = ds.sh
    a = v.pt(cx - FP.WIN_HX, FP.WIN_CZ - FP.WIN_HZ)
    b = v.pt(cx + FP.WIN_HX, FP.WIN_CZ - FP.WIN_HZ)
    sh.dim(a, b, a[1] + 9.0, f"{FP.WIN_W * 1000:.0f}", "h", f1=v.pt(cx - FP.WIN_HX, FP.WIN_CZ),
           f2=v.pt(cx + FP.WIN_HX, FP.WIN_CZ))
    c = v.pt(cx + FP.WIN_HX, FP.WIN_CZ - FP.WIN_HZ)
    d = v.pt(cx + FP.WIN_HX, FP.WIN_CZ + FP.WIN_HZ)
    sh.dim(c, d, c[0] + 9.0, f"{FP.WIN_H * 1000:.0f}", "v", f1=v.pt(cx, FP.WIN_CZ - FP.WIN_HZ),
           f2=v.pt(cx, FP.WIN_CZ + FP.WIN_HZ))
    X, Y = v.pt(cx - FP.WIN_HX, FP.WIN_CZ + FP.WIN_HZ)
    ds.text(X - 1.0, Y - 5.8, f"LAME CURVE  |dx/{FP.WIN_HX * 1000:.0f}|^n + |dz/{FP.WIN_HZ * 1000:.1f}|^n = 1,"
            f"  n = {FP.WIN_N:g}", 2.0, "mono", "start", tag="det")
    ds.text(X - 1.0, Y - 2.8, f"dashed: equivalent R{FP.WIN_R * 1000:.0f} corners", 2.0, "label", "start", fill=MUTED,
            tag="det")
    X, Y = v.pt(cx, FP.WIN_CZ - FP.WIN_HZ)
    ds.text(X, Y + 13.5, f"CL WL {FP.WIN_CZ * 1000:.0f} = CABIN CROWN - {FP.WIN_CROWN_DROP * 1000:.0f}", 2.0, "mono",
            "middle", tag="det")


def draw_detail_exit(ds, v):
    cv = ds.cv
    E = FP.EXIT
    cv.path(v.pts(FP.opening_outline(E)), W_OBJ, closed=True)
    cx = FP.DOOR_WINDOWS["exit_hatch"]
    cv.path(v.pts(FP.window_outline(cx)), W_OBJ, closed=True)
    hd = FP.DOOR_DETAILS["exit_handle"]
    cv.path(v.pts(FP.opening_outline(hd, 8)), W_FINE, closed=True)
    centre_marks(ds, v, E["cx"], E["cz"], E["hx"], E["hz"], 0.04)
    sh = ds.sh
    zb = E["cz"] - E["hz"]
    a, b = v.pt(E["cx"] + E["hx"], zb), v.pt(E["cx"] - E["hx"], zb)
    sh.dim(a, b, a[1] + 8.0, f"{2 * E['hx'] * 1000:.0f}", "h")
    c, d = v.pt(E["cx"] - E["hx"], zb), v.pt(E["cx"] - E["hx"], E["cz"] + E["hz"])
    sh.dim(c, d, c[0] + 8.0, f"{2 * E['hz'] * 1000:.0f}", "v")
    # window sill above the hatch sill
    w0 = FP.WIN_CZ - FP.WIN_HZ
    e, f = v.pt(E["cx"] + E["hx"], zb), v.pt(E["cx"] + E["hx"], w0)
    sh.dim(e, f, e[0] - 7.0, f"{(w0 - zb) * 1000:.0f}", "v", f1=v.pt(cx, zb), f2=v.pt(cx, w0),
           text_at=(e[0] - 8.6, 0.5 * (e[1] + f[1])))
    X, Y = v.pt(E["cx"] - E["hx"], E["cz"] + E["hz"])
    ds.text(X + 0.5, Y - 1.2, f"R{E['r'] * 1000:.0f}", 2.0, "mono", "start", tag="det")
    Xh = max(v.pt(hd["cx"] - hd["hx"], hd["cz"])[0], v.pt(hd["cx"] + hd["hx"], hd["cz"])[0])
    _, Yh = v.pt(hd["cx"], hd["cz"])
    ds.text(Xh + 1.5, Yh, "HANDLE", 1.8, "label", "start", vcenter=True, tag="det")      # clear of the centre line


def legend(ds, x0, y0):
    items = [("OML silhouette / opening outline / door-panel seam", W_OBJ, None, INK),
             ("door clear opening (published size, door frame)", W_FINE, (1.4, 0.8), MUTED),
             ("hidden (plan: below max-breadth WL)", W_OBJ, (1.4, 0.8), MUTED), ("hinge line / door open position", W_FINE, PHANTOM, ACCENT),
             ("max-breadth WL, centre lines", W_THIN, CHAIN, LIGHT), ("door sills / cabin floor reference", W_THIN,
             (3.0, 1.2), MUTED), ("context: cockpit side window", W_FINE, None, MUTED),
             ("context: PRO dark mask outline", W_FINE, (1.2, 0.8), MUTED),
             ("frame station grid (fuselage.FRAMES)", W_GRID, None, GRID),
             ("rev A openings (the model before this refit)", W_THIN, (1.0, 0.8), GHOST)]
    ds.text(x0, y0, "LEGEND", 3.0, "label", "start", weight=600, tag="legend")
    M.legend_rows(ds, x0, y0 + 5.5, [(s, dict(w=w, dash=dash, color=col)) for s, w, dash, col in items], dy=4.2,
                  size=2.3)


# ============================================================================================ tables
def openings_rows(R):
    rows = []
    for r in R:
        side = "PORT" if r["side"] < 0 else "STBD"
        if r["kind"] == "window":
            shape = f"LAME n{FP.WIN_N:g}"
            note = f"in {r['host']}" if r.get("host") else ""
        else:
            o = r["o"]
            shape = f"R{o['r'] * 1000:.0f}"
            hl = FP.hinge_line(o)
            od = o.get("open_deg")
            note = {"bottom": f"CLEAR OPENING (published); hinge WL {hl[2] * 1000:.0f} at the sill, opens down {od:.0f} "
                              f"deg; no window" if hl else "",
                    "top": f"CLEAR OPENING (published); hinge WL {hl[2] * 1000:.0f} at the top, opens up {od:.0f} deg; "
                           f"window P4" if hl else "",
                    None: "hatch seam = opening; plug, removed inward; window S2, handle above"}[o.get("hinge")]
        rows.append((r["id"], r["name"], side, f"{r['x0'] * 1000:.0f}", f"{r['cx'] * 1000:.0f}",
                     f"{r['x1'] * 1000:.0f}", f"{r['z0'] * 1000:.0f}", f"{r['cz'] * 1000:.0f}",
                     f"{r['z1'] * 1000:.0f}", f"{r['w'] * 1000:.0f} x {r['h'] * 1000:.0f}", shape, note))
        if r["kind"] == "door":
            pn = r["panel"]
            rows.append((r["id"] + "s", "  PANEL SEAM", side, f"{r['px0'] * 1000:.0f}", f"{pn['cx'] * 1000:.0f}",
                         f"{r['px1'] * 1000:.0f}", f"{r['pz0'] * 1000:.0f}", f"{pn['cz'] * 1000:.0f}",
                         f"{r['pz1'] * 1000:.0f}", f"{r['pw'] * 1000:.0f} x {r['ph'] * 1000:.0f}",
                         f"R{pn['r'] * 1000:.0f}", "DOOR_PANELS: skin cut / door slab outline (drawing = render seams)"))
    return rows


def deviation_rows(R, ref, ph, rd=None):
    """(item, ours, delta vs drawing, delta vs the Pilatus render, delta vs rev A, evidence).  Deltas = ours -
    reference (mm).  Render deltas: ours - render-derived value after the scale + offset pattern fit (render_check)."""
    rows = []
    f0 = lambda v: f"{v:+.0f}" if abs(v) >= 0.5 else "0"
    fl = lambda vs: " / ".join(f0(v) for v in vs)
    by = {r["id"]: r for r in R}
    port_w = [by[f"P{i + 1}"]["cx"] for i in range(len(FP.FIXED_WINDOWS[-1]))]
    stbd_w = [r["cx"] for r in R if r["side"] > 0 and r["kind"] == "window"]
    ra = REV_A
    have = ref is not None
    rok = bool(rd and rd.get("ok"))

    def d(vals, refs):
        return fl([(a - b) * 1000 for a, b in zip(vals, refs)]) if have else "n/a"

    def rdev(names):
        """ours - render for the named pattern features."""
        if not rok:
            return "n/a"
        return fl([-rd["res"][rd["names"].index(n)] for n in names])

    if have:
        cw = [ref[k] for k in ("cabin_win_1", "cabin_win_2", "cabin_win_3", "door_cargo_win")]
        dw = np.mean([c[1] - c[0] for c in cw])
        dh = np.mean([c[3] - c[2] for c in cw])
        dz = np.mean([0.5 * (c[2] + c[3]) for c in cw])
    rows.append(("Cabin window W x H", f"{FP.WIN_W * 1000:.0f} x {FP.WIN_H * 1000:.0f}",
                 d([FP.WIN_W, FP.WIN_H], [dw, dh]) if have else "n/a",
                 fl([(FP.WIN_W - rd["win_w"]) * 1000, (FP.WIN_H - rd["win_h"]) * 1000]) if rok else "n/a",
                 fl([(FP.WIN_W - ra["win"][0]) * 1000, (FP.WIN_H - ra["win"][1]) * 1000]),
                 f"w/h ours {FP.WIN_W / FP.WIN_H:.2f}, render {rd['win_wh']:.2f}, photos 0.78-0.82 (s/n 3001 0.80); "
                 "drawing kept (primary)" if rok else "photos: w/h 0.78-0.82 (PRO s/n 3001 close-up 0.80)"))
    from math import gamma
    lame_fill = gamma(1 + 1 / FP.WIN_N) ** 2 / gamma(1 + 2 / FP.WIN_N)
    rfill = rd.get("win_fill") if rok else None
    rows.append(("Cabin window shape", f"Lame n {FP.WIN_N:g}", "fit n 4.23",
                 f"fill {rfill - lame_fill:+.3f}" if rfill else "n/a",
                 "rrect r60", f"equivalent rrect R{FP.WIN_R * 1000:.0f} (rms 1.2 mm); area / box: ours {lame_fill:.3f}"
                 + (f", render P1 blob {rfill:.3f}" if rfill else "")))
    rows.append(("Cabin window CL WL", f"{FP.WIN_CZ * 1000:.0f}", d([FP.WIN_CZ], [dz]) if have else "n/a",
                 f0((FP.WIN_CZ - (FP.DOOR_PANELS['door_airstair']['cz'] + FP.DOOR_PANELS['door_airstair']['hz'] -
                                  rd["win_cl_below_d1_top"])) * 1000) + "*" if rok else "n/a",
                 f0((FP.WIN_CZ - ra["win"][2]) * 1000),
                 f"= cabin crown - {FP.WIN_CROWN_DROP * 1000:.0f}; *render: CL below the D1 top seam (perspective "
                 "not modelled)"))
    rows.append(("Port windows P1-P3 CL", " / ".join(f"{x * 1000:.0f}" for x in port_w),
                 d(port_w, [0.5 * (ref[k][0] + ref[k][1]) for k in ("cabin_win_1", "cabin_win_2", "cabin_win_3")])
                 if have else "n/a", rdev(["P1", "P2", "P3"]),
                 fl([(a - b) * 1000 for a, b in zip(port_w, ra["port"])]),
                 "photo pattern (NGX broadside, port) fit residual " +
                 "/".join(f"{abs(v):.0f}" for v in ph["port_fit_res"][1:4]) + " mm"))
    p4 = FP.DOOR_WINDOWS["door_cargo"]
    rows.append(("Cargo-door window P4 CL", f"{p4 * 1000:.0f}",
                 d([p4], [0.5 * (ref["door_cargo_win"][0] + ref["door_cargo_win"][1])]) if have else "n/a",
                 rdev(["P4"]), f0((p4 - ra["door_win"]["door_cargo"]) * 1000),
                 "PRO s/n 3001 air-to-air and the render: 4th window aft of D1, in D2"))
    rows.append(("Stbd windows S1-S5 CL", " / ".join(f"{x * 1000:.0f}" for x in stbd_w),
                 d(stbd_w, ref["plan_win"][1]) if have and len(ref["plan_win"][1]) == 5 else "n/a", "",
                 fl([(a - b) * 1000 for a, b in zip(stbd_w, sorted(ra["stbd"] + [ra["door_win"]["exit_hatch"]]))]),
                 "from the PLAN view (S2 in E1); photo (NGX Kenia) pattern residual "
                 f"<= {max(abs(v) for v in ph['stbd_fit_res']):.0f} mm"))
    rows.append(("Stbd windows, photo absolute", "", "", "",
                 "", "Kenia, spinner/cowl registered: " + " / ".join(f"{v * 1000:.0f}" for v in ph["stbd_abs"]) +
                 " (perspective: aft under-read)"))
    A, C, E = FP.AIRSTAIR, FP.CARGO, FP.EXIT
    PA, PC = FP.DOOR_PANELS["door_airstair"], FP.DOOR_PANELS["door_cargo"]
    ra_a, ra_c, ra_e = ra["airstair"], ra["cargo"], ra["exit"]
    rvx = lambda o, rv: fl([(o["cx"] - o["hx"] - (rv[0] - rv[2])) * 1000, (o["cx"] + o["hx"] - (rv[0] + rv[2])) * 1000])
    rvz = lambda o, rv: fl([(o["cz"] - o["hz"] - (rv[1] - rv[3])) * 1000, (o["cz"] + o["hz"] - (rv[1] + rv[3])) * 1000])
    xs = lambda o: [o["cx"] - o["hx"], o["cx"] + o["hx"]]
    zs = lambda o: [o["cz"] - o["hz"], o["cz"] + o["hz"]]
    mm2 = lambda v: " / ".join(f"{a * 1000:.0f}" for a in v)
    s2 = (f"{(ref['s2_airstair'][1] - ref['s2_airstair'][0]) * 1000:.0f}" if have and "s2_airstair" in ref else "?")
    for lab, o, key, rn, rv, ev in (
            ("D1 panel seam fwd / aft", PA, "door_airstair", ["D1 fwd seam", "D1 aft seam"], ra_a,
             f"drawn outline = render seams ({rd['d1_w'] * 1000:.0f} wide)" if rok else "drawn outline"),
            ("D1 clear opening fwd / aft", A, "door_airstair", None, ra_a,
             f"published 0.61, centred in the seam (15 mm frame each side); sheet 2 draws {s2}"),
            ("D2 panel seam fwd / aft", PC, "door_cargo", ["D2 fwd seam", "D2 aft seam"], ra_c,
             f"drawn outline = render seams ({rd['d2_w'] * 1000:.0f} wide)" if rok else "drawn outline"),
            ("D2 clear opening fwd / aft", C, "door_cargo", None, ra_c, "published 1.35 W, centred in the seam"),
            ("E1 hatch fwd / aft", E, "plan_exit", None, ra_e, "plan = stbd detail; photo hatch seam (spinner-"
             "registered) " + " - ".join(f"{v * 1000:.0f}" for v in ph["exit_abs"]))):
        refs = [ref[key][0], ref[key][1]] if have and key in ref else None
        rows.append((lab, mm2(xs(o)), d(xs(o), refs) if refs else "n/a", rdev(rn) if rn else "",
                     rvx(o, rv), ev))
    for lab, o, key, rv, ev in (
            ("D1 panel seam low / top", PA, "door_airstair", ra_a, "drawn outline 1229-2629 (render top seam = anchor)"),
            ("D1 clear sill / top", A, "door_airstair", ra_a, "1.35 H published; sill = cabin floor, 25 mm frame"),
            ("D2 panel seam low / top", PC, "door_cargo", ra_c, "drawn outline; lower seam behind the wing fairing"),
            ("D2 clear sill / top", C, "door_cargo", ra_c, "1.32 H published; sill = D1 sill (floor)"),
            ("E1 hatch sill / top", E, "detail_exit", ra_e, "0.482 x 0.641 projected = 0.696 along the skin: FAR 23.807(b) "
             "19 x 26 in min.")):
        refs = [ref[key][2], ref[key][3]] if have and key in ref else None
        rows.append((lab, mm2(zs(o)), d(zs(o), refs) if refs else "n/a", "", rvz(o, rv), ev))
    rows.append(("D1 window", "none", "none" if have else "n/a", "none" if rok else "n/a", "removed",
                 "PRO s/n 3001 (air-to-air, door closed) and the render: no window"))
    rows.append(("Corner radii D1 / D2 / E1", f"{PA['r'] * 1000:.0f} / {PC['r'] * 1000:.0f} / {E['r'] * 1000:.0f}",
                 "0 / 0 / 0", "", fl([(PA['r'] - ra_a[4]) * 1000, (PC['r'] - ra_c[4]) * 1000, (E['r'] - ra_e[4]) * 1000]),
                 f"panel seams (drawn); clear openings R{A['r'] * 1000:.0f} / R{C['r'] * 1000:.0f}"))
    rows.append(("D2 / D1 seam width ratio", f"{PC['hx'] / PA['hx']:.3f}", "0", f"{PC['hx'] / PA['hx'] - rd['d2_over_d1']:+.3f}"
                 if rok else "n/a", "", f"photo (NGX broadside, door openings) {ph['d2_over_d1']:.2f}"))
    rows.append(("Open angle D1 / D2 (deg)", f"{A['open_deg']:.0f} / {C['open_deg']:.0f}", "", "",
                 f"{A['open_deg'] - 128:+.0f} / {C['open_deg'] - 100:+.0f}", "D1: free edge ~5 cm off the ground (contact ~164, section C-C); D2: render, door open (~120)"))
    return rows


def photo_rows(ph, rd=None):
    k = ", ".join(f"{v * 1000:.0f}" for v in ph["stbd_abs"])
    rows = []
    if rd and rd.get("ok"):
        rows.append(("Pilatus tech-data render", "current PC-12 (PRO), port",
                     f"orthographic-like CGI side view: D1 / D2 seams + P1-P4 fit OUR stations within "
                     f"{max(abs(v) for v in rd['res']):.0f} mm (rms {np.sqrt(np.mean(rd['res'] ** 2)):.0f}); seams "
                     f"{rd['d1_w'] * 1000:.0f} / {rd['d2_w'] * 1000:.0f} wide; window {rd['win_w'] * 1000:.0f} x "
                     f"{rd['win_h'] * 1000:.0f}; no D1 window"))
        rows.append(("Pilatus render, D2 open", "current PC-12 (PRO), port", "cargo door raised ~120 deg (free edge "
                     "~0.99 m above the hinge); sill at the cabin floor, 3 latches in the lower frame"))
    rows += [
        ("ngx_kenia_stbd_pilatus", "NGX, stbd broadside", f"S1-S5 at STA {k} (spinner/cowl registered, 166.7 px/m); "
         f"pattern fit to ours <= {max(abs(v) for v in ph['stbd_fit_res']):.0f} mm; E1 hatch ~0.49-0.50 x 0.62-0.64"),
        ("ngx_ownership_port_pilatus", "NGX, port broadside", "D1 open (0.61 = scale bar), P1-P3, D2 open (hinged at "
         f"top); pattern fit <= {max(abs(v) for v in ph['port_fit_res']):.0f} mm; D2/D1 width {ph['d2_over_d1']:.2f}"),
        ("pro3001_air_port34_pilatus", "PRO s/n 3001, port 3/4", "airstair door CLOSED: outline visible, NO window; "
         "4 windows aft of it (P1-P3 + P4 in D2)"),
        ("pro3001_cabin_port_aero25", "PRO s/n 3001, port close", "P1-P3 w/h 0.80, pitch ratio 0.75 (ours 0.76); "
         "P3 aft edge to D2 fwd edge 1.41 window widths (ours 1.45)"),
        ("pro3001_stbd_side_aero25", "PRO s/n 3001, stbd", "S1, E1 (outlined, red placard above its window = "
         "handle), S3-S5: same row as the NGX, S1-E1 the widest pitch"),
    ]
    return rows


def stage3_items():
    PA, PC = FP.DOOR_PANELS["door_airstair"], FP.DOOR_PANELS["door_cargo"]
    return [
        f"Door cut-outs: cut the skin and the door slabs along DOOR_PANELS (seams {2 * PA['hx'] * 1000:.0f} x "
        f"{2 * PA['hz'] * 1000:.0f} / {2 * PC['hx'] * 1000:.0f} x {2 * PC['hz'] * 1000:.0f}), build the jambs / door "
        f"frames along the clear openings AIRSTAIR / CARGO ({2 * FP.AIRSTAIR['hx'] * 1000:.0f} x "
        f"{2 * FP.AIRSTAIR['hz'] * 1000:.0f} / {2 * FP.CARGO['hx'] * 1000:.0f} x {2 * FP.CARGO['hz'] * 1000:.0f}); "
        "openings_field(), "
        "build_skin() door_edges, build_door() and build_doors() still use the clear openings only.",
        "Door kinematics: build_doors() passes open_angle 128 / 100 literally -- read AIRSTAIR['open_deg'] "
        f"{FP.AIRSTAIR['open_deg']:.0f} (free edge ~5 cm off the ground, section C-C) and CARGO['open_deg'] "
        f"{FP.CARGO['open_deg']:.0f}, the hinge WLs from hinge_line() "
        f"({FP.hinge_line(FP.AIRSTAIR)[2] * 1000:.0f} / {FP.hinge_line(FP.CARGO)[2] * 1000:.0f}, on the panel); "
        "airstair steps / handrails and the cargo-door struts move with the doors; the airstair door has NO window.",
        "model/interior.py: FLOOR_Z 1.12 -> the door sills WL "
        f"{FP.DOOR_SILL_WL * 1000:.0f} (L1 proposes 1259); carpet 4.46-9.52 and the seats must clear D1 "
        f"{(FP.AIRSTAIR['cx'] - FP.AIRSTAIR['hx']) * 1000:.0f}-{(FP.AIRSTAIR['cx'] + FP.AIRSTAIR['hx']) * 1000:.0f} "
        f"and D2 {(FP.CARGO['cx'] - FP.CARGO['hx']) * 1000:.0f}-{(FP.CARGO['cx'] + FP.CARGO['hx']) * 1000:.0f} "
        "(D1 moved +255 mm aft, D2 -685 mm fwd); window reveals from window_outline() (Lame n 4.2) at WIN_CZ "
        f"{FP.WIN_CZ * 1000:.0f} (+178 mm).",
        "model/interior.py build_structure(): frames at window +/- 0.40 m -> the Pilatus frames (fuselage.FRAMES "
        "FR16-FR33), interrupted at openings_table() (P3 / S3 at 6980 straddle FR25 6971: window-frame forging or local "
        "jog); the window-belt stringer gap 1.70 < z < 2.32 -> about 1.95-2.43 (belt 1995-2380).",
        "Emergency exit: build_doors() names it 'Type III' -- the drawn plug hatch is 0.482 x 0.641 m projected "
        "(0.696 along the skin, FAR 23.807(b) 19 x 26 in); E1 moved from STA 5520 to 6205, over the wing: check the "
        "wing-root fairing and flap clearance.",
        "Livery (model/livery.py): the swoosh (WL 1.28-1.52) crosses both door panels -- paint the panel slabs, not "
        "the clear openings; the PRO dark cockpit mask's aft edge (a per-airframe livery item, livery.MASK_SCHEMES) "
        f"stays ahead of the D1 forward seam (STA {(PA['cx'] - PA['hx']) * 1000:.0f}): s/n 3008 leaves a blue gap of "
        "~0.10 m at the top and ~0.27 m low, s/n 3036 runs to within ~0.05 m of it.",
        "Wing-root fairing (wing / details): hides the lower D2 seam in side view (drawn low seam WL "
        f"{(PC['cz'] - PC['hz']) * 1000:.0f}); the fairing must not cut into the D2 panel aft of STA "
        f"{(PC['cx'] - PC['hx']) * 1000:.0f}.",
        "refs/mbp.py '[vs model]' checks hard-code the rev-A stations (5.52 ... 8.72): switch them to "
        "fuselage_parts.openings_table() (rows now carry panel and open_deg).",
        "Door frames / jambs (build_doors seams): re-check the jamb loop pick and the D2 slab against the aft "
        "fuselage split SPLIT_AFT 9.85 (D2 panel ends at 8940).",
    ]


# ============================================================================================ sheet
def draw(ds):
    R = openings()
    try:
        ref = reference()
    except Exception as e:                                                # noqa: BLE001
        ref = None
        ds.log.append(f"reference not available ({e}); deviation table without drawing deltas")
    ph = photo_check()
    try:
        rd = render_check()
    except Exception as e:                                                # noqa: BLE001
        rd = dict(ok=False, note=f"render check failed: {e}")
    ds.log.append("render: " + ("not cached" if rd is None else rd.get("note", "")))
    ds.frame_and_title()

    # ---------------- views (1:20)
    box = (X0, Z0, X1, Z1)
    vport = ds.add_view(side_view("port", origin=(64.0, 64.0), scale=20, model_origin=(X0, Z1), box=box))
    vplan = ds.add_view(plan_view("plan", origin=(64.0, 247.0), scale=20, model_origin=(X0, 0.0),
                                  box=(X0, -YP, X1, YP)))
    vst = ds.add_view(stbd_view("stbd", origin=(64.0 + K20 * (X1 - X0), 348.0), scale=20, model_origin=(X0, Z1),
                                box=box))
    draw_elevation(ds, vport, -1, R, row_y=46.0)
    draw_plan(ds, vplan, R)
    draw_elevation(ds, vst, +1, R, row_y=330.0)
    xc = 64.0 + 0.5 * K20 * (X1 - X0)
    view_title(ds, xc, 190.0, "PORT ELEVATION", "SEEN FROM PORT - SCALE 1:20")
    view_title(ds, xc, 303.0, "PLAN", "SEEN FROM ABOVE, STARBOARD UP - SCALE 1:20")
    view_title(ds, xc, 474.0, "STARBOARD ELEVATION", "SEEN FROM STARBOARD, NOSE RIGHT - SCALE 1:20")
    legend(ds, 30.0, 500.0)
    scale_bar(ds, 250.0, 506.0, 20, length_m=2.0, step_m=0.5)

    # ---------------- details
    cxA = FP.FIXED_WINDOWS[-1][0]
    vA = ds.add_view(side_view("detA", origin=(492.0, 86.0), scale=5, model_origin=(cxA, FP.WIN_CZ),
                               box=(cxA - 0.22, FP.WIN_CZ - 0.26, cxA + 0.22, FP.WIN_CZ + 0.26)))
    draw_detail_window(ds, vA, cxA)
    view_title(ds, 497.0, 153.0, "DETAIL A - CABIN WINDOW", "P1 (TYPICAL, ALL 9) - SCALE 1:5")
    E = FP.EXIT
    vB = ds.add_view(stbd_view("detB", origin=(598.0, 86.0), scale=10, model_origin=(E["cx"], E["cz"]),
                               box=(E["cx"] - 0.3, E["cz"] - 0.36, E["cx"] + 0.3, E["cz"] + 0.36)))
    draw_detail_exit(ds, vB)
    view_title(ds, 598.0, 153.0, "DETAIL B - EXIT E1", "SEEN FROM STARBOARD - SCALE 1:10")
    vS = ds.add_view(aft_view("secA", origin=(772.0, 145.0), scale=30, model_origin=(0.0, 0.0),
                              box=(-2.3, -0.05, 1.0, 3.7)))
    draw_section(ds, vS, R)
    view_title(ds, 745.0, 153.0, "SECTION C-C - DOORS, HINGES", "STA 6205 LOOKING FWD - SCALE 1:30")
    # view references on the parent views: cutting plane C-C (port elevation; the letters A / B are the details),
    # detail circles A (P1) and B (E1)
    xa = 6.205
    M.cutting_plane(ds, vport, (xa, float(F.z_bot(xa)) - 0.06), (xa, float(F.z_top(xa)) + 0.06), "C",
                    look=(-1.0, 0.0))
    M.detail_circle(ds, vport, cxA, FP.WIN_CZ, 0.30, "A", at=(-0.7, -1.0))
    M.detail_circle(ds, vst, E["cx"], E["cz"], EXIT_DETAIL_R, "B", at=(0.7, -1.0))

    # ---------------- tables
    cols = [("ID", 9, "l"), ("OPENING", 33, "l"), ("SIDE", 12, "c"), ("FWD", 14, "r"), ("CL STA", 15, "r"),
            ("AFT", 14, "r"), ("SILL", 14, "r"), ("CL WL", 14, "r"), ("TOP", 14, "r"), ("W x H", 27, "r"),
            ("CORNER", 21, "l"), ("HINGE / NOTE", 184, "l")]
    y = table(ds, 455.0, 168.0, cols, openings_rows(R), title="OPENINGS (model/fuselage_parts.py) - STA / WL mm",
              zebra=lambda i: i % 2 == 1, size=2.6, row_h=4.2)
    ds.text(455.0, y + 3.6, "Windows: Lame curve n 4.2 (detail A), 9 in all. Doors: published clear openings "
            "(W x H, projected) inside the drawn panel seams (rows D1s / D2s). Section C-C: hinges and open positions.",
            2.1, "label", "start", fill=MUTED, tag="tnote")
    dcols = [("ITEM", 39, "l"), ("OURS", 45, "l"), ("D DWG", 27, "l"), ("D RENDER", 23, "l"), ("D REV A", 44, "l"),
             ("EVIDENCE / NOTE", 193, "l")]
    drows = deviation_rows(R, ref, ph, rd)
    y2 = table(ds, 455.0, y + 9.0, dcols, drows,
               title="DEVIATIONS (mm, OURS - REFERENCE): PILATUS NGX DRAWING, PILATUS RENDER, PHOTOS, REV A",
               zebra=lambda i: i % 2 == 1, size=2.45, row_h=4.1, font="label")
    ds.text(455.0, y2 + 3.6, "D DWG: vs the registered Pilatus NGX drawing (sheet-1 side view; starboard: its plan "
            "view; exit WLs: sheet-1 stbd detail). D RENDER: vs the Pilatus tech-data side render after a scale + offset "
            "fit of the port pattern. REV A: the model before this refit.",
            2.1, "label", "start", fill=MUTED, tag="tnote")
    ds.log.append("deviations: " + "; ".join(f"{r[0]}: {r[2]}" for r in drows))

    # ---------------- Stage 3 hand-over + notes
    y3 = M.notes(ds, 455.0, y2 + 8.0, 826.0, stage3_items(), title="STAGE 3 - WHAT MUST FOLLOW THESE CONSTANTS",
                 size=2.5, line_h=3.4)
    y4 = M.notes(ds, 455.0, y3 + 2.0, 826.0, [
        "Drawn from the opening constants of model/fuselage_parts.py on the Stage-2 OML of model/fuselage.py "
        "(sheet L1), never from the mesh. STA = mm aft of the datum (3000 fwd of the firewall); WL above the static "
        "ground line.",
        "Positions follow the registered Pilatus NGX drawing (port: side view; starboard: plan view -- the sheet-1 "
        "starboard detail repeats the port window stations and is not used). The drawn door outlines are the door-"
        "panel seams (the Pilatus tech-data render shows the same 0.64 / 1.40 m seams); the published door sizes "
        "(projected W x H) are the clear openings inside them.",
        "PRO: no window in the airstair door (s/n 3001 photo, door closed; Pilatus render). The cockpit side window is "
        "context only (model/cockpit_glazing.py, glazing sheet).",
    ], title="NOTES", size=2.5, line_h=3.4)
    pcols = [("PHOTO (refs/photos.json) / RENDER", 62, "l"), ("VARIANT / VIEW", 50, "l"), ("WHAT IT SHOWS FOR THE OPENINGS", 259, "l")]
    y5 = table(ds, 455.0, y4 + 2.0, pcols, photo_rows(ph, rd), title="PHOTO / RENDER EVIDENCE", size=2.3, row_h=3.9,
               font="label", zebra=lambda i: i % 2 == 1)
    ds.log.append(f"right column ends at y={y5:.0f} (title block starts at {ds.title_box[1]:.0f})")
    # background lines broken for lettering: rev-A ghost outlines under the door notes, window centre marks under
    # the window ids
    M.break_paths_at_text(ds, lambda d: d.get("color") == GHOST, pad=0.4)
    M.break_paths_at_text(ds, lambda d: d.get("dash") == CHAIN, pad=0.4,          # section C-C centre line
                          texts=lambda t: t.startswith(("D2 HINGE", "DOOR SILLS")))
    M.break_paths_at_text(ds, lambda d: d.get("w") in (W_GRID, W_THIN) and d.get("dash") == CHAIN
                          and d.get("color") in (MUTED, None), pad=0.4,
                          texts=lambda t: re.fullmatch(r"[PS]\d", t) is not None)

    draw_overlay(ds, vport, vplan, vst, vA, vB, R, ph, rd)


# ============================================================================================ overlay
def draw_overlay(ds, vport, vplan, vst, vA, vB, R, ph, rd=None):
    try:
        n = ds.ov_mbp(vport, "side")
        n += ds.ov_mbp(vplan, "plan")
        n += ds.ov_mbp(vst, "detail_stbd")
        n += ds.ov_mbp(vA, "side")
        n += ds.ov_mbp(vB, "detail_stbd")
        ds.log.append(f"overlay: {n} Pilatus polylines")
    except Exception as e:                                                # noqa: BLE001
        ds.log.append(f"overlay: reference not available ({e})")
        return
    # photo-derived stations (blue): starboard windows (Kenia, absolute registration and pattern fit)
    zc = FP.WIN_CZ
    ds.ov_marks(vst, np.c_[ph["stbd_abs"], np.full(len(ph["stbd_abs"]), zc + 0.26)],
                labels=[f"{v * 1000:.0f}" for v in ph["stbd_abs"]], size=1.9)
    ds.ov_marks(vst, np.c_[ph["stbd_fit"], np.full(len(ph["stbd_fit"]), zc - 0.26)], labels=None)
    ds.ov_marks(vport, np.c_[ph["port_fit"], np.full(len(ph["port_fit"]), zc - 0.26)], labels=None)
    X, Y = vst.pt(X1 - 0.05, 2.90)
    ds.ov_text(X, Y, "RED: sheet-1 STBD DETAIL (window stations repeat PORT - known error; exit hatch = plan view)",
               2.0, RED)
    ds.ov_text(X, Y + 3.0, "BLUE: photo window centres, NGX Kenia stbd: upper = spinner-registered, lower = "
               "scale+offset fit", 2.0, BLUE)
    X, Y = vport.pt(X0 + 0.05, 2.90)
    ds.ov_text(X, Y, "RED: Pilatus sheet-1 side view (outer door outlines: 0.64 x 1.40 / 1.40 x 1.47)", 2.0, RED)
    ds.ov_text(X, Y + 3.0, "BLUE: photo pattern (NGX Ownership, port) scale+offset fit: D1, P1-P3, D2 centres", 2.0,
               BLUE)
    if rd and rd.get("ok"):
        # Pilatus render: seams and window centres after the pattern fit (triangles above the openings)
        for nm, xf in zip(rd["names"], rd["fit"]):
            zz = (FP.DOOR_PANELS["door_airstair"]["cz"] + FP.DOOR_PANELS["door_airstair"]["hz"] + 0.05 if "seam" in nm
                  else FP.WIN_CZ + FP.WIN_HZ + 0.03)
            Xs, Ys = vport.pt(xf, zz)
            ds.ov.polygon([(Xs - 0.9, Ys - 1.4), (Xs + 0.9, Ys - 1.4), (Xs, Ys)], fill="#7A3FB0")
        ds.ov_text(X, Y + 6.0, "PURPLE: Pilatus tech-data render (port), scale+offset fit: D1/D2 panel seams, P1-P4 "
                   f"centres (max residual {np.max(np.abs(rd['res'])):.0f} mm)", 2.0, "#7A3FB0")
        try:
            f = render_overlay_png(rd, R)
            ds.log.append(f"render check image: {f}")
        except Exception as e:                                            # noqa: BLE001
            ds.log.append(f"render check image failed: {e}")


def render_overlay_png(rd, R, path=None):
    """Private check image (git-ignored): the Pilatus tech-data render with OUR port openings (panel seams, clear
    openings, windows) mapped by the pattern fit (x) and the D1 top seam + the same scale (z)."""
    if not rd or not rd.get("ok"):
        return None
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image
    im = np.asarray(Image.open(RENDER_FILE).convert("RGB"))
    c0, c1 = rd["coef"]
    s = rd["px_per_m"]
    ztop = FP.DOOR_PANELS["door_airstair"]["cz"] + FP.DOOR_PANELS["door_airstair"]["hz"]
    X = lambda x: (np.asarray(x) - c1) / c0
    Z = lambda z: rd["d1_top_px"] + (ztop - np.asarray(z)) * s
    fig = plt.figure(figsize=(16, 7.2), dpi=110)
    ax = fig.add_axes([0, 0, 1, 1])
    x0p, x1p, y0p, y1p = int(X(4.2)), int(X(9.4)), int(Z(3.0)), int(Z(0.8))
    ax.imshow(im[y0p:y1p, x0p:x1p], extent=(x0p, x1p, y1p, y0p))
    for r in R:
        if r["side"] > 0:
            continue
        if r["kind"] == "door":
            P = r["poutline"]
            ax.plot(X(P[:, 0]), Z(P[:, 1]), "-", color="#E0231C", lw=1.2)
            P = r["outline"]
            ax.plot(X(P[:, 0]), Z(P[:, 1]), "--", color="#1F6FD1", lw=1.0)
        else:
            P = r["outline"]
            ax.plot(X(P[:, 0]), Z(P[:, 1]), "-", color="#E0231C", lw=1.0)
    xs = np.linspace(4.2, 9.4, 300)
    ax.plot(X(xs), Z(F.z_top(xs)), ":", color="#0E6E62", lw=1.0)
    ax.plot(X(xs), Z(F.z_bot(xs)), ":", color="#0E6E62", lw=1.0)
    ax.plot(X(xs), Z(np.full_like(xs, FP.DOOR_SILL_WL)), "--", color="#0E6E62", lw=0.6)
    ax.text(x0p + 10, y0p + 25, "Pilatus PC-12 tech-data render (private reference) + OURS: red = panel seams / "
            "windows, blue dashed = clear openings, green dotted = OML crown/keel (centre plane: perspective), "
            f"green dashed = door sills WL {FP.DOOR_SILL_WL * 1000:.0f}.  x: pattern fit (max residual "
            f"{np.max(np.abs(rd['res'])):.0f} mm), z: D1 top seam + same scale", fontsize=8, color="k",
            bbox=dict(fc="w", ec="none", alpha=0.8))
    ax.set_xlim(x0p, x1p)
    ax.set_ylim(y1p, y0p)
    ax.axis("off")
    path = path or (M.OUT_OVERLAY / "L3_render_check.png")
    fig.savefig(path)
    plt.close(fig)
    return path


if __name__ == "__main__":
    M.main(["L3"] + sys.argv[1:])
