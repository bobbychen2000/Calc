// ------------------------------------------------------------------
// Geometry primitives + a builder that bakes transforms and
// per-vertex material data (albedo, roughness, metalness, detail layer, emissive)
// ------------------------------------------------------------------
function raw() { return { p: [], n: [], u: [], i: [] }; }

// Box centered at origin
function gBox(w, h, d) {
  const g = raw(), x = w / 2, y = h / 2, z = d / 2;
  const faces = [
    [[1, 0, 0], [0, 0, -1], [0, 1, 0]], [[-1, 0, 0], [0, 0, 1], [0, 1, 0]],
    [[0, 1, 0], [1, 0, 0], [0, 0, -1]], [[0, -1, 0], [1, 0, 0], [0, 0, 1]],
    [[0, 0, 1], [1, 0, 0], [0, 1, 0]], [[0, 0, -1], [-1, 0, 0], [0, 1, 0]],
  ];
  for (const [n, u, v] of faces) {
    const b = g.p.length / 3;
    for (const [su, sv] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) {
      g.p.push((n[0] + u[0] * su + v[0] * sv) * x, (n[1] + u[1] * su + v[1] * sv) * y, (n[2] + u[2] * su + v[2] * sv) * z);
      g.n.push(n[0], n[1], n[2]);
      g.u.push((su + 1) / 2, (sv + 1) / 2);
    }
    g.i.push(b, b + 1, b + 2, b, b + 2, b + 3);
  }
  return g;
}

// Rounded box: clamp-and-project method with tangent-distributed grid (even arcs)
function gRBox(w, h, d, r, seg = 3) {
  const e = [w / 2, h / 2, d / 2];
  r = Math.min(r, e[0] * 0.999, e[1] * 0.999, e[2] * 0.999);
  const inner = e.map((v) => v - r);
  const coords = (ax) => {
    const c = [];
    for (let k = seg; k >= 1; k--) c.push(-inner[ax] - r * Math.tan((k / seg) * Math.PI / 4));
    c.push(-inner[ax], inner[ax]);
    for (let k = 1; k <= seg; k++) c.push(inner[ax] + r * Math.tan((k / seg) * Math.PI / 4));
    return c;
  };
  const g = raw();
  // face: normal axis a, sign s, tangent axes (u,v)
  const faces = [[0, 1, 2, 1], [0, -1, 1, 2], [1, 1, 0, 2], [1, -1, 2, 0], [2, 1, 1, 0], [2, -1, 0, 1]];
  // Choose u,v axes so that cross(u,v)=n (CCW outward)
  const faceAxes = [
    { a: 0, s: 1, u: 2, us: -1, v: 1 }, { a: 0, s: -1, u: 2, us: 1, v: 1 },
    { a: 1, s: 1, u: 0, us: 1, v: 2, vs: -1 }, { a: 1, s: -1, u: 0, us: 1, v: 2, vs: 1 },
    { a: 2, s: 1, u: 0, us: 1, v: 1 }, { a: 2, s: -1, u: 0, us: -1, v: 1 },
  ];
  void faces;
  for (const f of faceAxes) {
    const cu = coords(f.u), cv = coords(f.v);
    const nu = cu.length, nvv = cv.length;
    const base = g.p.length / 3;
    for (let j = 0; j < nvv; j++) {
      for (let i = 0; i < nu; i++) {
        const p = [0, 0, 0];
        p[f.a] = e[f.a] * f.s;
        p[f.u] = cu[i] * (f.us || 1);
        p[f.v] = cv[j] * (f.vs || 1);
        const q = [clamp(p[0], -inner[0], inner[0]), clamp(p[1], -inner[1], inner[1]), clamp(p[2], -inner[2], inner[2])];
        let n = V3.norm(V3.sub(p, q));
        g.p.push(q[0] + n[0] * r, q[1] + n[1] * r, q[2] + n[2] * r);
        g.n.push(n[0], n[1], n[2]);
        g.u.push(i / (nu - 1), j / (nvv - 1));
      }
    }
    for (let j = 0; j < nvv - 1; j++) {
      for (let i = 0; i < nu - 1; i++) {
        const a = base + j * nu + i, b = a + 1, c = a + nu, d = c + 1;
        g.i.push(a, b, d, a, d, c);
      }
    }
  }
  // fix winding: ensure outward-facing triangles
  fixWinding(g);
  return g;
}

