// SHA Live 3D, Phase 3 package E: the static gate-timing table data/sha_gate_times.json / .js (window.SHA_GATE_TIMES).
// Design docs/phase3/design.md §1.5 / §7.1 (GateTimes); report docs/phase3/gates_time.md.
//
//   node tools/sim/build_gate_times.mjs            (from sha3d/ or anywhere; ~1-2 min; deterministic)
//   node tools/sim/build_gate_times.mjs --check    (rebuild in memory and compare with the committed file; exit 1 if stale)
//
// The gate engine (js/live/gate_system.js) runs in node with the WebGL stub (tools/sim/gl_stub.mjs), booted exactly as the
// page's gates extension boots it; js/live/gates.js gateTimes() measures, for every bridge stand (56) and the two
// alternative positions on a base stand's bridges (238A, 259A), and for every TYPES key that fits the stand (the engine's
// accepted types plus the drawn models of the stand-in types, data/sha_sim_inputs.json params.standIns), [dock_s, undock_s,
// hurry_s, pushClear_s] with every other stand empty. The sim (C1) schedules with these numbers, so every device agrees;
// the page re-measures a few stands at boot and only logs a difference (js/live/gate_sync.js check()).
// inputs_sha256_16: the first 16 hex of the sha256 over the files the numbers depend on (listed in `inputs`) and the
// stand-in table; tools/sim/test_gate_sync.mjs fails when it is stale.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { bootGateEngine, SHA3D } from './gl_stub.mjs';

export const INPUT_FILES = ['js/live/gate_system.js', 'js/live/gates.js', 'js/live/gate_sync.js', 'js/aircraft/types.js', 'js/aircraft/fit.js', 'js/aircraft/dock.js',
  'js/world/gates.js', 'js/geo.js', 'data/models/manifest.js', 'data/sha_stands.json', 'data/sha_airport.json', 'data/sha_taxigraph.json', 'tools/sim/gl_stub.mjs', 'tools/sim/build_gate_times.mjs'];
const canon = (x) => Array.isArray(x) ? '[' + x.map(canon).join(',') + ']' : x && typeof x === 'object' ? '{' + Object.keys(x).sort().map(k => JSON.stringify(k) + ':' + canon(x[k])).join(',') + '}' : JSON.stringify(x);
export function standIns() {
  const j = JSON.parse(fs.readFileSync(path.join(SHA3D, 'data/sha_sim_inputs.json'), 'utf8'));
  const S = (j.params && j.params.standIns) || {}; const out = {};
  for (const k of Object.keys(S).sort()) out[k] = { model: S[k].model, spanM: S[k].spanM, lenM: S[k].lenM };
  return out;
}
export function inputsHash(si = standIns()) {
  const h = crypto.createHash('sha256');
  for (const f of INPUT_FILES) { h.update(f + '\n'); h.update(fs.readFileSync(path.join(SHA3D, f))); h.update('\n'); }
  h.update('standIns\n' + canon(si));
  return h.digest('hex').slice(0, 16);
}
const q = (a, p) => { if (!a.length) return null; const s = a.slice().sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(p * (s.length - 1) + 1e-9))]; };
const REF = { B: 'crj9', C: 'a321', CL: 'b753', D: 'b763', E: 'a333', EL: 'b77w', F: 'b748' };

