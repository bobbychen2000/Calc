// DOM user interface: status bar, flight lists, search, detail card (identity, runway, gate vs SFO's plan, deep links),
// 3D labels, view presets, runway statistics sheet, ATC sheet (atc.js), settings, about. Mobile first: on phones the
// list, the stats and the ATC panels are bottom sheets.
import { phaseLabel, category, gateLabel } from './traffic.js';
import { atcHtml, roleChip } from './atc.js';

const $ = (s, r = document) => r.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmtInt = (v) => v == null || isNaN(v) ? '—' : Math.round(v).toLocaleString('en-US');
const CAT_NAME = { arr: 'Arrivals', dep: 'Departures', ground: 'On ground', all: 'All' };

export class UI {
  constructor(root, opts) {
    this.root = root; this.o = opts; // {onSelect(hex), onView(name), onFollow(mode), onSetting(k,v), getTrack(hex), mode}
    this.tab = 'arr'; this.q = ''; this.sel = null; this.atcMark = new Map(); this.labels = new Map(); this.showLabels = true; this.sheet = 'peek';
    this.build();
  }
  build() {
    const R = this.root;
    R.insertAdjacentHTML('beforeend', `
<div id="labels" aria-hidden="true"></div>
<header id="top">
  <div class="brand"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5z"/></svg><span><b>SFO</b> Live 3D</span></div>
  <button id="status" class="pill" title="Data feed status"><i class="dot"></i><span class="txt">Starting…</span></button>
  <button id="btn-atc" class="pill" title="ATC audio (LiveATC.net)" aria-label="ATC audio"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a8 8 0 0 0-8 8v6a3 3 0 0 0 3 3h1a1 1 0 0 0 1-1v-5a1 1 0 0 0-1-1H6v-2a6 6 0 0 1 12 0v2h-2a1 1 0 0 0-1 1v5a1 1 0 0 0 1 1h1a3 3 0 0 0 3-3v-6a8 8 0 0 0-8-8"/></svg><span class="al">ATC</span><span class="tn"></span></button>
  <div id="clock" class="mono"></div>
</header>
<nav id="views" aria-label="Views">
  <button data-view="overview">Overview</button><button data-view="terminal">Terminals</button><button data-view="final28">28 Approach</button>
  <button data-view="runways1">1L/1R Departures</button><button data-view="tower">Tower</button><button data-view="top">Top</button>
  <button id="btn-settings" class="icon" title="Settings" aria-label="Settings"><svg viewBox="0 0 24 24"><path d="M12 15.5A3.5 3.5 0 1 1 12 8.5a3.5 3.5 0 0 1 0 7m7.43-2.53c.04-.32.07-.64.07-.97s-.03-.66-.07-1l2.11-1.63-2-3.46-2.49 1a7.3 7.3 0 0 0-1.69-.98l-.38-2.65h-4l-.38 2.65c-.61.25-1.17.58-1.69.98l-2.49-1-2 3.46L4.57 11c-.04.34-.07.67-.07 1s.03.65.07.97l-2.11 1.66 2 3.46 2.49-1c.52.4 1.08.73 1.69.98l.38 2.65h4l.38-2.65a7.3 7.3 0 0 0 1.69-.98l2.49 1 2-3.46z"/></svg></button>
  <button id="btn-about" class="icon" title="About the data" aria-label="About"><svg viewBox="0 0 24 24"><path d="M11 17h2v-6h-2zm1-15a10 10 0 1 0 0 20 10 10 0 0 0 0-20m0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16M11 9h2V7h-2z"/></svg></button>
</nav>
<aside id="panel" class="peek">
  <button id="grab" aria-label="Expand list"><i></i></button>
  <div class="tabs" role="tablist">
    <button data-tab="arr" class="t-arr">Arrivals <b></b></button><button data-tab="dep" class="t-dep">Departures <b></b></button>
    <button data-tab="ground" class="t-ground">Ground <b></b></button><button data-tab="all" class="t-all">All <b></b></button>
  </div>
  <button id="rwystats" class="rwystats mono" title="Runway statistics: landings (↓) and take-offs (↑) per runway detected from the aircraft's own motion"></button>
  <div class="search"><input id="search" type="search" placeholder="Flight, tail number, type, airline" autocomplete="off" spellcheck="false"></div>
  <div id="list" role="list"></div>
</aside>
<section id="card" hidden></section>
<div id="settings" class="pop" hidden>
  <h3>Settings</h3>
  <label>Lighting <select data-set="light"><option value="real">Real time at SFO</option><option value="day">Day</option><option value="dusk">Dusk</option><option value="night">Night</option></select></label>
  <label>Quality <select data-set="quality"><option value="auto">Auto</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label>
  <label class="chk"><input type="checkbox" data-set="labels" checked> Show labels</label>
  <label class="chk"><input type="checkbox" data-set="others" checked> Show traffic not bound for SFO</label>
  <button data-set="clearParked" class="ghost">Forget remembered parked aircraft</button>
</div>
<div id="about" class="pop wide" hidden></div>
<div id="rstats" class="pop wide sheet" hidden></div>
<div id="atc" class="pop wide sheet" hidden></div>
<footer id="attrib"></footer>
<div id="loading"><div class="lbox"><div class="brand big"><b>SFO</b> Live 3D</div><div class="bar"><i></i></div><div class="msg">Loading…</div></div></div>
`);
    this.el = { status: $('#status'), clock: $('#clock'), list: $('#list'), card: $('#card'), panel: $('#panel'), labels: $('#labels'), search: $('#search'), settings: $('#settings'), about: $('#about'), attrib: $('#attrib'), loading: $('#loading'), rstats: $('#rstats'), atc: $('#atc') };
    this.pops = [this.el.settings, this.el.about, this.el.rstats, this.el.atc];
    R.querySelectorAll('#panel .tabs button').forEach(b => b.addEventListener('click', () => { this.tab = b.dataset.tab; this.renderList(true); if (this.sheet === 'peek') this.setSheet('open'); }));
    this.el.search.addEventListener('input', () => { this.q = this.el.search.value.trim().toLowerCase(); if (this.q && this.tab !== 'all') this.tab = 'all'; this.renderList(true); });
    this.el.search.addEventListener('focus', () => { if (this.sheet !== 'open') this.setSheet('open'); });
    $('#grab').addEventListener('click', () => this.setSheet(this.sheet === 'open' ? 'peek' : 'open'));
    R.querySelectorAll('#views [data-view]').forEach(b => b.addEventListener('click', () => this.o.onView(b.dataset.view)));
    this.el.list.addEventListener('click', e => { const row = e.target.closest('[data-hex]'); if (row) this.o.onSelect(row.dataset.hex, true); });
    this.el.labels.addEventListener('click', e => { const l = e.target.closest('[data-hex]'); if (l) this.o.onSelect(l.dataset.hex, true); });
    $('#btn-settings').addEventListener('click', () => this.toggle(this.el.settings));
    $('#btn-about').addEventListener('click', () => this.toggle(this.el.about));
    this.el.status.addEventListener('click', () => this.toggle(this.el.about));
    $('#btn-atc').addEventListener('click', () => { this.toggle(this.el.atc); if (!this.el.atc.hidden) this.o.onAtc && this.o.onAtc('open'); });
    $('#rwystats').addEventListener('click', () => { this.toggle(this.el.rstats); if (!this.el.rstats.hidden) this.o.onStatsOpen && this.o.onStatsOpen(); });
    // stats + ATC sheets: rows / chips with data-hex select that aircraft; ATC feed buttons tune / open LiveATC
    for (const P of [this.el.rstats, this.el.atc]) P.addEventListener('click', e => {
      const h = e.target.closest('[data-hex]'); if (h) { this.o.onSelect(h.dataset.hex, true); if (window.innerWidth < 760) P.hidden = true; return; }
      const t = e.target.closest('button.tune'); if (t) { this.o.onAtc && this.o.onAtc('tune', t.dataset.mount); return; }
      if (e.target.closest('button.untune')) { this.o.onAtc && this.o.onAtc('tune', null); return; }
      const a = e.target.closest('a.listen'); if (a) { const m = a.dataset.mount; setTimeout(() => this.o.onAtc && this.o.onAtc('listen', m), 0); return; } // the link itself opens LiveATC (re-render after the click)
      if (e.target.closest('button.x')) P.hidden = true;
    });
    this.el.atc.addEventListener('input', e => { if (e.target.id === 'atc-delay') { const v = +e.target.value; const l = this.root.querySelector('#atc-delay-v'); if (l) l.textContent = v + ' s'; } });
    this.el.atc.addEventListener('change', e => { if (e.target.id === 'atc-delay') this.o.onAtc && this.o.onAtc('delay', +e.target.value); });
    this.el.settings.addEventListener('change', e => { const k = e.target.dataset.set; if (!k) return; const v = e.target.type === 'checkbox' ? e.target.checked : e.target.value; if (k === 'labels') this.showLabels = v; this.o.onSetting(k, v); });
    this.el.settings.addEventListener('click', e => { const k = e.target.dataset.set; if (k === 'clearParked') { this.o.onSetting(k, true); e.target.textContent = 'Forgotten'; } });
    document.addEventListener('pointerdown', e => { for (const p of this.pops) if (!p.hidden && !p.contains(e.target) && !e.target.closest('#btn-settings,#btn-about,#status,#btn-atc,#rwystats')) p.hidden = true; });
    this.el.card.addEventListener('click', e => {
      const b = e.target.closest('button[data-act]'); if (!b) return;
      const a = b.dataset.act; if (a === 'close') this.o.onSelect(null); else this.o.onFollow(a);
    });
  }
  toggle(p) { const show = p.hidden; for (const q of this.pops) q.hidden = true; p.hidden = !show; }
  // runway statistics sheet (stats.js statsHtml); re-rendered only while open
  statsOpen() { return !this.el.rstats.hidden; }
  setStatsSheet(html) { const P = this.el.rstats; const h = '<button class="x" aria-label="Close">×</button>' + html; if (P._h !== h) { const st = P.scrollTop; P.innerHTML = h; P.scrollTop = st; P._h = h; } }
  // ATC sheet (atc.js atcHtml); the slider is not re-rendered while it is being dragged
  atcOpen() { return !this.el.atc.hidden; }
  setAtc(state) {
    const P = this.el.atc; const act = document.activeElement;
    if (!P.hidden && !(act && act.id === 'atc-delay' && P.contains(act))) { const h = '<button class="x" aria-label="Close">×</button>' + atcHtml(state); if (P._h !== h) { const st = P.scrollTop; P.innerHTML = h; P.scrollTop = st; P._h = h; } }
    const b = this.root.querySelector('#btn-atc'); b.classList.toggle('on', !!state.tuned); b.querySelector('.tn').textContent = state.tuned ? (state.chip || 'on') : '';
  }
  setSheet(s) { this.sheet = s; this.el.panel.className = s; }
  progress(frac, msg) { const L = this.el.loading; if (!L) return; L.querySelector('.bar i').style.width = Math.round(frac * 100) + '%'; if (msg) L.querySelector('.msg').textContent = msg; }
  ready() { const L = this.el.loading; L.classList.add('done'); setTimeout(() => L.remove(), 700); this.el.loading = null; }
  fail(msg) { const L = this.el.loading; if (L) { L.querySelector('.msg').innerHTML = msg; L.classList.add('err'); } }
  setAbout(html) { this.el.about.innerHTML = html; }
  setAttrib(html) { this.el.attrib.innerHTML = html; }

