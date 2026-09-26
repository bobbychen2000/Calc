"""
render.turntable -- studio turntable movie of a GLB (Blender 5 / Cycles CPU, OIDN, AgX), H.264 MP4.

    /opt/venv-blender/bin/python render/turntable.py [--glb out/pc12.glb] [--out out/renders/turntable.mp4]
            [--frames 240] [--fps 24] [--size 1920x1080] [--samples 16] [--threshold 0.06]
            [--elev 15] [--distance 34] [--start-az AZ] [--direction ccw|cw]
            [--prop-spin [RPM]] [--shutter 0.5] [--camera-blur]
            [--range A:B] [--poster-frame 0] [--poster-samples N] [--encode-only] [--no-encode]
            [--set KEY=VALUE ...] [--no-lookdev] [--verbose]
    (from pc12/; the system python3 re-executes itself in /opt/venv-blender, override with $BLENDER_PYTHON)

The camera orbits 360 deg about the vertical axis through the aircraft's plan-view centre (bbox of the
posed, render-visible mesh) at --elev deg and --distance m (slant, to a target at mid-height).  Frame k
of N sits at azimuth start_az + 360 k / N (azimuth of the CAMERA seen from the aircraft, MODEL axes:
0 = behind the tail, -90 = port broadside, +-180 = ahead of the nose; 'ccw' = increasing, seen from
above), so the loop is seamless (frame N would repeat frame 0).  One focal length for the whole orbit:
the widest view (usually the wing diagonal) fills --fill of the width, the vertical envelope of all
azimuths is centred by a lens shift.

Studio = beauty.py's 'hero' preset, reused by import (no copy): the scene import / materials / pose
(beauty.Scene), the charcoal cyclorama with the glossy floor, the car-studio softboxes (HERO_LIGHTS, with
beauty's light linking) and the backdrop glow (beauty.studio_cyc via beauty.build_env), the softbox HDRI
for reflections, beauty.configure_render (AgX Punchy, OIDN) and beauty.finish_png (the hero grade).  The studio is built for the hero camera azimuth and then carried round with the
camera on one rig (cyclorama, lights, camera; the HDRI lookup is counter-rotated), so every frame is lit
exactly like the hero still -- the classic car turntable, equivalent to the aircraft turning on a
turntable in a fixed studio.  Turntable deltas to the hero preset (TT_OVERRIDES): a crisper floor
(roughness 0.10), fewer bounces, 16 spp adaptive (min 4, threshold 0.06), a 512 px HDRI importance map,
and the Cycles light tree OFF while lights are linked (hooks.light_tree_policy: Cycles 5.0.1's light tree
+ light linking is biased, +20 % on the cyclorama, and sprays fireflies -- 'glitter' -- over the glossy
floor; tree off equals the unlinked reference and renders faster); override anything with --set (beauty
syntax, e.g.
--set cyc.floor_rough=0.06 --set exposure=-0.3 --set pose.pitch=24).  If render/lookdev.py exists its
apply(bpy.data.materials, pre['lookdev']) runs where beauty.render_preset runs it (right after beauty's
materials; binding by parameter name in render/hooks.py, --no-lookdev skips it).

--prop-spin [RPM] (default 1700, the pivot's rpm) spins the propeller with motion blur: shutter
--shutter frames (0.5 = 180 deg), the rpm snapped so the loop holds a whole number of blade passages
(seamless), motion steps sized to the blur arc.  The orbit itself is NOT motion-blurred (the rig is
posed per frame, not keyframed) so the airframe stays crisp; --camera-blur keyframes it instead
(cinematic smear of the far wing tip, ~10 px at 1080p / 240 frames).

Efficiency: persistent data (BVH / images kept between frames: only the rig transform, the world rotation
and the prop change; a frame rendered in a persistent session is bit-identical to a fresh render of it --
checked), adaptive sampling, OIDN, low spp.  NB a persistent session ignores a new sample count until it
is reset (toggle use_persistent_data), which --poster-samples does.  Frames are written (graded, 8-bit) to
out/tmp/turntable/<stem>_frames/ (git-ignored) and RESUMED on a rerun with the same settings: a changed
setting or GLB discards them, edited code (beauty / lookdev / turntable) only warns (--restart discards);
--range A:B renders a slice (e.g. to split a long run over sessions).  When all N frames exist
they are encoded with Blender's own FFMPEG (sequencer, Standard view transform so the graded sRGB
frames pass through unchanged): H.264 in MP4, CRF 'HIGH', GOP = 1 s; then frame 0 and the middle frame are
decoded back from the MP4 and compared with the PNGs (PSNR in the sidecar).  Outputs next to --out:
<stem>.mp4, <stem>_poster.png (frame --poster-frame, or re-rendered with --poster-samples), <stem>.json
(settings, camera, per-frame timings, extrapolations) and <stem>_contact.jpg (8 frames).

Timings: every frame records wall and CPU seconds (the CPU was shared with 1-2 other Blender jobs, load
7-11 on 4 cores, so the CPU time is the portable number: idle wall ~ cpu-s / (0.95 x 4)); see TIMINGS.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from render import hooks  # noqa: E402

B = hooks.import_beauty()

OUT_MP4 = ROOT / "out" / "renders" / "turntable.mp4"
FRAMES_ROOT = ROOT / "out" / "tmp" / "turntable"
BLENDER_PY = B.BLENDER_PY

# turntable deltas to beauty.PRESETS['hero'] (everything else -- cyclorama colour, lights, HDRI, exposure,
# grade, pose -- is the hero preset's, so look development on the hero still carries over)
TT_OVERRIDES = dict(
    samples=16, noise_threshold=0.06, adaptive_min_samples=4,   # OIDN; the camera-locked studio keeps the
                                                                # background noise pattern still (fixed seed)
    world_map_res=512,                            # HDRI importance map (rebuilt every frame as the world turns)
    light_tree=None,                              # None: off while lights are linked (hooks.light_tree_policy)
    fast_gi=None,                                 # e.g. 1: Cycles fast GI (AO) after 1 bounce -- off by default
    bounces=(5, 2, 3, 3, 8),                      # max, diffuse, glossy, transmission, transparent
    cyc=dict(floor_rough=0.10),                   # merged into the hero 'cyc' dict: crisper floor reflection
    orbit=dict(elev=15.0, distance=34.0, fill=0.86, fill_h=0.82, align=(0.5, 0.5)),
)
TIMINGS = """
2026-09-25, out/pc12_snapshot.glb (~450k tris), lookdev materials, prop spin (1698 rpm, 180 deg shutter),
16 spp adaptive (min 4, thr 0.06) + OIDN, light tree off, 4 CPUs shared (load 7-11):
  640x360    48 frames : 13.1 cpu-s / frame (17.9 with the light tree on), 3.7 s wall at load 4; setup 4 s,
                         H.264 encode 0.5 s, decode check PSNR 39 dB, mean RGB within 0.3 of the PNGs
  1920x1080  3 frames  : 119-124 cpu-s / frame = 58 cpu-s / Mpx; wall 81-100 s at load ~9
  -> 240 frames at 1920x1080: ~2.1 h on 4 idle cores (32 s / frame; the 640x360 run extrapolates to
     2.07 h), ~6.4 h at the load measured during the 1080p frames
     (12 spp: ~25 % less; --range A:B splits the run across sessions, frames resume)
