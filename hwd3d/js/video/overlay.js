// Caption overlay and end card of the OD3 videos (hwd3d Phase 3, video). DOM drawn over the app's canvas and captured with
// the frame (page.screenshot in tools/video/render.mjs); the app's own UI is hidden by CSS (body.qa + #loading).
// What it shows (D1: type only - no registration, callsign, operator or address, ever; the models' registration panels are
// blank): the type name (the ICAO type designator's family name only: the data carries no model / variant field), the
// airport and runway, the phase line (js/video/provenance.js captionTrack), the scene's local time (PST/PDT from the data
// clock), the provenance of the CURRENT motion (js/video/provenance.js classes obs / inf / rec / nos), the time-lapse factor,
// the METAR in force at the scene time; and an end card with the notices of docs/ATTRIBUTION.md word for word
// (js/live/about.js NOTICES, tags stripped) plus the weather, imagery and model credits.
// The DATE: the METAR's day-time group (ddhhmmZ) and the end card's month name it, the clock gives the time of day to the
// second. Option timeOnly (job `timeOnly: true`) drops both, leaving the time of day only; endDate adds the full date to
// the end card. Which one a published video uses is the owner's decision (docs/phase3_video.md section 9).
import { NOTICES } from '../live/about.js';

const D1_BAD = [/\bx[0-9a-f]{8}\b/, /\b(?=[0-9a-f]*[a-f])[0-9a-f]{6}\b/, /\bN[1-9][0-9]{0,4}[A-HJ-NP-Z]{0,2}\b/];
// the ICAO type designator's name (ICAO Doc 8643): the pack's records carry the designator (`t`) only, no model or variant
export const TYPE_NAMES = { SF50: 'Cirrus SF50 Vision Jet', PC12: 'Pilatus PC-12' };
// what the drawn model is, and what the data does not say (owner rule: no unverified key assumption)
export const MODEL_NOTES = {
  PC12: 'The aircraft is drawn as a PC-12 PRO (NGX airframe), the model of this repository; the ADS-B data gives only the ICAO type designator PC12, which covers every PC-12 variant (PC-12/45, /47, /47E, NGX, PRO), so this aircraft\'s variant is not known.',
  SF50: 'The aircraft is drawn with the SF50 model of this repository; the ADS-B data gives only the ICAO type designator SF50, so this aircraft\'s production generation is not known.',
};
const plain = (h) => String(h).replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
// credits added to the ATTRIBUTION notices (each with its source): weather (aviationweather.gov, US Government work; the
// pack's METARs, tools/live/build_replay.py), the ground imagery (word for word the line of the app's About panel,
// js/live/about.js, which carries the undated-overview caveat of docs/ATTRIBUTION.md), the two own models
// (js/aircraft/models/SOURCES.json "own work (this repository); no third-party geometry or texture")
export const EXTRA_CREDITS = [
  'Weather: KHWD METAR from the NOAA / NWS Aviation Weather Center (aviationweather.gov), a U.S. Government work',
  'Ground imagery: USDA NAIP 2024 (USDA Farm Production and Conservation Business Center, Geospatial Enterprise Operations), public domain. The 24 km backdrop beyond the airport is the USDA NAIP image-service mosaic, which includes undated overview imagery.',
  'Aircraft models: Cirrus SF50 Vision Jet - procedural model from published dimensions; Pilatus PC-12 PRO (NGX airframe) - parametric model (pc12/). Both own work of this repository, neutral livery, no logos and no registration.',
];

