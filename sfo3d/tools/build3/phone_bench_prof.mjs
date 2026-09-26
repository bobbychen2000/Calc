// livetest.mjs job: phone-profile benchmark of live3.html (three.js renderer) in headless Chromium.
// Loads the page with the in-page probe (tools/build3/phone_bench_prof_probe.js) injected before the app starts, then per
// named view: per-frame main-thread time split by phase, per-pass draw calls / triangles, renderer debugInfo(), a scene
// census and (PROFILE=1) a CDP sampling CPU profile aggregated by function. Results: <OUT>/<LABEL>.json + a text summary.
//   SOFTGL=1 MOBILE=1 W=430 H=932 DPR=3 OUT=out/perf LABEL=low PAGE="live3.html?tier=low" PROFILE=1 DEBUG3=1 \
//     node livetest.mjs tools/build3/phone_bench_prof.mjs
// Env: PAGE (default live3.html), QS (default mode=snapshot), PERF (JSON -> window.SFO_PERF before the app starts),
//      VIEWS (';'-separated: overview | gate:<stand>,<d>,<side>,<pitch> | tower | hold:<i>,<d> | ac:<hex|ual>,<d> | look:x,y,z,yaw,pitch,dist),
//      WARM (frames before measuring, default 6), FRAMES (measured frames per view, default 20), PROFILE=1 (CPU profile,
//      another FRAMES frames), DEBUG3=1 (serve the unminified three.js build so profiles have function names),
//      SHOTS=1 (screenshot per view), LABEL (output name).
// Docs: docs/research/mobile_perf.md. Rendering here is CPU-only (llvmpipe / SwiftShader): frame intervals say nothing
// about a phone GPU; main-thread JS times, draw calls, passes and memory are the meaningful numbers.
import fs from 'fs'; import path from 'path'; import { fileURLToPath } from 'url';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');