export async function buildTable() {
  const E = await bootGateEngine();
  const si = standIns();
  const t0 = performance.now();
  const R = E.gatesMod.gateTimes(E.sys, E.gates, null, { standIns: si });
  const ms = performance.now() - t0;
  // order: stands by name, keys by name (deterministic output)
  const stands = {}, dockN = {};
  for (const n of Object.keys(R.stands).sort()) { stands[n] = {}; dockN[n] = {}; for (const k of Object.keys(R.stands[n]).sort()) { stands[n][k] = R.stands[n][k]; dockN[n][k] = R.dockN[n][k]; } }
  const all = Object.values(stands).flatMap(o => Object.values(o));
  const ref = []; for (const n of Object.keys(stands)) { const g = E.byName.get(n); const k = g && REF[g.cls]; if (k && stands[n][k]) ref.push(stands[n][k]); }
  const st = (rows, i) => ({ p50: q(rows.map(r => r[i]), 0.5), p90: q(rows.map(r => r[i]), 0.9), max: q(rows.map(r => r[i]), 1) });
  const zero = []; for (const n of Object.keys(dockN)) for (const k of Object.keys(dockN[n])) if (!dockN[n][k]) zero.push(n + ':' + k);
  const out = {
    v: 1, inputs_sha256_16: inputsHash(si), src: 'inf',
    note: 'Gate timings measured on the sha3d gate engine (js/live/gate_system.js, Oshkosh AeroTech sell-sheet rates, inf placeholder: the bridge make at ZSSS is unknown) in node with the WebGL stub, each stand x type alone (every other stand empty). The sim schedules with these numbers (design §1.5); the page re-measures sampled stands at boot and only logs a difference.',
    generator: 'tools/sim/build_gate_times.mjs (node; tools/sim/gl_stub.mjs)',
    fields: ['dock_s', 'undock_s', 'hurry_s', 'pushClear_s'],
    basis: {
      dock_s: 'dock call (setOccupant with the arrival, animated) -> docked: DOCK_DELAY 12 s + the docking path at the sheet rates; 22 s fallback animation where no bridge docks the type (dockN 0)',
      undock_s: 'undockEarly from docked -> every bridge at rest: the levelled retraction at the sheet rates (16 s fallback where no bridge docks)',
      hurry_s: 'undockEta from docked: the retraction at the sheet maximum rates (hurryPlans(undockPlans(g), 1).T)',
      pushClear_s: 'pushClearEta from docked: every bridge clear of the straight push-back sweep (pushHitK) at the maximum rates',
      rounding: 'each value rounded up to 0.1 s',
      pose: 'the type parked by the stop convention: nose wheel on the stand stop node (gate_system.js standTip), stand heading; 238A / 259A on the base stand bridges with their own pose',
      fit: 'the engine accepted types (span <= stand max + 0.6 m, length <= max + 2 m) plus the drawn model of each stand-in type whose own span and length fit (sha_sim_inputs params.standIns)',
    },
    rules: { dockAfterOnblockS: 20, undockLead: 'max(150 s, undock_s + 15 s) before off-block', src: 'inf (design §1.5 / §4.3; sfo3d DOCK_WAIT_MS 20 s)' },
    inputs: INPUT_FILES.concat(['data/sha_sim_inputs.json params.standIns']),
    stats: { stands: Object.keys(stands).length, bridgeStands: Object.keys(stands).filter(n => !R.alt[n]).length, altPositions: Object.keys(R.alt).length, entries: all.length,
      classReference: { n: ref.length, dock_s: st(ref, 0), undock_s: st(ref, 1), hurry_s: st(ref, 2), pushClear_s: st(ref, 3) },
      all: { dock_s: st(all, 0), undock_s: st(all, 1), hurry_s: st(all, 2), pushClear_s: st(all, 3) },
      noBridgeDocks: zero.length },
    alt: R.alt, stands, dockN,
  };
  return { out, ms, zero };
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname);
if (isMain) {
  const { out, ms, zero } = await buildTable();
  // one top-level field per line, one stand per line (readable diffs; plain JSON)
  const L = ['{']; const top = Object.keys(out);
  top.forEach((k, i) => { const v = out[k], c = i < top.length - 1 ? ',' : '';
    if (k === 'stands' || k === 'dockN') { L.push(JSON.stringify(k) + ':{'); const ns = Object.keys(v); ns.forEach((n, j) => L.push(JSON.stringify(n) + ':' + JSON.stringify(v[n]) + (j < ns.length - 1 ? ',' : ''))); L.push('}' + c); }
    else L.push(JSON.stringify(k) + ':' + JSON.stringify(v) + c); });
  L.push('}'); const json = L.join('\n') + '\n';
  const js = '// generated by tools/sim/build_gate_times.mjs - do not edit (src inf; docs/phase3/gates_time.md)\nwindow.SHA_GATE_TIMES = ' + json.trimEnd() + ';\n';
  const fj = path.join(SHA3D, 'data/sha_gate_times.json'), fs2 = path.join(SHA3D, 'data/sha_gate_times.js');
  const md5 = (s) => crypto.createHash('md5').update(s).digest('hex');
  if (process.argv.includes('--check')) {
    const old = fs.existsSync(fj) ? fs.readFileSync(fj, 'utf8') : '';
    const same = old === json; console.log(`gate times: built in ${(ms / 1000).toFixed(1)} s, ${out.stats.entries} entries; committed file ${same ? 'UP TO DATE' : 'STALE'} (md5 ${md5(old)} vs ${md5(json)})`);
    process.exit(same ? 0 : 1);
  }
  fs.writeFileSync(fj, json); fs.writeFileSync(fs2, js);
  const S = out.stats;
  console.log(`gate times: ${S.stands} stands (${S.bridgeStands} bridge stands + ${S.altPositions} alternative positions), ${S.entries} stand x type entries in ${(ms / 1000).toFixed(1)} s; inputs ${out.inputs_sha256_16}; md5 ${md5(json)}`);
  console.log('class reference', JSON.stringify(S.classReference));
  console.log('all entries   ', JSON.stringify(S.all));
  console.log(`no bridge docks the type: ${zero.length} entries ${JSON.stringify(zero.slice(0, 30))}${zero.length > 30 ? ' ...' : ''}`);
  console.log('wrote', path.relative(process.cwd(), fj), fs.statSync(fj).size, 'B and', path.relative(process.cwd(), fs2), fs.statSync(fs2).size, 'B');
}
