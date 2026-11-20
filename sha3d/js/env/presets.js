// forked from sfo3d@e3218d6 js/env/presets.js
// Real-weather presets for the ?wx=<id> QA hook and the snapshot-mode archived reports. sfo3d's were KSFO reports
// (data/sfo_env_presets.js); sha3d has none yet: a ZSSS preset set (IEM archive, docs/phase1/sources_sim.md s.3) can be
// generated into data/ later and imported here. Same exports as the sfo3d module; all empty.
export const ENV_PRESETS = [];
export const SNAPSHOT_TAF = null;
export const SNAPSHOT_TAFS = [];
export const SNAPSHOT_METARS = [];
/** The latest snapshot TAF issued at or before t (ms). */
export function snapshotTafAt(t) {
  let best = null; for (const x of SNAPSHOT_TAFS || []) if (Date.parse(x.issued) <= t && (!best || x.issued > best.issued)) best = x;
  return best;
}
export const presetById = (id) => ENV_PRESETS.find(p => p.id === id) || null;
/** The preset's runway configuration input in the EnvState runway shape. */
export function presetRunway(p) {
  const r = p && p.runway_config_input; if (!r) return null;
  return { arr: { ...r.arr }, dep: (r.dep || []).slice(), source: 'preset input (' + p.id + '): ' + (r.note || ''), tag: 'I' };
}
