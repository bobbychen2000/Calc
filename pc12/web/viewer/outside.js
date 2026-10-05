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
export const SUN = { az: 125, el: 40 };
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
};
const GROUND = { size: 400, y: -0.004, apron: [-120, -160, 240, 260], slab: 7.5, concrete: '#c9c6bf', grass: '#6f7a52',
  taxi: '#d9b43a', farColor: [0.20, 0.26, 0.13], farR: [199, 440], ridgeR: 400, ridgeColor: [0.42, 0.50, 0.58] };
// hangars / buildings: centre X, Z, width, height, depth (m), albedo; pre-lit by facing the sun (vertex colours)
const HANGARS = [
  [55, -95, 70, 16, 40, [0.95, 0.97, 1.0]], [-70, -120, 60, 14, 35, [0.92, 0.92, 0.9]],
  [130, -20, 30, 10, 60, [0.8, 0.82, 0.85]], [-150, -40, 40, 9, 25, [0.85, 0.8, 0.75]],
  [10, -190, 90, 12, 20, [0.9, 0.9, 0.92]],
];

// a deterministic PRNG (the apron's mottling is the same on every load and device)
function rng(seed) {
  let s = seed >>> 0;
  return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

function groundTexture(px) {
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
  return cv;
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
      uniforms: { uZen: { value: lin(SKY.zenith) }, uHor: { value: lin(SKY.horizon) }, uSun: { value: this.sun } },
      vertexShader: 'varying vec3 vD;\nvoid main() { vD = normalize( position ); gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 ); }',
      fragmentShader: `uniform vec3 uZen; uniform vec3 uHor; uniform vec3 uSun; varying vec3 vD;
void main() {
  vec3 d = normalize( vD );
  float e = clamp( d.y, 0.0, 1.0 );
  vec3 c = mix( uHor, uZen, pow( e, ${SKY.blend.toFixed(3)} ) );
  float s = max( dot( d, uSun ), 0.0 );
  c += vec3( 1.0, 0.95, 0.85 ) * ( ${SKY.glow[0].toFixed(3)} * pow( s, ${SKY.glow[1].toFixed(1)} ) + ${SKY.disc[0].toFixed(3)} * pow( s, ${SKY.disc[1].toFixed(1)} ) );
  if ( d.y < 0.0 ) c = uHor * ${SKY.below.toFixed(3)};
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
    const tex = new THREE.CanvasTexture(groundTexture(this.texPx));
    tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
    tex.generateMipmaps = true; tex.minFilter = THREE.LinearMipmapLinearFilter;
    this._tex = tex;
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(G.size, G.size),
      new THREE.MeshBasicMaterial({ name: 'outside_ground', map: tex, color: lin([1.05, 1.05, 1.05]), depthWrite: false }));
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
      // BoxGeometry groups: +x, -x, +y, -y, +z, -z
      const m = new THREE.Mesh(geo, [side, side, roof, roof, side, side]);
      m.position.set(cx, bh / 2, cz);
      w.add(m);
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
    const pm = new THREE.PMREMGenerator(renderer);
    this._env = pm.fromScene(es, 0, 0.1, 500).texture;
    pm.dispose();
    zen.copy(keep);
    return this._env;
  }
  // the cached environment belongs to a lost context: forget it (not disposed: its GL objects are gone)
  contextLost() { this._env = null; this._tex.needsUpdate = true; this._fac.needsUpdate = true; }
  ownsEnv(tex) { return !!tex && tex === this._env; }
}
