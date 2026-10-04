// Picture quality (owner 2026-10-03: "smoother curves, edges and a sharper, crisper picture"): the render paths behind
// Stage.render(), specular anti-aliasing, texture filtering, the key light's soft shadow and the 'Picture quality'
// setting.
//
//   still frames    once the camera and the scene have been still for STILL_DELAY frames, the scene is rendered into a
//                   multisampled render target at up to 2x the canvas resolution (capped by a pixel and a memory budget
//                   and by MAX_TEXTURE_SIZE / MAX_RENDERBUFFER_SIZE / MAX_VIEWPORT_DIMS), box-filtered down to the
//                   canvas (an exact area average, any scale) and accumulated over N frames jittered by Halton (2, 3)
//                   offsets within one source pixel: temporal supersampling.  Frame 0 is unjittered, so the first
//                   supersampled frame lands where the last moving frame was (no shift); later frames only refine.
//   moving frames   the canvas itself (its own 4x MSAA) at the moving pixel ratio.  Through the render target as well
//                   when the canvas has no MSAA (a browser that refused `antialias`), and supersampled (the still
//                   target's scale) when a supersampled frame has been measured to fit in the display refresh (Auto /
//                   Max): fast GPUs keep the still image's edges while orbiting.
//   same colours    the render target gets the canvas' exact shader output -- tone mapped (AgX + Punchy), sRGB-encoded,
//                   premultiplied alpha over a transparent clear (three r160 applies tone mapping and the output colour
//                   space to an 'XR' render target, WebGLPrograms; its RGBA8 storage is forced linear) -- and is
//                   averaged in that encoding, as the canvas' own MSAA resolve does: switching paths changes the
//                   sampling, never the colours.  Pixel-sized effects follow the scale: the ground grid's line width,
//                   the construction lines' opacity (1 px wide in the target = 1 / S of an output pixel).
//   specular AA     the GGX roughness widened by the screen-space variance of the shading normal (Tokuyoshi &
//                   Kaplanyan 2019, Filament's variance 0.15 / threshold 0.2) instead of three's additive
//                   `geometryRoughness` (max |dN| added to the roughness: it dulled every curved glossy surface by the
//                   same amount, rough or not); the roughness floor matched to the environment's base mip.
//   textures        the maximum anisotropy and trilinear mipmaps on every texture the model carries (the G3000 page
//                   atlas), and on the contact shadow.
//   key shadow      percentage-closer soft shadows on the ground (the only receiver): blocker search + a Vogel-disk
//                   PCF whose radius grows with the caster's height over the floor (a softbox of KEY_ANGLE degrees),
//                   so the tyres' contact is crisp and the wing's shadow soft; the shadow camera is fitted to the
//                   posed model each time the map is rendered (Stage._fitShadow).
//   adaptive (Auto) real frame times (rAF intervals while each frame renders; idle intervals give the refresh period)
//                   step the moving pixel ratio between min(1, dprMax) and dprMax, the still pixel budget (down to 1x),
//                   the accumulation length (down to none) and the moving supersampling; nothing goes below the
//                   pre-2026-10 picture (desktop: the full pixel ratio while moving).
//   setting         Specs panel 'Picture quality': Auto / High / Max (localStorage 'pc12-picture', try/catch);
//                   ?picture=auto|high|max, or ?quality=high|max (which also picks the desktop tier), override it
//                   without being remembered.
import * as THREE from 'three';

const Q_ = new URLSearchParams(location.search);
const qn = (k) => (Q_.has(k) && Q_.get(k) !== '' && isFinite(+Q_.get(k)) ? +Q_.get(k) : undefined);

export const PICTURE_KEY = 'pc12-picture';
export const PICTURE_MODES = ['auto', 'high', 'max'];
export const STILL_DELAY = 3;          // frames the camera and the scene must be still before supersampling starts

// The setting: URL override, else the remembered choice, else Auto.
export function pictureChoice() {
  const p = Q_.get('picture'), q = Q_.get('quality');
  if (PICTURE_MODES.includes(p)) return { mode: p, forced: true };
  if (q === 'high' || q === 'max' || q === 'auto') return { mode: q, forced: true };
  let s = null;
  try { s = localStorage.getItem(PICTURE_KEY); } catch (e) { s = null; }
  return { mode: PICTURE_MODES.includes(s) ? s : 'auto', forced: false };
}

// Budgets per device tier and mode:
//   frames   accumulated still frames (N)            px / mem  the still target's pixel / byte budget
//   ss       the largest still scale (per axis)      samples   its MSAA samples below / from a scale of 1.5
//   moveSS   the largest moving supersampling scale, used only when measured to fit the refresh (0: never)
//   adapt    still budget / accumulation / moving ratio follow measured frame times (Auto)
//   shadow   key-light shadow map; contact  contact-shadow map; pcss  [blocker search, filter] samples
export const PROFILES = {
  desktop: {
    auto: { frames: 16, px: 8.3e6, mem: 240e6, ss: 2, samples: [4, 2], moveSS: 1.5, adapt: true, shadow: 4096, contact: 1024, pcss: [16, 32] },
    high: { frames: 16, px: 8.3e6, mem: 240e6, ss: 2, samples: [4, 2], moveSS: 0, adapt: false, shadow: 4096, contact: 1024, pcss: [16, 32] },
    max: { frames: 32, px: 16.6e6, mem: 480e6, ss: 2, samples: [8, 4], moveSS: 2, adapt: false, shadow: 4096, contact: 1024, pcss: [24, 48] },
  },
  phone: {
    auto: { frames: 8, px: 2.1e6, mem: 64e6, ss: 1.5, samples: [4, 2], moveSS: 0, adapt: true, shadow: 2048, contact: 512, pcss: [8, 16] },
    high: { frames: 12, px: 3.7e6, mem: 96e6, ss: 2, samples: [4, 2], moveSS: 0, adapt: false, shadow: 2048, contact: 512, pcss: [12, 24] },
    max: { frames: 16, px: 8.3e6, mem: 192e6, ss: 2, samples: [4, 2], moveSS: 2, adapt: false, shadow: 2048, contact: 1024, pcss: [16, 32] },
  },
};
// ?ssframes= / ?sspx= override the accumulation length and the still pixel budget (tests, look development)
const OV = { frames: qn('ssframes'), px: qn('sspx') };

