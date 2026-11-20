// forked from sfo3d@e3218d6 js/live/airport.js (standGates: stand data -> gate objects) and js/live/app.js (the gate
// system glue: bridgeGate / applyGate, the bridge light sprites)
// sha3d gates extension (owned by the gates package): stands from window.SHA_STANDS (injected as ctx.stands - never
// imported at module scope, arch.md R4), apron-drive jet bridges, VDGS, CAAC stand-number signs, remote-stand equipment
// and the ground service vehicles around parked aircraft. The engine is js/live/gate_system.js (forked from sfo3d's
// js/live/gates.js); this file turns the data into its gate objects, gives it the world it tests against (the OSM T1 / T2
// outlines, the apron lanes of the taxi graph, the pavement map) and adds two DEBUG features:
//  - ?park=<stand>[:<ICAO>],...  (or park=contact | remote | all; window.SHA.qa.park(stand, icao)): parks a STATIC aircraft
//    model at the stand (default type by stand class: B E190, C A320 / B738 alternating, CL B752, D B763, E A333, EL B77W,
//    F B748), docks its bridge and places the GSE. A visual check of scale, bridges and equipment ONLY - not traffic: the
//    scene note says so while any is parked (there is no traffic engine before Phase 3; never unlabelled synthetic traffic).
//  - ?debug=push (or debug=gates): an overlay of every stand's lead-in (cyan), its push-back path (magenta, data push.pts),
//    the push end (magenta disc) and the data's bridge points (rotunda blue, docked cab green). Overlay, not paint.
// Provenance is kept on the gate objects for the planned Observed / Inferred legend: g.src / g.posSrc (stand), each
// bridge's src ('obs' = SAR corridor seen, 'inf' = OSM gate node / facade only) and bridgeStatus, b.modelSrc 'inf'
// (autoModel), g.vdgsSrc 'inf'. Inferred bridges are drawn exactly like observed ones (owner rule: flag, not style).
import { registerExtension } from './ext.js';
import { Mesh } from '../gl.js';
import { Geo } from '../geom.js';
import { m4, v3 } from '../math.js';
import { TYPES, ICAO_TYPES } from '../aircraft/types.js';
import { TYPE_MODELS } from '../aircraft/fit.js';
import { LiveGateSystem, setGateWorld, footprint, DEPARTURE_LEVELS, PBB } from './gate_system.js';
import { GSIGN_VS, GSIGN_FS } from './gate_signs.js';
import { OBJ_VS, OBJ_FS } from '../shaders/objects.js';
import { LiveAircraft } from './aircraft.js';
import { MODEL_SOURCES } from './models.js';
import { liveryForAirline } from './lookup.js';
import { aircraftLightStates } from '../env/aircraft_lights.js';

const I4 = () => new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
// wall top of the terminal outlines above the apron (the VDGS facade-mount test only, gate_system.js wallTop): T1 the
// airside concourse 9 m (photo ratio, docs/phase1/standards_refs.md §3: 9 +- 2 m), T2 the data height (25 m rule) - inf
const WALL_H = { 'osm:way/93184730': 9.0 };
// the debug type per stand class (models from ../sfo3d/data/models/; C alternates A320 / B738 by stand number)
const DEBUG_TYPE = { B: 'E190', C: 'A320', CL: 'B752', D: 'B763', E: 'A333', EL: 'B77W', F: 'B748' };
const debugType = (g) => g.cls === 'C' ? ((parseInt(g.name, 10) || 0) % 2 ? 'B738' : 'A320') : (DEBUG_TYPE[g.cls] || 'A320');

