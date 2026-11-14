// OD3 video driver (hwd3d Phase 3, video): deterministic frame-by-frame capture of the UNMODIFIED app under a virtual
// clock, a scripted cinematic camera planned from the engine's own trace, a caption overlay, and the encode - all from a
// FROZEN SNAPSHOT of the app (out/video/<case>/app/), so a render that is split, resumed or run for hours while the fix
// rounds edit js/** and the models can never mix engine, renderer or model versions.
//
//   node tools/video/render.mjs <job.json> <stage> [options]
//   stages:  snapshot   copy the app (live.html, live.css, js/**, data/**, the replay shim, the job's pack and anything else a
//                       probe boot requested) to out/video/<case>/app/ + MANIFEST.json (sha256 per file, tree hash);
//                       refuses to replace an existing snapshot without --refresh (a new snapshot = scout + plan again)
//            scout      engine-only run of the whole timeline (no GPU frames): the hero's pose per frame
//                       -> out/video/<case>/trace.json (+ the derived events, printed)
//            plan       the camera and the caption of every frame from the trace and the shot list (js/video/camera.js,
//                       js/video/provenance.js) -> out/video/<case>/cams.json + the per-shot report and its gates (printed)
//            render     PNG frames 1920x1080 -> out/video/<case>/frames/%05d.png; resumable (frames on disk are skipped -
//                       the state still advances through them) and splittable (--frames=a-b; --test=<name> = a job test range)
//            encode     ffmpeg libx264 -crf 16 -preset slow -pix_fmt yuv420p -r 30 +faststart -> out/video/<case>/<name>.mp4;
//                       refuses a missing frame or a frames directory of another plan, checks the encoded frame count
//            stills     3 stills per clip with ffmpeg -> out/video/<case>/<name>_still<k>.png
//            determinism  the same range rendered by two fresh browser runs (and once after rendering earlier frames):
//                       sha256 of every PNG must match
//   options: --frames=a-b  --test=<name>  --pick=f1,f2,.. [--dir=picks]  --force (re-render frames of THIS plan)
//            --clean (empty a frames directory that holds another plan's frames)  --nogate (render a plan whose gates fail)
//            --refresh (snapshot: replace)  --out=<dir>  --name=<clip>  --lead=<n> (determinism)
// Stamps, chained: trace.json carries scoutKey = sha256(snapshot tree + the job's scout fields); cams.json carries
// planKey = sha256(scoutKey + sha256(trace.json) + the job's plan fields); a frames directory's PLAN_STAMP =
// sha256(planKey + the render fields: size, shutter, overlay options). Every stage recomputes the key it builds on and
// refuses a mismatch. A render aborts when the hero is more than job.maxDevM (default 0.01 m) from its scout pose, when
// its phase or label differs from the scout's, when the page logs an error, or when the server misses a file / serves a
// byte that differs from the manifest.
// The job (out/od3/video_<case>.json, gitignored: it holds the window times) is described in docs/phase3_video.md.
// D1: the hero is chosen in the page by rule (type + event in the window) from a type-only pack; no key, registration or
// callsign is printed, written or shown. Ports 8700-8749 only.
import fs from 'node:fs'; import path from 'node:path'; import os from 'node:os'; import { spawnSync } from 'node:child_process'; import { pathToFileURL } from 'node:url';
import { ROOT, log, startServer, launch, bootApp, readPack, epochOf, VIDEO_SEED, sha256, SNAP_BASE, listFiles, makeSnapshot, verifySnapshot } from './lib.mjs';

const argv = process.argv.slice(2); const opt = (k, d) => { const a = argv.find(x => x.startsWith('--' + k + '=')); return a ? a.slice(k.length + 3) : (argv.includes('--' + k) ? true : d); };
const jobFile = argv[0], stage = argv[1] || 'all';
if (!jobFile || !fs.existsSync(jobFile)) { console.error('usage: node tools/video/render.mjs <job.json> <snapshot|scout|plan|render|encode|stills|determinism|all> [--frames=a-b] [--test=name]'); process.exit(2); }
const job = JSON.parse(fs.readFileSync(jobFile, 'utf8'));
const OUTD = path.resolve(ROOT, opt('out', job.out || `out/video/${job.case}`)); fs.mkdirSync(OUTD, { recursive: true });
if (!path.relative(path.join(ROOT, 'out'), OUTD).split(path.sep).every(p => p !== '..')) throw new Error('--out must be under hwd3d/out/ (gitignored)');
const SNAP = path.join(OUTD, 'app');
const FPS = job.fps || 30, [VW, VH] = job.size || [1920, 1080];
const SEED = job.seed ?? VIDEO_SEED, SHUTTER = job.shutter ?? 0.5, MAXDEV = job.maxDevM ?? 0.01;
const OVO = { timeOnly: !!job.timeOnly, endDate: !!job.endDate };
const T = (v) => typeof v === 'number' ? v : Date.parse(/Z$|[+-]\d\d:?\d\d$/.test(v) ? v : v + 'Z');
const P = (f) => path.join(OUTD, f);
const rd = (f) => JSON.parse(fs.readFileSync(P(f), 'utf8'));
const wr = (f, o) => fs.writeFileSync(P(f), typeof o === 'string' ? o : JSON.stringify(o));
const pick = (o, ks) => Object.fromEntries(ks.filter(k => o[k] !== undefined).map(k => [k, o[k]]));

