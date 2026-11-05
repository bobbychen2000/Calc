// App-side environment adapter (docs/research/environment_spec.md §3, §9.1 item 1, §11): owns the data clock, the
// METAR/SPECI/TAF reports and the current EnvState for js/live/app.js, which feeds BOTH renderers (the WebGL2
// js/renderer.js and, under live3.html, the three.js r186 js/three/renderer3.js) from it. Also the QA overlays:
// ?qa=env (EnvState HUD with tags, the METAR in use, its age and the open-question defaults) and ?qa=prov (airfield
// fixtures tinted by provenance: pub/obs green, std blue, inf orange, NV red, spec §11.4).
// Inputs by mode: snapshot / artifact = SNAPSHOT_METAR (3 reports, selected by data clock); live / replay = the relay's
// /api/metar?format=json list (polled every 60 s) and /api/taf; ?wx=<preset> / ?metar=<raw> / ?t= / ?rwy= overrides.
import { DataClock, parseEnvQuery } from './clock.js';
import { buildEnvState, envHudLines, OPEN_QUESTION_DEFAULTS } from './state.js';
import { metarSummary, splitReports } from './wx/metar.js';
import { presetById, presetRunway } from './presets.js';

export class AppEnv {
  /** opts: {mode: 'live'|'snapshot', relayInfo, snapshotNow, snapshotMetar (text), search (location.search), groundY} */
  constructor(opts = {}) {
    this.q = parseEnvQuery(opts.search || '');
    this.qa = this.q.qa;
    this.preset = this.q.wx ? presetById(this.q.wx) : null;
    const replay = opts.relayInfo && opts.relayInfo.features && opts.relayInfo.features.replay;
    const override = { t: this.q.t != null ? this.q.t : this.preset ? Date.parse(this.preset.time_utc) : null };
    this.clock = new DataClock({ mode: opts.mode, replay: replay || null, snapshotNow: opts.snapshotNow, override });
    if (opts.relayInfo && opts.relayInfo.dataNow) this.clock.setDataNow(opts.relayInfo.dataNow, Date.now());
    this.groundY = opts.groundY ?? 3;
    this.forced = !!(this.preset || this.q.metar);              // a fixed report: always the current one
    this.reports = this.q.metar ? [this.q.metar] : this.preset ? [this.preset.metar] : splitReports(opts.snapshotMetar);
    this.rwyOverride = this.q.rwy || (this.preset ? presetRunway(this.preset) : null);
    this.taf = null; this.state = null; this.hudEl = null; this.provCounts = null;
  }
  setTraffic(traffic) { this.clock.traffic = traffic; }
  setDataNow(ms, wall = Date.now()) { if (ms != null) this.clock.setDataNow(ms, wall); }
  setLightMode(m) { this.clock.setLightMode(m); }
  /** Relay JSON list [{obsTime, receiptTime, rawOb}] (ignored while a preset / ?metar= pins the report). */
  setReports(list) { if (!this.forced && Array.isArray(list) && list.length) this.reports = list; }
  setTaf(t) { if (t) this.taf = t.rawTAF || t; }
  /** EnvState at wall time `wall` (observedFlow: js/live/stats.js runwayConfig of the traffic events). */
  update(wall = Date.now(), observedFlow = null) {
    const c = this.clock.now(wall);
    this.state = buildEnvState(c.tEnv, { mode: c.mode, overridden: c.overridden || !!this.preset, reports: this.reports, taf: this.taf,
      live: this.forced || (c.mode === 'live' && !c.overridden), observedFlow, rwyOverride: this.rwyOverride, groundY: this.groundY, prev: this.state });
    this.state.tTraffic = c.tTraffic; this.state.lightMode = c.lightMode;
    if (this.hudEl) this.renderHud();
    return this.state;
  }
  /** Compact view of the current report for the UI and traffic QNH ({windDir, windKt, visSM, clouds, altim, ...}). */
  summary() { return this.state && this.state.wx.decoded ? metarSummary(this.state.wx.decoded) : null; }
  /** "environment time ≠ traffic time" note for the UI clock (spec §3.2). */
  clockNote() {
    const s = this.state; if (!s || !s.overridden) return '';
    const t = new Date(s.tEnv).toISOString().slice(0, 16).replace('T', ' ') + 'Z';
    return ` · env ${t}${this.preset ? ' (' + this.preset.id + ')' : s.lightMode && s.lightMode !== 'real' ? ' (' + s.lightMode + ')' : ''} ≠ traffic`;
  }
  // ------------------------------------------------------------------------------------------------ QA overlays
  attachHud(root) {
    if (!this.qa.has('env') || typeof document === 'undefined') return;
    const el = document.createElement('pre'); el.id = 'qa-env';
    el.style.cssText = 'position:absolute;left:8px;top:8px;z-index:50;max-width:min(96vw,980px);margin:0;padding:6px 8px;background:rgba(0,0,0,.62);color:#e8f0ff;font:11px/1.35 "IBM Plex Mono",monospace;white-space:pre-wrap;pointer-events:none;border-radius:4px';
    root.appendChild(el); this.hudEl = el; if (this.state) this.renderHud();
  }
  renderHud() {
    const L = envHudLines(this.state);
    if (this.provCounts) L.push(`?qa=prov fixtures: pub/obs ${this.provCounts.pub} green · std ${this.provCounts.std} blue · inf ${this.provCounts.inf} orange · NV ${this.provCounts.NV} red · photometry NV ${this.provCounts.photometryNV}`);
    L.push('open-question defaults [I]: ' + OPEN_QUESTION_DEFAULTS.join(' | '));
    this.hudEl.textContent = L.join('\n');
  }
  /** ?qa=prov: fixture records -> sprite records tinted by provenance (omnidirectional, fixed intensity, day and night). */
  provSprites(records, tint, counts) {
    this.provCounts = counts || null;
    return records.map(r => ({ p: r.p, c: tint[r.provClass], i: 30, s: 0.35 }));
  }
}
