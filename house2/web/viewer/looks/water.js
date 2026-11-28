// Look module "water": the pool's water surfaces and everything that lies under them (model/pool.py).
//
//   pool_water, spa_water     the water surface (kind water): a transparent sheet over the real shell.  Fresnel-weighted
//                             mirror of the scene (quality 'high': ONE planar reflection pass at half resolution, shared by
//                             both surfaces; 'low': the image-based sky plus a dark skyline), rippled by three scrolling
//                             copies of one slope tile (band-limited by its mip chain: the slope variance lost to the
//                             mips widens the sun glint and blurs the mirror instead of shimmering), sun glitter, a dark
//                             contact line where the water meets the tile (the mesh's UV v = distance to the wall).
//   pool_plaster, spa_tile,   the shell under the water.  Their shader (1) lifts every vertex to where it APPEARS through
//   pool_light, pool_fitting  the flat water surface (Snell, n = 1.333: the pool looks as shallow as a real one and the
//                             far wall shrinks), (2) lights it with the sun refracted into the water - its shadow is
//                             looked up where the ray entered the surface, so branch shadows lie on the floor where they
//                             should -, moving caustics, the sky through the surface and, at dusk, the pool lights,
//                             (3) absorbs on the way down and on the way up (red goes first: the turquoise deepens with
//                             depth and with the slant of the view) and adds the little light the water scatters.
//   pool_gap, coping_joint, skimmer_lid   plain.
//
// The water level, the pool lights and the waterline tile's colour map (borrowed from 'pool_tile' for 'spa_tile') are
// read from the scene at render time: the model needs no extras.  One water level per scene.
// Everything is procedural and seeded; ?still=1 freezes the ripples (time 0).
import * as THREE from 'three';
import * as SKYMOD from '../sky.js';      // soft dependency: SKIES[time].lightDesat (how much the lighting sky is greyed)

// ------------------------------------------------------------------------------------------------ parameters
export const WATER = {
  ior: 1.333,
  absorb: [0.30, 0.040, 0.012],          // 1 / m (pure water: red 0.3 - 0.4, green 0.04 - 0.06, blue 0.01 - 0.02)
  scatter: [0.006, 0.020, 0.026],        // albedo of the light scattered back by the water itself
  scatterK: 0.10,                        // 1 / m
  plaster: [0.46, 0.56, 0.60],            // linear albedo of the grey-blue pebble plaster (p21: the water 65 157 173)
  ripple: 1.0,                           // global ripple amplitude
  // slope layers: tile size (m), drift (m / s) x, z, rms slope per axis
  layers: [[2.9, 0.045, 0.022, 0.0060], [1.73, -0.030, 0.036, 0.0048], [8.3, 0.060, -0.018, 0.0055]],
  spaRipple: 1.7,
  glintRough: 0.035,
  reflDist: 12.0,                        // m: where the mirrored things are assumed to stand when a ripple bends the ray
  caustic: [1.9, 1.37, 0.55],            // tile A (m), tile B (m), strength
  lightDusk: [0.72, 0.95, 1.0, 5.5],     // colour and intensity of the pool lights at dusk
  skyline: { day: [0.050, 0.070, 0.040], dusk: [0.020, 0.024, 0.022] },   // 'low' only: what stands round the yard
};

// ------------------------------------------------------------------------------------------------ small helpers
function prng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const srgb8 = (v) => Math.round(255 * (v <= 0 ? 0 : v >= 1 ? 1 : v <= 0.0031308 ? 12.92 * v : 1.055 * Math.pow(v, 1 / 2.4) - 0.055));

function dataTex(data, n, o = {}) {
  const t = new THREE.DataTexture(data, n, n, THREE.RGBAFormat, THREE.UnsignedByteType);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = o.srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
  t.generateMipmaps = true;
  t.minFilter = THREE.LinearMipmapLinearFilter;
  t.magFilter = THREE.LinearFilter;
  t.anisotropy = o.anisotropy || 1;
  if (o.tile) t.repeat.set(1 / o.tile, 1 / o.tile);
  t.needsUpdate = true;
  return t;
}

// A tileable random wave field: nw plane waves with integer wave numbers k0 .. k1 per tile, slope amplitude ~ k^-p.
function waves(seed, nw, k0, k1, p) {
  const r = prng(seed), out = [];
  for (let i = 0; i < nw; i++) {
    const k = k0 * Math.pow(k1 / k0, r()), th = r() * 2 * Math.PI;
    let kx = Math.round(k * Math.cos(th));
    const kz = Math.round(k * Math.sin(th));
    if (kx === 0 && kz === 0) kx = 1;
    const kk = Math.hypot(kx, kz);
    out.push({ kx, kz, ph: r() * 2 * Math.PI, a: Math.pow(kk, -p), dx: kx / kk, dz: kz / kk });
  }
  return out;
}
// its slopes on an m x m grid, normalised to unit rms per axis
function slopeField(W, m) {
  const sx = new Float32Array(m * m), sz = new Float32Array(m * m);
  const cx = new Float32Array(m), sxT = new Float32Array(m), cz = new Float32Array(m), szT = new Float32Array(m);
  const w = 2 * Math.PI / m;
  for (const v of W) {
    for (let i = 0; i < m; i++) {
      cx[i] = Math.cos(v.kx * i * w); sxT[i] = Math.sin(v.kx * i * w);
      cz[i] = Math.cos(v.kz * i * w + v.ph); szT[i] = Math.sin(v.kz * i * w + v.ph);
    }
    const ax = v.a * v.dx, az = v.a * v.dz;
    for (let z = 0; z < m; z++) {
      const c1 = cz[z], s1 = szT[z], o = z * m;
      for (let x = 0; x < m; x++) {
        const c = cx[x] * c1 - sxT[x] * s1;
        sx[o + x] += c * ax; sz[o + x] += c * az;
      }
    }
  }
  let e = 0;
  for (let i = 0; i < m * m; i++) e += sx[i] * sx[i] + sz[i] * sz[i];
  const k = 1 / Math.sqrt(e / (2 * m * m));
  for (let i = 0; i < m * m; i++) { sx[i] *= k; sz[i] *= k; }
  return { sx, sz };
}