  // ------------------------------------------------------------ status bar
  // text: main status ("Live · 3.0 s"); sub: provider names (hidden on phones, where the tooltip / About has them)
  setStatus({ state, text, sub, title }) {
    const s = this.el.status; s.dataset.state = state; const t = s.querySelector('.txt'); if (t.textContent !== text) t.textContent = text;
    let p = s.querySelector('.prov'); if (!p) { p = document.createElement('span'); p.className = 'prov'; s.appendChild(p); } const ps = sub ? '· ' + sub : ''; if (p.textContent !== ps) p.textContent = ps;
    if (title) s.title = title;
  }
  setStats(text) { const e = this.root.querySelector('#rwystats'); if (e && e._t !== text) { e.textContent = text ? text + ' ›' : ''; e._t = text; e.hidden = !text; } }
  setClock(d, extra) {
    const t = d.toLocaleTimeString('en-US', { timeZone: 'America/Los_Angeles', hour: 'numeric', minute: '2-digit' });
    const z = d.toLocaleTimeString('en-US', { timeZone: 'America/Los_Angeles', timeZoneName: 'short' }).split(' ').pop();
    this.el.clock.innerHTML = `${esc(t)} <span class="dim">${esc(z)}</span>${extra ? ' <span class="wx">' + esc(extra) + '</span>' : ''}`;
  }

