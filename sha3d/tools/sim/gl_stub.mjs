// SHA Live 3D, Phase 3 package E: a WebGL2 / 2-D canvas / DOM stub so that the gate engine (js/live/gate_system.js,
// LiveGateSystem) runs in node, plus the engine boot the browser's gates extension does (js/live/gates.js buildWorld:
// shaGates, gateWorld with the WALL_H override, the engine with the ICAO atlas faces). Nothing is drawn: every GL call is a
// no-op that returns a truthy object (shader compile / link status included) and every GL constant is 1; the 2-D canvas
// measures text as 40 px per character (the sign atlas layout only). The stub counts the bytes handed to bufferData so a
// caller can see what a rebuild would upload (`glStats()`).
//
// Used by tools/sim/build_gate_times.mjs and tools/sim/test_gate_sync.mjs (and the design scratch out/phase3_design/
// gate_times.mjs it replaces). Node 22, run from anywhere:
//   import { bootGateEngine } from './gl_stub.mjs';
//   const E = await bootGateEngine();   // {sys, gates, byName, GS, gatesMod, T, geo, data, ms}
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const SHA3D = path.resolve(HERE, '..', '..');

const STATS = { bufferData: 0, bytes: 0, calls: 0 };
export function glStats(reset = false) { const s = { ...STATS }; if (reset) { STATS.bufferData = 0; STATS.bytes = 0; STATS.calls = 0; } return s; }

let installed = false;
/** install the globals (window, document, location, performance) the browser modules read; idempotent */
export function installGLStub() {
  if (installed) return; installed = true;
  if (typeof globalThis.window === 'undefined') globalThis.window = globalThis;
  if (typeof globalThis.location === 'undefined') globalThis.location = { search: '', href: 'http://localhost/sha3d/live.html' };
  const keep = new Set(['font', 'fillStyle', 'strokeStyle', 'textAlign', 'textBaseline', 'lineWidth', 'globalAlpha', 'lineJoin', 'lineCap', 'shadowBlur', 'shadowColor', 'imageSmoothingEnabled']);
  const cx2d = new Proxy({}, {
    get: (o, k) => k === 'measureText' ? (t) => ({ width: String(t).length * 40, actualBoundingBoxAscent: 30, actualBoundingBoxDescent: 8 })
      : k === 'getImageData' ? (x, y, w, h) => ({ data: new Uint8ClampedArray(Math.max(4, (w | 0) * (h | 0) * 4)), width: w | 0, height: h | 0 })
      : k === 'createImageData' ? (w, h) => ({ data: new Uint8ClampedArray(Math.max(4, (w | 0) * (h | 0) * 4)), width: w | 0, height: h | 0 })
      : (typeof k === 'string' && keep.has(k)) ? o[k] : () => ({ addColorStop() {} }),
    set: (o, k, v) => { o[k] = v; return true; } });
  const canvas = () => ({ width: 0, height: 0, style: {}, getContext: (kind) => kind === '2d' ? cx2d : GLSTUB, addEventListener() {}, toDataURL: () => '' });
  if (typeof globalThis.document === 'undefined') globalThis.document = { createElement: canvas, getElementById: () => null, body: { classList: { add() {}, remove() {} } } };
}
// the WebGL2 context: constants (UPPER_CASE) are 1; methods are no-ops returning {} (truthy: compile / link status OK);
// bufferData counts the bytes it is given
const GLSTUB = new Proxy({}, {
  get: (o, k) => {
    if (typeof k !== 'string') return undefined;
    if (/^[A-Z_0-9]+$/.test(k)) return 1;
    if (k === 'bufferData') return (t, d) => { STATS.bufferData++; STATS.calls++; STATS.bytes += d && d.byteLength ? d.byteLength : 0; };
    if (k === 'getExtension') return () => ({});
    if (k === 'getParameter') return () => 16;
    if (k === 'getProgramParameter') return (p, what) => ({});
    return () => { STATS.calls++; return {}; };
  },
});

const readJSON = (rel) => JSON.parse(fs.readFileSync(path.join(SHA3D, rel), 'utf8'));
let BOOT = null;
/**
 * the gate engine as the page builds it (js/live/gates.js buildWorld): data from sha3d/data, geo initialised, the gate
 * world (terminal outlines with the WALL_H override, apron lanes; pavedAt null - the raster pavement is a canvas), the
 * engine with the ICAO atlas faces. A second call returns the same engine unless fresh = true.
 */
export async function bootGateEngine({ fresh = false } = {}) {
  if (BOOT && !fresh) return BOOT;
  installGLStub();
  const data = { stands: readJSON('data/sha_stands.json'), airport: readJSON('data/sha_airport.json'), taxigraph: readJSON('data/sha_taxigraph.json') };
  const geo = await import('../../js/geo.js'); geo.initGeo(data.airport);
  const GL = await import('../../js/gl.js'); GL.initGL({ getContext: () => GLSTUB });
  const GS = await import('../../js/live/gate_system.js');
  const gatesMod = await import('../../js/live/gates.js');
  const T = await import('../../js/aircraft/types.js');
  const gates = gatesMod.shaGates(data.stands, geo.hdgVec);
  GS.setGateWorld(gatesMod.gateWorld(data.airport, data.taxigraph, null));
  const t0 = performance.now();
  const sys = new GS.LiveGateSystem(gates, { atlasExtra: Object.keys(T.ICAO_TYPES) });
  const ms = performance.now() - t0;
  BOOT = { sys, gates, byName: new Map(gates.map(g => [g.name, g])), GS, gatesMod, T, geo, data, ms };
  return BOOT;
}
