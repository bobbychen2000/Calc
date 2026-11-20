// forked from sfo3d@e3218d6 js/live/ui.js
// DOM user interface: status bar, flight lists, search, detail card, 3D labels, view presets, settings, about, and a legend
// slot. Mobile first: on phones the list is a bottom sheet (live.css).
// sha3d changes: brand and views for ZSSS; clock in Asia/Shanghai; no ATC sheet (PLAN s.6b Q4: no audio toggle); the SFO
// gate-plan rows, flysfo deep links, US regional-brand headline and runway-statistics sheet are removed; the traffic label
// functions come from ./traffic_api.js (Phase 2 stubs, the Phase 3 traffic engine re-exports its own there); setLegend()
// is the slot for the planned Observed / Inferred legend; setNote() shows a one-line scene note (e.g. "no traffic yet").
// P2e (UI shell): the Observed / Inferred legend box (a key line that opens a per-layer body; ui.el.legend is the body, so
// setLegend(html) and other packages' 'prev + mine' appends keep working; addLegendLine(key, html) for new lines), stand
// labels (updateStandLabels) and a stand card (renderStandCard), stands in the search, a close button on the popovers,
// the runway-rule setting, mode-aware empty text. Phone portrait: bottom sheet; laptop: side panel (live.css).
import { phaseLabel, category, gateLabel } from './traffic_api.js';
import { TZ } from '../env/clock.js';

const $ = (s, r = document) => r.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmtInt = (v) => v == null || isNaN(v) ? '—' : Math.round(v).toLocaleString('en-US');
const CAT_NAME = { arr: 'Arrivals', dep: 'Departures', ground: 'On ground', all: 'All' };
// view buttons: [id, label]; js/live/app.js view() knows each id
export const VIEW_BUTTONS = [['overview', 'Overview'], ['t2', 'T2'], ['t1', 'T1'], ['runways', 'Runways'], ['tower', 'Tower'], ['top', 'Top']];

