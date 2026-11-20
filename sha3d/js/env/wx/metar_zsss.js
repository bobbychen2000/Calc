// ZSSS METAR / SPECI decoder that keeps the report units, plus the inferred runway-direction rule (new; the JS twin of
// tools/wx/metar_zsss.py, docs/phase1/sources_sim.md s.3.3 and s.5.2). Pure ES module, no DOM: runs in Node and the browser.
// tools/wx/test_metar_zsss_js.mjs checks it against the Python reference (every decoded field and the rule's direction
// on every report of the archives), so keep the two line-by-line equal.
//
// Why a second decoder next to js/env/wx/metar.js (which the renderer's EnvState uses and which also cuts the trend):
// - ZSSS reports wind in MPS, visibility in metres and QNH in hPa (Q group). metar.js converts the wind to knots rounded
//   to 0.1 (1 MPS -> 1.9 kt -> 0.977 m/s back), which shifts the runway rule's thresholds (1.5 / 4.0 m/s); this decoder
//   keeps speed_ms, vis_m and qnh_hpa as reported.
// - The trend (NOSIG / BECMG / TEMPO, in every ZSSS report) is decoded APART from the observation: decode().trend; it is
//   never applied to the current sky (sfo3d's decoder did: '... BKN006 18/17 Q1017 BECMG TL0340 BKN011' gave two
//   observed layers).
// - It decodes the RAW TEXT. The AWC JSON fields are not used: wspd is knots rounded from MPS, visib is statute miles
//   with "6+" for 9999, wdir "VRB" (sources_sim.md s.3.3); the relay (sha_live_server.py) strips them.
// Wind direction in METAR is degrees TRUE (ICAO Annex 3); the runway headings below are TRUE too.
import { pyRound } from './metar.js';

export const KT_MS = 1852.0 / 3600.0;
// Runway true headings (OSM way bearings / AIP AD 2.12 (mirror)): 18L/36R 177.34 deg, 18R/36L 177.33 deg; both runways
// always run the same way (close parallels 365 m apart), so the rule decides one direction for both.
export const RWY_TRUE = { '18': 177.34, '36': 357.34 };
const WX_RE = /^(\+|-|VC)?(MI|PR|BC|DR|BL|SH|TS|FZ)?((?:DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PO|SQ|FC|SS|DS)*)$/;
const TREND_START = ['NOSIG', 'BECMG', 'TEMPO'];
const D2R = Math.PI / 180;

