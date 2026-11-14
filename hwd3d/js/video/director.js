// In-page director of the OD3 videos (hwd3d Phase 3, video). Imported by the driver (tools/video/render.mjs) into the
// UNMODIFIED app (live.html?mode=replay&fixedres=1) once it is ready, under the virtual clock of js/video/vclock.js.
//
//   const info = await (await import('/js/video/director.js')).installDirector(cfg)   -> window.__vd
//   cfg: { t0 (virtual epoch ms, as given to installVClock), packUrl, type ('SF50' | 'PC12'), event ('takeoff' | 'landing'),
//          window: {from, to} (data ms: the hero must be at HWD with its event inside), frames (js/video/timeline.js),
//          preStep (s, engine step of the pre-roll), models (kept for the job format: the app now draws every PC12 / SF50
//          with its detailed model, and the director always preloads both models),
//          cams (per-frame cameras [px, py, pz, tx, ty, tz, fovDeg] from js/video/camera.js, or null), cuts (frame indices
//          where a shot starts), shutter (motion-blur shutter of captured frames, 0..1; 0 = off), fps, runway,
//          overlay options { timeOnly, endDate } }
//   __vd.prepare()        pre-roll: the engine alone from the virtual epoch to the start of frame 0 (preStep sub-steps)
//   __vd.step(render)     one output frame: the engine in frames[f].n sub-steps of frames[f].h s (only the last one inside
//                         the app's own frame callback, which also syncs the drawables and - when `render` - renders);
//                         returns the hero pose (also the scout trace sample)
//   __vd.overlay(state)   caption / end card for the frame about to be captured (state.cap: the planned caption of the
//                         frame, js/video/provenance.js captionTrack; without it the live sample is used: preview only)
//
// The app's own hooks (Phase 3b, js/live/app.js; docs/phase3_video.md section 8 items 2-6 - they replaced the director's
// monkeypatches of the rig, the views, the engine and the renderer, 2026-11-14). The app's own loop is paused
// (HWD.qa.pause): the director drives every frame itself.
//  - the engine: HWD.stepEngine(now, dt) for the pre-roll and the sub-steps of a time-lapse frame;
//  - a frame: HWD.qa.frame({ wall: 1 / fps, engineDt: h, render, cut }): the animation clock (simT: propeller / fan angle,
//    strobe and beacon phase; flap, gear and control lags; the 30-s environment timer) advances by one VIDEO frame and the
//    engine by its own sub-step h, so the animation runs at video rate in every frame, time-lapse ramps included;
//    render: false is the app's no-draw frame (scout runs, the skip-ahead before a frame range): only the GPU work is
//    skipped, the engine, drawables and camera advance exactly as in a drawn frame and the renderer keeps the camera as its
//    previous camera (R.prev, the motion vectors' reference), so the first DRAWN frame of a range, a resume or a pick blurs
//    against the true previous frame; cut: true at a shot start clears that reference (no camera motion from the last shot);
//  - the camera: HWD.setCamera(fn) - the scripted camera of js/video/camera.js (or a plain chase camera without a plan);
//  - motion blur: HWD.setPost({ shutter: cfg.shutter }) (the app's own blur pass, js/renderer.js; the app's own loop runs
//    with 0);
//  - the drawables: the app's own (js/live/aircraft.js AircraftViews): every PC12 / SF50 is a DetailedAircraft whose gear,
//    flaps, propeller / fan, controls and lights the views drive from the drawn motion; the director only preloads the
//    models before the first frame, so a model never appears at a load-dependent frame (determinism).
// Hero selection BY RULE (D1): the pack's records of `type` with a ground fix within 2.5 km of the ARP and the case's event
// (take-off: ground then airborne; landing: airborne then ground) inside cfg.window; the most such fixes wins. Its key
// stays in this closure: it is never returned, logged or written (no UI text or log line may hold a key).
import { phaseLabel } from '../live/traffic.js';
import { wgs84ToWorld } from '../geo.js';
import { MODELS, loadModel } from '../aircraft/models.js';
import { Overlay } from './overlay.js';
import { speedLabel } from './timeline.js';
import { sampleSrc, pillText } from './provenance.js';