// RG = slope / 3 (signed, 0.5 = flat), B = |slope|^2 / 9: the mips then hold the mean slope and the mean square,
// i.e. the variance that a mip level has averaged away.
function rippleTex(n, anisotropy) {
  const { sx, sz } = slopeField(waves(4107, 44, 3, 40, 0.5), n);
  const d = new Uint8Array(n * n * 4);
  for (let i = 0; i < n * n; i++) {
    const a = sx[i], b = sz[i];
    d[i * 4] = Math.max(0, Math.min(255, Math.round(127.5 + a * 42.5)));
    d[i * 4 + 1] = Math.max(0, Math.min(255, Math.round(127.5 + b * 42.5)));
    d[i * 4 + 2] = Math.min(255, Math.round((a * a + b * b) / 9 * 255));
    d[i * 4 + 3] = 255;
  }
  return dataTex(d, n, { anisotropy });
}

// Caustics the way they form: a bundle of parallel rays, each bent by the wave slope where it enters, splatted on the
// floor (focus = the floor's depth in units of the waves' focal length).  R = intensity / 6 (mean 1 / 6).
function causticTex(n, anisotropy) {
  const ss = 2, m = n * ss;
  const { sx, sz } = slopeField(waves(7, 22, 3, 13, 0.4), m);
  let g = 0;
  for (let z = 0; z < m; z++) for (let x = 0; x < m; x++) { const dq = sx[z * m + (x + 1) % m] - sx[z * m + x]; g += dq * dq; }
  const f = 0.6 / Math.sqrt(g / (m * m)) / ss;
  const acc = new Float32Array(n * n);
  for (let z = 0; z < m; z++) {
    for (let x = 0; x < m; x++) {
      const i = z * m + x;
      let px = x / ss + f * sx[i], pz = z / ss + f * sz[i];
      px -= Math.floor(px / n) * n; pz -= Math.floor(pz / n) * n;
      const x0 = Math.floor(px), z0 = Math.floor(pz), fx = px - x0, fz = pz - z0;
      const x1 = (x0 + 1) % n, z1 = (z0 + 1) % n, xa = x0 % n, za = z0 % n;
      acc[za * n + xa] += (1 - fx) * (1 - fz); acc[za * n + x1] += fx * (1 - fz);
      acc[z1 * n + xa] += (1 - fx) * fz; acc[z1 * n + x1] += fx * fz;
    }
  }
  // a light blur (the sun is a disc), then the mean of min(a, b) of two independent copies for the shader's norm
  const c = new Float32Array(n * n);
  for (let z = 0; z < n; z++) {
    const zu = ((z + n - 1) % n) * n, zd = ((z + 1) % n) * n, zo = z * n;
    for (let x = 0; x < n; x++) {
      const xl = (x + n - 1) % n, xr = (x + 1) % n;
      c[zo + x] = (acc[zo + x] * 4 + (acc[zo + xl] + acc[zo + xr] + acc[zu + x] + acc[zd + x]) * 2
        + acc[zu + xl] + acc[zu + xr] + acc[zd + xl] + acc[zd + xr]) / 16 / (ss * ss);
    }
  }
  const d = new Uint8Array(n * n * 4);
  let mn = 0;
  const sh = Math.floor(n * 0.37) * n + Math.floor(n * 0.61);
  for (let i = 0; i < n * n; i++) {
    const v = Math.min(c[i] / 6, 1);
    d[i * 4] = d[i * 4 + 1] = d[i * 4 + 2] = Math.round(v * 255);
    d[i * 4 + 3] = 255;
    mn += Math.min(v, Math.min(c[(i + sh) % (n * n)] / 6, 1));
  }
  const t = dataTex(d, n, { anisotropy });
  t.userData.norm = 1 / (mn / (n * n));
  return t;
}

// tileable value noise, a few octaves -> R fine grain, G soft clouds, B a third field
function grainTex(n) {
  const d = new Uint8Array(n * n * 4);
  const chan = (seed, c0, oct, gain) => {
    const out = new Float32Array(n * n);
    let amp = 1, cells = c0, tot = 0;
    for (let o = 0; o < oct; o++) {
      const r = prng(seed + o * 17), L = new Float32Array(cells * cells);
      for (let i = 0; i < L.length; i++) L[i] = r() * 2 - 1;
      for (let y = 0; y < n; y++) {
        const v = y * cells / n, y0 = Math.floor(v), fy = v - y0, wy = fy * fy * (3 - 2 * fy), ya = (y0 % cells) * cells, yb = ((y0 + 1) % cells) * cells;
        for (let x = 0; x < n; x++) {
          const u = x * cells / n, x0 = Math.floor(u), fx = u - x0, wx = fx * fx * (3 - 2 * fx), xa = x0 % cells, xb = (x0 + 1) % cells;
          out[y * n + x] += amp * ((L[ya + xa] * (1 - wx) + L[ya + xb] * wx) * (1 - wy) + (L[yb + xa] * (1 - wx) + L[yb + xb] * wx) * wy);
        }
      }
      tot += amp; amp *= gain; cells *= 2;
    }
    for (let i = 0; i < n * n; i++) out[i] /= tot;
    return out;
  };
  const a = chan(11, 16, 4, 0.7), b = chan(23, 3, 4, 0.5), c = chan(37, 6, 3, 0.55);
  for (let i = 0; i < n * n; i++) {
    d[i * 4] = Math.max(0, Math.min(255, 127.5 + a[i] * 230));
    d[i * 4 + 1] = Math.max(0, Math.min(255, 127.5 + b[i] * 230));
    d[i * 4 + 2] = Math.max(0, Math.min(255, 127.5 + c[i] * 230));
    d[i * 4 + 3] = 255;
  }
  return dataTex(d, n);
}