export class UI {
  constructor(root, opts) {
    this.root = root; this.o = opts; // {onSelect(hex), onView(name), onFollow(mode), onSetting(k,v), showOthers()}
    this.tab = 'all'; this.q = ''; this.sel = null; this.atcMark = new Map(); this.labels = new Map(); this.showLabels = true; this.sheet = 'peek';
    this.build();
  }
  build() {
    const R = this.root;
    R.insertAdjacentHTML('beforeend', `
<div id="slabels" aria-hidden="true"></div>
<div id="labels" aria-hidden="true"></div>
<header id="top">
  <div class="brand"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5z"/></svg><span><b>SHA</b> Live 3D</span></div>
  <button id="status" class="pill" title="Data status"><i class="dot"></i><span class="txt">Starting…</span></button>
  <div id="clock" class="mono"></div>
</header>
<nav id="views" aria-label="Views">
  ${VIEW_BUTTONS.map(([v, l]) => `<button data-view="${v}">${l}</button>`).join('')}
  <button id="btn-settings" class="icon" title="Settings" aria-label="Settings"><svg viewBox="0 0 24 24"><path d="M12 15.5A3.5 3.5 0 1 1 12 8.5a3.5 3.5 0 0 1 0 7m7.43-2.53c.04-.32.07-.64.07-.97s-.03-.66-.07-1l2.11-1.63-2-3.46-2.49 1a7.3 7.3 0 0 0-1.69-.98l-.38-2.65h-4l-.38 2.65c-.61.25-1.17.58-1.69.98l-2.49-1-2 3.46L4.57 11c-.04.34-.07.67-.07 1s.03.65.07.97l-2.11 1.66 2 3.46 2.49-1c.52.4 1.08.73 1.69.98l.38 2.65h4l.38-2.65c.61-.25 1.17-.58 1.69-.98l2.49 1 2-3.46z"/></svg></button>
  <button id="btn-about" class="icon" title="About the data" aria-label="About"><svg viewBox="0 0 24 24"><path d="M11 17h2v-6h-2zm1-15a10 10 0 1 0 0 20 10 10 0 0 0 0-20m0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16M11 9h2V7h-2z"/></svg></button>
</nav>
<aside id="panel" class="peek">
  <button id="grab" aria-label="Expand list"><i></i></button>
  <div class="tabs" role="tablist">
    <button data-tab="arr" class="t-arr">Arrivals <b></b></button><button data-tab="dep" class="t-dep">Departures <b></b></button>
    <button data-tab="ground" class="t-ground">Ground <b></b></button><button data-tab="all" class="t-all">All <b></b></button>
  </div>
  <div id="note" class="rwystats" hidden></div>
  <div class="search"><input id="search" type="search" placeholder="Flight, airline, type, stand" autocomplete="off" spellcheck="false"></div>
  <div id="list" role="list"></div>
</aside>
<section id="card" hidden></section>
<div id="settings" class="pop" hidden>
  <h3>Settings</h3>
  <label>Lighting <select data-set="light"><option value="real">Real time at Hongqiao</option><option value="dawn">Dawn</option><option value="day">Day</option><option value="dusk">Dusk</option><option value="night">Night</option></select></label>
  <label>Quality <select data-set="quality"><option value="auto">Auto</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label>
  <label class="chk"><input type="checkbox" data-set="labels" checked> Show labels (stands, traffic)</label>
  <label title="Which runway direction the simulation infers from the METAR wind (docs/phase1/sources_sim.md s.5.2)">Runway direction rule <select data-set="rwyrule"><option value="tailwind">Tail-wind rule (default)</option><option value="intowind">Into the wind (fallback)</option></select></label>
  <label class="chk"><input type="checkbox" data-set="others" checked> Show traffic not bound for SHA</label>
</div>
<div id="about" class="pop wide" hidden></div>
<div id="legendbox" class="lg"><button id="lg-h" class="lg-h" aria-expanded="false" aria-controls="legend" title="What is observed and what is inferred"><span class="srcchip obs">obs</span> observed <span class="srcchip inf">inf</span> inferred <i class="lg-c" aria-hidden="true"></i></button><div id="legend" class="lg-b" hidden></div></div>
<footer id="attrib"></footer>
<div id="loading"><div class="lbox"><div class="brand big"><b>SHA</b> Live 3D</div><div class="bar"><i></i></div><div class="msg">Loading…</div></div></div>
`);
    this.el = { status: $('#status'), clock: $('#clock'), list: $('#list'), card: $('#card'), panel: $('#panel'), labels: $('#labels'), search: $('#search'), settings: $('#settings'), about: $('#about'), attrib: $('#attrib'), loading: $('#loading'), note: $('#note'), legend: $('#legend'), legendBox: $('#legendbox'), slabels: $('#slabels') };
    this.standLabels = new Map(); this.stands = []; this.onStand = null; this.onExtraSetting = null; this.legendLines = new Map();
    $('#lg-h').addEventListener('click', () => this.openLegend(this.el.legend.hidden));
    this.el.slabels.addEventListener('click', e => { const l = e.target.closest('[data-stand]'); if (l && this.onStand) this.onStand(l.dataset.stand, true); });
    this.pops = [this.el.settings, this.el.about];
    R.querySelectorAll('#panel .tabs button').forEach(b => b.addEventListener('click', () => { this.tab = b.dataset.tab; this.renderList(true); if (this.sheet === 'peek') this.setSheet('open'); }));
    this.el.search.addEventListener('input', () => { this.q = this.el.search.value.trim().toLowerCase(); if (this.q && this.tab !== 'all') this.tab = 'all'; this.renderList(true); });
    this.el.search.addEventListener('focus', () => { if (this.sheet !== 'open') this.setSheet('open'); });
    $('#grab').addEventListener('click', () => this.setSheet(this.sheet === 'open' ? 'peek' : 'open'));
    R.querySelectorAll('#views [data-view]').forEach(b => b.addEventListener('click', () => this.o.onView(b.dataset.view)));
    this.el.list.addEventListener('click', e => { const st = e.target.closest('[data-stand]'); if (st) { if (this.onStand) this.onStand(st.dataset.stand, true); return; } const row = e.target.closest('[data-hex]'); if (row) this.o.onSelect(row.dataset.hex, true); });
    this.el.labels.addEventListener('click', e => { const l = e.target.closest('[data-hex]'); if (l) this.o.onSelect(l.dataset.hex, true); });
    $('#btn-settings').addEventListener('click', () => this.toggle(this.el.settings));
    $('#btn-about').addEventListener('click', () => this.toggle(this.el.about));
    this.el.status.addEventListener('click', () => this.toggle(this.el.about));
    this.el.settings.addEventListener('change', e => { const k = e.target.dataset.set; if (!k) return; const v = e.target.type === 'checkbox' ? e.target.checked : e.target.value; if (k === 'labels') this.showLabels = v; this.o.onSetting(k, v); if (this.onExtraSetting) this.onExtraSetting(k, v); });
    document.addEventListener('pointerdown', e => { for (const p of this.pops) if (!p.hidden && !p.contains(e.target) && !e.target.closest('#btn-settings,#btn-about,#status')) p.hidden = true; });
    const C = this.el.card;
    this.el.card.addEventListener('click', e => {
      const b = e.target.closest('button[data-act]'); if (!b) return;
      const a = b.dataset.act;
      if (this.cardKind === 'stand') { if (a === 'close') this.renderStandCard(null); else if (a === 'fly' && this.onStand) this.onStand(this.sel, false, true); else if (a === 'more') C.classList.toggle('compact'); return; }
      if (a === 'close') this.o.onSelect(null); else this.o.onFollow(a);
    });
    for (const p of this.pops) p.addEventListener('click', e => { if (e.target.closest('[data-close]')) p.hidden = true; });
  }
  toggle(p) { const show = p.hidden; for (const q of this.pops) q.hidden = true; p.hidden = !show; }
  setSheet(s) { this.sheet = s; this.el.panel.className = s; }
  progress(frac, msg) { const L = this.el.loading; if (!L) return; L.querySelector('.bar i').style.width = Math.round(frac * 100) + '%'; if (msg) L.querySelector('.msg').textContent = msg; }
  ready() { const L = this.el.loading; L.classList.add('done'); setTimeout(() => L.remove(), 700); this.el.loading = null; }
  fail(msg) { const L = this.el.loading; if (L) { L.querySelector('.msg').innerHTML = msg; L.classList.add('err'); return; }
    let F = this.el.fatal; if (!F) { F = this.el.fatal = document.createElement('div'); F.id = 'fatal'; F.setAttribute('role', 'alert'); (this.root || document.body).appendChild(F); }
    F.innerHTML = '<div class="lbox"><div class="msg">' + msg + '</div></div>'; F.hidden = false; }
  setAbout(html) { this.el.about.innerHTML = '<button class="x" data-close aria-label="Close">×</button>' + html; }
  setAttrib(html) { this.el.attrib.innerHTML = html; }
  /** Legend body (the Observed / Inferred box; the key line stays): replaces the body html ('' empties it). */
  setLegend(html) { this.el.legend.innerHTML = html || ''; this.legendLines.clear(); if (!html) this.openLegend(false); }
  /** Add or replace one legend line (key = layer name). */
  addLegendLine(key, html) {
    let e = this.el.legend.querySelector(`[data-lg="${CSS.escape(key)}"]`);
    if (!e) { e = document.createElement('div'); e.className = 'lg-l'; e.dataset.lg = key; this.el.legend.appendChild(e); }
    e.innerHTML = html; this.legendLines.set(key, html);
  }
  openLegend(on) { const b = this.el.legend; b.hidden = !on || !b.innerHTML; $('#lg-h').setAttribute('aria-expanded', String(!b.hidden)); this.el.legendBox.classList.toggle('open', !b.hidden); }
  /** One-line note at the top of the list panel (e.g. "No traffic yet"). */
  setNote(text) { const e = this.el.note; if (e._t === text) return; e._t = text; e.textContent = text || ''; e.hidden = !text; }

