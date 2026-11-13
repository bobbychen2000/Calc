// Live airfield statistics from the traffic engine's own events (hwd3d Phase 2, P4). Forked from sfo3d/js/live/stats.js
// @ a967f9b. Kept: counts from the engine's events at DISPLAY time only (an event later than the scene time is not shown
// yet, so the panel never runs ahead of the 3-D view), "this page only knows what it has seen since it opened", one
// compact line plus a full sheet, rows that select the aircraft. Changed (fork map 2.8): the HWD event kinds of P3's
// classifier (TrafficEvent: takeoff, landing, touch_and_go, stop_and_go, go_around, low_pass, runway_taxi, lift_off,
// touch_down, hover_taxi, runup, line_up, park, unpark, hangar_in, hangar_out, scope_hwd, overflight) instead of the
// airliner touchdown / liftoff / in-block set; movements per runway END (10L, 28R, 10R, 28L) per hour; touch-and-goes
// and circuits with the median interval between one aircraft's consecutive runway contacts (the Phase 1 recording's
// median circuit is 239.5 s, refs/cache/adsb/hwd_events.json, fork map 2.8); helicopter operations; operations while the
// tower is closed (outside 07:00-21:00 local, FAA NASR; the event's own `tower` field, else classifier.js towerStatus);
// the status line is the traffic count by display-phase group (the "compact status line" of the Phase 2 brief).
// Identity: an event carries no identity (P3 contract); the sheet names an aircraft by its CURRENT ident.label (type
// only when masked, D1) through `nameOf`, and rows carry an opaque per-page id (`idOf`), never the track key.
// Dropped: runway occupancy / taxi times / rejected take-offs / configuration from airliner events, SFO's 4 runways.
import { PHASES, towerStatus } from './classifier.js';

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const median = (a) => { if (!a.length) return null; const s = a.slice().sort((p, q) => p - q); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
export const ENDS = ['28L', '28R', '10R', '10L'];
const RUNWAY_KINDS = ['takeoff', 'landing', 'touch_and_go', 'stop_and_go', 'go_around', 'low_pass'];
const CONTACT = new Set(['touch_and_go', 'stop_and_go', 'low_pass', 'go_around']);   // one circuit ends with one of these
const HELI_KINDS = ['lift_off', 'touch_down', 'hover_taxi'];
// display-phase groups for the status line (classifier.js PHASES groups, merged for a phone-width line)
export const GROUPS = [
  { id: 'pattern', label: 'pattern', test: (tr) => PHASES[tr.phase] && PHASES[tr.phase].group === 'pattern' },
  { id: 'runway', label: 'runway', test: (tr) => PHASES[tr.phase] && PHASES[tr.phase].group === 'runway' },
  { id: 'taxi', label: 'taxi', test: (tr) => ['taxi', 'runup', 'hold_short'].includes(tr.phase) },
  { id: 'parked', label: 'parked', test: (tr) => tr.phase === 'parked' || tr.phase === 'hangared' },
  { id: 'heli', label: 'heli', test: (tr) => PHASES[tr.phase] && PHASES[tr.phase].group === 'heli' },
  { id: 'area', label: 'arr/dep', test: (tr) => tr.phase === 'departing' || tr.phase === 'arriving' },
  { id: 'over', label: 'overflight', test: (tr) => tr.phase === 'overflight' || (tr.scope === 'overflight' && !(PHASES[tr.phase] && PHASES[tr.phase].group === 'ground')) },
];
/** traffic counts by phase group, over the tracks that are drawn (or remembered parked / in a hangar) */
export function phaseCounts(tracks) {
  const c = Object.fromEntries(GROUPS.map(g => [g.id, 0])); let n = 0, other = 0;
  for (const tr of tracks) {
    if (tr.vehicle || tr.removed) continue;
    if (!(tr.disp && tr.disp.valid && tr.inView) && !(tr.stale && tr.park)) continue;
    n++; const g = GROUPS.find(G => G.test(tr)); if (g) c[g.id]++; else other++;
  }
  return { counts: c, total: n, other };
}
export function statusLine(pc) {
  const parts = GROUPS.filter(g => pc.counts[g.id]).map(g => `${pc.counts[g.id]} ${g.label}`);
  if (pc.other) parts.push(`${pc.other} other`);
  return parts.length ? parts.join(' · ') : 'No traffic in view yet';
}

/** events seen up to scene time `now` (engine clock ms), in the last `windowMs` */
export function hwdStats(events, now, windowMs = 3600e3, towerOf = (e) => e.tower || towerStatus(e.t)) {
  const t0 = now - windowMs; const ends = {}; const heli = { lift_off: 0, touch_down: 0, hover_taxi: 0 }; const after = { n: 0, kinds: {} };
  const lastContact = new Map(); const circuits = []; let since = null, tg = 0, runups = 0; const recent = [];
  for (const e of events) {
    if (e.t > now) continue;
    if (since == null || e.t < since) since = e.t;
    const isRw = RUNWAY_KINDS.includes(e.kind) && e.rwy;
    // circuits: the interval between one aircraft's consecutive runway contacts (touch-and-go, stop-and-go, low pass)
    if (isRw && (CONTACT.has(e.kind) || e.kind === 'landing' || e.kind === 'takeoff') && e.key) {
      const p = lastContact.get(e.key); if (p != null && CONTACT.has(e.kind) && e.t >= t0 && e.t - p < 900e3) circuits.push((e.t - p) / 1000);
      lastContact.set(e.key, e.kind === 'landing' ? null : e.t);
    }
    if (e.t < t0) continue;
    if (isRw) { const r = ends[e.rwy] = ends[e.rwy] || { takeoff: 0, landing: 0, touch_and_go: 0, stop_and_go: 0, go_around: 0, low_pass: 0, last: 0 }; r[e.kind]++; r.last = Math.max(r.last, e.t); if (e.kind === 'touch_and_go') tg++; }
    if (HELI_KINDS.includes(e.kind)) heli[e.kind]++;
    if (e.kind === 'runup') runups++;
    const ops = isRw || e.kind === 'lift_off' || e.kind === 'touch_down';
    if (ops && towerOf(e) === 'closed') { after.n++; after.kinds[e.kind] = (after.kinds[e.kind] || 0) + 1; }
    if (isRw || e.kind === 'lift_off' || e.kind === 'touch_down' || e.kind === 'runup') recent.push(e);
  }
  // FAA operations count: a touch-and-go / stop-and-go / low approach is two operations (a landing and a take-off) [inf: the
  // FAA's counting convention is not re-read here; the sheet labels it "movements"]
  const tot = Object.values(ends).reduce((m, r) => (m.dep += r.takeoff, m.arr += r.landing, m.tg += r.touch_and_go + r.stop_and_go, m.lp += r.go_around + r.low_pass, m), { dep: 0, arr: 0, tg: 0, lp: 0 });
  return { ends, tot, heli, after, tg, runups, circuitMedianS: median(circuits), nCircuits: circuits.length, since, windowMs, now, recent: recent.slice(-14).reverse() };
}
/** one line for the panel: "28L ↑4 ↓3 T&G 6 · heli 2 (last 34 min)" */
export function statsLine(S) {
  const names = ENDS.filter(n => S.ends[n]);
  if (!names.length && !S.heli.lift_off && !S.heli.touch_down) return S.since ? 'No runway movements seen yet' : '';
  const parts = names.map(n => { const r = S.ends[n]; return `${n} ↑${r.takeoff} ↓${r.landing}${r.touch_and_go + r.stop_and_go ? ' T&G ' + (r.touch_and_go + r.stop_and_go) : ''}`; });
  const h = S.heli.lift_off + S.heli.touch_down; if (h) parts.push(`heli ${h}`);
  const mins = Math.round(Math.min(S.windowMs, S.now - (S.since || S.now)) / 60000);
  return parts.join(' · ') + ` (last ${mins} min)`;
}
const KIND_TXT = { takeoff: '↑ take-off', landing: '↓ landing', touch_and_go: '⟳ touch-and-go', stop_and_go: '⟳ stop-and-go', go_around: '⤴ go-around / low approach',
  low_pass: '⤴ low pass', lift_off: '↑ helicopter lift-off', touch_down: '↓ helicopter touch-down', runup: '◎ run-up' };
/** the full sheet. o: {nameOf(key) -> label | null, idOf(key) -> opaque id | null, clock(ms engine) -> 'h:mm', delayS,
 *  pc: phaseCounts(), mode} */
export function statsHtml(S, o = {}) {
  const towerOf = o.towerOf || ((e) => e.tower || towerStatus(e.t));
  const clock = o.clock || ((t) => new Date(t).toLocaleTimeString('en-US', { timeZone: 'America/Los_Angeles', hour: 'numeric', minute: '2-digit' }));
  const mins = Math.round(Math.min(S.windowMs, S.now - (S.since || S.now)) / 60000);
  const names = ENDS.filter(n => S.ends[n]);
  const tbl = names.length ? `<table class="rt"><thead><tr><th>Runway</th><th title="take-offs">↑</th><th title="full-stop landings">↓</th><th title="touch-and-go / stop-and-go">T&amp;G</th><th title="low pass / go-around">Low</th><th>Last</th></tr></thead><tbody>${names.map(n => { const r = S.ends[n];
    return `<tr><td class="mono"><b>${esc(n)}</b></td><td class="mono c-dep">${r.takeoff}</td><td class="mono c-arr">${r.landing}</td><td class="mono">${r.touch_and_go + r.stop_and_go}</td><td class="mono">${r.go_around + r.low_pass}</td><td class="mono dim">${r.last ? clock(r.last) : ''}</td></tr>`; }).join('')}
<tr class="sum"><td>All</td><td class="mono">${S.tot.dep}</td><td class="mono">${S.tot.arr}</td><td class="mono">${S.tot.tg}</td><td class="mono">${S.tot.lp}</td><td></td></tr></tbody></table>` : '<p class="dim">No runway movements seen yet.</p>';
  const pc = o.pc ? `<p>${esc(statusLine(o.pc))}</p>` : '';
  const recent = S.recent.length ? `<ul class="evl">${S.recent.map(e => { const id = o.idOf ? o.idOf(e.key) : null; const nm = o.nameOf ? o.nameOf(e.key) : null;
    return `<li${id != null ? ` data-id="${id}"` : ''}><span class="mono">${esc(clock(e.t))}</span> <span class="k-${/landing|touch_down/.test(e.kind) ? 'arr' : /takeoff|lift_off/.test(e.kind) ? 'dep' : 'ga'}">${esc(KIND_TXT[e.kind] || e.kind)}</span> <b>${esc(nm || (e.cls ? e.cls.replace('_', ' ') : 'aircraft'))}</b> <span class="dim">${esc(e.rwy || '')}</span>${e.src === 'inf' ? ' <span class="inf" title="inferred across a gap in the data">inf</span>' : ''}${towerOf(e) === 'closed' ? ' <span class="dim">tower closed</span>' : ''}</li>`; }).join('')}</ul>` : '';
  return `<h3>Airfield</h3>
<p class="dim small">Detected from each aircraft's own motion (rules calibrated on the Phase 1 recording), last ${mins || 0} min${S.since ? ` · watching since ${esc(clock(S.since))}` : ''}. This page only knows what it has seen since it opened.${o.delayS != null ? ` The scene runs <b class="mono">${o.delayS.toFixed(0)} s</b> behind ${o.mode === 'live' ? 'real time' : 'the recording head'}.` : ''}</p>
<h4>In view now</h4>${pc || '<p class="dim">—</p>'}
<h4>Runway movements</h4>${tbl}
<p class="small">Touch-and-goes: <b class="mono">${S.tg}</b>${S.circuitMedianS != null ? ` · circuit (median) <b class="mono">${Math.round(S.circuitMedianS)} s</b> <span class="dim">(${S.nCircuits})</span>` : ''} · run-ups <b class="mono">${S.runups}</b></p>
<h4>Helicopters</h4><p class="small">Lift-offs <b class="mono">${S.heli.lift_off}</b> · touch-downs <b class="mono">${S.heli.touch_down}</b> · hover-taxi <b class="mono">${S.heli.hover_taxi}</b></p>
<h4>Tower closed (21:00–07:00)</h4><p class="small">${S.after.n ? `<b class="mono">${S.after.n}</b> runway / helicopter operations while the tower was closed (CTAF 120.2)` : 'None seen.'}</p>
${recent ? `<h4>Latest</h4>${recent}` : ''}`;
}