// stand-in for the waterline tile (4 x 4 tiles of 0.1524 m, marbled cobalt glaze) until 'pool_tile' has its own map
function tileTex(n, anisotropy) {
  const d = new Uint8Array(n * n * 4), t = n / 4, r = prng(88), g = grainTex(64).image.data;
  const tiles = Array.from({ length: 16 }, () => ({ l: 0.8 + r() * 0.45, o: Math.floor(r() * 4096) }));
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      const tl = tiles[Math.floor(y / t) * 4 + Math.floor(x / t)];
      const e = Math.min(x % t, t - 1 - (x % t), y % t, t - 1 - (y % t));
      const m = Math.max(0, Math.min(1, e - 0.5));
      const q = g[((((y >> 1) * 64 + (x >> 1)) + tl.o) % 4096) * 4 + 1] / 255;
      const f = Math.max(0, Math.min(1, (q - 0.3) * 2.2));
      const i = (y * n + x) * 4;
      d[i] = srgb8(0.5 + ((0.018 + 0.085 * f) * tl.l - 0.5) * m);
      d[i + 1] = srgb8(0.54 + ((0.07 + 0.2 * f) * tl.l - 0.54) * m);
      d[i + 2] = srgb8(0.55 + ((0.23 + 0.33 * f) * tl.l - 0.55) * m);
      d[i + 3] = 255;
    }
  }
  return dataTex(d, n, { srgb: true, anisotropy, tile: 4 * 0.1524 });
}

// ------------------------------------------------------------------------------------------------ shaders
const GLSL_COMMON = /* glsl */`
#define W_IOR_INV 0.75019
// unit vector toward a light, as it runs INSIDE the water (the horizontal part shrinks by 1 / n)
vec3 wRefr( vec3 l ) { vec2 h = l.xz * W_IOR_INV; return vec3( h.x, sqrt( max( 1.0 - dot( h, h ), 0.0 ) ), h.y ); }
`;

// ---- under the water: vertex
const UW_VERT_PARS = /* glsl */`
uniform float uWaterY;
varying vec3 vWPos;
varying float vWPath;
#if NUM_DIR_LIGHTS > 0
  struct DirectionalLight {
    vec3 direction;
    vec3 color;
  };
  uniform DirectionalLight directionalLights[ NUM_DIR_LIGHTS ];
#endif
` + GLSL_COMMON;

const UW_VERT = /* glsl */`
{
  vec4 wTrue = modelMatrix * vec4( transformed, 1.0 );
  vWPos = wTrue.xyz;
  vWPath = 0.0;
  float wd = uWaterY - wTrue.y;
  float wh = cameraPosition.y - uWaterY;
  if ( wd > 0.0 && wh > 0.0 ) {
    // the ray from the eye crosses the surface at the horizontal distance x:  x + wd tan( t ) = r,  sin( i ) = n sin( t )
    float r = length( wTrue.xz - cameraPosition.xz );
    float x = r * wh / ( wh + wd * W_IOR_INV );
    for ( int k = 0; k < 5; k ++ ) {
      float q = x * x + wh * wh;
      float s2 = x * inversesqrt( q ) * W_IOR_INV;
      float c2 = sqrt( 1.0 - s2 * s2 );
      float f = x + wd * s2 / c2 - r;
      float df = 1.0 + wd * W_IOR_INV * wh * wh / ( q * sqrt( q ) * c2 * c2 * c2 );
      x = clamp( x - f / df, 0.0, r );
    }
    // seen from the eye the point lies on that ray: keep its place in plan, lift it
    float dApp = ( x > 1e-4 ) ? ( r - x ) * wh / x : wd * W_IOR_INV;
    vWPath = sqrt( ( r - x ) * ( r - x ) + wd * wd );
    wTrue.y = uWaterY - min( dApp, wd );
    gl_Position = projectionMatrix * viewMatrix * wTrue;
  }
}
`;

const UW_SHADOW_VERT = /* glsl */`
#if defined( USE_SHADOWMAP ) && NUM_DIR_LIGHT_SHADOWS > 0
{
  vec3 wSn = inverseTransformDirection( transformedNormal, viewMatrix );
  float wDs = uWaterY - vWPos.y;
  #pragma unroll_loop_start
  for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
    {
      vec4 wSp = vec4( vWPos, 1.0 );
      if ( wDs > 0.0 ) {
        // the light that reaches this point entered the water here: that is where its shadow is decided
        vec3 wLr = wRefr( inverseTransformDirection( directionalLights[ i ].direction, viewMatrix ) );
        wSp.xyz += wLr * ( wDs / wLr.y );
      } else {
        wSp.xyz += wSn * directionalLightShadows[ i ].shadowNormalBias;
      }
      vDirectionalShadowCoord[ i ] = directionalShadowMatrix[ i ] * wSp;
    }
  }
  #pragma unroll_loop_end
}
#endif
`;