"""


# =============================================================================================
# preset + orbit geometry
# =============================================================================================
def hero_azimuth():
    """Camera azimuth (deg, MODEL) of the hero preset's look-at camera: the studio is designed for it."""
    fb = B.PRESETS["hero"]["camera"]["fallback"]
    d = np.asarray(fb["pos"], float) - np.asarray(fb["target"], float)
    return math.degrees(math.atan2(d[1], d[0]))


def turntable_preset():
    pre = copy.deepcopy(B.PRESETS["hero"])
    for k, v in copy.deepcopy(TT_OVERRIDES).items():
        if isinstance(v, dict) and isinstance(pre.get(k), dict):
            pre[k].update(v)
        else:
            pre[k] = v
    pre["photo"] = None
    return pre


def orbit_C(T, az_deg, el_deg, dist):
    a, e = math.radians(az_deg), math.radians(el_deg)
    return np.asarray(T, float) + dist * np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])


def frame_orbit(pts, T, el, dist, W, H, fill=0.86, fill_h=0.82, align=(0.5, 0.5), n=120):
    """One focal length + principal point for the whole orbit: the widest azimuth fills 'fill' of the
    width (the look-at target is on the rotation axis, so fit max |x|), the vertical envelope over all
    azimuths fills at most fill_h of the height and is centred at align[1] * H by a lens shift."""
    ex = []
    for az in np.linspace(-180.0, 180.0, n, endpoint=False):
        C = orbit_C(T, az, el, dist)
        R = B.lookat_R(C, T)
        Xc = (pts - C) @ R.T
        Xc = Xc[Xc[:, 2] > 0.1]
        x, y = Xc[:, 0] / Xc[:, 2], Xc[:, 1] / Xc[:, 2]
        ex.append((az, x.min(), x.max(), y.min(), y.max()))
    ex = np.asarray(ex)
    hx = max(-ex[:, 1].min(), ex[:, 2].max())
    y0, y1 = ex[:, 3].min(), ex[:, 4].max()
    f_w = fill * W / (2 * hx)
    f_h = fill_h * H / (y1 - y0)
    f = min(f_w, f_h)
    cx = align[0] * W
    cy = align[1] * H - f * 0.5 * (y0 + y1)
    widest = float(ex[int(np.argmax(np.maximum(-ex[:, 1], ex[:, 2]))), 0])
    return f, cx, cy, dict(f_px=round(f, 2), binding="width" if f_w <= f_h else "height",
                           widest_az_deg=round(widest, 1), hfov_deg=round(math.degrees(2 * math.atan(W / 2 / f)), 2),
                           lens_mm_36=round(f * 36.0 / W, 1),
                           height_fill=round(f * (y1 - y0) / H, 3), width_fill=round(2 * f * hx / W, 3))