// still target bytes: colour + depth per MSAA sample, plus the resolved colour and depth
const rtBytes = (px, samples) => px * (8 * Math.max(1, samples) + 8);
const halton = (i, b) => { let f = 1, r = 0; while (i > 0) { f /= b; r += f * (i % b); i = Math.floor(i / b); } return r; };
const median = (a) => { if (!a.length) return NaN; const s = a.slice().sort((x, y) => x - y); return s[s.length >> 1]; };

// ------------------------------------------------------------------------------------ specular anti-aliasing
// Installed once into three's shader chunks (every MeshStandard / MeshPhysicalMaterial, no per-material patch).
// floor: the smallest roughness, the base mip of the prefiltered environment (three's 0.0525 is a 256 px face; the
// 2k studio HDRI makes a 512 px one: 1 / (1.16 sqrt(512)) = 0.038, cube_uv_reflection_fragment's roughnessToMip).
export const SPEC_AA = { variance: 0.15, threshold: 0.2 };
export function installSpecularAA(floor = 0.0525) {
  const C = THREE.ShaderChunk;
  if (C.lights_physical_fragment.includes('pcSpecAA')) return true;
  const f = (x) => (+x).toFixed(5);
  const kernel = `vec3 pcNdx = dFdx( nonPerturbedNormal ), pcNdy = dFdy( nonPerturbedNormal );
float pcSpecK = min( ${f(2 * SPEC_AA.variance)} * ( dot( pcNdx, pcNdx ) + dot( pcNdy, pcNdy ) ), ${f(SPEC_AA.threshold)} );`;
  const src = C.lights_physical_fragment;
  const out = src
    .replace(/vec3 dxy = max\( abs\( dFdx\( nonPerturbedNormal \) \), abs\( dFdy\( nonPerturbedNormal \) \) \);\s*float geometryRoughness = max\( max\( dxy\.x, dxy\.y \), dxy\.z \);/, kernel)
    .replace(/material\.roughness = max\( roughnessFactor, 0\.0525 \);\s*material\.roughness \+= geometryRoughness;\s*material\.roughness = min\( material\.roughness, 1\.0 \);/,
      `material.roughness = pcSpecAA( max( roughnessFactor, ${f(floor)} ), pcSpecK );`)
    .replace(/material\.clearcoatRoughness = max\( material\.clearcoatRoughness, 0\.0525 \);\s*material\.clearcoatRoughness \+= geometryRoughness;\s*material\.clearcoatRoughness = min\( material\.clearcoatRoughness, 1\.0 \);/,
      `material.clearcoatRoughness = pcSpecAA( max( material.clearcoatRoughness, ${f(floor)} ), pcSpecK );`);
  if (out === src || /geometryRoughness/.test(out)) {
    console.warn('specular anti-aliasing not installed: three.js lights_physical_fragment changed');
    return false;
  }
  C.lights_physical_fragment = out;
  // alpha = r^2; the filtered alpha^2 = alpha^2 + kernel; back to perceptual roughness
  C.lights_physical_pars_fragment = `float pcSpecAA( const in float r, const in float k ) {
	float a = r * r;
	return sqrt( sqrt( min( a * a + k, 1.0 ) ) );
}
` + C.lights_physical_pars_fragment;
  return true;
}

