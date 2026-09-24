// Shared TSL building blocks, ported from the GLSL chunks of the current renderer:
//   js/shaders/common.js 'noise' chunk (hash12, hash22, hash13, vnoise, fbm2) and ground.js groundfuncs band().
// The integer hash `ihashf` (uint arithmetic) is replaced by float hashes of the same cell coordinates: the patterns
// it drives are random placement, so exact bit-for-bit parity is not needed and float hashes compile identically on
// the WebGPU (WGSL) and WebGL 2 (GLSL) backends.
import { TSL } from '../lib.js';
const { Fn, vec2, vec3, float, fract, dot, floor, mix, smoothstep, abs } = TSL;

export const hash12 = Fn(([p]) => {
  const p3 = fract(vec3(p.x, p.y, p.x).mul(0.1031)).toVar();
  p3.addAssign(dot(p3, p3.yzx.add(33.33)));
  return fract(p3.x.add(p3.y).mul(p3.z));
}).setLayout({ name: 'hash12', type: 'float', inputs: [{ name: 'p', type: 'vec2' }] });

export const hash22 = Fn(([p]) => {
  const p3 = fract(vec3(p.x, p.y, p.x).mul(vec3(0.1031, 0.1030, 0.0973))).toVar();
  p3.addAssign(dot(p3, p3.yzx.add(33.33)));
  return fract(p3.xx.add(p3.yz).mul(p3.zy));
}).setLayout({ name: 'hash22', type: 'vec2', inputs: [{ name: 'p', type: 'vec2' }] });

export const hash13 = Fn(([q]) => {
  const p3 = fract(q.mul(0.1031)).toVar();
  p3.addAssign(dot(p3, p3.zyx.add(31.32)));
  return fract(p3.x.add(p3.y).mul(p3.z));
}).setLayout({ name: 'hash13', type: 'float', inputs: [{ name: 'q', type: 'vec3' }] });

export const vnoise = Fn(([p]) => {
  const i = floor(p).toVar(), f = fract(p).toVar();
  const u = f.mul(f).mul(f.mul(-2.0).add(3.0)).toVar();
  const a = hash12(i), b = hash12(i.add(vec2(1, 0))), c = hash12(i.add(vec2(0, 1))), d = hash12(i.add(vec2(1, 1)));
  return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}).setLayout({ name: 'vnoise', type: 'float', inputs: [{ name: 'p', type: 'vec2' }] });

// fbm with a compile-time octave count (the GLSL loop had a runtime `oct` but every call site passes a constant)
const fbmCache = {};
export function fbm2(p, oct) {
  if (!fbmCache[oct]) fbmCache[oct] = Fn(([p0]) => {
    const s = float(0).toVar(), pp = vec2(p0).toVar(); let a = 0.5, n = 0;
    for (let i = 0; i < oct; i++) { s.addAssign(vnoise(pp).mul(a)); n += a; pp.assign(pp.mul(2.03).add(vec2(1.7, 9.2))); a *= 0.5; }
    return s.div(n);
  }).setLayout({ name: 'fbm2_' + oct, type: 'float', inputs: [{ name: 'p0', type: 'vec2' }] });
  return fbmCache[oct](p);
}
// float replacement for ihashf(ivec2 c, int salt)
export const ihashf = (c, salt) => hash12(vec2(c).mul(vec2(0.1537, 0.2371)).add(vec2(float(salt).mul(17.13), float(salt).mul(-9.71))).add(vec2(311.7, 183.3)));

// band(x, a, b, fw) = smoothstep(a - fw, a + fw, x) - smoothstep(b - fw, b + fw, x)   (ground.js groundfuncs)
export const band = (x, a, b, fw) => smoothstep(float(a).sub(fw), float(a).add(fw), x).sub(smoothstep(float(b).sub(fw), float(b).add(fw), x));
export const sat = (x) => TSL.clamp(x, 0.0, 1.0);
export const absf = abs;
export const PI = Math.PI;