// Make each triangle's winding agree with its vertex normals (CCW when seen from normal side)
function fixWinding(g) {
  const P = g.p, N = g.n, I = g.i;
  for (let t = 0; t < I.length; t += 3) {
    const a = I[t], b = I[t + 1], c = I[t + 2];
    const ab = [P[b * 3] - P[a * 3], P[b * 3 + 1] - P[a * 3 + 1], P[b * 3 + 2] - P[a * 3 + 2]];
    const ac = [P[c * 3] - P[a * 3], P[c * 3 + 1] - P[a * 3 + 1], P[c * 3 + 2] - P[a * 3 + 2]];
    const fn = V3.cross(ab, ac);
    const vn = [N[a * 3] + N[b * 3] + N[c * 3], N[a * 3 + 1] + N[b * 3 + 1] + N[c * 3 + 1], N[a * 3 + 2] + N[b * 3 + 2] + N[c * 3 + 2]];
    if (V3.dot(fn, vn) < 0) { I[t + 1] = c; I[t + 2] = b; }
  }
  return g;
}

// Cylinder along Y centered on origin
function gCyl(rt, rb, h, seg = 16, caps = true, phi0 = 0, phiLen = Math.PI * 2) {
  const g = raw();
  const full = phiLen >= Math.PI * 2 - 1e-6;
  const slope = (rb - rt) / h;
  for (let s = 0; s <= seg; s++) {
    const a = phi0 + (s / seg) * phiLen, ca = Math.cos(a), sa = Math.sin(a);
    const n = V3.norm([ca, slope, sa]);
    g.p.push(ca * rt, h / 2, sa * rt); g.n.push(n[0], n[1], n[2]); g.u.push(s / seg, 1);
    g.p.push(ca * rb, -h / 2, sa * rb); g.n.push(n[0], n[1], n[2]); g.u.push(s / seg, 0);
  }
  for (let s = 0; s < seg; s++) {
    const a = s * 2, b = a + 1, c = a + 2, d = a + 3;
    g.i.push(a, c, b, b, c, d);
  }
  if (caps) {
    for (const [y, r, ny] of [[h / 2, rt, 1], [-h / 2, rb, -1]]) {
      if (r <= 0) continue;
      const c0 = g.p.length / 3;
      g.p.push(0, y, 0); g.n.push(0, ny, 0); g.u.push(0.5, 0.5);
      for (let s = 0; s <= seg; s++) {
        const a = phi0 + (s / seg) * phiLen;
        g.p.push(Math.cos(a) * r, y, Math.sin(a) * r); g.n.push(0, ny, 0); g.u.push(0.5 + Math.cos(a) / 2, 0.5 + Math.sin(a) / 2);
      }
      for (let s = 0; s < seg; s++) g.i.push(c0, c0 + 1 + s, c0 + 2 + s);
    }
  }
  void full;
  return fixWinding(g);
}

function gSphere(r, ws = 16, hs = 10) {
  const g = raw();
  for (let j = 0; j <= hs; j++) {
    const v = j / hs, th = v * Math.PI;
    for (let i = 0; i <= ws; i++) {
      const u = i / ws, ph = u * Math.PI * 2;
      const n = [Math.sin(th) * Math.cos(ph), Math.cos(th), Math.sin(th) * Math.sin(ph)];
      g.p.push(n[0] * r, n[1] * r, n[2] * r); g.n.push(...n); g.u.push(u, v);
    }
  }
  for (let j = 0; j < hs; j++) for (let i = 0; i < ws; i++) {
    const a = j * (ws + 1) + i, b = a + 1, c = a + ws + 1, d = c + 1;
    g.i.push(a, c, b, b, c, d);
  }
  return fixWinding(g);
}

