// DOM user interface (hwd3d Phase 2, P4). Forked from sfo3d/js/live/ui.js @ a967f9b. Kept: the layout and behaviour -
// top bar (brand, feed status pill, ATC pill, clock), view buttons, a flight panel that is a side panel on desktops and a
// bottom sheet (peek / open) on phones, search, the detail card with Follow / Chase / Free camera, DOM labels over the 3-D
// view with overlap culling, settings / about / statistics / ATC popovers (bottom sheets on phones), the loading overlay
// and the fatal-error overlay.
// Changed (fork map 1.1, 2.0, 2.7-2.9):
//  - identity: names come ONLY from tr.ident (P3 lookup.js identity: label = callsign / registration / type; reg,
//    callsign and operator are null for a LADD / PIA aircraft, D1). The card says "Identity withheld (LADD / PIA)" for a
//    masked track. A track key never reaches the DOM (fork map 2.0: no UI text may contain a key): rows, labels and
//    sheet entries carry an opaque per-page id (opts.idOf), and the card shows no address;
//  - categories are P3's category(): hwd_air, hwd_ground, heli, overflight, vehicle, unknown; the tabs are Air / Ground /
//    Heli / Over / All;
//  - the card shows the GA facts the brief asks for: registration, type and model, operator, phase (with an "inf" marker
//    when the phase or the parking spot is inferred, and "provisional"), parking spot (the descriptive Phase 1 zone label,
//    never an official number, D3), runway, HWD traffic vs overflight (D6), the tower state, altitude MSL / height above
//    the field / speed (round-2 recheck m7: altitudeOf below, not the raw pressure altitude), the data age with the
//    altitude method [inf], and the placeholder note (AircraftViews.modelNote);
//  - the compact status line in the panel = the traffic counts by phase group (stats.js phaseCounts), always visible;
//  - views: Overview, Tower, Green Ramp, West Hangars, 28L Final (+ settings, about);
//  - the ATC sheet is the D2 link-out (atc.js); there is no audio-delay slider and no per-feed highlight.
// Dropped: SFO's gate / stand rows vs SFO's flight plan, routes, airline headlines and lessor rules, flysfo / FlightAware
// deep links (they would turn a track into a lookup of a private aircraft), the hex in the card.
import { phaseLabel, category } from './traffic.js';
import { atcHtml, towerAt } from './atc.js';
import { statusLine } from './stats.js';
import { RULES } from './classifier.js';
import { INHG_HPA } from '../env/wx/metar.js';
import { FIELD_ELEV_FT } from '../geo.js';

const $ = (s, r = document) => r.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmtInt = (v) => v == null || isNaN(v) ? '—' : Math.round(v).toLocaleString('en-US');
const KT = 1852 / 3600, FT = 0.3048;
export const TABS = { air: 'Air', ground: 'Ground', heli: 'Heli', over: 'Over', all: 'All' };
const TAB_OF = { hwd_air: 'air', hwd_ground: 'ground', heli: 'heli', overflight: 'over', unknown: 'over', vehicle: null };
export const VIEW_NAMES = [['overview', 'Overview'], ['tower', 'Tower'], ['green', 'Green Ramp'], ['west', 'West Hangars'], ['final28l', '28L Final']];
// provenance names (fix round 1): registration / type / operator of a record are the aggregator's DATABASE values, not broadcast
const SRC_NAME = { adsb: 'broadcast', adsb_db: 'aggregator database (adsb.lol / adsb.fi)', mictronics: 'Mictronics database', icao_address: 'derived from the ICAO address (US block) - inferred', faa_acd: 'FAA ACD', inf: 'inferred' };
// why a masked aircraft shows type only: only 'd1' means it is flagged LADD / PIA
const maskHead = (I) => I.maskWhy === 'd1' ? 'Identity withheld · LADD / PIA' : 'Identity not shown · type-only feed';
const maskReg = (I) => I.maskWhy === 'd1' ? 'withheld (LADD / PIA: type only)' : 'not shown (this feed / recording shows every aircraft by type only)';
const PARK_KIND = { tiedown: 'tie-down', tie_down: 'tie-down', ramp: 'ramp spot', hangar_apron: 'hangar apron', helipad: 'helipad', hangar: 'hangar', door: 'hangar door', unspotted: 'no mapped spot' };
const inf = (t) => `<span class="inf" title="${esc(t || 'inferred')}">inf</span>`;