function wind(tok) {
  const m = tok.match(/^(\d{3}|VRB|\/\/\/)(\d{2,3}|\/\/)(?:G(\d{2,3}))?(MPS|KT)$/);
  if (!m) return null;
  const toMs = m[4] === 'MPS' ? 1.0 : KT_MS;
  const spd = m[2] === '//' ? null : parseInt(m[2], 10) * toMs;
  const w = { raw: tok, unit: m[4], dir_true_deg: (m[1] === 'VRB' || m[1] === '///') ? null : parseInt(m[1], 10),
    variable: m[1] === 'VRB', speed_ms: spd, gust_ms: m[3] ? parseInt(m[3], 10) * toMs : null };
  w.calm = spd === 0.0;
  w.speed_kt = spd == null ? null : pyRound(spd / KT_MS, 1);
  return w;
}
function sky(tok) {
  let m = tok.match(/^(FEW|SCT|BKN|OVC)(\d{3}|\/\/\/)(CB|TCU|\/\/\/)?$/);
  if (m) return { cover: m[1], base_ft: m[2] === '///' ? null : parseInt(m[2], 10) * 100, type: (m[3] != null && m[3] !== '///') ? m[3] : null };
  m = tok.match(/^VV(\d{3}|\/\/\/)$/);
  if (m) return { cover: 'VV', base_ft: m[1] === '///' ? null : parseInt(m[1], 10) * 100, type: null };
  if (['NSC', 'NCD', 'SKC', 'CLR'].includes(tok)) return { cover: tok, base_ft: null, type: null };
  return null;
}
function wx(tok) {
  if (tok === 'NSW') return { raw: tok, nsw: true };
  const m = tok.match(WX_RE);
  if (!m || !(m[3] || m[2] === 'TS')) return null;
  const ph = []; for (let k = 0; k < m[3].length; k += 2) ph.push(m[3].slice(k, k + 2));
  return { raw: tok, intensity: { '-': 'light', '+': 'heavy', VC: 'vicinity' }[m[1]] || 'moderate', descriptor: m[2] ?? null, phenomena: ph };
}
/** Wind / visibility / RVR / weather / sky / T/Td / QNH groups (shared by the body and the trend groups). */
function elements(tokens, out) {
  let i = 0;
  const push = (k, v) => { (out[k] ||= []).push(v); };
  while (i < tokens.length) {
    const t = tokens[i];
    const w = wind(t);
    if (w && !('wind' in out)) { out.wind = w; i++; continue; }
    let m = t.match(/^(\d{3})V(\d{3})$/);
    if (m && 'wind' in out) { out.wind.var_from = parseInt(m[1], 10); out.wind.var_to = parseInt(m[2], 10); i++; continue; }
    if (t === 'CAVOK') { out.cavok = true; out.vis_m = 10000; out.vis_ge = true; i++; continue; }
    m = t.match(/^(\d{4})(NDV)?$/);
    if (m && !('vis_m' in out)) { const v = parseInt(m[1], 10); out.vis_m = v; out.vis_ge = v === 9999; if (v === 9999) out.vis_m = 10000; i++; continue; }
    m = t.match(/^(\d{4})(N|NE|E|SE|S|SW|W|NW)$/);
    if (m && 'vis_m' in out) { push('vis_min', { m: parseInt(m[1], 10), dir: m[2] }); i++; continue; }
    m = t.match(/^R(\d{2}[LRC]?)\/([PM]?\d{4})(?:V([PM]?\d{4}))?([UDN])?$/);
    if (m) { push('rvr', { rwy: m[1], m: m[2], var: m[3] ?? null, tend: m[4] ?? null }); i++; continue; }
    m = t.match(/^(M?\d{2})\/(M?\d{2})?$/);
    if (m && !('temp_c' in out)) {
      const c = (s) => s == null ? null : (s.startsWith('M') ? -parseInt(s.slice(1), 10) : parseInt(s, 10));
      out.temp_c = c(m[1]); out.dew_c = c(m[2]); i++; continue;
    }
    m = t.match(/^Q(\d{4})$/);
    if (m) { out.qnh_hpa = parseInt(m[1], 10); i++; continue; }
    m = t.match(/^A(\d{4})$/);
    if (m) { out.qnh_hpa = pyRound(parseInt(m[1], 10) / 100 * 33.8639, 1); out.qnh_from_inhg = true; i++; continue; }
    const s = sky(t);
    if (s) { push('sky', s); i++; continue; }
    const x = wx(t);
    if (x) { push('wx', x); i++; continue; }
    if (t.startsWith('RE')) { push('recent_wx', t.slice(2)); i++; continue; }
    if (t === 'WS' && i + 1 < tokens.length) { push('windshear', tokens.slice(i, i + 3).join(' ')); i += 3; continue; }
    push('unparsed', t); i++;
  }
  return out;
}
/** -> [head+body tokens, trend tokens, rmk text]: the body ends at the first NOSIG / BECMG / TEMPO, or at RMK. */
export function splitReport(raw) {
  let toks = String(raw).replace(/=/g, ' ').split(/\s+/).filter(Boolean);
  let rmk = '';
  const r = toks.indexOf('RMK');
  if (r >= 0) { rmk = toks.slice(r + 1).join(' '); toks = toks.slice(0, r); }
  const k = toks.findIndex(t => TREND_START.includes(t));
  return k >= 0 ? [toks.slice(0, k), toks.slice(k), rmk] : [toks, [], rmk];
}
/** Decode one ZSSS METAR / SPECI from its raw text. Units as reported: speed_ms, gust_ms (and speed_kt), vis_m (9999 ->
 *  10000 with vis_ge), qnh_hpa; trend = [{kind: 'NOSIG'} | {kind: 'BECMG'|'TEMPO', fm?, tl?, at?, elements}]. */
