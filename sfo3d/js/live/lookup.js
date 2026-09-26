// Airline / aircraft-type naming, the brand (livery) an aircraft wears, and the airline colour families.
// Names: Virtual Radar Server standing data (github.com/vradarserver/standing-data), with a few type-name corrections.
// Brand: the livery follows the airframe, not the callsign (SkyWest flies United Express, Alaska, Delta Connection and
// American Eagle airframes under SKW): registration -> brand from data/brands.js (tools/liveries/build_brands_js.py; US DOT
// BTS marketing-carrier data, observed), registration series and operator majority (inferred), else the callsign's airline.
// The registration comes from the feed, or for US aircraft from the ICAO 24-bit address (nNumberFromHex).
// Colour families: the runtime colours of the painted liveries (data/brands.js BRAND_INFO.colors, for the procedural
// airframe and far LOD; the imported models wear the baked livery textures, js/aircraft/liveries.js), else simplified
// families per airline (FAM below).
import { AIRLINES, TYPE_NAMES } from '../../data/lookup.js';
import { BRAND_INFO, CALLSIGN_BRAND, REGIONAL_OPS, REG_BRAND, REG_SERIES, OP_MAJORITY, REG_OVERRIDE } from '../../data/brands.js';

// ICAO type designators whose standing-data model name is a military or licence variant; use the common civil name
const TYPE_FIX = {
  GLF4: 'Gulfstream|IV / G400 / G450', GLF5: 'Gulfstream|V / G550', GLF6: 'Gulfstream|G650', C172: 'Cessna|172 Skyhawk', C182: 'Cessna|182 Skylane',
  PC12: 'Pilatus|PC-12', AT76: 'ATR|72-600', AT75: 'ATR|72-500', EC35: 'Airbus Helicopters|H135', EC45: 'Airbus Helicopters|H145', B06: 'Bell|206',
  AS50: 'Airbus Helicopters|H125 / AS350', R44: 'Robinson|R44', SR22: 'Cirrus|SR22', C208: 'Cessna|208 Caravan', BE20: 'Beechcraft|King Air 200',
  C130: 'Lockheed|C-130 Hercules', C17: 'Boeing|C-17 Globemaster III', K35R: 'Boeing|KC-135', MD11: 'McDonnell Douglas|MD-11',
};
const AIRLINE_FIX = { NKS: 'Spirit Airlines|NK', LXJ: 'Flexjet|' };

export function airlineInfo(icao) {
  const s = AIRLINE_FIX[icao] || AIRLINES[icao]; if (!s) return null;
  const [name, iata] = s.split('|'); return { icao, name, iata: iata || null };
}
// callsign "UAL1234" -> airline + flight number "UA 1234"
export function parseCallsign(cs) {
  if (!cs) return { callsign: null, airline: null, number: null, display: null };
  cs = cs.trim().toUpperCase();
  const m = /^([A-Z]{3})(\d[0-9A-Z]{0,4})$/.exec(cs);
  if (m) {
    const al = airlineInfo(m[1]);
    if (al) { const num = m[2].replace(/^0+(?=\d)/, ''); return { callsign: cs, airline: al, number: num, display: (al.iata ? al.iata + ' ' : al.icao + ' ') + num }; }
  }
  return { callsign: cs, airline: null, number: null, display: cs };
}
export function typeInfo(icao, desc) {
  const s = (icao && (TYPE_FIX[icao] || TYPE_NAMES[icao])) || null;
  if (!s) return { icao: icao || null, maker: null, model: null, full: desc ? titleCase(desc) : (icao || 'Unknown type'), engines: null, species: null, wake: null };
  const [maker, model, engines, engType, species, wake] = s.split('|');
  const short = maker.replace(/ (Aerospace|Aircraft|Aviation|Helicopters|Industries|Corporation|Company)$/, '');
  return { icao, maker, model, full: (short + ' ' + model).trim(), engines: +engines || null, engType, species, wake };
}
function titleCase(s) { return s.toLowerCase().replace(/\b([a-z])/g, (m, c) => c.toUpperCase()).replace(/\b(Ii|Iii|Iv)\b/g, x => x.toUpperCase()); }