// ---------------------------------------------------------------- the snapshot, its modules and the chained keys
let SN = null;        // { M (manifest), m (modules imported from the snapshot) }
async function snap() {
  if (SN) return SN;
  const M = verifySnapshot(SNAP);
  const u = (rel) => pathToFileURL(path.join(SNAP, rel)).href;
  const [tl, cam, site, ap, geo, fx, prov] = await Promise.all(['js/video/timeline.js', 'js/video/camera.js', 'js/world/site.js', 'data/hwd_airport.js', 'js/geo.js', 'js/world/fixtures_naip.js', 'js/video/provenance.js'].map(r => import(u(r))));
  SN = { M, m: { buildTimeline: tl.buildTimeline, planCamera: cam.planCamera, buildSite: site.buildSite, HWD_AIRPORT: ap.HWD_AIRPORT, rwyAxis: geo.rwyAxis, FIXTURES_NAIP: fx.FIXTURES_NAIP, captionTrack: prov.captionTrack } };
  log(`app snapshot ${path.relative(ROOT, SNAP)}: ${M.n} files, tree ${M.tree.slice(0, 12)}, taken ${M.made} (git ${String(M.git_head).slice(0, 10)} + ${M.git_modified_paths} modified paths)`);
  return SN;
}
const scoutKey = (M) => sha256(JSON.stringify({ tree: M.tree, job: pick(job, ['type', 'event', 'runway', 'window', 'segments', 'end', 'fps', 'rampS', 'seed', 'preStep', 'models', 'pack']), seed: SEED }));
const planKey = (sk, traceSha) => sha256(JSON.stringify({ sk, traceSha, job: pick(job, ['shots', 'size', 'gates', 'caption']) }));
const stampOf = (pk) => sha256(JSON.stringify({ pk, size: [VW, VH], shutter: SHUTTER, overlay: OVO })).slice(0, 16);

// ---------------------------------------------------------------- pack + timeline
function ensurePack() {
  const file = job.pack.file; if (fs.existsSync(path.join(ROOT, file))) return file;
  const b = job.pack.build; if (!b) throw new Error('pack missing and no build options: ' + file);
  log('building the type-only pack with tools/live/build_replay.py');
  const r = spawnSync('python3', ['-B', 'tools/live/build_replay.py', '--from', b.from, '--minutes', String(b.minutes), '--name', b.name, '--out', path.dirname(file)], { cwd: ROOT, stdio: 'inherit' });
  if (r.status !== 0 || !fs.existsSync(path.join(ROOT, file))) throw new Error('pack build failed');
  return file;
}
function timeline(buildTimeline) {
  const segs = job.segments.map(s => ({ from: T(s.from), to: T(s.to), speed: s.speed ?? 1, label: s.label || '', skip: !!s.skip }));
  if (job.end && job.end.seconds) { const l = segs[segs.length - 1]; segs.push({ from: l.to, to: l.to + job.end.seconds * 1000, speed: 1, label: 'end card' }); }
  return buildTimeline({ segments: segs, fps: FPS, rampS: job.rampS ?? 1.0 });
}
const frameAt = (TL, t) => { const F = TL.frames; let lo = 0, hi = F.length; while (lo < hi) { const m = (lo + hi) >> 1; if (F[m].t < t) lo = m + 1; else hi = m; } return lo; };
// events of the hero from the trace (frame indices + positions)
function eventsOf(tr) {
  const E = {};
  const first = (pred, from = 0) => { for (let i = from; i < tr.length; i++) { const p = tr[i]; if (p && p.found && p.valid && pred(p, i)) return i; } return null; };
  E.firstValid = first(() => true);
  E.move = first((p) => p.ground && p.gs > 3);
  E.lineup = first((p) => p.phase === 'line_up' || p.phase === 'takeoff_roll');
  E.roll = first((p) => p.phase === 'takeoff_roll' || (p.ground && p.gs > 35));
  E.liftoff = first((p, i) => !p.ground && i > 0 && tr[i - 1] && tr[i - 1].ground);
  E.touchdown = first((p, i) => p.ground && i > 0 && tr[i - 1] && tr[i - 1].found && tr[i - 1].valid && !tr[i - 1].ground);
  E.stop = E.touchdown != null ? first((p) => p.ground && p.gs < 8, E.touchdown) : null;
  E.park = first((p) => p.phase === 'parked', E.stop ?? E.touchdown ?? (E.liftoff != null ? tr.length : 0));
  const out = {}; for (const [k, f] of Object.entries(E)) if (f != null) { const p = tr[f]; out[k] = { f, t: p.t, x: +p.x.toFixed(1), z: +p.z.toFixed(1), y: +p.y.toFixed(1), hdg: +p.hdg.toFixed(1), gs: +p.gs.toFixed(1), phase: p.phase }; }
  return out;
}
const resolveT = (v, ev) => {   // ISO / epoch ms, or {event, dt (s)}
  if (v == null) return null;
  if (typeof v === 'object') { const e = ev[v.event]; if (!e) throw new Error('event not in the trace: ' + v.event); return e.t + (v.dt || 0) * 1000; }
  return T(v);
};

