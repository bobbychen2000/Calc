// SHA Live 3D Phase 3 (package P3-A): deterministic integer hashing and random draws for the day plan.
// Pure ES module (node + browser), no imports. Everything is 32-bit integer arithmetic (Math.imul, >>> 0): the same
// numbers on every JavaScript engine (design s.1.4 "Seeds and integer arithmetic", review M5).
//   seed(day) = fnv1a32('sha3d-plan|v' + PLAN_VERSION + '|' + day); each draw uses splitmix32(seed ^ hash(slot) ^ PURPOSE),
//   independent of the processing order.

export const PLAN_VERSION = 1;

/** FNV-1a 32-bit over the UTF-16 code units of a string -> uint32 */
export function fnv1a32(str, h = 0x811c9dc5) {
  h >>>= 0;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

/** one splitmix32 step -> uint32 */
export function splitmix32(x) {
  x = (x + 0x9e3779b9) >>> 0;
  let z = x;
  z = Math.imul(z ^ (z >>> 16), 0x85ebca6b) >>> 0;
  z = Math.imul(z ^ (z >>> 13), 0xc2b2ae35) >>> 0;
  return (z ^ (z >>> 16)) >>> 0;
}

/** draw purposes (constants, so that two draws for one slot never share a stream) */
export const PURPOSE = Object.freeze({
  TIME: 0x1001, AIRLINE: 0x1002, TYPE: 0x1003, DELAY_BAND: 0x1004, DELAY_VAL: 0x1005, TURN: 0x1006, INTL: 0x1007,
  SHUFFLE: 0x1008, BIZ: 0x1009, STAND: 0x100a, CONT: 0x100b,
});

export const daySeed = (day) => fnv1a32('sha3d-plan|v' + PLAN_VERSION + '|' + day);

/** uint32 for (seed, slot key, purpose); order-independent */
export function draw(seed, key, purpose) {
  return splitmix32((seed ^ fnv1a32(String(key)) ^ purpose) >>> 0);
}

/** integer in [0, n) from a uint32 without float bias worth noting at the plan's sizes (n << 2^32) */
export const drawInt = (seed, key, purpose, n) => n > 0 ? Math.floor(draw(seed, key, purpose) * n / 4294967296) : 0;

/** integer in [lo, hi] */
export const drawRange = (seed, key, purpose, lo, hi) => lo + drawInt(seed, key, purpose, hi - lo + 1);

/** permille in [0, 1000) (integer comparisons for probabilities) */
export const drawPermille = (seed, key, purpose) => drawInt(seed, key, purpose, 1000);

/** deterministic Fisher-Yates shuffle (copy) keyed by a string */
export function shuffled(arr, seed, key) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = drawInt(seed, key + '#' + i, PURPOSE.SHUFFLE, i + 1);
    const t = a[i]; a[i] = a[j]; a[j] = t;
  }
  return a;
}

/** canonical JSON (sorted object keys, no whitespace) for hashing */
export function canonical(v) {
  if (v === null || typeof v !== 'object') return JSON.stringify(v === undefined ? null : v);
  if (Array.isArray(v)) return '[' + v.map(canonical).join(',') + ']';
  const ks = Object.keys(v).filter(k => v[k] !== undefined).sort();
  return '{' + ks.map(k => JSON.stringify(k) + ':' + canonical(v[k])).join(',') + '}';
}

/** 64-bit hex digest (two FNV-1a streams with different offsets) of the canonical JSON of v */
export function hashOf(v) {
  const s = canonical(v);
  const a = fnv1a32(s), b = fnv1a32(s, 0x01000193 ^ 0x5bd1e995);
  return a.toString(16).padStart(8, '0') + b.toString(16).padStart(8, '0');
}

/** largest-remainder apportionment of n over integer-scaled weights {key: w} -> {key: count}; ties by key order */
export function apportion(weights, n) {
  const keys = Object.keys(weights).filter(k => weights[k] > 0).sort();
  const out = {}; for (const k of Object.keys(weights)) out[k] = 0;
  if (!keys.length || n <= 0) return out;
  // integer arithmetic: weights scaled to integers (1e5) so that the result is engine-independent
  const W = keys.map(k => Math.round(weights[k] * 100000));
  const tot = W.reduce((s, w) => s + w, 0);
  if (tot <= 0) return out;
  const rem = [];
  let used = 0;
  keys.forEach((k, i) => {
    const num = W[i] * n;
    const q = Math.floor(num / tot);
    out[k] = q; used += q;
    rem.push([num - q * tot, k]);
  });
  rem.sort((x, y) => (y[0] - x[0]) || (x[1] < y[1] ? -1 : x[1] > y[1] ? 1 : 0));
  for (let i = 0; i < n - used; i++) out[rem[i % rem.length][1]]++;
  return out;
}
