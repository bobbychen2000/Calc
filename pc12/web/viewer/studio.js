// Studio look: HDRI environment (CC0 Poly Haven studio, see assets/SOURCES.md), AgX tone mapping with
// Blender's "AgX - Punchy" look, a blurred contact shadow under the aircraft and a fading ground grid.
import * as THREE from 'three';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';
import { HorizontalBlurShader } from 'three/addons/shaders/HorizontalBlurShader.js';
import { VerticalBlurShader } from 'three/addons/shaders/VerticalBlurShader.js';

// ------------------------------------------------------------------------------------ tone mapping
// three.js r160 has AgX but none of Blender's looks; the Blender renders use the "AgX" view with the
// "AgX - Punchy" look.  In Blender 5.0 (config.ocio, looks) that look is a GradingToneTransform that darkens the
// shadows plus a CDL power 1.0912, both applied in Blender's 25-stop "AgX Log" space before the sigmoid, with
// no saturation boost; it is not a power on three's 16.5-stop log encoding.  So the looks here replace three's
// per-channel sigmoid (agxDefaultContrastApprox) with a curve fitted to Blender's own output for neutral greys:
//   u = (log2(x) - AgxMinEv) / (AgxMaxEv - AgxMinEv) -> t, the value three's AgX then runs through the outset
//   matrix and a 2.2 power.  6th-degree fits for u >= u0 (below: t0 (u / u0)^n, continuous in value and slope),
//   sampled with bpy save_render (16-bit PNG, greys 2^-12 .. 2^6): max error 1.9 (punchy) / 2.7 (base) of 255.
//   Three's inset / outset matrices then give Blender's chroma behaviour: the paint blue, light blue, prop red and
//   exhaust straw land within ~5/255 of Blender's AgX + Punchy over 9 stops (the old post-sigmoid saturation
//   clipped the blue's red channel and pulled the red band's hue from ~11 to ~3 deg).
//   agx  three.js' own AgX curve (the original, lighter; no look)
export const LOOKS = {
  punchy: { u0: 0.241, n: 1.4829, c: [0.072168, -1.873578, 17.684209, -73.803482, 150.044219, -135.883919, 44.746295] },
  base: { u0: 0.142, n: 3.3887, c: [0.008921, -0.887749, 12.87547, -60.557374, 133.832696, -128.622563, 44.366612] },
  agx: null,
};
export function installToneMapping(renderer, look = 'punchy') {
  if (look === 'aces') { renderer.toneMapping = THREE.ACESFilmicToneMapping; return; }
  const L = Object.prototype.hasOwnProperty.call(LOOKS, look) ? LOOKS[look] : LOOKS.punchy;
  const f = (x) => (+x).toFixed(6);
  const horner = L ? L.c.slice().reverse().reduce((acc, k, i) => (i ? `( ${acc} ) * u + ${f(k)}` : f(k)), '') : '';
  const curve = L ? `vec3 pcLookCurve( vec3 u ) {
	vec3 p = ${horner};
	const float u0 = ${f(L.u0)};
	vec3 tail = ${f(L.c.reduce((a, k, i) => a + k * L.u0 ** i, 0))} * pow( max( u / u0, vec3( 0.0 ) ), vec3( ${f(L.n)} ) );
	return clamp( mix( tail, p, step( vec3( u0 ), u ) ), 0.0, 1.0 );
}
` : '';
  const glsl = `${curve}vec3 CustomToneMapping( vec3 color ) {
	const mat3 AgXInsetMatrix = mat3(
		vec3( 0.856627153315983, 0.137318972929847, 0.11189821299995 ),
		vec3( 0.0951212405381588, 0.761241990602591, 0.0767994186031903 ),
		vec3( 0.0482516061458583, 0.101439036467562, 0.811302368396859 )
	);
	const mat3 AgXOutsetMatrix = mat3(
		vec3( 1.1271005818144368, - 0.1413297634984383, - 0.14132976349843826 ),
		vec3( - 0.11060664309660323, 1.157823702216272, - 0.11060664309660294 ),
		vec3( - 0.016493938717834573, - 0.016493938717834257, 1.2519364065950405 )
	);
	const float AgxMinEv = - 12.47393;
	const float AgxMaxEv = 4.026069;
	color = LINEAR_SRGB_TO_LINEAR_REC2020 * color;
	color *= toneMappingExposure;
	color = AgXInsetMatrix * color;
	color = max( color, 1e-10 );
	color = log2( color );
	color = ( color - AgxMinEv ) / ( AgxMaxEv - AgxMinEv );
	color = clamp( color, 0.0, 1.0 );
	color = ${L ? 'pcLookCurve( color )' : 'agxDefaultContrastApprox( color )'};
	color = AgXOutsetMatrix * color;
	color = pow( max( vec3( 0.0 ), color ), vec3( 2.2 ) );
	color = LINEAR_REC2020_TO_LINEAR_SRGB * color;
	return clamp( color, 0.0, 1.0 );
}`;
  const chunk = THREE.ShaderChunk.tonemapping_pars_fragment;
  const re = /vec3 CustomToneMapping\( vec3 color \) \{[^}]*\}/;
  if (re.test(chunk) && chunk.includes('agxDefaultContrastApprox')) {
    THREE.ShaderChunk.tonemapping_pars_fragment = chunk.replace(re, glsl);
    renderer.toneMapping = THREE.CustomToneMapping;
  } else {
    renderer.toneMapping = THREE.AgXToneMapping ?? THREE.ACESFilmicToneMapping;
  }
}

