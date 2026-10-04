#!/usr/bin/env python3
"""Headless end-to-end test of the three.js viewer (web/index.html).

Starts a local HTTP server on a free port, opens the viewer in headless Chromium (SwiftShader)
with ?three=local, fails on console / page errors, renders the scenario screenshots into
out/tmp/viewer/ and runs numeric kinematic checks through the window.viewer hooks:
  - brace lower-link end stays on the gear attach point B (11 gear positions per gear),
    and the JS knee matches model/brace.py (the Python reference)
  - flap trailing edge moves down and aft; Fowler travel matches the pivot data
  - ailerons / elevators / rudder / stabiliser / tabs move in the documented directions,
    tabs opposite to their surfaces
  - nose doors are open whenever the nose gear is not locked up (gear down and in transit; instant poses and the
    real animated sequence); mains retract inward, nose gear aft; doors open outward
  - review round-1 regressions: gear readout when scrubbed, readouts never stale, shortcuts after a
    slider / button click, search Escape, wing structure hidden once the skins land, nothing below
    the ground when exploded / flying in, zero-explode parts grow in place, current build step always
    inside the panel, first camera fit uses the free viewport (and follows panel toggles), windshield
    see-through from the cockpit, prop blur disc follows exploded blades, compact info card on phones
  - propeller in motion (owner 2026-10-03, web/viewer/propblur.js): solid blades only while they turn < P / 8 a frame
    (60 / 30 fps), the blur sweep >= 2.5 frame steps, the ghost only moves forward (<= 0.4 P a frame), the disc in the
    plane of rotation on the thrust axis just outside the tips, kept in X-ray / cutaway / explode, spool-up / run-down
    times, and pixels: the averaged disc 60-97 % see-through, the true pattern azimuthally smooth, the white tip
    ring; review r3: the ghost's fan visible at 1,700 rpm [PR3-01], picks through the outer disc reach the parts
    behind it [PR3-02], the disc translucent edge-on [PR3-03]
  - review round-2 (viewer): AgX + Punchy look and per-theme exposure, one GLB request (preloaded), the
    meshopt-compressed GLB (web/package.py) decodes to the same triangles, loading errors without WebGL 2 or when a
    module fails to load, phone pixel ratio (taps keep it, drags and their coast drop it), 40 px touch targets,
    sheet header tap, landscape phone layout
  - merged with the stage-4 model: every GLB material has a viewer material, materials.json = the lookdev table,
    KHR_materials_clearcoat applied once, the interior lining lit as the cabin; every part of the GLB group 'Interior'
    (seats, floor, consoles, divider, tables, crew controls) lit as the cabin, the table's emissive displays / cabin
    lights and the GLB's sheepskin sheen carried into the viewer materials
  - review round-3 (viewer): WebGL context loss and restore (a note while lost, redraws by itself, same image), the
    Specs table fits the landscape panel, safe-area insets (landscape notch, portrait home indicator)
  - picture quality (owner 2026-10-03 "sharper crisper picture", web/viewer/picture.js): the still supersampling engages
    when still (2x multisampled target, jittered passes accumulated) and releases while moving, target sizes within the
    pixel / byte budget and the GL limits, MSAA samples (canvas and target), the same colours and position as the plain
    frame, moving supersampling and the no-MSAA canvas path, max anisotropy + mipmaps on every texture, specular AA, the
    PCSS ground shadow on a fitted shadow camera, the 1k HDRI, Auto's calibration (drained, min of 3) and the passes
    given back once frames fit, single supersampled passes while moving / while the prop spins, 1x / 2x still scales, the
    phone still canvas at the native ratio within the budget, the contact shadow at 512 while animating, the Specs panel's setting
    remembered across a reload, no GL / console errors
  - interior tour (viewer/tour.js, owner 2026-10-03 "no good link to navigate into the interior"): the toolbar entry
    (desktop and phone), every stop reached from the menu with the camera inside the cabin (tables and ray clearances)
    and well exposed (both themes), the walk held inside the cabin at every boundary, keyboard / pointer / touch
    controls, the flights, and exit restoring the exterior state; the tour data current with the interior tables;
    review r3 [T13]: a forward walk into a crew seat, the walk levelling a stop's steep look, the aisle's aft end
    looking aft, the strafe out of an aft-facing seat, the airstair stop and its hint
Optional --blender: re-imports out/pc12.glb in Blender (bpy, /opt/venv-blender) and checks
that Blender's scene graph gives the same part boxes and posed points as the viewer, and runs a
BVH interference sweep of the gear against doors / flaps / flight deck.  Interferences that are
GLB-data issues owned by model/gear.py are reported as KNOWN (they do not fail the run; they flip
to PASS once the GLB is fixed).

  - engine / propeller sound (owner 2026-10-03, web/viewer/sound.js): no AudioContext before a user gesture (off by
    default under automation, ?sound=1 turns it on) nor for a gesture with the engine off, the gesture that starts the
    engine makes one, the graph follows the state (blade-passing frequency = 5 x rpm / 60, the whine rising with Ng
    through the start, the propeller still until light-off, reverse / feather levels), quieter and low-passed inside
    with the whine kept faintly, M mutes, suspended when hidden / stopped; offline renders through the same graph:
    start -> idle -> 1,700 rpm -> reverse -> fine -> feather -> shutdown as a WAV + spectrogram (--sound-out) with its
    lines, dBA levels, BS.1770 loudness per phase (the default listening level, the start, the light-off), limiter /
    output curve, stereo and texture measured; close-ups under the loudness ceiling (idle, the loudest state), a steady
    run (noise loops), the start from the flight deck (the whine through the firewall)
usage: python3 test/viewer_test.py [--blender] [--no-shots] [--three cdn] [--only sound] [--sound-out DIR]
Exit code 0 = all checks pass.
"""
from __future__ import annotations

import argparse
import asyncio
import functools
import glob
import json
import math
import os
import subprocess
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]           # pc12/
OUT = ROOT / "out" / "tmp" / "viewer"
sys.path.insert(0, str(ROOT))

VIEW = {"width": 960, "height": 600}
PHONE = {"width": 390, "height": 844}
LAUNCH_ARGS = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]
# SwiftShader rasterises the MeshPhysicalMaterial scene on the CPU (~5-10 s a frame at 960x600); a screenshot
# waits for the frames already queued, so Playwright's 30 s default is too tight (after the paint sweep, shot 09, a
# capture took 27-31 s on the shared 4-core sandbox with the Stage-2 GLB too)
SHOT_TIMEOUT = 240000

results: list[tuple[str, bool, str, bool]] = []
CTX: dict = {}   # extra browser-context options (see --three cdn)


def check(name: str, ok: bool, detail: str = "", known: bool = False) -> bool:
    """known=True: a documented defect outside the viewer (GLB data); reported, never fails the run."""
    results.append((name, bool(ok), detail, known))
    return bool(ok)


def gl_to_model(p):
    return [p[2], p[0], p[1]]


def model_to_gl(p):
    return [p[1], p[2], p[0]]


def sub(a, b):
    return [x - y for x, y in zip(a, b)]


def norm(a):
    return math.sqrt(sum(x * x for x in a))


# ----------------------------------------------------------------------------- server / browser
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


class QuietServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        # the browser aborting a transfer (page closed mid-download) is not an error
        if isinstance(sys.exc_info()[1], (ConnectionResetError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


def start_server():
    srv = QuietServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def proxy_opts() -> dict:
    """Chromium ignores HTTPS_PROXY: pass it explicitly (local test server bypassed) so the CDN is reachable
    from sandboxes that only have an outbound proxy."""
    p = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    return {"proxy": {"server": p, "bypass": "127.0.0.1,localhost"}} if p else {}


async def launch(pw, args=None):
    """Launch Chromium; fall back to any installed Playwright build if the pinned one is missing."""
    LAUNCH_ARGS = args if args is not None else globals()["LAUNCH_ARGS"]
    exe = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
    if exe:
        return await pw.chromium.launch(executable_path=exe, args=LAUNCH_ARGS, **proxy_opts())
    try:
        return await pw.chromium.launch(args=LAUNCH_ARGS, **proxy_opts())
    except Exception as first:
        base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")
        # newest first; the headless shell (Playwright's default headless binary) before full Chromium
        cands = sorted(glob.glob(f"{base}/chromium_headless_shell-*/chrome-linux*/headless_shell"), reverse=True)
        cands += sorted(glob.glob(f"{base}/chromium-*/chrome-linux*/chrome"), reverse=True)
        for c in cands:
            try:
                return await pw.chromium.launch(executable_path=c, args=LAUNCH_ARGS, **proxy_opts())
            except Exception:
                continue
        raise first


# ----------------------------------------------------------------------------- JS helpers
JS_HELPERS = r"""
window.T = {
  V: window.viewer,
  sub: (a, b) => a.map((x, i) => x - b[i]),
  add: (a, b) => a.map((x, i) => x + b[i]),
  // attach a world point (current pose) to a part: returns its local coordinates
  attach: (id, p) => window.viewer.worldToLocal(id, p),
  world: (id, local) => window.viewer.nodeWorldPoint(id, local),
  box: (id) => window.viewer.partWorldBox(id),
  // a point at the trailing edge (max Z) / leading edge (min Z) of a part at its current pose
  te: (id) => { const b = window.viewer.partWorldBox(id); return [b.center[0], b.center[1], b.max[2] - 0.01]; },
  le: (id) => { const b = window.viewer.partWorldBox(id); return [b.center[0], b.center[1], b.min[2] + 0.01]; },
  neutral: () => {
    const V = window.viewer;
    V.setExplode(0, {instant: true}); V.setGear(0, {instant: true}); V.setFlaps(0, {instant: true});
    V.setDoor('airstair', 0, {instant: true}); V.setDoor('cargo', 0, {instant: true});
    V.setProp({rpm: 0, pitch: 0, angle: 0}, {instant: true});
    V.setControls({roll: 0, pitch: 0, yaw: 0, stabTrim: 0, ailTrim: 0, rudTrim: 0}, {instant: true});
  },
  // lowest world Y over the visible top-level parts (their boxes include child parts)
  lowest: () => {
    const V = window.viewer, I = V._internals; let m = Infinity, who = '';
    for (const id of V.visibleParts()) { if (I.model.part(id).parent) continue; const y = V.partWorldBox(id).min[1]; if (y < m) { m = y; who = id; } }
    return [m, who];
  },
  // per part: world bounds of the vertices its triangles use + the triangle count (rest pose; compares two GLB
  // encodings of the same model: unreferenced vertices, which gltf-transform drops, are ignored)
  geo: () => {
    const V = window.viewer, I = V._internals, v = new I.THREE.Vector3(), out = {};
    I.model.root.updateMatrixWorld(true);
    for (const id of V.parts()) {
      const b = [Infinity, Infinity, Infinity, -Infinity, -Infinity, -Infinity, 0];
      for (const mr of I.model.part(id).meshes) {
        const m = mr.mesh, g = m.geometry, P = g.attributes.position, idx = g.index;
        if (!P) continue;
        const n = idx ? idx.count : P.count;
        for (let k = 0; k < n; k++) {
          const i = idx ? idx.getX(k) : k;
          v.fromBufferAttribute(P, i).applyMatrix4(m.matrixWorld);
          if (v.x < b[0]) b[0] = v.x; if (v.y < b[1]) b[1] = v.y; if (v.z < b[2]) b[2] = v.z;
          if (v.x > b[3]) b[3] = v.x; if (v.y > b[4]) b[4] = v.y; if (v.z > b[5]) b[5] = v.z;
        }
        b[6] += Math.floor(n / 3);
      }
      out[id] = b;
    }
    return out;
  },
  // projected silhouette of the aircraft vs the free part of the viewport (not under the panel /
  // bottom sheet / toolbar), in CSS px
  fit: () => {
    const V = window.viewer, I = V._internals, cam = I.stage.camera, pts = I.stage.silhouette;
    cam.updateMatrixWorld();
    const cv = I.stage.renderer.domElement.getBoundingClientRect();
    const panel = document.getElementById('panel').getBoundingClientRect(), tb = document.getElementById('toolbar').getBoundingClientRect();
    const narrow = matchMedia('(max-width: 760px) and (min-height: 501px)').matches, open = document.getElementById('app').classList.contains('panel-open');
    const free = {x0: 0, x1: narrow || !open ? innerWidth : panel.left, y0: tb.bottom, y1: narrow ? panel.top : innerHeight};
    const v = new I.THREE.Vector3(); let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    for (let i = 0; i < pts.length; i += 3) {
      v.set(pts[i], pts[i + 1], pts[i + 2]).project(cam);
      const x = cv.left + (v.x + 1) / 2 * cv.width, y = cv.top + (1 - v.y) / 2 * cv.height;
      x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
    }
    return {free, box: [x0, x1, y0, y1], preset: V.state.cameraPreset,
      inside: x0 >= free.x0 - 2 && x1 <= free.x1 + 2 && y0 >= free.y0 - 2 && y1 <= free.y1 + 2,
      fill: Math.max((x1 - x0) / (free.x1 - free.x0), (y1 - y0) / (free.y1 - free.y0))};
  },
};
"""


async def js(page, body, arg=None):
    """Evaluate an async function body in the page."""
    return await page.evaluate("async (arg) => { " + body + " }", arg)


async def shot(page, name, setup, wait_frames=2, note=""):
    if setup:
        await js(page, setup)
    await js(page, f"await window.viewer.frames({wait_frames});")
    path = OUT / f"{name}.png"
    await page.screenshot(path=str(path), timeout=SHOT_TIMEOUT)
    print(f"  shot {path.relative_to(ROOT)} {note}")
    return path


# ----------------------------------------------------------------------------- scenarios
async def screenshots(page):
    print("screenshots ->", OUT.relative_to(ROOT))
    V = "const V = window.viewer; "
    await shot(page, "01_finished_3q", V + "T.neutral(); V.setStep('paint', {instant: true}); V.setCamera('three_quarter', {instant: true});")
    await shot(page, "02_step01_datum", V + "V.setStep('datum', {instant: true});")
    await shot(page, "03_step02_structure", V + "V.setStep('structure', {instant: true});")
    await shot(page, "04_step05_fuselage_primer", V + "V.setStep('fuselage_aft', {instant: true});")
    await shot(page, "05_step08_wing_flyin", V + "V.setStep('doors', {instant: true}); V.setStep('wing'); V.advance(0.95);",
               note="(mid fly-in, t = 0.95 s)")
    await shot(page, "06_step13_powerplant", V + "V.setStep('powerplant', {instant: true});")
    await shot(page, "07_step17_interior_cutaway", V + "V.setStep('interior', {instant: true});")
    await shot(page, "08_step19_paint_spraying", V + "V.setStep('details', {instant: true}); V.setStep('paint'); V.advance(1.35);",
               note="(livery sweep in progress)")
    await shot(page, "09_step19_painted", V + "V.advance(3.0);")
    await shot(page, "10_explode_1", V + "V.setExplode(1, {instant: true});")
    await shot(page, "11_cutaway", V + "V.setExplode(0, {instant: true}); V.setCutaway(true);")
    await shot(page, "12_xray", V + "V.setCutaway(false); V.setXray(true);")
    await shot(page, "13_construction_lines", V + "V.setXray(false); V.setConstruction(true); V.setCamera('side', {instant: true});")
    await shot(page, "14_gear_mid_retraction", V + "V.setConstruction(false); V.setCamera('gear_bay', {instant: true}); V.setGear(0.5, {instant: true});")
    await shot(page, "15_gear_up", V + "V.setCamera({pos: [-7.5, 1.1, -6.5], target: [0, 1.25, 5.2], fov: 38}, {instant: true}); V.setGear('up', {instant: true});")
    await shot(page, "16_flaps_40", V + "V.setGear('down', {instant: true}); V.setCamera({pos: [-9.5, 5.2, 15.5], target: [-2.8, 1.0, 6.6], fov: 40}, {instant: true}); V.setFlaps(40, {instant: true});")
    await shot(page, "17_doors_open", V + "V.setFlaps(0, {instant: true}); V.setCamera({pos: [-8.5, 2.2, 6.6], target: [-0.6, 1.6, 6.8], fov: 50}, {instant: true}); V.setDoor('airstair', 1, {instant: true}); V.setDoor('cargo', 1, {instant: true});")
    await shot(page, "18_controls_tail", V + "V.setDoor('airstair', 0, {instant: true}); V.setDoor('cargo', 0, {instant: true}); V.setCamera({pos: [3.8, 5.0, 17.6], target: [0, 3.5, 14.0], fov: 40}, {instant: true}); V.setControls({roll: 1, pitch: 1, yaw: 1}, {instant: true});",
               note="(pull + right rudder: elevator TEs up, rudder TE to starboard)")
    await shot(page, "18b_controls_right_aileron", V + "V.setCamera({pos: [9.6, 1.62, 8.4], target: [6.3, 1.42, 6.45], fov: 34}, {instant: true});",
               note="(right roll: right aileron up, Flettner tab down)")
    await shot(page, "19_prop_feathered", V + "V.setControls({roll: 0, pitch: 0, yaw: 0}, {instant: true}); V.setCamera({pos: [-2.6, 2.3, -2.4], target: [0, 1.6, 1.0], fov: 45}, {instant: true}); V.setProp({rpm: 0, pitch: 62}, {instant: true});")
    await shot(page, "20_prop_1700rpm", V + "V.setProp({rpm: 1700, pitch: 0}, {instant: true}); V.advance(0.2); V.pause(true);",
               note="(blurred disc: blade colours as faint rings)")
    await shot(page, "20b_prop_120rpm", V + "V.pause(false); V.setProp({rpm: 120, pitch: 0}, {instant: true}); V.advance(0.2); V.pause(true);",
               note="(spool-up: smeared blades)")
    await shot(page, "20c_prop_front_1700rpm", V + "V.pause(false); V.setCamera({pos: [0.05, 1.6, -3.5], target: [0, 1.65, 0.95], fov: 45}, {instant: true}); V.setProp({rpm: 1700, pitch: 0}, {instant: true}); V.advance(0.2); V.pause(true);")
    await shot(page, "21_cockpit", V + "V.pause(false); V.setProp({rpm: 0, pitch: 0}, {instant: true}); V.setCamera('cockpit', {instant: true});")
    await shot(page, "22_selected_part", V + "V.setCamera('three_quarter', {instant: true}); V.tab('parts'); V.select('eng_combustor', {instant: true});")
    await shot(page, "23_selected_in_xray", V + "V.setXray(true); V.setCamera('gear_bay', {instant: true}); V.select('gear_main_R', {instant: true});")
    await js(page, "window.viewer.select(null); window.viewer.setXray(false); window.viewer.tab('animate');")
    await shot(page, "24_animate_tab", "window.viewer.setCamera('three_quarter', {instant: true});")
    await shot(page, "25_drawings_ga", "window.viewer.tab('drawings'); await new Promise(r => setTimeout(r, 800));")
    await shot(page, "26_drawings_sections", "document.querySelector('[data-sheet=\"1\"]').click(); await new Promise(r => setTimeout(r, 800));")
    await shot(page, "27_specs", "window.viewer.tab('specs');")
    await js(page, "window.viewer.tab('build');")


# ----------------------------------------------------------------------------- numeric checks
async def numeric_checks(page):
    print("numeric checks")
    await js(page, "T.neutral(); window.viewer.setStep('paint', {instant: true}); window.viewer.tab('build');")

    # --- brace IK: lower-link end on B, and knee == model/brace.py reference
    from model.brace import pose as brace_pose
    for gear, up in (("gear_main_R", "brace_main_R_up"), ("gear_main_L", "brace_main_L_up"), ("gear_nose", "brace_nose_up")):
        lo = up.replace("_up", "_lo")
        data = await js(page, r"""
          const [gear, up, lo] = arg; const V = window.viewer;
          const pv = V.partExtras(up).pivot, g = V.partExtras(gear).pivot;
          const gl = (a) => [a[1], a[2], a[0]];
          const A = gl(pv.A), B0 = gl(pv.B0), K0 = gl(pv.K0);
          const out = [];
          for (let k = 0; k <= 10; k++) {
            V.setGear(k / 10, {instant: true});
            out.push({
              f: k / 10,
              end: V.nodeWorldPoint(lo, T.sub(B0, K0)),        // far end of the lower link
              B: V.nodeWorldPoint(gear, T.sub(B0, g.origin)),  // leg attach point, moving with the gear
              K: V.nodeWorldPoint(up, T.sub(K0, A)),           // knee = far end of the upper link
            });
          }
          V.setGear(0, {instant: true});
          return {pv, g, out};
        """, [gear, up, lo])
        pv, g = data["pv"], data["g"]
        worst = max(norm(sub(s["end"], s["B"])) for s in data["out"]) * 1000
        check(f"brace {up[:-3]}: lower-link end on B (11 poses)", worst < 2.0, f"max {worst:.3f} mm")
        # Python reference: brace.pose in model axes
        A, B0, K0 = pv["A"], pv["B0"], pv["K0"]
        g_origin_m, g_axis_m = gl_to_model(g["origin"]), gl_to_model(g["axis"])
        axis_m = gl_to_model(pv["axis"])
        import numpy as np
        worst_k = worst_b = 0.0
        for s in data["out"]:
            ang = math.radians(g["retract"] * s["f"])
            B, K = brace_pose(np.array(A), np.array(B0), np.array(K0), np.array(g_origin_m), np.array(g_axis_m), ang,
                              pv["L1"], pv["L2"], np.array(axis_m), np.array(pv["bend"]))
            worst_k = max(worst_k, norm(sub(s["K"], model_to_gl(list(K)))) * 1000)
            worst_b = max(worst_b, norm(sub(s["B"], model_to_gl(list(B)))) * 1000)
        check(f"brace {up[:-3]}: knee matches model/brace.py", worst_k < 0.5 and worst_b < 0.5,
              f"knee {worst_k:.4f} mm, B {worst_b:.4f} mm")

    # --- flaps: trailing edge down + aft, Fowler travel as stored (model axes -> gl)
    r = await js(page, r"""
      const V = window.viewer, out = {};
      for (const id of ['flap_R', 'flap_L']) {
        T.neutral();
        const te0 = T.te(id), loc = T.attach(id, te0), o0 = V.nodeWorldPoint(id, [0, 0, 0]);
        V.setFlaps(40, {instant: true});
        out[id] = {te0, te1: T.world(id, loc), o0, o1: V.nodeWorldPoint(id, [0, 0, 0]), travel: V.partExtras(id).pivot.travel};
      }
      T.neutral();
      return out;
    """)
    for id_, d in r.items():
        dy, dz = d["te1"][1] - d["te0"][1], d["te1"][2] - d["te0"][2]
        check(f"{id_} 40 deg: trailing edge down & aft", dy < -0.2 and dz > 0.05, f"dY {dy:+.3f} m, dZ {dz:+.3f} m")
        tr = model_to_gl(d["travel"])
        err = norm(sub(sub(d["o1"], d["o0"]), tr)) * 1000
        check(f"{id_} 40 deg: Fowler travel = pivot.travel", err < 1.0, f"hinge moved {[round(x, 3) for x in sub(d['o1'], d['o0'])]}, err {err:.2f} mm")

    # --- ailerons, tabs, elevators, rudder, stabiliser trim, tab trims
    r = await js(page, r"""
      const V = window.viewer, out = {};
      T.neutral();
      const P = {};
      for (const id of ['aileron_R', 'aileron_L', 'elevator_R', 'elevator_L', 'rudder', 'rudder_tab']) { const p = T.te(id); P[id] = {w0: p, loc: T.attach(id, p)}; }
      for (const id of ['ail_tab_R', 'ail_tab_L']) {
        const p = T.te(id), par = id === 'ail_tab_R' ? 'aileron_R' : 'aileron_L';
        P[id] = {w0: p, loc: T.attach(id, p), par, parLoc0: T.attach(par, p)};
      }
      const le = T.le('stabilizer'); P.stab = {w0: le, loc: T.attach('stabilizer', le)};
      const w = (id) => T.world(id, P[id].loc);
      const rel = (id) => T.sub(T.attach(P[id].par, w(id)), P[id].parLoc0);   // tab motion in its aileron's frame
      for (const roll of [1, -1]) {
        V.setControls({roll}, {instant: true});
        out['roll' + roll] = {aR: T.sub(w('aileron_R'), P.aileron_R.w0), aL: T.sub(w('aileron_L'), P.aileron_L.w0),
          tR: rel('ail_tab_R'), tL: rel('ail_tab_L'), defl: V.state.deflections};
      }
      V.setControls({roll: 0, pitch: 1}, {instant: true});
      out.pull = {eR: T.sub(w('elevator_R'), P.elevator_R.w0), eL: T.sub(w('elevator_L'), P.elevator_L.w0)};
      V.setControls({pitch: -1}, {instant: true});
      out.push = {eR: T.sub(w('elevator_R'), P.elevator_R.w0), eL: T.sub(w('elevator_L'), P.elevator_L.w0)};
      V.setControls({pitch: 0, yaw: 1}, {instant: true});
      out.yawR = {r: T.sub(w('rudder'), P.rudder.w0)};
      V.setControls({yaw: 0, stabTrim: -4}, {instant: true});
      out.stabNoseUp = {le: T.sub(T.world('stabilizer', P.stab.loc), P.stab.w0), eR: T.sub(w('elevator_R'), P.elevator_R.w0)};
      V.setControls({stabTrim: 0, rudTrim: 10}, {instant: true});
      out.rudTrim = {t: T.sub(w('rudder_tab'), P.rudder_tab.w0), defl: V.state.deflections.rudder_tab};
      V.setControls({rudTrim: 0, ailTrim: 5}, {instant: true});
      out.ailTrim = {tL: rel('ail_tab_L'), tR: rel('ail_tab_R'), defl: V.state.deflections.ail_tab_L};
      T.neutral();
      return out;
    """)
    a = r["roll1"]
    check("right roll: right aileron TE up, left aileron TE down", a["aR"][1] > 0.05 and a["aL"][1] < -0.03,
          f"dY R {a['aR'][1]:+.3f}, L {a['aL'][1]:+.3f} m")
    a2 = r["roll-1"]
    check("left roll: left aileron TE up, right aileron TE down", a2["aL"][1] > 0.05 and a2["aR"][1] < -0.03,
          f"dY R {a2['aR'][1]:+.3f}, L {a2['aL'][1]:+.3f} m")
    d = a["defl"]
    check("aileron differential (up 20 / down 15)", abs(d["aileron_R"] + 20) < 1e-6 and abs(d["aileron_L"] - 15) < 1e-6,
          f"R {d['aileron_R']:+.1f}, L {d['aileron_L']:+.1f} deg")
    ok_tabs = (a["tR"][1] < -0.002 and a["tL"][1] > 0.002 and a2["tR"][1] > 0.002 and a2["tL"][1] < -0.002)
    check("Flettner tabs move opposite to their ailerons", ok_tabs,
          f"tab dY in aileron frame: roll+ R {a['tR'][1]*1000:+.1f} L {a['tL'][1]*1000:+.1f} mm; roll- R {a2['tR'][1]*1000:+.1f} L {a2['tL'][1]*1000:+.1f} mm")
    check("tab gearing -0.6 x aileron", abs(d["ail_tab_R"] - 12) < 1e-6 and abs(d["ail_tab_L"] + 9) < 1e-6,
          f"tab R {d['ail_tab_R']:+.1f}, tab L {d['ail_tab_L']:+.1f} deg")
    p = r["pull"]
    check("pull: both elevator TEs up", p["eR"][1] > 0.05 and p["eL"][1] > 0.05, f"dY R {p['eR'][1]:+.3f}, L {p['eL'][1]:+.3f} m")
    p = r["push"]
    check("push: both elevator TEs down", p["eR"][1] < -0.05 and p["eL"][1] < -0.05, f"dY R {p['eR'][1]:+.3f}, L {p['eL'][1]:+.3f} m")
    check("right yaw: rudder TE to starboard (+X)", r["yawR"]["r"][0] > 0.1, f"dX {r['yawR']['r'][0]:+.3f} m")
    s = r["stabNoseUp"]
    check("stab trim -4 (nose-up): leading edge down, elevators ride along", s["le"][1] < -0.02 and s["eR"][1] > 0.02,
          f"LE dY {s['le'][1]:+.3f} m, elevator TE dY {s['eR'][1]:+.3f} m")
    check("rudder tab trim +10: tab TE to starboard", r["rudTrim"]["t"][0] > 0.01, f"dX {r['rudTrim']['t'][0]:+.3f} m")
    t = r["ailTrim"]
    check("left aileron tab trim +5: tab TE down, right tab unaffected", t["tL"][1] < -0.002 and abs(t["tR"][1]) < 1e-6,
          f"L {t['tL'][1]*1000:+.1f} mm, R {t['tR'][1]*1000:+.2f} mm")

    # --- crew controls (review r2 M4): the yokes roll with the roll command about their columns and slide with pitch,
    #     the rudder pedals swing with yaw (right rudder: right-foot pedals forward = -Z)
    r = await js(page, r"""
      const V = window.viewer, out = {};
      T.neutral();
      if (!V._internals.model.part('yoke_L')) return {missing: true};
      const hub = V.nodeWorldPoint('yoke_L', [0, 0, 0]);
      const g0 = [hub[0] + 0.12, hub[1] + 0.08, hub[2]];               // a point up the right grip (gl: +X = stbd)
      const loc = T.attach('yoke_L', g0);
      const pads = {};
      // a point on the pad, near its lower end (the hanging pedals' arms run up to the pivot under the panel: model
      // judging r1 INT-m1)
      for (const id of ['pedal_LL', 'pedal_LR']) { const b = T.box(id); const p = [b.center[0], b.min[1] + 0.05, b.center[2]]; pads[id] = {p0: p, loc: T.attach(id, p)}; }
      V.setControls({roll: 1}, {instant: true});
      out.rollR = T.sub(T.world('yoke_L', loc), g0);
      V.setControls({roll: 0, pitch: 1}, {instant: true});
      out.pull = T.sub(V.nodeWorldPoint('yoke_L', [0, 0, 0]), hub);
      const nb = T.box('gear_nose_steer'), nw = [nb.center[0], nb.center[1], nb.min[2] + 0.02];   // tyre front
      const nloc = V._internals.model.part('gear_nose_steer') ? T.attach('gear_nose_steer', nw) : null;
      V.setControls({pitch: 0, yaw: 1}, {instant: true});
      out.yawR = {L: T.sub(T.world('pedal_LL', pads.pedal_LL.loc), pads.pedal_LL.p0), R: T.sub(T.world('pedal_LR', pads.pedal_LR.loc), pads.pedal_LR.p0)};
      if (nloc) { out.steer = V.state.controls.steerDeg; out.noseFront = T.sub(T.world('gear_nose_steer', nloc), nw); }
      V.setGear(1, {instant: true});
      out.steerUp = V.state.controls.steerDeg;
      V.setGear(0, {instant: true});
      T.neutral();
      return out;
    """)
    if r.get("missing"):
        check("crew controls are viewer parts (yoke_L / pedals)", False, "yoke_L not in the GLB")
    else:
        check("right roll: the pilot's yoke turns clockwise (right grip goes down)", r["rollR"][1] < -0.03,
              f"grip point dY {r['rollR'][1]:+.3f} m")
        check("pull: the yoke comes aft (+Z) by the pitch travel", abs(r["pull"][2] - 0.09) < 0.005,
              f"hub dZ {r['pull'][2]:+.3f} m")
        check("right rudder: right-foot pedal forward, left-foot pedal aft", r["yawR"]["R"][2] < -0.03 and
              r["yawR"]["L"][2] > 0.03, f"pad dZ R {r['yawR']['R'][2]:+.3f}, L {r['yawR']['L'][2]:+.3f} m")
        check("[MJ r1 GR1-07] right rudder steers the nose wheel right (tyre front to +X), centred with the gear up",
              "steer" in r and r["steer"] > 10 and r["noseFront"][0] > 0.02 and abs(r["steerUp"]) < 1e-6,
              f"steer {r.get('steer', 'missing')} deg, tyre-front dX {r.get('noseFront', [0])[0]:+.3f} m, gear up "
              f"{r.get('steerUp')}")
    # --- the cutaway clips the cabin furniture / divider port half, not the seats or the controls (review r2 M3);
    #     every part is cut whole or not at all (review r3 C1: cup holders / switch caps floated over a clipped
    #     console), and the floors the seats stand on stay (review r3 F4)
    r = await js(page, r"""
      const V = window.viewer, I = V._internals, out = {};
      V.setCutaway(true);
      const cut = (mr) => (mr.mesh.material.clippingPlanes || []).some((p) => p.normal.x === 1 && p.constant === 0);
      const clipped = (id, mat) => I.model.part(id) ? I.model.part(id).meshes.filter((mr) => !mat || mr.base.name === mat)
                                   .map(cut) : [];
      out.divider = clipped('fd_divider');
      out.consoles = clipped('fd_consoles');
      out.ledge = clipped('cabin_interior', 'ledge_top');
      out.flight_deck = clipped('flight_deck');
      out.cabin_floor = clipped('cabin_floor');
      out.seat = clipped('seat_pax1');
      out.yoke = clipped('yoke_L');
      // parts cut by a material subset (some meshes clipped, some kept)
      out.mixed = I.model.list.filter((p) => p.ex.group === 'Interior' && p.meshes.length &&
        new Set(p.meshes.map(cut)).size > 1).map((p) => p.id);
      // every seat stands on an uncut floor: the kept floor meshes (cabin_floor carpet, flight-deck carpet) cover the
      // seat's footprint centre (glTF X = BL, Z = STA)
      const floors = [...I.model.part('cabin_floor').meshes, ...I.model.part('flight_deck').meshes
        .filter((mr) => mr.base.name === 'carpet_flightdeck')].filter((mr) => !cut(mr));
      const fb = floors.map((mr) => new I.THREE.Box3().setFromObject(mr.mesh));
      out.unsupported = I.model.list.filter((p) => /^seat_/.test(p.id)).filter((p) => {
        const b = V.partWorldBox(p.id), cx = 0.5 * (b.min[0] + b.max[0]), cz = 0.5 * (b.min[2] + b.max[2]);
        return !fb.some((f) => f.min.x <= cx && cx <= f.max.x && f.min.z <= cz && cz <= f.max.z &&
          f.min.y <= b.min[1] + 0.03 && f.max.y >= b.min[1] - 0.03);
      }).map((p) => p.id);
      V.setCutaway(false);
      return out;
    """)
    check("cutaway clips the divider, consoles and cabin ledges (port halves), not the panel, floors, seats or yokes",
          all(r["divider"]) and all(r["consoles"]) and all(r["ledge"]) and not any(r["flight_deck"]) and
          not any(r["cabin_floor"]) and not any(r["seat"]) and not any(r["yoke"]),
          json.dumps({k: (sum(v), len(v)) if isinstance(v, list) and v and isinstance(v[0], bool) else v
                      for k, v in r.items()}))
    check("[r3 C1] cutaway: every interior part cut whole or not at all (nothing left floating)", not r["mixed"],
          f"mixed: {r['mixed']}")
    check("[r3 F4] cutaway: every seat stands on an uncut floor", not r["unsupported"],
          f"{len(r['unsupported'])} unsupported: {r['unsupported']}")
    # --- club tables (review r3 F5): stowed = inside the ledge (fully clipped at the fascia), out at 0.5, the inboard
    #     leaf unfolded over the aisle at 1
    r = await js(page, r"""
      const V = window.viewer, I = V._internals, out = {};
      if (!I.model.part('table_club_p')) return {missing: true};
      const bx = () => { const b = V.partWorldBox('table_club_p_leaf'); return [b.min[0], b.max[0], b.min[1], b.max[1]]; };
      const ob = () => { const b = V.partWorldBox('table_club_p'); return [b.min[0], b.max[0]]; };
      const fascia = I.model.part('table_club_p').ex.pivot.fascia_bl;
      V.setTable(0, {instant: true}); out.stowed = ob(); out.fascia = fascia;
      V.setTable(0.5, {instant: true}); out.leaf = ob(); out.leafFolded = bx();
      V.setTable(1, {instant: true}); out.deployed = bx();
      V.setTable(0, {instant: true});
      out.clip = I.model.part('table_club_p').meshes.every((mr) => (mr.mesh.material.clippingPlanes || []).length > 0);
      return out;
    """)
    if r.get("missing"):
        check("[r3 F5] club tables are viewer parts", False, "table_club_p not in the GLB")
    else:
        check("[r3 F5] club table: stowed inside the ledge (outboard of the fascia, clipped there), the leaf out, the "
              "inboard leaf unfolded over the aisle",
              r["clip"] and r["stowed"][1] <= r["fascia"] + 0.035 and r["leaf"][1] > -0.40 and
              r["deployed"][1] > -0.10 and r["deployed"][2] > r["leafFolded"][3] - 0.001,
              json.dumps({k: [round(x, 3) for x in v] if isinstance(v, list) else v for k, v in r.items()}))

    # --- gear: mains inward, nose aft, nose doors open between the locks
    r = await js(page, r"""
      const V = window.viewer, out = {};
      T.neutral();
      const wheel = (id) => { const b = T.box(id); return [b.center[0], b.min[1] + 0.22, b.center[2]]; };
      const P = {};
      for (const id of ['gear_main_R', 'gear_main_L', 'gear_nose']) { const p = wheel(id); P[id] = {w0: p, loc: T.attach(id, p)}; }
      out.downDoor = V.state.gear.door;
      out.doorDown = (V.partExtras('gear_door_NR').pivot.rest || 0);   // the pose the GLB builds the doors in
      V.setGear(1, {instant: true});
      for (const id of ['gear_main_R', 'gear_main_L', 'gear_nose']) out[id] = T.sub(T.world(id, P[id].loc), P[id].w0);
      out.upDoor = V.state.gear.door;
      // nose-door free (inboard) edges, taken with the gear locked up (doors closed)
      for (const id of ['gear_door_NR', 'gear_door_NL']) {
        const b = T.box(id), p = [id.endsWith('R') ? b.min[0] + 0.01 : b.max[0] - 0.01, b.center[1], b.center[2]];
        P[id] = {w0: p, loc: T.attach(id, p)};
      }
      const samples = [];
      for (let k = 0; k <= 9; k++) {
        V.setGear(k / 10, {instant: true});
        const s = V.state.gear;
        samples.push({f: k / 10, door: s.door, doorDeg: s.noseDoorDeg, noseDeg: s.noseDeg,
          dNR: T.sub(T.world('gear_door_NR', P.gear_door_NR.loc), P.gear_door_NR.w0)[1],
          dNL: T.sub(T.world('gear_door_NL', P.gear_door_NL.loc), P.gear_door_NL.w0)[1]});
      }
      out.samples = samples;
      // real sequence, stepped deterministically (1/20 s)
      const seq = (dir) => {
        const rows = [];
        V.setGear(dir === 'up' ? 0 : 1, {instant: true});
        V.setGear(dir);
        for (let i = 0; i < 400; i++) {
          const g = V.advance(0.05).gear;
          rows.push([+(0.05 * (i + 1)).toFixed(2), g.pos, g.door, g.noseDeg, g.noseDoorDeg]);
          if (g.pos === g.target && g.door === (g.target >= 1 ? 0 : 1) && !g.moving) break;
        }
        return rows;
      };
      out.seqUp = seq('up');
      out.seqDown = seq('down');
      T.neutral();
      return out;
    """)
    check("right main retracts inward", r["gear_main_R"][0] < -0.3, f"wheel dX {r['gear_main_R'][0]:+.3f} m")
    check("left main retracts inward", r["gear_main_L"][0] > 0.3, f"wheel dX {r['gear_main_L'][0]:+.3f} m")
    check("nose gear retracts aft (and up)", r["gear_nose"][2] > 0.3 and r["gear_nose"][1] > 0.3,
          f"wheel dZ {r['gear_nose'][2]:+.3f}, dY {r['gear_nose'][1]:+.3f} m")
    bad = [s for s in r["samples"] if s["door"] < 0.999 or s["dNR"] > -0.08 or s["dNL"] > -0.08]
    check("nose doors open (85 deg, edges below closed) with the gear down and at 10..90 %", not bad,
          f"door {min(abs(s['doorDeg']) for s in r['samples']):.1f} deg, edge dY <= "
          f"{max(max(s['dNR'], s['dNL']) for s in r['samples']):+.3f} m")
    check("nose doors: open at rest (gear down, built open: pivot.rest 1), closed when locked up",
          r["downDoor"] == 1 and r["upDoor"] == 0 and r["doorDown"] == 1,
          f"door {r['downDoor']} down / {r['upDoor']} up, pivot.rest {r['doorDown']}")
    for name in ("seqUp", "seqDown"):
        rows = r[name]
        target = 1.0 if name == "seqUp" else 0.0
        door_end = 0.0 if target else 1.0      # nose doors close only once locked up; open with the gear down
        between_closed = [row for row in rows if 1e-9 < row[1] < 1 - 1e-9 and row[2] < 0.999]
        first_move = next((row for row in rows if abs(row[1] - (1 - target)) > 1e-9), None)
        end = rows[-1]
        ok = not between_closed and first_move is not None and first_move[2] >= 0.999 and end[1] == target and \
            end[2] == door_end
        check(f"gear {'up' if target else 'down'} sequence: doors open -> gear -> doors "
              f"{'close' if target else 'stay open'} ({door_end:g})", ok,
              f"{end[0]:.2f} s total; gear starts at {first_move[0] if first_move else '?'} s with doors {first_move[2] if first_move else '?'}; "
              f"{len(between_closed)} samples with doors not fully open in transit")

    # --- doors open outward (port side: -X); airstair down, cargo up
    r = await js(page, r"""
      const V = window.viewer; T.neutral();
      const b1 = T.box('door_airstair'), b2 = T.box('door_cargo');
      const p1 = [b1.center[0], b1.max[1] - 0.02, b1.center[2]], p2 = [b2.center[0], b2.min[1] + 0.02, b2.center[2]];
      const l1 = T.attach('door_airstair', p1), l2 = T.attach('door_cargo', p2);
      V.setDoor('airstair', 1, {instant: true}); V.setDoor('cargo', 1, {instant: true});
      const out = {air: T.sub(T.world('door_airstair', l1), p1), cargo: T.sub(T.world('door_cargo', l2), p2)};
      T.neutral();
      return out;
    """)
    check("airstair door: top edge swings out and down", r["air"][0] < -0.3 and r["air"][1] < -0.5, f"dX {r['air'][0]:+.3f}, dY {r['air'][1]:+.3f} m")
    check("cargo door: bottom edge swings out and up", r["cargo"][0] < -0.3 and r["cargo"][1] > 0.5, f"dX {r['cargo'][0]:+.3f}, dY {r['cargo'][1]:+.3f} m")

    # --- [RAIL-1] airstair handrail + restraint cables stay pinned through the door's travel (owner 2026-10-04: the
    # upper rod and the cables had flown in "from the sky", turning up to 189 deg about mid-air centres): the lower
    # rod's knee = the telescoping rod's knee end, the rod's far end on the jamb pivot, the sleeve pointing at the knee,
    # each cable from its door clamp to its jamb fitting; no pinned end moves more than 0.15 m per 1/40 of the command
    r = await js(page, r"""
      const V = window.viewer; T.neutral();
      const ids = ['door_airstair', 'door_airstair_rail', 'door_airstair_rail_up', 'door_airstair_cable', 'door_airstair_rail_sleeve'];
      const ex = {}, org = {};
      for (const id of ids) { ex[id] = V.partExtras(id); org[id] = V.nodeWorldPoint(id, [0, 0, 0]); }
      if (ids.some((id) => !ex[id])) return {missing: ids.filter((id) => !ex[id])};
      const J = (id, k) => ex[id].pivot.joints[k];
      const P = (id, w) => V.meshWorldPoint(id, T.sub(w, org[id]));
      const N = (id, w) => V.nodeWorldPoint(id, T.sub(w, org[id]));
      const A = J('door_airstair_rail_up', 'A'), Cj = J('door_airstair_cable', 'Cj'), Cs = J('door_airstair_cable', 'Cs');
      const rows = [];
      for (let i = 0; i <= 40; i++) {
        const v = i / 40;
        V.setDoor('airstair', v, {instant: true});
        const kLo = P('door_airstair_rail', J('door_airstair_rail', 'K'));
        const kUp = P('door_airstair_rail_up', J('door_airstair_rail_up', 'K'));
        const aUp = P('door_airstair_rail_up', A);
        const sl = N('door_airstair_rail_sleeve', T.add(A, T.sub(J('door_airstair_rail_up', 'K'), A)));
        rows.push({v, kLo, kUp, aUp, sl, cj: P('door_airstair_cable', Cj), cs: P('door_airstair_cable', Cs),
                   csDoor: N('door_airstair', Cs), top: Math.max(...ids.slice(1).map((id) => T.box(id).max[1]))});
      }
      V.setDoor('airstair', 0, {instant: true}); T.neutral();
      return {A, Cj, rows};
    """)
    if r.get("missing"):
        check("[RAIL-1] airstair handrail parts present", False, f"missing {r['missing']}")
    else:
        d = lambda a, b: math.dist(a, b)                                          # noqa: E731
        knee = max(math.hypot(q["kLo"][0] - q["kUp"][0], q["kLo"][1] - q["kUp"][1]) for q in r["rows"])
        a_err = max(d(q["aUp"], r["A"]) for q in r["rows"])
        cj_err = max(d(q["cj"], r["Cj"]) for q in r["rows"])
        cs_err = max(d(q["cs"], q["csDoor"]) for q in r["rows"])

        def ang(q):   # sleeve axis vs the line jamb pivot -> knee (deg), in the (X, Y) plane of the rails
            u = (q["sl"][0] - r["A"][0], q["sl"][1] - r["A"][1])
            w = (q["kUp"][0] - r["A"][0], q["kUp"][1] - r["A"][1])
            c = (u[0] * w[0] + u[1] * w[1]) / max(math.hypot(*u) * math.hypot(*w), 1e-12)
            return math.degrees(math.acos(max(-1.0, min(1.0, c))))
        sl_err = max(ang(q) for q in r["rows"])
        step = max(max(d(a[k], b[k]) for k in ("kLo", "aUp", "cj", "cs"))
                   for a, b in zip(r["rows"], r["rows"][1:]))
        top = max(q["top"] for q in r["rows"])
        check("[RAIL-1] airstair handrail pinned through the swing: knee joint, rod end on the jamb pivot, sleeve on "
              "the knee, cables jamb -> clamp; no jumps",
              knee < 0.002 and a_err < 0.002 and sl_err < 0.5 and cj_err < 0.002 and cs_err < 0.002 and step < 0.15
              and top < 2.62,
              f"knee {1000 * knee:.2f} mm, rod end {1000 * a_err:.2f} mm, sleeve {sl_err:.2f} deg, cable jamb "
              f"{1000 * cj_err:.2f} / clamp {1000 * cs_err:.2f} mm, max step {1000 * step:.0f} mm per 1/40, top WL "
              f"{top:.3f}")

    # --- propeller: spin + feather
    r = await js(page, r"""
      const V = window.viewer; T.neutral();
      // Z (airflow) extent of blade 1 over the pitch range: feathering turns the chord into the airflow
      const zs = [];
      for (let p = -38; p <= 62; p += 10) { V.setProp({pitch: p}, {instant: true}); zs.push([p, T.box('blade_1').size[2]]); }
      V.setProp({pitch: 0}, {instant: true});
      const z0 = T.box('blade_1').size[2];
      V.setProp({pitch: 62}, {instant: true});
      const z1 = T.box('blade_1').size[2];
      V.setProp({pitch: 0, rpm: 1700}, {instant: true});
      const a0 = V.state.prop.angle; V.advance(1 / 60); const a1 = V.state.prop.angle;
      T.neutral();
      return {z0, z1, zs, da: a1 - a0};
    """)
    zmax = max(z for _, z in r["zs"])
    check("feather: blade chord turns into the airflow", r["z1"] > r["z0"] + 0.05 and r["z1"] >= 0.97 * zmax,
          f"blade_1 airflow extent fine {r['z0']:.3f} m -> feather {r['z1']:.3f} m (max over -38..62: {zmax:.3f} m)")
    expect = 1700 / 60 * 2 * math.pi / 60
    check("1,700 rpm: prop turns 28.3 rev/s", abs(r["da"] - expect) < 1e-3, f"{r['da']:.4f} rad per 1/60 s (expect {expect:.4f})")

    # --- explode offsets (hierarchical)
    r = await js(page, r"""
      const V = window.viewer; T.neutral();
      const c0 = {f: T.box('fus_fwd').center, b: V.nodeWorldPoint('blade_1', [0, 0, 0])};
      V.setExplode(1, {instant: true});
      const c1 = {f: T.box('fus_fwd').center, b: V.nodeWorldPoint('blade_1', [0, 0, 0])};
      V.setExplode(0, {instant: true});
      return {df: T.sub(c1.f, c0.f), db: T.sub(c1.b, c0.b), ef: V.partExtras('fus_fwd').explode,
        eb: V.partExtras('blade_1').explode.map((x, i) => x + V.partExtras('propeller').explode[i])};
    """)
    check("explode 1.0 moves a part by its explode vector", norm(sub(r["df"], r["ef"])) < 1e-3, f"{[round(x, 3) for x in r['df']]}")
    check("explode is hierarchical (blade = propeller + own)", norm(sub(r["db"], r["eb"])) < 1e-3, f"{[round(x, 3) for x in r['db']]}")

    # --- build steps, primer / paint, construction lines
    r = await js(page, r"""
      const V = window.viewer, out = {};
      V.setStep('datum', {instant: true});
      out.datum = {vis: V.visibleParts().length, lines: V.state.linesVisible};
      V.setStep('doors', {instant: true});
      const vd = V.visibleParts();
      V.setStep('wing', {instant: true});
      const vw = V.visibleParts();
      out.wing = {wing: vw.includes('wing_R'), flap: vw.includes('flap_R'), paint: V.state.paint, sweep: V.state.paintSweep,
        structure: vw.includes('structure'), structureBefore: vd.includes('structure')};
      V.setStep('doors', {instant: true}); V.setStep('wing'); V.advance(0.6);
      out.wing.structureFlying = V.visibleParts().includes('structure');
      V.advance(4.0);
      out.wing.structureLanded = V.visibleParts().includes('structure');
      V.setStep('glazing', {instant: true}); V.setStep('doors'); V.advance(0.3);
      out.flying = {doorVisible: V.visibleParts().includes('door_airstair')};
      V.advance(3.0);
      out.landed = {doorVisible: V.visibleParts().includes('door_airstair'), pos: V.nodeWorldPoint('door_airstair', [0, 0, 0]), rest: V.partExtras('door_airstair').pivot.origin};
      V.setStep('details', {instant: true}); V.setStep('paint'); V.advance(0.5);
      out.spray = V.state.paintSweep;
      V.advance(4);
      out.painted = {paint: V.state.paint, sweep: V.state.paintSweep, vis: V.visibleParts().length, total: V.parts().length};
      V.setStep('interior', {instant: true});
      out.interior = V.state.cutaway;
      V.setStep('paint', {instant: true});
      out.final = V.state.cutaway;
      return out;
    """)
    check("step 'datum': construction only", r["datum"]["vis"] == 0 and r["datum"]["lines"] > 20, f"{r['datum']['vis']} parts, {r['datum']['lines']} construction objects")
    w = r["wing"]
    check("step 'wing': earlier parts shown, later hidden, skins in primer", w["wing"] and not w["flap"] and not w["paint"] and w["sweep"] < -50,
          f"paint={w['paint']} sweep={w['sweep']}")
    check("[BV-1] wing structure shown while the wing flies in, hidden once the skins land (no rib spikes)",
          w["structureBefore"] and w["structureFlying"] and not w["structureLanded"] and not w["structure"],
          f"doors {w['structureBefore']}, wing flying {w['structureFlying']}, landed {w['structureLanded']}, wing instant {w['structure']}")
    check("fly-in: parts appear, then land exactly at rest", r["flying"]["doorVisible"] is False and r["landed"]["doorVisible"]
          and norm(sub(r["landed"]["pos"], r["landed"]["rest"])) < 1e-6, "staggered start, lands at pivot origin")
    check("paint step: livery sprays on, then all parts painted", -3 < r["spray"] < 18 and r["painted"]["paint"] and r["painted"]["sweep"] == 100
          and r["painted"]["vis"] == r["painted"]["total"] - 1, f"sweep mid {r['spray']:.2f} m; {r['painted']['vis']}/{r['painted']['total']} parts visible (structure only in X-ray)")
    check("interior step auto-cutaway (reverts at the end)", r["interior"] and not r["final"])

    # --- cutaway / x-ray picking through the port side at the cabin
    r = await js(page, r"""
      const V = window.viewer; T.neutral(); V.setStep('paint', {instant: true});
      V.setCamera('side', {instant: true});
      // probe on the port cabin skin at STA 7.30, WL 1.60: clear of the canted port winglet (side view x 5.63-7.11,
      // WL 1.69-2.18), aft of window P3, ahead of the cargo-door seam; the cutaway ray then hits the side ledge
      const p = V.project([-0.3, 1.60, 7.3]);
      const out = {normal: V.pick(p[0], p[1])};
      V.setCutaway(true); out.cut = V.pick(p[0], p[1]);
      V.setCutaway(false); V.setXray(true); out.xray = V.pick(p[0], p[1]); out.structure = V.state.structureVisible;
      V.setXray(false);
      return out;
    """)
    skins = {"fus_center", "glazing_cabin", "door_frames"}
    check("pick without cutaway hits the skin", r["normal"] in skins, str(r["normal"]))
    check("cutaway exposes the cabin (pick goes inside)", r["cut"] not in skins and r["cut"] is not None, str(r["cut"]))
    check("x-ray: structure shown, picking prefers inner parts", r["structure"] and r["xray"] not in skins and r["xray"] is not None, str(r["xray"]))

    # --- selection / info card / tabs
    r = await js(page, r"""
      const V = window.viewer;
      V.select('eng_combustor', {instant: true});
      const card = document.getElementById('infoCard');
      const out = {sel: V.state.selected, card: !card.hidden, name: document.getElementById('icName').textContent};
      V.select(null);
      out.cleared = document.getElementById('infoCard').hidden;
      V.tab('specs');
      out.checks = document.querySelectorAll('#checksTable tbody tr').length;
      V.tab('drawings');
      await new Promise(r => setTimeout(r, 600));
      const img = document.getElementById('drawingImg');
      out.drawing = {visible: !document.getElementById('drawingView').hidden, w: img.naturalWidth};
      V.tab('build');
      return out;
    """)
    check("select(): highlight + info card", r["sel"] == "eng_combustor" and r["card"] and "Combustion" in r["name"], r["name"])
    check("select(null) clears the card", r["cleared"])
    check("specs tab: dimension checks table", r["checks"] >= 10, f"{r['checks']} rows")
    check("drawings tab: SVG loaded", r["drawing"]["visible"] and r["drawing"]["w"] > 100, f"naturalWidth {r['drawing']['w']}")

    # --- build auto-play and the scripted demo, stepped deterministically
    r = await js(page, r"""
      const V = window.viewer; T.neutral();
      V.setStep(0, {instant: true}); V.play(true);
      const steps = new Set();
      for (let i = 0; i < 400 && V.state.playing; i++) { V.advance(0.25); steps.add(V.state.step); }
      const play = {steps: steps.size, end: V.state.stepKey, playing: V.state.playing};
      V.demo();
      let gearMax = 0, flapMax = 0, rpmMax = 0, doorMax = 0, t = 0;
      for (; t < 120 && V.state.demo; t += 0.25) {
        V.advance(0.25);
        await new Promise((res) => setTimeout(res, 0));   // let the demo's awaits continue
        const s = V.state;
        gearMax = Math.max(gearMax, s.gear.pos); flapMax = Math.max(flapMax, s.flaps);
        rpmMax = Math.max(rpmMax, s.prop.rpm); doorMax = Math.max(doorMax, s.doors.airstair);
      }
      V.advance(5);
      const s = V.state;
      return {play, demo: {t, gearMax, flapMax, rpmMax, doorMax, running: s.demo, gearEnd: s.gear.pos, doorEnd: s.doors.airstair}};
    """)
    p = r["play"]
    check("build auto-play runs every step and stops at the end", p["steps"] >= 18 and p["end"] == "paint" and not p["playing"],
          f"{p['steps']} steps visited, ends on {p['end']}")
    d = r["demo"]
    check("demo sequence runs to completion", not d["running"] and d["gearMax"] == 1 and d["flapMax"] == 40 and d["rpmMax"] > 1600
          and d["doorMax"] == 1 and d["gearEnd"] == 0 and d["doorEnd"] == 0,
          f"{d['t']:.1f} s; gear up {d['gearMax']}, flaps {d['flapMax']:.0f}, rpm {d['rpmMax']:.0f}, doors {d['doorMax']}")
    await js(page, "T.neutral(); window.viewer.setStep('paint', {instant: true}); window.viewer.setCamera('three_quarter', {instant: true});")

    # --- hover highlight (desktop mouse) and drawing zoom
    xy = await js(page, "T.neutral(); window.viewer.select(null); window.viewer.setCamera('side', {instant: true}); return window.viewer.project([-0.84, 2.1, 7.2]);")
    await page.mouse.move(xy[0] - 30, xy[1])
    await page.mouse.move(xy[0], xy[1])
    await js(page, "await new Promise(r => setTimeout(r, 400)); await window.viewer.frames(2);")
    hov = await js(page, "return window.viewer.state.hovered;")
    check("hover highlights the part under the mouse", hov in ("fus_center", "glazing_cabin", "door_frames"), str(hov))
    await page.mouse.move(2, 300)
    z = await js(page, r"""
      window.viewer.tab('drawings');
      await new Promise(r => setTimeout(r, 500));
      const img = document.getElementById('drawingImg'), pane = document.getElementById('drawingPane');
      const w0 = img.getBoundingClientRect().width, r = pane.getBoundingClientRect();
      pane.dispatchEvent(new WheelEvent('wheel', {deltaY: -400, clientX: r.left + r.width / 2, clientY: r.top + r.height / 2, bubbles: true, cancelable: true}));
      const w1 = img.getBoundingClientRect().width;
      document.getElementById('dFit').click();
      const w2 = img.getBoundingClientRect().width;
      window.viewer.tab('build');
      return [w0, w1, w2];
    """)
    check("drawing: wheel zooms, Fit restores", z[1] > z[0] * 1.5 and abs(z[2] - z[0]) < 2, f"width {z[0]:.0f} -> {z[1]:.0f} -> {z[2]:.0f} px")

    # --- keyboard shortcuts
    await page.mouse.click(5, VIEW["height"] - 5)     # focus the canvas (bottom-left corner: ground)
    await js(page, "T.neutral(); window.viewer.select(null);")
    s0 = await js(page, "return window.viewer.state;")
    for k in ("x", "g", "e", "ArrowLeft", "c", "f"):
        await page.keyboard.press(k)
    s1 = await js(page, "return window.viewer.state;")
    ok = (s1["xray"] != s0["xray"] and s1["gear"]["target"] == 1 and s1["explodeTarget"] == 1
          and s1["step"] == s0["step"] - 1 and s1["cutawayUser"] != s0["cutawayUser"])
    check("keyboard: X, G, E, Left, C, F", ok, f"xray {s1['xray']}, gear target {s1['gear']['target']}, explode {s1['explodeTarget']}, step {s0['step']}->{s1['step']}")
    for k in ("x", "c", "e", "Escape"):
        await page.keyboard.press(k)
    await js(page, "T.neutral(); window.viewer.setStep('paint', {instant: true}); window.viewer.setFlaps(0, {instant: true});")


# ----------------------------------------------------------------------------- review round-1 regressions
async def material_checks(page):
    """Viewer materials vs the stage-4 model: every GLB material gets a viewer material (the lookdev table in
    web/viewer/materials.json, a copy of render/lookdev_materials.json, or its GLB values), a GLB clear coat
    (KHR_materials_clearcoat, written by cad/glb.py) is applied once -- three.js clearcoat = the table's, not layered on
    the loader's -- and the interior lining parts take the cabin light."""
    import struct
    raw = (ROOT / "out" / "pc12.glb").read_bytes()
    gltf = json.loads(raw[20:20 + struct.unpack("<I", raw[12:16])[0]])
    glb_mats = {m["name"]: m for m in gltf["materials"]}
    table = json.loads((ROOT / "web" / "viewer" / "materials.json").read_text())
    lookdev = json.loads((ROOT / "render" / "lookdev_materials.json").read_text())
    check("materials: web/viewer/materials.json is render/lookdev_materials.json", table == lookdev,
          f"{len(table['materials'])} vs {len(lookdev['materials'])} entries")
    T = table["materials"]
    r = await js(page, r"""
      // the GLB's meshes (not the viewer's own, e.g. the prop blur disc) with their base (unhighlighted) material
      const I = window.viewer._internals, out = {};
      for (const mr of I.model.meshRecs) {
        const m = mr.base, f = m.userData.pc12 || {};
        const e = out[m.name] || (out[m.name] = {cc: [], ccr: [], physical: [], interior: [], parts: [], em: [], sheen: [], tex: [], stripes: []});
        const add = (k, v) => { if (!e[k].includes(v)) e[k].push(v); };
        add('cc', +(m.clearcoat || 0).toFixed(4)); add('ccr', +(m.clearcoatRoughness || 0).toFixed(4));
        add('physical', !!m.isMeshPhysicalMaterial); add('interior', !!f.interior); add('parts', mr.part.id);
        add('em', m.emissive ? m.emissive.toArray().map((v) => +v.toFixed(3)).join(',') : '');
        add('sheen', +(m.sheen || 0).toFixed(3));
        add('tex', m.emissiveMap && m.emissiveMap.image ? `${m.emissiveMap.image.width}x${m.emissiveMap.image.height}` : '');
        add('stripes', !!f.stripes);
      }
      const grp = {};
      for (const mr of I.model.meshRecs) {
        if (mr.part.ex.group !== 'Interior') continue;
        const g = grp[mr.part.id] || (grp[mr.part.id] = [true, 0]);
        g[0] = g[0] && !!(mr.base.userData.pc12 || {}).interior; g[1] += 1;
      }
      return {mats: out, info: window.viewer.perf().materials, grp};
    """)
    mats, info = r["mats"], r["info"]
    used = set(mats)
    covered = set(info["upgraded"]) | set(info["kept"])
    ext_kept = sorted(n for n in info["kept"] if glb_mats.get(n, {}).get("extensions"))
    stage4 = ["seal", "seal_cabin", "glass_cabin", "paint_champagne", "exhaust_soot", "gear_bay"]
    check("materials: every GLB material has a viewer material; the stage-4 names and every KHR-extended one from the table",
          used <= covered and not ext_kept and all(n in info["upgraded"] for n in stage4) and used <= set(glb_mats),
          f"{len(info['upgraded'])} from the table, kept (GLB values): {', '.join(info['kept'])}"
          + (f"; uncovered {sorted(used - covered)}" if used - covered else "") + (f"; KHR-extended but kept {ext_kept}" if ext_kept else ""))
    bad = []
    for n, e in mats.items():
        g = glb_mats.get(n, {}).get("extensions", {}).get("KHR_materials_clearcoat", {})
        if n in T:
            want = T[n].get("clearcoatFactor") or 0.0
            want_r = max(0.1, T[n].get("clearcoatRoughnessFactor") or 0.0) if want else 0.0
            if abs((g.get("clearcoatFactor") or 0.0) - want) > 1e-6:
                bad.append(f"{n}: GLB clearcoat {g.get('clearcoatFactor')} vs table {want}")
        else:
            want = g.get("clearcoatFactor") or 0.0
            want_r = max(0.1, g.get("clearcoatRoughnessFactor") or 0.0) if want else 0.0
        if any(abs(c - want) > 1e-3 for c in e["cc"]) or any(abs(c - want_r) > 1e-3 for c in e["ccr"]) \
                or (want and not all(e["physical"])):
            bad.append(f"{n}: clearcoat {e['cc']} / rough {e['ccr']} (want {want} / {want_r:g})")
    ncc = sum(1 for n in mats if (T.get(n, {}).get("clearcoatFactor") or 0) > 0)
    check("materials: KHR_materials_clearcoat applied once (three.js clearcoat = table / GLB, roughness floored at 0.1)",
          not bad, "; ".join(bad[:4]) or f"{ncc} clear-coated materials, e.g. paint_blue {mats.get('paint_blue', {}).get('cc')}")
    lin = {n: mats.get(n, {}).get("interior") for n in ("lining", "lining_flightdeck")}
    check("materials: interior_lining (lining / lining_flightdeck) takes the cabin light (interior patch)",
          all(v == [True] for v in lin.values()) and "interior_lining" in (mats.get("lining_flightdeck") or {}).get("parts", []),
          str(lin))
    # Stage-3 interior (merge of wip/interior): every part of the GLB group 'Interior' takes the cabin light, the
    # table's emissiveFactor (G3000 PRIME page content, LED coves, reading lights, annunciators) survives the
    # MeshPhysicalMaterial upgrade, and the sheepskin keeps the GLB's KHR_materials_sheen
    grp = r["grp"]
    unlit = sorted(k for k, (ok, _) in grp.items() if not ok)
    check("materials: every part of the GLB group 'Interior' takes the cabin light (interior patch)",
          len(grp) >= 20 and not unlit, f"{len(grp)} parts" + (f"; not lit as the cabin: {unlit}" if unlit else ""))
    em_bad, n_em = [], 0
    for n, e in mats.items():
        f = T.get(n, {}).get("emissiveFactor")
        if not f or not any(f):
            continue
        n_em += 1
        for v in e["em"]:
            got = [float(t) for t in v.split(",")] if v else [0.0, 0.0, 0.0]
            if max(abs(a - b) for a, b in zip(got, f)) > 2e-3:
                em_bad.append(f"{n}: {v} vs {f}")
    sh = mats.get("sheepskin", {}).get("sheen", [])
    check("materials: emissive displays / cabin lights keep the table's emissiveFactor; the sheepskin keeps its sheen",
          n_em >= 8 and not em_bad and sh and min(sh) > 0,
          f"{n_em} emissive materials, sheepskin sheen {sh}" + (f"; {'; '.join(em_bad[:4])}" if em_bad else ""))
    # final judge r1 R2 / I1: the G3000 PRIME pages are the GLB's embedded atlas (model/g3000_pages.py) on the display
    # glass 'display_page' (TEXCOORD_0) -- the MeshPhysicalMaterial upgrade keeps it as the emissive map; the cabin
    # carpet carries the table's render_stripes pinstripe patch
    imgs = gltf.get("images") or []
    dp = mats.get("display_page", {})
    glb_dp = glb_mats.get("display_page", {})
    check("materials: the G3000 PRIME pages (GLB atlas texture) stay the display glass's emissive map in the viewer",
          len(imgs) == 1 and "emissiveTexture" in glb_dp and dp.get("tex") and all(dp["tex"])
          and "flight_deck" in dp.get("parts", []),
          f"GLB images {[i.get('name') for i in imgs]}, display_page emissive map {dp.get('tex')} on {dp.get('parts')}")
    cs = mats.get("carpet", {}).get("stripes", [])
    check("materials: the cabin carpet carries the render_stripes pinstripes", cs == [True], f"carpet stripes {cs}")


async def fit_check(page, label, refit_panel=False):
    """[UX-1/BV-4] the fitted preset on load uses the free viewport and hugs the silhouette."""
    f = await js(page, "return T.fit();")
    b = f["box"]
    check(f"[UX-1] {label}: aircraft inside the free viewport on load, fills it",
          f["inside"] and f["fill"] > 0.8 and f["preset"] is not None,
          f"silhouette x {b[0]:.0f}..{b[1]:.0f} y {b[2]:.0f}..{b[3]:.0f} in x {f['free']['x0']:.0f}..{f['free']['x1']:.0f} "
          f"y {f['free']['y0']:.0f}..{f['free']['y1']:.0f}; fill {f['fill']:.2f}; preset {f['preset']}")
    if refit_panel:
        # an untouched preset follows the panel: collapse -> wider free area -> bigger aircraft
        r = await js(page, r"""
          const V = window.viewer, f0 = T.fit();
          V.panel(false); await new Promise(r => setTimeout(r, 500)); V.advance(1.2);
          const f1 = T.fit();
          V.panel(true); await new Promise(r => setTimeout(r, 500)); V.advance(1.2);
          return {f0, f1, f2: T.fit()};
        """)
        w0 = r["f0"]["box"][1] - r["f0"]["box"][0]
        w1 = r["f1"]["box"][1] - r["f1"]["box"][0]
        check(f"[UX-1] {label}: untouched preset re-fits when the panel is toggled",
              r["f1"]["inside"] and w1 > w0 * 1.15 and r["f2"]["inside"] and r["f2"]["fill"] > 0.8,
              f"width {w0:.0f} -> {w1:.0f} px (panel closed) -> {r['f2']['box'][1] - r['f2']['box'][0]:.0f} px")


async def regression_checks(page):
    print("review round-1 regression checks")
    V = "const V = window.viewer; "
    # [F5/UX-3] gear scrubbed to mid-travel: doors stay open and the readout says so
    r = await js(page, V + r"""
      T.neutral(); V.tab('animate');
      V.setGear(0.5, {instant: true}); V.advance(3); await V.frames(2);
      const mid = document.getElementById('rGear').textContent;
      V.setGear(1, {instant: true}); V.setGear('down'); V.advance(0.3); await V.frames(2);    // locked up -> doors open first
      const opening = document.getElementById('rGear').textContent;
      V.advance(8); await V.frames(2);
      const down = document.getElementById('rGear').textContent;                            // down: doors stay open
      V.setGear('up'); V.advance(0.3); await V.frames(2);                                    // doors already open:
      const retracting = document.getElementById('rGear').textContent;                      // straight to retracting
      V.advance(8); await V.frames(2);
      const up = document.getElementById('rGear').textContent;
      T.neutral(); await V.frames(2);
      return {mid, opening, up, down, retracting, neutral: document.getElementById('rGear').textContent};
    """)
    check("[F5/UX-3] gear readout: scrubbed mid-travel = stopped, doors open", r["mid"].startswith("stopped") and "doors open" in r["mid"]
          and r["opening"].startswith("doors opening") and r["down"].startswith("DOWN")
          and r["retracting"].startswith("retracting") and r["up"].startswith("UP") and r["neutral"].startswith("DOWN"),
          f"'{r['mid']}' / '{r['opening']}' / '{r['down']}' / '{r['retracting']}' / '{r['up']}' / '{r['neutral']}'")
    # [UX-4] readouts are refreshed once motion stops (and after deterministic advance())
    r = await js(page, V + r"""
      T.neutral(); V.setFlaps(40, {instant: true}); V.setFlaps(15); V.advance(5); await V.frames(3);
      const flaps = document.getElementById('rFlaps').textContent;
      V.setControls({roll: 1}); V.advance(3); await V.frames(3);
      const ail = document.querySelector('#surfTable tr td:last-child').textContent;
      T.neutral(); await V.frames(2);
      return {flaps, ail, c: V.state.flaps};
    """)
    check("[UX-4] animate readouts are never left stale", r["flaps"] == "15.0°" and r["ail"] == "−20.0°",
          f"flaps readout '{r['flaps']}', aileron R '{r['ail']}'")
    # [UX-5] shortcuts after clicking a slider / a toolbar button
    await js(page, V + "T.neutral(); V.setXray(false); V.setCutaway(false); V.setConstruction(false); V.play(false); V.tab('build');")
    await page.click("#explode", timeout=SHOT_TIMEOUT)      # (the actionability wait: two rAFs, slow on a loaded machine)
    await page.keyboard.press("x")
    s1 = await js(page, "return window.viewer.state;")
    await page.keyboard.press("x")
    await page.click("#tLines", timeout=SHOT_TIMEOUT)
    await page.keyboard.press(" ")
    s2 = await js(page, "return window.viewer.state;")
    check("[UX-5] shortcuts work after clicking a slider; Space plays after clicking a button",
          s1["xray"] and s2["playing"] and s2["construction"],
          f"X after slider: xray {s1['xray']}; Space after 'Lines' click: playing {s2['playing']}, lines {s2['construction']}")
    await js(page, V + "V.play(false); V.setConstruction(false); V.setExplode(0, {instant: true}); V.setStep('paint', {instant: true}); document.activeElement && document.activeElement.blur();")
    # [UX-2] Escape in the parts search clears the filter too; group counts follow the filter
    await js(page, "window.viewer.tab('parts');")
    n_li = await js(page, "return document.querySelectorAll('#partTree li').length;")
    await page.fill("#partSearch", "flettner")
    f1 = await js(page, "return [document.getElementById('pCount').textContent, [...document.querySelectorAll('#partTree details:not([hidden]) .cnt')].map(e => e.textContent)];")
    await page.focus("#partSearch")
    await page.keyboard.press("Escape")
    f2 = await js(page, "return [document.getElementById('pCount').textContent, [...document.querySelectorAll('#partTree li')].filter(l => !l.hidden).length, document.getElementById('partSearch').value];")
    n_all, n_fc = await js(page, "const V = window.viewer, ids = V.parts(); return [ids.length, ids.filter(id => V.partExtras(id).group === V.partExtras('ail_tab_R').group).length];")
    check("[UX-2] search: Escape clears the query and the filter; counts show matches / total",
          f1[0] == f"2 of {n_all} parts" and f1[1] == [f"2 / {n_fc}"] and f2[0] == f"{n_all} parts" and f2[1] == n_all
          and f2[2] == "" and n_li == n_all,
          f"filtered {f1}; after Escape {f2}")
    await js(page, "window.viewer.tab('build');")
    # [BV-2] nothing below the ground: explode (ground drops with the parts) and fly-in (clamped)
    r = await js(page, V + r"""
      T.neutral(); V.setStep('paint', {instant: true});
      const out = {rest: [V.state.groundY, T.lowest()]};
      for (const f of [1, 1.5]) { V.setExplode(f, {instant: true}); out['e' + f] = [V.state.groundY, T.lowest()]; }
      V.setExplode(0, {instant: true}); out.back = V.state.groundY;
      const fly = [];
      for (const [prev, key] of [['doors', 'wing'], ['propeller', 'gear'], ['powerplant', 'cowling']]) {
        V.setStep(prev, {instant: true}); V.setStep(key);
        for (const t of [0.4, 0.3, 0.3, 0.3, 0.4]) { V.advance(t); fly.push([key, V.state.groundY, ...T.lowest()]); }
      }
      V.setStep('paint', {instant: true});
      out.fly = fly;
      return out;
    """)
    ok = all(g <= low + 0.02 for g, (low, _) in (r["rest"], r["e1"], r["e1.5"])) and r["rest"][0] == 0 and r["e1.5"][0] < -1.0 and r["back"] == 0
    check("[BV-2] explode: the ground drops so no part is below it (and returns to 0)", ok,
          f"ground/lowest: rest {r['rest'][0]:.3f}/{r['rest'][1][0]:.3f}, 1.0 {r['e1'][0]:.3f}/{r['e1'][1][0]:.3f}, "
          f"1.5 {r['e1.5'][0]:.3f}/{r['e1.5'][1][0]:.3f} ({r['e1.5'][1][1]})")
    worst = min(r["fly"], key=lambda x: x[2])
    check("[BV-2] build fly-in: parts never start below the ground", all(x[1] == 0 and x[2] >= -0.02 for x in r["fly"]),
          f"lowest during wing / gear / cowling fly-ins {worst[2]:+.3f} m ({worst[3]}, step {worst[0]})")
    # [BV-8] parts without an explode vector grow in place instead of dropping through built skins
    r = await js(page, V + r"""
      T.neutral(); const out = {};
      // times: every listed part has started growing but not finished (0.55 s + 0.14 s stagger, 1.2 s each)
      for (const [prev, key, ids, t] of [['propeller', 'gear', ['gear_bays', 'brace_main_R_up', 'brace_nose_up'], 1.9],
                                         ['fuselage_aft', 'glazing', ['glazing_cabin'], 1.0], ['gear', 'interior', ['flight_deck', 'cabin_interior'], 1.0]]) {
        V.setStep(key, {instant: true}); const c0 = Object.fromEntries(ids.map(id => [id, V.partWorldBox(id).center]));
        V.setStep(prev, {instant: true}); V.setStep(key); V.advance(t);
        for (const id of ids) { const I = window.viewer._internals, n = I.model.part(id).node;
          out[id] = {vis: V.visibleParts().includes(id), d: Math.hypot(...T.sub(V.partWorldBox(id).center, c0[id])), s: n.scale.x}; }
        V.advance(4); for (const id of ids) out[id].sEnd = window.viewer._internals.model.part(id).node.scale.x;
      }
      V.setStep('paint', {instant: true});
      return out;
    """)
    bad = {k: v for k, v in r.items() if not (v["vis"] and v["d"] < 0.02 and 0 < v["s"] < 0.999 and v["sEnd"] == 1)}
    check("[BV-8] zero-explode parts grow in place (no drop through built skins)", not bad,
          "; ".join(f"{k}: centre moved {v['d']*1000:.1f} mm, scale {v['s']:.2f}->{v['sEnd']:.0f}" for k, v in list(r.items())[:3]) + (f"; BAD {bad}" if bad else ""))
    # [BV-3] the current step row is always inside the panel (long step texts, with and without the info card)
    r = await js(page, V + r"""
      T.neutral(); V.tab('build'); const bad = []; let worst = -1e9;
      const panelBottom = document.getElementById('panel').getBoundingClientRect().bottom;
      for (const sel of [null, 'eng_combustor']) {
        if (sel) V.select(sel, {instant: true, frame: false}); else V.select(null);
        V.tab('build');
        const nSteps = document.querySelectorAll('#stepList li').length;
        for (let i = 0; i < nSteps; i++) {
          V.setStep(i, {instant: true});
          const li = document.querySelector('#stepList li.current').getBoundingClientRect(), ol = document.getElementById('stepList').getBoundingClientRect();
          worst = Math.max(worst, li.bottom - Math.min(panelBottom, ol.bottom));
          if (li.bottom > Math.min(panelBottom, ol.bottom) + 1 || li.top < ol.top - 1) bad.push([sel, i, Math.round(li.top), Math.round(li.bottom)]);
        }
      }
      V.select(null); V.setStep('paint', {instant: true});
      return {bad, worst};
    """)
    check("[BV-3] current build step row always visible in the panel (all 19 steps, card on/off)", not r["bad"],
          f"worst overhang {r['worst']:+.0f} px" + (f"; bad {r['bad'][:4]}" if r["bad"] else ""))
    # [BV-5] cockpit: the windshield is see-through from inside
    await js(page, V + "T.neutral(); V.setStep('paint', {instant: true}); V.panel(false); await new Promise(r => setTimeout(r, 400)); V.setCamera('cockpit', {instant: true}); await V.frames(3);")
    shot_path = OUT / "32_cockpit_windshield.png"
    await page.screenshot(path=str(shot_path), timeout=SHOT_TIMEOUT)
    try:
        from PIL import Image
        import numpy as np
        im = Image.open(shot_path).convert("L")
        # band above the glareshield, through the windshield (clear of the toolbar)
        med = float(np.median(np.asarray(im.crop((40, 120, VIEW["width"] - 40, 200)))))
        check("[BV-5] cockpit preset: bright outside through the windshield", med > 150, f"median luminance {med:.0f} (sky/background ~230, was ~40)")
    except ImportError:
        check("[BV-5] cockpit preset: bright outside through the windshield", True, "PIL not installed: skipped")
    await js(page, "window.viewer.panel(true); await new Promise(r => setTimeout(r, 400)); window.viewer.setCamera('three_quarter', {instant: true});")
    # [BV-6] the prop blur disc grows with the exploded blades
    r = await js(page, V + r"""
      T.neutral(); const I = V._internals, out = {};
      for (const f of [0, 1, 1.5]) {
        V.setExplode(f, {instant: true}); V.setProp({rpm: 1700, pitch: 0, angle: 0}, {instant: true}); V.advance(0.02);
        const hub = V.nodeWorldPoint('propeller', [0, 0, 0]); let tip = 0;
        // blade tip radius about the spin axis (vertices, current pose)
        const ax = new I.THREE.Vector3().fromArray(V.partExtras('propeller').pivot.axis).normalize(), h = new I.THREE.Vector3().fromArray(hub), v = new I.THREE.Vector3();
        I.model.root.updateMatrixWorld(true);
        for (let k = 1; k <= 5; k++) for (const mr of I.model.part('blade_' + k).meshes) {
          const g = mr.mesh.geometry.attributes.position;
          for (let i = 0; i < g.count; i += 5) { v.fromBufferAttribute(g, i).applyMatrix4(mr.mesh.matrixWorld).sub(h); tip = Math.max(tip, v.addScaledVector(ax, -v.dot(ax)).length()); }
        }
        out[f] = {disc: I.kin.blur.outerR * I.kin.blur.disc.scale.x, visible: I.kin.blur.disc.visible, push: V.state.propDiscPush, tip};
      }
      T.neutral();
      return out;
    """)
    ok = all(v["visible"] for v in r.values()) and abs(r["1"]["disc"] - r["0"]["disc"] - 0.45) < 0.01 and abs(r["1.5"]["disc"] - r["0"]["disc"] - 0.675) < 0.01
    ok = ok and all(0 < v["disc"] - v["tip"] < 0.05 for v in r.values())
    check("[BV-6] prop blur disc grows with the exploded blades (radial push 0.45 m x f)", ok,
          f"disc radius {r['0']['disc']:.3f} / {r['1']['disc']:.3f} / {r['1.5']['disc']:.3f} m at explode 0 / 1 / 1.5 "
          f"(blade tips {r['0']['tip']:.3f} / {r['1']['tip']:.3f} / {r['1.5']['tip']:.3f} m)")
    # [BV-9] structure pushed behind the coincident skins
    r = await js(page, "const m = window.viewer._internals.model; return m.part('structure').meshes.map(mr => [mr.base.polygonOffset, mr.base.polygonOffsetFactor, mr.base.polygonOffsetUnits]);")
    check("[BV-9] structure materials carry a polygon offset (no z-fighting with the skins)", all(x[0] and x[1] > 0 and x[2] > 0 for x in r), str(r[0]))


async def prop_blur_checks(page):
    """Propeller in motion (owner 2026-10-03: "the propeller spinning doesn't look too real"; web/viewer/propblur.js):
    the solid blades cross-fade into the motion-blurred disc before they could alias (wagon wheel), the disc lies in
    the plane of rotation on the thrust axis, the averaged disc is mostly see-through with the blade colours as rings,
    nothing strobes at any rpm or frame rate, realistic spool-up / run-down times."""
    print("propeller blur checks")
    V = "const V = window.viewer, I = V._internals, kin = I.kin, B = kin.blur; "
    r = await js(page, V + r"""
      T.neutral(); V.setStep('paint', {instant: true});
      if (!B) return {has: false};
      const P = B.period, out = {has: true, P, rows: {}};
      const look = () => ({...B.state, bladeVis: B.fadeMats.every((m) => m.visible), bladeOpaque: B.fadeMats.every((m) => !m.transparent && m.opacity === 1),
        disc: B.disc.visible, band: !!B.band && B.band.visible});
      // rpm sweep at 60 and 30 frames a second (the smoothed frame time follows the animation steps)
      for (const fps of [60, 30]) {
        const rows = [];
        for (const rpm of [0, 5, 10, 20, 30, 45, 60, 80, 100, 150, 200, 300, 500, 1000, 1550, 1700]) {
          V.setProp({rpm, pitch: 0, angle: 0}, {instant: true});
          V.advance(0.6, 1 / fps);
          rows.push({rpm, step: rpm * 6 / fps, ...look()});
        }
        out.rows[fps] = rows;
      }
      // the ghost (and the true pattern) only ever advance forward, by at most 0.4 P a frame
      V.setProp({rpm: 1700, pitch: 0, angle: 0}, {instant: true}); V.advance(0.5, 1 / 30);
      let gmin = Infinity, gmax = -Infinity, prev = B.ghostPhase;
      for (let i = 0; i < 40; i++) {
        V.advance(1 / 30, 1 / 30);
        const d = ((B.ghostPhase - prev) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI);
        prev = B.ghostPhase; gmin = Math.min(gmin, d); gmax = Math.max(gmax, d);
      }
      out.ghost = {min: gmin, max: gmax};
      // the disc on the thrust axis: every disc vertex in the plane through the hub normal to the spin axis (at two
      // spin angles), its outer edge just outside the blade tips
      const pv = V.partExtras('propeller').pivot, ax = new I.THREE.Vector3().fromArray(pv.axis).normalize();
      const hub = new I.THREE.Vector3().fromArray(V.nodeWorldPoint('propeller', [0, 0, 0]));
      const plane = [], radii = [];
      for (const ang of [0, 1.1]) {
        V.setProp({rpm: 1700, pitch: 0, angle: ang}, {instant: true}); V.advance(0, 1 / 60);
        I.model.root.updateMatrixWorld(true);
        const g = B.disc.geometry.attributes.position, v = new I.THREE.Vector3();
        let pmax = 0, rmax = 0;
        for (let i = 0; i < g.count; i++) {
          v.fromBufferAttribute(g, i).applyMatrix4(B.disc.matrixWorld).sub(hub);
          pmax = Math.max(pmax, Math.abs(v.dot(ax)));
          rmax = Math.max(rmax, v.addScaledVector(ax, -v.dot(ax)).length());
        }
        plane.push(pmax); radii.push(rmax);
      }
      let tip = 0;
      for (const b of B.blades) {
        for (const mr of b.meshes) {
          const g = mr.mesh.geometry.attributes.position, v = new I.THREE.Vector3();
          for (let i = 0; i < g.count; i += 7) { v.fromBufferAttribute(g, i).applyMatrix4(mr.mesh.matrixWorld).sub(hub); tip = Math.max(tip, v.addScaledVector(ax, -v.dot(ax)).length()); }
        }
      }
      // the thrust line, 2 deg nose-down and 2 deg right of the station axis (powerplant.thrust_dir), in glTF axes
      out.axis = {plane, radii, tip, thrustDeg: [Math.asin(-ax.y) * 180 / Math.PI, Math.asin(ax.x) * 180 / Math.PI],
        hubErr: hub.distanceTo(new I.THREE.Vector3().fromArray(pv.origin))};
      // modes: X-ray, cutaway and explode keep the disc (whole: no clipping), isolating a blade keeps solid geometry
      const modes = {};
      V.setProp({rpm: 1700, pitch: 0}, {instant: true}); V.advance(0.3);
      V.setXray(true); V.advance(0.05); modes.xray = B.disc.visible && B.band.visible;
      V.setXray(false); V.setCutaway(true); V.advance(0.05); modes.cut = B.disc.visible && !(B.disc.material.clippingPlanes || []).length;
      V.setCutaway(false); V.setExplode(1, {instant: true}); V.advance(0.05); modes.explode = B.disc.visible && Math.abs(B.disc.scale.x - (B.outerR + B.push) / B.outerR) < 1e-9 && B.push > 0.4;
      V.setExplode(0, {instant: true}); V.isolate('blade_3'); V.advance(0.05); modes.isolated = !B.disc.visible && B.fadeMats.every((m) => m.visible && m.opacity === 1);
      V.isolate(null); V.advance(0.05); modes.back = B.disc.visible;
      // pitch when stopped: the solid blades show feather
      V.setProp({rpm: 0, pitch: 62}, {instant: true}); V.advance(0.05);
      modes.feather = !B.disc.visible && B.fadeMats.every((m) => m.visible && !m.transparent) && Math.abs(kin.surf.blade_1.angle - 62) < 1e-6;
      out.modes = modes;
      // spool: start to ground idle, governed 1,000 -> 1,700, shutdown run-down (1/60 s steps, rpm sampled every 0.1 s)
      const spool = (from, to, until, tmax) => {
        V.setProp({rpm: from, pitch: 0}, {instant: true}); V.setProp({rpm: to});
        let t = 0, mono = true, last = from;
        while (t < tmax && !until(V.state.prop.rpm)) {
          V.advance(0.1); t += 0.1;
          const x = V.state.prop.rpm;
          if ((to > from && x < last - 1e-9) || (to < from && x > last + 1e-9)) mono = false;
          last = x;
        }
        return {t, mono, rpm: V.state.prop.rpm};
      };
      out.spool = {start: spool(0, 1000, (x) => x >= 990, 40), gov: spool(1000, 1700, (x) => x >= 1690, 20),
        down: spool(1700, 1000, (x) => x <= 1010, 20), stop: spool(1700, 0, (x) => x <= 30, 60)};
      T.neutral();
      return out;
    """)
    if not r.get("has"):
        check("prop blur: disc built from the blade geometry", False, "no kin.blur")
        return
    P = math.degrees(r["P"])
    for fps, rows in r["rows"].items():
        strobe = [x for x in rows if x["fade"] < 0.999 and x["step"] > P / 8]
        check(f"prop blur {fps} fps: solid blades only while they turn < {P / 8:.0f} deg a frame (no strobing)", not strobe,
              ", ".join(f"{x['rpm']} rpm fade {x['fade']:.2f}" for x in strobe) or
              "fade: " + " ".join(f"{x['rpm']}:{x['fade']:.2f}" for x in rows if 0 < x["fade"] < 1 or x["rpm"] in (0, 100)))
        short = [x for x in rows if x["disc"] and x["sweepDeg"] < min(P, 2.5 * x["step"]) - 1e-6]
        check(f"prop blur {fps} fps: the smear spans >= 2.5 frame steps (or one blade spacing)", not short,
              ", ".join(f"{x['rpm']} rpm sweep {x['sweepDeg']:.1f}" for x in short) or
              "sweep: " + " ".join(f"{x['rpm']}:{x['sweepDeg']:.0f}" for x in rows if x["rpm"] in (30, 60, 100, 150, 200, 300)))
        lo = rows[0]
        check(f"prop blur {fps} fps: stopped = solid opaque blades, no disc", lo["fade"] == 0 and not lo["disc"] and lo["bladeVis"] and lo["bladeOpaque"],
              str({k: lo[k] for k in ("fade", "disc", "bladeVis", "bladeOpaque")}))
        hi = {x["rpm"]: x for x in rows}
        ok = all(hi[k]["fade"] == 1 and hi[k]["disc"] and hi[k]["band"] and not hi[k]["bladeVis"] and abs(hi[k]["sweepDeg"] - P) < 1e-6
                 and hi[k]["ghost"] > 0.1 for k in (1000, 1550, 1700))
        check(f"prop blur {fps} fps: idle..1,700 rpm = blurred disc + spinner band, blades faded out, ghost on", ok,
              f"1,700: fade {hi[1700]['fade']:.2f}, sweep {hi[1700]['sweepDeg']:.1f} deg (P {P:.0f}), ghost {hi[1700]['ghost']:.2f}, blades drawn {hi[1700]['bladeVis']}")
    g = r["ghost"]
    check("prop blur: the ghost only moves forward, <= 0.4 blade spacing a frame (no backwards wagon wheel)",
          g["min"] > 0 and g["max"] <= 0.4 * r["P"] + 1e-6, f"{math.degrees(g['min']):.1f} .. {math.degrees(g['max']):.1f} deg a frame at 1,700 rpm / 30 fps")
    a = r["axis"]
    check("prop blur: disc in the plane of rotation through the hub (thrust line)", max(a["plane"]) < 1e-3 and a["hubErr"] < 1e-3
          and abs(a["thrustDeg"][0] - 2) < 0.05 and abs(a["thrustDeg"][1] - 2) < 0.05,
          f"off-plane {max(a['plane']) * 1000:.3f} mm; axis {a['thrustDeg'][0]:.2f} deg down, {a['thrustDeg'][1]:.2f} deg right")
    check("prop blur: disc edge just outside the blade tips", 0 < min(a["radii"]) - a["tip"] < 0.03,
          f"disc R {min(a['radii']):.3f} m, tips {a['tip']:.3f} m")
    m = r["modes"]
    check("prop blur: kept in X-ray, cutaway (unclipped) and explode; solid blades when one is isolated; feather stopped",
          all(m.values()), str(m))
    sp = r["spool"]
    check("spool: start to ground idle in 8-16 s, monotonic", 8 <= sp["start"]["t"] <= 16 and sp["start"]["mono"], f"{sp['start']['t']:.1f} s")
    check("spool: governed 1,000 -> 1,700 / 1,700 -> 1,000 in 1.5-5 s", 1.5 <= sp["gov"]["t"] <= 5 and 1.5 <= sp["down"]["t"] <= 5
          and sp["gov"]["mono"] and sp["down"]["mono"], f"up {sp['gov']['t']:.1f} s, down {sp['down']['t']:.1f} s")
    check("spool: shutdown run-down 1,700 -> 0 in 12-30 s", 12 <= sp["stop"]["t"] <= 30 and sp["stop"]["mono"], f"{sp['stop']['t']:.1f} s to < 30 rpm")

    # a steadily spinning, blurred prop leaves the key-light shadow map alone (the blades are hidden, the spinner round)
    r = await js(page, V + r"""
      T.neutral(); V.setProp({rpm: 1700, pitch: 0}, {instant: true}); V.advance(0.3); await V.frames(3);
      const p0 = V.perf().renders; await V.frames(8); const p1 = V.perf().renders;
      const out = {shadow: p1.shadowRenders - p0.shadowRenders, renders: p1.renders - p0.renders, moving: V.state.prop.angle};
      T.neutral(); return out;
    """)
    check("prop blur: no shadow-map passes while the blurred prop spins", r["shadow"] == 0 and r["renders"] >= 8,
          f"{r['shadow']} shadow renders in {r['renders']} frames")

    # review r1 PR1-01..04: the faded blades are hidden as meshes (never picked, no highlight overlay drawn on them),
    # the disc is picked as the propeller and tinted while it is selected; the chrome spinner is held still once the
    # blur is complete; Off feathers the propeller, a start from feather unfeathers once it turns 300 rpm
    r = await js(page, V + r"""
      T.neutral(); V.panel(false); V.setCamera({pos: [-1.5, 2.25, -0.5], target: [0, 1.7, 1.1], fov: 32}, {instant: true});
      V.setProp({rpm: 1700, pitch: 0}, {instant: true}); V.advance(0.5);
      const M = I.model, THREE = I.THREE, cam = I.stage.camera, cv = I.stage.renderer.domElement.getBoundingClientRect();
      const prop = M.parts.get('propeller').node, picks = {}, core = {};
      for (let k = 0; k < 30; k++) {
        V.advance(1 / 60); prop.updateMatrixWorld(true); cam.updateMatrixWorld();
        for (const [r, a] of [[0.3, 0.3], [0.6, 0.3], [0.9, 2.0], [1.1, 4.1]]) {
          const f = B.frame, p = new THREE.Vector3().addScaledVector(f.e1, r * Math.cos(a)).addScaledVector(f.e2, r * Math.sin(a))
            .applyMatrix4(prop.matrixWorld).project(cam);
          const id = V.pick(cv.left + (p.x + 1) / 2 * cv.width, cv.top + (1 - p.y) / 2 * cv.height);
          picks[id] = (picks[id] || 0) + 1;
          if (r < 0.4) core[id] = (core[id] || 0) + 1;
        }
      }
      const hidden = B.fadeRecs.length > 0 && B.fadeRecs.every((mr) => !mr.mesh.visible);
      V.select('blade_2', {frame: false}); V.advance(1 / 60);
      const ovl = M.overlays.sel.filter((o) => o.userData.mr.blurFade);
      const drawn = ovl.filter((o) => o.visible && o.parent && o.parent.visible).length;
      const tint = B.discU.uPbTint.value.w;
      V.select(null); V.advance(1 / 60);
      const tint0 = B.discU.uPbTint.value.w;
      // the chrome's world matrix (rotation, the quantisation scale and offset) unchanged frame to frame: the largest
      // displacement of its bounding-box corners (m)
      const chrome = B.still.length ? B.still[0].mesh : null, mw = [];
      if (chrome && !chrome.geometry.boundingBox) chrome.geometry.computeBoundingBox();
      for (let k = 0; k < 4 && chrome; k++) { V.advance(1 / 60); I.model.root.updateMatrixWorld(true); mw.push(chrome.matrixWorld.clone()); }
      let still = chrome ? 0 : 9;
      if (chrome) {
        const bb = chrome.geometry.boundingBox;
        for (let i = 0; i < 8; i++) {
          const c = new THREE.Vector3(i & 1 ? bb.max.x : bb.min.x, i & 2 ? bb.max.y : bb.min.y, i & 4 ? bb.max.z : bb.min.z);
          const p0 = c.clone().applyMatrix4(mw[0]);
          for (const m of mw.slice(1)) still = Math.max(still, c.clone().applyMatrix4(m).distanceTo(p0));
        }
      }
      document.querySelector('[data-rpm="0"]').click();
      const off = {rpm: kin.t.rpm, pitch: kin.t.pitch};
      V.setProp({rpm: 0, pitch: 62}, {instant: true}); V.advance(0.05);
      document.querySelector('[data-rpm="1000"]').click();
      let at = null;
      for (let t = 0; t < 15 && at == null; t += 0.05) { V.advance(0.05); if (kin.t.pitch === 0) at = V.state.prop.rpm; }
      V.setProp({rpm: 0, pitch: 0}, {instant: true}); V.advance(0.05);
      const back = chrome ? B.still[0].mesh.quaternion.equals(B.still[0].q0) && B.still[0].mesh.position.equals(B.still[0].p0) : false;
      T.neutral(); V.panel(true);
      return {picks, core, hidden, ovl: ovl.length, drawn, tint, tint0, still, off, at, back};
    """)
    check("[PR1-01] blurred prop: the faded blades are hidden meshes, a pick over the disc's root smear is 'propeller' "
          "(never a blade; further out the part behind it, PR3-02), a selected blade draws no overlay, the disc is tinted instead",
          r["hidden"] and list(r["core"]) == ["propeller"] and not any(k and k.startswith("blade_") for k in r["picks"])
          and r["ovl"] > 0 and r["drawn"] == 0 and r["tint"] > 0.2 and r["tint0"] == 0,
          f"picks {r['picks']} (root smear {r['core']}), overlays {r['drawn']}/{r['ovl']} drawn, tint {r['tint']:.2f} -> {r['tint0']:.2f}")
    # review r3 PR3-02: with the prop at 1,700 rpm in the 3/4 view, the cowl, chin inlet, stacks and nose gear seen through
    # the outer disc are picked as themselves (the whole 2.67 m disc had caught every click)
    rp = await js(page, V + r"""
      T.neutral(); V.panel(false); V.setCamera('three_quarter', {instant: true});
      V.setProp({rpm: 1700, pitch: 0}, {instant: true}); V.advance(0.5);
      const M = I.model, THREE = I.THREE, cam = I.stage.camera, cv = I.stage.renderer.domElement.getBoundingClientRect();
      M.root.updateMatrixWorld(true); cam.updateMatrixWorld();
      const rc = new THREE.Raycaster(), ndc = new THREE.Vector2(), v = new THREE.Vector3(), out = {};
      for (const id of ['cowl_upper', 'cowl_lower', 'chin_inlet', 'exhaust_stacks', 'gear_nose_steer']) {
        const res = {};
        let n = 0;
        for (const mr of M.part(id).meshes) {
          const g = mr.mesh.geometry.attributes.position;
          for (let i = 0; i < g.count && n < 40; i += 97) {
            v.fromBufferAttribute(g, i).applyMatrix4(mr.mesh.matrixWorld).project(cam);
            if (Math.abs(v.x) > 1 || Math.abs(v.y) > 1) continue;
            ndc.set(v.x, v.y); rc.setFromCamera(ndc, cam);
            const h = rc.intersectObject(B.disc, false)[0];
            if (!h || B.pickCore(h.point)) continue;
            // only points actually seen through the disc: a silhouette vertex whose ray grazes past every mesh has nothing
            // behind the disc to take the click (the disc is then the fallback, by design)
            if (!rc.intersectObjects(M.pickables, false).some((x) => x.object !== B.disc && x.distance > h.distance)) continue;
            const pid = V.pick(cv.left + (v.x + 1) / 2 * cv.width, cv.top + (1 - v.y) / 2 * cv.height);
            res[pid] = (res[pid] || 0) + 1; n++;
          }
        }
        out[id] = res;
      }
      const sp = new THREE.Vector3().fromArray(V.nodeWorldPoint('propeller', [0, 0, 0])).project(cam);
      out.spinner = V.pick(cv.left + (sp.x + 1) / 2 * cv.width, cv.top + (1 - sp.y) / 2 * cv.height);
      T.neutral(); V.panel(true);
      return out;
    """)
    tried = {k: v for k, v in rp.items() if isinstance(v, dict)}
    # (a point of a part may be hidden behind another part, which then takes the pick; never the disc)
    ok = (rp["spinner"] == "propeller" and sum(1 for v in tried.values() if sum(v.values()) > 0) >= 3
          and not any(v.get("propeller") or any(k and k.startswith("blade_") for k in v) for v in tried.values()))
    check("[PR3-02] spinning prop (3/4 view): the parts seen through the outer disc pick as themselves (or the part in "
          "front of them), never the propeller; the spinner as the propeller", ok,
          f"spinner -> {rp['spinner']}; " + "; ".join(f"{k}: {v}" for k, v in tried.items()))
    check("[PR1-03] blurred prop: the chrome spinner stands still (no twinkling facets), turns again when stopped",
          r["still"] < 1e-5 and r["back"], f"spinner box corners moved <= {r['still'] * 1000:.4f} mm over 3 frames at 1,700 rpm")
    check("[PR1-04] Off feathers the propeller (62 deg); a start from feather unfeathers once it turns ~300 rpm",
          r["off"] == {"rpm": 0, "pitch": 62} and r["at"] is not None and 290 <= r["at"] <= 360,
          f"Off -> {r['off']}, unfeathered at {r['at']} rpm")

    # pixels: the averaged disc on its own (isolated propeller, looking aft along the thrust axis) against the bare backdrop
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        check("prop blur: averaged disc is mostly see-through, rings at the tips", True, "PIL not installed: skipped")
        return
    await prop_band_checks(page)
    setup = V + r"""
      T.neutral(); V.isolate('propeller');
      const pv = V.partExtras('propeller').pivot, ax = pv.axis, o = pv.origin;
      V.setCamera({pos: [o[0] + 4.2 * ax[0], o[1] + 4.2 * ax[1], o[2] + 4.2 * ax[2]], target: o, fov: 45}, {instant: true});
    """
    pts = await js(page, setup + r"""
      const THREE = I.THREE, a = new THREE.Vector3().fromArray(pv.axis).normalize();
      const e1 = new THREE.Vector3(1, 0, 0).addScaledVector(a, -a.x).normalize(), e2 = new THREE.Vector3().crossVectors(a, e1);
      const out = {};
      for (const rr of [0.5, 0.8, 1.1, 1.22, 1.31]) {
        out[rr] = [];
        for (let k = 0; k < 72; k++) {
          const t = 2 * Math.PI * (k + 0.5) / 72, p = new THREE.Vector3().fromArray(o).addScaledVector(e1, rr * Math.cos(t)).addScaledVector(e2, rr * Math.sin(t));
          out[rr].push(V.project(p.toArray()));
        }
      }
      return out;
    """)
    shots = {}
    for key, js_set in (("bare", "V.hide('propeller'); V.advance(0.05);"),
                        ("stopped", "V.showAll(); V.isolate('propeller'); V.setProp({rpm: 0, pitch: 0, angle: 0.2}, {instant: true}); V.advance(0.05);"),
                        ("spin", "V.setProp({rpm: 1700, pitch: 0}, {instant: true}); V.advance(0.5); V.pause(true);"),
                        ("spin0", "B._apG = B.apply; B.apply = (...a) => { B._apG(...a); B.U.uPbGhost.value.x = 0; }; "
                                  "V.pause(false); V.advance(1 / 60); V.pause(true);")):
        await js(page, V + js_set + " await V.frames(2);")
        path = OUT / f"prop_px_{key}.png"
        await page.screenshot(path=str(path), timeout=SHOT_TIMEOUT)
        shots[key] = np.asarray(Image.open(path).convert("RGB"), dtype=float)
    await js(page, "const B = window.viewer._internals.kin.blur; if (B._apG) { B.apply = B._apG; delete B._apG; } "
                   "window.viewer.pause(false); window.viewer.isolate(null); window.viewer.showAll(); T.neutral();")
    lin = lambda x: np.where(x / 255 <= 0.04045, x / 255 / 12.92, ((x / 255 + 0.055) / 1.055) ** 2.4)
    ring = {}
    for rr, pp in pts.items():
        vals = {k: np.array([lin(shots[k][int(round(y)), int(round(x))]).mean() for x, y, _ in pp]) for k in shots}
        ratio = vals["spin"] / np.maximum(vals["bare"], 1e-4)
        ratio0 = vals["spin0"] / np.maximum(vals["bare"], 1e-4)
        ring[float(rr)] = (float(ratio.mean()), float(ratio0.std()), float(vals["stopped"].std() / max(vals["bare"].mean(), 1e-4)),
                           float(ratio.std()))
    mid = [ring[x][0] for x in (0.5, 0.8, 1.1)]
    check("prop blur: averaged disc mostly see-through (60-97 % of the backdrop at 0.5-1.1 m)", all(0.6 <= x <= 0.97 for x in mid),
          " / ".join(f"r {x}: {ring[x][0] * 100:.0f} %" for x in (0.5, 0.8, 1.1, 1.22, 1.31)))
    check("prop blur: the true pattern azimuthally smooth at 1,700 rpm (ghost zeroed; vs the stopped blades)",
          all(ring[x][1] < 0.06 for x in (0.5, 0.8, 1.1)) and all(ring[x][2] > 0.2 for x in (0.5, 0.8, 1.1)),
          " / ".join(f"r {x}: spin sd {ring[x][1] * 100:.1f} %, stopped sd {ring[x][2] * 100:.0f} %" for x in (0.5, 0.8, 1.1)))
    check("[PR3-01] prop blur at 1,700 rpm: the ghost draws a visible fan of smeared blades (azimuthal sd 4-35 % of the "
          "backdrop at 0.5-1.1 m), not a uniform veil", all(0.04 <= ring[x][3] <= 0.35 for x in (0.5, 0.8, 1.1)),
          " / ".join(f"r {x}: sd {ring[x][3] * 100:.1f} %" for x in (0.5, 0.8, 1.1)))
    # PR3-03: edge-on (camera in the plane of rotation) the disc stays translucent (a flat disc's coverage tends to 1 there)
    pts = await js(page, r"""
      const V = window.viewer, I = V._internals, THREE = I.THREE, B = I.kin.blur; T.neutral(); V.isolate('propeller');
      const pv = V.partExtras('propeller').pivot, o = new THREE.Vector3().fromArray(pv.origin), a = new THREE.Vector3().fromArray(pv.axis).normalize();
      const side = new THREE.Vector3(1, 0, 0).addScaledVector(a, -a.x).normalize(), up = new THREE.Vector3().crossVectors(a, side).normalize();
      // ~2 deg off the plane of rotation (as the Side preset): exactly in it the flat disc rasterises to nothing
      V.setCamera({pos: o.clone().addScaledVector(side, -4.5).addScaledVector(a, 0.15).toArray(), target: o.toArray(), fov: 40}, {instant: true});
      return [0.5, 0.7, 0.85].flatMap((rr) => [rr, -rr].map((q) => V.project(o.clone().addScaledVector(up, q).toArray())));
    """)
    edge = {}
    for key, js_set in (("bare", "V.hide('propeller'); V.advance(0.05);"),
                        ("spin", "V.showAll(); V.isolate('propeller'); V.setProp({rpm: 1700, pitch: 0}, {instant: true}); V.advance(0.5); V.pause(true);")):
        await js(page, V + js_set + " await V.frames(2);")
        path = OUT / f"prop_px_edge_{key}.png"
        await page.screenshot(path=str(path), timeout=SHOT_TIMEOUT)
        edge[key] = np.asarray(Image.open(path).convert("RGB"), dtype=float)
    await js(page, "window.viewer.pause(false); window.viewer.isolate(null); window.viewer.showAll(); T.neutral();")
    er = []
    for x, y, _ in pts:
        xi, yi = int(round(x)), int(round(y))
        win = lambda im: im[yi - 1:yi + 2, xi - 1:xi + 2].mean(axis=2).min()      # the darkest pixel round it (sRGB)
        er.append(win(edge["spin"]) / max(win(edge["bare"]), 1e-4))
    check("[PR3-03] prop blur seen edge-on (~2 deg off its plane): translucent (the darkest pixel along the disc 35-95 % "
          "of the backdrop's sRGB value: drawn, not an opaque black crescent)", 0.35 <= min(er) and max(er) <= 0.95,
          " ".join(f"{v * 100:.0f}%" for v in er))
    check("prop blur: white tip band lighter than the black blade inboard of it", ring[1.31][0] > ring[1.1][0],
          f"tip {ring[1.31][0] * 100:.1f} % vs {ring[1.1][0] * 100:.1f} % of the backdrop")


async def prop_band_checks(page):
    """Review r2 PR2-01 / 02: the root-boot band on the spinner is steady frame to frame at 1,700 rpm (no ghost on it),
    opaque and drawn before the disc (the disc inside the spinner never shows through the still spinner's blade
    cut-outs: no standing dark notch); the solid blades cross-fade over a short sweep window."""
    from PIL import Image
    import numpy as np
    V = "const V = window.viewer, I = V._internals, kin = I.kin, B = kin.blur; "
    pts = await js(page, V + r"""
      T.neutral(); V.panel(false); V.setStep('paint', {instant: true});
      V.setCamera({pos: [-0.75, 1.85, -0.45], target: [0, 1.62, 0.95], fov: 35}, {instant: true});
      V.setProp({rpm: 1700, pitch: 0}, {instant: true}); V.advance(1.5); V.pause(true); await V.frames(2);
      const THREE = I.THREE, f = B.frame, fit = B.bandFit, node = B.prop.node, cam = I.stage.camera;
      node.updateMatrixWorld(true); cam.updateMatrixWorld();
      const eye = cam.position.clone(), out = [];
      // band points on the camera's side of the disc plane only (behind it the disc's blur legitimately covers them)
      const camAx = node.worldToLocal(eye.clone()).dot(f.a);
      for (let i = 0; i < 17; i++) {
        const z = fit.z0 + 0.008 + (fit.z1 - fit.z0 - 0.016) * i / 16, u = (z - fit.zm) / fit.hz;
        if (z * Math.sign(camAx) < 0.01) continue;
        const r = fit.cf[0] + fit.cf[1] * u + fit.cf[2] * u * u + 0.0015;
        for (let k = 0; k < 360; k++) {
          const t = 2 * Math.PI * k / 360, er = f.e1.clone().multiplyScalar(Math.cos(t)).addScaledVector(f.e2, Math.sin(t));
          const p = er.clone().multiplyScalar(r).addScaledVector(f.a, z).applyMatrix4(node.matrixWorld);
          const n = er.clone().transformDirection(node.matrixWorld);
          if (n.dot(eye.clone().sub(p).normalize()) < 0.35) continue;
          out.push(V.project(p.toArray()));
        }
      }
      return {pts: out, order: [B.band.renderOrder, B.disc.renderOrder], depthWrite: B.band.material.depthWrite};
    """)
    shots = {}
    for key, js_set in (("f0", "V.pause(false); V.advance(1 / 60); V.pause(true);"),
                        ("f1", "V.pause(false); V.advance(1 / 60); V.pause(true);"),
                        ("f2", "V.pause(false); V.advance(1 / 60); V.pause(true);"),
                        ("ghost0", "B._apR = B.apply; B.apply = (...a) => { B._apR(...a); B.U.uPbGhost.value.x = 0; }; "
                                   "V.pause(false); V.advance(1 / 60); V.pause(true);"),
                        ("ghost0_nodisc", "B.disc.visible = false; B.disc.layers.disable(0);"),
                        ("ref", "B.disc.layers.enable(0); B.apply = B._apR; delete B._apR;")):
        await js(page, V + js_set + " I.stage.needsRender = true; await V.frames(2);")
        path = OUT / f"prop_band_{key}.png"
        await page.screenshot(path=str(path), timeout=SHOT_TIMEOUT)
        shots[key] = np.asarray(Image.open(path).convert("L"), dtype=float)
    await js(page, "window.viewer.pause(false); T.neutral(); window.viewer.panel(true);")
    H, W = shots["f0"].shape
    xy = [(int(round(x)), int(round(y))) for x, y, _ in pts["pts"] if 0 <= x < W and 0 <= y < H]
    val = {k: np.array([v[y, x] for x, y in xy]) for k, v in shots.items()}
    flick = max(np.percentile(np.abs(val["f1"] - val["f0"]), 95), np.percentile(np.abs(val["f2"] - val["f1"]), 95))
    ghost = np.percentile(np.abs(val["ghost0"] - val["f2"]), 95)
    notch = np.percentile(np.abs(val["ghost0_nodisc"] - val["ghost0"]), 99)
    check("[PR2-01] spinner band at 1,700 rpm (1/60 s steps): steady frame to frame (95th pct <= 8 levels), no ghost on it, "
          "drawn first and opaque (the disc inside the spinner never shows through the cut-outs)",
          len(xy) > 200 and flick <= 8 and ghost <= 3 and notch <= 2 and pts["order"][0] < pts["order"][1] and pts["depthWrite"],
          f"{len(xy)} band pixels: frame-to-frame {flick:.1f}, ghost zeroed {ghost:.1f}, disc hidden {notch:.1f} levels; "
          f"render order band {pts['order'][0]} / disc {pts['order'][1]}")
    r = await js(page, V + r"""
      T.neutral();
      const rows = [];
      for (const rpm of [20, 24, 28, 32, 36, 40, 44]) { V.setProp({rpm, pitch: 0}, {instant: true}); V.advance(0.6); rows.push([rpm, B.state.fade]); }
      V.setProp({rpm: 0, pitch: 0}, {instant: true}); V.advance(0.1); T.neutral();
      return rows;
    """)
    part = [rpm for rpm, f in r if 0.02 < f < 0.98]
    check("[PR2-02] the solid blades cross-fade into the disc within ~24-40 rpm at 60 fps (half-faded 'glass' blades only briefly)",
          bool(part) and min(part) >= 20 and max(part) <= 44, " ".join(f"{rpm}:{f:.2f}" for rpm, f in r))


async def phone_card_check(page):
    """[UX-6] compact info card on phones: the hint is visible, the tree keeps its room, details fold out."""
    r = await js(page, r"""
      const V = window.viewer; V.tab('parts'); V.select('eng_combustor', {instant: true}); await V.frames(2);
      const card = document.getElementById('infoCard').getBoundingClientRect(), hint = document.getElementById('icHint').getBoundingClientRect();
      const body = document.getElementById('panelBody').getBoundingClientRect(), sheet = document.getElementById('panel').getBoundingClientRect();
      const out = {card: card.height, sheet: sheet.height, hint: [hint.top, hint.bottom, hint.height], cardBox: [card.top, card.bottom], tree: body.height,
        bodyShown: getComputedStyle(document.getElementById('icBody')).display !== 'none'};
      document.getElementById('icMore').click(); await V.frames(1);
      out.expanded = getComputedStyle(document.getElementById('icBody')).display !== 'none';
      document.getElementById('icMore').click();
      return out;
    """)
    ok = (r["hint"][2] > 10 and r["hint"][0] >= r["cardBox"][0] and r["hint"][1] <= r["cardBox"][1] and r["hint"][1] <= PHONE["height"]
          and not r["bodyShown"] and r["expanded"] and r["tree"] >= 120)
    check("[UX-6] phone info card: hint visible, compact (details fold out), tree keeps room", ok,
          f"card {r['card']:.0f}px of sheet {r['sheet']:.0f}px, hint {r['hint'][2]:.0f}px visible, tree {r['tree']:.0f}px, details {r['bodyShown']}->{r['expanded']}")


# ----------------------------------------------------------------------------- interior tour (viewer/tour.js)
def cabin_clearance(p, door_open=False):
    """Clearance (m) of a MODEL-axes eye point to the cabin's lining / headliner / floor, from the interior tables
    (model/interior.py): the side lining at the eye height, the headliner (cabin) or lining crown (flight deck) over
    it, the floor under it.  In the airstair door's clear opening (door open) the side limit is the opening itself."""
    from model import interior as I
    from model import fuselage_parts as FP
    x, y, z = p
    fl = float(I.FLOOR["wl"])
    A = FP.AIRSTAIR
    in_door = door_open and y < -0.40 and abs(x - A["cx"]) <= A["hx"] and z <= FP.DOOR_SILL_WL + 2 * A["hz"]
    if in_door:
        side = min(x - (A["cx"] - A["hx"]), (A["cx"] + A["hx"]) - x, FP.DOOR_SILL_WL + 2 * A["hz"] - z)
        top = side
    else:
        side = I.lining_half_width(x, z) - abs(y)
        top = (I.headliner_z(x, y) if x >= float(I.DIVIDER["x_aft"]) else I.lining_crown(x, y)) - z
    return {"side": side, "top": top, "floor": z - fl, "min": min(side, top, z - fl)}


TOUR_RAYS = r"""
  // nearest visible surface round the eye (26 directions, 0.5 m): the camera is not inside or against any mesh
  const V = window.viewer, I = V._internals, THREE = I.THREE, cam = I.stage.camera;
  I.model.root.updateMatrixWorld(true);
  const eye = cam.position.clone(), rc = new THREE.Raycaster(), box = new THREE.Box3();
  rc.near = 0; rc.far = 0.5;
  const near = I.model.meshRecs.filter((mr) => mr.mesh.visible).filter((mr) => {
    const g = mr.mesh.geometry; if (!g.boundingBox) g.computeBoundingBox();
    return box.copy(g.boundingBox).applyMatrix4(mr.mesh.matrixWorld).distanceToPoint(eye) <= 0.5; });
  const meshes = near.map((mr) => mr.mesh);
  let best = 0.5, who = '';
  for (const a of [-1, 0, 1]) for (const b of [-1, 0, 1]) for (const c of [-1, 0, 1]) {
    if (!a && !b && !c) continue;
    rc.set(eye, new THREE.Vector3(a, b, c).normalize());
    const h = rc.intersectObjects(meshes, false)[0];
    if (h && h.distance < best) { best = h.distance; who = I.model.meshToPart.get(h.object).id + '/' + (h.object.material.name || ''); }
  }
  return [best, who, near.length];
"""


def lum_stats(path, box):
    from PIL import Image
    import numpy as np
    a = np.asarray(Image.open(path).convert("L").crop(box), float)
    return float(np.median(a)), float(np.percentile(a, 10)), float(np.percentile(a, 90))


async def tour_checks(page, shots=True):
    """Interior tour: the toolbar entry, every stop reached from the menu (camera inside the cabin, clear of every
    surface, well exposed), the walk clamped at the lining / seats / divider / partition / headliner / doorway, the
    keyboard and pointer controls, a flight with motion, and exit restoring the exterior state."""
    V = "const V = window.viewer; "
    # the generated data is current (web/tour_data.py from the interior tables) and self-consistent
    r = subprocess.run([sys.executable, str(ROOT / "web" / "tour_data.py"), "--check"], capture_output=True, text=True)
    check("[T1] tour data (web/viewer/tour_data.js) matches the interior tables", r.returncode == 0,
          (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "")
    data = await js(page, "return window.viewer.tour.data;")
    stops = data["stops"]
    # [T2] the entry: first on the toolbar, an accessible menu button
    e = await js(page, r"""
      const b = document.getElementById('tourEnter'), tb = document.getElementById('toolbar'), r = b.getBoundingClientRect();
      const first = tb.querySelector('button:not([hidden])');
      return {first: first === b, name: b.textContent.trim(), popup: b.getAttribute('aria-haspopup'), ctrl: b.getAttribute('aria-controls'),
        expanded: b.getAttribute('aria-expanded'), visible: r.width > 0 && r.right <= innerWidth && r.bottom <= innerHeight,
        top: document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2) === b || b.contains(document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2)),
        bg: getComputedStyle(b).backgroundColor, accent: getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()};
    """)
    check("[T2] 'Go inside' entry: first toolbar button, accent, menu button (aria-haspopup / controls / expanded)",
          e["first"] and e["visible"] and e["top"] and "Go inside" in e["name"] and e["popup"] == "menu" and e["ctrl"] == "tourMenu"
          and e["expanded"] == "false", f"{e['name']!r}, bg {e['bg']}")
    # [T3] every stop from the menu: at the stop, inside, clear of the lining (tables) and of every mesh (rays)
    await js(page, V + "T.neutral(); V.setStep('paint', {instant: true}); V.panel(false); await new Promise(r => setTimeout(r, 400));")
    bad, rows, lum = [], [], []
    for i, s in enumerate(stops):
        st = await js(page, r"""
          const V = window.viewer, id = arg;
          const trig = V.state.tour.active ? document.getElementById('tourStop') : document.getElementById('tourEnter');
          trig.click(); await V.frames(1);
          const menuOpen = !document.getElementById('tourMenu').hidden;
          document.querySelector(`#tourMenu [data-stop="${id}"]`).click();
          V.tour.finish(); V.advance(3.0); await V.frames(2);
          const st = V.state;
          return {tour: st.tour, camInside: st.camInside, menuOpen, menuClosed: document.getElementById('tourMenu').hidden,
            cam: st.camera.pos, doors: st.doors, cut: st.cutaway, label: document.getElementById('tourStopLabel').textContent,
            exposure: V._internals.stage.renderer.toneMappingExposure};
        """, s["id"])
        t = st["tour"]
        p = t["pos"]
        cl = cabin_clearance(p, door_open=st["doors"]["airstair"] > 0.99)
        ray = await js(page, TOUR_RAYS)
        ok = (t["active"] and t["stop"] == s["id"] and max(abs(a - b) for a, b in zip(p, s["eye"])) < 1e-3 and t["outside"] < 1e-6
              and st["camInside"] and st["menuOpen"] and st["menuClosed"] and st["label"] == s["label"] and not st["cut"]
              and cl["min"] >= 0.05 and ray[0] >= 0.05 and (not s.get("doors") or st["doors"]["airstair"] > 0.99))
        rows.append(f"{s['id']}: region {t['region']}, lining/top/floor {cl['side'] * 1000:.0f}/{cl['top'] * 1000:.0f}/"
                    f"{cl['floor'] * 1000:.0f} mm, nearest mesh {ray[0] * 1000:.0f} mm")
        if not ok:
            bad.append(f"{s['id']}: {t} {cl} ray {ray} menu {st['menuOpen']}/{st['menuClosed']} label {st['label']!r}")
        if shots:
            path = await shot(page, f"40_tour_{i + 1}_{s['id']}", "", note=f"({s['label']})")
            med, p10, p90 = lum_stats(path, (0, 60, VIEW["width"], VIEW["height"] - 60))
            lum.append((s["id"], med, p10, p90))
    check("[T3] every tour stop reachable from the menu: at its eye, camera inside the cabin (lining / headliner / floor "
          ">= 50 mm by the tables, nearest mesh >= 50 mm), lit as inside", not bad, "; ".join(bad[:2]) or " | ".join(rows))
    if lum:
        # (the airstair stop looks out of the door at the studio floor, -38 deg since review r2 NAV2-05: an outside view,
        # up to 235 like the exterior shots)
        dark = [x for x in lum if not (70 <= x[1] <= (235 if x[0] == "airstair" else 215) and x[2] >= 12)]
        check("[T4] every stop well exposed (median luminance 70-215, the airstair door's view out 70-235; 10th percentile >= 12)", not dark,
              ", ".join(f"{k} {m:.0f} ({a:.0f}-{b:.0f})" for k, m, a, b in lum))
        # review r1 NAV1-04: the headliner reads light (the photos are near-white; at >= 200 AgX greys the whole cabin)
        hl = [lum_stats(str(OUT / f"40_tour_{i + 1}_{s['id']}.png"), (330, 70, 630, 130))[0] for i, s in enumerate(stops)
              if s["id"] == "cabin_fwd"]
        check("[T4b] cabin_fwd headliner light (median >= 200 / 255; review r2 NAV2-04)", bool(hl) and hl[0] >= 200, f"{hl[0]:.0f}" if hl else "no shot")
    # [T5] walking: clamped at the partition, the flight deck front, the seats, the headliner, the floor, the divider
    r = await js(page, r"""
      const V = window.viewer, T = V.tour, out = {};
      const at = (id) => { T.go(id, {motion: false}); };
      const look = (deg) => { const s = T.state(); T.look(deg - s.yawDeg, -s.pitchDeg); };
      at('cabin_fwd'); look(0);   out.aft = T.walk({f: 1}, 12);
      look(180);                  out.fwd = T.walk({f: 1}, 14);
      at('cabin_aft'); look(0); T.walk({f: 1}, 1.6);
      out.club_x = T.state().pos[0];
      out.port = T.walk({s: -1}, 4); out.stbd = T.walk({s: 1}, 6);
      out.up = T.walk({u: 1}, 4); out.down = T.walk({u: -1}, 6);
      V.setDoor('airstair', 0, {instant: true});
      at('cabin_aft'); look(180); T.walk({s: -1}, 4); out.vest = T.state();
      out.divider = T.walk({f: 1}, 4);
      at('airstair'); look(-90); out.door = T.walk({f: 1}, 4);
      V.setDoor('airstair', 0, {instant: true}); V.advance(2.0); out.doorShut = T.state();
      V.setDoor('airstair', 1, {instant: true});
      at('pilot'); out.pilotFwd = T.walk({f: 1}, 3); out.pilotIn = T.walk({s: 1}, 3);
      // out of the pilot seat: inboard into the gap between the seats, then aft into the flight deck (standing up)
      at('pilot'); T.walk({s: 1}, 0.36); look(0); out.pilotAft = T.walk({f: 1}, 3);
      // a sidestep in the aisle next to a seat slides into it (review r1 NAV1-07)
      const p3 = V.tour.data.regions.find((g) => g.id === 'seat_pax3');
      at('cabin_aft'); look(0); T.walk({f: 1}, (p3.x[0] - 0.30 - T.state().pos[0]) / 1.0);
      out.pullFrom = T.state().pos; out.pull = T.walk({s: 1}, 2.5);
      return out;
    """)
    R = {x["id"]: x for x in data["regions"]}
    fl, ce = data["floor"], data["ceiling"]
    walks = {k: v for k, v in r.items() if isinstance(v, dict)}
    clear = {k: cabin_clearance(v["pos"], door_open=(k == "door")) for k, v in walks.items()}
    worst = min(clear.items(), key=lambda kv: kv[1]["min"])
    outside = max(v["outside"] for v in walks.values())
    ok = (abs(r["aft"]["pos"][0] - R["aisle"]["x"][1]) < 2e-3                       # baggage partition (curtain)
          and abs(r["fwd"]["pos"][0] - R["crew_gap"]["face_x0"]) < 2e-3 and r["fwd"]["region"] == "crew_gap"   # on
          #   down into the gap between the crew seats, level with the seated eyes (review r3 NAV3-01), not over the pedestal
          and sorted(round(v["pos"][1], 3) for v in (r["port"], r["stbd"])) == [round(R["aisle"]["y"][0], 3), round(R["aisle"]["y"][1], 3)]
          and r["down"]["pos"][2] >= data["crouch_min"] - 1e-6 and r["up"]["pos"][2] > r["down"]["pos"][2]
          and abs(r["vest"]["pos"][1] - R["vestibule"]["y"][0]) < 2e-3              # entry vestibule, the lining side
          and abs(r["divider"]["pos"][0] - R["vestibule"]["x"][0]) < 2e-3           # stopped at the divider's aft face
          and abs(r["door"]["pos"][1] - R["doorway"]["y"][0]) < 2e-3                # the open doorway's outboard limit
          and r["doorShut"]["pos"][1] >= R["vestibule"]["y"][0] - 2e-3              # eased in once the door shut
          and r["pilotFwd"]["region"] == "seat_pilot" and r["pilotIn"]["region"] in ("crew_gap", "flight_deck", "seat_copilot")
          and r["pilotAft"]["region"] in ("flight_deck", "aisle") and r["pilotAft"]["pos"][2] - fl > 1.2
          and r["pull"]["region"] == "seat_pax3"
          and outside < 1e-6 and worst[1]["min"] >= 0.05)
    check("[T5] walking is held inside the cabin: partition, flight-deck front, aisle edges at the seats, headliner, "
          "floor, vestibule lining, divider wall, doorway (and back in when the door shuts), the pilot's seat",
          ok, f"aft x {r['aft']['pos'][0]:.3f}, fwd x {r['fwd']['pos'][0]:.3f} ({r['fwd']['region']}), aisle y {r['port']['pos'][1]:+.3f}/{r['stbd']['pos'][1]:+.3f} "
              f"at x {r['club_x']:.2f}, eye {r['down']['pos'][2] - fl:.3f}-{r['up']['pos'][2] - fl:.3f} above the floor, vestibule y "
              f"{r['vest']['pos'][1]:+.3f}, divider x {r['divider']['pos'][0]:.3f}, doorway y {r['door']['pos'][1]:+.3f} -> "
              f"{r['doorShut']['pos'][1]:+.3f} shut, nearest lining/headliner {worst[1]['min'] * 1000:.0f} mm ({worst[0]}); pilot seat "
              f"-> {r['pilotAft']['region']}; aisle sidestep at x {r['pullFrom'][0]:.2f} -> {r['pull']['region']}")
    # review r1 NAV1-01 / 02: the walk's ends keep the eye off the walls (no full-screen smear): forward, between the seat
    # backs >= 0.45 m from every flight-deck mesh; aft, >= 0.35 m from the baggage curtain / header
    near = {}
    for k, setup in (("fwd", "TT.go('cabin_fwd', {motion: false}); look(180); TT.walk({f: 1}, 14);"),
                     ("aft", "TT.go('cabin_aft', {motion: false}); look(0); TT.walk({f: 1}, 12);")):
        near[k] = await js(page, "const TT = window.viewer.tour; const look = (deg) => { const s = TT.state(); "
                                 "TT.look(deg - s.yawDeg, -s.pitchDeg); }; " + setup + " window.viewer.advance(0.05);" + r'''
          // the nearest surface in the line of sight: rays within 12 deg left / right and 12 deg below .. 6 deg above the
          // level walking direction, 1 m (the overhead console hangs above the head between the crew seat backs, as in
          // the aircraft: a ray 12 deg up meets it ~0.4 m ahead)
          const V = window.viewer, I = V._internals, THREE = I.THREE, cam = I.stage.camera;
          I.model.root.updateMatrixWorld(true);
          const eye = cam.position.clone(), d0 = new THREE.Vector3(), rc = new THREE.Raycaster();
          cam.getWorldDirection(d0); d0.y = 0; d0.normalize();
          rc.near = 0; rc.far = 1.0;
          const meshes = I.model.meshRecs.filter((mr) => mr.mesh.visible).map((mr) => mr.mesh);
          let best = 1.0, who = '';
          for (const yaw of [-12, -6, 0, 6, 12]) for (const pit of [-12, -6, 0, 6]) {
            const d = d0.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), yaw * Math.PI / 180);
            d.applyAxisAngle(new THREE.Vector3().crossVectors(d, new THREE.Vector3(0, 1, 0)).normalize(), pit * Math.PI / 180);
            rc.set(eye, d.normalize());
            const h = rc.intersectObjects(meshes, false)[0];
            if (h && h.distance < best) { best = h.distance; who = I.model.meshToPart.get(h.object).id + '/' + (h.object.material.name || ''); }
          }
          return [best, who];''')
    check("[T5b] walk ends: in the line of sight forward from the gap between the crew seats >= 0.45 m to the flight "
          "deck, aft (looking aft) >= 0.80 m to the baggage curtain / header (review r3 NAV3-04: 0.40 m was one flat wall)",
          near["fwd"][0] >= 0.45 and near["aft"][0] >= 0.80,
          f"forward end nearest mesh {near['fwd'][0] * 1000:.0f} mm ({near['fwd'][1]}), aft end {near['aft'][0] * 1000:.0f} mm ({near['aft'][1]})")
    # [T6] keyboard: the menu by keys (Enter / arrows / Enter), W walks, arrow turns, digits pick stops, Esc exits
    r = await js(page, "window.viewer.tour.exit({motion: false}); window.viewer.tour.menu(false); document.getElementById('tourEnter').focus(); return document.activeElement.id;")
    await page.keyboard.press("Enter")
    k1 = await js(page, "return [!document.getElementById('tourMenu').hidden, document.activeElement.dataset.stop || document.activeElement.id];")
    await page.keyboard.press("ArrowDown")
    await page.keyboard.press("ArrowDown")
    k2 = await js(page, "return document.activeElement.dataset.stop || document.activeElement.id;")
    await page.keyboard.press("Enter")
    await js(page, "window.viewer.tour.finish(); await window.viewer.frames(1);")
    k3 = await js(page, "return [window.viewer.state.tour.stop, document.activeElement.id];")
    await page.keyboard.press("4")
    await js(page, "window.viewer.tour.finish();")
    s0 = await js(page, "return window.viewer.state.tour;")
    # held keys act per animation frame (frame dt, at most 0.1 s): hold them over a few rendered frames (a SwiftShader
    # frame of the cabin takes seconds, and headless Chromium hands requestAnimationFrame 1/60 s steps)
    await page.keyboard.down("w")
    await js(page, "await window.viewer.frames(4);")
    await page.keyboard.up("w")
    await page.keyboard.down("ArrowLeft")
    await js(page, "await window.viewer.frames(4);")
    await page.keyboard.up("ArrowLeft")
    await js(page, "await window.viewer.frames(2);")
    s1 = await js(page, "return window.viewer.state.tour;")
    await page.keyboard.press("Escape")
    await js(page, "window.viewer.tour.finish(); await window.viewer.frames(1);")
    s2 = await js(page, "return [window.viewer.state.tour.active, window.viewer.state.cameraPreset];")
    ok = (r == "tourEnter" and k1 == [True, "pilot"] and k2 == "fd_cabin" and k3 == ["fd_cabin", "tourStop"] and s0["stop"] == "cabin_fwd"
          and s1["pos"][0] < s0["pos"][0] - 0.002 and abs(s1["yawDeg"] - s0["yawDeg"]) > 0.05 and s1["outside"] < 1e-6 and s2 == [False, "three_quarter"])
    check("[T6] keyboard: Enter opens the stop menu (focus on stop 1), arrows + Enter enter stop 3 (focus on the stop button), "
          "4 = cabin forward, W walks, Left turns, Esc goes back outside", ok,
          f"menu {k1}, -> {k2}, entered {k3}, walked {s0['pos'][0]:.3f} -> {s1['pos'][0]:.3f}, yaw {s0['yawDeg']:.0f} -> {s1['yawDeg']:.0f}, out {s2}")
    # [T7] pointer: a drag looks around (the eye stays put), the wheel moves forward, no picking while inside
    await js(page, "window.viewer.tour.enter('cabin_aft', {motion: false}); await window.viewer.frames(1);")
    a = await js(page, "return window.viewer.state.tour;")
    cv = await js(page, "const r = window.viewer._internals.stage.renderer.domElement.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2];")
    await page.mouse.move(cv[0], cv[1])
    await page.mouse.down()
    for i in range(1, 6):
        await page.mouse.move(cv[0] + 30 * i, cv[1] + 6 * i)
    await page.mouse.up()
    b = await js(page, "return [window.viewer.state.tour, window.viewer.state.selected];")
    await page.mouse.wheel(0, -300)
    await page.wait_for_timeout(600)
    c = await js(page, "await window.viewer.frames(2); return window.viewer.state.tour;")
    ok = (abs(b[0]["yawDeg"] - a["yawDeg"]) > 10 and b[0]["pitchDeg"] > a["pitchDeg"] and b[0]["pos"] == a["pos"] and b[1] is None
          and c["pos"][0] > a["pos"][0] + 0.2 and c["outside"] < 1e-6)
    check("[T7] pointer: a drag turns the view (the eye stays), the wheel walks forward, nothing picked", ok,
          f"yaw {a['yawDeg']:.0f} -> {b[0]['yawDeg']:.0f}, pitch {a['pitchDeg']:.1f} -> {b[0]['pitchDeg']:.1f}, wheel x {a['pos'][0]:.3f} -> {c['pos'][0]:.3f}")
    # [T8] the flights (motion on): outside -> fade -> inside; inside -> inside along the aisle, never through a wall
    r = await js(page, r"""
      const V = window.viewer, T = V.tour;
      T.exit({motion: false}); V.setCamera('three_quarter', {instant: true}); T.motion(true); V.pause(true);
      T.enter('cabin_aft');
      let fadeMax = 0, n = 0, cutAt = null, camOut = null;
      while (V.state.tour.flying && n < 400) { V.advance(0.05); n++; const s = V.state.tour; fadeMax = Math.max(fadeMax, s.fade);
        if (cutAt == null && V._internals.tour.inside) cutAt = n * 0.05; }
      const end1 = V.state.tour;
      T.go('club');
      let worst = 0, jump = 0, prev = V.state.tour.yawDeg, m = 0, regions = new Set();
      while (V.state.tour.flying && m < 400) { V.advance(0.05); m++; const s = V.state.tour; worst = Math.max(worst, s.outside);
        jump = Math.max(jump, Math.abs(((s.yawDeg - prev + 540) % 360) - 180)); prev = s.yawDeg; regions.add(s.region); }
      const end2 = V.state.tour;
      T.go('pilot');
      let k = 0, worst2 = 0; prev = V.state.tour.yawDeg;
      while (V.state.tour.flying && k < 400) { V.advance(0.05); k++; const s = V.state.tour; worst2 = Math.max(worst2, s.outside);
        jump = Math.max(jump, Math.abs(((s.yawDeg - prev + 540) % 360) - 180)); prev = s.yawDeg; }
      const end3 = V.state.tour;
      T.exit();
      let x = 0; while (V.state.tour.flying && x < 100) { V.advance(0.05); x++; }
      const out = {t1: n * 0.05, fadeMax, cutAt, end1, t2: m * 0.05, worst, jump, regions: [...regions], end2, t3: k * 0.05, worst2, end3,
        t4: x * 0.05, exitState: V.state.tour, preset: V.state.cameraPreset, fadeEnd: V.state.tour.fade};
      T.motion(null); V.pause(false);
      return out;
    """)
    ok = (r["end1"]["stop"] == "cabin_aft" and not r["end1"]["flying"] and r["fadeMax"] > 0.98 and r["cutAt"] is not None
          and 0.8 < r["t1"] < 3.0 and r["end2"]["stop"] == "club" and r["worst"] < 0.03 and r["jump"] < 12 and 0.8 < r["t2"] < 3.6
          and r["end3"]["stop"] == "pilot" and r["worst2"] < 0.03 and not r["exitState"]["active"] and r["preset"] == "three_quarter"
          and r["fadeEnd"] == 0)
    check("[T8] flights: outside -> inside fades through the skin; cabin aft -> club seat -> pilot along the aisle (never "
          "more than 30 mm off the walkable volume, the view turning < 240 deg/s); exit fades back to the 3/4 view", ok,
          f"in {r['t1']:.2f} s (cut at {r['cutAt']}), -> club {r['t2']:.2f} s (off {r['worst'] * 1000:.0f} mm, yaw step <= {r['jump']:.1f} deg, "
          f"via {r['regions']}), -> pilot {r['t3']:.2f} s (off {r['worst2'] * 1000:.0f} mm), out {r['t4']:.2f} s")
    # [T9] exit restores what the tour changed: cutaway, X-ray, explode, build step, isolate, panel, the airstair door
    r = await js(page, r"""
      const V = window.viewer;
      V.setStep('wing', {instant: true}); V.setCutaway(true); V.setExplode(0.4, {instant: true}); V.setDoor('cargo', 1, {instant: true});
      V.panel(true); V.isolate(null);
      const before = V.state;
      V.tour.enter('airstair', {motion: false}); V.advance(0.1); await V.frames(1);   // (camInside: the render loop's updateCabin)
      const inside = V.state;
      V.tour.exit({motion: false}); await V.frames(1);
      const after = V.state;
      V.setCutaway(false); V.setExplode(0, {instant: true}); V.setDoor('cargo', 0, {instant: true}); V.setStep('paint', {instant: true});
      return {before: [before.stepKey, before.cutawayUser, before.explodeTarget, before.doors, before.cameraPreset],
        inside: [inside.stepKey, inside.cutaway, inside.explodeTarget, inside.doors, inside.camInside, inside.tour.active],
        after: [after.stepKey, after.cutawayUser, after.explodeTarget, after.doors, after.cameraPreset, after.tour.active,
          V._internals.stage.controls.enabled, document.getElementById('app').classList.contains('touring')]};
    """)
    b, i_, a_ = r["before"], r["inside"], r["after"]
    ok = (i_[0] == "paint" and i_[1] is False and i_[2] == 0 and i_[3]["airstair"] == 1 and i_[3]["cargo"] == 1 and i_[4] and i_[5]
          and a_[0] == b[0] and a_[1] is True and abs(a_[2] - 0.4) < 1e-9 and a_[3]["airstair"] == 0 and a_[3]["cargo"] == 1
          and a_[4] == "three_quarter" and a_[5] is False and a_[6] is True and a_[7] is False)
    check("[T9] exit restores the exterior state (build step, cutaway, explode, the airstair door it opened; a door the user "
          "opened stays) and the orbit camera at the 3/4 view", ok, f"before {b}, inside {i_}, after {a_}")


    await tour_r2_checks(page, data, shots)
    await tour_r3_checks(page, data, shots)
    await tour_r4_checks(page, data, shots)


async def tour_r2_checks(page, data, shots=True):
    """[T12] review r2 (NAV2-01..06): a stop picked during the exit fade goes back inside cleanly; a sideways step out of
    a seat holds on the aisle / gap centre line until pressed again, an aft step from a crew seat walks out through the
    gap; a walk into a seat turns to its facing; the airstair stop looks out at -38 deg; the vestibule keeps WALL_CLEAR
    from the closed door's lining."""
    from model import interior as I
    from model import fuselage_parts as FP
    r = await js(page, r"""
      const V = window.viewer, T = V.tour, out = {};
      const look = (deg, pitch = 0) => { const s = T.state(); T.look(deg - s.yawDeg, pitch - s.pitchDeg); };
      // NAV2-01: a stop picked 0.1 s into the exit fade
      T.motion(true);
      T.enter('cabin_fwd', {motion: false}); V.advance(0.2);
      T.exit({motion: true}); V.advance(0.1); T.go('club'); V.advance(6); await V.frames(2);
      const s1 = T.state();
      out.race = {active: s1.active, stop: s1.stop, flying: s1.flying, camInside: V.state.camInside,
        touring: document.getElementById('app').classList.contains('touring'), controls: V._internals.stage.controls.enabled};
      T.motion(null);
      // NAV2-02: from the club seat (PAX 3) a held sidestep stops on the aisle centre line; pressed again, into PAX 4
      T.go('club', {motion: false});
      const a = T.walk({s: 1}, 1.0), b = T.walk({s: 1}, 1.0);
      out.club = [a.region, a.pos[1], b.region, b.pos[1]];
      // ... a short sidestep in the pilot seat, then S: out through the gap to the cabin; a long one stops in the gap,
      // pressed again it goes on into the co-pilot seat
      T.go('pilot', {motion: false}); T.walk({s: 1}, 0.15); const c = T.walk({f: -1}, 3);
      T.go('pilot', {motion: false}); const d = T.walk({s: 1}, 1.0), e = T.walk({s: 1}, 1.0);
      out.pilot = [c.region, c.pos[0], d.region, d.pos[1], e.region];
      // NAV2-03: walking aft from the divider, a sidestep into PAX 3 (forward-facing) turns the view forward
      T.go('cabin_aft', {motion: false}); look(0); T.walk({f: 1}, 1.9); const f = T.walk({s: 1}, 1.5);
      out.seat = [f.region, f.yawDeg, f.pitchDeg, f.pos[1]];
      // NAV2-05 / NAV3-02: the airstair stop's pitch (landscape)
      T.go('airstair', {motion: false}); out.air = T.state().pitchDeg;
      T.exit({motion: false}); await V.frames(1);
      return out;
    """)
    R = {x["id"]: x for x in data["regions"]}
    rc = r["race"]
    check("[T12] NAV2-01: a stop picked during the exit fade goes back inside (tour, UI and camera agree)",
          rc["active"] and rc["stop"] == "club" and not rc["flying"] and rc["touring"] and not rc["controls"] and rc["camInside"], str(rc))
    cl, pi = r["club"], r["pilot"]
    ok = (cl[0] == "aisle" and abs(cl[1]) < 1e-3 and cl[2] == "seat_pax4" and abs(cl[3] - R["seat_pax4"]["eye_bl"]) < 1e-3
          and pi[0] in ("aisle", "flight_deck") and pi[1] > R["flight_deck"]["x"][0] and pi[2] == "crew_gap" and abs(pi[3]) < 1e-3
          and pi[4] == "seat_copilot")
    check("[T12] NAV2-02: a sidestep out of a seat holds on the aisle / gap centre line (pressed again: the opposite seat); "
          "an aft step from a crew seat walks out through the gap", ok,
          f"club: {cl[0]} y {cl[1]:+.3f} -> {cl[2]} y {cl[3]:+.3f}; pilot: S -> {pi[0]} x {pi[1]:.2f}, D -> {pi[2]} y {pi[3]:+.3f} -> {pi[4]}")
    se = r["seat"]
    check("[T12] NAV2-03: a sidestep into a forward-facing seat turns the view forward (-8 deg) and ends at the seated eye",
          se[0] == "seat_pax3" and abs(abs(se[1]) - 180) < 0.5 and abs(se[2] + 8) < 0.5 and abs(se[3] - R["seat_pax3"]["eye_bl"]) < 1e-3,
          f"{se[0]}, yaw {se[1]:.1f}, pitch {se[2]:.1f}, y {se[3]:+.3f}")
    fl = float(I.FLOOR["wl"])
    wall = float(I.lining_half_width(float(FP.AIRSTAIR["cx"]), fl + 1.0)) + R["vestibule"]["y"][0]
    check("[T12] NAV2-05 / 06: the airstair stop looks down the steps (-48 deg on a landscape screen, review r3 NAV3-02); "
          "the vestibule keeps 0.40 m from the closed door (widened onto the doorway only while it is open)",
          abs(r["air"] + 48) < 0.5 and abs(wall - 0.40) < 2e-3
          and R["vestibule_door"].get("when") == "door_airstair" and R["vestibule_door"]["y"][0] <= -0.449,
          f"pitch {r['air']:.1f}, vestibule edge {R['vestibule']['y'][0]:+.3f} = {wall:.3f} m from the door lining")


async def tour_r3_checks(page, data, shots=True):
    """[T13] review r3 (NAV3-01..05): a forward walk from the cabin goes on into the gap between the crew seats and a
    sidestep from there into a crew seat; a walk from a stop's steep look levels the view (a look input keeps the
    user's pitch); the aft end of the aisle looking aft stops 0.9 m short of the baggage partition; in a seat the walk
    turned round, the strafe that pushes into the side wall slides back out to the aisle; the airstair stop from inside
    the door frame (BL -0.42, -112 / -48 deg), its hint under the toolbar, the hint fading after the first input."""
    r = await js(page, r"""
      const V = window.viewer, T = V.tour, out = {};
      const look = (deg, pitch = 0) => { const s = T.state(); T.look(deg - s.yawDeg, pitch - s.pitchDeg); };
      // NAV3-01: cabin_fwd -> W 6 s -> A: the pilot seat
      T.go('cabin_fwd', {motion: false}); out.fwd = T.walk({f: 1}, 6); out.into = T.walk({s: -1}, 1.2);
      // NAV3-03: out of the pilot seat (-21 deg) and aft: levelled to -6; with an F press first, the user's pitch stays
      T.go('pilot', {motion: false}); out.p0 = T.state().pitchDeg; out.lvl = T.walk({f: -1}, 1.6);
      T.go('pilot', {motion: false}); T.walk({f: -1}, 0.3); T.look(0, -10); out.own = T.walk({f: -1}, 1.3);
      // NAV3-04: walking aft looking aft ends FACE_CLEAR short of the partition; backing up still reaches cabin_fwd
      T.go('cabin_aft', {motion: false}); look(0); out.aft = T.walk({f: 1}, 8);
      look(180); out.back = T.walk({f: -1}, 3);
      // NAV3-05: forward down the aisle, a sidestep into PAX 1 (aft-facing: the view turns round), then the other
      // strafe (pushing outboard) slides back out to the aisle
      const p1 = V.tour.data.regions.find((g) => g.id === 'seat_pax1');
      T.go('cabin_fwd', {motion: false});
      T.walk({f: 1}, (T.state().pos[0] - 0.5 * (p1.x[0] + p1.x[1])) / 1.0);
      out.in1 = T.walk({s: -1}, 1.2); V.advance(0.5); out.in1b = T.state();
      out.out1 = T.walk({s: 1}, 1.5);
      // NAV3-02: the airstair stop and its hint (shown again: earlier checks' looks have faded it)
      T.exit({motion: false}); await V.frames(1);
      const U = V._internals.tourUI; U.hintDismissed = false; clearTimeout(U.hintTimer); U.hintTimer = null;
      T.enter('airstair', {motion: false}); await V.frames(1);
      const h = document.getElementById('tourHint');
      out.air = T.state();
      out.hintTop = !h.hidden && h.classList.contains('top') && h.getBoundingClientRect().top < innerHeight / 3;
      T.look(5, 0);
      for (let i = 0; i < 150 && !h.hidden; i++) await new Promise((res) => setTimeout(res, 100));   // ~2.9 s nominal
      out.hintGone = h.hidden;
      T.exit({motion: false}); await V.frames(1);
      return out;
    """)
    R = {x["id"]: x for x in data["regions"]}
    f, i = r["fwd"], r["into"]
    check("[T13] NAV3-01: a forward walk from the cabin goes on into the gap between the crew seats (seated eye), a sidestep "
          "from there into the pilot seat",
          f["region"] == "crew_gap" and abs(f["pos"][0] - R["crew_gap"]["face_x0"]) < 2e-3
          and abs(f["pos"][2] - R["crew_gap"]["eye_z"]) < 2e-3 and i["region"] == "seat_pilot"
          and abs(i["pos"][1] - R["seat_pilot"]["eye_bl"]) < 2e-3,
          f"W -> {f['region']} {f['pos']}, A -> {i['region']} {i['pos']}")
    lv, ow = r["lvl"], r["own"]
    check("[T13] NAV3-03: a walk out of a stop's steep look levels the view to -6 deg; after a look input the user's "
          "pitch stays", r["p0"] < -15 and abs(lv["pitchDeg"] + 6) < 0.5 and lv["region"] in ("aisle", "flight_deck", "crew_gap")
          and ow["pitchDeg"] < -20 and not ow["pitchAuto"],
          f"pilot {r['p0']:.1f} -> {lv['pitchDeg']:.1f} deg ({lv['region']}); with a look first {ow['pitchDeg']:.1f}")
    a, b = r["aft"], r["back"]
    face = R["aisle"].get("face_x1")
    check("[T13] NAV3-04: walking aft looking aft ends 0.9 m short of the baggage partition; backing up reaches the "
          "cabin_fwd stop's eye", face is not None and abs(a["pos"][0] - face) < 2e-3 and abs(b["pos"][0] - R["aisle"]["x"][1]) < 2e-3,
          f"aft end x {a['pos'][0]:.3f} (face_x1 {face}), backing up x {b['pos'][0]:.3f} (aisle end {R['aisle']['x'][1]})")
    n1, n1b, o1 = r["in1"], r["in1b"], r["out1"]
    check("[T13] NAV3-05: a sidestep into an aft-facing seat from a forward walk turns the view round; the other strafe "
          "(into the side wall) slides back out to the aisle",
          n1["region"] == "seat_pax1" and n1b["seatFlip"] and abs(n1b["yawDeg"]) < 1 and o1["region"] == "aisle"
          and abs(o1["pos"][1]) <= R["aisle"]["y"][1] + 1e-3,
          f"in: {n1['region']} yaw {n1b['yawDeg']:.0f} flip {n1b['seatFlip']}; other strafe -> {o1['region']} y {o1['pos'][1]:+.3f}")
    ai = r["air"]
    import importlib.util as _ilu
    _sp = _ilu.spec_from_file_location("tour_data_py", ROOT / "web" / "tour_data.py")
    _td = _ilu.module_from_spec(_sp); _sp.loader.exec_module(_td)
    air_look = _td.AIRSTAIR_LOOK                        # (-106 / -48 since review r4 NAV8-05; r3: -112 / -48)
    check(f"[T13] NAV3-02: the airstair stop from inside the door frame (BL -0.42) looking down the steps ({air_look[0]:.0f} / {air_look[1]:.0f} deg), "
          "its hint under the toolbar, gone after the first look input",
          abs(ai["pos"][1] + 0.42) < 1e-3 and abs(ai["yawDeg"] - air_look[0]) < 0.5 and abs(ai["pitchDeg"] - air_look[1]) < 0.5
          and r["hintTop"] and r["hintGone"],
          f"eye {ai['pos']}, yaw {ai['yawDeg']:.1f}, pitch {ai['pitchDeg']:.1f}, hint top {r['hintTop']}, faded {r['hintGone']}")
    if shots:
        await js(page, "const T = window.viewer.tour; T.enter('airstair', {motion: false}); await window.viewer.frames(2);")
        await shot(page, "43_tour_airstair_r3", "")
        await js(page, "window.viewer.tour.exit({motion: false}); await window.viewer.frames(1);")


# material-ID pass at the current camera: each listed group of material names in its own flat colour (R = (k + 1) * 16,
# G = B = 0), everything else black, rendered with the stage camera into a target the size of the drawing buffer
MAT_MASK = r"""
  const groups = arg, V = window.viewer, I = V._internals, THREE = I.THREE, st = I.stage, r = st.renderer;
  const size = r.getDrawingBufferSize(new THREE.Vector2());
  const rt = new THREE.WebGLRenderTarget(size.x, size.y);
  const cols = groups.map((g, i) => new THREE.MeshBasicMaterial({color: new THREE.Color().setRGB((i + 1) / 16, 0, 0, THREE.LinearSRGBColorSpace), toneMapped: false}));
  const blank = new THREE.MeshBasicMaterial({color: 0x000000, toneMapped: false});
  const saved = new Map();
  // a group lists material names, or 'part:material' for one part's material only
  I.model.root.traverse((o) => { if (o.isMesh) { saved.set(o, o.material); const pr = I.model.meshToPart.get(o), pid = pr ? pr.id : '';
    const nm = o.material.name || ''; const gi = groups.findIndex((g) => g.includes(nm) || g.includes(pid + ':' + nm));
    const m = (gi >= 0 ? cols[gi] : blank).clone(); m.side = o.material.side; m.clippingPlanes = o.material.clippingPlanes; o.material = m; } });
  const bg = st.scene.background; st.scene.background = null;
  const hid = []; st.scene.traverse((o) => { if (o.visible && (o.isMesh || o.isLine || o.isPoints || o.isSprite) && !saved.has(o)) { hid.push(o); o.visible = false; } });
  r.setRenderTarget(rt); r.setClearColor(0x000000, 1); r.clear(); r.render(st.scene, st.camera); r.setRenderTarget(null); r.setClearColor(0x000000, 0);
  const px = new Uint8Array(size.x * size.y * 4); r.readRenderTargetPixels(rt, 0, 0, size.x, size.y, px);
  for (const [o, m] of saved) o.material = m;
  for (const o of hid) o.visible = true;
  st.scene.background = bg; rt.dispose(); st.needsRender = true;
  // per CSS pixel (nearest), flipped to screen rows: the group index + 1, 0 = none
  const W = innerWidth, H = innerHeight, out = new Array(W * H).fill(0);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const sx = Math.min(size.x - 1, Math.floor((x + 0.5) * size.x / W)), sy = size.y - 1 - Math.min(size.y - 1, Math.floor((y + 0.5) * size.y / H));
    const i = (sy * size.x + sx) * 4, R = px[i];
    if (px[i + 1] < 4 && px[i + 2] < 4 && R >= 8) { const k = Math.round(R / 16); if (Math.abs(R - 16 * k) <= 3 && k >= 1 && k <= groups.length) out[y * W + x] = k; }
  }
  return {W, H, mask: out.join(',')};
"""


async def material_stats(page, png_path, groups):
    """Median sRGB and HSV of each material group's interior pixels (the ID mask eroded by one pixel) in the screenshot
    png_path taken at the current camera: {name: (n, (r, g, b), lum, hue_deg, sat)}."""
    import colorsys
    import numpy as np
    from PIL import Image
    names = list(groups)
    m = await js(page, MAT_MASK, [groups[k] for k in names])
    W, H = m["W"], m["H"]
    k = np.array(m["mask"].split(","), int).reshape(H, W)
    img = np.asarray(Image.open(png_path).convert("RGB"), float)[:H, :W]
    out = {}
    for i, n in enumerate(names):
        g = k == i + 1
        e = g.copy()
        e[1:, :] &= g[:-1, :]; e[:-1, :] &= g[1:, :]; e[:, 1:] &= g[:, :-1]; e[:, :-1] &= g[:, 1:]
        if e.sum() < 20:
            out[n] = (int(e.sum()), None, None, None, None)
            continue
        c = np.median(img[e], 0)
        h, s_, v = colorsys.rgb_to_hsv(*(c / 255.0))
        out[n] = (int(e.sum()), tuple(int(x) for x in c), float(0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]), h * 360.0, s_)
    return out


async def tour_r4_checks(page, data, shots=True):
    """[T14]-[T18] review r4: the cabin light (NAV8-01 / INT8-01: no veil over the dark trim, the light trim near-white,
    the runner's AI Orange saturated), a released sidestep stops at once (NAV8-02: real key events), a walk into a crew
    seat turns to its stop's pitch (NAV8-03), the stop button follows the walk (NAV8-04), the airstair stop's portrait
    heading and the walk pad aside there (NAV8-05)."""
    from model import interior as I
    V = "const V = window.viewer, T = V.tour; "
    await js(page, V + "V.panel(false); await new Promise(r => setTimeout(r, 300));")
    look = {}
    for sid in ("pilot", "fd_cabin", "cabin_fwd"):
        await js(page, V + "T.enter(arg, {motion: false}); T.finish(); V.advance(0.5); await V.frames(3);", sid)
        path = await shot(page, f"44_tour_look_{sid}", "")
        look[sid] = await material_stats(page, path, {
            "lining": ["lining"], "overhead": ["interior_lining:panel_dark"], "bezel": ["flight_deck:bezel_black"],
            "runner": ["carpet_orange"],
            "ledge": ["ledge_top", "ledge_panel"], "walnut": ["veneer_walnut"]})
        await js(page, V + "T.exit({motion: false}); await V.frames(1);")
    rows, ok = [], True
    for sid, st in look.items():
        rows.append(sid + ": " + ", ".join(f"{k} {v[2]:.0f}" + (f" h{v[3]:.0f} s{v[4]:.2f}" if k == "runner" else "")
                                          for k, v in st.items() if v[1] is not None))
    fd = [look[s][k][2] for s in ("pilot", "fd_cabin") for k in ("overhead", "bezel") if look[s][k][1] is not None]
    hl = [look[s]["lining"][2] for s in ("cabin_fwd", "fd_cabin") if look[s]["lining"][1] is not None]
    cf = look["cabin_fwd"]
    run, led, wal = cf["runner"], cf["ledge"], cf["walnut"]
    ok = (len(fd) >= 3 and max(fd) <= 50 and cf["lining"][1] is not None and min(hl) >= 190 and run[1] is not None and 20 <= run[3] <= 35
          and run[4] >= 0.6 and led[1] is not None and led[2] <= 80 and wal[1] is not None and wal[2] <= 90)
    check("[T14] NAV8-01 / INT8-01: the cabin light -- overhead panel and display bezels near-black (<= 50) on the pilot / "
          "fd_cabin stops, the lining light (>= 190), at cabin_fwd the runner AI Orange (hue 20-35 deg, saturation >= 0.6), "
          "ledges <= 80, walnut <= 90 (median sRGB luminance of each material's pixels)", ok, " | ".join(rows))
    r = await js(page, r"""
      const V = window.viewer, T = V.tour, out = {};
      const key = (type, code) => document.body.dispatchEvent(new KeyboardEvent(type, {code, key: code.slice(-1).toLowerCase(), bubbles: true}));
      const look = (deg, pitch = 0) => { const s = T.state(); T.look(deg - s.yawDeg, pitch - s.pitchDeg); };
      const R = (id) => V.tour.data.regions.find((g) => g.id === id);
      const p3 = R('seat_pax3');
      // NAV8-02: walking aft to PAX 3, D (real key events) into the seat: the view turns forward; released, the eye stays
      // at the seated eye; then A (into the side wall in the turned view) slides out, released, it ends on the centre line
      T.enter('cabin_aft', {motion: false}); T.finish(); look(0, -6);
      T.walk({f: 1}, (0.5 * (p3.x[0] + p3.x[1]) - T.state().pos[0]) / 1.0);
      key('keydown', 'KeyD'); V.advance(1.2); key('keyup', 'KeyD'); out.inHeld = T.state(); V.advance(1.0); out.inRel = T.state();
      key('keydown', 'KeyA'); V.advance(1.6); key('keyup', 'KeyA'); V.advance(1.0); out.out = T.state();
      // NAV8-03 / 04: cabin_fwd -> W into the gap between the crew seats -> D into the co-pilot seat
      T.go('cabin_fwd', {motion: false}); T.walk({f: 1}, 6); out.gapLabel = document.getElementById('tourStopLabel').textContent;
      key('keydown', 'KeyD'); V.advance(1.2); key('keyup', 'KeyD'); V.advance(0.8); await V.frames(1);
      out.cop = T.state(); out.copLabel = document.getElementById('tourStopLabel').textContent;
      out.checked = [...document.querySelectorAll('#tourMenu [aria-checked="true"]')].map((b) => b.dataset.stop);
      T.go('club', {motion: false}); await V.frames(1); out.stopLabel = document.getElementById('tourStopLabel').textContent;
      out.stopChecked = [...document.querySelectorAll('#tourMenu [aria-checked="true"]')].map((b) => b.dataset.stop);
      // NAV8-05: the airstair stop's heading on a portrait screen; the walk pad aside there
      T.go('airstair', {motion: false}); await V.frames(1);
      const TT = V._internals.tour, s = V.tour.data.stops.find((x) => x.id === 'airstair');
      Object.defineProperty(TT, 'portrait', {value: true, configurable: true}); out.airP = TT.stopAngles(s);
      delete TT.portrait; out.airL = TT.stopAngles(s);
      out.padAside = document.getElementById('tourPad').classList.contains('aside');
      T.go('club', {motion: false}); out.padAfter = document.getElementById('tourPad').classList.contains('aside');
      T.exit({motion: false}); await V.frames(1);
      return out;
    """)
    R = {x["id"]: x for x in data["regions"]}
    ih, ir, o = r["inHeld"], r["inRel"], r["out"]
    check("[T15] NAV8-02: a released sidestep stops at once (real key events): into PAX 3 the eye stays within 1 cm of the "
          "seated eye; out of the turned seat (A, into the side wall) it ends on the aisle's centre line",
          ih["region"] == "seat_pax3" and ir["region"] == "seat_pax3" and abs(ir["pos"][1] - R["seat_pax3"]["eye_bl"]) <= 0.01
          and o["region"] == "aisle" and abs(o["pos"][1]) < 0.02,
          f"in: {ih['region']} y {ih['pos'][1]:+.3f} -> released {ir['pos'][1]:+.3f} (eye_bl {R['seat_pax3']['eye_bl']:+.3f}); "
          f"out: {o['region']} y {o['pos'][1]:+.3f}")
    cp = r["cop"]
    want = R["seat_copilot"].get("pitch")
    check("[T16] NAV8-03: a walk into a crew seat turns to its stop's pitch (the panel and yoke framed, not the sky)",
          cp["region"] == "seat_copilot" and want is not None and want < -15 and abs(cp["pitchDeg"] - want) < 0.5,
          f"{cp['region']}, pitch {cp['pitchDeg']:.1f} (region pitch {want})")
    check("[T17] NAV8-04: the stop button follows the walk (the region's label, no menu stop marked) and names a stop at one",
          r["gapLabel"] == "Flight deck" and r["copLabel"] == "Co-pilot seat" and not r["checked"]
          and r["stopLabel"] == "Club seats" and r["stopChecked"] == ["club"],
          f"gap {r['gapLabel']!r}, walked into {r['copLabel']!r} (marked {r['checked']}), at a stop {r['stopLabel']!r} {r['stopChecked']}")
    import math as _m
    ap, al = r["airP"], r["airL"]
    s_air = next(x for x in data["stops"] if x["id"] == "airstair")
    check("[T18] NAV8-05: the airstair stop takes its own heading / pitch on a portrait screen; the walk pad moves aside "
          "there (and back elsewhere)",
          abs(_m.degrees(ap["yaw"]) - s_air["yaw_portrait"]) < 0.1 and abs(_m.degrees(ap["pitch"]) - s_air["pitch_portrait"]) < 0.1
          and abs(_m.degrees(al["yaw"]) - s_air["yaw_portrait"]) > 2 and r["padAside"] and not r["padAfter"],
          f"portrait {_m.degrees(ap['yaw']):.1f} / {_m.degrees(ap['pitch']):.1f}, landscape {_m.degrees(al['yaw']):.1f} / "
          f"{_m.degrees(al['pitch']):.1f}, pad aside {r['padAside']} -> {r['padAfter']}")


async def tour_phone_checks(page, ctx, shots=True):
    """[T10] phones: the entry is visible on load (not scrolled off the toolbar), the menu fits, inside the sheet folds
    away and the walk pad / hint show; one-finger drag looks, a pinch walks; exit re-opens the sheet."""
    await js(page, "window.viewer.select(null); window.viewer.tab('build'); window.viewer.panel(true); window.viewer.setCamera('three_quarter', {instant: true}); await new Promise(r => setTimeout(r, 400));")
    e = await js(page, r"""
      const b = document.getElementById('tourEnter'), r = b.getBoundingClientRect(), el = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return {box: [r.left, r.top, r.right, r.bottom], hit: b === el || b.contains(el), w: innerWidth, h: innerHeight};
    """)
    await js(page, "document.getElementById('tourEnter').click(); await window.viewer.frames(1);")
    m = await js(page, "const r = document.getElementById('tourMenu').getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom, document.getElementById('tourMenu').scrollHeight <= document.getElementById('tourMenu').clientHeight + 1];")
    if shots:
        await shot(page, "41_tour_phone_menu", "")
    await js(page, "document.querySelector('#tourMenu [data-stop=\"club\"]').click(); window.viewer.tour.finish(); await window.viewer.frames(2);")
    s = await js(page, r"""
      const V = window.viewer, q = (id) => document.getElementById(id), vis = (el) => !el.hidden && el.getBoundingClientRect().height > 0;
      const pad = [...q('tourPad').querySelectorAll('button')].map((b) => { const r = b.getBoundingClientRect(); return [r.width, r.height, r.bottom]; });
      const hint = q('tourHint').getBoundingClientRect(), sheet = q('panel').getBoundingClientRect();
      return {tour: V.state.tour, sheetOpen: q('app').classList.contains('panel-open'), pad, padVis: vis(q('tourPad')), hintVis: vis(q('tourHint')),
        hint: [hint.left, hint.right, hint.bottom], sheetTop: sheet.top, exitVis: vis(q('tourExit')), enterVis: vis(q('tourEnter'))};
    """)
    if shots:
        await shot(page, "42_tour_phone_club", "")
    cdp = await ctx.new_cdp_session(page)
    x, y = 200, 300
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
    for i in range(1, 6):
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x - 15 * i, "y": y}]})
        await page.wait_for_timeout(30)
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    await page.wait_for_timeout(150)
    dragged = await js(page, "return window.viewer.state.tour;")
    t1 = await js(page, "window.viewer.tour.go('cabin_aft', {motion: false}); return window.viewer.state.tour;")
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": 180, "y": 300, "id": 1}, {"x": 220, "y": 300, "id": 2}]})
    for i in range(1, 7):
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": 180 - 15 * i, "y": 300, "id": 1}, {"x": 220 + 15 * i, "y": 300, "id": 2}]})
        await page.wait_for_timeout(30)
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    await page.wait_for_timeout(700)
    t2 = await js(page, "await window.viewer.frames(2); return window.viewer.state.tour;")
    await js(page, "document.getElementById('tourExit').click(); window.viewer.tour.finish(); await window.viewer.frames(1);")
    after = await js(page, "return [window.viewer.state.tour.active, document.getElementById('app').classList.contains('panel-open'), window.viewer.state.cameraPreset];")
    yaw_moved = s["tour"]["stop"] == "club" and abs(dragged["yawDeg"] - s["tour"]["yawDeg"]) > 5 and dragged["pos"] == s["tour"]["pos"]
    ok = (e["hit"] and 0 <= e["box"][0] and e["box"][2] <= e["w"] and e["box"][3] - e["box"][1] >= 40
          and m[0] >= 0 and m[2] <= e["w"] and m[3] <= e["h"] and m[4]
          and s["tour"]["active"] and not s["sheetOpen"] and s["padVis"] and all(w >= 40 and h >= 40 for w, h, _ in s["pad"])
          and s["hintVis"] and s["hint"][0] >= 0 and s["hint"][1] <= e["w"] and s["hint"][2] <= s["sheetTop"]
          and max(b for _, _, b in s["pad"]) <= s["sheetTop"] and s["exitVis"] and not s["enterVis"]
          and yaw_moved and t2["pos"][0] > t1["pos"][0] + 0.1 and t2["outside"] < 1e-6 and after == [False, True, "three_quarter"])
    check("[T10] phone 390x844: 'Go inside' on screen at load (>= 40 px, not under the toolbar fade), the stop menu fits; "
          "inside: sheet folded, walk pad (>= 40 px) and hint above it; a finger drag looks, a pinch walks; Exit re-opens the sheet", ok,
          f"entry {[round(v) for v in e['box']]}, menu bottom {m[3]:.0f}/{e['h']}, pad {s['pad'][0][:2]}, hint {[round(v) for v in s['hint']]} "
          f"(sheet top {s['sheetTop']:.0f}), drag yaw {s['tour']['yawDeg']:.0f} -> {dragged['yawDeg']:.0f}, pinch x {t1['pos'][0]:.3f} -> "
          f"{t2['pos'][0]:.3f}, exit {after}")


