// Dump of the app's jet-bridge levels and FIXED solids (walkway, rotunda drum) for the 3-D building assets
// (tools/blender: dom_geom.py door frames / vestibules / drum notches, verify_domestic_r2.py, verify_itb.py).
//
// Close-out round 3, fix round 2 (verifier finding v1 / v6): the domestic bridge-attachment elements assumed one 5.4-m
// bridge floor; js/live/gates.js now carries a level per pier (DEPARTURE_LEVELS: C 3.2, D 3.65, E / F 4.88, G 2.7, A / B
// 5.4) and the probes read a scene2d.json extracted before that change. This script runs the app's own gates.js in Node
// (no browser: the same prep as the bridges track's bcheck2 harness) and writes, per bridge of every contact stand:
//   stand, gate, door, upper, Hb / HbTag / HbSrc (the pier level), Hr (rotunda floor), rotR, rot [x, z],
//   walk = the app's fixed-walkway polyline [x, floor above the apron, z] (gates.js walkY: Hb at the building, Hr at
//   the rotunda), walkLen, and the rest-pose solids of the fixed parts (gates.js solidsQ(..., fixed=true): walkway
//   segments and the rotunda drum; lo / hi above the APRON, i.e. GROUND_Y subtracted).
// It records the SHA-256 of every input so the Python side can refuse a stale dump (tools/blender/app_bridges.py).
//
// Usage: node tools/blender/app_bridges.mjs            -> tools/blender/app_bridges.json  (committed: the build input)
//        node tools/blender/app_bridges.mjs <out.json>
// Light (< 1 GB, ~1 min): no heavy lock needed.
import fs from 'fs'; import path from 'path'; import crypto from 'crypto'; import { fileURLToPath, pathToFileURL } from 'url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..', '..');
const OUT = process.argv[2] || path.join(HERE, 'app_bridges.json');
globalThis.document = { createElement: () => ({ getContext: () => null }), hidden: false };
const imp = (p) => import(pathToFileURL(path.join(ROOT, p)).href);
const { STANDS } = await imp('data/sfo_stands.js');
const { standGates } = await imp('js/live/airport.js');
const GJ = await imp('js/live/gates.js');
const { GROUND_Y: G } = await imp('js/geo.js');
const { LiveGateSystem, DEPARTURE_LEVELS } = GJ;

const gates = standGates(STANDS);
const gsys = Object.create(LiveGateSystem.prototype); gsys.gates = gates; gsys.anims = new Map(); gsys.dirty = false;
gsys.attachUpper();
for (const g of gates) for (const b of gsys.bridgesOf(g)) gsys.prepBridge(g, b);
gsys.finishPrep();

const r3 = (v) => Math.round(v * 1000) / 1000;
const out = [];
for (const g of gates) {
  if (!g.bridge) continue;
  for (const b of gsys.bridgesOf(g)) {
    const walk = (b.walk || []).map((p, i) => [r3(p[0]), r3(gsys.walkY(b, i)), r3(p[2])]);
    const rest = gsys.solidsQ(b, { a: b.a0, e: b.e0, t: 0, h: b.h0 }, 0, true)
      .filter(s => s.part === 'walkway' || s.part === 'rotunda')
      .map(s => ({ part: s.part, seg: s.seg, c: [r3(s.c[0]), r3(s.c[1])], u: [r3(s.u[0]), r3(s.u[1])], hl: r3(s.hl), hw: r3(s.hw),
                   lo: r3(s.lo - G), hi: r3(s.hi - G), round: s.round != null ? r3(s.round) : undefined }));
    out.push({ stand: g.name, letter: (g.pier || g.letter || g.name[0]), gate: b.gate, door: b.door, upper: !!b.upper,
               Hb: r3(b.Hb), HbTag: b.HbTag, HbSrc: b.HbSrc, Hr: r3(b.Hr), rotR: r3(b.rotR), rot: [r3(b.rot[0]), r3(b.rot[2])],
               walkLen: r3(b.walkLen || 0), walkFrom: b.walkFrom || 0, twin: !!b.twinOf, walk, rest });
  }
}
const sha = (p) => crypto.createHash('sha256').update(fs.readFileSync(path.join(ROOT, p))).digest('hex');
const inputs = {};
for (const p of ['js/live/gates.js', 'data/sfo_stands.js', 'data/sfo_buildings.js', 'js/live/airport.js', 'js/geo.js']) inputs[p] = sha(p);
const J = { about: 'js/live/gates.js bridge levels + fixed rest solids (heights above the apron, m); tools/blender/app_bridges.mjs',
            generated: new Date().toISOString(), groundY: G, departure_levels: DEPARTURE_LEVELS, inputs, bridges: out };
fs.writeFileSync(OUT, JSON.stringify(J));
const by = {}; for (const b of out) { const k = b.letter; by[k] = by[k] || new Set(); by[k].add(b.Hb); }
console.log('app_bridges:', out.length, 'bridges ->', path.relative(ROOT, OUT), Object.entries(by).map(([k, v]) => k + ' ' + [...v].join('/')).join(', '));