# =============================================================================================
# scene
# =============================================================================================
class Turntable:
    def __init__(self, glb, pre, W, H, N, fps, start_az, direction, quiet=True, lookdev=None):
        import bpy
        self.bpy, self.pre, self.N, self.fps, self.dir = bpy, pre, int(N), int(fps), (1 if direction == "ccw" else -1)
        self.info = dict(created=time.strftime("%Y-%m-%d %H:%M:%S"), blender=bpy.app.version_string)
        t0 = time.time()
        S = self.S = B.Scene(glb, quiet=quiet)
        self.info.update(glb=S.glb_src, glb_mtime=S.glb_mtime, import_s=round(S.t_import, 1))
        before = set(bpy.data.objects.keys())
        S.hide(["structure"] + list(pre.get("hide", ())))
        S.materials(pre.get("paint"))
        # photo-matched materials exactly where beauty.render_preset applies them (after beauty's own)
        self.info["lookdev"] = hooks.apply_lookdev(lookdev, S=S, pre=pre, name="turntable", info=self.info,
                                                   context="turntable") if lookdev is not None else None
        self.info["pose"] = dict(pre.get("pose", {}))
        self.info["pose_result"] = S.pose(**pre.get("pose", {}))
        pts = S.visible_points()
        lo, hi = pts.min(0), pts.max(0)
        orb = pre["orbit"]
        self.T = np.array([0.5 * (lo[0] + hi[0]), 0.5 * (lo[1] + hi[1]), orb.get("target_z", 0.5 * (lo[2] + hi[2]))])
        el, dist = float(orb["elev"]), float(orb["distance"])
        f, cx, cy, fr = frame_orbit(pts, self.T, el, dist, W, H, orb.get("fill", 0.86), orb.get("fill_h", 0.82),
                                    tuple(orb.get("align", (0.5, 0.5))))
        # build the studio for the hero azimuth, then carry it round on the rig
        self.az_build = hero_azimuth()
        self.start_az = self.az_build if start_az is None else float(start_az)
        C0 = orbit_C(self.T, self.az_build, el, dist)
        cam0 = self.cam0 = B.Cam(B.lookat_R(C0, self.T), C0, f, W, H, cx, cy)
        B.build_env(S, pre, cam0, self.info)
        self.cam_obj = S.camera(cam0)
        rig = self.rig = bpy.data.objects.new("turntable_rig", None)
        S.sc.collection.objects.link(rig)
        rig.location = (float(self.T[0]), float(self.T[1]), 0.0)
        rig.rotation_mode = "XYZ"
        bpy.context.view_layer.update()
        inv = rig.matrix_world.inverted()
        carried = []
        for o in bpy.data.objects:
            if o.name in before or o is rig or o.parent is not None:
                continue
            o.parent = rig
            o.matrix_parent_inverse = inv
            carried.append(o.name)
        # world: HDRI lookup rotation (mapping node), counter-rotated with the rig
        self.map_node = None
        nt = S.sc.world.node_tree if S.sc.world else None
        for n in (nt.nodes if nt else ()):
            if n.type == "MAPPING":
                self.map_node = n
        self.rot0 = 0.0
        if self.map_node is not None:
            e = self.map_node.inputs["Rotation"].default_value
            if abs(e[0]) > 1e-6 or abs(e[1]) > 1e-6:
                self.info.setdefault("warnings", []).append("tilted environment: only its z rotation follows the rig")
            self.rot0 = float(e[2])
        S.sc.render.fps, S.sc.render.fps_base = self.fps, 1.0
        S.sc.frame_start, S.sc.frame_end = 1, self.N
        self.info.update(
            setup_s=round(time.time() - t0, 1),
            orbit=dict(pivot_model=self.T.round(3).tolist(), elev_deg=el, distance_m=dist, start_az_deg=round(self.start_az, 2),
                       studio_built_for_az_deg=round(self.az_build, 2), direction="ccw" if self.dir > 0 else "cw",
                       frames=self.N, fps=self.fps, seconds=round(self.N / self.fps, 2), **fr),
            camera_frame0=self.camera_at(0).to_json(), carried_by_rig=carried,
            bbox_model=[lo.round(3).tolist(), hi.round(3).tolist()])

    # -------------------------------------------------------------------------------------- per frame
    def theta(self, k):
        """Rig rotation (rad) for frame index k (0-based, may be fractional)."""
        return math.radians(self.start_az - self.az_build) + self.dir * 2 * math.pi * k / self.N

    def az(self, k):
        return (self.start_az + self.dir * 360.0 * k / self.N + 180.0) % 360.0 - 180.0

    def camera_at(self, k):
        th = self.theta(k)
        Rz = np.array([[math.cos(th), -math.sin(th), 0], [math.sin(th), math.cos(th), 0], [0, 0, 1.0]])
        p = np.array([self.T[0], self.T[1], 0.0])
        C = Rz @ (self.cam0.C - p) + p
        R = self.cam0.R @ Rz.T
        return B.Cam(R, C, self.cam0.f, self.cam0.W, self.cam0.H, self.cam0.cx, self.cam0.cy)

    def camera_blur(self):
        """Keyframe the orbit (instead of posing it per frame) so the shutter smears the camera motion."""
        rig = self.rig
        for fr, k in ((1, 0), (self.N + 1, self.N)):
            rig.rotation_euler[2] = self.theta(k)
            rig.keyframe_insert("rotation_euler", index=2, frame=fr)
            if self.map_node is not None:
                self.map_node.inputs["Rotation"].default_value[2] = self.rot0 - self.theta(k)
                self.map_node.inputs["Rotation"].keyframe_insert("default_value", index=2, frame=fr)
        for idb in (rig, self.S.sc.world.node_tree if self.map_node is not None else None):
            if idb is not None and idb.animation_data:
                _linear(idb.animation_data)
        self.keyed = True

    def set_frame(self, k):
        if not getattr(self, "keyed", False):
            self.rig.rotation_euler[2] = self.theta(k)
            if self.map_node is not None:
                self.map_node.inputs["Rotation"].default_value[2] = self.rot0 - self.theta(k)
        self.S.sc.frame_set(int(k) + 1)

    # -------------------------------------------------------------------------------------- propeller
    def prop_spin(self, rpm, shutter, blades=5):
        """Spin the propeller at ~rpm (snapped to a whole number of blade passages per loop) with motion
        blur over 'shutter' frames; returns the effective settings."""
        S, sc = self.S, self.S.sc
        prop, pv = S.parts.get("propeller"), S.pivot.get("propeller")
        if prop is None or pv is None:
            return dict(error="no propeller pivot in the GLB")
        loop_s = self.N / self.fps
        passes = max(1, round(rpm / 60.0 * loop_s * blades))
        rpm_eff = passes / blades / loop_s * 60.0
        w = rpm_eff / 60.0 * 2 * math.pi                    # rad/s; + = clockwise seen from the cockpit
        ax = B.gl2b(pv["axis"])
        prop.rotation_mode = "AXIS_ANGLE"
        a0 = float(prop.rotation_axis_angle[0])
        for fr, a in ((1, a0), (self.N + 1, a0 + w * loop_s)):
            prop.rotation_axis_angle = (a, *ax)
            prop.keyframe_insert("rotation_axis_angle", index=0, frame=fr)
        _linear(prop.animation_data)
        sc.render.use_motion_blur = True
        sc.render.motion_blur_shutter = float(shutter)
        for obj in (sc.render, sc.cycles):
            try:
                obj.motion_blur_position = "CENTER"
            except Exception:
                pass
        arc = math.degrees(w * shutter / self.fps)
        steps = 1 + max(0, math.ceil(math.log2(max(arc, 1.0) / 60.0)))   # <= ~60 deg per motion segment
        n = 0
        for o in S.meshes_of(["propeller"]):
            try:
                o.cycles.motion_steps = steps
                n += 1
            except Exception:
                pass
        per_frame = math.degrees(w / self.fps)
        return dict(rpm_requested=rpm, rpm=round(rpm_eff, 2), blade_passages_per_loop=passes, shutter_frames=shutter,
                    blur_arc_deg=round(arc, 1), deg_per_frame=round(per_frame, 1),
                    apparent_deg_per_frame=round((per_frame + 36.0) % 72.0 - 36.0, 1),
                    motion_steps=steps, meshes=n)