async def tour_dark_check(page, shots=True):
    """[T11] dark theme: the cabin keeps the daylight studio and exposure inside (the dark studio left the headliner
    near black), and the theme's look comes back outside."""
    r = await js(page, r"""
      const V = window.viewer, st = V._internals.stage;
      V.panel(false); await new Promise(r => setTimeout(r, 300));
      const out0 = st.renderer.toneMappingExposure;
      V.tour.enter('cabin_fwd', {motion: false}); await V.frames(2);
      const S = await import(new URL('viewer/scene.js', location.href).href);
      return {dark: st.dark, out0, inside: st.renderer.toneMappingExposure, key: st.lookKey, ev: S.LOOK.interiorEV};
    """)
    med = None
    if shots:
        path = await shot(page, "43_tour_dark_cabin_fwd", "")
        med = lum_stats(path, (0, 60, VIEW["width"], VIEW["height"] - 60))[0]
    r2 = await js(page, "const V = window.viewer, st = V._internals.stage; V.tour.exit({motion: false}); await V.frames(2); return [st.renderer.toneMappingExposure, st.lookKey];")
    # inside: the light theme's exposure 1.9 lifted by LOOK.interiorEV (review r1 NAV1-04; 0.3 since review r4 NAV8-01)
    ok = (r["dark"] and r["key"] == "light" and abs(r["ev"] - 0.3) < 1e-9 and abs(r["inside"] - 1.9 * 2 ** r["ev"]) < 0.01
          and r2 == [r["out0"], "dark"] and (med is None or 70 <= med <= 215))
    check("[T11] dark theme: the cabin is lit with the daylight studio inside (exposure / grade), the dark look outside", ok,
          f"exposure {r['out0']} -> {r['inside']} -> {r2[0]}, grade {r['key']} -> {r2[1]}" + (f", median luminance {med:.0f}" if med is not None else ""))


