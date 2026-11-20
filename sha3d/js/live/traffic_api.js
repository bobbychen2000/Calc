// sha3d: the traffic functions the UI needs (phase label, list category, stand label). Phase 2 stubs: there is no traffic
// engine yet. The Phase 3 traffic package replaces this file's body with re-exports from its engine, e.g.
//   export { phaseLabel, category, gateLabel } from './traffic.js';
// (sfo3d@e3218d6 js/live/ui.js imported them from its js/live/traffic.js.)
export const phaseLabel = (tr) => (tr && tr.phase) || '';
export const category = (tr) => (tr && tr.cat) || 'other';
export const gateLabel = (g) => (g && (g.label || g.name)) || '';
