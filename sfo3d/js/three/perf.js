// Performance flags and per-frame timing for the three.js renderer (js/three/renderer3.js, js/three/engine.js), used by
// the phone benchmark artifact (tools/build3/phone_bench.sh, docs/research/mobile_perf.md). Everything here is inert
// unless window.SFO_PERF is set before the app bundle runs (artifacts cannot take query strings, so the benchmark page
// sets the global; a local page may pass ?perf=<json> instead). With it unset every hook below is a no-op and the
// renderer builds exactly what it built before (desktop tiers unchanged).
//
// window.SFO_PERF, read once when this module is evaluated (before the renderer is constructed):
//   tier      'high' | 'medium' | 'low'           quality tier (engine.js QUALITY3); default: the app's own choice
//   ao        true | false | 'half' | 'quarter'   GTAO: tier default / off / at 1/2 or 1/4 of the render resolution
//   aa        'traa' | 'fxaa' | 'none'            anti-aliasing (traa: false is the same as aa: 'fxaa'). Without TRAA the
//                                                 per-frame rotation of the shadow PCF taps and of the GTAO noise is
//                                                 turned off (nothing would average it; engine.js pcfTemporal)
//   bloom     true | false
//   cascades  0 | 1 | 2 | 3                       sun shadow cascades; 0 = no sun shadows (shadowMap off, no shadow passes)
//   shadow    512 | 1024 | 2048                   shadow map size per cascade
//   scale     0.2 .. 1                            fixed render scale: a fraction of CSS px x min(devicePixelRatio, the
//                                                 tier's dprMax), the same measure as the app's dynamic scale
//                                                 (js/live/app.js size()); it also turns the app's dynamic resolution off
//   gpuTime   true | false                        GPU time per frame and per pass from WebGPU 'timestamp-query' (or
//                                                 WebGL EXT_disjoint_timer_query_webgl2); default true; 'n/a' when the
//                                                 adapter does not offer it
//
// Timing (window.SFOPerf; mark() / stats() are what the benchmark page calls). Per rAF frame: the interval, the
// main-thread time of all rAF callbacks (the app's tick, js/live/app.js), and inside it: traffic.update +
// physics.resolve ('trf'), scene.frame = Renderer3.frameScene (bridges / GSE / aircraft sync) + light-sprite collection
// ('scn'), Renderer3.render ('rnd': environment, sprite upload, then Engine.render), Engine.render alone ('sub': the
// three.js RenderPipeline, i.e. encoding and submitting every pass), ui.updateLabels ('lbl', DOM); 'oth' is the rest of
// the tick (syncViews, camera rig, UI lists). Per frame from renderer.info (reset by Engine.render): draw calls,
// triangles, render passes (info.render.frameCalls). Per pass (a three.js r186 InspectorBase hook, beginRender /
// finishRender around every Renderer._renderScene): calls, draws, triangles, JS time (children excluded) and GPU time
// (the timestamp pool's per-pass durations, matched by the render-context uid). Nothing is sent anywhere.
import { THREE, TSL } from './lib.js';

const WIN = typeof window !== 'undefined' ? window : {};
const now = () => performance.now();
function readFlags() {
  let f = WIN.SFO_PERF || null;
  if (!f) { try { const q = new URLSearchParams(location.search).get('perf'); if (q) { f = JSON.parse(q); WIN.SFO_PERF = f; } } catch (e) { } }
  return f && typeof f === 'object' ? f : null;
}
const FLAGS = readFlags();

// ---------------------------------------------------------------- per-frame records
const MAX_FRAMES = 4000;
let cur = null, lastT = -1;
const newRec = (t, dt) => ({ t, dt, raf: 0, trf: 0, scn: 0, rnd: 0, sub: 0, lbl: 0, draws: 0, tris: 0, passes: 0, W: 0, H: 0 });
function timeMethod(o, k, field) {
  if (!o || typeof o[k] !== 'function' || o[k].__perf) return false;
  const f = o[k];
  const g = function () { const c = cur, t0 = now(); try { return f.apply(this, arguments); } finally { if (c) c[field] += now() - t0; } };
  g.__perf = f; o[k] = g; return true;
}
const pct = (a, p) => { if (!a.length) return 0; const s = a.slice().sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(p * s.length))]; };
const mean = (a) => { let s = 0; for (const v of a) s += v; return a.length ? s / a.length : 0; };