export class UI {
  constructor(root, opts) {
    this.root = root; this.o = opts; // {onSelect(id, fly), onView(name), onFollow(mode), onSetting(k, v), showOthers(), idOf(key), trackOf(id), onAtcOpen(), onStatsOpen(), altCtx()}
    this.tab = 'all'; this.q = ''; this.sel = null; this.labels = new Map(); this.showLabels = true; this.sheet = 'peek'; this.towerOpen = null;
    this.build();
  }
  build() {
    const R = this.root;
    R.insertAdjacentHTML('beforeend', `
<div id="labels" aria-hidden="true"></div>
<header id="top">
  <div class="brand"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5z"/></svg><span><b>HWD</b> Live 3D</span></div>
  <button id="status" class="pill" title="Data feed status"><i class="dot"></i><span class="txt">Starting…</span></button>
  <button id="btn-atc" class="pill" title="ATC (LiveATC.net link, tower hours)" aria-label="ATC"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a8 8 0 0 0-8 8v6a3 3 0 0 0 3 3h1a1 1 0 0 0 1-1v-5a1 1 0 0 0-1-1H6v-2a6 6 0 0 1 12 0v2h-2a1 1 0 0 0-1 1v5a1 1 0 0 0 1 1h1a3 3 0 0 0 3-3v-6a8 8 0 0 0-8-8"/></svg><span class="al">ATC</span><span class="tn"></span></button>
  <div id="clock" class="mono"></div>
</header>
<nav id="views" aria-label="Views">
  ${VIEW_NAMES.map(([k, n]) => `<button data-view="${k}">${n}</button>`).join('')}
  <button id="btn-settings" class="icon" title="Settings" aria-label="Settings"><svg viewBox="0 0 24 24"><path d="M12 15.5A3.5 3.5 0 1 1 12 8.5a3.5 3.5 0 0 1 0 7m7.43-2.53c.04-.32.07-.64.07-.97s-.03-.66-.07-1l2.11-1.63-2-3.46-2.49 1a7.3 7.3 0 0 0-1.69-.98l-.38-2.65h-4l-.38 2.65c-.61.25-1.17.58-1.69.98l-2.49-1-2 3.46L4.57 11c-.04.34-.07.67-.07 1s.03.65.07.97l-2.11 1.66 2 3.46 2.49-1c.52.4 1.08.73 1.69.98l.38 2.65h4l.38-2.65a7.3 7.3 0 0 0 1.69-.98l2.49 1 2-3.46z"/></svg></button>
  <button id="btn-about" class="icon" title="About and credits" aria-label="About and credits"><svg viewBox="0 0 24 24"><path d="M11 17h2v-6h-2zm1-15a10 10 0 1 0 0 20 10 10 0 0 0 0-20m0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16M11 9h2V7h-2z"/></svg></button>
</nav>
<aside id="panel" class="peek">
  <button id="grab" aria-label="Expand list"><i></i></button>
  <div class="tabs" role="tablist">${Object.entries(TABS).map(([k, n]) => `<button data-tab="${k}" class="t-${k}">${n} <b></b></button>`).join('')}</div>
  <button id="statsbtn" class="statsbtn" title="Traffic in view by phase and runway movements detected from the aircraft's own motion · tap for the airfield statistics"><span id="phaseline" class="rwystats mono"></span><span id="rwystats" class="rwystats mono"></span></button>
  <div class="search"><input id="search" type="search" placeholder="Registration, callsign, type, operator, spot" autocomplete="off" spellcheck="false"></div>
  <div id="list" role="list"></div>
</aside>
<section id="card" hidden></section>
<div id="settings" class="pop" hidden>
  <h3>Settings</h3>
  <label>Lighting <select data-set="light"><option value="real">Scene time</option><option value="dawn">Dawn</option><option value="day">Day</option><option value="dusk">Dusk</option><option value="night">Night</option></select></label>
  <label class="chk"><input type="checkbox" data-set="labels" checked> Show labels</label>
  <label class="chk"><input type="checkbox" data-set="others" checked> Show overflights (not HWD traffic)</label>
  <button data-set="clearParked" class="ghost">Forget remembered parked aircraft</button>
</div>
<div id="about" class="pop wide sheet" hidden></div>
<div id="rstats" class="pop wide sheet" hidden></div>
<div id="atc" class="pop wide sheet" hidden></div>
<footer id="attrib"></footer>
<div id="loading"><div class="lbox"><div class="brand big"><b>HWD</b> Live 3D</div><div class="bar"><i></i></div><div class="msg">Loading…</div></div></div>
`);
    this.el = { status: $('#status'), clock: $('#clock'), list: $('#list'), card: $('#card'), panel: $('#panel'), labels: $('#labels'), search: $('#search'), settings: $('#settings'), about: $('#about'), attrib: $('#attrib'), loading: $('#loading'), rstats: $('#rstats'), atc: $('#atc'), phase: $('#phaseline'), rws: $('#rwystats') };
    this.pops = [this.el.settings, this.el.about, this.el.rstats, this.el.atc];
    R.querySelectorAll('#panel .tabs button').forEach(b => b.addEventListener('click', () => { this.tab = b.dataset.tab; this.renderList(true); if (this.sheet === 'peek') this.setSheet('open'); }));
    this.el.search.addEventListener('input', () => { this.q = this.el.search.value.trim().toLowerCase(); if (this.q && this.tab !== 'all') this.tab = 'all'; this.renderList(true); });
    this.el.search.addEventListener('focus', () => { if (this.sheet !== 'open') this.setSheet('open'); });
    $('#grab').addEventListener('click', () => this.setSheet(this.sheet === 'open' ? 'peek' : 'open'));
    R.querySelectorAll('#views [data-view]').forEach(b => b.addEventListener('click', () => this.o.onView(b.dataset.view)));
    this.el.list.addEventListener('click', e => { const row = e.target.closest('[data-id]'); if (row) { this.o.onSelect(+row.dataset.id, true); if (window.innerWidth < 760) this.setSheet('peek'); } });
    this.el.labels.addEventListener('click', e => { const l = e.target.closest('[data-id]'); if (l) this.o.onSelect(+l.dataset.id, true); });
    $('#btn-settings').addEventListener('click', () => this.toggle(this.el.settings));
    $('#btn-about').addEventListener('click', () => this.toggle(this.el.about));
    this.el.status.addEventListener('click', () => this.toggle(this.el.about));
    $('#btn-atc').addEventListener('click', () => { this.toggle(this.el.atc); if (!this.el.atc.hidden && this.o.onAtcOpen) this.o.onAtcOpen(); });
    // (fix round 2: the two status lines are ONE button - one 44-px touch target on phones instead of two of 19-21 px)
    for (const b of [$('#statsbtn')]) b.addEventListener('click', () => { this.toggle(this.el.rstats); if (!this.el.rstats.hidden && this.o.onStatsOpen) this.o.onStatsOpen(); });
    for (const P of [this.el.rstats, this.el.atc, this.el.about]) P.addEventListener('click', e => {
      const h = e.target.closest('[data-id]'); if (h) { this.o.onSelect(+h.dataset.id, true); if (window.innerWidth < 760) P.hidden = true; return; }
      if (e.target.closest('button.x')) P.hidden = true;
    });
    this.el.settings.addEventListener('change', e => { const k = e.target.dataset.set; if (!k) return; const v = e.target.type === 'checkbox' ? e.target.checked : e.target.value; if (k === 'labels') this.showLabels = v; this.o.onSetting(k, v); });
    this.el.settings.addEventListener('click', e => { const k = e.target.dataset.set; if (k === 'clearParked') { this.o.onSetting(k, true); e.target.textContent = 'Forgotten'; } });
    document.addEventListener('pointerdown', e => { for (const p of this.pops) if (!p.hidden && !p.contains(e.target) && !e.target.closest('#btn-settings,#btn-about,#status,#btn-atc,#statsbtn')) p.hidden = true; });
    this.el.card.addEventListener('click', e => {
      const b = e.target.closest('button[data-act]'); if (!b) return;
      const a = b.dataset.act; if (a === 'close') this.o.onSelect(null); else this.o.onFollow(a);
    });
  }
  // phaseLabel with the tower suffix corrected to the DATA clock (fork map I3: P3 keys tower status off the engine
  // wall clock, wrong in replay / snapshot). open === true strips a false 'tower closed (CTAF)'.
  // one altitude per track for the list, the card and the 3-D label, refreshed on the list's 1-s tick (altTick), so the three
  // never print different numbers for the same aircraft at the same moment (m7); on the ground it is null at once
  altFor(tr) {
    if (!tr || !tr.disp || !tr.disp.valid || tr.disp.ground || tr.stale) return null;
    const M = this._altC || (this._altC = new WeakMap()), g = this._altGen || 0; let c = M.get(tr);
    if (!c || c.g !== g) { c = { g, r: altitudeOf(tr, this.o.altCtx ? this.o.altCtx() : null) }; M.set(tr, c); }
    return c.r;
  }
  altTick() { this._altGen = (this._altGen || 0) + 1; }
  ph(tr, now) { let s = phaseLabel(tr, now); if (this.towerOpen === true) s = s.replace(' · tower closed (CTAF)', ''); return s; }
  toggle(p) { const show = p.hidden; for (const q of this.pops) q.hidden = true; p.hidden = !show; }
  statsOpen() { return !this.el.rstats.hidden; }
  setSheetHtml(P, html) { const h = '<button class="x" aria-label="Close">×</button>' + html; if (P._h !== h) { const st = P.scrollTop; P.innerHTML = h; P.scrollTop = st; P._h = h; } }
  setStatsSheet(html) { this.setSheetHtml(this.el.rstats, html); }
  atcOpen() { return !this.el.atc.hidden; }
  /** ATC pill + sheet: tower state at the scene time t (ms, data clock) */
  setAtc(t, mode) {
    const T = towerAt(t); const b = $('#btn-atc'); b.classList.toggle('closed', T.open === false); b.classList.toggle('open', T.open === true);
    const tn = b.querySelector('.tn'); if (tn.textContent !== T.chip) tn.textContent = T.chip; b.title = T.label ? T.label + ' · LiveATC.net link' : 'ATC';
    if (this.atcOpen()) this.setSheetHtml(this.el.atc, atcHtml({ t, mode }));
  }
  setSheet(s) { this.sheet = s; this.el.panel.className = s; }
  progress(frac, msg) { const L = this.el.loading; if (!L) return; L.querySelector('.bar i').style.width = Math.round(frac * 100) + '%'; if (msg) L.querySelector('.msg').textContent = msg; }
  ready() { const L = this.el.loading; if (!L) return; L.classList.add('done'); setTimeout(() => L.remove(), 700); this.el.loading = null; }
  fail(msg) { const L = this.el.loading; if (L) { L.querySelector('.msg').innerHTML = msg; L.classList.add('err'); return; }
    let F = this.el.fatal; if (!F) { F = this.el.fatal = document.createElement('div'); F.id = 'fatal'; F.setAttribute('role', 'alert'); (this.root || document.body).appendChild(F); }
    F.innerHTML = '<div class="lbox"><div class="msg">' + msg + '</div></div>'; F.hidden = false; }
  setAbout(html) { this.setSheetHtml(this.el.about, html); }
  setAttrib(html) { this.el.attrib.innerHTML = html; }