const CSS = `
#vov { position: fixed; inset: 0; z-index: 50; pointer-events: none; font-family: Inter, 'DejaVu Sans', sans-serif; color: #fff;
  -webkit-font-smoothing: antialiased; }
#vov .vv-scrim-top { position: absolute; left: 0; right: 0; top: 0; height: 250px; background: linear-gradient(180deg, rgba(4,8,14,.58) 0%, rgba(4,8,14,.30) 50%, rgba(4,8,14,0) 100%); }
#vov .vv-scrim-bot { position: absolute; left: 0; right: 0; bottom: 0; height: 170px; background: linear-gradient(0deg, rgba(4,8,14,.62) 0%, rgba(4,8,14,.25) 55%, rgba(4,8,14,0) 100%); }
#vov .vv-cap { position: absolute; left: 64px; top: 52px; text-shadow: 0 1px 3px rgba(0,0,0,.55); }
#vov .vv-type { font-size: 50px; font-weight: 650; letter-spacing: -0.01em; line-height: 1.08; }
#vov .vv-where { font-size: 27px; font-weight: 450; opacity: .92; margin-top: 8px; }
#vov .vv-what { font-size: 27px; font-weight: 500; margin-top: 14px; display: flex; gap: 18px; align-items: baseline; }
#vov .vv-what .vv-ph { color: #ffe9b0; }
#vov .vv-what .vv-tm { opacity: .9; font-weight: 450; font-variant-numeric: tabular-nums; }   /* tnum only here: Inter's tnum also widens the hyphen ('ADS - B') */
#vov .vv-spd { position: absolute; right: 64px; top: 48px; text-align: right; text-shadow: 0 1px 3px rgba(0,0,0,.55); transition: none; }
#vov .vv-spd .vv-k { font-size: 64px; font-weight: 700; line-height: 1; }
#vov .vv-spd .vv-l { font-size: 21px; opacity: .85; margin-top: 4px; letter-spacing: .04em; text-transform: uppercase; }
#vov .vv-src { position: absolute; left: 64px; bottom: 58px; display: flex; align-items: center; gap: 14px; padding: 10px 20px 10px 16px; border-radius: 28px;
  background: rgba(8,12,18,.62); border: 1px solid rgba(255,255,255,.16); font-size: 24px; font-weight: 520; }
#vov .vv-src .vv-dot { width: 16px; height: 16px; border-radius: 50%; flex: none; }
#vov .vv-src.vv-obs .vv-dot { background: #49d17d; box-shadow: 0 0 0 4px rgba(73,209,125,.22); }
#vov .vv-src.vv-inf .vv-dot { background: #ffb02e; box-shadow: 0 0 0 4px rgba(255,176,46,.24); }
#vov .vv-src.vv-rec .vv-dot { background: #ff7a45; box-shadow: 0 0 0 4px rgba(255,122,69,.26); }
#vov .vv-src.vv-nos .vv-dot { background: #9fb3c8; box-shadow: 0 0 0 4px rgba(159,179,200,.24); }
#vov .vv-src .vv-sub { font-size: 19px; font-weight: 420; opacity: .8; }
#vov .vv-wx { position: absolute; right: 64px; bottom: 62px; font-family: 'JetBrains Mono', 'DejaVu Sans Mono', monospace; font-size: 19px; opacity: .9; text-align: right; text-shadow: 0 1px 2px rgba(0,0,0,.6); }
#vov .vv-credit { position: absolute; right: 64px; bottom: 30px; font-size: 15px; opacity: .72; text-align: right; text-shadow: 0 1px 2px rgba(0,0,0,.6); }
#vov .vv-end { position: absolute; inset: 0; background: #0a0e13; opacity: 0; display: flex; flex-direction: column; justify-content: center; padding: 0 150px; }
#vov .vv-end h1 { font-size: 46px; font-weight: 650; margin: 0 0 10px; letter-spacing: -0.01em; }
#vov .vv-end .vv-sub { font-size: 25px; opacity: .88; margin-bottom: 26px; line-height: 1.35; }
#vov .vv-end .vv-note { font-size: 20px; opacity: .78; margin-bottom: 28px; line-height: 1.4; max-width: 1500px; }
#vov .vv-end h2 { font-size: 21px; font-weight: 600; text-transform: uppercase; letter-spacing: .08em; opacity: .7; margin: 0 0 12px; }
#vov .vv-end ul { margin: 0; padding: 0; list-style: none; font-size: 17px; line-height: 1.42; opacity: .9; max-width: 1620px; }
#vov .vv-end li { margin: 0 0 9px; padding-left: 18px; position: relative; }
#vov .vv-end li::before { content: ''; position: absolute; left: 0; top: .62em; width: 6px; height: 6px; border-radius: 50%; background: #6c8aa8; }
#vov .vv-fade { position: absolute; inset: 0; background: #000; opacity: 0; }
body.qa #loading, #loading { display: none !important; }
`;

