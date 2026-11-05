// METAR / SPECI (and basic TAF) decoder for KSFO plus the METAR -> rendering-parameter mapping: a line-by-line port
// of tools/env/metar_decode.py (decode_metar, decode_taf, render_params, extinction_from_visibility), which is the
// reference. Gate A-WX (docs/research/environment_spec.md §11.3): tools/env/test_metar_js.mjs replays every call the
// 38 Python unit tests make (58 real KSFO reports + FAA coding examples) and the 58 fixtures + 14 presets, recorded by
// tools/env/build_metar_golden.py, and requires deep-equal results. Replaces the old regex METAR parser of js/livedata.js,
// which read `M1/4SM` as 4 SM and ignored fractions, RVR, weather, VV and remarks.
// Pure ES module, no DOM: runs in Node and in the browser. Output objects use the Python keys (snake_case) so the two
// stay diffable; js/env/state.js builds the EnvState from them.
//
// Standards (quoted in docs/research/weather.md §2; paragraph numbers as in the Python reference):
//   [7900] FAA Order JO 7900.5E w/ Chg 1, Surface Weather Observing, ch. 13 (coding): 13.10 wind, 13.11 visibility,
//          13.12 RVR, 13.13 present weather + Table 13-4, 13.14 sky + Tables 13-5/13-6, 13.15-13.16, remarks 13.21-13.58.
//          https://www.faa.gov/documentLibrary/media/Order/JO_7900.5E_with_Change_1.pdf
//   [AIM]  FAA AIM (2026-07-09, Change 3) 7-1-7 flight categories, 7-1-28 METAR/TAF key.
//   [R99]  Rasmussen et al. 1999 (ASOS day Koschmieder eps = 0.055; night simplified Allard I0 = 25 cd,
//          CDB = 0.084 mi^-1), https://opensky.ucar.edu/system/files/2024-08/articles_15245.pdf (NWS spec itself: 2nd).
//   [GN07] Garg & Nayar 2007 (Marshall-Palmer, v = 200 sqrt(a)); [AC27F] FAA AC 150/5345-27F 3.2.2 / 3.5 (windsock).
// Everything marked INFERRED is a modelling choice of the reference (docs/research/weather.md §3), not a sourced fact.

export const SM_M = 1609.344;          // statute mile (exact)
export const FT_M = 0.3048;            // foot (exact)
export const KT_MS = 1852.0 / 3600.0;  // knot (exact)
export const INHG_HPA = 33.8639;       // inch of mercury (0 degC) to hPa

// ---------------------------------------------------------------------------------------------------- helpers
/** Python round(x, n): correctly rounded on the exact binary value, ties to even (JS toFixed rounds ties away). */
export function pyRound(x, n = 0) {
  if (typeof x !== 'number' || !Number.isFinite(x)) return x;
  const ax = Math.abs(x);
  if (ax >= 1e21) return x;
  let s = ax.toFixed(n);
  const full = ax.toFixed(100), dot = full.indexOf('.');
  const rest = full.slice(dot + 1 + n);
  if (/^50*$/.test(rest)) {                                  // exact tie: choose the even neighbour
    const last = +s.replace('.', '').slice(-1);
    if (last % 2 === 1) { const keep = full.slice(0, dot + 1 + n); s = keep.endsWith('.') ? keep.slice(0, -1) : keep; }
  }
  const v = Number(s);
  return x < 0 ? -v : v;
}
const fm = (re, s) => (typeof s === 'string' ? s.match(re) : null);   // regexes below are written ^(?:...)$ (= re.fullmatch)
const pySplit = (s) => s.split(/\s+/).filter(t => t.length > 0);
const g = (m, k) => (m[k] === undefined ? null : m[k]);               // Python: unmatched group -> None
const removeSuffix = (s, suf) => (s.endsWith(suf) ? s.slice(0, s.length - suf.length) : s);
const pyMod = (a, b) => ((a % b) + b) % b;

// ---------------------------------------------------------------------------------------------------- vocabularies
// [7900] Table 13-4 (present weather)
export const DESCRIPTORS = ['MI', 'PR', 'BC', 'DR', 'BL', 'SH', 'TS', 'FZ'];
export const PRECIP = ['DZ', 'RA', 'SN', 'SG', 'IC', 'PL', 'GR', 'GS', 'UP'];
export const OBSCUR = ['BR', 'FG', 'FU', 'VA', 'DU', 'SA', 'HZ', 'PY'];
export const OTHER = ['PO', 'SQ', 'FC', 'SS', 'DS'];
const PHEN = [...PRECIP, ...OBSCUR, ...OTHER];
const WX_RE = new RegExp('^([+-]|VC)?(MI|PR|BC|DR|BL|SH|TS|FZ)?((?:' + PHEN.join('|') + ')*)$');
// [7900] Table 13-5: summation amount in eighths (min, max)
export const COVER_OKTAS = { FEW: [0.5, 2], SCT: [3, 4], BKN: [5, 7], OVC: [8, 8], VV: [8, 8] };
const COMPASS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
const LOCWORDS = new Set([...COMPASS, 'OHD', 'VC', 'VCY', 'DSNT', 'ALQDS', 'AND', 'MOV', 'IN', 'GAP', 'BNK', 'BANK', 'AT', 'AP',
  'OVR', 'THRU', 'UNKN', 'STNRY', 'BAY', 'RWY', 'DSIPTD', 'ONLY', 'MOVE', 'ALDQS', 'DNST']);   // typos observed at KSFO 2016-2026

const isDir = (tok) => tok.split('-').every(p => COMPASS.includes(p));

