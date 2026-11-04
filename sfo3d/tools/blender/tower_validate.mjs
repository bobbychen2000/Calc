// Validate a .glb with the Khronos glTF-Validator and print a JSON summary (used by tools/blender/build_tower.py).
// The validator (Apache-2.0) is a third-party npm package kept outside the repo:
//   npm i --prefix refs/cache/engine/node gltf-validator@2.0.0-dev.3.10      (recorded in refs/cache/engine/node/SOURCES.json)
// Run: node tools/blender/tower_validate.mjs data/buildings3d/tower.glb [modules dir, default refs/cache/engine/node]
import fs from 'fs';
import path from 'path';
import { createRequire } from 'module';

const [file, mods = 'refs/cache/engine/node'] = process.argv.slice(2);
const require = createRequire(path.resolve(mods, 'node_modules', 'noop.js'));
const validator = require('gltf-validator');
const r = await validator.validateBytes(new Uint8Array(fs.readFileSync(file)), { maxIssues: 1000 });
const codes = {};
for (const m of r.issues.messages) codes[`${['error', 'warning', 'info', 'hint'][m.severity]}:${m.code}`] = (codes[`${['error', 'warning', 'info', 'hint'][m.severity]}:${m.code}`] || 0) + 1;
console.log(JSON.stringify({
  validator: r.validatorVersion, errors: r.issues.numErrors, warnings: r.issues.numWarnings, infos: r.issues.numInfos, hints: r.issues.numHints,
  codes, first: r.issues.messages.filter((m) => m.severity <= 1).slice(0, 10).map((m) => `${m.code} ${m.pointer || ''} ${m.message}`),
  drawCalls: r.info && r.info.drawCallCount, triangles: r.info && r.info.totalTriangleCount, vertices: r.info && r.info.totalVertexCount,
}));