  // ------------------------------------------------------------ lists
  rowsFor(tracks) {
    const q = this.q, out = [];
    for (const tr of tracks) {
      if (!tr.disp.valid && !tr.stale) continue;
      const cat = category(tr);
      if (this.tab !== 'all' && cat !== this.tab) continue;
      if (this.tab === 'all' && cat === 'other' && !this.o.showOthers()) continue;
      if (cat === 'vehicle' && !q) continue; // airport vehicles: only through the search
      if (q) {
        const hay = [tr.cs && tr.cs.display, tr.info.flight, tr.info.reg, tr.info.icao, tr.type && tr.type.full, tr.cs && tr.cs.airline && tr.cs.airline.name, tr.gate && tr.gate.name, tr.hex].filter(Boolean).join(' ').toLowerCase();
        if (!hay.includes(q)) continue;
      }
      out.push({ tr, cat });
    }
    const key = (r) => { const t = r.tr; if (r.cat === 'arr') return t.finalInfo ? -t.finalInfo.a : Math.hypot(t.disp.x, t.disp.z) + 50000;
      if (r.cat === 'dep') return -(t.liftoffAt || 0); if (r.cat === 'ground') return ({ takeoff: 0, landing: 1, holding: 2, taxi: 3, pushback: 4, stopped: 5, gate: 6, parked: 7 }[t.phase] ?? 8) * 1e6 + (t.stale ? 5e5 : 0) + (t.gate ? t.gate.name.charCodeAt(0) * 100 + parseInt(t.gate.name.slice(1)) || 0 : 0);
      return Math.hypot(t.disp.x, t.disp.z); };
    out.sort((a, b) => key(a) - key(b));
    return out;
  }
  renderList(force, tracks = this._tracks) {
    if (!tracks) return; this._tracks = tracks;
    const counts = { arr: 0, dep: 0, ground: 0, all: 0 };
    for (const tr of tracks) { if (!tr.disp.valid && !tr.stale) continue; const c = category(tr); if (counts[c] != null) counts[c]++; if (c !== 'other' || this.o.showOthers()) counts.all++; }
    this.root.querySelectorAll('#panel .tabs button').forEach(b => { b.classList.toggle('on', b.dataset.tab === this.tab); b.querySelector('b').textContent = counts[b.dataset.tab]; });
    const rows = this.rowsFor(tracks);
    const now = Date.now();
    const html = rows.length ? rows.map(({ tr, cat }) => {
      const I = tr.info, D = tr.disp;
      const name = tr.cs && tr.cs.display || I.reg || tr.hex.toUpperCase();
      const route = routeText(tr);
      const alt = D.ground || tr.stale || I.altBaro == null ? '' : `${fmtInt(I.altBaro)} ft`;
      const spd = tr.stale ? '' : D.gs > 1 ? `${fmtInt(D.gs / 0.514444)} kt` : '';
      return `<div class="row c-${cat}${this.sel === tr.hex ? ' sel' : ''}${tr.stale ? ' stale' : ''}${I.emergency ? ' emg' : ''}" data-hex="${tr.hex}" role="listitem">
  <div class="l1"><b>${esc(name)}</b><span class="ty mono">${esc(I.icao || '····')}</span><span class="rg mono">${esc(I.reg || '')}</span>${this.atcMark && this.atcMark.has(tr.hex) ? `<span class="atcchip">${esc(this.atcMark.get(tr.hex))}</span>` : ''}<span class="ph">${esc(phaseLabel(tr, now))}</span></div>
  <div class="l2"><span class="rt">${esc(route)}</span><span class="nums mono">${esc([alt, spd].filter(Boolean).join('  '))}</span></div></div>`;
    }).join('') : `<div class="empty">${this.q ? 'No matches.' : { arr: 'No arrivals in range right now.', dep: 'No departures in the last minutes.', ground: 'No aircraft reporting on the ground.', all: 'No traffic yet.' }[this.tab]}</div>`;
    if (force || html !== this._lastHtml) { const st = this.el.list.scrollTop; this.el.list.innerHTML = html; this.el.list.scrollTop = st; this._lastHtml = html; }
  }

