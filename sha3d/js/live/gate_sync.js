// SHA Live 3D, Phase 3 package E: the gate and time adapter between the traffic simulator and the gate engine.
// Design: docs/phase3/design.md §1.5 (gate engine coupling), §4.3 (bridges, stairs, bus, service windows), §6.4 (gate
// rebuilds), §7.1 (frozen interface); report: docs/phase3/gates_time.md.
//
//   createGateSync(gateSys, gates, opts) -> { apply(events, tB), resetTo(t, standStates), info(),
//                                              attach(nowFn), detach(), check(n), standPose(name, typeKey), engineGate(name) }
//
// The sim (js/sim/sim.js, C1) is the authority on what happens at a stand and when; this adapter turns that into the gate
// engine's calls (js/live/gate_system.js LiveGateSystem) so that the bridges, the VDGS face, the stairs, buses and GSE
// follow it:
//   sim event                  engine call (all at the event's own sim time t, integer ms)
//   'onblock'  (remote stand)  dockAt(g, typeKey, t, pose, icao)    stairs + bus + GSE at the aircraft (no bridge)
//   'dock'     (contact stand) dockAt(...)                          bridges dock: DOCK_DELAY 12 s + the path at the
//                                                                    sheet's rates (on-block + 20 s in the sim's rules)
//   'undock'                   undockAt(g, t) = undockEarly         the bridges retract at the sheet's rates; the aircraft
//                                                                    stays the occupant for the neighbours (g._early)
//   'pushstart'                pushAt(g, t)                         setOccupant(g, null); a retraction still running
//                                                                    finishes at the maximum rates (hurryUndock)
//   'service' (data.mode)      setService(g, 'turn' | 'cold', t)    a cold stand: no GSE, stairs or bus (review M7)
//   'docked' 'pushend' 'offblock' 'takeoff' 'touchdown' 'switch'    no engine call (counted)
// Fields read from an event: t, kind, stand (the sim stand name; 238A / 259A use the base stand's bridges with their own
// pose, as the DEBUG park does), mv, and data: {typeKey | icao, freighter, pose: {nose: [x, z], dir: [dx, dz]}, mode}. A
// missing typeKey is looked up through opts.movement(mv) (the DayPlan movement: typeKey, icao); a missing pose is the
// engine's stop convention (standTip: the nose wheel on the stop node, CLAUDE.md "Conventions").
//
// resetTo(t, standStates) (design §1.4: every backward jump and every forward jump > 120 s) rebuilds the engine state of
// a forward play at t from the sim's StandState per stand (§7.1: {af, typeKey, icao, freighter, pose, state: 'empty' |
// 'docking' | 'docked' | 'early' | 'pushing', since, service}); the optional fields tDock, tUndock, tPush (ms, sim) and
// prev ({typeKey, icao, pose, freighter, tDock, tUndock, tPush}: the occupant that left last, whose departure hold may
// still keep the neighbours' bridges parked) make it exact; without them they come from `since` and the gate-timing
// table (tDock = since - dock_s for 'docked', tUndock = since - max(150 s, undock_s + 15 s) for 'pushing').
//
// While attached (attach(nowFn), or opts.now): the engine's clock is the sim clock (gateSys.now(), read by js/scene.js),
// its timers are retired at their own due times (advance) and its static set is built per stand with caches
// (buildChunked: a change rebuilds the stand and its neighbours only); the GSE keep-out is every aircraft the engine
// knows at the stands (occupantFootprints). DEBUG ?park= aircraft and traffic exclude each other (design §6.3): attach()
// refuses while any is parked, and SHA.qa.park refuses while traffic runs. detach() restores Date.now() and Phase 2's build.
import { TYPES, ICAO_TYPES } from '../aircraft/types.js';
import { standTip, EV_ORDER, RESET_HORIZON_S } from './gate_system.js';
import { gateTimes } from './gates.js';

// sim rules that use the table (design §1.5, §4.3; inf): the bridges dock 20 s after on-block (sfo3d DOCK_WAIT_MS) and
// undock max(150 s, undock_s + 15 s) before off-block
export const DOCK_AFTER_ONBLOCK_S = 20, UNDOCK_LEAD_MIN_S = 150, UNDOCK_LEAD_MARGIN_S = 15;
export const undockLeadS = (row) => Math.max(UNDOCK_LEAD_MIN_S, (row ? row[1] : 0) + UNDOCK_LEAD_MARGIN_S);
const CALL = { onblock: 'dock', dock: 'dock', undock: 'undock', pushstart: 'push', service: 'service' };
const ICAO_OF = {}; for (const [icao, k] of Object.entries(ICAO_TYPES)) if (!ICAO_OF[k]) ICAO_OF[k] = icao;