// ------------------------------------------------------------------ colour families
const W = [0.94, 0.94, 0.95], NAVY = [0.07, 0.12, 0.3], GRAY = [0.6, 0.62, 0.66];
const L = (top, belly, tail, tail2, eng, bellyLine = -5, stripe = [0, 0, 0, 0]) => ({ top, belly, tail, tail2, eng, stripe, bellyLine, tailStyle: 1 });
export const NEUTRAL = L(W, W, [0.86, 0.87, 0.89], GRAY, [0.85, 0.86, 0.88]);
const FAM = {
  UAL: L(W, [0.16, 0.3, 0.6], [0.07, 0.14, 0.34], [0.16, 0.3, 0.6], [0.07, 0.14, 0.34], -0.35),
  ASA: L(W, W, [0.05, 0.15, 0.32], [0.1, 0.55, 0.6], [0.05, 0.15, 0.32], -5, [0.1, 0.55, 0.6, 1]),
  SWA: L([0.18, 0.3, 0.64], W, [0.18, 0.3, 0.64], [0.85, 0.15, 0.2], [0.18, 0.3, 0.64], 0.1),
  AAL: L([0.76, 0.78, 0.8], [0.76, 0.78, 0.8], [0.15, 0.3, 0.6], [0.8, 0.12, 0.15], [0.76, 0.78, 0.8]),
  DAL: L(W, [0.08, 0.12, 0.28], [0.08, 0.12, 0.28], [0.75, 0.1, 0.15], [0.08, 0.12, 0.28], -0.25),
  JBU: L(W, W, [0.1, 0.2, 0.5], [0.2, 0.45, 0.8], [0.1, 0.2, 0.5]),
  ACA: L(W, [0.25, 0.26, 0.28], [0.08, 0.08, 0.09], [0.75, 0.1, 0.1], W, -0.5),
  BAW: L(W, [0.09, 0.13, 0.32], [0.1, 0.16, 0.38], [0.78, 0.1, 0.14], GRAY, -0.3),
  DLH: L(W, W, [0.05, 0.1, 0.26], W, [0.05, 0.1, 0.26]),
  AFR: L(W, W, W, [0.1, 0.2, 0.55], W, -5, [0.1, 0.2, 0.55, 1]),
  KLM: L([0.0, 0.6, 0.85], W, [0.0, 0.6, 0.85], W, [0.0, 0.5, 0.78], -0.05),
  UAE: L(W, W, W, [0.75, 0.08, 0.1], W),
  QTR: L([0.9, 0.9, 0.9], [0.9, 0.9, 0.9], [0.38, 0.05, 0.2], W, [0.9, 0.9, 0.9]),
  SIA: L(W, W, [0.07, 0.16, 0.36], [0.9, 0.7, 0.2], W, -5, [0.07, 0.16, 0.36, 1]),
  CPA: L(W, [0.7, 0.72, 0.74], [0.1, 0.4, 0.35], W, W, -0.6),
  EVA: L(W, [0.55, 0.6, 0.55], [0.12, 0.36, 0.26], [0.95, 0.55, 0.1], [0.12, 0.36, 0.26], -0.55),
  CAL: L(W, W, [0.72, 0.32, 0.46], W, W),
  JAL: L(W, W, W, [0.8, 0.08, 0.1], W),
  ANA: L(W, [0.85, 0.86, 0.88], W, [0.05, 0.25, 0.55], [0.05, 0.25, 0.55], -0.5, [0.05, 0.25, 0.55, 1]),
  KAL: L([0.58, 0.75, 0.88], [0.7, 0.72, 0.75], W, [0.1, 0.25, 0.6], [0.58, 0.75, 0.88], -0.3),
  AAR: L(W, [0.62, 0.62, 0.66], [0.6, 0.6, 0.64], [0.85, 0.25, 0.2], W, -0.4),
  QFA: L(W, W, [0.82, 0.08, 0.1], W, W),
  ANZ: L(W, W, [0.06, 0.06, 0.07], W, [0.06, 0.06, 0.07]),
  WJA: L(W, W, [0.0, 0.33, 0.42], [0.1, 0.2, 0.4], W),
  VIR: L([0.88, 0.88, 0.9], [0.88, 0.88, 0.9], [0.78, 0.07, 0.15], [0.35, 0.1, 0.4], [0.78, 0.07, 0.15]),
  EIN: L(W, W, [0.0, 0.45, 0.4], W, W),
  THY: L(W, W, [0.8, 0.05, 0.1], W, W),
  AIC: L(W, W, [0.7, 0.1, 0.25], [0.85, 0.65, 0.25], W),
  PAL: L(W, W, [0.1, 0.2, 0.5], [0.85, 0.15, 0.15], W),
  CSN: L(W, W, [0.2, 0.45, 0.8], [0.85, 0.15, 0.2], W),
  FJI: L(W, W, [0.25, 0.18, 0.12], W, W),
  HAL: L(W, W, [0.35, 0.15, 0.45], [0.85, 0.35, 0.55], W),
  FFT: L(W, [0.1, 0.45, 0.25], [0.1, 0.45, 0.25], W, W, -0.4),
  NKS: L([0.95, 0.85, 0.12], [0.95, 0.85, 0.12], [0.95, 0.85, 0.12], [0.1, 0.1, 0.1], [0.95, 0.85, 0.12]),
  SCX: L(W, NAVY, [0.95, 0.5, 0.1], NAVY, W, -0.4),
  VOI: L(W, W, [0.45, 0.15, 0.5], [0.2, 0.7, 0.4], W),
  VIV: L(W, W, [0.35, 0.7, 0.2], W, W),
  AMX: L(W, [0.85, 0.86, 0.88], [0.06, 0.12, 0.25], W, W, -0.5),
  AVA: L([0.8, 0.05, 0.1], [0.8, 0.05, 0.1], [0.8, 0.05, 0.1], W, [0.8, 0.05, 0.1]),
  CMP: L(W, W, [0.07, 0.14, 0.36], [0.8, 0.65, 0.3], W),
  FDX: L(W, [0.55, 0.57, 0.6], [0.3, 0.1, 0.45], [0.95, 0.45, 0.1], W, -0.45),
  UPS: L([0.88, 0.88, 0.88], [0.3, 0.2, 0.12], [0.3, 0.2, 0.12], [0.85, 0.65, 0.2], [0.3, 0.2, 0.12], -0.2),
  GTI: L(W, W, [0.1, 0.2, 0.45], W, W),
  MXY: L(W, NAVY, NAVY, [0.3, 0.6, 0.85], W, -0.4),
  SWR: L(W, W, [0.82, 0.05, 0.1], W, W),
  IBE: L(W, W, [0.8, 0.1, 0.15], [0.95, 0.75, 0.1], W),
  AUA: L(W, W, [0.82, 0.05, 0.1], W, W),
  SAS: L(W, W, [0.07, 0.12, 0.35], W, [0.07, 0.12, 0.35]),
};
const SAME = { QXE: 'ASA', GJS: 'UAL', ASH: 'UAL', ENY: 'AAL', PDT: 'AAL', JIA: 'AAL', JZA: 'ACA', TAI: 'AVA', LRC: 'AVA' };
const famOf = (code) => { if (!code) return null; const b = code.split('-')[0]; return FAM[SAME[b] || b] || null; };

