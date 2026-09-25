"""
render.beauty -- photo-matched beauty renders of out/pc12.glb (Blender 5 / Cycles, CPU, OIDN, AgX).

    /opt/venv-blender/bin/python render/beauty.py [--glb out/pc12.glb] [--preset p1,p2|all]
            [--out DIR] [--size WxH] [--samples N] [--compare] [--set KEY=VALUE ...] [--list]
    (from pc12/; the system python3 re-executes itself in /opt/venv-blender, override with
    $BLENDER_PYTHON).  --fit NAME[,..]|all refits the cameras stored in overlays/vqa/cams_beauty.json.

Every preset renders out/renders/<preset>.png (+ <preset>.json: camera P / K R t, pose, lighting,
timings).  With --compare a preset that has a reference photo also writes
refs/cache/overlays/vqa/<preset>_compare.jpg (photo | render, same size, labelled) and
<preset>_blend.jpg (50 % blend, to judge the camera match); these contain the photo, so they stay in
the git-ignored cache.  --size is a bounding box: a photo-matched preset keeps its photo's aspect
ratio inside it (1600x1000 -> e.g. 1500x1000 for a 3:2 photo).  --set overrides any preset field for
one run (JSON values, dotted keys into nested dicts: --set exposure=0.4 --set pose.gear=1
--set 'grade={"white":0.9}'), for look development without editing the file.

The GLB is copied to a temp file before the import (another process may rebuild it meanwhile).
Parts 'structure' are hidden.  World coordinates in Blender == MODEL coordinates
(x = station aft of the datum, y = butt line + starboard, z = water line, ground = 0).

Presets (reference photos in refs/cache/photos/, cameras in refs/cache/overlays/*/):
  hangar_port34      MSN 3008 in the white delivery hangar, port 3/4 front, airstair open.  Photo
                     pro3008_port34_pilatus.webp (== cand/..._MSN-3008_130); camera
                     overlays/livery/cams.json 'port_hangar_130' (livery agent's fit, rms 7.7 px).
                     Modelled room: epoxy floor, white walls, OSB ceiling with LED strips, closed
                     mid-grey hangar door behind the camera (what the paint mirrors).
  apron_stbd34       MSN 3008 on the apron in sun, starboard 3/4 front.  Photo pro3008_stbd34_pilatus
                     (== cand/..._CL_IMG_0517); cams.json 'stbd_ground'.  HDRI ground + shadow catcher.
  nose_port_closeup  wide-angle low close-up of the port nose, airstair open (cand/..._MSN-3008_188);
                     camera fitted here (overlays/vqa/cams_beauty.json 'nose_188', rms ~36 px).
  air_below_left     air-to-air from below, gear UP (gear, braces and doors posed from the pivot
                     extras), prop motion-blurred at 1700 rpm, 1/160 s (cand/..._PC-12-PRO-N81DW);
                     cams.json 'stbd_air'.
  wing_from_cabin    right wing, radar pod and winglet at golden hour over Kata Tjuta
                     (cand/..._IMG_0459); camera fitted here ('wing_0459', rms ~17 px): the fit puts
                     the phone at the RIGHT COCKPIT SIDE WINDOW with its 2x lens (f ~3055 px of 2311,
                     hfov 41 deg); a prior at the first cabin window cannot fit (rms 37 px).  The
                     environment is tilted to the photo's visible horizon (two-point line), the domes
                     are ray-cast from photo pixels onto a plain 900 m below, and the fuselage /
                     interior are invisible to camera rays (they still cast shadows and reflect).
  top                telephoto from above-ahead over a snowy runway, gear down as in the photo
                     (cand/pil_PC12_048 -- an NGX in another livery, for the plan form); fitted here
                     ('top_048').  The runway texture is generated from the photo's markings projected
                     through the fitted camera onto the ground 119 m below (40.5 m wide -- Buochs is
                     40 m -- piano keys STA 331-360, bar 365, centre line BL -7.8).
  side_port_ortho    orthographic broadside from port (2 deg look-down so the contact shadows show),
                     white seamless studio (reference cand/pil_techdata_side_5000, Pilatus studio view).
  hero               low 3/4 front studio shot (no photo): charcoal cyclorama square to the camera,
                     glossy floor, car-studio softboxes; the camera re-aims and sets f from the posed
                     mesh (fills 90 % of the width), so the framing follows model changes.
A solved camera missing from the cache falls back to the preset's rough look-at camera.

Cameras: pinhole fits in the livery-agent format (p = rotation vector (3), t (3), f; X_cam = R X + t,
u = W/2 + f x/z, v = H/2 + f y/z, MODEL coordinates) are scaled to the render size; Blender's camera is
set up from K [R | t] exactly as render/blender_ortho.py does (sensor fit horizontal, shift from the
principal point).  The cameras fitted here keep their keypoints / on-line pixels / centre prior in
overlays/vqa/cams_beauty.json (numpy Levenberg-Marquardt, no scipy needed).

Lighting: Poly Haven HDRIs, all CC0 1.0 (https://polyhaven.com/license), downloaded once into
refs/cache/hdri/<id>_<res>.hdr by ensure_hdri() (source URLs appended to refs/cache/hdri/SOURCES.txt):
  white_studio_06                       bright white skylit studio: hangar, orthographic side view
  zwartkops_straight_afternoon          race-track straight, wide asphalt, clear sky: apron, nose
  kloofendal_43d_clear_puresky          clear sky, sun 43 deg: air-to-air
  qwantani_sunset_puresky               low sun: wing from the cockpit (sky dimmed, + sun lamp)
  kloofendal_overcast_puresky           soft overcast: top view over the runway
  studio_small_09                       softbox studio: hero reflections (low strength)
  (driving_school, kloofendal_48d_partly_cloudy_puresky: spares, listed in HDRIS)
Each HDRI is analysed once (<file>.sun.json: brightest region = sun azimuth / elevation, and the
horizontal irradiance E_h) so a preset places the sun in MODEL azimuth (0 deg = toward +x / aft,
90 deg = toward +y / starboard, the direction TOWARD the sun) -- chosen from each photo's shadows /
lit faces.  For the two ground shots the rotation also keeps the HDRI's asphalt straight in the
camera's view.  Air shots replace the puresky HDRIs' flat, sky-bright lower half with terrain radiance
(ground_albedo * E_h / pi) so undersides are dark as in the photos; camera_grade (hue / sat / value)
or camera_sky (a gradient) change only what CAMERA rays see of the sky (a polariser), not the light.
Ground: glossy epoxy floor (hangar), Cycles shadow catcher over the HDRI's own ground (apron, nose
close-up; side view: transparent film composited on white), charcoal cyclorama (hero), procedural
scrub desert with haze and Kata Tjuta domes (wing), procedural snowy runway (top).

Tone: AgX ('AgX - Punchy' look), per-preset exposure and white balance; the 16-bit output is then
graded to the 8-bit PNG (grade: levels black / white, mid-tone gamma, saturation) -- press/delivery
photos are graded like a camera JPEG (clipped whites, firmer mid-tones) while AgX rolls highlights
off softly; e.g. the hangar grade brings the white walls to the photo's 242 while the fuselage side
keeps the photo's measured blue (rows 186-202: photo 72/103/165, render ~71/104/159 before grade).

Materials after import (by GLB material name): paint_* = two-layer automotive / aviation paint: a
clear coat (Coat 1.0, roughness 0.03, IOR 1.5) over a metallic-flake base for the blues / navy /
silver / wing dark (PAINT_FLAKE: metallic 0.55-0.85, roughness 0.35-0.45, low dielectric specular
since it sits inside the lacquer) or a solid base for white / pinstripe / belly; trim_black glossy
lacquer; chrome metallic 1.0, roughness 0.05; glass / glass_windshield thin tinted glass (GLASS_TINT
transmission mixed with a two-surface Fresnel glossy reflection, the interior shows dimly behind real
reflections); prop blades glossy black; tyres matte rubber; de-ice boots satin black.

Pose (from the node extras 'pivot', same conventions as web/viewer/kinematics.js): gear 0 = down ..
1 = up (retract x pos about the gear axis; brace knees solved like model/brace.py:solve_knee,
upper link about A, lower link about the knee), nose doors 0 = closed .. 1 = open (default: open unless the gear is
locked up), doors 0..1 of
their 'open' angle, blade pitch deg (feather 62 on the ground), propeller clocking deg, prop rpm +
shutter for motion blur (air), flaps deg (+ Fowler travel).

Timings (1600x1000 box, default samples, OIDN; 2026-09-25, 4 CPUs shared with other agents).  Each
sidecar JSON records render wall time, render CPU time and cpu / cores = the wall time on idle cores:
  preset             size       samples  idle-est.   measured wall (load avg while rendering)
  hangar_port34      1500x1000   24 spp      64 s      168 s  (load 10.8)
  apron_stbd34       1333x1000   40 spp      38 s       94 s  (load 10.1)
  nose_port_closeup  1500x1000   40 spp      64 s      166 s  (load 11.5)
  air_below_left     1480x1000   48 spp      14 s       34 s  (load 10.6)
  wing_from_cabin    1600x900    48 spp      58 s      104 s  (load 7.5)
  top                1480x1000   48 spp      42 s      102 s  (load 10.7)
  side_port_ortho    1600x618    32 spp      43 s       93 s  (load 8.6)
  hero               1600x1000   32 spp      59 s      140 s  (load 9.5)
  (+ 1-3 s import / setup; 'top' adds ~30 s once per render size to generate the runway texture,
  cached in out/tmp/beauty/)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import warnings
from pathlib import Path

import numpy as np

# Blender 5 flags Material/World.use_nodes (always on from 6.0); setting it keeps 4.x compatibility
warnings.filterwarnings("ignore", message=".*use_nodes.*", category=DeprecationWarning)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GLB = ROOT / "out" / "pc12.glb"
CACHE = ROOT / "refs" / "cache"
HDRI_DIR = CACHE / "hdri"
PHOTO_DIR = CACHE / "photos"
VQA_DIR = CACHE / "overlays" / "vqa"
BEAUTY_CAMS = VQA_DIR / "cams_beauty.json"
OUT_DIR = ROOT / "out" / "renders"
BLENDER_PY = os.environ.get("BLENDER_PYTHON", "/opt/venv-blender/bin/python")

# =============================================================================================
# HDRIs (Poly Haven, CC0)
# =============================================================================================
HDRIS = {
    "white_studio_06": dict(res="4k", note="bright white skylit studio (hangar door light, side view)"),
    "driving_school": dict(res="4k", note="large sunny asphalt yard, distant trees (spare)"),
    "zwartkops_straight_afternoon": dict(res="4k", note="race-track straight: wide asphalt, clear sky, flat "
                                                         "grass horizon (apron, nose close-up)"),
    "kloofendal_43d_clear_puresky": dict(res="4k", note="clear deep-blue sky, high sun (air-to-air)"),
    "qwantani_sunset_puresky": dict(res="4k", note="low sun (wing from the cabin)"),
    "kloofendal_overcast_puresky": dict(res="2k", note="soft overcast (top view)"),
    "studio_small_09": dict(res="2k", note="softbox studio (hero reflections, low strength)"),
}
POLYHAVEN_FILES = "https://api.polyhaven.com/files/{id}"


def _download(url, dest):
    dest = Path(dest)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "pc12-beauty/1.0"})
        with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f, 1 << 20)
    except Exception as e:                       # fall back to curl (proxy / CA set up for it)
        print(f"  urllib failed ({e}); trying curl", flush=True)
        subprocess.run(["curl", "-sSfL", "-m", "600", "-o", str(tmp), url], check=True)
    tmp.replace(dest)


def ensure_hdri(hid, res=None):
    """Path of the Poly Haven HDRI <hid> at <res> (.hdr), downloading it once into refs/cache/hdri/."""
    res = res or HDRIS.get(hid, {}).get("res", "2k")
    HDRI_DIR.mkdir(parents=True, exist_ok=True)
    path = HDRI_DIR / f"{hid}_{res}.hdr"
    if path.exists() and path.stat().st_size > 1000:
        return path
    print(f"  downloading HDRI {hid} ({res}) from Poly Haven (CC0) ...", flush=True)
    meta = HDRI_DIR / f"{hid}.files.json"
    try:
        req = urllib.request.Request(POLYHAVEN_FILES.format(id=hid), headers={"User-Agent": "pc12-beauty/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            files = json.loads(r.read())
    except Exception:
        subprocess.run(["curl", "-sSfL", "-m", "60", "-o", str(meta), POLYHAVEN_FILES.format(id=hid)], check=True)
        files = json.loads(meta.read_text())
    url = files["hdri"][res]["hdr"]["url"]
    _download(url, path)
    (HDRI_DIR / "SOURCES.txt").open("a").write(
        f"{path.name}  {url}  Poly Haven, CC0 1.0 (https://polyhaven.com/license)\n")
    return path


# =============================================================================================
# cameras
# =============================================================================================
def rodrigues(r):
    r = np.asarray(r, float)
    th = np.linalg.norm(r)
    if th < 1e-12:
        return np.eye(3)
    k = r / th
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K


def rotvec(R):
    c = np.clip((np.trace(R) - 1) / 2, -1, 1)
    th = math.acos(c)
    if th < 1e-9:
        return np.zeros(3)
    if th > math.pi - 1e-6:
        A = (R + np.eye(3)) / 2
        k = np.sqrt(np.clip(np.diag(A), 0, None))
        i = int(np.argmax(k))
        k = A[i] / k[i]
        return th * k / np.linalg.norm(k)
    w = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]]) / (2 * math.sin(th))
    return th * w


def lookat_R(pos, target, up=(0, 0, 1), roll_deg=0.0):
    """OpenCV rotation (rows: image right, image down, look) for a camera at pos looking at target."""
    C = np.asarray(pos, float)
    f = np.asarray(target, float) - C
    f /= np.linalg.norm(f)
    r = np.cross(f, up)
    r /= np.linalg.norm(r)
    d = np.cross(f, r)
    R = np.stack([r, d, f])
    if roll_deg:
        a = math.radians(roll_deg)
        Rz = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
        R = Rz @ R
    return R


class Cam:
    """Pinhole (OpenCV axes, corner pixel origin) or orthographic camera in MODEL coordinates."""

    def __init__(self, R, C, f, W, H, cx=None, cy=None, ortho_width=None):
        self.R, self.C = np.asarray(R, float), np.asarray(C, float)
        self.f, self.W, self.H = float(f), int(W), int(H)
        self.cx = 0.5 * W if cx is None else float(cx)
        self.cy = 0.5 * H if cy is None else float(cy)
        self.ortho_width = ortho_width            # metres across the image (ortho) or None

    @property
    def aspect(self):
        return self.W / self.H

    def scaled_to(self, W, H):
        s = W / self.W
        return Cam(self.R, self.C, self.f * s, W, H, self.cx * s, self.cy * s, self.ortho_width)

    @property
    def K(self):
        return np.array([[self.f, 0, self.cx], [0, self.f, self.cy], [0, 0, 1.0]])

    @property
    def t(self):
        return -self.R @ self.C

    @property
    def P(self):
        if self.ortho_width:
            s = self.W / self.ortho_width
            P = np.zeros((3, 4))
            P[0, :3], P[1, :3] = s * self.R[0], s * self.R[1]
            P[0, 3] = self.cx - s * self.R[0] @ self.C
            P[1, 3] = self.cy - s * self.R[1] @ self.C
            P[2, 3] = 1.0
            return P
        return self.K @ np.c_[self.R, self.t]

    def project(self, X):
        X = np.atleast_2d(np.asarray(X, float))
        h = np.c_[X, np.ones(len(X))] @ self.P.T
        return h[:, :2] / h[:, 2:3]

    def to_json(self):
        return dict(K=self.K.tolist(), R=self.R.tolist(), t=self.t.tolist(), C=self.C.tolist(), P=self.P.tolist(),
                    width=self.W, height=self.H, pixel_origin="corner", ortho_width_m=self.ortho_width,
                    hfov_deg=None if self.ortho_width else math.degrees(2 * math.atan(self.W / 2 / self.f)))


def cam_from_fit(entry):
    """Livery-agent pinhole fit {p: [rotvec(3), t(3), f], W, H} -> Cam."""
    p = np.asarray(entry["p"], float)
    R = rodrigues(p[:3])
    t = p[3:6]
    return Cam(R, -R.T @ t, p[6], entry["W"], entry["H"])


def cam_lookat(pos, target, hfov, W, H, roll=0.0):
    R = lookat_R(pos, target, roll_deg=roll)
    f = 0.5 * W / math.tan(math.radians(hfov) / 2)
    return Cam(R, pos, f, W, H)


def load_fit(spec):
    """Solved camera from the cache ({'file': rel. to refs/cache, 'key'}) or None."""
    path = CACHE / spec["file"]
    try:
        d = json.loads(path.read_text())
        return d[spec["key"]]
    except Exception:
        return None


# ---- camera fitting (numpy Levenberg-Marquardt; the keypoints live in cams_beauty.json) ----------
def _proj_p(p, X, W, H):
    R = rodrigues(p[:3])
    Xc = np.atleast_2d(X) @ R.T + p[3:6]
    return np.c_[W / 2 + p[6] * Xc[:, 0] / Xc[:, 2], H / 2 + p[6] * Xc[:, 1] / Xc[:, 2]]


def fit_camera(entry, iters=200, verbose=True):
    """Refine entry['p'] from entry['keypoints'] = [[X(3), uv(2), weight], ...] and optional
    entry['on_lines'] = [[A(3), B(3), [uv, ...], weight]] (pixels on the projected 3-D segment AB) and
    entry['prior_C'] = [C(3), sigma_m] (soft prior on the camera centre).  Returns the new p and rms."""
    W, H = entry["W"], entry["H"]
    kp = entry.get("keypoints", [])
    lines = entry.get("on_lines", [])
    pri = entry.get("prior_C")
    fix_f = entry.get("fix_f", False)

    def resid(p):
        r = []
        for X, uv, w in kp:
            r.extend((w * (_proj_p(p, X, W, H)[0] - uv)).tolist())
        for A, B, uvs, w in lines:
            S = np.linspace(0, 1, 200)[:, None] * (np.asarray(B) - A) + A
            Q = _proj_p(p, S, W, H)
            for uv in uvs:
                r.append(w * float(np.min(np.linalg.norm(Q - uv, axis=1))))
        if pri is not None:
            C = -rodrigues(p[:3]).T @ p[3:6]
            r.extend(((C - pri[0]) / pri[1] * 5.0).tolist())
        if fix_f:
            r.append((p[6] - entry["p"][6]) * 1e3)
        return np.asarray(r, float)

    p = np.asarray(entry["p"], float).copy()
    lam = 1e-3
    r = resid(p)
    for _ in range(iters):
        J = np.empty((len(r), 7))
        for j in range(7):
            h = 1e-6 * max(1.0, abs(p[j])) if j < 6 else 1e-4 * p[6]
            q = p.copy()
            q[j] += h
            J[:, j] = (resid(q) - r) / h
        A = J.T @ J
        g = J.T @ r
        improved = False
        for _ in range(10):
            dp = -np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-12), g)
            rn = resid(p + dp)
            if rn @ rn < r @ r:
                p, r = p + dp, rn
                lam = max(lam / 3, 1e-9)
                improved = True
                break
            lam *= 5
        if not improved or np.linalg.norm(dp) < 1e-10:
            break
    res = [(_proj_p(p, X, W, H)[0] - uv) for X, uv, w in kp]
    rms = float(np.sqrt(np.mean([e @ e for e in res]))) if res else 0.0
    if verbose:
        C = -rodrigues(p[:3]).T @ p[3:6]
        print(f"  fit: C = {np.round(C, 3).tolist()} f = {p[6]:.0f} px "
              f"(hfov {math.degrees(2 * math.atan(W / 2 / p[6])):.1f} deg), keypoint rms {rms:.1f} px")
        for (X, uv, w), e in zip(kp, res):
            print(f"     {np.round(X, 3).tolist()} -> {uv}: {np.round(e, 1).tolist()}")
    return p, rms


# =============================================================================================
# presets
# =============================================================================================
LIVERY_CAMS = "overlays/livery/cams.json"
BEAUTY_CAMS_REL = "overlays/vqa/cams_beauty.json"

PRESETS = {
    "hangar_port34": dict(
        photo="pro3008_port34_pilatus.webp",
        photo_note="MSN 3008 delivery (== cand/pn_first-pc12-pro-hando_MSN-3008_130.webp)",
        camera=dict(fit=dict(file=LIVERY_CAMS, key="port_hangar_130"),
                    fallback=dict(pos=(-1.7, -3.74, 0.84), target=(6.6, 1.7, 1.8), hfov=65.0), W=1920, H=1280),
        env="hangar", hdri="white_studio_06", sun_az=None, hdri_rot=90.0, strength=1.5, exposure=1.0,
        room=dict(strip_strength=70.0, door=0.3), bounces=(5, 2, 3, 2, 8), samples=24, noise_threshold=0.04,
        white_balance=(5800.0, 0.0), grade=dict(white=0.86, gamma=1.18, sat=1.05),
        pose=dict(gear=0.0, door_airstair=1.0, pitch=62.0, prop_clock=0.0),
    ),
    "apron_stbd34": dict(
        photo="pro3008_stbd34_pilatus.webp",
        photo_note="MSN 3008 on the apron (== cand/pn_first-pc12-pro-hando_CL_IMG_0517.webp)",
        camera=dict(fit=dict(file=LIVERY_CAMS, key="stbd_ground"),
                    fallback=dict(pos=(-13.8, 17.8, 1.45), target=(7.0, 0.0, 1.8), hfov=29.4), W=1733, H=1300),
        # clear sky, high sun on the starboard side (the photo's lit starboard flank); the HDRI's asphalt
        # straight (toward its azimuth ~ -125 deg) is turned into the camera's view, which puts the sun at
        # model azimuth 48 deg (aft-starboard, elevation 53 deg)
        env="apron", hdri="zwartkops_straight_afternoon", sun_az=48.3, strength=1.0, exposure=0.6,
        ground_gain=3.0, samples=40,       # the photo apron (~0.4 lit) is lighter than race asphalt (~0.11)
        camera_grade=dict(sat=1.25, val=0.95), grade=dict(white=0.95, gamma=1.05, sat=1.1),
        pose=dict(gear=0.0, pitch=62.0, prop_clock=20.0),
    ),
    "nose_port_closeup": dict(
        photo="cand/pn_first-pc12-pro-hando_MSN-3008_188.webp",
        photo_note="MSN 3008 handover, port nose close-up (wide angle)",
        camera=dict(fit=dict(file=BEAUTY_CAMS_REL, key="nose_188"),
                    fallback=dict(pos=(0.5, -2.3, 1.5), target=(9.0, 2.6, 0.6), hfov=74.0), W=1950, H=1300),
        # high sun from starboard (photo: the man's shadow falls port-aft, the ground ahead of the nose
        # wheel is in the fuselage shadow); asphalt straight turned into the view as for apron_stbd34
        env="apron", hdri="zwartkops_straight_afternoon", sun_az=107.8, strength=1.0, exposure=0.6,
        ground_gain=3.0, samples=40,
        camera_grade=dict(sat=1.25, val=0.95), grade=dict(white=0.95, gamma=1.05, sat=1.1),
        pose=dict(gear=0.0, door_airstair=1.0, pitch=62.0, prop_clock=0.0),
    ),
    "air_below_left": dict(
        photo="cand/pn_first-pc12-pro-hando_PC-12-PRO-N81DW.webp",
        photo_note="N81DW (MSN 3008) air-to-air from below, gear up",
        camera=dict(fit=dict(file=LIVERY_CAMS, key="stbd_air"),
                    fallback=dict(pos=(25.4, 25.5, -12.4), target=(7.0, 0.0, 2.0), hfov=29.0), W=1924, H=1300),
        # sun on the starboard side (the photo's sunlit flank faces the camera, belly and wing undersides in
        # shade); terrain radiance below the horizon instead of the puresky HDRI's flat, sky-bright lower half
        env="air", hdri="kloofendal_43d_clear_puresky", sun_az=80.0, strength=1.0, exposure=0.3,
        ground_albedo=(0.13, 0.11, 0.08), camera_grade=dict(sat=1.15, val=0.95, hue=0.52),
        grade=dict(white=0.97, sat=1.08),
        pose=dict(gear=1.0, pitch=24.0, prop_clock=10.0, rpm=1700, shutter_s=1 / 160),
    ),
    "wing_from_cabin": dict(
        photo="cand/pn_first-pc12-pro-hando_IMG_0459.webp",
        photo_note="MSN 3008 over Kata Tjuta: right wing, tip pod and winglet from the right cockpit side window",
        camera=dict(fit=dict(file=BEAUTY_CAMS_REL, key="wing_0459"),
                    fallback=dict(pos=(3.9, 0.7, 2.15), target=(5.6, 7.5, 1.7), hfov=41.4), W=2311, H=1300),
        # low sun ahead (the domes are side-lit from the image left = forward, shadows fall aft / right;
        # the winglet's inboard face and the pod crown catch it)
        env="air_ground", hdri="qwantani_sunset_puresky", sun_az=180.0, strength=0.35, exposure=0.1,
        sun_lamp=dict(strength=7.0, colour=(1.0, 0.74, 0.48), el=9.0, angle=0.6),
        # the photo's hazy golden-hour sky: warm pale horizon, pale cyan above (camera rays only)
        camera_sky=((0.0, (0.80, 0.72, 0.58)), (0.03, (0.86, 0.80, 0.64)), (0.12, (0.72, 0.74, 0.70)),
                    (0.35, (0.55, 0.65, 0.72)), (1.0, (0.36, 0.50, 0.66))),
        grade=dict(black=0.03, white=0.95, gamma=1.05, sat=1.1),
        # world up from the photo's visible horizon (tilted: the aircraft banks a little)
        horizon=((0.0, 82.0), (2311.0, 152.0)), ground_depth=900.0,
        # Kata Tjuta domes placed by ray casting photo pixels onto the ground plane (photo px, 2311 x 1300):
        # (top u, top v, base u, base v, half-width px)
        domes=((660, 350, 600, 730, 450), (980, 210, 1150, 560, 400), (290, 245, 300, 430, 190),
               (30, 270, 0, 400, 150), (130, 370, 150, 560, 150), (360, 335, 380, 470, 120),
               (700, 275, 700, 420, 130), (1250, 360, 1250, 620, 200), (130, 615, 130, 700, 180),
               (800, 650, 800, 790, 220), (1450, 300, 1500, 480, 200)),
        camera_invisible=("fus_", "cowl_", "glazing_", "flight_deck", "cabin_interior", "door_", "exit_hatch",
                          "dorsal_fin", "antennas", "lights", "belly_fairing", "propeller", "blade_"),
        pose=dict(gear=1.0, pitch=24.0, prop_clock=0.0),
    ),
    "top": dict(
        photo="cand/pil_PC12_048.webp",
        photo_note="Pilatus press photo (NGX/PRO, other livery) from above-ahead over a snowy runway, gear down",
        camera=dict(fit=dict(file=BEAUTY_CAMS_REL, key="top_048"),
                    fallback=dict(pos=(-87.8, 2.3, 38.1), target=(7.0, 0.0, 2.0), hfov=10.6), W=5000, H=3378),
        env="runway", hdri="kloofendal_overcast_puresky", sun_az=None, hdri_rot=0.0, strength=1.2, exposure=-0.1,
        white_balance=(6000.0, 0.0), grade=dict(black=0.1, white=0.97, sat=1.3),
        ground_depth=119.0,
        pose=dict(gear=0.0, pitch=24.0, prop_clock=0.0, rpm=1700, shutter_s=1 / 500),
    ),
    "side_port_ortho": dict(
        photo="cand/pil_techdata_side_5000.webp",
        photo_note="Pilatus tech-data side view (NGX studio image; near-broadside perspective)",
        # framed like the photo (3500 x 1351): 209.3 px/m (spinner tip x 186 .. aft-most x 3200 = 14.40 m),
        # ground at row 985 -> 16.72 m wide, centred on STA 7.86 / WL 1.48
        camera=dict(ortho=dict(view="side_port", centre=(7.86, 0.0, 1.48), width_m=16.72, elev_deg=2.0),
                    W=3500, H=1351),
        env="studio_white", hdri="white_studio_06", sun_az=None, hdri_rot=90.0, strength=1.1, exposure=0.1,
        samples=32,
        pose=dict(gear=0.0, pitch=62.0, prop_clock=0.0),
    ),
    "hero": dict(
        photo=None,
        # low 3/4 front from port, ~50 mm-equivalent; 'frame' re-aims and sets f from the posed mesh so the
        # aircraft fills 90 % of the width wherever the model grows or shrinks
        camera=dict(fallback=dict(pos=(-12.5, -16.0, 1.05), target=(7.0, 0.0, 1.7), hfov=40.0), W=1600, H=1000,
                    frame=dict(fill=0.90, align=(0.50, 0.53))),
        env="studio_cyc", hdri="studio_small_09", sun_az=None, hdri_rot=200.0, strength=0.12, exposure=-0.4,
        cyc=dict(back=13.0, radius=7.0, colour=(0.007, 0.0075, 0.009), floor_rough=0.16, glow=5000.0),
        grade=dict(white=0.97, gamma=1.05, sat=1.05), samples=32, noise_threshold=0.04,
        pose=dict(gear=0.0, pitch=18.0, prop_clock=16.0),
    ),
}
DEFAULT_LOOK = "AgX - Punchy"
# hero lights: name, position, target, size (m), power (W), colour, lights the aircraft?, spread (deg).
# The aircraft is lit by a big high key from camera left and a low fill (+ the studio HDRI at low
# strength); the overhead box and the two rims are light-linked to the cyclorama ONLY: a soft pool of
# light and a grazing gradient on the glossy floor that ground the aircraft without washing out the
# deep metallic blue; 'cyc_glow' paints the halo on the backdrop.
HERO_LIGHTS = (   # name, pos, target, size, W, colour, on_floor, spread deg
    ("overhead", (7.5, 0.0, 10.0), (7.5, 0.0, 1.5), (18.0, 4.0), 14000.0, (1.0, 0.98, 0.96), False, 100.0),
    ("key", (-11.0, -6.0, 9.0), (5.0, 0.0, 1.4), (6.0, 4.0), 9000.0, (1.0, 0.97, 0.93), True, 55.0),
    ("rim_R", (20.0, 10.0, 4.5), (8.0, 0.0, 2.0), (2.0, 7.0), 7000.0, (0.86, 0.91, 1.0), False, 70.0),
    ("rim_L", (16.0, -14.0, 4.0), (8.0, 0.0, 2.0), (2.0, 7.0), 5000.0, (0.86, 0.91, 1.0), False, 70.0),
    ("fill_low", (-14.0, 3.0, 1.5), (4.0, 0.0, 1.2), (6.0, 2.0), 1000.0, (0.92, 0.95, 1.0), True, 90.0),
)
DEFAULT_BOUNCES = (6, 3, 4, 4, 12)          # max, diffuse, glossy, transmission, transparent
# metallic paints: (metallic, roughness) of the flake base under the clear coat (see Scene.materials)
PAINT_FLAKE = {"paint_blue": (0.7, 0.42), "paint_blue_light": (0.65, 0.4), "paint_navy": (0.6, 0.42),
               "paint_wing_dark": (0.55, 0.45), "paint_silver": (0.85, 0.35), "paint_stripe": (0.6, 0.35)}
GLASS_TINT = {"glass_windshield": (0.16, 0.175, 0.17), "glass": (0.12, 0.13, 0.13)}


def auto_frame(cam: Cam, pts, fill=0.9, align=(0.5, 0.5), iters=3):
    """Re-aim a perspective camera (position kept) at the image-plane bbox of pts and set f so that the
    bbox spans 'fill' of the width (or of the height, whichever binds); the bbox centre lands at
    align * (W, H) through the principal point (a lens shift only for align != 0.5)."""
    R, C = cam.R.copy(), cam.C.copy()
    for _ in range(iters):
        Xc = (pts - C) @ R.T
        Xc = Xc[Xc[:, 2] > 0.1]
        x, y = Xc[:, 0] / Xc[:, 2], Xc[:, 1] / Xc[:, 2]
        xc, yc = 0.5 * (x.min() + x.max()), 0.5 * (y.min() + y.max())
        R = lookat_R(C, C + R.T @ np.array([xc, yc, 1.0]))
    Xc = (pts - C) @ R.T
    Xc = Xc[Xc[:, 2] > 0.1]
    x, y = Xc[:, 0] / Xc[:, 2], Xc[:, 1] / Xc[:, 2]
    f = min(fill * cam.W / (x.max() - x.min()), fill * cam.H / (y.max() - y.min()))
    cx = align[0] * cam.W - f * 0.5 * (x.min() + x.max())
    cy = align[1] * cam.H - f * 0.5 * (y.min() + y.max())
    return Cam(R, C, f, cam.W, cam.H, cx, cy)


def preset_camera(name, box_W, box_H):
    """Camera for a preset scaled to fit the render box (keeps the preset/photo aspect)."""
    spec = PRESETS[name]["camera"]
    W0, H0 = spec["W"], spec["H"]
    s = min(box_W / W0, box_H / H0)
    W, H = int(round(W0 * s)), int(round(H0 * s))
    source = "fallback"
    if "ortho" in spec:
        o = spec["ortho"]
        el = math.radians(o.get("elev_deg", 0.0))
        look = np.array([0.0, math.cos(el), -math.sin(el)])          # side_port: from -y toward +y
        R = np.stack([np.array([1.0, 0, 0]), np.cross(look, [1.0, 0, 0]), look])
        C = np.asarray(o["centre"], float) - 60.0 * look
        return Cam(R, C, 1.0, W, H, ortho_width=o["width_m"]), "ortho"
    cam = None
    if "fit" in spec:
        e = load_fit(spec["fit"])
        if e is not None:
            cam = cam_from_fit(e)
            source = f"{spec['fit']['file']}:{spec['fit']['key']}"
    if cam is None:
        fb = spec["fallback"]
        cam = cam_lookat(fb["pos"], fb["target"], fb["hfov"], W0, H0, fb.get("roll", 0.0))
    return cam.scaled_to(W, H), source


# =============================================================================================
# Blender scene
# =============================================================================================
def gl2b(v):
    """glTF vector -> Blender local (importer convention: X = x, Y = -z, Z = y)."""
    return (float(v[0]), -float(v[2]), float(v[1]))


def gl2m(v):
    """glTF vector -> MODEL (x = gl.z, y = gl.x, z = gl.y)."""
    return np.array([v[2], v[0], v[1]], float)


def m2b(v):
    """MODEL vector -> Blender local frame of the imported hierarchy (via glTF)."""
    return gl2b((v[1], v[2], v[0]))


def solve_knee(A, B, L1, L2, axis, bend_ref):
    """model/brace.py:solve_knee (numpy copy; runs inside Blender's python)."""
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    d = B - A
    d = d - axis * np.dot(d, axis)
    D = min(np.linalg.norm(d), L1 + L2 - 1e-9)
    u = d / max(D, 1e-12)
    a = (L1 ** 2 - L2 ** 2 + D ** 2) / (2 * D)
    h = math.sqrt(max(L1 ** 2 - a ** 2, 0.0))
    perp = np.cross(axis, u)
    if np.dot(perp, bend_ref) < 0:
        perp = -perp
    return A + a * u + h * perp


def rot_about(axis, deg, origin, P):
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    th = math.radians(deg)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    R = np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K
    return R @ (np.asarray(P, float) - origin) + origin


def signed_angle(u, v, n):
    n = np.asarray(n, float) / np.linalg.norm(n)
    a = u - n * np.dot(u, n)
    b = v - n * np.dot(v, n)
    return math.atan2(np.dot(n, np.cross(a, b)), np.dot(a, b))


def _to_py(x):
    if hasattr(x, "to_dict"):
        return {k: _to_py(v) for k, v in x.to_dict().items()}
    if isinstance(x, dict):
        return {k: _to_py(v) for k, v in x.items()}
    if hasattr(x, "to_list"):
        return x.to_list()
    if isinstance(x, (list, tuple)):
        return [_to_py(v) for v in x]
    try:
        return list(x) if not isinstance(x, (str, int, float)) else x
    except TypeError:
        return x


class Scene:
    def __init__(self, glb, quiet=True):
        import bpy
        from mathutils import Matrix
        self.bpy = bpy
        self.tmpdir = Path(tempfile.mkdtemp(prefix="pc12_beauty_"))
        src = Path(glb)
        local = self.tmpdir / "model.glb"
        shutil.copyfile(src, local)                  # snapshot: the GLB may be rebuilt meanwhile
        self.glb_src, self.glb_mtime = str(src), src.stat().st_mtime
        t = time.time()
        with _quiet(quiet):
            bpy.ops.wm.read_factory_settings(use_empty=True)
            bpy.ops.import_scene.gltf(filepath=str(local))
        self.t_import = time.time() - t
        roots = [o for o in bpy.data.objects if o.parent is None]
        Rz = Matrix.Rotation(math.pi / 2, 4, "Z")          # Blender (y, -x, z) -> model (x, y, z)
        for o in roots:
            o.matrix_world = Rz @ o.matrix_world
        bpy.context.view_layer.update()
        self.sc = bpy.context.scene
        self.parts = {}                                     # part id -> node object
        for o in bpy.data.objects:
            if "part" in o.keys():
                self.parts.setdefault(str(o["part"]), o)
        self.pivot = {}
        for pid, o in self.parts.items():
            if "pivot" in o.keys():
                self.pivot[pid] = _to_py(o["pivot"])
        self.meshes = [o for o in bpy.data.objects if o.type == "MESH"]
        self.chain = {o.name: self._chain(o) for o in self.meshes}
        self._extra = []

    @staticmethod
    def _chain(o):
        c = []
        while o is not None:
            if "part" in o.keys():
                c.append(str(o["part"]))
            o = o.parent
        return c

    def meshes_of(self, prefixes):
        return [o for o in self.meshes if any(c.startswith(p) for c in self.chain[o.name] for p in prefixes)]

    # ------------------------------------------------------------------ visibility
    def visible_points(self, max_per_mesh=4000):
        """World vertices (MODEL axes, subsampled) of the render-visible aircraft meshes, posed."""
        dg = self.bpy.context.evaluated_depsgraph_get()
        out = []
        for o in self.meshes:
            if o.hide_render or not o.visible_camera:
                continue
            me = o.evaluated_get(dg).data
            n = len(me.vertices)
            if n == 0:
                continue
            co = np.empty(n * 3, np.float32)
            me.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3)[:: max(1, n // max_per_mesh)]
            M = np.array(o.matrix_world)
            out.append(co @ M[:3, :3].T + M[:3, 3])
        return np.vstack(out)

    def hide(self, prefixes):
        for o in self.meshes_of(prefixes):
            o.hide_render = True

    def camera_invisible(self, prefixes):
        for o in self.meshes_of(prefixes):
            o.visible_camera = False

    # ------------------------------------------------------------------ pose
    def _rot_local(self, pid, deg):
        o = self.parts.get(pid)
        pv = self.pivot.get(pid)
        if o is None or pv is None:
            return
        from mathutils import Quaternion
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = Quaternion(gl2b(pv["axis"]), math.radians(deg))

    def pose(self, gear=0.0, nose_doors=None, door_airstair=0.0, door_cargo=0.0, pitch=0.0, prop_clock=0.0,
             flaps=0.0, rpm=0.0, shutter_s=0.0, **_):
        P = self.pivot
        # doors (open angle in radians)
        for pid, v in (("door_airstair", door_airstair), ("door_cargo", door_cargo)):
            if pid in P and v:
                self._rot_local(pid, math.degrees(P[pid]["open"]) * v)
        # gear + nose clamshells (open unless the gear is locked up, as in the viewer; the GLB builds them at
        # pivot 'rest' = 1 = open)
        if nose_doors is None:
            nose_doors = 0.0 if gear >= 1 - 1e-6 else 1.0
        for pid in ("gear_main_R", "gear_main_L", "gear_nose"):
            if pid in P:
                self._rot_local(pid, P[pid]["retract"] * gear)
        for pid in ("gear_door_NR", "gear_door_NL"):
            if pid in P:
                self._rot_local(pid, P[pid]["open"] * (nose_doors - P[pid].get("rest", 0.0)))
        # braces: B follows the gear leg; knee from solve_knee; upper link about A, lower about the knee
        knees = {}
        for pid in ("brace_main_R_up", "brace_main_L_up", "brace_nose_up"):
            pv = P.get(pid)
            if pv is None or pv.get("gear") not in P:
                continue
            g = P[pv["gear"]]
            A, B0, K0 = (np.asarray(pv[k], float) for k in ("A", "B0", "K0"))
            ax = gl2m(pv["axis"])
            B = rot_about(gl2m(g["axis"]), g["retract"] * gear, gl2m(g["origin"]), B0)
            K = solve_knee(A, B, pv["L1"], pv["L2"], ax, np.asarray(pv["bend"], float))
            ua = signed_angle(K0 - A, K - A, ax)
            la = signed_angle(B0 - K0, B - K, ax) - ua
            self._rot_local(pid, math.degrees(ua))
            lo = pid.replace("_up", "_lo")
            if lo in P:
                self._rot_local(lo, math.degrees(la))
            knees[pid] = K.round(4).tolist()
        # flaps (Fowler: rotate + travel)
        for pid in ("flap_R", "flap_L"):
            pv = P.get(pid)
            if pv is None or not flaps:
                continue
            self._rot_local(pid, flaps)
            mx = pv.get("max", 40.0)
            tr = np.asarray(pv.get("travel", (0, 0, 0)), float) * flaps / mx
            o = self.parts[pid]
            o.location = tuple(np.asarray(o.location) + np.asarray(m2b(tr)))
        # propeller: blade pitch, clocking, spin blur
        for k in range(1, 6):
            self._rot_local(f"blade_{k}", pitch)
        prop = self.parts.get("propeller")
        pv = P.get("propeller")
        if prop is not None and pv is not None:
            ax = gl2b(pv["axis"])
            prop.rotation_mode = "AXIS_ANGLE"
            a0 = math.radians(prop_clock)
            prop.rotation_axis_angle = (a0, *ax)
            if rpm and shutter_s:
                fps = self.sc.render.fps
                dth = rpm / 60.0 * 2 * math.pi / fps            # rotation per frame
                self.sc.frame_set(1)
                for fr, a in ((0, a0 - dth), (1, a0), (2, a0 + dth)):
                    prop.rotation_axis_angle = (a, *ax)
                    prop.keyframe_insert("rotation_axis_angle", index=0, frame=fr)
                ad = prop.animation_data
                if ad and ad.action:
                    try:
                        for fc in _fcurves(ad):
                            for kp in fc.keyframe_points:
                                kp.interpolation = "LINEAR"
                    except Exception:
                        pass
                self.sc.frame_set(1)
                self.sc.render.use_motion_blur = True
                self.sc.render.motion_blur_shutter = shutter_s * fps
                for obj in (self.sc.render, self.sc.cycles):
                    try:
                        obj.motion_blur_position = "CENTER"
                    except Exception:
                        pass
        self.bpy.context.view_layer.update()
        return dict(knees=knees)

    # ------------------------------------------------------------------ materials
    def _bsdf(self, m):
        if m is None or m.node_tree is None:
            return None
        for n in m.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                return n
        return None

    def materials(self, paint=None):
        """Beauty materials over the GLB ones (matched by material name).  Paint = two layers as in real
        automotive/aviation metallic paint: a pigment + aluminium-flake base (Metallic > 0, tinted by the
        base colour, blurred by the flake roughness, low dielectric specular because it sits INSIDE the
        lacquer) under a glossy clear coat (Coat 1.0, IOR 1.5, roughness 0.03) that carries the sharp
        white reflections.  paint: optional {material: (metallic, roughness)} overrides."""
        bpy = self.bpy
        metal_paint = dict(PAINT_FLAKE)
        metal_paint.update(paint or {})
        for m in bpy.data.materials:
            b = self._bsdf(m)
            if b is None:
                continue
            n = m.name
            inp = b.inputs
            if n.startswith("paint_") or n == "trim_black":
                if n in metal_paint:
                    inp["Metallic"].default_value, inp["Roughness"].default_value = metal_paint[n]
                    inp["Specular IOR Level"].default_value = 0.2
                else:                                   # solid colours (white, pinstripe, belly, black trim)
                    inp["Metallic"].default_value = 0.0
                    inp["Roughness"].default_value = 0.3 if n != "trim_black" else 0.2
                    inp["Specular IOR Level"].default_value = 0.25
                inp["Coat Weight"].default_value = 1.0
                inp["Coat Roughness"].default_value = 0.03
                inp["Coat IOR"].default_value = 1.5
            elif n == "chrome":
                inp["Base Color"].default_value = (0.85, 0.86, 0.88, 1)
                inp["Metallic"].default_value, inp["Roughness"].default_value = 1.0, 0.05
            elif n == "exhaust_polished":
                inp["Roughness"].default_value = 0.12
            elif n == "tire":
                inp["Base Color"].default_value = (0.028, 0.028, 0.03, 1)
                inp["Roughness"].default_value = 0.88
                inp["Specular IOR Level"].default_value = 0.3
            elif n == "deice_boot":
                inp["Base Color"].default_value = (0.018, 0.02, 0.022, 1)
                inp["Metallic"].default_value, inp["Roughness"].default_value = 0.0, 0.42
            elif n in ("glass", "glass_windshield"):
                # neutral grey-green tint (windshield laminate lighter than the cabin acrylic)
                self._thin_glass(m, tint=GLASS_TINT[n])
            elif n == "prop_blade":                      # glossy black composite blades
                inp["Base Color"].default_value = (0.012, 0.012, 0.014, 1)
                inp["Roughness"].default_value = 0.3
            elif n in ("wheel", "gear_leg"):
                inp["Roughness"].default_value = 0.28

    def _thin_glass(self, m, tint, rough=0.015, ior=1.52):
        nt = m.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        tr.inputs["Color"].default_value = (*tint, 1)
        gl = nt.nodes.new("ShaderNodeBsdfGlossy")
        gl.inputs["Color"].default_value = (1, 1, 1, 1)
        gl.inputs["Roughness"].default_value = rough
        fr = nt.nodes.new("ShaderNodeFresnel")
        fr.inputs["IOR"].default_value = ior
        # two surfaces of a thin pane: ~2x the single-surface Fresnel reflectance (0.04 -> ~0.08 at normal
        # incidence), saturating toward grazing
        mx = nt.nodes.new("ShaderNodeMath")
        mx.operation = "MULTIPLY_ADD"
        mx.inputs[1].default_value = 0.9
        mx.inputs[2].default_value = 0.05
        nt.links.new(fr.outputs[0], mx.inputs[0])
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(mx.outputs[0], mix.inputs[0])
        nt.links.new(tr.outputs[0], mix.inputs[1])
        nt.links.new(gl.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs[0])
        try:
            m.surface_render_method = "BLENDED"
        except Exception:
            pass

    def new_material(self, name, color=(0.8, 0.8, 0.8), rough=0.5, metallic=0.0, coat=0.0, spec=0.5):
        m = self.bpy.data.materials.new(name)
        try:
            m.use_nodes = True
        except Exception:
            pass
        b = self._bsdf(m)
        b.inputs["Base Color"].default_value = (*color, 1)
        b.inputs["Roughness"].default_value = rough
        b.inputs["Metallic"].default_value = metallic
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.05
        b.inputs["Specular IOR Level"].default_value = spec
        return m

    # ------------------------------------------------------------------ geometry helpers
    def plane(self, name, size, centre=(0, 0, 0), normal=(0, 0, 1), mat=None, uv_scale=None):
        bpy = self.bpy
        from mathutils import Matrix, Vector
        me = bpy.data.meshes.new(name)
        h = size / 2
        me.from_pydata([(-h, -h, 0), (h, -h, 0), (h, h, 0), (-h, h, 0)], [], [(0, 1, 2, 3)])
        me.update()
        if uv_scale is not None:
            uv = me.uv_layers.new(name="UVMap")
            for i, (u, v) in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
                uv.data[i].uv = (u, v)
        o = bpy.data.objects.new(name, me)
        self.sc.collection.objects.link(o)
        n = Vector(normal).normalized()
        q = Vector((0, 0, 1)).rotation_difference(n)
        o.matrix_world = Matrix.Translation(Vector(centre)) @ q.to_matrix().to_4x4()
        if mat is not None:
            me.materials.append(mat)
        self._extra.append(o)
        return o

    def area_light(self, name, pos, target, size, power, color=(1, 1, 1), spread_deg=None):
        """Rectangular area light at pos facing target (size a x b m, power W); not seen by the camera.
        spread_deg < 180 focuses it like a softbox with a honeycomb grid."""
        from mathutils import Vector
        ld = self.bpy.data.lights.new(name, "AREA")
        ld.shape = "RECTANGLE"
        ld.size, ld.size_y = size
        ld.energy = power
        ld.color = color
        if spread_deg is not None:
            try:
                ld.spread = math.radians(spread_deg)
            except Exception:
                pass
        o = self.bpy.data.objects.new(name, ld)
        self.sc.collection.objects.link(o)
        o.location = pos
        d = Vector(target) - Vector(pos)
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = d.to_track_quat("-Z", "Y")
        try:
            o.visible_camera = False
        except Exception:
            pass
        self._extra.append(o)
        return o

    def box_face(self, name, centre, dims, normal, mat):
        """Rectangle dims (a, b) centred at centre facing normal (a along the first in-plane axis)."""
        from mathutils import Matrix, Vector
        n = np.asarray(normal, float)
        n /= np.linalg.norm(n)
        a = np.cross([0, 0, 1.0], n) if abs(n[2]) < 0.9 else np.array([1.0, 0, 0])
        a /= np.linalg.norm(a)
        b = np.cross(n, a)
        if abs(n[2]) >= 0.9:
            a, b = np.array([1.0, 0, 0]), np.cross(n, [1.0, 0, 0])
        ha, hb = dims[0] / 2, dims[1] / 2
        c = np.asarray(centre, float)
        V = [c - ha * a - hb * b, c + ha * a - hb * b, c + ha * a + hb * b, c - ha * a + hb * b]
        me = self.bpy.data.meshes.new(name)
        me.from_pydata([tuple(v) for v in V], [], [(0, 1, 2, 3)])
        me.update()
        if np.dot(np.cross(V[1] - V[0], V[3] - V[0]), n) < 0:
            me.flip_normals()
        o = self.bpy.data.objects.new(name, me)
        self.sc.collection.objects.link(o)
        me.materials.append(mat)
        self._extra.append(o)
        return o

    # ------------------------------------------------------------------ world
    def world(self, hdri_path, strength=1.0, rot_z_deg=0.0, env_R=None, camera_bg=None, ground_rgb=None,
              camera_grade=None, camera_sky=None, ground_gain=None):
        """HDRI world.  env_R: 3x3 rotation MODEL -> HDRI frame (tilted environments); rot_z_deg: extra
        azimuth rotation of the lookup.  camera_bg: RGB seen by camera rays instead of the HDRI (studio).
        ground_rgb: radiance that REPLACES the HDRI below its horizon (the 'puresky' HDRIs carry a flat,
        sky-bright lower half; real terrain seen from the air is ~albedo * E / pi, much darker and warmer).
        camera_grade: dict(sat, val, hue) applied to the HDRI as seen by CAMERA rays only (a polariser:
        deeper blue sky without changing the lighting).  camera_sky: [(sin elevation, (r, g, b)), ...] a
        gradient in the (tilted) HDRI frame seen by CAMERA rays instead of the HDRI (hazy horizon skies).
        ground_gain: multiplies the HDRI below its horizon (a lighter apron than the HDRI's asphalt; the
        shadow catcher then darkens that brighter ground, so shadows keep the sky fill)."""
        bpy = self.bpy
        w = bpy.data.worlds.new("beauty")
        self.sc.world = w
        try:
            w.use_nodes = True
        except Exception:
            pass
        nt = w.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputWorld")
        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.vector_type = "POINT"
        # lookup vector s = Rz(rot) @ env_R @ D  (D = world ray direction)
        from mathutils import Matrix
        M = np.eye(3) if env_R is None else np.asarray(env_R, float)
        a = math.radians(rot_z_deg)
        Rz = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
        M = Rz @ M
        eul = Matrix(M.tolist()).to_euler("XYZ")
        mp.inputs["Rotation"].default_value = eul
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(str(hdri_path), check_existing=True)
        env.interpolation = "Cubic"
        nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
        bg = nt.nodes.new("ShaderNodeBackground")
        bg.inputs["Strength"].default_value = strength
        col = env.outputs["Color"]
        if ground_gain:
            sepg = nt.nodes.new("ShaderNodeSeparateXYZ")
            nt.links.new(mp.outputs["Vector"], sepg.inputs[0])
            mrg = nt.nodes.new("ShaderNodeMapRange")
            mrg.interpolation_type = "SMOOTHSTEP"
            mrg.inputs["From Min"].default_value, mrg.inputs["From Max"].default_value = 0.005, -0.03
            mrg.inputs["To Min"].default_value, mrg.inputs["To Max"].default_value = 1.0, float(ground_gain)
            nt.links.new(sepg.outputs["Z"], mrg.inputs["Value"])
            mg = nt.nodes.new("ShaderNodeMix")
            mg.data_type = "RGBA"
            mg.blend_type = "MULTIPLY"
            mg.inputs["Factor"].default_value = 1.0
            nt.links.new(col, mg.inputs["A"])
            cv = nt.nodes.new("ShaderNodeCombineColor")
            for ch in ("Red", "Green", "Blue"):
                nt.links.new(mrg.outputs["Result"], cv.inputs[ch])
            nt.links.new(cv.outputs["Color"], mg.inputs["B"])
            col = mg.outputs["Result"]
        if ground_rgb is not None:
            # replace the HDRI below its horizon by a flat terrain radiance (smooth over ~3 deg)
            sep = nt.nodes.new("ShaderNodeSeparateXYZ")
            nt.links.new(mp.outputs["Vector"], sep.inputs[0])
            mr = nt.nodes.new("ShaderNodeMapRange")
            mr.interpolation_type = "SMOOTHSTEP"
            mr.inputs["From Min"].default_value = 0.01
            mr.inputs["From Max"].default_value = -0.05
            nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.blend_type = "MIX"
            nt.links.new(mr.outputs["Result"], mix.inputs["Factor"])
            nt.links.new(col, mix.inputs["A"])
            mix.inputs["B"].default_value = (*[c / max(strength, 1e-6) for c in ground_rgb], 1)
            col = mix.outputs["Result"]
        nt.links.new(col, bg.inputs["Color"])
        final = bg.outputs[0]
        if camera_sky and camera_bg is None:
            sep2 = nt.nodes.new("ShaderNodeSeparateXYZ")
            nrm = nt.nodes.new("ShaderNodeVectorMath")
            nrm.operation = "NORMALIZE"
            nt.links.new(mp.outputs["Vector"], nrm.inputs[0])
            nt.links.new(nrm.outputs["Vector"], sep2.inputs[0])
            ramp = nt.nodes.new("ShaderNodeValToRGB")
            E = ramp.color_ramp.elements
            stops = sorted(camera_sky, key=lambda t: t[0])
            E[0].position, E[0].color = stops[0][0], (*stops[0][1], 1)
            E[1].position, E[1].color = stops[-1][0], (*stops[-1][1], 1)
            for pos, c in stops[1:-1]:
                e = E.new(pos)
                e.color = (*c, 1)
            nt.links.new(sep2.outputs["Z"], ramp.inputs[0])
            camera_bg = ramp.outputs[0]
            strength_cam = 1.0
        if camera_grade and camera_bg is None:
            hsv = nt.nodes.new("ShaderNodeHueSaturation")
            hsv.inputs["Hue"].default_value = camera_grade.get("hue", 0.5)
            hsv.inputs["Saturation"].default_value = camera_grade.get("sat", 1.0)
            hsv.inputs["Value"].default_value = camera_grade.get("val", 1.0)
            nt.links.new(col, hsv.inputs["Color"])
            camera_bg = hsv.outputs["Color"]
        if camera_bg is not None:
            lp = nt.nodes.new("ShaderNodeLightPath")
            bg2 = nt.nodes.new("ShaderNodeBackground")
            if isinstance(camera_bg, str) and camera_bg == "gradient_dark":
                # vertical gradient in screen space: charcoal at the top, a little lighter at the horizon
                win = nt.nodes.new("ShaderNodeTexCoord")
                sp = nt.nodes.new("ShaderNodeSeparateXYZ")
                nt.links.new(win.outputs["Window"], sp.inputs[0])
                ramp = nt.nodes.new("ShaderNodeValToRGB")
                ramp.color_ramp.elements[0].position = 0.0
                ramp.color_ramp.elements[0].color = (0.055, 0.06, 0.068, 1)
                ramp.color_ramp.elements[1].position = 1.0
                ramp.color_ramp.elements[1].color = (0.006, 0.0065, 0.008, 1)
                nt.links.new(sp.outputs["Y"], ramp.inputs[0])
                nt.links.new(ramp.outputs[0], bg2.inputs["Color"])
            elif hasattr(camera_bg, "links"):                  # a node socket (graded HDRI)
                nt.links.new(camera_bg, bg2.inputs["Color"])
            else:
                bg2.inputs["Color"].default_value = (*camera_bg, 1)
            bg2.inputs["Strength"].default_value = (1.0 if camera_sky else strength) if hasattr(camera_bg, "links") else 1.0
            ms = nt.nodes.new("ShaderNodeMixShader")
            nt.links.new(lp.outputs["Is Camera Ray"], ms.inputs[0])
            nt.links.new(bg.outputs[0], ms.inputs[1])
            nt.links.new(bg2.outputs[0], ms.inputs[2])
            final = ms.outputs[0]
        nt.links.new(final, out.inputs[0])
        return w

    # ------------------------------------------------------------------ camera
    def camera(self, cam: Cam):
        bpy = self.bpy
        from mathutils import Matrix
        cd = bpy.data.cameras.new("beauty_cam")
        co = bpy.data.objects.new("beauty_cam", cd)
        self.sc.collection.objects.link(co)
        self.sc.camera = co
        cd.sensor_fit = "HORIZONTAL"
        cd.sensor_width = 36.0
        W, H = cam.W, cam.H
        R = cam.R
        if cam.ortho_width:
            cd.type = "ORTHO"
            cd.ortho_scale = cam.ortho_width
            cd.clip_start, cd.clip_end = 1.0, 200.0
        else:
            cd.type = "PERSP"
            cd.lens = cam.f * cd.sensor_width / W
            cd.shift_x = (0.5 * W - cam.cx) / W
            cd.shift_y = (cam.cy - 0.5 * H) / W
            dist = float(np.linalg.norm(cam.C - np.array([7.0, 0, 2.0])))
            cd.clip_start = 0.02 if dist < 20 else 0.2
            cd.clip_end = 60000.0
        M = np.eye(4)
        M[:3, :3] = np.stack([R[0], -R[1], -R[2]], 1)
        M[:3, 3] = cam.C
        co.matrix_world = Matrix(M.tolist())
        self.sc.render.resolution_x, self.sc.render.resolution_y = W, H
        self.sc.render.resolution_percentage = 100
        self.sc.render.pixel_aspect_x = self.sc.render.pixel_aspect_y = 1.0
        return co


def _fcurves(ad):
    """F-curves of an animation (Blender 5 layered actions or legacy)."""
    act = ad.action
    fcs = []
    try:
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    fcs.extend(bag.fcurves)
    except Exception:
        pass
    if not fcs:
        try:
            fcs = list(act.fcurves)
        except Exception:
            pass
    return fcs


class _quiet:
    """Silence C-level stdout (Blender's importer / renderer chatter)."""

    def __init__(self, enabled=True):
        self.enabled = enabled

    def __enter__(self):
        if not self.enabled:
            return self
        sys.stdout.flush()
        self.fd = os.dup(1)
        self.null = os.open(os.devnull, os.O_WRONLY)
        os.dup2(self.null, 1)
        return self

    def __exit__(self, *a):
        if not self.enabled:
            return False
        sys.stdout.flush()
        os.dup2(self.fd, 1)
        os.close(self.fd)
        os.close(self.null)
        return False


# =============================================================================================
# environments
# =============================================================================================
def hdri_sun(path):
    """(azimuth deg, elevation deg, peak) of the HDRI's brightest region in the environment lookup
    frame, cached in <path>.sun.json.  Azimuth: direction (cos az, sin az) = +x toward +y."""
    sj = Path(str(path) + ".sun.json")
    if sj.exists():
        try:
            d = json.loads(sj.read_text())
            if d.get("convention") == "cycles-v3":
                return d
        except Exception:
            pass
    import bpy
    img = bpy.data.images.load(str(path), check_existing=True)
    W, H = img.size
    px = np.empty(W * H * 4, np.float32)
    img.pixels.foreach_get(px)
    rgb = px.reshape(H, W, 4)[..., :3]
    L = rgb.mean(-1)                                     # row 0 = bottom
    # irradiance on a horizontal surface from the upper hemisphere (per channel), E = sum L sin(el) dw
    el_rows = (np.arange(H) + 0.5) / H * math.pi - math.pi / 2
    w_rows = np.where(el_rows > 0, np.sin(el_rows) * np.cos(el_rows), 0.0) * (math.pi / H) * (2 * math.pi / W)
    E_h = (rgb.sum(1) * w_rows[:, None]).sum(0)
    k = 8
    Ls = L[: H // k * k, : W // k * k].reshape(H // k, k, W // k, k).mean((1, 3))
    i, j = np.unravel_index(int(np.argmax(Ls)), Ls.shape)
    u = (j + 0.5) / Ls.shape[1]
    v = (i + 0.5) / Ls.shape[0]
    # Cycles equirect (direction_to_equirectangular): u = 0.5 - atan2(D.y, D.x) / 2pi, v = 0.5 + asin(D.z) / pi
    az = math.degrees(math.pi - 2 * math.pi * u)
    az = (az + 180.0) % 360.0 - 180.0
    el = math.degrees(math.pi * (v - 0.5))
    res = dict(az=az, el=el, peak=float(Ls.max()), mean=float(L.mean()), E_h=[float(v) for v in E_h],
               convention="cycles-v3")
    try:
        sj.write_text(json.dumps(res))
    except Exception:
        pass
    return res


def rot_to(a, b):
    """Rotation matrix taking unit vector a onto unit vector b."""
    a = np.asarray(a, float) / np.linalg.norm(a)
    b = np.asarray(b, float) / np.linalg.norm(b)
    v = np.cross(a, b)
    c = float(np.dot(a, b))
    if np.linalg.norm(v) < 1e-12:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + K + K @ K * (1 / (1 + c))


def env_up_from_horizon(cam: Cam, line):
    """World 'up' (MODEL axes) whose horizon (the vanishing line of the level plane) is the image line
    through the two pixels line = [(u0, v0), (u1, v1)] of this camera (a single row v0 = zero roll).
    The plane through the camera centre and the horizon rays has the camera-frame normal K^T l."""
    if np.isscalar(line):
        line = [(0.0, float(line)), (float(cam.W), float(line))]
    p0 = np.array([*line[0], 1.0])
    p1 = np.array([*line[1], 1.0])
    n_c = cam.K.T @ np.cross(p0, p1)
    probe = np.linalg.solve(cam.K, np.array([0.5 * (p0[0] + p1[0]), 0.5 * (p0[1] + p1[1]) - 50.0, 1.0]))
    if n_c @ probe < 0:                                   # 'up' points to the image side above the line
        n_c = -n_c
    up = cam.R.T @ n_c
    return up / np.linalg.norm(up)


def runway_texture(path, x0, x1, y0, y1, px_per_m=16.0, rw=None, seed=3):
    """Procedural snowy runway in WORLD metres over [x0, x1] x [y0, y1] (runway along +x).  rw: dict
    (from the top_048 photo projected onto the fitted ground plane, see PRESETS['top']): y (centre line),
    width, keys_x (piano-key band), key_off (key centre offsets from the centre line), key_w, bar_x
    (transverse bar), dash (centre-line dashes: x of one dash start, length, gap).  Surface: dark asphalt
    with darker tar repairs, wind-blown snow dust (elongated along x), snow-filled cracks (thin light
    meandering lines = iso-lines of a noise field), worn paint; blue-white snow banks past the edges.
    8-bit sRGB PNG, columns = y (column 0 = y0), rows = x with the LAST row = x0 (Blender's image v runs
    bottom-up; the runway quad maps v = 0 to x0)."""
    from PIL import Image
    rw = dict(RUNWAY_048, **(rw or {}))
    rng = np.random.default_rng(seed)
    W = int((y1 - y0) * px_per_m)
    H = int((x1 - x0) * px_per_m)
    y = y0 + (np.arange(W) + 0.5) / px_per_m
    x = x0 + (np.arange(H) + 0.5) / px_per_m
    Y, X = np.meshgrid(y, x)
    Yc = Y - rw["y"]

    def noise(sx, sy, amp=1.0, octaves=1):
        """value noise (cell sx along x by sy across, metres), smoothstep-interpolated, fractal"""
        out = np.zeros_like(X)
        a, fx_, fy_ = amp, sx, sy
        for _ in range(octaves):
            gx, gy = (X - x0) / fx_, (Y - y0) / fy_
            n = rng.standard_normal((int(gx.max()) + 3, int(gy.max()) + 3))
            i0, j0 = np.floor(gx).astype(int), np.floor(gy).astype(int)
            fx, fy = gx - i0, gy - j0
            fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
            aa = n[i0, j0] * (1 - fy) + n[i0, j0 + 1] * fy
            bb = n[i0 + 1, j0] * (1 - fy) + n[i0 + 1, j0 + 1] * fy
            out += a * (aa * (1 - fx) + bb * fx)
            a, fx_, fy_ = a * 0.5, fx_ * 0.5, fy_ * 0.5
        return out

    asph = 0.062 + noise(40, 25, 0.008, 3) + noise(0.8, 0.8, 0.005)
    tar = (noise(18, 9, 1.0, 2) > 1.0) | (noise(6, 25, 1.0) > 1.35)            # darker tar repairs
    asph = np.where(tar, asph - 0.012, asph)
    dn = noise(70, 6, 1.0, 4)                                                    # snow drifts blown along x:
    dust = np.clip((dn - 0.55) / 0.15, 0, 1) * np.clip(noise(4, 2, 0.6) + 0.7, 0, 1)   # sharp-edged
    asph = asph + 0.10 * dust
    for sc, thr, val in ((14.0, 0.02, 0.5), (5.0, 0.018, 0.35)):                 # snow-filled cracks
        c = np.abs(noise(sc, sc * 0.6, 1.0, 3)) < thr
        c &= noise(40, 25) > 0.4                                                 # sparse, in zones
        asph = np.where(c, val, asph)
    half = 0.5 * rw["width"]
    edge = half + 0.15 * noise(25, 3, 1.0, 2) + 0.3                               # plough line
    on_rw = np.abs(Yc) < edge
    snow = 0.82 + noise(20, 20, 0.02, 3)
    bank = np.clip(1 - (np.abs(Yc) - edge) / 5.0, 0, 1) ** 2                    # dirty plough bank
    snow = snow - 0.10 * bank
    img = np.where(on_rw, asph, snow)
    # paint (worn: patchy under the snow dust)
    wear = np.clip(0.75 - 0.7 * dust + noise(2, 1.2, 0.25, 2), 0.15, 0.9)
    paint = np.zeros_like(img, bool)
    ka, kb = rw["keys_x"]
    for off in rw["key_off"]:
        for sgn in (-1, 1):
            paint |= (np.abs(Yc - sgn * off) < 0.5 * rw["key_w"]) & (X > ka) & (X < kb)
    paint |= (np.abs(X - rw["bar_x"]) < 0.9) & (np.abs(Yc) < half - 1.5)
    d0, dl, dg = rw["dash"]
    paint |= (np.abs(Yc) < 0.45) & (np.mod(X - d0, dl + dg) < dl) & (X < ka - 10.0)
    img = np.where(paint & on_rw, 0.68 * wear + img * (1 - wear), img)
    cool = np.where(on_rw, 0.35 * dust, 1.0)[..., None]                      # snow blue-white, asphalt neutral
    rgb = img[..., None] * ((1 - cool) * np.array([0.99, 1.0, 1.01]) + cool * np.array([0.86, 0.93, 1.06]))
    Image.fromarray((np.clip(rgb[::-1], 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)).save(path)
    return path


# the top_048 runway (Buochs-like, 40 m) measured on the photo through the fitted camera, ground 119 m below
RUNWAY_048 = dict(y=-7.8, width=40.5, keys_x=(331.0, 360.0), key_off=(2.1, 5.8, 9.5, 13.2, 16.9), key_w=1.7,
                  bar_x=365.5, dash=(256.0, 30.0, 20.0))


def ground_footprint(cam: Cam, z, max_dist=5000.0, margin=0.15):
    """Bounding box (x0, x1, y0, y1) of the plane z seen by the camera (image border rays)."""
    u = np.r_[np.linspace(0, cam.W, 9), np.full(9, cam.W), np.linspace(cam.W, 0, 9), np.zeros(9)]
    v = np.r_[np.zeros(9), np.linspace(0, cam.H, 9), np.full(9, cam.H), np.linspace(cam.H, 0, 9)]
    d = np.c_[(u - cam.cx) / cam.f, (v - cam.cy) / cam.f, np.ones_like(u)] @ cam.R
    P = []
    for di in d:
        t = (z - cam.C[2]) / di[2] if di[2] < -1e-9 else np.inf
        t = min(t, max_dist / np.linalg.norm(di))
        P.append(cam.C + t * di)
    P = np.asarray(P)
    lo, hi = P[:, :2].min(0), P[:, :2].max(0)
    pad = margin * (hi - lo)
    return lo[0] - pad[0], hi[0] + pad[0], lo[1] - pad[1], hi[1] + pad[1]


def build_env(S: Scene, pre, cam: Cam, info):
    bpy = S.bpy
    env = pre["env"]
    hdri = ensure_hdri(pre["hdri"])
    sun = hdri_sun(hdri)
    info["hdri"] = dict(id=pre["hdri"], file=str(hdri.relative_to(ROOT)), license="CC0 (Poly Haven)",
                        sun_el_deg=round(sun["el"], 1))
    rot = pre.get("hdri_rot", 0.0)
    env_R = None
    strength = pre.get("strength", 1.0)
    if pre.get("sun_az") is not None:
        rot = sun["az"] - pre["sun_az"]          # world azimuth = hdri azimuth - rotation
    if env == "air_ground":
        # horizon given in the pixel frame of the camera spec (the photo); scale to the render
        s = cam.W / pre["camera"]["W"]
        line = [(u * s, v * s) for u, v in pre["horizon"]]
        up = env_up_from_horizon(cam, line)
        env_R = rot_to(up, (0, 0, 1))             # MODEL -> level frame
        info["env_up_model"] = up.round(4).tolist()
        # sun azimuth is then measured in the level frame; keep the preset's sun_az there
    ground_rgb = None
    if pre.get("ground_albedo") is not None:
        E = np.asarray(sun.get("E_h", (3.0, 3.0, 3.0)))
        ground_rgb = tuple(float(v) for v in strength * np.asarray(pre["ground_albedo"]) * E / math.pi)
        info["hdri"]["ground_rgb"] = [round(v, 4) for v in ground_rgb]
    S.world(hdri, strength=strength, rot_z_deg=rot, env_R=env_R,
            camera_bg={"studio_white": (1.0, 1.0, 1.0)}.get(env),
            ground_rgb=ground_rgb, camera_grade=pre.get("camera_grade"), camera_sky=pre.get("camera_sky"),
            ground_gain=pre.get("ground_gain"))
    info["hdri"]["rot_z_deg"] = round(rot, 2)
    if pre.get("sun_lamp") and pre.get("sun_az") is not None:
        sl = pre["sun_lamp"]
        az, el = math.radians(pre["sun_az"]), math.radians(sl.get("el", sun["el"]))
        d_level = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
        d = (np.asarray(env_R).T @ d_level) if env_R is not None else d_level      # toward the sun, MODEL
        ld = bpy.data.lights.new("sun", "SUN")
        ld.energy = sl.get("strength", 4.0)
        ld.color = sl.get("colour", (1.0, 0.9, 0.75))
        ld.angle = math.radians(sl.get("angle", 0.6))
        lo = bpy.data.objects.new("sun", ld)
        S.sc.collection.objects.link(lo)
        from mathutils import Vector
        lo.rotation_mode = "QUATERNION"
        lo.rotation_quaternion = Vector(tuple(-d)).to_track_quat("-Z", "Y")
        info["sun_lamp"] = dict(dir_model=d.round(4).tolist(), **{k: v for k, v in sl.items()})
    sc = S.sc
    if env == "hangar":
        hangar_room(S, pre.get("room", {}))
    elif env in ("apron", "studio_white"):
        p = S.plane("shadow_catcher", 400.0, (0, 0, -0.003), mat=S.new_material("catcher", (0.5, 0.5, 0.5), 0.9))
        p.is_shadow_catcher = True
        if env == "studio_white":
            sc.render.film_transparent = True
    elif env == "studio_cyc":
        studio_cyc(S, pre, cam, info)
    elif env == "air_ground":
        up = np.asarray(info["env_up_model"])
        centre = cam.C - pre.get("ground_depth", 1500.0) * up
        S.plane("desert", 600000.0, tuple(centre), normal=tuple(up), mat=desert_material(S, cam.C, up))
        if pre.get("domes"):
            info["domes"] = kata_tjuta(S, pre, cam, env_R, pre.get("ground_depth", 1500.0))
    elif env == "runway":
        zg = -pre.get("ground_depth", 119.0)
        x0, x1, y0, y1 = ground_footprint(cam, zg)
        key = "_".join(f"{v:.0f}" for v in (x0, x1, y0, y1))
        tex_dir = ROOT / "out" / "tmp" / "beauty"
        tex_dir.mkdir(parents=True, exist_ok=True)
        png = tex_dir / f"runway8_{key}.png"
        if not png.exists():
            runway_texture(png, x0, x1, y0, y1, rw=pre.get("runway"))
        m = S.new_material("runway", rough=0.75, spec=0.4)
        nt = m.node_tree
        tx = nt.nodes.new("ShaderNodeTexImage")
        tx.image = bpy.data.images.load(str(png))
        tx.image.pack()
        tx.interpolation = "Cubic"
        tx.extension = "EXTEND"
        nt.links.new(tx.outputs["Color"], S._bsdf(m).inputs["Base Color"])
        # quad over the footprint; texture rows run along +x, columns along +y
        me = bpy.data.meshes.new("runway")
        me.from_pydata([(x0, y0, zg), (x1, y0, zg), (x1, y1, zg), (x0, y1, zg)], [], [(0, 1, 2, 3)])
        uv = me.uv_layers.new(name="UVMap")
        for i, (uu, vv) in enumerate([(0, 0), (0, 1), (1, 1), (1, 0)]):
            uv.data[i].uv = (uu, vv)
        me.materials.append(m)
        o = bpy.data.objects.new("runway", me)
        S.sc.collection.objects.link(o)
        snow = S.new_material("snow", color=(0.70, 0.76, 0.87), rough=0.9)
        S.plane("snow", 20000.0, (0, 0, zg - 0.05), mat=snow)
        info["runway_footprint"] = [round(v, 1) for v in (x0, x1, y0, y1)]
    return info


def studio_cyc(S: Scene, pre, cam: Cam, info):
    """Seamless charcoal cyclorama (floor sweeping up into a back wall through a radius) square to the
    camera's horizontal look direction, glossy floor, softboxes (HERO_LIGHTS) with the overhead / rim
    boxes light-linked away from the floor, and a soft glow light on the backdrop behind the aircraft."""
    bpy = S.bpy
    cy = dict(back=13.0, radius=7.0, colour=(0.03, 0.032, 0.036), floor_rough=0.28, height=40.0, width=160.0)
    cy.update(pre.get("cyc", {}))
    ctr = np.array([7.2, 0.0, 0.0])
    w = cam.R[2].copy()
    w[2] = 0.0
    w /= np.linalg.norm(w)                         # horizontal look direction
    u = np.cross(w, [0, 0, 1.0])
    R_, D, Hh, Wd = cy["radius"], cy["back"], cy["height"], cy["width"]
    prof = [(-80.0, 0.0), (D - R_, 0.0)]           # (along w, up) profile: floor, quarter circle, wall
    for k in range(1, 17):
        t = 0.5 * math.pi * k / 16
        prof.append((D - R_ + R_ * math.sin(t), R_ - R_ * math.cos(t)))
    prof.append((D, Hh))
    us = np.linspace(-Wd / 2, Wd / 2, 3)
    verts, faces = [], []
    for a, z in prof:
        for uu in us:
            verts.append(tuple(ctr + a * w + uu * u + np.array([0, 0, z - 0.003])))
    nu = len(us)
    for i in range(len(prof) - 1):
        for j in range(nu - 1):
            faces.append((i * nu + j, i * nu + j + 1, (i + 1) * nu + j + 1, (i + 1) * nu + j))
    me = bpy.data.meshes.new("cyclorama")
    me.from_pydata(verts, [], faces)
    me.update()
    for poly in me.polygons:
        poly.use_smooth = True
    m = S.new_material("cyc", color=cy["colour"], rough=cy["floor_rough"], spec=0.5)
    # rougher on the wall than on the floor (by the shading normal's z)
    nt = m.node_tree
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.6, 0.98
    mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 0.8, cy["floor_rough"]
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], S._bsdf(m).inputs["Roughness"])
    me.materials.append(m)
    cyc = bpy.data.objects.new("cyclorama", me)
    S.sc.collection.objects.link(cyc)
    S._extra.append(cyc)
    # light linking (Blender >= 4.0): lights flagged False light the cyclorama only; the key also skips
    # the flat prop blades (a softbox mirrored in a whole satin-black blade face reads as a white blade)
    blades = S.meshes_of(["blade_"]) if cy.get("exclude_blades", True) else []
    colls = {}
    for key, members, state in (("floor_only", [cyc], "INCLUDE"), ("no_blades", blades, "EXCLUDE")):
        if not members:
            continue
        c = bpy.data.collections.new(f"cyc_{key}")
        for o in members:
            c.objects.link(o)
        for co in c.collection_objects:
            co.light_linking.link_state = state
        colls[key] = c
    for nm, pos, tgt, size, power, col, on_aircraft, spread in pre.get("lights", HERO_LIGHTS):
        L = S.area_light(nm, pos, tgt, size, power, col, spread)
        key = "floor_only" if not on_aircraft else (None if nm.startswith("fill") else "no_blades")
        if key in colls:
            try:
                L.light_linking.receiver_collection = colls[key]
            except Exception as e:
                info.setdefault("warnings", []).append(f"light linking unavailable: {e}")
    # backdrop glow: a big soft light in front of the wall, low, aimed up the sweep behind the aircraft
    g = ctr + (D - 3.5) * w + np.array([0, 0, 0.6])
    S.area_light("cyc_glow", tuple(g), tuple(ctr + (D + 2.0) * w + np.array([0, 0, 6.0])), (26.0, 3.0),
                 cy.get("glow", 3000.0), (0.80, 0.86, 1.0), 120.0)
    info["cyc"] = dict(w=w.round(3).tolist(), back=D, radius=R_)


def hangar_room(S: Scene, room):
    """White delivery hangar of the MSN 3008 photos: glossy epoxy floor, white walls, OSB ceiling with
    LED strip lights.  The side toward -x (behind the camera) is the closed hangar door, a mid-grey
    sectional door (room['door'] = albedo, None = open to the HDRI): the paint mirrors it, and the deep
    blue of the photo's fuselage sides needs a darker surface behind the photographer than the white
    walls.  Wall positions from the solved 'port_hangar_130' camera: the ceiling/wall edges in the photo
    put the back wall at x ~ 20.5 m and the right-hand wall at y ~ +10 m for a ~8.5 m ceiling."""
    x_back, y_stbd, y_port, z_ceil = room.get("x_back", 20.5), room.get("y_stbd", 10.0), room.get("y_port", -16.0), \
        room.get("z_ceil", 8.5)
    x_open = room.get("x_open", -18.0)
    floor = S.new_material("epoxy_floor", color=(0.80, 0.80, 0.79), rough=0.12, coat=0.25, spec=0.5)
    wall = S.new_material("hangar_wall", color=(0.82, 0.82, 0.81), rough=0.85, spec=0.3)
    osb = S.new_material("osb_ceiling", color=(0.50, 0.36, 0.20), rough=0.8, spec=0.2)
    nt = osb.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vo = nt.nodes.new("ShaderNodeTexVoronoi")
    vo.inputs["Scale"].default_value = 9.0
    nt.links.new(tc.outputs["Object"], vo.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.17, 0.085, 0.026, 1)     # photo OSB ~ sRGB (156, 115, 62)
    ramp.color_ramp.elements[1].color = (0.30, 0.16, 0.05, 1)
    nt.links.new(vo.outputs["Color"], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], S._bsdf(osb).inputs["Base Color"])
    xc, yc = 0.5 * (x_open + x_back), 0.5 * (y_port + y_stbd)
    Lx, Ly = x_back - x_open, y_stbd - y_port
    S.box_face("floor", (xc, yc, -0.003), (Lx + 40, Ly + 40), (0, 0, 1), floor)
    S.box_face("ceiling", (xc, yc, z_ceil), (Lx, Ly), (0, 0, -1), osb)
    S.box_face("wall_back", (x_back, yc, z_ceil / 2), (z_ceil, Ly), (-1, 0, 0), wall)
    S.box_face("wall_stbd", (xc, y_stbd, z_ceil / 2), (Lx, z_ceil), (0, -1, 0), wall)
    S.box_face("wall_port", (xc, y_port, z_ceil / 2), (Lx, z_ceil), (0, 1, 0), wall)
    if room.get("door", 0.35) is not None:
        a = room.get("door", 0.35)
        door = S.new_material("hangar_door", color=(a, a, a * 1.02), rough=0.6, spec=0.3)
        S.box_face("wall_door", (x_open, yc, z_ceil / 2), (z_ceil, Ly), (1, 0, 0), door)
    # LED strips along x (visible, and reflected in the paint as in the photo)
    em = S.bpy.data.materials.new("led_strip")
    try:
        em.use_nodes = True
    except Exception:
        pass
    b = S._bsdf(em)
    b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Color"].default_value = (1.0, 1.0, 1.0, 1)
    b.inputs["Emission Strength"].default_value = room.get("strip_strength", 45.0)
    for y in room.get("strips_y", (-12.0, -8.0, -4.0, 0.0, 4.0, 8.0)):
        S.box_face(f"strip_{y:+.0f}", (0.5 * (x_open + x_back) + 2, y, z_ceil - 0.25), (Lx - 8, 0.12), (0, 0, -1), em)


HAZE = dict(colour=(0.80, 0.72, 0.58), dist=45000.0)     # aerial perspective (wing_from_cabin)


def add_haze(m, colour=None, dist=None):
    """Aerial perspective for a far-field material: blend the surface shader toward an EMISSION of the
    horizon colour with 1 - exp(-ray length / dist), so distant terrain fades into the camera sky
    (an albedo blend would still be lit and leave a seam at the horizon)."""
    colour, dist = colour or HAZE["colour"], dist or HAZE["dist"]
    nt = m.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    surf = out.inputs["Surface"].links[0].from_socket
    lp = nt.nodes.new("ShaderNodeLightPath")
    mth = nt.nodes.new("ShaderNodeMath")
    mth.operation = "MULTIPLY"
    mth.inputs[1].default_value = -1.0 / dist
    nt.links.new(lp.outputs["Ray Length"], mth.inputs[0])
    ex = nt.nodes.new("ShaderNodeMath")
    ex.operation = "EXPONENT"
    nt.links.new(mth.outputs[0], ex.inputs[0])
    f = nt.nodes.new("ShaderNodeMath")
    f.operation = "SUBTRACT"
    f.inputs[0].default_value = 1.0
    nt.links.new(ex.outputs[0], f.inputs[1])
    # only for camera rays: reflections / shadows see the plain surface
    cr = nt.nodes.new("ShaderNodeMath")
    cr.operation = "MULTIPLY"
    nt.links.new(f.outputs[0], cr.inputs[0])
    nt.links.new(lp.outputs["Is Camera Ray"], cr.inputs[1])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*colour, 1)
    em.inputs["Strength"].default_value = 1.0
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(cr.outputs[0], mx.inputs[0])
    nt.links.new(surf, mx.inputs[1])
    nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    return m


