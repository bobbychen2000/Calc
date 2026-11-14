// Studio look for the dev model viewer (OD4, 2026-11-14): the pc12 project's own three.js viewer (pc12/web/dev.html, the
// owner's reference look; settings read in out/pc12_ref_viewer/viewer_settings.md) rebuilt on the hwd3d renderer, so a
// still of dev/model.html?look=studio compares 1:1 with the reference at the same camera and any remaining difference is a
// material / shading difference of the hwd3d aircraft programs, not lighting. Not used by the app.
//
//   dev.html                                         here
//   ACESFilmic, exposure 1 (three applies / 0.6)     post.exposure 1 / 0.6, bloom / vignette / grain / chromatic aberration off
//   scene.environment = PMREM(RoomEnvironment)       the same room rendered into hwd3d's equirect env map (R.envTex): black
//                                                    walls + the six emissive panels of three r160 RoomEnvironment (linear
//                                                    radiance 100 / 50 / 50 / 17 / 43 / 20) seen from the origin; mip blur
//   DirectionalLight 1.6 at (5, 10, -6)              R.light.sunDir / sunColor 1.6 (irradiance, white), no shadows
//   HemisphereLight(0xffffff, 0x8899aa, 0.6)         + the room's cosine-weighted radiance -> uSkyUp / uSkyHorizon /
//                                                    uGroundBounce (acSky view factors in js/aircraft/detailed.js)
//   background 0xdfe3e6 (not tone mapped)            a backdrop sphere whose radiance tone-maps to (223, 227, 230)
//   no fog, no shadows, every mesh drawn             fog 0, aircraft shadowDist 0 (the 'structure' part stays excluded)
//   PMREM base blur (sigma 0.04 rad)                 uEnvLod0 2.5: the env map is read at least at mip 2.5
// The lights are given in glTF axes of the aircraft (X starboard, Y up, Z aft) and turned into the world frame with the
// aircraft's heading, so the light stays fixed to the aircraft as in dev.html.
import { gl, Mesh } from '../js/gl.js';
import { m4 } from '../js/math.js';
import { GLASS_VS } from '../js/aircraft/detailed.js';

const ROOM_PANELS = [   // three r160 examples/jsm/environments/RoomEnvironment.js: position, scale (unit box), radiance
  { p: [-16.116, 14.37, 8.208], s: [0.1, 2.428, 2.739], L: 50 }, { p: [-16.109, 18.021, -8.207], s: [0.1, 2.425, 2.751], L: 50 },
  { p: [14.904, 12.198, -1.832], s: [0.15, 4.265, 6.331], L: 17 }, { p: [-0.462, 8.89, 14.52], s: [4.38, 5.441, 0.088], L: 43 },
  { p: [3.235, 11.486, -12.541], s: [2.5, 2.0, 0.1], L: 20 }, { p: [0.0, 20.0, 0.0], s: [1.0, 0.1, 1.0], L: 100 },
];
const ROOM_WALL = 0.004;   // the room's walls / floor: lit by RoomEnvironment's PointLight at the legacy intensity 5 (no renderer passed) -> near black
// radiance of the room along glTF direction d (ray from the origin, where PMREM renders it)
function roomL(d) {
  let best = Infinity, L = ROOM_WALL;
  for (const b of ROOM_PANELS) {
    let t0 = -Infinity, t1 = Infinity;
    for (let k = 0; k < 3; k++) { const lo = b.p[k] - b.s[k] / 2, hi = b.p[k] + b.s[k] / 2;
      if (Math.abs(d[k]) < 1e-9) { if (0 < lo || 0 > hi) { t0 = Infinity; break; } continue; }
      let a = lo / d[k], c = hi / d[k]; if (a > c) [a, c] = [c, a]; t0 = Math.max(t0, a); t1 = Math.min(t1, c); }
    if (t0 <= t1 && t0 > 0 && t0 < best) { best = t0; L = b.L; }
  }
  return L;
}
// the camera's tone curve (js/shaders/post.js FINAL_FS: ACES fit + sRGB), to find the backdrop radiance
const inM = [[0.59719, 0.35458, 0.04823], [0.07600, 0.90834, 0.01566], [0.02840, 0.13383, 0.83777]];
const outM = [[1.60475, -0.53108, -0.07367], [-0.10208, 1.10813, -0.00605], [-0.00327, -0.07276, 1.07602]];
const mv = (M, v) => M.map(r => r[0] * v[0] + r[1] * v[1] + r[2] * v[2]);
const rrt = (v) => (v * (v + 0.0245786) - 0.000090537) / (v * (0.983729 * v + 0.4329510) + 0.238081);
const srgb = (c) => (c <= 0.0031308 ? c * 12.92 : 1.055 * Math.pow(c, 1 / 2.4) - 0.055);
const tone = (x, e) => mv(outM, mv(inM, x.map(v => v * e)).map(rrt)).map(c => srgb(Math.min(1, Math.max(0, c))));
export function backdropRadiance(target255, exposure) {
  const t = target255.map(v => v / 255); let x = [0.5, 0.5, 0.5];
  for (let i = 0; i < 200; i++) { const y = tone(x, exposure); x = x.map((v, k) => Math.max(1e-4, v * Math.pow(t[k] / Math.max(1e-4, y[k]), 1.5))); }
  return x;
}