// ------------------------------------------------------------------------------------ environment
export function loadHDR(url, onProgress) {
  return new Promise((resolve, reject) => {
    new RGBELoader().load(url, resolve, onProgress, (e) => reject(e instanceof Error ? e : new Error(String(e && e.message || e))));
  });
}

// Graded, prefiltered studio environments from one equirectangular HDRI.  r160 has no
// environmentRotation, so the turn is baked in (pixel columns shifted).  Grades:
//   floor  factor below the horizon (the HDRI's white floor -> a darker studio floor in the reflections)
//   walls  factor for everything that is not a lamp / softbox (luminance < 1.5, back to 1 at 6): the
//          dark theme mirrors a dark cyclorama like the Blender hero, the softboxes keep their punch
//   top    radiance of a large round overhead softbox added round the zenith (the HDRI's ceiling is
//          black acoustic foam, so wing tops and the plan view would mirror nothing)
//   lift   neutral floor on the luminance: a texel darker than `lift` is raised to it (added evenly to r, g, b)
//          before the other grades.  studio_small_09's right half and ceiling are black foam (luminance ~0.02); a
//          small lift turns it into a dark grey room like the hangar's ceiling in photo 130.  (A large one, 0.35,
//          turned the whole upper hemisphere into one flat grey: chrome, clear coat and glass mirrored nothing.)
//   wallLift the lift round the horizon and below (blended into `lift` 15..35 deg up): the foam walls as a mid-grey
//          hangar wall (the exhaust stacks and tyres mirror them), the ceiling stays dark.  null = `lift` everywhere.
//   strips radiance of the ceiling LED strips added to the upper hemisphere (STRIPS: rows along the fuselage axis,
//          like the hangar of photo 130 and the Blender hangar render): the structure the cowl, windshield,
//          spinner and exhaust stacks mirror.  0 = none.
// The strips are a runtime grade, not a painted HDRI: a ray from the aircraft in direction d (d.y > 0.08) meets the
// ceiling plane y = h at X = h d.x / d.y, Z = h d.z / d.y (glTF axes: X span, Z fuselage axis); a texel gets `strips`
// where |Z| < len and |X - x_i| < w / 2, anti-aliased by supersampling the texels along the strip edges.
export const STRIPS = { x: [-6, -2, 2, 6], w: 0.3, h: 5.5, len: 14 };

