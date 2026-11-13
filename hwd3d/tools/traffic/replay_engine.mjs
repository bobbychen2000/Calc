// Offline harness of the HWD traffic engine (hwd3d Phase 2, P3). Runs js/live/{traffic,classifier,parking,ground}.js
// headless in Node over a P1 replay pack (out/replay/pack_<name>.json.gz, hwd-pack/1) exactly as the in-page replay shim
// feeds the app (the first lookahead_s of the window at once, then each payload at its time, display lookahead_s behind),
// and reports:
//   - event counts vs the offline classifier (out/traffic/ref_<name>.json from tools/traffic/ref_window.py, which filters
//     the Phase 1 per-event rows to the window) and the sequence sanity pairs (TT / LL, hwd_events.json quality);
//   - ground-on-pavement violations (every wheel of every drawn ground aircraft tested against site.paved; airframe in a
//     building), overlaps of drawn ground aircraft (planforms, margin 0), jumps;
//   - motion plausibility: longitudinal / lateral acceleration, turn rate, vertical speed of the DRAWN bodies (p50 / p99 /
//     max, exceedance frames) on the ground and in the air;
//   - parking: parked tracks matched to spots by kind, unspotted parked, hangared; route use across ground holes;
//   - D6: tracks by scope, overflight types / categories, airliner categories never 'hwd', no runway event for overflights;
//   - D1: masked tracks show type only; no identity string of a LADD/PIA aircraft (out/traffic/leak_<name>.json, local
//     only) anywhere in the engine output; no key used as a label; a synthetic unmasked LADD record is masked.
// usage: node tools/traffic/replay_engine.mjs <name> [--hz 10] [--pack PATH] [--minutes M] [--json out/traffic/run_<name>.json]
import fs from 'node:fs'; import zlib from 'node:zlib'; import path from 'node:path'; import { fileURLToPath } from 'node:url';
import { buildSite } from '../../js/world/site.js';
import { HWD_AIRPORT } from '../../data/hwd_airport.js';
import { TAXIGRAPH } from '../../data/hwd_taxigraph.js';
import { parsePayload, normalizeAircraft } from '../../js/live/feed.js';
import { Traffic, phaseLabel, category } from '../../js/live/traffic.js';
import { ParkingModel } from '../../js/live/parking.js';
import { GroundPhysics, samples, bodyOf, overlaps, pavedWith } from '../../js/live/ground.js';
import { PHASES } from '../../js/live/classifier.js';
import { identity } from '../../js/live/lookup.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const args = process.argv.slice(2); const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : d; };
const name = args.find(a => !a.startsWith('--') && !args[args.indexOf(a) - 1]?.startsWith('--')) || 'weekend';
const HZ = +opt('hz', 10), DT = 1 / HZ;
const packPath = opt('pack', path.join(ROOT, 'out', 'replay', `pack_${name}.json.gz`));
const pack = JSON.parse(zlib.gunzipSync(fs.readFileSync(packPath)).toString());
const L = pack.lookahead_s || 60;
const refPath = path.join(ROOT, 'out', 'traffic', `ref_${name}.json`), leakPath = path.join(ROOT, 'out', 'traffic', `leak_${name}.json`);
const REF = fs.existsSync(refPath) ? JSON.parse(fs.readFileSync(refPath)) : null;
const LEAK = fs.existsSync(leakPath) ? JSON.parse(fs.readFileSync(leakPath)).ids : [];
const t0w = Date.now();

const site = buildSite(HWD_AIRPORT);
const parking = new ParkingModel({ airport: HWD_AIRPORT, taxigraph: TAXIGRAPH, site });
const traffic = new Traffic({ airport: HWD_AIRPORT, taxigraph: TAXIGRAPH, site, parking, persist: false });
traffic.setLookahead(L);
const physics = new GroundPhysics({ site, net: traffic.net, parking });

