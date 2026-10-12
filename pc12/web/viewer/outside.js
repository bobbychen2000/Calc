// The world outside the glazing while the eye is inside the cabin (look L1, review FD-J02 / LK-01): a procedural sunny
// apron -- sky dome, concrete apron with slab joints and a taxi line, grass, a far ring, a few pre-lit hangars and a
// ridge on the horizon -- so the windshield and the side windows show a real outside instead of the white studio void,
// and (environment()) the image-based light inside comes from that sky and ground, not from the studio's softboxes.
// No image files (nothing to licence or download) and no lettering or logos.  Shown only inside (Stage.setInteriorLook):
// the exterior studio is untouched.  Not pickable, casts / receives no shadow, not on the contact-shadow layer.
//
// Axes: glTF (X = starboard, Y = up, Z = aft); the aircraft's nose points to -Z.  Radiance values are linear and
// AgX-calibrated: the renderer's exposure applies (the sky's ShaderMaterial includes the tone mapping and colour-space
// chunks, so the still / temporal passes' 'XR' targets treat it like every other material).
import * as THREE from 'three';

const D2R = Math.PI / 180;
// the sun: az from dead ahead toward starboard, el above the horizon (model axes: x aft, y starboard, z up).  Behind the
// starboard wing root (az 125 / el 40) it comes in through the co-pilot's side window and the forward cabin windows: sun
// on the pedestal, the sub-panels and the seats, the glareshield's shade over the PDU tops (a sun-only sweep: az 65 /
// el 26 -- the look assessment's -- lit only the glareshield's lip from the seats; az 40 / el 50 and the port-side
// mirror images lit no more)
const Q_O = new URLSearchParams(typeof location !== 'undefined' ? location.search : '');
const qo = (k, d) => { const v = parseFloat(Q_O.get(k)); return Number.isFinite(v) ? v : d; };
// flight deck fix r1 (FDO1-05): az 25 / el 45 -- ahead and to starboard, over the windshield: sun on the hood with the
// posts' shadows across it, on the pedestal, the armrests and the seats, the panel in the glareshield's shade (P1046409:
// the sun patch on the co-pilot's fleece; the look track's az 125 / el 40 from behind the starboard wing root lit only
// the stack face from the seats)
// flight deck fix r2 (FDO2-02 / FID-FD2-04): el 45 -> 30, az 25 -> 20 -- the sun through the windshield now lands on the
// hood crown with the centre post's and A-pillars' shadows across it from both crew stops (an az 20-90 / el 28-35 sweep:
// az 60 lit the pilot's sill and console, az 90 the seats -- P1046408's sheepskin 127 -> 192)
export const SUN = { az: qo('sunaz', 20), el: qo('sunel', 30) };      // ?sunaz= ?sunel= (look development)
export function sunDirection(az = SUN.az, el = SUN.el) {
  const a = az * D2R, e = el * D2R;
  // model (-cos e cos a, cos e sin a, sin e) -> glTF (y, z, x)
  return new THREE.Vector3(Math.cos(e) * Math.sin(a), Math.sin(e), -Math.cos(e) * Math.cos(a)).normalize();
}

// sky radiance (linear): the horizon / zenith of a clear midday sky at the interior exposure (x1.3 over the first
// prototype: the windshield's sky read ~225-245 sRGB, as P1046408 / 10 through the glass), the sun's glow and disc
export const SKY = {
  zenith: [0.26, 0.47, 1.0],
  horizon: [1.24, 1.33, 1.43],
  blend: 0.45,                // mix(horizon, zenith, elevation^blend)
  glow: [0.6, 12],            // sun glow: k * pow(cos, n)
  disc: [6.0, 900],           // sun disc
  below: 0.8,                 // below the horizon (behind the ridge / far ring): 0.8 x the horizon
  // the image-based light inside takes the zenith this much toward its own grey: a cabin's daylight comes in through
  // the windows from the bright horizon and the apron, not from the deep blue overhead (the full blue zenith tinted every
  // up-facing surface -- the sheepskin read slate blue, B - R ~50 against P1046408's ~22)
  envDesat: 0.6,
  haze: [[1.36, 1.31, 1.22], 0.35, 28.0],     // warm horizon haze: colour (linear), share at the horizon, falloff / elevation
  // flight deck fix r5 (FDO4-04: through the windshield the sky read pure white, 254, against P1046410's clear blue
  // 210 / 233 / 251): the sky as SEEN is multiplied by `seen` [tint (linear), from / to sin(elevation)] above the haze --
  // the image-based light inside (environment()) keeps the untinted sky, so the calibrated cabin light does not move
  seen: [[0.50, 0.72, 1.0], 0.0, 0.14],
};
// flight deck fix r1 (FDO1-08): the apron as seen through the glazing x `shown` (0.86: the near-white concrete clipped
// at the interior exposure); the image-based light inside keeps the full value (`environment()`: the calibrated cabin
// light is unchanged)
// flight deck fix r2 (FDO2-08 / FID-FD2-08: a bright bland sim floor, ~230 sRGB with regular seams, filling the side
// windows): shown at 0.34 (0.62 still read ~215 through AgX; ~180-195 from the seats), low-frequency stains and tone variation, tyre marks along the lead-in
// lines, oil spots, tie-down rings, the hangars' and parked shapes' cast shadows and contact darkening baked into the
// apron (the sun is fixed), a second taxi line, a distance haze toward the horizon (`haze`: colour, from / to m, most);
// the image-based light inside keeps the apron's mean albedo (`envK`, the calibrated cabin light unchanged)
const GROUND = { size: 400, y: -0.004, apron: [-120, -160, 240, 260], slab: 7.5, concrete: '#c9c6bf', grass: '#6f7a52',
  shown: 0.34, envK: 1.08, haze: ['198,205,212', 55, 200, 0.5],
  taxi: '#d9b43a', farColor: [0.20, 0.26, 0.13], farR: [199, 440], ridgeR: 400, ridgeColor: [0.42, 0.50, 0.58] };