  // ------------------------------------------------------------ status bar
  setStatus({ state, text, sub, title }) {
    const s = this.el.status; s.dataset.state = state; const t = s.querySelector('.txt'); if (t.textContent !== text) t.textContent = text;
    let p = s.querySelector('.prov'); if (!p) { p = document.createElement('span'); p.className = 'prov'; s.appendChild(p); } const ps = sub ? '· ' + sub : ''; if (p.textContent !== ps) p.textContent = ps;
    if (title != null) s.title = title;
  }
  setPhaseLine(pc) { const t = statusLine(pc); const e = this.el.phase; if (e._t !== t) { e.textContent = t + ' ›'; e._t = t; } }
  setStats(text) { const e = this.el.rws; if (e._t !== text) { e.textContent = text || ''; e._t = text; e.hidden = !text; } }
  setClock(t, extra) {
    if (t == null || !Number.isFinite(t)) { this.el.clock.textContent = ''; return; }
    const d = new Date(t);
    const tm = d.toLocaleTimeString('en-US', { timeZone: 'America/Los_Angeles', hour: 'numeric', minute: '2-digit' });
    const z = d.toLocaleTimeString('en-US', { timeZone: 'America/Los_Angeles', timeZoneName: 'short' }).split(' ').pop();
    const h = `${esc(tm)} <span class="dim">${esc(z)}</span>${extra ? ' <span class="wx">' + esc(extra) + '</span>' : ''}`;
    if (this.el.clock._h !== h) { this.el.clock.innerHTML = h; this.el.clock._h = h; }
  }