  // ------------------------------------------------------------ status bar
  setStatus({ state, text, sub, title }) {
    const s = this.el.status; s.dataset.state = state; const t = s.querySelector('.txt'); if (t.textContent !== text) t.textContent = text;
    let p = s.querySelector('.prov'); if (!p) { p = document.createElement('span'); p.className = 'prov'; s.appendChild(p); } const ps = sub ? '· ' + sub : ''; if (p.textContent !== ps) p.textContent = ps;
    if (title) s.title = title;
  }
  setClock(d, extra) {
    const t = d.toLocaleTimeString('en-GB', { timeZone: TZ, hour: '2-digit', minute: '2-digit' });
    this.el.clock.innerHTML = `${esc(t)} <span class="dim">CST</span>${extra ? ' <span class="wx">' + esc(extra) + '</span>' : ''}`;
  }

  // ------------------------------------------------------------ lists (filled by the Phase 3 traffic engine)
  rowsFor(tracks) {
    const q = this.q, out = [];
    for (const tr of tracks) {
      if (!tr.disp.valid && !tr.stale) continue;
      const cat = category(tr);
      if (this.tab !== 'all' && cat !== this.tab) continue;
      if (this.tab === 'all' && cat === 'other' && !this.o.showOthers()) continue;
      if (cat === 'vehicle' && !q) continue;
      if (q) {
        const hay = [tr.cs && tr.cs.display, tr.info.flight, tr.info.reg, tr.info.icao, tr.type && tr.type.full, tr.cs && tr.cs.airline && tr.cs.airline.name, tr.gate && tr.gate.name, tr.hex].filter(Boolean).join(' ').toLowerCase();
        if (!hay.includes(q)) continue;
      }
      out.push({ tr, cat });
    }
    out.sort((a, b) => Math.hypot(a.tr.disp.x, a.tr.disp.z) - Math.hypot(b.tr.disp.x, b.tr.disp.z));
    return out;
  }
  renderList(force, tracks = this._tracks || []) {
    this._tracks = tracks;
    const counts = { arr: 0, dep: 0, ground: 0, all: 0 };
    for (const tr of tracks) { if (!tr.disp.valid && !tr.stale) continue; const c = category(tr); if (counts[c] != null) counts[c]++; if (c !== 'other' || this.o.showOthers()) counts.all++; }
    this.root.querySelectorAll('#panel .tabs button').forEach(b => { b.classList.toggle('on', b.dataset.tab === this.tab); b.querySelector('b').textContent = counts[b.dataset.tab]; });
    const rows = this.rowsFor(tracks); const now = Date.now();
    const rowsHtml = rows.length ? rows.map(({ tr, cat }) => {
      const I = tr.info, D = tr.disp; const name = tr.cs && tr.cs.display || I.reg || tr.hex.toUpperCase();
      const alt = D.ground || tr.stale || I.altBaro == null ? '' : `${fmtInt(I.altBaro)} ft`;
      const spd = tr.stale ? '' : D.gs > 1 ? `${fmtInt(D.gs / 0.514444)} kt` : '';
      const src = tr.src === 'inf' ? '<span class="srcchip inf" title="inferred (simulated)">inf</span>' : tr.src === 'obs' ? '<span class="srcchip obs" title="observed">obs</span>' : '';
      return `<div class="row c-${cat}${this.sel === tr.hex ? ' sel' : ''}${tr.stale ? ' stale' : ''}" data-hex="${tr.hex}" role="listitem">
  <div class="l1"><b>${esc(name)}</b><span class="ty mono">${esc(I.icao || '····')}</span>${src}<span class="ph">${esc(phaseLabel(tr, now))}</span></div>
  <div class="l2"><span class="rt">${esc(tr.gate ? gateLabel(tr.gate) : '')}</span><span class="nums mono">${esc([alt, spd].filter(Boolean).join('  '))}</span></div></div>`;
    }).join('') : '';
    const sr = this.standRows();
    const html = (rowsHtml || sr) ? rowsHtml + sr : `<div class="empty">${this.q ? 'No matches.' : this.emptyText || 'No traffic.'}</div>`;
    if (force || html !== this._lastHtml) { const st = this.el.list.scrollTop; this.el.list.innerHTML = html; this.el.list.scrollTop = st; this._lastHtml = html; }
  }