  // ------------------------------------------------------------ detail card
  // extra: {modelNote, follow, sfo: Traffic.planFor(tr) result, atc: atc.js atcRoles(tr), tDisp: scene time}
  renderCard(tr, extra = {}) {
    const C = this.el.card;
    if (!tr) { C.hidden = true; this.sel = null; document.body.classList.remove('has-card'); return; }
    this.sel = tr.hex; C.hidden = false; document.body.classList.add('has-card');
    const I = tr.info, D = tr.disp, cat = category(tr), now = Date.now();
    const al = tr.cs && tr.cs.airline;
    const title = al ? al.name : (I.ownOp ? titleCase(I.ownOp) : (I.flight ? 'Callsign ' + I.flight : 'Unidentified'));
    const r = tr.route && tr.route.codes && tr.route.plausible ? tr.route : null;
    const ap = (code) => { if (!r) return null; const a = r.airports.find(x => x.iata === code || x.icao === code); return a ? `${code} <span class="dim">${esc(a.city || a.name)}</span>` : esc(code); };
    const sfo = extra.sfo || null; const sf = sfo && sfo.flight;
    const routeHtml = r ? r.codes.map(ap).join(' <span class="arrow">→</span> ') + (tr.route.src ? '' : '')
      : sf && sf.other && sf.other.iata ? (sf.kind === 'A' ? `${esc(sf.other.iata)} <span class="dim">${esc(sf.other.city || '')}</span> <span class="arrow">→</span> SFO` : `SFO <span class="arrow">→</span> ${esc(sf.other.iata)} <span class="dim">${esc(sf.other.city || '')}</span>`) + ' <span class="dim">· per SFO</span>'
      : '<span class="dim">Route not available</span>';
    const altFt = D.ground || tr.stale ? null : I.altBaro;
    const vs = I.vsFpm;
    const age = tr.lastFixT ? Math.max(0, (now - tr.lastFixT) / 1000) : null;
    const prov = { lol: 'adsb.lol', fi: 'adsb.fi' }[I.posSrc] || null; const mlat = I.src && /mlat/.test(I.src);
    const m = extra.modelNote || '';
    const rw = runwayText(tr);
    const roles = extra.atc || [];
    C.className = 'c-' + cat;
    C.innerHTML = `
<div class="ch"><div class="al">${esc(title)}</div><button data-act="close" class="x" aria-label="Close">×</button></div>
<div class="fl"><b>${esc(tr.cs && tr.cs.display || I.reg || tr.hex.toUpperCase())}</b>${I.flight && tr.cs && tr.cs.display !== I.flight ? `<span class="mono dim">${esc(I.flight)}</span>` : ''}${sf && sf.fn && !(sfo.cands || []).some(c => c.linked && c.fn === sf.fn) && sf.fn.replace(/\s+/g, '') !== String(tr.cs && tr.cs.display || '').replace(/\s+/g, '') ? `<span class="mono dim" title="Flight number SFO lists for this callsign">${esc(sf.fn)}</span>` : ''}</div>
<div class="ty">${esc(tr.type ? tr.type.full : 'Type not reported')}${I.icao ? ` <span class="mono dim">${esc(I.icao)}</span>` : ''}</div>
<div class="ph c-${cat}">${esc(phaseLabel(tr, now))}</div>
<dl>
  <dt>Tail</dt><dd class="mono">${esc(I.reg || '—')}</dd>
  <dt>Route</dt><dd>${routeHtml}</dd>
  ${rw ? `<dt>Runway</dt><dd>${rw}</dd>` : ''}
  ${gateRows(tr, sfo)}
  ${verifyLinks(tr, sfo)}
  <dt>Altitude</dt><dd class="mono">${altFt == null ? (D.ground || tr.stale ? 'On ground' : '—') : fmtInt(altFt) + ' ft'}</dd>
  <dt>Speed</dt><dd class="mono">${tr.stale ? '—' : fmtInt((I.gsKt ?? D.gs / 0.514444)) + ' kt'}</dd>
  ${vs != null && !D.ground && !tr.stale ? `<dt>Vertical</dt><dd class="mono">${vs > 0 ? '+' : ''}${fmtInt(vs)} ft/min</dd>` : ''}
  ${I.squawk ? `<dt>Squawk</dt><dd class="mono">${esc(I.squawk)}${I.emergency && I.emergency !== 'none' ? ' <span class="emg">' + esc(I.emergency) + '</span>' : ''}</dd>` : ''}
  ${I.ownOp && al ? `<dt>Operator</dt><dd>${esc(titleCase(I.ownOp))}</dd>` : ''}
  ${roles.length ? `<dt>ATC</dt><dd><span class="atcchip">${roles.map(roleChip).map(esc).join(' → ')}</span> <span class="dim">likely</span></dd>` : ''}
  <dt>Data</dt><dd>${tr.stale ? 'last received ' + ago(now - tr.lastRecv) : age == null ? '—' : `position <b class="mono">${age < 10 ? age.toFixed(1) : Math.round(age)} s</b> old`}${prov && !tr.stale ? ` <span class="dim">· ${prov}${mlat ? ' (MLAT)' : ''}</span>` : ''}<span class="dim"> · hex ${esc(tr.hex)}</span></dd>
</dl>
${m ? `<div class="model">${esc(m)}</div>` : ''}
<div class="acts"><button data-act="follow" class="${extra.follow === 'follow' ? 'on' : ''}">Follow</button><button data-act="chase" class="${extra.follow === 'chase' ? 'on' : ''}">Chase</button><button data-act="free">Free camera</button></div>`;
  }