export function createGateSync(gateSys, gates, opts = {}) {
  const sys = gateSys; if (!sys) throw new Error('gate_sync: no gate engine');
  gates = gates || sys.gates;
  const byName = new Map(gates.map(g => [g.name, g]));
  const engByName = new Map(sys.gates.map(g => [g.name, g]));
  const gi = new Map(sys.gates.map((g, i) => [g, i]));
  let table = opts.gateTimes || (typeof window !== 'undefined' && window.SHA_GATE_TIMES) || null;
  const movement = typeof opts.movement === 'function' ? opts.movement : null;
  const mirror = new Map();     // sim stand name -> its state as this adapter last set it
  const C = { applied: 0, ignored: 0, missing: 0, unknownStand: 0, conflicts: 0, resets: 0, byKind: {} };
  let attached = false, prevFoot = null, checkRes = null, lastApplyMs = 0;

  const engineGate = (nameOrG) => { const g = typeof nameOrG === 'object' ? nameOrG : byName.get(String(nameOrG)); if (!g) return null;
    const e = engByName.get(g.name) || g; return e.sharesBridgesOf ? (engByName.get(e.sharesBridgesOf) || e) : e; };
  const standPose = (name, typeKey) => { const g = typeof name === 'object' ? name : byName.get(String(name)); const T = TYPES[typeKey]; if (!g || !T) return null;
    const tip = standTip(g, T); return { nose: [tip[0], tip[2]], dir: g.dir.slice() }; };
  const row = (name, tk) => { const S = table && table.stands; const r = S && S[name] && S[name][tk]; return r || null; };
  const typeOf = (ev) => { const d = ev.data || {}; let tk = d.typeKey || ev.typeKey || null, icao = d.icao || ev.icao || null, fr = !!(d.freighter || ev.freighter);
    if ((!tk || !icao) && movement && ev.mv) { const m = movement(ev.mv); if (m) { tk = tk || m.typeKey || (m.model && ICAO_TYPES[m.model]) || (m.icao && ICAO_TYPES[m.icao]) || null; icao = icao || m.icao || null; fr = fr || !!m.freighter; } }
    if (!tk && icao) tk = ICAO_TYPES[icao] || null;
    return { tk: tk && TYPES[tk] ? tk : null, icao: icao || (tk && ICAO_OF[tk]) || null, freighter: fr }; };

  // ---- events (forward play)
  function apply(events, tB = null) {
    const p0 = performance.now();
    const list = [];
    for (const ev of events || []) {
      if (!ev || !Number.isFinite(ev.t)) continue; C.byKind[ev.kind] = (C.byKind[ev.kind] || 0) + 1;
      const call = CALL[ev.kind]; const g = byName.get(String(ev.stand)); const eg = g ? engineGate(g) : null;
      if (!call) { trackOnly(ev); C.ignored++; continue; }
      if (!eg) { C.unknownStand++; continue; }
      if (ev.kind === 'onblock' && eg.bridge) { trackOnly(ev); continue; }     // (a contact stand docks on the 'dock' event)
      list.push({ t: Math.floor(ev.t), call, ev, g, eg });
    }
    list.sort((a, b) => (a.t - b.t) || (EV_ORDER[a.call] - EV_ORDER[b.call]) || (gi.get(a.eg) - gi.get(b.eg)));
    for (const x of list) {
      sys.advance(x.t); sys.step(Math.max(x.t, sys._now ?? x.t));
      const name = x.g.name, M = mirror.get(name) || { state: 'empty' };
      if (x.call === 'dock') {
        const ty = typeOf(x.ev); if (!ty.tk) { C.missing++; continue; }
        if (M.state !== 'empty' && M.mv != null && M.mv === x.ev.mv && M.typeKey === ty.tk) { C.applied++; continue; }   // (onblock + dock at a remote stand)
        const pose = (x.ev.data && x.ev.data.pose) || standPose(x.g, ty.tk);
        sys.dockAt(x.eg, ty.tk, x.t, pose, ty.icao, { freighter: ty.freighter }, true);
        mirror.set(name, { state: x.eg.bridge ? 'docking' : 'docked', since: x.t, tDock: x.t, typeKey: ty.tk, icao: ty.icao, freighter: ty.freighter, pose, mv: x.ev.mv || null, af: (x.ev.data && x.ev.data.af) || null, service: 'turn', prev: M.prev || null });
      } else if (x.call === 'undock') {
        sys.undockAt(x.eg, x.t, true); if (M.state !== 'empty') mirror.set(name, { ...M, state: x.eg.bridge ? 'early' : M.state, since: x.t, tUndock: x.t });
      } else if (x.call === 'push') {
        sys.pushAt(x.eg, x.t, true); if (M.state !== 'empty') mirror.set(name, { ...M, state: 'pushing', since: x.t, tPush: x.t });
      } else if (x.call === 'service') {
        const mode = (x.ev.data && x.ev.data.mode) || x.ev.mode; sys.setService(x.eg, mode, x.t); if (M.state !== 'empty') mirror.set(name, { ...M, service: mode === 'cold' ? 'cold' : 'turn' });
      }
      C.applied++;
    }
    if (Number.isFinite(tB)) sys.advance(Math.floor(tB));
    lastApplyMs = performance.now() - p0;
    return { applied: list.length, ms: +lastApplyMs.toFixed(2) };
  }
  function trackOnly(ev) {   // docked / pushend: the adapter's own mirror (info, a later resetTo without prev)
    const M = mirror.get(String(ev.stand)); if (!M) return;
    if (ev.kind === 'docked' && M.state === 'docking') mirror.set(String(ev.stand), { ...M, state: 'docked', since: Math.floor(ev.t) });
    if ((ev.kind === 'pushend' || ev.kind === 'offblock') && M.state === 'pushing') mirror.set(String(ev.stand), { state: 'empty', since: Math.floor(ev.t), prev: { typeKey: M.typeKey, icao: M.icao, pose: M.pose, freighter: M.freighter, tDock: M.tDock, tUndock: M.tUndock ?? null, tPush: M.tPush } });
  }

  // ---- jumps
  function entries(S) {
    if (!S) return [];
    if (S instanceof Map) return [...S.entries()];
    if (Array.isArray(S)) return S.map(s => Array.isArray(s) ? s : [s.stand || s.name, s]);
    return Object.entries(S);
  }
  function occupantOf(name, s) {
    const g = byName.get(String(name)); if (!g) { C.unknownStand++; return null; }
    const eg = engineGate(g);
    const lift = (o, st) => {
      const tk = o.typeKey || (o.icao && ICAO_TYPES[o.icao]) || null; if (!tk || !TYPES[tk]) return null;
      const r = row(g.name, tk); const since = Number.isFinite(o.since) ? Math.floor(o.since) : null;
      const tDock = o.tDock ?? (st === 'docking' ? since : st === 'docked' && r && since != null ? since - Math.round(r[0] * 1000) : null);
      const tPush = o.tPush ?? (st === 'pushing' ? since : null);
      const tUndock = o.tUndock ?? (st === 'early' ? since : st === 'pushing' && tPush != null && eg.bridge ? tPush - undockLeadS(r) * 1000 : null);
      return { typeKey: tk, icao: o.icao || ICAO_OF[tk] || null, freighter: !!o.freighter, pose: o.pose && o.pose.nose ? { nose: o.pose.nose.slice(), dir: o.pose.dir.slice() } : standPose(g, tk), tDock, tUndock, tPush };
    };
    const st = s && s.state ? s.state : 'empty';
    const cur = st !== 'empty' ? lift(s, st) : null; const prev = s && s.prev ? lift(s.prev, 'gone') : null;
    if (st !== 'empty' && !cur) C.missing++;
    return { name: g.name, g, eg, occ: { gate: eg, state: cur ? st : 'empty', ...(cur || {}), service: s && s.service, prev }, sim: s };
  }
  function resetTo(t, standStates, ropts = {}) {
    t = Math.floor(t);
    const used = new Map(); const score = (o) => o.occ.state !== 'empty' ? 2 : o.occ.prev ? 1 : 0;
    for (const [name, s] of entries(standStates)) {
      const o = occupantOf(name, s); if (!o) continue;
      const k = o.eg.id; const prior = used.get(k);
      if (!prior) { used.set(k, o); continue; }
      // (238 and 238A on one bridge set: the later occupant wins; the sim's exclusive pairs should prevent it)
      if (score(o) === 2 && score(prior) === 2) { C.conflicts++; if ((o.occ.tDock ?? -Infinity) >= (prior.occ.tDock ?? -Infinity)) used.set(k, o); continue; }
      if (score(o) > score(prior)) used.set(k, o);
    }
    const L = [...used.values()];
    const r = sys.resetTo(t, L.map(o => o.occ), ropts);
    mirror.clear();
    for (const o of L) { const c = o.occ; if (c.state === 'empty' && !c.prev) continue;
      mirror.set(o.name, { state: c.state, since: o.sim && Number.isFinite(o.sim.since) ? Math.floor(o.sim.since) : t, typeKey: c.typeKey, icao: c.icao, freighter: c.freighter, pose: c.pose,
        tDock: c.tDock, tUndock: c.tUndock, tPush: c.tPush, service: c.service === 'cold' ? 'cold' : 'turn', mv: o.sim && o.sim.mv || null, af: o.sim && o.sim.af || null, prev: c.prev }); }
    C.resets++; return r;
  }

  // ---- the engine's clock and build while traffic runs
  function attach(nowFn) {
    if (attached) return { ok: true, already: true };
    const nDbg = typeof sys.debugParkCount === 'function' ? sys.debugParkCount() : 0;
    if (nDbg > 0) return { ok: false, why: `DEBUG ?park= has ${nDbg} static aircraft: traffic and the DEBUG park exclude each other (design §6.3)` };
    if (opts.check !== false && !checkRes && table) checkRes = check(opts.check || 5);
    sys.setTimeSource(typeof nowFn === 'function' ? nowFn : () => Date.now());
    sys.setChunked(opts.chunked !== false);
    prevFoot = sys.aircraftFootprints; sys.aircraftFootprints = () => sys.occupantFootprints();
    attached = true; sys.dirty = true; return { ok: true, check: checkRes };
  }
  function detach() {
    if (!attached) return false;
    sys.resetTo(Date.now(), []); sys.setTimeSource(null); sys.setChunked(false); sys.aircraftFootprints = prevFoot; prevFoot = null;
    mirror.clear(); attached = false; sys.dirty = true; return true;
  }
  // the boot check (design §1.5): n stands of the table re-measured on this engine (it must be idle - no occupant - and is
  // left empty): the class reference and one more type per stand; display only, the sim keeps the table
  function check(n = 5, keysPer = 2) {
    if (!table || !table.stands) return { ok: false, why: 'no gate-timing table' };
    const names = Object.keys(table.stands).sort(); if (!names.length) return { ok: false, why: 'empty table' };
    const pick = []; const step = names.length / Math.max(1, n); for (let i = 0; i < n && i < names.length; i++) pick.push(names[Math.floor(i * step + step / 2) % names.length]);
    const want = {}; for (const s of pick) { const ks = Object.keys(table.stands[s]).sort(); const ref = { B: 'crj9', C: 'a321', CL: 'b753', D: 'b763', E: 'a333', EL: 'b77w', F: 'b748' }[(byName.get(s) || {}).cls];
      const chosen = []; if (ref && ks.includes(ref)) chosen.push(ref); for (let j = 0; chosen.length < keysPer && j < ks.length; j++) { const k = ks[(j * 7 + s.length) % ks.length]; if (!chosen.includes(k)) chosen.push(k); } want[s] = chosen; }
    const p0 = performance.now(); let live;
    try { live = gateTimes(sys, pick.map(s => byName.get(s)).filter(Boolean), (g) => want[g.name] || []); }
    catch (e) { return { ok: false, why: String(e && e.message || e) }; }
    const mism = []; let agree = 0, n2 = 0, maxDiff = 0;
    for (const s of pick) for (const k of want[s]) { const a = table.stands[s][k], b = live.stands[s] && live.stands[s][k]; n2++;
      if (!b) { mism.push({ stand: s, key: k, table: a, live: null }); continue; }
      const d = Math.max(...a.map((v, i) => Math.abs(v - b[i]))); maxDiff = Math.max(maxDiff, d);
      if (d === 0) agree++; else mism.push({ stand: s, key: k, table: a, live: b }); }
    const res = { ok: mism.length === 0, stands: pick, entries: n2, agree, mismatches: mism, maxDiffS: +maxDiff.toFixed(3), ms: Math.round(performance.now() - p0), inputs: table.inputs_sha256_16 || null };
    if (!res.ok) try { console.warn('[gate_sync] boot check: the gate-timing table differs from this engine at ' + mism.length + ' of ' + n2 + ' sampled entries (display only; the sim keeps the table): ' + JSON.stringify(mism.slice(0, 3))); } catch (e) { }
    return res;
  }
  function info() {
    const states = {}; let cold = 0; for (const M of mirror.values()) { states[M.state] = (states[M.state] || 0) + 1; if (M.service === 'cold' && M.state !== 'empty') cold++; }
    return { v: 1, src: 'inf', attached, now: sys.now(), traffic: sys.trafficRunning(), chunked: !!sys._chunked, stands: mirror.size, states, cold,
      counts: { ...C, byKind: { ...C.byKind } }, lastApplyMs: +lastApplyMs.toFixed(2), lastReset: sys.lastReset || null, lastBuild: sys.lastBuild || null, check: checkRes,
      table: table ? { inputs_sha256_16: table.inputs_sha256_16 || null, stands: Object.keys(table.stands || {}).length, entries: Object.values(table.stands || {}).reduce((n, o) => n + Object.keys(o).length, 0) } : null,
      horizonS: RESET_HORIZON_S, advanceStuck: sys._advanceStuck || 0 };
  }
  const api = { apply, resetTo, info, attach, detach, check, standPose, flushGse: () => sys.flushGse(), engineGate: (n) => engineGate(n), mirror: () => new Map(mirror), setTable: (T) => { table = T; checkRes = null; }, row };
  if (typeof opts.now === 'function') api.attachResult = attach(opts.now);
  return api;
}