export class StudioEnvironment {
  constructor(renderer, hdrTexture, rotDeg = 0) {
    this.renderer = renderer;
    const img = hdrTexture.image, W = img.width, H = img.height, src = img.data;
    const ch = src.length / (W * H);
    const half = src instanceof Uint16Array;
    const k = Math.round((((rotDeg % 360) + 360) % 360) / 360 * W);
    const f = new Float32Array(W * H * 3);
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        const i = (y * W + x) * ch, o = (y * W + ((x + k) % W)) * 3;
        for (let c = 0; c < 3; c++) f[o + c] = half ? THREE.DataUtils.fromHalfFloat(src[i + c]) : src[i + c];
      }
    }
    this.W = W; this.H = H; this.f = f;
    this.flipY = hdrTexture.flipY;
    this.cache = new Map();
    hdrTexture.dispose();
  }

  // fraction of the texel (column x, row y; fractional = a point) covered by a ceiling strip
  _strip(xf, yf) {
    const { W, H } = this, S = STRIPS;
    const el = (0.5 - yf / H) * Math.PI, se = Math.sin(el);
    if (se <= 0.08) return 0;
    const phi = (xf / W - 0.5) * 2 * Math.PI, t = (S.h / se) * Math.cos(el);
    const X = t * Math.cos(phi), Z = t * Math.sin(phi);
    if (Math.abs(Z) >= S.len) return 0;
    for (const x of S.x) if (Math.abs(X - x) < S.w / 2) return 1;
    return 0;
  }

  _stripTexel(x, y) {
    // centre sample; texels whose corners disagree with it straddle an edge: 4 x 4 supersampling
    const c = this._strip(x + 0.5, y + 0.5);
    if (this._strip(x, y) === c && this._strip(x + 1, y) === c && this._strip(x, y + 1) === c && this._strip(x + 1, y + 1) === c) {
      // a strip narrower than a texel can hide between the corners: test the middle of each edge too
      if (this._strip(x + 0.5, y) === c && this._strip(x + 0.5, y + 1) === c && this._strip(x, y + 0.5) === c && this._strip(x + 1, y + 0.5) === c) return c;
    }
    let n = 0;
    for (let j = 0; j < 4; j++) for (let i = 0; i < 4; i++) n += this._strip(x + (i + 0.5) / 4, y + (j + 0.5) / 4);
    return n / 16;
  }

  get({ floor = 1, walls = 1, top = 0, lift = 0, wallLift = null, strips = 0 } = {}) {
    const key = `${floor}|${walls}|${top}|${lift}|${wallLift}|${strips}`;
    if (this.cache.has(key)) return this.cache.get(key);
    const { W, H, f } = this;
    const out = new Uint16Array(W * H * 4);
    const toH = THREE.DataUtils.toHalfFloat, one = toH(1);
    const sm = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
    for (let y = 0; y < H; y++) {
      const el = 90 - ((y + 0.5) / H) * 180;               // row 0 = straight up
      const kf = 1 + (floor - 1) * sm(1, 8, -el);           // below the horizon
      const add = top * sm(48, 62, el);                      // overhead softbox: zenith angle < ~35 deg
      const lamps = strips > 0 && el > 4;
      // the lift: `lift` overhead, `wallLift` (if given) round the horizon and below, blended 15..35 deg up
      const lf = wallLift == null ? lift : wallLift + (lift - wallLift) * sm(15, 35, el);
      for (let x = 0; x < W; x++) {
        const i = (y * W + x) * 3, o = (y * W + x) * 4;
        let r = f[i], g = f[i + 1], b = f[i + 2];
        let L = 0.2126 * r + 0.7152 * g + 0.0722 * b;
        if (L < lf) { const d = lf - L; r += d; g += d; b += d; L = lf; }
        const k = kf * (walls === 1 ? 1 : walls + (1 - walls) * sm(1.5, 6, L));
        const a = add + (lamps ? strips * this._stripTexel(x, y) : 0);
        out[o] = toH(r * k + a); out[o + 1] = toH(g * k + a); out[o + 2] = toH(b * k + a); out[o + 3] = one;
      }
    }
    const tex = new THREE.DataTexture(out, W, H, THREE.RGBAFormat, THREE.HalfFloatType);
    tex.colorSpace = THREE.LinearSRGBColorSpace;
    tex.minFilter = tex.magFilter = THREE.LinearFilter;
    tex.generateMipmaps = false;
    tex.flipY = this.flipY;
    tex.mapping = THREE.EquirectangularReflectionMapping;
    tex.needsUpdate = true;
    const pm = new THREE.PMREMGenerator(this.renderer);
    const env = pm.fromEquirectangular(tex).texture;
    pm.dispose();
    tex.dispose();
    this.cache.set(key, env);
    return env;
  }
}

