// sha3d airfield-lighting controller: PLACEHOLDER (inf). sfo3d@e3218d6 js/env/lighting/controller.js implemented the FAA
// JO 7110.65 chapter 3-4 intensity rules for SFO's fixtures; FAA lighting rules must not run in sha3d, so it is not
// forked. Until the airfield-lighting package builds the ZSSS systems from the AIP (mirror) AD 2.14 facts (PALS CAT I,
// PAPI 3 deg, RCLL, REDL, RWSL, stop bars) and CAAC MH 5001-2021 (docs/phase1/standards_refs.md), nothing is switched.
// Same exported names and return shape as the sfo3d module, so js/env/state.js keeps working.
export function controllerFromEnv(st) {
  return { systems: {}, night: !!(st && st.towerNight), note: 'airfield lighting not modelled (sha3d Phase 2 placeholder)', tag: 'inf' };
}
export function controllerHud(c) { return c && c.note ? c.note : 'not modelled'; }
export const RUNWAY_OF = {};
export const MITL_PCT = {};