// ------------------------------------------------------------------ registration from the ICAO 24-bit address (US)
// The FAA assigns US Mode S codes A00001..ADF7C7 to N-numbers in a fixed order (N1, N1A, N1AA, ..., N10, ...): 1-5
// characters after N, digits then up to two letters (no I or O). Verified: identical to the registration for 392,062
// of 392,213 US entries of the tar1090-db aircraft database (d9459d7, 21 Sep 2026; the 151 others are database errors
// such as 6-character N-numbers or stale records), see docs/research/liveries_impl.md.
const NCH = 'ABCDEFGHJKLMNPQRSTUVWXYZ';
const NSUF = 1 + 24 * 25, NB4 = 1 + 24 + 10, NB3 = 10 * NB4 + NSUF, NB2 = 10 * NB3 + NSUF, NB1 = 10 * NB2 + NSUF;
const nSuffix = (r) => { if (r === 0) return ''; r -= 1; const i = Math.floor(r / 25), j = r % 25; return NCH[i] + (j ? NCH[j - 1] : ''); };
export function nNumberFromHex(hex) {
  const v = parseInt(hex, 16); if (!(v >= 0xA00001 && v <= 0xADF7C7)) return null;
  let r = v - 0xA00001; let out = 'N' + (Math.floor(r / NB1) + 1); r %= NB1;
  if (r < NSUF) return out + nSuffix(r); r -= NSUF;
  out += Math.floor(r / NB2); r %= NB2; if (r < NSUF) return out + nSuffix(r); r -= NSUF;
  out += Math.floor(r / NB3); r %= NB3; if (r < NSUF) return out + nSuffix(r); r -= NSUF;
  out += Math.floor(r / NB4); r %= NB4; if (r === 0) return out; return out + (r <= 24 ? NCH[r - 1] : String(r - 25));
}

