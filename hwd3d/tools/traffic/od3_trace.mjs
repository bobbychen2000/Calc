// OD3 case traces (hwd3d Phase 2 fix round 4, docs/phase2_run.md section 10): the per-second DRAWN state of the OD3 hero aircraft -
// case S (a light-jet take-off) and case P (a single-turboprop landing) - through the engine exactly as tools/traffic/replay_engine.mjs runs it (the
// app's opening-burst ingestion, 10 Hz, GroundPhysics), plus acceptance checks a pilot would make (rotation, flare, roll, taxi).
//
// usage: node tools/traffic/od3_trace.mjs S|P [--lookahead 120] [--out out/od3]
//   - the packs and windows come from out/od3/windows.json (gitignored, local only); the hero is the first track of the case's type
//     that lifts off (S) / touches down (P) at HWD; the trace spans 470 s before to 100 s after that event (S), 130 s before to 260 s
//     after it (P). Nothing here names a time, date or identity: the output files (out/od3/trace_case_<C>.{json,csv}, gitignored) carry
//     window-relative seconds and UTC clock times for local checking only (D1).
//   - columns: t (s from the event), x / z (m, world frame), h_ft (above the ground), gs_kt, vs_fpm, hdg (deg true), pitch / roll (deg,
//     disp.pitch / disp.roll), ground, label (the phase label the UI shows), phase, src (obs: within 2 s of a fix and not reconstructed;
//     inf otherwise), mode (the engine's target mode), along / off (m, on 28L from its threshold end / beside its centreline), flaps.
// Lookahead default 120 s: replay / snapshot packs are built with 120 s since decision (c) (docs/PLAN.md 6b; build_replay.py).
import fs from 'node:fs'; import zlib from 'node:zlib'; import path from 'node:path'; import { fileURLToPath } from 'node:url';
import { buildSite } from '../../js/world/site.js';
import { HWD_AIRPORT } from '../../data/hwd_airport.js';
import { TAXIGRAPH } from '../../data/hwd_taxigraph.js';
import { parsePayload } from '../../js/live/feed.js';
import { Traffic, phaseLabel, speedsOf } from '../../js/live/traffic.js';
import { ParkingModel } from '../../js/live/parking.js';
import { GroundPhysics, samples, pavedWith } from '../../js/live/ground.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const args = process.argv.slice(2), opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : d; };
const CASE = (args[0] || 'S').toUpperCase(), W = JSON.parse(fs.readFileSync(path.join(ROOT, 'out', 'od3', 'windows.json')));
const C = CASE === 'S' ? { win: W.od3s, kind: 'lift-off', pre: 470, post: 100 } : { win: W.od3p, kind: 'touchdown', pre: 130, post: 260 };
const pack = JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(ROOT, C.win.pack))).toString());
const L = +opt('lookahead', 120), OUTD = path.resolve(ROOT, opt('out', 'out/od3'));   // (an absolute --out is used as it is)
const site = buildSite(HWD_AIRPORT), parking = new ParkingModel({ airport: HWD_AIRPORT, taxigraph: TAXIGRAPH, site });
const traffic = new Traffic({ airport: HWD_AIRPORT, taxigraph: TAXIGRAPH, site, parking, persist: false }); traffic.setLookahead(L);
const physics = new GroundPhysics({ site, net: traffic.net, parking }), PAV = pavedWith(site);
const R = site.runways.find(r => r.id === '10R/28L');
const st = {}, expand = (p) => ({ now: p.now, dataNow: p.dataNow, seq: p.seq, _source: p._source, ac: p.d.map(r => { const a = st[r[0]] || (st[r[0]] = { hex: r[0] }); for (const k in r[1]) a[k] = r[1][k]; if (r[2]) for (const k of r[2]) delete a[k]; return { ...a }; }) });
const tS = pack.from + L; let ei = 0, first = true; const fine = new Map();   // key -> 10-Hz rows of that type's tracks
// (round 4 iteration 2, F10) the reference speeds of each candidate track, cached while its track is alive: the hero's track is removed
// before the end of the run, and speedsOf(null) then gave the class default ('gliders / ultralights / unknown', VR 52.7 kt) for the hero
const SPK = new Map();
for (let t = tS; t <= pack.until + L + 20; t += 0.1) {
  while (ei < pack.events.length && pack.events[ei].T <= t) { const e = pack.events[ei++], p = expand(e.p); const rc = first ? (p.now != null && p.now < tS * 1000 - 3000 ? p.now : tS * 1000) : e.T * 1000; traffic.ingest(parsePayload(p, rc), rc); }
  first = false; traffic.update(t * 1000, 0.1); physics.resolve(traffic, 0.1);
  const td = traffic.displayTime(t * 1000);
  for (const tr of traffic.tracks.values()) {
    if (tr.info.icao !== C.win.type || !tr.disp.valid) continue;
    if (!SPK.has(tr.key) && tr.dims) SPK.set(tr.key, traffic.spd(tr));
    const D = tr.disp, o = traffic.target(tr, td, { peek: true }), px = D.x - R.origin[0], pz = D.z - R.origin[1];
    const nf = tr.fx.reduce((m, f) => Math.min(m, Math.abs(f.t - td) / 1000), 1e9), gear = D.ground ? samples(tr.dims, D.x, D.z, D.hdg).gear : [];
    let rows = fine.get(tr.key); if (!rows) fine.set(tr.key, rows = []);
    rows.push({ tw: +(td / 1000 - pack.from).toFixed(1), utc: new Date(td).toISOString().slice(11, 21), x: +D.x.toFixed(2), z: +D.z.toFixed(2), h_ft: +((D.y - site.groundY(D.x, D.z)) / 0.3048).toFixed(1),
      gs_kt: +(D.gs / 0.514444).toFixed(1), vs_fpm: Math.round((D.vs || 0) / 0.3048 * 60), hdg: +D.hdg.toFixed(1), pitch: +((D.pitch || 0) * 180 / Math.PI).toFixed(1), roll: +((D.roll || 0) * 180 / Math.PI).toFixed(1),
      ground: D.ground, label: phaseLabel(tr, td), phase: tr.phase, src: nf <= 2 && !o.recon ? 'obs' : 'inf', mode: o.mode, alpha: +D.alpha.toFixed(2),
      along: +(R.length - (px * R.dir[0] + pz * R.dir[1])).toFixed(1), off: +(px * R.right[0] + pz * R.right[1]).toFixed(1), flaps: +(D.flapsF ?? 0).toFixed(2), gearF: +(D.gear ?? 1).toFixed(2),
      surface: site.surface(D.x, D.z), offPave: gear.some(g => !PAV(g[0], g[1])), tRest: !!(o.stop || (o.gs || 0) < 0.3) });
  }
}
// the hero: the first track of the type with the case's event within 2.5 km of the ARP
let key = null, tEv = null;
for (const [k, rows] of fine) { for (let i = 1; i < rows.length; i++) { const a = rows[i - 1], b = rows[i]; if (a.alpha < 0.99 || b.alpha < 0.99 || Math.hypot(b.x, b.z) > 2500) continue;
  if ((C.kind === 'lift-off' && a.ground && !b.ground) || (C.kind === 'touchdown' && !a.ground && b.ground)) { key = k; tEv = b.tw; break; } } if (key) break; }