  // ------------------------------------------------------------ lists
  shown(tr) { return (tr.disp.valid && tr.inView) || (tr.stale && tr.park); }
  rowsFor(tracks) {
    const q = this.q, out = [];
    for (const tr of tracks) {
      if (!this.shown(tr) || !tr.ident) continue;
      const cat = category(tr), tab = TAB_OF[cat];
      if (!tab) continue;                                   // ground vehicles: not listed
      if (this.tab !== 'all' && tab !== this.tab) continue;
      if (this.tab === 'all' && tab === 'over' && !this.o.showOthers()) continue;
      if (q) {
        const I = tr.ident;   // masked tracks carry no reg / callsign / operator (D1), so they cannot be searched by them
        const hay = [I.label, I.reg, I.callsign, I.operator, I.icaoType, I.typeName, tr.park && tr.park.zone, phaseLabel(tr)].filter(Boolean).join(' ').toLowerCase();
        if (!hay.includes(q)) continue;
      }
      out.push({ tr, cat, tab });
    }
    const ORDER = { air: 0, heli: 1, ground: 2, over: 3 };
    const GORD = { final: 0, base: 1, downwind: 2, crosswind: 3, upwind: 4, initial_climb: 5, go_around: 6, low_pass: 6, takeoff_roll: 7, landing_roll: 7, touch_and_go: 7, stop_and_go: 7, line_up: 8, hold_short: 9, runup: 10, taxi: 11, runway_taxi: 11, parked: 20, hangared: 21 };
    const key = (r) => (ORDER[r.tab] ?? 5) * 1e7 + (GORD[r.tr.phase] ?? 15) * 1e5 + (r.tr.stale ? 5e4 : 0) + Math.min(4e4, Math.hypot(r.tr.disp.x, r.tr.disp.z));
    out.sort((a, b) => key(a) - key(b));
    return out;
  }
  renderList(force, tracks = this._tracks) {
    if (!tracks) return; this._tracks = tracks;
    const counts = { air: 0, ground: 0, heli: 0, over: 0, all: 0 };
    for (const tr of tracks) { if (!this.shown(tr) || !tr.ident) continue; const t = TAB_OF[category(tr)]; if (!t) continue; counts[t]++; if (t !== 'over' || this.o.showOthers()) counts.all++; }
    this.root.querySelectorAll('#panel .tabs button').forEach(b => { b.classList.toggle('on', b.dataset.tab === this.tab); const bb = b.querySelector('b'); const v = String(counts[b.dataset.tab]); if (bb.textContent !== v) bb.textContent = v; });
    const rows = this.rowsFor(tracks);
    const now = Date.now(), AC = this.o.altCtx ? this.o.altCtx() : null;
    const html = rows.length ? rows.map(({ tr, cat }) => {
      const I = tr.ident, D = tr.disp, id = this.o.idOf(tr.key);
      const alt = altShort(this.altFor(tr));                   // ft MSL at the display time (legend above the rows)
      const spd = tr.stale ? '' : D.gs > 1 ? `${fmtInt(D.gs / KT)} kt` : '';
      const sub = I.masked ? (I.typeName || 'type only') : [I.reg && I.reg !== I.label ? I.reg : null, I.operator, I.typeName].filter(Boolean).join(' · ');
      const ph = this.ph(tr, now);
      return `<div class="row c-${cat}${this.sel === tr.key ? ' sel' : ''}${tr.stale ? ' stale' : ''}${tr.info && tr.info.emergency ? ' emg' : ''}" data-id="${id}" role="listitem">
  <div class="l1"><b>${esc(I.label)}</b><span class="ty mono">${esc(I.icaoType || '····')}</span>${I.masked ? `<span class="d1" title="${I.maskWhy === 'd1' ? 'LADD / PIA: type only' : 'type-only feed'}">type only</span>` : ''}<span class="ph">${esc(ph)}${isInf(tr) ? ' ' + inf('phase or spot inferred') : ''}</span></div>
  <div class="l2"><span class="rt">${esc(sub)}</span><span class="nums mono">${esc([alt, spd].filter(Boolean).join('  '))}</span></div></div>`;
    }).join('') : `<div class="empty">${this.q ? 'No matches.' : { air: 'No HWD traffic in the air right now.', ground: 'No aircraft on the ground yet.', heli: 'No helicopters right now.', over: 'No overflights right now.', all: 'No traffic yet.' }[this.tab]}</div>`;
    // the altitude legend (m7): the rows print '1,450 ft'; what that number is and how it was made, marked inferred
    const anyAlt = rows.some(({ tr }) => tr.disp && tr.disp.valid && !tr.disp.ground && !tr.stale);
    const M = anyAlt ? altMethod(null, AC) : null;
    const legend = M ? `<div class="legend" title="${esc(M.title)}">Altitudes in ft MSL · ${esc(M.text)} ${inf(M.title)}</div>` : '';
    const full = legend + html;
    if (force || full !== this._lastHtml) { const st = this.el.list.scrollTop; this.el.list.innerHTML = full; this.el.list.scrollTop = st; this._lastHtml = full; }
  }