// ---- under the water: fragment
const UW_FRAG_PARS = /* glsl */`
uniform float uWaterY;
uniform float uWTime;
uniform vec3 uAbsorb;
uniform vec4 uScatter;
uniform sampler2D uCaustic;
uniform sampler2D uRipple;
uniform sampler2D uGrain;
uniform vec4 uCausticP;
uniform vec4 uPoolLights[ 6 ];
uniform vec3 uPoolLightDir[ 6 ];
uniform vec3 uPoolLightCol;
varying vec3 vWPos;
varying float vWPath;
` + GLSL_COMMON + /* glsl */`
float wCaustic( vec3 p, vec3 lr, float d ) {
  vec2 q = p.xz + lr.xz * ( d / lr.y );
  vec2 w = ( texture2D( uRipple, q * 0.23 + uWTime * vec2( 0.013, 0.008 ) ).rg - 0.5 ) * 0.12;
  float a = texture2D( uCaustic, q * uCausticP.x + w + uWTime * vec2( 0.022, 0.012 ) ).r;
  float b = texture2D( uCaustic, vec2( q.y, - q.x ) * uCausticP.y - w * 0.8 + uWTime * vec2( - 0.016, 0.019 ) + 0.37 ).r;
  float c = min( a, b ) * uCausticP.w;
  return 1.0 + uCausticP.z * smoothstep( 0.03, 0.8, d ) * ( c - 1.0 );
}
`;

const UW_FRAG = /* glsl */`
vec3 wN = inverseTransformDirection( normal, viewMatrix );
float wD = max( uWaterY - vWPos.y, 0.0 );
vec3 wAlb = diffuseColor.rgb;
#ifdef W_GRAIN
{
  vec2 gp = abs( wN.y ) > 0.5 ? vWPos.xz : ( abs( wN.x ) > 0.5 ? vWPos.zy : vWPos.xy );
  vec3 g1 = texture2D( uGrain, gp * 0.71 ).rgb;
  vec3 g2 = texture2D( uGrain, gp * 0.097 + 0.37 ).rgb;
  wAlb *= 1.0 + ( g1.r - 0.5 ) * 0.07 + ( g2.g - 0.5 ) * 0.10 + ( g1.b - 0.5 ) * 0.04;
}
#endif
vec3 wE = vec3( 0.0 );          // irradiance that reaches the surface (already dimmed on its way down)
vec3 wTop = vec3( 0.0 );        // what falls on the water above (for the scattered light)
#if NUM_DIR_LIGHTS > 0
  #pragma unroll_loop_start
  for ( int i = 0; i < NUM_DIR_LIGHTS; i ++ ) {
    {
      vec3 lc = directionalLights[ i ].color;
      if ( lc.r + lc.g + lc.b > 0.0 ) {
        vec3 lw = inverseTransformDirection( directionalLights[ i ].direction, viewMatrix );
        vec3 lr = wRefr( lw );
        float ci = max( lw.y, 0.0 );
        float tf = 1.0 - ( 0.02 + 0.98 * pow( 1.0 - ci, 5.0 ) );
        float sh = 1.0;
        #if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_DIR_LIGHT_SHADOWS )
          sh = receiveShadow ? getShadow( directionalShadowMap[ i ], directionalLightShadows[ i ].shadowMapSize, directionalLightShadows[ i ].shadowBias, directionalLightShadows[ i ].shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
        #endif
        float ca = 1.0;
        #if UNROLLED_LOOP_INDEX == 0
          ca = wCaustic( vWPos, lr, wD );
        #endif
        // the beam keeps its flux through the surface: its irradiance across the beam grows by cos i / cos t
        wE += lc * ( tf * ci / lr.y * max( dot( wN, lr ), 0.0 ) * sh * ca ) * exp( - uAbsorb * ( wD / lr.y ) );
        wTop += lc * ( ci * sh );
      }
    }
  }
  #pragma unroll_loop_end
#endif
{
  vec3 wSky = vec3( 0.0 );
  #if defined( USE_ENVMAP ) && defined( ENVMAP_TYPE_CUBE_UV )
    wSky = getIBLIrradiance( normalize( ( viewMatrix * vec4( 0.0, 1.0, 0.0, 0.0 ) ).xyz ) );
    #ifdef W_SKYOFF
      wSky = max( wSky - uSkyOff, vec3( 0.0 ) );
    #endif
  #endif
  // the whole sky is squeezed into a cone of 97 degrees overhead: the floor gets all of it, a wall a fifth
  wE += wSky * ( 0.94 * ( 0.2 + 0.8 * max( wN.y, 0.0 ) ) ) * exp( - uAbsorb * ( wD * 1.2 ) );
  wTop += wSky;
}
if ( uPoolLightCol.r + uPoolLightCol.g + uPoolLightCol.b > 0.0 ) {
  for ( int k = 0; k < 6; k ++ ) {
    vec3 dl = vWPos - uPoolLights[ k ].xyz;
    float r2 = dot( dl, dl );
    float rr = sqrt( r2 );
    vec3 w = dl / max( rr, 1e-3 );
    float beam = 0.10 + 0.90 * max( dot( w, uPoolLightDir[ k ] ), 0.0 );
    wE += uPoolLightCol * ( uPoolLights[ k ].w * beam * max( dot( wN, - w ), 0.0 ) / ( r2 + 0.04 ) ) * exp( - uAbsorb * rr );
  }
}
vec3 wLo = wAlb * RECIPROCAL_PI * wE;
// the light that total reflection sends back down lights the shell again, the more the less the water absorbs;
// 0.5625 = 1 / n^2: radiance shrinks when it leaves the water
wLo *= 0.5625 / ( 1.0 - wAlb * 0.44 * exp( - uAbsorb * ( 2.6 * wD ) ) );
wLo += totalEmissiveRadiance * 0.5625;
vec3 wOut = wLo * exp( - uAbsorb * vWPath ) + uScatter.rgb * RECIPROCAL_PI * wTop * ( 1.0 - exp( - uScatter.w * vWPath ) );
`;

