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
// ---- plausibility checks added in fix round 1 (docs/phase2_run.md section 6): each one would have caught a review finding
//   teleports      (fix round 2: ANY absence, whatever its length) a drawn aircraft (as AircraftViews draws it: valid, in the
//                  D6 window, not hidden, alpha > 0.02) that disappears - fade cut, fade-out and removal, hideSeg, air hide,
//                  hangar - and reappears > 1.5 x speed x absence + 10 m (and > 10 m) from where it vanished. Absences that
//                  were only outside the D6 window / simulation range are window re-entries, not teleports. Each teleport
//                  is split by the signal: 'engine' (the fixes around the absence are no further apart than a polling hole
//                  plus latency, SIGNAL_LOSS_S) or 'signal' (the aircraft was not heard for longer: it moved unseen).
//                  Fix round 1 counted only absences < 5 s - finding 1 of round 2
//   ghost_parked   drawn 'parked' > 50 m from its newest fix at the display time (a stale park pose) - finding 2
//   slow_liftoff   a fixed-wing drawn leaving the ground below 0.65 x its ACD approach speed - finding 3
//   hard_stops     on the ground from > 40 kt to < 8 kt within 3 s - finding 3
//   grass_route    a drawn route / plan sample of a fixed-wing with a wheel off pavement - finding 4 (subset of off_pavement)
//   hops           a fixed-wing airborne episode < 150 s that starts and ends on the ground within 200 m - finding 5
//   air_hover      a fixed-wing drawn airborne below 0.5 x its approach speed - finding 6
//   heli_in_bldg   a helicopter drawn with any part inside a building footprint - finding 7
//   label_*        phase label contradicting the drawn state (airborne label rolling > 5 kt; ground label > 50 ft up;
//                  'parked' moving > 2 m/s; 'Helicopter on the ground' > 10 ft up) - finding 9
const SIGNAL_LOSS_S = 90;   // s: longer than any recorder hole (<= 52.4 s) + report latency (seen_pos) [inf]
const PL = { teleports: 0, teleports_hwd: 0, teleports_engine: 0, teleports_signal: 0, window_reentries: 0, teleLog: [], misaligned: 0, alignLog: [], ghost_parked_frames: 0, ghostLog: [], slow_liftoff: 0, liftLog: [], hard_stops: 0, hops: 0, hopLog: [], grass_route_frames: 0, air_hover_frames: 0, heli_in_bldg_frames: 0,
  label_air_on_ground: 0, label_ground_in_air: 0, label_parked_moving: 0, label_heli_ground_up: 0,
  // review round 3 (recheck of fix round 2): M1 silent aircraft on runways / overlapped by other traffic; M2 fast ground motion
  // off the runways and landing rolls that speed up; M3 lift-offs / touchdowns off the runway and ground -> air re-appearances
  // (a hidden take-off faded in); m4 every ground planform overlap and fixed-wing building intrusion; m5 taxi labels at speed
  stale_on_runway_frames: 0, stale_overlap_frames: 0, fast_off_runway_frames: 0, landing_roll_speed_rise: 0, liftoff_off_runway: 0, touchdown_off_runway: 0,
  ground_air_reappear: 0, taxi_label_fast_frames: 0, newLog: [],
  // review round 3, iteration 2 (recheck of fix round 3): F1 the drawn body far from its own reports / faster than them /
  // climbing faster than the type and the data; F2 low flight off the runways; F3 air pairs too close; F6 more label
  // contradictions; M3 hidden take-offs (the owner's fallback) declared by the engine and checked separately
  off_reports_samples: 0, air_overspeed_samples: 0, air_climb_samples: 0, low_air_off_runway_frames: 0, air_pair_close_frames: 0, air_pair_close_reported: 0,
  label_hold_moving: 0, label_lineup_fast: 0, label_runway_taxi_off: 0, label_no_signal_moving: 0, label_runway_in_air: 0,
  m3_hidden_takeoffs: 0, m3Log: [], xLog: [] };