# ----------------------------------------------------------------------------- blender cross-check
BLENDER_SCRIPT = r'''
import bpy, json, sys, math
import numpy as np
from mathutils import Matrix, Vector
args = json.load(open(sys.argv[sys.argv.index("--") + 1]))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=args["glb"])
bl = lambda p: Vector((p[0], -p[2], p[1]))          # glTF (Y up) -> Blender (Z up)
gl = lambda v: [v[0], v[2], -v[1]]
parts = {o["part"]: o for o in bpy.data.objects if "part" in o.keys()}
def part_of(o):
    while o is not None:
        if "part" in o.keys(): return o["part"]
        o = o.parent
boxes = {}
bpy.context.view_layer.update()
for o in bpy.data.objects:
    if o.type != "MESH": continue
    pid = part_of(o)
    n = len(o.data.vertices)
    co = np.empty(n * 3); o.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    M = np.array(o.matrix_world)
    w = co @ M[:3, :3].T + M[:3, 3]
    w = np.stack([w[:, 0], w[:, 2], -w[:, 1]], 1)
    lo, hi = w.min(0), w.max(0)
    if pid in boxes:
        boxes[pid] = [np.minimum(boxes[pid][0], lo).tolist(), np.maximum(boxes[pid][1], hi).tolist()]
    else:
        boxes[pid] = [lo.tolist(), hi.tolist()]
# a part's box includes its child parts (as the viewer's partWorldBox does)
parent = {pid: part_of(o.parent) for pid, o in parts.items()}
full = {pid: [list(b[0]), list(b[1])] for pid, b in boxes.items()}
for pid in boxes:
    q = parent.get(pid)
    while q is not None:
        f = full.setdefault(q, [list(boxes[pid][0]), list(boxes[pid][1])])
        f[0] = [min(a, b) for a, b in zip(f[0], boxes[pid][0])]
        f[1] = [max(a, b) for a, b in zip(f[1], boxes[pid][1])]
        q = parent.get(q)
rest = {pid: o.matrix_basis.copy() for pid, o in parts.items()}
out = {"boxes": full, "poses": {}}
for sc in args["scenarios"]:
    for pid, o in parts.items(): o.matrix_basis = rest[pid]
    for pid, (deg, off) in sc["pose"].items():
        o = parts[pid]
        axis = bl(o["pivot"]["axis"]).normalized()
        T = Matrix.Translation(rest[pid].to_translation() + bl(off))
        o.matrix_basis = T @ Matrix.Rotation(math.radians(deg), 4, axis)
    bpy.context.view_layer.update()
    out["poses"][sc["name"]] = [gl(parts[pid].matrix_world @ bl(p)) for pid, p in sc["points"]]

# ---- gear interference sweep (BVH triangle overlaps), posed independently from the pivot extras
from mathutils.bvhtree import BVHTree
sys.path.insert(0, args["root"])
from model.brace import solve_knee
m2g = lambda a: np.array([a[1], a[2], a[0]], float)
PV = {pid: dict(o["pivot"].to_dict() if hasattr(o["pivot"], "to_dict") else o["pivot"]) for pid, o in parts.items() if "pivot" in o.keys()}
meshes = {}
for o in bpy.data.objects:
    if o.type == "MESH": meshes.setdefault(part_of(o), []).append(o)
def reset():
    for pid, o in parts.items(): o.matrix_basis = rest[pid]
def setrot(pid, rad):
    o = parts[pid]
    o.matrix_basis = Matrix.Translation(rest[pid].to_translation()) @ Matrix.Rotation(rad, 4, bl(list(PV[pid]["axis"])).normalized())
def rotm(axis, ang):
    a = np.asarray(axis, float); a = a / np.linalg.norm(a)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * K @ K
def sang(u, v, n):
    n = n / np.linalg.norm(n); u = u - n * u.dot(n); v = v - n * v.dot(n)
    return math.atan2(n.dot(np.cross(u, v)), u.dot(v))
def pose_gear(gid, frac):
    pv = PV[gid]; th = math.radians(pv["retract"] * frac); setrot(gid, th)
    bid = {"gear_main_R": "brace_main_R", "gear_main_L": "brace_main_L", "gear_nose": "brace_nose"}[gid]
    up = PV[bid + "_up"]; A, B0, K0, bend = (m2g(up[k]) for k in ("A", "B0", "K0", "bend"))
    ax = np.array(up["axis"], float); go = np.array(pv["origin"], float)
    B = rotm(np.array(pv["axis"], float), th) @ (B0 - go) + go
    K = solve_knee(A, B, up["L1"], up["L2"], ax, bend)
    ua = sang(K0 - A, K - A, ax)
    setrot(bid + "_up", ua); setrot(bid + "_lo", sang(B0 - K0, B - K, ax) - ua)
def tree(pids):
    bpy.context.view_layer.update()
    V, F, off = [], [], 0
    for pid in pids:
        for o in meshes.get(pid, []):
            n = len(o.data.vertices); co = np.empty(n * 3); o.data.vertices.foreach_get("co", co)
            M = np.array(o.matrix_world); w = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
            o.data.calc_loop_triangles(); t = np.empty(len(o.data.loop_triangles) * 3, dtype=np.int32)
            o.data.loop_triangles.foreach_get("vertices", t)
            V.append(w); F.append(t.reshape(-1, 3) + off); off += n
    V = np.vstack(V); F = np.vstack(F)
    return BVHTree.FromPolygons([Vector(v) for v in V], [tuple(f) for f in F.tolist()], all_triangles=True)
def pairs(a, b): return len(tree(a).overlap(tree(b)))
NOSE = ["gear_nose", "brace_nose_up", "brace_nose_lo"]
res = {}
reset()
def door_frac(d, v):   # nose door at opening fraction v (pivot 'open' = closed -> open, geometry built at 'rest')
    setrot(d, math.radians(PV[d]["open"] * (v - PV[d].get("rest", 0.0))))
for d in ("gear_door_NR", "gear_door_NL"): door_frac(d, 1.0)
res["nose_doors_open_vs_nose_gear"] = []
for f in (0.0, 0.1, 0.2, 0.3, 0.5, 0.8, 1.0):
    pose_gear("gear_nose", f)
    res["nose_doors_open_vs_nose_gear"].append([f, pairs(["gear_door_NR"], NOSE), pairs(["gear_door_NL"], NOSE)])
reset()
res["gear_down_rest_doors"] = pairs(["gear_door_NR", "gear_door_NL"], NOSE)
pose_gear("gear_nose", 1.0)
res["nose_up_doors_closing"] = []
for v in (0.75, 0.5, 0.25, 0.0):
    for d in ("gear_door_NR", "gear_door_NL"): door_frac(d, v)
    res["nose_up_doors_closing"].append([v, pairs(["gear_door_NR", "gear_door_NL"], NOSE)])
reset()
for g in ("gear_main_R", "gear_main_L"): pose_gear(g, 1.0)
res["mains_up_vs_flaps"] = pairs(["gear_main_R", "gear_main_L"], ["flap_R", "flap_L", "flap_fairings"])
pose_gear("gear_nose", 1.0)
res["nose_up_vs_flight_deck"] = pairs(["gear_nose"], ["flight_deck"] + [k for k in parts if k.startswith(("yoke_",
                                                                                                      "pedal_"))])
reset()
out["interference"] = res
json.dump(out, open(args["out"], "w"))
'''