  // ------------------------------------------------------------ detail card (D1: the identity rows come from tr.ident only)
  // extra: {modelNote, follow, tScene (data clock ms, for the tower state), parkLabel, ageS, srcText}
  renderCard(tr, extra = {}) {
    const C = this.el.card;
    if (!tr) { C.hidden = true; this.sel = null; document.body.classList.remove('has-card'); return; }
    this.sel = tr.key; C.hidden = false; document.body.classList.add('has-card');
    const I = tr.ident || {}, D = tr.disp, P = tr.phaseInfo || {}, cat = category(tr), now = Date.now();
    const head = I.masked ? maskHead(I) : I.operator ? esc(I.operator) + (I.opSrc && I.opSrc !== 'adsb' ? ` <span class="dim">· ${esc(SRC_NAME[I.opSrc] || I.opSrc)}</span>` : '') : ({ hwd_air: 'HWD traffic', hwd_ground: 'HWD traffic', heli: 'Helicopter', overflight: 'Overflight', unknown: 'Not yet classified', vehicle: 'Ground vehicle' }[cat] || '');
    const scope = tr.scope === 'hwd' ? 'HWD traffic' : tr.scope === 'overflight' ? 'Overflight, not HWD traffic' : 'Not yet classified (watching)';
    const T = towerAt(extra.tScene);
    const park = parkText(tr, extra);
    // altitude MSL + height above the field from the same rounded value; the method on the data line, marked inf (m7)
    const AC = this.o.altCtx ? this.o.altCtx() : null, AR = this.altFor(tr), AT = AR ? altCard(AR) : null, AM = AR ? altMethod(AR, AC) : null;
    const vs = D.vs && !D.ground && !tr.stale ? D.vs / FT * 60 : null;
    C.className = 'c-' + cat;
    C.innerHTML = `
<div class="ch"><div class="al">${head}</div><button data-act="close" class="x" aria-label="Close">×</button></div>
<div class="fl"><b>${esc(I.label || 'Aircraft')}</b>${!I.masked && I.callsign && I.callsign !== I.label ? `<span class="mono dim">${esc(I.callsign)}</span>` : ''}</div>
<div class="ty">${esc(I.typeName || (I.icaoType ? '' : 'Type not reported'))}${I.icaoType ? ` <span class="mono dim">${esc(I.icaoType)}</span>` : ''}</div>
<div class="ph c-${cat}">${esc(this.ph(tr, now))}${P.src === 'inf' ? ' ' + inf(P.rule || 'inferred phase') : ''}</div>
<dl>
  <dt>Registration</dt><dd class="mono">${I.masked ? `<span class="dim">${maskReg(I)}</span>` : I.reg ? esc(I.reg) + (I.regSrc ? ` <span class="dim small">${esc(SRC_NAME[I.regSrc] || I.regSrc)}</span>` : '') + (I.regSrc === 'icao_address' ? ' ' + inf('N-number derived from the ICAO address; not checked against the registry') : '') : '—'}</dd>
  ${!I.masked && I.callsign && I.callsign === I.label && I.reg && I.reg !== I.callsign ? `<dt>Callsign</dt><dd class="mono">${esc(I.callsign)}</dd>` : ''}
  <dt>Operator</dt><dd>${I.masked ? `<span class="dim">${I.maskWhy === 'd1' ? 'withheld' : 'not shown'}</span>` : I.operator ? esc(I.operator) : '<span class="dim">not known</span>'}</dd>
  ${park ? `<dt>Parking</dt><dd>${park}</dd>` : ''}
  ${P.rwy ? `<dt>Runway</dt><dd class="mono"><b>${esc(P.rwy)}</b>${P.leg ? ` <span class="dim">${esc(P.leg)}</span>` : ''}</dd>` : ''}
  <dt>Traffic</dt><dd>${esc(scope)}${tr.scope === 'overflight' ? '' : ''}</dd>
  ${AT ? `<dt>Altitude</dt><dd class="mono"><span class="nw">${esc(AT.msl)}</span> <span class="dim nw">· ${esc(AT.above)}</span></dd>` : `<dt>Altitude</dt><dd>${D.ground || tr.stale ? 'On the ground' : '—'}</dd>`}
  <dt>Speed</dt><dd class="mono">${tr.stale ? '—' : fmtInt(D.gs / KT) + ' kt'}${vs != null && Math.abs(vs) > 150 ? ` <span class="dim">· ${vs > 0 ? '+' : ''}${fmtInt(Math.round(vs / 50) * 50)} ft/min</span>` : ''}</dd>
  <dt>Tower</dt><dd>${T.open == null ? '—' : T.open ? 'Open <span class="dim">(07:00–21:00)</span>' : 'Closed · <span class="mono">CTAF 120.2</span>'}</dd>
  <dt>Data</dt><dd>${tr.stale ? 'last signal ' + ago(extra.staleMs) : extra.ageS == null ? '—' : `position <b class="mono">${extra.ageS < 10 ? extra.ageS.toFixed(1) : Math.round(extra.ageS)} s</b> old`}${extra.srcText ? ` <span class="dim">· ${esc(extra.srcText)}</span>` : ''}${AM ? `<br><span class="dim small altm" title="${esc(AM.title)}">altitude: ${esc(AM.text)}${AR.interp ? ', between fixes' : ''}</span> ${inf(AM.title)}` : ''}</dd>
</dl>
${extra.modelNote ? `<div class="model">${esc(extra.modelNote)}</div>` : ''}
<div class="acts"><button data-act="follow" class="${extra.follow === 'follow' ? 'on' : ''}">Follow</button><button data-act="chase" class="${extra.follow === 'chase' ? 'on' : ''}">Chase</button><button data-act="free">Free camera</button></div>`;
  }