const HWD_R = 2500;            // m from the ARP: "at HWD"
const D2R = Math.PI / 180, KT = 1852 / 3600;

async function fetchPack(url) {
  const r = await fetch(url, { cache: 'no-store' }); if (!r.ok) throw new Error('pack HTTP ' + r.status);
  const buf = new Uint8Array(await r.arrayBuffer());
  const txt = buf[0] === 0x1f && buf[1] === 0x8b ? await new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'))).text() : new TextDecoder().decode(buf);
  return JSON.parse(txt);
}
// the rule (see the header) -> { key, n, fixes } | null
function selectHero(pack, { type, event, window: win }) {
  const st = {}, per = new Map();
  for (const e of pack.events) {
    for (const r of e.p.d) {
      const a = st[r[0]] || (st[r[0]] = {}); for (const k in r[1]) a[k] = r[1][k]; if (r[2]) for (const k of r[2]) delete a[k];
      if (a.t !== type || a.lat == null || a.lon == null) continue;
      const T = e.T * 1000; if (win && (T < win.from || T > win.to)) continue;
      const w = wgs84ToWorld(a.lat, a.lon); const g = a.alt_baro === 'ground';
      let L = per.get(r[0]); if (!L) per.set(r[0], L = []);
      L.push({ T, x: w[0], z: w[2], g, r: Math.hypot(w[0], w[2]) });
    }
  }
  let best = null;
  for (const [key, L] of per) {
    const atHwd = L.filter(f => f.g && f.r < HWD_R); if (!atHwd.length) continue;
    let ok = false;
    if (event === 'takeoff') { const tg = atHwd[0].T; ok = L.some(f => !f.g && f.T > tg); }
    else if (event === 'landing') { const tg = atHwd[atHwd.length - 1].T; ok = L.some(f => !f.g && f.T < tg && f.r < 15000); }
    else ok = true;
    if (!ok) continue;
    if (!best || atHwd.length > best.n) best = { key, n: atHwd.length, fixes: L.length };
  }
  return best;
}

export async function installDirector(cfg) {
  const H = window.HWD, V = window.__vclock;
  if (!H || !V) throw new Error('director: the app (window.HWD) or the virtual clock is missing');
  if (window.__vd) return window.__vd.info();
  const d = new Director(cfg, H, V); await d.init(); window.__vd = d; return d.info();
}

