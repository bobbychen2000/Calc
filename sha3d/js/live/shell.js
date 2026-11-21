// SHA Live 3D UI shell (new, P2e: relay / modes / UI shell / About). Registered as the extension 'shell' (order 90: its
// start() runs after the markings / gates / terminals packages, so it can merge what they put into the legend and the
// About panel). It owns:
//   - the status pill and the clock line by mode (app.hooks.status): Live (relay) / Snapshot / Static / Relay offline;
//     the weather text from the raw METAR in the report's units (js/env/wx/metar_zsss.js: m/s, metres, hPa);
//   - the inferred runway mode (tail-wind rule, fallback "into the wind", Settings switch): window.SHA.runwayMode(),
//     SHA.setRunwayRule(rule), window event 'sha:runway' {detail: mode} on every change - for the Phase 3 traffic engine;
//   - relay polls the core does not do: the TAF (every 15 min) and the observed ADS-B list (only when the relay runs with
//     --adsb; the relay itself asks adsb.lol at most once per 180 s): window.SHA.observed;
//   - stand labels (projected every 100 ms, nearest first, overlaps hidden), the stand card, stands in the list search;
//   - the Observed / Inferred legend (default lines + whatever other packages added), the About panel's closing notice.
import { registerExtension } from './ext.js';
import { RELAY, fetchTaf, fetchAdsb } from './relay.js';
import { modeLine } from './about.js';
import { decode as decodeZsss, runwayMode, windText, RULES } from '../env/wx/metar_zsss.js';
import { TZ } from '../env/clock.js';