// ---------------------------------------------------------------- the page (served from the snapshot)
async function openPage({ root = SNAP, manifest } = {}) {
  const packUrl = job.pack.file; const pack = readPack(packUrl, root); const t0 = epochOf(pack);
  const srv = await startServer({ root, manifest }); const br = await launch({ W: VW, H: VH });
  const b = await bootApp(br.page, { base: srv.base, packUrl, t0, seed: SEED, root });
  log(`app ready in ${b.bootMs} ms (${VW}x${VH}, port ${srv.port}, served from ${path.relative(ROOT, root) || '.'})`);
  const check = (what) => {   // a miss / a byte mismatch / a page error ends the run (nothing outside the snapshot, ever)
    if (srv.missed.length) throw new Error(`${what}: the server could not serve ${srv.missed.slice(0, 4).join(', ')} (not in the snapshot)`);
    if (srv.bad.length) throw new Error(`${what}: served bytes differ from the manifest: ${srv.bad.slice(0, 4).join(', ')}`);
    const e = br.errors.filter(x => x.type !== 'warning'); if (e.length) throw new Error(`${what}: page error: ${e[0].text.slice(0, 200)}`);
  };
  const models = () => Object.fromEntries([...srv.served].filter(([k]) => k.endsWith('.glb')).map(([k, h]) => [path.basename(k), h]));
  return { ...br, srv, pack, packUrl, t0, check, models, close: async () => { await br.browser.close(); srv.server.close(); } };
}
async function installDirector(S, TL, extra = {}) {
  const cfg = { t0: S.t0, packUrl: S.packUrl, type: job.type, event: job.event, runway: job.runway || '28L', models: job.models !== false, fps: FPS,
    window: job.window ? { from: T(job.window.from), to: T(job.window.to) } : null, frames: TL.frames, cams: null, preStep: job.preStep || 0.1, overlay: OVO, ...extra };
  const info = await S.page.evaluate(async (cfg) => (await import('/js/video/director.js')).installDirector(cfg), cfg);
  if (!info.hero) throw new Error('no hero of type ' + job.type + ' with a ' + job.event + ' at HWD in the window (rule)');
  log('director:', JSON.stringify({ hero: info.heroStats, frames: info.frames, models: info.models, shutter: info.shutter, cuts: info.cuts }));
  if (job.models !== false && !Object.values(info.models).every(Boolean)) throw new Error('the detailed model did not load');
  const pr = await S.page.evaluate(() => __vd.prepare()); log('pre-roll:', pr.steps, 'engine steps');
  return info;
}