// Lathe around Y: pts = [[r, y], ...]
function gLathe(pts, seg = 24, phi0 = 0, phiLen = Math.PI * 2) {
  const g = raw();
  const np = pts.length;
  // profile normals (2D) from neighbors
  const pn = pts.map((p, k) => {
    const a = pts[Math.max(0, k - 1)], b = pts[Math.min(np - 1, k + 1)];
    const dr = b[0] - a[0], dy = b[1] - a[1];
    const l = Math.hypot(dr, dy) || 1;
    return [dy / l, -dr / l];
  });
  for (let s = 0; s <= seg; s++) {
    const a = phi0 + (s / seg) * phiLen, ca = Math.cos(a), sa = Math.sin(a);
    for (let k = 0; k < np; k++) {
      const [r, y] = pts[k], [nr, ny] = pn[k];
      g.p.push(ca * r, y, sa * r); g.n.push(ca * nr, ny, sa * nr); g.u.push(s / seg, k / (np - 1));
    }
  }
  for (let s = 0; s < seg; s++) for (let k = 0; k < np - 1; k++) {
    const a = s * np + k, b = a + 1, c = a + np, d = c + 1;
    g.i.push(a, b, c, b, d, c);
  }
  return fixWinding(g);
}

// Ear-clipping triangulation for simple polygons [[x,y],...]
function triangulate(poly) {
  const n = poly.length;
  if (n < 3) return [];
  let area = 0;
  for (let i = 0; i < n; i++) { const a = poly[i], b = poly[(i + 1) % n]; area += a[0] * b[1] - b[0] * a[1]; }
  const idx = [];
  for (let i = 0; i < n; i++) idx.push(i);
  if (area < 0) idx.reverse();
  const out = [];
  const isEar = (i0, i1, i2) => {
    const a = poly[i0], b = poly[i1], c = poly[i2];
    const cr = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
    if (cr <= 1e-12) return false;
    for (const k of idx) {
      if (k === i0 || k === i1 || k === i2) continue;
      const p = poly[k];
      const d1 = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]);
      const d2 = (c[0] - b[0]) * (p[1] - b[1]) - (c[1] - b[1]) * (p[0] - b[0]);
      const d3 = (a[0] - c[0]) * (p[1] - c[1]) - (a[1] - c[1]) * (p[0] - c[0]);
      if (d1 >= 0 && d2 >= 0 && d3 >= 0) return false;
    }
    return true;
  };
  let guard = 0;
  while (idx.length > 3 && guard++ < 5000) {
    let found = false;
    for (let k = 0; k < idx.length; k++) {
      const i0 = idx[(k + idx.length - 1) % idx.length], i1 = idx[k], i2 = idx[(k + 1) % idx.length];
      if (isEar(i0, i1, i2)) { out.push(i0, i1, i2); idx.splice(k, 1); found = true; break; }
    }
    if (!found) break;
  }
  if (idx.length === 3) out.push(idx[0], idx[1], idx[2]);
  return out;
}

