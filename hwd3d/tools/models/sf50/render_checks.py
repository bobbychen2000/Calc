#!/usr/bin/env python3 -B
"""
Check renders of the SF50 model (numpy rasteriser, raster.py): orthographic side / top / front views with dimension
annotations (model vs source) and perspective views, posed with the same pivot conventions the runtime uses.

    cd hwd3d && python3 -B tools/models/sf50/render_checks.py [names...]   -> docs/phase3/sf50_*.png
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                     # noqa: E402
from PIL import Image, ImageDraw, ImageFont            # noqa: E402

import sf50_kernel as K                                # noqa: E402
import sf50_geom as G                                  # noqa: E402
import raster as RS                                    # noqa: E402
import build_sf50 as B                                 # noqa: E402

OUT = HERE.parents[2] / "docs/phase3"
MODEL_GLB = HERE.parents[2] / "js/aircraft/models/sf50.glb"
CAPTIONS = {}   # file -> caption text (written to docs/phase3/SOURCES.json at the end; fix round 1 of Phase 3a)


def write_captions():
    """docs/phase3/SOURCES.json entries for the check renders written in this run: caption, licence notice, and the
    sha256 of js/aircraft/models/sf50.glb (the renders come from the same builder code; tools/models/test_models.mjs fails
    a caption whose hash is not the current file's, so a stale still cannot pass as current)."""
    import hashlib
    import json
    f = OUT / "SOURCES.json"
    S = json.loads(f.read_text()) if f.exists() else {}
    h = hashlib.sha256(MODEL_GLB.read_bytes()).hexdigest() if MODEL_GLB.exists() else None
    for name, cap in CAPTIONS.items():
        S[name] = {"caption": cap + " Rendered from the builder's meshes (tools/models/sf50/build_sf50.py build_parts) by the "
                   "numpy z-buffer rasteriser tools/models/sf50/raster.py; blue = model vs a published value, orange = inferred.",
                   "model": "SF50", "model_sha256": h,
                   "rendered_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime((OUT / name).stat().st_mtime)),
                   "made_by": "tools/models/sf50/render_checks.py",
                   "licence": "Own render of an own model (this repository): no third-party geometry, texture or photo; "
                              "original neutral livery, no manufacturer logo, no registration (D1)."}
    keys = sorted(S, key=lambda k: (k != "_note", k))
    f.write_text(json.dumps({k: S[k] for k in keys}, indent=1) + "\n")


# ------------------------------------------------------------------------------------------------ posing
def pose_parts(parts, st):
    """Return {part id: [(Mesh, mat)]} posed for state st (keys: gear_up 0..1, flaps deg, roll, pitch, yaw -1..1,
    doors {id: 0..1}, fan rad, ail_trim deg)."""
    S = dict(gear_up=0.0, flaps=0.0, roll=0.0, pitch=0.0, yaw=0.0, doors={}, fan=0.0, ail_trim=0.0)
    S.update(st)
    ang = {}
    world = {}

    def local(pid):
        p = parts[pid]
        pv = p.pivot
        if not pv:
            return np.eye(4)
        k = pv["kind"]
        a, tr = 0.0, None
        if k == "gear":
            a = pv["retract"] * S["gear_up"]
        elif k == "gear_door":
            a = pv["open"] if (pv.get("seq") == "down" and S["gear_up"] < 0.999) else 0.0
        elif k == "flap":
            f = min(S["flaps"], pv.get("max", 40))
            a = f
            tr = np.asarray(pv.get("travel", [0, 0, 0]), float) * f / pv.get("max", 40)
        elif k == "aileron":
            lo, hi = pv["range"]
            c = -pv.get("sign", 1) * S["roll"]
            a = c * hi if c >= 0 else -c * lo
        elif k == "ruddervator":
            lo, hi = pv["range"]
            pr = pv.get("pitchRange", pv["range"])
            c = S["pitch"]
            e = c * pr[0] if c >= 0 else -c * pr[1]
            a = float(np.clip(e + pv.get("side", 1) * S["yaw"] * pv.get("yawGain", 9.0), lo, hi))
        elif k == "rudder":
            lo, hi = pv["range"]
            a = S["yaw"] * hi if S["yaw"] >= 0 else -S["yaw"] * lo
        elif k == "door":
            return K.rotation_about(pv["axis"], pv["open"] * S["doors"].get(pid, 0.0), pv["origin"])
        elif k == "spin":
            return K.rotation_about(pv["axis"], S["fan"], pv["origin"])
        elif k == "tab":
            pa = ang.get(p.parent, 0.0)
            a = pv.get("gearing", 0.0) * pa + (S["ail_trim"] if parts[p.parent].pivot["kind"] == "aileron" and parts[p.parent].pivot.get("sign", 1) < 0 else 0.0)
            if "range" in pv:
                a = float(np.clip(a, *pv["range"]))
        ang[pid] = a
        M = K.rotation_about(pv["axis"], np.radians(a), pv["origin"])
        if tr is not None:
            M[:3, 3] += tr
        return M

    def W(pid):
        if pid in world:
            return world[pid]
        p = parts[pid]
        Pm = W(p.parent) if p.parent else np.eye(4)
        world[pid] = Pm @ local(pid)
        return world[pid]

    out = {}
    for pid, p in parts.items():
        M = W(pid)
        out[pid] = [(m.transformed(M) if not np.allclose(M, np.eye(4)) else m, mat) for m, mat in p.meshes]
    return out


def items(posed, skip=()):
    op, gl = [], []
    for pid, lst in posed.items():
        if pid in skip:
            continue
        for m, mat in lst:
            rgba, met, rough = K.MATERIALS[mat]
            rgba = list(rgba) + [1.0] * (4 - len(rgba))
            (gl if rgba[3] < 1 else op).append((m.V, m.F, m.N, rgba, met, rough))
    return op, gl


# ------------------------------------------------------------------------------------------------ annotation helpers
def font(sz):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            pass
    return ImageFont.load_default()


INK = (20, 60, 140)
INF = (170, 70, 20)


def dim(d, cam, p0, p1, text, off=(0, 0), col=INK, fsz=22, ext=True):
    """Dimension line between model points p0, p1 with an offset in pixels (perpendicular)."""
    x0, y0, _ = cam.project(np.asarray(p0, float))
    x1, y1, _ = cam.project(np.asarray(p1, float))
    ox, oy = off
    a, b = (x0 + ox, y0 + oy), (x1 + ox, y1 + oy)
    if ext:
        d.line([(x0, y0), a], fill=(150, 150, 150), width=1)
        d.line([(x1, y1), b], fill=(150, 150, 150), width=1)
    d.line([a, b], fill=col, width=2)
    v = np.array(b) - np.array(a)
    L = np.linalg.norm(v)
    if L > 1:
        u = v / L
        n = np.array([-u[1], u[0]])
        for P, s in ((np.array(a), 1), (np.array(b), -1)):
            tip = P
            q1 = P + s * 14 * u + 5 * n
            q2 = P + s * 14 * u - 5 * n
            d.polygon([tuple(tip), tuple(q1), tuple(q2)], fill=col)
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    f = font(fsz)
    lines = text.split("\n")
    w = max(d.textlength(l, font=f) for l in lines)
    h = fsz * 1.25 * len(lines)
    d.rectangle([mx - w / 2 - 6, my - h / 2 - 4, mx + w / 2 + 6, my + h / 2 + 2], fill=(255, 255, 255))
    for i, l in enumerate(lines):
        d.text((mx - d.textlength(l, font=f) / 2, my - h / 2 + i * fsz * 1.25), l, fill=col, font=f)


def label(d, xy, text, col=(30, 30, 30), fsz=22, anchor="la"):
    d.text(xy, text, fill=col, font=font(fsz), anchor=anchor)


def save(img, name, annot=None):
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    if annot:
        d = ImageDraw.Draw(im)
        annot(d)
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    im.save(p, optimize=True)
    CAPTIONS[name] = CAPTION_OF.get(name, name)
    print("wrote", p.relative_to(HERE.parents[2]), im.size)
    return p


CAPTION_OF = {
    "sf50_side.png": "SF50 check render: left side, orthographic, gear down, dimensioned (length, height, nose -> wing root LE, wheelbase).",
    "sf50_top.png": "SF50 check render: top view, orthographic, dimensioned (span to the outermost tip point, nose -> root LE / TE, fuselage width).",
    "sf50_front.png": "SF50 check render: front view, orthographic, gear down (track, height, V-tail and wing dihedral, upswept wing tips).",
    "sf50_34.png": "SF50 check render: 3/4 front, gear down, flaps up.",
    "sf50_34rear.png": "SF50 check render: rear 3/4, flaps 39 deg (TCDS 100 %), ruddervators half pull, roll right 0.4, cabin door open.",
    "sf50_gearup.png": "SF50 check render: from below, gear retracted (mains inward into the wing, nose forward [inf: directions]).",
    "sf50_nose.png": "SF50 check render: close range nose, windshield, cabin door, nose gear and lamp, cabin interior.",
    "sf50_tail.png": "SF50 check render: close range nacelle exhaust and mixer, V-tail, ruddervators and tabs, ventral fins / yaw SAS.",
    "sf50_inlet.png": "SF50 check render: close range dorsal inlet (raised D lip, heated lip finish), fan, cowl fillets into the spine.",
}


# ------------------------------------------------------------------------------------------------ views
def checks_by_name(checks):
    return {c["check"]: c for c in checks}


def view_side(posed, C, ss=2):
    cam = RS.Camera.ortho((0, 1, 0), (0, 0, 1), (5.62, 0, 1.62), 2.95, 1920, 1000)
    op, gl = items(posed)
    img = RS.render(op, cam, glass_items=gl, ssaa=ss)

    def annot(d):
        L = C["Overall length"]
        dim(d, cam, [G.X_NOSE, 0, G.HEIGHT], [G.X_TAIL, 0, G.HEIGHT], f"length {L['model']:.3f} m  (source {L['source_value']:.3f}: FAA ACD 30.7 ft, AFM Fig 1-1)",
            off=(0, -40))
        H = C["Overall height (static)"]
        dim(d, cam, [G.X_TAIL + 0.15, 0, 0], [G.X_TAIL + 0.15, 0, H["model"]], f"height\n{H['model']:.3f} m\n(src {H['source_value']:.3f})", off=(70, 0), fsz=20)
        WB = C["Wheelbase (tyre contacts)"]
        dim(d, cam, [G.X_NOSE_AXLE, 0, 0], [G.X_MAIN_AXLE, 0, 0], f"wheelbase {WB['model']:.3f} m  [inf: AFM Fig 1-1 scaled]",
            off=(0, 40), col=INF)
        dim(d, cam, [G.X_NOSE, 0, 0.30], [G.X_LE_FUS, 0, 0.30], "nose -> wing root LE 3.383 m (AFM 11.1 ft)", off=(0, 0), fsz=18)
        d.line([cam.project(np.array([0.5, 0, 0]))[:2], cam.project(np.array([10.6, 0, 0]))[:2]], fill=(120, 120, 120), width=1)
        label(d, (20, 20), "Cirrus SF50 (own parametric model, hwd3d M1) - left side, orthographic, gear down (nose doors open)", fsz=24)
        label(d, (20, 52), "blue = model vs published value; orange = inferred (read off the AFM three-view)", fsz=18, col=(90, 90, 90))
    return save(img, "sf50_side.png", annot)


def view_top(posed, C, ss=2):
    cam = RS.Camera.ortho((0, 0, -1), (-1, 0, 0), (5.45, 0, 1.5), 6.35, 1500, 1500)
    op, gl = items(posed)
    img = RS.render(op, cam, glass_items=gl, ssaa=ss)

    def annot(d):
        S = C["Wing span (overall)"]
        dim(d, cam, [3.6, -G.SPAN / 2, 0], [3.6, G.SPAN / 2, 0], f"span {S['model']:.3f} m  (source {S['source_value']:.3f}: FAA ACD 38.7 ft; EASA TCDS 11.67)",
            off=(0, -40), fsz=20)
        V = C["V-tail span, tip to tip"]
        dim(d, cam, [10.45, -G.VTAIL_SPAN / 2, 0], [10.45, G.VTAIL_SPAN / 2, 0], f"V-tail {V['model']:.3f} m (AFM 14.7 ft = {V['source_value']:.3f})",
            off=(0, 25), fsz=20)
        A = C["Wing reference area (m^2)"]
        label(d, (30, 1380), f"wing reference area (trapezoid to the full span): model {A['model']:.2f} m2, EASA TCDS 18.18 m2", fsz=20)
        TE = C["Nose -> wing root TE (fillet)"]
        dim(d, cam, [G.X_NOSE, -2.9, 0], [G.X_NOSE + TE["model"], -2.9, 0], f"nose -> root TE\n{TE['model']:.3f} m\n(AFM 18.3 ft)", off=(-60, 0), fsz=18)
        LE = C["Nose -> wing root LE"]
        dim(d, cam, [G.X_NOSE, -2.2, 0], [G.X_NOSE + LE["model"], -2.2, 0], f"-> root LE\n{LE['model']:.3f} m\n(AFM 11.1 ft)", off=(-10, 0), fsz=18)
        Wd = C["Fuselage max width (OML)"]
        dim(d, cam, [4.4, -float(G.half_w(4.4)), 0], [4.4, float(G.half_w(4.4)), 0], f"{Wd['model']:.2f} m [inf]", off=(0, 0), col=INF, fsz=16, ext=False)
        label(d, (20, 20), "Top view (orthographic), nose up", fsz=24)
    return save(img, "sf50_top.png", annot)


def view_front(posed, C, ss=2):
    cam = RS.Camera.ortho((1, 0, 0), (0, 0, 1), (5.0, 0, 1.55), 3.25, 1920, 1000)
    op, gl = items(posed)
    img = RS.render(op, cam, glass_items=gl, ssaa=ss)

    def annot(d):
        T = C["Main-gear track (tyre contacts)"]
        dim(d, cam, [0, -G.TRACK / 2, 0], [0, G.TRACK / 2, 0], f"track {T['model']:.3f} m (AFM 11.2 ft = {T['source_value']:.3f})", off=(0, 40))
        # V-tail angle
        e = np.array([0, np.cos(G.VT_DIHEDRAL), np.sin(G.VT_DIHEDRAL)])
        r0 = np.array([0, G.VT_ROOT_Y, G.VT_ROOT_Z])
        for s in (1, -1):
            a = r0 * [1, s, 1]
            b = a + 2.7 * e * [1, s, 1]
            d.line([cam.project(a)[:2], cam.project(b)[:2]], fill=INF, width=2)
            d.line([cam.project(a)[:2], cam.project(a + [0, s * 1.2, 0])[:2]], fill=INF, width=1)
        label(d, cam.project(np.array([0, 2.35, 3.05]))[:2], f"V-tail dihedral {np.degrees(G.VT_DIHEDRAL):.0f} deg\n[inf: AFM front view 37-39 deg]", col=INF, fsz=20)
        a = np.array([0, 1.0, float(G.wing_z_le(1.0))])
        b = np.array([0, 5.4, float(G.wing_z_le(5.4))])
        d.line([cam.project(a)[:2], cam.project(b)[:2]], fill=INF, width=2)
        label(d, cam.project(np.array([0, 3.0, 0.62]))[:2], f"wing dihedral {np.degrees(G.DIHEDRAL):.1f} deg [inf: AFM front view]", col=INF, fsz=20)
        H = C["Overall height (static)"]
        dim(d, cam, [0, -2.55, 0], [0, -2.55, H["model"]], f"{H['model']:.3f} m\n(src 3.322)", off=(0, 0), fsz=18)
        label(d, (20, 20), "Front view (orthographic), gear down, nose-gear doors open", fsz=24)
    return save(img, "sf50_front.png", annot)


def view_34(posed, name, eye, tgt, fov=34, W=1920, H=1080, ss=2, title=None):
    cam = RS.Camera.persp(eye, tgt, (0, 0, 1), fov, W, H)
    op, gl = items(posed)
    img = RS.render(op, cam, glass_items=gl, ssaa=ss)

    def annot(d):
        if title:
            label(d, (20, 20), title, fsz=24)
    return save(img, name, annot)


def main(names=None):
    t0 = time.time()
    parts = B.build_parts()
    checks, _ = B.verify(parts)
    C = checks_by_name(checks)
    down = pose_parts(parts, {})
    want = lambda n: names is None or n in names
    if want("side"):
        view_side(down, C)
    if want("top"):
        view_top(down, C)
    if want("front"):
        view_front(down, C)
    if want("34"):
        view_34(down, "sf50_34.png", (-2.6, -9.6, 4.4), (5.3, 0.2, 1.35), 36,
                title="3/4 view, gear down, flaps up (rasteriser check render)")
    if want("34rear"):
        p = pose_parts(parts, {"flaps": 39.0, "pitch": 0.5, "roll": 0.4, "doors": {"door_upper": 1.0, "door_lower": 1.0}})
        view_34(p, "sf50_34rear.png", (14.8, -7.6, 4.8), (5.6, 0.0, 1.5), 34,
                title="rear 3/4: flaps 39 deg (TCDS 100 %), ruddervators half pull, roll right 0.4, cabin door open")
    if want("gearup"):
        p = pose_parts(parts, {"gear_up": 1.0})
        view_34(p, "sf50_gearup.png", (2.0, -7.5, -1.6), (5.4, 0.0, 1.0), 40,
                title="from below, gear retracted: mains inward into the wing, nose forward, doors closed")
    if want("nose"):
        view_34(down, "sf50_nose.png", (0.0, -3.4, 2.5), (2.75, 0.0, 1.55), 42,
                title="close range: nose, windshield, cabin door, nose gear (landing light), cabin interior")
    if want("tail"):
        view_34(down, "sf50_tail.png", (11.6, -3.3, 3.2), (7.6, 0.0, 2.0), 40,
                title="close range: nacelle exhaust & mixer, V-tail, ruddervators & tabs, ventral fins / yaw SAS")
    if want("inlet"):
        view_34(down, "sf50_inlet.png", (3.9, -2.2, 3.3), (6.4, 0.0, 2.35), 38,
                title="close range: engine inlet (heated lip), fan, pylon NACA inlet")
    write_captions()
    print(f"done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