/** '1/2' -> [0.5, ''], '3' -> [3, ''], 'M1/4' -> [0.25, 'M'], 'P6' -> [6, 'P']. */
function frac(s) {
  let pre = '';
  if ('MP'.includes(s.slice(0, 1)) && s.length > 1 && /[0-9]/.test(s[1])) { pre = s[0]; s = s.slice(1); }
  let v;
  if (s.includes('/')) { const [n, d] = s.split('/'); v = parseInt(n, 10) / parseInt(d, 10); } else v = parseFloat(s);
  return [v, pre];
}
/** Statute-mile visibility at tokens[i] ('1 1/2SM', 'M1/4SM', 'P6SM', '10SM') -> [sm, prefix, n] or null [7900 13.11]. */
function visValue(tokens, i) {
  const t = tokens[i];
  if (fm(/^\d{1,2}$/, t) && i + 1 < tokens.length && fm(/^\d\/\d{1,2}SM$/, tokens[i + 1])) {
    const v2 = frac(tokens[i + 1].slice(0, -2))[0];
    return [parseInt(t, 10) + v2, '', 2];
  }
  const m = fm(/^([MP]?\d{1,2}(?:\/\d{1,2})?)SM$/, t);
  if (m) { const [v, pre] = frac(m[1]); return [v, pre, 1]; }
  return null;
}
/** Remark visibility without the SM suffix ('1 1/2', 'M1/4', '6', '3SM' seen at KSFO). */
function visRemarkValue(tokens, i) {
  if (i >= tokens.length) return null;
  const t = removeSuffix(tokens[i], 'SM');
  if (fm(/^\d{1,2}$/, t) && i + 1 < tokens.length && fm(/^\d\/\d{1,2}(SM)?$/, tokens[i + 1]))
    return [parseInt(t, 10) + frac(removeSuffix(tokens[i + 1], 'SM'))[0], '', 2];
  if (fm(/^[MP]?\d{1,2}(\/\d{1,2})?$/, t)) { const [v, pre] = frac(t); return [v, pre, 1]; }
  return null;
}
const temp = (s) => (s.startsWith('M') ? 0 - parseInt(s.slice(1), 10) : parseInt(s, 10));
/** [7900] 13.52: sign digit 1 = below 0 degC, then tenths. */
const tgroup = (s) => (s[0] === '1' ? -1 : 1) * parseInt(s.slice(1, 4), 10) / 10.0;
/** [7900] 13.40 SLP ('SLP982' = 998.2): the candidate nearest the altimeter QNH, else the usual < 500 -> 10xx rule. */
function slp(ppp, altimHpa) {
  const v = parseInt(ppp, 10) / 10.0;
  const c = [900 + v, 1000 + v];
  if (altimHpa) return Math.abs(c[1] - altimHpa) < Math.abs(c[0] - altimHpa) ? c[1] : c[0];
  return parseInt(ppp, 10) < 500 ? c[1] : c[0];
}

// ------------------------------------------------------------------------------------------------- body elements
/** Present-weather group -> object, or null [7900 13.13, Table 13-4]. */
function parseWx(tok) {
  if (tok === 'NSW') return { raw: tok, nsw: true };
  const m = tok.match(WX_RE);
  const I = m ? g(m, 1) : null, D = m ? g(m, 2) : null, P = m ? m[3] : '';
  if (!m || (!P && D !== 'TS' && !(I === 'VC' && D === 'SH'))) return null;
  if (!I && !D && !P) return null;
  const ph = []; for (let k = 0; k < P.length; k += 2) ph.push(P.slice(k, k + 2));
  const inten = I || '';
  return { raw: tok, intensity: inten === '-' ? 'light' : inten === '+' ? 'heavy' : (inten !== 'VC' ? 'moderate' : null),
    vicinity: inten === 'VC', descriptor: D, phenomena: ph, precip: ph.filter(p => PRECIP.includes(p)),
    obscuration: ph.filter(p => OBSCUR.includes(p)), tornadic: tok === '+FC' };
}
function parseSky(tok) {
  let m = fm(/^(FEW|SCT|BKN|OVC)(\d{3}|\/\/\/)(CB|TCU|\/\/\/)?$/, tok);
  if (m) return { cover: m[1], height_ft: m[2] === '///' ? null : parseInt(m[2], 10) * 100, type: g(m, 3) !== '///' ? g(m, 3) : null };
  m = fm(/^VV(\d{3}|\/\/\/)$/, tok);
  if (m) return { cover: 'VV', height_ft: m[1] === '///' ? null : parseInt(m[1], 10) * 100, type: null };
  if (['CLR', 'SKC', 'NSC', 'NCD'].includes(tok)) return { cover: tok, height_ft: null, type: null };
  return null;
}
function parseBody(tokens, out, taf = false) {
  let i = 0;
  while (i < tokens.length) {
    const t = tokens[i];
    let m = fm(/^(\d{3}|VRB|\/\/\/)(\d{2,3}|\/\/)(?:G(\d{2,3}))?(KT|MPS|KMH)$/, t);
    if (m && !('wind' in out)) {
      const unit = { KT: 1.0, MPS: 1 / KT_MS, KMH: 1 / 1.852 }[m[4]];
      const spd = m[2] === '//' ? null : pyRound(parseInt(m[2], 10) * unit, 1);
      const calm = t.startsWith('00000');
      const d = (m[1] === 'VRB' || m[1] === '///' || calm) ? null : parseInt(m[1], 10);
      out.wind = { dir_true_deg: d, speed_kt: spd, gust_kt: m[3] ? pyRound(parseInt(m[3], 10) * unit, 1) : null,
        variable: m[1] === 'VRB', calm, var_from: null, var_to: null };
      i++; continue;
    }
    m = fm(/^(\d{3})V(\d{3})$/, t);
    if (m && 'wind' in out) { out.wind.var_from = parseInt(m[1], 10); out.wind.var_to = parseInt(m[2], 10); i++; continue; }
    if (t === 'CAVOK') { out.visibility = { sm: 10000 / SM_M, prefix: 'P', m: 10000.0, raw: t }; i++; continue; }
    const v = visValue(tokens, i);
    if (v && !('visibility' in out)) {
      const [val, pre, n] = v;
      out.visibility = { sm: val, prefix: pre || null, m: val * SM_M, raw: tokens.slice(i, i + n).join(' ') };
      i += n; continue;
    }
    if (fm(/^\d{4}$/, t) && !('visibility' in out) && 'wind' in out) {          // ICAO metres (not used in the US)
      out.visibility = { sm: (t === '9999' ? 10000 : parseInt(t, 10)) / SM_M, prefix: t === '9999' ? 'P' : null,
        m: t === '9999' ? 10000.0 : parseFloat(t), raw: t };
      i++; continue;
    }
    m = fm(/^R(\d{2}[LRC]?)\/([MP]?)(\d{4})(?:V([MP]?)(\d{4}))?(FT)?(?:\/?([UDN]))?$/, t);
    if (m) {
      const lo = parseInt(m[3], 10), hi = m[5] ? parseInt(m[5], 10) : null;
      (out.rvr ||= []).push({ runway: m[1], min_ft: lo, min_prefix: m[2] || null, max_ft: hi, max_prefix: hi ? (m[4] || null) : null,
        unit: m[6] ? 'ft' : 'm', tendency: g(m, 7), raw: t });
      i++; continue;
    }
    const w = parseWx(t);
    if (w) { (out.weather ||= []).push(w); i++; continue; }
    const s = parseSky(t);
    if (s) { (out.sky ||= []).push(s); i++; continue; }
    m = fm(/^(M?\d{2})\/(M?\d{2})?$/, t);
    if (m && !taf) { out.temp_c = temp(m[1]); out.dewpoint_c = m[2] ? temp(m[2]) : null; i++; continue; }
    m = fm(/^A(\d{4})$/, t);
    if (m) { out.altimeter_inhg = parseInt(m[1], 10) / 100.0; out.qnh_hpa = pyRound(out.altimeter_inhg * INHG_HPA, 1); i++; continue; }
    m = fm(/^Q(\d{4})$/, t);
    if (m) { out.qnh_hpa = parseFloat(m[1]); i++; continue; }
    m = fm(/^WS(\d{3})\/(\d{3})(\d{2,3})KT$/, t);
    if (m && taf) { out.wind_shear = { height_ft: parseInt(m[1], 10) * 100, dir: parseInt(m[2], 10), speed_kt: parseInt(m[3], 10) }; i++; continue; }
    (out.unparsed ||= []).push(t);
    i++;
  }
}

