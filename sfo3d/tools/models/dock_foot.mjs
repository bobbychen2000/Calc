#!/usr/bin/env node
// Skin of every docking door over the jet-bridge bellows footprint, measured on the RENDERED mesh, for
// js/aircraft/dock.js (the bellows front follows the fuselage: AC 150/5220-21C §2.3.f(3), "a folding bellows aircraft
// closure. The closure, when fitted to the aircraft fuselage, must surround both the open aircraft door and the doorway").
//
// Why a measured table (review 5 Nov 2026, aircraft-v1): the flat bellows front, 3.1 m along the fuselage at T.dockHW (the
// skin at the door's own station), cut 0.17-0.25 m into the tapering nose skin at its aft end on every widebody door 1
// and stood 0.2-0.4 m off it at its forward end. The section table of data/models/features.json (1 m stations, 8 height
// fractions) is too coarse for the bellows: interpolated over the footprint it is 0.05-0.23 m off the mesh in the taper.
//
// Method: each type's model is decoded, stretched (js/aircraft/stretch.js applyStretch with T.fit.stretch) and placed
// exactly as js/live/aircraft.js placement() draws it (scale, seating, stance pitch), then cut with planes at the stations
// X + ds (X = the dock station js/live/gates.js doorOf uses: T.dockX1 / T.dockX2 / T.dockX3, ds = aft) and intersected
// with the heights sill + dz; the value is the outermost left-side skin (zones base 0 and glass 5, the zones the
// review measured) within hw + 0.6 m of the centre line (hw = the cab stop T.dockHW / 2 / 3: nothing beyond the cab front
// can be the skin at the door), null where no skin is cut (above the crown). Every grid records the X / sill / hw it was
// measured for; js/aircraft/dock.js ignores a grid whose door has moved since (a refit without a re-run).
//
// Output: data/models/dock_foot.js (DOCK_FOOT). Run after any change to js/aircraft/fit.js, js/aircraft/types.js or a
// model:   node tools/models/dock_foot.mjs            (write)
//          node tools/models/dock_foot.mjs --check    (no write; staleness + the drawn bellows (js/aircraft/dock.js)
//                                                     against finer mesh cuts, JSON on stdout: tools/models/check_dims.py)
import fs from 'fs'; import zlib from 'zlib'; import path from 'path'; import { fileURLToPath } from 'url';
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const fit = await import(path.join(ROOT, 'js/aircraft/fit.js'));
const { TYPES } = await import(path.join(ROOT, 'js/aircraft/types.js'));
const { applyStretch } = await import(path.join(ROOT, 'js/aircraft/stretch.js'));
const { m4 } = await import(path.join(ROOT, 'js/math.js'));

export const GRID = { ds: 0.4, n: 4, dz: 0.15, m: 20 };      // stations -1.6..+1.6 m (the bellows is 3.1-3.2 m long), heights sill..sill + 3.0 m
const REACH_OUT = 0.6;                                        // m beyond hw: the cab front (js/live/gates.js fr = spacer - 0.45 + bellows 0.6)