def _cpu():
    r = resource.getrusage(resource.RUSAGE_SELF)
    return r.ru_utime + r.ru_stime


def _linear(ad):
    for fc in B._fcurves(ad):
        fc.extrapolation = "LINEAR"
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


# =============================================================================================
# encode / verify / contact sheet
# =============================================================================================
def encode_mp4(frames, fps, out_mp4, crf="HIGH", preset="GOOD", quiet=True):
    """Graded 8-bit PNG frames -> H.264 MP4 through Blender's sequencer + FFMPEG (Standard view
    transform: sRGB in, sRGB out).  Wipes the current Blender scene."""
    import bpy
    from PIL import Image
    out_mp4 = Path(out_mp4)
    W, H = Image.open(frames[0]).size
    with B._quiet(quiet):
        bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
    sc.render.fps, sc.render.fps_base = int(fps), 1.0
    se = sc.sequence_editor_create()
    st = se.strips.new_image("frames", str(frames[0]), 1, 1)
    for p in frames[1:]:
        st.elements.append(Path(p).name)
    try:
        st.colorspace_settings.name = "sRGB"
    except Exception:
        pass
    sc.frame_start, sc.frame_end = 1, len(frames)
    _passthrough_colour(sc)
    sc.render.use_sequencer, sc.render.use_compositing = True, False
    ims = sc.render.image_settings
    ims.media_type = "VIDEO"
    ims.file_format = "FFMPEG"
    ff = sc.render.ffmpeg
    ff.format, ff.codec = "MPEG4", "H264"
    ff.constant_rate_factor, ff.ffmpeg_preset = crf, preset
    ff.gopsize = int(fps)
    ff.audio_codec = "NONE"
    stem = out_mp4.stem + "_enc_"
    for old in out_mp4.parent.glob(stem + "*"):
        old.unlink()
    sc.render.filepath = str(out_mp4.parent / stem)
    sc.render.use_file_extension = True
    t = time.time()
    with B._quiet(quiet):
        bpy.ops.render.render(animation=True)
    made = sorted(out_mp4.parent.glob(stem + "*.mp4"))
    if not made:
        raise RuntimeError(f"FFMPEG produced no file for {sc.render.filepath}")
    made[-1].replace(out_mp4)
    return dict(seconds=round(time.time() - t, 1), bytes=out_mp4.stat().st_size, codec="H.264", container="MP4",
                crf=crf, preset=preset, gop=int(fps), size=[W, H], frames=len(frames), fps=int(fps))