  // ------------------------------------------------------------ 3D labels
  updateLabels(items, W, H) { // items: [{id, x, y, depth, cat, text, sub, sel, stale}]
    const L = this.labels, seen = new Set();
    if (!this.showLabels) { for (const [, e] of L) e.style.display = 'none'; return; }
    items.sort((a, b) => (b.sel - a.sel) || (a.depth - b.depth));
    const boxes = []; let shown = 0; const cap = W < 500 ? 24 : 60;
    for (const it of items) {
      let e = L.get(it.id);
      if (!e) { e = document.createElement('div'); e.dataset.id = it.id; e.innerHTML = '<b></b><span></span>'; this.el.labels.appendChild(e); L.set(it.id, e); }
      seen.add(it.id);
      const w = it.sub ? 92 : 56, h = it.sub ? 30 : 18;
      // clamped into the viewport (fix round 1: labels at the screen edge were cut off on the phone)
      if (it.x > -60 && it.x < W + 60) it.x = Math.min(W - w / 2 - 2, Math.max(w / 2 + 2, it.x));
      const box = [it.x - w / 2, it.y - h - 14, it.x + w / 2, it.y - 14];
      const clash = !it.sel && (shown > cap || boxes.some(b => b[0] < box[2] && box[0] < b[2] && b[1] < box[3] && box[1] < b[3]));
      if (clash || it.x < -60 || it.y < -60 || it.x > W + 60 || it.y > H + 60) { e.style.display = 'none'; continue; }
      boxes.push(box); shown++;
      const cls = 'lbl c-' + it.cat + (it.sel ? ' sel' : '') + (it.stale ? ' stale' : '') + (it.sub ? '' : ' mini');
      if (e.className !== cls) e.className = cls;
      if (e._t !== it.text) { e.firstChild.textContent = it.text; e._t = it.text; }
      const sub = it.sub || ''; if (e._s !== sub) { e.lastChild.textContent = sub; e._s = sub; }
      e.style.display = '';
      e.style.transform = `translate3d(${it.x.toFixed(1)}px, ${it.y.toFixed(1)}px, 0)`;
    }
    for (const [id, e] of L) if (!seen.has(id)) { if (e._gone) { e.remove(); L.delete(id); } else { e.style.display = 'none'; e._gone = true; } } else e._gone = false;
  }
}
export const isInf = (tr) => !!((tr.phaseInfo && tr.phaseInfo.src === 'inf') || (tr.park && tr.park.src === 'inf'));
// ------------------------------------------------------------ altitude (review round-2 recheck m7)
// alt_baro is the transponder's PRESSURE altitude, referenced to 29.92 inHg (14 CFR 91.217(a)(2), LII copy read 2026-11-13),
// not a height above sea level: with the KHWD altimeter at 30.13 a C172 on short final reports about -150 ft. Until this
// round the list, the 3-D labels and the card printed it raw ('Final 28L -150 ft'), and the card set it beside a drawn
// height from another datum ('Altitude 400 ft · 560 ft AGL'). Now every place shows ONE value, the altitude MSL at the
// display time, and the card's height above the field is computed from that same rounded value:
//  1. 'baro' (default): what an altimeter set to the current KHWD altimeter setting A would read. A barometric altimeter
//     set to A reads H(p) - H(A), where H is the NWS pressure-altitude equation H(p) = (1 - (p / 1013.25)^0.190284) x
//     145,366.45 ft (weather.gov/media/epz/wxcalc/pressureAltitude.pdf, read 2026-11-13) [V]; the NWS altimeter-setting
//     equation (weather.gov/media/epz/wxcalc/altimeterSetting.pdf, read 2026-11-13) is the same relation solved for A at
//     the station elevation [V]. So MSL = alt_baro - H(A). No temperature correction (indicated, not true, altitude)
//     [inf]. (The cockpit rule of thumb 1 inHg ~ 1,000 ft gives 8 % more: dH/dA at 29.92 is 924 ft per inHg, computed.)
//     A comes from the KHWD METAR at or before the scene time (data clock), at most STALE_MIN (90) min old (js/env/state.js,
//     spec 3.3), and never from a QA weather override (?metar= / ?wx=: not the traffic's weather) - app.js qnhAt();
//  2. 'geom' (no usable METAR, or no alt_baro): alt_geom - GEOM_OFF, the Phase 1 calibration of the GNSS height against the
//     NASR runway surfaces (GEOM_OFF -108.09 ft, n 797, hwd_events.json `calibration`; classifier.js RULES) [obs calibration,
//     inf use]. Over the five review windows the two agree to a median of -37..+9 ft (docs/phase2_app.md section 9);
//  3. 'drawn': the engine's drawn height (D.y, NAVD 88 ~ MSL) where neither bracketing fix has a usable value (a take-off or
//     landing reconstructed across a recorder hole) [inf].
// The value is taken at the DISPLAY time, not from the newest fix (the replay display runs 60 s behind the newest fix): at a
// fix it is that fix's report; between fixes it follows the drawn height, shifted by the report-minus-drawn offset of the two
// fixes around the display time (interpolated in time) [inf] - see altitudeOf.
// Plausibility (owner's rule): an airborne aircraft is not below the ground under it. A value more than PLAUS_FT below that
// ground (a transponder off by more than the 125-ft tolerance, or a fix flagged airborne on the runway) falls to the next
// method; within PLAUS_FT (the 25-ft report quantum) it is shown at the ground height (`clamped`) [inf].
const STD_P0_HPA = 1013.25, STD_N = 0.190284, STD_K_FT = 145366.45;     // NWS pressure-altitude equation [V]
export const hStdFt = (hPa) => (1 - Math.pow(hPa / STD_P0_HPA, STD_N)) * STD_K_FT;
export const PLAUS_FT = 25;                     // [inf]
const ALT_ROUND = 10;                            // display step, ft (reports come in 25- or 100-ft steps) [inf]
const r10 = (v) => Math.round(v / ALT_ROUND) * ALT_ROUND + 0;   // + 0: no '-0'
/** Altitude of an airborne track at the display time. A (app.js altCtx): {tD (engine ms), qnh: {inHg, obsMs} | null,
 *  fieldFt, groundFt(x, z)}. -> null on the ground / no position, else {msl, mslR, above, fieldFt, method, interp, clamped, qnh}.
 *  The value at a fix is the report itself (baro / geom); between fixes it is the DRAWN height plus the report-minus-drawn
 *  offset of the fixes around the display time, interpolated in time - so the number follows the 3-D picture through a
 *  recorder hole (a flare, a reconstructed take-off) and still equals the report at every fix. (A straight interpolation of
 *  the reports printed '110 ft MSL' over a BL8 the engine drew touching down; review run below, docs/phase2_app.md 9.) */
