// Picture quality (owner 2026-10-03: "smoother curves, edges and a sharper, crisper picture"): the render paths behind
// Stage.render(), specular anti-aliasing, texture filtering, the key light's soft shadow and the 'Picture quality'
// setting.
//
//   still canvas    once nothing moves, the canvas goes up to the screen's own pixel ratio (3 at most) as far as the
//                   profile's pixel budget allows (stillDpr: a 390 x 844 phone at 3x gets ~2.5x on Auto instead of the
//                   1.5x it has while moving), so the budget buys output resolution before supersampling; while the
//                   camera moves or the scene animates, the tier's ratio (phones 1 / 1.5).
//   still frames    once the camera and the scene have been still for STILL_DELAY frames, the scene is rendered into a
//                   multisampled render target at 1x or 2x the canvas resolution (whatever budget is left; capped by a
//                   memory budget and by MAX_TEXTURE_SIZE / MAX_RENDERBUFFER_SIZE / MAX_VIEWPORT_DIMS), box-filtered down
//                   to the canvas and accumulated over N frames jittered by Halton (2, 3) offsets within one MSAA cell
//                   (a 1 / samples share of a target pixel: the MSAA samples are n-rooks, so the jittered samples fill
//                   each output pixel evenly and the result is the box filter of a dense supersampling, not a wider tent;
//                   fractional scales would add the target pixels' own box, so still frames use 1x or 2x only).
//                   Frame 0 is unjittered, so the first supersampled frame lands where the last moving frame was (no
//                   shift); later frames only refine.
//   spinning prop   with the camera still and only the propeller's motion-blur disc animating (its blades faded into
//   (layered)       the disc, the spinner held still: PropBlur.overlay), the still frames above are rendered WITHOUT the
//                   disc -- the static scene refines and converges as usual -- and every frame shows that image with its
//                   depth (a full-screen pass writing gl_FragDepth) and draws only the disc, its root band and the
//                   turning hub on top (camera layer OVERLAY_LAYER, the canvas' own MSAA): the analytic blur keeps
//                   moving at full rate over a supersampled, converged aircraft, and each frame costs a full-screen copy
//                   and the disc instead of the 2M-triangle scene (review CR1-03; also where still refinement is off).
//   moving frames   temporal anti-aliasing (review CR1-02): each moving frame is rendered into a multisampled target at
//                   the canvas size (the canvas' 4x MSAA, Max 8x) with a sub-pixel jitter within one MSAA cell, then
//                   blended with the previous result reprojected by the camera motion (the scene is static while one
//                   orbits): the world position from the nearest depth of the 3 x 3 neighbourhood, or, where nothing
//                   wrote depth (the ground grid and shadows), the ground plane under the view ray; Catmull-Rom history
//                   samples, the history clipped to the neighbourhood's colour variance in YCoCg and its range; 15 % of
//                   the new frame, up to 60 % from a pixel of motion a frame (the history is resampled every frame).
//                   The first moving frame continues from the converged still image, so a drag starts from the
//                   supersampled picture; thin panel gaps (4 mm door outlines: sub-pixel slivers, dotted under 4x MSAA
//                   alone), stair-stepped edges and specular sparkle settle.  A cut (a preset jump) starts afresh.  On top, one supersampled pass per frame (no accumulation, up to the
//                   profile's moveSS scale, box-filtered before the temporal blend) when such a frame is predicted from
//                   the measured still passes, and then measured, to fit in the display refresh.  The same single
//                   supersampled pass (without the temporal blend: no motion vectors for moving parts) while only the
//                   scene animates and the camera is still (gear / door / explode animations: 'busyss').
//   same colours    the render targets get the canvas' exact shader output -- tone mapped (AgX + Punchy), sRGB-encoded,
//                   premultiplied alpha over a transparent clear (three r160 applies tone mapping and the output colour
//                   space to an 'XR' render target, WebGLPrograms; its RGBA8 storage is forced linear) -- and are
//                   averaged in that encoding, as the canvas' own MSAA resolve does: switching paths changes the
//                   sampling, never the colours.  Pixel-sized effects follow the scale: the ground grid's line width,
//                   the construction lines' opacity (1 px wide in the target = 1 / S of an output pixel).
//   specular AA     the GGX roughness widened by the screen-space variance of the shading normal (Tokuyoshi &
//                   Kaplanyan 2019, Filament's variance 0.15 / threshold 0.2) instead of three's additive
//                   `geometryRoughness` (max |dN| added to the roughness: it dulled every curved glossy surface by the
//                   same amount, rough or not); the roughness floor matched to the environment's base mip.
//   textures        the maximum anisotropy and trilinear mipmaps on every texture the model carries (the G3000 page
//                   atlas), and on the contact shadow (rendered at 512 while the scene animates, full size once still).
//   key shadow      percentage-closer soft shadows on the ground (the only receiver): blocker search + a Vogel-disk
//                   PCF whose radius grows with the caster's height over the floor (a softbox of KEY_ANGLE degrees),
//                   so the tyres' contact is crisp and the wing's shadow soft; the shadow camera is fitted to the
//                   posed model each time the map is rendered (Stage._fitShadow).
//   adaptive (Auto) a start-up calibration (the median of 3 plain frames, each waited for with 1-pixel reads before and
//                   after: no earlier GPU work in the sample, review PERF-1) predicts the still budget and the
//                   accumulation length; at run time real frame times (fences for isolated frames, rAF intervals while
//                   frames render back to back; idle intervals give the refresh period) step the still budget (down to
//                   the tier's ratio at 1x), the accumulation length (down to none), the phone Max moving ratio and the
//                   moving / animating supersampling, and give the passes back once plain frames fit the refresh again
//                   (a stall at start-up does not cost the session its still refinement).  Nothing goes below the
//                   pre-2026-10 picture (desktops keep the full pixel ratio while moving).
//   memory          at most two multisampled targets (the still plan and the moving plan; one when they agree), the
//                   accumulation pair, the temporal history pair; each released after RELEASE_MS without use.
//   setting         Specs panel 'Picture quality': Auto / High / Max (localStorage 'pc12-picture', try/catch);
//                   ?picture=auto|high|max, or ?quality=high|max (which also picks the desktop tier), override it
//                   without being remembered; ?movess=1|0 forces the single-pass supersampling of moving / animating
//                   frames on or off (tests, look development: a software renderer never measures it as fitting);
//                   ?taa=0 turns the temporal anti-aliasing of moving frames off, ?layer=0 the layered spinning prop.
import * as THREE from 'three';

const Q_ = new URLSearchParams(location.search);
const qn = (k) => (Q_.has(k) && Q_.get(k) !== '' && isFinite(+Q_.get(k)) ? +Q_.get(k) : undefined);