// Extrude a 2D polygon (x,y) along z by depth (centered). Sides smooth if angle < smoothDeg.
function gExtrude(shape, depth, smoothDeg = 30) {
  const g = raw();
  const n = shape.length, z0 = -depth / 2, z1 = depth / 2;
  let area = 0;
  for (let i = 0; i < n; i++) { const a = shape[i], b = shape[(i + 1) % n]; area += a[0] * b[1] - b[0] * a[1]; }
  const ccw = area > 0;
  const tri = triangulate(shape);
  // caps
  for (const [z, nz] of [[z1, 1], [z0, -1]]) {
    const b = g.p.length / 3;
    for (const [x, y] of shape) { g.p.push(x, y, z); g.n.push(0, 0, nz); g.u.push(x, y); }
    for (let t = 0; t < tri.length; t += 3) g.i.push(b + tri[t], b + tri[t + 1], b + tri[t + 2]);
  }
  // side edge normals
  const en = [];
  for (let i = 0; i < n; i++) {
    const a = shape[i], b = shape[(i + 1) % n];
    const dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy) || 1;
    en.push(ccw ? [dy / l, -dx / l] : [-dy / l, dx / l]);
  }
  const cosT = Math.cos(smoothDeg * DEG);
  let acc = 0;
  for (let i = 0; i < n; i++) {
    const a = shape[i], b = shape[(i + 1) % n];
    const nPrev = en[(i + n - 1) % n], nCur = en[i], nNext = en[(i + 1) % n];
    const sa = nPrev[0] * nCur[0] + nPrev[1] * nCur[1] > cosT;
    const sb = nNext[0] * nCur[0] + nNext[1] * nCur[1] > cosT;
    const na = sa ? V3.norm([nPrev[0] + nCur[0], nPrev[1] + nCur[1], 0]) : [nCur[0], nCur[1], 0];
    const nb = sb ? V3.norm([nNext[0] + nCur[0], nNext[1] + nCur[1], 0]) : [nCur[0], nCur[1], 0];
    const l = Math.hypot(b[0] - a[0], b[1] - a[1]);
    const base = g.p.length / 3;
    g.p.push(a[0], a[1], z1, b[0], b[1], z1, b[0], b[1], z0, a[0], a[1], z0);
    g.n.push(...na, ...nb, ...nb, ...na);
    g.u.push(acc, z1, acc + l, z1, acc + l, z0, acc, z0);
    acc += l;
    g.i.push(base, base + 1, base + 2, base, base + 2, base + 3);
  }
  return fixWinding(g);
}

// Sweep an open 2D profile [[x,y],...] along z from z0 to z1 (segments along z = zs).
// normalSide: +1 uses left-hand normal of the polyline direction, -1 the other.
function gSweep(profile, z0, z1, opts = {}) {
  const g = raw();
  const np = profile.length;
  const zs = opts.zsteps || 1;
  const side = opts.side || 1;
  const crease = opts.crease || [];
  // per-vertex normals (smooth unless crease index)
  const segN = [];
  for (let k = 0; k < np - 1; k++) {
    const a = profile[k], b = profile[k + 1];
    const dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy) || 1;
    segN.push([(-dy / l) * side, (dx / l) * side]);
  }
  const verts = []; // [x,y,nx,ny,s]
  let s = 0;
  for (let k = 0; k < np; k++) {
    if (k > 0) s += Math.hypot(profile[k][0] - profile[k - 1][0], profile[k][1] - profile[k - 1][1]);
    const nA = segN[Math.max(0, k - 1)], nB = segN[Math.min(np - 2, k)];
    if (crease.includes(k) && k > 0 && k < np - 1) {
      verts.push([profile[k][0], profile[k][1], nA[0], nA[1], s, 'end']);
      verts.push([profile[k][0], profile[k][1], nB[0], nB[1], s, 'start']);
    } else {
      const nn = V3.norm([nA[0] + nB[0], nA[1] + nB[1], 0]);
      verts.push([profile[k][0], profile[k][1], nn[0], nn[1], s, '']);
    }
  }
  const nvr = verts.length;
  const us = opts.uscale || 1;
  for (let j = 0; j <= zs; j++) {
    const z = z0 + (z1 - z0) * (j / zs);
    for (const v of verts) { g.p.push(v[0], v[1], z); g.n.push(v[2], v[3], 0); g.u.push(v[4] * us, z * us); }
  }
  for (let j = 0; j < zs; j++) {
    for (let k = 0; k < nvr - 1; k++) {
      if (verts[k][5] === 'end') continue; // crease split
      const a = j * nvr + k, b = a + 1, c = a + nvr, d = c + 1;
      g.i.push(a, b, d, a, d, c);
    }
  }
  return fixWinding(g);
}