// ------------------------------------------------------------------------------------ PCSS key shadow on the ground
// Shared uniforms (Stage._fitShadow sets them for the fitted shadow camera):
//   uPcssK      filter radius in shadow-map UV per unit of (receiver - blocker) depth (the light's half angle)
//   uPcssSearch blocker search radius (UV)     uPcssMin  smallest filter radius (UV, ~1.5 texels)
//   uPcssFrame  the accumulation frame: turns the per-pixel rotation of the sample disc (noise averages out)
export const PCSS_U = {
  uPcssK: { value: new THREE.Vector2(0.001, 0.001) },
  uPcssSearch: { value: new THREE.Vector2(0.01, 0.01) },
  uPcssMin: { value: new THREE.Vector2(0.0003, 0.0003) },
  uPcssFrame: { value: 0 },
};
const GLSL_PCSS = `uniform vec2 uPcssK;
uniform vec2 uPcssSearch;
uniform vec2 uPcssMin;
uniform float uPcssFrame;
float pcIGN( vec2 p ) { return fract( 52.9829189 * fract( dot( p, vec2( 0.06711056, 0.00583715 ) ) ) ); }
vec2 pcVogel( int i, int n, float phi ) {
	float r = sqrt( ( float( i ) + 0.5 ) / float( n ) );
	float t = float( i ) * 2.39996323 + phi;
	return r * vec2( cos( t ), sin( t ) );
}
float pcPCSS( sampler2D sm, vec4 sc ) {
	float phi = 6.2831853 * fract( pcIGN( gl_FragCoord.xy ) + uPcssFrame * 0.6180340 );
	float zR = sc.z, zSum = 0.0, nB = 0.0;
	for ( int i = 0; i < PC_PCSS_BLOCKER; i ++ ) {
		float z = unpackRGBAToDepth( texture2D( sm, sc.xy + pcVogel( i, PC_PCSS_BLOCKER, phi ) * uPcssSearch ) );
		if ( z < zR ) { zSum += z; nB += 1.0; }
	}
	if ( nB < 0.5 ) return 1.0;
	vec2 r = clamp( ( zR - zSum / nB ) * uPcssK, uPcssMin, uPcssSearch );
	float s = 0.0;
	for ( int i = 0; i < PC_PCSS_FILTER; i ++ ) {
		s += step( zR, unpackRGBAToDepth( texture2D( sm, sc.xy + pcVogel( i, PC_PCSS_FILTER, phi + 1.3 ) * r ) ) );
	}
	return s / float( PC_PCSS_FILTER );
}
`;
// the ground's ShadowMaterial: three's PCF branch of getShadow() replaced by pcPCSS (renderer.shadowMap.type PCF)
export function patchShadowMaterial(mat, [blocker, filter]) {
  const chunk = THREE.ShaderChunk.shadowmap_pars_fragment;
  const re = /#if defined\( SHADOWMAP_TYPE_PCF \)\s*\n\s*vec2 texelSize[\s\S]*?\* \( 1\.0 \/ 17\.0 \);/;
  if (!re.test(chunk) || !chunk.includes('float getShadow(')) {
    console.warn('PCSS not installed: three.js shadowmap_pars_fragment changed');
    return false;
  }
  const pars = chunk.replace('float getShadow(', GLSL_PCSS + 'float getShadow(')
    .replace(re, '#if defined( SHADOWMAP_TYPE_PCF )\n\t\t\tshadow = pcPCSS( shadowMap, shadowCoord );');
  mat.defines = { ...(mat.defines || {}), PC_PCSS_BLOCKER: blocker | 0, PC_PCSS_FILTER: filter | 0 };
  mat.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, PCSS_U);
    sh.fragmentShader = sh.fragmentShader.replace('#include <shadowmap_pars_fragment>', pars);
  };
  mat.customProgramCacheKey = () => `pc12:pcss${blocker}/${filter}`;
  mat.needsUpdate = true;
  return true;
}

// ------------------------------------------------------------------------------------ full-screen passes
const FS_VERT = 'void main() { gl_Position = vec4( position.xy, 0.0, 1.0 ); }';
// area-weighted box filter of the source over each output pixel (any scale >= 1), optionally blended into the running
// average: out = mix( prev, box, uW )
const DOWN_FRAG = `uniform sampler2D tSrc;
uniform sampler2D tPrev;
uniform vec2 uScale;
uniform ivec2 uSrcMax;
uniform float uW;
void main() {
	vec2 o = floor( gl_FragCoord.xy );
	vec2 a = o * uScale, b = a + uScale;
	vec4 sum = vec4( 0.0 );
	float wsum = 0.0;
	for ( int j = 0; j < 4; j ++ ) {
		float y = floor( a.y ) + float( j );
		if ( y >= b.y ) break;
		float wy = min( b.y, y + 1.0 ) - max( a.y, y );
		for ( int i = 0; i < 4; i ++ ) {
			float x = floor( a.x ) + float( i );
			if ( x >= b.x ) break;
			float w = ( min( b.x, x + 1.0 ) - max( a.x, x ) ) * wy;
			sum += w * texelFetch( tSrc, min( ivec2( x, y ), uSrcMax ), 0 );
			wsum += w;
		}
	}
	vec4 c = sum / max( wsum, 1e-6 );
	if ( uW < 1.0 ) c = mix( texelFetch( tPrev, ivec2( o ), 0 ), c, uW );
	gl_FragColor = c;
}`;
const BLIT_FRAG = `uniform sampler2D tSrc;
void main() { gl_FragColor = texelFetch( tSrc, ivec2( floor( gl_FragCoord.xy ) ), 0 ); }`;

function fsMaterial(frag, uniforms) {
  return new THREE.ShaderMaterial({
    vertexShader: FS_VERT, fragmentShader: frag, uniforms,
    depthTest: false, depthWrite: false, blending: THREE.NoBlending, toneMapped: false,
  });
}