if (!key) { console.error('no ' + C.kind + ' of a ' + C.win.type + ' found'); process.exit(1); }
const all = fine.get(key).filter(r => r.tw >= tEv - C.pre && r.tw <= tEv + C.post).map(r => ({ t: +(r.tw - tEv).toFixed(1), ...r }));
const rows1 = all.filter(r => Math.abs(r.t * 10 - Math.round(r.t) * 10) < 0.5);
// ---- checks (10-Hz rows)
const SP = SPK.get(key) || speedsOf(traffic.tracks.get(key) ? traffic.tracks.get(key).dims : null), chk = {};
const ev = all.findIndex(r => r.t === 0), E = all[ev], Ep = all[ev - 1];
chk.event = { kind: C.kind, along_28L_m: (C.kind === 'lift-off' ? Ep : E).along, cl_offset_m: (C.kind === 'lift-off' ? Ep : E).off, gs_kt: E.gs_kt, pitch_deg: (C.kind === 'lift-off' ? E : Ep).pitch, surface: (C.kind === 'lift-off' ? Ep : E).surface };
const seg = (a, b) => all.filter(r => r.t >= a && r.t <= b);
const maxBy = (A, f) => A.reduce((m, r) => Math.max(m, f(r)), -1e9), minBy = (A, f) => A.reduce((m, r) => Math.min(m, f(r)), 1e9);
let aG = 0, aA = 0, stall = 0, dPitch = 0, yawRoll = 0, restMoves = 0, aGt = null, aAt = null, restPlanned = 0; const restMovesT = [], restPlannedT = [];
for (let k = 1; k < all.length; k++) { const p = all[k - 1], q = all[k]; if (p.alpha < 0.99 || q.alpha < 0.99) continue;
  const a = (q.gs_kt - p.gs_kt) * 0.514444 / 0.1; if (p.ground && q.ground) { if (Math.abs(a) > Math.abs(aG)) { aG = a; aGt = q.t; } } else if (!p.ground && !q.ground) { if (Math.abs(a) > Math.abs(aA)) { aA = a; aAt = q.t; } }
  const adv = Math.hypot(q.x - p.x, q.z - p.z); if (q.ground && p.gs_kt > 20 && adv < 0.2 * p.gs_kt * 0.514444 * 0.1) stall++;
  dPitch = Math.max(dPitch, Math.abs(q.pitch - p.pitch));
  // (a pivot on a planned wait with a heading - the take-off plan's pivot before it taxis off, a line-up - is counted apart)
  // (at rest = the body below 0.6 kt AND its target resting in both frames, as the harness's rest_pose_change_frames; a body that
  // turns on a braked wheel as its target taxis off is moving, not at rest)
  if (p.ground && q.ground && p.gs_kt < 0.6 && q.gs_kt < 0.6 && p.tRest && q.tRest && (adv > 0.02 || Math.abs(((q.hdg - p.hdg) % 360 + 540) % 360 - 180) > 0.3)) {
    if (/:wait$/.test(q.mode || '') && adv <= 0.02) { restPlanned++; restPlannedT.push(q.t); } else { restMoves++; restMovesT.push(q.t); } } }