def blender_scenarios(ex):
    """Poses written straight from the pivot semantics (independent of the viewer's JS)."""
    fl = ex["flap_R"]["pivot"]
    tr = model_to_gl(fl["travel"])
    ail_R, ail_L = ex["aileron_R"]["pivot"]["range"][0], ex["aileron_L"]["pivot"]["range"][1]   # right roll: R up, L down
    gear = {k: ex[k]["pivot"]["retract"] for k in ("gear_main_R", "gear_main_L", "gear_nose")}
    return [
        {"name": "flaps40", "js": "V.setFlaps(40, {instant: true});",
         "pose": {"flap_R": [40, tr], "flap_L": [40, tr]}},
        {"name": "roll_right", "js": "V.setControls({roll: 1}, {instant: true});",
         "pose": {"aileron_R": [ail_R, [0, 0, 0]], "aileron_L": [ail_L, [0, 0, 0]],
                  "ail_tab_R": [-0.6 * ail_R, [0, 0, 0]], "ail_tab_L": [-0.6 * ail_L, [0, 0, 0]]}},
        {"name": "pull_trim_yaw", "js": "V.setControls({pitch: 1, stabTrim: -4, yaw: 1}, {instant: true});",
         "pose": {"elevator_R": [-20, [0, 0, 0]], "elevator_L": [-20, [0, 0, 0]], "stabilizer": [-4, [0, 0, 0]],
                  "rudder": [25, [0, 0, 0]]}},
        {"name": "gear_up_doors_open", "js": "V.setGear(1, {instant: true}); V.setDoor('airstair', 1, {instant: true}); V.setDoor('cargo', 1, {instant: true});",
         "pose": {**{k: [v, [0, 0, 0]] for k, v in gear.items()},
                  "door_airstair": [math.degrees(ex["door_airstair"]["pivot"]["open"]), [0, 0, 0]],
                  "door_cargo": [math.degrees(ex["door_cargo"]["pivot"]["open"]), [0, 0, 0]]}},
    ]