// ---- payload expansion (replay_shim.js expand: v2 field deltas; absent = gone, state kept)
const st = {};
function expand(p) { const ac = p.d.map(r => { const a = st[r[0]] || (st[r[0]] = { hex: r[0] }); for (const k in r[1]) a[k] = r[1][k]; if (r[2]) for (const k of r[2]) delete a[k]; return { ...a }; }); return { now: p.now, dataNow: p.dataNow, seq: p.seq, _source: p._source, ac }; }

// ---- metrics
const DUMP = args.includes('--dump') ? new Map() : null;
const PAV = pavedWith(site);
const M = { bldCells: new Map(), inBldDoor: 0, frames: 0, visFrames: 0, groundFrames: 0, heliGroundFrames: 0, heliUnpaved: 0, offSite: 0, airFrames: 0, offPave: 0, offPaveMoving: 0, offPaveRoute: 0, inBld: 0, ovl: { parked: 0, mixed: 0, moving: 0 }, jumps: 0,
  offPaveCells: new Map(), ovlPairs: new Set(), offPaveTracks: new Set(), provisionalFrames: 0, phaseFrames: {}, scopeFrames: {}, updMs: [] };
const DIST = { g_along: [], g_lat: [], g_w: [], a_lat: [], a_w: [], a_vs: [], a_along: [], g_plat: [], a_plat: [], g_crab: [] };
const EXC = { g_along3: 0, g_lat3: 0, g_w30: 0, a_lat6: 0, a_w25: 0, a_vs_lim: 0, roll_along6: 0, g_plat3: 0, a_plat6: 0, g_crab10: 0 };
const prev = new Map();
// every track object of the run (the engine drops lost tracks): D1 and D6 are checked over all of them, and the identity
// / phase-label strings each one showed are collected for the leak search
const EVER = new Map(), SHOWN = new Map();
function noteShown(tr) { let S = SHOWN.get(tr.key); if (!S) SHOWN.set(tr.key, S = new Set());
  S.add(JSON.stringify(tr.ident || null)); S.add(phaseLabel(tr)); S.add(JSON.stringify(tr.phaseInfo || null)); S.add(JSON.stringify(tr.park || null)); S.add(category(tr)); }