// ---------------------------------------------------------------- stages
async function snapshotStage() {
  if (fs.existsSync(path.join(SNAP, 'MANIFEST.json')) && !opt('refresh')) {
    const M = JSON.parse(fs.readFileSync(path.join(SNAP, 'MANIFEST.json'), 'utf8'));
    throw new Error(`a snapshot exists (${M.n} files, tree ${M.tree.slice(0, 12)}, ${M.made}); --refresh replaces it (then scout and plan again)`);
  }
  ensurePack();
  // probe: boot the working tree's app once with the director, step a few drawn frames, and list every file it requested
  const { buildTimeline } = await import(pathToFileURL(path.join(ROOT, 'js/video/timeline.js')).href);
  const TL = timeline(buildTimeline); const S = await openPage({ root: ROOT });
  let served;
  try {
    await installDirector(S, TL);
    for (let i = 0; i < 3; i++) await S.page.evaluate(() => __vd.step(true));
    await S.page.evaluate(() => __vd.overlay({ fade: 0, caption: 1, end: 0 }));
    served = [...S.srv.served.keys()];
    if (S.srv.missed.length) log('probe: not found (left out):', S.srv.missed.slice(0, 8).join(', '));
  } finally { await S.close(); }
  const base = [...SNAP_BASE.flatMap(r => listFiles(ROOT, r)), job.pack.file];
  const extra = served.filter(r => !base.includes(r));
  const M = makeSnapshot(SNAP, [...base, ...extra], { case: job.case, probe_served: served.length, extra });
  log(`snapshot ${path.relative(ROOT, SNAP)}: ${M.n} files (${extra.length} beyond js/, data/, live.*, the shim and the pack${extra.length ? ': ' + extra.join(', ') : ''}), tree ${M.tree.slice(0, 12)}`);
  const glb = Object.entries(M.files).filter(([k]) => k.endsWith('.glb')).map(([k, h]) => `${path.basename(k)} ${h.slice(0, 8)}`); log('models in the snapshot:', glb.join(', '));
}
async function scout() {
  const { M, m } = await snap(); const TL = timeline(m.buildTimeline); const S = await openPage({ manifest: M });
  try {
    await installDirector(S, TL);
    const t = Date.now(); const trace = [];
    for (let a = 0; a < TL.frames.length; a += 300) {
      const part = await S.page.evaluate(async ([a, b]) => { const o = []; for (let f = a; f < b; f++) o.push(await __vd.step(false)); return o; }, [a, Math.min(TL.frames.length, a + 300)]);
      for (const p of part) { if (p.near) p.near = p.near.slice(0, 12); trace.push(p); }
      S.check('scout');
    }
    const ev = eventsOf(trace);
    wr('trace.json', { job: path.basename(jobFile), scoutKey: scoutKey(M), app: M.tree, frames: TL.frames.length, fps: FPS, made: new Date().toISOString(), served_models: S.models(), events: ev, trace });
    const cnt = (k) => trace.reduce((m, p) => (m[p[k]] = (m[p[k]] || 0) + 1, m), {});
    log(`scout: ${trace.length} frames (${(trace.length / FPS).toFixed(1)} s of video, ${((TL.t1 - TL.t0) / 1000).toFixed(0)} s of data) in ${((Date.now() - t) / 1000).toFixed(1)} s`);
    log('src:', JSON.stringify(cnt('src')), 'kind:', JSON.stringify(cnt('kind')), 'phase:', JSON.stringify(cnt('phase')));
    log('hero not drawn:', trace.filter(p => !p.found || !p.valid || !(p.alpha > 0.05)).length, 'frames');
    for (const [k, e] of Object.entries(ev)) log(`event ${k.padEnd(9)} frame ${String(e.f).padStart(5)}  video ${(e.f / FPS).toFixed(1).padStart(6)} s  at (${e.x}, ${e.z}) y ${e.y} hdg ${e.hdg} ${e.gs} kt ${e.phase}`);
    log('models served:', JSON.stringify(Object.fromEntries(Object.entries(S.models()).map(([k, h]) => [k, h.slice(0, 8)]))), 'errors:', S.errors.length);
  } finally { await S.close(); }
}
// fixtures a camera must keep clear of: [x, z, radius]
const FIX_CLEAR = 18;
// plan gates per shot kind (px per frame / px per frame^2 at 1920 x 1080, m): the hero's screen speed and its change, the
// background's pan speed from the camera's rotation (captured frames carry motion blur, shutter 0.5: a 40-px/frame pan is
// a 20-px streak), the dolly's lag error, the hero's rest jitter in a static shot; job.gates[kind] and shot.gates override
// (with a `why`, printed) [inf: design limits]
const GATES = {
  establish: { heroPx: 4, heroAcc: 3, pan: 5, restJitter: 0 },
  chase: { heroPx: 6, heroAcc: 1.5, pan: 40 },
  dolly: { heroPx: 4, heroAcc: 1.5, pan: 5, lagErr: 3 },
  fixed: { heroPx: 32, heroAcc: 3, pan: 50 },
  tower: { heroPx: 20, heroAcc: 3, pan: 30 },
  hold: {},
};
async function plan() {
  const { M, m } = await snap(); const TL = timeline(m.buildTimeline);
  const raw = fs.readFileSync(P('trace.json')); const { trace, events, scoutKey: sk } = JSON.parse(raw);
  if (sk !== scoutKey(M)) throw new Error('trace.json is of another snapshot or job (scoutKey): run the scout again');
  if (trace.length !== TL.frames.length) throw new Error('trace.json is of another timeline: run the scout again');
  const obstacles = [...m.FIXTURES_NAIP.units.map(u => [u.x, u.z, 1]), ...(m.HWD_AIRPORT.markers || []).map(mk => [mk.x, mk.z, mk.kind === 'segmented_circle' ? (mk.diameter_m || 30) / 2 : 2])];
  const shots = job.shots.map((s, i) => {
    const f0 = frameAt(TL, resolveT(s.from, events)); const nx = job.shots[i + 1];
    const f1 = nx ? frameAt(TL, resolveT(nx.from, events)) : TL.frames.length;
    const o = { ...s, f0, f1 }; delete o.from; delete o.gates;
    if (o.at && o.at.event) { const e = events[o.at.event]; const A = m.rwyAxis(o.at.rwy); const al = (e.x - A.origin[0]) * A.dir[0] + (e.z - A.origin[1]) * A.dir[1]; o.at = { ...o.at, along: al + (o.at.dalong || 0) }; }
    // a fixed camera at the runway edge keeps FIX_CLEAR m from the light units (VASI / PAPI boxes, NAIP-measured) and the
    // windsock / segmented circle: moved along the runway in 5-m steps (alternately past / short of the planned point)
    if (o.at) { const A = m.rwyAxis(o.at.rwy); const pt = (al) => [A.origin[0] + A.dir[0] * al + A.right[0] * o.at.across, A.origin[1] + A.dir[1] * al + A.right[1] * o.at.across];
      const clear = (q) => obstacles.every(([x, z, r]) => Math.hypot(q[0] - x, q[1] - z) >= r + FIX_CLEAR);
      let k = 0; const a0 = o.at.along; while (!clear(pt(o.at.along)) && k < 40) { k++; o.at.along = a0 + (k % 2 ? 1 : -1) * 5 * Math.ceil(k / 2); }
      if (k) log(`shot ${o.name}: camera moved ${(o.at.along - a0).toFixed(0)} m along ${o.at.rwy} to keep ${FIX_CLEAR} m from the light units`); }
    return o;
  });
  const site = m.buildSite(m.HWD_AIRPORT);
  const { cams, report } = m.planCamera({ trace, shots, site, rwyAxis: m.rwyAxis, fps: FPS, aspect: VW / VH, obstacles, heightPx: VH });
  // gates
  const fails = [];
  for (const [i, r] of report.entries()) {
    const g = { ...(GATES[r.kind] || {}), ...((job.gates || {})[r.kind] || {}), ...(job.shots[i].gates || {}) }; r.gates = g;
    const chk = (k, v, at) => { if (g[k] != null && v != null && v > g[k]) fails.push(`${r.name}: ${k} ${v} > ${g[k]}${at != null ? ' at frame ' + at : ''}`); };
    if (g.why) log(`shot ${r.name}: gates ${JSON.stringify(Object.fromEntries(Object.entries(g).filter(([k]) => k !== 'why')))} - ${g.why}`);
    chk('heroPx', r.heroPxMax, r.heroPxAt); chk('heroAcc', r.heroAccMax, r.heroAccAt); chk('pan', r.bgPxMax, r.bgPxAt); chk('lagErr', r.lagErrMax, r.lagErrAt); chk('restJitter', r.restJitter, r.restJitterAt);
    for (let f = r.f0 + 1; f < r.f1; f++) if (TL.frames[f] && TL.frames[f].cut) fails.push(`${r.name}: a skip segment ends inside the shot (frame ${f}): start a shot there`);
    if (r.offScreen) fails.push(`${r.name}: hero off-screen in ${r.offScreen} frames`);
    if (r.occluded) fails.push(`${r.name}: line of sight through a building in ${r.occluded} frames`);
  }
  // the caption of every frame (pill + phase line, held >= 0.5 s of video), deduplicated
  const cap = m.captionTrack(trace, { fps: FPS, ...(job.caption || {}), cuts: shots.map(s => s.f0).filter(f => f > 0) }); const tab = [], ix = new Map(), capIdx = cap.map(c => { const k = JSON.stringify([c.phase, c.cls, c.text, c.sub]); if (!ix.has(k)) { ix.set(k, tab.length); tab.push({ phase: c.phase, cls: c.cls, text: c.text, sub: c.sub }); } return ix.get(k); });
  const held = cap.filter(c => c.held).length;
  const pk = planKey(sk, sha256(raw));
  wr('cams.json', { planKey: pk, scoutKey: sk, app: M.tree, frames: cams.length, shots: shots.map(s => ({ kind: s.kind, name: s.name, f0: s.f0, f1: s.f1 })), cuts: shots.map(s => s.f0).filter(f => f > 0),
    report, gates: { ok: !fails.length, fails }, capTab: tab, capIdx, cams });
  for (const r of report) log(`shot ${String(r.name).padEnd(16)} ${String(r.f0).padStart(5)}-${String(r.f1).padStart(5)} (${(r.frames / FPS).toFixed(1).padStart(5)} s)  camAGL>=${r.camAglMin}  step<=${r.stepMax} (rel ${r.relStepMax})  ac>=${r.acClearMin}  fixt>=${r.fixtureMin}  |ndc|<=${r.ndcMax}  off ${r.offScreen} occl ${r.occluded} raised ${r.raised} pushed ${r.pushed}  fov ${r.fov}`
    + `\n      hero px/f<=${r.heroPxMax}@${r.heroPxAt} px/f2<=${r.heroAccMax}@${r.heroAccAt}  pan px/f<=${r.bgPxMax}@${r.bgPxAt} (>20: ${r.bgOver20})${r.lagErrMax != null ? `  lag err<=${r.lagErrMax} m@${r.lagErrAt} vmax ${r.carAtVmax} f` : ''}  rest jitter ${r.restJitter}${r.restJitterAt != null ? '@' + r.restJitterAt : ''}`);
  log(`plan: ${cams.length} frames, ${(cams.length / FPS).toFixed(1)} s of video; captions: ${tab.length} states, ${held} frames held (< 0.5 s states)`);
  if (fails.length) { log('GATES FAILED (render refuses this plan without --nogate):'); for (const f of fails) log('  ' + f); process.exitCode = 3; }
  else log('gates: all passed');
}
function rangeOf(TL) {
  const t = opt('test'); if (t) { const T0 = job.tests && job.tests[t]; if (!T0) throw new Error('no test ' + t); const ev = fs.existsSync(P('trace.json')) ? rd('trace.json').events : {};
    const a = frameAt(TL, resolveT(T0.from, ev)); return [a, Math.min(TL.frames.length - 1, a + Math.round(T0.seconds * FPS) - 1)]; }
  const fr = opt('frames'); if (fr) { const [a, b] = String(fr).split('-').map(Number); return [a, Math.min(TL.frames.length - 1, b)]; }
  return [0, TL.frames.length - 1];
}
// overlay state of frame f: fade from black at the start, captions fade in, the end card fades in over 0.8 s
function overlayState(TL, f) {
  const F = TL.frames, endF = job.end && job.end.seconds ? F.length - Math.round(job.end.seconds * FPS) : F.length;
  return { fade: f < 12 ? 1 - f / 12 : 0, caption: clamp01((f - 6) / 18), end: f >= endF ? clamp01((f - endF + 1) / (0.8 * FPS)) : 0 };
}
const clamp01 = (x) => Math.max(0, Math.min(1, x));
/** the plan of the current snapshot + job, checked: -> { TL, C (cams.json), tr (trace), stamp } */
async function checkedPlan() {
  const { M, m } = await snap(); const TL = timeline(m.buildTimeline);
  const raw = fs.readFileSync(P('trace.json')); const tj = JSON.parse(raw); const C = rd('cams.json');
  const sk = scoutKey(M);
  if (tj.scoutKey !== sk) throw new Error('trace.json is of another snapshot or job: scout and plan again');
  if (C.planKey !== planKey(sk, sha256(raw))) throw new Error('cams.json is of another trace, snapshot or shot list: plan again');
  if (C.cams.length !== TL.frames.length) throw new Error('cams.json is of another timeline: plan again');
  if (!C.gates.ok && !opt('nogate')) throw new Error(`the plan's gates failed (${C.gates.fails.length}: ${C.gates.fails[0]}): fix the shots and plan again, or pass --nogate`);
  return { M, TL, C, tr: tj.trace, stamp: stampOf(C.planKey) };
}
function guardDir(FD, stamp) {
  const sf = path.join(FD, 'PLAN_STAMP');
  if (fs.existsSync(sf) && fs.readFileSync(sf, 'utf8').trim().split('\n')[0] !== stamp) {
    if (!opt('clean')) throw new Error(`${path.relative(ROOT, FD)} holds frames of another plan, snapshot or render setting (PLAN_STAMP): pass --clean to empty it, or move them away`);
    for (const f of fs.readdirSync(FD)) if (/^\d{5}\.png$/.test(f)) fs.rmSync(path.join(FD, f));
    log(`--clean: emptied ${path.relative(ROOT, FD)} (frames of another plan)`);
  }
  fs.writeFileSync(sf, stamp + '\n');
}
async function render({ dir = 'frames', range = null, quiet = false } = {}) {
  const { M, TL, C, tr, stamp } = await checkedPlan(); const { cams } = C;
  const picks = !range && opt('pick') ? String(opt('pick')).split(',').map(Number).filter(Number.isFinite).sort((x, y) => x - y) : null;
  const [a, b] = range || (picks ? [picks[0], picks[picks.length - 1]] : rangeOf(TL)); const FD = P(picks ? opt('dir', 'picks') : dir); fs.mkdirSync(FD, { recursive: true });
  const name = (f) => path.join(FD, String(f).padStart(5, '0') + '.png');
  guardDir(FD, stamp);
  const force = !!opt('force'); const todo = []; for (const f of (picks || Array.from({ length: b - a + 1 }, (_, i) => a + i))) if (force || !fs.existsSync(name(f))) todo.push(f);
  const todoSet = new Set(todo);
  if (!todo.length) { log(`render: frames ${a}-${b} already on disk`); return { a, b, times: [] }; }
  const S = await openPage({ manifest: M }); const times = [], loads = []; let maxDev = 0, maxDevAt = null;
  try {
    await installDirector(S, TL, { cams, cuts: C.cuts, shutter: SHUTTER });
    S.check('boot');
    // skip ahead (state only) to the first frame to draw
    const first = todo[0]; const tk = Date.now();
    for (let f = 0; f < first; f += 300) {
      const devs = await S.page.evaluate(async (n) => { const o = []; for (let i = 0; i < n; i++) { const p = await __vd.step(false); o.push(p.found ? [p.f, p.x, p.y, p.z, p.phase, p.label] : [p.f]); } return o; }, Math.min(300, first - f));
      for (const d of devs) { const q = tr[d[0]]; if (d.length > 1 && q && q.found) { const dv = Math.hypot(d[1] - q.x, d[2] - q.y, d[3] - q.z); if (dv > maxDev) { maxDev = dv; maxDevAt = d[0]; } if (dv > MAXDEV || d[4] !== q.phase || d[5] !== q.label) throw new Error(`frame ${d[0]} (skip-ahead): the hero is ${dv.toFixed(4)} m from its scout pose (limit ${MAXDEV}), phase ${d[4]} / ${q.phase}: the engine is not the one scouted - snapshot, scout and plan again`); } }
      S.check('skip-ahead');
    }
    if (first) log(`skip-ahead: ${first} frames (state only) in ${((Date.now() - tk) / 1000).toFixed(1)} s`);
    const endF = job.end && job.end.seconds ? TL.frames.length - Math.round(job.end.seconds * FPS) : TL.frames.length;
    for (let f = first; f <= b; f++) {
      const t1 = Date.now(); const ov = overlayState(TL, f); const draw = todoSet.has(f); const cap = C.capTab[C.capIdx[f]];
      // a fully opaque end card needs no 3-D frame
      const pose = await S.page.evaluate(async ([gpu, capt, ov]) => { const p = await __vd.step(gpu); if (capt) __vd.overlay({ ...ov, pose: p }); return p; }, [draw && !(ov.end >= 1), draw, { ...ov, cap }]);
      const q = tr[f];
      if (q && pose.found && q.found) { const dv = Math.hypot(pose.x - q.x, pose.y - q.y, pose.z - q.z); if (dv > maxDev) { maxDev = dv; maxDevAt = f; }
        if (dv > MAXDEV || pose.phase !== q.phase || pose.label !== q.label) throw new Error(`frame ${f}: the hero is ${dv.toFixed(4)} m from its scout pose (limit ${MAXDEV}), phase ${pose.phase} / ${q.phase}, label ${pose.label} / ${q.label}: snapshot, scout and plan again`); }
      else if (!!(q && q.found) !== !!pose.found) throw new Error(`frame ${f}: hero found ${pose.found} in the render, ${q && q.found} in the scout`);
      S.check('frame ' + f);
      if (!draw) continue;
      const png = await S.page.screenshot({ type: 'png' });
      fs.writeFileSync(name(f), png);
      const dt = (Date.now() - t1) / 1000; times.push(dt); loads.push(os.loadavg()[0]);
      if (!quiet) log(`frame ${f} (${f - a + 1}/${b - a + 1}) ${dt.toFixed(2)} s  ${cap.phase} · ${cap.cls} ${pose.gs != null ? pose.gs.toFixed(0) + ' kt' : ''}`);
    }
    const rl = fs.existsSync(P('render_log.json')) ? rd('render_log.json') : [];
    const sp = times.length ? { min: +Math.min(...times).toFixed(2), median: +median(times).toFixed(2), max: +Math.max(...times).toFixed(2) } : null;
    rl.push({ at: new Date().toISOString(), dir: path.basename(FD), range: [a, b], drawn: times.length, stamp, app: M.tree, git_head: M.git_head, s_per_frame: sp,
      load1: loads.length ? { min: +Math.min(...loads).toFixed(1), median: +median(loads).toFixed(1), max: +Math.max(...loads).toFixed(1) } : null,
      max_dev_m: +maxDev.toFixed(5), max_dev_at: maxDevAt, limit_m: MAXDEV, shutter: SHUTTER, errors: S.errors.length, models_served: S.models() });
    wr('render_log.json', JSON.stringify(rl, null, 1));
    log(`render ${a}-${b}: ${times.length} frames; s/frame min ${sp.min} median ${sp.median} max ${sp.max} (load ${rl[rl.length - 1].load1.median}); hero vs scout max ${maxDev.toFixed(5)} m (limit ${MAXDEV}); errors ${S.errors.length}; models ${Object.entries(S.models()).map(([k, h]) => k + ' ' + h.slice(0, 8)).join(', ')}`);
    if (endF < TL.frames.length && b >= endF) log('end card from frame', endF);
  } finally { await S.close(); }
  return { a, b, times, maxDev };
}
const median = (v) => { const s = v.slice().sort((x, y) => x - y); return s.length ? s[s.length >> 1] : NaN; };
function ffmpeg(args) { const r = spawnSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', ...args], { stdio: 'inherit' }); if (r.status !== 0) throw new Error('ffmpeg failed'); }
const clipName = () => opt('name', opt('test') ? 'test_' + opt('test') : job.case.toLowerCase() === 's' ? 'sf50_takeoff' : 'pc12_landing');
async function encode() {
  const { TL, stamp } = await checkedPlan(); const [a, b] = rangeOf(TL); const nm = clipName(); const FD = P(opt('dir', 'frames'));
  // every frame of the range must be on disk and belong to this plan: the image2 demuxer stops at the first gap and exits 0
  const sf = path.join(FD, 'PLAN_STAMP');
  if (!fs.existsSync(sf) || fs.readFileSync(sf, 'utf8').trim().split('\n')[0] !== stamp) throw new Error(`${path.relative(ROOT, FD)} holds no frames of this plan (PLAN_STAMP): render first`);
  const miss = []; for (let f = a; f <= b; f++) if (!fs.existsSync(path.join(FD, String(f).padStart(5, '0') + '.png'))) miss.push(f);
  if (miss.length) throw new Error(`${miss.length} of ${b - a + 1} frames missing (first ${miss.slice(0, 6).join(', ')}): render them first`);
  const out = P(nm + '.mp4'); const t = Date.now();
  ffmpeg(['-framerate', String(FPS), '-start_number', String(a), '-i', path.join(FD, '%05d.png'), '-frames:v', String(b - a + 1),
    '-c:v', 'libx264', '-crf', '16', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-r', String(FPS), '-movflags', '+faststart', out]);
  const pr = spawnSync('ffprobe', ['-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', out]).stdout.toString().trim();
  const got = parseInt(pr, 10);
  if (got !== b - a + 1) { fs.renameSync(out, out + '.short'); throw new Error(`encoded ${got} frames, expected ${b - a + 1}: kept as ${path.basename(out)}.short`); }
  log('encoded', path.relative(ROOT, out), (fs.statSync(out).size / 1e6).toFixed(2), 'MB,', got, 'frames (ffprobe count),', ((Date.now() - t) / 1000).toFixed(1), 's');
  return out;
}
function stills() {
  const nm = clipName(); const clip = P(nm + '.mp4');
  const dur = +spawnSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', clip]).stdout.toString().trim();
  const outs = [];
  for (const [k, q] of [[1, 0.1], [2, 0.5], [3, 0.9]]) { const o = P(`${nm}_still${k}.png`); ffmpeg(['-ss', (dur * q).toFixed(3), '-i', clip, '-frames:v', '1', o]); outs.push(o); }
  log('stills:', outs.map(o => path.relative(ROOT, o)).join(' '));
}
async function determinism() {
  const { TL } = await checkedPlan(); const [a, b] = rangeOf(TL);
  const hash = (d) => Object.fromEntries(fs.readdirSync(P(d)).filter(f => f.endsWith('.png')).map(f => [f, sha256(fs.readFileSync(path.join(P(d), f)))]));
  for (const d of ['det_A', 'det_B', 'det_C']) fs.rmSync(P(d), { recursive: true, force: true });
  await render({ dir: 'det_A', range: [a, b], quiet: true });
  await render({ dir: 'det_B', range: [a, b], quiet: true });
  const c0 = Math.max(0, a - (+opt('lead', 6)));
  await render({ dir: 'det_C', range: [c0, b], quiet: true });   // renders c0..a-1 too: a drawn frame must not change later ones
  const A = hash('det_A'), B = hash('det_B'), Cc = hash('det_C');
  const keys = Object.keys(A).sort(); let ab = 0, ac = 0;
  for (const k of keys) { if (A[k] === B[k]) ab++; if (A[k] === Cc[k]) ac++; }
  const res = { range: [a, b], lead: a - c0, shutter: SHUTTER, frames: keys.length, sameAB: ab, sameAC: ac, sha: Object.fromEntries(keys.map(k => [k, A[k].slice(0, 16)])) };
  wr('determinism.json', res); log('determinism:', JSON.stringify({ frames: res.frames, shutter: SHUTTER, identical_two_runs: ab, identical_after_rendering_earlier_frames: ac }));
  if (ab !== keys.length || ac !== keys.length) process.exitCode = 4;
}

const stages = stage === 'all' ? ['scout', 'plan', 'render', 'encode', 'stills'] : [stage];
for (const s of stages) {
  if (s === 'snapshot') await snapshotStage(); else if (s === 'scout') await scout(); else if (s === 'plan') await plan(); else if (s === 'render') await render();
  else if (s === 'encode') await encode(); else if (s === 'stills') stills(); else if (s === 'determinism') await determinism();
  else { console.error('unknown stage', s); process.exit(2); }
  if (process.exitCode && s === 'plan' && stages.length > 1) break;
}
process.exit(process.exitCode || 0);