  // ------------------------------------------------------------ detail card (generic; Phase 3 adds runway / stand rows)
  renderCard(tr, extra = {}) {
    const C = this.el.card;
    if (!tr) { if (this.cardKind === 'stand') return; C.hidden = true; this.sel = null; this.cardKind = null; document.body.classList.remove('has-card'); return; }
    this.sel = tr.hex; this.cardKind = 'track'; C.hidden = false; document.body.classList.add('has-card');
    const I = tr.info, D = tr.disp, cat = category(tr), now = Date.now(); const al = tr.cs && tr.cs.airline;
    C.className = 'c-' + cat;
    C.innerHTML = `
<div class="ch"><div class="al">${esc(al ? al.name : I.flight ? 'Callsign ' + I.flight : 'Unidentified')}</div><button data-act="close" class="x" aria-label="Close">×</button></div>
<div class="fl"><b>${esc(tr.cs && tr.cs.display || I.reg || tr.hex.toUpperCase())}</b></div>
<div class="ty">${esc(tr.type ? tr.type.full : 'Type not known')}${I.icao ? ` <span class="mono dim">${esc(I.icao)}</span>` : ''}</div>
<div class="ph c-${cat}">${esc(phaseLabel(tr, now))}</div>
<dl>
  ${tr.gate ? `<dt>Stand</dt><dd class="mono">${esc(gateLabel(tr.gate))}</dd>` : ''}
  <dt>Altitude</dt><dd class="mono">${D.ground || I.altBaro == null ? 'On ground' : fmtInt(I.altBaro) + ' ft'}</dd>
  <dt>Speed</dt><dd class="mono">${fmtInt(D.gs / 0.514444)} kt</dd>
  <dt>Source</dt><dd>${tr.src === 'obs' ? 'observed' : tr.src === 'inf' ? 'inferred (simulated)' : '—'}</dd>
</dl>
${extra.modelNote ? `<div class="model">${esc(extra.modelNote)}</div>` : ''}
<div class="acts"><button data-act="follow" class="${extra.follow === 'follow' ? 'on' : ''}">Follow</button><button data-act="chase" class="${extra.follow === 'chase' ? 'on' : ''}">Chase</button><button data-act="free">Free camera</button></div>`;
  }

