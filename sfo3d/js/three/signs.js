// Airfield, stand and jet-bridge signs rendered with the offline MSDF glyph atlas (tools/build3/msdf_atlas.py ->
// js/three/assets/msdf_signs.{png,json}).
// Where signs are and what they say is decided by the existing modules, unchanged: js/live/signs.js buildSigns (hold
// position, location, painted holding position and distance-remaining signs) and js/live/gates.js LiveGateSystem
// (stand ID, VDGS and bridge gate numbers). Those modules emit quads that point into a Canvas2D bitmap atlas; each
// quad's UV rectangle identifies its face (kind + text) in the atlas map, and here the face is rebuilt as a background
// panel (colour, border) plus MSDF glyph quads, so the text is sharp at any distance.
// Face styles follow js/live/signs.js makeAtlas: mand/paint red #b3120f, gate #10151c, others #0b0b0b; loc text and
// border #f4c21b, VDGS text #ffb020 (monospace), others #f2f2f2; 70 px text on 96 px faces, 150 px on 190 px paint faces.
import { THREE, TSL } from './lib.js';
import { makeAtlas } from '../live/signs.js';
const { Fn, attribute, vec2, vec3, vec4, float, texture, max, min, mix, smoothstep, clamp, fwidth, abs, length, select, step, uniform } = TSL;

const hex = (h) => { const c = new THREE.Color(h); return [c.r, c.g, c.b]; }; // THREE.Color(hex) converts sRGB -> linear
const STYLE = {
  mand: { bg: hex('#b3120f'), fg: hex('#f2f2f2'), font: 'sans', px: 70, h: 96 },
  paint: { bg: hex('#b3120f'), fg: hex('#f2f2f2'), font: 'sans', px: 150, h: 190, border: [0, 10], bc: hex('#e8b51c') },
  loc: { bg: hex('#0b0b0b'), fg: hex('#f4c21b'), font: 'sans', px: 70, h: 96, border: [4, 10], bc: hex('#f4c21b') },
  drs: { bg: hex('#0b0b0b'), fg: hex('#f2f2f2'), font: 'sans', px: 70, h: 96 },
  gate: { bg: hex('#10151c'), fg: hex('#f2f2f2'), font: 'sans', px: 70, h: 96 },
  vdgs: { bg: hex('#0b0b0b'), fg: hex('#ffb020'), font: 'mono', px: 70, h: 96 },
};

export async function loadSignFont() {
  const base = new URL('./assets/', import.meta.url);
  const meta = await (await fetch(new URL('msdf_signs.json', base))).json();
  const tex = await new THREE.TextureLoader().loadAsync(new URL('msdf_signs.png', base).href);
  tex.flipY = false; tex.colorSpace = THREE.NoColorSpace; tex.generateMipmaps = true; tex.minFilter = THREE.LinearMipmapLinearFilter; tex.magFilter = THREE.LinearFilter; tex.anisotropy = 8; tex.needsUpdate = true;
  return { meta, tex };
}

// rect -> face lookup for an atlas map {key: {u0, v0, u1, v1, aspect}} (makeAtlas output)
export function faceIndex(map) {
  const list = Object.entries(map).map(([key, r]) => { const i = key.indexOf(':'); return { key, kind: key.slice(0, i), text: key.slice(i + 1), r }; });
  return (u0, v0) => { let best = null, bd = 1e9; for (const f of list) { const d = Math.abs(f.r.u0 - u0) + Math.abs(f.r.v0 - v0); if (d < bd) { bd = d; best = f; } } return bd < 1e-4 ? best : null; };
}
// the face list of js/live/signs.js buildSigns (same kinds, texts and order -> identical atlas layout)
// locName replicates js/live/signs.js locName (not exported, signs.js line ~146 as of 24 Sep 2026)
function locName(t) { if (!t || /INTERSECTION/i.test(t)) return null; const s = t.split('/')[0].trim(); return s.length <= 3 ? s : null; }
export function worldSignAtlasMap(details) {
  const faces = new Map(); const add = (kind, text) => { const key = kind + ':' + text; if (!faces.has(key)) faces.set(key, { key, kind, text }); };
  for (const h of details.holds || []) { add('mand', h.text); add('paint', h.text); const loc = locName(h.twy); if (loc) add('loc', loc); }
  for (let k = 1; k <= 12; k++) add('drs', String(k));
  return makeAtlas([...faces.values()]).map;
}