// ---------------------------------------------------------------- stand data -> gate objects (sfo3d standGates)
// World coordinates throughout (gate_system.js stW / stD are the identity): g.nose = the stop point [x, z] (data nose: the
// OSM stop node, used as the nose tip of the class reference aircraft, inf), g.dir = unit [x, z] of the parked heading.
export function shaGates(stands, hdgVec) {
  const CM = {}; for (const [k, v] of Object.entries(stands.class_max || {})) CM[k] = { span: v[0], len: v[1] };
  const remoteBy = new Map((stands.remote || []).map(r => [r.name, r]));
  const gates = [];
  for (const s of stands.stands || []) {
    const dir = hdgVec(s.hdg); const cm = CM[s.cls] || CM.C || { span: 36.5, len: 45 };
    const walkLen = (w) => { let L = 0; for (let i = 1; i < (w || []).length; i++) L += Math.hypot(w[i][0] - w[i - 1][0], w[i][1] - w[i - 1][1]); return L; };
    const bridges = (s.bridges || []).map(b => ({
      gate: b.gate || s.name, attach: b.attach.slice(), attachW: b.attach.slice(), door: b.door || 1, upper: false,
      rotundaW: b.rotunda || null, cabW: b.cab || null, walkW: walkLen(b.walk) > 0.5 ? b.walk : null, cabPose: b.cab_pose || null,
      stowW: null, rotundaMaxR: null, rotundaTwinOf: null, tunnelEndW: null, extRange: null, model: null, dockTypesOut: [],
      cabTurnDeg: null, cabOption: null, stowLen: null, rotundaSrc: b.rotunda_src || null,
      src: b.src || 'inf', reachM: b.reach_m ?? null, reachFlag: b.reach_flag || null }));
    for (const b of bridges) reachFix(b);
    const term = /^T1\b/.test(s.area || '') ? 'T1' : /^T2\b/.test(s.area || '') ? 'T2' : null;
    const rm = remoteBy.get(s.name);
    gates.push({
      id: s.name, name: s.name, alias: s.alias || [], cls: s.cls, src: s.src, posSrc: s.pos_src || null, clsSrc: s.cls_src || null,
      maxSpan: s.span_max ? Math.min(cm.span, s.span_max + 0.1) : cm.span, maxLen: s.len_max ? Math.min(cm.len, s.len_max + 0.1) : cm.len,
      gate: s.gate || s.name, excl: s.excl || [], area: s.area || '', terminal: term, contact: !!s.contact, bridgeStatus: s.bridge_status || null,
      sharesBridgesOf: s.bridge_status === 'shared' && (s.alt_group || []).length ? s.alt_group[0] : null,
      leadinW: s.leadin || null, push: s.push || null, typesOk: null, typeStops: null,
      nose: s.nose.slice(), dir, outN: [-dir[0], -dir[1]], attach: bridges.length ? bridges[0].attach : s.nose.slice(), bridges,
      wide: cm.span > 41.2, len: cm.len, span: cm.span, bridge: bridges.length > 0, remote: !s.contact, service: rm ? (/business/.test(rm.service || '') ? 'business' : 'bus') : null,
      hdg: s.hdg, world: { x: s.nose[0], z: s.nose[1], hdg: s.hdg }, empty: true, acType: null, dynamic: false, vdgsSrc: bridges.length ? 'inf' : null,
    });
  }
  // alternative positions sharing a base stand's bridge (238A -> 238, 259A -> 259: data bridge_status 'shared')
  const byName = new Map(gates.map(g => [g.name, g]));
  for (const g of gates) { const base = g.sharesBridgesOf ? byName.get(g.sharesBridgesOf) : null; if (!base) { g.sharesBridgesOf = null; continue; }
    g.sharedBridges = base.bridges; g.sharedFrom = base.id; (base.altGates = base.altGates || []).push(g.id); }
  return gates;
}

// A data bridge whose docked reach (rotunda -> the class reference's docked cab, reach_m) is beyond the longest sell-sheet
// unit (AT3 72/150: 41.4 m operational, 43.7 m mechanical, rotunda to cab pivot; the data cab lies ~1 m beyond the pivot)
// could never dock: 236 (44.8 m), 266 (48.4 m) and 240 (52.5 m; the data flags 240 / 266 'reach > 45 m ... the rotunda
// (OSM gate node) is uncertain'). Its rotunda is moved out along the fixed link (the last walkway segment, else towards
// the cab) until the reach is REACH_MAX, at most 15 m, and the fixed link is extended to it: b.rotundaMoved (m, inf).
const REACH_MAX = 43.0;
function reachFix(b) {
  if (!b.rotundaW || !b.cabW || !(b.reachM > REACH_MAX)) return;
  const r = b.rotundaW, c = b.cabW; const w = b.walkW; let u = null;
  if (w && w.length >= 2) { const A = w[w.length - 2], B = w[w.length - 1]; const L = Math.hypot(B[0] - A[0], B[1] - A[1]); if (L > 0.5) u = [(B[0] - A[0]) / L, (B[1] - A[1]) / L]; }
  if (!u) { const L = Math.hypot(c[0] - r[0], c[1] - r[1]); u = [(c[0] - r[0]) / L, (c[1] - r[1]) / L]; }
  const at = (d) => [r[0] + u[0] * d, r[1] + u[1] * d]; const reach = (d) => { const p = at(d); return Math.hypot(c[0] - p[0], c[1] - p[1]); };
  let d = 0; while (d < 15 && reach(d) > REACH_MAX) d += 0.05; d = +d.toFixed(2);
  const p = at(d); b.rotundaData = r.slice(); b.rotundaW = p; b.walkW = (w && w.length >= 2 ? w.slice() : [b.attach.slice(), r.slice()]).concat([p]);
  b.rotundaMoved = d; b.reachUsed = +reach(d).toFixed(2); b.rotundaSrc = (b.rotundaSrc || '') + `; moved ${d} m out along the fixed link so that the docked reach is ${b.reachUsed} m (sha3d gates, inf)`;
}