class Director {
  constructor(cfg, H, V) { this.cfg = cfg; this.H = H; this.V = V; this.f = -1; this.wallPrev = null; this.camLast = null; this.camNow = null; }
  async init() {
    const { cfg, H } = this;
    this.pack = await fetchPack(cfg.packUrl);
    this.L = this.pack.lookahead_s || 60;
    // the shim's offset (out/replay/replay_shim.js start(): Date.now() / 1000 - (from + L), evaluated at t0) -> data <-> wall
    this.off = cfg.t0 / 1000 - (this.pack.from + this.L);
    const sel = selectHero(this.pack, cfg);
    let heroKey = sel ? sel.key : null; this.heroStats = sel ? { fixesAtHwd: sel.n, fixes: sel.fixes } : null;
    this.hero = () => (heroKey != null ? H.traffic.tracks.get(heroKey) || null : null);
    this.heroView = () => (heroKey != null ? { v: H.views.get(heroKey), S: H.views.drive ? H.views.drive(heroKey) : null } : null);
    this.metars = (this.pack.metar || []).slice().sort((a, b) => a.obsTime - b.obsTime);
    // detailed models: EVERY registered type loaded before the first frame (the app's views draw every PC12 / SF50 with its
    // model; a load finishing during the run would put the model in at a load-dependent frame)
    this.modelOk = {};
    for (const ty of Object.keys(MODELS)) { try { await loadModel(ty); this.modelOk[ty] = true; } catch (e) { this.modelOk[ty] = false; console.warn('video: model load failed', ty, String(e && e.message || e)); } }
    // the app's hooks (header): its own loop paused, the planned camera, the capture shutter
    H.qa.pause(true);
    H.setCamera(() => this.camNow);
    const oo = cfg.overlay || {};
    this.ov = new Overlay({ type: cfg.type, event: cfg.event, runway: cfg.runway || '28L', endDate: !!(oo.endDate ?? cfg.endDate), timeOnly: !!oo.timeOnly });
    H.qa.hideUI(true);
    this.frames = cfg.frames || null; this.cams = cfg.cams || null;
    this.fps = cfg.fps || 30; this.shutter = +cfg.shutter || 0; this.cuts = new Set(cfg.cuts || []);
    H.setPost({ shutter: this.shutter });
  }
  info() { return { hero: !!this.heroStats, heroStats: this.heroStats, frames: this.frames ? this.frames.length : 0, models: this.modelOk, off: this.off, lookahead: this.L, f: this.f, shutter: this.shutter, cuts: this.cuts.size }; }
  setCams(c) { this.cams = c; return true; }
  wallOf(tData) { return (tData / 1000 + this.off + this.L) * 1000; }
  dataOf(wall) { return wall - this.L * 1000 - this.off * 1000; }   // the data time the app displays at virtual wall time `wall`
  // ---------------------------------------------------------------- stepping
  engine(now, dt) { this.H.stepEngine(now, dt); }
  async prepare({ preStep = this.cfg.preStep || 0.1 } = {}) {
    const V = this.V, F0 = this.frames[0];
    const end = this.wallOf(F0.t - F0.dt); let w = V.wall, n = 0;
    if (end < w) throw new Error('director: the first frame lies before the virtual epoch');
    while (w < end - 1e-6) {
      const nw = Math.min(end, w + preStep * 1000); V.advanceTo(nw); this.engine(nw, (nw - w) / 1000); w = nw;
      if (++n % 10 === 0) await V.settle(2);
    }
    await V.settle(2);
    this.wallPrev = end; this.f = -1;
    return { steps: n, wall: V.wall };
  }
  /** one output frame; render: true -> the GPU frame is drawn (and the overlay updated), false -> state only */
  async step(render = true) {
    const { V, H } = this; const f = ++this.f; const F = this.frames[f];
    if (!F) throw new Error('director: no frame ' + f);
    const w0 = this.wallPrev, w1 = this.wallOf(F.t);
    for (let i = 1; i < F.n; i++) { const w = w0 + (w1 - w0) * i / F.n; V.advanceTo(w); this.engine(w, F.h); }
    V.advanceTo(w1); V.tickPerf(1000 / this.fps);
    this.camNow = this.cameraFor(f);
    // the app's frame: animation dt = one video frame, the engine's last sub-step h; a cut clears the blur reference
    H.qa.frame({ wall: 1 / this.fps, engineDt: F.h, render: !!render, cut: this.cuts.has(f) });
    await V.settle(2);
    this.wallPrev = w1;
    return this.pose(f);
  }
  // ---------------------------------------------------------------- camera
  cameraFor(f) {
    const c = this.cams && this.cams[f];
    if (c) return camOf([c[0], c[1], c[2]], [c[3], c[4], c[5]], c[6] * D2R);
    // no plan (scout runs): a plain chase camera behind the hero, so a debug render still shows it
    const tr = this.hero(); const D = tr && tr.disp;
    if (!D || !D.valid) return this.camLast || camOf([0, 200, 600], [0, 12, 0], 45 * D2R);
    const h = D.hdg * D2R, fx = Math.sin(h), fz = -Math.cos(h);
    const t = [D.x, D.y + 2, D.z], p = [D.x - fx * 45, D.y + 14, D.z - fz * 45];
    p[1] = Math.max(p[1], this.H.site.groundY(p[0], p[2]) + 1.5);
    return (this.camLast = camOf(p, t, 40 * D2R));
  }
  // ---------------------------------------------------------------- hero pose / provenance of the current sample
  pose(f) {
    const F = this.frames[f], tr = this.hero(), out = { f, t: F.t, speed: F.speed };
    if (!tr) { out.found = false; return out; }
    const D = tr.disp, gy = this.H.site.groundY(D.x, D.z);
    const dimsOf = (t) => (this.H.views.dimsOf ? this.H.views.dimsOf(t) : t.dims);   // the drawable's dims (the model's frame)
    const tDisp = this.H.traffic.displayTime(Date.now());
    Object.assign(out, { found: true, valid: !!D.valid, inView: !!tr.inView, x: D.x, y: D.y, z: D.z, hdg: D.hdg, pitch: (D.pitch || 0) / D2R, roll: (D.roll || 0) / D2R,
      gs: D.gs / KT, vs: D.vs, ground: !!D.ground, agl: D.y - gy, gy, alpha: D.alpha, gear: D.gear, flaps: D.flaps, phase: tr.phase,
      label: phaseLabel(tr, Date.now()).replace(/ \(provisional\)$/, ''), stale: !!tr.stale, L: (dimsOf(tr) && dimsOf(tr).L) || 10, span: (dimsOf(tr) && dimsOf(tr).span) || 12 });
    Object.assign(out, sampleSrc(tr.fx, tDisp, !!tr.stale));
    // the drawable's driven state (js/live/aircraft.js: gear, flaps, propeller / fan, controls, lights - all inferred rules)
    const hv = this.heroView(), v = hv && hv.v, S = hv && hv.S;
    if (v) {
      const L = v.lightsOn || {};
      Object.assign(out, { detailed: !!v.loaded, vgear: +(+v.gear).toFixed(3), vflaps: v.flaps != null ? +(+v.flaps).toFixed(2) : null, flapsTgt: S ? S.flaps : null,
        rotor: +(+v.rotor || 0).toFixed(1), running: S ? !!S.running : null, gearUp: S ? !!S.gearUp : null,
        ctl: S ? [+S.ctl.roll.toFixed(3), +S.ctl.pitch.toFixed(3), +S.ctl.yaw.toFixed(3)] : null,
        lights: ['nav', 'beacon', 'strobe', 'landing', 'taxi'].map(k => (L[k] ? k[0].toUpperCase() : '-')).join('') });
    }
    // other drawn aircraft near the hero (the camera keeps clear of their bodies)
    const near = [];
    for (const o of this.H.traffic.tracks.values()) {
      if (o === tr || !o.disp.valid || !o.inView || o.hidden || !(o.disp.alpha > 0.02)) continue;
      const d = Math.hypot(o.disp.x - D.x, o.disp.z - D.z); if (d > 800) continue;
      const T = dimsOf(o) || {}; near.push([+o.disp.x.toFixed(2), +o.disp.y.toFixed(2), +o.disp.z.toFixed(2), +(0.5 * Math.max(T.L || 9, T.span || 10)).toFixed(1)]);
    }
    out.near = near;
    return out;
  }
  // ---------------------------------------------------------------- overlay
  overlay(o = {}) {
    const p = o.pose || {}; const F = this.frames[Math.max(0, this.f)];
    const tData = F.t;
    const m = this.metars.filter(x => x.obsTime * 1000 <= tData).pop();
    // the planned caption of this frame (render runs), else the live sample (the preview without a plan)
    const c = o.cap || (() => { const [text, sub] = pillText(p); return { phase: p.label || '', cls: p.src, text, sub }; })();
    this.ov.update({ phase: c.phase || '', tData, src: c.cls, srcText: c.text, srcSub: c.sub, speed: speedLabel(F.nominal ?? F.speed), metar: m ? m.rawOb : '', end: o.end || 0, fade: o.fade || 0, caption: o.caption });
    return true;
  }
}
function camOf(pos, target, fov) {
  const d = Math.hypot(target[0] - pos[0], target[1] - pos[1], target[2] - pos[2]);
  return { pos, target, fov, near: Math.min(5, Math.max(0.2, d * 0.004)), split: Math.min(8000, Math.max(2500, d * 3.5)), far: 40000,
    shadowSplits: [Math.max(60, d * 0.6), Math.max(400, d * 2.2), Math.max(2500, d * 4.5)] };
}