// runway rectangle test (site.runways axes; m = extra half-width) - the pavement a take-off / landing roll uses
const onRwy = (x, z, m = 3) => (site.runways || []).some(r => { const px = x - r.origin[0], pz = z - r.origin[1], al = px * r.dir[0] + pz * r.dir[1], ac = px * r.right[0] + pz * r.right[1]; return al >= 0 && al <= r.length && Math.abs(ac) <= r.halfWidth + m; });
const newLog = (...a) => { if (PL.newLog.length < 400) PL.newLog.push(a); };
const LR = new Map();
const PRES = new Map(), SER = new Map();
// presence of every key as AircraftViews draws it; why it is absent (per frame)
function absentWhy(tr) {
  const D = tr.disp; if (!D.valid) return tr._far ? 'far' : 'invalid';
  if (!tr.inView) return 'window'; if (tr.hidden) return 'hidden'; if (tr.fadeOut) return 'fadeOut'; if (tr.cutting) return 'cut';
  if (tr.inHangarRest) return 'inHangar'; if (tr.airHidden) return 'airHidden'; if (tr._hideSeg) return 'hideSeg'; return 'other';
}
// the longest gap between consecutive fixes of the track inside [t0 - 60 s, t1] (display times, ms)
function fixGap(tr, t0, t1) { const F = tr.fx; let g = 0; for (let k = 1; k < F.length; k++) { if (F[k].t < t0 - 60000 || F[k - 1].t > t1) continue; g = Math.max(g, F[k].t - F[k - 1].t); } return g / 1000; }
// one re-appearance after an absence (also run on the planted cases at the end):
//  last = the drawn state before the absence {t, x, y, z, gs, ground, cls}, D = the drawn state now, td = display time (ms),
//  why = Set of absence reasons, m3 = the engine's declared hidden take-offs of this track (tr.m3Log: [{t1, x, y, z}])
//  -> { gAir, d, g, allow, jump, m3 }
// (review round 3, M3: a ground -> air re-appearance - a take-off hidden in the absence - is allowed only what the speed
// BEFORE the vanish covers; max(gs) let a hidden take-off fade in 1 km away at climb-out speed unflagged. Iteration 2 (F4):
// the state before the vanish now carries its ground flag - the test read a field that was never stored and could not fire)
// An M3 hidden take-off is the owner's fallback for a take-off no runway plan can time (traffic.js transitionFor): hidden
// from its last ground position until its first airborne fix, it appears THERE at its reported height. It is counted as
// m3_hidden_takeoffs (listed), not as a teleport, only when the body appears within 60 m (+ what it flew since) of that fix
// within 8 s of its time; any other ground -> air re-appearance is a failure.
function reappear(last, D, td, why, m3) {
  const g = (td - last.t) / 1000, d = Math.hypot(D.x - last.x, D.z - last.z, D.y - last.y);
  const gAir = !!last.ground && !D.ground && last.cls !== 'heli', allow = 1.5 * (gAir ? last.gs : Math.max(D.gs, last.gs)) * g + 10;
  const M = gAir && why.has('hideSeg') && (m3 || []).find(m => td >= m.t1 - 2000 && td <= m.t1 + 8000 && Math.hypot(D.x - m.x, D.z - m.z, D.y - m.y) < 60 + D.gs * Math.max(0, (td - m.t1) / 1000));
  return { gAir, d, g, allow, jump: d > allow && d > 10, m3: !!M };
}
function presence(now) {
  const td = traffic.displayTime(now);
  for (const [k, V] of PRES) if (!traffic.tracks.has(k) && V.last) { if (!V.absent) V.absent = { t: td, why: new Set() }; V.absent.why.add('removed'); }
  for (const tr of traffic.tracks.values()) {
    const D = tr.disp, present = !!(D.valid && tr.inView && !tr.hidden && D.alpha > 0.02 && tr.dims);
    let V = PRES.get(tr.key); if (!V) PRES.set(tr.key, V = { last: null, absent: null });
    if (present) {
      if (V.absent && V.last) {
        const Rr = reappear(V.last, D, td, V.absent.why, tr.m3Log), g = Rr.g, d = Rr.d, gAir = Rr.gAir;
        if (Rr.m3) { PL.m3_hidden_takeoffs++; if (PL.m3Log.length < 40) PL.m3Log.push([Math.round(td / 1000 - pack.from), tr.info.icao || '?', +d.toFixed(0), +g.toFixed(1), +((D.y - site.groundY(D.x, D.z)) / 0.3048).toFixed(0), (tr.m3Log[tr.m3Log.length - 1] || {}).why || '']); }
        else if (gAir && tr.dims && !tr.vehicle && Math.hypot(D.x, D.z) < 3000) { PL.ground_air_reappear++; newLog('ground_air_reappear', Math.round(td / 1000 - pack.from), tr.info.icao || '?', +d.toFixed(0), +g.toFixed(1), +((D.y - site.groundY(D.x, D.z)) / 0.3048).toFixed(0), site.surface(D.x, D.z)); }
        if (Rr.jump && !Rr.m3) {
          const why = [...V.absent.why], onlyWin = why.every(w => w === 'window' || w === 'far');
          if (onlyWin) PL.window_reentries++;
          else {
            // (a track removed and created again holds only its new fixes: the silence between the old track's newest fix and
            // the new one's first counts too)
            const f1 = tr.fx.find(f => f.t > (V.lastFixT || 0)), gap = Math.max(fixGap(tr, V.last.t, td), f1 && V.lastFixT ? (f1.t - V.lastFixT) / 1000 : 0), kind = gap > SIGNAL_LOSS_S ? 'signal' : 'engine';
            PL.teleports++; PL['teleports_' + kind]++; if (tr.scope === 'hwd') PL.teleports_hwd++;
            if (PL.teleLog.length < 60) PL.teleLog.push([Math.round(td / 1000 - pack.from), tr.info.icao || '?', tr.scope, tr.phase, +d.toFixed(0), +g.toFixed(1), why.join('+'), kind, +gap.toFixed(0)]);
          }
        }
      }
      V.absent = null; V.last = { t: td, x: D.x, y: D.y, z: D.z, gs: D.gs, ground: !!D.ground, cls: tr.dims ? tr.dims.cls : null }; V.lastFixT = tr.last ? tr.last.t : V.lastFixT;
    } else if (V.last) { if (!V.absent) V.absent = { t: td, why: new Set() }; V.absent.why.add(absentWhy(tr)); }
  }
}
// every track object of the run (the engine drops lost tracks): D1 and D6 are checked over all of them, and the identity
// / phase-label strings each one showed are collected for the leak search
const EVER = new Map(), SHOWN = new Map();
function noteShown(tr) { let S = SHOWN.get(tr.key); if (!S) SHOWN.set(tr.key, S = new Set());
  S.add(JSON.stringify(tr.ident || null)); S.add(phaseLabel(tr)); S.add(JSON.stringify(tr.phaseInfo || null)); S.add(JSON.stringify(tr.park || null)); S.add(category(tr)); }
