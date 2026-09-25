// Dump the app's aircraft geometry (js/aircraft/types.js, after applySpec) for the Python stand checker
// (tools/stands/geom.py, review round 2: the checker must use the planforms and door tables the app renders).
// Output: refs/cache/stands/app_types.json  {ICAO designator: {key, L, span, R, wing, hstab, doors, doorsOpt, dock2, eng, rear, xMain, track}}
// Usage: node tools/stands/dump_types.mjs
import { TYPES, ICAO_TYPES } from '../../js/aircraft/types.js';
import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const out = {};
for (const [icao, key] of Object.entries(ICAO_TYPES)) {
  const T = TYPES[key]; if (!T) continue;
  const w = T.wing, h = T.hstab;
  out[icao] = { key, L: T.L, span: w ? w.span : null, R: T.R, Ln: T.Ln ?? null,
    wing: w ? { rootLE: w.rootLE, rootC: w.rootC, tipC: w.tipC, sweep: w.sweep ?? 27, kinkZ: w.kinkZ, kinkC: w.kinkC } : null,
    hstab: h ? { span: h.span, x: h.x, rootC: h.rootC } : null,
    doors: T.doors || [], doorsOpt: T.doorsOpt || [], dock2: T.dock2 ?? null,
    // review round 3: engine nacelles for the collision planform (js/aircraft/model.js: underwing front at the wing LE
    // at z (LE measured from z0 = 0.88 R) minus fwd; rear = fuselage-mounted, front at x)
    eng: (T.eng || []).map(e => ({ z: e.z, len: e.len, r: e.r, fwd: e.fwd })), rear: T.rear ? { x: T.rear.x, z: T.rear.z, len: T.rear.len, r: T.rear.r } : null,
    xMain: T.gear && T.gear.main ? T.gear.main[0].x : null, track: T.gear && T.gear.main ? T.gear.main[0].z * 2 : null };
}
mkdirSync(join(ROOT, 'refs', 'cache', 'stands'), { recursive: true });
writeFileSync(join(ROOT, 'refs', 'cache', 'stands', 'app_types.json'), JSON.stringify(out, null, 1));
console.log(Object.keys(out).length, 'types ->', 'refs/cache/stands/app_types.json');