  // ------------------------------------------------------------ stands (P2e): search rows, labels, card
  /** stands: [{name, area, cls, clsSrc, contact, src, ...}] (js/live/shell.js builds them from data/sha_stands.js) */
  setStands(list) { this.stands = list || []; this.renderList(true); }
  standRows() {
    const q = this.q; if (!q || !this.stands.length) return '';
    const hit = this.stands.filter(s => s.name.toLowerCase().startsWith(q) || ('stand ' + s.name).startsWith(q) || (s.area || '').toLowerCase().includes(q)).slice(0, 40);
    if (!hit.length) return '';
    return `<div class="sect">Stands <span class="dim">(${hit.length}${hit.length === 40 ? '+' : ''})</span></div>` + hit.map(s => `<div class="row c-stand${this.cardKind === 'stand' && this.sel === s.name ? ' sel' : ''}" data-stand="${esc(s.name)}" role="listitem">
  <div class="l1"><b>Stand ${esc(s.name)}</b><span class="ty mono">class ${esc(s.cls)}</span><span class="srcchip ${s.clsSrc === 'obs' ? 'obs' : 'inf'}" title="class ${s.clsSrc === 'obs' ? 'observed (Sentinel-2 wide-body evidence)' : 'inferred'}">${s.clsSrc === 'obs' ? 'obs' : 'inf'}</span><span class="ph">${s.contact ? 'contact' : 'remote'}</span></div>
  <div class="l2"><span class="rt">${esc(s.area || '')}</span></div></div>`).join('');
  }
  /** Stand labels: items [{name, x, y, depth, cls, clsSrc, sel}] in CSS px; overlapping labels are hidden (nearest wins). */
  updateStandLabels(items, W, H) {
    const L = this.standLabels, seen = new Set();
    if (!this.showLabels) items = [];
    items.sort((a, b) => (b.sel - a.sel) || (a.depth - b.depth));
    const boxes = []; let shown = 0;
    for (const it of items) {
      const w = 18 + it.name.length * 7.5 + 16, h = 18;
      const box = [it.x - w / 2, it.y - h - 8, it.x + w / 2, it.y - 6];
      if (!it.sel && (shown >= 90 || boxes.some(b => b[0] < box[2] + 2 && box[0] < b[2] + 2 && b[1] < box[3] + 1 && box[1] < b[3] + 1))) continue;
      if (it.x < -40 || it.y < -40 || it.x > W + 40 || it.y > H + 40) continue;
      boxes.push(box); shown++;
      let e = L.get(it.name);
      if (!e) { e = document.createElement('div'); e.dataset.stand = it.name; e.innerHTML = `<b>${esc(it.name)}</b><i>${esc(it.cls)}</i>`; this.el.slabels.appendChild(e); L.set(it.name, e); }
      const cls = 'slbl ' + (it.clsSrc === 'obs' ? 'obs' : 'inf') + (it.contact ? ' contact' : ' remote') + (it.sel ? ' sel' : '');
      if (e.className !== cls) e.className = cls;
      e.title = `Stand ${it.name} · class ${it.cls} (${it.clsSrc === 'obs' ? 'observed' : 'inferred'}) · ${it.contact ? 'contact' : 'remote'}`;
      e.style.display = ''; e.style.transform = `translate3d(${it.x.toFixed(1)}px, ${it.y.toFixed(1)}px, 0)`;
      seen.add(it.name);
    }
    for (const [n, e] of L) if (!seen.has(n)) e.style.display = 'none';
  }
  /** Stand card: s = shell stand record (or null to close). */
  renderStandCard(s) {
    const C = this.el.card;
    if (!s) { if (this.cardKind === 'stand') { C.hidden = true; this.sel = null; this.cardKind = null; document.body.classList.remove('has-card'); this.renderList(true); } return; }
    this.cardKind = 'stand'; this.sel = s.name; C.hidden = false; document.body.classList.add('has-card'); C.className = 'c-stand';   // (re-render: not compact)
    const chip = (src) => `<span class="srcchip ${src === 'obs' ? 'obs' : 'inf'}">${src === 'obs' ? 'obs' : 'inf'}</span>`;
    C.innerHTML = `
<div class="ch"><div class="al">${esc(s.area || 'Stand')}</div><button data-act="more" class="more" aria-label="Details">details</button><button data-act="close" class="x" aria-label="Close">×</button></div>
<div class="fl"><b>Stand ${esc(s.name)}</b>${s.alias && s.alias.length ? `<span class="dim">also ${esc(s.alias.join(', '))}</span>` : ''}</div>
<div class="ty">${s.contact ? 'Contact stand' : 'Remote stand'}${s.service ? ` <span class="dim">· ${esc(s.service)}</span>` : ''}</div>
<dl>
  <dt>Position</dt><dd>OpenStreetMap stop node${s.osmNode ? ` <span class="mono dim">${esc(s.osmNode)}</span>` : ''} ${chip('obs')}</dd>
  <dt>Heading</dt><dd class="mono">${esc(s.hdg)}° <span class="dim">(lead-in line)</span> ${chip(s.hdgSrc || 'obs')}</dd>
  <dt>Class</dt><dd><b>${esc(s.cls)}</b> <span class="dim">· span ≤ ${esc(s.spanMax)} m</span> ${chip(s.clsSrc)}</dd>
  <dt>Bridges</dt><dd>${s.bridges ? `${s.bridges} ${s.bridgesObs ? `(${s.bridgesObs} seen on SAR)` : ''} ${chip(s.bridgesObs ? 'obs' : 'inf')}` : '—'}</dd>
  <dt>Push-back</dt><dd>${s.push ? esc(s.push) + ' ' + chip('inf') : '—'}</dd>
</dl>
<div class="model">${esc(s.note || '')}</div>
<div class="acts"><button data-act="fly">Fly to stand</button><button data-act="close">Close</button></div>`;
    this.renderList(true);
  }

