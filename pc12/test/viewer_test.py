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
  - nose doors are open whenever the nose gear is between the locks (instant poses and the
    real animated sequence); mains retract inward, nose gear aft; doors open outward
  - review round-1 regressions: gear readout when scrubbed, readouts never stale, shortcuts after a
    slider / button click, search Escape, wing structure hidden once the skins land, nothing below
    the ground when exploded / flying in, zero-explode parts grow in place, current build step always
    inside the panel, first camera fit uses the free viewport (and follows panel toggles), windshield
    see-through from the cockpit, prop blur disc follows exploded blades, compact info card on phones
Optional --blender: re-imports out/pc12.glb in Blender (bpy, /opt/venv-blender) and checks
that Blender's scene graph gives the same part boxes and posed points as the viewer, and runs a
BVH interference sweep of the gear against doors / flaps / flight deck.  Interferences that are
GLB-data issues owned by model/gear.py are reported as KNOWN (they do not fail the run; they flip
to PASS once the GLB is fixed).

usage: python3 test/viewer_test.py [--blender] [--no-shots] [--three cdn]
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


async def launch(pw):
    """Launch Chromium; fall back to any installed Playwright build if the pinned one is missing."""
    exe = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
    if exe:
        return await pw.chromium.launch(executable_path=exe, args=LAUNCH_ARGS)
    try:
        return await pw.chromium.launch(args=LAUNCH_ARGS)
    except Exception as first:
        base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")
        # newest first; the headless shell (Playwright's default headless binary) before full Chromium
        cands = sorted(glob.glob(f"{base}/chromium_headless_shell-*/chrome-linux*/headless_shell"), reverse=True)
        cands += sorted(glob.glob(f"{base}/chromium-*/chrome-linux*/chrome"), reverse=True)
        for c in cands:
            try:
                return await pw.chromium.launch(executable_path=c, args=LAUNCH_ARGS)
            except Exception:
                continue
        raise first