const DEG = Math.PI / 180;
const store = { get(k, d) { try { const v = localStorage.getItem('shalive.' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } }, set(k, v) { try { localStorage.setItem('shalive.' + k, JSON.stringify(v)); } catch (e) { } } };
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const hhmmZ = (ms) => new Date(ms).toISOString().slice(11, 16).replace(':', '') + 'Z';
const localFmt = (ms, opts) => new Date(ms).toLocaleString('en-GB', { timeZone: TZ, ...opts });
const S = { stands: [], byName: new Map(), sel: null, tLab: 0, rwy: null, rule: 'tailwind', observed: null, app: null };

/** Stand records for the UI from data/sha_stands.js (all positions are OSM stop nodes: observed). */
function standRecords(data) {
  const D = data && data.stands; if (!D || !D.stands) return [];
  const remote = new Map((D.remote || []).map(r => [r.name, r]));
  return D.stands.map(s => {
    const br = s.bridges || [];
    const P = s.push || null;
    return { name: String(s.name), alias: s.alias || [], area: s.area || '', nose: s.nose, hdg: Math.round(s.hdg), hdgSrc: 'obs',
      cls: s.cls, clsSrc: s.cls_src === 'obs' ? 'obs' : 'inf', spanMax: s.span_max, contact: !!s.contact,
      bridges: br.length, bridgesObs: br.filter(b => b.src === 'obs').length, osmNode: s.osm && s.osm.node ? String(s.osm.node) : null,
      service: !s.contact && remote.get(String(s.name)) ? remote.get(String(s.name)).service : null,
      push: P ? `${Math.round(P.push_dist_m || 0)} m back along the lead-in line, then onto the apron lane` : null,
      note: `Class ${s.cls_src === 'obs' ? 'from Sentinel-2 parked-aircraft evidence (observed)' : 'by rule from the stand geometry and neighbours (inferred)'}; ` +
        `the stop node is taken as the nose position (inferred). Bridges: ${br.length ? br.filter(b => b.src === 'obs').length + ' seen on Umbra SAR, ' + br.filter(b => b.src !== 'obs').length + ' from OSM gate nodes only' : 'none (remote stand: bus service inferred)'}.` };
  });
}

function legendLines(app) {
  const names = new Set(app.extensions().map(e => e.name));
  const L = [];
  L.push(['airfield', '<b>Airfield:</b> outlines from OpenStreetMap <span class="srcchip obs">obs</span>; widths, shoulders, which surfaces are concrete, slab joints <span class="srcchip inf">inf</span> (unless the AIP (mirror) gives them).']);
  L.push(['stands', '<b>Stand labels:</b> number and stop from OpenStreetMap <span class="srcchip obs">obs</span>; the class letter is green when Sentinel-2 showed a wide-body there <span class="srcchip obs">obs</span>, amber when set by rule <span class="srcchip inf">inf</span>. Dashed: remote stand.']);
  if (names.has('markings')) L.push(['markings', '<b>Markings and signs:</b> CAAC MH 5001-2021 dimensions; presence and placement inferred from the map <span class="srcchip inf">inf</span> (ZSSS paint not surveyed).']);
  if (names.has('terminals')) L.push(['buildings', '<b>Buildings:</b> outlines from OpenStreetMap <span class="srcchip obs">obs</span>; heights, forms, facades, the tower form <span class="srcchip inf">inf</span>.']);
  else L.push(['buildings', '<b>Buildings:</b> outlines from OpenStreetMap <span class="srcchip obs">obs</span>; heights <span class="srcchip inf">inf</span>.']);
  L.push(['weather', '<b>Weather:</b> the ZSSS METAR <span class="srcchip obs">obs</span> (live via the relay, or recorded in a snapshot); the runway direction in use <span class="srcchip inf">inf</span>.']);
  L.push(['traffic', '<b>Traffic:</b> none yet. Simulated aircraft will be <span class="srcchip inf">inf</span>; ADS-B positions <span class="srcchip obs">obs</span>.']);
  return L;
}

function setupLegend(app) {
  const ui = app.ui;
  // keyed lines other packages added before us (P2f: gates' 'gates' line), kept and placed after the stand-label line;
  // raw html another package may have put into the body without addLegendLine is kept as one 'packages' line
  const keep = [...ui.legendLines.entries()];
  const prev = keep.length ? '' : (ui.el.legend.innerHTML || '').replace(/^\s*<b>Observed \/ inferred<\/b>(<br>)?/, '').trim();
  ui.setLegend('');
  for (const [k, h] of legendLines(app)) { ui.addLegendLine(k, h); if (k === 'stands') for (const [k2, h2] of keep) ui.addLegendLine(k2, h2); }
  if (prev) ui.addLegendLine('packages', prev);
  const q = new URLSearchParams(location.search).get('legend');
  ui.openLegend(q === '1' ? true : q === '0' ? false : !!store.get('legend', false));
  document.getElementById('lg-h').addEventListener('click', () => store.set('legend', !ui.el.legend.hidden));
}

function rwyText(m) {
  if (!m) return '';
  const r = m.report;
  const arr = m.arr.length ? 'arr ' + m.arr.join(' ') : 'no arrivals', dep = m.dep.length ? 'dep ' + m.dep.join(' ') : 'no departures';
  return `Runway in use (inferred): ${m.flow} flow · ${arr} · ${dep}` + (r ? ` · ${m.rule === 'intowind' ? 'into-the-wind rule' : 'tail-wind rule'}` : ' · no METAR: default direction');
}

function noteUpdate(app) {
  const t = [S.wxLine, S.rwyLine].filter(Boolean).join('\n');
  app.ui.setNote(t);
}
function computeRunway(app, force) {
  const E = app.envCore; const st = E.state; if (!st) return;
  const m = runwayMode(E.reports || [], { rule: S.rule, tMs: st.tEnv });
  const key = m.dir + m.arr.join() + m.dep.join() + (m.report ? m.report.raw : '') + S.rule;
  if (!force && S.rwy && S.rwyKey === key) return;
  const changed = !S.rwy || S.rwy.dir !== m.dir;
  S.rwy = m; S.rwyKey = key;
  S.rwyLine = rwyText(m); noteUpdate(app);
  if (changed || force) { try { window.dispatchEvent(new CustomEvent('sha:runway', { detail: m })); } catch (e) { } }
}

function status(app, now) {
  const ui = app.ui, cfg = app.cfg || {}, mi = cfg.modeInfo || {}, st = app.envCore.state;
  const M = app.envCore.summary();
  const tShown = cfg.mode === 'snapshot' && st ? st.tEnv : now;
  if (cfg.mode === 'live' && cfg.relay) {
    const age = M && st && st.wx && st.wx.ageMin != null ? Math.round(st.wx.ageMin) : null;
    const obs = S.observed && S.observed.enabled ? ` · ${S.observed.ac.length} observed` : '';
    ui.setStatus({ state: 'live', text: 'Live weather', sub: (M ? 'METAR ' + M.raw.split(' ').find(t => /^\d{6}Z$/.test(t))?.slice(2) : 'no METAR yet') + obs,
      title: `Live through the local relay: ZSSS METAR / TAF${age != null ? ' (latest report ' + age + ' min old)' : ''}; ${S.observed && S.observed.enabled ? 'observed ADS-B on (adsb.lol, at most one request per 180 s)' : 'observed ADS-B off'}. No simulated traffic yet (Phase 3).` });
  } else if (cfg.mode === 'snapshot') {
    const t = cfg.snapshot ? cfg.snapshot.now : now;
    const sub = localFmt(t, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
    if (mi.relayWanted) ui.setStatus({ state: 'err', text: 'Relay offline', sub: 'snapshot ' + sub, title: 'The relay was requested (?relay=1) but did not answer' + (mi.relayError ? ' (' + mi.relayError + ')' : '') + ': showing the recorded snapshot instead.' });
    else ui.setStatus({ state: 'snap', text: 'Snapshot · ' + localFmt(t, { day: 'numeric', month: 'short' }), sub: localFmt(t, { hour: '2-digit', minute: '2-digit' }) + ' CST', title: 'Snapshot: recorded ZSSS weather at ' + (cfg.snapshot ? cfg.snapshot.nowUtc : '') + ' (no network). No traffic: open ADS-B does not cover Hongqiao; simulated traffic comes in Phase 3.' });
  } else {
    ui.setStatus({ state: 'wait', text: 'Static scene', sub: 'no relay', title: 'No relay: no live weather (clear default) and no traffic. Start sha_live_server.py for live ZSSS weather.' });
  }
  // clock line: local time (CST) + weather in the report's own units
  let wx = '';
  if (M && M.raw) {
    const d = decodeZsss(M.raw);
    const vis = d.cavok ? 'CAVOK' : d.vis_m != null ? (d.vis_ge ? '≥10 km' : d.vis_m >= 5000 ? (d.vis_m / 1000).toFixed(0) + ' km' : d.vis_m + ' m') : '';
    const sky = d.cavok ? '' : (d.sky || []).filter(s => s.base_ft != null).map(s => s.cover + String(s.base_ft / 100).padStart(3, '0')).join(' ');
    wx = [windText(d.wind), vis, sky, d.qnh_hpa ? 'Q' + d.qnh_hpa : ''].filter(Boolean).join(' · ');
    const tt = d.day != null ? String(d.hour).padStart(2, '0') + String(d.minute).padStart(2, '0') + 'Z' : '';
    const tr = (d.trend || []).map(g => g.kind).join(' ');
    S.wxLine = `${d.type || 'METAR'} ${tt} (observed): ${wx}${d.temp_c != null ? ' · ' + d.temp_c + '/' + d.dew_c + ' °C' : ''}${tr ? ' · trend ' + tr + ' not applied' : ''}`;
  } else S.wxLine = st && st.wx && st.wx.forecast ? 'Weather: TAF forecast (no current METAR)' : 'Weather: no report (clear default sky)';
  noteUpdate(app);
  ui.setClock(new Date(tShown), wx + app.envCore.clockNote());
  if (st && (!S.tRwy || now - S.tRwy > 30000 || S.rwyEnvT !== st.tEnv)) { S.tRwy = now; S.rwyEnvT = st.tEnv; computeRunway(app, false); }
}

// ------------------------------------------------------------------------------------------------ stand labels
function standLabels(app) {
  const R = app.R, C = R.curCam; if (!C || !C.vpNear) return;
  const canvas = R.canvas || document.getElementById('gl'); const W = canvas.clientWidth, H = canvas.clientHeight;
  const vp = C.vpNear, cp = C.pos, G = app.geo.GROUND_Y;
  const maxD = app.rig.mode === 'fp' ? 1800 : Math.max(500, Math.min(2600, 250 + 1.35 * (app.rig.dist || 0))); const items = [];
  if (!(app.rig.mode === 'fp' || (app.rig.dist || 1e9) < 3200)) { app.ui.updateStandLabels([], W, H); return; }
  for (const s of S.stands) {
    const x = s.nose[0] - cp[0], y = G + 3 - cp[1], z = s.nose[1] - cp[2];
    const dist = Math.hypot(x, y, z); if (dist > maxD && s.name !== S.sel) continue;
    const cw = vp[3] * x + vp[7] * y + vp[11] * z + vp[15]; if (cw < 0.5) continue;
    const sx = (vp[0] * x + vp[4] * y + vp[8] * z + vp[12]) / cw, sy = (vp[1] * x + vp[5] * y + vp[9] * z + vp[13]) / cw;
    items.push({ name: s.name, x: (sx * 0.5 + 0.5) * W, y: (0.5 - sy * 0.5) * H, depth: dist, cls: s.cls, clsSrc: s.clsSrc, contact: s.contact, sel: s.name === S.sel ? 1 : 0 });
  }
  app.ui.updateStandLabels(items, W, H);
}
function flyToStand(app, s) {
  const h = app.geo.hdgVec(s.hdg); const G = app.geo.GROUND_Y;
  const tgt = [s.nose[0] - h[0] * 18, G, s.nose[1] - h[1] * 18]; const lf = [h[1], -h[0]];
  const off = [h[0] * 0.75 + lf[0] * 0.66, h[1] * 0.75 + lf[1] * 0.66];
  app.rig.stopFollow(); app.rig.leaveTower();
  app.rig.flyTo({ target: tgt, dist: s.cls === 'E' || s.cls === 'EL' || s.cls === 'F' ? 120 : 90, yaw: Math.atan2(off[0], -off[1]), pitch: 24 * DEG, fov: 50 * DEG });
  app.ui.root.querySelectorAll('#views [data-view]').forEach(b => b.classList.remove('on'));
}
function selectStand(app, name, fromLabel = false, fly = false) {
  const s = S.byName.get(String(name)); if (!s) { app.ui.renderStandCard(null); S.sel = null; return false; }
  S.sel = s.name; app.ui.renderStandCard(s);
  if (fly || !fromLabel) { flyToStand(app, s); if (matchMedia('(max-width: 760px)').matches) app.ui.el.card.classList.add('compact'); }   // phone: keep the stand in view
  if (app.ui.sheet === 'open' && matchMedia('(max-width: 760px)').matches) app.ui.setSheet('peek');
  return true;
}

registerExtension({
  name: 'shell', order: 90,
  async start(app) {
    S.app = app; const ui = app.ui, cfg = app.cfg || {};
    S.rule = RULES[store.get('rwyrule', 'tailwind')] ? store.get('rwyrule', 'tailwind') : 'tailwind';
    const sel = ui.root.querySelector('[data-set="rwyrule"]'); if (sel) sel.value = S.rule;
    // stands: labels, card, search
    S.stands = standRecords(app.data); S.byName = new Map(S.stands.map(s => [s.name, s]));
    ui.setStands(S.stands);
    ui.onStand = (name, fromLabel, fly) => selectStand(app, name, fromLabel, fly);
    ui.emptyText = cfg.mode === 'snapshot' ? 'No traffic in this snapshot. Open ADS-B does not cover Hongqiao; simulated traffic (labelled inferred) comes in Phase 3. Search a stand number to find it.'
      : 'No traffic yet. Open ADS-B does not cover Hongqiao; simulated traffic (labelled inferred) comes in Phase 3. Search a stand number to find it.';
    ui.renderList(true, []);
    // settings: runway rule
    ui.onExtraSetting = (k, v) => { if (k === 'rwyrule' && RULES[v]) { S.rule = v; store.set('rwyrule', v); computeRunway(app, true); } };
    // legend and About (the closing notice after the other packages' sections; the mode line refreshed)
    setupLegend(app);
    const ab = ui.el.about; const tail = ab.querySelector('.about-tail'); if (tail) ab.appendChild(tail);
    const ml = ab.querySelector('#about-mode'); if (ml && cfg.modeInfo) ml.innerHTML = modeLine(cfg.modeInfo);
    ui.el.attrib.addEventListener('click', e => { if (e.target.closest('[data-about]')) { e.preventDefault(); ui.toggle(ui.el.about); } });
    // status / clock / runway
    app.hooks.status = (now) => status(app, now);
    computeRunway(app, true); status(app, Date.now());
    // relay polls beyond the core's METAR poll
    if (cfg.relay) {
      const f = (cfg.relayInfo && cfg.relayInfo.features) || {};
      if (f.taf) { const taf = async () => { const t = await fetchTaf(); if (t && t.rawTAF) { app.envCore.setTaf(t.rawTAF); app.applyEnv(Date.now(), true); } }; taf(); setInterval(taf, RELAY.tafPollMs); }
      if (f.adsb) {
        const ob = async () => { const j = await fetchAdsb(); if (j) { S.observed = { enabled: !!j.enabled, ac: (j.ac || []).filter(a => a.src === 'obs'), fetched: j.fetched_utc, excluded: j.excluded || {}, next: j.next_request_in_s }; app.observed = S.observed; } };
        ob(); setInterval(ob, RELAY.adsbPollMs);
      }
    }
    // API for the traffic phase and QA
    app.runwayMode = () => S.rwy; window.SHA.runwayMode = app.runwayMode;
    app.setRunwayRule = (r) => { if (!RULES[r]) return false; S.rule = r; store.set('rwyrule', r); if (sel) sel.value = r; computeRunway(app, true); return true; };
    Object.assign(app.qa, {
      selectStand: (n, fly = true) => selectStand(app, n, !fly, fly),
      closeCard: () => { S.sel = null; ui.renderStandCard(null); return true; },
      openAbout: (on = true) => { for (const p of ui.pops) p.hidden = true; ui.el.about.hidden = !on; return true; },
      openSettings: (on = true) => { for (const p of ui.pops) p.hidden = true; ui.el.settings.hidden = !on; return true; },
      openLegend: (on = true) => { ui.openLegend(on); return true; },
      sheet: (s) => { ui.setSheet(s); return true; },
      search: (q) => { ui.el.search.value = q; ui.el.search.dispatchEvent(new Event('input')); return true; },
      standLabels: () => [...ui.standLabels.values()].filter(e => e.style.display !== 'none').map(e => e.dataset.stand),
      runway: () => S.rwy, mode: () => ({ mode: cfg.mode, relay: !!cfg.relay, features: cfg.relayInfo && cfg.relayInfo.features || null, snapshot: cfg.snapshot ? cfg.snapshot.nowUtc : null }),
    });
  },
  frame(t, app) {
    const now = performance.now(); if (now - S.tLab > 100) { S.tLab = now; try { standLabels(app); } catch (e) { } }
    return [];
  },
});