def kata_tjuta(S: Scene, pre, cam: Cam, env_R, depth):
    """Sandstone domes (Kata Tjuta) standing on the level ground plane 'depth' below the camera.  Each
    dome is given in the photo's pixel frame by its top pixel, base pixel and half-width: the base pixel
    is ray-cast onto the ground, the top pixel fixes the height above that base point, the half-width
    the radius.  Shape: an ellipsoid half-buried in the plain (steep flanks, rounded crest)."""
    bpy = S.bpy
    s = cam.W / pre["camera"]["W"]
    Kinv = np.linalg.inv(cam.K)
    RL = np.asarray(env_R, float)                       # MODEL -> level frame

    def ray(u, v):
        d = RL @ (cam.R.T @ (Kinv @ np.array([u * s, v * s, 1.0])))
        return d / np.linalg.norm(d)

    mat = add_haze(sandstone_material(S))
    rng = np.random.default_rng(7)
    out = []
    for k, (tu, tv, bu, bv, hw) in enumerate(pre["domes"]):
        db = ray(bu, bv)
        if db[2] >= -1e-4:
            continue
        foot = db * (-depth / db[2])                     # near foot, level frame, camera at the origin
        rad = float(np.linalg.norm(foot) * hw * s / cam.f)
        hor = foot[:2] / np.linalg.norm(foot[:2])
        base = np.array([*(foot[:2] + 0.8 * rad * hor), -depth])      # dome centre on the plain
        rad *= np.linalg.norm(base) / np.linalg.norm(foot)             # keep the photo's angular width
        rho = float(np.hypot(base[0], base[1]))
        dt = ray(tu, tv)
        th = dt * (rho / max(np.hypot(dt[0], dt[1]), 1e-9))
        h = float(th[2] + depth)
        if h <= 5.0:
            continue
        bpy.ops.mesh.primitive_uv_sphere_add(segments=72, ring_count=36, radius=1.0)
        o = bpy.context.active_object
        o.name = f"dome_{k}"
        for poly in o.data.polygons:
            poly.use_smooth = True
        el = rng.uniform(0.75, 1.0)
        yaw = rng.uniform(0, math.pi)
        Rz = np.array([[math.cos(yaw), -math.sin(yaw), 0], [math.sin(yaw), math.cos(yaw), 0], [0, 0, 1]])
        sink = 0.12 * h                                  # bedded in the plain: steeper flanks at the foot
        M_level = Rz @ np.diag([rad, rad * el, h + sink])
        M = np.eye(4)
        M[:3, :3] = RL.T @ M_level                       # level -> MODEL
        M[:3, 3] = cam.C + RL.T @ np.array([base[0], base[1], -depth - sink])
        from mathutils import Matrix
        o.matrix_world = Matrix(M.tolist())
        o.data.materials.append(mat)
        tex = bpy.data.textures.new(f"dome_lumps_{k}", "CLOUDS")
        tex.noise_scale = 0.8
        tex.noise_depth = 3
        md = o.modifiers.new("lumps", "DISPLACE")
        md.texture = tex
        md.texture_coords = "LOCAL"
        md.strength = 0.05
        md.mid_level = 0.5
        S._extra.append(o)
        out.append(dict(dist_m=round(float(np.linalg.norm(base)), 0), height_m=round(h, 0), radius_m=round(rad, 0)))
    return out


