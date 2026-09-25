// Replay recorded ADS-B through the app's OWN traffic logic in node (no browser, no WebGL) and log what it displays.
//
// Runs js/live/traffic.js (Traffic: ingest -> classify -> update), js/live/ground.js (GroundPhysics.resolve) and
// js/live/feed.js (parsePayload) unmodified, fed with the payload sequence written by tools/live/replay_feed.py, on a
// simulated clock (Date.now() is never used by these modules' update paths; the harness passes the clock explicitly).
// Browser APIs stubbed: document.createElement('canvas') -> @napi-rs/canvas (Skia) so that airport.js
// paintAirportMapReal (pavement mask) and ground.js buildingGrid (building mask) run exactly as in the page.
// localStorage is not used (persist: false, as in snapshot mode; parked persistence is not exercised).
//
// Wiring reproduces js/live/app.js:
//   gates = standGates(STANDS)                                   (world.js buildLiveWorld with opts.stands)
//   paintAirportMapReal(AIRPORT, gates, res, DETAILS, {paint, pavement, endZones})
//   traffic = new Traffic({gates, airport, persist:false, centerlines: DETAILS.centerlines, onGateChange})
//   traffic.buildingAt = buildingGrid(AIRPORT);  traffic.delay = (relay ? 5000 : 7000) + 2500
//   physics = new GroundPhysics({ paved: world.paved, building })   -- NOTE: app.js:91 sets world.paved = null before
//             app.js:172 reads it, so the app's GroundPhysics runs WITHOUT the pavement test. --paved-bug (default)
//             reproduces that; --paved-fixed passes the real mask.
//   per frame: traffic.update(now, dt); physics.resolve(traffic, dt)
//   routes: adsb.lol routeset answers cached by replay_feed.py routes (refs/cache/replay/routes.json), applied 6 s
//           after a track appears (app.js polls routes every 6 s).
// Extra measurements made here (the app does not expose them): gear points on pavement (the real mask), planform
// overlaps between ground aircraft and airframe points inside buildings -- the planform/gear geometry below is a
// verbatim copy of ground.js samples()/inside() (not exported there).
//
// Usage: node tools/live/replay_app.mjs --polls refs/cache/replay/polls_relay5.jsonl --delay 7500 --out refs/cache/replay/app_relay5.jsonl.gz
//        [--dt 0.1] [--log 0.5] [--paved-fixed] [--no-routes]
// Needs a canvas module: `npm i --no-save @napi-rs/canvas` somewhere and CANVAS_MODULE=/abs/path/node_modules/@napi-rs/canvas/index.js
import fs from 'fs'; import path from 'path'; import zlib from 'zlib'; import { fileURLToPath } from 'url';

const HERE = path.dirname(fileURLToPath(import.meta.url)); const ROOT = path.resolve(HERE, '..', '..');
const argv = process.argv.slice(2); const opt = (k, d) => { const i = argv.indexOf('--' + k); return i >= 0 ? argv[i + 1] : d; }; const flag = (k) => argv.includes('--' + k);
const POLLS = opt('polls', path.join(ROOT, 'refs/cache/replay/polls_relay5.jsonl'));
const OUTF = opt('out', path.join(ROOT, 'refs/cache/replay/app_relay5.jsonl.gz'));
const DELAY = +opt('delay', 7500), DT = +opt('dt', 0.1), LOG = +opt('log', 0.5);
const PAVED_FIXED = flag('paved-fixed'), ROUTES = !flag('no-routes');

// ---- browser stubs
let createCanvas;
for (const m of [process.env.CANVAS_MODULE, '@napi-rs/canvas'].filter(Boolean)) { try { ({ createCanvas } = await import(m)); break; } catch (e) { } }
if (!createCanvas) { console.error('no canvas module: set CANVAS_MODULE to @napi-rs/canvas/index.js'); process.exit(1); }
globalThis.document = { createElement: () => createCanvas(1, 1), hidden: false };

const imp = (p) => import(path.join(ROOT, p));
const { AIRPORT } = await imp('data/sfo_airport.js'); const { DETAILS } = await imp('data/sfo_details.js'); const { STANDS } = await imp('data/sfo_stands.js');
const { PAINT } = await imp('data/sfo_paint.js'); const { PAVEMENT } = await imp('data/sfo_pavement.js');
const { standGates, paintAirportMapReal, endZoneRects } = await imp('js/live/airport.js');
const { Traffic, phaseLabel, category, antOf, RWY } = await imp('js/live/traffic.js');
const { GroundPhysics, buildingGrid } = await imp('js/live/ground.js');
const { parsePayload } = await imp('js/live/feed.js');
const { TYPES } = await imp('js/aircraft/types.js');