const LIMS = 'ground: |a_long| > 3 m/s2 (taxi) or > 6 m/s2 (runway roll), |a_lat| > 3 m/s2, |turn| > 30 deg/s; air: |a_lat| > 6 m/s2 (~31 deg bank), |turn| > 25 deg/s, |vs| > 2,500 ft/min (jets 6,000) [inf limits for GA]';
function sampleFrame(now) {
  M.frames++;
  const ground = [];
  for (const tr of traffic.tracks.values()) {
    EVER.set(tr.key, tr); if (M.frames % HZ === 0) noteShown(tr);
    const D = tr.disp; if (!D.valid || !(D.alpha > 0.5) || !tr.inView || tr.hidden) { prev.delete(tr.key); continue; }
    M.visFrames++; M.phaseFrames[tr.phase] = (M.phaseFrames[tr.phase] || 0) + 1; M.scopeFrames[tr.scope] = (M.scopeFrames[tr.scope] || 0) + 1;
    if (tr.phaseInfo.provisional) M.provisionalFrames++;
    const T = tr.dims;
    let offNow = 0;
    if (D.ground && T && !tr.vehicle && T.cls !== 'heli') { const S0 = samples(T, D.x, D.z, D.hdg); offNow = S0.gear.some(g => !PAV(g[0], g[1])) ? 1 : 0; }
    if (DUMP && (M.frames % HZ === 0 || offNow)) { let d = DUMP.get(tr.key); if (!d) DUMP.set(tr.key, d = { type: tr.info.icao, cls: T && T.cls, p: [] }); d.p.push([+(now / 1000).toFixed(1), +D.x.toFixed(1), +D.z.toFixed(1), D.ground ? 1 : 0, D.route ? 1 : 0, tr.phase, +D.gs.toFixed(1), +D.hdg.toFixed(0), +(D.y).toFixed(1), offNow]); }
    if (D.ground && T && !tr.vehicle && T.cls === 'heli') { M.heliGroundFrames++; const S = samples(T, D.x, D.z, D.hdg); if (S.gear.some(g => !PAV(g[0], g[1]))) M.heliUnpaved++; const B = bodyOf(T, D.x, D.z, D.hdg); B.tr = tr; ground.push(B); }
    else if (D.ground && T && !tr.vehicle) {
      M.groundFrames++;
      const S = samples(T, D.x, D.z, D.hdg);
      if (S.gear.some(g => !site.paved(g[0], g[1]))) M.offSite++;
      const off = S.gear.filter(g => !PAV(g[0], g[1])).length;
      if (off) { M.offPave++; if (D.gs > 0.5) M.offPaveMoving++; if (D.route) M.offPaveRoute++; M.offPaveTracks.add(tr.key); const c = Math.round(D.x / 50) * 50 + ',' + Math.round(D.z / 50) * 50; M.offPaveCells.set(c, (M.offPaveCells.get(c) || 0) + 1); }
      const doorSpot = tr.park && tr.park.spotId && (parking.byId.get(tr.park.spotId) || {}).door;
      if (S.fus.some(p => site.building(p[0], p[1])) && doorSpot) M.inBldDoor++;
      else if (S.fus.some(p => site.building(p[0], p[1]))) { M.inBld++; const kb = tr.phase + '@' + Math.round(D.x / 20) * 20 + ',' + Math.round(D.z / 20) * 20 + (tr.park && tr.park.spotId ? ':' + tr.park.kind : ''); M.bldCells.set(kb, (M.bldCells.get(kb) || 0) + 1); }
      const B = bodyOf(T, D.x, D.z, D.hdg); B.tr = tr; ground.push(B);
    } else if (!D.ground) M.airFrames++;
    // kinematics of the drawn body
    const p = prev.get(tr.key);
    if (p && p.alpha > 0.99 && D.alpha > 0.99 && p.ground === D.ground) {
      const dxy = Math.hypot(D.x - p.x, D.z - p.z), v = D.gs, aL = (D.gs - p.gs) / DT;
      let dh = ((D.hdg - p.hdg + 540) % 360) - 180; const w = dh / DT; const aLat = v * w * Math.PI / 180;
      if (dxy > Math.max(v, p.gs) * DT * 1.5 + 2) M.jumps++;
      // path-based: velocity from the drawn positions, its change = the true acceleration of the drawn body; crab = angle
      // between the nose and the direction of motion (sideways sliding)
      const vx1 = (D.x - p.x) / DT, vz1 = (D.z - p.z) / DT, sp1 = Math.hypot(vx1, vz1);
      if (p.vx != null && sp1 > 1 && Math.hypot(p.vx, p.vz) > 1) { const ax = (vx1 - p.vx) / DT, az = (vz1 - p.vz) / DT; const pl = Math.abs(ax * vz1 - az * vx1) / sp1;
        (D.ground ? DIST.g_plat : DIST.a_plat).push(pl); if (D.ground && pl > 3) EXC.g_plat3++; if (!D.ground && pl > 6) EXC.a_plat6++;
        if (D.ground) { const crab = Math.abs(((Math.atan2(vx1, -vz1) * 180 / Math.PI - D.hdg) % 360 + 540) % 360 - 180); DIST.g_crab.push(crab); if (crab > 10 && sp1 > 2) EXC.g_crab10++; } }
      if (D.ground) { if (v > 0.5 || p.gs > 0.5) { DIST.g_along.push(Math.abs(aL)); DIST.g_lat.push(Math.abs(aLat)); DIST.g_w.push(Math.abs(w)); }
        const rollNow = Math.max(v, p.gs) > 10; if (!rollNow && Math.abs(aL) > 3) EXC.g_along3++; if (rollNow && Math.abs(aL) > 6) EXC.roll_along6++; if (Math.abs(aLat) > 3) EXC.g_lat3++; if (Math.abs(w) > 30) EXC.g_w30++; }
      else { DIST.a_lat.push(Math.abs(aLat)); DIST.a_w.push(Math.abs(w)); DIST.a_along.push(Math.abs(aL)); const vs = D.vs / 0.3048 * 60; DIST.a_vs.push(Math.abs(vs));
        if (Math.abs(aLat) > 6) EXC.a_lat6++; if (Math.abs(w) > 25) EXC.a_w25++; if (Math.abs(vs) > (T && T.cls === 'jet' ? 6000 : 2500)) EXC.a_vs_lim++; }
    }
    { const q = prev.get(tr.key); prev.set(tr.key, { x: D.x, z: D.z, hdg: D.hdg, gs: D.gs, ground: D.ground, alpha: D.alpha, vx: q ? (D.x - q.x) / DT : null, vz: q ? (D.z - q.z) / DT : null }); }
  }
  for (let i = 0; i < ground.length; i++) for (let j = i + 1; j < ground.length; j++) {
    const A = ground[i], B = ground[j]; if (!overlaps(A, B, 0)) continue;
    const pa = A.tr.disp.gs < 0.3, pb = B.tr.disp.gs < 0.3; const k = pa && pb ? 'parked' : pa || pb ? 'mixed' : 'moving'; M.ovl[k]++;
    M.ovlPairs.add([A.tr.key, B.tr.key].sort().join('|') + ':' + k);
  }
}
const pct = (a, q) => { if (!a.length) return null; const s = a.slice().sort((x, y) => x - y); return +s[Math.min(s.length - 1, Math.floor(q * s.length))].toFixed(2); };