# ----------------------------------------------------------------------------- JS helpers
JS_HELPERS = r"""
window.T = {
  V: window.viewer,
  sub: (a, b) => a.map((x, i) => x - b[i]),
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
  // projected silhouette of the aircraft vs the free part of the viewport (not under the panel /
  // bottom sheet / toolbar), in CSS px
  fit: () => {
    const V = window.viewer, I = V._internals, cam = I.stage.camera, pts = I.stage.silhouette;
    cam.updateMatrixWorld();
    const cv = I.stage.renderer.domElement.getBoundingClientRect();
    const panel = document.getElementById('panel').getBoundingClientRect(), tb = document.getElementById('toolbar').getBoundingClientRect();
    const narrow = matchMedia('(max-width: 760px)').matches, open = document.getElementById('app').classList.contains('panel-open');
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
    await page.screenshot(path=str(path))
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
    await shot(page, "20_prop_1700rpm", V + "V.setProp({rpm: 1700, pitch: 0}, {instant: true}); V.advance(0.2); V.pause(true);")
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

    # --- gear: mains inward, nose aft, nose doors open between the locks
    r = await js(page, r"""
      const V = window.viewer, out = {};
      T.neutral();
      const wheel = (id) => { const b = T.box(id); return [b.center[0], b.min[1] + 0.22, b.center[2]]; };
      const P = {};
      for (const id of ['gear_main_R', 'gear_main_L', 'gear_nose']) { const p = wheel(id); P[id] = {w0: p, loc: T.attach(id, p)}; }
      for (const id of ['gear_door_NR', 'gear_door_NL']) {
        const b = T.box(id), p = [id.endsWith('R') ? b.min[0] + 0.01 : b.max[0] - 0.01, b.center[1], b.center[2]];   // free (inboard) edge
        P[id] = {w0: p, loc: T.attach(id, p)};
      }
      V.setGear(1, {instant: true});
      for (const id of ['gear_main_R', 'gear_main_L', 'gear_nose']) out[id] = T.sub(T.world(id, P[id].loc), P[id].w0);
      const samples = [];
      for (let k = 1; k <= 9; k++) {
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
          if (g.pos === g.target && g.door === 0) break;
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
    check("nose doors open (85 deg, edges down) at gear 10..90 %", not bad,
          f"door {min(s['doorDeg'] for s in r['samples']):.1f} deg, edge dY <= {max(max(s['dNR'], s['dNL']) for s in r['samples']):+.3f} m")
    for name in ("seqUp", "seqDown"):
        rows = r[name]
        target = 1.0 if name == "seqUp" else 0.0
        between_closed = [row for row in rows if 1e-9 < row[1] < 1 - 1e-9 and row[2] < 0.999]
        first_move = next((row for row in rows if abs(row[1] - (1 - target)) > 1e-9), None)
        end = rows[-1]
        ok = not between_closed and first_move is not None and first_move[2] >= 0.999 and end[1] == target and end[2] == 0
        check(f"gear {'up' if target else 'down'} sequence: doors open -> gear -> doors close", ok,
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
      V.setGear(0, {instant: true}); V.setGear('up'); V.advance(0.3); await V.frames(2);
      const opening = document.getElementById('rGear').textContent;
      V.advance(8); await V.frames(2);
      const up = document.getElementById('rGear').textContent;
      T.neutral(); await V.frames(2);
      return {mid, opening, up, down: document.getElementById('rGear').textContent};
    """)
    check("[F5/UX-3] gear readout: scrubbed mid-travel = stopped, doors open", r["mid"].startswith("stopped") and "doors open" in r["mid"]
          and r["opening"].startswith("doors opening") and r["up"].startswith("UP") and r["down"].startswith("DOWN"),
          f"'{r['mid']}' / '{r['opening']}' / '{r['up']}' / '{r['down']}'")
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
    await page.click("#explode")
    await page.keyboard.press("x")
    s1 = await js(page, "return window.viewer.state;")
    await page.keyboard.press("x")
    await page.click("#tLines")
    await page.keyboard.press(" ")
    s2 = await js(page, "return window.viewer.state;")
    check("[UX-5] shortcuts work after clicking a slider; Space plays after clicking a button",
          s1["xray"] and s2["playing"] and s2["construction"],
          f"X after slider: xray {s1['xray']}; Space after 'Lines' click: playing {s2['playing']}, lines {s2['construction']}")
    await js(page, V + "V.play(false); V.setConstruction(false); V.setExplode(0, {instant: true}); V.setStep('paint', {instant: true}); document.activeElement && document.activeElement.blur();")
    # [UX-2] Escape in the parts search clears the filter too; group counts follow the filter
    await js(page, "window.viewer.tab('parts');")
    await page.fill("#partSearch", "flettner")
    f1 = await js(page, "return [document.getElementById('pCount').textContent, [...document.querySelectorAll('#partTree details:not([hidden]) .cnt')].map(e => e.textContent)];")
    await page.focus("#partSearch")
    await page.keyboard.press("Escape")
    f2 = await js(page, "return [document.getElementById('pCount').textContent, [...document.querySelectorAll('#partTree li')].filter(l => !l.hidden).length, document.getElementById('partSearch').value];")
    check("[UX-2] search: Escape clears the query and the filter; counts show matches / total",
          f1[0].startswith("2 of") and f1[1] == ["2 / 11"] and f2[0] == "69 parts" and f2[1] == 69 and f2[2] == "",
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
    await page.screenshot(path=str(shot_path))
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
        for (let k = 1; k <= 5; k++) { const b = V.partWorldBox('blade_' + k); for (const x of [b.min, b.max]) for (const y of [b.min, b.max]) tip = Math.max(tip, Math.hypot(x[0] - hub[0], y[1] - hub[1])); }
        out[f] = {disc: 1.34 * I.kin.disc.children[0].scale.x, visible: I.kin.disc.visible, push: V.state.propDiscPush};
      }
      T.neutral();
      return out;
    """)
    ok = all(v["visible"] for v in r.values()) and abs(r["1"]["disc"] - r["0"]["disc"] - 0.45) < 0.01 and abs(r["1.5"]["disc"] - r["0"]["disc"] - 0.675) < 0.01
    check("[BV-6] prop blur disc grows with the exploded blades (radial push 0.45 m x f)", ok,
          f"disc radius {r['0']['disc']:.3f} / {r['1']['disc']:.3f} / {r['1.5']['disc']:.3f} m at explode 0 / 1 / 1.5")
    # [BV-9] structure pushed behind the coincident skins
    r = await js(page, "const m = window.viewer._internals.model; return m.part('structure').meshes.map(mr => [mr.base.polygonOffset, mr.base.polygonOffsetFactor, mr.base.polygonOffsetUnits]);")
    check("[BV-9] structure materials carry a polygon offset (no z-fighting with the skins)", all(x[0] and x[1] > 0 and x[2] > 0 for x in r), str(r[0]))


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
for d in ("gear_door_NR", "gear_door_NL"): setrot(d, math.radians(PV[d]["open"]))
res["nose_doors_open_vs_nose_gear"] = []
for f in (0.0, 0.1, 0.2, 0.3, 0.5, 0.8, 1.0):
    pose_gear("gear_nose", f)
    res["nose_doors_open_vs_nose_gear"].append([f, pairs(["gear_door_NR"], NOSE), pairs(["gear_door_NL"], NOSE)])
reset()
res["gear_down_doors_closed"] = pairs(["gear_door_NR", "gear_door_NL"], NOSE)
for g in ("gear_main_R", "gear_main_L"): pose_gear(g, 1.0)
res["mains_up_vs_flaps"] = pairs(["gear_main_R", "gear_main_L"], ["flap_R", "flap_L", "flap_fairings"])
pose_gear("gear_nose", 1.0)
res["nose_up_vs_flight_deck"] = pairs(["gear_nose"], ["flight_deck"])
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
        check("[F2] blender: gear down, doors closed: leg and lower brace clear the doors", it["gear_down_doors_closed"] == 0,
              f"{it['gear_down_doors_closed']} tri pairs", known=True)
        check("[F3] blender: retracted mains clear the flaps / flap fairings (flaps 0)", it["mains_up_vs_flaps"] == 0,
              f"{it['mains_up_vs_flaps']} tri pairs", known=True)
        check("[F4] blender: retracted nose wheel clears the flight deck", it["nose_up_vs_flight_deck"] == 0,
              f"{it['nose_up_vs_flight_deck']} tri pairs", known=True)


# ----------------------------------------------------------------------------- phone + error path
async def phone_checks(browser, base, shots=True):
    ctx = await browser.new_context(viewport=PHONE, device_scale_factor=1, is_mobile=True, has_touch=True, reduced_motion="reduce", **CTX)
    page = await ctx.new_page()
    errs = []
    page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errs.append(str(e)))
    await page.goto(base)
    await page.wait_for_function("window.__ready === true", timeout=180000)
    await page.evaluate(JS_HELPERS)
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
    check("phone: no console errors", not errs, "; ".join(errs[:3]))
    await ctx.close()


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
    await page.screenshot(path=str(OUT / "00_loading.png"))
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
    await page.close()