const gates = standGates(STANDS);
const apt = paintAirportMapReal(AIRPORT, gates, undefined, DETAILS, { paint: PAINT, pavement: PAVEMENT, endZones: endZoneRects() });
const building = buildingGrid(AIRPORT);
if (flag('dump-mask')) { // pavement + building masks sampled at 1 m in world (x,z) for the Python analysis (replay_audit.py)
  const X0 = -2700, Z0 = -2350, W = 4650, H = 4150; const buf = Buffer.alloc(W * H);
  for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) { const x = X0 + i + 0.5, z = Z0 + j + 0.5; buf[j * W + i] = (apt.paved(x, z) ? 1 : 0) | (building(x, z) ? 2 : 0); }
  fs.writeFileSync(path.join(ROOT, 'refs/cache/replay/masks_1m.pgm'), Buffer.concat([Buffer.from(`P5\n# x0 ${X0} z0 ${Z0} res 1 bit0=paved bit1=building\n${W} ${H}\n255\n`), buf]));
  console.log('masks written'); process.exit(0);
}
const gateEvents = [];
const traffic = new Traffic({ gates, airport: AIRPORT, persist: false, centerlines: DETAILS.centerlines, onGateChange: (g, tr) => gateEvents.push([simNow / 1000, g.name, tr ? tr.hex : null]) });
traffic.buildingAt = building; traffic.delay = DELAY;
const physics = new GroundPhysics({ paved: PAVED_FIXED ? apt.paved : null, building });
const removed = []; traffic.onRemove = (tr) => removed.push([simNow / 1000, tr.hex, tr.phase]);
let routes = {}; try { routes = JSON.parse(fs.readFileSync(path.join(ROOT, 'refs/cache/replay/routes.json'), 'utf8')); } catch (e) { }

// ---- copy of ground.js samples()/inside() (planform + gear points)
const hv = (h) => [Math.sin(h), -Math.cos(h)];
function samples(T, nose, h) {
  const f = hv(h), r = [-f[1], f[0]];
  const P = (along, side) => [nose[0] - f[0] * along + r[0] * side, nose[1] - f[1] * along + r[1] * side];
  const w = T.wing, span = w ? w.span / 2 : 16, le = w ? w.rootLE : T.L * 0.4, sw = Math.tan(((w && w.sweep) || 27) * Math.PI / 180);
  const tipLE = le + span * sw, tipC = w ? w.tipC : 1.5;
  const gear = [P(T.xNose ?? 3, 0), P(T.xMain, (T.track || 6) / 2), P(T.xMain, -(T.track || 6) / 2)];
  const hs = T.hstab ? T.hstab.span / 2 : 6, hx = T.hstab ? T.hstab.x + (T.hstab.rootC || 3) : T.L - 2;
  const outline = [P(0, 0), P(T.L, 0), P(tipLE + tipC / 2, span), P(tipLE + tipC / 2, -span), P(le + span * 0.5 * sw, span * 0.5), P(le + span * 0.5 * sw, -span * 0.5),
    P(hx, hs), P(hx, -hs), P(T.L * 0.25, 0), P(T.L * 0.5, 0), P(T.L * 0.75, 0), P(le, T.R), P(le, -T.R)];
  return { gear, outline, f, r };
}
function inside(A, q, m) {
  const T = A.T, f = A.f, r = A.r;
  const dx = q[0] - A.nose[0], dz = q[1] - A.nose[1];
  const x = -(dx * f[0] + dz * f[1]), y = dx * r[0] + dz * r[1];
  if (x > -m && x < T.L + m && Math.abs(y) < T.R + m) return true;
  const w = T.wing;
  if (w) { const ay = Math.abs(y), le = w.rootLE + ay * Math.tan((w.sweep || 27) * Math.PI / 180); const ch = w.rootC - (w.rootC - w.tipC) * Math.min(1, ay / (w.span / 2)); if (ay < w.span / 2 + m && x > le - m && x < le + ch + m) return true; }
  if (T.hstab && x > T.hstab.x - m && x < T.L + m && Math.abs(y) < T.hstab.span / 2 + m) return true;
  return false;
}