// ------------------------------------------------------------------------------------ contact shadow
// The three.js "contact shadows" recipe: an orthographic camera under the aircraft looks up, renders the
// model's depth (only meshes on CONTACT_LAYER) as darkness that fades with height, blurs it twice and
// lays the result on the ground.  Rendered only when the pose changes (update()).
export const CONTACT_LAYER = 3;

export class ContactShadow {
  constructor(renderer, { size = 512, height = 1.6, darkness = 1.25, blur = 3.2, opacity = 0.62 } = {}) {
    this.renderer = renderer;
    this.size = size;
    this.height = height;
    this.blur = blur;
    const rtOpts = { type: THREE.HalfFloatType };
    this.rt = new THREE.WebGLRenderTarget(size, size, rtOpts);
    this.rt.texture.generateMipmaps = false;
    this.rtBlur = new THREE.WebGLRenderTarget(size, size, rtOpts);
    this.rtBlur.texture.generateMipmaps = false;
    this.group = new THREE.Group();
    this.group.name = 'contact_shadow';
    const geo = new THREE.PlaneGeometry(1, 1).rotateX(Math.PI / 2);
    this.material = new THREE.MeshBasicMaterial({ map: this.rt.texture, transparent: true, opacity, depthWrite: false, toneMapped: false, fog: false });
    this.plane = new THREE.Mesh(geo, this.material);
    this.plane.renderOrder = -2;
    this.plane.scale.y = -1;            // the texture's v runs the other way
    this.plane.raycast = () => {};
    this.group.add(this.plane);
    this.blurPlane = new THREE.Mesh(geo);
    this.blurPlane.visible = false;
    this.blurPlane.layers.set(CONTACT_LAYER);   // rendered by the layer-3 camera (else the blur clears the map)
    this.cam = new THREE.OrthographicCamera(-0.5, 0.5, 0.5, -0.5, 0, height);
    this.cam.rotation.x = Math.PI / 2;  // look up
    this.cam.layers.set(CONTACT_LAYER);
    this.group.add(this.cam);
    const dm = (this.depthMat = new THREE.MeshDepthMaterial());
    dm.userData.darkness = { value: darkness };
    dm.onBeforeCompile = (sh) => {
      sh.uniforms.darkness = dm.userData.darkness;
      sh.fragmentShader = 'uniform float darkness;\n' + sh.fragmentShader.replace(
        'gl_FragColor = vec4( vec3( 1.0 - fragCoordZ ), opacity );',
        'gl_FragColor = vec4( vec3( 0.0 ), ( 1.0 - fragCoordZ ) * darkness );');
    };
    dm.depthTest = false;
    dm.depthWrite = false;
    dm.side = THREE.DoubleSide;
    this.hBlur = new THREE.ShaderMaterial(HorizontalBlurShader);
    this.hBlur.depthTest = false;
    this.vBlur = new THREE.ShaderMaterial(VerticalBlurShader);
    this.vBlur.depthTest = false;
    this.w = 1; this.d = 1;
  }

  // footprint (glTF X / Z extent of the model box + margin) and ground height
  fit(box, groundY) {
    const c = box.getCenter(new THREE.Vector3()), s = box.getSize(new THREE.Vector3());
    const m = 2.5;
    this.w = s.x + 2 * m; this.d = s.z + 2 * m;
    this.group.position.set(c.x, groundY, c.z);
    // PlaneGeometry rotated about X lies in XZ: scale x = width, z = depth; scale.y = -1 turns its
    // front face up and flips v (the render target's rows run the other way)
    this.plane.scale.set(this.w, -1, this.d);
    this.blurPlane.scale.set(this.w, 1, this.d);
    const cam = this.cam;
    cam.left = -this.w / 2; cam.right = this.w / 2; cam.top = this.d / 2; cam.bottom = -this.d / 2;
    cam.far = this.height;
    cam.updateProjectionMatrix();
  }