// ------------------------------------------------------------------------------------------------------ remarks
const AEROSOL_ALOFT = ['FU', 'HZ', 'DU', 'SA', 'VA'];   // = metar_decode.py AEROSOL_ALOFT (truth2-4)
const OBSC_RE = new RegExp('^(MI|PR|BC)?(' + OBSCUR.join('|') + ')$');
const EVT_FULL = /^(?:[A-Z]{2,6}?(?:[BE](?:\d{4}|\d{2}|MM))+)+$/;
const EVT_ITER = /([A-Z]{2,6}?)((?:[BE](?:\d{4}|\d{2}|MM))+)/g;
const EVT_WX = new RegExp('^(SH|FZ)?(' + PRECIP.join('|') + ')+$');
const SIG_RE = new RegExp('^(CB|CBMAM|TCU|ACC|ACSL|SCSL|CCSL|VIRGA|TS|VCTS|FOG|(?:VC|MI|PR|BC)?(?:' + [...OBSCUR, ...PRECIP].join('|') + ')+|VCSH)$');
const SIG_CLOUDS = ['CB', 'CBMAM', 'TCU', 'ACC', 'ACSL', 'SCSL', 'CCSL'];

/** RMK section ([7900] 13.17-13.58); unrecognised free text kept in rmk.plain (e.g. 'FG IN GAP W'). */
function parseRemarks(rt, out) {
  const r = out.rmk;
  const toks = pySplit(rt);
  const altimHpa = out.qnh_hpa;
  const plain = [];
  const n = toks.length;
  const flush = () => { if (plain.length) { (r.plain ||= []).push(plain.join(' ')); plain.length = 0; } };
  const rwyLoc = (k) => {        // 'RWY L10' or 'RWYL10' after a group -> [loc, k]
    if (k < n && toks[k] === 'RWY' && k + 1 < n) return ['RWY ' + toks[k + 1], k + 2];
    if (k < n && fm(/^RWY\w+$/, toks[k])) return [toks[k], k + 1];
    return [null, k];
  };
  let i = 0;
  while (i < n) {
    let t = toks[i];
    let nxt = i + 1 < n ? toks[i + 1] : '';
    let m;
    // automated station type 13.21 ('A02' with a zero occurs 76 times at KSFO 2016-26)
    if (['AO1', 'AO2', 'AO1A', 'AO2A', 'A01', 'A02'].includes(t)) { flush(); r.station_type = t[1] === '0' ? t.replace('0', 'O') : t; i++; continue; }
    // peak wind 13.22: PK WND dddff(f)/(hh)mm
    if (t === 'PK' && nxt === 'WND' && i + 2 < n) {
      m = fm(/^(\d{3})(\d{2,3})\/(\d{2,4})$/, toks[i + 2]);
      if (m) { flush(); r.peak_wind = { dir_true_deg: parseInt(m[1], 10), speed_kt: parseInt(m[2], 10), time: m[3] }; i += 3; continue; }
    }
    // wind shift 13.23
    if (t === 'WSHFT' && fm(/^\d{2,4}$/, nxt)) {
      flush(); const fropa = i + 2 < n && toks[i + 2] === 'FROPA';
      r.wind_shift = { time: nxt, fropa }; i += fropa ? 3 : 2; continue;
    }
    // tower / surface visibility 13.24
    if ((t === 'TWR' || t === 'SFC') && nxt === 'VIS') {
      const v = visRemarkValue(toks, i + 2);
      if (v) { flush(); r[t === 'TWR' ? 'tower_vis_sm' : 'surface_vis_sm'] = v[0]; i += 2 + v[2]; continue; }
    }
    // VIS / CIG LWR <dir>
    if ((t === 'VIS' || t === 'CIG') && nxt === 'LWR' && i + 2 < n && isDir(toks[i + 2])) {
      flush(); (r.lower_toward ||= []).push({ what: t, dir: toks[i + 2] }); i += 3; continue;
    }
    // VIS remarks: variable 13.25, sector 13.26, second location 13.27
    if (t === 'VIS') {
      let whole = 0, k0 = 1;
      if (fm(/^\d$/, nxt) && i + 2 < n && fm(/^\d\/\d{1,2}V.+$/, toks[i + 2])) { whole = parseInt(nxt, 10); k0 = 2; nxt = toks[i + 2]; }
      m = fm(/^([MP]?\d{1,2}(?:\/\d{1,2})?)V([MP]?\d{1,2}(?:\/\d{1,2})?)(SM)?$/, nxt);
      if (m) {
        flush();
        const lo = whole + frac(m[1])[0]; let hi = frac(m[2])[0]; let k = k0 + 1;
        if (!m[2].includes('/') && i + k < n && fm(/^\d\/\d{1,2}$/, toks[i + k])) { hi += frac(toks[i + k])[0]; k++; }
        r.vis_variable_sm = [lo, hi]; i += k; continue;
      }
      let j = i + 1; const dirs = [];
      while (j < n && isDir(toks[j])) { dirs.push(toks[j]); j++; }
      let v = visRemarkValue(toks, j);
      if (dirs.length && v) { flush(); (r.vis_sector ||= []).push({ dirs, sm: v[0], prefix: v[1] || null }); i = j + v[2]; continue; }
      v = visRemarkValue(toks, i + 1);
      if (v) {
        const [loc, k] = rwyLoc(i + 1 + v[2]);
        flush(); (r.vis_other ||= []).push({ sm: v[0], loc }); i = k; continue;
      }
    }
    // variable ceiling 13.34, ceiling at a second location 13.38
    if (t === 'CIG') {
      m = fm(/^(\d{3})V(\d{3})$/, nxt);
      if (m) { flush(); r.cig_variable_ft = [parseInt(m[1], 10) * 100, parseInt(m[2], 10) * 100]; i += 2; continue; }
      if (fm(/^\d{3}$/, nxt)) {
        const [loc, k] = rwyLoc(i + 2);
        flush(); r.cig_second_location = { height_ft: parseInt(nxt, 10) * 100, loc }; i = k; continue;
      }
    }
    // obscuration 13.35 ('FG BKN000', 'FU FEW004')
    if (fm(OBSC_RE, t) && fm(/^(FEW|SCT|BKN|OVC)\d{3}$/, nxt)) {
      flush(); (r.obscuration_layers ||= []).push({ wx: t, cover: nxt.slice(0, 3), height_ft: parseInt(nxt.slice(3), 10) * 100 }); i += 2; continue;
    }
    // variable sky condition 13.36 ('BKN014 V OVC')
    if (fm(/^(FEW|SCT|BKN|OVC)(\d{3})?$/, t) && nxt === 'V' && i + 2 < n && ['FEW', 'SCT', 'BKN', 'OVC'].includes(toks[i + 2])) {
      flush(); (r.sky_variable ||= []).push({ from: t.slice(0, 3), height_ft: t.length > 3 ? parseInt(t.slice(3), 10) * 100 : null, to: toks[i + 2] });
      i += 3; continue;
    }
    // lightning 13.28: [OCNL|FRQ|CONS] LTG[IC][CC][CG][CA] [loc...]
    m = fm(/^LTG((?:IC|CC|CG|CA)*)$/, t);
    if (m || (['OCNL', 'FRQ', 'CONS'].includes(t) && fm(/^LTG(?:IC|CC|CG|CA)*$/, nxt))) {
      flush();
      let freq = null;
      if (!m) { freq = t; i++; t = toks[i]; m = fm(/^LTG((?:IC|CC|CG|CA)*)$/, t); }
      const types = []; for (let k = 0; k < m[1].length; k += 2) types.push(m[1].slice(k, k + 2));
      let j = i + 1; const loc = [];
      while (j < n && (['DSNT', 'VC', 'OHD', 'ALQDS', 'AND'].includes(toks[j]) || isDir(toks[j]))) { loc.push(toks[j]); j++; }
      (r.lightning ||= []).push({ frequency: freq, types, loc: loc.join(' ') || null });
      i = j; continue;
    }
    // begin/end of precipitation 13.29 and thunderstorm 13.30 ('RAB05E30SNB20E55', 'TSB0159E30', 'RAEMMB27')
    if (fm(EVT_FULL, t) && /\d|[BE]MM/.test(t)) {
      const evs = [];
      for (const mm of t.matchAll(EVT_ITER)) for (const e of mm[2].matchAll(/([BE])(\d{4}|\d{2}|MM)/g))
        evs.push({ wx: mm[1], event: e[1] === 'B' ? 'begin' : 'end', time: e[2] });
      if (evs.length && evs.every(e => e.wx === 'TS' || fm(EVT_WX, e.wx))) { flush(); (r.wx_events ||= []).push(...evs); i++; continue; }
    }
    // pressure rising / falling rapidly 13.39
    if (t === 'PRESRR' || t === 'PRESFR') { flush(); r.pressure_rapid = t === 'PRESRR' ? 'rising' : 'falling'; i++; continue; }
    // sea-level pressure 13.40
    m = fm(/^SLP(\d{3})$/, t);
    if (m) { flush(); r.slp_hpa = slp(m[1], altimHpa); i++; continue; }
    if (t === 'SLPNO') { flush(); r.slp_hpa = null; (r.sensor_status ||= []).push('SLPNO'); i++; continue; }
    // hourly precipitation 13.46 (hundredths of an inch since the last METAR)
    m = fm(/^P(\d{4}|\/\/\/\/)$/, t);
    if (m) { flush(); r.precip_hourly_in = m[1].includes('/') ? null : parseInt(m[1], 10) / 100.0; i++; continue; }
    // ice accretion 13.47
    m = fm(/^I([136])(\d{3}|\/\/\/)$/, t);
    if (m) { flush(); r['ice_accretion_' + m[1] + 'h_in'] = m[2].includes('/') ? null : parseInt(m[2], 10) / 100.0; i++; continue; }
    // 3/6-hour precipitation 13.48 (6RRRR), 24-hour 13.49 (7RRRR)
    m = fm(/^([67])(\d{4}|\/\/\/\/)$/, t);
    if (m) { flush(); r[m[1] === '6' ? 'precip_3or6h_in' : 'precip_24h_in'] = m[2].includes('/') ? null : parseInt(m[2], 10) / 100.0; i++; continue; }
    // snow depth 13.50, water equivalent 13.51
    m = fm(/^4\/(\d{3})$/, t);
    if (m) { flush(); r.snow_depth_in = parseInt(m[1], 10); i++; continue; }
    m = fm(/^933(\d{3})$/, t);
    if (m) { flush(); r.snow_water_equiv_in = parseInt(m[1], 10) / 10.0; i++; continue; }
    // hourly temperature / dew point 13.52
    m = fm(/^T([01]\d{3})([01]\d{3})?$/, t);
    if (m) { flush(); r.temp_c_tenths = tgroup(m[1]); r.dewpoint_c_tenths = m[2] ? tgroup(m[2]) : null; i++; continue; }
    // 6-h max/min 13.53/13.54, 24-h max/min 13.55, 3-h pressure tendency 13.56
    m = fm(/^([12])([01]\d{3})$/, t);
    if (m) { flush(); r[m[1] === '1' ? 'max_temp_6h_c' : 'min_temp_6h_c'] = tgroup(m[2]); i++; continue; }
    m = fm(/^4([01]\d{3})([01]\d{3})$/, t);
    if (m) { flush(); r.max_temp_24h_c = tgroup(m[1]); r.min_temp_24h_c = tgroup(m[2]); i++; continue; }
    m = fm(/^5([0-8])(\d{3})$/, t);
    if (m) { flush(); r.pressure_tendency = { character: parseInt(m[1], 10), change_hpa: parseInt(m[2], 10) / 10.0 }; i++; continue; }
    // sensor status 13.57
    if (['PWINO', 'PNO', 'FZRANO', 'TSNO', 'RVRNO'].includes(t)) { flush(); (r.sensor_status ||= []).push(t); i++; continue; }
    if (t === 'VISNO' || t === 'CHINO') {
      flush(); const [loc, k] = rwyLoc(i + 1);
      (r.sensor_status ||= []).push(t + (loc ? ' ' + loc : '')); i = k; continue;
    }
    // breaks in overcast (plain-language contraction, FAA Order JO 7340)
    if (t === 'BINOVC') { flush(); r.breaks_in_overcast = true; i++; continue; }
    // maintenance indicator 13.58
    if (t === '$') { flush(); r.maintenance = true; i++; continue; }
    // hailstone size 13.32
    if (t === 'GR' && nxt && (nxt === 'LESS' || fm(/^\d(\/\d)?$/, nxt))) {
      flush();
      if (nxt === 'LESS') { r.hail_size_in = '<1/4'; i += 4; continue; }          // 'GR LESS THAN 1/4'
      const v = visRemarkValue(toks, i + 1);
      r.hail_size_in = v[0]; i += 1 + v[2]; continue;
    }
    // significant clouds 13.37, thunderstorm location 13.31, virga 13.33, distant / vicinity phenomena
    m = fm(SIG_RE, t);
    if (m) {
      flush(); let j = i + 1; const loc = [];
      while (j < n && (LOCWORDS.has(toks[j]) || isDir(toks[j]))) { loc.push(toks[j]); j++; }
      const entry = { what: t, loc: loc.join(' ') || null };
      (r[SIG_CLOUDS.includes(t) ? 'significant_clouds' : 'phenomena'] ||= []).push(entry);
      if ((t.includes('FG') || t === 'FOG') && loc.some(w => w === 'BNK' || w === 'BANK')) r.fog_bank = entry.loc;   // plain language (weather.md 2.9)
      if ((t.includes('FG') || t === 'FOG') && loc.includes('GAP')) r.fog_in_gap = entry.loc;                          // KSFO 'FG IN GAP W' (weather.md 4.3)
      i = j; continue;
    }
    plain.push(t);
    i++;
  }
  flush();
}