// Accumulates panel backgrounds (opaque) and glyphs (transparent) from sign quads
export class SignBuilder {
  constructor(font) { this.font = font; this.bg = { pos: [], nrm: [], col: [], fuv: [], fdim: [], bcol: [], idx: [] }; this.gl = { pos: [], nrm: [], uv: [], col: [], idx: [] }; this.dark = { pos: [], nrm: [], idx: [] }; }
  // quad: 4 corner positions + their atlas uvs, normal, kind flag (0 housing, 1 lit face, 2 painted), face (from faceIndex) or null
  addQuad(P, UV, n, flag, face) {
    if (flag < 0.5 || !face) { const b = this.dark.pos.length / 3; for (const p of P) { this.dark.pos.push(p[0], p[1], p[2]); this.dark.nrm.push(n[0], n[1], n[2]); } this.dark.idx.push(b, b + 1, b + 2, b, b + 2, b + 3); return; }
    const st = STYLE[face.kind] || STYLE.drs; const r = face.r;
    // corners by uv: top-left (u0,v0), top-right (u1,v0), bottom-left (u0,v1)
    const near = (u, v) => { let bi = 0, bd = 1e9; for (let i = 0; i < 4; i++) { const d = Math.abs(UV[i][0] - u) + Math.abs(UV[i][1] - v); if (d < bd) { bd = d; bi = i; } } return P[bi]; };
    const TL = near(r.u0, r.v0), TR = near(r.u1, r.v0), BL = near(r.u0, r.v1);
    const W = st.h * r.aspect, H = st.h; // face size in atlas px (makeAtlas: w = aspect * h)
    const lit = flag < 1.5 ? 1 : 0, painted = flag > 1.5 ? 1 : 0;
    const at = (x, y, lift) => [TL[0] + (TR[0] - TL[0]) * x / W + (BL[0] - TL[0]) * y / H + n[0] * lift, TL[1] + (TR[1] - TL[1]) * x / W + (BL[1] - TL[1]) * y / H + n[1] * lift, TL[2] + (TR[2] - TL[2]) * x / W + (BL[2] - TL[2]) * y / H + n[2] * lift];
    // background panel
    { const B = this.bg; const b = B.pos.length / 3; const corners = [[0, H], [W, H], [W, 0], [0, 0]];
      for (const [x, y] of corners) { const p = at(x, y, 0); B.pos.push(...p); B.nrm.push(...n); B.col.push(...st.bg, lit); B.fuv.push(x, y); B.fdim.push(W, H, st.border ? st.border[0] : -1, st.border ? st.border[1] : -1); B.bcol.push(...(st.bc || [0, 0, 0])); }
      B.idx.push(b, b + 1, b + 2, b, b + 2, b + 3); }
    // glyphs: centred at (W/2, H/2 + 3) like makeAtlas fillText with textBaseline 'middle'; condensed to fit W - 44
    const F = this.font.meta.fonts[st.font]; const px = st.px; const text = face.text;
    const glyphOf = (ch) => F.glyphs[ch] || (ch === ' ' ? { advance: st.font === 'mono' ? 0.6 : 0.278 } : F.glyphs['?']); // space: advance only (Liberation metrics)
    let adv = 0; for (const ch of text) adv += glyphOf(ch).advance;
    const natural = adv * px, avail = Math.max(1, W - (face.kind === 'paint' ? 60 : 44));
    const sx = natural > avail ? avail / natural : 1;
    let x = W / 2 - natural * sx / 2; const base = H / 2 + 3 + F.capHeight * px / 2;
    const A = this.font.meta.atlas; const G = this.gl; const lift = painted ? 0.004 : 0.006;
    for (const ch of text) {
      const g = glyphOf(ch);
      if (g.atlas) {
        const [l, bo, rr, t] = g.plane; const [ax, ay, aw, ah] = g.atlas;
        const x0 = x + l * px * sx, x1 = x + rr * px * sx, y0 = base - t * px, y1 = base - bo * px;
        const b = G.pos.length / 3;
        for (const [xx, yy, uu, vv] of [[x0, y1, ax, ay + ah], [x1, y1, ax + aw, ay + ah], [x1, y0, ax + aw, ay], [x0, y0, ax, ay]]) { G.pos.push(...at(xx, yy, lift)); G.nrm.push(...n); G.uv.push(uu / A.width, vv / A.height); G.col.push(...st.fg, lit); }
        G.idx.push(b, b + 1, b + 2, b, b + 2, b + 3);
      }
      x += g.advance * px * sx;
    }
  }
  // sign geometry arrays {pos, nrm, uv, ext, idx} (signs.js G / gates.js signQuad layout: 4 vertices per quad)
  addSignArrays(S, lookup) {
    const nq = S.pos.length / 12;
    for (let q = 0; q < nq; q++) {
      const P = [], UV = []; for (let i = 0; i < 4; i++) { const v = q * 4 + i; P.push([S.pos[v * 3], S.pos[v * 3 + 1], S.pos[v * 3 + 2]]); UV.push([S.uv[v * 2], S.uv[v * 2 + 1]]); }
      const v0 = q * 4; const n = [S.nrm[v0 * 3], S.nrm[v0 * 3 + 1], S.nrm[v0 * 3 + 2]]; const flag = S.ext[v0 * 4];
      let face = null;
      if (flag > 0.5) { let u0 = 1e9, vv0 = 1e9; for (const [u, v] of UV) { u0 = Math.min(u0, u); vv0 = Math.min(vv0, v); } face = lookup(u0, vv0); }
      this.addQuad(P, UV, n, flag, face);
    }
  }
  geometries() {
    const mk = (A, attrs) => { if (!A.idx.length) return null; const g = new THREE.BufferGeometry(); for (const [name, arr, size] of attrs) g.setAttribute(name, new THREE.BufferAttribute(new Float32Array(arr), size)); g.setIndex(A.idx); g.computeBoundingSphere(); return g; };
    const B = this.bg;
    return {
      bg: mk(B, [['position', B.pos, 3], ['normal', B.nrm, 3], ['color', B.col, 4], ['fuv', B.fuv, 2], ['fdim', B.fdim, 4], ['bcol', B.bcol, 3]]),
      glyphs: mk(this.gl, [['position', this.gl.pos, 3], ['normal', this.gl.nrm, 3], ['uv', this.gl.uv, 2], ['color', this.gl.col, 4]]),
      dark: mk(this.dark, [['position', this.dark.pos, 3], ['normal', this.dark.nrm, 3]]),
    };
  }
}