// ------------------------------------------------------------------------------------ Picture
export class Picture {
  constructor(stage) {
    this.stage = stage;
    const R = (this.R = stage.renderer), gl = R.getContext();
    this.device = stage.quality.low ? 'phone' : 'desktop';
    const ch = pictureChoice();
    this.mode = ch.mode;
    this.forced = ch.forced;
    // capabilities
    const vp = gl.getParameter(gl.MAX_VIEWPORT_DIMS);
    this.caps = {
      maxSamples: R.capabilities.maxSamples || 0,
      maxSize: Math.min(R.capabilities.maxTextureSize, gl.getParameter(gl.MAX_RENDERBUFFER_SIZE), vp[0], vp[1]),
      aniso: R.capabilities.getMaxAnisotropy(),
      canvasSamples: gl.getParameter(gl.SAMPLES) | 0,
      halfFloat: R.extensions.has('EXT_color_buffer_float') || R.extensions.has('EXT_color_buffer_half_float'),
    };
    // full-screen passes (their own scene: a single triangle)
    this.fsCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    const tri = new THREE.BufferGeometry();
    tri.setAttribute('position', new THREE.Float32BufferAttribute([-1, -1, 0, 3, -1, 0, -1, 3, 0], 3));
    this.fsMesh = new THREE.Mesh(tri);
    this.fsMesh.frustumCulled = false;
    this.fsScene = new THREE.Scene();
    this.fsScene.add(this.fsMesh);
    this.down = fsMaterial(DOWN_FRAG, {
      tSrc: { value: null }, tPrev: { value: null }, uScale: { value: new THREE.Vector2(1, 1) },
      uSrcMax: { value: [0, 0] }, uW: { value: 1 },        // ivec2: three's setter takes an array
    });
    this.blit = fsMaterial(BLIT_FRAG, { tSrc: { value: null } });
    this.rt = null;            // the multisampled supersampling target
    this.acc = [null, null];   // running-average ping-pong at the canvas resolution
    this.a = { valid: false, k: 0, N: 0, done: true, plan: null, cam: new Float64Array(32) };
    // frame bookkeeping (beginFrame: one per animation frame)
    this.frame = 0;
    this.lastMove = -1e9;
    this.extRun = 0;
    this.lastExt = -1e9;
    this.kind = 'none';        // the last render's path: direct | move | movess | still | rt
    // adaptive state + measurements (own rAF loop: rAF intervals of frames that rendered = their cost)
    this.stillPx = Infinity;   // Auto's current still pixel budget (<= the profile's)
    this.framesCap = Infinity; // Auto's current accumulation length (<= the profile's)
    this.moveSS = false;       // moving frames supersampled
    this.moveCool = 0;         // no moving supersampling before this time (after it was too slow)
    this.costs = { direct: [], move: [], movess: [], still: [], idle: [] };
    this.vsync = 1000 / 60;
    this.predicted = false;
    this.events = [];          // adaptive steps (tests / the Specs note)
    this._renders = 0;         // renders since the last tick
    this._n = 0;               // renders in all
    this._seen = 0;            // cost samples in all (the first, shader compiles and uploads, is dropped)
    this._prev = { kind: 'none', backlog: false };
    this._backlog = false;     // the last render was submitted while a measured one was still on the GPU
    this._fence = null;        // the measured render on the GPU: {sync, t0, kind}
    this._lastNow = 0;
    this._hiddenAt = -1;
    this._lines = [];
    document.addEventListener('visibilitychange', () => { this._hiddenAt = this.frame; this._fence = null; });
    const tick = (now) => { requestAnimationFrame(tick); this._tick(now); };
    requestAnimationFrame(tick);
    this.applyProfile(false);
  }

  get profile() { return PROFILES[this.device][this.mode]; }
  get adaptive() { return !!this.profile.adapt; }
  // the accumulation length / still budget in use (profile, Auto's measurements, URL overrides)
  get N() { return Math.max(0, Math.round(OV.frames ?? Math.min(this.profile.frames, this.framesCap))); }
  get pxBudget() { return OV.px ?? Math.min(this.profile.px, this.stillPx); }
  // Auto refines only once a plain frame has been measured (a software renderer must not start with a 4x frame)
  get ready() { return !this.adaptive || this.predicted || OV.frames != null; }

  // ---- settings
  setMode(mode, { remember = true } = {}) {
    if (!PICTURE_MODES.includes(mode) || mode === this.mode) return;
    this.mode = mode;
    if (remember) { try { localStorage.setItem(PICTURE_KEY, mode); } catch (e) { /* private mode: not remembered */ } }
    // Auto keeps what it measured (the calibration, its still budget); moving supersampling is re-earned per mode
    this.moveSS = false; this.moveCool = 0;
    for (const k of ['movess', 'still']) this.costs[k].length = 0;
    this.applyProfile(true);
    this.invalidate();
    this.stage.needsRender = true;
    this.syncUI();
  }

  // shadow / contact map sizes, PCSS samples and the moving pixel ratio of the profile
  applyProfile(live) {
    const st = this.stage, P = this.profile, q = st.quality;
    q.picture = this.mode;
    q.shadowMap = P.shadow;
    q.contactMap = P.contact;
    // moving pixel ratio: the device tier's (phones 1), Max keeps the full ratio
    q.dprMove = this.mode === 'max' ? q.dprMax : q.dprMoveBase;
    if (!live) return;
    const key = st.key;
    if (key && key.shadow.mapSize.x !== P.shadow) {
      key.shadow.mapSize.set(P.shadow, P.shadow);
      if (key.shadow.map) { key.shadow.map.dispose(); key.shadow.map = null; }
      st.shadowDirty = true;
    }
    if (st.contact && st.contact.size !== P.contact) { st.contact.setSize(P.contact); st.contactDirty = true; }
    if (st.shadowPlane) patchShadowMaterial(st.shadowPlane.material, P.pcss);
  }