async def blender_check(page):
    py = os.environ.get("BLENDER_PYTHON", "/opt/venv-blender/bin/python")
    if not Path(py).exists():
        check("blender cross-check", False, f"{py} not found")
        return
    print("blender cross-check")
    ids = await js(page, "return window.viewer.parts();")
    ex = await js(page, "return Object.fromEntries(arg.map(id => [id, window.viewer.partExtras(id)]));", ids)
    scen = blender_scenarios(ex)
    # sample points: a trailing-edge / tip point on each posed part, in that part's local frame
    viewer_pts = {}
    for sc in scen:
        pids = list(sc["pose"].keys())
        res = await js(page, r"""
          const [pids, setup] = arg; const V = window.viewer; T.neutral();
          const loc = pids.map(id => { const b = T.box(id); return T.attach(id, [b.center[0], b.min[1] + 0.02, b.max[2] - 0.01]); });
          new Function('V', setup)(V);
          const w = pids.map((id, k) => T.world(id, loc[k]));
          T.neutral();
          return {loc, w};
        """, [pids, sc["js"]])
        sc["points"] = [[pid, res["loc"][k]] for k, pid in enumerate(pids)]
        viewer_pts[sc["name"]] = res["w"]
    boxes = await js(page, "T.neutral(); return Object.fromEntries(arg.map(id => [id, T.box(id)]));", ids)
    tmp = OUT / "blender"
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "check.py").write_text(BLENDER_SCRIPT)
    (tmp / "in.json").write_text(json.dumps({"glb": str(ROOT / "out" / "pc12.glb"), "scenarios": scen, "out": str(tmp / "out.json"), "root": str(ROOT)}))
    t0 = time.time()
    p = subprocess.run([py, str(tmp / "check.py"), "--", str(tmp / "in.json")], capture_output=True, text=True, timeout=600)
    if p.returncode != 0 or not (tmp / "out.json").exists():
        check("blender cross-check runs", False, (p.stderr or p.stdout)[-400:])
        return
    bo = json.loads((tmp / "out.json").read_text())
    worst, worst_id = 0.0, ""
    for pid in ids:
        if pid not in bo["boxes"]:
            continue
        a, b = boxes[pid], bo["boxes"][pid]
        e = max(max(abs(x - y) for x, y in zip(a["min"], b[0])), max(abs(x - y) for x, y in zip(a["max"], b[1])))
        if e > worst:
            worst, worst_id = e, pid
    check("blender: same part boxes as three.js (all parts)", worst < 1e-3 and len(bo["boxes"]) == len(ids),
          f"{len(bo['boxes'])} parts, max diff {worst*1000:.3f} mm ({worst_id}); import+pose {time.time()-t0:.1f} s")
    for sc in scen:
        errs = [norm(sub(a, b)) for a, b in zip(viewer_pts[sc["name"]], bo["poses"][sc["name"]])]
        check(f"blender: posed '{sc['name']}' matches viewer", max(errs) < 1e-3, f"max {max(errs)*1000:.3f} mm over {len(errs)} parts")
    # gear interference (GLB geometry, model/gear.py): KNOWN until the GLB is rebuilt with the fixes
    it = bo.get("interference", {})
    if it:
        rows = it["nose_doors_open_vs_nose_gear"]
        check("[F1] blender: open nose doors clear the nose gear + brace over the whole travel", all(a == 0 and b == 0 for _, a, b in rows),
              "tri pairs NR/NL at gear " + ", ".join(f"{f:.1f}: {a}/{b}" for f, a, b in rows), known=True)
        check("[F2] blender: rest pose (gear down, nose doors open): leg and brace clear the doors",
              it["gear_down_rest_doors"] == 0, f"{it['gear_down_rest_doors']} tri pairs", known=True)
        rows = it["nose_up_doors_closing"]
        check("[F2b] blender: gear up, nose doors closing: the doors clear the stowed gear + brace",
              all(n == 0 for _, n in rows), ", ".join(f"door {v:.2f}: {n}" for v, n in rows), known=True)
        check("[F3] blender: retracted mains clear the flaps / flap fairings (flaps 0)", it["mains_up_vs_flaps"] == 0,
              f"{it['mains_up_vs_flaps']} tri pairs", known=True)
        check("[F4] blender: retracted nose wheel clears the flight deck", it["nose_up_vs_flight_deck"] == 0,
              f"{it['nose_up_vs_flight_deck']} tri pairs", known=True)


# ----------------------------------------------------------------------------- phone + error path
async def iphone_chip_check(browser, base):
    """[GEO8-01] an iPhone (Safari: no navigator.deviceMemory) with a >= 1080 px wide screen is offered the full model."""
    ctx = await browser.new_context(viewport=PHONE, device_scale_factor=1, is_mobile=True, has_touch=True, reduced_motion="reduce",
                                    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
                                               "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1", **CTX)
    await ctx.add_init_script("""Object.defineProperty(Navigator.prototype, 'deviceMemory', {get: () => undefined});
      Object.defineProperty(screen, 'width', {get: () => 1170}); Object.defineProperty(screen, 'height', {get: () => 2532});""")
    page = await ctx.new_page()
    await page.goto(base)
    await page.wait_for_function("window.__ready === true", timeout=180000)
    r = await js(page, "return {mem: navigator.deviceMemory, shown: !document.getElementById('detailChip').hidden, "
                       "text: document.getElementById('detailChipText').textContent};")
    check("[GEO8-01] iPhone (no deviceMemory, 1170 px screen): the full-detail model is offered on the stage",
          r["mem"] is None and r["shown"] and "triangles" in r["text"], f"deviceMemory {r['mem']}, chip {r['shown']} {r['text']!r}")
    await ctx.close()


async def phone_checks(browser, base, shots=True):
    ctx = await browser.new_context(viewport=PHONE, device_scale_factor=1, is_mobile=True, has_touch=True, reduced_motion="reduce", **CTX)
    page = await ctx.new_page()
    errs, reqs = [], []
    page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("request", lambda r: reqs.append(r.url.split("?")[0].rsplit("/", 1)[-1]))
    await page.goto(base)
    await page.wait_for_function("window.__ready === true", timeout=180000)
    await page.evaluate(JS_HELPERS)
    # the light tier (model/build.py out/pc12_low.glb, PC12_RES=1) on phones, as the 512 px HDRI; its part cards count it
    glbs = sorted(u for u in reqs if u.endswith(".glb"))
    low = json.loads((ROOT / "out" / "pc12_meta.json").read_text())["stats"].get("low", {})
    spec = await js(page, "return document.getElementById('statsList').textContent;")
    check("phone: loads the light tier (pc12_low.glb) only, the Specs panel counts it", glbs == ["pc12_low.glb"]
          and bool(low) and f"{low.get('triangles', 0):,}" in spec,
          f"requested {glbs}, stats.low {low.get('triangles')} triangles")
    # review r2 RES2-03: a capable phone (deviceMemory >= 4: headless Chromium reports 8) is offered the full model on
    # the stage once; x keeps the light model, remembered
    chip = await js(page, r"""
      const c = document.getElementById('detailChip'), out = {shown: !c.hidden, text: document.getElementById('detailChipText').textContent};
      if (out.shown) { const b = c.getBoundingClientRect(), s = document.getElementById('panel').getBoundingClientRect();
        out.box = [b.left, b.right, b.bottom, s.top]; }
      document.getElementById('detailChipClose').click();
      out.after = c.hidden; out.stored = localStorage.getItem('pc12-detail'); localStorage.removeItem('pc12-detail');
      return out;
    """)
    check("[RES2-03] phone: the full-detail model offered once on the stage (chip above the sheet); x keeps the light model",
          chip["shown"] and "triangles" in chip["text"] and chip["after"] and chip["stored"] == "light"
          and chip["box"][0] >= 0 and chip["box"][1] <= PHONE["width"] and chip["box"][2] <= chip["box"][3] + 1,
          f"{chip['text']!r}, box {chip.get('box')}, after x: hidden {chip['after']}, stored {chip['stored']!r}")
    await fit_check(page, "phone 390x844 3/4")
    if shots:
        await shot(page, "28_phone_390x844", "")
        await shot(page, "29_phone_animate", "window.viewer.tab('animate');")
        await shot(page, "30_phone_drawings", "window.viewer.tab('drawings'); await new Promise(r => setTimeout(r, 800));")
        await js(page, "window.viewer.tab('build');")
    lay = await js(page, r"""
      const p = document.getElementById('panel').getBoundingClientRect(), tb = document.getElementById('toolbar').getBoundingClientRect();
      const bodyW = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth);
      const gut = parseFloat(getComputedStyle(document.getElementById('panelBody')).paddingLeft);
      return {bodyW, w: innerWidth, h: innerHeight, panelTop: p.top, panelW: p.width, tbRight: tb.right, gut};
    """)
    check("phone: no horizontal page scroll", lay["bodyW"] <= lay["w"], f"scrollWidth {lay['bodyW']} / {lay['w']}")
    check("phone: panel is a bottom sheet, 16 px gutters", lay["panelTop"] > lay["h"] * 0.4 and abs(lay["panelW"] - lay["w"]) < 1 and lay["gut"] == 16,
          f"sheet top {lay['panelTop']:.0f}px, width {lay['panelW']:.0f}px, gutter {lay['gut']}px")
    await phone_card_check(page)
    if shots:
        await shot(page, "30b_phone_selected_card", "")
    await touch_checks(page, ctx)
    await tour_phone_checks(page, ctx, shots)
    check("phone: no console errors", not errs, "; ".join(errs[:3]))
    await ctx.close()


async def touch_checks(page, ctx):
    """[M3] pixel ratio: a tap keeps it, a drag and its damped coast drop it, back after two still frames (one buffer
    resize per switch); [m4] 40 px touch targets; the sheet header toggles the sheet (tap, swipe)."""
    await js(page, "window.viewer.select(null); window.viewer.tab('build'); window.viewer.panel(true);")
    r = await js(page, r"""
      const st = window.viewer._internals.stage, R = st.renderer, q0 = st.quality, dpr0 = st.dpr, ss = R.setSize;
      let sizes = 0;
      R.setSize = function (...a) { sizes++; return ss.apply(this, a); };
      st.quality = {...q0, dprMax: 1.5, dprMove: 1};
      st.dpr = 1.5; st.tween = null; st.camMoving = false; st._still = 5;
      const seq = [], step = (k) => { st.applyQuality(); seq.push([k, st.dpr]); };
      st.interacting = true; st.dragged = false; step('tap down');
      st.interacting = false; step('tap up');
      st.interacting = true; st.dragged = true; step('drag');
      st.interacting = false; st.camMoving = true; step('coast'); step('coast');
      st.camMoving = false; step('still 1'); step('still 2');
      R.setSize = ss; st.quality = q0; st.dpr = dpr0; R.setPixelRatio(dpr0); st.needsRender = true;
      return {seq, sizes};
    """)
    want = [["tap down", 1.5], ["tap up", 1.5], ["drag", 1], ["coast", 1], ["coast", 1], ["still 1", 1], ["still 2", 1.5]]
    check("[M3] phone pixel ratio: tap keeps it; drag + coast at dprMove; back after 2 still frames, 1 resize per switch",
          r["seq"] == want and r["sizes"] == 2, f"{r['seq']}, setSize calls {r['sizes']}")
    # review CR1-01: on a 3x phone the still canvas goes up to the native ratio within the pixel budget (Auto 2.1 MP:
    # ~2.5x at 390 x 844) before any supersampling; the tier's ratio while the scene animates; PERF-3: phone Auto keeps
    # the 1024 / 256 shadow maps
    r = await js(page, r"""
      const st = window.viewer._internals.stage, P = st.picture, q0 = st.quality, pred = P.predicted, busy = st.busy, cap = P.framesCap,
        spx = P.stillPx;
      // Auto's measured state set aside (calibrated, no cut passes, the profile's own budget): SwiftShader's frame times
      // on the phone page (the light tier's 1.9M triangles) cut the still budget towards the floor -- Auto working, not
      // the ratio logic under test
      st.quality = {...q0, dprMax: 1.5, dprNative: 3, dprMove: 1}; P.predicted = true; P.framesCap = Infinity; P.stillPx = Infinity;
      const out = {still: P.stillDpr(), css: [st.size.w, st.size.h], px: P.pxBudget, profile: [P.device, P.mode], S: null,
        shadow: st.key.shadow.mapSize.x, contact: st.contact.size};
      st.dpr = 0; st._still = 5; st._busy = true; st.applyQuality(); out.busyDpr = st.dpr;
      st._busy = false; st.applyQuality(); out.stillDprSet = st.dpr; out.S = P._plan().S;
      st.quality = q0; P.predicted = pred; P.framesCap = cap; P.stillPx = spx; st._busy = busy; st.dpr = q0.dprMax; st.renderer.setPixelRatio(q0.dprMax); P.invalidate();
      st.needsRender = true;
      return out;
    """)
    css = r["css"][0] * r["css"][1]
    exp = max(1.5, min(3, math.floor(math.sqrt(r["px"] / css) * 20) / 20))
    check("[CR1-01 / PERF-3] phone 3x: still canvas at the native ratio within the budget (then 1x, no supersampling), "
          "1.5 while animating; Auto shadows 1024 / 256",
          r["profile"] == ["phone", "auto"] and abs(r["still"] - exp) < 1e-9 and r["still"] > 2.3 and r["stillDprSet"] == r["still"]
          and r["busyDpr"] == 1.5 and r["S"] == 1 and r["still"] ** 2 * css <= r["px"] * 1.0001
          and r["shadow"] == 1024 and r["contact"] == 256, str(r))
    # the controls' own events: a tap does not count as a drag, a moving finger does
    cdp = await ctx.new_cdp_session(page)
    x, y = 60, 330
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
    await page.wait_for_timeout(60)
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    await page.wait_for_timeout(150)
    tap = await js(page, "return window.viewer._internals.stage.dragged;")
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
    for i in range(1, 6):
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x + 12 * i, "y": y}]})
        await page.wait_for_timeout(30)
    await page.wait_for_timeout(100)
    drag = await js(page, "const st = window.viewer._internals.stage; return [st.dragged, st.interacting];")
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    check("[M3] OrbitControls: a tap is not a drag, a moving finger is", tap is False and drag == [True, True], f"tap dragged={tap}, drag {drag}")
    await js(page, "window.viewer.setCamera('three_quarter', {instant: true});")
    # touch targets in the Build and Animate tabs + toolbar
    small = []
    for tab in ("build", "animate", "drawings"):
        small += await js(page, r"""
          window.viewer.tab(arg); await window.viewer.frames(1);
          const els = [...document.querySelectorAll('#panel button, #toolbar button, #panel input[type=range], #panel a')]
            .filter((e) => e.offsetParent !== null && getComputedStyle(e).visibility !== 'hidden');
          return els.map((e) => { const r = e.getBoundingClientRect(), chip = !!e.closest('.chips') || e.id === 'sheetHandle' || e.type === 'range';
            return [arg + ':' + (e.id || e.textContent.trim().slice(0, 14)), Math.round(r.width), Math.round(r.height), chip]; })
            .filter(([, w, h, chip]) => h < (chip ? 32 : 40) || w < 24);
        """, tab)
    check("[m4] phone touch targets: buttons >= 40 px, chips / sliders / sheet handle >= 32 px", not small, str(small[:6]))
    # the sheet header: tap toggles, swipe down closes, swipe up opens
    await js(page, "window.viewer.tab('build');")
    is_open = "return document.getElementById('app').classList.contains('panel-open');"
    await page.click("#panel .brand h1", timeout=SHOT_TIMEOUT)
    t1 = await js(page, is_open)
    await page.click("#panel .brand h1", timeout=SHOT_TIMEOUT)
    t2 = await js(page, is_open)
    hy = await js(page, "const r = document.querySelector('#panel .brand h1').getBoundingClientRect(); return [r.left + 10, r.top + r.height / 2];")

    async def swipe(dy):
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": hy[0], "y": hy[1]}]})
        for i in range(1, 5):
            await cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": hy[0], "y": hy[1] + dy * i / 4}]})
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        await page.wait_for_timeout(450)
        return await js(page, is_open)
    s_down = await swipe(60)
    hy = await js(page, "const r = document.querySelector('#panel .brand h1').getBoundingClientRect(); return [r.left + 10, r.top + r.height / 2];")
    s_up = await swipe(-60)
    check("[m4] sheet header: tap toggles, swipe down closes, swipe up opens", (t1, t2, s_down, s_up) == (False, True, False, True),
          f"tap {t1}/{t2}, swipe down {s_down}, swipe up {s_up}")
    await js(page, "window.viewer.panel(true); await new Promise(r => setTimeout(r, 350));")


async def landscape_check(browser, base, shots=True):
    """[m3] phones in landscape: a 300 px side panel and a one-row toolbar leave the aircraft most of the screen."""
    ctx = await browser.new_context(viewport={"width": 844, "height": 390}, device_scale_factor=1, is_mobile=True, has_touch=True,
                                    reduced_motion="reduce", **CTX)
    page = await ctx.new_page()
    await page.goto(base)
    await page.wait_for_function("window.__ready === true", timeout=180000)
    await page.evaluate(JS_HELPERS)
    r = await js(page, r"""
      const p = document.getElementById('panel').getBoundingClientRect(), t = document.getElementById('toolbar').getBoundingClientRect();
      return {panelW: p.width, panelLeft: p.left, tbBottom: t.bottom, sheet: matchMedia('(max-width: 760px) and (min-height: 501px)').matches};
    """)
    free = (r["panelLeft"]) * (390 - r["tbBottom"]) / (844 * 390)
    check("[m3] landscape phone 844x390: side panel <= 300 px, one-row toolbar, free view >= 50 %",
          not r["sheet"] and r["panelW"] <= 300 and r["tbBottom"] <= 80 and free >= 0.5,
          f"panel {r['panelW']:.0f} px, toolbar bottom {r['tbBottom']:.0f} px, free {free:.0%} of the screen")
    await fit_check(page, "landscape phone 844x390 3/4")
    if shots:
        await shot(page, "30c_phone_landscape", "")
    # [m5] the Specs dimension table fits the ~275 px column (no sideways scroll)
    t = await js(page, r"""
      window.viewer.tab('specs'); await window.viewer.frames(1);
      const w = document.querySelector('#pane-specs .table-wrap');
      const r = [w.scrollWidth, w.clientWidth];
      window.viewer.tab('build');
      return r;
    """)
    check("[m5] landscape phone: the Specs dimension table fits its column", t[0] <= t[1], f"table {t[0]} px in {t[1]} px")
    # [m4] safe areas (viewport-fit=cover): iPhone landscape insets L47 R47 B21 keep the controls clear of the notch
    cdp = await ctx.new_cdp_session(page)
    try:
        await cdp.send("Emulation.setSafeAreaInsetsOverride", {"insets": {"left": 47, "right": 47, "bottom": 21}})
    except Exception as e:  # noqa: BLE001  (older Chromium)
        print(f"  skip safe-area check: {e}")
        await ctx.close()
        return
    r = await js(page, r"""
      await new Promise((r) => setTimeout(r, 400));
      const box = (e) => e.getBoundingClientRect(), W = innerWidth, H = innerHeight;
      // (shown controls only: the interior tour's inside buttons are hidden outside, with an empty box at 0, 0)
      const tb = [...document.querySelectorAll('#toolbar button, #toolbar input')].filter((e) => e.offsetParent !== null).map(box);
      // the tab row scrolls sideways: its box (not the tabs scrolled out of it) must clear the inset
      const pb = [...document.querySelectorAll('#panel .panel-head button, #tabs, #pane-build .build-controls button, #stepList')]
        .filter((e) => e.offsetParent !== null).map(box);
      const open = {tbLeft: Math.min(...tb.map((b) => b.left)), panelRight: Math.max(...pb.map((b) => b.right))};
      window.viewer.panel(false); await new Promise((r) => setTimeout(r, 450));
      const po = box(document.getElementById('panelOpen'));
      window.viewer.panel(true); await new Promise((r) => setTimeout(r, 450));
      window.viewer.setCamera('three_quarter', {instant: true}); await window.viewer.frames(1);
      const f = T.fit();
      return {...open, openRight: po.right, W, H, fitLeft: f.box[0], fitRight: f.box[1], free: f.free.x1};
    """)
    ok = r["tbLeft"] >= 47 and r["panelRight"] <= r["W"] - 47 and r["openRight"] <= r["W"] - 47 and r["fitLeft"] >= 47 - 2
    check("[m4] safe areas, landscape insets 47/47/21: toolbar, panel, 'Panel' button and the fitted aircraft clear of the notch", ok,
          f"toolbar left {r['tbLeft']:.0f}, panel controls right {r['panelRight']:.0f}, Panel button right {r['openRight']:.0f} "
          f"(limit {r['W'] - 47}), 3/4 view x {r['fitLeft']:.0f}..{r['fitRight']:.0f} (panel at {r['free']:.0f})")
    await ctx.close()


async def safe_area_portrait(browser, base):
    """[m4] portrait phone with a 34 px home-indicator inset: the collapsed sheet's tab row stays above it."""
    ctx = await browser.new_context(viewport=PHONE, device_scale_factor=1, is_mobile=True, has_touch=True, reduced_motion="reduce", **CTX)
    page = await ctx.new_page()
    await page.goto(base)
    await page.wait_for_function("window.__ready === true", timeout=180000)
    cdp = await ctx.new_cdp_session(page)
    try:
        await cdp.send("Emulation.setSafeAreaInsetsOverride", {"insets": {"top": 47, "bottom": 34}})
    except Exception as e:  # noqa: BLE001
        print(f"  skip safe-area check: {e}")
        await ctx.close()
        return
    r = await js(page, r"""
      window.viewer.panel(false); await new Promise((r) => setTimeout(r, 500));
      const tabs = document.getElementById('tabs').getBoundingClientRect(), tb = document.getElementById('toolbar');
      const first = tb.querySelector('button').getBoundingClientRect();
      window.viewer.panel(true); await new Promise((r) => setTimeout(r, 450));
      return {tabsBottom: tabs.bottom, tbTop: first.top, H: innerHeight};
    """)
    check("[m4] safe areas, portrait insets top 47 / bottom 34: toolbar below the notch, collapsed sheet's tabs above the home indicator",
          r["tabsBottom"] <= r["H"] - 34 and r["tbTop"] >= 47, f"tabs bottom {r['tabsBottom']:.0f} (limit {r['H'] - 34}), toolbar top {r['tbTop']:.0f}")
    await ctx.close()


def blue_median(png: bytes):
    """Median RGB of the livery-blue pixels of a screenshot (None without PIL)."""
    try:
        from PIL import Image
        import io
    except ImportError:
        return None
    im = Image.open(io.BytesIO(png)).convert("RGB")
    px = [p for p in im.getdata() if p[2] > p[0] + 40 and p[2] > p[1] + 15]
    if len(px) < 200:
        return None
    return [sorted(c)[len(c) // 2] for c in zip(*px)], len(px)


async def context_loss_check(page):
    """[M1] WebGL context lost (phones: backgrounded tab, GPU memory pressure) and restored: a note while it is lost,
    the viewer redraws on its own after the restore, with the environment and shadows rebuilt (same image)."""
    await js(page, "window.viewer.reset(); window.viewer.panel(false); await new Promise((r) => setTimeout(r, 350)); "
                   "window.viewer.setCamera('three_quarter', {instant: true}); await window.viewer.frames(3);")
    before = await page.screenshot(timeout=SHOT_TIMEOUT)
    r = await js(page, r"""
      const st = window.viewer._internals.stage, gl = st.renderer.getContext(), ext = gl.getExtension('WEBGL_lose_context');
      if (!ext) return {skip: true};
      ext.loseContext();
      await new Promise((r) => setTimeout(r, 500));
      const lost = [gl.isContextLost(), window.viewer.state.contextLost, !document.getElementById('glNote').hidden];
      const n0 = st.stats.renders;
      ext.restoreContext();
      // no input from here on: the viewer has to redraw by itself
      const t0 = performance.now();
      while (st.stats.renders === n0 && performance.now() - t0 < 60000) await new Promise((r) => setTimeout(r, 100));
      return {lost, redrawn: st.stats.renders > n0, ms: Math.round(performance.now() - t0), noteHidden: document.getElementById('glNote').hidden,
        env: st.envSource, restored: !gl.isContextLost()};
    """)
    if r.get("skip"):
        print("  skip context-loss check: no WEBGL_lose_context")
        return
    await js(page, "await window.viewer.frames(2);")
    after = await page.screenshot(timeout=SHOT_TIMEOUT)
    (OUT / "33_after_context_restore.png").write_bytes(after)
    await js(page, "window.viewer.panel(true); await new Promise((r) => setTimeout(r, 350));")
    b0, b1 = blue_median(before), blue_median(after)
    same = b0 is not None and b1 is not None and max(abs(x - y) for x, y in zip(b0[0], b1[0])) <= 4
    check("[M1] WebGL context loss: note while lost, redraws itself after the restore, same image (blue median)",
          all(r["lost"]) and r["redrawn"] and r["noteHidden"] and r["restored"] and (same or b0 is None),
          f"lost {r['lost']}, redrawn after {r['ms']} ms, env {r['env']}, blue median {b0 and b0[0]} -> {b1 and b1[0]}"
          + (f" ({b0[1]} / {b1[1]} px)" if b0 and b1 else ""))


async def loading_shot(browser, base):
    """Hold the GLB back for a moment and capture the loading screen (separate page)."""
    page = await browser.new_page(viewport=VIEW, reduced_motion="reduce", **CTX)

    async def slow_glb(route):
        await asyncio.sleep(2.0)
        try:
            await route.continue_()
        except Exception:
            pass
    await page.route("**/pc12.glb", slow_glb)
    await page.goto(base)
    await page.wait_for_selector("#loading", state="visible")
    await page.wait_for_timeout(300)
    await page.screenshot(path=str(OUT / "00_loading.png"), timeout=SHOT_TIMEOUT)
    print("  shot out/tmp/viewer/00_loading.png")
    await page.close()


async def dark_and_data(browser, base, shots=True):
    """Dark colour scheme (prefers-color-scheme) and re-hosting via ?data=<base>."""
    page = await browser.new_page(viewport=VIEW, color_scheme="dark", reduced_motion="reduce", **CTX)
    errs = []
    page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errs.append(str(e)))
    await page.goto(base + "&data=../out/&cam=side")
    await page.wait_for_function("window.__ready === true", timeout=180000)
    err = await page.evaluate("window.__error || ''")
    bg = await page.evaluate("getComputedStyle(document.body).backgroundColor")
    check("?data=<base> + dark theme load", not err and not errs and bg != "rgb(233, 236, 239)", f"body bg {bg}")
    if not err:
        await page.evaluate(JS_HELPERS)
        await fit_check(page, "dark 960x600 ?cam=side")
    if shots and not err:
        await shot(page, "31_dark_theme", "window.viewer.setCamera('three_quarter', {instant: true}); window.viewer.setCutaway(true);")
    if not err:
        await js(page, "window.viewer.setCutaway(false);")
        await tour_dark_check(page, shots)
    await page.close()


# ----------------------------------------------------------------------------- picture quality (web/viewer/picture.js)
PIC_VIEW = {"width": 480, "height": 320}     # small: SwiftShader renders each 2x supersampled frame in a few seconds
PIC_WAIT = r"""
  const P = window.viewer._internals.stage.picture, t0 = performance.now(), f0 = P.frame;
  while (P.frame < f0 + 2 && performance.now() - t0 < 60000) await new Promise((r) => setTimeout(r, 30));
  while (!P.state().done && performance.now() - t0 < 600000) await new Promise((r) => setTimeout(r, 200));
  return P.state();
"""


def image_shift(png_a: bytes, png_b: bytes, box):
    """Sub-pixel shift (dx, dy) of image b against a over box (x0, y0, x1, y1): the integer offset in -3..3 with the
    least mean absolute difference, refined by a parabola through its neighbours; None without PIL / numpy."""
    try:
        from PIL import Image
        import io
        import numpy as np
    except ImportError:
        return None
    a = np.asarray(Image.open(io.BytesIO(png_a)).convert("L"), float)
    b = np.asarray(Image.open(io.BytesIO(png_b)).convert("L"), float)
    x0, y0, x1, y1 = box

    def err(dx, dy):
        return float(np.abs(a[y0 + dy:y1 + dy, x0 + dx:x1 + dx] - b[y0:y1, x0:x1]).mean())
    e, bx, by = min((err(dx, dy), dx, dy) for dx in range(-3, 4) for dy in range(-3, 4))

    def sub(em, e0, ep):
        den = em - 2 * e0 + ep
        return 0.5 * (em - ep) / den if den > 1e-9 else 0.0
    return (bx + sub(err(bx - 1, by), e, err(bx + 1, by)), by + sub(err(bx, by - 1), e, err(bx, by + 1)), e)


async def picture_auto_check(page):
    """Picture quality, Auto on this page: the frame times it measured and what it chose; specular AA, PCSS ground
    shadow on a fitted shadow camera, the 1k studio HDRI, anisotropic filtering, MSAA on the canvas, no GL errors."""
    r = await js(page, r"""
      const I = window.viewer._internals, st = I.stage, P = st.picture, R = st.renderer, gl = R.getContext();
      const s = P.state(), sc = st.key.shadow.camera, chunk = I.THREE.ShaderChunk.lights_physical_fragment;
      const tex = [];
      I.model.root.traverse((o) => { const m = o.material; if (!m || Array.isArray(m)) return;
        for (const k of Object.keys(m)) { const t = m[k]; if (t && t.isTexture && !t.isDataTexture && !t.isRenderTargetTexture && !tex.includes(t)) tex.push(t); } });
      const ct = st.contact.rt.texture;
      return {s, specAA: chunk.includes('pcSpecAA') && !chunk.includes('geometryRoughness'),
        shadowType: R.shadowMap.type, pcf: I.THREE.PCFShadowMap, pcss: st.shadowPlane.material.defines,
        frustum: [sc.right - sc.left, sc.top - sc.bottom, sc.far - sc.near], envW: st.studioEnv && st.studioEnv.W,
        tex: tex.map((t) => [t.name, t.anisotropy, t.generateMipmaps, t.minFilter]), maxAniso: R.capabilities.getMaxAnisotropy(),
        contact: [ct.anisotropy, ct.generateMipmaps, st.contact.size], lmf: I.THREE.LinearMipmapLinearFilter,
        attrs: gl.getContextAttributes(), samples: gl.getParameter(gl.SAMPLES), glError: gl.getError()};
    """)
    s = r["s"]
    check("[PQ] Auto: measured the frame time and chose the still refinement for it (a slow software renderer: none)",
          s["mode"] == "auto" and s["adaptive"] and any(v is not None for k, v in s["cost"].items() if k != "idle") and len(s["events"]) >= 1
          and (s["N"] == 0) == any("no still refinement" in e["what"] or "no refinement" in e["what"] for e in s["events"]),
          f"costs {s['cost']}, vsync {s['vsync']} ms, passes {s['N']}, events {[e['what'] for e in s['events']]}")
    check("[PQ] specular anti-aliasing (normal-variance roughness) installed in three's physical shading",
          r["specAA"], "lights_physical_fragment patched" if r["specAA"] else "three's geometryRoughness still in place")
    fw, fh, fd = r["frustum"]
    check("[PQ] key-light shadow: PCSS on the ground, shadow camera fitted to the casters (< 21 m; was a 24.4 m square), 4096 map on desktop",
          r["shadowType"] == r["pcf"] and (r["pcss"] or {}).get("PC_PCSS_FILTER", 0) >= 16 and fw < 21 and fh < 21
          and s["shadowMap"] == 4096, f"frustum {fw:.1f} x {fh:.1f} x {fd:.1f} m, PCSS {r['pcss']}, map {s['shadowMap']}")
    check("[PQ] 1k studio HDRI on desktop (the 2k copy measured no sharper reflections: review CR1-06)", r["envW"] == 1024,
          f"env width {r['envW']}")
    bad = [t for t in r["tex"] if t[1] != r["maxAniso"] or not t[2] or t[3] != r["lmf"]]
    check("[PQ] textures: max anisotropy + trilinear mipmaps (page atlas, contact shadow)",
          r["tex"] and not bad and r["contact"][0] == r["maxAniso"] and r["contact"][1] and r["contact"][2] == 1024,
          f"{len(r['tex'])} textures at {r['maxAniso']}x {', '.join(t[0] or '?' for t in r['tex'])}; contact {r['contact']}; bad {bad}")
    check("[PQ] MSAA on the canvas (antialias, >= 4 samples)", r["attrs"]["antialias"] and r["samples"] >= 4,
          f"antialias {r['attrs']['antialias']}, SAMPLES {r['samples']}")
    check("[PQ] no GL errors", r["glError"] == 0, f"gl.getError() {r['glError']}")
    # review PERF-1: the calibration = the median of up to 3 drained plain frames (one over 3 s ends it), and passes cut
    # on a stall come back once plain frames fit the refresh (simulated: fast frame times injected, then put back)
    rc = await js(page, r"""
      const P = window.viewer._internals.stage.picture, keep = {cap: P.framesCap, px: P.stillPx, cut: P._cutAt, pc: P._predictCut,
        vs: P.vsync, direct: P.costs.direct.slice(), restored: P._restored, ev: P.events.length};
      const calib = P._calib.slice(), N0 = P.N;
      P.framesCap = 0; P._cutAt = -1e9; P.vsync = 16.7; P.costs.direct = [5, 6, 5, 7, 5];
      P._adapt('direct');
      const back = {N: P.N, frames: P.profile.frames, ev: P.events.slice(-1)[0]};
      P.framesCap = keep.cap; P.stillPx = keep.px; P._cutAt = keep.cut; P._predictCut = keep.pc; P.vsync = keep.vs;
      P.costs.direct = keep.direct; P._restored = keep.restored; P.events.length = keep.ev; P.invalidate();
      return {calib, N0, back, predicted: P.predicted};
    """)
    check("[PERF-1] Auto calibration: median of <= 3 drained plain frames; passes cut on a stall come back when frames fit the refresh",
          rc["predicted"] and 1 <= len(rc["calib"]) <= 3 and (len(rc["calib"]) == 3 or max(rc["calib"]) > 3000)
          and rc["back"]["N"] == rc["back"]["frames"] and "back on" in (rc["back"]["ev"] or {}).get("what", ""),
          f"calibration {rc['calib']} ms, passes {rc['N0']}; fast frames injected: passes {rc['back']['N']} / {rc['back']['frames']}, "
          f"{(rc['back']['ev'] or {}).get('what')}")


async def picture_checks(browser, base):
    """Picture quality (owner 2026-10-03 "sharper crisper picture"): the supersampled still path in High (a fixed mode),
    its render-target sizes within budget, MSAA samples, the release while moving, the same colours / no shift against
    the plain frame, moving supersampling and the no-MSAA canvas path, and the Specs panel setting remembered."""
    ctx = await browser.new_context(viewport=PIC_VIEW, device_scale_factor=1, reduced_motion="reduce", **CTX)
    page = await ctx.new_page()
    errs = []
    page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errs.append(str(e)))
    await page.goto(base + "&quality=high&ssframes=3", wait_until="domcontentloaded", timeout=300000)
    await page.wait_for_function("window.__ready === true", timeout=300000)
    await js(page, "window.viewer.panel(false); window.viewer.setCamera('three_quarter', {instant: true}); "
                   "await new Promise((r) => setTimeout(r, 400)); window.viewer.setCamera('three_quarter', {instant: true});")
    gl0 = await js(page, "return window.viewer._internals.stage.renderer.getContext().getError();")
    s = await js(page, PIC_WAIT)
    still_png = await page.screenshot(timeout=SHOT_TIMEOUT)
    (OUT / "34_picture_still_high.png").write_bytes(still_png)
    pl, rt, acc, cap = s["plan"], s["rt"] or {}, s["acc"] or {}, s["caps"]
    check("[PQ] still supersampling engages: 2x target, 3 jittered passes accumulated, at the canvas size",
          s["path"] == "still" and s["done"] and s["k"] == s["N"] == 3 and abs(pl["S"] - 2) < 1e-6
          and [rt.get("w"), rt.get("h")] == [2 * s["out"][0], 2 * s["out"][1]] and [acc.get("w"), acc.get("h")] == s["out"],
          f"path {s['path']}, k {s['k']}/{s['N']}, out {s['out']}, target {rt}, accumulation {acc}")
    check("[PQ] render target within budget: pixels, bytes, MAX_TEXTURE / RENDERBUFFER / VIEWPORT size",
          pl["w"] * pl["h"] <= s["budget"]["px"] and pl["bytes"] <= s["budget"]["mem"] and max(pl["w"], pl["h"]) <= cap["maxSize"],
          f"{pl['w']}x{pl['h']} = {pl['w'] * pl['h'] / 1e6:.2f} MP <= {s['budget']['px'] / 1e6:.1f} MP, {pl['bytes'] / 1e6:.0f} MB <= "
          f"{s['budget']['mem'] / 1e6:.0f} MB, max size {cap['maxSize']}")
    check("[PQ] MSAA in the supersampling target (2 samples at 2x, 4 below 1.5x; never above MAX_SAMPLES)",
          rt.get("samples") == min(2, cap["maxSamples"]) and cap["maxSamples"] >= 4 and cap["canvasSamples"] >= 4,
          f"target {rt.get('samples')} samples, MAX_SAMPLES {cap['maxSamples']}, canvas {cap['canvasSamples']}")
    # moving: the temporal AA path (the accumulation dropped, the history continues from the still image); still
    # again: it restarts and converges
    mv = await js(page, r"""
      const st = window.viewer._internals.stage, P = st.picture;
      st.interacting = true; st.dragged = true; st.needsRender = true;
      const t0 = performance.now();
      while (P.kind !== 'taa' && performance.now() - t0 < 120000) await new Promise((r) => setTimeout(r, 100));
      const during = P.state();
      return {path: during.path, valid: during.valid, k: during.k, dpr: st.dpr, taa: during.taa};
    """)
    move_png = await page.screenshot(timeout=SHOT_TIMEOUT)
    (OUT / "34b_picture_moving_high.png").write_bytes(move_png)
    s2 = await js(page, "const st = window.viewer._internals.stage; st.interacting = false; st.dragged = false; st.needsRender = true; " + PIC_WAIT)
    last = (mv["taa"] or {}).get("last") or {}
    check("[PQ] moving: temporal AA frames (the still accumulation dropped, the history seeded from the still image); "
          "still again: the accumulation restarts and converges",
          mv["path"] == "taa" and not mv["valid"] and last.get("seeded") and last.get("history")
          and s2["path"] in ("still", "shown") and s2["done"] and s2["k"] == 3,
          f"moving: path {mv['path']}, accumulation valid {mv['valid']}, taa {last}; still again: {s2['path']} {s2['k']}/{s2['N']}")
    b0, b1 = blue_median(move_png), blue_median(still_png)
    sh = image_shift(move_png, still_png, (20, 60, PIC_VIEW["width"] - 20, PIC_VIEW["height"] - 20))
    same = b0 and b1 and max(abs(x - y) for x, y in zip(b0[0], b1[0])) <= 3
    check("[PQ] the supersampled still keeps the plain frame's colours and position (no pop / shift on the switch)",
          bool(same) and (sh is None or math.hypot(sh[0], sh[1]) < 0.25),
          f"blue median {b0 and b0[0]} -> {b1 and b1[0]}, image shift "
          + ("n/a (no numpy)" if sh is None else f"({sh[0]:+.3f}, {sh[1]:+.3f}) px, mean |diff| {sh[2]:.2f}"))
    # the moving paths: a supersampled pass before the temporal blend (fast GPUs: one 1.5x pass, High's moveSS), the
    # temporal AA at the canvas size (its MSAA), without temporal AA a canvas without MSAA (through a multisampled target)
    # and the plain canvas; render targets, accumulation and history released once unused for 30 s (PERF-4); an
    # animation with the camera still (explode): one 2x pass per frame when it fits, no accumulation
    paths = await js(page, r"""
      const V = window.viewer, st = V._internals.stage, P = st.picture, out = {};
      const until = async (f) => { const t0 = performance.now(); while (!f() && performance.now() - t0 < 180000) await new Promise((r) => setTimeout(r, 100)); };
      P.moveSS = true; st.interacting = true; st.dragged = true; st.needsRender = true;
      await until(() => P.kind === 'movess'); out.movess = [P.kind, P.rt && P.rt.width, st.dpr, !!(P.taa.last && P.taa.last.ss)];
      P.moveSS = false; st.needsRender = true;
      await until(() => P.kind === 'taa'); out.taa = [P.kind, P.rt && P.rt.width, P.rt && P.rt.samples, !!(P.rt && P.rt.depthTexture)];
      P.allowTaa = false; P.caps.canvasSamples = 0; st.needsRender = true;
      await until(() => P.kind === 'rt'); out.rt = [P.kind, P.rt && P.rt.width, P.rt && P.rt.samples];
      P.caps.canvasSamples = 4; st.needsRender = true;
      await until(() => P.kind === 'move'); out.move = [P.kind];
      P.allowTaa = true;
      for (const t of P.pool) t._pcUsed = -1e9;
      P._used = {acc: -1e9, hist: -1e9, cur: -1e9}; P._gcAt = 0;
      const r0 = P.releases || 0; st.needsRender = true;
      await until(() => (P.releases || 0) > r0); out.release = [P.kind, P.pool.length, !!P.acc[0], (P.releases || 0) - r0];
      st.interacting = false; st.dragged = false;
      P.busySS = true; P.busyCool = Infinity; V.setExplode(0.4);
      await until(() => P.kind === 'busyss'); out.busy = [P.kind, P.rt && P.rt.width, st.busy, P.state().valid];
      P.busySS = false; V.setExplode(0, {instant: true});
      await until(() => !st.busy && P.kind !== 'busyss'); P.busyCool = 0;
      st.needsRender = true;
      return out;
    """)
    W = PIC_VIEW["width"]
    check("[PQ] moving paths: a 1.5x pass before the temporal blend, the temporal AA at the canvas size (MSAA, depth resolved), "
          "a no-MSAA canvas through a multisampled target; unused targets released; an explode animation: one 2x pass per frame",
          paths["movess"][0] == "movess" and paths["movess"][1] == round(1.5 * W) and paths["movess"][3]
          and paths["taa"][0] == "taa" and paths["taa"][1] == W and paths["taa"][2] >= 4 and paths["taa"][3]
          and paths["rt"][0] == "rt" and paths["rt"][1] == W and paths["rt"][2] >= 4 and paths["move"][0] == "move"
          and paths["release"][1] <= 1 and not paths["release"][2] and paths["release"][3] >= 1
          and paths["busy"][0] == "busyss" and paths["busy"][1] == 2 * W and paths["busy"][2] and not paths["busy"][3], str(paths))
    # still frames at 1x or 2x only (a fractional scale adds the target pixels' own box: CR1-04), the jitter within one
    # MSAA cell; the contact shadow at 512 while the scene animates, full size once still (PERF-4)
    sc = await js(page, r"""
      const st = window.viewer._internals.stage, P = st.picture, o = P._out(), keep = P.stillPx, out = {};
      P.stillPx = o.x * o.y * 2.25; out.s15 = P._plan().S; P.stillPx = o.x * o.y * 4; out.s2 = P._plan().S; P.stillPx = keep;
      st.busy = true; st.contactDirty = true; st.render(); out.busy = st.contact.shown;
      st.busy = false; out.dirty = st.contactDirty; st.render(); out.still = st.contact.shown;
      st.needsRender = true;
      return out;
    """)
    check("[CR1-04 / PERF-4] still scale 1x or 2x only (1.5x budget -> 1x); contact shadow 512 while animating, 1024 once still",
          sc["s15"] == 1 and sc["s2"] == 2 and sc["busy"] == 512 and sc["dirty"] and sc["still"] == 1024, str(sc))
    # the Specs panel setting, remembered across a reload (localStorage)
    await js(page, PIC_WAIT)
    ui = await js(page, r"""
      window.viewer.panel(true); window.viewer.tab('specs'); await window.viewer.frames(1);
      document.querySelector('#pictureSeg [data-picture="max"]').click();
      const P = window.viewer._internals.stage.picture;
      return {mode: P.mode, stored: localStorage.getItem('pc12-picture'), note: document.getElementById('pictureNote').textContent,
        pressed: [...document.querySelectorAll('#pictureSeg button')].map((b) => b.getAttribute('aria-pressed'))};
    """)
    gl1 = await js(page, "return window.viewer._internals.stage.renderer.getContext().getError();")
    await page.goto(base.replace("?", "?ssframes=1&") + "&tab=specs", wait_until="domcontentloaded", timeout=300000)
    await page.wait_for_function("window.__ready === true", timeout=300000)
    after = await js(page, r"""
      const P = window.viewer._internals.stage.picture, q = window.viewer.perf().quality;
      const out = {mode: P.mode, forced: P.forced, quality: q.picture, shadow: q.shadowMap,
        pressed: [...document.querySelectorAll('#pictureSeg button')].map((b) => b.getAttribute('aria-pressed'))};
      document.querySelector('#pictureSeg [data-picture="auto"]').click();
      out.back = [P.mode, localStorage.getItem('pc12-picture')];
      localStorage.removeItem('pc12-picture');
      return out;
    """)
    check("[PQ] 'Picture quality' setting: Max chosen in the Specs panel, remembered after a reload, back to Auto",
          ui["mode"] == "max" and ui["stored"] == "max" and ui["pressed"] == ["false", "false", "true"]
          and ("passes" in ui["note"] or "as drawn" in ui["note"]) and "MSAA" not in ui["note"]
          and after["mode"] == "max" and not after["forced"] and after["quality"] == "max" and after["pressed"] == ["false", "false", "true"]
          and after["back"] == ["auto", "auto"], f"click {ui}; reload {after}")
    check("[PQ] no GL errors in the supersampled paths", gl0 == 0 and gl1 == 0, f"gl.getError() {gl0} / {gl1}")
    check("[PQ] no console errors (picture quality page)", not errs, "; ".join(errs[:3]))
    await ctx.close()