// the world the bridges and equipment are tested against: terminal outlines, apron lanes, pavement
function gateWorld(airport, taxigraph, pavedAt) {
  const outlines = [];
  for (const b of airport.buildings || []) if (b.kind === 'terminal') for (const r of [b.ring, ...(b.more_rings || [])]) if (r && r.length >= 3) outlines.push({ ring: r, h: WALL_H[b.id] ?? b.height_m ?? 20, id: b.id });
  const lanes = [];
  for (const L of (taxigraph && taxigraph.links) || []) { if (L.kind !== 'taxiway' && L.kind !== 'taxilane') continue; const hc = L.kind === 'taxiway' ? 11.5 : 7.5;
    for (let i = 1; i < (L.pts || []).length; i++) lanes.push([L.pts[i - 1][0], L.pts[i - 1][1], L.pts[i][0], L.pts[i][1], hc]); }
  return { outlines, lanes, pavedAt };
}

// ---------------------------------------------------------------- debug overlay: lead-ins, push-back paths, bridge points
function pushOverlay(gates, G) {
  const geo = new Geo();
  const E = (c) => [0.6, 0, 0, 1.2];
  const ribbon = (pts, w, col, dy = 0) => { const y = G + 0.12 + dy; for (let i = 1; i < pts.length; i++) { const A = pts[i - 1], B = pts[i]; const dx = B[0] - A[0], dz = B[1] - A[1], L = Math.hypot(dx, dz); if (L < 0.05) continue;
    const n = [-dz / L * w / 2, dx / L * w / 2]; geo.quad([A[0] + n[0], y, A[1] + n[1]], [B[0] + n[0], y, B[1] + n[1]], [B[0] - n[0], y, B[1] - n[1]], [A[0] - n[0], y, A[1] - n[1]], col, E(col)); } }; // (normal up)
  const dashed = (pts, w, col, dy = 0, on = 4, off = 3) => { let acc = 0; for (let i = 1; i < pts.length; i++) { const A = pts[i - 1], B = pts[i]; const L = Math.hypot(B[0] - A[0], B[1] - A[1]);
    for (let t = 0; t < L; t += 0.5) { const ph = (acc + t) % (on + off); if (ph < on) { const t1 = Math.min(L, t + 0.5); ribbon([[A[0] + (B[0] - A[0]) * t / L, A[1] + (B[1] - A[1]) * t / L], [A[0] + (B[0] - A[0]) * t1 / L, A[1] + (B[1] - A[1]) * t1 / L]], w, col, dy); } } acc += L; } };
  const disc = (p, r, col, h = 0.15) => geo.cylinder(r, h, 16, col, E(col), m4.translate(p[0], G + 0.05, p[1]), true);
  const MAG = [0.95, 0.1, 0.85, 1], CYA = [0.1, 0.85, 0.95, 1], BLU = [0.15, 0.35, 1.0, 1], GRN = [0.2, 0.95, 0.2, 1];
  let n = 0;
  for (const g of gates) {
    if (g.leadinW && g.leadinW.length > 1) ribbon(g.leadinW, 1.0, CYA, 0);
    if (g.push && g.push.pts && g.push.pts.length > 1) { dashed(g.push.pts, 2.2, MAG, 0.06); disc(g.push.pts[g.push.pts.length - 1], 3.0, MAG); n++; }
    disc(g.nose, 1.5, CYA, 0.3);
    for (const b of g.bridges || []) { if (b.rotundaW) disc(b.rotundaW, 1.8, BLU, 0.4); if (b.cabW) disc(b.cabW, 1.4, GRN, 0.4); }
  }
  return { geo, n };
}