  // Specs panel: the Auto / High / Max buttons (index.html #pictureSeg) and the status note
  bindUI(root = document) {
    const seg = root.getElementById && root.getElementById('pictureSeg');
    if (!seg) return;
    this.ui = { seg, note: root.getElementById('pictureNote') };
    for (const b of seg.querySelectorAll('button[data-picture]')) b.addEventListener('click', () => this.setMode(b.dataset.picture));
    this.syncUI();
  }
  syncUI() {
    if (!this.ui) return;
    for (const b of this.ui.seg.querySelectorAll('button[data-picture]')) b.setAttribute('aria-pressed', String(b.dataset.picture === this.mode));
    if (this.ui.note) this.ui.note.textContent = this.describe();
  }
  describe() {
    const s = this.state(), p = s.plan;
    const x = (v) => `${(+v).toFixed(2).replace(/\.?0+$/, '')}×`;
    const still = !s.N ? 'still frames as rendered' : `still frames ${p && p.S > 1 ? `${x(p.S)} supersampled, ` : ''}${s.N} passes`;
    const move = s.moveSS && p ? `moving ${x(p.S)} supersampled` : `moving ${x(s.dprMove)} pixel ratio`;
    return `${this.mode === 'auto' ? 'Auto: ' : ''}${still} · ${move} · ${s.caps.canvasSamples}× MSAA · shadows ${this.stage.quality.shadowMap}`;
  }

  // ---- the frame loop
  invalidate() { this.a.valid = false; this.a.done = false; }
  // WebGL context lost: the pending fence belongs to the dead context
  contextLost() { this._fence = null; this.invalidate(); }
  get movingInput() {
    const st = this.stage;
    return (st.interacting && st.dragged) || !!st.tween || st.camMoving;
  }
  // once per animation frame, before the render decision (Stage.applyQuality): the moving / still pixel ratio (phones:
  // dprMove while moving, dprMax after two still frames, a tap keeps it) and the refinement requests
  beginFrame() {
    const st = this.stage, q = st.quality;
    this.frame++;
    const moving = this.movingInput;
    if (moving) this.lastMove = this.frame;
    st._still = moving ? 0 : st._still + 1;
    const moveDpr = this.moveSS ? q.dprMax : q.dprMove;
    const want = moving ? moveDpr : st._still >= 2 ? q.dprMax : st.dpr;
    let changed = false;
    if (want !== st.dpr) {
      st.dpr = want;
      st.renderer.setPixelRatio(want);     // r160: setPixelRatio() re-applies setSize() itself (one buffer realloc)
      st.needsRender = true;
      this.invalidate();
      changed = true;
    }
    // still long enough and not converged: one more refinement frame (Auto: one plain frame measured first)
    if (!moving && !st.contextLost && this.N > 0) {
      if (!this.ready) { if (this._n >= 1 && !this._calibrated && this._renders === 0) st._refine = true; }
      else if (!this.a.done && this.frame - this.lastMove >= STILL_DELAY) st._refine = true;
    }
    return changed;
  }