// hangars / buildings: centre X, Z, width, height, depth (m), albedo; pre-lit by facing the sun (vertex colours)
// (flight deck fix r3 FDO3-07 asked for the building P1046408 shows behind the glare at the photo-fitted panel_408b
// camera: through its fitted camera a tall block 12-14 deg right of the nose ~21 deg up and a long hall 20-31 deg right,
// its roof 15-18 deg up, from the cabin eye.  A nearer hall there (22-50 deg right, eaves ~19 deg up) was tried and
// taken out again: from the crew seats the same azimuths and elevations are open blue sky down to the hood on both sides
// of the centre post in P1046410 and P1046409 -- the same aircraft, the same session --, the hall filled the right
// windshield at the pilot stop and the Cockpit preset ([FD-L1] sky over the cowl 250 -> 203, [BV-5] 145).  The crew-seat
// photos win: the buildings stay low and far)
const HANGARS = [
  [55, -95, 70, 16, 40, [0.95, 0.97, 1.0]], [-70, -120, 60, 14, 35, [0.92, 0.92, 0.9]],
  [130, -20, 30, 10, 60, [0.8, 0.82, 0.85]], [-150, -40, 40, 9, 25, [0.85, 0.8, 0.75]],
  [10, -190, 90, 12, 20, [0.9, 0.9, 0.92]],
];

// parked shapes on the apron (FDO1-08: the photos show other aircraft and vehicles beyond the nose): generic low-poly
// single-engine turboprops (white, grey trim; no markings) and a tug -- [x, z, heading deg (0 = nose to -Z), scale]
const PARKED = [[-34, -52, 155, 1.0], [42, -66, 200, 0.95], [-62, -78, 120, 1.05]];
const TUGS = [[30, -58, 70]];
// (fix r2 FID-FD2-08) a fuel truck and cones off the port beam, seen through the pilot's side window [x, z, heading]
const TRUCKS = [[-27, 4, 80]];
const CONES = [[-9.5, 1.5], [-9.5, -3.5], [9.5, 1.5]];