// ---- the surface
const WS_VERT_PARS = /* glsl */`
varying vec3 vWPos;
varying float vWEdge;
`;
const WS_VERT = /* glsl */`
vWPos = ( modelMatrix * vec4( transformed, 1.0 ) ).xyz;
vWEdge = abs( uv.y );
`;
const WS_FRAG_PARS = /* glsl */`
uniform float uWTime;
uniform sampler2D uRipple;
uniform vec4 uRippleA;
uniform vec4 uRippleB;
uniform vec4 uRippleC;
uniform float uRippleK;
uniform vec4 uEnvP;            // 1 / gain of the lighting sky, its re-saturation, glint roughness, mirror distance
uniform vec3 uSkyline;
#ifdef W_PLANAR
  uniform sampler2D uReflMap;
  uniform mat4 uReflMatrix;
  uniform float uReflOn;
#endif
varying vec3 vWPos;
varying float vWEdge;
vec3 wEnv( vec3 r, float rough ) {
  vec3 c = vec3( 0.0 );
  #if defined( USE_ENVMAP ) && defined( ENVMAP_TYPE_CUBE_UV )
    c = textureCubeUV( envMap, r, rough ).rgb * uEnvP.x;
    float l = dot( c, vec3( 0.2126, 0.7152, 0.0722 ) );
    c = max( vec3( l ) + ( c - vec3( l ) ) * uEnvP.y, vec3( 0.0 ) );
  #endif
  // what stands round a garden: fences, hedges, trees - a dark band above the horizon
  float az = atan( r.z, r.x );
  float hgt = 0.11 + 0.05 * sin( az * 3.0 + 1.3 ) + 0.03 * sin( az * 7.0 ) + 0.018 * sin( az * 17.0 + 2.0 );
  return mix( c, uSkyline, ( 1.0 - smoothstep( hgt - 0.012, hgt + 0.012, r.y ) ) * 0.9 );
}
#ifdef W_PLANAR
vec3 wMirror( vec3 p, vec3 r ) {
  vec4 q = uReflMatrix * vec4( p + r * uEnvP.w, 1.0 );
  return min( texture2D( uReflMap, clamp( q.xy / q.w, 0.002, 0.998 ) ).rgb, vec3( 6.0 ) );
}
#endif
`;
const WS_FRAG = /* glsl */`
vec3 wOut;
float wAlpha;
{
  vec2 p = vWPos.xz;
  // three drifting copies of one slope tile (the 2nd and 3rd turned): mean slope and the variance the mips took away
  vec4 ta = texture2D( uRipple, p * uRippleA.x + uWTime * uRippleA.yz );
  vec4 tb = texture2D( uRipple, mat2( 0.292, 0.956, - 0.956, 0.292 ) * p * uRippleB.x + uWTime * uRippleB.yz );
  vec4 tc = texture2D( uRipple, mat2( 0.857, - 0.515, 0.515, 0.857 ) * p * uRippleC.x + uWTime * uRippleC.yz );
  vec2 sa = ( ta.rg - 0.5 ) * 6.0, sb = ( tb.rg - 0.5 ) * 6.0, sc = ( tc.rg - 0.5 ) * 6.0;
  vec3 amp = vec3( uRippleA.w, uRippleB.w, uRippleC.w ) * uRippleK;
  vec2 slope = sa * amp.x + ( sb * mat2( 0.292, 0.956, - 0.956, 0.292 ) ) * amp.y + ( sc * mat2( 0.857, - 0.515, 0.515, 0.857 ) ) * amp.z;
  float var = max( ta.b * 9.0 - dot( sa, sa ), 0.0 ) * amp.x * amp.x + max( tb.b * 9.0 - dot( sb, sb ), 0.0 ) * amp.y * amp.y
            + max( tc.b * 9.0 - dot( sc, sc ), 0.0 ) * amp.z * amp.z;
  float sig = sqrt( var );
  vec3 N = normalize( vec3( - slope.x, 1.0, - slope.y ) );
  vec3 V = normalize( cameraPosition - vWPos );
  float nv = clamp( dot( N, V ), 0.0, 1.0 );
  vec3 R = reflect( - V, N );
  R.y = max( R.y, 0.004 );
  R = normalize( R );
  // Fresnel of a rippled sheet: toward the horizon the eye meets the facets that lean toward it
  float F = 0.02 + 0.98 * pow( 1.0 - clamp( nv + 0.8 * sig, 0.0, 1.0 ), 5.0 );
  vec3 refl;
  #ifdef W_PLANAR
    if ( uReflOn > 0.5 ) {
      vec3 up = vec3( 0.0, 1.6 * sig, 0.0 );
      refl = 0.5 * wMirror( vWPos, R ) + 0.25 * ( wMirror( vWPos, normalize( R + up ) ) + wMirror( vWPos, normalize( R - up * min( 1.0, R.y / max( up.y, 1e-4 ) ) ) ) );
    } else {
      refl = wEnv( R, clamp( sig * 2.0, 0.0, 0.5 ) );
    }
  #else
    refl = wEnv( R, clamp( sig * 2.0, 0.0, 0.5 ) );
  #endif
  // the sun on the facets
  vec3 glint = vec3( 0.0 );
  #if NUM_DIR_LIGHTS > 0
  {
    vec3 lw = inverseTransformDirection( directionalLights[ 0 ].direction, viewMatrix );
    float sh = 1.0;
    #if defined( USE_SHADOWMAP ) && NUM_DIR_LIGHT_SHADOWS > 0
      sh = receiveShadow ? getShadow( directionalShadowMap[ 0 ], directionalLightShadows[ 0 ].shadowMapSize, directionalLightShadows[ 0 ].shadowBias, directionalLightShadows[ 0 ].shadowRadius, vDirectionalShadowCoord[ 0 ] ) : 1.0;
    #endif
    vec3 H = normalize( lw + V );
    float a2 = uEnvP.z * uEnvP.z + var;
    float nh = max( dot( N, H ), 0.0 );
    float dd = nh * nh * ( a2 - 1.0 ) + 1.0;
    float Fh = 0.02 + 0.98 * pow( 1.0 - max( dot( V, H ), 0.0 ), 5.0 );
    glint = min( directionalLights[ 0 ].color * ( sh * a2 / ( PI * dd * dd ) * Fh * 0.25 / max( nv, 0.1 ) ), vec3( 30.0 ) ) * step( 0.0, lw.y );
  }
  #endif
  float g = dot( glint, vec3( 0.3333 ) );
  wAlpha = clamp( F + g * 0.6, 0.0, 1.0 );
  wOut = ( refl * F + glint ) / max( wAlpha, 1e-3 );
  // the meniscus on the tile: a thin dark line
  float edge = 1.0 - smoothstep( 0.003, 0.016, vWEdge );
  wOut = mix( wOut, wOut * 0.4, edge * 0.85 );
  wAlpha = mix( wAlpha, max( wAlpha, 0.62 ), edge * 0.85 );
}
`;