export function decode(raw) {
  const [body, trend, rmk] = splitReport(String(raw).trim());
  const out = { raw: String(raw).trim() };
  let i = 0;
  if (body.length && (body[0] === 'METAR' || body[0] === 'SPECI')) { out.type = body[0]; i = 1; } else out.type = 'METAR';
  if (i < body.length && body[i] === 'COR') { out.cor = true; i++; }
  out.station = body[i] ?? null; i++;
  const m = i < body.length ? body[i].match(/^(\d{2})(\d{2})(\d{2})Z$/) : null;
  if (m) { out.day = parseInt(m[1], 10); out.hour = parseInt(m[2], 10); out.minute = parseInt(m[3], 10); i++; }
  if (i < body.length && (body[i] === 'AUTO' || body[i] === 'NIL')) { out[body[i].toLowerCase()] = true; i++; }
  elements(body.slice(i), out);
  out.trend = decodeTrend(trend);
  if (rmk) out.rmk = rmk;
  return out;
}
/** ICAO Annex 3 trend: NOSIG, or BECMG / TEMPO groups with FMhhmm / TLhhmm / AThhmm and elements. */
export function decodeTrend(tokens) {
  const groups = []; let cur = null;
  for (const t of tokens) {
    if (t === 'NOSIG') { groups.push({ kind: 'NOSIG' }); cur = null; continue; }
    if (t === 'BECMG' || t === 'TEMPO') { cur = { kind: t, elements_raw: [] }; groups.push(cur); continue; }
    if (cur == null) continue;
    const m = t.match(/^(FM|TL|AT)(\d{4})$/);
    if (m) { cur[m[1].toLowerCase()] = m[2]; continue; }
    cur.elements_raw.push(t);
  }
  for (const g of groups) if (g.kind !== 'NOSIG') { g.elements = elements(g.elements_raw, {}); delete g.elements_raw; }
  return groups;
}
/** [headwind (+), crosswind (+ from the right)] in m/s on direction '18' or '36'; null for VRB / missing. */
export function components(w, rwy) {
  if (!w || w.dir_true_deg == null || w.speed_ms == null) return null;
  const a = (w.dir_true_deg - RWY_TRUE[rwy]) * D2R;
  return [w.speed_ms * Math.cos(a), w.speed_ms * Math.sin(a)];
}

/** Inferred runway-direction rule [inf] (tools/wx/metar_zsss.py RunwayDirection; sources_sim.md s.5.2).
 *  AIP (mirror) AD 2.20 2.1.2 tolerates a 3-5 m/s tail wind "for short time" DURING a change of direction; it is not the
 *  trigger. Model: keep the current direction while its tail wind (gusts included) is <= 1.5 m/s; turn round after two
 *  consecutive reports above 1.5 m/s, or one above 4.0 m/s; calm / VRB keeps. Calibrated on the runway designators of
 *  the RVR / wind-shear groups of ZSSS METARs 2023-2026 (169 reports, 60 days): 86.4 % agreement in sample, 78.1 % out
 *  of sample (leave-one-day-out) - not shown to beat the parameter-free fallback below (80.5 %). */
export class RunwayDirection {
  constructor(start = '36') { this.dir = start; this.pending = 0; this.TAIL_KEEP_MS = 1.5; this.TAIL_MAX_MS = 4.0; }
  step(w) {
    const c = components(w, this.dir);
    if (c == null) { this.pending = 0; return [this.dir, 'keep (calm/VRB/missing)']; }
    let head = c[0];
    if (w.gust_ms) head = Math.min(head, w.gust_ms * Math.cos((w.dir_true_deg - RWY_TRUE[this.dir]) * D2R));
    const tail = -head;
    if (tail > this.TAIL_MAX_MS || (tail > this.TAIL_KEEP_MS && this.pending >= 1)) {
      this.dir = this.dir === '36' ? '18' : '36'; this.pending = 0;
      return [this.dir, `change (tailwind ${tail.toFixed(1)} m/s)`];
    }
    if (tail > this.TAIL_KEEP_MS) { this.pending++; return [this.dir, `keep, tailwind ${tail.toFixed(1)} m/s (1st report > ${this.TAIL_KEEP_MS})`]; }
    this.pending = 0; return [this.dir, 'keep'];
  }
}
/** Parameter-free fallback [inf] (metar_zsss.py RunwayDirectionIntoWind): the direction with a head wind; keep the current
 *  one while |headwind| < 0.5 m/s and when calm / VRB / missing; gusts ignored. 80.5 % agreement, nothing fitted. */
export class RunwayDirectionIntoWind {
  constructor(start = '36') { this.dir = start; this.DEAD_MS = 0.5; }
  step(w) {
    const c = components(w, '36');
    if (c == null || Math.abs(c[0]) < this.DEAD_MS) return [this.dir, 'keep'];
    const nw = c[0] > 0 ? '36' : '18';
    if (nw !== this.dir) { this.dir = nw; return [this.dir, `change (headwind on ${nw})`]; }
    return [this.dir, 'keep'];
  }
}

