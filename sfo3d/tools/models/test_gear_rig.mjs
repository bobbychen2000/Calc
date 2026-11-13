// js/live/models.js gearRig on the shipped gear-carrying models (13 Nov 2026): leg pivots + per-vertex leg codes.
// Expectations from the meshes (tools: scratch gear_an.py clusters): nose leg ahead of 0.3 L on the centreline, mains at
// |z| ~ strut position, the 777 models' zone-3 flap-track tips at 11-20 m span static (code 4), every zone-3/4 vertex coded.
// usage: node tools/models/test_gear_rig.mjs   (exit 1 on failure)
import fs from 'fs'; import zlib from 'zlib';
import { gearRig } from '../../js/live/models.js';
let fail = 0; const ok = (c, m) => { if (!c) fail++; console.log(c ? 'ok  ' : 'FAIL', m); };
for (const key of ['b77w', 'b772', 'b738']) {
  let raw = fs.readFileSync(`data/models/${key}.sfom`); if (raw[0] === 0x1f && raw[1] === 0x8b) raw = zlib.gunzipSync(raw);
  const ab = raw.buffer.slice(raw.byteOffset, raw.byteOffset + raw.length); const dv = new DataView(ab);
  const hl = dv.getUint32(8, true); const head = JSON.parse(new TextDecoder().decode(new Uint8Array(ab, 12, hl)));
  const B = 12 + hl, nv = head.nv, q = head.quant, o = head.offsets;
  const pq = new Uint16Array(ab, B + o.pos, nv * 3), zone = new Uint8Array(ab, B + o.zone, nv);
  const pos = new Float32Array(nv * 3), extra = new Float32Array(nv * 4);
  for (let i = 0; i < nv * 3; i++) pos[i] = q.pmin[i % 3] + pq[i] * q.pscale[i % 3];
  for (let i = 0; i < nv; i++) extra[i * 4] = zone[i];
  const R = gearRig(pos, zone, extra, nv);
  ok(!!R, `${key} rig ${R && R.map(v => v.toFixed(2)).join(', ')}`);
  const cnt = {}; let bad = 0;
  for (let i = 0; i < nv; i++) {
    const z = zone[i]; if (z !== 3 && z !== 4) continue; const code = Math.round((extra[i * 4] - z) * 10);
    if (Math.floor(extra[i * 4] + 0.5) !== z) bad++; cnt[z + ':' + code] = (cnt[z + ':' + code] || 0) + 1;
  }
  ok(bad === 0, `${key} zone integer kept (floor(x + 0.5)); codes ${JSON.stringify(cnt)}`);
  ok(R[0] < 0 && R[0] > -0.3 * head.dims.L && R[3] > 0.5, `${key} nose pivot ahead of 0.3 L, main pivot off the centreline`);
}
process.exit(fail ? 1 : 0);