// ------------------------------------------------------------------------------------------------------- METAR
const iso = (d) => d.toISOString().replace('.000Z', 'Z');
/** The latest date not after ref + 1 day for the DDhhmmZ group (Python _resolve_day). */
function resolveDay(ref, d, h, mi) {
  let y = ref.getUTCFullYear(), mo = ref.getUTCMonth() + 1;
  for (let k = 0; k < 3; k++) {
    const ok = d >= 1 && h < 24 && mi < 60 && (() => { const c = new Date(Date.UTC(y, mo - 1, d, h, mi)); return c.getUTCDate() === d && c.getUTCMonth() === mo - 1; })();
    if (ok) { const cand = new Date(Date.UTC(y, mo - 1, d, h, mi)); if ((cand - ref) / 1000 <= 86400) return cand; }
    mo -= 1; if (mo === 0) { y -= 1; mo = 12; }
  }
  return new Date(Date.UTC(ref.getUTCFullYear(), ref.getUTCMonth(), Math.min(d, 28), h, mi));
}

/** Decode one METAR/SPECI line. ref (Date, UTC) resolves the month/year of DDhhmmZ. Returns a JSON-safe object. */
export function decodeMetar(raw, ref = null) {
  const text = pySplit(String(raw).replace(/=/g, ' ')).join(' ');
  const out = { raw: text, type: null, station: null, modifier: [], rmk: {} };
  let body = text, rmk = '';
  const k = text.indexOf(' RMK ');
  if (k >= 0) { body = text.slice(0, k); rmk = text.slice(k + 5); }
  if (text.startsWith('RMK ')) { body = ''; rmk = text.slice(4); }
  const toks = pySplit(body);
  let i = 0;
  if (toks.length && (toks[0] === 'METAR' || toks[0] === 'SPECI')) { out.type = toks[0]; i++; }
  if (i < toks.length && fm(/^[A-Z][A-Z0-9]{3}$/, toks[i])) { out.station = toks[i]; i++; }
  if (i < toks.length && fm(/^\d{6}Z$/, toks[i])) {
    const d = parseInt(toks[i].slice(0, 2), 10), h = parseInt(toks[i].slice(2, 4), 10), mi = parseInt(toks[i].slice(4, 6), 10);
    out.time = { day: d, hour: h, minute: mi };
    if (ref != null) out.time.utc = iso(resolveDay(ref, d, h, mi));
    i++;
  }
  while (i < toks.length && ['AUTO', 'COR', 'RTD', 'NIL'].includes(toks[i])) { out.modifier.push(toks[i]); i++; }
  parseBody(toks.slice(i), out);
  if (rmk) parseRemarks(rmk, out);
  derive(out);
  return out;
}