export default async ({ page, shot, base, OUT }) => {
  const pg = process.env.PAGE || 'live3.html';
  const label = process.env.LABEL || 'bench';
  const N = +(process.env.FRAMES || 20), WARM = +(process.env.WARM || 6);
  const t0 = Date.now(); const el = () => ((Date.now() - t0) / 1000).toFixed(0) + ' s';
  let crashed = false; page.on('crash', () => { crashed = true; console.log('PAGE CRASHED at', el()); });
  const guard = setInterval(() => { if (crashed) process.exit(3); }, 2000);
  if (process.env.PERF) await page.addInitScript((j) => { window.SFO_PERF = JSON.parse(j); }, process.env.PERF);
  await page.addInitScript({ path: path.join(HERE, 'phone_bench_prof_probe.js') });
  if (process.env.DEBUG3) await page.route('**/vendor/three/three.module.js', (r) => r.fulfill({ path: path.join(ROOT, 'vendor/three/three.debug.js'), contentType: 'text/javascript' }));
  await page.goto(base + pg + (pg.includes('?') ? '&' : '?') + (process.env.QS || 'mode=snapshot'));
  await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 0, polling: 500 });
  const err = await page.evaluate(() => window.__sfoError); if (err) throw new Error(err);
  console.log('app ready', el());
  await page.evaluate(async () => { await Promise.all(SFO.scene.aircraft.map(a => a.ready)); });
  await page.waitForFunction(() => SFO.R.isComplete && SFO.R.isComplete() && SFO.R.frames > 3, null, { timeout: 0, polling: 500 });
  await page.evaluate(() => SFOProbe.install());
  console.log('renderer complete', el(), JSON.stringify(await page.evaluate(() => ({ backend: SFO.R.engine.backend, tier: SFO.R.tier, W: SFO.R.W, H: SFO.R.H, canvas: [SFO.R.canvas.width, SFO.R.canvas.height], perf: window.SFO_PERF || null }))));
  const frames = async (n) => { const f0 = await page.evaluate(() => SFO.R.frames); await page.waitForFunction(([f, n]) => SFO.R.frames >= f + n, [f0, n], { timeout: 0, polling: 100 }); };
  const census = () => page.evaluate(() => {
    const E = SFO.R.engine; const out = { groups: {}, programs: null };
    const vis = (o) => { for (let p = o; p; p = p.parent) if (!p.visible) return false; return true; };
    for (const ch of E.scene.children) {
      let n = 0, v = 0, cs = 0, inst = 0, tris = 0; const mats = new Set();
      ch.traverse(o => { if (!o.isMesh) return; n++; const V = vis(o); if (V) { v++; if (o.castShadow) cs++; if (o.isInstancedMesh) inst += o.count; const g = o.geometry; tris += g.index ? g.index.count / 3 : (g.attributes.position ? g.attributes.position.count / 3 : 0); } (Array.isArray(o.material) ? o.material : [o.material]).forEach(m => mats.add(m)); });
      const k = (ch.name || ch.type) + (out.groups[ch.name || ch.type] ? '#' + ch.id : ''); out.groups[k] = { meshes: n, visible: v, casters: cs, instances: inst, trisVisible: Math.round(tris), materials: mats.size };
    }
    try { const R = E.renderer; out.programs = R._pipelines && R._pipelines.programs ? { vertex: R._pipelines.programs.vertex.size, fragment: R._pipelines.programs.fragment.size } : null; } catch (e) { }
    out.aircraft = SFO.scene.aircraft.length; out.tracks = SFO.traffic.tracks.size;
    let sprites = 0; try { sprites = SFO.R.sprites.n; } catch (e) { } out.sprites = sprites;
    out.gates = { items: SFO.gateSys.items ? SFO.gateSys.items(Date.now()).length : null };
    out.labels = document.querySelectorAll('#labels > *, .lbl').length;
    return out;
  });
  const results = { label, page: pg, perf: process.env.PERF ? JSON.parse(process.env.PERF) : null, views: [] };
  results.census0 = await census();
  let cdp = null;
  if (process.env.PROFILE) { cdp = await page.context().newCDPSession(page); await cdp.send('Profiler.enable'); await cdp.send('Profiler.setSamplingInterval', { interval: 250 }); }
  const views = (process.env.VIEWS || 'overview;gate:B26,60,1,14;tower;hold:12,60').split(';').filter(Boolean);
  for (const v of views) {
    const [k, argS] = v.split(':'); const a = argS ? argS.split(',') : [];
    const ok = await page.evaluate(([k, a]) => {
      const q = SFO.qa;
      if (k === 'overview') { SFO.view('overview'); SFO.rig.anim && (SFO.rig.anim.t = 99); SFO.rig.update(0); return true; }
      if (k === 'gate') return q.gate(a[0], +(a[1] || 38), +(a[2] || 1), +(a[3] || 9));
      if (k === 'tower') return q.tower();
      if (k === 'hold') return q.hold(+a[0], +(a[1] || 32));
      if (k === 'ac') { let h = a[0]; if (h === 'ual') { const t = q.tracks().find(t => t.gate && /^UAL/.test(t.flight || '')); h = t && t.hex; } return h ? q.aircraft(h, +(a[1] || 60)) : false; }
      if (k === 'look') { q.look([+a[0], +a[1], +a[2]], +a[3], +a[4], +a[5], 50); return true; }
      return false;
    }, [k, a]);
    if (!ok) { console.log('view failed', v); continue; }
    await frames(WARM);
    await page.evaluate(() => SFOProbe.mark());
    const tv = Date.now(); await frames(N);
    const sum = await page.evaluate(() => SFOProbe.summary());
    const passes = await page.evaluate(() => SFOProbe.collectPasses(3));
    const info = await page.evaluate(() => ({ ...SFO.R.debugInfo(), jsHeapMB: performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1048576) : null }));
    delete info.aircraft; delete info.flood;
    const rec = { view: v, wallS: (Date.now() - tv) / 1000, summary: sum, passes, info, census: await census() };
    if (cdp) {
      await cdp.send('Profiler.start'); await frames(N); const { profile } = await cdp.send('Profiler.stop');
      rec.profile = aggregate(profile);
      fs.writeFileSync(path.join(OUT, `${label}_${v.replace(/\W+/g, '_')}.cpuprofile`), JSON.stringify(profile));
    }
    results.views.push(rec);
    console.log(`\n== ${label} ${v}: ${sum.frames} frames, tick p50 ${sum.cpu && sum.cpu.p50.toFixed(1)} ms mean ${sum.cpu && sum.cpu.mean.toFixed(1)} ms; interval mean ${sum.dt && sum.dt.mean.toFixed(0)} ms`);
    console.log('phases', JSON.stringify(sum.ph));
    console.log('passes', JSON.stringify(passes));
    console.log('info', JSON.stringify(info));
    if (rec.profile) console.log('profile top self', JSON.stringify(rec.profile.top.slice(0, 25)), '\nby file', JSON.stringify(rec.profile.files.slice(0, 12)));
    if (process.env.SHOTS) await shot(`${label}_${v.replace(/\W+/g, '_')}`);
  }
  fs.writeFileSync(path.join(OUT, label + '.json'), JSON.stringify(results, null, 1));
  console.log('wrote', path.join(OUT, label + '.json'), el());
  clearInterval(guard);
};

// CDP profile -> self time per function and per file (ms and share of sampled time; idle and GC reported separately)
function aggregate(profile) {
  const byId = new Map(profile.nodes.map(n => [n.id, n]));
  const self = new Map(); let total = 0;
  for (let i = 0; i < profile.samples.length; i++) { const id = profile.samples[i]; const d = (profile.timeDeltas[i] || 0) / 1000; self.set(id, (self.get(id) || 0) + d); total += d; }
  const fn = new Map(), files = new Map(); let idle = 0, gc = 0, program = 0;
  for (const [id, ms] of self) {
    const cf = byId.get(id).callFrame; const name = cf.functionName || '(anon)';
    if (name === '(idle)') { idle += ms; continue; } if (name === '(garbage collector)') { gc += ms; continue; } if (name === '(program)') { program += ms; continue; }
    const file = (cf.url || '').replace(/^.*\/(?=[^/]+\/[^/]+$)/, '');
    const key = name + ' ' + file + ':' + (cf.lineNumber + 1);
    fn.set(key, (fn.get(key) || 0) + ms); files.set(file, (files.get(file) || 0) + ms);
  }
  const busy = total - idle;
  const top = [...fn].sort((a, b) => b[1] - a[1]).slice(0, 60).map(([k, ms]) => [k, +ms.toFixed(1), +(100 * ms / busy).toFixed(1)]);
  const fl = [...files].sort((a, b) => b[1] - a[1]).slice(0, 30).map(([k, ms]) => [k, +ms.toFixed(1), +(100 * ms / busy).toFixed(1)]);
  return { totalMs: +total.toFixed(0), idleMs: +idle.toFixed(0), gcMs: +gc.toFixed(1), programMs: +program.toFixed(1), top, files: fl };
}
