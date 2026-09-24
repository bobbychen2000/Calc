// Live runway statistics from the traffic engine's own events (traffic.js Traffic.events, data time), never from the
// transponder air/ground flag (docs/research/traffic_audit.md s.6.10): arrivals per runway from touchdown events,
// departures from liftoff events, go-arounds, runway occupancy (touchdown -> runway exit) and taxi times
// (exit -> in-block, off-block -> take-off roll). Counts cover what this browser has seen since it started (a fresh
// page knows nothing about the hour before it opened); `since` says from when.
// `now` should be the scene time (Traffic.displayTime): events later than that are not shown yet, so the panel never
// runs ahead of the 3D view (or of the ATC audio when an audio delay is set).
const median = (a) => { if (!a.length) return null; const s = a.slice().sort((p, q) => p - q); return s[s.length >> 1]; };
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const NM = 1852;

export function runwayStats(events, now = Date.now(), windowMs = 3600e3) {
  const t0 = now - windowMs; const rw = {}; const ga = []; const rot = []; const taxiIn = []; const taxiOut = []; const rto = [];
  const lastBy = new Map(); let since = null; const recent = [];
  for (const e of events) {
    if (e.t > now) continue;
    if (since == null || e.t < since) since = e.t;
    const L = lastBy.get(e.hex) || {}; lastBy.set(e.hex, L);
    if (e.kind === 'exit' && e.rot != null && e.t >= t0) rot.push(e.rot);
    if (e.kind === 'exit') L.exit = e.t;
    if (e.kind === 'in-block' && L.exit && e.t - L.exit < 3600e3) { if (e.t >= t0) taxiIn.push((e.t - L.exit) / 60000); L.exit = null; }
    if (e.kind === 'off-block') L.off = e.t;
    if (e.kind === 'takeoff-roll' && L.off && e.t - L.off < 3600e3) { if (e.t >= t0) taxiOut.push((e.t - L.off) / 60000); L.off = null; }
    if (e.t < t0) continue;
    if (e.kind === 'rejected-takeoff') rto.push(e);
    if (e.kind === 'touchdown' || (e.kind === 'liftoff' && !e.unseen) || e.kind === 'go-around') recent.push(e);
    if (!e.rwy && e.kind !== 'go-around') continue;
    const r = e.rwy ? (rw[e.rwy] = rw[e.rwy] || { arr: 0, dep: 0, ga: 0, last: 0 }) : null;
    if (e.kind === 'touchdown') { r.arr++; r.last = Math.max(r.last, e.t); }
    else if (e.kind === 'liftoff' && !e.unseen) { r.dep++; r.last = Math.max(r.last, e.t); }
    else if (e.kind === 'go-around') { if (r) r.ga++; ga.push(e); }
  }
  const in10 = (k) => events.filter(e => e.kind === k && e.t <= now && e.t >= now - 600e3 && !e.unseen).length;
  return { runways: rw, goArounds: ga, rejected: rto, recent: recent.slice(-12).reverse(), rotMedianS: median(rot), taxiInMin: median(taxiIn), taxiOutMin: median(taxiOut),
    nRot: rot.length, nTaxiIn: taxiIn.length, nTaxiOut: taxiOut.length, arr10: in10('touchdown'), dep10: in10('liftoff'), since, windowMs, now, config: runwayConfig(events, now) };
}

// runway configuration in use, inferred from the runways of the last 20 min of observed landings and take-offs
// (no ATIS is read: docs/research/atc.md s.1.2 -- the D-ATIS text source was not cleared for use)
export function runwayConfig(events, now = Date.now(), spanMs = 1200e3) {
  const arr = {}, dep = {}; let n = 0;
  for (let i = events.length - 1; i >= 0; i--) {
    const e = events[i]; if (e.t > now) continue; if (now - e.t > spanMs) break;
    if (e.kind === 'touchdown' && e.rwy) { arr[e.rwy] = (arr[e.rwy] || 0) + 1; n++; }
    if (e.kind === 'liftoff' && e.rwy && !e.unseen) { dep[e.rwy] = (dep[e.rwy] || 0) + 1; n++; }
  }
  const order = (m) => Object.keys(m).sort((a, b) => m[b] - m[a] || a.localeCompare(b));
  return { arr: order(arr), dep: order(dep), n, spanMin: spanMs / 60000 };
}

