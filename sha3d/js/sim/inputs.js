// SHA Live 3D Phase 3 (package P3-A): access to the committed day-plan inputs (data/sha_sim_inputs.js ->
// window.SHA_SIM_INPUTS, built by tools/sim/build_sim_inputs.py). Pure ES module (node + browser); nothing is imported at
// module scope from window data (arch.md R4): the global is read only when simInputs(win) is called.
// Design: docs/phase3/design.md s.2.1, s.7.1 (SimInputs, frozen interface: fields may be added, never renamed).

const H = 3600000, DAY = 86400000;

/** simInputs(win = globalThis) -> SimInputs (the object of window.SHA_SIM_INPUTS, validated); throws if absent / wrong v */
export function simInputs(win = globalThis) {
  const I = win && win.SHA_SIM_INPUTS;
  if (!I || I.v !== 1) throw new Error('SHA_SIM_INPUTS v1 missing (load data/sha_sim_inputs.js)');
  for (const k of ['profile', 'totals', 'weights', 'typeMix', 'turnaround', 'terminals', 'delays', 'published', 'notams', 'params'])
    if (!(k in I)) throw new Error('SHA_SIM_INPUTS: missing ' + k);
  return I;
}

/** 'YYYY-MM-DD' -> [t0, t1] ms of the operating day (04:00 local UTC+8 -> 04:00 next day = 20:00Z (D-1) .. 20:00Z (D)) */
export function dayWindow(day, inputs) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(day || '');
  if (!m) throw new Error('bad day ' + day);
  const P = (inputs && inputs.params) || {};
  const off = P.utcOffsetH ?? 8, start = P.dayStartLocalH ?? 4;
  const t0 = Date.UTC(+m[1], +m[2] - 1, +m[3]) + (start - off) * H;
  return [t0, t0 + DAY];
}

/** operating day 'YYYY-MM-DD' of an instant (ms) */
export function dayOf(tMs, inputs) {
  const P = (inputs && inputs.params) || {};
  const d = new Date(tMs + ((P.utcOffsetH ?? 8) - (P.dayStartLocalH ?? 4)) * H);
  return d.toISOString().slice(0, 10);
}

/** local hour (UTC+8) 0..23 of an instant */
export const localHour = (tMs, inputs) => Math.floor((((tMs + ((inputs && inputs.params && inputs.params.utcOffsetH) ?? 8) * H) % DAY) + DAY) % DAY / H);

/** start (ms) of local hour h within the operating day starting at t0 */
export function hourStart(t0, h, inputs) {
  const start = (inputs && inputs.params && inputs.params.dayStartLocalH) ?? 4;
  return t0 + (((h - start) % 24 + 24) % 24) * H;
}

/** daily movement total for a day (the totals row whose [from, to] contains it) */
export function totalFor(inputs, day) {
  for (const r of inputs.totals || []) if (day >= r.from && day <= r.to) return r;
  const L = inputs.totals || [];
  return L.length ? L[L.length - 1] : { perDay: 783.4, basis: 'default' };
}

/** NOTAM records active at t (ms) of a kind */
export function notamsAt(notams, tMs, kind) {
  const out = [];
  for (const n of notams || []) {
    if (kind && n.kind !== kind) continue;
    for (const w of n.windows || []) if (tMs >= w[0] && tMs < w[1]) { out.push(n); break; }
  }
  return out;
}

/** no landing possible at t: 18L/36R closed by a NOTAM (F4551) while 18R/36L takes no landings 1600-2300 UTC (AIP (mirror)
 *  AD 2.20 2.1.6, as js/env/wx/metar_zsss.js assignRunways), or both runways closed */
export function noLandingAt(notams, tMs) {
  const closed = notamsAt(notams, tMs, 'rwy_closed').map(n => n.target && n.target.runway).filter(Boolean);
  const noLand = notamsAt(notams, tMs, 'rwy_no_landing').map(n => n.target && n.target.runway).filter(Boolean);
  const east = closed.includes('18L/36R') || noLand.includes('18L/36R');
  const west = closed.includes('18R/36L') || noLand.includes('18R/36L');
  const h = new Date(tMs).getUTCHours(), westNight = h >= 16 && h < 23;
  return east && (west || westNight);
}

/** stands closed at any time in [a, b) -> Set of stand names */
export function closedStands(notams, a, b) {
  const s = new Set();
  for (const n of notams || []) {
    if (n.kind !== 'stand_closed' || !n.target || !n.target.stand) continue;
    for (const w of n.windows || []) if (w[0] < b && w[1] > a) { s.add(String(n.target.stand)); break; }
  }
  return s;
}