// ---------------------------------------------------------------- the extension
const state = { sys: null, gates: [], parked: new Map(), overlay: null, info: null, G: 0 };

registerExtension({
  name: 'gates', order: 30,
  buildWorld: async (ctx) => {
    const { R, airport, stands, taxigraph, geo, groundY } = ctx; state.G = groundY;
    if (!stands || !stands.stands) { ctx.log('gates: no stand data (window.SHA_STANDS)'); return { info: 'no stand data' }; }
    R.addProgram('gsign', GSIGN_VS, GSIGN_FS);
    // the bridges' own object program: the glazed tunnels' night glow (the curtain-wall material's interior light) at 0.4
    // of a terminal facade's (photo 18, a T2 bridge at night, shows a lit but not facade-bright tunnel; inf)
    R.addProgram('objG', OBJ_VS, OBJ_FS);
    const gates = shaGates(stands, geo.hdgVec); state.gates = gates;
    setGateWorld(gateWorld(airport, taxigraph, ctx.ground && ctx.ground.pavedAt));
    const t0 = performance.now();
    const sys = new LiveGateSystem(gates, { atlasExtra: Object.keys(ICAO_TYPES) }); state.sys = sys;
    sys.objProg = 'objG'; sys.objUniforms = () => ({ uEmissiveBoost: 1, uNight: ((R.extraCommon && R.extraCommon.uNight) || 0) * 0.4 });
    const ms = performance.now() - t0;
    const items = [];
    const q = new URLSearchParams(location.search); const dbg = (q.get('debug') || '').split(',');
    if (dbg.includes('push') || dbg.includes('gates')) { const O = pushOverlay(gates, groundY); state.overlay = O.n;
      items.push({ mesh: new Mesh(O.geo.data()), prog: 'obj', model: I4(), bbox: O.geo.bbox(), castShadow: false, noCull: true, polyOffset: [-2, -4], uniforms: { uEmissiveBoost: 1 }, debug: 'push' }); }
    state.info = gateStats(sys, gates, ms);
    ctx.log('gates ' + JSON.stringify(state.info.summary));
    return { gates, items, info: state.info.summary };
  },
  start: async (app) => {
    const sys = state.sys; if (!sys) return;
    app.scene.gateSys = sys;
    sys.aircraftFootprints = () => [...state.parked.values()].map(P => footprint(P.nose3, P.f3, P.T, P.gate));
    const q = new URLSearchParams(location.search);
    const QN = { high: [1800, 1600], medium: [1300, 1100], ultra: [4000, 2500], low: [1000, 700] }[(app.qa.info().quality) || 'high'] || [1800, 1600];
    // ---- debug parking
    const byName = new Map(state.gates.map(g => [g.name, g]));
    const baseNote = (app.ui.el && app.ui.el.note && app.ui.el.note._t) || ''; // (the core's note, restored when nothing is parked)
    async function park(name, icao = null, animate = false) {
      const g = byName.get(String(name)); if (!g) return { ok: false, why: 'no stand ' + name };
      const ty = (icao || debugType(g)).toUpperCase(); const m = TYPE_MODELS[ty]; const T = m && TYPES[m.t];
      if (!T) return { ok: false, why: 'no model for ' + ty };
      unpark(g.name);
      const f2 = g.dir, f3 = [f2[0], 0, f2[1]], nose3 = [g.nose[0], state.G, g.nose[1]];
      const ac = new LiveAircraft(m.t, m.m && MODEL_SOURCES[m.m] ? m.m : null, liveryForAirline(null), { id: 'debug-park-' + g.name, lod: 1, lodDist: QN[0], shadowDist: QN[1] });
      ac.pos = [g.nose[0] - f2[0] * ac.T.xMain, state.G, g.nose[1] - f2[1] * ac.T.xMain]; ac.fwd = f3; ac.gear = 1; ac.dirt = 0.35;
      Object.assign(ac.lightsOn, aircraftLightStates({ phase: 'parked', ground: true, gs: 0, altAgl: 0, stale: false }));
      ac.debugPark = true; app.scene.add(ac);
      // the bridge stand: the stand itself, or the base stand whose bridge an alternative position shares
      const B = g.sharesBridgesOf ? byName.get(g.sharesBridgesOf) : g;
      state.parked.set(g.name, { ac, gate: g, bridgeGate: B, T, type: m.t, icao: ty, nose3, f3 });
      sys.setOccupant(B, m.t, !!animate, Date.now(), { nose: g.nose.slice(), dir: g.dir.slice() }, ty);
      sys.dirty = true; note();
      await ac.ready;
      const docked = B.bridge ? sys.bridgesOf(B).map(b => { const P = sys.planFor(B, b); return { gate: b.gate, model: b.modelUsed || null, docks: !!P.ok, why: P.ok ? null : P.why }; }) : [];
      return { ok: true, stand: g.name, type: m.t, icao: ty, model: m.m || null, L: +ac.T.L.toFixed(2), span: ac.T.wing ? +ac.T.wing.span.toFixed(2) : null, bridges: docked, debug: true };
    }
    function unpark(name) {
      const P = state.parked.get(String(name)); if (!P) return false;
      const i = app.scene.aircraft.indexOf(P.ac); if (i >= 0) app.scene.aircraft.splice(i, 1);
      sys.setOccupant(P.bridgeGate, null, false, Date.now(), null, null);
      state.parked.delete(String(name)); sys.dirty = true; note(); return true;
    }
    function note() {
      const n = state.parked.size;
      app.ui.setNote(n ? `DEBUG ?park=: ${n} static aircraft (not traffic)` : baseNote);
    }
    app.qa.park = park; app.qa.unpark = unpark; app.qa.unparkAll = () => { for (const k of [...state.parked.keys()]) unpark(k); return true; };
    app.qa.parked = () => [...state.parked.values()].map(P => ({ stand: P.gate.name, icao: P.icao, type: P.type }));
    app.qa.gates = () => state.info;
    app.qa.gate = (name) => gateDetail(sys, byName.get(String(name)));
    // camera: a stand's bridge from the apron (side +1: the aircraft's left, where the bridges are)
    app.qa.bridgeView = (name, dist = 70, pitch = 20, side = 1, fov = 50) => {
      const g = byName.get(String(name)); if (!g) return false; const b = (g.bridges || [])[0];
      const tgt = b && b.rot ? [(b.rot[0] + g.nose[0]) / 2, state.G + 4, (b.rot[2] + g.nose[1]) / 2] : [g.nose[0], state.G + 4, g.nose[1]];
      const lf = [g.dir[1], -g.dir[0]]; const off = [g.dir[0] * 0.8 + lf[0] * 0.6 * side, g.dir[1] * 0.8 + lf[1] * 0.6 * side];
      app.qa.look(tgt, Math.atan2(off[0], -off[1]) * 180 / Math.PI, pitch, dist, fov); return true; };
    const list = (q.get('park') || '').split(',').map(s => s.trim()).filter(Boolean);
    const want = [];
    for (const it of list) {
      if (it === 'contact' || it === 'all') for (const g of state.gates) if (g.bridge) want.push([g.name, null]);
      if (it === 'remote' || it === 'all') for (const g of state.gates) if (!g.contact) want.push([g.name, null]);
      if (it !== 'contact' && it !== 'remote' && it !== 'all') { const [n, t] = it.split(':'); want.push([n, t || null]); }
    }
    for (const [n, t] of want) { const r = await park(n, t, false); if (!r.ok) console.warn('[gates] park', n, r.why); }
    if (want.length) console.log('[gates] DEBUG parked', state.parked.size, 'static aircraft');
    // (appended to whatever the core / other packages put in the legend slot)
    if (q.get('legend') === '1') { const prev = (app.ui.el && app.ui.el.legend && app.ui.el.legend.innerHTML) || ''; const mine = legendHtml(state.info);
      app.ui.setLegend(prev ? prev + '<br>' + mine.replace(/^<b>Observed \/ inferred<\/b><br>/, '') : mine); }
  },
  // light sprites: cab floodlights at night (photocell: the scene's night factor; inf), beacons flash while a bridge moves
  lights: (t, app) => {
    const sys = state.sys; if (!sys || !sys.sprites) return [];
    const night = ((app.R.extraCommon && app.R.extraCommon.uNight) || 0) > 0.5; const S = [];
    for (const s of sys.sprites) { if (s.night) { if (night) S.push(s); } else if (s.beacon) { if (s.moving) { const k = Math.pow(Math.max(0, Math.sin(t * 6.3)), 6); S.push({ ...s, i: 40 + 400 * k }); } } else S.push(s); }
    return S;
  },
});