// ---- run: wall clock = data clock (the shim's offset is 0 here)
const evs = pack.events; let ei = 0;
const tStart = pack.from + L, tEnd = Math.min(pack.until + L + 20, opt('minutes') ? pack.from + L + 60 * +opt('minutes') : 1e12);
let firstBatch = true;
for (let t = tStart; t <= tEnd; t += DT) {
  while (ei < evs.length && evs[ei].T <= t) {
    const p = expand(evs[ei].p); const recv = firstBatch ? tStart * 1000 : evs[ei].T * 1000;
    traffic.ingest(parsePayload(p, recv), recv); ei++;
  }
  firstBatch = false;
  const a = performance.now();
  traffic.update(t * 1000, DT); physics.resolve(traffic, DT);
  M.updMs.push(performance.now() - a);
  sampleFrame(t * 1000);
}
// end of the window: decide what is still open (contexts that would time out after it)
for (const tr of traffic.tracks.values()) for (const e of traffic.classifier.flush(tr, tEnd * 1000 + 3600e3)) traffic.event(e);

// ---- events vs the offline reference
const OFF = ['touch_and_go', 'full_stop_landing', 'takeoff', 'low_pass_unresolved', 'lift_off', 'touch_down', 'hover_taxi', 'runway_ground_move', 'landing_unresolved', 'low_transit', 'stop_and_go', 'low_approach_go_around'];
const inWin = traffic.events.filter(e => e.t >= pack.from * 1000 && e.t <= pack.until * 1000);
const cnt = {}; for (const e of inWin) { const r = cnt[e.type] || (cnt[e.type] = { total: 0, by_src: {}, by_end: {} }); r.total++; r.by_src[e.src] = (r.by_src[e.src] || 0) + 1; const k = e.rwy || '-'; r.by_end[k] = (r.by_end[k] || 0) + 1; }
const cmp = OFF.map(k => ({ type: k, live: cnt[k] ? cnt[k].total : 0, offline: REF && REF.counts[k] ? REF.counts[k].total : 0, live_src: cnt[k] ? cnt[k].by_src : {}, offline_src: REF && REF.counts[k] ? REF.counts[k].by_src : {} }));
// sequence sanity (hwd_events.json quality codes)
const code = { takeoff: 'T', full_stop_landing: 'L', touch_and_go: 'G', stop_and_go: 'S', low_approach_go_around: 'P', low_pass_unresolved: 'U', landing_unresolved: 'l' };
const byKey = new Map(); for (const e of traffic.events) if (code[e.type]) { if (!byKey.has(e.key)) byKey.set(e.key, []); byKey.get(e.key).push(e); }
const pairs = {}; for (const E of byKey.values()) { E.sort((p, q) => p.t - q.t); for (let i = 1; i < E.length; i++) if (E[i].t - E[i - 1].t < 3600e3) { const k = code[E[i - 1].type] + code[E[i].type]; pairs[k] = (pairs[k] || 0) + 1; } }
const kinds = {}; for (const e of inWin) kinds[e.kind] = (kinds[e.kind] || 0) + 1;