  // ------------------------------------------------------------ 3D labels
  updateLabels(items, W, H) { // items: [{hex, x, y, depth, cat, text, sub, sel, dist}]
    const L = this.labels, seen = new Set();
    if (!this.showLabels) { for (const [, e] of L) e.style.display = 'none'; return; }
    items.sort((a, b) => (b.sel - a.sel) || (!!b.atc - !!a.atc) || (a.depth - b.depth));
    const boxes = []; let shown = 0;
    for (const it of items) {
      let e = L.get(it.hex);
      if (!e) { e = document.createElement('div'); e.dataset.hex = it.hex; e.innerHTML = '<b></b><span></span><em></em>'; this.el.labels.appendChild(e); L.set(it.hex, e); }
      seen.add(it.hex);
      const w = it.sub ? 104 : 64, h = it.sub ? 34 : 20;
      const box = [it.x - w / 2, it.y - h - 16, it.x + w / 2, it.y - 16];
      const clash = !it.sel && !it.atc && (shown > 60 || boxes.some(b => b[0] < box[2] && box[0] < b[2] && b[1] < box[3] && box[1] < b[3]));
      if (clash || it.x < -60 || it.y < -60 || it.x > W + 60 || it.y > H + 60) { e.style.display = 'none'; continue; }
      boxes.push(box); shown++;
      const cls = 'lbl c-' + it.cat + (it.sel ? ' sel' : '') + (it.stale ? ' stale' : '') + (it.sub ? '' : ' mini') + (it.atc ? ' atc' : '');
      if (e.className !== cls) e.className = cls;
      if (e._t !== it.text) { e.firstChild.textContent = it.text; e._t = it.text; }
      const sub = it.sub || ''; if (e._s !== sub) { e.children[1].textContent = sub; e._s = sub; }
      const chip = it.atc || ''; if (e._c !== chip) { e.lastChild.textContent = chip; e._c = chip; }
      e.style.display = '';
      e.style.transform = `translate3d(${it.x.toFixed(1)}px, ${it.y.toFixed(1)}px, 0)`;
    }
    for (const [hex, e] of L) if (!seen.has(hex)) { if (e._gone) { e.remove(); L.delete(hex); } else { e.style.display = 'none'; e._gone = true; } } else e._gone = false;
  }
}
export function routeText(tr) {
  const r = tr.route; if (!r || !r.codes || !r.plausible) return tr.gate ? '' : '';
  const c = r.codes; const i = c.indexOf('SFO');
  const city = (code) => { const a = r.airports.find(x => x.iata === code || x.icao === code); return a ? (a.city || a.name || code) : code; };
  if (tr.dirSFO === 'arr' || (i === c.length - 1 && i > 0)) { const o = c[Math.max(0, (i > 0 ? i : c.length) - 1)]; return `from ${o} ${city(o)}`; }
  if (tr.dirSFO === 'dep' || i === 0) { const d = c[Math.min(c.length - 1, (i >= 0 ? i : 0) + 1)]; return `to ${d} ${city(d)}`; }
  return c.join(' → ');
}
// runway: landed / departed / lined up / on final (from the engine's own detection, traffic.js)
function runwayText(tr) {
  const ph = tr.phase;
  if (ph === 'final' && tr.finalInfo) return `<b class="mono">${esc(tr.finalInfo.R.name)}</b> <span class="dim">on final</span>`;
  if (ph === 'goaround') return `<b class="mono">${esc(tr.m.rwy || '')}</b> <span class="dim">go-around</span>`;
  if ((ph === 'lineup' || ph === 'takeoff') && tr.m.rwy) return `<b class="mono">${esc(tr.m.rwy)}</b> <span class="dim">${ph === 'takeoff' ? 'take-off roll' : 'lined up'}</span>`;
  if (tr.depRunway && (ph === 'departure' || tr.dirSFO === 'dep')) return `<b class="mono">${esc(tr.depRunway)}</b> <span class="dim">departed${tr.liftoffAt ? ' ' + clock(tr.liftoffAt) : ''}</span>`;
  if (tr.arrRunway && tr.landedAt) return `<b class="mono">${esc(tr.arrRunway)}</b> <span class="dim">landed ${clock(tr.landedAt)}</span>`;
  return '';
}
const clock = (t) => new Date(t).toLocaleTimeString('en-US', { timeZone: 'America/Los_Angeles', hour: 'numeric', minute: '2-digit' });
// gate / stand: what the aircraft's own position says vs what SFO's flight status says (gate_truth.md s.6)
//   match  -> "Gate B12 · per SFO ✓ (arrival stand)"
//   differ -> "Stand B12 · from position" + "SFO says B14 (arrival 10:05–11:20)"
//   plan only (not parked at a known stand) -> "SFO: B14 (departure)"
// SFO lists a stand per turn window and a passenger gate per flight; a turn with a tow has two stands, so the observed
// stand agrees when it is any stand (or gate) SFO lists for this callsign's arrival or departure near now.
const KIND = { arr: 'arrival', dep: 'departure', both: 'arrival/departure' };
function sfoCandText(c) { const n = c.stand || c.gate; const g = c.stand && c.gate && c.gate !== c.stand && !c.stand.startsWith(c.gate) ? ` (gate ${esc(c.gate)})` : '';
  return `<b class="mono">${esc(n)}</b>${g} <span class="dim">${KIND[c.kind]}${c.linked && c.fn ? ' ' + esc(c.fn) : ''}${c.from && c.to ? ' ' + clock(c.from) + '–' + clock(c.to) : ''}</span>`; }