const LIMS = 'ground: |a_long| > 3 m/s2 (taxi) or > 6 m/s2 (runway roll), |a_lat| > 3 m/s2, |turn| > 30 deg/s; air: |a_lat| > 6 m/s2 (~31 deg bank), |turn| > 25 deg/s, |vs| > 2,500 ft/min (jets 6,000) [inf limits for GA]';
function sampleFrame(now) {
  M.frames++;
  presence(now);
  const ground = [];
  for (const tr of traffic.tracks.values()) {
    EVER.set(tr.key, tr); if (M.frames % HZ === 0) noteShown(tr);
    const D = tr.disp; if (!D.valid || !(D.alpha > 0.5) || !tr.inView || tr.hidden) { prev.delete(tr.key); continue; }
    { const T0 = tr.dims, fw = T0 && T0.cls !== 'heli' && !tr.vehicle, va = ((T0 && T0.vapp_kt) || 62) * 0.514444, gy0 = site.groundY(D.x, D.z), agl = (D.y - gy0) / 0.3048;
      if (tr.phase === 'parked') { const F = tr.fx, td = traffic.displayTime(now); let k = F.length - 1; while (k > 0 && F[k].t > td) k--; if (F[k] && Math.hypot(F[k].x - D.x, F[k].z - D.z) > 50) { PL.ghost_parked_frames++; if (PL.ghostLog.length < 20) PL.ghostLog.push([Math.round(now / 1000 - pack.from - L), tr.info.icao || '?', Math.round(Math.hypot(F[k].x - D.x, F[k].z - D.z))]); } }
      if (fw && !D.ground && D.gs < 0.5 * va) PL.air_hover_frames++;
      if (fw && D.ground && D.route && samples(T0, D.x, D.z, D.hdg).gear.some(g => !PAV(g[0], g[1]))) PL.grass_route_frames++;
      if (T0 && T0.cls === 'heli' && D.ground) { const S0 = samples(T0, D.x, D.z, D.hdg); if (S0.fus.concat(S0.outline).some(p => site.building(p[0], p[1]))) PL.heli_in_bldg_frames++; }
      const ph = PHASES[tr.phase] || PHASES.unknown;
      if (fw && D.ground && ph.airborne && D.gs > 5 * 0.514444) PL.label_air_on_ground++;
      if (!D.ground && agl > 50 && ['parked', 'hangared', 'taxi', 'runup', 'hold_short'].includes(tr.phase)) PL.label_ground_in_air++;
      if (tr.phase === 'parked' && D.gs > 2) PL.label_parked_moving++;
      if (T0 && T0.cls === 'heli' && tr.phase === 'heli_ground' && agl > 10) PL.label_heli_ground_up++;
      // (review round 3) M1 / M2 / m5 per-frame checks
      if (fw && D.ground && tr.stale && samples(T0, D.x, D.z, D.hdg).gear.some(g => onRwy(g[0], g[1], 0))) { if (!tr._lgSR) newLog('stale_on_runway', Math.round(traffic.displayTime(now) / 1000 - pack.from), tr.info.icao || '?', Math.round(D.x), Math.round(D.z)); tr._lgSR = 1; PL.stale_on_runway_frames++; }
      if (fw && D.ground && D.gs > 30 * 0.514444 && !onRwy(D.x, D.z, 3)) { PL.fast_off_runway_frames++; if (M.frames % HZ === 0) newLog('fast_off_runway', Math.round(traffic.displayTime(now) / 1000 - pack.from), tr.info.icao || '?', +(D.gs / 0.514444).toFixed(0), tr.phase, Math.round(D.x), Math.round(D.z), site.surface(D.x, D.z)); }
      if (fw && ['taxi', 'hold_short', 'runup'].includes(tr.phase) && D.gs > 35 * 0.514444) { PL.taxi_label_fast_frames++; if (M.frames % HZ === 0) newLog('taxi_label_fast', Math.round(traffic.displayTime(now) / 1000 - pack.from), tr.info.icao || '?', +(D.gs / 0.514444).toFixed(0), tr.phase, site.surface(D.x, D.z)); }
      if (fw && D.ground && tr.phase === 'landing_roll') { let q = LR.get(tr.key); if (!q) LR.set(tr.key, q = { vmin: D.gs, n: 0 }); q.vmin = Math.min(q.vmin, D.gs);
        if (D.gs > q.vmin + 2) { PL.landing_roll_speed_rise++; if (!q.n++) newLog('landing_roll_speed_rise', Math.round(traffic.displayTime(now) / 1000 - pack.from), tr.info.icao || '?', +(q.vmin / 0.514444).toFixed(0), +(D.gs / 0.514444).toFixed(0), site.surface(D.x, D.z)); } }
      else LR.delete(tr.key);
      { const p0 = prev.get(tr.key); if (fw && p0 && p0.alpha > 0.5 && p0.ground !== D.ground && Math.hypot(D.x, D.z) < 2500) { const lo = p0.ground, px = lo ? p0.x : D.x, pz = lo ? p0.z : D.z;
        if (!onRwy(px, pz, 3)) { PL[lo ? 'liftoff_off_runway' : 'touchdown_off_runway']++; newLog(lo ? 'liftoff_off_runway' : 'touchdown_off_runway', Math.round(traffic.displayTime(now) / 1000 - pack.from), tr.info.icao || '?', Math.round(px), Math.round(pz), site.surface(px, pz), +(D.gs / 0.514444).toFixed(0)); } } }
      if (fw && M.frames % HZ === 0) { let S = SER.get(tr.key); if (!S) SER.set(tr.key, S = { type: tr.info.icao || '?', va, s: [] }); S.s.push([now / 1000, D.x, D.z, D.ground ? 1 : 0, D.gs, agl]); } }
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
      if (off) { if (M.frames % HZ === 0) newLog('off_pavement', Math.round(traffic.displayTime(now) / 1000 - pack.from), tr.info.icao || '?', tr.phase, Math.round(D.x), Math.round(D.z), +(D.gs / 0.514444).toFixed(0), D.route ? 'route' : '', tr.stale ? 'stale' : '');
        M.offPave++; if (D.gs > 0.5) M.offPaveMoving++; if (D.route) M.offPaveRoute++; M.offPaveTracks.add(tr.key); const c = Math.round(D.x / 50) * 50 + ',' + Math.round(D.z / 50) * 50; M.offPaveCells.set(c, (M.offPaveCells.get(c) || 0) + 1); }
      const doorSpot = tr.park && tr.park.spotId && (parking.byId.get(tr.park.spotId) || {}).door;
      // (iteration 2, F4: the fuselage AND the planform outline - wing tips, tail - are tested; the fuselage alone let a wing
      // inside a hangar pass. A parked aircraft nose-in at a hangar-door spot is reported apart, not gated)
      const inB = S.fus.some(p => site.building(p[0], p[1])) || S.outline.some(p => site.building(p[0], p[1]));
      if (inB && doorSpot) M.inBldDoor++;
      else if (inB) { M.inBld++; if (M.frames % HZ === 0) newLog('fw_in_building', Math.round(traffic.displayTime(now) / 1000 - pack.from), tr.info.icao || '?', tr.phase, Math.round(D.x), Math.round(D.z), +(D.gs / 0.514444).toFixed(0), tr.stale ? 'stale' : ''); const kb = tr.phase + '@' + Math.round(D.x / 20) * 20 + ',' + Math.round(D.z / 20) * 20 + (tr.park && tr.park.spotId ? ':' + tr.park.kind : ''); M.bldCells.set(kb, (M.bldCells.get(kb) || 0) + 1); }
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
    if (A.tr.stale || B.tr.stale) PL.stale_overlap_frames++;
    if (M.frames % 5 === 0) newLog('overlap', Math.round(traffic.displayTime(now) / 1000 - pack.from), A.tr.info.icao || '?', B.tr.info.icao || '?', k, A.tr.stale ? 'staleA' : '', B.tr.stale ? 'staleB' : '', A.tr.phase, B.tr.phase, Math.round(A.x), Math.round(A.z));
    M.ovlPairs.add([A.tr.key, B.tr.key].sort().join('|') + ':' + k);
  }
}
// ---- iteration 2 of review round 3 (F1, F2, F3, F6): measured on what AircraftViews draws (valid, in view, not hidden,
// alpha > 0.02), fixed-wing unless stated:
//   off_reports_samples      1 Hz, every aircraft: the body more than 150 m (horizontally) from the position interpolated
//                            between its two reports around the display time when those are at most 5 s apart (the late
//                            join drew aircraft minutes behind and kilometres away from their reports)
//   air_overspeed_samples    1 Hz, airborne between two airborne reports: drawn speed > 1.15 x the faster of the two
//   air_climb_samples        1 Hz, airborne: drawn climb > 1.25 x the type's take-off climb rate (traffic.spd) AND > 1 m/s
//                            more than the data supports (the reported vertical rates of the two reports, their height chord)
//   low_air_off_runway_frames airborne below 35 ft AGL within 2.5 km of the ARP and more than 30 m beside or 300 m beyond
//                            every runway (a low pass / touch-and-go drawn over the infield grass)
//   air_pair_close_frames    two airborne aircraft (helicopters too) drawn closer than 30 m (3-D) while their reports -
//                            interpolated at the display time - are 60 m or more apart (a drawn mid-air); pairs whose
//                            reports are that close are air_pair_close_reported (INFO: formation, or an unresolved echo)
//   label_*                  hold short / run-up / in hangar moving > 5 kt; lined up > 15 kt; 'runway taxi' off the runway;
//                            'No signal' moving > 2 kt; take-off / landing roll / runway taxi labels > 50 ft up
// The limits are design values [inf]; tools/traffic reports what the drawn motion does.
const inRwyBox = (x, z, lat, lon) => (site.runways || []).some(r => { const px = x - r.origin[0], pz = z - r.origin[1], al = px * r.dir[0] + pz * r.dir[1], ac = px * r.right[0] + pz * r.right[1]; return al >= -lon && al <= r.length + lon && Math.abs(ac) <= r.halfWidth + lat; });
const xLog = (...a) => { if (PL.xLog.length < 600) PL.xLog.push(a); };
function repAt(tr, td) {   // the reported (raw) position interpolated at td, and the bracketing fixes
  const F = tr.fx; if (!F.length) return null; let i = F.length - 1; while (i > 0 && F[i - 1].t > td) i--;
  const b = F[i], a = i > 0 ? F[i - 1] : null;
  if (!a || td >= b.t) return { x: b.x, z: b.z, y: b.y, a: b, b, gap: Infinity };
  const u = clamp01((td - a.t) / Math.max(1, b.t - a.t)); return { x: a.x + (b.x - a.x) * u, z: a.z + (b.z - a.z) * u, y: a.y + (b.y - a.y) * u, a, b, gap: b.t - a.t };
}
function clamp01(u) { return Math.max(0, Math.min(1, u)); }
function extraFrame(now) {
  const td = traffic.displayTime(now), t = Math.round(td / 1000 - pack.from), s1 = M.frames % HZ === 0, air = [];
  for (const tr of traffic.tracks.values()) {
    const D = tr.disp, T = tr.dims; if (!D.valid || !tr.inView || tr.hidden || !(D.alpha > 0.02) || !T || tr.vehicle) continue;
    const fw = T.cls !== 'heli', agl = (D.y - site.groundY(D.x, D.z)) / 0.3048, kt = D.gs / 0.514444, lab = tr.info.icao || '?';
    if (!D.ground) air.push(tr);
    if (s1) {
      const R = repAt(tr, td);
      if (R && R.gap <= 5000 && td >= R.a.t) { const d = Math.hypot(D.x - R.x, D.z - R.z); if (d > 150) { PL.off_reports_samples++; xLog('off_reports', t, lab, Math.round(d), tr.phase, +kt.toFixed(0)); } }
      if (fw && !D.ground && R && R.a !== R.b && !R.a.ground && !R.b.ground && R.a.gs != null && R.b.gs != null) {
        const vmax = Math.max(R.a.gs, R.b.gs) * 0.514444; if (D.gs > 1.15 * vmax) { PL.air_overspeed_samples++; xLog('air_overspeed', t, lab, +kt.toFixed(0), +(vmax / 0.514444).toFixed(0), tr.phase); }
        const cl = traffic.spd(tr).climb, dt = Math.max(1, (R.b.t - R.a.t) / 1000), chord = (R.b.y - R.a.y) / dt, vrep = Math.max(R.a.vsm ?? -1e9, R.b.vsm ?? -1e9, chord);
        if (D.vs > 1.25 * cl && D.vs > vrep + 1.0) { PL.air_climb_samples++; xLog('air_climb', t, lab, Math.round(D.vs / 0.3048 * 60), Math.round(cl / 0.3048 * 60), Math.round(vrep / 0.3048 * 60), tr.phase); }
      }
      if (fw) {
        if (['hold_short', 'runup', 'hangared'].includes(tr.phase) && kt > 5) { PL.label_hold_moving++; xLog('label_hold_moving', t, lab, tr.phase, +kt.toFixed(0)); }
        if (tr.phase === 'line_up' && kt > 15) { PL.label_lineup_fast++; xLog('label_lineup_fast', t, lab, +kt.toFixed(0)); }
        if (tr.phase === 'runway_taxi' && D.ground && !onRwy(D.x, D.z, 0)) { PL.label_runway_taxi_off++; xLog('label_runway_taxi_off', t, lab, site.surface(D.x, D.z)); }
        if (tr.phase === 'no_signal' && kt > 2) { PL.label_no_signal_moving++; xLog('label_no_signal_moving', t, lab, +kt.toFixed(0), D.ground ? 'G' : Math.round(agl) + 'ft'); }
        if (!D.ground && agl > 50 && ['takeoff_roll', 'landing_roll', 'runway_taxi'].includes(tr.phase)) { PL.label_runway_in_air++; xLog('label_runway_in_air', t, lab, tr.phase, Math.round(agl)); }
      }
    }
    if (fw && !D.ground && Math.hypot(D.x, D.z) < 2500 && agl < 35 && !inRwyBox(D.x, D.z, 30, 300)) { PL.low_air_off_runway_frames++; if (s1) xLog('low_air_off_runway', t, lab, Math.round(agl), Math.round(D.x), Math.round(D.z), +kt.toFixed(0), tr.phase, site.surface(D.x, D.z)); }
  }
  for (let i = 0; i < air.length; i++) for (let j = i + 1; j < air.length; j++) {
    const A = air[i].disp, B = air[j].disp, d = Math.hypot(A.x - B.x, A.y - B.y, A.z - B.z); if (d >= 30) continue;
    const ra = repAt(air[i], td), rb = repAt(air[j], td), dr = ra && rb ? Math.hypot(ra.x - rb.x, ra.y - rb.y, ra.z - rb.z) : 0;
    if (dr < 60) PL.air_pair_close_reported++; else { PL.air_pair_close_frames++; if (s1) xLog('air_pair_close', t, air[i].info.icao || '?', air[j].info.icao || '?', Math.round(d), Math.round(A.y - B.y), Math.round(dr)); }
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
  sampleFrame(t * 1000); extraFrame(t * 1000);
}
// plausibility from the 1-Hz series of the drawn fixed-wing bodies
for (const S of SER.values()) {
  const a = S.s;
  for (let k = 1; k < a.length; k++) { if (a[k][0] - a[k - 1][0] > 1.5) continue;
    if (a[k - 1][3] === 1 && a[k][3] === 0 && Math.max(a[k - 1][4], a[k][4]) < 0.65 * S.va) { PL.slow_liftoff++; if (PL.liftLog.length < 20) PL.liftLog.push([Math.round(a[k][0] - pack.from - L), S.type, +(Math.max(a[k - 1][4], a[k][4]) / 0.514444).toFixed(0)]); } }
  for (let k = 3; k < a.length; k++) if (a[k][3] === 1 && a[k - 3][3] === 1 && a[k - 3][4] > 40 * 0.514444 && a[k][4] < 8 * 0.514444 && a[k][0] - a[k - 3][0] < 3.5) PL.hard_stops++;
  // (fix round 2: a hop stays near and low - < 600 m from the lift-off point and < 300 ft AGL; a 140-s touch-and-go circuit
  // of an aerobatic single that lands within 200 m of where it lifted off is not one)
  for (let k = 1; k < a.length; k++) if (a[k - 1][3] === 1 && a[k][3] === 0) { let j = k, far = 0, hi = 0; while (j < a.length && a[j][3] === 0 && a[j][0] - a[j - 1][0] < 3) { far = Math.max(far, Math.hypot(a[j][1] - a[k - 1][1], a[j][2] - a[k - 1][2])); hi = Math.max(hi, a[j][5] || 0); j++; }
    if (j < a.length && a[j][3] === 1 && a[j][0] - a[k - 1][0] < 150 && Math.hypot(a[j][1] - a[k - 1][1], a[j][2] - a[k - 1][2]) < 200 && far < 600 && hi < 300) { PL.hops++; if (PL.hopLog.length < 10) PL.hopLog.push([Math.round(a[k - 1][0] - pack.from - L), S.type, Math.round(far), Math.round(hi)]); } }
}
// touch-downs / lift-offs on the HWD site whose drawn track over the last / first 2-12 s is more than 15 deg off the runway
// axis (a straight 'ag:lin' chord from a base-leg fix to the runway: review round 2, finding 5) [inf limit]
{ const RH = (site.runways || []).map(r => Math.atan2(r.dir[0], -r.dir[1]) * 180 / Math.PI);
  const off = (t) => Math.min(...RH.map(h => Math.min(Math.abs(((t - h) % 360 + 540) % 360 - 180), Math.abs(((t - h + 180) % 360 + 540) % 360 - 180))));
  for (const S of SER.values()) { const a = S.s;
    for (let k = 1; k < a.length; k++) { if (a[k][0] - a[k - 1][0] > 1.5 || Math.abs(a[k][1]) > 2500 || Math.abs(a[k][2]) > 2500 || a[k - 1][3] === a[k][3]) continue;
      const td = a[k][3] === 1, P = a.filter(q => td ? (q[0] >= a[k][0] - 12 && q[0] <= a[k][0] - 2) : (q[0] >= a[k][0] + 2 && q[0] <= a[k][0] + 12));
      if (P.length < 5) continue;
      const dx = P[P.length - 1][1] - P[0][1], dz = P[P.length - 1][2] - P[0][2]; if (Math.hypot(dx, dz) < 30) continue;
      const m = off(Math.atan2(dx, -dz) * 180 / Math.PI);
      if (m > 15) { PL.misaligned++; if (PL.alignLog.length < 20) PL.alignLog.push([Math.round(a[k][0] - pack.from - L), S.type, td ? 'touchdown' : 'lift-off', +m.toFixed(0)]); } } } }
PL.label_contradictions = PL.label_air_on_ground + PL.label_ground_in_air + PL.label_parked_moving + PL.label_heli_ground_up
  + PL.label_hold_moving + PL.label_lineup_fast + PL.label_runway_taxi_off + PL.label_no_signal_moving + PL.label_runway_in_air;   // (iteration 2, F6: the last five)
// pass / fail (fix round 2: every limit is zero - the 6-per-hour allowance of fix round 1 for re-placements is gone; the
// teleports of the gate are those the ENGINE caused with the signal continuous; a re-placement after a real signal loss
// (the aircraft moved unseen for > SIGNAL_LOSS_S) is reported as teleports_signal, also gated at 0 for HWD traffic)
const hrs = Math.max(1 / 60, (tEnd - tStart) / 3600);
const sigHwd = PL.teleLog.filter(r => r[7] === 'signal' && r[2] === 'hwd').length;
const CHECKS = { teleports_engine: [PL.teleports_engine, 0], teleports_signal_hwd: [sigHwd, 0], ghost_parked_frames: [PL.ghost_parked_frames, 0], slow_liftoff: [PL.slow_liftoff, 0], hard_stops: [PL.hard_stops, 0], hops: [PL.hops, 0],
  air_hover_frames: [PL.air_hover_frames, 0], heli_in_bldg_frames: [PL.heli_in_bldg_frames, 0], label_contradictions: [PL.label_contradictions, 0], grass_route_frames: [PL.grass_route_frames, 0],
  misaligned_transitions: [PL.misaligned, 0],
  // review round 3: M1 (silent aircraft on a runway / in an overlap), M2 (ground > 30 kt off a runway, landing roll speeding up),
  // M3 (lift-off / touchdown off the runway, ground -> air re-appearance), m4 (any ground overlap, fixed-wing in a building), m5
  stale_on_runway_frames: [PL.stale_on_runway_frames, 0], stale_overlap_frames: [PL.stale_overlap_frames, 0], fast_off_runway_frames: [PL.fast_off_runway_frames, 0],
  landing_roll_speed_rise: [PL.landing_roll_speed_rise, 0], liftoff_off_runway: [PL.liftoff_off_runway, 0], touchdown_off_runway: [PL.touchdown_off_runway, 0], ground_air_reappear: [PL.ground_air_reappear, 0],
  ground_overlap_frames: [M.ovl.parked + M.ovl.mixed + M.ovl.moving, 0], fw_in_building_frames: [M.inBld, 0], taxi_label_fast_frames: [PL.taxi_label_fast_frames, 0],
  // review round 3, iteration 2: F1 / F2 / F3 (see extraFrame)
  off_reports_samples: [PL.off_reports_samples, 0], air_overspeed_samples: [PL.air_overspeed_samples, 0], air_climb_samples: [PL.air_climb_samples, 0], low_air_off_runway_frames: [PL.low_air_off_runway_frames, 0], air_pair_close_frames: [PL.air_pair_close_frames, 0] };
// (iteration 2, F4) planted cases: each gate below must FIRE on its planted input and must NOT fire on its planted
// exception - a gate that cannot fire is dead code (ground_air_reappear read a field that was never stored)
{ const last = { t: 0, x: 0, y: 12, z: 0, gs: 0, ground: true, cls: 'single_hw' }, Dp = { x: -800, y: 45, z: -400, gs: 36, ground: false };
  const why = new Set(['hideSeg']), r1 = reappear(last, Dp, 48000, why, null), r2 = reappear(last, Dp, 48000, why, [{ t1: 47500, x: -790, y: 44, z: -405 }]);
  const r3 = reappear({ ...last, ground: false, gs: 36 }, { ...Dp, x: 40, z: -20 }, 1000, new Set(['cut']), null);
  const ok = r1.gAir && r1.jump && !r1.m3 && r2.m3 && !r3.jump;
  CHECKS.planted_reappear = [ok ? 0 : 1, 0]; }
{ const okLow = !inRwyBox(0, -700, 30, 300) && inRwyBox(site.runways[0].origin[0], site.runways[0].origin[1], 30, 300);
  CHECKS.planted_low_air_box = [okLow ? 0 : 1, 0]; }
// reported, not gated: transitions without a take-off / landing plan (the straight fallback chord) - review round 2, finding 5
const INFO = { m3_hidden_takeoffs: PL.m3_hidden_takeoffs, air_pair_close_reported: PL.air_pair_close_reported, transition_linear: traffic.counters.transitionLinear || 0, transition_plans: traffic.counters.transitionPlans || 0, transition_fallback: traffic.counters.transitionFallback || 0, teleports_per_h: +(PL.teleports / hrs).toFixed(1), window_reentries: PL.window_reentries };
const FAILED = Object.entries(CHECKS).filter(([k, [v, lim]]) => v > lim).map(([k]) => k);
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
{ // review round 2, finding 7: a late D1 flag ('forget' from the relay, SSE or poll) leaves a type-only card that says LADD /
  // PIA (maskWhy 'd1'), no registration / callsign, and the track is not persisted
  const t2 = new Traffic({ airport: HWD_AIRPORT, taxigraph: TAXIGRAPH, site, parking: null, persist: false }); const nowS = 1.8e9;
  t2.ingest(parsePayload({ now: nowS * 1000, ac: [{ hex: 'a12345', r: 'N12345', flight: 'N12345', t: 'C172', category: 'A1', lat: 37.66, lon: -122.12, alt_baro: 'ground', _pt: nowS }] }, nowS * 1000), nowS * 1000);
  const before = t2.tracks.get('a12345'); const hadReg = !!(before && before.ident && before.ident.reg);
  t2.forget(['a12345']); const I2 = before && before.ident;
  d1.late_flag_forget_ok = hadReg && !!I2 && I2.masked && I2.maskWhy === 'd1' && !I2.reg && !I2.callsign && I2.label === 'C172' && !!before.fadeOut === !!before.disp.valid;
  CHECKS.d1_late_flag_forget = [d1.late_flag_forget_ok ? 0 : 1, 0]; if (!d1.late_flag_forget_ok) FAILED.push('d1_late_flag_forget');
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
  parking: park, scope, d1, physics: physics.stats, plausibility: PL, checks: CHECKS, checks_failed: FAILED, info: INFO,
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
console.log('plausibility', JSON.stringify({ ...PL, teleLog: undefined, ghostLog: undefined, liftLog: undefined, hopLog: undefined, alignLog: undefined, newLog: undefined, m3Log: undefined, xLog: undefined }));
if (PL.m3Log.length) console.log('m3 hidden take-offs [t s, type, m from the last drawn ground pose, absent s, ft AGL at the fix, why]', JSON.stringify(PL.m3Log));
if (PL.teleLog.length) console.log('teleports [t s, type, scope, phase, m, absent s, why, engine|signal, longest fix gap s]', JSON.stringify(PL.teleLog));
if (PL.alignLog.length) console.log('misaligned [t s, type, kind, deg off the runway]', JSON.stringify(PL.alignLog));
if (PL.hopLog.length) console.log('hops [t s, type, max m from lift-off, max ft AGL]', JSON.stringify(PL.hopLog));
if (PL.newLog.length && args.includes('--log')) for (const r of PL.newLog) console.log('log', JSON.stringify(r));
if (PL.xLog.length && args.includes('--log')) for (const r of PL.xLog) console.log('xlog', JSON.stringify(r));
console.log('INFO', JSON.stringify(INFO));
console.log('CHECKS', Object.entries(CHECKS).map(([k, [v, lim]]) => `${k} ${v} (<= ${lim}) ${v > lim ? 'FAIL' : 'ok'}`).join(' | '));
console.log(FAILED.length ? 'RESULT: FAILED ' + FAILED.join(', ') : 'RESULT: ALL PLAUSIBILITY CHECKS PASSED');
if (args.includes('--strict') && FAILED.length) process.exitCode = 1;