// ---- parking / scope / D1 at the end + over the run
const allTracks = [...traffic.tracks.values()];
const parkedNow = allTracks.filter(tr => tr.park);
const park = { parked_tracks_end: parkedNow.length, by_kind: {}, unspotted: 0, hangared: 0, park_events: inWin.filter(e => e.kind === 'park').length, unpark_events: inWin.filter(e => e.kind === 'unpark').length,
  hangar_in: inWin.filter(e => e.kind === 'hangar_in').length, hangar_out: inWin.filter(e => e.kind === 'hangar_out').length, spots_occupied: parking.occupancy().size };
for (const tr of parkedNow) { if (tr.park.inside) park.hangared++; else if (tr.park.spotId) park.by_kind[tr.park.kind] = (park.by_kind[tr.park.kind] || 0) + 1; else park.unspotted++; }
const parkEv = inWin.filter(e => e.kind === 'park'); park.park_events_matched = parkEv.filter(e => e.spot).length;
const kIdx = new Map(); park.park_event_list = parkEv.map(e => { const tr = EVER.get(e.key); if (!kIdx.has(e.key)) kIdx.set(e.key, kIdx.size + 1); return [kIdx.get(e.key), Math.round(e.t / 1000 - pack.from), (tr && tr.info.icao) || '?', e.spot || null, e.rule || null, (tr && tr.dims && +tr.dims.span.toFixed(1)) || null]; });
const scope = { end: {}, overflight_types: {}, overflight_categories: {}, hwd_types: {}, airliner_hwd: 0, overflight_with_runway_events: 0 };
const evByKey = new Map(); for (const e of traffic.events) { if (!evByKey.has(e.key)) evByKey.set(e.key, []); evByKey.get(e.key).push(e); }
const seenKeys = new Set(traffic.events.map(e => e.key));
for (const tr of allTracks) scope.end[tr.scope] = (scope.end[tr.scope] || 0) + 1;
scope.run = {}; scope.tracks_run = EVER.size;
for (const tr of EVER.values()) {
  scope.run[tr.scope] = (scope.run[tr.scope] || 0) + 1;
  if (false) scope.end[tr.scope] = (scope.end[tr.scope] || 0) + 1;
  if (tr.scope === 'overflight') { scope.overflight_types[tr.info.icao || '?'] = (scope.overflight_types[tr.info.icao || '?'] || 0) + 1; scope.overflight_categories[tr.info.category || '?'] = (scope.overflight_categories[tr.info.category || '?'] || 0) + 1;
    if ((evByKey.get(tr.key) || []).some(e => ['takeoff', 'landing', 'touch_and_go', 'stop_and_go', 'runway_taxi', 'lift_off', 'touch_down'].includes(e.kind))) scope.overflight_with_runway_events++; }
  if (tr.scope === 'hwd') scope.hwd_types[tr.info.icao || '?'] = (scope.hwd_types[tr.info.icao || '?'] || 0) + 1;
  if (tr.scope === 'hwd' && ['A3', 'A4', 'A5'].includes(tr.info.category)) { scope.airliner_hwd++; (scope.airliner_hwd_types = scope.airliner_hwd_types || []).push(`${tr.info.icao || '?'} ${tr.info.category}: ${(evByKey.get(tr.key) || []).map(e => e.kind).join(',')}`); }
}
scope.overflight_then_hwd = [...EVER.values()].filter(tr => tr.scope === 'hwd' && (evByKey.get(tr.key) || []).some(e => e.type === 'overflight')).length;
scope.overflight_tag_extra = [...evByKey.values()].reduce((n, E) => n + Math.max(0, E.filter(e => e.type === 'overflight').length - 1), 0);
scope.overflight_events = inWin.filter(e => e.kind === 'overflight').length; scope.scope_hwd_events = inWin.filter(e => e.kind === 'scope_hwd').length;
// D1
const d1 = { tracks_seen: seenKeys.size, tracks_end: allTracks.length, tracks: EVER.size, unmasked_with_identity: 0, masked: 0, masked_with_identity: 0, label_is_key: 0, leak_strings: LEAK.length, leaks_found: 0, synthetic_ladd_masked: null };
const outStrings = [];
for (const tr of allTracks) noteShown(tr);
for (const S of SHOWN.values()) for (const x of S) outStrings.push(x);
for (const tr of EVER.values()) {
  const I = tr.ident || {};
  if (I.masked) { d1.masked++; if (I.reg || I.callsign || I.operator || (I.label && I.label !== (I.icaoType || 'Aircraft'))) d1.masked_with_identity++; }
  if (I.label && I.label.toLowerCase() === String(tr.key).toLowerCase()) d1.label_is_key++;
  if (!I.masked && (I.reg || I.callsign)) d1.unmasked_with_identity++;
}
for (const e of traffic.events) outStrings.push(JSON.stringify({ ...e, key: undefined }));
const blob = outStrings.join('\n').toUpperCase();
for (const s of LEAK) if (blob.includes(s.toUpperCase())) d1.leaks_found++;
{ // a relay that did NOT mask: dbFlags 8 with registration and callsign must still come out type-only
  const a = normalizeAircraft({ hex: 'a12345', r: 'N12345', flight: 'N12345', t: 'C172', category: 'A1', dbFlags: 8, lat: 37.66, lon: -122.12, alt_baro: 'ground', _pt: 1 }, 1000);
  const I = identity({ ...a, reg: a.reg, flight: a.flight, icao: a.icao }, a.hex, null);
  d1.synthetic_ladd_masked = I.masked && !I.reg && !I.callsign && I.label === 'C172';
}