/** Ceiling, flight category, precise temperatures, relative humidity (exported for js/env/wx/taf.js forecasts). */
export function derive(out) {
  const sky = out.sky || [];
  // [7900] 10.4a: ceiling = lowest BKN/OVC layer or VV into a surface obscuration ('BKN000' is not a ceiling)
  let ceil = null;
  for (const s of sky) {
    if (['BKN', 'OVC', 'VV'].includes(s.cover) && s.height_ft != null) {
      if (s.cover !== 'VV' && s.height_ft === 0) continue;
      ceil = ceil == null ? s.height_ft : Math.min(ceil, s.height_ft);
    }
  }
  out.ceiling_ft = ceil;
  const vis = out.visibility ? out.visibility.sm : null;
  // [AIM] 7-1-7 categories
  let cat = null;
  if (vis != null || ceil != null) {
    const c = ceil != null ? ceil : 1e9, v = vis != null ? vis : 1e9;
    cat = (c < 500 || v < 1) ? 'LIFR' : (c < 1000 || v < 3) ? 'IFR' : (c <= 3000 || v <= 5) ? 'MVFR' : 'VFR';
  }
  out.flight_category = cat;
  const r = out.rmk;
  const t = 'temp_c_tenths' in r ? r.temp_c_tenths : ('temp_c' in out ? out.temp_c : null);
  const td = 'dewpoint_c_tenths' in r ? r.dewpoint_c_tenths : ('dewpoint_c' in out ? out.dewpoint_c : null);
  out.temp_c_best = t; out.dewpoint_c_best = td;
  if (t != null && td != null) {
    // Magnus form, Alduchov & Eskridge (1996) over water: es = 6.1094 exp(17.625 T / (T + 243.04))
    const es = (x) => 6.1094 * Math.exp(17.625 * x / (x + 243.04));
    out.rel_humidity_pct = pyRound(100.0 * es(td) / es(t), 1);
  } else out.rel_humidity_pct = null;
}