// a deterministic PRNG (the apron's mottling is the same on every load and device)
function rng(seed) {
  let s = seed >>> 0;
  return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

// shadow polygon of an axis-aligned box (centre x, z, width, depth, height) on the ground for the sun direction
// (glTF; towards the sun): the convex hull of its footprint and its top projected along -sun
function boxShadow(cx, cz, bw, bd, bh, sun) {
  const kx = -sun.x / Math.max(sun.y, 0.05), kz = -sun.z / Math.max(sun.y, 0.05), P = [];
  for (const [dx, dz] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) {
    P.push([cx + 0.5 * dx * bw, cz + 0.5 * dz * bd], [cx + 0.5 * dx * bw + kx * bh, cz + 0.5 * dz * bd + kz * bh]);
  }
  P.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lo = [], up = [];
  for (const p of P) { while (lo.length >= 2 && cross(lo[lo.length - 2], lo[lo.length - 1], p) <= 0) lo.pop(); lo.push(p); }
  for (const p of P.slice().reverse()) { while (up.length >= 2 && cross(up[up.length - 2], up[up.length - 1], p) <= 0) up.pop(); up.push(p); }
  return lo.slice(0, -1).concat(up.slice(0, -1));
}

function groundTexture(px, sun = sunDirection()) {
  const cv = document.createElement('canvas');
  cv.width = cv.height = px;
  const g = cv.getContext('2d'), G = GROUND, S = px / G.size, o = G.size / 2;
  const R = rng(1201);
  g.fillStyle = G.grass; g.fillRect(0, 0, px, px);
  // grass mottling
  for (let i = 0; i < 1500; i++) {
    g.fillStyle = `rgba(${R() < 0.5 ? '70,80,48' : '128,138,94'},${0.06 + 0.08 * R()})`;
    g.fillRect(R() * px, R() * px, (4 + 20 * R()) * S, (4 + 20 * R()) * S);
  }
  const [ax, az, aw, ad] = G.apron;
  g.fillStyle = G.concrete; g.fillRect((ax + o) * S, (az + o) * S, aw * S, ad * S);
  // concrete mottling: slab-sized lighter / darker patches
  for (let i = 0; i < 4000; i++) {
    g.fillStyle = `rgba(${R() < 0.5 ? '90,88,84' : '235,232,226'},${0.05 + 0.08 * R()})`;
    g.fillRect((ax + o + R() * aw) * S, (az + o + R() * ad) * S, G.slab * S * R(), G.slab * S * R());
  }
  // slab joints
  g.strokeStyle = 'rgba(70,68,64,0.55)'; g.lineWidth = Math.max(1, 1.2 * px / 2048);
  for (let x = ax; x <= ax + aw + 1e-6; x += G.slab) { g.beginPath(); g.moveTo((x + o) * S, (az + o) * S); g.lineTo((x + o) * S, (az + ad + o) * S); g.stroke(); }
  for (let z = az; z <= az + ad + 1e-6; z += G.slab) { g.beginPath(); g.moveTo((ax + o) * S, (z + o) * S); g.lineTo((ax + aw + o) * S, (z + o) * S); g.stroke(); }
  // the taxi line along the aircraft's axis and a lead-in arc (0.15 m wide)
  g.strokeStyle = G.taxi; g.lineWidth = Math.max(1, 0.3 * S);
  g.beginPath(); g.moveTo(o * S, (az + o) * S); g.lineTo(o * S, (az + ad + o) * S); g.stroke();
  g.beginPath(); g.arc((o + 25) * S, (o - 30) * S, 25 * S, Math.PI * 0.5, Math.PI); g.stroke();
  // (fix r2) a second taxi line across the apron ahead and a lead-in from the port side
  g.beginPath(); g.moveTo((ax + o) * S, (o - 42) * S); g.lineTo((ax + aw + o) * S, (o - 42) * S); g.stroke();
  g.beginPath(); g.arc((o - 30) * S, (o - 12) * S, 30 * S, 0, Math.PI * 0.5); g.stroke();
  const W2 = (x, z) => [(x + o) * S, (z + o) * S];
  // low-frequency stains and tone variation over the apron (soft blobs 3-18 m)
  for (let i = 0; i < 220; i++) {
    const [cx, cz] = W2(ax + R() * aw, az + R() * ad), rr = (3 + 15 * R()) * S;
    const gr = g.createRadialGradient(cx, cz, 0, cx, cz, rr);
    const c = R() < 0.7 ? '78,76,72' : '214,210,202', a = 0.06 + 0.12 * R();
    gr.addColorStop(0, `rgba(${c},${a})`); gr.addColorStop(1, `rgba(${c},0)`);
    g.fillStyle = gr; g.fillRect(cx - rr, cz - rr, 2 * rr, 2 * rr);
  }
  // tyre marks along the lead-in lines (dark rubber, 0.25 m wide, either side of the line)
  g.lineCap = 'round';
  for (const d of [-1.6, -1.3, 1.3, 1.6]) {
    g.strokeStyle = `rgba(40,40,40,${0.10 + 0.08 * R()})`; g.lineWidth = Math.max(1, 0.25 * S);
    g.beginPath(); g.moveTo((o + d) * S, (o - 140) * S); g.lineTo((o + d) * S, (o + 60) * S); g.stroke();
    g.beginPath(); g.arc((o + 25) * S, (o - 30) * S, (25 + d) * S, Math.PI * 0.5, Math.PI); g.stroke();
  }
  // tie-down rings in rows and oil spots under the parked aircraft
  g.strokeStyle = 'rgba(52,52,50,0.7)'; g.lineWidth = Math.max(1, 0.06 * S);
  for (let x = -60; x <= 60; x += 15) for (const z of [-30, -75]) { const [cx, cz] = W2(x, z); g.beginPath(); g.arc(cx, cz, 0.18 * S, 0, 2 * Math.PI); g.stroke(); }
  for (const [x, z, hd] of PARKED) {
    const h = hd * D2R;
    for (let k = 0; k < 3; k++) {
      const [cx, cz] = W2(x - Math.sin(h) * (4 + 2 * R()) + (R() - 0.5), z + Math.cos(h) * (4 + 2 * R()) + (R() - 0.5)), rr = (0.4 + 0.9 * R()) * S;
      const gr = g.createRadialGradient(cx, cz, 0, cx, cz, rr);
      gr.addColorStop(0, 'rgba(30,28,26,0.45)'); gr.addColorStop(1, 'rgba(30,28,26,0)');
      g.fillStyle = gr; g.fillRect(cx - rr, cz - rr, 2 * rr, 2 * rr);
    }
  }
  // the buildings' cast shadows and the dark band at their foot (the sun is fixed: baked), the parked shapes' shadows
  const poly = (P, style) => { g.fillStyle = style; g.beginPath(); P.forEach(([x, z], i) => { const [u, v] = W2(x, z); if (i) g.lineTo(u, v); else g.moveTo(u, v); }); g.closePath(); g.fill(); };
  for (const [cx, cz, bw, bh, bd] of HANGARS) {
    poly(boxShadow(cx, cz, bw, bd, bh, sun), 'rgba(38,40,46,0.42)');
    g.strokeStyle = 'rgba(30,30,32,0.35)'; g.lineWidth = 1.6 * S;
    const [u0, v0] = W2(cx - 0.5 * bw, cz - 0.5 * bd);
    g.strokeRect(u0, v0, bw * S, bd * S);
  }
  const kx = -sun.x / Math.max(sun.y, 0.05), kz = -sun.z / Math.max(sun.y, 0.05);
  const rot = (x, z, h, sc, dx, dz) => [x + sc * (dx * Math.cos(h) - dz * Math.sin(h)), z + sc * (dx * Math.sin(h) + dz * Math.cos(h))];
  for (const [x, z, hd, sc] of PARKED) {
    const h = hd * D2R;
    const ell = []; for (let k = 0; k < 24; k++) { const a = 2 * Math.PI * k / 24; ell.push(rot(x + kx * 1.75 * sc, z + kz * 1.75 * sc, h, sc, 0.75 * Math.cos(a), 1.0 + 6.4 * Math.sin(a))); }
    poly(ell, 'rgba(38,40,46,0.40)');
    poly([[-8, -1.5], [8, -1.5], [8, 0.3], [-8, 0.3]].map(([dx, dz]) => rot(x + kx * 1.25 * sc, z + kz * 1.25 * sc, h, sc, dx, dz)), 'rgba(38,40,46,0.38)');
    poly([[-2.6, 7.5], [2.6, 7.5], [2.6, 8.5], [-2.6, 8.5]].map(([dx, dz]) => rot(x + kx * 4.5 * sc, z + kz * 4.5 * sc, h, sc, dx, dz)), 'rgba(38,40,46,0.32)');
  }
  for (const [x, z, hd, bw, bl] of [...TUGS.map(([a, b, c]) => [a, b, c, 1.5, 2.6]), ...TRUCKS.map(([a, b, c]) => [a, b, c, 2.5, 8.2])]) {
    poly([[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]].map(([dx, dz]) => rot(x + kx * 1.2, z + kz * 1.2, hd * D2R, 1, dx * bw, dz * bl)), 'rgba(38,40,46,0.40)');
  }
  // distance haze toward the horizon
  const [hc, h0, h1, hk] = G.haze;
  const gr = g.createRadialGradient(o * S, o * S, h0 * S, o * S, o * S, h1 * S);
  gr.addColorStop(0, `rgba(${hc},0)`); gr.addColorStop(1, `rgba(${hc},${hk})`);
  g.fillStyle = gr; g.fillRect(0, 0, px, px);
  return cv;
}

// a hangar facade (sRGB, multiplied by the pre-lit vertex colour): light corrugated cladding, a darker door bay over the
// lower two thirds with its panel joints, a row of high windows, a dark roof-edge band
function facadeTexture() {
  const W = 512, H = 256, cv = document.createElement('canvas');
  cv.width = W; cv.height = H;
  const g = cv.getContext('2d');
  g.fillStyle = '#e4e5e6'; g.fillRect(0, 0, W, H);
  g.fillStyle = 'rgba(120,124,130,0.18)';
  for (let x = 0; x < W; x += 4) g.fillRect(x, 0, 1.5, H);            // corrugation
  g.fillStyle = '#7d8288'; g.fillRect(0, 0, W, 10);                     // roof edge
  g.fillStyle = '#9aa0a6'; g.fillRect(W * 0.08, H * 0.34, W * 0.84, H * 0.66);   // door bay
  g.strokeStyle = 'rgba(60,64,70,0.55)'; g.lineWidth = 2;
  for (let i = 0; i <= 8; i++) { const x = W * (0.08 + 0.84 * i / 8); g.beginPath(); g.moveTo(x, H * 0.34); g.lineTo(x, H); g.stroke(); }
  g.fillStyle = '#5d6b78';
  for (let x = W * 0.1; x < W * 0.9; x += W * 0.07) g.fillRect(x, H * 0.16, W * 0.045, H * 0.08);   // high windows
  // (FDO1-08) cladding panel seams, the door leaves' horizontal joints and a shade of grime toward the ground
  g.fillStyle = 'rgba(70,74,80,0.35)';
  for (let x = 0; x < W; x += W / 16) g.fillRect(x, 10, 1.5, H * 0.34 - 10);
  for (const y of [0.52, 0.70, 0.88]) g.fillRect(W * 0.08, H * y, W * 0.84, 1.5);
  const gr = g.createLinearGradient(0, H * 0.75, 0, H);
  gr.addColorStop(0, 'rgba(60,58,54,0)'); gr.addColorStop(1, 'rgba(60,58,54,0.28)');
  g.fillStyle = gr; g.fillRect(0, H * 0.75, W, H * 0.25);
  // (flight deck fix r3 FDO3-07: flat, toy-like boxes) the eaves' shadow band under the roof edge, the door leaves'
  // vertical joints doubled with a light edge (a recessed seam catching the sun), a door track along the bay's top, a
  // personnel door, down pipes and a darker plinth
  const ev = g.createLinearGradient(0, 10, 0, 30);
  ev.addColorStop(0, 'rgba(40,44,50,0.45)'); ev.addColorStop(1, 'rgba(40,44,50,0)');
  g.fillStyle = ev; g.fillRect(0, 10, W, 20);
  for (let i = 0; i <= 16; i++) {
    const x = W * (0.08 + 0.84 * i / 16);
    g.fillStyle = 'rgba(48,52,58,0.45)'; g.fillRect(x - 1, H * 0.34, 1.5, H * 0.66);
    g.fillStyle = 'rgba(255,255,255,0.35)'; g.fillRect(x + 0.5, H * 0.34, 1, H * 0.66);
  }
  g.fillStyle = '#5a6068'; g.fillRect(W * 0.07, H * 0.325, W * 0.86, 4);
  g.fillStyle = '#6e767e'; g.fillRect(W * 0.94, H * 0.62, W * 0.03, H * 0.38);
  g.fillStyle = 'rgba(40,44,50,0.5)'; g.fillRect(W * 0.94, H * 0.62, W * 0.03, 2);
  g.fillStyle = 'rgba(90,96,104,0.7)';
  for (const x of [W * 0.03, W * 0.985]) g.fillRect(x, 10, 3, H - 10);
  g.fillStyle = 'rgba(70,70,68,0.45)'; g.fillRect(0, H - 6, W, 6);
  return cv;
}

// (fix r2) the distance haze on the pre-lit shapes: their vertex colours mixed toward the haze colour (linear) by distance
const HAZE_LIN = [0.56, 0.61, 0.66];
function hazeK(x, z) {
  const [, h0, h1, hk] = GROUND.haze, d = Math.hypot(x, z), t = Math.min(1, Math.max(0, (d - h0) / (h1 - h0)));
  return hk * t * t * (3 - 2 * t);
}
function hazeGeo(geo, k) {
  if (!(k > 0)) return geo;
  const c = geo.attributes.color;
  for (let i = 0; i < c.count; i++) c.setXYZ(i, c.getX(i) + (HAZE_LIN[0] - c.getX(i)) * k, c.getY(i) + (HAZE_LIN[1] - c.getY(i)) * k, c.getZ(i) + (HAZE_LIN[2] - c.getZ(i)) * k);
  return geo;
}

export class OutsideWorld {
  // low: the light tier's 1024 px ground (2048 elsewhere)
  constructor({ low = false, sun = sunDirection() } = {}) {
    this.sun = sun.clone().normalize();
    this.texPx = low ? 1024 : 2048;
    this.group = new THREE.Group();
    this.group.name = 'outside_world';
    this.group.visible = false;
    this._env = null;
    this._build();
  }

  _build() {
    const w = this.group, G = GROUND, lin = (c) => new THREE.Color().setRGB(c[0], c[1], c[2], THREE.LinearSRGBColorSpace);
    // ---- sky dome (camera far plane 500)
    const sky = new THREE.Mesh(new THREE.SphereGeometry(440, 64, 32), new THREE.ShaderMaterial({
      name: 'outside_sky', side: THREE.BackSide, depthWrite: false, fog: false,
      uniforms: { uZen: { value: lin(SKY.zenith) }, uHor: { value: lin(SKY.horizon) }, uSun: { value: this.sun },
        uSeen: { value: new THREE.Vector4(...SKY.seen[0], 1) } },
      vertexShader: 'varying vec3 vD;\nvoid main() { vD = normalize( position ); gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 ); }',
      fragmentShader: `uniform vec3 uZen; uniform vec3 uHor; uniform vec3 uSun; uniform vec4 uSeen; varying vec3 vD;
void main() {
  vec3 d = normalize( vD );
  float e = clamp( d.y, 0.0, 1.0 );
  vec3 c = mix( uHor, uZen, pow( e, ${SKY.blend.toFixed(3)} ) );
  float s = max( dot( d, uSun ), 0.0 );
  c += vec3( 1.0, 0.95, 0.85 ) * ( ${SKY.glow[0].toFixed(3)} * pow( s, ${SKY.glow[1].toFixed(1)} ) + ${SKY.disc[0].toFixed(3)} * pow( s, ${SKY.disc[1].toFixed(1)} ) );
  // (flight deck fix r3 FDO3-07) a faint warm haze in the lowest few degrees over the horizon
  c = mix( c, vec3( ${SKY.haze[0].map((x) => x.toFixed(3)).join(', ')} ), ${SKY.haze[1].toFixed(3)} * exp( - e * ${SKY.haze[2].toFixed(1)} ) );
  if ( d.y < 0.0 ) c = uHor * ${SKY.below.toFixed(3)};
  // (flight deck fix r5) the sky as seen a clear blue (uSeen.w 0 while the image-based light is rendered)
  c *= mix( vec3( 1.0 ), uSeen.xyz, uSeen.w * smoothstep( ${SKY.seen[1].toFixed(3)}, ${SKY.seen[2].toFixed(3)}, e ) );
  gl_FragColor = vec4( c, 1.0 );
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}` }));
    sky.renderOrder = -10;
    sky.frustumCulled = false;
    this._skyMat = sky.material;
    w.add(sky);
    // ---- the far ring and the apron / grass square: drawn first without depth (the ring overlaps the square's corners;
    // 2 mm apart they would z-fight at 200 m with the cabin's 1 cm near plane), the aircraft and hangars over them
    const far = new THREE.Mesh(new THREE.RingGeometry(G.farR[0], G.farR[1], 96, 1),
      new THREE.MeshBasicMaterial({ name: 'outside_far', color: lin(G.farColor), side: THREE.DoubleSide, depthWrite: false }));
    far.rotation.x = -Math.PI / 2; far.position.y = G.y - 0.002; far.renderOrder = -9;
    w.add(far);
    const tex = new THREE.CanvasTexture(groundTexture(this.texPx, this.sun));
    tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
    tex.generateMipmaps = true; tex.minFilter = THREE.LinearMipmapLinearFilter;
    this._tex = tex;
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(G.size, G.size),
      new THREE.MeshBasicMaterial({ name: 'outside_ground', map: tex, color: lin([G.shown, G.shown, G.shown]), depthWrite: false }));
    this._groundMat = ground.material;
    ground.rotation.x = -Math.PI / 2; ground.position.y = G.y; ground.renderOrder = -8;
    w.add(ground);
    // ---- hangars (pre-lit: sunlit faces bright, the shaded ones sky-lit): corrugated cladding, a darker door bay
    // with its panel joints, a row of high windows, a roof edge (one small canvas for every facade; no lettering)
    const lit = (n) => 0.38 + 0.9 * Math.max(0, n.dot(this.sun));
    const fac = new THREE.CanvasTexture(facadeTexture());
    fac.colorSpace = THREE.SRGBColorSpace; fac.anisotropy = 4;
    this._fac = fac;
    const side = new THREE.MeshBasicMaterial({ name: 'outside_facade', map: fac, vertexColors: true });
    const roof = new THREE.MeshBasicMaterial({ name: 'outside_roof', vertexColors: true });
    for (const [cx, cz, bw, bh, bd, col] of HANGARS) {
      const geo = new THREE.BoxGeometry(bw, bh, bd);
      const nrm = geo.attributes.normal, c = [], n = new THREE.Vector3();
      for (let i = 0; i < nrm.count; i++) {
        n.fromBufferAttribute(nrm, i);
        const k = lit(n) * (n.y > 0.5 ? 0.82 : 1);          // the roof a shade darker than the cladding
        c.push(col[0] * k, col[1] * k, col[2] * k);
      }
      geo.setAttribute('color', new THREE.Float32BufferAttribute(c, 3));
      hazeGeo(geo, hazeK(cx, cz));
      // BoxGeometry groups: +x, -x, +y, -y, +z, -z
      const m = new THREE.Mesh(geo, [side, side, roof, roof, side, side]);
      m.position.set(cx, bh / 2, cz);
      w.add(m);
    }
    // ---- parked aircraft and a tug (pre-lit like the hangars; generic shapes, no markings)
    const prelit = (geo, col) => {
      const nrm = geo.attributes.normal, c = [], n = new THREE.Vector3();
      for (let i = 0; i < nrm.count; i++) {
        n.fromBufferAttribute(nrm, i);
        const k = lit(n);
        c.push(col[0] * k, col[1] * k, col[2] * k);
      }
      geo.setAttribute('color', new THREE.Float32BufferAttribute(c, 3));
      return geo;
    };
    const vmat = new THREE.MeshBasicMaterial({ name: 'outside_parked', vertexColors: true });
    const part = (geo, col, x, y, z, rx = 0, ry = 0, rz = 0) => {
      geo.rotateX(rx); geo.rotateY(ry); geo.rotateZ(rz); geo.translate(x, y, z);
      return prelit(geo.toNonIndexed(), col);
    };
    const WHITE = [0.86, 0.87, 0.88], GREY = [0.42, 0.44, 0.47], DARK = [0.06, 0.065, 0.07];
    for (const [px, pz, hd, sc] of PARKED) {
      const gs = [
        part(new THREE.CylinderGeometry(0.62, 0.78, 9.0, 16), WHITE, 0, 1.75, 0.6, Math.PI / 2),          // fuselage
        part(new THREE.ConeGeometry(0.62, 3.6, 16), WHITE, 0, 1.75, 6.9, Math.PI / 2),                    // tail cone
        part(new THREE.SphereGeometry(0.78, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), WHITE, 0, 1.75, -3.9, -Math.PI / 2),
        part(new THREE.ConeGeometry(0.30, 0.55, 12), GREY, 0, 1.75, -4.95, -Math.PI / 2),                  // spinner
        part(new THREE.BoxGeometry(16.0, 0.22, 1.8), WHITE, 0, 1.25, -0.6),                                 // wing
        part(new THREE.BoxGeometry(0.16, 2.3, 1.6), WHITE, 0, 3.4, 7.6),                                    // fin
        part(new THREE.BoxGeometry(5.2, 0.12, 1.0), WHITE, 0, 4.5, 8.0),                                    // T-tail
        part(new THREE.BoxGeometry(1.15, 0.38, 0.06), DARK, 0, 2.35, -2.45, 0.55),                          // windshield
        part(new THREE.BoxGeometry(1.62, 0.32, 2.6), DARK, 0, 2.05, 0.2),                                   // window band
        part(new THREE.CylinderGeometry(0.18, 0.18, 1.2, 8), GREY, 0, 0.55, -3.2),                          // nose leg
        part(new THREE.CylinderGeometry(0.28, 0.28, 0.2, 12), DARK, 0, 0.28, -3.2, 0, 0, Math.PI / 2),      // nose wheel
        part(new THREE.CylinderGeometry(0.32, 0.32, 0.24, 12), DARK, -2.25, 0.32, 0.4, 0, 0, Math.PI / 2),  // mains
        part(new THREE.CylinderGeometry(0.32, 0.32, 0.24, 12), DARK, 2.25, 0.32, 0.4, 0, 0, Math.PI / 2),
        part(new THREE.CylinderGeometry(0.1, 0.1, 1.1, 6), GREY, -2.25, 0.85, 0.4),
        part(new THREE.CylinderGeometry(0.1, 0.1, 1.1, 6), GREY, 2.25, 0.85, 0.4),
      ];
      for (const g of gs) {
        const m = new THREE.Mesh(hazeGeo(g, hazeK(px, pz)), vmat);
        m.scale.setScalar(sc);
        m.rotation.y = -hd * D2R;
        m.position.set(px, 0, pz);
        w.add(m);
      }
    }
    for (const [tx, tz, hd] of TUGS) {
      for (const g of [part(new THREE.BoxGeometry(1.5, 0.75, 2.6), [0.55, 0.45, 0.14], 0, 0.62, 0),
        part(new THREE.BoxGeometry(1.2, 0.85, 0.9), [0.55, 0.45, 0.14], 0, 1.4, 0.7),
        part(new THREE.BoxGeometry(1.1, 0.45, 0.05), DARK, 0, 1.55, 0.24),
        ...[-0.62, 0.62].flatMap((x) => [-0.85, 0.85].map((z) => part(new THREE.CylinderGeometry(0.3, 0.3, 0.25, 10), DARK, x, 0.3, z, 0, 0, Math.PI / 2)))]) {
        const m = new THREE.Mesh(hazeGeo(g, hazeK(tx, tz)), vmat);
        m.rotation.y = -hd * D2R;
        m.position.set(tx, 0, tz);
        w.add(m);
      }
    }
    // (fix r2 FID-FD2-08) a fuel truck off the port beam and traffic cones by the wing tips: generic shapes, no markings
    const TANK = [0.80, 0.81, 0.82], CONE = [0.95, 0.32, 0.04];
    for (const [tx, tz, hd] of TRUCKS) {
      const wheels = [-2.6, 1.0, 2.4].flatMap((z) => [-1.05, 1.05].map((x) => part(new THREE.CylinderGeometry(0.48, 0.48, 0.35, 12), DARK, x, 0.48, z, 0, 0, Math.PI / 2)));
      for (const g of [part(new THREE.BoxGeometry(2.4, 2.3, 2.1), WHITE, 0, 1.65, -3.0),                     // cab
        part(new THREE.BoxGeometry(2.2, 0.75, 0.05), DARK, 0, 2.15, -4.07),                                    // windshield
        part(new THREE.BoxGeometry(2.42, 0.6, 1.2), DARK, 0, 2.2, -3.0),                                       // side windows
        part(new THREE.CylinderGeometry(1.08, 1.08, 5.4, 18), TANK, 0, 1.95, 1.0, Math.PI / 2),                // tank
        part(new THREE.BoxGeometry(2.3, 0.35, 7.8), GREY, 0, 0.78, -0.3),                                      // chassis
        part(new THREE.BoxGeometry(2.25, 0.5, 1.0), GREY, 0, 1.2, 3.6),                                        // hose cabinet
        ...wheels]) {
        const m = new THREE.Mesh(hazeGeo(g, hazeK(tx, tz)), vmat);
        m.rotation.y = -hd * D2R;
        m.position.set(tx, 0, tz);
        w.add(m);
      }
    }
    for (const [cx, cz] of CONES) {
      for (const g of [part(new THREE.ConeGeometry(0.17, 0.7, 12), CONE, 0, 0.38, 0), part(new THREE.BoxGeometry(0.42, 0.04, 0.42), CONE, 0, 0.02, 0),
        part(new THREE.CylinderGeometry(0.105, 0.125, 0.09, 12), WHITE, 0, 0.42, 0)]) {
        const m = new THREE.Mesh(g, vmat);
        m.position.set(cx, 0, cz);
        w.add(m);
      }
    }
    // ---- the ridge on the horizon (a hazy blue-grey band of hills)
    const N = 256, pos = [], idx = [];
    for (let i = 0; i <= N; i++) {
      const a = (i / N) * 2 * Math.PI;
      const h = 6 + 9 * (0.5 + 0.5 * Math.sin(3 * a + 1)) * (0.6 + 0.4 * Math.sin(11 * a)) + 4 * Math.sin(29 * a);
      const x = G.ridgeR * Math.cos(a), z = G.ridgeR * Math.sin(a);
      pos.push(x, -1, z, x, Math.max(2, h), z);
      if (i < N) { const b = 2 * i; idx.push(b, b + 1, b + 2, b + 1, b + 3, b + 2); }
    }
    const rg = new THREE.BufferGeometry();
    rg.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    rg.setIndex(idx);
    const ridge = new THREE.Mesh(rg, new THREE.MeshBasicMaterial({ name: 'outside_ridge', color: lin(G.ridgeColor), side: THREE.DoubleSide }));
    ridge.frustumCulled = false;
    w.add(ridge);
    w.traverse((o) => {
      if (!o.isMesh) return;
      o.castShadow = false; o.receiveShadow = false; o.raycast = () => {};
      o.layers.set(0);              // never on the contact-shadow (or overlay) layer
      o.userData.outside = true;
    });
  }

  setVisible(on) { this.group.visible = !!on; }

  // The image-based light inside (look L4, LK-05): the world rendered into a prefiltered environment once (linear
  // radiance: PMREM renders without tone mapping), cached; null after a lost context (rebuilt on demand)
  environment(renderer) {
    if (this._env) return this._env;
    const es = new THREE.Scene(), copy = this.group.clone(true);
    copy.visible = true;
    es.add(copy);
    // (the clone shares the sky's material: its zenith desaturated for this render only, SKY.envDesat)
    const zen = this._skyMat.uniforms.uZen.value, keep = zen.clone();
    const y = 0.2126 * zen.r + 0.7152 * zen.g + 0.0722 * zen.b, k = SKY.envDesat;
    zen.setRGB(zen.r + (y - zen.r) * k, zen.g + (y - zen.g) * k, zen.b + (y - zen.b) * k, THREE.LinearSRGBColorSpace);
    const gk = this._groundMat.color.clone();
    this._groundMat.color.setRGB(GROUND.envK, GROUND.envK, GROUND.envK, THREE.LinearSRGBColorSpace);
    const seen = this._skyMat.uniforms.uSeen.value, seenW = seen.w;
    seen.w = 0;
    const pm = new THREE.PMREMGenerator(renderer);
    this._env = pm.fromScene(es, 0, 0.1, 500).texture;
    pm.dispose();
    seen.w = seenW;
    zen.copy(keep);
    this._groundMat.color.copy(gk);
    return this._env;
  }
  // the cached environment belongs to a lost context: forget it (not disposed: its GL objects are gone)
  contextLost() { this._env = null; this._tex.needsUpdate = true; this._fac.needsUpdate = true; }
  ownsEnv(tex) { return !!tex && tex === this._env; }
}