// Tube along a 3D polyline
function gTube(path, r, seg = 8, capped = true) {
  const g = raw();
  const np = path.length;
  let prevN = null;
  for (let k = 0; k < np; k++) {
    const a = path[Math.max(0, k - 1)], b = path[Math.min(np - 1, k + 1)];
    const t = V3.norm(V3.sub(b, a));
    let nref = prevN || (Math.abs(t[1]) < 0.9 ? [0, 1, 0] : [1, 0, 0]);
    let bn = V3.norm(V3.cross(t, nref));
    let nn = V3.cross(bn, t);
    prevN = nn;
    for (let s = 0; s <= seg; s++) {
      const ang = (s / seg) * Math.PI * 2;
      const d = V3.add(V3.scale(nn, Math.cos(ang)), V3.scale(bn, Math.sin(ang)));
      g.p.push(path[k][0] + d[0] * r, path[k][1] + d[1] * r, path[k][2] + d[2] * r);
      g.n.push(d[0], d[1], d[2]); g.u.push(s / seg, k / (np - 1));
    }
  }
  for (let k = 0; k < np - 1; k++) for (let s = 0; s < seg; s++) {
    const a = k * (seg + 1) + s, b = a + 1, c = a + seg + 1, d = c + 1;
    g.i.push(a, c, b, b, c, d);
  }
  if (capped) {
    for (const k of [0, np - 1]) {
      const a = path[Math.max(0, k - 1)], b = path[Math.min(np - 1, k + 1)];
      const t = V3.scale(V3.norm(V3.sub(b, a)), k === 0 ? -1 : 1);
      const c0 = g.p.length / 3;
      g.p.push(...path[k]); g.n.push(...t); g.u.push(0.5, 0.5);
      const ring = k * (seg + 1);
      for (let s = 0; s <= seg; s++) {
        g.p.push(g.p[(ring + s) * 3], g.p[(ring + s) * 3 + 1], g.p[(ring + s) * 3 + 2]);
        g.n.push(...t); g.u.push(0, 0);
      }
      for (let s = 0; s < seg; s++) g.i.push(c0, c0 + 1 + s, c0 + 2 + s);
    }
  }
  return fixWinding(g);
}

// Quad in XY plane facing +Z
function gQuad(w, h) {
  const g = raw();
  g.p.push(-w / 2, -h / 2, 0, w / 2, -h / 2, 0, w / 2, h / 2, 0, -w / 2, h / 2, 0);
  g.n.push(0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1);
  g.u.push(0, 0, 1, 0, 1, 1, 0, 1);
  g.i.push(0, 1, 2, 0, 2, 3);
  return g;
}

// Rounded-rectangle outline points (CCW), w x h, corner radius r
function rrectPts(w, h, r, segC = 6, cx = 0, cy = 0) {
  r = Math.min(r, w / 2, h / 2);
  const pts = [];
  const cs = [[w / 2 - r, h / 2 - r, 0], [-w / 2 + r, h / 2 - r, 90], [-w / 2 + r, -h / 2 + r, 180], [w / 2 - r, -h / 2 + r, 270]];
  for (const [x, y, a0] of cs) {
    for (let k = 0; k <= segC; k++) {
      const a = (a0 + (k / segC) * 90) * DEG;
      pts.push([cx + x + Math.cos(a) * r, cy + y + Math.sin(a) * r]);
    }
  }
  return pts;
}


// Smooth vertex normals from faces
function computeNormals(g) {
  const n = new Float32Array(g.p.length);
  for (let t = 0; t < g.i.length; t += 3) {
    const a = g.i[t] * 3, b = g.i[t + 1] * 3, c = g.i[t + 2] * 3;
    const abx = g.p[b] - g.p[a], aby = g.p[b + 1] - g.p[a + 1], abz = g.p[b + 2] - g.p[a + 2];
    const acx = g.p[c] - g.p[a], acy = g.p[c + 1] - g.p[a + 1], acz = g.p[c + 2] - g.p[a + 2];
    const fx = aby * acz - abz * acy, fy = abz * acx - abx * acz, fz = abx * acy - aby * acx;
    for (const v of [a, b, c]) { n[v] += fx; n[v + 1] += fy; n[v + 2] += fz; }
  }
  for (let k = 0; k < n.length; k += 3) {
    const l = Math.hypot(n[k], n[k + 1], n[k + 2]) || 1;
    g.n[k] = n[k] / l; g.n[k + 1] = n[k + 1] / l; g.n[k + 2] = n[k + 2] / l;
  }
  return g;
}