// ---------------------------------------------------------------- statistics / diagnostics (QA, legend, report)
function gateStats(sys, gates, ms) {
  const B = []; for (const g of gates) for (const b of g.bridges || []) B.push({ g, b });
  const by = (f) => { const o = {}; for (const x of B) { const k = f(x); o[k] = (o[k] || 0) + 1; } return o; };
  const refDock = B.map(({ g, b }) => { const tk = { B: 'crj9', C: 'a321', CL: 'b753', D: 'b763', E: 'a333', EL: 'b77w', F: 'b748' }[g.cls]; const gp = { ...g, acType: tk, _lastType: tk, dockType: null, dock: null };
    let P = null; try { P = sys.makePlan(gp, b); } catch (e) { P = { ok: false, why: String(e.message) }; } return { stand: g.name, ok: !!P.ok, why: P.ok ? null : P.why }; });
  const vd = gates.filter(g => g.bridge).map(g => sys.vdgsSpot(g));
  const summary = {
    stands: gates.length, contact: gates.filter(g => g.contact).length, remote: gates.filter(g => !g.contact).length,
    bridges: B.length, bridgesObs: B.filter(x => x.b.src === 'obs').length, bridgesInf: B.filter(x => x.b.src !== 'obs').length,
    sharedAlt: gates.filter(g => g.sharesBridgesOf).length, vdgs: gates.filter(g => g.bridge).length,
    vdgsPosts: vd.filter(v => v.post).length, vdgsFacade: vd.filter(v => !v.post).length, vdgsBlocked: sys.vdgsBlocked || 0,
    models: by(x => x.b.modelUsed || 'default'), restAuto: B.filter(x => x.b.autoRest).length, restTurned: B.filter(x => x.b.restTurn).length, restBlocked: B.filter(x => x.b.restBlocked).length,
    rotundaShifted: B.filter(x => x.b.rotShift).length, rotundaMoved: B.filter(x => x.b.rotundaMoved).map(x => x.g.name + ':' + x.b.rotundaMoved), refTypeDocks: refDock.filter(r => r.ok).length, buildMs: Math.round(ms),
    departureLevels: Object.fromEntries(Object.entries(DEPARTURE_LEVELS).map(([k, v]) => [k, v.h])),
  };
  return { summary, refDock, bridges: B.map(({ g, b }) => gateBridge(g, b)) };
}
function gateBridge(g, b) {
  const r2 = (v) => v == null ? null : +v.toFixed(2);
  return { stand: g.name, cls: g.cls, gate: b.gate, src: b.src, status: g.bridgeStatus, model: b.modelUsed || null, modelWhy: b.modelWhy || null,
    opR: r2(b.m && b.m.opR), opE: r2(b.m && b.m.opE), dataReach: b.reachM, reachFlag: b.reachFlag, rotundaMoved: b.rotundaMoved || 0, walk: r2(b.walkLen), rotR: r2(b.rotR), rotShift: b.rotShift || 0,
    Hb: b.Hb, Hr: r2(b.Hr), slopeMax: r2(b.slopeMax), restAuto: !!b.autoRest, restE: r2(b.e0), restTurn: b.restTurn || 0, restBlocked: !!b.restBlocked, swingWide: b.swingWide || null,
    targets: (b._tg || []).length, stair: b.stairSide };
}
function gateDetail(sys, g) {
  if (!g) return null;
  return { name: g.name, cls: g.cls, area: g.area, contact: g.contact, bridgeStatus: g.bridgeStatus, remote: g.remote, service: g.service, shares: g.sharesBridgesOf,
    maxSpan: g.maxSpan, accepted: sys.acceptedTypes(g).map(a => a.icao), vdgs: g.bridge ? sys.vdgsSpot(g) : null, sign: g.bridge ? null : sys.remoteSpot(g),
    bridges: (g.bridges || []).map(b => gateBridge(g, b)), occupant: g.acType || null };
}
function legendHtml(I) {
  const s = I.summary;
  return '<b>Observed / inferred</b><br>Stands: OpenStreetMap stop nodes (observed); class and stop as nose tip inferred.<br>' +
    `Jet bridges: ${s.bridgesObs} seen on SAR (observed), ${s.bridgesInf} from OSM gate nodes only (inferred), drawn alike; ` +
    'bridge model, rest pose, levels, VDGS position and GSE inferred. Stand signs: CAAC MH 5001-2021 8.5.';
}
