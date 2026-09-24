// Replay the relay's SSE event sequence (tools/live/build_stream.py, built from the REAL recording through the relay's
// own merge code) through the app's traffic engine in node, on a simulated clock, and measure what it displays.
//
// Runs js/live/feed.js parsePayload, js/live/traffic.js (Traffic: ingest -> state machine -> kinematic display) and
// js/live/ground.js (GroundPhysics) unmodified, wired as js/live/app.js wires them (taxi graph, stand set, pavement
// mask union, SFO plan). Browser APIs stubbed: document.createElement('canvas') -> @napi-rs/canvas so that
// airport.js paintAirportMapReal (pavement mask) and ground.js buildingGrid (buildings) run as in the page.
//
// Output (gzip JSON lines): meta; rows every --log s [T, hex, phase(display), machine phase, rwy, gate, x, y, z, hdg,
// ground, gs, flight, icao, delay, gateSrc]; final summary {events, counters, kin, overlaps, offpave, ...}.
// Kinematic metrics are measured on every frame from the displayed state:
//   ground: longitudinal / lateral acceleration, jerk, yaw rate, sideslip (motion vs nose), per aircraft maxima;
//   air: horizontal and vertical acceleration, turn rate; teleports = a frame displacement > (|v|+5 m/s) dt + 1 m.
// Usage: node tools/live/replay_engine.mjs --stream refs/cache/replay_day/stream.jsonl.gz [--gates refs/cache/replay_day/gates.jsonl.gz]
//        [--no-plan] [--out refs/cache/replay_day/engine.jsonl.gz] [--dt 0.1] [--log 0.5] [--latency 0.08]
import fs from 'fs'; import path from 'path'; import zlib from 'zlib'; import readline from 'readline'; import { fileURLToPath } from 'url';

const HERE = path.dirname(fileURLToPath(import.meta.url)); const ROOT = path.resolve(HERE, '..', '..');
const argv = process.argv.slice(2); const opt = (k, d) => { const i = argv.indexOf('--' + k); return i >= 0 ? argv[i + 1] : d; }; const flag = (k) => argv.includes('--' + k);
const STREAM = opt('stream', path.join(ROOT, 'refs/cache/replay_day/stream.jsonl.gz'));
const GATES = opt('gates', path.join(path.dirname(STREAM), 'gates.jsonl.gz'));
const OUTF = opt('out', path.join(path.dirname(STREAM), flag('no-plan') ? 'engine_noplan.jsonl.gz' : 'engine.jsonl.gz'));
const DT = +opt('dt', 0.1), LOG = +opt('log', 0.5), LAT = +opt('latency', 0.08);
const USE_PLAN = !flag('no-plan');

let createCanvas;
for (const m of [process.env.CANVAS_MODULE, '@napi-rs/canvas'].filter(Boolean)) { try { ({ createCanvas } = await import(m)); break; } catch (e) { } }
if (!createCanvas) { console.error('no canvas module: set CANVAS_MODULE to @napi-rs/canvas/index.js'); process.exit(1); }
globalThis.document = { createElement: () => createCanvas(1, 1), hidden: false };

const imp = (p) => import(path.join(ROOT, p));
const { AIRPORT } = await imp('data/sfo_airport.js'); const { DETAILS } = await imp('data/sfo_details.js'); const { STANDS } = await imp('data/sfo_stands.js');
const { PAINT } = await imp('data/sfo_paint.js'); const { PAVEMENT } = await imp('data/sfo_pavement.js');
let TAXIGRAPH = null; try { ({ TAXIGRAPH } = await imp('data/sfo_taxigraph.js')); } catch (e) { console.error('no taxi graph'); }
const { standGates, paintAirportMapReal, endZoneRects } = await imp('js/live/airport.js');
const { Traffic, phaseLabel, category } = await imp('js/live/traffic.js');
const { GroundPhysics, buildingGrid, bodyOf, overlaps, samples, pavedUnion } = await imp('js/live/ground.js');
const { parsePayload } = await imp('js/live/feed.js');
const { TYPES } = await imp('js/aircraft/types.js');

const gates = standGates(STANDS);
const apt = paintAirportMapReal(AIRPORT, gates, undefined, DETAILS, { paint: PAINT, pavement: PAVEMENT, endZones: endZoneRects() });
const building = buildingGrid(AIRPORT);
const traffic = new Traffic({ gates, airport: AIRPORT, persist: false, centerlines: DETAILS.centerlines, taxigraph: TAXIGRAPH, stands: STANDS });
traffic.buildingAt = building; traffic.towBy = new Map(); traffic.towLog = [];
if (process.env.DELAY) { traffic.adaptDelay = false; traffic.delay = traffic.delayTarget = +process.env.DELAY; }
const DEBUG = process.env.DEBUG || null; traffic.debug = DEBUG; const UNTIL = process.env.UNTIL ? +process.env.UNTIL : null;
const physics = new GroundPhysics({ paved: apt.paved, building, net: traffic.net });
const pavedMaskOnly = apt.paved, pavedAll = pavedUnion(apt.paved, traffic.net);