// Loft through rounded-rectangle sections stacked along y.
// sec: {y, x, z, w (x size), d (z size), r (corner radius)}; optional rot (tilt about x, radians)
function gLoft(secs, segC = 4, caps = [true, true]) {
  const g = raw();
  const rings = secs.map((s) => rrectPts(s.w, s.d, Math.max(0.0005, Math.min(s.r, s.w / 2 - 1e-4, s.d / 2 - 1e-4)), segC, s.x || 0, s.z || 0));
  const n = rings[0].length;
  for (let j = 0; j < secs.length; j++) for (let i = 0; i < n; i++) {
    g.p.push(rings[j][i][0], secs[j].y, rings[j][i][1]); g.n.push(0, 1, 0); g.u.push(i / n, j / (secs.length - 1));
  }
  for (let j = 0; j < secs.length - 1; j++) for (let i = 0; i < n; i++) {
    const a = j * n + i, b = j * n + ((i + 1) % n), c = a + n, d = b + n;
    g.i.push(a, b, d, a, d, c);
  }
  computeNormals(g);
  // make side normals point outward
  let dot = 0;
  for (let i = 0; i < n; i++) { const k = i * 3; dot += g.n[k] * (g.p[k] - (secs[0].x || 0)) + g.n[k + 2] * (g.p[k + 2] - (secs[0].z || 0)); }
  if (dot < 0) {
    for (let k = 0; k < g.n.length; k++) g.n[k] = -g.n[k];
    for (let t = 0; t < g.i.length; t += 3) { const tmp = g.i[t + 1]; g.i[t + 1] = g.i[t + 2]; g.i[t + 2] = tmp; }
  }
  for (const [j, ny] of [[0, -1], [secs.length - 1, 1]]) {
    if (!caps[j === 0 ? 0 : 1]) continue;
    const s = secs[j], c0 = g.p.length / 3;
    g.p.push(s.x || 0, s.y, s.z || 0); g.n.push(0, ny, 0); g.u.push(0.5, 0.5);
    for (const [x, z] of rings[j]) { g.p.push(x, s.y, z); g.n.push(0, ny, 0); g.u.push(0, 0); }
    for (let i = 0; i < n; i++) {
      const a = c0 + 1 + i, b = c0 + 1 + ((i + 1) % n);
      if (ny > 0) g.i.push(c0, b, a); else g.i.push(c0, a, b);
    }
  }
  return fixCaps(g);
}
function fixCaps(g) { return fixWinding(g); }

// Soft cushion: rounded block with a pillowed top edge (quarter-round of radius e) and slight crown
function cushionSecs(w, d, h, y0, opts = {}) {
  const e = opts.edge ?? Math.min(0.04, h * 0.45);
  const r = opts.r ?? 0.03;
  const crown = opts.crown ?? 0.008;
  const x = opts.x || 0, z = opts.z || 0;
  const secs = [{ y: y0, x, z, w: w - 0.02, d: d - 0.02, r }, { y: y0 + 0.01, x, z, w, d, r }];
  const N = 5;
  for (let k = 0; k <= N; k++) {
    const th = (k / N) * Math.PI / 2;
    const inset = e * (1 - Math.cos(th));
    secs.push({ y: y0 + h - e + e * Math.sin(th) + (k === N ? crown : crown * Math.sin(th) * 0.6), x, z, w: w - 2 * inset, d: d - 2 * inset, r: r + inset * 0.6 });
  }
  return secs;
}

