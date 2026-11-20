// forked from sfo3d@e3218d6 js/env/presets.js
// Real-weather presets for the ?wx=<id> QA hook and the snapshot-mode archived reports. sfo3d's were KSFO reports
// (data/sfo_env_presets.js); sha3d has none yet: a ZSSS preset set (IEM archive, docs/phase1/sources_sim.md s.3) can be
// generated into data/ later and imported here. Same exports as the sfo3d module; all empty.
export const ENV_PRESETS = [];
// sha3d: the snapshot mode's recorded reports come from data/sha_snapshot.js (tools/live/build_snapshot.py), injected by
// js/live/entry.js through setSnapshotWx() before js/env/app_env.js reads them (live bindings: never imported data at
// module scope, arch.md R4). SNAPSHOT_METARS = raw report strings, SNAPSHOT_TAFS = [{issued (ISO), raw}].
export let SNAPSHOT_TAF = null;
export let SNAPSHOT_TAFS = [];
export let SNAPSHOT_METARS = [];
export function setSnapshotWx({ metars = [], tafs = [] } = {}) {
  SNAPSHOT_METARS = metars.map(m => typeof m === 'string' ? m : m.rawOb || m.raw).filter(Boolean);
  SNAPSHOT_TAFS = tafs.filter(t => t && t.raw && t.issued).map(t => ({ issued: t.issued, raw: t.raw }));
  SNAPSHOT_TAF = SNAPSHOT_TAFS.slice().sort((a, b) => (a.issued < b.issued ? 1 : -1))[0] || null;
}
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