// ---- inputs
async function readLines(f, fn) { const rl = readline.createInterface({ input: fs.createReadStream(f).pipe(zlib.createGunzip()), crlfDelay: Infinity }); for await (const l of rl) if (l) fn(JSON.parse(l)); }
const events = []; await readLines(STREAM, (j) => events.push(j));
const plans = []; if (USE_PLAN && fs.existsSync(GATES)) await readLines(GATES, (j) => plans.push(j));
console.error(`stream events ${events.length}, plans ${plans.length}`);

const out = zlib.createGzip(); const ws = fs.createWriteStream(OUTF); out.pipe(ws);
let simNow = (events[0].T + LAT) * 1000; const tEnd = UNTIL ? Math.min(UNTIL * 1000, (events[events.length - 1].T + LAT) * 1000) : (events[events.length - 1].T + LAT) * 1000;
out.write(JSON.stringify({ meta: { stream: STREAM, plan: USE_PLAN, dt: DT, log: LOG, t0: simNow / 1000, t1: tEnd / 1000, taxigraph: !!TAXIGRAPH } }) + '\n');

// ---- metrics
const K = new Map();       // hex -> kinematic state from the previous frames
const kin = { ground: { along: [], lat: [], jerk: [], yaw: [], slip: [] }, air: { along: [], lat: [], vacc: [], turn: [] } };
const maxes = new Map();   // hex -> per-aircraft maxima
// exceedance thresholds (m/s^2, m/s^3, deg/s, deg): ground braking/acceleration 0.36 g, lateral 0.3 g, yaw 25 deg/s,
// sideslip 5 deg; air along-track 0.3 g, lateral 6 m/s^2 (= a 31.5 deg bank), vertical 0.3 g, turn 7 deg/s
const EX = { gAcc: 3.5, gLat: 3.0, gJerk: 6.0, gYaw: 25, slip: 5, aAcc: 3.0, aLat: 6.0, aVacc: 3.0, aTurn: 7 };
const exceed = Object.fromEntries(Object.keys(EX).map(k => [k, 0])); const exceedWho = Object.fromEntries(Object.keys(EX).map(k => [k, new Map()]));
const slipLog = []; let teleports = 0, gapResets = 0; const teleWho = new Map(); let frames = 0;
const overlapPairs = new Map(); let overlapFrames = 0;
const offPave = { maskOnly: 0, union: 0, frames: 0, who: new Map() }; const inBld = { frames: 0, who: new Map() };
const sample = (arr, v) => { if (arr.length < 400000) arr.push(v); else arr[Math.floor(Math.random() * arr.length)] = v; };
const wrapD = (a) => { a = (a + 180) % 360; if (a < 0) a += 360; return a - 180; };
const bump = (m, k, v = 1) => m.set(k, (m.get(k) || 0) + v);