export function altitudeOf(tr, A) {
  const D = tr && tr.disp; if (!D || !D.valid || D.ground || tr.stale) return null;
  const ok = Number.isFinite; if (!ok(D.y)) return null;
  const F = tr.fx || [], tD = A && A.tD != null ? A.tD : Infinity;
  let i = F.length - 1; while (i >= 0 && F[i].t > tD) i--;
  const a = i >= 0 ? F[i] : null, b = i + 1 < F.length ? F[i + 1] : null;
  const yFt = D.y / FT;
  // offset (report MSL - the fix's drawn target height) at a and b; interpolated when both exist, else the one that does
  const anchored = (mslOf) => {
    const off = (f) => { if (!f || !ok(f.y)) return null; const m = mslOf(f); return m != null && ok(m) ? m - f.y / FT : null; };
    const oa = off(a), ob = off(b);
    if (oa != null && ob != null) { const s = b.t - a.t, w = s > 0 ? Math.min(1, Math.max(0, (tD - a.t) / s)) : 0; return { v: yFt + oa + (ob - oa) * w, interp: s > 4000 && Math.min(tD - a.t, b.t - tD) > 1500 }; }
    if (oa != null) return { v: yFt + oa, interp: tD - a.t > 1500 };
    if (ob != null) return { v: yFt + ob, interp: b.t - tD > 1500 };
    return null;
  };
  const C = [];
  if (A && A.qnh) { const h = hStdFt(A.qnh.inHg * INHG_HPA); const p = anchored(f => f.altB != null ? f.altB - h : null); if (p) C.push({ msl: p.v, method: 'baro', interp: p.interp }); }
  { const p = anchored(f => f.altG != null && !f.geomBad ? f.altG - RULES.GEOM_OFF : null); if (p) C.push({ msl: p.v, method: 'geom', interp: p.interp }); }
  C.push({ msl: yFt, method: 'drawn', interp: false });
  let gFt = A && A.groundFt && ok(D.x) && ok(D.z) ? A.groundFt(D.x, D.z) : 0; if (!ok(gFt)) gFt = 0;
  const C1 = C.filter(q => ok(q.msl));
  const c = C1.find(q => q.msl >= gFt - PLAUS_FT) || C1[C1.length - 1];
  const clamped = c.msl < gFt, msl = Math.max(c.msl, gFt);
  const mslR = r10(msl), fieldFt = A && A.fieldFt != null ? A.fieldFt : FIELD_ELEV_FT;
  return { msl, mslR, above: r10(mslR - fieldFt), fieldFt, method: c.method, interp: c.interp, clamped, qnh: c.method === 'baro' ? A.qnh : null };
}
/** list rows and 3-D labels: '1,450 ft' (the list's legend and the card say 'ft MSL') */
export const altShort = (r) => r ? `${fmtInt(r.mslR)} ft` : '';
/** card: '1,450 ft MSL' + '1,400 ft above field' (from the same rounded value, so the two never disagree) */
export function altCard(r) {
  const ab = r.above >= ALT_ROUND ? `${fmtInt(r.above)} ft above field` : r.above <= -ALT_ROUND ? `${fmtInt(-r.above)} ft below field elevation` : 'at field elevation';
  return { msl: `${fmtInt(r.mslR)} ft MSL`, above: ab };
}
const QNH_WHY = { override: 'the QA weather override is not used for altitudes', none: 'no KHWD METAR at or before this time', stale: 'the latest KHWD METAR is over 90 min old', noalt: 'the KHWD METAR has no altimeter setting' };
const tLocal = (ms) => new Date(ms).toLocaleTimeString('en-US', { timeZone: 'America/Los_Angeles', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' });
/** the method, for the card's data line and the list legend: {text, title} */
export function altMethod(r, A) {
  const q = r ? r.qnh : A && A.qnh;
  const m = r ? r.method : q ? 'baro' : 'geom';
  const fe = `field elevation ${fmtInt(r ? r.fieldFt : (A && A.fieldFt) ?? FIELD_ELEV_FT)} ft (FAA NASR)`;
  const base = m === 'baro' ? `pressure altitude corrected with the KHWD altimeter ${q.inHg.toFixed(2)} inHg (METAR ${tLocal(q.obsMs)})`
    : m === 'geom' ? `GNSS height + ${fmtInt(-RULES.GEOM_OFF)} ft (HWD calibration${A && A.qnh ? ', no pressure altitude reported' : '; ' + (QNH_WHY[A && A.qnhWhy] || QNH_WHY.none)})`
    : 'drawn height (no usable altitude report at this time)';
  const why = m === 'baro' ? `MSL = alt_baro - H(A), H(p) = (1 - (p/1013.25 hPa)^0.190284) x 145,366.45 ft (NWS pressure-altitude and altimeter-setting equations); indicated altitude, no temperature correction; transponder altitude is within 125 ft of the altimeter (14 CFR 91.217)`
    : m === 'geom' ? `alt_geom - (${RULES.GEOM_OFF.toFixed(2)} ft): the Phase 1 calibration of the GNSS height against the NASR runway surfaces (n 797)`
    : 'the traffic engine\'s drawn height (NAVD 88), reconstructed between fixes';
  const extra = r ? [r.interp ? 'between two fixes: the drawn path, shifted to match the reports at the fixes on either side' : '', r.clamped ? 'shown at the ground height (the report was up to 25 ft below it)' : ''].filter(Boolean) : [];
  return { text: base, title: [why, fe, ...extra].join('; ') };
}
function parkText(tr, extra) {
  const p = tr.park; if (!p) return '';
  if (p.inside) return `In hangar${p.zone ? ' ' + esc(p.zone) : ''} ${inf(p.rule || 'signal ended next to the hangar')}`;
  const kind = PARK_KIND[p.kind] || (p.kind ? String(p.kind).replace(/_/g, ' ') : 'parked');
  const where = extra.parkLabel || p.zone || null;
  // (fix round 1: 'unspotted [obs]' read as nonsense on the phone card - an aircraft parked where no Phase 1 spot is mapped
  // stands at its own reported position, which is what the obs mark then says)
  if (p.kind === 'unspotted' || !p.spotId) return `Parked here${where ? ' · ' + esc(where) : ''} <span class="dim">· no mapped spot (its own reported position)</span>`;
  return `${where ? esc(where) : esc(kind)}${where && kind ? ` <span class="dim">· ${esc(kind)}</span>` : ''} ${p.src === 'inf' ? inf('spot inferred (NAIP / parked stays)') : '<span class="obs" title="spot observed: two or more independent observations (NAIP, recorded stays)">obs</span>'}`;
}
function ago(ms) { if (ms == null) return '—'; const m = Math.round(ms / 60000); return m < 1 ? 'just now' : m < 60 ? m + ' min ago' : Math.floor(m / 60) + ' h ' + (m % 60) + ' min ago'; }
