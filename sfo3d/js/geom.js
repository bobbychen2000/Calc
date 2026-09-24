// Geometry builder: accumulate triangles with per-vertex attributes (pos, nrm, col(rgba), extra(rough, metal, matID, emissive))
import { v3, m4 } from './math.js';

export class Geo {
  constructor() { this.pos = []; this.nrm = []; this.col = []; this.ext = []; this.idx = []; this.uv = []; }
  get nv() { return this.pos.length / 3; }
  vert(p, n, c, e, uv) {
    this.pos.push(p[0], p[1], p[2]); this.nrm.push(n[0], n[1], n[2]);
    this.col.push(c[0], c[1], c[2], c[3] ?? 1); this.ext.push(e[0] ?? 0.8, e[1] ?? 0, e[2] ?? 0, e[3] ?? 0);
    this.uv.push(uv ? uv[0] : 0, uv ? uv[1] : 0);
    return this.nv - 1;
  }
  tri(a, b, c) { this.idx.push(a, b, c); }
  // flat quad (p0..p3 counter-clockwise when viewed from outside)
  quad(p0, p1, p2, p3, c, e, uvs) {
    const n = v3.norm(v3.cross(v3.sub(p1, p0), v3.sub(p3, p0)));
    const a = this.vert(p0, n, c, e, uvs && uvs[0]), b = this.vert(p1, n, c, e, uvs && uvs[1]), cc = this.vert(p2, n, c, e, uvs && uvs[2]), d = this.vert(p3, n, c, e, uvs && uvs[3]);
    this.idx.push(a, b, cc, a, cc, d);
  }
  // axis-aligned box in local frame then transformed by matrix M (optional)
  box(min, max, c, e, M, faces = 'all') {
    const [x0, y0, z0] = min, [x1, y1, z1] = max;
    const P = (x, y, z) => M ? m4.xform(M, [x, y, z]) : [x, y, z];
    const F = {
      px: [P(x1, y0, z1), P(x1, y0, z0), P(x1, y1, z0), P(x1, y1, z1)],
      nx: [P(x0, y0, z0), P(x0, y0, z1), P(x0, y1, z1), P(x0, y1, z0)],
      py: [P(x0, y1, z1), P(x1, y1, z1), P(x1, y1, z0), P(x0, y1, z0)],
      ny: [P(x0, y0, z0), P(x1, y0, z0), P(x1, y0, z1), P(x0, y0, z1)],
      pz: [P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)],
      nz: [P(x1, y0, z0), P(x0, y0, z0), P(x0, y1, z0), P(x1, y1, z0)],
    };
    for (const k in F) { if (faces !== 'all' && !faces.includes(k)) continue; const q = F[k]; this.quad(q[0], q[1], q[2], q[3], c, e); }
  }
  // extrude a 2D polygon (x,z pairs, CCW seen from above) from y0 to y1; wall material per edge via fn
  extrude(poly, y0, y1, wallC, wallE, roofC, roofE, opts = {}) {
    const n = poly.length;
    for (let i = 0; i < n; i++) {
      const a = poly[i], b = poly[(i + 1) % n];
      const p0 = [a[0], y0, a[1]], p1 = [b[0], y0, b[1]], p2 = [b[0], y1, b[1]], p3 = [a[0], y1, a[1]];
      const wc = typeof wallC === 'function' ? wallC(i) : wallC, we = typeof wallE === 'function' ? wallE(i) : wallE;
      if (opts.smooth) {
        // smooth normals for curved walls
        const na = opts.normals[i], nb = opts.normals[(i + 1) % n];
        const i0 = this.vert(p0, na, wc, we), i1 = this.vert(p1, nb, wc, we), i2 = this.vert(p2, nb, wc, we), i3 = this.vert(p3, na, wc, we);
        this.idx.push(i0, i2, i1, i0, i3, i2);
      } else this.quad(p0, p3, p2, p1, wc, we); // outward facing for CCW (y up): order so normal points out
    }
    if (roofC) this.cap(poly, y1, roofC, roofE, true);
  }
  // triangulate simple polygon (ear clipping) at height y
  cap(poly, y, c, e, up = true) {
    const idx = earcut(poly); const base = this.nv;
    const n = up ? [0, 1, 0] : [0, -1, 0];
    poly.forEach(p => this.vert([p[0], y, p[1]], n, c, e));
    for (let i = 0; i < idx.length; i += 3) { if (up) this.idx.push(base + idx[i], base + idx[i + 2], base + idx[i + 1]); else this.idx.push(base + idx[i], base + idx[i + 1], base + idx[i + 2]); }
  }
  // lathe around y axis: profile [[r,y],...], segments
  lathe(profile, seg, c, e, M, capTop = false) {
    const base = this.nv;
    for (let j = 0; j < profile.length; j++) {
      const [r, y] = profile[j];
      // profile normal
      const pa = profile[Math.max(0, j - 1)], pb = profile[Math.min(profile.length - 1, j + 1)];
      const dr = pb[0] - pa[0], dy = pb[1] - pa[1]; let nr = dy, ny = -dr; const l = Math.hypot(nr, ny) || 1; nr /= l; ny /= l;
      const cj = typeof c === 'function' ? c(j) : c, ej = typeof e === 'function' ? e(j) : e;
      for (let i = 0; i <= seg; i++) {
        const a = i / seg * Math.PI * 2; const ca = Math.cos(a), sa = Math.sin(a);
        let p = [r * ca, y, r * sa]; let nn = [nr * ca, ny, nr * sa];
        if (M) { p = m4.xform(M, p); nn = v3.norm(m4.xdir(M, nn)); }
        this.vert(p, nn, cj, ej, [i / seg, j / (profile.length - 1)]);
      }
    }
    for (let j = 0; j < profile.length - 1; j++) for (let i = 0; i < seg; i++) {
      const a = base + j * (seg + 1) + i, b = a + 1, cc = a + seg + 1, d = cc + 1;
      this.idx.push(a, cc, b, b, cc, d);
    }
    if (capTop) {
      const [r, y] = profile[profile.length - 1]; const ctr = this.vert(M ? m4.xform(M, [0, y, 0]) : [0, y, 0], M ? v3.norm(m4.xdir(M, [0, 1, 0])) : [0, 1, 0], typeof c === 'function' ? c(profile.length - 1) : c, typeof e === 'function' ? e(profile.length - 1) : e);
      const first = this.nv;
      for (let i = 0; i <= seg; i++) { const a = i / seg * Math.PI * 2; let p = [r * Math.cos(a), y, r * Math.sin(a)]; if (M) p = m4.xform(M, p); this.vert(p, M ? v3.norm(m4.xdir(M, [0, 1, 0])) : [0, 1, 0], typeof c === 'function' ? c(profile.length - 1) : c, typeof e === 'function' ? e(profile.length - 1) : e); }
      for (let i = 0; i < seg; i++) this.idx.push(ctr, first + i + 1, first + i);
    }
  }
  cylinder(r, h, seg, c, e, M, caps = true) { this.lathe([[r, 0], [r, h]], seg, c, e, M, caps); }
  merge(g, M) {
    const base = this.nv;
    for (let i = 0; i < g.nv; i++) {
      let p = [g.pos[i * 3], g.pos[i * 3 + 1], g.pos[i * 3 + 2]], n = [g.nrm[i * 3], g.nrm[i * 3 + 1], g.nrm[i * 3 + 2]];
      if (M) { p = m4.xform(M, p); n = v3.norm(m4.xdir(M, n)); }
      this.pos.push(...p); this.nrm.push(...n);
    }
    this.col.push(...g.col); this.ext.push(...g.ext); this.uv.push(...g.uv);
    for (const k of g.idx) this.idx.push(k + base);
  }
  bbox() {
    const b = [1e9, 1e9, 1e9, -1e9, -1e9, -1e9];
    for (let i = 0; i < this.pos.length; i += 3) for (let k = 0; k < 3; k++) { b[k] = Math.min(b[k], this.pos[i + k]); b[k + 3] = Math.max(b[k + 3], this.pos[i + k]); }
    return b;
  }
  data() {
    return { pos: new Float32Array(this.pos), nrm: new Float32Array(this.nrm), col: new Float32Array(this.col), extra: new Float32Array(this.ext), uv: new Float32Array(this.uv), idx: new Uint32Array(this.idx), bbox: this.bbox() };
  }
}