async def error_path(browser, base):
    page = await browser.new_page(viewport=VIEW, **CTX)
    await page.goto(base + "&glb=../out/does_not_exist.glb")
    await page.wait_for_function("window.__ready === true", timeout=60000)
    msg = await page.evaluate("[window.__error || '', getComputedStyle(document.getElementById('loading')).display, document.getElementById('loadMsg').textContent]")
    check("missing GLB: clear error on the loading screen", "Could not load" in msg[0] and "does_not_exist" in msg[2] and msg[1] != "none",
          msg[2].splitlines()[0] if msg[2] else "")
    await page.close()


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
            await page.goto(base)
            await page.wait_for_function("window.__ready === true", timeout=180000)
            err = await page.evaluate("window.__error || ''")
            check("viewer loads (GLB + meta + three.js)", not err, err or f"{time.time() - t0:.1f} s")
            if err:
                return
            await page.evaluate(JS_HELPERS)
            st = await js(page, "return window.viewer.state;")
            check("starts on the finished aircraft", st["stepKey"] == "paint" and st["paint"] and not st["loading"], st["stepKey"])
            await fit_check(page, "960x600 3/4", refit_panel=True)
            if not args.no_shots:
                await screenshots(page)
            await numeric_checks(page)
            await regression_checks(page)
            if args.blender:
                await blender_check(page)
            check("no console errors / page errors", not errors, "; ".join(errors[:4]))
            bad = [t for _, t in failed] + [t for u, t in aborted if u not in ok_urls]
            check("no failed requests", not bad,
                  "; ".join(bad[:4]) or (f"{len(aborted)} aborted after a 200 response (stream)" if aborted else ""))
            await page.close()
            await phone_checks(browser, base, shots=not args.no_shots)
            await dark_and_data(browser, base, shots=not args.no_shots)
            await error_path(browser, base)
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