function gateRows(tr, sfo) {
  const g = tr.gate; const kind = g && g.bridge ? 'Gate' : 'Stand';
  // a turn's arrival and departure usually carry the same stand window: show it once ("arrival/departure")
  const all = []; for (const c of (sfo && sfo.cands) || []) { const d = all.find(q => q.stand === c.stand && q.gate === c.gate && q.from === c.from && q.to === c.to); if (d) { if (d.kind !== c.kind) d.kind = 'both'; } else all.push({ ...c }); }
  const near = all.filter(c => c.now || c.from == null);
  const cands = near.length ? near : all;
  if (g) {
    const names = new Set([...(g.names || []), g.name, g.gateName].filter(Boolean).map(x => String(x).toUpperCase()));
    const hit = cands.find(c => (c.stand && names.has(c.stand)) || (!c.stand && c.gate && names.has(c.gate))) || (tr.gateSrc === 'sfo' ? { kind: null } : null);
    if (hit) return `<dt>${kind}</dt><dd><b class="mono">${esc(gateLabel(g))}</b> · per SFO <span class="ok" title="SFO's flight status lists this stand for this flight">✓</span>${hit.kind ? ` <span class="dim">(${KIND[hit.kind]}${hit.linked && hit.fn ? ' ' + esc(hit.fn) : ''}${hit.stand ? ' stand' : ' gate'})</span>` : ''}</dd>`;
    return `<dt>${kind}</dt><dd><b class="mono">${esc(gateLabel(g))}</b> <span class="dim">· from position</span>${cands.length ? `<br><span class="warn">SFO says</span> ${cands.map(sfoCandText).join(' · ')}` : ''}</dd>`;
  }
  if (cands.length && tr.disp && tr.disp.ground) return `<dt>SFO</dt><dd>${cands.map(sfoCandText).join(' · ')} <span class="dim">· not parked at a known stand yet</span></dd>`;
  if (cands.length) return `<dt>SFO</dt><dd>${cands.map(sfoCandText).join(' · ')}</dd>`;
  return '';
}
// one-click manual checks for the owner (gate_truth.md s.6.3): SFO's own flight-status search (the page reads
// ?type=arrivals|departures&search=... -- observed in its code, not tested in a browser) and FlightAware (human use).
// The flight number SFO lists (marketing number for regional callsigns) is used when the relay provides the plan.
function verifyLinks(tr, sfo) {
  const cs = tr.info.flight && tr.info.flight.trim(); if (!cs) return '';
  const f = sfo && sfo.flight;
  const m = /^([A-Z]{3})0*(\d+)[A-Z]?$/.exec(cs); const num = f && f.fn ? (/(\d+)\s*$/.exec(f.fn) || [])[1] : m ? m[2] : null;
  const type = f ? (f.kind === 'D' ? 'departures' : 'arrivals') : tr.dirSFO === 'dep' ? 'departures' : 'arrivals';
  const a = [];
  if (num) a.push(`<a href="https://www.flysfo.com/flight-info/flight-status?type=${type}&search=${encodeURIComponent(num)}" target="_blank" rel="noopener">flysfo.com ↗</a>`);
  a.push(`<a href="https://www.flightaware.com/live/flight/${encodeURIComponent(cs)}" target="_blank" rel="noopener">FlightAware ↗</a>`);
  return `<dt>Check</dt><dd>${a.join(' · ')}</dd>`;
}
function titleCase(s) { return String(s).toLowerCase().replace(/\b([a-z])/g, (m, c) => c.toUpperCase()).replace(/\b(Inc|Llc|Co)\b\.?/gi, x => x); }
function ago(ms) { const m = Math.round(ms / 60000); return m < 1 ? 'just now' : m < 60 ? m + ' min ago' : Math.floor(m / 60) + ' h ' + (m % 60) + ' min ago'; }
export { CAT_NAME };