// ---- replay
const polls = fs.readFileSync(POLLS, 'utf8').split('\n').filter(Boolean).map(l => JSON.parse(l));
const out = zlib.createGzip(); const ws = fs.createWriteStream(OUTF); out.pipe(ws);
let simNow = polls[0].T * 1000; const tEnd = polls[polls.length - 1].T * 1000;
let k = 0, frame = 0, nextLog = simNow, nextRoute = simNow; const logEvery = LOG * 1000;
const seenAt = new Map(); const phaseLog = new Map();
out.write(JSON.stringify({ meta: { polls: POLLS, delay: DELAY, dt: DT, log: LOG, pavedFixed: PAVED_FIXED, routes: ROUTES && Object.keys(routes).length, t0: simNow / 1000, t1: tEnd / 1000 } }) + '\n');
while (simNow < tEnd) {
  while (k < polls.length && polls[k].T * 1000 <= simNow) { const P = parsePayload(polls[k].p, polls[k].T * 1000); traffic.ingest(P, polls[k].T * 1000); k++; }
  if (ROUTES && simNow >= nextRoute) {
    nextRoute = simNow + 6000;
    for (const tr of traffic.tracks.values()) {
      if (!seenAt.has(tr.hex)) seenAt.set(tr.hex, simNow);
      if (tr.route === undefined && tr.cs && tr.cs.airline && tr.last && simNow - seenAt.get(tr.hex) >= 6000) { const r = routes[tr.cs.callsign]; traffic.setRoute(tr, r === undefined ? null : r); }
    }
  }
  traffic.update(simNow, DT); physics.resolve(traffic, DT);
  for (const tr of traffic.tracks.values()) { const p = phaseLog.get(tr.hex); if (p !== tr.phase) { phaseLog.set(tr.hex, tr.phase); out.write(JSON.stringify({ ev: 'phase', t: simNow / 1000, hex: tr.hex, phase: tr.phase, rwy: tr.runway, label: phaseLabel(tr, simNow) }) + '\n'); } }
  if (simNow >= nextLog) {
    nextLog += logEvery;
    const ground = [];
    for (const tr of traffic.tracks.values()) {
      const D = tr.disp; if (!D.valid) continue;
      const T = tr.model && TYPES[tr.model.t];
      let offPave = null, inBld = null, body = null;
      if (T && D.ground) {
        const f = hv(D.hdg); const nose = [D.x + f[0] * antOf(T), D.z + f[1] * antOf(T)]; const S = samples(T, nose, D.hdg);
        offPave = S.gear.filter(g => !apt.paved(g[0], g[1])).length; inBld = S.outline.filter(p => building(p[0], p[1])).length;
        body = { hex: tr.hex, T, nose, f: S.f, r: S.r, h: D.hdg, S }; ground.push(body);
      }
      tr._row = [+(simNow / 1000).toFixed(2), tr.hex, tr.phase, tr.runway || null, tr.gate ? tr.gate.name : null, +D.x.toFixed(1), +D.y.toFixed(1), +D.z.toFixed(1), +(D.hdg * 180 / Math.PI).toFixed(1),
        +(D.pitch * 180 / Math.PI).toFixed(1), +(D.roll * 180 / Math.PI).toFixed(1), +D.gear.toFixed(2), +D.flaps.toFixed(2), +D.spoilers.toFixed(2), D.ground ? 1 : 0, +(D.gs || 0).toFixed(1), +(D.extrap || 0).toFixed(1),
        tr.stale ? 1 : 0, tr.finalInfo ? +tr.finalInfo.a.toFixed(0) : null, tr.dirSFO || null, phaseLabel(tr, simNow), category(tr), offPave, inBld, [], tr.phys && tr.phys.cur ? +Math.hypot(tr.phys.cur[0], tr.phys.cur[1]).toFixed(1) : 0,
        tr.info.flight || null, tr.info.icao || null, tr.model ? tr.model.t : null];
    }
    for (let i = 0; i < ground.length; i++) for (let j = i + 1; j < ground.length; j++) {
      const A = ground[i], B = ground[j];
      if (Math.hypot(A.nose[0] - B.nose[0], A.nose[1] - B.nose[1]) > (A.T.L + B.T.L) * 0.5 + 45) continue;
      const hit = A.S.outline.some(p => inside(B, p, 0)) || B.S.outline.some(p => inside(A, p, 0));
      if (hit) { traffic.tracks.get(A.hex)._row[24].push(B.hex); traffic.tracks.get(B.hex)._row[24].push(A.hex); }
    }
    for (const tr of traffic.tracks.values()) if (tr.disp.valid && tr._row) { out.write(JSON.stringify(tr._row) + '\n'); tr._row = null; }
  }
  simNow += DT * 1000; frame++;
}
out.write(JSON.stringify({ gateEvents, removed, physics: physics.stats }) + '\n');
out.end(); await new Promise(r => ws.on('finish', r));
console.log('frames', frame, 'polls', k, 'tracks', traffic.tracks.size, '->', OUTF);