// --------------------------------------------------------------------------------------------------------- TAF
/** Split a TAF into base + FM / TEMPO / BECMG / PROBnn groups, each decoded with the METAR body parser [AIM 7-1-28]. */
export function decodeTaf(raw) {
  const text = pySplit(String(raw).replace(/=/g, ' ')).join(' ');
  const toks = pySplit(text);
  let i = 0;
  const out = { raw: text, modifier: [], periods: [] };
  if (toks.length && toks[0] === 'TAF') i++;
  while (i < toks.length && ['AMD', 'COR', 'RTD'].includes(toks[i])) { out.modifier.push(toks[i]); i++; }
  out.station = toks[i]; i++;
  if (fm(/^\d{6}Z$/, toks[i])) { out.issued = toks[i]; i++; }
  if (fm(/^\d{4}\/\d{4}$/, toks[i])) { out.valid = toks[i]; i++; }
  let cur = { change: 'BASE', from: (out.valid || '').split('/')[0] || null, to: null, prob: null, tokens: [] };
  const chunks = [cur];
  while (i < toks.length) {
    const t = toks[i];
    const m = fm(/^FM(\d{6})$/, t);
    if (m) { cur = { change: 'FM', from: m[1], to: null, prob: null, tokens: [] }; chunks.push(cur); i++; continue; }
    if (t === 'TEMPO' || t === 'BECMG' || fm(/^PROB\d{2}$/, t)) {
      const prob = t.startsWith('PROB') ? parseInt(t.slice(4), 10) : null;
      let change = !prob ? t : 'PROB';
      let j = i + 1;
      if (prob && j < toks.length && toks[j] === 'TEMPO') { change = 'PROB TEMPO'; j++; }
      let fr = null, to = null;
      if (j < toks.length && fm(/^\d{4}\/\d{4}$/, toks[j])) { [fr, to] = toks[j].split('/'); j++; }
      cur = { change, from: fr, to, prob, tokens: [] }; chunks.push(cur); i = j; continue;
    }
    cur.tokens.push(t); i++;
  }
  for (const c of chunks) {
    const p = { change: c.change, from: c.from, to: c.to, prob: c.prob };
    const el = { rmk: {} };
    parseBody(c.tokens, el, true);
    delete el.rmk;
    Object.assign(p, el);
    const hs = (el.sky || []).filter(x => ['BKN', 'OVC', 'VV'].includes(x.cover) && x.height_ft).map(x => x.height_ft);
    p.ceiling_ft = hs.length ? Math.min(...hs) : null;
    out.periods.push(p);
  }
  return out;
}

// ----------------------------------------------------------------------------------------- rendering parameters
export const ASOS_DAY_CONTRAST = 0.055;          // [R99]
export const ASOS_NIGHT_I0_CD = 25.0;            // [R99] candles
export const ASOS_NIGHT_CDB_PER_MI = 0.084;      // [R99] mi^-1

/** Invert the ASOS visibility algorithm: reported visibility (m) -> extinction coefficient (1/m). Day: Koschmieder
 *  V = -ln(eps)/sigma, eps = 0.055; night: simplified Allard Vn = (I0/CDB) exp(-sigma Vn), V in miles [R99 eq. 24]. */
