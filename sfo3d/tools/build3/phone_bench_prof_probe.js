// In-page performance probe for SFO Live 3D (live3.html / the phone-test artifact). Plain script, no modules: it is
// injected before the app starts (Playwright addInitScript in tools/build3/phone_bench_prof.mjs, or inlined in the
// phone-test page), so it can time the app's own rAF loop.
// What it measures (docs/research/mobile_perf.md):
//   - per frame: the rAF interval of the app's loop (js/live/app.js `function tick`) and the main-thread time of that
//     tick (JS + whatever the browser makes the tick wait for, e.g. a WebGPU getCurrentTexture() that blocks while all
//     drawables are queued on the GPU: that is GPU back-pressure, not JS work);
//   - per frame, split by phase, by wrapping the app's objects once they exist (window.SFO): traffic.update,
//     physics.resolve, rig.update, scene.frame (-> Renderer3.frameScene -> AircraftRenderer.sync, Bridges3.update ->
//     LiveGateSystem.items; aircraft light sprites; each static light-sprite source), Renderer3.render (-> sprite
//     upload, Engine.render = the three.js RenderPipeline), scene.commit, ui.updateLabels, ui.renderList and the other
//     UI setters. Anything else in the tick (the app's syncViews, the dynamic-resolution controller, ...) is 'other';
//   - per render pass (three.js Renderer._renderScene, nested: shadow maps are rendered from inside the lit pass): the
//     pass's own draw calls and triangles, its JS time, the target size and attachment count (collectPasses()).
// Nothing is sent anywhere; results are read with SFOProbe.summary() / SFOProbe.passes().
(function () {
  if (window.SFOProbe) return;
  var now = function () { return performance.now(); };
  var P = window.SFOProbe = { frames: [], cur: null, maxFrames: 3000, wrapped: [], passRec: null, markT: 0 };
  // ---------------------------------------------------------------- rAF: the app's loop is `function tick()`
  var raf = window.requestAnimationFrame.bind(window);
  var lastTickT = 0;
  window.requestAnimationFrame = function (cb) {
    if (!cb || cb.name !== 'tick') return raf(cb);
    return raf(function (t) {
      var t0 = now(); P.cur = { t: t0, dt: lastTickT ? t - lastTickT : 0, ph: {} }; lastTickT = t;
      try { cb(t); } finally {
        var f = P.cur; f.cpu = now() - t0; P.cur = null; P.frames.push(f);
        if (P.frames.length > P.maxFrames) P.frames.splice(0, P.frames.length - P.maxFrames);
      }
    });
  };
  // ---------------------------------------------------------------- phase wrappers
  function wrap(o, k, label) {
    if (!o || typeof o[k] !== 'function' || o[k].__probe) return false;
    var f = o[k];
    var g = function () {
      var c = P.cur; if (!c) return f.apply(this, arguments);
      var t0 = now();
      try { return f.apply(this, arguments); } finally { c.ph[label] = (c.ph[label] || 0) + now() - t0; }
    };
    g.__probe = f; o[k] = g; P.wrapped.push(label); return true;
  }
  P.wrap = wrap;
  function install() {
    var S = window.SFO; if (!S || !S.R) return false;
    var R = S.R;
    wrap(S.traffic, 'update', 'traffic');
    wrap(S.physics, 'resolve', 'physics');
    wrap(S.rig, 'update', 'rig');
    wrap(S.scene, 'frame', 'scene.frame');
    wrap(S.scene, 'commit', 'commit');
    wrap(R, 'frameScene', 'frameScene');
    wrap(R, 'render', 'R.render');
    if (R.engine) wrap(R.engine, 'render', 'E.render');
    if (R.acr) wrap(R.acr, 'sync', 'acr.sync');
    if (R.bridges) wrap(R.bridges, 'update', 'bridges');
    if (R.sprites) { wrap(R.sprites, 'end', 'sprites.end'); }
    wrap(S.gateSys, 'items', 'gates.items');
    wrap(S.ui, 'updateLabels', 'labels');
    wrap(S.ui, 'renderList', 'ui.list');
    ['setStatus', 'setStats', 'setClock', 'setAtc', 'renderCard', 'setStatsSheet'].forEach(function (k) { wrap(S.ui, k, 'ui.other'); });
    // aircraft light sprites (scene.frame's own loop) and each static sprite source
    if (S.scene && S.scene.aircraft && !S.scene.__probeAc) {
      S.scene.__probeAc = true;
      var proto = S.scene.aircraft[0] && Object.getPrototypeOf(S.scene.aircraft[0]);
      if (proto && proto.lightSprites && !proto.lightSprites.__probe) wrap(proto, 'lightSprites', 'ac.lightSprites');
    }
    if (S.scene && S.scene.staticLights) S.scene.staticLights.forEach(function (fn, i) {
      if (typeof fn !== 'function' || fn.__probe) return;
      var w = { f: fn }; wrap(w, 'f', 'lights.static' + i); S.scene.staticLights[i] = w.f;
    });
    // three.js passes
    var E = R.engine;
    if (E && E.renderer && !E.renderer.__probePass) {
      var TR = E.renderer; TR.__probePass = true; var orig = TR._renderScene; var stack = [];
      TR._renderScene = function (scene, camera, useFB) {
        var rec = P.passRec; if (!rec) return orig.apply(this, arguments);
        var I = this.info.render; var d0 = I.drawCalls, tr0 = I.triangles, t0 = now();
        var rt = this.getRenderTarget(); var mrt = this.getMRT && this.getMRT();
        var name;
        if (scene && scene.isQuadMesh) name = 'quad:' + ((scene.material && scene.material.name) || (rt && rt.texture && rt.texture.name) || '?');
        else if (camera && camera.isOrthographicCamera) name = 'shadow';
        else if (scene === E.fxScene) name = 'lights';
        else if (scene === E.scene) name = 'scene' + (mrt ? '+mrt' : '');
        else name = 'other:' + (scene && (scene.name || scene.type));
        if (rt) name += ' ' + rt.width + 'x' + rt.height + (rt.textures && rt.textures.length > 1 ? ' x' + rt.textures.length : '');
        else name += ' canvas';
        var fr = { child: 0, childT: 0, childTr: 0 }; stack.push(fr);
        try { return orig.apply(this, arguments); } finally {
          stack.pop(); var dd = I.drawCalls - d0, dt = I.triangles - tr0, ms = now() - t0;
          var e = rec[name] || (rec[name] = { n: 0, draws: 0, tris: 0, ms: 0 });
          e.n++; e.draws += dd - fr.child; e.tris += dt - fr.childTr; e.ms += ms - fr.childT;
          var up = stack[stack.length - 1]; if (up) { up.child += dd; up.childTr += dt; up.childT += ms; }
        }
      };
    }
    return !!(R.acr && R.bridges);
  }
  var iv = setInterval(function () { try { if (install()) clearInterval(iv); } catch (e) { console.warn('[probe]', e); } }, 250);
  P.install = install;
  // ---------------------------------------------------------------- results
  function pct(a, p) { if (!a.length) return 0; var s = a.slice().sort(function (x, y) { return x - y; }); return s[Math.min(s.length - 1, Math.floor(p * s.length))]; }
  P.pct = pct;
  P.mark = function () { P.markT = now(); };
  // frames since the last mark(): intervals, tick time, phases (mean / p50 / p95 ms)
  P.summary = function (since) {
    var t = since != null ? since : P.markT; var F = P.frames.filter(function (f) { return f.t >= t && f.dt > 0; });
    var out = { frames: F.length }; if (!F.length) return out;
    var dt = F.map(function (f) { return f.dt; }), cpu = F.map(function (f) { return f.cpu; });
    var mean = function (a) { var s = 0; for (var i = 0; i < a.length; i++) s += a[i]; return s / a.length; };
    out.fps = 1000 / mean(dt); out.dt = { mean: mean(dt), p50: pct(dt, 0.5), p95: pct(dt, 0.95) }; out.cpu = { mean: mean(cpu), p50: pct(cpu, 0.5), p95: pct(cpu, 0.95) };
    var keys = {}; F.forEach(function (f) { for (var k in f.ph) keys[k] = 1; });
    out.ph = {};
    Object.keys(keys).forEach(function (k) { var a = F.map(function (f) { return f.ph[k] || 0; }); out.ph[k] = { mean: +mean(a).toFixed(2), p95: +pct(a, 0.95).toFixed(2), max: +Math.max.apply(null, a).toFixed(2) }; });
    // 'other' = tick time not inside any top-level phase
    var top = ['traffic', 'physics', 'rig', 'scene.frame', 'R.render', 'commit', 'labels', 'ui.list', 'ui.other'];
    var oth = F.map(function (f) { var s = f.cpu; top.forEach(function (k) { s -= f.ph[k] || 0; }); return s; });
    out.ph.other = { mean: +mean(oth).toFixed(2), p95: +pct(oth, 0.95).toFixed(2), max: +Math.max.apply(null, oth).toFixed(2) };
    return out;
  };
  // per-pass stats over the next n app frames (resolves with {passes: {name: {n, draws, tris, ms} per frame}, frames})
  P.collectPasses = function (n) {
    return new Promise(function (res) {
      var rec = {}; var f0 = P.frames.length; P.passRec = rec;
      var chk = setInterval(function () {
        if (P.frames.length - f0 < n) return; clearInterval(chk); P.passRec = null;
        var k = P.frames.length - f0; var out = {};
        Object.keys(rec).forEach(function (name) { var e = rec[name]; out[name] = { n: +(e.n / k).toFixed(2), draws: +(e.draws / k).toFixed(1), tris: Math.round(e.tris / k), ms: +(e.ms / k).toFixed(2) }; });
        res({ frames: k, passes: out });
      }, 50);
    });
  };
})();