// materials (shared): lit faces glow at night (signs.js SIGN_FS: emis = albedo * uNight * 1.6)
export function signMaterials(font, { night, noiseTex, reversed }) {
  const off = reversed ? 1 : -1;
  const bg = new THREE.MeshStandardNodeMaterial({ side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: off * 1, polygonOffsetUnits: off * 2 });
  const bgCore = Fn(() => {
    const c = attribute('color', 'vec4'); const f = attribute('fuv', 'vec2'); const d = attribute('fdim', 'vec4'); const bc = attribute('bcol', 'vec3');
    const e = min(min(f.x, d.x.sub(f.x)), min(f.y, d.y.sub(f.y))); const aa = max(fwidth(e), 1e-3);
    const band = smoothstep(d.z.sub(aa), d.z.add(aa), e).mul(float(1.0).sub(smoothstep(d.w.sub(aa), d.w.add(aa), e))).mul(step(0.0, d.z));
    return vec4(mix(c.rgb, bc, band), c.a);
  }).once();
  bg.colorNode = vec4(bgCore().rgb, 1.0); bg.roughnessNode = float(0.45); bg.metalnessNode = float(0.0);
  bg.emissiveNode = bgCore().rgb.mul(bgCore().a).mul(night).mul(1.6);
  const glyph = new THREE.MeshStandardNodeMaterial({ side: THREE.DoubleSide, transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: off * 2, polygonOffsetUnits: off * 4 });
  const A = font.meta.atlas; const R = font.meta.distanceRange;
  const cov = Fn(() => {
    const u = TSL.uv(); const s = texture(font.tex, u);
    const med = max(min(s.r, s.g), min(max(s.r, s.g), s.b));
    // signed distance in atlas texels; screen pixels per atlas texel from the uv derivatives
    const dTex = med.sub(0.5).mul(2 * R), dSdf = s.a.sub(0.5).mul(2 * R);
    const texPerPx = length(fwidth(u.mul(vec2(A.width, A.height)))).mul(0.7071).max(1e-4);
    const pxPerTex = float(1.0).div(texPerPx);
    const m = clamp(dTex.mul(pxPerTex).add(0.5), 0.0, 1.0);
    const sdf = clamp(dSdf.mul(pxPerTex).add(0.5), 0.0, 1.0);
    // minified (< ~1.5 px per texel): the true-SDF channel (mip-friendly) instead of the corner-preserving median
    return mix(sdf, m, smoothstep(0.35, 0.8, pxPerTex));
  }).once();
  glyph.colorNode = vec4(attribute('color', 'vec4').rgb, 1.0); glyph.opacityNode = cov(); glyph.roughnessNode = float(0.45);
  glyph.emissiveNode = attribute('color', 'vec4').rgb.mul(attribute('color', 'vec4').a).mul(night).mul(1.6);
  const dark = new THREE.MeshStandardNodeMaterial({ color: new THREE.Color(0.05, 0.05, 0.05), roughness: 0.5, metalness: 0.1, side: THREE.DoubleSide });
  return { bg, glyph, dark };
}
export function signMeshes(builder, mats, name = 'signs') {
  const G = builder.geometries(); const group = new THREE.Group(); group.name = name;
  if (G.dark) { const m = new THREE.Mesh(G.dark, mats.dark); m.castShadow = true; m.receiveShadow = true; group.add(m); }
  if (G.bg) { const m = new THREE.Mesh(G.bg, mats.bg); m.receiveShadow = true; m.castShadow = false; group.add(m); }
  if (G.glyphs) { const m = new THREE.Mesh(G.glyphs, mats.glyph); m.receiveShadow = true; m.renderOrder = 2; group.add(m); }
  return group;
}