// ------------------------------------------------------------------------------------------- runway mode (for Phase 3)
export const RULES = {
  tailwind: { make: (s) => new RunwayDirection(s), label: 'tail-wind rule (turn after 2 reports > 1.5 m/s or 1 > 4.0 m/s)', agreement: '86.4 % in sample, 78.1 % out of sample' },
  intowind: { make: (s) => new RunwayDirectionIntoWind(s), label: '"into the wind" (parameter-free fallback)', agreement: '80.5 %' },
};
/** AIP (mirror) AD 2.20 2.1.1 segregated mode: "RWY18R/36L mainly used for departure; RWY18L/36R mainly used for arrival".
 *  2.1.6: no landings on 18R/36L 1600-2300 UTC (except alternates). closed: runway ids closed now (e.g. by NOTAM; the
 *  traffic phase applies NOTAMs, sources_sim.md s.4). -> {arr: [...ends], dep: [...ends], notes: [...]} */
export function assignRunways(dir, tMs = Date.now(), closed = []) {
  const east = dir === '36' ? '36R' : '18L', west = dir === '36' ? '36L' : '18R';
  const isClosed = (id) => closed.some(c => String(c).split('/').includes(id));
  const h = new Date(tMs).getUTCHours(), night = h >= 16 && h < 23;
  const notes = ['AIP (mirror) AD 2.20 2.1.1: 18L/36R mainly arrivals, 18R/36L mainly departures'];
  let arr = [east], dep = [west];
  if (isClosed(east) && !isClosed(west)) {
    dep = [west];
    if (night) { arr = []; notes.push('18L/36R closed; AD 2.20 2.1.6: no landings on 18R/36L 1600-2300 UTC (except alternates)'); }
    else { arr = [west]; notes.push('18L/36R closed: single-runway operation on 18R/36L [inf]'); }
  } else if (isClosed(west) && !isClosed(east)) { dep = [east]; notes.push('18R/36L closed: departures from 18L/36R [inf]'); }
  else if (isClosed(east) && isClosed(west)) { arr = []; dep = []; notes.push('both runways closed'); }
  return { arr, dep, notes };
}
/** Step the rule over METAR / SPECI reports in time order (every report, as a live simulator sees them).
 *  reports: raw strings or {rawOb | raw, obsTime (epoch s)}; tMs: only reports observed at or before tMs count
 *  (null = all). Returns the inferred runway mode, tag 'inf':
 *  {dir: '36'|'18', flow: 'north'|'south', arr, dep, rule, reason, report: {raw, obsMs, wind}, history: [...], tag}. */
export function runwayMode(reports, { rule = 'tailwind', start = '36', tMs = null, closed = [] } = {}) {
  const R = (RULES[rule] || RULES.tailwind).make(start);
  const seen = new Set(), list = [];
  for (const r of reports || []) {
    const raw = typeof r === 'string' ? r : (r && (r.rawOb || r.raw)) || '';
    if (!raw || seen.has(raw.trim())) continue; seen.add(raw.trim());
    const obsMs = r && r.obsTime != null ? r.obsTime * 1000 : r && r.obsMs != null ? r.obsMs : null;
    if (tMs != null && obsMs != null && obsMs > tMs) continue;
    list.push({ raw: raw.trim(), obsMs });
  }
  list.sort((a, b) => (a.obsMs ?? 0) - (b.obsMs ?? 0));
  const history = []; let last = null, reason = 'no report: start direction ' + start + ' (no preferred direction is published)';
  for (const it of list) {
    const d = decode(it.raw); const [dir, why] = R.step(d.wind || null);
    last = { raw: it.raw, obsMs: it.obsMs, wind: d.wind || null }; reason = why;
    history.push({ obsMs: it.obsMs, dir, why });
  }
  const dir = R.dir; const A = assignRunways(dir, tMs ?? (last && last.obsMs) ?? Date.now(), closed);
  return { dir, flow: dir === '36' ? 'north' : 'south', arr: A.arr, dep: A.dep, notes: A.notes, rule, ruleLabel: (RULES[rule] || RULES.tailwind).label,
    reason, report: last, history, tag: 'inf' };
}
/** One-line wind text in the report's units ('340° 4 m/s G9', 'VRB 1 m/s', 'calm'). */
export function windText(w) {
  if (!w || w.speed_ms == null) return '';
  if (w.calm) return 'calm';
  const u = w.unit === 'MPS' ? ' m/s' : ' kt', f = w.unit === 'MPS' ? 1 : 1 / KT_MS;
  const d = w.dir_true_deg != null ? String(w.dir_true_deg).padStart(3, '0') + '°' : 'VRB';
  return `${d} ${Math.round(w.speed_ms * f)}${u}${w.gust_ms ? ' G' + Math.round(w.gust_ms * f) : ''}`;
}