  // ---- rendering (Stage.render): picks the path for this frame, measures it
  render() {
    const gl = this.R.getContext(), idle = !this._fence, t0 = performance.now();
    this.kind = this._path();
    this._renders++;
    this._n++;
    this._backlog = !idle;
    // Auto's start-up calibration: the second frame (the first compiles shaders and uploads textures) waited for with a
    // 1-pixel read -- a one-off stall while the loading card is still up; a fence is not reliable on every
    // implementation (SwiftShader signals it before the frame is drawn)
    if (this.adaptive && !this._calibrated && this._n >= 2) {
      this._calibrated = true;
      gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, this._px || (this._px = new Uint8Array(4)));
      this._sample(this.kind, performance.now() - t0);
      return;
    }
    // GPU completion of a frame submitted to an idle GPU = its cost (Chrome runs a frame ahead, so the rAF interval
    // after an isolated frame says nothing); the first frame (shader compiles, uploads) is not measured
    if (idle && this._n > 1 && gl.fenceSync) {
      const sync = gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE, 0);
      if (sync) { this._fence = { sync, t0, kind: this.kind, gl }; gl.flush(); this._poll(); }
    }
  }
  _poll() {
    setTimeout(() => {
      const f = this._fence;
      if (!f) return;
      const gl = f.gl;
      if (gl.isContextLost()) { this._fence = null; return; }
      if (gl.getSyncParameter(f.sync, gl.SYNC_STATUS) === gl.SIGNALED) {
        gl.deleteSync(f.sync);
        this._fence = null;
        if (!document.hidden && this._hiddenAt < this.frame - 1) this._sample(f.kind, performance.now() - f.t0);
      } else if (performance.now() - f.t0 > 120000) { gl.deleteSync(f.sync); this._fence = null; }
      else this._poll();
    }, 2);
  }

  _path() {
    const st = this.stage, R = this.R;
    const ext = st._needs;          // requested from outside this frame (a change), not just a refinement step
    st._needs = false; st._refine = false;
    if (ext) { this.extRun = this.lastExt === this.frame - 1 ? this.extRun + 1 : 1; this.lastExt = this.frame; }
    const moving = this.movingInput || st.busy || (ext && this.extRun >= 2);
    if (moving) this.lastMove = this.frame;
    const still = !moving && this.N > 0 && this.ready && this.frame - this.lastMove >= STILL_DELAY;
    if (still) {
      if (ext || !this.a.valid || this._camChanged()) this._restart();
      if (this.a.k < this.a.N) this._refineStep();
      else this._show(this.acc[(this.a.k - 1) & 1]);      // converged and nothing changed: the result again
      return 'still';
    }
    this.invalidate();
    const plan = this.moveSS && moving ? this._plan() : null;
    if (plan && plan.S > 1) {
      this._renderSS(plan, 0, 0);
      this._down(plan, null, 1, null);
      return 'movess';
    }
    if (this.caps.canvasSamples < 2 && this.caps.maxSamples >= 2) {
      // the canvas has no MSAA: through a multisampled target at the canvas size
      const p1 = this._plan(1);
      this._renderSS(p1, 0, 0);
      this._down(p1, null, 1, null);
      return 'rt';
    }
    R.setRenderTarget(null);
    R.render(st.scene, st.camera);
    return moving ? 'move' : 'direct';
  }

  // the canvas (output) size in device pixels
  _out() { return this.R.getDrawingBufferSize(this._v2 || (this._v2 = new THREE.Vector2())); }

  // supersampling plan for the current canvas: scale, target size, MSAA samples (budgets and GL limits)
  _plan(force = null) {
    const P = this.profile, cap = this.caps, o = this._out();
    const W = Math.max(1, o.x), H = Math.max(1, o.y), out = W * H;
    let S = force ?? Math.min(P.ss, Math.sqrt(Math.max(1, this.pxBudget / out)));
    S = Math.max(1, Math.min(S, cap.maxSize / W, cap.maxSize / H));
    if (force == null) { if (S > 1.94) S = 2; else if (S < 1.05) S = 1; }
    let samples = Math.min(cap.maxSamples, S >= 1.5 ? P.samples[1] : P.samples[0]);
    const mem = P.mem;
    while (samples > 2 && rtBytes(out * S * S, samples) > mem) samples >>= 1;
    while (S > 1 && rtBytes(out * S * S, samples) > mem) S = Math.max(1, S * 0.9);
    const w = Math.max(1, Math.round(W * S)), h = Math.max(1, Math.round(H * S));
    return { S, W, H, w, h, samples, sx: w / W, sy: h / H, bytes: rtBytes(w * h, samples) };
  }

  _ensureRT(plan) {
    let rt = this.rt;
    if (rt && rt.width === plan.w && rt.height === plan.h && rt.samples === plan.samples) return rt;
    if (rt) rt.dispose();
    rt = this.rt = new THREE.WebGLRenderTarget(plan.w, plan.h, {
      samples: plan.samples, type: THREE.UnsignedByteType, depthBuffer: true, stencilBuffer: false,
      minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter, generateMipmaps: false,
    });
    // the canvas' pipeline into the target: tone mapping + sRGB encoding in the shaders (an 'XR' target), RGBA8 storage
    rt.isXRRenderTarget = true;
    rt.texture.colorSpace = THREE.SRGBColorSpace;
    rt.texture.internalFormat = 'RGBA8';
    return rt;
  }

  _ensureAcc(W, H) {
    for (let i = 0; i < 2; i++) {
      const a = this.acc[i];
      if (a && a.width === W && a.height === H) continue;
      if (a) a.dispose();
      const t = new THREE.WebGLRenderTarget(W, H, {
        type: this.caps.halfFloat ? THREE.HalfFloatType : THREE.UnsignedByteType, depthBuffer: false, stencilBuffer: false,
        minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter, generateMipmaps: false,
      });
      this.acc[i] = t;
    }
  }

  // render the scene into the supersampling target, jittered by (jx, jy) output pixels
  _renderSS(plan, jx, jy) {
    const st = this.stage, R = this.R, cam = st.camera, rt = this._ensureRT(plan);
    const e = cam.projectionMatrix.elements, keep = [e[8], e[9], e[12], e[13]];
    if (jx || jy) {
      if (cam.isPerspectiveCamera) { e[8] -= 2 * jx / plan.W; e[9] -= 2 * jy / plan.H; } else { e[12] += 2 * jx / plan.W; e[13] += 2 * jy / plan.H; }
      cam.projectionMatrixInverse.copy(cam.projectionMatrix).invert();
    }
    // pixel-sized effects at the target's scale: grid line width, construction-line weight
    const g = st.grid && st.grid.material.uniforms.uPx;
    if (g) g.value = Math.sqrt(plan.sx * plan.sy);
    const lines = this._scaleLines(Math.sqrt(plan.sx * plan.sy));
    R.setRenderTarget(rt);
    R.render(st.scene, cam);
    R.setRenderTarget(null);
    for (const [m, op] of lines) m.opacity = op;
    if (g) g.value = 1;
    if (jx || jy) {
      e[8] = keep[0]; e[9] = keep[1]; e[12] = keep[2]; e[13] = keep[3];
      cam.projectionMatrixInverse.copy(cam.projectionMatrix).invert();
    }
  }
  // 1 px lines in a target S times finer cover 1 / S of an output pixel: their opacity x S (capped at 1)
  _scaleLines(s) {
    const out = this._lines;
    out.length = 0;
    if (s <= 1.001) return out;
    this.stage.scene.traverseVisible((o) => {
      if (!o.isLine || !o.material || Array.isArray(o.material)) return;
      const m = o.material;
      if (out.some(([x]) => x === m)) return;
      out.push([m, m.opacity]);
      if (m.transparent) m.opacity = Math.min(1, m.opacity * s);
    });
    return out;
  }

  // box-filter the target into `dst` (null = the canvas), blended with `prev` by weight w
  _down(plan, dst, w, prev) {
    const R = this.R, u = this.down.uniforms;
    u.tSrc.value = this.rt.texture;
    u.tPrev.value = prev ? prev.texture : null;
    u.uScale.value.set(plan.sx, plan.sy);
    u.uSrcMax.value = [plan.w - 1, plan.h - 1];
    u.uW.value = prev ? w : 1;
    this._fs(this.down, dst);
  }
  _show(src) {
    this.blit.uniforms.tSrc.value = src.texture;
    this._fs(this.blit, null);
  }
  _fs(mat, dst) {
    const R = this.R, info = R.info, auto = info.autoReset;
    info.autoReset = false;               // keep the scene's draw statistics (viewer.perf())
    this.fsMesh.material = mat;
    R.setRenderTarget(dst);
    R.render(this.fsScene, this.fsCam);
    R.setRenderTarget(null);
    info.autoReset = auto;
  }

  _camSig() {
    const c = this.stage.camera, s = this._sig || (this._sig = new Float64Array(32));
    c.updateMatrixWorld();
    s.set(c.matrixWorld.elements, 0); s.set(c.projectionMatrix.elements, 16);
    return s;
  }
  _camChanged() {
    const s = this._camSig(), a = this.a.cam;
    for (let i = 0; i < 32; i++) if (Math.abs(s[i] - a[i]) > 1e-9) return true;
    return false;
  }
  _restart() {
    const a = this.a, plan = this._plan(), o = this._out();
    a.plan = plan; a.k = 0; a.N = Math.max(1, this.N); a.valid = true; a.done = false;
    a.cam.set(this._camSig());
    this._ensureAcc(o.x, o.y);
  }
  // one accumulation step: frame k jittered by Halton (2, 3) within one target pixel (k = 0: centred)
  _refineStep() {
    const a = this.a, plan = a.plan, k = a.k;
    const jx = k ? (halton(k, 2) - 0.5) / plan.sx : 0, jy = k ? (halton(k, 3) - 0.5) / plan.sy : 0;
    PCSS_U.uPcssFrame.value = k;
    this._renderSS(plan, jx, jy);
    PCSS_U.uPcssFrame.value = 0;
    const dst = this.acc[k & 1], prev = k ? this.acc[(k - 1) & 1] : null;
    this._down(plan, dst, 1 / (k + 1), prev);
    this._show(dst);
    a.k = k + 1;
    if (a.k >= a.N) a.done = true;
  }

  // ---- measurements.  Own rAF callback (after main.js' frame()): an interval between two frames without a render (and
  // nothing on the GPU) is the refresh period; between back-to-back renders submitted while the GPU was still busy
  // with an earlier one, the throughput cost of a frame.  Isolated frames are measured by their fence (render()).
  _tick(now) {
    const dt = now - this._lastNow;
    this._lastNow = now;
    const kind = this._renders > 0 ? this.kind : 'idle', backlog = this._renders > 0 && this._backlog;
    this._renders = 0;
    const prev = this._prev;
    this._prev = { kind, backlog };
    if (this._hiddenAt >= this.frame - 1 || document.hidden || !(dt > 0) || dt > 60000) return;
    if (prev.kind === 'idle' && kind === 'idle') {
      if (this._fence) return;
      const c = this.costs.idle;
      c.push(dt); if (c.length > 40) c.shift();
      const sorted = c.slice().sort((x, y) => x - y);
      this.vsync = Math.min(34, Math.max(5, sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * 0.25))]));
    } else if (prev.kind !== 'idle' && prev.kind !== 'none' && kind !== 'idle' && prev.backlog) this._sample(prev.kind, dt);
  }
  _sample(kind, ms) {
    this._seen++;
    const c = this.costs[kind];
    if (!c) return;
    c.push(ms); if (c.length > 12) c.shift();
    if (this.adaptive || this.profile.moveSS) this._adapt(kind);
  }

  _log(what) {
    this.events.push({ t: Math.round(performance.now()), frame: this.frame, what });
    if (this.events.length > 50) this.events.shift();
    this.syncUI();
  }

  // Auto: step the still budget / accumulation / moving ratio by the measured costs; Auto and Max: moving
  // supersampling when a supersampled frame fits in the refresh
  _adapt(kind) {
    const v = this.vsync, q = this.stage.quality, P = this.profile, C = this.costs, now = performance.now();
    const auto = this.adaptive;
    if (kind === 'direct' || kind === 'move') {
      const c = C[kind];
      // startup prediction from a plain frame: very slow devices (software rendering) skip the refinement entirely
      if (auto && !this.predicted && c.length >= 1) {
        this.predicted = true;
        const c0 = Math.min(...c), o = this._out(), out = o.x * o.y;
        if (c0 > 400) { this.framesCap = 0; this._log(`frame ${Math.round(c0)} ms: no still refinement`); }
        else if (c0 > 120) { this.framesCap = Math.min(this.framesCap, 4); this.stillPx = out; this._log(`frame ${Math.round(c0)} ms: 1x, 4 passes`); }
        else if (c0 > 1.3 * v) {
          // fragment-bound guess: a supersampled frame costs c0 x its pixel ratio; aim at 45 ms
          this.stillPx = Math.max(out, out * 45 / c0);
          this._log(`frame ${Math.round(c0)} ms: still budget ${(this.stillPx / 1e6).toFixed(1)} MP`);
        }
      }
      if (auto && kind === 'move' && c.length >= 6) {
        const m = median(c.slice(-6)), lo = Math.min(1, q.dprMax);
        if (m > 1.6 * v + 4 && q.dprMove > lo && now > (this._moveStepAt || 0) + 1000) {
          q.dprMove = Math.max(lo, Math.round(q.dprMove * 0.8 * 100) / 100);
          this._moveStepAt = now; this._moveDownAt = now; c.length = 0;
          this._log(`moving ${Math.round(m)} ms: pixel ratio ${q.dprMove}`);
        } else if (m < 1.1 * v && q.dprMove < q.dprMax && now > (this._moveStepAt || 0) + 3000 && now > (this._moveDownAt || 0) + 10000) {
          q.dprMove = Math.min(q.dprMax, Math.round(q.dprMove * 1.25 * 100) / 100);
          this._moveStepAt = now; c.length = 0;
          this._log(`moving ${Math.round(m)} ms: pixel ratio ${q.dprMove}`);
        }
      }
    } else if (kind === 'still') {
      const c = C.still;
      if (c.length < 3) return;
      const m = median(c.slice(-5)), plan = this.a.plan, o = this._out(), out = o.x * o.y;
      if (auto) {
        if (m > Math.max(2.5 * v, 45)) {
          if (plan && plan.S > 1.01) {
            this.stillPx = Math.max(out, plan.w * plan.h * Math.max(0.3, 40 / m));
            this._log(`still ${Math.round(m)} ms: budget ${(this.stillPx / 1e6).toFixed(1)} MP`);
          } else if (m > 400) { this.framesCap = 0; this._log(`still ${Math.round(m)} ms: no refinement`); }
          else if (m > 150) { this.framesCap = Math.max(4, Math.floor(Math.min(this.framesCap, P.frames) / 2)); this._log(`still ${Math.round(m)} ms: ${this.framesCap} passes`); }
          c.length = 0;
        } else if (m < 1.2 * v && this.stillPx < P.px) {
          this.stillPx = Math.min(P.px, (plan ? plan.w * plan.h : out) * 1.5);
          c.length = 0;
          this._log(`still ${Math.round(m)} ms: budget ${(this.stillPx / 1e6).toFixed(1)} MP`);
        }
      }
      // supersampled frames within the refresh: also while moving (Auto, Max)
      if (P.moveSS && !this.moveSS && plan && plan.S > 1 && plan.S <= P.moveSS && m < (auto ? 0.8 : 1.0) * v && now > this.moveCool && q.dprMove >= q.dprMax) {
        this.moveSS = true;
        this._log(`still ${Math.round(m)} ms: moving frames supersampled`);
      }
    } else if (kind === 'movess') {
      const c = C.movess;
      if (c.length >= 4 && median(c.slice(-4)) > 1.3 * v + 2) {
        this.moveSS = false; this.moveCool = now + 10000; c.length = 0;
        this._log('moving supersampling too slow: off');
      }
    }
  }

  // anisotropic, trilinear filtering on every texture of a subtree (the GLB's page atlas)
  filterTextures(root) {
    const done = new Set(), A = this.caps.aniso;
    root.traverse((o) => {
      const mats = o.material ? (Array.isArray(o.material) ? o.material : [o.material]) : [];
      for (const m of mats) {
        for (const k of Object.keys(m)) {
          const t = m[k];
          if (!t || !t.isTexture || done.has(t) || t.isRenderTargetTexture || t.isDataTexture) continue;
          done.add(t);
          t.anisotropy = A;
          t.minFilter = THREE.LinearMipmapLinearFilter;
          t.magFilter = THREE.LinearFilter;
          t.generateMipmaps = true;
          t.needsUpdate = true;
        }
      }
    });
    this.textures = [...done].map((t) => ({ name: t.name, w: t.image && t.image.width, h: t.image && t.image.height, anisotropy: t.anisotropy, mipmaps: t.generateMipmaps }));
    return this.textures;
  }

  // everything a test or the Specs note needs
  state() {
    const a = this.a, st = this.stage, o = this._out(), q = st.quality;
    const plan = a.plan || this._plan();
    return {
      mode: this.mode, forced: this.forced, device: this.device, adaptive: this.adaptive, path: this.kind,
      k: a.k, N: this.N, done: this.N === 0 || (a.done && a.valid), valid: a.valid,
      out: [o.x, o.y], plan: { S: plan.S, w: plan.w, h: plan.h, samples: plan.samples, bytes: plan.bytes },
      rt: this.rt ? { w: this.rt.width, h: this.rt.height, samples: this.rt.samples } : null,
      acc: this.acc[0] ? { w: this.acc[0].width, h: this.acc[0].height, type: this.acc[0].texture.type } : null,
      budget: { px: this.pxBudget, mem: this.profile.mem, frames: this.profile.frames },
      moveSS: this.moveSS, dpr: st.dpr, dprMax: q.dprMax, dprMove: q.dprMove,
      vsync: Math.round(this.vsync * 10) / 10,
      cost: Object.fromEntries(Object.entries(this.costs).map(([k, c]) => [k, c.length ? Math.round(median(c)) : null])),
      caps: { ...this.caps }, textures: this.textures || [], events: this.events.slice(-12),
      shadowMap: st.key ? st.key.shadow.mapSize.x : null, contactMap: st.contact ? st.contact.size : null,
    };
  }

  dispose() {
    if (this.rt) this.rt.dispose();
    for (const a of this.acc) if (a) a.dispose();
    this.rt = null; this.acc = [null, null];
    this.invalidate();
  }
}