function decode(m) {
  const raw0 = fs.readFileSync(path.join(ROOT, 'data/models', m + '.sfom')); const raw = (raw0[0] === 0x1f && raw0[1] === 0x8b) ? zlib.gunzipSync(raw0) : raw0;
  const buf = raw.buffer.slice(raw.byteOffset, raw.byteOffset + raw.length); const dv = new DataView(buf);
  const hl = dv.getUint32(8, true); const head = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 12, hl)));
  const B = 12 + hl, nv = head.nv, q = head.quant, o = head.offsets;
  const pq = new Uint16Array(buf, B + o.pos, nv * 3), zone = new Uint8Array(buf, B + o.zone, nv).slice();
  const pos = new Float32Array(nv * 3); for (let i = 0; i < nv; i++) for (let k = 0; k < 3; k++) pos[i * 3 + k] = q.pmin[k] + pq[i * 3 + k] * q.pscale[k];
  const idx = head.idxType === 'u16' ? new Uint16Array(buf, B + o.idx, head.ni).slice() : new Uint32Array(buf, B + o.idx, head.ni).slice();
  return { head, pos, zone, nv, idx };
}
const decoded = new Map();
// vertex positions of type t (model m) in the aircraft frame of js/live/aircraft.js placement() (x forward, station X at
// local x = T.xMain - X; y above the ground; z to starboard)
export function rendered(t, m) {
  const T = TYPES[t]; if (!decoded.has(m)) decoded.set(m, decode(m));
  const D = decoded.get(m); const pos = D.pos.slice(); const dims = { ...D.head.dims };
  const st = fit.stretchFor(t, m); if (st) applyStretch(pos, D.zone, D.nv, st, dims);
  const s = T.L / dims.L; const y = dims.hasGear ? -dims.low * s : T.Hc;
  let P = m4.mul(m4.translate(T.xMain, y, 0), m4.scale(s, s, s));
  const p = dims.hasGear && T.fit && T.fit.model === m ? T.fit.pitch : null;
  if (p && p.a) P = m4.mul(P, m4.mul(m4.translate(p.x0, p.y0, 0), m4.mul(m4.rotZ(-p.a), m4.translate(-p.x0, -p.y0, 0))));
  const W = new Float32Array(D.nv * 3);
  for (let i = 0; i < D.nv; i++) { const v = m4.xform(P, [pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2]]); W[i * 3] = v[0]; W[i * 3 + 1] = v[1]; W[i * 3 + 2] = v[2]; }
  return { W, D, T };
}
// left-side skin triangles (zones 0 / 5) within the local-x window [x0, x1]
export function skinTris(G, x0, x1) {
  const { W, D } = G; const out = [];
  for (let k = 0; k < D.idx.length; k += 3) {
    const a = D.idx[k], b = D.idx[k + 1], c = D.idx[k + 2];
    const za = D.zone[a], zb = D.zone[b], zc = D.zone[c]; if (!((za === 0 || za === 5) && (zb === 0 || zb === 5) && (zc === 0 || zc === 5))) continue;
    const xa = W[a * 3], xb = W[b * 3], xc = W[c * 3]; if (Math.max(xa, xb, xc) < x0 || Math.min(xa, xb, xc) > x1) continue;
    if (W[a * 3 + 2] >= 0 && W[b * 3 + 2] >= 0 && W[c * 3 + 2] >= 0) continue;
    out.push([[xa, W[a * 3 + 1], W[a * 3 + 2]], [xb, W[b * 3 + 1], W[b * 3 + 2]], [xc, W[c * 3 + 1], W[c * 3 + 2]]]);
  }
  return out;
}
// planar cut x = xc: segments in (y, z)
export function cutAt(tris, xc) {
  const segs = [];
  for (const P of tris) {
    const pts = [];
    for (let e = 0; e < 3; e++) { const p = P[e], q = P[(e + 1) % 3]; const da = p[0] - xc, db = q[0] - xc; if ((da < 0) !== (db < 0)) { const u = da / (da - db); pts.push([p[1] + u * (q[1] - p[1]), p[2] + u * (q[2] - p[2])]); } }
    if (pts.length === 2) segs.push(pts);
  }
  return segs;
}
// outermost left skin (|z|, m) of a cut at height h, ignoring anything beyond lim (wing, engine: not the skin at the door)
export function skinAt(segs, h, lim) {
  let best = null;
  for (const [p, q] of segs) { const da = p[0] - h, db = q[0] - h; if ((da < 0) === (db < 0)) continue; const u = da / (da - db); const z = p[1] + u * (q[1] - p[1]); if (z >= 0 || -z > lim) continue; if (best == null || -z > best) best = -z; }
  return best;
}
// the dock station, cab floor and cab stop of door `which` exactly as js/live/gates.js doorOf takes them
export function dockRef(T, which) {
  if (which === 3) return T.dockX3 != null ? { X: T.dockX3, sill: T.dockSill3, hw: T.dockHW3 } : null;
  if (which === 2) return T.dockX2 != null ? { X: T.dockX2, sill: T.dockSill2 ?? T.dockSill, hw: T.dockHW2 ?? T.dockHW ?? T.R } : null;
  return { X: T.dockX1 ?? T.doors[0], sill: T.dockSill ?? T.sill, hw: T.dockHW ?? T.R };
}
export function measure(G, ref, grid = GRID) {
  const T = G.T; const x0 = T.xMain - ref.X; const tris = skinTris(G, x0 - grid.n * grid.ds - 0.2, x0 + grid.n * grid.ds + 0.2);
  const S = [];
  for (let i = -grid.n; i <= grid.n; i++) {
    const segs = cutAt(tris, x0 - i * grid.ds); const col = [];
    for (let j = 0; j <= grid.m; j++) { const v = skinAt(segs, ref.sill + j * grid.dz, ref.hw + REACH_OUT); col.push(v == null ? null : Math.round(v * 100) / 100); }
    S.push(col);
  }
  return S;
}

export function buildAll(log = () => {}) {
  const types = {};
  for (const t of Object.keys(fit.TYPE_MODEL).sort()) {
    const m = fit.TYPE_MODEL[t]; const T = TYPES[t]; if (!m || !T || !T.fit || T.fit.model !== m) continue;
    const G = rendered(t, m); const e = {};
    for (const which of [1, 2, 3]) {
      const ref = dockRef(T, which); if (!ref || ref.X == null || ref.sill == null || ref.hw == null) continue;
      e[which] = { X: +ref.X.toFixed(3), sill: +ref.sill.toFixed(3), hw: +ref.hw.toFixed(3), S: measure(G, ref) };
    }
    types[t] = e; log(t + ' ' + Object.keys(e).join(','));
  }
  return { ...GRID, types };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  const check = process.argv.includes('--check');
  const out = buildAll(check ? () => {} : (s) => console.log(s));
  const file = path.join(ROOT, 'data/models/dock_foot.js');
  if (!check) {
    const body = JSON.stringify(out).replace(/"types":\{/, '"types":{\n').replace(/\]\]\}\},"/g, ']]}},\n"');
    fs.writeFileSync(file, '// generated by tools/models/dock_foot.mjs (do not edit): the rendered skin over the jet-bridge bellows footprint of\n' +
      '// every docking door, S[i][j] = skin half width (m) at station X + (i - n) * ds (aft +) and height sill + j * dz, null =\n' +
      '// no skin. Read by js/aircraft/dock.js; X / sill / hw = the door it was measured for (js/live/gates.js doorOf).\n' +
      'export const DOCK_FOOT = ' + body + ';\n');
    console.log('wrote', path.relative(ROOT, file), (fs.statSync(file).size / 1024).toFixed(1), 'KB');
  } else {
    const { checkAll } = await import(path.join(ROOT, 'tools/models/dock_check.mjs'));
    console.log(JSON.stringify(await checkAll(out, { rendered, skinTris, cutAt, skinAt })));
  }
}