// Minimal ear clipping for simple polygons (array of [x,y])
export function earcut(poly) {
  const n = poly.length; if (n < 3) return [];
  let area = 0; for (let i = 0; i < n; i++) { const a = poly[i], b = poly[(i + 1) % n]; area += a[0] * b[1] - b[0] * a[1]; }
  const V = []; for (let i = 0; i < n; i++) V.push(area > 0 ? i : n - 1 - i);
  const out = []; let guard = 0;
  const inTri = (p, a, b, c) => { const s = (u, v, w) => (u[0] - w[0]) * (v[1] - w[1]) - (v[0] - w[0]) * (u[1] - w[1]); const d1 = s(p, a, b), d2 = s(p, b, c), d3 = s(p, c, a); return !(((d1 < 0) || (d2 < 0) || (d3 < 0)) && ((d1 > 0) || (d2 > 0) || (d3 > 0))); };
  while (V.length > 3 && guard++ < 10000) {
    let found = false;
    for (let i = 0; i < V.length; i++) {
      const i0 = V[(i + V.length - 1) % V.length], i1 = V[i], i2 = V[(i + 1) % V.length];
      const a = poly[i0], b = poly[i1], c = poly[i2];
      const cr = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
      if (cr <= 1e-9) continue;
      let ok = true; for (const j of V) { if (j === i0 || j === i1 || j === i2) continue; if (inTri(poly[j], a, b, c)) { ok = false; break; } }
      if (!ok) continue;
      out.push(i0, i1, i2); V.splice(i, 1); found = true; break;
    }
    if (!found) break;
  }
  if (V.length === 3) out.push(V[0], V[1], V[2]);
  return out;
}
