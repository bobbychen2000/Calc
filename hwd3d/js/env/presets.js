// KHWD weather presets for the ?wx=<id> QA hook (replaces sfo3d/js/env/presets.js + data/sfo_env_presets.js @ a967f9b,
// which hold KSFO reports and TAFs). Phase 2: no KHWD presets yet (fork map 1.4: "replace (empty, or KHWD presets
// later)"); no KHWD TAF exists (aviationweather.gov taf?ids=KHWD returns [], fork map measurements), so there are no
// snapshot TAFs. The interface is sfo3d's, so js/env/app_env.js works unchanged.
export const ENV_PRESETS = [];
export const SNAPSHOT_TAF = null, SNAPSHOT_TAFS = [], SNAPSHOT_METARS = [];
export function presetById(id) { return ENV_PRESETS.find(p => p.id === id) || null; }
export function presetRunway(p) { return p && p.rwy ? p.rwy : null; }
export function snapshotTafAt() { return null; }