const out = {
  name, pack: path.relative(ROOT, packPath), window: { from: new Date(pack.from * 1000).toISOString(), until: new Date(pack.until * 1000).toISOString() }, lookahead_s: L, hz: HZ,
  run: { wall_s: +((Date.now() - t0w) / 1000).toFixed(1), frames: M.frames, update_ms_p50: pct(M.updMs, 0.5), update_ms_p99: pct(M.updMs, 0.99), tracks_seen: seenKeys.size, tracks_end: allTracks.length, counters: traffic.counters, net: { routes: traffic.net.routes, routeFails: traffic.net.routeFails }, classifier: traffic.classifier.counters, flow: traffic.classifier.flow },
  events_vs_offline: cmp, events_by_kind: kinds, sequence_pairs: pairs,
  visible: { aircraft_frames: M.visFrames, ground: M.groundFrames, air: M.airFrames, provisional_frames: M.provisionalFrames, phases: M.phaseFrames, scope: M.scopeFrames },
  pavement: { fixed_wing_ground_frames: M.groundFrames, heli_ground_frames: M.heliGroundFrames, heli_unpaved_frames: M.heliUnpaved, off_site_osm_pavement_frames: M.offSite, off_pavement_frames: M.offPave, off_pavement_moving: M.offPaveMoving, off_pavement_on_route: M.offPaveRoute, off_pavement_aircraft: M.offPaveTracks.size, frac: M.groundFrames ? +(M.offPave / M.groundFrames).toFixed(4) : null,
    worst_cells_50m: [...M.offPaveCells.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8), in_building_frames: M.inBld, door_spot_nose_in_hangar_frames: M.inBldDoor, in_building_where: [...M.bldCells.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6) },
  overlaps: { frames: M.ovl, pairs: M.ovlPairs.size, pair_kinds: [...M.ovlPairs].reduce((o, k) => { const t = k.split(':')[1]; o[t] = (o[t] || 0) + 1; return o; }, {}) },
  motion: { limits: LIMS, jumps: M.jumps, exceed_frames: EXC,
    path_lateral: { ground: { p50: pct(DIST.g_plat, .5), p99: pct(DIST.g_plat, .99), max: pct(DIST.g_plat, 1), n: DIST.g_plat.length }, air: { p50: pct(DIST.a_plat, .5), p99: pct(DIST.a_plat, .99), max: pct(DIST.a_plat, 1), n: DIST.a_plat.length } },
    ground_crab_deg: { p50: pct(DIST.g_crab, .5), p99: pct(DIST.g_crab, .99), max: pct(DIST.g_crab, 1) },
    ground: { along: { p50: pct(DIST.g_along, .5), p99: pct(DIST.g_along, .99), max: pct(DIST.g_along, 1) }, lat: { p50: pct(DIST.g_lat, .5), p99: pct(DIST.g_lat, .99), max: pct(DIST.g_lat, 1) }, turn_dps: { p50: pct(DIST.g_w, .5), p99: pct(DIST.g_w, .99), max: pct(DIST.g_w, 1) }, n: DIST.g_along.length },
    air: { along: { p50: pct(DIST.a_along, .5), p99: pct(DIST.a_along, .99), max: pct(DIST.a_along, 1) }, lat: { p50: pct(DIST.a_lat, .5), p99: pct(DIST.a_lat, .99), max: pct(DIST.a_lat, 1) }, turn_dps: { p50: pct(DIST.a_w, .5), p99: pct(DIST.a_w, .99), max: pct(DIST.a_w, 1) }, vs_fpm: { p50: pct(DIST.a_vs, .5), p99: pct(DIST.a_vs, .99), max: pct(DIST.a_vs, 1) }, n: DIST.a_lat.length } },
  parking: park, scope, d1, physics: physics.stats,
};
if (DUMP) { for (const tr of traffic.tracks.values()) { const d = DUMP.get(tr.key); if (d) d.fx = tr.fx.map(f => [+(f.t / 1000).toFixed(1), +f.x.toFixed(1), +f.z.toFixed(1), f.g ? 1 : 0, f.ground ? 1 : 0, f.ph, f.gs]); }
  for (const [k, d] of DUMP) if (!d.fx) d.fx = [];
  fs.writeFileSync(path.join(ROOT, 'out', 'traffic', `dump_${name}${opt('tag', '')}.json`), JSON.stringify(Object.fromEntries(DUMP))); }