PIC_RENDERED = r"""
  window.PQ = {
    st: () => window.viewer._internals.stage,
    P: () => window.viewer._internals.stage.picture,
    // n more renders, then two animation frames (the canvas presented)
    rendered: async (n = 1) => {
      const st = PQ.st(), r0 = st.stats.renders, t0 = performance.now();
      while (st.stats.renders < r0 + n && performance.now() - t0 < 600000) await new Promise((r) => setTimeout(r, 50));
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    },
    converge: async () => {
      const t0 = performance.now(), f0 = PQ.P().frame;
      // (two animation frames first: a camera change made before the call is seen by then)
      while (PQ.P().frame < f0 + 2) await new Promise((r) => setTimeout(r, 30));
      while (performance.now() - t0 < 1200000) { const s = PQ.P().state(); if (s.done && s.path !== 'none') break; await new Promise((r) => setTimeout(r, 100)); }
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      return PQ.P().state();
    },
    // the camera turned about the orbit centre (vertical axis), a frame due
    orbit: (deg) => {
      const V = window.viewer, st = PQ.st(), c = st.camera, t = st.controls.target.clone();
      const d = c.position.clone().sub(t); d.applyAxisAngle(new V._internals.THREE.Vector3(0, 1, 0), deg * Math.PI / 180);
      c.position.copy(t).add(d); c.lookAt(t); c.updateMatrixWorld(); st.needsRender = true;
    },
  };
"""


def png_array(png: bytes):
    try:
        from PIL import Image
        import io
        import numpy as np
    except ImportError:
        return None
    return np.asarray(Image.open(io.BytesIO(png)).convert("RGB"), float)


async def picture_motion_checks(browser, base):
    """[CR1-02] temporal anti-aliasing of moving frames: closer to the converged supersampled image than the plain 4x MSAA
    frame after the same orbit, the history continued from the still image, a cut resets it; [CR1-03] the spinning
    propeller with the camera still: the static scene refines (layered: still passes without the disc, then the disc
    drawn over the converged image every frame), consecutive frames differ only on the disc."""
    ctx = await browser.new_context(viewport=PIC_VIEW, device_scale_factor=1, reduced_motion="reduce", **CTX)
    page = await ctx.new_page()
    errs = []
    page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errs.append(str(e)))
    await page.goto(base + "&quality=high&ssframes=4", wait_until="domcontentloaded", timeout=300000)
    await page.wait_for_function("window.__ready === true", timeout=300000)
    await js(page, PIC_RENDERED + "window.viewer.panel(false); window.viewer.setCamera('three_quarter', {instant: true});")
    # the orbit: 8 moving frames of 0.15 deg from the converged still at A, ending at B; with temporal AA, then the same
    # from A again with it off (the plain 4x MSAA canvas frame); the reference: the converged still at B
    shots, kinds = {}, {}
    for mode in ("taa", "plain"):
        await js(page, "window.viewer.setCamera('three_quarter', {instant: true}); await PQ.converge();")
        kinds[mode] = await js(page, r"""
          const st = PQ.st(), P = PQ.P(), out = [];
          P.allowTaa = arg === 'taa';
          st.interacting = true; st.dragged = true;
          for (let i = 0; i < 8; i++) { PQ.orbit(0.15); await PQ.rendered(1); out.push([P.kind, P.taa.last && P.taa.last.history]); }
          return out;
        """, mode)
        shots[mode] = await page.screenshot(timeout=SHOT_TIMEOUT)
        (OUT / f"35_picture_orbit_{mode}.png").write_bytes(shots[mode])
        if mode == "taa":
            await js(page, "const st = PQ.st(); st.interacting = false; st.dragged = false; st.needsRender = true; await PQ.converge();")
            shots["ref"] = await page.screenshot(timeout=SHOT_TIMEOUT)
            (OUT / "35_picture_orbit_still.png").write_bytes(shots["ref"])
        await js(page, "const st = PQ.st(), P = PQ.P(); st.interacting = false; st.dragged = false; P.allowTaa = true; st.needsRender = true;")
    a = {k: png_array(v) for k, v in shots.items()}
    try:
        from scipy.ndimage import gaussian_filter
    except ImportError:
        gaussian_filter = None
    if a["ref"] is not None and gaussian_filter is not None:
        import numpy as np
        ref = a["ref"]
        # where the picture has detail (edges, panel lines, the livery): the reference's gradient in its top quarter
        g = np.abs(np.diff(ref.mean(axis=2), axis=1))[:-1, :] + np.abs(np.diff(ref.mean(axis=2), axis=0))[:, :-1]
        m = g > max(4.0, float(np.percentile(g, 75)))
        # the error at the scale of the artefacts (dotted gaps, stair-stepped edges, sparkle): both images through a
        # 0.7 px Gaussian, which leaves those and takes out the temporal blend's sub-pixel softness; raw for the record
        gb = lambda x: gaussian_filter(x, (0.7, 0.7, 0))
        err = {k: float(np.abs(gb(a[k]) - gb(ref))[:-1, :-1].mean(axis=2)[m].mean()) for k in ("taa", "plain")}
        raw = {k: round(float(np.abs(a[k] - ref)[:-1, :-1].mean(axis=2)[m].mean()), 2) for k in ("taa", "plain")}
        # the colours: medians over the paint's blue areas 2 px inside their edges (the edge pixels blend with their
        # light neighbours as much as each path's anti-aliasing softens them, which shifts a whole-mask median's red by
        # 3-4 / 255 without any pixel changing colour), pixels blue in both images
        from scipy.ndimage import binary_erosion
        blue = lambda x: x[..., 2] > x[..., 0] + 40
        core = binary_erosion(blue(ref), iterations=2)
        cols = {k: [round(float(np.median(a[k][..., c][core & blue(a[k])]))) for c in range(3)] for k in a}
    else:
        err, raw, cols = {"taa": None, "plain": None}, {}, {}
    ok_k = all(k == "taa" for k, _ in kinds["taa"]) and all(h for _, h in kinds["taa"]) and all(k == "move" for k, _ in kinds["plain"])
    check("[CR1-02] moving: temporal AA frames are closer to the converged supersampled image than the plain 4x MSAA frame "
          "after the same 8-frame orbit (edge pixels, at the artefacts' scale), same colours",
          ok_k and err["taa"] is not None and err["taa"] < 0.97 * err["plain"]
          and all(max(abs(x - y) for x, y in zip(cols[k], cols["ref"])) <= 3 for k in ("taa", "plain")),
          f"mean |diff| to the still on edges (0.7 px Gaussian): taa {err['taa'] and round(err['taa'], 2)}, plain "
          f"{err['plain'] and round(err['plain'], 2)} (raw {raw}); paths {kinds['taa'][-1]} / {kinds['plain'][-1]}; blue medians (2 px inside) {cols}")
    # a cut (a preset jump while 'moving') starts the history afresh
    cut = await js(page, r"""
      const st = PQ.st(), P = PQ.P(), c0 = P.taa.cuts;
      st.interacting = true; st.dragged = true; PQ.orbit(0.1); await PQ.rendered(1);
      window.viewer.setCamera('front', {instant: true}); st.needsRender = true; await PQ.rendered(1);
      const out = {cuts: P.taa.cuts - c0, last: P.taa.last, kind: P.kind};
      st.interacting = false; st.dragged = false; st.needsRender = true;
      return out;
    """)
    check("[CR1-02] a camera cut (preset jump) restarts the temporal history instead of smearing the old view",
          cut["kind"] == "taa" and cut["cuts"] >= 1, str(cut))
    # [CR1-03] the spinning propeller, camera still: still passes without the overlay, then the overlay alone per frame
    pr = await js(page, r"""
      const V = window.viewer, st = PQ.st(), P = PQ.P(), R = st.renderer, out = {kinds: []};
      V.setCamera({pos: [-4.2, 2.2, -2.2], target: [0, 1.6, 1.6], fov: 36}, {instant: true});
      await PQ.converge();
      V.setProp({rpm: 1700}, {instant: true});
      for (let i = 0; i < 16; i++) {
        await PQ.rendered(1);
        const s = P.state(); out.kinds.push([P.kind, s.k, s.layered, (st.overlay || []).length, s.N]);
        if (P.kind === 'layer') break;
      }
      out.calls = R.info.render.calls; out.tris = R.info.render.triangles;
      // the blur disc's screen box: its bounding sphere's box (world), projected
      const T = V._internals.THREE, disc = V._internals.kin.blur.disc, pts = [];
      disc.geometry.computeBoundingSphere();
      const sph = disc.geometry.boundingSphere.clone().applyMatrix4(disc.matrixWorld), r = sph.radius;
      for (const x of [-r, r]) for (const y of [-r, r]) for (const z of [-r, r]) {
        const p = sph.center.clone().add(new T.Vector3(x, y, z)).project(st.camera);
        pts.push([(p.x + 1) / 2 * st.size.w, (1 - p.y) / 2 * st.size.h]);
      }
      out.box = [Math.min(...pts.map((p) => p[0])), Math.min(...pts.map((p) => p[1])), Math.max(...pts.map((p) => p[0])), Math.max(...pts.map((p) => p[1]))];
      return out;
    """)
    pa = await page.screenshot(timeout=SHOT_TIMEOUT)
    await js(page, "await PQ.rendered(1);")
    pb = await page.screenshot(timeout=SHOT_TIMEOUT)
    (OUT / "36_picture_prop_layered.png").write_bytes(pa)
    ka, kb = png_array(pa), png_array(pb)
    if ka is not None:
        import numpy as np
        d = np.abs(ka - kb).max(axis=2)
        x0, y0, x1, y1 = (int(v) for v in pr["box"])
        out_mask = np.ones(d.shape, bool)
        out_mask[max(0, y0 - 4):max(0, y1 + 4), max(0, x0 - 4):max(0, x1 + 4)] = False
        outside, inside = float(d[out_mask].max()), float(d[~out_mask].max())
    else:
        outside = inside = None
    refined = [k for k in pr["kinds"] if k[0] == "still"]
    check("[CR1-03] spinning propeller, camera still: the static scene refines (still passes without the disc) and converges; "
          "then each frame draws only the disc over it (frames differ only on the propeller)",
          len(refined) >= 1 and all(k[2] for k in refined) and pr["kinds"][-1][0] == "layer" and pr["kinds"][-1][3] >= 2
          and pr["kinds"][-1][1] == pr["kinds"][-1][4] >= 2
          and pr["calls"] <= 12 and outside is not None and outside <= 2 and inside > 2,
          f"paths {pr['kinds']}, overlay draw calls {pr['calls']} ({pr['tris']} triangles); max |frame diff| outside the "
          f"propeller {outside}, on it {inside}")
    await js(page, "window.viewer.setProp({rpm: 0}, {instant: true}); PQ.st().needsRender = true;")
    gl = await js(page, "return window.viewer._internals.stage.renderer.getContext().getError();")
    check("[CR1-02 / 03] no GL / console errors (temporal AA, layered propeller)", gl == 0 and not errs, f"gl {gl}; " + "; ".join(errs[:3]))
    await ctx.close()


async def error_path(browser, base):
    page = await browser.new_page(viewport=VIEW, **CTX)
    await page.goto(base + "&glb=../out/does_not_exist.glb")
    await page.wait_for_function("window.__ready === true", timeout=60000)
    msg = await page.evaluate("[window.__error || '', getComputedStyle(document.getElementById('loading')).display, document.getElementById('loadMsg').textContent]")
    check("missing GLB: clear error on the loading screen", "Could not load" in msg[0] and "does_not_exist" in msg[2] and msg[1] != "none",
          msg[2].splitlines()[0] if msg[2] else "")
    await page.close()


async def boot_failures(pw, browser, base):
    """[M1] no endless 'Loading model…': a three.js module that fails to load, and a browser without WebGL."""
    page = await browser.new_page(viewport=VIEW, **CTX)

    async def abort(route):
        await route.abort()
    await page.route("**/build/three.module.min.js", abort)
    await page.goto(base)
    await page.wait_for_function("window.__ready === true", timeout=60000)
    r = await page.evaluate("[window.__error || '', getComputedStyle(document.getElementById('loadRetry')).display]")
    check("[M1] a three.js module that fails to load: error card with Retry", bool(r[0]) and ("viewer scripts" in r[0] or "CDN" in r[0])
          and r[1] != "none", r[0].splitlines()[0] if r[0] else "no error shown")
    await page.close()
    try:
        nogl = await launch(pw, ["--disable-webgl", "--disable-3d-apis"])
    except Exception as e:  # noqa: BLE001
        check("[M1] no WebGL 2: clear message, nothing downloaded", False, f"could not launch Chromium without WebGL: {e!r}")
        return
    page = await nogl.new_page(viewport=VIEW, **CTX)
    reqs = []
    page.on("request", lambda q: reqs.append(q.url))
    await page.goto(base)
    await page.wait_for_function("window.__ready === true", timeout=30000)
    msg = await page.evaluate("window.__error || ''")
    glb = [u for u in reqs if u.endswith(".glb") or u.endswith(".hdr")]
    check("[M1] no WebGL 2: clear message, nothing downloaded", "WebGL 2" in msg and not glb, (msg.splitlines() or [""])[0] + f"; {len(reqs)} requests")
    await nogl.close()


async def meshopt_check(browser, base, ref):
    """[M2] the packaged GLB (web/package.py: dequantize + gltf-transform meshopt) decodes to the same triangles."""
    sys.path.insert(0, str(ROOT / "web"))
    import package  # noqa: E402
    dst = OUT / "pc12_meshopt.glb"
    try:
        info = package.meshopt(ROOT / "out" / "pc12.glb", dst)
    except RuntimeError as e:
        if "not found" in str(e):
            print(f"  skip meshopt check: {e}")
            return
        check("[M2] meshopt GLB (web/package.py)", False, str(e)[:300])
        return
    page = await browser.new_page(viewport=VIEW, device_scale_factor=1, reduced_motion="reduce", **CTX)
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    await page.goto(base + "&glb=../out/tmp/viewer/pc12_meshopt.glb")
    await page.wait_for_function("window.__ready === true", timeout=180000)
    err = await page.evaluate("window.__error || ''")
    if err:
        check("[M2] meshopt GLB loads (MeshoptDecoder)", False, err)
        await page.close()
        return
    await page.evaluate(JS_HELPERS)
    geo = await js(page, "return T.geo();")
    worst, who = 0.0, ""
    for k, a in ref.items():
        b = geo.get(k)
        if b is None or b[6] != a[6]:
            worst, who = float("inf"), f"{k}: tris {a[6]} vs {b[6] if b else None}"
            break
        d = max(abs(x - y) for x, y in zip(a[:6], b[:6])) if a[6] else 0.0
        if d > worst:
            worst, who = d, k
    tris = sum(v[6] for v in geo.values())
    check("[M2] meshopt GLB: same parts and triangles, geometry within 0.05 mm",
          set(geo) == set(ref) and worst < 5e-5 and not errs,
          f"{info['bytes_in'] / 1048576:.1f} -> {info['bytes_out'] / 1048576:.1f} MB, {len(geo)} parts, {tris} tris, "
          f"worst {worst * 1000:.4f} mm ({who})" + (f"; {errs[:2]}" if errs else ""))
    await page.close()


# ----------------------------------------------------------------------------- engine sound (web/viewer/sound.js)
# counts AudioContext constructions (the page must not make one before the gesture that starts the engine)
AC_COUNTER = """(() => { window.__acCreated = 0;
  for (const k of ['AudioContext', 'webkitAudioContext']) { const A = window[k]; if (!A) continue;
    window[k] = class extends A { constructor(...a) { super(...a); window.__acCreated++; } }; } })();"""
# the offline render: start -> ground idle -> 1,700 rpm -> reverse -> fine -> feather -> shutdown (setProp arguments
# at t, s), heard from the 3/4 view at the default volume
SOUND_SCRIPT = [{"t": 0.5, "set": {"rpm": 1000}}, {"t": 16.0, "set": {"rpm": 1700}}, {"t": 23.0, "set": {"pitch": -38}},
                {"t": 28.0, "set": {"pitch": 0}}, {"t": 31.0, "set": {"pitch": 62}}, {"t": 35.0, "set": {"rpm": 0, "pitch": 62}}]
SOUND_SECONDS = 60.0
SOUND_EVENTS = ((0.5, "start"), (16, "1,700 rpm"), (23, "reverse"), (28, "fine"), (31, "feather"), (35, "shutdown"))
# steady segments of that render (s)
SOUND_SEGS = {"crank": (1.0, 2.2), "idle": (13.0, 16.0), "max": (19.5, 23.0), "rev": (25.5, 28.0), "feather": (33.5, 35.0),
              "stop": (45.0, 47.0)}
# extra renders from instant poses: the loudest state (reverse at 1,700 rpm, the camera 6 m from the hub in the plane of
# rotation, full volume), a steady 1,700 rpm (noise-loop repetition) and a start heard from the flight deck
LISTEN_CLOSE = {"d": 6, "cos": 0.0, "side": -0.9, "inside": False, "sta": 0.9, "door": 0}
LISTEN_PILOT = {"d": 3.8, "cos": -1, "side": 0, "inside": True, "sta": 4.5, "door": 0}
GR_FROM = 2.0     # s: the gain reduction counts from here (Chromium's compressor meters a decaying start-up value first)
SOUND_EXTRA = {
    "loudest": {"script": [{"t": 0, "set": {"rpm": 1700, "pitch": -38}, "instant": True}], "duration": 8,
                "listener": LISTEN_CLOSE, "volume": 1.0},
    "close_idle": {"script": [{"t": 0, "set": {"rpm": 1000, "pitch": 0}, "instant": True}], "duration": 8,
                   "listener": LISTEN_CLOSE},
    "steady": {"script": [{"t": 0, "set": {"rpm": 1700, "pitch": 0}, "instant": True}], "duration": 16},
    "pilot": {"script": [{"t": 0.5, "set": {"rpm": 1000}}], "duration": 16, "listener": LISTEN_PILOT},
}


def _wav(path: Path):
    import wave
    import numpy as np
    with wave.open(str(path)) as w:
        sr, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
        x = np.frombuffer(w.readframes(n), dtype="<i2").reshape(-1, ch).astype(np.float64) / 32768
    return sr, x


def _a_weight_db(f):
    import numpy as np
    f2 = f ** 2
    ra = 12194 ** 2 * f2 ** 2 / ((f2 + 20.6 ** 2) * np.sqrt((f2 + 107.7 ** 2) * (f2 + 737.9 ** 2)) * (f2 + 12194 ** 2))
    return 20 * np.log10(ra + 1e-20) + 2.0