// Material presets are plain objects: {c:'#rrggbb', r:rough, m:metal, l:layer, e:emissive, a:alpha-ish unused}
class Builder {
  constructor() { this.p = []; this.n = []; this.u = []; this.c = []; this.m = []; this.i = []; }
  add(g, xf, mat, uvOverride) {
    const base = this.p.length / 3;
    const col = hexRGB(mat.c || '#ffffff');
    const r = Math.round(clamp(mat.r ?? 0.6, 0.02, 1) * 255), me = Math.round(clamp(mat.m ?? 0, 0, 1) * 255);
    const l = mat.l || 0, e = Math.round(clamp(mat.e || 0, 0, 1) * 255);
    const nv = g.p.length / 3;
    for (let k = 0; k < nv; k++) {
      let p = [g.p[k * 3], g.p[k * 3 + 1], g.p[k * 3 + 2]];
      let n = [g.n[k * 3], g.n[k * 3 + 1], g.n[k * 3 + 2]];
      if (xf) { p = M4.point(xf, p); n = V3.norm(M4.dir(xf, n)); }
      this.p.push(p[0], p[1], p[2]);
      this.n.push(n[0], n[1], n[2]);
      if (uvOverride) this.u.push(...uvOverride(k, g)); else this.u.push(g.u[k * 2] || 0, g.u[k * 2 + 1] || 0);
      let cc = col;
      if (mat.vary) { const f = 1 + (Math.sin(p[0] * 13.1 + p[1] * 7.7 + p[2] * 5.3) * 0.5) * mat.vary; cc = col.map((v) => clamp(Math.round(v * f), 0, 255)); }
      this.c.push(cc[0], cc[1], cc[2], 255);
      this.m.push(r, me, l, mat.eFn ? Math.round(clamp(mat.eFn(p), 0, 1) * 255) : e);
    }
    // If transform mirrors, flip winding
    let flip = false;
    if (xf) {
      const det = xf[0] * (xf[5] * xf[10] - xf[9] * xf[6]) - xf[4] * (xf[1] * xf[10] - xf[9] * xf[2]) + xf[8] * (xf[1] * xf[6] - xf[5] * xf[2]);
      flip = det < 0;
    }
    for (let t = 0; t < g.i.length; t += 3) {
      if (flip) this.i.push(base + g.i[t], base + g.i[t + 2], base + g.i[t + 1]);
      else this.i.push(base + g.i[t], base + g.i[t + 1], base + g.i[t + 2]);
    }
    return this;
  }
  // append an already-built geometry (keeps its per-vertex colours/materials)
  addBuilt(geo, xf) {
    const base = this.p.length / 3, nv = geo.pos.length / 3;
    for (let k = 0; k < nv; k++) {
      let p = [geo.pos[k * 3], geo.pos[k * 3 + 1], geo.pos[k * 3 + 2]], n = [geo.nrm[k * 3], geo.nrm[k * 3 + 1], geo.nrm[k * 3 + 2]];
      if (xf) { p = M4.point(xf, p); n = V3.norm(M4.dir(xf, n)); }
      this.p.push(...p); this.n.push(...n); this.u.push(geo.uv[k * 2], geo.uv[k * 2 + 1]);
      for (let c = 0; c < 4; c++) { this.c.push(geo.col[k * 4 + c]); this.m.push(geo.mat[k * 4 + c]); }
    }
    let flip = false;
    if (xf) flip = (xf[0] * (xf[5] * xf[10] - xf[9] * xf[6]) - xf[4] * (xf[1] * xf[10] - xf[9] * xf[2]) + xf[8] * (xf[1] * xf[6] - xf[5] * xf[2])) < 0;
    for (let t = 0; t < geo.idx.length; t += 3) {
      if (flip) this.i.push(base + geo.idx[t], base + geo.idx[t + 2], base + geo.idx[t + 1]);
      else this.i.push(base + geo.idx[t], base + geo.idx[t + 1], base + geo.idx[t + 2]);
    }
    return this;
  }
  get vcount() { return this.p.length / 3; }
  build() {
    const pos = new Float32Array(this.p);
    const mn = [1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9];
    for (let k = 0; k < pos.length; k += 3) for (let a = 0; a < 3; a++) { mn[a] = Math.min(mn[a], pos[k + a]); mx[a] = Math.max(mx[a], pos[k + a]); }
    return {
      pos, nrm: new Float32Array(this.n), uv: new Float32Array(this.u),
      col: new Uint8Array(this.c), mat: new Uint8Array(this.m), idx: this.i, bounds: [mn, mx],
    };
  }
}
