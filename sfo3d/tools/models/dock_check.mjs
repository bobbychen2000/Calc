// Check of the jet-bridge bellows closure against the rendered skin (tools/models/dock_foot.mjs --check; rows in
// tools/models/check_dims.py). For every docking door of every type with a model:
//   stale       the committed data/models/dock_foot.js grid differs from a fresh measurement (> 1 cm), or its door has
//               moved (js/aircraft/dock.js then draws the flat bellows)
//   pen         the most the skin stands outside the closure front (m, > 0 = the skin cuts through the bellows), over
//               the whole closure front (every 0.1 m along the fuselage, 0.05 m in height, up to the closure's top)
//   penEdge     the same on the closure's outline (side curtains, top and bottom edge): what can be seen from outside
//   gapEdge     the widest gap between the closure front and the skin on its outline where there is skin (m)
//   flatPen / flatGap  the same two for the old flat front (front at the cab stop hw, full 3.0 m height): before/after
// The skin is measured as dock_foot.mjs measures it (planar cuts of the drawn mesh), on a 4x / 3x finer grid than the
// table the closure is built from, so interpolation between the table's nodes is part of the result.
import path from 'path'; import { fileURLToPath } from 'url';
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const fit = await import(path.join(ROOT, 'js/aircraft/fit.js'));
const { TYPES } = await import(path.join(ROOT, 'js/aircraft/types.js'));
const { DOCK_FOOT } = await import(path.join(ROOT, 'data/models/dock_foot.js'));
const dock = await import(path.join(ROOT, 'js/aircraft/dock.js'));
const { m4 } = await import(path.join(ROOT, 'js/math.js'));

// DF: the measuring functions of tools/models/dock_foot.mjs (passed in: that module imports this one)
export async function checkAll(fresh, DF) {
  const rows = [];
  for (const t of Object.keys(fresh.types)) {
    const T = TYPES[t]; const m = fit.TYPE_MODEL[t]; const G = DF.rendered(t, m);
    for (const w of Object.keys(fresh.types[t])) {
      const which = +w; const ref = dock.dockRef(T, which); const f = fresh.types[t][w]; const c = DOCK_FOOT.types[t] && DOCK_FOOT.types[t][w];
      let stale = !c || Math.abs(c.X - f.X) > 0.005 || Math.abs(c.sill - f.sill) > 0.005 || Math.abs(c.hw - f.hw) > 0.005;
      if (!stale) for (let i = 0; i < f.S.length && !stale; i++) for (let j = 0; j < f.S[i].length; j++) { const a = f.S[i][j], b = c.S[i][j]; if ((a == null) !== (b == null) || (a != null && Math.abs(a - b) > 0.01)) { stale = true; break; } }
      const sh = dock.bellowsShape(T, which, 1);
      const x0 = T.xMain - ref.X; const tris = DF.skinTris(G, x0 - 1.9, x0 + 1.9);
      const B = dock.BELLOWS; const lim = ref.hw + 0.6;
      let pen = -9, penEdge = -9, gapEdge = 0, flatPen = -9, flatGap = 0, at = null, atG = null;
      const topAt = (z) => sh ? sh.topAt(z) : B.y1;
      for (let zi = -16; zi <= 16; zi++) {
        const z = zi * 0.1; const segs = DF.cutAt(tris, x0 - z); const edgeZ = Math.abs(zi) >= 15;   // |z| 1.5-1.6: the side curtains
        for (let yi = 1; yi * 0.05 <= B.y1 + 1e-9; yi++) {
          const y = yi * 0.05; const S = DF.skinAt(segs, ref.sill + y, lim);
          if (S != null) { flatPen = Math.max(flatPen, S - ref.hw); if (edgeZ || yi === 1 || y > B.y1 - 0.051) flatGap = Math.max(flatGap, ref.hw - S); }
          const top = topAt(z); if (!sh || y > top + 1e-9) continue;
          const front = ref.hw - sh.ext(z, y); const edge = edgeZ || yi === 1 || y > top - 0.051;
          if (S == null) { if (edge) { gapEdge = Math.max(gapEdge, 9); atG = [z, y, 'no skin']; } continue; }
          const p = S - front; if (p > pen) { pen = p; at = [z, y]; }
          if (edge) { if (p > penEdge) penEdge = p; if (-p > gapEdge) { gapEdge = -p; atG = [z, y]; } }
        }
      }
      // the DRAWN closure (js/aircraft/dock.js bellowsGeo, cab frame = identity, cab front at x = 0, i.e. hw + 0.6 m from
      // the centre line at kk = 1): every vertex and every edge midpoint against the skin at its own station and height
      let dPen = -9, dGap = 0, nPts = 0;
      if (sh) {
        const pts = []; const geo = { quad: (a, b, c, d) => { const P = [a, b, c, d]; for (let i = 0; i < 4; i++) { pts.push(P[i]); const q = P[(i + 1) % 4]; pts.push([(P[i][0] + q[0]) / 2, (P[i][1] + q[1]) / 2, (P[i][2] + q[2]) / 2]); } } };
        const bell = B.rest + B.ext; dock.bellowsGeo(geo, m4.basis([1, 0, 0], [0, 1, 0], [0, 0, 0]), 0, bell, sh, [0, 0, 0, 1], [0, 0, 0, 0]);
        const cuts = new Map(); const segsAt = (z) => { const k = z.toFixed(4); if (!cuts.has(k)) cuts.set(k, DF.cutAt(tris, x0 - z)); return cuts.get(k); };
        for (const [x, y, z] of pts) {
          const S = DF.skinAt(segsAt(z), ref.sill + y, lim); if (S == null) continue; nPts++;
          const lat = ref.hw + (bell - x); // lateral distance of the point from the centre line
          dPen = Math.max(dPen, S - lat);
          const front = Math.abs(x - (bell + sh.ext(z, y))) < 1e-6; const outline = Math.abs(z) >= B.w - 1e-6 || y <= B.y0 + 1e-6 || y >= sh.topAt(z) - 1e-6;
          if (front && outline) dGap = Math.max(dGap, lat - S);
        }
      }
      rows.push({ drawnPen: sh ? +dPen.toFixed(3) : null, drawnGapEdge: sh ? +dGap.toFixed(3) : null, drawnPts: nPts, t, door: which, stale, top: sh ? +sh.top.toFixed(2) : null, topMin: sh ? +Math.min(...sh.cols.map(sh.topAt)).toFixed(2) : null, hw: ref.hw, pen: sh ? +pen.toFixed(3) : null, penEdge: sh ? +penEdge.toFixed(3) : null, gapEdge: sh ? +gapEdge.toFixed(3) : null,
        at: at && at.map(v => typeof v === 'number' ? +v.toFixed(2) : v), atGap: atG && atG.map(v => typeof v === 'number' ? +v.toFixed(2) : v), flatPen: +flatPen.toFixed(3), flatGap: +flatGap.toFixed(3) });
    }
  }
  return rows;
}