  setGround(y) { this.group.position.y = y; }

  _blur(amount) {
    const r = this.renderer, bp = this.blurPlane;
    bp.visible = true;
    bp.position.copy(this.group.position).y += 0.01;
    bp.material = this.hBlur;
    this.hBlur.uniforms.tDiffuse.value = this.rt.texture;
    this.hBlur.uniforms.h.value = amount / this.size;
    r.setRenderTarget(this.rtBlur);
    r.render(bp, this.cam);
    bp.material = this.vBlur;
    this.vBlur.uniforms.tDiffuse.value = this.rtBlur.texture;
    this.vBlur.uniforms.v.value = amount / this.size;
    r.setRenderTarget(this.rt);
    r.render(bp, this.cam);
    bp.visible = false;
  }

  update(scene) {
    const r = this.renderer;
    const bg = scene.background, ov = scene.overrideMaterial, rt = r.getRenderTarget();
    const clear = r.getClearColor(new THREE.Color()), alpha = r.getClearAlpha();
    const sm = r.shadowMap.autoUpdate, smu = r.shadowMap.needsUpdate;
    this.group.updateMatrixWorld(true);
    scene.background = null;
    scene.overrideMaterial = this.depthMat;
    r.shadowMap.autoUpdate = false;       // the key-light shadow map is not this render's business
    r.shadowMap.needsUpdate = false;
    r.setClearColor(0x000000, 0);
    r.setRenderTarget(this.rt);
    r.clear();
    r.render(scene, this.cam);
    scene.overrideMaterial = ov;
    this._blur(this.blur);
    this._blur(this.blur * 0.4);
    r.setRenderTarget(rt);
    r.setClearColor(clear, alpha);
    r.shadowMap.autoUpdate = sm;
    r.shadowMap.needsUpdate = smu;
    scene.background = bg;
  }

  dispose() { this.rt.dispose(); this.rtBlur.dispose(); }
}

// ------------------------------------------------------------------------------------ ground grid
// 1 m / 5 m lines, anti-aliased with fwidth, fading out radially around the aircraft.
export function makeGrid() {
  const mat = new THREE.ShaderMaterial({
    uniforms: {
      uColor: { value: new THREE.Color(0x000000) },
      uAlpha: { value: 0.12 },
      uCenter: { value: new THREE.Vector2(0, 7) },
      uR: { value: new THREE.Vector2(5, 21) },
    },
    vertexShader: `varying vec3 vW;
void main() { vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: `uniform vec3 uColor; uniform float uAlpha; uniform vec2 uCenter; uniform vec2 uR;
varying vec3 vW;
float gridLine(vec2 p, float spacing, float width) {
  vec2 c = p / spacing;
  vec2 g = abs(fract(c - 0.5) - 0.5) / max(fwidth(c), vec2(1e-5));
  return 1.0 - min(min(g.x, g.y) / width, 1.0);
}
void main() {
  float minor = gridLine(vW.xz, 1.0, 1.0);
  float major = gridLine(vW.xz, 5.0, 1.4);
  float fade = 1.0 - smoothstep(uR.x, uR.y, distance(vW.xz, uCenter));
  float a = max(minor * 0.5, major) * uAlpha * fade;
  if (a < 0.003) discard;
  gl_FragColor = vec4(uColor, a);
}`,
    transparent: true, depthWrite: false, extensions: { derivatives: true },
  });
  const grid = new THREE.Mesh(new THREE.PlaneGeometry(90, 90).rotateX(-Math.PI / 2), mat);
  grid.renderOrder = -3;
  grid.raycast = () => {};
  grid.name = 'grid';
  return grid;
}