chk.max_ground_accel_ms2 = +aG.toFixed(2); chk.max_ground_accel_at = aGt; chk.max_air_accel_ms2 = +aA.toFixed(2); chk.max_air_accel_at = aAt; chk.ground_stall_frames = stall; chk.max_pitch_step_deg_per_frame = +dPitch.toFixed(2); chk.rest_pose_change_frames = restMoves; chk.rest_pose_change_at = restMovesT.slice(0, 20); chk.planned_pivot_frames = restPlanned; chk.planned_pivot_at = restPlannedT.length ? [restPlannedT[0], restPlannedT[restPlannedT.length - 1]] : null;
chk.ground_off_pavement_samples = all.filter(r => r.ground && r.offPave).length;
if (C.kind === 'lift-off') {
  const roll = seg(-60, 0).filter(r => r.ground && r.surface === 'runway'); let k = roll.length - 1; while (k > 0 && roll[k - 1].gs_kt < roll[k].gs_kt + 0.05 && roll[k - 1].gs_kt > 0.5) k--;
  const r0 = roll[k] || roll[0];
  chk.takeoff_roll = { start_t: r0 ? r0.t : null, start_gs_kt: r0 ? r0.gs_kt : null, start_along_m: r0 ? r0.along : null, liftoff_along_m: Ep.along, ground_roll_m: r0 ? +(Ep.along - r0.along).toFixed(0) : null, runway_left_m: +(R.length - Ep.along).toFixed(0), liftoff_gs_kt: E.gs_kt,
    heading_spread_on_centreline_deg: +(maxBy(roll.filter(r => r.gs_kt > 3), r => r.hdg) - minBy(roll.filter(r => r.gs_kt > 3), r => r.hdg)).toFixed(1), cl_offset_max_m: +maxBy(roll, r => Math.abs(r.off)).toFixed(2) };
  chk.rotation = { pitch_2s_before: (all[ev - 20] || {}).pitch, pitch_at_liftoff: E.pitch, pitch_max_first_30s: maxBy(seg(0, 30), r => r.pitch), climb_vs_fpm_10s: (all[ev + 100] || {}).vs_fpm };
  chk.height_drop_after_liftoff_ft = +minBy(seg(0, 40).slice(1).map((r, i, A) => ({ d: r.h_ft - (i ? A[i - 1].h_ft : E.h_ft) })), q => q.d).toFixed(1);
} else {
  const ap = seg(-40, -0.1); chk.flare = { pitch_10s_before: (all[ev - 100] || {}).pitch, pitch_at_touchdown: Ep.pitch, pitch_min_final_last_60s: minBy(seg(-60, -5), r => r.pitch), vs_fpm_at_touchdown: Ep.vs_fpm };
  chk.height_rise_before_touchdown_ft = +maxBy(ap.slice(1).map((r, i) => ({ d: r.h_ft - ap[i].h_ft })), q => q.d).toFixed(1);
  chk.rollout = { cl_offset_max_m: +maxBy(seg(0, 40).filter(r => r.ground && r.surface === 'runway'), r => Math.abs(r.off)).toFixed(2) };
}
chk.labels = [...new Set(rows1.map(r => r.label))];
// (round 4 iteration 2, F2 / F7) the label runs at 10 Hz (every change, with how long the label was shown), and the shortest run that
// is not a runway event; the heading at rest and in the line-up (the largest heading step while below 2 kt on the runway)
{ const runs = []; for (const r of all) { const q = runs[runs.length - 1]; if (!q || q.label !== r.label) runs.push({ label: r.label, t0: r.t, t1: r.t }); else q.t1 = r.t; }
  chk.label_runs = runs.map(q => [q.t0, +(q.t1 - q.t0 + 0.1).toFixed(1), q.label]);
  chk.label_short_runs = runs.slice(1, -1).filter(q => q.t1 - q.t0 + 0.1 < 2 && !/Take-off roll|Landing roll|Touch-and-go|Climbing out|Final/.test(q.label)).map(q => [q.t0, +(q.t1 - q.t0 + 0.1).toFixed(1), q.label]); }
{ let w = 0, wt = null; for (let k = 1; k < all.length; k++) { const p = all[k - 1], q = all[k]; if (!p.ground || !q.ground || q.gs_kt > 2 || q.surface !== 'runway') continue;
    const d = Math.abs(((q.hdg - p.hdg) % 360 + 540) % 360 - 180); if (d > w) { w = d; wt = q.t; } }
  chk.runway_slow_heading_step = { max_deg_per_frame: +w.toFixed(2), at: wt }; }
chk.inferred_samples = all.filter(r => r.src === 'inf').length; chk.samples = all.length;
const out = { case: CASE, type: C.win.type, lookahead_s: L, note: 'local only (gitignored): per-second drawn state of the OD3 case aircraft and acceptance checks (tools/traffic/od3_trace.mjs)',
  speeds: { vr_kt: +(SP.vr / 0.514444).toFixed(1), roll_m: SP.roll, accTO: +SP.accTO.toFixed(2), basis: SP.perf }, checks: chk, trace_1hz: rows1, trace_10hz: all };
fs.mkdirSync(OUTD, { recursive: true }); fs.writeFileSync(path.join(OUTD, `trace_case_${CASE}.json`), JSON.stringify(out, null, 1));
const cols = Object.keys(rows1[0] || {}); fs.writeFileSync(path.join(OUTD, `trace_case_${CASE}.csv`), [cols.join(','), ...rows1.map(r => cols.map(c => JSON.stringify(r[c] ?? '')).join(','))].join('\n'));
console.log(JSON.stringify({ case: CASE, lookahead_s: L, speeds: out.speeds, checks: { ...chk, label_runs: undefined } }, null, 1));
