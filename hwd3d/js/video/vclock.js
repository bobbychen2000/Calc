// Virtual clock for the OD3 video pipeline (hwd3d Phase 3, video). A CLASSIC script (not a module): the Playwright driver
// (tools/video/render.mjs) injects it with page.addInitScript before any page script runs, followed by
// `installVClock({ t0, perf0, seed })`. dev/video.html loads it with a plain <script> for the interactive preview.
//
// What it replaces, so the UNMODIFIED app (live.html) runs on a clock the driver owns:
//   Date.now() and `new Date()` (no arguments) -> the virtual wall clock `wall` (epoch ms): the traffic engine
//       (app.js engineNow), the replay shim's head (out/replay/replay_shim.js: data time = wall - offset), the METAR clock;
//   performance.now()        -> the virtual frame clock `perf` (ms): app.js tick() takes its frame dt from it;
//   requestAnimationFrame / cancelAnimationFrame -> a queue that runs ONLY when the driver calls vclock.frame();
//   setTimeout / setInterval with a delay > 0 -> timers on the virtual WALL timeline, fired in due order (ties: creation
//       order) by vclock.advance(); a delay <= 0 is passed to the real setTimeout (boot continuations, the shim's history
//       hand-off) - they run at the next real task, which the driver lets through between steps (vclock.settle);
//   Math.random              -> a seeded PRNG (mulberry32): the drawables' animation seeds (placeholder.js /
//       detailed.js `seed`) are then the same in every run.
// The two clocks are decoupled on purpose: a time-lapse frame advances `wall` by k x dt (the engine and the shim follow
// it, in sub-steps) but `perf` by one dt only, so the app's frame callback gets dt = the last sub-step and its own
// per-frame state (prop / lights animation time simT, the 30-s environment refresh) runs at video rate.
// Nothing here talks to the network or writes anything; no identity passes through it.
(function () {
  'use strict';
  if (window.__vclock) return;
  const W = window, RealDate = W.Date;
  const real = {
    setTimeout: W.setTimeout.bind(W), clearTimeout: W.clearTimeout.bind(W),
    setInterval: W.setInterval.bind(W), clearInterval: W.clearInterval.bind(W),
    raf: W.requestAnimationFrame ? W.requestAnimationFrame.bind(W) : null,
    perfNow: performance.now.bind(performance), dateNow: RealDate.now, random: Math.random,
  };
  function mulberry32(a) {
    return function () { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  function installVClock({ t0 = 1.7e12, perf0 = 1000, seed = 0x5eed, passZero = true } = {}) {
    if (W.__vclock) return W.__vclock;
    let wall = +t0, perf = +perf0;
    const timers = new Map();   // id -> {id, due, seq, fn, args, every}
    const rafs = new Map();     // id -> cb
    let nextId = 1, seq = 0, nextRaf = 1, fired = 0, framesRun = 0;
    // ---- Date
    function VDate(...a) {
      if (!new.target) return new RealDate(wall).toString();
      return a.length ? new RealDate(...a) : new RealDate(wall);
    }
    VDate.prototype = RealDate.prototype;
    VDate.now = () => wall; VDate.parse = RealDate.parse; VDate.UTC = RealDate.UTC;
    Object.defineProperty(VDate, Symbol.hasInstance, { value: (x) => x instanceof RealDate });
    W.Date = VDate;
    // ---- performance.now
    try { performance.now = () => perf; } catch (e) { Object.defineProperty(performance, 'now', { value: () => perf, configurable: true }); }
    // ---- Math.random
    Math.random = mulberry32(seed >>> 0);
    // ---- timers
    const realIds = new Map();  // virtual id -> real handle (delay <= 0)
    W.setTimeout = function (fn, d, ...args) {
      const id = nextId++; d = +d || 0;
      if (typeof fn !== 'function') { const src = String(fn); fn = () => (0, eval)(src); }
      if (d <= 0 && passZero) { realIds.set(id, real.setTimeout(() => { realIds.delete(id); fn(...args); }, 0)); return id; }
      timers.set(id, { id, due: wall + Math.max(0, d), seq: seq++, fn, args, every: 0 }); return id;
    };
    W.setInterval = function (fn, d, ...args) {
      const id = nextId++; d = Math.max(1, +d || 0);
      if (typeof fn !== 'function') { const src = String(fn); fn = () => (0, eval)(src); }
      timers.set(id, { id, due: wall + d, seq: seq++, fn, args, every: d }); return id;
    };
    W.clearTimeout = W.clearInterval = function (id) {
      if (id == null) return;
      timers.delete(id);
      const r = realIds.get(id); if (r != null) { real.clearTimeout(r); realIds.delete(id); }
    };
    // ---- rAF
    W.requestAnimationFrame = function (cb) { const id = nextRaf++; rafs.set(id, cb); return id; };
    W.cancelAnimationFrame = function (id) { rafs.delete(id); };
    // ---- driver API
    const earliest = (limit) => { let b = null; for (const t of timers.values()) if (t.due <= limit && (!b || t.due < b.due || (t.due === b.due && t.seq < b.seq))) b = t; return b; };
    const api = {
      real, mulberry32,
      get wall() { return wall; }, get perf() { return perf; },
      /** advance the wall clock to `to` (ms), firing every virtual timer that falls due on the way, each at its own due
       *  time; returns the number of callbacks run */
      advanceTo(to) {
        let n = 0;
        for (;;) {
          const t = earliest(to); if (!t) break;
          wall = Math.max(wall, t.due);
          if (t.every) { t.due += t.every; t.seq = seq++; } else timers.delete(t.id);
          try { t.fn(...t.args); } catch (e) { console.error('vclock timer', e); }
          n++; if (n > 1e6) throw new Error('vclock: runaway timers');
        }
        if (to > wall) wall = to;
        fired += n; return n;
      },
      advance(ms) { return api.advanceTo(wall + ms); },
      /** advance the frame clock (performance.now) by ms */
      tickPerf(ms) { perf += ms; return perf; },
      /** run the queued animation-frame callbacks once (the ones queued during the run wait for the next call) */
      frame() {
        const cbs = [...rafs.values()]; rafs.clear(); framesRun++;
        for (const cb of cbs) { try { cb(perf); } catch (e) { console.error('vclock frame', e); } }
        return cbs.length;
      },
      /** let pending real tasks (0-delay timers, promise chains of fetch / Response bodies) run: n real macrotasks */
      settle(n = 2) { return new Promise((res) => { let k = 0; const go = () => (++k >= n ? res() : real.setTimeout(go, 0)); real.setTimeout(go, 0); }); },
      pendingRaf: () => rafs.size,
      timers: () => [...timers.values()].map(t => ({ due: t.due, every: t.every })),
      stats: () => ({ wall, perf, timers: timers.size, fired, frames: framesRun, raf: rafs.size }),
    };
    W.__vclock = api;
    return api;
  }
  W.installVClock = installVClock;
})();