def sandstone_material(S: Scene):
    """Kata Tjuta conglomerate: red-orange with darker streaks and weathering bands, rough."""
    m = S.bpy.data.materials.new("sandstone")
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    b = S._bsdf(m)
    b.inputs["Roughness"].default_value = 0.9
    b.inputs["Specular IOR Level"].default_value = 0.25
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sc = nt.nodes.new("ShaderNodeVectorMath")
    sc.operation = "MULTIPLY"
    sc.inputs[1].default_value = (9.0, 9.0, 1.2)            # streaks run down the flanks
    nt.links.new(tc.outputs["Generated"], sc.inputs[0])
    st = nt.nodes.new("ShaderNodeTexNoise")
    st.inputs["Scale"].default_value = 2.0
    st.inputs["Detail"].default_value = 10.0
    st.inputs["Roughness"].default_value = 0.65
    nt.links.new(sc.outputs["Vector"], st.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 5.0
    nz.inputs["Detail"].default_value = 6.0
    nt.links.new(tc.outputs["Generated"], nz.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "FLOAT"
    mix.inputs["Factor"].default_value = 0.4
    nt.links.new(st.outputs["Fac"], mix.inputs["A"])
    nt.links.new(nz.outputs["Fac"], mix.inputs["B"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    E = ramp.color_ramp.elements
    E[0].position, E[0].color = 0.30, (0.19, 0.035, 0.010, 1)
    E[1].position, E[1].color = 0.62, (0.62, 0.12, 0.025, 1)
    nt.links.new(mix.outputs["Result"], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], b.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    nt.links.new(mix.outputs["Result"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def desert_material(S: Scene, cam_C, up):
    """Central-Australian plain seen from ~900 m: orange-red sand with grey-green scrub clumps (spinifex,
    mulga) whose density varies in 200-800 m patches, drier yellow-beige grassland patches, fading into
    a warm haze with distance from the camera."""
    m = S.bpy.data.materials.new("desert")
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    b = S._bsdf(m)
    b.inputs["Roughness"].default_value = 0.95
    b.inputs["Specular IOR Level"].default_value = 0.2
    tc = nt.nodes.new("ShaderNodeTexCoord")

    def noise(scale, detail=6.0, rough=0.55):
        n = nt.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
        return n.outputs["Fac"]

    def mrange(src, a, b_, lo=0.0, hi=1.0):
        r = nt.nodes.new("ShaderNodeMapRange")
        r.inputs["From Min"].default_value, r.inputs["From Max"].default_value = a, b_
        r.inputs["To Min"].default_value, r.inputs["To Max"].default_value = lo, hi
        nt.links.new(src, r.inputs["Value"])
        return r.outputs["Result"]

    def mix(fac, A, B):
        x = nt.nodes.new("ShaderNodeMix")
        x.data_type = "RGBA"
        if isinstance(fac, float):
            x.inputs["Factor"].default_value = fac
        else:
            nt.links.new(fac, x.inputs["Factor"])
        for sock, v in (("A", A), ("B", B)):
            if isinstance(v, tuple):
                x.inputs[sock].default_value = (*v, 1)
            else:
                nt.links.new(v, x.inputs[sock])
        return x.outputs["Result"]

    sand = mix(mrange(noise(0.0015, 8), 0.35, 0.65), (0.26, 0.095, 0.04), (0.36, 0.16, 0.07))
    dry = mix(mrange(noise(0.0009, 6), 0.52, 0.62), sand, (0.42, 0.33, 0.17))          # yellow grassland
    density = mrange(noise(0.0025, 8, 0.6), 0.3, 0.7, 0.3, 0.65)                     # scrub density
    clumps = noise(0.2, 4, 0.55)                                                      # ~5 m clumps
    thr = nt.nodes.new("ShaderNodeMath")
    thr.operation = "GREATER_THAN"
    nt.links.new(clumps, thr.inputs[0])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(density, inv.inputs[1])
    nt.links.new(inv.outputs[0], thr.inputs[1])
    ground = mix(thr.outputs[0], dry, (0.10, 0.10, 0.075))
    nt.links.new(ground, b.inputs["Base Color"])
    add_haze(m)
    return m


# =============================================================================================
# render
# =============================================================================================
def configure_render(S: Scene, pre, samples, out_png):
    sc = S.sc
    sc.render.engine = "CYCLES"
    c = sc.cycles
    c.device = "CPU"
    c.samples = int(samples)
    c.use_adaptive_sampling = True
    c.adaptive_threshold = float(pre.get("noise_threshold", 0.03))
    c.adaptive_min_samples = 16
    c.use_denoising = True
    try:
        c.denoiser = "OPENIMAGEDENOISE"
        c.denoising_input_passes = "RGB_ALBEDO_NORMAL"
        c.denoising_prefilter = "FAST"
        c.denoising_quality = "HIGH"
    except Exception:
        pass
    bo = pre.get("bounces", DEFAULT_BOUNCES)
    c.max_bounces, c.diffuse_bounces, c.glossy_bounces = bo[0], bo[1], bo[2]
    c.transmission_bounces, c.transparent_max_bounces = bo[3], bo[4]
    c.caustics_reflective = c.caustics_refractive = False
    c.sample_clamp_indirect = 8.0
    c.blur_glossy = 0.5
    c.pixel_filter_type = "BLACKMAN_HARRIS"
    c.filter_width = 1.5
    try:
        c.use_light_tree = True
    except Exception:
        pass
    sc.render.use_persistent_data = False
    vs = sc.view_settings
    vs.view_transform = "AgX"
    try:
        vs.look = pre.get("look", DEFAULT_LOOK)
    except Exception:
        pass
    vs.exposure = float(pre.get("exposure", 0.0))
    vs.gamma = 1.0
    wb = pre.get("white_balance")                 # (illuminant temperature K, tint) to neutralise
    try:
        vs.use_white_balance = wb is not None
        if wb is not None:
            vs.white_balance_temperature, vs.white_balance_tint = float(wb[0]), float(wb[1])
    except Exception:
        pass
    sc.display_settings.display_device = "sRGB"
    ims = sc.render.image_settings
    try:
        ims.media_type = "IMAGE"
    except Exception:
        pass
    ims.file_format = "PNG"
    ims.color_mode = "RGBA" if sc.render.film_transparent else "RGB"
    ims.color_depth = "16"                        # graded / flattened to 8 bit by finish_png()
    ims.compression = 40
    sc.render.filepath = str(out_png)
    try:
        sc.render.threads_mode = "AUTO"
    except Exception:
        pass


def render_preset(name, glb, out_dir, box, samples, compare, quiet=True):
    import bpy
    pre = PRESETS[name]
    t0 = time.time()
    S = Scene(glb, quiet=quiet)
    info = dict(preset=name, glb=S.glb_src, glb_mtime=S.glb_mtime, created=time.strftime("%Y-%m-%d %H:%M:%S"))
    cam, cam_src = preset_camera(name, *box)
    info["camera_source"] = cam_src
    S.hide(["structure"] + list(pre.get("hide", ())))
    if pre.get("camera_invisible"):
        S.camera_invisible(pre["camera_invisible"])
    S.materials(pre.get("paint"))
    info["pose"] = dict(pre.get("pose", {}))
    info["pose_result"] = S.pose(**pre.get("pose", {}))
    fr = pre["camera"].get("frame")
    if fr and not cam.ortho_width and cam_src == "fallback":
        cam = auto_frame(cam, S.visible_points(), fr.get("fill", 0.9), fr.get("align", (0.5, 0.5)))
        info["camera_source"] = cam_src = "fallback + auto_frame"
    build_env(S, pre, cam, info)
    S.camera(cam)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_png = out_dir / f"{name}.png"
    configure_render(S, pre, samples, out_png)
    t1 = time.time()
    import resource
    ru0 = resource.getrusage(resource.RUSAGE_SELF)
    with _quiet(quiet):
        bpy.ops.render.render(write_still=True)
    t2 = time.time()
    ru1 = resource.getrusage(resource.RUSAGE_SELF)
    cpu_s = (ru1.ru_utime - ru0.ru_utime) + (ru1.ru_stime - ru0.ru_stime)
    ncpu = os.cpu_count() or 1
    finish_png(out_png, pre.get("grade"), white_bg=S.sc.render.film_transparent)
    info.update(camera=cam.to_json(), size=[cam.W, cam.H], samples=samples,
                timings=dict(import_s=round(S.t_import, 1), setup_s=round(t1 - t0 - S.t_import, 1),
                             render_s=round(t2 - t1, 1), total_s=round(time.time() - t0, 1),
                             render_cpu_s=round(cpu_s, 1), cpus=ncpu,
                             render_idle_est_s=round(cpu_s / ncpu, 1),       # wall time on idle cores
                             load_avg=[round(v, 2) for v in os.getloadavg()]),
                photo=pre.get("photo"), photo_note=pre.get("photo_note"),
                view_transform="AgX", look=pre.get("look", DEFAULT_LOOK), exposure=pre.get("exposure", 0.0))
    (out_dir / f"{name}.json").write_text(json.dumps(info, indent=1, default=float))
    if compare and pre.get("photo"):
        write_compare(name, out_png, info)
    shutil.rmtree(S.tmpdir, ignore_errors=True)
    print(f"[{name}] {cam.W}x{cam.H}, {samples} spp: render {t2 - t1:.1f} s (cpu {cpu_s:.0f} s = "
          f"{cpu_s / ncpu:.0f} s on {ncpu} idle cores), total {time.time() - t0:.1f} s "
          f"-> {out_png.relative_to(ROOT) if out_png.is_relative_to(ROOT) else out_png}  (camera: {cam_src})",
          flush=True)
    return info


def finish_png(png, grade=None, white_bg=False):
    """16-bit render -> graded 8-bit PNG.  grade (display-referred, after AgX): dict(white=, black=,
    gamma=, sat=): levels (input 'white' -> 1, 'black' -> 0), mid-tone power (> 1 darker), saturation.
    Photographic delivery images are graded like a camera JPEG (clipped whites, firmer mid-tones) while
    AgX rolls highlights off softly; the grade closes that gap without changing the scene.  white_bg:
    composite a transparent film over white (studio)."""
    import bpy
    from PIL import Image
    img = bpy.data.images.load(str(png), check_existing=False)
    img.colorspace_settings.name = "Non-Color"            # raw 16-bit display values
    W, H = img.size
    px = np.empty(W * H * 4, np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    a = px.reshape(H, W, 4)[::-1]                          # row 0 = top
    rgb, alpha = a[..., :3].astype(np.float64), a[..., 3:4].astype(np.float64)
    if white_bg:
        rgb = rgb * alpha + (1.0 - alpha)                  # straight alpha over white
    if grade:
        lo, hi = grade.get("black", 0.0), grade.get("white", 1.0)
        rgb = np.clip((rgb - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
        if grade.get("gamma", 1.0) != 1.0:
            rgb = rgb ** grade["gamma"]
        if grade.get("sat", 1.0) != 1.0:
            lum = rgb @ np.array([0.2126, 0.7152, 0.0722])
            rgb = np.clip(lum[..., None] + grade["sat"] * (rgb - lum[..., None]), 0.0, 1.0)
    Image.fromarray((np.clip(rgb, 0, 1) * 255.0 + 0.5).astype(np.uint8), "RGB").save(png, optimize=False,
                                                                                    compress_level=6)


def _font(size):
    from PIL import ImageFont
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    try:
        return ImageFont.load_default(size)
    except Exception:
        return ImageFont.load_default()


def write_compare(name, render_png, info):
    """photo | render (same size, labelled) and a 50 % blend into refs/cache/overlays/vqa/."""
    from PIL import Image, ImageDraw
    pre = PRESETS[name]
    VQA_DIR.mkdir(parents=True, exist_ok=True)
    ren = Image.open(render_png).convert("RGB")
    ph = Image.open(PHOTO_DIR / pre["photo"]).convert("RGB")
    W, H = ren.size
    # the camera is fitted to the full photo: resize (aspect preserved up to rounding); a reference whose
    # aspect differs by > 1 % is letterboxed rather than stretched
    if abs(ph.width / ph.height - W / H) > 0.01 * W / H:
        k = min(W / ph.width, H / ph.height)
        fit = ph.resize((round(ph.width * k), round(ph.height * k)), Image.LANCZOS)
        ph = Image.new("RGB", (W, H), (24, 25, 28))
        ph.paste(fit, ((W - fit.width) // 2, (H - fit.height) // 2))
    else:
        ph = ph.resize((W, H), Image.LANCZOS)
    pad, bar = 12, 44
    sheet = Image.new("RGB", (2 * W + 3 * pad, H + bar + 2 * pad), (24, 25, 28))
    sheet.paste(ph, (pad, bar + pad))
    sheet.paste(ren, (2 * pad + W, bar + pad))
    d = ImageDraw.Draw(sheet)
    f = _font(22)
    d.text((pad, 10), f"PHOTO  {Path(pre['photo']).name}", fill=(235, 235, 235), font=f)
    d.text((2 * pad + W, 10), f"MODEL  {name}  ({Path(info['glb']).name} "
           f"{time.strftime('%Y-%m-%d %H:%M', time.localtime(info['glb_mtime']))}"
           f", camera {info['camera_source'].split('/')[-1]})", fill=(235, 235, 235), font=f)
    out = VQA_DIR / f"{name}_compare.jpg"
    sheet.save(out, quality=90)
    Image.blend(ph, ren, 0.5).save(VQA_DIR / f"{name}_blend.jpg", quality=88)
    return out


# =============================================================================================
# CLI
# =============================================================================================
def _have_bpy():
    try:
        import bpy  # noqa: F401
        return True
    except Exception:
        return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--glb", default=str(GLB))
    ap.add_argument("--preset", default="all", help="comma list or 'all'")
    ap.add_argument("--out", default=str(OUT_DIR))
    ap.add_argument("--size", default="1600x1000", help="bounding box WxH (presets keep their aspect)")
    ap.add_argument("--samples", type=int, default=None, help="Cycles samples (default per preset, 24-48 with adaptive sampling + OIDN)")
    ap.add_argument("--compare", action="store_true", help="photo | render side-by-sides into refs/cache/overlays/vqa/")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--fit", default=None, help="refit cams_beauty.json entries (comma list or 'all'), then exit")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="override a preset field for this run (JSON value; dotted keys for nested dicts, "
                         "e.g. --set exposure=0.4 --set pose.gear=1 --set sun_az=200)")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args(argv)
    if a.list:
        for k, v in PRESETS.items():
            print(f"{k:18s} photo={v.get('photo')}  env={v['env']}  hdri={v['hdri']}")
        return 0
    if a.fit:
        d = json.loads(BEAUTY_CAMS.read_text())
        keys = list(d) if a.fit == "all" else a.fit.split(",")
        for k in keys:
            print(f"[fit] {k}")
            p, rms = fit_camera(d[k])
            d[k]["p"], d[k]["rms"] = p.tolist(), rms
        BEAUTY_CAMS.write_text(json.dumps(d, indent=1))
        return 0
    if not _have_bpy():
        cmd = [BLENDER_PY, str(Path(__file__).resolve())] + (argv if argv is not None else sys.argv[1:])
        return subprocess.call(cmd, cwd=str(ROOT))
    names = list(PRESETS) if a.preset == "all" else [n.strip() for n in a.preset.split(",") if n.strip()]
    for n in names:
        if n not in PRESETS:
            raise SystemExit(f"unknown preset {n!r}; have {', '.join(PRESETS)}")
    for kv in a.set:
        k, _, v = kv.partition("=")
        try:
            v = json.loads(v)
        except ValueError:
            pass
        for n in names:
            d = PRESETS[n]
            *path, leaf = k.split(".")
            for q in path:
                d = d.setdefault(q, {})
            d[leaf] = v
    bw, bh = (int(v) for v in a.size.lower().split("x"))
    glb = Path(a.glb)
    if not glb.is_absolute():
        glb = (Path.cwd() / glb) if (Path.cwd() / glb).exists() else ROOT / a.glb
    for n in names:
        spp = a.samples or PRESETS[n].get("samples", 48)
        render_preset(n, glb, a.out, (bw, bh), spp, a.compare, quiet=not a.verbose)
    return 0


if __name__ == "__main__":
    sys.exit(main())