export const PICTURE_KEY = 'pc12-picture';
export const PICTURE_MODES = ['auto', 'high', 'max'];
export const STILL_DELAY = 3;          // frames the camera and the scene must be still before supersampling starts
// camera layer of the per-frame overlay drawn over a still image (the spinning propeller's blur disc, band, hub)
export const OVERLAY_LAYER = 5;

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
//   frames   accumulated still frames (N)            px / mem  the still pixel budget (canvas first, then the target's
//                                                              scale) / the still target's bytes
//   ss       the largest still scale (per axis)      samples   its MSAA samples below / from a scale of 1.5 (the
//                                                              moving target: the first)
//   moveSS   the largest single-pass supersampling scale while the camera moves (the scene animating: up to ss), used
//            only when predicted and measured to fit the refresh (0: never)
//   taa      temporal anti-aliasing of moving frames
//   adapt    still budget / accumulation / moving ratio follow measured frame times (Auto)
//   shadow   key-light shadow map; contact  contact-shadow map; pcss  [blocker search, filter] samples
// Phones on Auto keep the pre-2026-10 shadow sizes (1024 / 256: at phone sizes a 1024 map over the ~19 m shadow
// frustum is already finer than a pixel) and spend the budget on the still canvas.
export const PROFILES = {
  desktop: {
    auto: { frames: 16, px: 8.3e6, mem: 240e6, ss: 2, samples: [4, 2], moveSS: 1.5, taa: true, adapt: true, shadow: 4096, contact: 1024, pcss: [16, 32] },
    high: { frames: 16, px: 8.3e6, mem: 240e6, ss: 2, samples: [4, 2], moveSS: 1.5, taa: true, adapt: false, shadow: 4096, contact: 1024, pcss: [16, 32] },
    max: { frames: 32, px: 16.6e6, mem: 480e6, ss: 2, samples: [8, 4], moveSS: 2, taa: true, adapt: false, shadow: 4096, contact: 1024, pcss: [24, 48] },
  },
  phone: {
    auto: { frames: 8, px: 2.1e6, mem: 50e6, ss: 2, samples: [4, 2], moveSS: 0, taa: true, adapt: true, shadow: 1024, contact: 256, pcss: [8, 16] },
    high: { frames: 12, px: 3.7e6, mem: 96e6, ss: 2, samples: [4, 2], moveSS: 0, taa: true, adapt: false, shadow: 2048, contact: 512, pcss: [12, 24] },
    max: { frames: 16, px: 8.3e6, mem: 192e6, ss: 2, samples: [4, 2], moveSS: 2, taa: true, adapt: false, shadow: 2048, contact: 1024, pcss: [16, 32] },
  },
};
// ?ssframes= / ?sspx= override the accumulation length and the still pixel budget, ?movess=1|0 forces the single-pass
// supersampling of moving / animating frames on / off, ?taa=0 / ?layer=0 switch the temporal AA / the layered prop off
const OV = { frames: qn('ssframes'), px: qn('sspx'), moveSS: qn('movess'), taa: qn('taa'), layer: qn('layer') };
const PLAIN = new Set(['direct', 'move', 'rt', 'taa']);   // the paths of an unrefined frame (one plain scene render)
const RELEASE_MS = 30000;   // a render target / accumulation / history unused for this much rendering time is released
const CALIB_N = 3;          // start-up calibration: plain frames measured (their median is the prediction's frame time)
// temporal AA: weight of the new frame (a still camera / at TAA_FAST px of motion a frame and above: the second -- the
// history is resampled every frame, so the faster the image moves the less of it is kept), the history clip width
// (standard deviations), the history resampling kernel (Keys' a: -0.5 = Catmull-Rom), the jitter cycle (Halton indices
// 1 .. TAA_CYCLE).  Tuned on 8-frame orbits of 0.15 and 0.5 deg a frame against the converged still (2026-10-04):
// [0.1, 0.25] at 24 px kept too much resampled history (softer than the plain frame); sharper kernels and a display
// sharpen measured worse
const TAA_ALPHA = [0.15, 0.6], TAA_FAST = 1, TAA_GAMMA = 1.25, TAA_KEYS = -0.5, TAA_CYCLE = 8;
// a cut, not a motion: the view turns by more than TAA_CUT_RAD, or the eye moves by more than TAA_CUT_DIST x its distance
// to the orbit centre, or the field of view changes by more than a fifth, between the history's camera and this one
const TAA_CUT_RAD = 0.35, TAA_CUT_DIST = 0.3;

// still target bytes: colour + depth per MSAA sample, plus the resolved colour and depth
const rtBytes = (px, samples) => px * (8 * Math.max(1, samples) + 8);
const halton = (i, b) => { let f = 1, r = 0; while (i > 0) { f /= b; r += f * (i % b); i = Math.floor(i / b); } return r; };
const median = (a) => { if (!a.length) return NaN; const s = a.slice().sort((x, y) => x - y); return s[s.length >> 1]; };