// runway pair an aircraft holds short of: within 150 m of the centreline and inside the runway's length (+100 m).
// The 76 hold bars in data/sfo_details.js lie 75-96 m from the nearest centreline (measured 24 Sep 2026); the ADS-B
// antenna of an aircraft stopped at a bar is ~10-40 m further back (traffic.js ANT = 0.2 x length behind the nose)
function holdingShort(rwys, x, z) {
  if (!rwys) return null; let best = null, bd = 150;
  for (const R of rwys) { const dx = x - R.start[0], dz = z - R.start[1]; const a = dx * R.dir[0] + dz * R.dir[1], c = Math.abs(-dx * R.dir[1] + dz * R.dir[0]);
    if (a > -100 && a < R.len + 100 && c < bd) { bd = c; best = R.pair; } }
  return best;
}
// what is queued right now (display-time phases): departures lined up / holding short / taxiing out, arrivals on final.
// rwys = traffic.js RWY (to tell "holding short of a runway" from "stopped somewhere on a taxiway")
export function runwayQueue(tracks, rwys = null) {
  const lined = [], holding = [], taxiOut = [], finals = {};
  for (const tr of tracks) {
    if (tr.vehicle || tr.stale || !tr.disp || !tr.disp.valid) continue;
    const name = (tr.cs && tr.cs.display) || tr.info.flight || tr.info.reg || tr.hex.toUpperCase();
    const it = { hex: tr.hex, name, icao: tr.info.icao || '', rwy: tr.m && tr.m.rwy || null };
    if (tr.phase === 'lineup' || tr.phase === 'takeoff') lined.push(it);
    else if (tr.phase === 'holding' && tr.dirSFO !== 'arr' && !tr.landedAt) { const p = holdingShort(rwys, tr.disp.x, tr.disp.z); if (p) holding.push({ ...it, rwy: it.rwy || p }); }
    else if (tr.phase === 'taxi' && tr.dirSFO === 'dep') taxiOut.push(it);
    else if (tr.phase === 'final' && tr.finalInfo) { const r = tr.finalInfo.R.name; (finals[r] = finals[r] || []).push({ ...it, rwy: r, nm: Math.max(0, -tr.finalInfo.a / NM) }); }
  }
  for (const k in finals) finals[k].sort((a, b) => a.nm - b.nm);
  return { lined, holding, taxiOut, finals };
}

// one compact line for the panel, e.g. "28L ↓4 ↑12 · 28R ↓2 ↑1 · go-arounds 0 · ROT 58 s (last 60 min)"
export function statsLine(S, now = S.now || Date.now()) {
  const names = Object.keys(S.runways).filter(n => S.runways[n].arr || S.runways[n].dep || S.runways[n].ga).sort((a, b) => (S.runways[b].arr + S.runways[b].dep) - (S.runways[a].arr + S.runways[a].dep));
  if (!names.length) return S.since ? 'No landings or take-offs seen yet · tap for runway stats' : '';
  const parts = names.map(n => `${n} ↓${S.runways[n].arr} ↑${S.runways[n].dep}`);
  parts.push(`go-arounds ${S.goArounds.length}`);
  if (S.rotMedianS != null) parts.push(`ROT ${Math.round(S.rotMedianS)} s`);
  const mins = Math.round(Math.min(S.windowMs, now - (S.since || now)) / 60000);
  return parts.join(' · ') + ` (last ${mins} min)`;
}