const TAG = opt('tag', '');
const jp = opt('json', path.join(ROOT, 'out', 'traffic', `run_${name}${TAG}.json`)); fs.mkdirSync(path.dirname(jp), { recursive: true }); fs.writeFileSync(jp, JSON.stringify(out, null, 1));
// ---- print
console.log(`== ${name} ${out.window.from} .. ${out.window.until}  (${out.run.wall_s} s wall, ${M.frames} frames, update p50 ${out.run.update_ms_p50} ms p99 ${out.run.update_ms_p99} ms)`);
console.log('events (window)        live  offline   live src / offline src');
for (const r of cmp) console.log(`  ${r.type.padEnd(24)} ${String(r.live).padStart(3)}  ${String(r.offline).padStart(4)}    ${JSON.stringify(r.live_src)} / ${JSON.stringify(r.offline_src)}`);
console.log('kinds', JSON.stringify(kinds)); console.log('pairs', JSON.stringify(pairs));
console.log('pavement', JSON.stringify(out.pavement)); console.log('overlaps', JSON.stringify(out.overlaps));
console.log('motion', JSON.stringify(out.motion)); console.log('parking', JSON.stringify(park)); console.log('scope', JSON.stringify(scope)); console.log('d1', JSON.stringify(d1));
console.log('counters', JSON.stringify(traffic.counters), 'net', JSON.stringify(out.run.net), 'flow', JSON.stringify(out.run.flow));
console.log('visible phases', JSON.stringify(M.phaseFrames));