// ------------------------------------------------------------------------------------ specular anti-aliasing
// Installed once into three's shader chunks (every MeshStandard / MeshPhysicalMaterial, no per-material patch).
// floor: the smallest roughness, the base mip of the prefiltered environment (three's 0.0525 is a 256 px face, the 1k
// studio HDRI's; a 2k one makes a 512 px face: 1 / (1.16 sqrt(512)) = 0.038, cube_uv_reflection_fragment's roughnessToMip).
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
//   uPcssFrame  the accumulation / temporal frame: turns the per-pixel rotation of the sample disc (noise averages out)
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
const DOWN_FRAG = `uniform highp sampler2D tSrc;
uniform highp sampler2D tPrev;
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
const BLIT_FRAG = `uniform highp sampler2D tSrc;
void main() { gl_FragColor = texelFetch( tSrc, ivec2( floor( gl_FragCoord.xy ) ), 0 ); }`;
// the still image and its depth (the static scene's, at the target's scale) onto the canvas, for the overlay's depth test
const COMPOSE_FRAG = `uniform highp sampler2D tSrc;
uniform highp sampler2D tDepth;
uniform vec2 uDScale;
uniform ivec2 uDMax;
void main() {
	vec2 o = floor( gl_FragCoord.xy );
	gl_FragColor = texelFetch( tSrc, ivec2( o ), 0 );
	gl_FragDepth = texelFetch( tDepth, min( ivec2( ( o + 0.5 ) * uDScale ), uDMax ), 0 ).r;
}`;
// temporal AA: the current (jittered, multisampled) frame blended with the history reprojected through the depth
// buffer (camera motion), the history clipped to the current 3 x 3 neighbourhood's colour variance (YCoCg + alpha)
const TAA_FRAG = `uniform highp sampler2D tCur;
uniform highp sampler2D tDepth;
uniform highp sampler2D tHist;
uniform mat4 uInvVP;       // NDC of this frame -> world (unjittered)
uniform mat4 uHistVP;      // world -> clip space of the history's camera (unjittered)
uniform float uGround;     // the ground's height: the ground grid and shadows write no depth
uniform vec2 uOut;         // output size (px)
uniform vec2 uDScale;      // depth texels per output pixel
uniform ivec2 uDMax;
uniform vec2 uHist;        // history size (px)
uniform vec2 uAlpha;       // weight of the new frame: still / at uFast px of motion and above
uniform float uFast;
uniform float uGamma;
uniform float uValid;      // 0: no history
uniform float uKeys;
vec3 pcYCoCg( vec3 c ) { return vec3( 0.25 * c.r + 0.5 * c.g + 0.25 * c.b, 0.5 * c.r - 0.5 * c.b, -0.25 * c.r + 0.5 * c.g - 0.25 * c.b ); }
vec3 pcRGB( vec3 c ) { return vec3( c.x + c.y - c.z, c.x + c.z, c.x - c.y - c.z ); }
// bicubic history sample (Keys' kernel, uKeys: -0.5 = Catmull-Rom, sharper below) in 5 bilinear taps (the 4 x 4
// kernel's corners dropped)
vec4 pcHist( vec2 uv ) {
	vec2 p = uv * uHist, tc = floor( p - 0.5 ) + 0.5, f = p - tc, f2 = f * f, f3 = f2 * f;
	float a = uKeys;
	vec2 w0 = a * ( f3 - 2.0 * f2 + f );
	vec2 w1 = ( a + 2.0 ) * f3 - ( a + 3.0 ) * f2 + 1.0;
	vec2 w2 = -( a + 2.0 ) * f3 + ( 2.0 * a + 3.0 ) * f2 - a * f;
	vec2 w3 = a * ( f2 - f3 );
	vec2 w12 = w1 + w2, t12 = ( tc + w2 / w12 ) / uHist, t0 = ( tc - 1.0 ) / uHist, t3 = ( tc + 2.0 ) / uHist;
	vec4 s = texture2D( tHist, vec2( t12.x, t0.y ) ) * ( w12.x * w0.y ) + texture2D( tHist, vec2( t0.x, t12.y ) ) * ( w0.x * w12.y )
		+ texture2D( tHist, t12 ) * ( w12.x * w12.y ) + texture2D( tHist, vec2( t3.x, t12.y ) ) * ( w3.x * w12.y )
		+ texture2D( tHist, vec2( t12.x, t3.y ) ) * ( w12.x * w3.y );
	float ws = w12.x * w0.y + w0.x * w12.y + w12.x * w12.y + w3.x * w12.y + w12.x * w3.y;
	return clamp( s / ws, 0.0, 1.0 );
}
void main() {
	ivec2 o = ivec2( floor( gl_FragCoord.xy ) ), mx = ivec2( uOut ) - 1;
	vec4 c = texelFetch( tCur, o, 0 );
	vec4 m1 = vec4( 0.0 ), m2 = vec4( 0.0 ), lo = vec4( 1.0 ), hi = vec4( 0.0 );
	float dz = 1.0;
	vec2 dp = vec2( o );
	for ( int j = -1; j <= 1; j ++ ) for ( int i = -1; i <= 1; i ++ ) {
		ivec2 q = clamp( o + ivec2( i, j ), ivec2( 0 ), mx );
		vec4 s = texelFetch( tCur, q, 0 );
		vec4 y = vec4( pcYCoCg( s.rgb ), s.a );
		m1 += y; m2 += y * y; lo = min( lo, s ); hi = max( hi, s );
		float d = texelFetch( tDepth, min( ivec2( ( vec2( q ) + 0.5 ) * uDScale ), uDMax ), 0 ).r;
		if ( d < dz ) { dz = d; dp = vec2( q ); }
	}
	if ( uValid < 0.5 ) { gl_FragColor = c; return; }
	// motion of the nearest surface in the neighbourhood (edges move with the object in front); where nothing wrote
	// depth, the ground plane under the view ray (the grid, the contact and key shadows), else the far plane
	vec2 uvd = ( dp + 0.5 ) / uOut, nd = uvd * 2.0 - 1.0;
	vec4 wp = uInvVP * vec4( nd, dz * 2.0 - 1.0, 1.0 );
	wp /= wp.w;
	if ( dz >= 1.0 ) {
		vec4 a = uInvVP * vec4( nd, -1.0, 1.0 ), b = uInvVP * vec4( nd, 1.0, 1.0 );
		a /= a.w; b /= b.w;
		float t = ( uGround - a.y ) / ( b.y - a.y );
		if ( t > 0.0 && t < 1.0 ) wp = vec4( mix( a.xyz, b.xyz, t ), 1.0 );
	}
	vec4 pc = uHistVP * wp;
	vec2 mv = ( pc.w > 1e-6 ? pc.xy / pc.w * 0.5 + 0.5 : uvd ) - uvd;
	vec2 uvh = ( vec2( o ) + 0.5 ) / uOut + mv;
	if ( pc.w <= 1e-6 || any( lessThan( uvh, vec2( 0.0 ) ) ) || any( greaterThan( uvh, vec2( 1.0 ) ) ) ) { gl_FragColor = c; return; }
	vec4 h = pcHist( uvh );
	vec4 hy = vec4( pcYCoCg( h.rgb ), h.a );
	vec4 mu = m1 / 9.0, sd = sqrt( max( m2 / 9.0 - mu * mu, 0.0 ) );
	vec4 ext = uGamma * sd + 1.0 / 512.0, v = hy - mu, u = abs( v ) / ext;
	float k = max( max( u.x, u.y ), max( u.z, u.w ) );
	if ( k > 1.0 ) hy = mu + v / k;
	h = clamp( vec4( pcRGB( hy.xyz ), hy.w ), lo, hi );
	float a = mix( uAlpha.x, uAlpha.y, clamp( length( mv * uOut ) / uFast, 0.0, 1.0 ) );
	gl_FragColor = clamp( mix( h, c, a ), 0.0, 1.0 );
}`;

function fsMaterial(frag, uniforms, extra = {}) {
  return new THREE.ShaderMaterial({
    vertexShader: FS_VERT, fragmentShader: frag, uniforms,
    depthTest: false, depthWrite: false, blending: THREE.NoBlending, toneMapped: false, ...extra,
  });
}
function colourTarget(W, H, halfFloat, linear) {
  const f = linear ? THREE.LinearFilter : THREE.NearestFilter;
  return new THREE.WebGLRenderTarget(W, H, {
    type: halfFloat ? THREE.HalfFloatType : THREE.UnsignedByteType, depthBuffer: false, stencilBuffer: false,
    minFilter: f, magFilter: f, generateMipmaps: false,
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
    // a software renderer (SwiftShader, llvmpipe, WARP): its fences signal before the frame is drawn, so measured pass
    // costs cannot earn the single-pass supersampling there
    let renderer = '';
    try {
      const dbg = gl.getExtension('WEBGL_debug_renderer_info');
      renderer = String(gl.getParameter(dbg ? dbg.UNMASKED_RENDERER_WEBGL : gl.RENDERER) || '');
    } catch (e) { renderer = ''; }
    this.caps = {
      renderer, software: /swiftshader|llvmpipe|softpipe|software|basic render|microsoft basic/i.test(renderer),
      webgl2: !!R.capabilities.isWebGL2,
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
    // writes the depth too: the depth test on with ALWAYS (a disabled test writes no depth)
    this.compose = fsMaterial(COMPOSE_FRAG, {
      tSrc: { value: null }, tDepth: { value: null }, uDScale: { value: new THREE.Vector2(1, 1) }, uDMax: { value: [0, 0] },
    }, { depthTest: true, depthWrite: true, depthFunc: THREE.AlwaysDepth });
    this.taaMat = fsMaterial(TAA_FRAG, {
      tCur: { value: null }, tDepth: { value: null }, tHist: { value: null }, uInvVP: { value: new THREE.Matrix4() },
      uHistVP: { value: new THREE.Matrix4() }, uGround: { value: 0 },
      uOut: { value: new THREE.Vector2(1, 1) }, uDScale: { value: new THREE.Vector2(1, 1) }, uDMax: { value: [0, 0] },
      uHist: { value: new THREE.Vector2(1, 1) }, uAlpha: { value: new THREE.Vector2(TAA_ALPHA[0], TAA_ALPHA[1]) },
      uFast: { value: TAA_FAST }, uGamma: { value: TAA_GAMMA }, uValid: { value: 0 }, uKeys: { value: TAA_KEYS },
    });
    // the temporal AA's settings (look development may change them on a live page; jitter: x the MSAA cell)
    this.taaP = { alpha: TAA_ALPHA.slice(), fast: TAA_FAST, gamma: TAA_GAMMA, keys: TAA_KEYS, jitter: 1 };
    this.pool = [];            // multisampled targets (with depth textures), least recently used first, at most 2
    this.rt = null;            // the target of the last scene pass
    this.acc = [null, null];   // running-average ping-pong at the canvas resolution
    this.a = { valid: false, k: 0, N: 0, done: true, plan: null, cam: new Float64Array(32), layered: false, rt: null };
    // temporal AA: history ping-pong (canvas size), the box-filtered supersampled frame, the history's camera, the seed
    // (the still image the first moving frame continues from)
    const pose = () => ({ pos: new THREE.Vector3(), dir: new THREE.Vector3(0, 0, -1), fov: 0 });
    this.taa = { rt: [null, null], i: 0, valid: false, vp: new THREE.Matrix4(), pose: pose(), seed: null, k: 0, frames: 0, cuts: 0, last: null };
    this._pose = pose();
    this.cur = null;
    this.allowTaa = true;
    this._vpm = new THREE.Matrix4();
    this._used = { acc: 0, hist: 0, cur: 0 };
    // frame bookkeeping (beginFrame: one per animation frame)
    this.frame = 0;
    this.lastMove = -1e9;
    this.extRun = 0;
    this.lastExt = -1e9;
    this.kind = 'none';        // the last render's path: direct | move | taa | movess | busyss | still | layer | shown | rt
    // adaptive state + measurements (own rAF loop: rAF intervals of frames that rendered = their cost)
    this.stillPx = Infinity;   // Auto's current still pixel budget (<= the profile's)
    this.framesCap = Infinity; // Auto's current accumulation length (<= the profile's)
    this.moveSS = false;       // moving frames supersampled (camera moving)
    this.moveCool = 0;         // no moving supersampling before this time (after it was too slow)
    this.busySS = false;       // animating frames supersampled (camera still, the scene moving: gear, doors)
    this.busyCool = 0;
    this.costs = { direct: [], move: [], taa: [], movess: [], busyss: [], still: [], layer: [], shown: [], rt: [], idle: [] };
    this.vsync = 1000 / 60;
    this.predicted = false;
    this.events = [];          // adaptive steps (tests / the Specs note)
    this._calib = [];          // start-up calibration samples (ms)
    this._cutAt = -1e9;        // when Auto last cut the passes (framesCap); _restored: how often they came back
    this._restored = 0;
    this._predictCut = false;  // the start-up prediction lowered the still budget
    this._gcAt = 0;
    this._renders = 0;         // renders since the last tick
    this._n = 0;               // renders in all
    this._seen = 0;            // cost samples in all
    this._prev = { kind: 'none', backlog: false };
    this._backlog = false;     // the last render was submitted while a measured one was still on the GPU
    this._fence = null;        // the measured render on the GPU: {sync, t0, kind}
    this._lastNow = 0;
    this._hiddenAt = -1;
    this._lines = [];
    this._lights = null;
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
  // Auto refines only once plain frames have been measured (a software renderer must not start with a 4x frame)
  get ready() { return !this.adaptive || this.predicted || OV.frames != null; }
  // temporal AA of moving frames (WebGL2: multisampled targets with depth textures, texelFetch)
  // (allowTaa: tests compare against the plain moving frame on the same page)
  get taaOn() { return this.allowTaa && this.caps.webgl2 && this.caps.maxSamples >= 2 && (OV.taa != null ? OV.taa > 0 : !!this.profile.taa); }
  // the canvas' CSS pixels, and the still budget's floor: the tier's pixel ratio at 1x
  get cssPx() { return Math.max(1, this.stage.size.w * this.stage.size.h); }
  get floorPx() { const d = this.stage.quality.dprMax; return this.cssPx * d * d; }
  // the still canvas' pixel ratio: up to the screen's own (QUALITY.dprNative, 3 at most) within the pixel budget, in
  // steps of 0.05; the tier's ratio (dprMax) until Auto has calibrated, without still refinement, and below it
  stillDpr() {
    const q = this.stage.quality, lo = q.dprMax, hi = Math.max(lo, q.dprNative || lo);
    if (hi - lo < 0.01 || !this.ready || this.N === 0) return lo;
    const r = Math.floor(Math.sqrt(this.pxBudget / this.cssPx) * 20) / 20;
    return Math.max(lo, Math.min(hi, r));
  }

  // ---- settings
  setMode(mode, { remember = true } = {}) {
    if (!PICTURE_MODES.includes(mode) || mode === this.mode) return;
    this.mode = mode;
    if (remember) { try { localStorage.setItem(PICTURE_KEY, mode); } catch (e) { /* private mode: not remembered */ } }
    // Auto keeps what it measured (the calibration, its still budget); moving supersampling is re-earned per mode
    this.moveSS = false; this.moveCool = 0; this.busySS = false; this.busyCool = 0;
    for (const k of ['movess', 'busyss', 'still']) this.costs[k].length = 0;
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
  // plain language (review UX-1): what the setting does on this device
  describe() {
    const s = this.state(), p = s.plan, auto = this.mode === 'auto';
    const x = (v) => `${(+v).toFixed(2).replace(/\.?0+$/, '')}×`;
    const out = [];
    if (!s.N) out.push(auto ? 'This device draws the picture as it is (too slow for extra sharpening passes)' : 'The picture is shown as drawn');
    else {
      const how = [`${s.N} passes`];
      if (s.dprStill > s.dprMax + 0.01) how.push(`${x(s.dprStill)} screen resolution`);
      if (p && p.S > 1) how.push(`${x(p.S)} supersampled`);
      out.push(`Sharpens the image when you stop moving (${how.join(', ')})`);
    }
    const mv = [];
    if (s.taa) mv.push('edges smoothed over successive frames');
    if (s.moveSS) mv.push('supersampled');
    if (s.dprMove < s.dprMax - 0.01) mv.push('lighter resolution, to keep it fluid');
    out.push(mv.length ? `while moving: ${mv.join(', ')}` : 'full resolution while moving');
    if (auto && s.N) out.push(this.reduced ? 'this device: reduced to keep it fluid' : 'this device: full quality');
    return out.join(' · ');
  }
  // Auto has cut the passes or the still budget below the profile's
  get reduced() {
    const P = this.profile;
    return this.adaptive && (Math.min(P.frames, this.framesCap) < P.frames || this.stillPx < P.px);
  }

  // ---- the frame loop
  invalidate() { this.a.valid = false; this.a.done = false; }
  // WebGL context lost: the pending fence belongs to the dead context; every target with it
  contextLost() {
    this._fence = null;
    this.invalidate();
    this.taa.valid = false; this.taa.seed = null;
  }
  get movingInput() {
    const st = this.stage;
    return (st.interacting && st.dragged) || !!st.tween || st.camMoving;
  }
  // the overlay animating over a still image (the spinning propeller's blur: Stage.overlay, set by main.js), or null
  get overlay() {
    const o = this.stage.overlay;
    return o && o.length && OV.layer !== 0 ? o : null;
  }
  // once per animation frame, before the render decision (Stage.applyQuality): the moving / still pixel ratio (phones:
  // dprMove while moving, the still ratio after two still frames, a tap keeps it; the tier's ratio while the scene
  // animates) and the refinement requests
  beginFrame() {
    const st = this.stage, q = st.quality;
    this.frame++;
    const moving = this.movingInput;
    if (moving) this.lastMove = this.frame;
    st._still = moving ? 0 : st._still + 1;
    const moveDpr = this.moveSS || OV.moveSS === 1 ? q.dprMax : q.dprMove;
    const want = moving ? moveDpr : st._still >= 2 ? (st.busy ? q.dprMax : this.stillDpr()) : st.dpr;
    let changed = false;
    if (want !== st.dpr) {
      st.dpr = want;
      st.renderer.setPixelRatio(want);     // r160: setPixelRatio() re-applies setSize() itself (one buffer realloc)
      st.needsRender = true;
      this.invalidate();
      changed = true;
    }
    // still long enough and not converged: one more refinement frame (Auto: the calibration frames first); the layered
    // propeller refines its static image even without still refinement (one pass)
    if (!moving && !st.contextLost && (this.N > 0 || this.overlay)) {
      if (!this.ready) { if (this._n >= 1 && this._renders === 0) st._refine = true; }
      else if (!this.a.done && this.frame - this.lastMove >= STILL_DELAY) st._refine = true;
    }
    return changed;
  }

  // ---- rendering (Stage.render): picks the path for this frame, measures it
  render() {
    const gl = this.R.getContext();
    // Auto's start-up calibration (review PERF-1): plain frames 2 .. 1 + CALIB_N, each waited for with a 1-pixel read
    // BEFORE it (the GPU drained: the first frame's shadow maps, texture uploads and the program links compileAsync did
    // not cover are not in the sample) and after it; a fence is not reliable on every implementation (SwiftShader
    // signals it before the frame is drawn).  The prediction takes their median (a one-off stall in one of them does
    // not count); a frame over 3 s (software rendering) ends the calibration at once.
    const calib = this.adaptive && !this.predicted && OV.frames == null && this._n >= 1 && this._calib.length < CALIB_N;
    const px = this._px || (this._px = new Uint8Array(4));
    if (calib) gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
    const idle = !this._fence, t0 = performance.now();
    this.kind = this._path();
    this._renders++;
    this._n++;
    this._backlog = !idle;
    if (calib) {
      gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
      const ms = performance.now() - t0;
      if (PLAIN.has(this.kind)) {
        this._calib.push(ms);
        if (this._calib.length >= CALIB_N || ms > 3000) this._predict(median(this._calib));
      }
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

  // render time (ms): advances only while frames render, by at most 100 ms a frame -- a still picture looked at for a
  // while does not age the targets the next drag or animation needs (RELEASE_MS counts rendering time)
  _clock() {
    const t = performance.now(), d = this._clockAt == null ? 0 : Math.min(100, Math.max(0, t - this._clockAt));
    this._clockAt = t;
    return (this._rclock = (this._rclock || 0) + d);
  }

  _path() {
    const st = this.stage, R = this.R, now = this._clock();
    const ext = st._needs;          // requested from outside this frame (a change), not just a refinement step
    st._needs = false; st._refine = false; st._ovl = false;
    if (ext) { this.extRun = this.lastExt === this.frame - 1 ? this.extRun + 1 : 1; this.lastExt = this.frame; }
    const camMoving = this.movingInput;
    const animating = !camMoving && (st.busy || (ext && this.extRun >= 2));
    if (camMoving || animating) this.lastMove = this.frame;
    this._gc(now);
    const ovl = this.overlay;
    const settled = !camMoving && !animating && this.ready && this.frame - this.lastMove >= STILL_DELAY;
    if (settled && (this.N > 0 || ovl)) {
      const layered = !!ovl;
      if (ext || !this.a.valid || this.a.layered !== layered || this._camChanged()) this._restart(layered);
      const a = this.a, refining = a.k < a.N;
      if (refining) this._refineStep(layered ? ovl : null);
      const src = this.acc[(a.k - 1) & 1];
      if (layered) this._compose(src, ovl);
      else this._show(src);
      this._used.acc = now;
      if (layered && a.rt) a.rt._pcUsed = now;
      // the temporal history continues from this image when the camera moves again
      const seed = this._seed || (this._seed = { rt: null, vp: new THREE.Matrix4(), pose: { pos: new THREE.Vector3(), dir: new THREE.Vector3(), fov: 0 } });
      seed.rt = src; seed.vp.copy(this._vp(st.camera)); this._poseOf(st.camera, seed.pose);
      this.taa.valid = false;
      this.taa.seed = seed;
      return refining ? 'still' : layered ? 'layer' : 'shown';
    }
    this.invalidate();
    // camera moving: temporal anti-aliasing (with a supersampled pass when one fits the refresh)
    if (camMoving && this.taaOn) return this._taaFrame(now);
    this.taa.valid = false;
    // one supersampled pass, no accumulation (no ghosting): the camera moving (temporal AA off), or only the scene
    // animating (the gear, a door) -- when such a frame fits in the refresh
    const plan = camMoving ? (this._ssOn('move') ? this._ssPlan('move') : null)
      : animating ? (this._ssOn('busy') ? this._ssPlan('busy') : null) : null;
    if (plan) {
      this._renderSS(plan, 0, 0);
      this._down(plan, null, 1, null);
      return camMoving ? 'movess' : 'busyss';
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
    return camMoving || animating ? 'move' : 'direct';
  }

  // single-pass supersampling: forced by ?movess=, else earned by the measured costs (_adapt)
  _ssOn(kind) {
    if (OV.moveSS != null) return OV.moveSS > 0;
    return kind === 'move' ? this.moveSS : this.busySS;
  }
  // its scale (any value: a single pass): within the pixel budget and the profile's moving cap (camera moving) or
  // the still cap (only the scene animating); null below 1.2 (not worth a pass through the target)
  _ssScale(kind) {
    const P = this.profile, o = this._out(), out = Math.max(1, o.x * o.y);
    const capS = kind === 'move' ? P.moveSS || (OV.moveSS > 0 ? 1.5 : 0) : P.ss;
    const S = Math.min(capS, Math.sqrt(Math.max(1, this.pxBudget / out)));
    return S >= 1.2 ? S : 0;
  }
  _ssPlan(kind) {
    const S = this._ssScale(kind);
    if (!S) return null;
    const plan = this._plan(S);
    return plan.S > 1.15 ? plan : null;
  }

  // the canvas (output) size in device pixels
  _out() { return this.R.getDrawingBufferSize(this._v2 || (this._v2 = new THREE.Vector2())); }

  // supersampling plan for the current canvas: scale, target size, MSAA samples (budgets and GL limits).  Still frames
  // (no `force`) use 1x or 2x only: at a fractional scale the target pixels straddling an output pixel's edge add their
  // own box to the filter (~0.37 px at 1.26x against the box's 0.29), softer than 1x with jittered passes (CR1-04).
  _plan(force = null) {
    const P = this.profile, cap = this.caps, o = this._out();
    const W = Math.max(1, o.x), H = Math.max(1, o.y), out = W * H;
    let S = force ?? Math.min(P.ss, Math.sqrt(Math.max(1, this.pxBudget / out)));
    S = Math.max(1, Math.min(S, cap.maxSize / W, cap.maxSize / H));
    if (force == null) S = S >= 1.94 && 2 * Math.max(W, H) <= cap.maxSize ? 2 : 1;
    let samples = Math.min(cap.maxSamples, S >= 1.5 ? P.samples[1] : P.samples[0]);
    const mem = P.mem;
    while (samples > 2 && rtBytes(out * S * S, samples) > mem) samples >>= 1;
    if (force == null) { if (S > 1 && rtBytes(out * S * S, samples) > mem) { S = 1; samples = Math.min(cap.maxSamples, P.samples[0]); } }
    else while (S > 1 && rtBytes(out * S * S, samples) > mem) S = Math.max(1, S * 0.9);
    while (S === 1 && samples > 2 && rtBytes(out, samples) > mem) samples >>= 1;
    const w = Math.max(1, Math.round(W * S)), h = Math.max(1, Math.round(H * S));
    return { S, W, H, w, h, samples, sx: w / W, sy: h / H, bytes: rtBytes(w * h, samples) };
  }

  // a multisampled target for the plan, from the pool (the still and the moving plan; least recently used out)
  _target(plan) {
    const pool = this.pool;
    const i = pool.findIndex((t) => t.width === plan.w && t.height === plan.h && t.samples === plan.samples);
    let rt;
    if (i >= 0) rt = pool.splice(i, 1)[0];
    else {
      while (pool.length >= 2) this._dropTarget(pool[0]);
      rt = new THREE.WebGLRenderTarget(plan.w, plan.h, {
        samples: plan.samples, type: THREE.UnsignedByteType, depthBuffer: true, stencilBuffer: false,
        minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter, generateMipmaps: false,
      });
      // the canvas' pipeline into the target: tone mapping + sRGB encoding in the shaders (an 'XR' target), RGBA8
      // storage; the depth resolved into a texture (the layered propeller's depth test, the temporal reprojection)
      rt.isXRRenderTarget = true;
      rt.texture.colorSpace = THREE.SRGBColorSpace;
      rt.texture.internalFormat = 'RGBA8';
      rt.depthTexture = new THREE.DepthTexture(plan.w, plan.h, THREE.UnsignedIntType);
    }
    pool.push(rt);
    rt._pcUsed = this._rclock || 0;
    return (this.rt = rt);
  }
  _dropTarget(rt) {
    const i = this.pool.indexOf(rt);
    if (i >= 0) this.pool.splice(i, 1);
    // (a converged still image keeps its accumulation; the layered propeller needs the target's depth)
    if (rt === this.a.rt) { this.a.rt = null; if (this.a.layered) this.invalidate(); }
    if (rt === this.rt) this.rt = null;
    rt.dispose();
  }

  _ensureAcc(W, H) {
    for (let i = 0; i < 2; i++) {
      const a = this.acc[i];
      if (a && a.width === W && a.height === H) continue;
      if (a) a.dispose();
      // linear filtering: the temporal history samples it (between pixels) when a drag starts from the still image
      this.acc[i] = colourTarget(W, H, this.caps.halfFloat, true);
    }
  }

  // render the scene into a multisampled target for the plan, jittered by (jx, jy) output pixels; `hide`: objects
  // left out of this pass (the layered propeller's overlay)
  _renderSS(plan, jx, jy, hide = null) {
    const st = this.stage, R = this.R, cam = st.camera, rt = this._target(plan);
    const e = cam.projectionMatrix.elements, keep = [e[8], e[9], e[12], e[13]];
    if (jx || jy) {
      if (cam.isPerspectiveCamera) { e[8] -= 2 * jx / plan.W; e[9] -= 2 * jy / plan.H; } else { e[12] += 2 * jx / plan.W; e[13] += 2 * jy / plan.H; }
      cam.projectionMatrixInverse.copy(cam.projectionMatrix).invert();
    }
    // pixel-sized effects at the target's scale: grid line width, construction-line weight
    const g = st.grid && st.grid.material.uniforms.uPx;
    if (g) g.value = Math.sqrt(plan.sx * plan.sy);
    const lines = this._scaleLines(Math.sqrt(plan.sx * plan.sy));
    const vis = hide ? hide.map((o) => o.visible) : null;
    if (hide) for (const o of hide) o.visible = false;
    R.setRenderTarget(rt);
    R.render(st.scene, cam);
    R.setRenderTarget(null);
    if (hide) hide.forEach((o, i) => { o.visible = vis[i]; });
    for (const [m, op] of lines) m.opacity = op;
    if (g) g.value = 1;
    if (jx || jy) {
      e[8] = keep[0]; e[9] = keep[1]; e[12] = keep[2]; e[13] = keep[3];
      cam.projectionMatrixInverse.copy(cam.projectionMatrix).invert();
    }
    return rt;
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

  // box-filter a target (default: the last scene pass') into `dst` (null = the canvas), blended with `prev` by weight w
  _down(plan, dst, w, prev, src = this.rt) {
    const u = this.down.uniforms;
    u.tSrc.value = src.texture;
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

  // the layered propeller: the still image with the static scene's depth onto the canvas, then only the overlay
  // (camera layer OVERLAY_LAYER: the disc, the band, the turning hub; the lights on that layer too, so its programs are
  // the ones the full scene uses) -- MSAA on the canvas, depth-tested against the static scene, blended as in a full
  // render (the disc is drawn after the opaque scene and the glazing there too)
  _compose(src, ovl) {
    const st = this.stage, R = this.R, cam = st.camera, a = this.a, rt = a.rt, plan = a.plan;
    const u = this.compose.uniforms;
    u.tSrc.value = src.texture;
    u.tDepth.value = rt.depthTexture;
    u.uDScale.value.set(plan.sx, plan.sy);
    u.uDMax.value = [plan.w - 1, plan.h - 1];
    this._fs(this.compose, null);
    for (const o of ovl) o.layers.enable(OVERLAY_LAYER);
    for (const l of this._sceneLights()) l.layers.enable(OVERLAY_LAYER);
    const mask = cam.layers.mask, clear = R.autoClear;
    cam.layers.set(OVERLAY_LAYER);
    R.autoClear = false;
    R.setRenderTarget(null);
    R.render(st.scene, cam);
    R.autoClear = clear;
    cam.layers.mask = mask;
  }
  _sceneLights() {
    if (!this._lights || this._lightsN !== this.stage.scene.children.length) {
      const L = [];
      this.stage.scene.traverse((o) => { if (o.isLight) L.push(o); });
      this._lights = L;
      this._lightsN = this.stage.scene.children.length;
    }
    return this._lights;
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
  // the camera's (unjittered) view-projection matrix
  _vp(cam) {
    cam.updateMatrixWorld();
    return this._vpm.multiplyMatrices(cam.projectionMatrix, cam.matrixWorldInverse);
  }
  _restart(layered) {
    const a = this.a, o = this._out();
    // (the layered propeller without still refinement: one plain pass at 1x, the canvas' samples)
    const plan = this.N > 0 ? this._plan() : this._plan(1);
    a.plan = plan; a.k = 0; a.N = Math.max(1, this.N); a.valid = true; a.done = false; a.layered = layered; a.rt = null;
    a.cam.set(this._camSig());
    this._ensureAcc(o.x, o.y);
  }
  // one accumulation step: frame k jittered by Halton (2, 3) within one MSAA cell (k = 0: centred).  The standard MSAA
  // patterns (2x / 4x / 8x) are n-rooks: n samples at n distinct x and y offsets 1 / n of a target pixel apart.  A jitter
  // of +-1 / (2n) target pixel fills the gaps between them, so per axis the samples cover each target pixel -- and at 1x
  // / 2x each output pixel -- evenly: the box filter of a dense supersampling (the 16x reference).  A jitter over the
  // whole target pixel (the first version) spilled half a target pixel past every edge: a 1.5-2 px tent (review CR1-04).
  _refineStep(hide) {
    const a = this.a, plan = a.plan, k = a.k, n = Math.max(1, plan.samples);
    const jx = k ? (halton(k, 2) - 0.5) / (n * plan.sx) : 0, jy = k ? (halton(k, 3) - 0.5) / (n * plan.sy) : 0;
    PCSS_U.uPcssFrame.value = k;
    a.rt = this._renderSS(plan, jx, jy, hide);
    PCSS_U.uPcssFrame.value = 0;
    const dst = this.acc[k & 1], prev = k ? this.acc[(k - 1) & 1] : null;
    this._down(plan, dst, 1 / (k + 1), prev);
    a.k = k + 1;
    if (a.k >= a.N) a.done = true;
  }

  // ---- temporal anti-aliasing of a moving frame (review CR1-02)
  _ensureHist(W, H) {
    const T = this.taa;
    for (let i = 0; i < 2; i++) {
      const t = T.rt[i];
      if (t && t.width === W && t.height === H) continue;
      if (t) t.dispose();
      T.rt[i] = colourTarget(W, H, this.caps.halfFloat, true);
      T.valid = false;
    }
  }
  // the camera's pose (world position, view direction, field of view)
  _poseOf(cam, out) {
    cam.updateMatrixWorld();
    out.pos.setFromMatrixPosition(cam.matrixWorld);
    cam.getWorldDirection(out.dir);
    out.fov = cam.isPerspectiveCamera ? cam.fov : 0;
    return out;
  }
  // the camera's motion between two poses: px a frame at the orbit centre's distance (turn + displacement over the
  // distance, times the focal length in pixels), and whether it is a cut (TAA_CUT_*)
  _motion(a, b) {
    const st = this.stage, cam = st.camera, H = this._out().y, t = st.controls && st.controls.target;
    const dist = Math.max(0.05, t ? b.pos.distanceTo(t) : 1), ang = a.dir.angleTo(b.dir), mv = a.pos.distanceTo(b.pos);
    const f = cam.isPerspectiveCamera ? H / (2 * Math.tan((cam.fov * Math.PI) / 360)) : (H * cam.zoom * dist) / Math.max(1e-6, cam.top - cam.bottom);
    const cut = ang > TAA_CUT_RAD || mv > TAA_CUT_DIST * dist || (a.fov > 0 && Math.abs(a.fov - b.fov) > 0.2 * b.fov);
    return { px: (ang + mv / dist) * f, cut };
  }
  _taaFrame(now) {
    const st = this.stage, cam = st.camera, T = this.taa, o = this._out(), W = o.x, H = o.y;
    // the frame: one supersampled pass when it fits the refresh (moveSS), else the canvas size with its MSAA
    const ss = this._ssOn('move') ? this._ssPlan('move') : null;
    const plan = ss || this._plan(1);
    const n = Math.max(1, plan.samples), k = (T.k = (T.k % TAA_CYCLE) + 1), js = this.taaP.jitter;
    const jx = (js * (halton(k, 2) - 0.5)) / (n * plan.sx), jy = (js * (halton(k, 3) - 0.5)) / (n * plan.sy);
    const vp = (this._vpCur || (this._vpCur = new THREE.Matrix4())).copy(this._vp(cam));
    PCSS_U.uPcssFrame.value = k;
    const rt = this._renderSS(plan, jx, jy);
    PCSS_U.uPcssFrame.value = 0;
    let cur = rt;
    if (ss) {
      if (!this.cur || this.cur.width !== W || this.cur.height !== H) { if (this.cur) this.cur.dispose(); this.cur = colourTarget(W, H, false, false); }
      this._down(plan, this.cur, 1, null, rt);
      cur = this.cur;
      this._used.cur = now;
    }
    this._ensureHist(W, H);
    // the history: the last moving frame's, else the still image the drag starts from
    let hist = null, hvp = null, hpose = null;
    if (T.valid) { hist = T.rt[T.i]; hvp = T.vp; hpose = T.pose; }
    else if (T.seed && T.seed.rt && T.seed.rt.texture) { hist = T.seed.rt; hvp = T.seed.vp; hpose = T.seed.pose; }
    const pose = this._poseOf(cam, this._pose), m = hist ? this._motion(hpose, pose) : { px: 0, cut: false };
    if (m.cut) { hist = null; T.cuts++; }
    const tp = this.taaP;
    const u = this.taaMat.uniforms, dst = T.rt[T.i ^ 1];
    u.tCur.value = cur.texture;
    u.tDepth.value = rt.depthTexture;
    u.uOut.value.set(W, H);
    u.uDScale.value.set(plan.sx, plan.sy);
    u.uDMax.value = [plan.w - 1, plan.h - 1];
    u.uValid.value = hist ? 1 : 0;
    u.tHist.value = hist ? hist.texture : cur.texture;
    u.uHist.value.set(hist ? hist.width : W, hist ? hist.height : H);
    if (hist) { u.uInvVP.value.copy(vp).invert(); u.uHistVP.value.copy(hvp); }
    u.uGround.value = st.groundY || 0;
    u.uAlpha.value.set(tp.alpha[0], tp.alpha[1]); u.uFast.value = tp.fast; u.uGamma.value = tp.gamma; u.uKeys.value = tp.keys;
    this._fs(this.taaMat, dst);
    this._show(dst);
    T.last = { seeded: !T.valid && !!hist, history: !!hist, k, ss: !!ss, plan: { w: plan.w, h: plan.h, samples: plan.samples },
      motionPx: Math.round(m.px * 100) / 100 };
    T.i ^= 1; T.valid = true; T.vp.copy(vp); T.pose.pos.copy(pose.pos); T.pose.dir.copy(pose.dir); T.pose.fov = pose.fov; T.seed = null; T.frames++;
    this._used.hist = now;
    return ss ? 'movess' : 'taa';
  }

  // render targets, the accumulation pair and the temporal history released after RELEASE_MS without use (the next
  // frame that needs one allocates it again)
  _gc(now) {
    if (now - this._gcAt < 1000) return;
    this._gcAt = now;
    let n = 0;
    for (const t of this.pool.slice()) if (now - (t._pcUsed || 0) > RELEASE_MS) { this._dropTarget(t); n++; }
    if (this.acc[0] && now - this._used.acc > RELEASE_MS) {
      for (const a of this.acc) if (a) a.dispose();
      this.acc = [null, null]; this.invalidate(); this.taa.seed = null; n++;
    }
    if (this.taa.rt[0] && now - this._used.hist > RELEASE_MS) {
      for (const t of this.taa.rt) if (t) t.dispose();
      this.taa.rt = [null, null]; this.taa.valid = false; n++;
    }
    if (this.cur && now - this._used.cur > RELEASE_MS) { this.cur.dispose(); this.cur = null; n++; }
    if (n) this.releases = (this.releases || 0) + 1;
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

  // Auto's start-up prediction from the calibration (c0: the median plain frame, ms): very slow devices (software
  // rendering) skip the refinement entirely; slow ones refine at the tier's ratio with 4 passes
  _predict(c0) {
    this.predicted = true;
    const v = this.vsync, out = this.floorPx;
    this.costs.direct.push(c0);                 // (shown by state().cost)
    if (c0 > 400) { this.framesCap = 0; this._cutNow(); this._log(`frame ${Math.round(c0)} ms: no still refinement`); }
    else if (c0 > 120) {
      this.framesCap = Math.min(this.framesCap, 4); this.stillPx = out; this._predictCut = true; this._cutNow();
      this._log(`frame ${Math.round(c0)} ms: 1x, 4 passes`);
    } else if (c0 > 1.3 * v) {
      // fragment-bound guess: a supersampled frame costs c0 x its pixel ratio; aim at 45 ms
      this.stillPx = Math.max(out, out * 45 / c0); this._predictCut = true;
      this._log(`frame ${Math.round(c0)} ms: still budget ${(this.stillPx / 1e6).toFixed(1)} MP`);
    } else this._log(`frame ${Math.round(c0)} ms: full still refinement`);
    this.syncUI();
  }
  _cutNow() { this._cutAt = performance.now(); }

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
    if (PLAIN.has(kind)) {
      const c = C[kind];
      // the passes back (review PERF-1): plain frames fit the refresh again, so a cut made on a stall (a lazy pipeline
      // compile, a GC pause) or on a slow 1x still pass (which costs about a plain frame) was wrong.  Backs off (5 s,
      // 10 s, 20 s, ...) if the cut keeps coming back.
      if (auto && this.predicted && c.length >= 5 && (Math.min(P.frames, this.framesCap) < P.frames || this._predictCut)
          && now > this._cutAt + 5000 * Math.pow(2, Math.min(this._restored, 6))) {
        const m = median(c.slice(-5));
        if (m < 1.3 * v) {
          this.framesCap = Infinity;
          if (this._predictCut) { this.stillPx = Infinity; this._predictCut = false; }
          this._restored++; this._cutAt = now;
          this.invalidate();
          this.stage.needsRender = true;
          this._log(`frames ${Math.round(m)} ms: still refinement back on`);
        }
      }
      // the moving pixel ratio (phones on Max: dprMove = dprMax): down while moving frames miss the refresh, never below
      // the tier's moving ratio (desktops: the full ratio, as before 2026-10; phones 1); up again once they fit
      if (auto && (kind === 'move' || kind === 'taa') && c.length >= 6) {
        const m = median(c.slice(-6)), lo = q.low ? Math.min(1, q.dprMax) : q.dprMoveBase;
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
      const m = median(c.slice(-5)), plan = this.a.plan, o = this._out(), out = Math.max(1, o.x * o.y);
      const cur = plan ? plan.w * plan.h : out, floor = this.floorPx;
      if (auto) {
        if (m > Math.max(2.5 * v, 45)) {
          if (cur > floor * 1.02) {
            // the 2x target, then the still canvas above the tier's ratio, come down first
            this.stillPx = Math.max(floor, cur * Math.max(0.3, 40 / m));
            this._log(`still ${Math.round(m)} ms: budget ${(this.stillPx / 1e6).toFixed(1)} MP`);
          } else if (m > 400) { this.framesCap = 0; this._cutNow(); this._log(`still ${Math.round(m)} ms: no refinement`); }
          else if (m > 150) {
            this.framesCap = Math.max(4, Math.floor(Math.min(this.framesCap, P.frames) / 2)); this._cutNow();
            this._log(`still ${Math.round(m)} ms: ${this.framesCap} passes`);
          }
          c.length = 0;
        } else if (m < 1.2 * v && this.stillPx < P.px) {
          // (from the budget, not the plan: a budget between 1x and 2x leaves the plan at 1x)
          this.stillPx = Math.min(P.px, Math.max(cur, this.stillPx) * 1.5);
          c.length = 0;
          this._log(`still ${Math.round(m)} ms: budget ${(this.stillPx / 1e6).toFixed(1)} MP`);
        }
      }
      // single supersampled passes predicted to fit in the refresh (a fragment-bound frame: the still pass' cost per
      // target pixel): while the camera moves (up to moveSS, the full moving ratio kept) and while only the scene
      // animates (up to the still scale); the measured costs of those frames switch them off again (below)
      if (P.moveSS && !this.caps.software) {
        const fit = 0.8 * v, per = m / Math.max(1, cur), cost = (S) => per * out * S * S;
        const Sm = this._ssScale('move'), Sb = this._ssScale('busy');
        if (!this.moveSS && Sm && now > this.moveCool && q.dprMove >= q.dprMax && cost(Sm) < fit) {
          this.moveSS = true;
          this._log(`still ${Math.round(m)} ms: moving frames ${Sm.toFixed(2)}x supersampled`);
        }
        if (!this.busySS && Sb && now > this.busyCool && cost(Sb) < fit) {
          this.busySS = true;
          this._log(`still ${Math.round(m)} ms: animating frames ${Sb.toFixed(2)}x supersampled`);
        }
      }
    } else if (kind === 'movess' || kind === 'busyss') {
      // off again: 4 frames over the refresh, or a single one far over it (the prediction was wrong)
      const c = C[kind];
      if ((c.length >= 4 && median(c.slice(-4)) > 1.3 * v + 2) || c[c.length - 1] > 3 * v + 10) {
        if (kind === 'movess') { this.moveSS = false; this.moveCool = now + 10000; } else { this.busySS = false; this.busyCool = now + 10000; }
        c.length = 0;
        this._log(`${kind === 'movess' ? 'moving' : 'animating'} supersampling too slow: off`);
      }
    }
  }

  // every target released (tests; the next frame that needs one allocates it again)
  release() {
    for (const t of this.pool.slice()) this._dropTarget(t);
    for (const a of this.acc) if (a) a.dispose();
    for (const t of this.taa.rt) if (t) t.dispose();
    if (this.cur) this.cur.dispose();
    this.acc = [null, null]; this.taa.rt = [null, null]; this.cur = null;
    this.taa.valid = false; this.taa.seed = null;
    this.invalidate();
    this.releases = (this.releases || 0) + 1;
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
    const a = this.a, st = this.stage, o = this._out(), q = st.quality, T = this.taa;
    const plan = a.plan || this._plan();
    return {
      mode: this.mode, forced: this.forced, device: this.device, adaptive: this.adaptive, path: this.kind,
      k: a.k, N: this.N, done: (this.N === 0 && !a.layered) || (a.done && a.valid), valid: a.valid, layered: a.layered,
      out: [o.x, o.y], plan: { S: plan.S, w: plan.w, h: plan.h, samples: plan.samples, bytes: plan.bytes },
      rt: this.rt ? { w: this.rt.width, h: this.rt.height, samples: this.rt.samples } : null, targets: this.pool.length,
      acc: this.acc[0] ? { w: this.acc[0].width, h: this.acc[0].height, type: this.acc[0].texture.type } : null,
      taa: { on: this.taaOn, valid: T.valid, frames: T.frames, cuts: T.cuts, last: T.last, seed: !!T.seed },
      budget: { px: this.pxBudget, mem: this.profile.mem, frames: this.profile.frames },
      moveSS: this.moveSS, busySS: this.busySS, dpr: st.dpr, dprMax: q.dprMax, dprMove: q.dprMove,
      dprStill: this.stillDpr(), dprNative: q.dprNative, framesCap: this.framesCap === Infinity ? null : this.framesCap,
      calib: this._calib.map((x) => Math.round(x)), predicted: this.predicted, releases: this.releases || 0,
      vsync: Math.round(this.vsync * 10) / 10,
      cost: Object.fromEntries(Object.entries(this.costs).map(([k, c]) => [k, c.length ? Math.round(median(c)) : null])),
      caps: { ...this.caps }, textures: this.textures || [], events: this.events.slice(-12),
      shadowMap: st.key ? st.key.shadow.mapSize.x : null, contactMap: st.contact ? st.contact.size : null,
    };
  }

  dispose() { this.release(); }
}