let k = 0, p = 0, nextLog = simNow;
while (simNow < tEnd) {
  while (p < plans.length && (plans[p].T + LAT) * 1000 <= simNow) { traffic.setPlan(plans[p].gates); p++; }
  while (k < events.length && (events[k].T + LAT) * 1000 <= simNow) { const P = parsePayload(events[k].p, events[k].T * 1000); traffic.ingest(P, (events[k].T + LAT) * 1000); k++; }
  traffic.update(simNow, DT); physics.resolve(traffic, DT); frames++;
  const ground = [];
  for (const tr of traffic.tracks.values()) {
    const D = tr.disp; if (!D.valid || tr.vehicle) continue;
    const near = Math.hypot(D.x, D.z) < (D.ground ? 6000 : 40000) && tr.info.category !== 'A7';
    const s = K.get(tr.hex);
    // ground kinematics are measured at the main-gear centre (the point that cannot slip sideways; the antenna point
    // swings sideways in a turn), airborne ones at the reference point
    const Tk = tr.model && TYPES[tr.model.t]; const bk = D.ground && Tk ? Math.max(1, (Tk.xMain ?? Tk.L * 0.47) - 0.2 * Tk.L) : 0;
    const PX = D.x - Math.sin(D.hdg) * bk, PZ = D.z + Math.cos(D.hdg) * bk;
    const vx = s ? (PX - s.x) / DT : 0, vz = s ? (PZ - s.z) / DT : 0, vy = s ? (D.y - s.y) / DT : 0;
    if (s && s.n >= 2 && near && s.g === D.ground) {
      const disp = Math.hypot(PX - s.x, PZ - s.z), vprev = Math.hypot(s.vx, s.vz);
      if (disp > (vprev + 5) * DT + 1) { if (tr._reset === 'gap' || tr._reset === 'init') { gapResets++; } else { teleports++; bump(teleWho, (tr.info.flight || tr.hex) + (D.ground ? ':gnd' : ':air') + (tr._reset ? ':' + tr._reset : '')); } tr._reset = null; }
      else {
        const ax = (vx - s.vx) / DT, az = (vz - s.vz) / DT, ay = (vy - s.vy) / DT;
        const sp = Math.hypot(vx, vz); const hx = Math.sin(D.hdg), hz = -Math.cos(D.hdg);
        const yaw = wrapD((D.hdg - s.hdg) * 180 / Math.PI) / DT;
        const M = maxes.get(tr.hex) || { f: tr.info.flight || tr.hex }; maxes.set(tr.hex, M); const T0 = tr.model && TYPES[tr.model.t];
        const put = (key, v, arr) => { sample(arr, v); if (!(M[key] >= v)) M[key] = v; if (v > EX[key]) { exceed[key]++; bump(exceedWho[key], M.f); } };
        if (D.ground && s.g) {
          const along = Math.abs(ax * hx + az * hz), lat = Math.abs(-ax * hz + az * hx);
          put('gAcc', along, kin.ground.along); put('gLat', lat, kin.ground.lat); put('gYaw', Math.abs(yaw), kin.ground.yaw);
          if (s.ax != null && sp > 0.5) put('gJerk', Math.hypot(ax - s.ax, az - s.az) / DT, kin.ground.jerk);
          if (sp > 1) { let sl = Math.abs(wrapD((Math.atan2(vx, -vz) - D.hdg) * 180 / Math.PI)); sl = Math.min(sl, 180 - sl); put('slip', sl, kin.ground.slip); if (sl > 5 && process.env.SLIPLOG && slipLog.length < 60) slipLog.push([new Date(simNow).toISOString().slice(11, 22), M.f, tr.hex, sp.toFixed(1), sl.toFixed(0), tr.m.phase, tr.phase, (tr.ctl && tr.ctl.v || 0).toFixed(1)]); }
        } else if (!D.ground && !s.g) {
          const tx = sp > 1 ? vx / sp : hx, tz = sp > 1 ? vz / sp : hz;
          const light = tr.info.category === 'A1' || (T0 && T0.L < 20); const lf = light ? 1.7 : 1; // light aircraft: 45 deg bank
          put('aAcc', Math.abs(ax * tx + az * tz), kin.air.along); put('aLat', Math.abs(-ax * tz + az * tx) / lf, kin.air.lat); put('aVacc', Math.abs(ay), kin.air.vacc); put('aTurn', Math.abs(yaw) / (light ? 1.8 : 1), kin.air.turn);
        }
        s.ax = ax; s.az = az;
      }
    }
    K.set(tr.hex, { x: PX, z: PZ, y: D.y, vx, vz, vy, hdg: D.hdg, g: D.ground, n: s && s.g === D.ground ? s.n + 1 : 1, ax: s ? s.ax : null, az: s ? s.az : null });
    // surface checks on displayed ground aircraft at SFO
    const T = tr.model && TYPES[tr.model.t];
    if (T && D.ground && Math.abs(D.x) < 3000 && Math.abs(D.z) < 3000) {
      const B = bodyOf(T, D.x, D.z, D.hdg); B.hex = tr.hex; B.f0 = tr.info.flight || tr.hex; ground.push(B);
      const S = samples(T, B.nose, D.hdg); B.S = S;
      const om = S.gear.filter(g => !pavedMaskOnly(g[0], g[1])).length, ou = S.gear.filter(g => !pavedAll(g[0], g[1])).length;
      offPave.frames++; if (om) offPave.maskOnly++; if (ou) { offPave.union++; bump(offPave.who, B.f0 + '@' + Math.round(D.x) + ',' + Math.round(D.z)); }
      const ib = S.outline.filter(q => building(q[0], q[1])).length; if (ib) { inBld.frames++; bump(inBld.who, B.f0); }
    }
  }
  for (const [hex] of K) if (!traffic.tracks.has(hex)) K.delete(hex);
  let any = false;
  for (let i = 0; i < ground.length; i++) for (let j = i + 1; j < ground.length; j++) if (overlaps(ground[i], ground[j], 0)) { any = true; bump(overlapPairs, [ground[i].f0, ground[j].f0].sort().join('~'), DT); }
  if (any) overlapFrames++;
  if (simNow >= nextLog) {
    nextLog += LOG * 1000;
    if (DEBUG && traffic.tracks.get(DEBUG) && traffic.tracks.get(DEBUG)._dbg) { const d = traffic.tracks.get(DEBUG)._dbg; const tr = traffic.tracks.get(DEBUG); console.error(new Date(simNow).toISOString().slice(11, 21), tr.m.phase, d.ph, 'tgt', d.ox.toFixed(1), d.oz.toFixed(1), d.oy.toFixed(1), 'v', Math.hypot(d.ovx, d.ovz).toFixed(1), (Math.atan2(d.ovx, -d.ovz) * 57.3).toFixed(0), 'vy', (d.ovy || 0).toFixed(1), d.stop ? 'STOP' : '', 'ex', d.ex.toFixed(1), '| ctl', d.x.toFixed(1), d.z.toFixed(1), d.y.toFixed(1), 'v', d.v.toFixed(1), 'a', d.a.toFixed(2), 'psi', (d.psi * 57.3).toFixed(0), 'k', d.k.toFixed(4), 'err', Math.hypot(d.ox - d.x, d.oz - d.z).toFixed(1), tr.ctl.towing ? 'TOW' : '', tr.gate ? tr.gate.name : '', (tr.parkHdg != null ? (tr.parkHdg * 57.3).toFixed(0) : ''), tr.parkMode || ''); }
    for (const tr of traffic.tracks.values()) {
      const D = tr.disp; if (!D.valid) continue;
      out.write(JSON.stringify([+(simNow / 1000).toFixed(2), tr.hex, tr.phase, tr.m.phase, tr.m.rwy || tr.runway || null, tr.gate ? tr.gate.name : null, +D.x.toFixed(1), +D.y.toFixed(1), +D.z.toFixed(1), +(D.hdg * 180 / Math.PI).toFixed(1),
        D.ground ? 1 : 0, +(D.gs || 0).toFixed(1), tr.info.flight || null, tr.info.icao || null, Math.round(traffic.delay), tr.gateSrc || null, tr.vehicle ? 1 : 0, tr.stale ? 1 : 0, +(D.pitch * 180 / Math.PI).toFixed(1), +D.gear.toFixed(2)]) + '\n');
    }
  }
  simNow += DT * 1000;
}
const pct = (a, q) => { if (!a.length) return null; const s = a.slice().sort((x, y) => x - y); return +s[Math.min(s.length - 1, Math.floor(q / 100 * s.length))].toFixed(2); };
const dist = (a) => ({ n: a.length, p50: pct(a, 50), p99: pct(a, 99), p999: pct(a, 99.9), max: a.length ? +a.reduce((m, v) => v > m ? v : m, -Infinity).toFixed(2) : null });
const top = (m, n = 8) => [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, n);
const summary = {
  frames, dt: DT, events: traffic.events, counters: traffic.counters,
  kin: { ground: Object.fromEntries(Object.entries(kin.ground).map(([k, v]) => [k, dist(v)])), air: Object.fromEntries(Object.entries(kin.air).map(([k, v]) => [k, dist(v)])) },
  thresholds: EX, exceed, exceedWho: Object.fromEntries(Object.entries(exceedWho).map(([k, m]) => [k, top(m)])),
  teleports, gapResets, teleWho: top(teleWho, 20), towBy: top(traffic.towBy, 15).map(([k, v]) => [k, +v.toFixed(0)]), towLog: traffic.towLog, overlapFrames, overlapPairs: top(overlapPairs, 20).map(([k, v]) => [k, +v.toFixed(1)]),
  offPave: { frames: offPave.frames, maskOnly: offPave.maskOnly, union: offPave.union, who: top(offPave.who, 15) }, inBld: { frames: inBld.frames, who: top(inBld.who) },
  worst: [...maxes.values()].sort((a, b) => (b.gAcc || 0) - (a.gAcc || 0)).slice(0, 5),
};
out.write(JSON.stringify({ summary }) + '\n'); out.end(); await new Promise(r => ws.on('finish', r));
console.log(JSON.stringify({ frames, tracks: traffic.tracks.size, teleports, overlapFrames, offPave: summary.offPave, exceed, counters: traffic.counters, events: traffic.events.length }, null, 0));
console.log('->', OUTF); if (slipLog.length) console.log(slipLog.map(q => q.join(' ')).join('\n'));