// ------------------------------------------------------------------ brand
const REG_MAP = new Map();
for (const b in REG_BRAND) for (const r of REG_BRAND[b].split(' ')) if (r) REG_MAP.set(r, b);
const ADSB_BTS = { E75L: 'E175', E75S: 'E175', E170: 'E170', CRJ2: 'CRJ2', CRJ7: 'CRJ7', CRJ9: 'CRJ9', E145: 'E145', E135: 'E145' };
// -> { brand, src: 'obs' | 'inf', why, reg, special? } or null (no brand known: neutral livery)
//   airline: ICAO designator of the callsign; reg: registration from the feed; hex: ICAO address; icaoType: ADS-B type
export function brandFor({ airline = null, reg = null, hex = null, icaoType = null } = {}) {
  let R = reg ? String(reg).toUpperCase().replace(/-/g, '') : null, regSrc = 'feed';
  if (!R && hex) { R = nNumberFromHex(hex); regSrc = 'hex'; }
  if (R && REG_OVERRIDE[R]) { const o = REG_OVERRIDE[R]; return { brand: o.brand, src: 'obs', why: 'registration ' + R + ': ' + o.special, reg: R, special: o }; }
  if (R && REG_MAP.has(R)) return { brand: REG_MAP.get(R), src: 'obs', why: 'registration ' + R + ' (' + regSrc + ') in the US DOT BTS tail table', reg: R };
  const op = airline && REGIONAL_OPS[airline];
  if (op) {
    const t = ADSB_BTS[icaoType] || null;
    const m = R && /^N(\d+)([A-Z]*)$/.exec(R);
    if (m && t) for (const [o, typ, nd, suf, lo, hi, b] of REG_SERIES) {
      if (o === op && typ === t && m[1].length === nd && m[2] === suf && +m[1] >= lo && +m[1] <= hi) return { brand: b, src: 'inf', why: 'registration series ' + 'N' + lo + suf + '-N' + hi + suf, reg: R };
    }
    const M = OP_MAJORITY[op];
    if (M) { const b = (t && M[t]) || M['*']; return { brand: b, src: 'inf', why: 'majority brand of ' + airline + (t ? ' ' + t : '') + ' flights', reg: R }; }
  }
  if (airline && CALLSIGN_BRAND[airline]) return { brand: CALLSIGN_BRAND[airline], src: 'obs', why: 'callsign ' + airline + ' (the airline\'s own flights)', reg: R };
  return null;
}
export function brandName(code) { return (code && BRAND_INFO[code] && BRAND_INFO[code].name) || null; }

