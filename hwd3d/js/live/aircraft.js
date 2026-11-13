// Aircraft views (hwd3d Phase 2, P3; fork map 2.9). Replaces sfo3d/js/live/aircraft.js @ a967f9b (LiveAircraft: imported
// airliner models + procedural airliner + liveries), which is not forked: Phase 2 draws every aircraft as a GA placeholder
// (js/aircraft/placeholder.js) sized from its dimension record; real models are Phase 3.
//
//   new AircraftViews(scene, { quality })
//   .sync(traffic, now, { nightF, selectedKey, dt })   creates / updates / removes one drawable per drawn track: position =
//        the traffic body (main-gear contact; on the ground y = site.groundY, set by traffic.js), heading (deg true) ->
//        fwd, pitch / roll, gear, rotor spin, light states (js/env/aircraft_lights.js aircraftLightStates)
//   .get(key) -> GaAircraft | null ;  .modelNote(tr) -> text ;  .dispose()
// A track is drawn when disp.valid, inside the D6 window (tr.inView), not hidden (hangared) and its fade alpha > 0.5 (the
// obj program has no alpha: the 0.4-s fades of traffic.js become a cut at their midpoint).
import { GaAircraft } from '../aircraft/placeholder.js';
import { dimsNote } from '../aircraft/ga_dims.js';
import { aircraftLightStates } from '../env/aircraft_lights.js';

const D2R = Math.PI / 180, KT = 1852 / 3600, FT = 0.3048;
// GA display phases -> the light-state vocabulary of aircraft_lights.js lightPhase
const LIGHT_PHASE = { parked: 'parked', hangared: 'parked', taxi: 'taxi', runup: 'holding', hold_short: 'holding', line_up: 'lineup', runway_taxi: 'taxi',
  takeoff_roll: 'takeoff', landing_roll: 'rollout', touch_and_go: 'rollout', stop_and_go: 'rollout', heli_ground: 'holding', vehicle: 'vehicle' };

export class AircraftViews {
  constructor(scene, { quality = 'high' } = {}) { this.scene = scene; this.quality = quality; this.map = new Map(); this.t = 0; }
  sync(traffic, now, { nightF = 0, selectedKey = null, dt = 1 / 30 } = {}) {
    const seen = new Set();
    for (const tr of traffic.tracks.values()) {
      const D = tr.disp;
      if (!D.valid || !tr.inView || tr.hidden || !(D.alpha > 0.5) || !tr.dims) continue;
      seen.add(tr.key);
      let v = this.map.get(tr.key);
      if (v && v.T !== tr.dims) { this.scene.remove(v); v.dispose(); v = null; }   // type resolved later: new placeholder
      if (!v) { v = new GaAircraft(tr.dims, { id: tr.key, lodDist: this.quality === 'low' ? 4000 : 8000, shadowDist: this.quality === 'low' ? 1200 : 2500 }); this.map.set(tr.key, v); this.scene.add(v); }
      v.pos = [D.x, D.y, D.z];
      v.fwd = [Math.sin(D.hdg * D2R), 0, -Math.cos(D.hdg * D2R)];
      v.pitch = D.pitch || 0; v.roll = D.roll || 0; v.gear = D.gear ?? 1; v.selected = tr.key === selectedKey;
      const heli = tr.dims.cls === 'heli';
      v.rotor = heli ? (!D.ground || D.gs > 0.5 || ['heli_hover', 'heli_hover_taxi'].includes(tr.phase) ? 40 : 0) : 0;   // ~380 rpm [inf]
      v.step(dt);
      const altAgl = traffic.groundY ? D.y - traffic.groundY(D.x, D.z) : 0;
      const ph = LIGHT_PHASE[tr.phase] || (D.ground ? 'taxi' : 'climb');
      v.lightsOn = aircraftLightStates({ phase: ph, ground: D.ground, gs: D.gs / KT, altAgl, stale: tr.stale });
      v.visible = true;
    }
    for (const [k, v] of this.map) if (!seen.has(k)) { this.scene.remove(v); v.dispose(); this.map.delete(k); }
  }
  get(key) { return this.map.get(key) || null; }
  modelNote(tr) { return dimsNote(tr && tr.dims); }
  dispose() { for (const v of this.map.values()) { this.scene.remove(v); v.dispose(); } this.map.clear(); }
}