  // ------------------------------------------------------------ 3D labels
  updateLabels(items, W, H) { // items: [{hex, x, y, depth, cat, text, sub, sel}]
    const L = this.labels, seen = new Set();
    if (!this.showLabels) { for (const [, e] of L) e.style.display = 'none'; return; }
    items.sort((a, b) => (b.sel - a.sel) || (a.depth - b.depth));
    const boxes = []; let shown = 0;
    for (const it of items) {
      let e = L.get(it.hex);
      if (!e) { e = document.createElement('div'); e.dataset.hex = it.hex; e.innerHTML = '<b></b><span></span><em></em>'; this.el.labels.appendChild(e); L.set(it.hex, e); }
      seen.add(it.hex);
      const w = it.sub ? 104 : 64, h = it.sub ? 34 : 20;
      const box = [it.x - w / 2, it.y - h - 16, it.x + w / 2, it.y - 16];
      const clash = !it.sel && (shown > 60 || boxes.some(b => b[0] < box[2] && box[0] < b[2] && b[1] < box[3] && box[1] < b[3]));
      if (clash || it.x < -60 || it.y < -60 || it.x > W + 60 || it.y > H + 60) { e.style.display = 'none'; continue; }
      boxes.push(box); shown++;
      const cls = 'lbl c-' + it.cat + (it.sel ? ' sel' : '') + (it.stale ? ' stale' : '') + (it.sub ? '' : ' mini');
      if (e.className !== cls) e.className = cls;
      if (e._t !== it.text) { e.firstChild.textContent = it.text; e._t = it.text; }
      const sub = it.sub || ''; if (e._s !== sub) { e.children[1].textContent = sub; e._s = sub; }
      e.style.display = '';
      e.style.transform = `translate3d(${it.x.toFixed(1)}px, ${it.y.toFixed(1)}px, 0)`;
    }
    for (const [hex, e] of L) if (!seen.has(hex)) { if (e._gone) { e.remove(); L.delete(hex); } else { e.style.display = 'none'; e._gone = true; } } else e._gone = false;
  }
}
export { CAT_NAME };