export const STUDIO = { exposure: 1 / 0.6, sun: { dirGl: [5, 10, -6], E: 1.6 }, hemi: { sky: [1, 1, 1], ground: [0x88, 0x99, 0xaa], I: 0.6 }, bg: [223, 227, 230] };
const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };

// glTF axes of an aircraft at heading fwd (world [x, 0, z] unit) -> world direction
const glToWorld = (fwd, v) => { const r = [-fwd[2], 0, fwd[0]]; return [r[0] * v[0] - fwd[0] * v[2], v[1], r[2] * v[0] - fwd[2] * v[2]]; };
const norm = (v) => { const l = Math.hypot(...v); return v.map(x => x / l); };

let envData = null, bgItem = null;
function solveN(A, y) {   // Gaussian elimination with partial pivoting
  const n = y.length, M = A.map((r, i) => [...r, y[i]]);
  for (let c = 0; c < n; c++) { let p = c; for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r; [M[c], M[p]] = [M[p], M[c]];
    for (let r = 0; r < n; r++) if (r !== c) { const f = M[r][c] / M[c][c]; for (let k = c; k <= n; k++) M[r][k] -= f * M[c][k]; } }
  return M.map((r, i) => r[n] / r[i]);
}
// R: Renderer (after applyEnvToRenderer); fwd: the aircraft's heading vector; centre: world point the backdrop surrounds
export function applyStudio(R, fwd, centre, post) {
  // 1. environment map: the room in R.envTex (512 x 256 equirect, js/shaders/common.js dirToEquirect), in WORLD directions
  const W = 512, H = 256;
  if (!envData) envData = new Float32Array(W * H * 4);
  const right = [-fwd[2], 0, fwd[0]];
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const phi = ((x + 0.5) / W - 0.5) * 2 * Math.PI, th = (y + 0.5) / H * Math.PI;
    const dw = [Math.sin(th) * Math.sin(phi), Math.cos(th), -Math.sin(th) * Math.cos(phi)];   // world (inverse of dirToEquirect)
    const dg = [dw[0] * right[0] + dw[2] * right[2], dw[1], -(dw[0] * fwd[0] + dw[2] * fwd[2])];   // -> glTF of the aircraft
    const L = roomL(dg), i = (y * W + x) * 4; envData[i] = envData[i + 1] = envData[i + 2] = L; envData[i + 3] = 1;
  }
  gl.bindTexture(gl.TEXTURE_2D, R.envTex.tex); gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, W, H, gl.RGBA, gl.FLOAT, envData); gl.generateMipmap(gl.TEXTURE_2D);
  // 2. diffuse: hemisphere light (exactly linear in N.y) + the room's cosine-weighted radiance E(N) / pi, which is strongly
  //    directional (the aft and the overhead panels dominate): fitted with second-order spherical harmonics and handed to the
  //    aircraft programs as uAmbSH (js/aircraft/detailed.js acSky, uEnvSphere = 1); uSkyUp / uSkyHorizon / uGroundBounce
  //    get the same field (up / horizontal mean / down) for the other programs
  const cosRad = (n) => { let s = 0; const N = 48; for (let j = 0; j < N; j++) for (let i = 0; i < 2 * N; i++) {
    const th = (j + 0.5) / N * Math.PI, ph = (i + 0.5) / (2 * N) * 2 * Math.PI, d = [Math.sin(th) * Math.cos(ph), Math.cos(th), Math.sin(th) * Math.sin(ph)];
    const c = d[0] * n[0] + d[1] * n[1] + d[2] * n[2]; if (c > 0) s += roomL(d) * c * Math.sin(th); }
    return s * Math.PI / (N * N); };   // E / pi = (1 / pi) sum L cos dw, dw = sin(th) (pi / N)^2
  // least squares over 512 normals of a Fibonacci sphere (normals in WORLD axes; the room is looked up in glTF axes) on the
  // nine second-order basis functions [1, x, y, z, xy, yz, 3z^2 - 1, xz, x^2 - y^2]: rms 0.037, max 0.083 against the exact
  // E / pi (first order: up to 0.16 too bright on the port side); the hemisphere light (exactly 1 and y terms) is added
  const basis = (n) => { const [x, y, z] = n; return [1, x, y, z, x * y, y * z, 3 * z * z - 1, x * z, x * x - y * y]; };
  const NB = 9, A = Array.from({ length: NB }, () => new Array(NB).fill(0)), y = new Array(NB).fill(0);
  for (let k = 0; k < 512; k++) { const z = 1 - 2 * (k + 0.5) / 512, r = Math.sqrt(1 - z * z), ph = k * 2.399963229728653;
    const nw = [r * Math.cos(ph), z, r * Math.sin(ph)], ng = [nw[0] * right[0] + nw[2] * right[2], nw[1], -(nw[0] * fwd[0] + nw[2] * fwd[2])];
    const v = cosRad(ng), f = basis(nw);
    for (let i = 0; i < NB; i++) { y[i] += f[i] * v; for (let j = 0; j < NB; j++) A[i][j] += f[i] * f[j]; } }
  const sol = solveN(A, y);
  const hs = STUDIO.hemi.sky.map(c => c * STUDIO.hemi.I / Math.PI), hg = STUDIO.hemi.ground.map(c => lin(c) * STUDIO.hemi.I / Math.PI);
  const sh = new Float32Array(NB * 3);
  for (let i = 0; i < NB; i++) for (let c = 0; c < 3; c++) sh[i * 3 + c] = sol[i] + (i === 0 ? (hs[c] + hg[c]) / 2 : i === 2 ? (hs[c] - hg[c]) / 2 : 0);
  const at = (n) => [0, 1, 2].map(c => basis(n).reduce((a, b, i) => a + b * sh[i * 3 + c], 0));
  const up = at([0, 1, 0]), down = at([0, -1, 0]), hz = [[1, 0, 0], [-1, 0, 0], [0, 0, 1], [0, 0, -1]].map(at).reduce((a, b) => a.map((v, i) => v + b[i] / 4), [0, 0, 0]);
  const sunDir = norm(glToWorld(fwd, norm(STUDIO.sun.dirGl)));
  R.light = { sunDir, sunColor: [STUDIO.sun.E, STUDIO.sun.E, STUDIO.sun.E], skyUp: up, skyHorizon: hz.map((v, i) => Math.max(0, 2 * v - down[i])), ground: down.map(v => Math.max(0, v)) };
  // 3. no fog, no clouds; exposure / post as dev.html
  R.env.fog = [0, 0.001, 0, 0]; R.env.cloud = [0, 1500, 14000, 0];
  R.extraCommon = Object.assign(R.extraCommon || {}, { uNight: 0, uEnvSphere: 1, uEnvLod0: 2.5, uAmbSH: sh });
  Object.assign(post, { exposure: STUDIO.exposure, bloom: 0, vignette: 0, grain: 0, shutter: 0, sat: 1.0, ca: 0 });   // ca 0: no chromatic aberration (dev.html has none; on thin dark seams against the bright backdrop it fringes magenta)
  // 4. backdrop sphere (radius 250 m) of the tone-mapped background colour
  const bgL = backdropRadiance(STUDIO.bg, STUDIO.exposure);
  if (!R.progs.studiobg) R.addProgram('studiobg', GLASS_VS, `
#include <common>
#include <fout>
in vec3 vWP; in vec3 vN; in vec4 vCol; in vec4 vExt; in vec2 vUV;
uniform vec3 uBg;
void main(){ writeOut(uBg, vWP, 1.0); }`);
  if (!bgItem) {
    const S = 48, pos = [], idx = [], nrm = [], col = [], ext = [], uv = [];
    for (let j = 0; j <= S; j++) for (let i = 0; i <= 2 * S; i++) { const th = j / S * Math.PI, ph = i / (2 * S) * 2 * Math.PI;
      const d = [Math.sin(th) * Math.cos(ph), Math.cos(th), Math.sin(th) * Math.sin(ph)]; pos.push(...d.map(v => v * 250)); nrm.push(...d.map(v => -v)); col.push(1, 1, 1, 1); ext.push(1, 0, 0, 0); uv.push(0, 0); }
    for (let j = 0; j < S; j++) for (let i = 0; i < 2 * S; i++) { const a = j * (2 * S + 1) + i, b = a + 2 * S + 1; idx.push(a, b, a + 1, a + 1, b, b + 1); }
    const mesh = new Mesh({ pos: new Float32Array(pos), nrm: new Float32Array(nrm), col: new Float32Array(col), extra: new Float32Array(ext), uv: new Float32Array(uv), idx: new Uint32Array(idx), bbox: [-250, -250, -250, 250, 250, 250] });
    bgItem = { mesh, prog: 'studiobg', model: m4.ident(), bbox: null, castShadow: false, noCull: true, uniforms: { uBg: bgL } };
  }
  bgItem.model = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, centre[0], centre[1], centre[2], 1]);
  bgItem.uniforms = { uBg: bgL };
  return { item: bgItem, bgL, room: { sh: Array.from(sh), up, hz, down } };
}