def _passthrough_colour(sc):
    sc.display_settings.display_device = "sRGB"
    vs = sc.view_settings
    vs.view_transform = "Standard"
    try:
        vs.look = "None"
    except Exception:
        pass
    vs.exposure, vs.gamma = 0.0, 1.0
    try:
        vs.use_white_balance = False
        vs.use_curve_mapping = False
    except Exception:
        pass
    try:
        sc.sequencer_colorspace_settings.name = "sRGB"
    except Exception:
        pass


def decode_check(mp4, frames, ks, tmp_dir, quiet=True):
    """Decode frames ks of the MP4 (sequencer movie strip) and compare with the source PNGs (PSNR dB)."""
    import bpy
    from PIL import Image
    with B._quiet(quiet):
        bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    W, H = Image.open(frames[0]).size
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
    se = sc.sequence_editor_create()
    st = se.strips.new_movie("mp4", str(mp4), 1, 1)
    n = int(st.frame_final_duration)
    sc.frame_start, sc.frame_end = 1, n
    _passthrough_colour(sc)
    sc.render.use_sequencer, sc.render.use_compositing = True, False
    ims = sc.render.image_settings
    ims.media_type, ims.file_format, ims.color_mode, ims.color_depth = "IMAGE", "PNG", "RGB", "8"
    res = dict(decoded_frames=n, fps=round(float(getattr(st, "fps", 0.0)), 3), psnr_db={})
    for k in ks:
        png = Path(tmp_dir) / f"decoded_{k:04d}.png"
        sc.frame_set(k + 1)
        sc.render.filepath = str(png)
        with B._quiet(quiet):
            bpy.ops.render.render(write_still=True)
        a = np.asarray(Image.open(png).convert("RGB"), np.float64)
        b = np.asarray(Image.open(frames[k]).convert("RGB"), np.float64)
        mse = float(np.mean((a - b) ** 2))
        res["psnr_db"][str(k)] = round(10 * math.log10(255.0 ** 2 / max(mse, 1e-9)), 2)
        res.setdefault("mean_rgb_png", {})[str(k)] = b.mean((0, 1)).round(1).tolist()
        res.setdefault("mean_rgb_mp4", {})[str(k)] = a.mean((0, 1)).round(1).tolist()
    return res