// pass label from what three's inspector hook gets (scene, camera, render target)
function passName(E, scene, camera, rt) {
  let n;
  if (scene && scene.isQuadMesh) n = (rt && rt.texture && rt.texture.name) || scene.name || (scene.material && scene.material.name) || 'quad';
  else if (camera && camera.isOrthographicCamera) n = 'shadow';
  else if (E && scene === E.fxScene) n = 'lights';
  else if (E && scene === E.scene) n = 'scene';
  else n = 'other:' + ((scene && (scene.name || scene.type)) || '?');
  if (rt) n += ' ' + rt.width + 'x' + rt.height + (rt.textures && rt.textures.length > 1 ? ' mrt' + rt.textures.length : '');
  else n += ' screen';
  return n;
}

export const Perf = {
  active: !!FLAGS,
  flags: FLAGS || {},
  gpuTime: !!FLAGS && FLAGS.gpuTime !== false,
  gpuSupported: false,
  frames: [], resizes: 0, markT: 0, markResizes: 0,
  passAcc: new Map(), accFrames: 0, gpuSamples: [], gpuFrames: 0, uidName: new Map(), _stack: [], _gpuN: 0, _gpuBusy: false,
  r3: null, R: null,

  // ------------------------------------------------------------ construction-time hooks
  // tier + overrides -> a copy of the tier's QUALITY3 entry (renderer3.js constructor); EngineClass.temporalShadows
  // follows TRAA
  quality(tier, table, EngineClass) {
    const f = this.flags; const t = f.tier && table[f.tier] ? f.tier : tier;
    const Q = { ...table[t] };
    if (f.ao === false || f.ao === 'off' || f.ao === 'none') Q.ao = 'none';
    else if (f.ao === 'quarter') Q.aoScale = 0.25; else if (f.ao === 'half') Q.aoScale = 0.5; else if (f.ao === 'full') Q.aoScale = 1.0;
    const aa = f.aa || (f.traa === false ? 'fxaa' : f.traa === true ? 'traa' : null);
    if (aa === 'traa' || aa === 'fxaa' || aa === 'none') { Q.traa = aa === 'traa'; Q.aa = aa; }
    if (f.bloom != null) Q.bloom = !!f.bloom;
    if (f.cascades != null) { const c = Math.max(0, Math.min(3, Math.round(+f.cascades) || 0)); if (c === 0) { Q.shadows = false; Q.cascades = 1; } else Q.cascades = c; }
    if (+f.shadow > 0) Q.shadow = Math.round(+f.shadow);
    if (EngineClass && !Q.traa) EngineClass.temporalShadows = false;
    this.Q = Q; this.tier = t;
    return { tier: t, Q };
  },
  // Q.ao === 'none' (engine.js buildPipeline): the lit pass alone, with the velocity MRT only when TRAA needs it
  scenePass(E) {
    const { pass, mrt, output, velocity } = TSL;
    const sp = pass(E.scene, E.camera); sp.name = 'scene';
    if (E.Q.traa) sp.setMRT(mrt({ output, velocity }));
    E.scenePass = sp; E.aoNode = null;
    return { color: sp, depth: sp.getTextureNode('depth'), vel: E.Q.traa ? sp.getTextureNode('velocity') : null };
  },
  // fixed render size (flags.scale): handles Renderer3.resize and returns true, or returns false (not pinned)
  resize(r3) {
    const s = +this.flags.scale; if (!this.active || !(s > 0)) return false;
    const c = r3.canvas; if (!c) return false;
    const d = Math.min(WIN.devicePixelRatio || 1, (r3.Q && r3.Q.dprMax) || 2);
    const w = Math.max(2, Math.round((c.clientWidth || 1) * d * s)), h = Math.max(2, Math.round((c.clientHeight || 1) * d * s));
    const changed = w !== r3.W || h !== r3.H || c.width !== w || c.height !== h;
    r3.W = w; r3.H = h;
    if (r3.ready && changed) { r3.engine.resize(w, h, 1); this.resizes++; }
    return true;
  },

  // ------------------------------------------------------------ timing hooks (renderer3.js constructor)
  attach(r3) {
    if (!this.active || this.r3) return;
    this.r3 = r3; WIN.SFOPerf = this;
    timeMethod(r3, 'render', 'rnd');
    const E = r3.engine, self = this, er = E.render;
    E.render = function () {
      const t0 = now();
      try { return er.apply(this, arguments); } finally {
        const c = cur; if (c) { c.sub += now() - t0; const I = this.renderer.info.render; c.draws = I.drawCalls; c.tris = I.triangles; c.passes = I.frameCalls; c.W = r3.W; c.H = r3.H; }
        self.accFrames++; self._gpuTick();
      }
    };
    Promise.resolve().then(() => r3.initP).then(() => this._onInit()).catch((e) => console.warn('[perf] init', e));
    // the app's objects exist once startApp has returned (window.SFO)
    const iv = setInterval(() => {
      const S = WIN.SFO; if (!S || !S.traffic) return; clearInterval(iv);
      timeMethod(S.traffic, 'update', 'trf'); timeMethod(S.physics, 'resolve', 'trf'); timeMethod(S.scene, 'frame', 'scn');
      if (S.ui) timeMethod(S.ui, 'updateLabels', 'lbl');
    }, 200);
    const f = this.flags;
    console.log('[perf] flags ' + JSON.stringify(f) + ' -> tier ' + r3.tier + ', ao ' + (r3.Q.ao === 'none' ? 'off' : r3.Q.ao + ' x' + r3.Q.aoScale) + ', aa ' + (r3.Q.aa || (r3.Q.traa ? 'traa' : 'none')) + ', bloom ' + !!r3.Q.bloom + ', cascades ' + (r3.Q.shadows === false ? 0 : r3.Q.cascades) + ' x ' + r3.Q.shadow);
  },
  _onInit() {
    const E = this.r3 && this.r3.engine; const R = E && E.renderer; if (!R) return;
    this.R = R;
    try { R.inspector = this._inspector(); } catch (e) { console.warn('[perf] inspector hook', e); }
    const B = R.backend || {};
    this.gpuSupported = !!(this.gpuTime && B.trackTimestamp && (B.isWebGPUBackend ? !!(B.device && B.device.features && B.device.features.has('timestamp-query')) : !!B.disjoint));
    console.log('[perf] backend ' + E.backend + ', GPU timer ' + (this.gpuSupported ? 'yes' : this.gpuTime ? 'n/a (no timestamp-query)' : 'off'));
  },
  // three r186 InspectorBase: beginRender / finishRender bracket every Renderer._renderScene (nested for the shadow
  // maps, which are rendered from inside the lit pass); the uid is the render context's timestamp-query key
  _inspector() {
    const P = this;
    class PerfInspector extends THREE.InspectorBase {
      beginRender(uid, scene, camera, rt) {
        const R = this.getRenderer(); const I = R.info.render;
        P._stack.push({ uid, name: passName(P.r3 && P.r3.engine, scene, camera, rt), d: I.drawCalls, tr: I.triangles, t: now(), cd: 0, ctr: 0, ct: 0 });
      }
      finishRender() {
        const f = P._stack.pop(); if (!f) return;
        const I = this.getRenderer().info.render;
        const dd = I.drawCalls - f.d, dt = I.triangles - f.tr, ms = now() - f.t;
        const a = P._pass(f.name); a.n++; a.draws += dd - f.cd; a.tris += dt - f.ctr; a.ms += ms - f.ct;
        const up = P._stack[P._stack.length - 1]; if (up) { up.cd += dd; up.ctr += dt; up.ct += ms; }
        if (P.gpuSupported) { P.uidName.set(f.uid, f.name); if (P.uidName.size > 6000) { let k = 0; for (const key of P.uidName.keys()) { P.uidName.delete(key); if (++k >= 3000) break; } } }
      }
    }
    return new PerfInspector();
  },
  _pass(name) { let a = this.passAcc.get(name); if (!a) { a = { n: 0, draws: 0, tris: 0, ms: 0, gpu: 0, gpuN: 0 }; this.passAcc.set(name, a); } return a; },
  // GPU time: resolve the timestamp pool every 3rd frame (async map; three returns the previous value while one is
  // pending) and read the per-pass durations it keeps (pool.timestamps: uid 'r:<call>:<context>:f<frame>' -> ms)
  _gpuTick() {
    if (!this.gpuSupported || this._gpuBusy || !this.R) return;
    if ((++this._gpuN % 3) !== 0) return;
    this._gpuBusy = true;
    Promise.resolve(this.R.resolveTimestampsAsync('render')).then((total) => this._gpuCollect(total)).catch(() => { }).finally(() => { this._gpuBusy = false; });
  },
  _gpuCollect(total) {
    const B = this.R.backend; const pool = B && B.timestampQueryPool && B.timestampQueryPool.render; const ts = pool && pool.timestamps;
    const ok = (ms) => ms >= 0 && ms < 2000; // an end before its begin (reset counters) or a stale slot reads as garbage
    if (ts && ts.size) {
      const byFrame = new Map();
      for (const [uid, ms] of ts) {
        if (!ok(ms)) continue;
        const m = /:f(\d+)$/.exec(uid); const fr = m ? m[1] : '?';
        byFrame.set(fr, (byFrame.get(fr) || 0) + ms);
        const name = this.uidName.get(uid); if (name) { const a = this._pass(name); a.gpu += ms; a.gpuN++; }
      }
      const t = now(); for (const v of byFrame.values()) this.gpuSamples.push({ t, ms: v });
      this.gpuFrames += byFrame.size;
    } else if (ok(total) && total > 0) { this.gpuSamples.push({ t: now(), ms: total }); this.gpuFrames++; }
    if (this.gpuSamples.length > 3000) this.gpuSamples.splice(0, this.gpuSamples.length - 3000);
  },

  // ------------------------------------------------------------ measurement windows (the benchmark page)
  mark() { this.markT = now(); this.passAcc = new Map(); this.accFrames = 0; this.gpuFrames = 0; this.markResizes = this.resizes; this._stack.length = 0; return this.markT; },
  // frames closed since mark(): fps, interval percentiles, long frames, mean CPU split, draws, GPU
  stats(t0 = this.markT) {
    const F = this.frames.filter((f) => f.t > t0 && f.dt > 0);
    const out = { n: F.length, W: this.r3 ? this.r3.W : 0, H: this.r3 ? this.r3.H : 0, resizes: this.resizes - this.markResizes };
    if (!F.length) return out;
    const dt = F.map((f) => f.dt); const sum = dt.reduce((s, v) => s + v, 0);
    out.fps = +(1000 * F.length / sum).toFixed(1); out.p50 = +pct(dt, 0.5).toFixed(1); out.p95 = +pct(dt, 0.95).toFixed(1); out.max = +Math.max(...dt).toFixed(0);
    out.long = dt.filter((v) => v > 50).length;
    const m = (k) => +mean(F.map((f) => f[k])).toFixed(2);
    out.cpu = { tick: m('raf'), tick95: +pct(F.map((f) => f.raf), 0.95).toFixed(1), trf: m('trf'), scn: m('scn'), rnd: m('rnd'), sub: m('sub'), lbl: m('lbl') };
    out.cpu.oth = +Math.max(0, out.cpu.tick - out.cpu.trf - out.cpu.scn - out.cpu.rnd - out.cpu.lbl).toFixed(2);
    out.draws = Math.round(mean(F.map((f) => f.draws))); out.tris = Math.round(mean(F.map((f) => f.tris))); out.passes = +mean(F.map((f) => f.passes)).toFixed(1);
    const G = this.gpuSamples.filter((g) => g.t > t0).map((g) => g.ms);
    out.gpu = this.gpuSupported ? (G.length ? { mean: +mean(G).toFixed(2), p95: +pct(G, 0.95).toFixed(2), n: G.length } : null) : 'n/a';
    const k = Math.max(1, this.accFrames), kg = Math.max(1, this.gpuFrames);
    out.pass = [...this.passAcc].map(([name, a]) => ({ name, n: +(a.n / k).toFixed(2), draws: +(a.draws / k).toFixed(1), tris: Math.round(a.tris / k), ms: +(a.ms / k).toFixed(2), gpu: this.gpuSupported && a.gpuN ? +(a.gpu / kg).toFixed(2) : null }))
      .sort((x, y) => ((y.gpu || 0) - (x.gpu || 0)) || (y.ms - x.ms));
    return out;
  },
  describe() {
    const r3 = this.r3, E = r3 && r3.engine, Q = (r3 && r3.Q) || {}; const c = r3 && r3.canvas;
    return { backend: E && E.backend, reversed: !!(E && E.reversed), tier: r3 && r3.tier, W: r3 && r3.W, H: r3 && r3.H,
      css: c ? [c.clientWidth, c.clientHeight] : null, dpr: WIN.devicePixelRatio || 1,
      ao: Q.ao === 'none' ? 'off' : Q.ao + ' x' + Q.aoScale, aa: Q.aa || (Q.traa ? 'traa' : 'none'), bloom: !!Q.bloom,
      cascades: Q.shadows === false ? 0 : Q.cascades, shadow: Q.shadow, scale: +this.flags.scale || null,
      gpuTimer: this.gpuSupported ? 'yes' : this.gpuTime ? 'n/a' : 'off' };
  },
};

// rAF: every callback is timed (the app's tick is the one that matters; the others are tiny); callbacks of one display
// frame share its timestamp, so a new timestamp closes the previous frame's record
if (Perf.active && typeof WIN.requestAnimationFrame === 'function') {
  const raf = WIN.requestAnimationFrame.bind(WIN);
  WIN.requestAnimationFrame = function (cb) {
    return raf(function (t) {
      if (t !== lastT) {
        if (cur) { Perf.frames.push(cur); if (Perf.frames.length > MAX_FRAMES) Perf.frames.splice(0, Perf.frames.length - MAX_FRAMES); }
        cur = newRec(t, lastT >= 0 ? t - lastT : 0); lastT = t;
      }
      const c = cur, t0 = now();
      try { return cb(t); } finally { c.raf += now() - t0; }
    });
  };
}