// ------------------------------------------------------------------ liveries (colour family objects)
const HEX = (h) => { h = h.replace('#', ''); return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16) / 255); };
function familyOf(code) {
  const I = code && BRAND_INFO[code];
  if (I && I.colors) {
    const c = I.colors; const s = c.stripe ? [...HEX(c.stripe), 1] : [0, 0, 0, 0];
    // bellyLine in data/brands.js: belly boundary as a fraction of the fuselage half height (cabin eta, painter convention);
    // the colour families use metres on a 1.98 m radius fuselage (scaled per type in js/aircraft/fleet.js / aircraft.js)
    return L(HEX(c.top), HEX(c.belly), HEX(c.tail), HEX(c.tail2 || c.tail), HEX(c.eng), c.bellyLine != null ? c.bellyLine * 1.98 : -5, s);
  }
  return famOf(code);
}
const livCache = new Map();
function livery(code, B, airline) {
  const k = (code || '-') + '|' + (B ? B.src + '|' + B.why : '') + '|' + (airline || '');
  let v = livCache.get(k);
  if (!v) {
    const fam = (code && familyOf(code)) || famOf(airline) || NEUTRAL;
    v = Object.assign({}, fam, { brand: code || null, brandName: brandName(code), brandSrc: B ? B.src : null, brandWhy: B ? B.why : null,
      reg: B ? B.reg || null : null, special: B && B.special ? B.special.special : null, airline: airline || null, resolved: !!(B && B.reg) });
    livCache.set(k, v);
  }
  return v;
}
// callsign airline (+ registration / ICAO address / type when known) -> livery object: colour family + brand fields
// (brand, brandName, brandSrc 'obs' | 'inf', brandWhy). Unknown operators: NEUTRAL (white, grey tail, no titles).
export function liveryForAirline(icao, reg = null, hex = null, icaoType = null) {
  const B = brandFor({ airline: icao || null, reg, hex, icaoType });
  return livery(B ? B.brand : null, B, icao || null);
}
// the livery an aircraft wears, from the livery its track carries plus the aircraft's own ICAO address and type (used
// by js/live/aircraft.js while js/live/traffic.js passes only the callsign airline)
export function resolveLivery(L, hex, icaoType) {
  if (!L || L.resolved || !hex) return L;
  const B = brandFor({ airline: L.airline, reg: L.reg, hex, icaoType });
  if (!B) return L;
  return livery(B.brand, B, L.airline);
}

// ------------------------------------------------------------------ freighters
// An aircraft is drawn as a freighter (no cabin windows: js/shaders/aircraft_real.js uNoCabin) when (review round 1: only
// the FedEx / UPS brands dropped their windows; 777Fs, 747-400Fs, 767Fs of other operators were drawn with cabin rows)
//  1. its operator is an all-cargo airline (ICAO designators of the callsign; observed at SFO in the recorder and the
//     census, docs/research/liveries.md §1: FedEx, UPS, Kalitta, Atlas, Cargolux, Lufthansa Cargo, ABX, ATI, China
//     Southern Cargo (CSG, B-223G 777F), Air Incheon, AirBridgeCargo, Amerijet, Nippon Cargo, Air China Cargo, China Cargo,
//     SF Airlines, Polar, Martinair Cargo, Western Global), or
//  2. its operator flies that type at SFO only as a freighter (China Airlines 747-400 / 777: the passenger fleet at SFO is
//     A350 / 777-300ER; EVA B77L = 777F; Asiana 747-400; Cathay 747 = 747-8F / -400F; Korean 777F), or
//  3. the aircraft database's own description says so (tar1090-db desc "...F", "FREIGHTER").
export const CARGO_OPS = new Set(['FDX', 'UPS', 'CKS', 'GTI', 'CLX', 'GEC', 'ABX', 'ATN', 'CSG', 'AIH', 'ABW', 'AJT', 'NCA', 'CAO', 'CKK', 'CSS', 'PAC', 'MPH', 'WGN']);
const CARGO_TYPE = { CAL: ['B744', 'B77L'], EVA: ['B77L'], AAR: ['B744'], CPA: ['B744', 'B748'], KAL: ['B77L'] };
export function isFreighter({ airline = null, icaoType = null, desc = null, brandCargo = false } = {}) {
  if (brandCargo) return true;
  if (airline && CARGO_OPS.has(airline)) return true;
  if (airline && icaoType && CARGO_TYPE[airline] && CARGO_TYPE[airline].includes(icaoType)) return true;
  if (desc && /(FREIGHT|CARGO|\b\d{3}-?\d*F\b|-F$)/i.test(desc)) return true;
  return false;
}