const hhmm = (t) => new Date(t).toLocaleTimeString('en-US', { timeZone: 'America/Los_Angeles', hour: 'numeric', minute: '2-digit' });
const fmtMin = (m) => m == null ? '—' : m < 10 ? m.toFixed(1) + ' min' : Math.round(m) + ' min';
const who = (e) => esc((e.flight || '').trim() || e.reg || e.hex.toUpperCase());
// the full stats sheet (ui.js shows it in a popover / bottom sheet); rows with data-hex select that aircraft
export function statsHtml(S, Q) {
  const mins = Math.round(Math.min(S.windowMs, S.now - (S.since || S.now)) / 60000);
  const names = Object.keys(S.runways).sort((a, b) => (S.runways[b].arr + S.runways[b].dep + S.runways[b].ga) - (S.runways[a].arr + S.runways[a].dep + S.runways[a].ga) || a.localeCompare(b));
  const tot = names.reduce((m, n) => (m.arr += S.runways[n].arr, m.dep += S.runways[n].dep, m), { arr: 0, dep: 0 });
  const C = S.config;
  const cfg = C.n ? `Landing <b>${C.arr.join(' · ') || '—'}</b> &nbsp;·&nbsp; Departing <b>${C.dep.join(' · ') || '—'}</b>` : 'Not enough traffic seen yet';
  const tbl = names.length ? `<table class="rt"><thead><tr><th>Runway</th><th>Arrivals</th><th>Departures</th><th>Go-arounds</th><th>Last</th></tr></thead><tbody>${names.map(n => { const r = S.runways[n]; return `<tr><td class="mono"><b>${esc(n)}</b></td><td class="mono c-arr">${r.arr}</td><td class="mono c-dep">${r.dep}</td><td class="mono">${r.ga || ''}</td><td class="mono dim">${r.last ? hhmm(r.last) : ''}</td></tr>`; }).join('')}
<tr class="sum"><td>All</td><td class="mono">${tot.arr}</td><td class="mono">${tot.dep}</td><td class="mono">${S.goArounds.length}</td><td></td></tr></tbody></table>` : '<p class="dim">No landings or take-offs seen yet.</p>';
  const gaList = S.goArounds.length ? `<ul class="evl">${S.goArounds.slice().reverse().map(e => `<li data-hex="${esc(e.hex)}"><span class="mono">${hhmm(e.t)}</span> <b>${who(e)}</b> ${esc(e.icao || '')} <span class="dim">runway ${esc(e.rwy || '?')}${e.minAlt != null ? ` · lowest ${Math.round(e.minAlt)} ft` : ''}</span></li>`).join('')}</ul>` : '<p class="dim">None.</p>';
  const q = (arr, lbl) => arr.length ? `<div class="q"><span class="ql">${lbl}</span> ${arr.map(i => `<button class="chip" data-hex="${esc(i.hex)}">${esc(i.name)}${i.rwy ? ` <span class="dim">${esc(i.rwy)}</span>` : ''}${i.nm != null ? ` <span class="dim">${i.nm.toFixed(1)} nm</span>` : ''}</button>`).join('')}</div>` : '';
  const fin = Object.keys(Q.finals).sort().map(r => q(Q.finals[r], 'Final ' + esc(r))).join('');
  const queue = q(Q.lined, 'On runway') + q(Q.holding, 'Holding short') + q(Q.taxiOut, 'Taxiing out') + fin;
  const recent = S.recent.length ? `<ul class="evl">${S.recent.map(e => `<li data-hex="${esc(e.hex)}"><span class="mono">${hhmm(e.t)}</span> <span class="k-${e.kind === 'touchdown' ? 'arr' : e.kind === 'liftoff' ? 'dep' : 'ga'}">${e.kind === 'touchdown' ? '↓ landed' : e.kind === 'liftoff' ? '↑ departed' : '⟲ go-around'}</span> <b>${who(e)}</b> ${esc(e.icao || '')} <span class="dim">${esc(e.rwy || '')}</span></li>`).join('')}</ul>` : '';
  return `<h3>Runways</h3>
<p class="dim small">Detected from each aircraft's own motion (touchdown = braking, lift-off = climbing), last ${mins || 0} min${S.since ? ` · watching since ${hhmm(S.since)}` : ''}. This page only knows what it has seen since it opened.</p>
<h4>Configuration</h4><p>${cfg}${C.n ? ` <span class="dim small">(inferred from the last ${C.spanMin} min)</span>` : ''}</p>
<h4>Movements</h4>${tbl}
<p class="small">Last 10 min: <b class="mono">${S.arr10}</b> arrivals, <b class="mono">${S.dep10}</b> departures${S.rejected.length ? ` · rejected take-offs: ${S.rejected.map(who).join(', ')}` : ''}</p>
<h4>Now</h4>${queue || '<p class="dim">Nothing lined up, holding or on final.</p>'}
<h4>Go-arounds</h4>${gaList}
<h4>Times (median)</h4><p class="small">Runway occupancy <b class="mono">${S.rotMedianS != null ? Math.round(S.rotMedianS) + ' s' : '—'}</b> <span class="dim">(${S.nRot})</span> · taxi-in <b class="mono">${fmtMin(S.taxiInMin)}</b> <span class="dim">(${S.nTaxiIn})</span> · taxi-out <b class="mono">${fmtMin(S.taxiOutMin)}</b> <span class="dim">(${S.nTaxiOut})</span></p>
${recent ? `<h4>Latest</h4>${recent}` : ''}`;
}