export function extinctionFromVisibility(visM, night = false, contrast = ASOS_DAY_CONTRAST) {
  if (visM == null || visM <= 0) return null;
  if (!night) return -Math.log(contrast) / visM;
  const vMi = visM / SM_M;
  const sPerMi = Math.log(ASOS_NIGHT_I0_CD / (ASOS_NIGHT_CDB_PER_MI * vMi)) / vMi;
  return Math.max(sPerMi, 1e-9) / SM_M;
}
/** [7900] 10.7 summation principle -> own fraction per layer (random overlap, INFERRED). */
function layerCoverages(sky) {
  const out = []; let prev = 0.0;
  for (const s of sky) {
    if (!(s.cover in COVER_OKTAS)) continue;
    const [lo, hi] = COVER_OKTAS[s.cover];
    let tot = Math.max(prev, (lo + hi) / 2 / 8.0);
    // INFERRED floor for a second layer of the same class (FEW003 FEW008): halfway from the layers below to the class's
    // upper bound (review truth1-11; = tools/env/metar_decode.py)
    if (tot <= prev && hi / 8.0 > prev) tot = prev + (hi / 8.0 - prev) / 2;
    const own = prev >= 1.0 ? 1.0 : Math.max(0.0, 1.0 - (1.0 - tot) / (1.0 - prev));
    out.push({ ...s, summation: pyRound(tot, 3), own_fraction: pyRound(own, 3) });
    prev = tot;
  }
  return out;
}

/** Map a decoded METAR to renderer inputs (Python render_params; every value's basis in weather.md §3).
 *  night: the ASOS photocell picks the night equation (caller decides, environment_spec.md §4.2-4.3). */
