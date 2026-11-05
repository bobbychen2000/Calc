// Model stretch (js/aircraft/fit.js T.fit.stretch) applied to the vertex positions of an imported model. Pure arithmetic
// (no WebGL), shared by js/live/models.js (renderer) and the node tools (tools/models/dock_foot.mjs, check_dims), so
// the tools measure exactly the geometry that is drawn. Python port: tools/liveries/common.py apply_stretch.
import { plugShift } from './fit.js';

// stretch (js/aircraft/fit.js), all in model units of the unstretched model (x forward, nose = 0, aft negative; y up; z right):
//   cut1, cut2, d1, d2, bl2  fuselage plugs at cut1 / cut2 of length d1 / d2 (negative: section removed, the aft one
//                        blended over bl2), see js/aircraft/fit.js plugShift. The atlas (tools/liveries/atlas.py) splits the
//                        mesh at the stations, so only a 2 cm band of triangles is stretched by a plug.
//   wing {z0, z1, dz, xMin}  span fit: outboard of z0 the wing is stretched spanwise, linearly up to z1, and everything
//                        outboard of z1 (the tip device) moves rigidly by dz (only vertices ahead of xMin: not the tailplane)
//   tipCut {z0, y0, zTo, yTo}  vertices outboard of z0 and above y0 (the model's winglet) folded to (zTo, yTo)
//   tipShear {z0, y0, yt, k, p, xMin}  winglet cant: vertices ahead of xMin, outboard of z0 and above y0 move out by
//                        k (y - y0) ((y - y0) / (yt - y0))^(p - 1): k (yt - y0) at the tip height yt
//   engScale {k, keep}   nacelles scaled radially by k about their axis, the lowest line kept (keep 'low', default) or the
//                        top line (keep 'top': the pylon attachment; 737 MAX LEAP-1B)
//   wingLift {z0, t, xMin} / htLift {z0, t, xMax}  wing / tailplane sheared up by t per unit |z| outboard of z0
//   squash {y0, k}       everything below y0 compressed vertically by k (engine ground clearance fit)
//   gearUp               model units the model's own gear (zone 3) is moved up (oleo compression)
//   noseExt {xMin, yTop, yBot, e}  nose-leg extension (737 MAX stance, js/aircraft/fit.js NOSE_LEG): gear vertices (zone 3)
//                        ahead of xMin and below yTop move down by e (y - yTop) / (yBot - yTop), clamped to [0, e]: the
//                        oleo between yTop and yBot is stretched, the wheels below yBot move rigidly. dims.low (the main
//                        tyres: placement() seats the model on them) is kept
//   fin {yF, xF, k}      fin height fit: vertices aft of xF and above the fuselage top yF (not engines, pylons, gear)
//                        are scaled vertically about yF by k
const ZONE_NOFIN = new Set([2, 3, 7]); // engine, gear, pylon (tools/convert_models.py ZONE)
export function applyStretch(pos, zone, nv, st, dims) {
  const W = st.wing, Fn = st.fin;
  if (st.tipCut) {                    // fold the model's own tip device onto the wing tip (a procedural one replaces it)
    const { z0, y0, zTo, yTo } = st.tipCut;
    for (let i = 0; i < nv; i++) { const z = pos[i * 3 + 2]; if (Math.abs(z) > z0 && pos[i * 3 + 1] > y0) { pos[i * 3 + 1] = yTo; pos[i * 3 + 2] = Math.sign(z) * Math.min(Math.abs(z), zTo); } }
  }
  if (st.engScale && zone) {          // nacelles (zone 2) scaled radially about their own axis, lowest (or top) line kept
    const k = st.engScale.k, top = st.engScale.keep === 'top';
    for (const sg of [-1, 1]) {
      let y0 = 1e9, y1 = -1e9, zs = 0, n = 0;
      for (let i = 0; i < nv; i++) if (zone[i] === 2 && Math.sign(pos[i * 3 + 2]) === sg) { const y = pos[i * 3 + 1]; if (y < y0) y0 = y; if (y > y1) y1 = y; zs += pos[i * 3 + 2]; n++; }
      if (!n) continue; const yc = (y0 + y1) / 2, zc = zs / n, lift = (k - 1) * (yc - (top ? y1 : y0));
      for (let i = 0; i < nv; i++) if (zone[i] === 2 && Math.sign(pos[i * 3 + 2]) === sg) { pos[i * 3 + 1] = yc + (pos[i * 3 + 1] - yc) * k + lift; pos[i * 3 + 2] = zc + (pos[i * 3 + 2] - zc) * k; }
    }
  }
  if (W) {
    const { z0, z1, dz, xMin } = W; const sc = dz / (z1 - z0);
    for (let i = 0; i < nv; i++) {
      if (pos[i * 3] < xMin) continue;
      const z = pos[i * 3 + 2], az = Math.abs(z); if (az <= z0) continue;
      pos[i * 3 + 2] = z + Math.sign(z) * (az >= z1 ? dz : (az - z0) * sc);
    }
    dims.span += 2 * dz;
  }
  if (st.tipShear) {                 // winglet cant (js/aircraft/fit.js WINGLET): outboard of z0 and above y0, |z| grows by k per unit height
    const { z0, y0, yt, k, xMin } = st.tipShear; const e = st.tipShear.p ?? 1;   // e: 2 = the cant grows from 0 at y0 (no kink at the blend)
    for (let i = 0; i < nv; i++) { if (pos[i * 3] < xMin) continue; const z = pos[i * 3 + 2], y = pos[i * 3 + 1]; if (Math.abs(z) > z0 && y > y0) pos[i * 3 + 2] = z + Math.sign(z) * k * (y - y0) * Math.pow((y - y0) / (yt - y0), e - 1); }
    dims.span += 2 * k * (yt - y0);
  }
  if (Fn) {
    const { yF, xF, k } = Fn; let top = -1e9;
    for (let i = 0; i < nv; i++) {
      const y = pos[i * 3 + 1];
      if (pos[i * 3] < xF && y > yF && !(zone && ZONE_NOFIN.has(zone[i]))) pos[i * 3 + 1] = yF + (y - yF) * k;
      if (pos[i * 3 + 1] > top) top = pos[i * 3 + 1];
    }
    dims.H = top;
  }
  if (st.wingLift) {                  // wing dihedral fit: outboard of z0 (fuselage side) the wing, pylons and nacelles rise by t per unit |z|
    const { z0, t, xMin } = st.wingLift;
    for (let i = 0; i < nv; i++) { const az = Math.abs(pos[i * 3 + 2]); if (az > z0 && pos[i * 3] >= xMin && !(zone && (zone[i] === 1 || zone[i] === 3))) pos[i * 3 + 1] += t * (az - z0); }
  }
  if (st.htLift) {                    // tailplane dihedral fit (aft of xMax)
    const { z0, t, xMax } = st.htLift;
    for (let i = 0; i < nv; i++) { const az = Math.abs(pos[i * 3 + 2]); if (az > z0 && pos[i * 3] < xMax && !(zone && zone[i] === 1)) pos[i * 3 + 1] += t * (az - z0); }
  }
  if (st.squash) {                    // vertical compression below the fuselage centre line (js/aircraft/fit.js engine clearance)
    const { y0, k } = st.squash;
    for (let i = 0; i < nv; i++) { const y = pos[i * 3 + 1]; if (y < y0) pos[i * 3 + 1] = y0 + (y - y0) * k; }
    if (dims.low != null) dims.low = y0 + (dims.low - y0) * k;
  }
  if (st.noseExt && zone) {          // nose-leg extension (the nose tyre comes down by e; the main gear and dims.low stay)
    const { xMin, yTop, yBot, e } = st.noseExt;
    for (let i = 0; i < nv; i++) { const y = pos[i * 3 + 1]; if (zone[i] !== 3 || pos[i * 3] <= xMin || y >= yTop) continue; pos[i * 3 + 1] = y - e * Math.min(1, (yTop - y) / (yTop - yBot)); }
  }
  if (st.gearUp) {                    // oleo compression of a model's own gear (js/aircraft/fit.js): the gear moves up
    let low = 1e9;
    for (let i = 0; i < nv; i++) { if (zone && zone[i] === 3) pos[i * 3 + 1] += st.gearUp; if (pos[i * 3 + 1] < low) low = pos[i * 3 + 1]; }
    dims.low = low;
  }
  if (st.cut1 != null) {
    const { cut1, cut2, d1, d2 } = st; const bl2 = st.bl2 || 0;
    for (let i = 0; i < nv; i++) {
      const x = pos[i * 3]; pos[i * 3] = x + plugShift(x, cut1, d1) + plugShift(x, cut2, d2, bl2);
    }
    dims.L += d1 + d2; dims.tailX -= d1 + d2;
  }
}