def _kweight(x, sr):
    """ITU-R BS.1770-4 K-weighting (its 48 kHz coefficients; other rates resampled to 48 kHz first) of a (n, ch)
    signal; returns (y, 48000)"""
    from math import gcd
    from scipy import signal
    if sr != 48000:
        g = gcd(48000, sr)
        x = signal.resample_poly(x, 48000 // g, sr // g, axis=0)
    y = signal.lfilter([1.53512485958697, -2.69169618940638, 1.19839281085285], [1, -1.69065929318241, 0.73248077421585],
                       x, axis=0)
    return signal.lfilter([1, -2, 1], [1, -1.99004745483398, 0.99007225036621], y, axis=0), 48000


def loudness(x, sr, a=0.0, b=None, hp=None):
    """BS.1770 loudness (LUFS) of the stereo signal x (n, 2) over [a, b] s: gated integrated (400 ms blocks, 75 %
    overlap, -70 / -10 LU gates); hp: a 4th-order high-pass first (Hz: 250 = a small-speaker proxy)"""
    import numpy as np
    from scipy import signal
    s = x[int(a * sr):int(b * sr) if b else None]
    if hp:
        s = signal.sosfilt(signal.butter(4, hp, "hp", fs=sr, output="sos"), s, axis=0)
    y, fs = _kweight(s, sr)
    e = np.concatenate([[0], np.cumsum((y ** 2).sum(axis=1))])
    W, H = int(0.4 * fs), int(0.1 * fs)
    ends = np.arange(W, len(y) + 1, H)
    l = -0.691 + 10 * np.log10((e[ends] - e[ends - W]) / W + 1e-30)
    l = l[l > -70]
    if not len(l):
        return -99.0
    rel = -0.691 + 10 * math.log10(float((10 ** ((l + 0.691) / 10)).mean())) - 10
    l = l[l > rel]
    return -0.691 + 10 * math.log10(float((10 ** ((l + 0.691) / 10)).mean()))


def momentary(x, sr, hop=0.05):
    """BS.1770 momentary loudness (400 ms windows every hop s): (window end times, LUFS)"""
    import numpy as np
    y, fs = _kweight(x, sr)
    e = np.concatenate([[0], np.cumsum((y ** 2).sum(axis=1))])
    W, H = int(0.4 * fs), int(hop * fs)
    ends = np.arange(W, len(y) + 1, H)
    return ends / fs, -0.691 + 10 * np.log10((e[ends] - e[ends - W]) / W + 1e-30)


def sound_stats(m, sr, a, b, log=None):
    """One segment [a, b] s of a mono signal: rms dBFS, A-weighted level (dB, same reference), the A-weighted share
    above 2 kHz (dB), and -- with the state log -- the tonal share (blade-pass harmonics +- 2.5 bins, the whine and its
    2nd harmonic +- 6 bins, unweighted %) and the propeller band's envelope fluctuation (0.7-12 x blade pass,
    envelope < 30 Hz: std / mean)."""
    import numpy as np
    from scipy import signal
    s = m[int(a * sr):int(b * sr)]
    f, P = signal.welch(s, sr, nperseg=16384)
    df = f[1]
    PA = P * 10 ** (_a_weight_db(f) / 10)
    out = {"rms": 10 * math.log10(float((s * s).mean()) + 1e-24), "la": 10 * math.log10(float(PA.sum() * df) + 1e-24),
           "hi2k": 10 * math.log10(float(PA[f > 2000].sum() / max(PA.sum(), 1e-30)) + 1e-24)}
    if log:
        rows = [r for r in log if a <= r["t"] <= b]
        bpf = sum(r["bladeHz"] for r in rows) / len(rows)
        wh = rows[len(rows) // 2]["whineHz"]
        tone = np.zeros_like(P, bool)
        k = 1
        while bpf > 5 and k * bpf < sr / 2:
            tone |= np.abs(f - k * bpf) < 2.5 * df
            k += 1
        for o in (1, 2):
            tone |= np.abs(f - o * wh) < 6 * df
        out["tonal"] = 100 * float(P[tone].sum() / P.sum())
        if bpf > 20:
            sos = signal.butter(4, [0.7 * bpf, min(12 * bpf, 0.45 * sr)], "bandpass", fs=sr, output="sos")
            env = np.abs(signal.hilbert(signal.sosfilt(sos, s)))
            env = signal.sosfilt(signal.butter(2, 30, fs=sr, output="sos"), env)[sr // 2:]
            out["env"] = float(env.std() / env.mean())
    return out


def write_spectrogram(wav_path: Path, log: list, gr: list, png: Path) -> dict:
    """Spectrogram of the rendered WAV (log frequency) with the expected blade-pass harmonics (5 rpm / 60) and the
    whine (16 x Ng) from the state log overlaid, the level and the limiter's gain reduction below; returns the
    measured spectral peaks / levels for the checks."""
    import numpy as np
    from scipy import signal
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sr, x = _wav(wav_path)
    m = x.mean(axis=1)
    t = np.array([r["t"] for r in log])
    bp = np.array([r["bladeHz"] for r in log])
    wh = np.array([r["whineHz"] for r in log])
    f, tt, S = signal.spectrogram(m, sr, nperseg=8192, noverlap=8192 - 1024, window="hann", scaling="spectrum")
    db = 10 * np.log10(S + 1e-14)
    fig = plt.figure(figsize=(14, 10))
    gs = fig.add_gridspec(2, 2, height_ratios=[3, 1], width_ratios=[60, 1], hspace=0.12, wspace=0.03)
    ax, cax, ax1 = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, 0])
    pc = ax.pcolormesh(tt, f[1:], db[1:], shading="auto", cmap="magma", vmin=db.max() - 90, vmax=db.max())
    ax.set_yscale("log"); ax.set_ylim(20, 20000); ax.set_xlim(0, t[-1]); ax.set_ylabel("Hz")
    for k, ls in ((1, "-"), (2, "--"), (3, ":")):
        ax.plot(t, k * bp, color="cyan", lw=0.8, ls=ls, alpha=0.85, label=f"{k} x blade pass (5 x rpm / 60)")
    ax.plot(t, wh, color="lime", lw=0.8, alpha=0.85, label="compressor whine (16 x Ng)")
    ax.plot(t, 2 * wh, color="lime", lw=0.6, ls="--", alpha=0.6, label="2 x whine")
    lit = next((r["t"] for r in log if r.get("lit")), None)
    for tc, lab in SOUND_EVENTS + (((lit, "light-off"),) if lit else ()):
        ax.axvline(tc, color="w", lw=0.6, alpha=0.5); ax.text(tc + 0.2, 25, lab, color="w", fontsize=8)
    ax.legend(loc="upper right", fontsize=8)
    ax.set_title("PC-12 PRO viewer engine sound (web/viewer/sound.js, offline render of the live graph, 3/4 view, default volume)")
    fig.colorbar(pc, cax=cax, label="dB")
    hop = sr // 20
    rms = np.sqrt(np.convolve(m * m, np.ones(hop) / hop, mode="same"))[::hop]
    ax1.plot(np.arange(len(rms)) * hop / sr, 20 * np.log10(rms + 1e-9), color="k", lw=0.8, label="rms dBFS")
    g = np.array([v for v in gr if v[0] >= GR_FROM]) if gr else None
    if g is not None and len(g):      # (the compressor's start-up metering, < GR_FROM s, left out)
        ax1.plot(g[:, 0], g[:, 1] * 10 - 70, color="tab:red", lw=0.8, label="limiter gain reduction x 10 (dB, 0 at -70)")
    ax1.set_ylim(-80, 0); ax1.set_xlim(0, t[-1]); ax1.set_ylabel("dBFS"); ax1.set_xlabel("s")
    ax2 = ax1.twinx()
    ax2.plot(t, [r["rpm"] for r in log], color="tab:blue", lw=0.8, label="propeller rpm")
    ax2.plot(t, [r["ng"] * 17 for r in log], color="tab:green", lw=0.8, label="Ng % x 17")
    ax2.set_ylim(0, 1800); ax1.legend(loc="upper left", fontsize=8); ax2.legend(loc="upper right", fontsize=8)
    fig.savefig(png, dpi=90, bbox_inches="tight")
    plt.close(fig)

    def level(a, b):
        s = m[int(a * sr):int(b * sr)]
        return 20 * math.log10(math.sqrt(float((s * s).mean())) + 1e-12)

    def peak(a, b, lo, hi):
        s = m[int(a * sr):int(b * sr)]
        sp = np.abs(np.fft.rfft(s * np.hanning(len(s)), 1 << 20))
        fr = np.fft.rfftfreq(1 << 20, 1 / sr)
        k = (fr >= lo) & (fr <= hi)
        return float(fr[k][np.argmax(sp[k])])

    def expect(key, a, b):
        v = [r[key] for r in log if a <= r["t"] <= b]
        return sum(v) / len(v)

    seg = {k: sound_stats(m, sr, a, b, log) for k, (a, b) in SOUND_SEGS.items()}
    lo_t = lit if lit is not None else 3.0
    # BS.1770 per phase (the stereo signal), on a small-speaker proxy too; the momentary loudness through the start
    for k, (a_, b_) in SOUND_SEGS.items():
        seg[k]["lufs"] = loudness(x, sr, a_, b_)
        seg[k]["lufs_hp"] = loudness(x, sr, a_, b_, hp=250)
    tm, lm = momentary(x, sr)
    mom = lambda a_, b_: float(lm[(tm >= a_) & (tm <= b_)].max())        # noqa: E731
    start_m = {"onset": mom(SOUND_EVENTS[0][0] + 0.4, SOUND_EVENTS[0][0] + 0.8), "crank": mom(lo_t - 1.0, lo_t),
               "light": mom(lo_t, lo_t + 1.0), "after": float(lm[(tm >= lo_t + 2.0) & (tm <= lo_t + 2.5)].mean())}
    L, R = x[sr:, 0], x[sr:, 1]
    gr_after = [v for tg, v in gr if tg >= GR_FROM]
    I, M = SOUND_SEGS["idle"], SOUND_SEGS["max"]
    return {
        "peak": float(np.abs(x).max()), "pre": level(0.0, 0.45), "end": level(SOUND_SECONDS - 2, SOUND_SECONDS), "seg": seg,
        "lightoff": level(lo_t, lo_t + 0.5), "lit": lit, "gr": min(gr_after) if gr_after else 0.0,
        "corr": float(np.corrcoef(L, R)[0, 1]), "mom": start_m, "shoulder": 100 * float((np.abs(x[sr:]) > 0.7).mean()),
        "lufs_rd": loudness(x, sr, 7.0, 11.0),
        "bp_idle": (peak(*I, 50, 200), expect("bladeHz", *I)), "bp_max": (peak(*M, 50, 250), expect("bladeHz", *M)),
        "wh_idle": (peak(*I, 3000, 12000), expect("whineHz", *I)), "wh_max": (peak(*M, 3000, 12000), expect("whineHz", *M)),
        # the whine line through the start (sweeping ~650 Hz / s): measured peak vs the log in 0.4 s windows
        "wh_start": [(a, peak(a, a + 0.4, 0.8 * expect("whineHz", a, a + 0.4), 1.2 * expect("whineHz", a, a + 0.4)),
                      expect("whineHz", a, a + 0.4)) for a in (4, 6, 8, 10)],
    }


def loop_correlation(wav_path: Path, lags=(2.71, 3.23, 11.3, 13.7)) -> dict:
    """The noise loops must not repeat: the normalised correlation of a 0.5 s window of the 9-11 kHz band (the inlet
    hiss, broadband only) with the signal lag s later (+- 45 ms), for the old (2.71 / 3.23 s) and the new loop lengths."""
    import numpy as np
    from scipy import signal
    sr, x = _wav(wav_path)
    y = signal.sosfilt(signal.butter(6, (9000, 11000), "bandpass", fs=sr, output="sos"), x.mean(axis=1))
    a = y[int(1.5 * sr):int(2.0 * sr)]
    out = {}
    for lag in lags:
        i0 = int((1.5 + lag) * sr)
        seg = y[i0 - 2000:i0 + 2000 + len(a)]
        if len(seg) < len(a) + 4000:
            continue
        c = signal.correlate(seg, a, "valid", method="fft")
        cs = np.concatenate([[0], np.cumsum(seg ** 2)])
        e = np.sqrt((cs[len(a):] - cs[:-len(a)]) * float(np.dot(a, a)))
        out[lag] = float(np.abs(c / np.maximum(e, 1e-20)).max())
    return out


async def sound_checks(browser, base, out_dir: Path):
    """Engine / propeller sound (owner 2026-10-03, web/viewer/sound.js): no AudioContext before a user gesture, nor for
    a gesture with the engine off (an orbit drag); the gesture that starts the engine (a click on Idle) makes it; the
    graph follows the state (blade-passing frequency = 5 x rpm / 60, the whine rising with Ng through the start, the
    propeller still until light-off, reverse / feather levels); quieter and low-passed inside the cabin with the whine
    kept faintly (the flight deck louder than the aft cabin); M mutes the master gain; hidden page / engine off ->
    suspended; and offline renders through the same graph: start -> idle -> 1,700 -> reverse -> fine -> feather ->
    shutdown, written as a 16-bit WAV with its spectrogram (out_dir), its lines, levels (dBA), limiter, stereo and
    texture measured; the loudest state (6 m, reverse, full volume) for the limiter; a steady run for the noise loops;
    the start from the flight deck."""
    print("sound checks")
    ctx = await browser.new_context(viewport=VIEW, device_scale_factor=1, reduced_motion="reduce", **CTX)
    await ctx.add_init_script(AC_COUNTER)
    # iOS 17's navigator.audioSession (absent in Chromium): a stub, so the test sees what sound.js asks of it (SND8-01)
    await ctx.add_init_script("if (!navigator.audioSession) Object.defineProperty(navigator, 'audioSession', "
                              "{ value: { type: 'auto' }, configurable: true });")
    page = await ctx.new_page()
    errs = []
    page.on("console", lambda m: errs.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errs.append(f"pageerror: {e}"))
    await page.goto(base + "&sound=1")
    await page.wait_for_function("window.__ready === true", timeout=180000)
    S = "const V = window.viewer, S = V.sound; "
    # 1. no context before a gesture, even with sound on and the engine started from script
    r = await js(page, S + """
      V.pause(true);
      const s0 = S.state();
      V.setProp({rpm: 1000}); V.advance(1.0); const s1 = S.sync();     // (main.js setProp: no gesture)
      V.setProp({rpm: 0, pitch: 62}, {instant: true}); V.advance(0.05); S.sync();
      return {s0, s1, n: window.__acCreated, chip: !document.getElementById('soundChip').hidden};""")
    check("[sound] no AudioContext before a user gesture (sound on, engine started by script)",
          r["n"] == 0 and r["s0"]["ctx"] is None and r["s1"]["ctx"] is None and r["s0"]["on"] and not r["s0"]["gesture"]
          and r["s1"]["active"],
          f"{r['n']} contexts, engine {r['s1']['engine']['phase']} at {r['s1']['engine']['rpm']:.0f} rpm")
    # 2. gestures with the engine off (a tab click, an orbit drag on the canvas) open no audio device; the gesture that
    #    starts the engine -- the click on Idle -- creates one, running
    await page.click("#tab-animate")
    box = await page.locator("canvas").first.bounding_box()
    cx, cy = box["x"] + box["width"] * 0.4, box["y"] + box["height"] * 0.5
    await page.mouse.move(cx, cy); await page.mouse.down(); await page.mouse.move(cx + 60, cy + 10, steps=4); await page.mouse.up()
    await page.wait_for_timeout(300)
    r1 = await js(page, S + "V.advance(0.05); return {n: window.__acCreated, s: S.sync()};")
    await page.click('[data-rpm="1000"]')
    r2 = await js(page, S + "V.advance(0.1); return {n: window.__acCreated, s: S.sync(), rpmCmd: V._internals.kin.t.rpm, pressed: [...document.querySelectorAll('#aSound, #soundChip')].map((b) => b.getAttribute('aria-pressed')), chip: !document.getElementById('soundChip').hidden, session: navigator.audioSession.type};")
    check("[sound] iOS audio session 'playback' once the engine sound starts (the silent switch does not mute it; SND8-01)",
          r2["session"] == "playback", f"navigator.audioSession.type {r2['session']!r} after the Idle click")
    check("[sound] no AudioContext for gestures with the engine off (tab click, orbit drag); the click on Idle makes one (running)",
          r1["n"] == 0 and r1["s"]["ctx"] is None and r1["s"]["gesture"] and r2["n"] == 1 and r2["s"]["graph"]
          and r2["s"]["ctx"] == "running" and r2["rpmCmd"] == 1000 and r2["s"]["engine"]["phase"] == "start" and r2["s"]["active"]
          and r2["pressed"] == ["true", "true"] and r2["chip"],
          f"after the tab click + drag: {r1['n']} ({r1['s']['ctx']}); after Idle: {r2['n']}, {r2['s']['ctx']}, {r2['rpmCmd']} rpm "
          f"commanded, phase {r2['s']['engine']['phase']}, pressed {r2['pressed']}, chip {r2['chip']}")
    # 3. the start: the whine pitch (16 x Ng) rises, light-off, the propeller still until then, the blade-passing tone =
    #    5 x rpm / 60 throughout
    r = await js(page, S + """
      const rows = [];
      for (let i = 0; i < 64; i++) { V.advance(0.25); const s = S.sync(), e = s.engine, p = s.targets;
        rows.push({t: e.t, rpm: e.rpm, ng: e.ng, phase: e.phase, lit: e.lit, light: e.light, comb: e.comb, whine: p.whineHz,
          blade: p.bladeHz, prop: p.prop, w1: p.whine1, starter: p.starter, tick: p.tick, shots: s.shots}); }
      return rows;""")
    start = [x for x in r if x["phase"] == "start"]
    mono = all(b["whine"] >= a["whine"] - 1e-6 for a, b in zip(start, start[1:]))
    lo = next((x for x in r if x["light"] > 0.3), None)
    idle = r[-1]
    check("[sound] start: the whine pitch rises with Ng (monotonic) to ~6 kHz at ground idle; light-off 1.5-4 s, its one-shot "
          "played once; starter + igniters",
          mono and len(start) > 20 and start[0]["whine"] < 2000 and abs(idle["whine"] - 16 * 0.6 * 37468 / 60) < 0.02 * 6000
          and lo is not None and 1.5 <= lo["t"] <= 4 and start[2]["starter"] > 0 and start[2]["tick"] > 0 and idle["starter"] == 0
          and r[0]["shots"] == 0 and idle["shots"] == 1,
          f"whine {start[0]['whine']:.0f} -> {idle['whine']:.0f} Hz over {len(start)} samples, light-off at {lo['t'] if lo else -1:.2f} s "
          f"(one-shots {r[0]['shots']} -> {idle['shots']}), idle Ng {idle['ng']:.1f} % / {idle['rpm']:.0f} rpm at {idle['t']:.1f} s")
    pre = [x for x in r if not x["lit"]]
    lit0 = next((x["t"] for x in r if x["lit"]), 99)
    after = next((x for x in r if x["t"] >= lit0 + 2.0), None)
    check("[sound] the propeller stays still until light-off (free turbine: <= 5 rpm creep), then accelerates (> 100 rpm 2 s later)",
          pre and max(x["rpm"] for x in pre) <= 5 and after is not None and after["rpm"] > 100,
          f"max {max((x['rpm'] for x in pre), default=-1):.1f} rpm before light-off at {lit0:.2f} s, "
          f"{after['rpm'] if after else -1:.0f} rpm at {after['t'] if after else -1:.2f} s")
    bad = [x for x in r if abs(x["blade"] - 5 * x["rpm"] / 60) > 0.01 * max(5 * x["rpm"] / 60, 1e-3)]
    check("[sound] blade-passing target = 5 x rpm / 60 at every step of the start", not bad and idle["prop"] > 0.02,
          f"{len(r) - len(bad)}/{len(r)} within 1 %, idle prop level {idle['prop']:.3f}")

    async def settle(body):
        """run body (JS), let the AudioParams settle in real time (tau 0.05 / 0.12 s), return the sound state"""
        await js(page, S + body + " S.sync();")
        await page.wait_for_timeout(900)
        return await js(page, S + "return S.sync();")
    # 4. steady idle / 1,700 rpm: the live AudioParam = 5 x rpm / 60 within 1 %
    si = await settle("V.advance(3);")
    sm = await settle("V.setProp({rpm: 1700}); V.advance(6);")
    ok = []
    for s in (si, sm):
        want = 5 * s["engine"]["rpm"] / 60
        ok.append((s["values"]["bladeHz"], want, abs(s["values"]["bladeHz"] - want) <= 0.01 * want))
    check("[sound] blade-passing AudioParam = 5 x rpm / 60 within 1 % (idle, 1,700 rpm)", all(o[2] for o in ok) and abs(ok[1][1] - 141.67) < 0.5,
          ", ".join(f"{v:.2f} / {w:.2f} Hz" for v, w, _ in ok))
    check("[sound] 1,700 rpm: louder and higher than idle (prop level, whine pitch, Ng)",
          sm["targets"]["prop"] > 2 * si["targets"]["prop"] and sm["targets"]["whineHz"] > si["targets"]["whineHz"] * 1.25
          and sm["engine"]["ng"] > 80,
          f"prop {si['targets']['prop']:.3f} -> {sm['targets']['prop']:.3f}, whine {si['targets']['whineHz']:.0f} -> "
          f"{sm['targets']['whineHz']:.0f} Hz, Ng {si['engine']['ng']:.1f} -> {sm['engine']['ng']:.1f} %")
    # 5. blade pitch: reverse = the growl + rasp and a louder propeller, more of it broadband; feather quiet
    sr_ = await settle("V.setProp({pitch: -38}); V.advance(4);")
    sf = await settle("V.setProp({pitch: 62}); V.advance(4);")
    tot = lambda t: math.sqrt(sum(t[k] ** 2 for k in ("prop", "fund", "swish", "growl", "rasp")))  # noqa: E731
    check("[sound] reverse (-38 deg): growl + rasp on, the propeller louder (tone + broadband); feather (62 deg): the prop < 40 % of fine pitch",
          sr_["targets"]["growl"] > 0.05 and sr_["targets"]["rasp"] > 0.05 and tot(sr_["targets"]) > 1.4 * tot(sm["targets"])
          and sm["targets"]["growl"] == 0 and sm["targets"]["rasp"] == 0 and sf["targets"]["prop"] < 0.4 * sm["targets"]["prop"]
          and sf["engine"]["rpm"] > 1690,
          f"propeller total fine {tot(sm['targets']):.3f}, reverse {tot(sr_['targets']):.3f} (growl {sr_['targets']['growl']:.3f}, "
          f"rasp {sr_['targets']['rasp']:.3f}), feather tone {sf['targets']['prop']:.3f} vs {sm['targets']['prop']:.3f}")
    # 6. inside: quieter and low-passed with the whine's high band kept faintly, the flight deck louder than the aft cabin
    so = await settle("V.setProp({pitch: 0}); V.advance(3); V.setCamera('three_quarter', {instant: true});")
    sp = await settle("V.tour.enter('pilot', {motion: false}); V.tour.finish(); V.advance(0.1);")
    sa = await settle("V.tour.go('cabin_fwd', {motion: false}); V.tour.finish(); V.advance(0.1);")   # the aisle's aft end
    await js(page, S + "V.tour.exit({motion: false}); V.tour.finish(); V.advance(0.1); S.sync();")
    L = lambda s: (s["targets"]["gain"], s["targets"]["lpIn"], s["values"]["gain"], s["listener"]["inside"], s["targets"]["hiIn"],  # noqa: E731
                   s["targets"]["wetIn"])
    check("[sound] inside: quieter + low-passed, the whine band ~-20 dB, cabin room (flight deck < 3/4 view, aft cabin < flight deck)",
          not L(so)[3] and L(sp)[3] and L(sa)[3] and L(sp)[0] < L(so)[0] and L(sa)[0] < L(sp)[0] and L(sp)[1] <= 1500
          and L(sa)[1] < L(sp)[1] and L(so)[1] >= 15000 and abs(L(sa)[2] - L(sa)[0]) < 0.05 * L(sa)[0]
          and L(so)[4] == 0 and 0.05 <= L(sp)[4] <= 0.2 and L(sp)[5] == 1 and L(so)[5] == 0,
          f"gain / low-pass / whine band: 3/4 view {L(so)[0]:.2f} / {L(so)[1]:.0f} Hz / {L(so)[4]:.2f}, pilot {L(sp)[0]:.2f} / "
          f"{L(sp)[1]:.0f} Hz / {L(sp)[4]:.2f}, aft cabin {L(sa)[0]:.2f} / {L(sa)[1]:.0f} Hz / {L(sa)[4]:.2f}")
    # 7. M mutes the master gain (then the context suspends); M again restores it; the choice is stored
    await page.keyboard.press("m")
    await page.wait_for_timeout(1000)
    m1 = await js(page, S + "return {s: S.state(), store: localStorage.getItem('pc12.viewer.sound'), pressed: document.getElementById('aSound').getAttribute('aria-pressed')};")
    await page.keyboard.press("m")
    await page.wait_for_timeout(900)
    m2 = await js(page, S + "return {s: S.sync(), store: localStorage.getItem('pc12.viewer.sound')};")
    want_master = m2["s"]["level"] * m2["s"]["volume"] ** 2
    check("[sound] M mutes: master gain -> 0 (context then suspended), stored 'off', aria-pressed false; M again: on (level x volume^2)",
          not m1["s"]["on"] and m1["s"]["set"]["master"] == 0 and m1["s"]["values"]["master"] < 1e-3 and m1["s"]["ctx"] == "suspended"
          and m1["store"] == "off" and m1["pressed"] == "false" and m2["s"]["on"] and m2["store"] == "on" and m2["s"]["ctx"] == "running"
          and abs(m2["s"]["set"]["master"] - want_master) < 1e-6 and want_master > 0,
          f"muted: master {m1['s']['values']['master']:.4f} ({m1['s']['ctx']}); on again: master target {m2['s']['set']['master']:.3f} "
          f"= {want_master:.3f} ({m2['s']['ctx']})")
    # 8. the page hidden -> suspended; visible again -> running
    h = await js(page, S + """
      const def = (k, v) => Object.defineProperty(document, k, {configurable: true, get: () => v});
      def('hidden', true); def('visibilityState', 'hidden'); document.dispatchEvent(new Event('visibilitychange'));
      await new Promise((r) => setTimeout(r, 400)); const hid = S.state().ctx;
      delete document.hidden; delete document.visibilityState; document.dispatchEvent(new Event('visibilitychange'));
      await new Promise((r) => setTimeout(r, 600)); return [hid, S.sync().ctx];""")
    check("[sound] page hidden -> context suspended, visible -> running", h == ["suspended", "running"], str(h))
    # 9. shutdown: every source fades out, the chip hides, the context suspends once the engine has stopped
    sd = await js(page, S + "V.setProp({rpm: 0, pitch: 62}); V.advance(30); return S.sync();")
    lv = {k: sd["targets"][k] for k in ("prop", "fund", "swish", "growl", "rasp", "whine1", "whine2", "whine3", "whine4", "hay",
                                         "hum", "roar", "hiss", "starter", "tick", "whoomp")}
    for _ in range(40):                    # the idle suspend runs on a timer (~2.5 s after the engine has stopped)
        await page.wait_for_timeout(250)
        sd2 = await js(page, S + "return S.state();")
        if sd2["ctx"] == "suspended":
            break
    check("[sound] shutdown: no sound once stopped (every level 0), chip hidden, context suspended",
          max(lv.values()) < 1e-6 and not sd["active"] and sd2["chip"] is False and sd2["ctx"] == "suspended",
          f"max level {max(lv.values()):.2e}, ctx {sd2['ctx']}")
    # 10. the offline renders (the same EngineVoice / engineParams; Kinematics stepped at 60 Hz)
    out_dir.mkdir(parents=True, exist_ok=True)
    import base64

    async def render(o):
        t0 = time.time()
        rr = await js(page, S + "V.setProp({rpm: 0, pitch: 62, angle: 0}, {instant: true}); return await S.render(arg);", o)
        rr["took"] = time.time() - t0
        return rr
    rr = await render({"script": SOUND_SCRIPT, "duration": SOUND_SECONDS})
    wav = out_dir / "pc12_engine_sequence.wav"
    wav.write_bytes(base64.b64decode(rr["wav"]))
    (out_dir / "pc12_engine_sequence_log.json").write_text(json.dumps(rr["log"]))
    png = out_dir / "spectrogram.png"
    a = write_spectrogram(wav, rr["log"], rr["gr"], png)
    print(f"  wav {wav} ({rr['seconds']:.0f} s, {rr['sampleRate']} Hz, {rr['channels']} ch, rendered in {rr['took']:.1f} s), spectrogram {png}")
    sg = a["seg"]
    check("[sound] offline render: 16-bit WAV, peaks < 0.96 (the output curve's ceiling 0.95), silent before the start and after the run-down",
          a["peak"] < 0.96 and a["pre"] < -90 and a["end"] < -90 and wav.stat().st_size > 44 + 2 * 2 * 44100 * 50,
          f"peak {a['peak']:.3f}, rms before {a['pre']:.0f} / end {a['end']:.0f} dBFS")
    # SR2-01: the default listening level (BS.1770, the 3/4 view, volume 1.0) and the start heard
    lu = {k: sg[k]["lufs"] for k in sg}
    mo = a["mom"]
    check("[sound] default listening level (BS.1770, 3/4 view, volume 1.0): ground idle -27 .. -22 LUFS, 1,700 rpm -18 .. -13, "
          "reverse -14 .. -10; the crank <= 12 LU under idle (small-speaker proxy too), the spool-up <= 6",
          -27 <= lu["idle"] <= -22 and -18 <= lu["max"] <= -13 and -14 <= lu["rev"] <= -10 and lu["crank"] >= lu["idle"] - 12
          and sg["crank"]["lufs_hp"] >= sg["idle"]["lufs_hp"] - 12 and a["lufs_rd"] >= lu["idle"] - 6,
          f"LUFS crank {lu['crank']:.1f}, spool-up (7-11 s) {a['lufs_rd']:.1f}, idle {lu['idle']:.1f}, 1,700 {lu['max']:.1f}, reverse "
          f"{lu['rev']:.1f}, feathered {lu['feather']:.1f}; HP 250 Hz: crank {sg['crank']['lufs_hp']:.1f}, idle {sg['idle']['lufs_hp']:.1f}")
    check("[sound] the start: audible within 0.4 s of the click (momentary >= idle - 16 LU), the light-off a distinct "
          "event (momentary >= crank + 6 LU and >= what follows + 2)",
          mo["onset"] >= lu["idle"] - 16 and mo["light"] >= mo["crank"] + 6 and mo["light"] >= mo["after"] + 2,
          f"momentary LUFS: 0.4-0.8 s after the click {mo['onset']:.1f}, the crank {mo['crank']:.1f}, light-off {mo['light']:.1f} "
          f"({mo['light'] - mo['crank']:+.1f} LU), 2 s later {mo['after']:.1f}")
    check("[sound] offline render levels (dBA, 3/4 view, default volume): 1,700 >= idle + 10; reverse 1,700 + 4..8; feathered < 1,700 - 3; "
          "crank audible (> idle - 20), light-off a step up; run-down fading",
          sg["max"]["la"] >= sg["idle"]["la"] + 10 and sg["max"]["la"] + 4 <= sg["rev"]["la"] <= sg["max"]["la"] + 8
          and sg["feather"]["la"] < sg["max"]["la"] - 3 and sg["idle"]["la"] - 20 < sg["crank"]["la"] < sg["idle"]["la"]
          and a["lightoff"] > sg["crank"]["rms"] + 6 and sg["stop"]["la"] < sg["idle"]["la"] - 10,
          f"dBA re idle: crank {sg['crank']['la'] - sg['idle']['la']:+.1f}, 1,700 {sg['max']['la'] - sg['idle']['la']:+.1f}, reverse "
          f"{sg['rev']['la'] - sg['idle']['la']:+.1f}, feathered {sg['feather']['la'] - sg['idle']['la']:+.1f}, run-down "
          f"{sg['stop']['la'] - sg['idle']['la']:+.1f}; rms dBFS idle {sg['idle']['rms']:.1f}, 1,700 {sg['max']['rms']:.1f}, reverse "
          f"{sg['rev']['rms']:.1f}; light-off {a['lightoff'] - sg['crank']['rms']:+.1f} dB over the crank")
    check("[sound] the limiter idles at the default volume in the 3/4 view (gain reduction > -0.2 dB throughout), the output "
          "curve rounds < 0.1 % of the samples",
          a["gr"] > -0.2 and a["shoulder"] < 0.1, f"deepest {a['gr']:.2f} dB, {a['shoulder']:.3f} % of the samples above the curve's knee")
    check("[sound] texture at 1,700 rpm: tonal share 50-70 % (unweighted), propeller-band envelope std/mean 0.2-0.4 (gusts, "
          "turbulence); stereo L/R correlation 0.5-0.97 (the room)",
          50 <= sg["max"]["tonal"] <= 70 and 0.2 <= sg["max"]["env"] <= 0.4 and 0.5 <= a["corr"] <= 0.97,
          f"tonal {sg['max']['tonal']:.1f} % (idle {sg['idle']['tonal']:.1f} %, reverse {sg['rev']['tonal']:.1f} %), envelope "
          f"{sg['max']['env']:.3f} (idle {sg['idle']['env']:.3f}), L/R corr {a['corr']:.3f}")
    bp = [a["bp_idle"], a["bp_max"]]
    check("[sound] spectrum: the blade-passing line at 5 x rpm / 60 (idle, 1,700 rpm) within 1 %",
          all(abs(m_ - w_) <= 0.01 * w_ for m_, w_ in bp), ", ".join(f"{m_:.2f} / {w_:.2f} Hz" for m_, w_ in bp))
    wh = [a["wh_idle"], a["wh_max"]]
    ws = [(m_, w_) for _, m_, w_ in a["wh_start"]]
    # steady: 1 %; through the start sweep 2.5 % (the parameters follow the state with a 0.05 s smoothing lag: ~30 Hz)
    check("[sound] spectrum: the whine line follows 16 x Ng (idle, 1,700 rpm: 1 %; through the start sweep: 2.5 %)",
          all(abs(m_ - w_) <= 0.01 * w_ for m_, w_ in wh) and all(abs(m_ - w_) <= 0.025 * w_ for m_, w_ in ws),
          ", ".join(f"{m_:.0f}/{w_:.0f}" for m_, w_ in wh + ws) + " Hz")
    # the extra renders
    ex = {}
    for name, o in SOUND_EXTRA.items():
        rx = await render(o)
        p_ = out_dir / f"pc12_sound_{name}.wav"
        p_.write_bytes(base64.b64decode(rx["wav"]))
        ex[name] = (p_, rx)
        print(f"  wav {p_} ({rx['seconds']:.0f} s, rendered in {rx['took']:.1f} s)")
    p_, rx = ex["loudest"]
    srL, xL = _wav(p_)
    grL = [v for t_, v in rx["gr"] if t_ >= GR_FROM]
    xL = xL[int(GR_FROM * srL):]
    loud = loudness(xL, srL)
    shL = 100 * float((abs(xL) > 0.7).mean())
    srI, xI = _wav(ex["close_idle"][0])
    close_idle = loudness(xI[int(GR_FROM * srI):], srI)
    check("[sound] close-ups (6 m in the disc plane): idle >= 6 LU louder than the 3/4 view (the distance law); the loudest "
          "state (reverse 1,700 rpm, full volume) held at the ceiling (<= 3 LU over the 3/4 view): limiter gain reduction "
          "<= 1 dB on average, < 1 % of the samples on the output curve, peaks < 0.96",
          close_idle >= lu["idle"] + 6 and grL and sum(grL) / len(grL) >= -1.0 and float(abs(xL).max()) < 0.96
          and loud <= lu["rev"] + 3 and shL < 1.0,
          f"idle {close_idle:.1f} LUFS ({close_idle - lu['idle']:+.1f} LU); loudest {loud:.1f} LUFS ({loud - lu['rev']:+.1f} LU), gain "
          f"reduction mean {sum(grL) / max(len(grL), 1):.2f} / deepest {min(grL, default=0):.2f} dB, {shL:.2f} % on the curve, peak "
          f"{float(abs(xL).max()):.3f}")
    lc = loop_correlation(ex["steady"][0])
    check("[sound] the noise does not loop audibly: the 9-11 kHz hiss correlates < 0.25 with itself 2.7 / 3.2 / 11.3 / 13.7 s later",
          len(lc) == 4 and max(lc.values()) < 0.25, ", ".join(f"{k} s: {v:.3f}" for k, v in lc.items()))
    srP, xP = _wav(ex["pilot"][0])
    pl = sound_stats(xP.mean(axis=1), srP, 13.0, 16.0)
    po = sg["idle"]
    check("[sound] flight deck at idle: the whine heard faintly through the firewall (A-weighted share above 2 kHz -25 .. -12 dB; "
          "outside > -6 dB), quieter than the 3/4 view",
          -25 <= pl["hi2k"] <= -12 and po["hi2k"] > -6 and pl["la"] < po["la"],
          f"above 2 kHz: inside {pl['hi2k']:.1f} dB, 3/4 view {po['hi2k']:.1f} dB; level {pl['la'] - po['la']:+.1f} dBA re the 3/4 view")
    check("[sound] no console errors / page errors", not errs, "; ".join(errs[:4]))
    await js(page, "window.viewer.pause(false);")
    await ctx.close()


# ----------------------------------------------------------------------------- main
async def run(args):
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    srv = start_server()
    port = srv.server_address[1]
    three = "local" if args.three == "local" else "cdn"
    if three == "cdn":
        # sandboxes with a TLS-intercepting proxy present a CA Chromium does not trust
        CTX["ignore_https_errors"] = True
    base = f"http://127.0.0.1:{port}/web/index.html?three={three}"
    t0 = time.time()
    try:
        async with async_playwright() as pw:
            browser = await launch(pw)
            if args.only == "sound":
                await sound_checks(browser, base, args.sound_out)
                await browser.close()
                return
            if args.only in ("phone", "picture"):
                if args.only == "phone":
                    await phone_checks(browser, base, shots=not args.no_shots)
                    await iphone_chip_check(browser, base)
                else:
                    await picture_checks(browser, base)
                    await picture_motion_checks(browser, base)
                await browser.close()
                return
            page = await browser.new_page(viewport=VIEW, device_scale_factor=1, reduced_motion="reduce", **CTX)
            errors, failed, aborted, ok_urls = [], [], [], set()
            page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
            # net::ERR_ABORTED after a 200 response is not a failure: three.js' FileLoader streams the ~10 MB GLB
            # through its own ReadableStream for the progress bar, and headless Chromium can report the original request as
            # aborted although the model loads (checked above: 'viewer loads'); flaky in the baseline, S3-17.  An
            # aborted request that never got a response still fails the check.
            page.on("requestfailed", lambda r: (aborted if "ERR_ABORTED" in str(r.failure) else failed).append(
                (r.url, f"{r.url} ({r.failure})")))
            page.on("response", lambda r: failed.append((r.url, f"{r.url} HTTP {r.status}")) if r.status >= 400
                    else ok_urls.add(r.url))
            requests = []
            page.on("request", lambda r: requests.append(r.url))
            await page.goto(base)
            await page.wait_for_function("window.__ready === true", timeout=180000)
            err = await page.evaluate("window.__error || ''")
            check("viewer loads (GLB + meta + three.js)", not err, err or f"{time.time() - t0:.1f} s")
            if err:
                return
            await page.evaluate(JS_HELPERS)
            if args.only in ("tour", "prop"):
                if args.only == "tour":
                    await tour_checks(page, shots=not args.no_shots)
                else:
                    await prop_blur_checks(page)
                await page.close()
                await browser.close()
                return
            st = await js(page, "return window.viewer.state;")
            check("starts on the finished aircraft", st["stepKey"] == "paint" and st["paint"] and not st["loading"], st["stepKey"])
            # [m2] the boot script's preloads are the requests the viewer makes: one download each
            glb_req = [u for u in requests if u.split("?")[0].endswith((".glb", ".hdr", "pc12_meta.json", "materials.json"))]
            check("[m2] model / HDRI / meta / materials preloaded and downloaded once each", len(glb_req) == 4 and len(set(glb_req)) == 4,
                  f"{len(glb_req)} requests: " + ", ".join(sorted(u.rsplit('/', 1)[-1] for u in glb_req)))
            check("desktop: loads the full model (pc12.glb), not the light tier",
                  sorted(u.split("?")[0].rsplit("/", 1)[-1] for u in glb_req if u.split("?")[0].endswith(".glb")) == ["pc12.glb"],
                  ", ".join(sorted(u.rsplit('/', 1)[-1] for u in glb_req)))
            # [R1/R2/R4] Blender's AgX + Punchy look; the light theme's lifted studio and exposure
            pf = await js(page, "return window.viewer.perf();")
            lk = pf["look"]
            check("[R2] tone mapping: AgX with Blender's Punchy look (fitted curve, no extra saturation)",
                  lk["look"] == "punchy" and "pcLookCurve" in await js(page, "return window.viewer._internals.THREE.ShaderChunk.tonemapping_pars_fragment;"),
                  f"look {lk['look']}, light {lk['theme']['light']}, dark {lk['theme']['dark']}")
            await material_checks(page)
            ref_geo = await js(page, "return T.geo();")
            await fit_check(page, "960x600 3/4", refit_panel=True)
            if not args.no_shots:
                await screenshots(page)
            await numeric_checks(page)
            await prop_blur_checks(page)
            await regression_checks(page)
            await tour_checks(page, shots=not args.no_shots)
            if args.blender:
                await blender_check(page)
            await context_loss_check(page)
            await picture_auto_check(page)
            snd = await js(page, "return window.viewer.sound.state();")
            check("[sound] off by default under automation: no AudioContext made in the whole main run",
                  snd["supported"] and not snd["on"] and snd["created"] == 0 and snd["ctx"] is None,
                  f"on {snd['on']}, {snd['created']} contexts, gesture seen {snd['gesture']}")
            check("no console errors / page errors", not errors, "; ".join(errors[:4]))
            bad = [t for _, t in failed] + [t for u, t in aborted if u not in ok_urls]
            check("no failed requests", not bad,
                  "; ".join(bad[:4]) or (f"{len(aborted)} aborted after a 200 response (stream)" if aborted else ""))
            await page.close()
            await phone_checks(browser, base, shots=not args.no_shots)
            await iphone_chip_check(browser, base)
            await landscape_check(browser, base, shots=not args.no_shots)
            await safe_area_portrait(browser, base)
            await dark_and_data(browser, base, shots=not args.no_shots)
            await picture_checks(browser, base)
            await picture_motion_checks(browser, base)
            await error_path(browser, base)
            await boot_failures(pw, browser, base)
            await meshopt_check(browser, base, ref_geo)
            await sound_checks(browser, base, args.sound_out)
            if not args.no_shots:
                await loading_shot(browser, base)
            await browser.close()
    finally:
        srv.shutdown()
    print(f"total {time.time() - t0:.0f} s")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--blender", action="store_true", help="also cross-check the GLB in Blender (bpy)")
    ap.add_argument("--no-shots", action="store_true", help="skip screenshots (numeric checks only)")
    ap.add_argument("--three", default="local", choices=["local", "cdn"],
                    help="three.js source: web/three_local (default) or the jsDelivr CDN")
    ap.add_argument("--only", default="all", choices=["all", "sound", "tour", "prop", "phone", "picture"],
                    help="sound: only the engine-sound section (its own page; ~2 min); tour: only the interior tour "
                         "[T1]-[T18] on the desktop page; prop / phone / picture: those sections alone (a rerun of a "
                         "section that timed out or was starved under load)")
    ap.add_argument("--sound-out", type=Path, default=OUT / "sound",
                    help="folder for the offline render pc12_engine_sequence.wav + spectrogram.png (default out/tmp/viewer/sound)")
    args = ap.parse_args()
    try:
        asyncio.run(run(args))
    except Exception as e:  # report instead of a bare traceback
        import traceback
        traceback.print_exc()
        check("test harness", False, repr(e))
    w = max(len(n) for n, _, _, _ in results) if results else 10
    print("\n" + "-" * (w + 60))
    for name, ok, detail, known in results:
        print(f"{'PASS' if ok else 'KNOWN' if known else 'FAIL'}  {name.ljust(w)}  {detail}")
    nfail = sum(1 for _, ok, _, known in results if not ok and not known)
    nknown = sum(1 for _, ok, _, known in results if not ok and known)
    npass = sum(1 for _, ok, _, _ in results if ok)
    print("-" * (w + 60))
    print(f"{npass}/{len(results)} passed" + (f", {nknown} KNOWN (GLB data, see model/)" if nknown else "")
          + (f", {nfail} FAILED" if nfail else ""))
    sys.exit(1 if nfail else 0)


if __name__ == "__main__":
    main()