export class Overlay {
  /** opts: { type, event: 'takeoff'|'landing', runway, tz, endDate (show the date on the end card), timeOnly (the time of day
   *  only: no METAR day-time group, no month on the end card) } */
  constructor(opts = {}) {
    this.o = { runway: '28L', tz: 'America/Los_Angeles', ...opts };
    const st = document.createElement('style'); st.id = 'vov-css'; st.textContent = CSS; document.head.appendChild(st);
    const el = this.el = document.createElement('div'); el.id = 'vov';
    const name = TYPE_NAMES[this.o.type] || this.o.type || 'Aircraft';
    const ev = this.o.event === 'landing' ? 'Landing' : 'Take-off';
    el.innerHTML = `<div class="vv-scrim-top"></div><div class="vv-scrim-bot"></div>
<div class="vv-cap"><div class="vv-type">${esc(name)}</div><div class="vv-where">Hayward Executive (KHWD) · runway ${esc(this.o.runway)}</div>
<div class="vv-what"><span class="vv-ph"></span><span class="vv-tm"></span></div></div>
<div class="vv-spd"><div class="vv-k"></div><div class="vv-l">time-lapse</div></div>
<div class="vv-src"><span class="vv-dot"></span><span class="vv-t"></span><span class="vv-sub"></span></div>
<div class="vv-wx"></div><div class="vv-credit">Recorded ADS-B: adsb.lol (ODbL) · Map data © OpenStreetMap contributors (ODbL) · USDA NAIP · FAA NASR</div>
<div class="vv-end"><h1>${esc(name)} · ${ev}, runway ${esc(this.o.runway)}</h1>
<div class="vv-sub">Hayward Executive Airport (KHWD), Hayward, California · <span class="vv-day"></span></div>
<div class="vv-note">A real recorded flight: positions, altitudes and speeds are the aircraft's own ADS-B reports as recorded by adsb.lol, shown by aircraft type only (no registration, callsign or operator). The recorder saw about 14 s of each minute; the Hayward Live 3D traffic engine interpolates between the reports, stretches marked <i>reconstructed</i> have no report at all, and <i>no ADS-B signal</i> marks a silence of the transponder itself. ${esc(MODEL_NOTES[this.o.type] || '')} Rendered with the Hayward Live 3D WebGL2 renderer.</div>
<h2>Credits</h2><ul>${[...NOTICES.map(plain), ...EXTRA_CREDITS].map(t => `<li>${esc(t)}</li>`).join('')}</ul></div>
<div class="vv-fade"></div>`;
    document.body.appendChild(el);
    this.q = (s) => el.querySelector(s);
    this.last = {};
  }
  set(sel, prop, v) { if (this.last[sel + prop] === v) return; this.last[sel + prop] = v; const e = this.q(sel); if (prop === 'text') e.textContent = v; else if (prop === 'cls') e.className = v; else e.style[prop] = v; }
  /** s: { phase, tData (ms), src: 'obs'|'inf'|'rec'|'nos', srcText, srcSub, speed (label or null), metar (raw line or ''), end (0..1), fade (0..1), caption (0..1) } */
  update(s) {
    const tz = this.o.tz, d = new Date(s.tData);
    const tm = d.toLocaleTimeString('en-US', { timeZone: tz, hour: 'numeric', minute: '2-digit', second: '2-digit', timeZoneName: 'short' });
    this.set('.vv-what .vv-ph', 'text', s.phase || '');
    this.set('.vv-what .vv-tm', 'text', tm);
    this.set('.vv-spd', 'opacity', s.speed ? '1' : '0'); this.set('.vv-spd .vv-k', 'text', s.speed || '');
    this.set('.vv-src', 'cls', 'vv-src vv-' + (s.src || 'obs')); this.set('.vv-src .vv-t', 'text', s.srcText || ''); this.set('.vv-src .vv-sub', 'text', s.srcSub || '');
    this.set('.vv-wx', 'text', metarLine(s.metar || '', { timeOnly: this.o.timeOnly }));
    // the date: by default the end card names the month and the METAR its day-time group; endDate adds the full date,
    // timeOnly leaves the time of day only (a date + time + type at one airport can be enough to look the flight up in
    // public ADS-B history: docs/phase3_video.md section 9, an owner decision)
    const month = d.toLocaleDateString('en-US', { timeZone: tz, month: 'long', year: 'numeric' });
    this.set('.vv-end .vv-day', 'text', this.o.endDate && !this.o.timeOnly ? d.toLocaleDateString('en-US', { timeZone: tz, weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }) + ', ' + tm : this.o.timeOnly ? 'recorded ADS-B' : 'recorded ADS-B, ' + month);
    const cap = s.caption == null ? 1 : s.caption;
    for (const k of ['.vv-cap', '.vv-spd', '.vv-src', '.vv-wx', '.vv-credit', '.vv-scrim-top', '.vv-scrim-bot']) if (k !== '.vv-spd') this.set(k, 'opacity', String(cap));
    this.set('.vv-end', 'opacity', String(s.end || 0));
    this.set('.vv-fade', 'opacity', String(s.fade || 0));
    // D1 guard: nothing on screen may look like a track key ('x' + 8 hex in a type-only pack, a 6-hex ICAO address) or a
    // US registration (N-number); the overlay is built from the type name and the app's phase label only, so this never
    // fires unless a label source changes - then the frame is refused rather than captured
    const txt = this.el.textContent;
    if (D1_BAD.some(re => re.test(txt))) throw new Error('overlay: identity-like text on screen (D1)');
  }
  remove() { this.el.remove(); const c = document.getElementById('vov-css'); if (c) c.remove(); }
}
/** "METAR KHWD ddhhmmZ dddffKT ... Annnn RMK ..." -> the line without the remarks (RMK and after); timeOnly: also without
 *  the day-time group (ddhhmmZ names the day of the month) */
export const metarLine = (raw, { timeOnly = false } = {}) => {
  if (!raw) return '';
  let s = String(raw).replace(/\s+RMK\b.*$/, '').trim();
  if (timeOnly) s = s.replace(/\s\d{6}Z(?=\s)/, '');
  return s;
};