// ------------------------------------------------------------------------------------------------ the module
export function register(lib) {
  const ctx = lib.ctx;
  const low = ctx.quality === 'low';
  const S = { scene: null, countdown: 0, waters: [], rt: null, vcam: null, inPass: false, passFrame: -1, passCam: null, time: ctx.time || 'day', ownTile: null };
  let tex = null;
  const textures = () => {
    if (tex) return tex;
    const t0 = performance.now();
    const n = low ? 256 : 512, an = Math.min(ctx.anisotropy || 1, 8);
    tex = { ripple: rippleTex(n, an), caustic: causticTex(n, an), grain: grainTex(256), tile: tileTex(256, an) };
    tex.ms = Math.round(performance.now() - t0);
    if (typeof globalThis !== 'undefined') globalThis.__waterTex = { ms: tex.ms };
    return tex;
  };

  const L = WATER.layers;
  const U = {
    uWaterY: { value: 0 },
    uWTime: { value: 0 },
    uAbsorb: { value: new THREE.Vector3(...WATER.absorb) },
    uScatter: { value: new THREE.Vector4(...WATER.scatter, WATER.scatterK) },
    uCaustic: { value: null },
    uRipple: { value: null },
    uGrain: { value: null },
    uCausticP: { value: new THREE.Vector4(1 / WATER.caustic[0], 1 / WATER.caustic[1], WATER.caustic[2], 1) },
    uPoolLights: { value: Array.from({ length: 6 }, () => new THREE.Vector4(0, -1000, 0, 0)) },
    uPoolLightDir: { value: Array.from({ length: 6 }, () => new THREE.Vector3(0, 0, 1)) },
    uPoolLightCol: { value: new THREE.Vector3(0, 0, 0) },
    uRippleA: { value: new THREE.Vector4(1 / L[0][0], L[0][1] / L[0][0], L[0][2] / L[0][0], L[0][3]) },
    uRippleB: { value: new THREE.Vector4(1 / L[1][0], L[1][1] / L[1][0], L[1][2] / L[1][0], L[1][3]) },
    uRippleC: { value: new THREE.Vector4(1 / L[2][0], L[2][1] / L[2][0], L[2][2] / L[2][0], L[2][3]) },
    uEnvP: { value: new THREE.Vector4(1, 1, WATER.glintRough, WATER.reflDist) },
    uSkyline: { value: new THREE.Vector3(...WATER.skyline.day) },
    uReflMap: { value: null },
    uReflMatrix: { value: new THREE.Matrix4() },
    uReflOn: { value: 0 },
  };
  const applyTime = (t) => {
    S.time = t;
    const dusk = t === 'dusk', k = (SKYMOD.SKIES || {})[t] || {};
    const c = WATER.lightDusk;
    U.uPoolLightCol.value.set(c[0], c[1], c[2]).multiplyScalar(dusk ? c[3] : 0);
    U.uEnvP.value.x = 1 / (ctx.envGain || 1);
    U.uEnvP.value.y = 1 / Math.max(0.2, 1 - (k.lightDesat || 0));
    U.uSkyline.value.set(...(dusk ? WATER.skyline.dusk : WATER.skyline.day));
    for (const m of lensMats) m.emissiveIntensity = dusk ? 7.0 : 0.0;
  };
  const lensMats = [];
  lib.onTime(applyTime);
  lib.onTick((s) => { U.uWTime.value = s; });

  // ---- what the scene tells: water level, pool lights, the tile's map
  const box = new THREE.Box3(), v3 = new THREE.Vector3(), n3 = new THREE.Vector3();
  function scan(scene) {
    S.scene = scene;
    S.countdown = 240;
    S.waters.length = 0;
    const lights = [];
    let level = null, tileMap = null;
    scene.traverse((o) => {
      if (!o.isMesh) return;
      const name = o.userData.matName || (o.material && o.material.name);
      if (name === 'pool_water' || name === 'spa_water') {
        S.waters.push(o);
        if (name === 'pool_water' || level === null) {
          if (!o.geometry.boundingBox) o.geometry.computeBoundingBox();
          box.copy(o.geometry.boundingBox).applyMatrix4(o.matrixWorld);
          level = box.max.y;
        }
      } else if (name === 'pool_light') {
        lenses(o, lights);
      } else if (name === 'pool_tile' && o.material && o.material.map && !tileMap) {
        tileMap = o.material.map;
      }
    });
    if (level !== null) U.uWaterY.value = level;
    lights.sort((a, b) => b.w - a.w);
    for (let i = 0; i < 6; i++) {
      const l = lights[i];
      if (l) { U.uPoolLights.value[i].set(l.p.x, l.p.y, l.p.z, l.w); U.uPoolLightDir.value[i].copy(l.n); } else U.uPoolLights.value[i].set(0, -1000, 0, 0);
    }
    if (tileMap && S.ownTile && S.ownTile.map !== tileMap) { S.ownTile.map = tileMap; S.ownTile.needsUpdate = true; }
  }
  // every connected piece of a 'pool_light' mesh is one lens: centre, normal, strength ~ area
  function lenses(o, out) {
    const g = o.geometry, pos = g.attributes.position, nor = g.attributes.normal, idx = g.index;
    if (!pos || !idx) return;
    const par = new Int32Array(pos.count).map((_, i) => i);
    const find = (i) => { while (par[i] !== i) { par[i] = par[par[i]]; i = par[i]; } return i; };
    for (let i = 0; i < idx.count; i += 3) {
      const a = find(idx.getX(i)), b = find(idx.getX(i + 1)), c = find(idx.getX(i + 2));
      par[b] = a; par[c] = a;
    }
    const groups = new Map();
    for (let i = 0; i < pos.count; i++) {
      const r = find(i);
      let q = groups.get(r);
      if (!q) groups.set(r, q = { p: new THREE.Vector3(), n: new THREE.Vector3(), c: 0, lo: new THREE.Vector3(1e9, 1e9, 1e9), hi: new THREE.Vector3(-1e9, -1e9, -1e9) });
      v3.fromBufferAttribute(pos, i).applyMatrix4(o.matrixWorld);
      q.p.add(v3); q.lo.min(v3); q.hi.max(v3); q.c++;
      if (nor) q.n.add(n3.fromBufferAttribute(nor, i).transformDirection(o.matrixWorld));
    }
    for (const q of groups.values()) {
      const r = q.hi.distanceTo(q.lo) / 2;
      out.push({ p: q.p.multiplyScalar(1 / q.c), n: q.n.normalize(), w: Math.min(1.5, (r / 0.1) * (r / 0.1)) });
    }
  }
  function frame(scene) {
    if (S.scene !== scene || --S.countdown <= 0) scan(scene);
  }

  // ---- the planar reflection (quality 'high'): the scene seen from the mirrored eye, clipped at the water
  const P = { cam: new THREE.Vector3(), tgt: new THREE.Vector3(), rot: new THREE.Matrix4(), plane: new THREE.Plane(), clip: new THREE.Vector4(), q: new THREE.Vector4(), size: new THREE.Vector2(), up: new THREE.Vector3(0, 1, 0), pt: new THREE.Vector3() };
  function mirror(renderer, scene, camera) {
    if (S.inPass || !camera.isPerspectiveCamera) return;
    if (S.passFrame === renderer.info.render.frame && S.passCam === camera) return;
    const y = U.uWaterY.value;
    P.cam.setFromMatrixPosition(camera.matrixWorld);
    if (P.cam.y - y < 0.01) { U.uReflOn.value = 0; return; }
    renderer.getDrawingBufferSize(P.size);
    const w = Math.max(64, Math.min(1280, Math.round(P.size.x / 2))), h = Math.max(36, Math.round(w * P.size.y / P.size.x));
    if (!S.rt) {
      const type = renderer.capabilities.isWebGL2 && renderer.extensions.get('EXT_color_buffer_float') ? THREE.HalfFloatType : THREE.UnsignedByteType;
      S.rt = new THREE.WebGLRenderTarget(w, h, { type, depthBuffer: true, samples: 0, colorSpace: THREE.LinearSRGBColorSpace, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, generateMipmaps: false });
      S.vcam = new THREE.PerspectiveCamera();
      S.vcam.matrixAutoUpdate = true;
      U.uReflMap.value = S.rt.texture;
    } else if (S.rt.width !== w || S.rt.height !== h) S.rt.setSize(w, h);
    const v = S.vcam;
    // the eye, the point it looks at and its up vector, mirrored in the water plane
    P.rot.extractRotation(camera.matrixWorld);
    P.tgt.set(0, 0, -1).applyMatrix4(P.rot).add(P.cam);
    v.position.set(P.cam.x, 2 * y - P.cam.y, P.cam.z);
    v.up.set(0, 1, 0).applyMatrix4(P.rot);
    v.up.y = -v.up.y;
    v.lookAt(P.tgt.x, 2 * y - P.tgt.y, P.tgt.z);
    v.near = camera.near; v.far = camera.far;
    v.updateMatrixWorld();
    v.matrixWorldInverse.copy(v.matrixWorld).invert();
    v.projectionMatrix.copy(camera.projectionMatrix);
    U.uReflMatrix.value.set(0.5, 0, 0, 0.5, 0, 0.5, 0, 0.5, 0, 0, 0.5, 0.5, 0, 0, 0, 1).multiply(v.projectionMatrix).multiply(v.matrixWorldInverse);
    // oblique near plane = the water (Lengyel)
    P.plane.setFromNormalAndCoplanarPoint(P.up, P.pt.set(0, y - 0.004, 0)).applyMatrix4(v.matrixWorldInverse);
    P.clip.set(P.plane.normal.x, P.plane.normal.y, P.plane.normal.z, P.plane.constant);
    const pm = v.projectionMatrix.elements;
    P.q.set((Math.sign(P.clip.x) + pm[8]) / pm[0], (Math.sign(P.clip.y) + pm[9]) / pm[5], -1, (1 + pm[10]) / pm[14]);
    P.clip.multiplyScalar(2 / P.clip.dot(P.q));
    pm[2] = P.clip.x; pm[6] = P.clip.y; pm[10] = P.clip.z + 1; pm[14] = P.clip.w;
    v.projectionMatrixInverse.copy(v.projectionMatrix).invert();

    const vis = S.waters.map((o) => o.visible);
    for (const o of S.waters) o.visible = false;
    const rt0 = renderer.getRenderTarget(), face = renderer.getActiveCubeFace(), mip = renderer.getActiveMipmapLevel();
    const xr = renderer.xr.enabled, sa = renderer.shadowMap.autoUpdate;
    S.inPass = true;
    renderer.xr.enabled = false;
    renderer.shadowMap.autoUpdate = false;
    renderer.setRenderTarget(S.rt);
    renderer.state.buffers.depth.setMask(true);
    if (renderer.autoClear === false) renderer.clear();
    try { renderer.render(scene, v); } finally {
      renderer.xr.enabled = xr;
      renderer.shadowMap.autoUpdate = sa;
      renderer.setRenderTarget(rt0, face, mip);
      S.waters.forEach((o, i) => { o.visible = vis[i]; });
      S.inPass = false;
    }
    S.passFrame = renderer.info.render.frame;
    S.passCam = camera;
    U.uReflOn.value = 1;
  }

  // ---- materials
  const skyOff = THREE.ShaderChunk.envmap_physical_pars_fragment.includes('uSkyOff');
  function under(key, o) {
    const t = textures();
    U.uCaustic.value = t.caustic; U.uRipple.value = t.ripple; U.uGrain.value = t.grain;
    U.uCausticP.value.w = t.caustic.userData.norm;
    const m = new THREE.MeshStandardMaterial({ roughness: 1, metalness: 0 });
    if (Array.isArray(o.color)) m.color.setRGB(o.color[0], o.color[1], o.color[2], THREE.LinearSRGBColorSpace); else m.color.set(o.color);
    if (o.map) m.map = o.map;
    if (o.emissive) { m.emissive.setRGB(...o.emissive, THREE.LinearSRGBColorSpace); m.emissiveIntensity = 0; lensMats.push(m); }
    m.defines = { ...(o.grain ? { W_GRAIN: '' } : {}), ...(skyOff ? { W_SKYOFF: '' } : {}) };
    m.onBeforeCompile = (sh) => {
      for (const k of ['uWaterY', 'uWTime', 'uAbsorb', 'uScatter', 'uCaustic', 'uRipple', 'uGrain', 'uCausticP', 'uPoolLights', 'uPoolLightDir', 'uPoolLightCol']) sh.uniforms[k] = U[k];
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\n' + UW_VERT_PARS)
        .replace('#include <project_vertex>', '#include <project_vertex>\n' + UW_VERT)
        .replace('#include <shadowmap_vertex>', UW_SHADOW_VERT);
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <clipping_planes_pars_fragment>', '#include <clipping_planes_pars_fragment>\n' + UW_FRAG_PARS)
        .replace('#include <lights_fragment_begin>', UW_FRAG)
        .replace('#include <lights_fragment_maps>', '')
        .replace('#include <lights_fragment_end>', '')
        .replace('vec3 outgoingLight = totalDiffuse + totalSpecular + totalEmissiveRadiance;', 'vec3 outgoingLight = wOut;');
    };
    m.customProgramCacheKey = () => 'water-under-2' + (o.grain ? 'g' : '') + (skyOff ? 's' : '');
    m.onBeforeRender = (renderer, scene) => frame(scene);
    m.userData.water = key;
    applyTime(ctx.time || S.time);
    return m;
  }
  function surface(key, rippleK) {
    const t = textures();
    U.uRipple.value = t.ripple;
    const m = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.05, metalness: 0, transparent: true, depthWrite: false });
    const uK = { value: WATER.ripple * rippleK };
    m.defines = low ? {} : { W_PLANAR: '' };
    m.onBeforeCompile = (sh) => {
      for (const k of ['uWTime', 'uRipple', 'uRippleA', 'uRippleB', 'uRippleC', 'uEnvP', 'uSkyline', 'uReflMap', 'uReflMatrix', 'uReflOn']) sh.uniforms[k] = U[k];
      sh.uniforms.uRippleK = uK;
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\n' + WS_VERT_PARS)
        .replace('#include <project_vertex>', '#include <project_vertex>\n' + WS_VERT);
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <clipping_planes_pars_fragment>', '#include <clipping_planes_pars_fragment>\n' + WS_FRAG_PARS)
        .replace('#include <lights_fragment_begin>', WS_FRAG)
        .replace('#include <lights_fragment_maps>', '')
        .replace('#include <lights_fragment_end>', '')
        .replace('vec3 outgoingLight = totalDiffuse + totalSpecular + totalEmissiveRadiance;', 'vec3 outgoingLight = wOut;\n\tdiffuseColor.a = wAlpha;');
    };
    m.customProgramCacheKey = () => 'water-surface-2' + (low ? 'l' : 'h');
    m.onBeforeRender = (renderer, scene, camera) => { frame(scene); if (!low) mirror(renderer, scene, camera); };
    m.userData.water = key;
    applyTime(ctx.time || S.time);
    return m;
  }

  lib.add('pool_water', () => surface('pool_water', 1.0), { water: true });
  lib.add('spa_water', () => surface('spa_water', WATER.spaRipple), { water: true });
  lib.add('pool_plaster', () => under('pool_plaster', { color: WATER.plaster, grain: true }));
  lib.add('spa_tile', () => { const m = under('spa_tile', { color: 0xffffff, map: textures().tile }); S.ownTile = m; S.countdown = 0; return m; });
  lib.add('pool_light', () => under('pool_light', { color: [0.78, 0.84, 0.86], emissive: [0.72, 0.95, 1.0] }), { noShadow: true });
  lib.add('pool_fitting', () => under('pool_fitting', { color: [0.80, 0.81, 0.80] }), { noShadow: true });
  lib.add('pool_gap', { color: 0x0b0c0d, roughness: 0.9 });
  lib.add('coping_joint', { color: 0xa9a59b, roughness: 0.95 });
  lib.add('skimmer_lid', { color: 0xcfcabd, roughness: 0.7 });
}
