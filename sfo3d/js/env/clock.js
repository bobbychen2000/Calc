// The environment's data clock (docs/research/environment_spec.md §3.2): what "now" means for the Sun, the Moon and
// the weather. Pure ES module, no DOM (the URL is passed in), runs in Node (tools/env/test_env_state.mjs) and the browser.
//
// | mode     | t_env                                                                  | source                          |
// |----------|------------------------------------------------------------------------|---------------------------------|
// | live     | traffic.displayTime(wall): wall − display delay − ATC-audio delay       | js/live/traffic.js displayTime  |
// | replay   | the recording's clock: relay dataNow (ms, /api/ping and every payload)  | sfo_live_server.py Hub.data_now |
// |          | + (displayTime(wall) − wall at dataNow) × replay speed                  |                                 |
// | snapshot | cfg.snapshot.now (23 Sep 2026 17:51:25Z, data/snapshot.js)             | data/snapshot.js                |
// | override | ?t=<ISO-8601 UTC> or ?wx=<preset id>: environment only, traffic keeps  | §3.2 / §11.1 (I); the UI shows  |
// |          | its own time (a fixed instant, I: deterministic QA renders)             | "environment time ≠ traffic"    |
// Light-mode menu (Real / Dawn / Day / Dusk / Night): instants on the same LOCAL date from ephemeris sunEvents(),
// Dawn = midpoint of civil dawn and sunrise, Day = solar transit, Dusk = civil dusk − 10 min, Night = nautical dusk
// + 60 min (§3.2, I; replaces the hard-coded UTC−7 presets of js/live/app.js, 1 h off in PST and seasonally wrong).
// Local date and UTC offset from Intl.DateTimeFormat timeZone 'America/Los_Angeles' (DST-correct), never a constant.
import { sunEvents } from './ephemeris.js';

export const TZ = 'America/Los_Angeles';   // SFO local time (FAA Chart Supplement: UTC−8 (−7DT))

/** UTC offset (hours) of America/Los_Angeles at instant ms, from Intl (DST-correct). */
export function utcOffsetHours(ms, tz = TZ) {
  const f = new Intl.DateTimeFormat('en-US', { timeZone: tz, hourCycle: 'h23', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const p = Object.fromEntries(f.formatToParts(new Date(ms)).filter(x => x.type !== 'literal').map(x => [x.type, +x.value]));
  const asUtc = Date.UTC(p.year, p.month - 1, p.day, p.hour % 24, p.minute, p.second);
  return Math.round((asUtc - Math.floor(ms / 1000) * 1000) / 60000) / 60;
}
/** Local calendar date {y, m, d, offsetH} at instant ms. */
export function localDate(ms, tz = TZ) {
  const off = utcOffsetHours(ms, tz); const L = new Date(ms + off * 3600e3);
  return { y: L.getUTCFullYear(), m: L.getUTCMonth() + 1, d: L.getUTCDate(), offsetH: off };
}
/** Light-mode instant (ms) on the local date of `ms`; mode 'real' returns ms. Returns {t, events, mode}. */
export function lightModeTime(mode, ms) {
  if (!mode || mode === 'real') return { t: ms, mode: 'real', events: null };
  const L = localDate(ms);
  const E = sunEvents(L.y, L.m, L.d, L.offsetH);
  const at = {
    dawn: E.civilDawn && E.sunrise ? (E.civilDawn.getTime() + E.sunrise.getTime()) / 2 : null,
    day: E.transit ? E.transit.getTime() : null,
    dusk: E.civilDusk ? E.civilDusk.getTime() - 10 * 60e3 : null,
    night: E.nauticalDusk ? E.nauticalDusk.getTime() + 60 * 60e3 : null,
  }[mode];
  return { t: at != null ? Math.round(at) : ms, mode: at != null ? mode : 'real', events: E };
}

/** Parse the QA / time-machine query (§11.1): ?t= ?wx= ?metar= ?rwy=arr:28L,28R;dep:1L,1R ?qa=env,prov. */
export function parseEnvQuery(search) {
  const q = new URLSearchParams(search || '');
  const out = { t: null, wx: q.get('wx') || null, metar: q.get('metar') || null, rwy: null, qa: new Set((q.get('qa') || '').split(',').filter(Boolean)) };
  const t = q.get('t');
  if (t) { const ms = Date.parse(/Z$|[+-]\d\d:?\d\d$/.test(t) ? t : t + 'Z'); if (Number.isFinite(ms)) out.t = ms; }
  const r = q.get('rwy');
  if (r) {
    const arr = {}, dep = [];
    for (const part of r.split(';')) {
      const [k, v] = part.split(':'); if (!v) continue;
      for (const e of v.split(',').map(s => s.trim().toUpperCase()).filter(Boolean)) { if (k === 'arr') arr[e] = 'override'; else if (k === 'dep') dep.push(e); }
    }
    out.rwy = { arr, dep, source: 'override (?rwy=)' };
  }
  return out;
}

export class DataClock {
  /** opts: {mode: 'live'|'snapshot', relay, snapshotNow, traffic, override {t}, presetT} */
  constructor(opts = {}) {
    this.mode = opts.mode === 'snapshot' ? 'snapshot' : (opts.replay ? 'replay' : 'live');
    this.snapshotNow = opts.snapshotNow ?? null;
    this.traffic = opts.traffic || null;
    this.overrideT = opts.override && opts.override.t != null ? opts.override.t : (opts.presetT ?? null);
    this.replaySpeed = (opts.replay && opts.replay.speed) || 1;
    this.anchor = null;                 // replay: {dataNow, wall}
    this.lightMode = 'real';
  }
  /** Replay: a relay dataNow sample (ms) received at wall time `wall` (ms). */
  setDataNow(dataNow, wall = Date.now()) { if (Number.isFinite(dataNow)) this.anchor = { dataNow, wall }; }
  setLightMode(m) { this.lightMode = m || 'real'; }
  /** Traffic time on screen (ms). */
  trafficTime(wall = Date.now()) {
    if (this.mode === 'snapshot') return this.snapshotNow;
    const disp = this.traffic && this.traffic.displayTime ? this.traffic.displayTime(wall) : wall;
    if (this.mode === 'replay' && this.anchor) return this.anchor.dataNow + (disp - this.anchor.wall) * this.replaySpeed;
    return disp;
  }
  /** {tEnv, tTraffic, mode, overridden, lightMode} */
  now(wall = Date.now()) {
    const tTraffic = this.trafficTime(wall);
    let tEnv = this.overrideT != null ? this.overrideT : tTraffic, mode = this.mode, overridden = this.overrideT != null;
    if (this.lightMode && this.lightMode !== 'real') { const L = lightModeTime(this.lightMode, tEnv); if (L.mode !== 'real') { tEnv = L.t; overridden = true; } }
    return { tEnv, tTraffic, mode, overridden, lightMode: this.lightMode };
  }
}