def contact_sheet(frames, out, n=8, cols=4, width=1600):
    from PIL import Image, ImageDraw
    idx = np.linspace(0, len(frames), n, endpoint=False).astype(int)
    ims = [Image.open(frames[i]).convert("RGB") for i in idx]
    W, H = ims[0].size
    tw = width // cols
    th = int(round(tw * H / W))
    rows = int(math.ceil(n / cols))
    sheet = Image.new("RGB", (tw * cols, th * rows), (20, 20, 22))
    d = ImageDraw.Draw(sheet)
    f = B._font(max(12, tw // 22))
    for j, (i, im) in enumerate(zip(idx, ims)):
        x, y = (j % cols) * tw, (j // cols) * th
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x + 6, y + 4), f"{i}", fill=(230, 230, 230), font=f)
    sheet.save(out, quality=88)
    return out


# =============================================================================================
# CLI
# =============================================================================================
def _signature(a, pre, glb):
    keys = dict(glb=str(glb), glb_mtime=Path(glb).stat().st_mtime, size=a.size, frames=a.frames, fps=a.fps,
                samples=a.samples, threshold=a.threshold, start_az=a.start_az, direction=a.direction,
                prop_spin=a.prop_spin, shutter=a.shutter, camera_blur=a.camera_blur, set=a.set,
                lookdev_enabled=hooks.LOOKDEV.exists() and not a.no_lookdev,
                pre=json.loads(json.dumps(pre, default=str)))
    code = dict(lookdev=(hashlib.sha1(hooks.LOOKDEV.read_bytes()).hexdigest()[:12]
                         if (hooks.LOOKDEV.exists() and not a.no_lookdev) else None),
                beauty=hashlib.sha1((HERE / "beauty.py").read_bytes()).hexdigest()[:12],
                turntable=hashlib.sha1(Path(__file__).read_bytes()).hexdigest()[:12])
    return keys, code


def _parse_range(s, N):
    if not s:
        return 0, N
    a, _, b = s.partition(":")
    return max(0, int(a or 0)), min(N, int(b or N))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--glb", default=str(B.GLB))
    ap.add_argument("--out", default=str(OUT_MP4), help="MP4 path (poster / JSON / contact sheet next to it)")
    ap.add_argument("--frames", type=int, default=240, help="frames per 360 deg")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--samples", type=int, default=None, help="max Cycles spp (adaptive; default 16)")
    ap.add_argument("--threshold", type=float, default=None, help="adaptive noise threshold (default 0.06)")
    ap.add_argument("--elev", type=float, default=None, help="camera elevation deg (default 15)")
    ap.add_argument("--distance", type=float, default=None, help="camera distance m (default 34)")
    ap.add_argument("--fill", type=float, default=None, help="width fill of the widest azimuth (default 0.86)")
    ap.add_argument("--start-az", type=float, default=None,
                    help="camera azimuth at frame 0, deg (default: the hero still's, front-port 3/4)")
    ap.add_argument("--direction", choices=("ccw", "cw"), default="ccw", help="orbit sense seen from above")
    ap.add_argument("--prop-spin", type=float, nargs="?", const=-1.0, default=None, metavar="RPM",
                    help="spin the propeller with motion blur (RPM, default: the GLB pivot's, 1700)")
    ap.add_argument("--shutter", type=float, default=0.5, help="motion-blur shutter in frames (0.5 = 180 deg)")
    ap.add_argument("--camera-blur", action="store_true", help="motion-blur the orbit too")
    ap.add_argument("--range", default=None, metavar="A:B", help="render only frame indices A..B-1")
    ap.add_argument("--poster-frame", type=int, default=0)
    ap.add_argument("--poster-samples", type=int, default=None, help="re-render the poster with more samples")
    ap.add_argument("--frames-dir", default=None)
    ap.add_argument("--restart", action="store_true", help="discard frames already rendered")
    ap.add_argument("--encode-only", action="store_true")
    ap.add_argument("--no-encode", action="store_true")
    ap.add_argument("--crf", default="HIGH", help="Blender FFMPEG constant_rate_factor (HIGH ~ crf 20)")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="override a field of the turntable preset (beauty.py --set syntax)")
    ap.add_argument("--no-lookdev", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args(argv)
    if not hooks.have_bpy():
        cmd = [BLENDER_PY, str(Path(__file__).resolve())] + (argv if argv is not None else sys.argv[1:])
        return subprocess.call(cmd)                        # same cwd: relative --out / --glb keep their meaning
    import bpy
    quiet = not a.verbose

    lookdev = hooks.load_lookdev(not a.no_lookdev)       # import-time patches land before the preset copy
    pre = turntable_preset()
    presets = {"turntable": pre}
    hooks.apply_sets(presets, ["turntable"], a.set)
    if a.samples is not None:
        pre["samples"] = a.samples
    if a.threshold is not None:
        pre["noise_threshold"] = a.threshold
    for k, v in (("elev", a.elev), ("distance", a.distance), ("fill", a.fill)):
        if v is not None:
            pre["orbit"][k] = v
    a.samples, a.threshold = int(pre["samples"]), float(pre["noise_threshold"])
    W, H = (int(v) for v in a.size.lower().split("x"))
    N = int(a.frames)
    glb = Path(a.glb)
    if not glb.is_absolute():
        glb = (Path.cwd() / glb) if (Path.cwd() / glb).exists() else ROOT / a.glb
    out_mp4 = Path(a.out).resolve()                      # relative paths: from the current directory
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    stem = out_mp4.with_suffix("")
    fdir = Path(a.frames_dir) if a.frames_dir else FRAMES_ROOT / f"{out_mp4.stem}_frames"
    fdir.mkdir(parents=True, exist_ok=True)
    frames = [fdir / f"f{k:04d}.png" for k in range(N)]
    side = Path(str(stem) + ".json")
    info = json.loads(side.read_text()) if (a.encode_only and side.exists()) else {}

    if not a.encode_only:
        sig, code = _signature(a, pre, glb)
        sig_file = fdir / "settings.json"
        old = json.loads(sig_file.read_text()) if sig_file.exists() else {}
        stale = list(fdir.glob("f*.png"))
        if old.get("settings") != sig or a.restart:
            if stale:
                why = "--restart" if a.restart else "settings / GLB changed"
                print(f"[turntable] {why}: removing {len(stale)} old frames in {fdir}", flush=True)
            for p in stale:
                p.unlink()
            old = {}
        elif stale and old.get("code") != code:
            # same settings, edited beauty / lookdev / turntable code: keep the frames (hours of work), but say so
            print(f"[turntable] WARNING: {len(stale)} frames were rendered with other code versions "
                  f"({old.get('code')} -> {code}); keeping them -- pass --restart to re-render all", flush=True)
        sig_file.write_text(json.dumps(dict(settings=sig, code=code,
                                            code_history=old.get("code_history", []) + [code]), indent=1, default=str))
        k0, k1 = _parse_range(a.range, N)
        todo = [k for k in range(k0, k1) if not frames[k].exists()]
        prop_rpm = None
        if a.prop_spin is not None:
            prop_rpm = a.prop_spin
        print(f"[turntable] {W}x{H}, {N} frames @ {a.fps} fps, {a.samples} spp (thr {a.threshold}); "
              f"{len(todo)} to render in {fdir.relative_to(ROOT) if fdir.is_relative_to(ROOT) else fdir}", flush=True)
        t_all = time.time()
        tt = Turntable(glb, pre, W, H, N, a.fps, a.start_az, a.direction, quiet=quiet, lookdev=lookdev)
        info = tt.info
        info["settings"] = dict({k: v for k, v in sig.items() if k != "pre"}, code=code)
        info["preset"] = json.loads(json.dumps(pre, default=float))
        if prop_rpm is not None:
            pv = tt.S.pivot.get("propeller", {})
            info["prop_spin"] = tt.prop_spin(pv.get("rpm", 1700.0) if prop_rpm < 0 else prop_rpm, a.shutter)
        if a.camera_blur:
            tt.camera_blur()
            sc = tt.S.sc
            sc.render.use_motion_blur = True
            sc.render.motion_blur_shutter = float(a.shutter)
        raw0 = fdir / "_raw.png"
        B.configure_render(tt.S, pre, a.samples, raw0)
        sc, c = tt.S.sc, tt.S.sc.cycles
        sc.render.use_persistent_data = True               # BVH, images, shaders kept between frames
        c.adaptive_min_samples = min(int(pre.get("adaptive_min_samples", 8)), a.samples)
        hooks.light_tree_policy(tt.S, pre, info)           # off with light linking (Cycles 5.0.1 bias)
        if pre.get("world_map_res") and sc.world is not None:
            sc.world.cycles.sampling_method = "MANUAL"
            sc.world.cycles.sample_map_resolution = int(pre["world_map_res"])
        if pre.get("fast_gi"):
            c.use_fast_gi, c.fast_gi_method = True, "REPLACE"
            c.ao_bounces_render = int(pre["fast_gi"])
        if info.get("lookdev") is None:
            info["lookdev"] = hooks.lookdev_status(lookdev, not a.no_lookdev)
        info["setup_total_s"] = round(time.time() - t_all, 1)
        per = []
        for j, k in enumerate(todo):
            tt.set_frame(k)
            raw = fdir / f"f{k:04d}.raw.png"
            sc.render.filepath = str(raw)
            t, u = time.time(), _cpu()
            with B._quiet(quiet):
                bpy.ops.render.render(write_still=True)
            tr = time.time() - t
            B.finish_png(raw, pre.get("grade"))
            raw.replace(frames[k])
            dt, du = time.time() - t, _cpu() - u
            per.append(dict(k=k, az=round(tt.az(k), 2), render_s=round(tr, 2), total_s=round(dt, 2), cpu_s=round(du, 1)))
            rest = np.median([p["total_s"] for p in per[1:]] if len(per) > 1 else [dt]) * (len(todo) - j - 1)
            print(f"  frame {k:4d} az {tt.az(k):7.1f}: {tr:6.1f} s render, {dt:6.1f} s total, {du:6.1f} cpu-s "
                  f"(x{du / max(dt, 1e-6):.1f})   (eta {rest / 60:5.1f} min)", flush=True)
        # poster
        poster = Path(str(stem) + "_poster.png")
        pk = int(a.poster_frame) % N
        if a.poster_samples:
            if a.camera_blur:                              # a still: no orbit smear on the poster
                for idb in (tt.rig, sc.world.node_tree if sc.world else None):
                    for fc in (B._fcurves(idb.animation_data) if idb is not None and idb.animation_data else ()):
                        fc.mute = True
                tt.keyed = False
            tt.set_frame(pk)
            c.samples = int(a.poster_samples)
            # a persistent Cycles session ignores a new sample count until it is reset: toggle it
            sc.render.use_persistent_data = False
            sc.render.use_persistent_data = True
            raw = fdir / "poster.raw.png"
            sc.render.filepath = str(raw)
            t = time.time()
            with B._quiet(quiet):
                bpy.ops.render.render(write_still=True)
            B.finish_png(raw, pre.get("grade"))
            raw.replace(poster)
            info["poster"] = dict(frame=pk, samples=a.poster_samples, render_s=round(time.time() - t, 1))
        elif frames[pk].exists():
            shutil.copyfile(frames[pk], poster)
            info["poster"] = dict(frame=pk, samples=a.samples)
        shutil.rmtree(tt.S.tmpdir, ignore_errors=True)
        info["frames_rendered"] = per
        rs = [p["render_s"] for p in per]
        ts = [p["total_s"] for p in per]
        cs = [p["cpu_s"] for p in per]
        if per:
            steady = ts[1:] if len(ts) > 1 else ts
            med = float(np.median(steady))
            cmed = float(np.median(cs[1:] if len(cs) > 1 else cs))
            ncpu = os.cpu_count() or 4
            info["timing"] = dict(
                size=[W, H], samples=a.samples, rendered=len(per), first_frame_s=ts[0],
                median_frame_s=round(med, 2), mean_frame_s=round(float(np.mean(steady)), 2),
                median_render_only_s=round(float(np.median(rs[1:] if len(rs) > 1 else rs)), 2),
                render_wall_s=round(time.time() - t_all, 1),
                s_per_megapixel=round(med / (W * H / 1e6), 2),
                median_cpu_s=round(cmed, 1), cpu_s_per_megapixel=round(cmed / (W * H / 1e6), 1),
                load_avg=[round(v, 2) for v in os.getloadavg()],
                extrapolate_240f_1920x1080_min=round((info["setup_total_s"] + ts[0]
                                                      + 239 * med * (1920 * 1080) / (W * H)) / 60.0, 1),
                extrapolate_240f_1920x1080_idle_min=round(240 * cmed / (0.95 * ncpu) * (1920 * 1080) / (W * H) / 60.0, 1),
                note="wall = at the measured CPU contention; idle = cpu-s / (0.95 x %d cores); both linear in "
                     "pixels at the same spp -- measure at the final size for a better number" % ncpu)
        info["frames_dir"] = str(fdir)

    have = [p for p in frames if p.exists()]
    if len(have) == N and not a.no_encode:
        info["encode"] = encode_mp4(frames, a.fps, out_mp4, crf=a.crf, quiet=quiet)
        info["encode"]["file"] = str(out_mp4)
        tmpd = ROOT / "out" / "tmp" / "turntable"
        info["decode_check"] = decode_check(out_mp4, frames, sorted({0, N // 2}), tmpd, quiet=quiet)
        cs = Path(str(stem) + "_contact.jpg")
        contact_sheet(frames, cs)
        info["contact_sheet"] = str(cs)
        print(f"[turntable] -> {out_mp4} ({info['encode']['bytes'] / 1e6:.1f} MB, {N} frames, "
              f"{info['encode']['seconds']} s encode); decode PSNR {info['decode_check']['psnr_db']}", flush=True)
    elif not a.no_encode:
        print(f"[turntable] {len(have)}/{N} frames present: not encoding yet", flush=True)
    side.write_text(json.dumps(info, indent=1, default=float))
    if "timing" in info:
        t = info["timing"]
        print(f"[turntable] {t['rendered']} frames at {W}x{H}: first {t['first_frame_s']} s, median "
              f"{t['median_frame_s']} s/frame ({t['s_per_megapixel']} s/Mpx); 240 f @ 1920x1080 ~ "
              f"{t['extrapolate_240f_1920x1080_min']} min", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