export function renderParams(d, night = false, marineLayerDepthFt = null, routineMinute = 56) {
  const p = { sources: {} };
  const vis = d.visibility || null;
  const visM = vis ? vis.m : null;
  const lowerBound = !!vis && (vis.prefix === 'P' || vis.sm >= 10);
  const beta = extinctionFromVisibility(visM, night);
  p.visibility_m = visM;
  p.visibility_is_lower_bound = lowerBound;          // '10SM' = 10 or more ([ASOS] "10 miles or greater")
  p.extinction_per_m = beta;                         // an UPPER bound when visibility_is_lower_bound
  p.sources.extinction = 'ASOS inversion, ' + (night ? 'night Allard' : 'day Koschmieder eps=0.055') + ' equation [R99]';
  const wx = d.weather || [];
  const phen = new Set(); for (const w of wx) if (!w.vicinity) for (const ph of (w.phenomena || [])) phen.add(ph);
  const desc = new Set(wx.map(w => (w.descriptor === undefined ? null : w.descriptor)));
  const fog = phen.has('FG');
  p.fog = null;
  if (fog || phen.has('BR')) {
    const vvL = (d.sky || []).find(s => s.cover === 'VV'); const vv = vvL ? vvL.height_ft : null;
    p.fog = { kind: fog ? 'fog' : 'mist', partial: ['BC', 'PR', 'MI'].some(x => desc.has(x)), shallow: desc.has('MI'),
      vertical_visibility_ft: vv,
      // INFERRED: a surface layer at least as deep as VV; without VV, mist fills the layer up to the lowest cloud base
      top_ft_min: vv != null ? vv : (d.ceiling_ft === undefined ? null : d.ceiling_ft) };
  }
  p.aerosol = { haze: phen.has('HZ'), smoke: phen.has('FU'),
    smoke_aloft: (d.rmk.obscuration_layers || []).filter(o => o.wx === 'FU'),
    distant: (d.rmk.phenomena || []).filter(x => ['FU', 'HZ', 'DU', 'SA'].includes(x.what)) };
  // clouds
  const layers = layerCoverages(d.sky || []);
  const depthFt = marineLayerDepthFt || 1000;
  for (const L of layers) {
    const h = L.height_ft;
    L.base_m = h == null ? null : h * FT_M;
    // INFERRED thickness: low stratus = marine-layer depth (MIT LL ATC-319 "usually less than 1000 feet"); else unknown
    L.thickness_m_guess = (h != null && h < 3000 && ['BKN', 'OVC', 'SCT'].includes(L.cover)) ? depthFt * FT_M : null;
  }
  // obscuration aloft by smoke / haze / dust / sand / volcanic ash ('FU FEW004', [7900] 13.35): an aerosol layer, not a
  // water cloud - kept in the summation, moved to aerosol_layers (= tools/env/metar_decode.py; review truth2-4)
  const aer = new Map((d.rmk.obscuration_layers || []).filter(o => AEROSOL_ALOFT.includes(o.wx)).map(o => [o.cover + '|' + o.height_ft, o.wx]));
  for (const L of layers) L.aerosol = aer.get(L.cover + '|' + L.height_ft) ?? null;
  p.aerosol_layers = layers.filter(L => L.aerosol);
  p.cloud_layers = layers.filter(L => !L.aerosol);
  const cl = p.cloud_layers;
  p.ceiling_m = d.ceiling_ft == null ? null : d.ceiling_ft * FT_M;
  let clear = 1.0; for (const L of cl) clear *= (1.0 - L.own_fraction);
  p.sun_visible_probability = pyRound(clear, 3);        // INFERRED (random overlap)
  const nOk = 8.0 * (1.0 - clear);
  // Kasten & Czeplak (1980) G(N)/G(0) = 1 - 0.75 (N/8)^3.4 [2nd, weather.md 3.4]
  p.global_irradiance_ratio = pyRound(1.0 - 0.75 * Math.pow(nOk / 8.0, 3.4), 3);
  p.sky_automated_limit_note = (d.sky || []).some(s => s.cover === 'CLR') ? 'CLR = no cloud detected at or below 12,000 ft [7900] Table 13-5 note 1' : null;
  // precipitation
  const pr = wx.filter(w => w.precip && w.precip.length && !w.vicinity);
  p.precip = null;
  if (pr.length) {
    const w0 = pr[0];
    // GRRA = rain (particles, rate, wetting) with a hail flag; hail alone has no drop parameters (not drawn; review
    // truth1-10; = tools/env/metar_decode.py)
    const hail = w0.precip.includes('GR') ? 'GR' : w0.precip.includes('GS') ? 'GS' : null;
    const kind = (w0.precip.length === 1 && w0.precip[0] === 'DZ') ? 'drizzle' : (hail && !w0.precip.includes('RA') ? 'hail' : 'rain');
    const inten = w0.intensity;
    // [7900] Table 9-4 rain-rate classes (in/h -> mm/h); drizzle intensity is visibility-based (Table 9-5)
    const rateCls = { light: [0.1, 2.54], moderate: [2.8, 7.62], heavy: [7.62, 25.0] }[inten || 'moderate'];
    let rate = null;
    const hp = d.rmk.precip_hourly_in;
    if (hp) {
      // Prrrr = amount since the last METAR [7900 13.46]; KSFO routine METARs at hh:56 (every routine report 2016-2026)
      let mins = 60;
      if (d.time && d.time.minute !== routineMinute) mins = pyMod(d.time.minute - routineMinute, 60) || 60;
      rate = hp * 25.4 * 60.0 / mins;
    }
    if (rate == null) rate = kind !== 'drizzle' ? Math.sqrt(Math.max(rateCls[0], 0.1) * rateCls[1]) : 0.25;   // INFERRED mid-class
    const lam = 4.1 * Math.pow(rate, -0.21);      // Marshall-Palmer slope per mm of diameter [GN07]
    const n0 = 8000.0;                            // m^-3 mm^-1 (2nd/NV, spec §4.6)
    p.precip = { kind, intensity: inten, showery: w0.descriptor === 'SH', thunder: w0.descriptor === 'TS', hail, rate_mm_h: pyRound(rate, 2),
      rate_basis: hp ? 'Prrrr remark' : 'intensity class midpoint (INFERRED)',
      drops_per_m3_gt_0p5mm: kind === 'rain' ? pyRound(n0 / lam * Math.exp(-lam * 0.5), 0) : null,
      median_volume_diameter_mm: kind === 'rain' ? pyRound(3.67 / lam, 2) : kind === 'drizzle' ? 0.3 : null,
      fall_speed_m_s: kind === 'rain' ? pyRound(200.0 * Math.sqrt(3.67 / lam / 2 / 1000.0), 2) : kind === 'drizzle' ? 1.0 : null };
  }
  // wetness (INFERRED state-machine inputs; the renderer integrates over time)
  const evs = d.rmk.wx_events || [];
  p.surface = { precip_now: pr.length > 0, precip_ended_this_hour: evs.some(e => e.event === 'end' && e.wx !== 'TS'),
    precip_since_last_metar_in: d.rmk.precip_hourly_in === undefined ? null : d.rmk.precip_hourly_in,
    precip_3or6h_in: d.rmk.precip_3or6h_in === undefined ? null : d.rmk.precip_3or6h_in };
  // wind / windsock [AC27F]: 0 at <= 3 kt, full at 15 kt, linear between (INFERRED shape)
  const w = d.wind || {};
  const spd = w.speed_kt || 0.0;
  const ext = spd < 3 ? 0.0 : Math.min(1.0, (spd - 3.0) / 12.0);
  p.wind = { from_true_deg: w.dir_true_deg === undefined ? null : w.dir_true_deg, speed_m_s: spd * KT_MS,
    gust_m_s: w.gust_kt ? w.gust_kt * KT_MS : null, variable: w.variable === undefined ? false : w.variable,
    range_deg: (w.var_from != null) ? [w.var_from, w.var_to] : null,
    windsock_extension: pyRound(ext, 3), windsock_full_at_kt: 15, windsock_moves_at_kt: 3,
    peak_since_last_metar_kt: d.rmk.peak_wind ? (d.rmk.peak_wind.speed_kt === undefined ? null : d.rmk.peak_wind.speed_kt) : null };
  // lightning [7900] Table 13-7: OCNL < 1/min, FRQ 1-6/min, CONS > 6/min (midpoints INFERRED)
  const lt = d.rmk.lightning || [];
  const tsHere = wx.some(x => x.descriptor === 'TS' && !x.vicinity);
  const tsVc = wx.some(x => x.descriptor === 'TS' && x.vicinity);
  const rateMap = { OCNL: 0.5, FRQ: 3.5, CONS: 8.0 };
  const rates = lt.map(x => (x.frequency in rateMap ? rateMap[x.frequency] : 0.5));
  p.lightning = { at_station: tsHere, vicinity: tsVc, flashes_per_min: Math.max(...(rates.length ? rates : [(tsHere || tsVc) ? 0.5 : 0.0])), reports: lt };
  p.flight_category = d.flight_category === undefined ? null : d.flight_category;
  return p;
}

// ------------------------------------------------------------------------------------------- convenience views
/** Split a multi-report text (relay / SNAPSHOT_METAR) into lines; the relay serves raw reports newest first. */
export function splitReports(text) { return String(text || '').split(/\r?\n/).map(s => s.trim()).filter(Boolean); }

/** Compact view for UI / legacy callers (the fields of the old js/livedata.js regex parser):
 *  {raw, windDir (deg true | null), windKt, gustKt, visSM, visPrefix, clouds [{cover, ft}], tempC, dewC, altim (inHg)}. */
export function metarSummary(d) {
  return { raw: d.raw, windDir: d.wind ? d.wind.dir_true_deg : null, windKt: d.wind ? d.wind.speed_kt : null, gustKt: d.wind ? d.wind.gust_kt : null,
    visSM: d.visibility ? d.visibility.sm : null, visPrefix: d.visibility ? d.visibility.prefix : null,
    clouds: (d.sky || []).filter(s => s.height_ft != null && s.cover !== 'VV').map(s => ({ cover: s.cover, ft: s.height_ft })),
    vvFt: ((d.sky || []).find(s => s.cover === 'VV') || {}).height_ft ?? null,
    tempC: d.temp_c_best, dewC: d.dewpoint_c_best, altim: d.altimeter_inhg ?? null, category: d.flight_category };
}
